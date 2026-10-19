"""Chapter 107: bounded, offline concurrency exercises. Python 3.11+."""
from __future__ import annotations
import argparse,asyncio,concurrent.futures,hashlib,json,math,statistics,threading,time
from dataclasses import dataclass
class ConcurrencyError(ValueError):pass
def count(value,lower=1,upper=64):
    if type(value) is not int or not lower<=value<=upper:raise ConcurrencyError("invalid concurrency limit")
    return value
def cpu_task(n):
    if type(n) is not int or not 0<=n<=200000:raise ConcurrencyError("invalid workload")
    return sum(i*i for i in range(n))
def serial_cpu(work):
    return [cpu_task(n) for n in work]
def threaded_cpu(work,workers=2):
    count(workers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(cpu_task,work))
def process_cpu(work,workers=2):
    count(workers,1,8)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(cpu_task,work))
def thread_io(items,workers=4):
    count(workers)
    def synthetic(item):
        if type(item) is not int or item<0:raise ConcurrencyError("invalid item")
        time.sleep(0.001)
        return item*2
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(synthetic,items))
async def bounded_async(items,limit=4):
    count(limit)
    semaphore=asyncio.Semaphore(limit)
    active=0;peak=0;lock=asyncio.Lock()
    async def one(item):
        nonlocal active,peak
        if type(item) is not int or item<0:raise ConcurrencyError("invalid item")
        async with semaphore:
            async with lock:
                active+=1;peak=max(peak,active)
            try:
                await asyncio.sleep(0.001)
                return item*2
            finally:
                async with lock:active-=1
    values=await asyncio.gather(*(one(i) for i in items))
    return {"values":values,"peak_inflight":peak,"limit":limit}
async def cancel_example():
    task=asyncio.create_task(asyncio.sleep(10))
    task.cancel()
    try:await task
    except asyncio.CancelledError:return {"cancelled":True,"active_tasks":0}
    return {"cancelled":False,"active_tasks":0}
async def timeout_example(seconds=0.001):
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<seconds<=1:raise ConcurrencyError("timeout")
    try:await asyncio.wait_for(asyncio.sleep(1),timeout=seconds)
    except TimeoutError:return {"timed_out":True}
    return {"timed_out":False}
class SafeCounter:
    def __init__(self):self._value=0;self._lock=threading.Lock()
    def add(self,amount=1):
        if type(amount) is not int or amount<0:raise ConcurrencyError("amount")
        with self._lock:self._value+=amount
    @property
    def value(self):
        with self._lock:return self._value
def backpressure(arrivals,capacity):
    count(capacity,1,1000)
    if type(arrivals) is not int or arrivals<0:raise ConcurrencyError("arrivals")
    return {"accepted":min(arrivals,capacity),"rejected":max(0,arrivals-capacity),"queue_capacity":capacity}
def percentile(samples,p):
    if not isinstance(samples,(list,tuple)) or not samples:raise ConcurrencyError("samples")
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in samples):raise ConcurrencyError("samples")
    if type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=100:raise ConcurrencyError("percentile")
    a=sorted(samples);pos=(len(a)-1)*p/100;lo=math.floor(pos);hi=math.ceil(pos)
    return a[lo]+(a[hi]-a[lo])*(pos-lo)
def benchmark(fn,*args,iterations=3):
    count(iterations,1,30)
    ms=[]
    for _ in range(iterations):
        start=time.perf_counter_ns();fn(*args);ms.append((time.perf_counter_ns()-start)/1e6)
    return {"iterations":iterations,"median_ms":statistics.median(ms),"p95_ms":percentile(ms,95),"min_ms":min(ms)}
@dataclass(frozen=True)
class Incident:
    name:str
    inflight:int
    pool_capacity:int
    queue_depth:int
    error_rate:float
    def diagnose(self):
        if not isinstance(self.name,str) or not self.name.strip():raise ConcurrencyError("name")
        if any(type(x) is not int or x<0 for x in (self.inflight,self.pool_capacity,self.queue_depth)):raise ConcurrencyError("capacity")
        if type(self.error_rate) not in (int,float) or not math.isfinite(self.error_rate) or not 0<=self.error_rate<=1:raise ConcurrencyError("errors")
        return {"incident":self.name,"saturated":self.pool_capacity==0 or self.inflight>=self.pool_capacity,
                "queued":self.queue_depth>0,"error_budget_risk":self.error_rate>=0.05,
                "action":"investigate-only","mutations":0}
def demo():
    work=[1000,2000,3000]
    async_result=asyncio.run(bounded_async([1,2,3,4,5],2))
    return {"mode":"offline","serial_cpu":serial_cpu(work),"thread_cpu":threaded_cpu(work,2),
            "thread_io":thread_io([1,2,3],2),"async_io":async_result,
            "backpressure":backpressure(12,5),
            "incident":Incident("postgres-pool",15,10,22,0.08).diagnose(),
            "mutations":0,"network_calls":0}
def main(argv=None):
    p=argparse.ArgumentParser(description="Offline Python concurrency lab")
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--process-demo",action="store_true",help="run bounded process pool explicitly")
    a=p.parse_args(argv);out=demo()
    if a.process_demo:out["process_cpu"]=process_cpu([1000,2000,3000],2)
    print(json.dumps(out,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
