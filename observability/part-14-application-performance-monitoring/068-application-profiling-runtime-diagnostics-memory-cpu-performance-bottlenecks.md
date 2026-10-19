# Chapter 068 — Application Profiling, Runtime Diagnostics, Memory, CPU and Performance Bottlenecks

**Part 14 — Application Performance Monitoring**  
**Audience:** SRE, DBRE, Python/Java/Go platform engineers and incident responders.  
**Prerequisites:** Chapters 066–067; application RED metrics and tracing.

## Objectives

Distinguish CPU time from wall time, memory growth from allocation churn, runtime contention from dependency waits, and genuine regressions from profiler overhead. Capture safe profiles and connect findings to p95/p99, error rates, queueing and resource limits.

## Architecture

```text
HTTP requests -> application workers -> DB/Redis/Kafka
       |                |
 RED histograms    CPU / heap / GC / threads / async / locks
       |                |
 distributed traces + bounded profiler captures
       |                |
 Prometheus + Grafana + profiles + incident timeline
       |
 safe mitigation -> SLO validation -> rollback
```

## Theory and operational tradeoffs

| Signal | Diagnosis | Caveat |
|---|---|---|
| CPU utilization | busy cores, hotspots | CPU quota throttling can hide demand |
| Wall vs CPU time | blocked vs executing work | high wall time may be downstream wait |
| RSS and heap | memory pressure | allocator fragmentation and page cache differ |
| Allocations and GC | churn, pauses | collection pauses vary by runtime |
| Threads and goroutines | lock and scheduler contention | high count alone is not a leak |
| Event loop delay | blocking async work | distinguish scheduling delay from I/O |
| p95/p99 histogram | user impact | don't average per-instance percentiles |
| Profiling overhead | measurement bias | benchmark with profiler off/on |

**Python:** `cProfile` records deterministic function-call statistics, `tracemalloc` tracks Python allocations (not all native memory), and `py-spy` is a sampling profiler requiring appropriate OS permissions. Understand the GIL, process parallelism and blocking I/O.

**JVM:** use Java Flight Recorder, JFR events, GC logs and heap telemetry; do not casually collect huge heap dumps containing sensitive data. **Go:** `net/http/pprof` must be access-restricted; inspect CPU, heap, mutex and goroutine profiles.

## Executable local Python profiling

```python
# profile_demo.py: safe local synthetic workload
import cProfile,pstats,io,tracemalloc,time
def work(n=50000):
 return sum((i*i)%97 for i in range(n))
tracemalloc.start()
prof=cProfile.Profile()
start=time.perf_counter()
prof.enable()
for _ in range(20):work()
prof.disable()
elapsed=time.perf_counter()-start
current,peak=tracemalloc.get_traced_memory()
out=io.StringIO()
pstats.Stats(prof,stream=out).sort_stats("cumulative").print_stats(10)
print(out.getvalue())
print({"wall_seconds":round(elapsed,3),"traced_current_bytes":current,"traced_peak_bytes":peak})
```

```bash
python3 profile_demo.py
python3 -m cProfile -s cumulative profile_demo.py
```

For live workloads, prefer approved short-duration sampling and compare overhead against baseline. `perf`, eBPF profilers, JVM JFR and Go pprof require runtime-specific configuration and permissions; validate on staging first.

## Kubernetes and dependency correlation

```bash
kubectl top pod -n STAGING_NAMESPACE
kubectl describe pod APP_POD -n STAGING_NAMESPACE
kubectl get pod APP_POD -n STAGING_NAMESPACE -o jsonpath='{.status.containerStatuses[*].lastState}'
```

Review CPU throttling, OOMKilled events, resource requests/limits, node pressure and container restarts. Compare traces for PostgreSQL lock waits, Redis command latency and Kafka consumer backpressure before blaming application CPU.

## Production incident simulation

After a deployment, API p99 rises and pods scale out without restoring throughput. CPU utilization appears moderate, but throttling and thread-pool waits rise; heap allocation churn increases, and PostgreSQL connection acquisition dominates trace spans. Compare wall/CPU time, container quotas, GC and dependency waits. Apply one reversible mitigation at a time and validate user-facing SLO recovery.

## Offline readiness gate

The following files validate a **synthetic** staging review, not live profiling.

### healthy.json

```json
{
  "owner": "runtime-sre",
  "environment": "staging",
  "change_id": "OBS-068",
  "cpu_percent": 58,
  "max_cpu_percent": 85,
  "memory_mb": 600,
  "max_memory_mb": 1024,
  "p95_ms": 170,
  "max_p95_ms": 300,
  "profiler_overhead_percent": 2,
  "max_profiler_overhead_percent": 5,
  "destructive_change": false,
  "checks": {
    "baseline": true,
    "cpu_profile": true,
    "memory_profile": true,
    "gc_review": true,
    "thread_review": true,
    "async_review": true,
    "io_wait": true,
    "db_waits": true,
    "redis_waits": true,
    "container_limits": true,
    "flamegraph": true,
    "profiler_overhead": true,
    "latency_histograms": true,
    "security": true,
    "incident_review": true,
    "rollback": true
  }
}
```

### profiling_gate.py

