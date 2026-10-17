# Chapter 056 — Multiprocessing and Process Pools SRE/DBRE Lab

**Python 3.10+ | Standard library | Offline and read-only**

## Project layout
```text
ch056/
  process_ops.py
  test_process_ops.py
```

## 1. process_ops.py
```python
"""Chapter 056 — bounded offline process-pool telemetry computation."""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from multiprocessing import get_context, get_all_start_methods
import argparse
import hashlib
import json
import math
import os
import re
import sys
import time

MAX_JOBS = 32
MAX_WORKERS = 4
MAX_ITERATIONS = 200000
POLICY = {
    "postgresql": ("replication_lag", "seconds", 30, 120),
    "elasticsearch": ("search_latency", "milliseconds", 200, 500),
    "kafka": ("consumer_lag", "messages", 1000, 10000),
}

class PipelineError(ValueError):
    pass

@dataclass(frozen=True)
class Job:
    service: str
    engine: str
    metric: str
    unit: str
    value: float
    iterations: int = 10000

@dataclass(frozen=True)
class JobResult:
    service: str
    engine: str
    severity: str
    checksum: str
    worker_pid: int

def validate_job(raw: dict[str, object]) -> Job:
    if not isinstance(raw, dict) or set(raw) != {
        "service", "engine", "metric", "unit", "value", "iterations"
    }:
        raise PipelineError("invalid job schema")
    service = raw["service"]
    engine = raw["engine"]
    if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise PipelineError("invalid service")
    if not isinstance(engine, str) or engine not in POLICY:
        raise PipelineError("invalid engine")
    metric, unit, _, _ = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise PipelineError("metric/unit mismatch")
    value = raw["value"]
    if type(value) not in (int, float):
        raise PipelineError("metric must be a number, not boolean")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise PipelineError("invalid numeric value") from exc
    if not math.isfinite(number) or number < 0:
        raise PipelineError("metric must be finite and nonnegative")
    iterations = raw["iterations"]
    if type(iterations) is not int or not 1 <= iterations <= MAX_ITERATIONS:
        raise PipelineError("iterations outside 1..200000")
    return Job(service, engine, metric, unit, number, iterations)

def compute(job: Job) -> JobResult:
    """Top-level pickleable worker. No network, filesystem or database mutation."""
    metric, unit, warning, critical = POLICY[job.engine]
    if job.metric != metric or job.unit != unit:
        raise PipelineError("worker metric/unit mismatch")
    if not math.isfinite(job.value) or job.value < 0:
        raise PipelineError("worker invalid value")
    if type(job.iterations) is not int or not 1 <= job.iterations <= MAX_ITERATIONS:
        raise PipelineError("worker invalid iteration budget")
    severity = "critical" if job.value >= critical else "warning" if job.value >= warning else "healthy"
    seed = f"{job.engine}:{job.service}:{job.value:.6f}".encode("ascii")
    digest = hashlib.sha256(seed).digest()
    for _ in range(job.iterations):
        digest = hashlib.sha256(digest).digest()
    return JobResult(job.service, job.engine, severity, digest.hex(), os.getpid())

def fixture_jobs(iterations: int = 10000) -> list[Job]:
    return [
        Job("pg-replica", "postgresql", "replication_lag", "seconds", 45, iterations),
        Job("es-search", "elasticsearch", "search_latency", "milliseconds", 650, iterations),
        Job("kafka-worker", "kafka", "consumer_lag", "messages", 10000, iterations),
    ]

def aggregate(results: list[JobResult]) -> dict[str, object]:
    counts = {"healthy": 0, "warning": 0, "critical": 0}
    for item in results:
        if item.severity not in counts:
            raise PipelineError("unexpected severity")
        counts[item.severity] += 1
    return {
        "schema_version": 1, "dry_run": True, "total": len(results),
        "counts": counts,
        "results": [
            {"service": item.service, "engine": item.engine,
             "severity": item.severity, "checksum": item.checksum}
            for item in sorted(results, key=lambda x: (x.engine, x.service))
        ],
    }

def run(jobs: list[Job], *, workers: int = 2, timeout: float = 15.0,
        start_method: str = "spawn") -> dict[str, object]:
    if type(workers) is not int or not 1 <= workers <= MAX_WORKERS:
        raise PipelineError("workers must be 1..4")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 120:
        raise PipelineError("timeout must be finite in (0,120]")
    if start_method not in ("spawn", "forkserver"):
        raise PipelineError("start method must be spawn or forkserver")
    if start_method not in get_all_start_methods():
        raise PipelineError("start method unsupported on this platform")
    if len(jobs) > MAX_JOBS:
        raise PipelineError("too many jobs")
    if len({(job.engine, job.service) for job in jobs}) != len(jobs):
        raise PipelineError("duplicate job")
    if not jobs:
        return aggregate([])
    deadline = time.monotonic() + timeout
    # Use a documented explicit context; spawn works on Windows and POSIX.
    with ProcessPoolExecutor(max_workers=workers, mp_context=get_context(start_method)) as pool:
        futures = [pool.submit(compute, job) for job in jobs]
        results = []
        try:
            for future in futures:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise PipelineError("batch deadline exceeded")
                try:
                    results.append(future.result(timeout=remaining))
                except FutureTimeout as exc:
                    raise PipelineError("batch deadline exceeded") from exc
        except Exception:
            for future in futures:
                future.cancel()
            # Executor context still waits for running work; this is NOT a hard
            # process execution timeout. Production needs kill/terminate policy.
            raise
    return aggregate(results)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline CPU-bound process-pool SRE/DBRE lab")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--start-method", choices=("spawn", "forkserver"), default="spawn")
    args = parser.parse_args(argv)
    try:
        jobs = fixture_jobs(args.iterations)
        if type(args.iterations) is not int or not 1 <= args.iterations <= MAX_ITERATIONS:
            raise PipelineError("invalid iteration budget")
        report = run(jobs, workers=args.workers, timeout=args.timeout,
                     start_method=args.start_method)
    except (PipelineError, OSError, RuntimeError):
        print("processing failed: sanitized operational error", file=sys.stderr)
        return 3
    print(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. test_process_ops.py
```python
"""Chapter 056 unit tests: deterministic worker tests plus small real spawn-pool smoke test."""
import json
import math
import os
import unittest
from multiprocessing import get_all_start_methods
from concurrent.futures import ProcessPoolExecutor
from process_ops import (
    Job, JobResult, PipelineError, validate_job, compute, fixture_jobs,
    aggregate, run, main,
)

