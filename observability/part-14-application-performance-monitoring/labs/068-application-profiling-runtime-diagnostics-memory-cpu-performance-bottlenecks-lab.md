# Chapter 068 — Application Profiling and Runtime Diagnostics Lab

**Part 14 — Application Performance Monitoring**

## Offline lab

Save `healthy.json`, `profiling_gate.py` and `test_profiling_gate.py` from [Chapter 068](../068-application-profiling-runtime-diagnostics-memory-cpu-performance-bottlenecks.md).

```bash
python3 profiling_gate.py healthy.json
python3 -m unittest -v test_profiling_gate.py
```

Expected PASS and 28 authored tests; record actual output.

## Staging execution

1. Record owner, version, change ID, baseline throughput, error rate and p95/p99.
2. Inspect Linux CPU, RSS and thread counts.
3. Inspect Kubernetes CPU throttling, limits and OOM events.
4. Run bounded cProfile and tracemalloc captures on a synthetic workload.
5. Review wall vs CPU time, hot functions, allocations and GC.
6. Compare runtime waits against PostgreSQL, Redis and Kafka spans.
7. Review approved JVM JFR or Go pprof where applicable.
8. Quantify profiler overhead with and without instrumentation.
9. Simulate bounded staging CPU or memory pressure.
10. Restore baseline and validate user-facing SLO recovery.

## Negative drills

Check missing reviews, unsafe environment, CPU/memory/p95 breaches, profiler overhead breach, invalid percentages and unsafe changes.

## Evidence

```text
UTC / owner / change:
RED baseline and regression:
CPU vs wall time:
Memory / allocations / GC:
Threads / event loop / runtime:
Dependency wait spans:
Profiler duration and overhead:
Sensitive-data and access review:
Rollback and SLO recovery:
Offline gate and 28 test outcomes:
```

Synthetic gates are not live performance certification.
