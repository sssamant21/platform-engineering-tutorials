"""Chapter 106 deterministic profiling and benchmarking lab; no production actions."""
from __future__ import annotations
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import argparse,asyncio,cProfile,io,json,math,pstats,statistics,time,tracemalloc
class PerfError(ValueError):pass
def validate_samples(samples):
    if not isinstance(samples,(list,tuple)) or not samples:raise PerfError("empty samples")
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in samples):raise PerfError("invalid latency")
def percentile(samples,p):
    validate_samples(samples)
    if type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=100:raise PerfError("percentile")
    a=sorted(samples);pos=(len(a)-1)*p/100;lo=math.floor(pos);hi=math.ceil(pos)
    return a[lo]+(a[hi]-a[lo])*(pos-lo)
def summary(samples):
    validate_samples(samples)
    return {"count":len(samples),"mean_ms":statistics.fmean(samples),"p50_ms":percentile(samples,50),
            "p95_ms":percentile(samples,95),"p99_ms":percentile(samples,99),"max_ms":max(samples)}
def budget(samples,p95_limit_ms=100,p99_limit_ms=200):
    if type(p95_limit_ms) not in (int,float) or type(p99_limit_ms) not in (int,float) or p95_limit_ms<=0 or p99_limit_ms<=0:raise PerfError("limits")
    s=summary(samples)
    return {"pass":s["p95_ms"]<=p95_limit_ms and s["p99_ms"]<=p99_limit_ms,"summary":s}
def slow_count(values):
    return sum(values.count(x) for x in set(values))
def fast_count(values):
    d={}
    for x in values:d[x]=d.get(x,0)+1
    return sum(d.values())
def cpu_profile(fn,*args):
    profiler=cProfile.Profile();profiler.enable()
    try:result=fn(*args)
    finally:profiler.disable()
    stream=io.StringIO();pstats.Stats(profiler,stream=stream).sort_stats("cumulative").print_stats(12)
    return {"result":result,"profile_excerpt":stream.getvalue()[:6000]}
def memory_profile(fn,*args):
    started=tracemalloc.is_tracing()
    if not started:tracemalloc.start()
    before,_=tracemalloc.get_traced_memory()
    try:
        result=fn(*args);_,peak=tracemalloc.get_traced_memory()
    finally:
        if not started:tracemalloc.stop()
    return {"result":result,"peak_traced_bytes":max(0,peak-before),"scope":"Python traced allocations only"}
def benchmark(fn,inputs,iterations=5):
    if type(iterations) is not int or not 1<=iterations<=1000:raise PerfError("iterations")
    timings=[]
    for _ in range(iterations):
        start=time.perf_counter_ns();fn(inputs);timings.append((time.perf_counter_ns()-start)/1_000_000)
    return summary(timings)
async def io_async(delay=0):
    if type(delay) not in (int,float) or delay<0 or delay>0.1:raise PerfError("delay")
    await asyncio.sleep(delay)
    return "ok"
async def async_batch(n=5):
    if type(n) is not int or not 1<=n<=100:raise PerfError("batch")
    return await asyncio.gather(*(io_async(0) for _ in range(n)))
def threaded_io(n=5):
    if type(n) is not int or not 1<=n<=100:raise PerfError("batch")
    with ThreadPoolExecutor(max_workers=min(n,8)) as pool:return list(pool.map(lambda _: "ok",range(n)))
@dataclass(frozen=True)
class Incident:
    name:str
    baseline_p95_ms:float
    current_p95_ms:float
    cpu_pct:float
    memory_pct:float
    def evaluate(self):
        values=(self.baseline_p95_ms,self.current_p95_ms,self.cpu_pct,self.memory_pct)
        if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in values):raise PerfError("incident")
        if self.baseline_p95_ms<=0 or self.cpu_pct>100 or self.memory_pct>100:raise PerfError("incident range")
        return {"incident":self.name,"latency_regression":self.current_p95_ms/self.baseline_p95_ms>=2,
                "cpu_pressure":self.cpu_pct>=85,"memory_pressure":self.memory_pct>=90,
                "action":"investigate-only","mutations":0}
def demo():
    data=[i%30 for i in range(150)]
    slow=cpu_profile(slow_count,data);fast=cpu_profile(fast_count,data)
    return {"mode":"local-offline","synthetic_latency":summary([10,11,12,14,16,22,35,80,140,230]),
            "slo":budget([10,11,12,14,16,22,35,80,140,230]),
            "cpu_slow_result":slow["result"],"cpu_fast_result":fast["result"],
            "memory":memory_profile(fast_count,data),
            "incident":Incident("postgres-query-latency",40,160,91,65).evaluate(),
            "mutations":0,"network_calls":0}
def main(argv=None):
    p=argparse.ArgumentParser(description="Offline Python performance lab")
    p.add_argument("--dry-run",action="store_true");p.add_argument("--profile",action="store_true")
    a=p.parse_args(argv);out=demo()
    if a.profile:out["cprofile"]=cpu_profile(slow_count,[i%30 for i in range(150)])["profile_excerpt"]
    print(json.dumps(out,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