PG={"service":"pg-replica","engine":"postgresql","metric":"replication_lag",
    "unit":"seconds","value":45,"iterations":5}

class ProcessTests(unittest.TestCase):
    def bad(self, **kwargs):
        with self.assertRaises(PipelineError): validate_job({**PG, **kwargs})
    def test_valid(self): self.assertEqual(validate_job(PG).engine,"postgresql")
    def test_bad_engine(self): self.bad(engine="mysql")
    def test_bad_metric(self): self.bad(metric="latency")
    def test_bad_unit(self): self.bad(unit="milliseconds")
    def test_bad_service(self): self.bad(service="=cmd")
    def test_bad_unicode(self): self.bad(service="東京")
    def test_bad_bool(self): self.bad(value=True)
    def test_bad_string(self): self.bad(value="45")
    def test_bad_nan(self): self.bad(value=float("nan"))
    def test_bad_inf(self): self.bad(value=float("inf"))
    def test_bad_negative(self): self.bad(value=-1)
    def test_bad_zero_iterations(self): self.bad(iterations=0)
    def test_bad_large_iterations(self): self.bad(iterations=200001)
    def test_bad_bool_iterations(self): self.bad(iterations=True)
    def test_bad_extra(self): self.bad(secret="x")
    def test_bad_missing(self):
        raw=dict(PG); del raw["unit"]
        with self.assertRaises(PipelineError): validate_job(raw)
    def test_compute_warning(self):
        self.assertEqual(compute(validate_job(PG)).severity,"warning")
    def test_compute_critical(self):
        self.assertEqual(compute(fixture_jobs(1)[1]).severity,"critical")
    def test_compute_kafka(self):
        self.assertEqual(compute(fixture_jobs(1)[2]).severity,"critical")
    def test_compute_healthy(self):
        self.assertEqual(compute(Job("pg","postgresql","replication_lag","seconds",1,1)).severity,"healthy")
    def test_compute_digest_length(self):
        self.assertEqual(len(compute(validate_job(PG)).checksum),64)
    def test_compute_deterministic(self):
        job=validate_job(PG)
        self.assertEqual(compute(job).checksum,compute(job).checksum)
    def test_compute_worker_pid(self):
        self.assertEqual(compute(validate_job(PG)).worker_pid,os.getpid())
    def test_compute_worker_bad_unit(self):
        with self.assertRaises(PipelineError):
            compute(Job("pg","postgresql","replication_lag","ms",1,1))
    def test_compute_worker_bad_value(self):
        with self.assertRaises(PipelineError):
            compute(Job("pg","postgresql","replication_lag","seconds",float("nan"),1))
    def test_compute_worker_bad_budget(self):
        with self.assertRaises(PipelineError):
            compute(Job("pg","postgresql","replication_lag","seconds",1,0))
    def test_fixture_three(self): self.assertEqual(len(fixture_jobs(1)),3)
    def test_aggregate_empty(self): self.assertEqual(aggregate([])["total"],0)
    def test_aggregate_counts(self):
        r=[compute(job) for job in fixture_jobs(1)]
        self.assertEqual(aggregate(r)["counts"],{"healthy":0,"warning":1,"critical":2})
    def test_aggregate_dry_run(self): self.assertTrue(aggregate([])["dry_run"])
    def test_aggregate_sorted(self):
        r=[JobResult("z","postgresql","warning","a",1),JobResult("a","postgresql","healthy","b",2)]
        self.assertEqual(aggregate(r)["results"][0]["service"],"a")
    def test_aggregate_no_pid(self):
        self.assertNotIn("worker_pid",json.dumps(aggregate([compute(validate_job(PG))])))
    def test_aggregate_invalid(self):
        with self.assertRaises(PipelineError):
            aggregate([JobResult("x","postgresql","unknown","a",1)])
    def test_run_empty(self): self.assertEqual(run([])["total"],0)
    def test_run_workers_zero(self):
        with self.assertRaises(PipelineError): run([],workers=0)
    def test_run_workers_five(self):
        with self.assertRaises(PipelineError): run([],workers=5)
    def test_run_workers_bool(self):
        with self.assertRaises(PipelineError): run([],workers=True)
    def test_run_timeout_zero(self):
        with self.assertRaises(PipelineError): run([],timeout=0)
    def test_run_timeout_nan(self):
        with self.assertRaises(PipelineError): run([],timeout=float("nan"))
    def test_run_timeout_bool(self):
        with self.assertRaises(PipelineError): run([],timeout=True)
    def test_run_timeout_large(self):
        with self.assertRaises(PipelineError): run([],timeout=121)
    def test_run_invalid_method(self):
        with self.assertRaises(PipelineError): run([],start_method="fork")
    def test_run_duplicate(self):
        job=fixture_jobs(1)[0]
        with self.assertRaises(PipelineError): run([job,job])
    def test_run_too_many(self):
        jobs=[Job(f"pg{i}","postgresql","replication_lag","seconds",1,1) for i in range(33)]
        with self.assertRaises(PipelineError): run(jobs)
    def test_run_spawn(self):
        if "spawn" not in get_all_start_methods(): self.skipTest("spawn unsupported")
        result=run(fixture_jobs(10),workers=2,timeout=20)
        self.assertEqual(result["counts"],{"healthy":0,"warning":1,"critical":2})
    def test_run_checksum_matches_direct(self):
        if "spawn" not in get_all_start_methods(): self.skipTest("spawn unsupported")
        jobs=fixture_jobs(10)
        result=run(jobs,workers=2,timeout=20)
        direct=aggregate([compute(job) for job in jobs])
        self.assertEqual(result["results"],direct["results"])
    def test_run_no_secret(self):
        self.assertNotIn("password",json.dumps(aggregate([compute(validate_job(PG))])))
    def test_main_invalid(self): self.assertEqual(main(["--iterations","0"]),3)

