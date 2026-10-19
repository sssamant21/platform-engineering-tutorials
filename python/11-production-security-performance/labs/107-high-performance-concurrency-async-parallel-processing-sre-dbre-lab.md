# Chapter 107 — High-Performance Concurrency, Async and Parallel Processing SRE/DBRE Lab

[Python engine](107/concurrency_lab.py) · [Automated tests](107/test_concurrency_lab.py) · [Project README](107/README.md)

## Mission

A Kubernetes Python API fans out to PostgreSQL, Elasticsearch and MongoDB while a Kafka consumer performs CPU-intensive transforms. The platform sees pool exhaustion, event-loop stalls, queue growth and p99 regression. Design bounded concurrency, correct cancellation and reliable SRE incident recovery.

```text
Synthetic requests -> bounded admission -> thread/async/process work
       -> concurrency and queue budgets
       -> cancellation, timeout and lock correctness
       -> benchmark + p95/p99 + incident classification
       -> advisory recovery plan / zero production writes
```

## Lab 1 — Execute

```bash
cd python/11-production-security-performance/labs/107
python -m compileall -q concurrency_lab.py test_concurrency_lab.py
python -m unittest -v test_concurrency_lab.py
python concurrency_lab.py --dry-run
python concurrency_lab.py --process-demo
```

## Lab 2 — Threads and process pools

Compare `serial_cpu`, `threaded_cpu` and `process_cpu` on the same deterministic inputs. Validate output equality, bounded workers and top-level picklable functions. Explain the traditional GIL, free-threaded builds, process startup/IPC overhead and Kubernetes CPU quotas. Do not infer performance improvements from tiny workloads.

## Lab 3 — Async and cancellation

Run `bounded_async` with different semaphore limits; confirm peak inflight never exceeds the limit. Exercise `cancel_example` and `timeout_example`, then design production cleanup using `finally`, bounded deadlines, cancellation propagation and idempotent remote operations.

## Lab 4 — Synchronization and backpressure

Use `SafeCounter` to avoid shared-state races. Calculate accepted/rejected requests using bounded queue capacity; explain actual `asyncio.Queue(maxsize=N)` and `queue.Queue(maxsize=N)` designs, producer blocking, graceful draining and overload responses.

## Lab 5 — Benchmark and production incident

Measure serial/thread/process approaches using `perf_counter_ns` and compare latency percentiles; record workload size, warmup and quota. Diagnose synthetic PostgreSQL connection-pool saturation and map real telemetry: `pg_stat_activity`, Elasticsearch threadpool rejections, MongoDB pool wait, Kafka lag and Kubernetes throttling.

## Production incident simulations

| # | Scenario | Expected outcome | Mode |
|---|---|---|---|
| 1 | Valid concurrency limit | Accept | Automated |
| 2 | Boolean/zero/oversized worker limit | Reject | Automated |
| 3 | CPU task expected sum | Correct | Automated |
| 4 | Negative CPU work | Reject | Automated |
| 5 | Thread CPU result | Match serial | Automated |
| 6 | Process CPU result | Match serial | Automated |
| 7 | Process worker budget exceeded | Reject | Automated |
| 8 | Threaded synthetic I/O | Ordered output | Automated |
| 9 | Invalid I/O item | Reject | Automated |
| 10 | Async I/O results | Ordered output | Automated |
| 11 | Async semaphore limit | Never exceeded | Automated |
| 12 | Invalid async item/limit | Reject | Automated |
| 13 | Cancellation | Cancelled | Automated |
| 14 | Timeout | Timed out | Automated |
| 15 | Invalid timeout | Reject | Automated |
| 16 | Thread-safe counter | Correct total | Automated |
| 17 | Invalid counter increment | Reject | Automated |
| 18 | Queue overload | Reject excess | Automated |
| 19 | Queue below capacity | No rejection | Automated |
| 20 | Invalid arrival count | Reject | Automated |
| 21 | p50/p95/p99 | Correct | Automated |
| 22 | Empty/NaN/invalid percentile | Reject | Automated |
| 23 | Repeated benchmark | Summarize | Automated |
| 24 | Invalid benchmark iterations | Reject | Automated |
| 25 | Pool saturation | Flag | Automated |
| 26 | Queue growth | Flag | Automated |
| 27 | Error rate ≥5% | Flag | Automated |
| 28 | Invalid incident metrics | Reject | Automated |
| 29 | Offline CLI | JSON report | Automated |
| 30 | Zero network/mutations | Preserve | Automated |
| 31 | PostgreSQL connection pool exhaustion | Bound per-replica pools | Guided |
| 32 | Elasticsearch threadpool rejections | Limit fanout/retries | Guided |
| 33 | MongoDB pool wait | Inspect blocking driver | Guided |
| 34 | Kafka consumer lag | Separate CPU work | Guided |
| 35 | Kubernetes CPU throttling | Right-size workers | Guided |
| 36 | Async event-loop stall | Remove blocking call | Guided |
| 37 | Lock-order deadlock | Capture stacks/reproduce | Guided |
| 38 | Process worker crash | Recover idempotently | Guided |
| 39 | Cancellation during DB write | Check remote outcome | Guided |
| 40 | p99 regression after scaling | Halt and roll back | Guided |

## Troubleshooting and runbooks

**Pool exhaustion:** measure per-replica pool caps, backend max connections, leaked sessions, queue wait and retries; throttle ingress and adjust safely.

**Event-loop blocking:** inspect slow tasks, synchronous I/O, event-loop lag and stack traces; offload with bounded workers.

**Deadlock:** capture thread stacks, inspect lock order and shared-state contention, stop admissions and restart safely.

**Process crash:** inspect exit codes, OOM, serialization/pickling and resource quotas; replay idempotent work.

**Queue overload:** apply admission control, shed load, cap retries and drain with deadlines.

**Kafka lag:** correlate processing latency, partition ordering, heartbeat timeouts and offset commit correctness.

**SLO regression:** compare p95/p99, errors, throughput and resource pressure; roll back when budget breached.

## Final 100-point assessment

| Competency | Points |
|---|---:|
| GIL, free-threaded and execution model selection | 20 |
| Threads/processes/async correctness | 20 |
| Synchronization, cancellation and timeouts | 20 |
| Backpressure, resource limits and observability | 15 |
| Production SRE/DBRE incidents and runbooks | 15 |
| Automated tests and reproducible benchmarks | 10 |
| **Total** | **100** |

**Pass:** ≥90 points, offline tests executed, bounded resource and cancellation proof, no-write evidence and reviewed production rollout/rollback.

**Validation:** Offline test code published; exact committed runtime execution, CI, real integrations and production load acceptance pending.
