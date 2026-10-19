# Chapter 106 — Python Application Performance Profiling and Optimization SRE/DBRE Lab

[Python source](106/performance_lab.py) · [Automated tests](106/test_performance_lab.py) · [Project guide](106/README.md)

## Mission

A Python API and Kubernetes CronJob supporting PostgreSQL, Elasticsearch and MongoDB have developed high p99 latency and CPU pressure. Build a reproducible performance investigation using offline data, CPU/memory profilers, concurrency examples and SLO-based decision gates.

```text
Synthetic latency / CPU / memory incident signals
     -> validate data and percentiles
     -> cProfile/pstats + tracemalloc + microbenchmark
     -> compare slow vs optimized implementation
     -> inspect asyncio/thread I/O examples
     -> SLO assessment and operational runbook
     -> zero cloud/database writes
```

## Lab 1 — Execute

```bash
cd python/11-production-security-performance/labs/106
python -m compileall -q performance_lab.py test_performance_lab.py
python -m unittest -v test_performance_lab.py
python performance_lab.py --dry-run
python performance_lab.py --profile
```

## Lab 2 — CPU and memory

Run `cpu_profile(slow_count,...)` and `cpu_profile(fast_count,...)`; compare call counts and cumulative time. Explain asymptotic complexity, profiler overhead and why small synthetic benchmarks are not production performance evidence. Use `memory_profile` to observe Python traced allocations and discuss RSS, native allocations, cache pressure and Kubernetes OOM events.

## Lab 3 — Benchmarking and latency percentiles

Compute p50/p95/p99 with linear interpolation, validate missing/NaN/negative samples, run repeated `perf_counter_ns` benchmarks, and compare SLO budgets. Discuss coordinated omission, request weighting, fleet-level histogram aggregation, confidence intervals and warmup.

## Lab 4 — Concurrency and async

Run `async_batch` and `threaded_io` with bounded tasks. Explain event-loop blocking, cancellation, semaphore/backpressure, CPU-bound multiprocessing and Python GIL caveats. Design a safe asynchronous PostgreSQL query pool with explicit connection limits.

## Lab 5 — Production investigation design

Correlate application traces with PostgreSQL locks/query plans, Elasticsearch search rejections/oversized pagination, MongoDB cursor/index behavior and Kubernetes CPU throttling. Create canary release criteria for p95/p99, error rate, memory and downstream load.

## Production incident simulations

| # | Scenario | Expected outcome | Mode |
|---|---|---|---|
| 1 | p0/p100 boundary | Exact minimum/maximum | Automated |
| 2 | p50 median | Correct | Automated |
| 3 | p95 interpolation | Correct | Automated |
| 4 | p99 interpolation | Correct | Automated |
| 5 | Single sample | Correct | Automated |
| 6 | Unsorted samples | Sort before percentile | Automated |
| 7 | Empty samples | Reject | Automated |
| 8 | Negative/NaN/infinite latency | Reject | Automated |
| 9 | Invalid percentile | Reject | Automated |
| 10 | Mean and count | Correct | Automated |
| 11 | Passing SLO | Pass | Automated |
| 12 | Failing SLO | Fail | Automated |
| 13 | Invalid SLO limits | Reject | Automated |
| 14 | Slow vs fast result | Equal correctness | Automated |
| 15 | CPU profile call stats | Capture | Automated |
| 16 | Python allocation peak | Capture | Automated |
| 17 | Repeated benchmark | Summarize | Automated |
| 18 | Invalid benchmark count | Reject | Automated |
| 19 | Async I/O completion | Complete | Automated |
| 20 | Bounded async batch | Complete | Automated |
| 21 | Invalid async delay/batch | Reject | Automated |
| 22 | Threaded I/O completion | Complete | Automated |
| 23 | Invalid thread batch | Reject | Automated |
| 24 | 2x latency regression | Flag | Automated |
| 25 | CPU >=85% | Flag | Automated |
| 26 | Memory >=90% | Flag | Automated |
| 27 | Healthy synthetic incident | No pressure flag | Automated |
| 28 | Invalid incident baseline | Reject | Automated |
| 29 | CPU >100% or NaN | Reject | Automated |
| 30 | Dry-run profiler CLI | JSON report | Automated |
| 31 | PostgreSQL N+1 query | Inspect spans/EXPLAIN | Guided |
| 32 | Connection pool exhaustion | Bound concurrency | Guided |
| 33 | Elasticsearch large query size | Reduce page/fanout | Guided |
| 34 | Elasticsearch search threadpool rejections | Backoff and profile | Guided |
| 35 | MongoDB slow cursor | Inspect indexes/batch | Guided |
| 36 | Kubernetes CPU throttling | Inspect cgroup limits | Guided |
| 37 | Kubernetes OOMKilled | Compare RSS/tracemalloc | Guided |
| 38 | Async event-loop stall | Find blocking call | Guided |
| 39 | py-spy permission denied | Use approved staging sampling | Guided |
| 40 | Canary p99 regression | Halt and roll back | Guided |

## Troubleshooting and runbooks

**CPU saturation:** compare per-process and cgroup CPU, profiler hot functions, traffic mix, thread pools and throttling; test optimization on representative workload.

**Memory growth:** inspect RSS, Python heap snapshots, native buffers, caches and GC; preserve evidence and roll back leaks.

**Async stall:** identify blocking calls, event-loop delay, pool wait and cancellation; introduce bounded async concurrency.

**PostgreSQL latency:** inspect query plans, locks, storage IOPS, connection pool and application serialization before scaling.

**Elasticsearch search slowness:** inspect oversized `size`, shards, threadpool rejection, I/O saturation and retry storms.

**Tail-latency regression:** compare complete request distributions, errors, traffic and resource saturation; enforce canary rollback.

## Final 100-point assessment

| Competency | Points |
|---|---:|
| CPU/memory profiling and tool selection | 20 |
| Benchmarking and percentile/SLO correctness | 20 |
| Async/thread/process performance design | 20 |
| SRE/DBRE bottleneck diagnosis | 15 |
| Canary safety, incident response and runbooks | 15 |
| Automated tests and reproducible validation | 10 |
| **Total** | **100** |

**Pass:** ≥90 points, offline tests executed, baseline/optimized correctness preserved, explicit profiler limitations, and production change plan with SLO guardrails and rollback.

**Validation:** Offline test source published; execution of exact committed revision, CI, py-spy and production workload validation pending.