if __name__=="__main__":
    unittest.main()

```

## 3. Run the lab
Linux/macOS/WSL:
```bash
python3 -m py_compile process_ops.py test_process_ops.py
python3 -m unittest -v test_process_ops.py
python3 process_ops.py --workers 2 --iterations 10000 --timeout 15
```

Windows PowerShell:
```powershell
py -3 -m py_compile process_ops.py test_process_ops.py
py -3 -m unittest -v test_process_ops.py
py -3 process_ops.py --workers 2 --iterations 10000 --timeout 15
```

Run from actual Python files, not a notebook cell. Expected report: 3 events, 1 warning, 2 critical; deterministic checksums across runs. Worker PIDs are deliberately omitted from output. Exit 0 means successful offline processing, not healthy infrastructure.

## 4. Incident simulations
1. Execute the spawn-pool smoke test on your platform.
2. Compare checksums computed directly versus through the pool.
3. Increase iterations and measure CPU utilization and wall time.
4. Reduce timeout to a very small value and observe that `Future.result` timeout does not kill workers.
5. Inject a worker exception with an invalid metric or unit.
6. Try a nested function as a worker to reproduce pickling errors in a separate training script.
7. Omit the main guard in a disposable training script and inspect spawn startup failure.
8. Exceed the four-worker or 32-job safety budget.
9. Inject NaN, Infinity, boolean or negative values.
10. Submit duplicate jobs and verify rejection.
11. Compare spawn and forkserver where supported.
12. Run under a container CPU quota and record throughput and memory.

## 5. Troubleshooting and runbooks
**Broken pool:** inspect worker crashes, cgroup memory limits and imports; rebuild a fresh pool rather than reusing broken state.

**Timeout:** distinguish batch wait deadline from hard process execution deadline; terminate through a supervised boundary when required.

**Serialization:** pass only validated, picklable DTOs; never deserialize untrusted pickle payloads.

**Resource pressure:** lower workers and iteration budgets, measure per-worker RSS, and rerun controlled benchmarks.

**Rollback:** restore last known-good worker configuration and compare deterministic results before resuming automation.

## 6. 100-point assessment
| Area | Points |
|---|---:|
| Syntax and automated tests | 25 |
| Multiprocessing architecture and spawn safety | 20 |
| Serialization and worker isolation | 20 |
| Bounded tasks, deadlines and failures | 15 |
| Incident simulations | 10 |
| Production runbooks and rollback | 10 |

Target **90/100** and all safety checks passing. Source and tests are published; execution has not been independently verified.
