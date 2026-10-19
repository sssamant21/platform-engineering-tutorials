# Chapter 107 — High-Performance Concurrency, Async and Parallel Processing Lab

[Python implementation](concurrency_lab.py) · [Automated tests](test_concurrency_lab.py) · [Full SRE/DBRE lab](../107-high-performance-concurrency-async-parallel-processing-sre-dbre-lab.md)

## Run offline

Python 3.11+ standard library only. No cloud SDK, database, network access, credentials or production writes.

```bash
cd python/11-production-security-performance/labs/107
python -m compileall -q concurrency_lab.py test_concurrency_lab.py
python -m unittest -v test_concurrency_lab.py
python concurrency_lab.py --dry-run
python concurrency_lab.py --process-demo
```

PowerShell: `py -3 -m unittest -v test_concurrency_lab.py`. The process-pool demo is explicitly opt-in because worker startup and process limits differ by OS.

## Implemented

- CPU work using serial, `ThreadPoolExecutor` and bounded `ProcessPoolExecutor`.
- Synthetic I/O using threads and `asyncio.gather` guarded by `asyncio.Semaphore`.
- Cancellation and timeout examples.
- Lock-protected shared counter.
- Bounded admission/backpressure calculations.
- Validated p50/p95/p99 latency interpolation and repeated microbenchmarks.
- Synthetic saturation, queue and error-budget incident analysis.
- **No cloud/database calls, real network I/O, production actions or measured speedup claims.**

## Exercises

1. Verify CPU results match across serial, thread and process modes.
2. Benchmark different worker counts without claiming general speedups.
3. Explain GIL versus free-threaded builds and C-extension safety.
4. Prove async peak inflight does not exceed semaphore limit.
5. Exercise cancellation and timeout cleanup.
6. Verify thread-safe counter under concurrent updates.
7. Model queue overflow and reject work beyond capacity.
8. Validate p95/p99 and sample integrity.
9. Diagnose synthetic PostgreSQL pool saturation.
10. Design bounded Elasticsearch search fanout.
11. Diagnose Kafka lag from CPU-bound processing.
12. Draft Kubernetes quota-aware worker and rollback policy.

## Production extension blueprint — NOT implemented

Use real OpenTelemetry spans and Prometheus metrics for queue wait, inflight tasks, worker restarts, CPU quota, RSS, event-loop lag, pool wait and request p99. Integrate bounded async drivers, circuit breakers, deadlines, idempotency and drain-on-shutdown. Validate actual workloads in staging with safe quotas and approval-gated rollout.

## CI template (not enabled)

```yaml
name: chapter-107-concurrency-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/11-production-security-performance/labs/107
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q concurrency_lab.py test_concurrency_lab.py
      - run: python -m unittest -v test_concurrency_lab.py
```

Pin reviewed action commit SHAs before enabling. **Validation:** Tests published; exact committed test execution, CI, production DB integrations and load/performance validation pending.