```python
"""Offline profiling readiness validation. No live process profiling."""
import json,sys
from pathlib import Path
CHECKS=["baseline","cpu_profile","memory_profile","gc_review","thread_review","async_review","io_wait","db_waits","redis_waits","container_limits","flamegraph","profiler_overhead","latency_histograms","security","incident_review","rollback"]
LIMITS=[("cpu_percent","max_cpu_percent"),("memory_mb","max_memory_mb"),("p95_ms","max_p95_ms"),("profiler_overhead_percent","max_profiler_overhead_percent")]
def validate(d):
 e=[]
 if not isinstance(d,dict):return ["expected object"]
 for k in ("owner","environment","change_id"):
  if not isinstance(d.get(k),str) or not d[k].strip():e.append("missing "+k)
 if d.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 c=d.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append("unverified "+k)
 for a,b in LIMITS:
  x,y=d.get(a),d.get(b)
  if type(x) not in (int,float) or x<0:e.append("invalid "+a)
  if type(y) not in (int,float) or y<0:e.append("invalid "+b)
  if type(x) in (int,float) and type(y) in (int,float) and x>y:e.append("breach "+a)
 for k in ("cpu_percent","max_cpu_percent","profiler_overhead_percent","max_profiler_overhead_percent"):
  x=d.get(k)
  if type(x) in (int,float) and x>100:e.append("invalid percent "+k)
 if d.get("destructive_change") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_profiling_gate.py

```python
import copy,json,unittest
from pathlib import Path
from profiling_gate import validate
class ProfilingTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["baseline"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["cpu_profile"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["memory_profile"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["gc_review"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["thread_review"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["async_review"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["io_wait"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["db_waits"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["redis_waits"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["container_limits"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["flamegraph"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["profiler_overhead"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["latency_histograms"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["security"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["incident_review"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["cpu_percent"]=95
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["memory_mb"]=2048
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["p95_ms"]=600
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["profiler_overhead_percent"]=20
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["max_cpu_percent"]=150
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["destructive_change"]=True
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["checks"]=None
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 profiling_gate.py healthy.json
python3 -m unittest -v test_profiling_gate.py
```

Expected PASS and **28 authored tests**; execution not yet verified.

## 24 hands-on exercises

1. Capture baseline RED signals.
2. Inspect Linux process CPU.
3. Inspect thread utilization.
4. Inspect process RSS.
5. Review cgroup CPU throttling.
6. Review memory working set.
7. Run Python cProfile.
8. Compare cumulative and per-call time.
9. Run tracemalloc snapshot.
10. Inspect allocation diff.
11. Review garbage collector metrics.
12. Inspect thread stack safely.
13. Review async event-loop blocking.
14. Profile connection-pool waits.
15. Review PostgreSQL query waits.
16. Review Redis latency.
17. Review JVM JFR.
18. Review JVM heap and GC.
19. Review Go pprof.
20. Compare flamegraph hotspots.
21. Review profiler overhead.
22. Perform bounded load test.
23. Simulate staging regression.
24. Verify rollback and SLO recovery.

## 24 production failure scenarios

1. **CPU-bound request:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
2. **GIL contention:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
3. **Thread pool starvation:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
4. **Event loop blocking:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
5. **Memory leak:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
6. **Memory fragmentation:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
7. **GC pause spike:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
8. **OOMKilled pod:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
9. **Cgroup CPU throttling:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
10. **Disk IO wait:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
11. **Network retry storm:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
12. **Database connection wait:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
13. **Slow SQL plan:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
14. **Redis hot key:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
15. **Kafka consumer backpressure:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
16. **JVM heap exhaustion:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
17. **JVM allocation churn:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
18. **Go goroutine leak:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
19. **Lock contention:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
20. **High profiler overhead:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
21. **Misleading average latency:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
22. **Incorrect flamegraph attribution:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
23. **Sampling bias:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.
24. **Rollback incomplete:** collect before/after RED, profiler, runtime and dependency evidence; document approved mitigation and rollback.

## Eight production runbooks

1. **CPU saturation: compare wall vs CPU time, flamegraphs, throttling and workload shape.**
2. **Memory growth: inspect RSS, heap, allocations, GC and container limits.**
3. **Event-loop stall: inspect blocking sync work, queue latency and cancellation.**
4. **JVM runtime: inspect JFR, GC logs, allocation rate and heap pressure.**
5. **Go runtime: inspect pprof CPU/heap and goroutine profiles.**
6. **Dependency wait: correlate traces, DB locks, Redis command latency and pool waits.**
7. **Profiler safety: scope sampling, protect sensitive symbols and avoid unbounded production captures.**
8. **Recovery: compare before/after SLOs, rollback and preserve sanitized evidence.**

## 100-point assessment

| Area | Points |
|---|---:|
| Runtime architecture and profiling theory | 20 |
| CPU, threads and async diagnosis | 20 |
| Memory, GC and leak diagnosis | 20 |
| Lab, security and profiler overhead | 20 |
| Incident recovery and rollback | 20 |
| **Total** | **100** |

Suggested pass 85/100. Production readiness requires witnessed safe profiling, independent SLO measurements and rollback drills.

**Companion:** [Chapter 068 lab](labs/068-application-profiling-runtime-diagnostics-memory-cpu-performance-bottlenecks-lab.md).

**Next:** Chapter 069 — Application Performance Testing, Load, Stress, Soak and Capacity Observability.
