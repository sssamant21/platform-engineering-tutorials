# Chapter 106 — Application Performance Profiling and Optimization Executable Lab

[Python profiler/benchmark](performance_lab.py) · [Automated tests](test_performance_lab.py) · [Full SRE/DBRE lab](../106-application-performance-profiling-optimization-sre-dbre-lab.md)

## Run locally

Python 3.11+ standard library only. No external packages, cloud credentials, database connections, network calls or production mutations.

```bash
cd python/11-production-security-performance/labs/106
python -m compileall -q performance_lab.py test_performance_lab.py
python -m unittest -v test_performance_lab.py
python performance_lab.py --dry-run
python performance_lab.py --profile
```

PowerShell: `py -3 -m unittest -v test_performance_lab.py`.

## Implemented

- Validated latency samples and deterministic interpolated p50/p95/p99.
- Simple p95/p99 latency budget checks.
- Intentionally inefficient counting versus dictionary-based counting.
- CPU `cProfile`/`pstats` and Python-allocation `tracemalloc` instrumentation.
- `perf_counter_ns` illustrative repeated microbenchmark.
- `asyncio.gather` and bounded `ThreadPoolExecutor` I/O-style examples.
- Synthetic SRE incident evaluation for latency regression, CPU and memory pressure.
- Zero network calls and zero production mutations.

## Exercises

1. Validate percentile interpolation and reject invalid samples.
2. Compare p50, p95 and p99 for synthetic outliers.
3. Trigger SLO budget failures and explain error-budget impact.
4. Profile `slow_count` versus `fast_count` with `cProfile`.
5. Explain cumulative versus self time and profiler overhead.
6. Observe `tracemalloc` traced peak and contrast with process RSS.
7. Benchmark repeated runs; discuss warmup and variance.
8. Compare threading and asyncio for I/O, not CPU parallelism.
9. Diagnose synthetic CPU/memory/latency incident signals.
10. Design `py-spy` read-only sampling for an approved staging process.
11. Correlate PostgreSQL/Elasticsearch query latency with Python traces.
12. Write canary, SLO and rollback acceptance criteria.

## Optional tools (not installed or executed)

```bash
python -m pip install py-spy pyperf
py-spy top --pid <PID>
py-spy record --pid <PID> -o profile.svg
```

Use approved permissions and isolated staging workloads. Avoid profiling arbitrary production processes or changing security privileges without review.

## CI template (not enabled)

```yaml
name: chapter-106-performance-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/11-production-security-performance/labs/106
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q performance_lab.py test_performance_lab.py
      - run: python -m unittest -v test_performance_lab.py
```

Pin reviewed action commit SHAs before enabling. **Validation:** Test source is published; execution of exact committed revision, CI, py-spy, live DB/cloud profiling and production load testing remain pending.
