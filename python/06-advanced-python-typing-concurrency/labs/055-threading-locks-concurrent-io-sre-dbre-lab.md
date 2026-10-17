# Chapter 055 — Threading, Locks and Concurrent I/O SRE/DBRE Lab

**Python 3.10+ | Standard library | Offline and read-only**

## Project layout
```text
ch055/
  concurrent_ops.py
  test_concurrent_ops.py
```

## 1. concurrent_ops.py
```python
"""Chapter 055: bounded, offline, concurrent SRE/DBRE telemetry polling."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from threading import Lock, Event as StopEvent
from typing import Callable
import argparse
import json
import math
import re
import sys
import time

POLICY = {
    "postgresql": ("replication_lag", "seconds", 30.0, 120.0),
    "elasticsearch": ("search_latency", "milliseconds", 200.0, 500.0),
    "kafka": ("consumer_lag", "messages", 1000.0, 10000.0),
}
MAX_WORKERS = 8
MAX_TASKS = 100

class PollError(ValueError):
    pass

@dataclass(frozen=True)
class Target:
    service: str
    engine: str
    metric: str
    unit: str
    value: float
    simulated_delay: float = 0.0

@dataclass(frozen=True)
class Result:
    service: str
    engine: str
    severity: str
    value: float

@dataclass
class SafeCounters:
    _lock: Lock = field(default_factory=Lock)
    started: int = 0
    completed: int = 0
    failed: int = 0

    def mark_started(self) -> None:
        with self._lock:
            self.started += 1

    def mark_completed(self) -> None:
        with self._lock:
            self.completed += 1

    def mark_failed(self) -> None:
        with self._lock:
            self.failed += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {"started": self.started, "completed": self.completed, "failed": self.failed}

def validate_target(raw: dict[str, object]) -> Target:
    if set(raw) not in (
        {"service", "engine", "metric", "unit", "value"},
        {"service", "engine", "metric", "unit", "value", "simulated_delay"},
    ):
        raise PollError("invalid target fields")
    service, engine = raw["service"], raw["engine"]
    if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise PollError("invalid service")
    if not isinstance(engine, str) or engine not in POLICY:
        raise PollError("invalid engine")
    metric, unit, _, _ = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise PollError("metric/unit mismatch")
    value = raw["value"]
    delay = raw.get("simulated_delay", 0.0)
    if type(value) not in (int, float) or type(delay) not in (int, float):
        raise PollError("numeric fields must not be booleans")
    try:
        number, pause = float(value), float(delay)
    except (OverflowError, ValueError) as exc:
        raise PollError("invalid numeric fields") from exc
    if not math.isfinite(number) or number < 0:
        raise PollError("invalid metric value")
    if not math.isfinite(pause) or not 0 <= pause <= 0.05:
        raise PollError("invalid simulated delay")
    return Target(service, engine, metric, unit, number, pause)

def poll(target: Target, stop: StopEvent, counters: SafeCounters,
         sleeper: Callable[[float], None] = time.sleep) -> Result:
    counters.mark_started()
    try:
        if stop.is_set():
            raise PollError("cancelled")
        if target.simulated_delay:
            sleeper(target.simulated_delay)
        if stop.is_set():
            raise PollError("cancelled")
        _, _, warning, critical = POLICY[target.engine]
        severity = ("critical" if target.value >= critical else
                    "warning" if target.value >= warning else "healthy")
        result = Result(target.service, target.engine, severity, target.value)
        counters.mark_completed()
        return result
    except Exception:
        counters.mark_failed()
        raise

def aggregate(results: list[Result], counters: SafeCounters) -> dict[str, object]:
    counts = {"healthy": 0, "warning": 0, "critical": 0}
    for result in results:
        counts[result.severity] += 1
    return {
        "schema_version": 1, "dry_run": True, "total": len(results),
        "counts": counts, "counters": counters.snapshot(),
        "results": [
            {"service": r.service, "engine": r.engine,
             "severity": r.severity, "value": r.value}
            for r in sorted(results, key=lambda r: (r.engine, r.service))
        ],
    }

def run(targets: list[Target], *, workers: int = 3,
        timeout: float = 1.0,
        sleeper: Callable[[float], None] = time.sleep) -> dict[str, object]:
    if type(workers) is not int or not 1 <= workers <= MAX_WORKERS:
        raise PollError("workers must be 1..8")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise PollError("timeout must be finite in (0,30]")
    if len(targets) > MAX_TASKS:
        raise PollError("too many targets")
    if len({(t.engine, t.service) for t in targets}) != len(targets):
        raise PollError("duplicate target")
    counters = SafeCounters()
    stop = StopEvent()
    futures: list[Future[Result]] = []
    results: list[Result] = []
    # The timeout below is a whole-batch deadline, not a per-task deadline.
    deadline = time.monotonic() + timeout
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ch055") as pool:
        for target in targets:
            futures.append(pool.submit(poll, target, stop, counters, sleeper))
        try:
            for future in futures:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise PollError("batch deadline exceeded")
                try:
                    results.append(future.result(timeout=remaining))
                except FutureTimeout as exc:
                    raise PollError("batch deadline exceeded") from exc
        except Exception:
            stop.set()
            for future in futures:
                future.cancel()
            # Context manager waits for running tasks to finish. Threads cannot
            # be forcibly killed; production I/O adapters need their own timeouts.
            raise
    return aggregate(results, counters)

def fixtures() -> list[Target]:
    return [
        Target("pg-replica", "postgresql", "replication_lag", "seconds", 45),
        Target("es-search", "elasticsearch", "search_latency", "milliseconds", 650),
        Target("kafka-worker", "kafka", "consumer_lag", "messages", 10000),
    ]

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline concurrent telemetry polling lab")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args(argv)
    try:
        report = run(fixtures(), workers=args.workers, timeout=args.timeout)
    except (PollError, OSError):
        print("poll failed: sanitized operational error", file=sys.stderr)
        return 3
    print(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. test_concurrent_ops.py
```python
import json
import math
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
from concurrent_ops import (
    Target, Result, PollError, SafeCounters, validate_target,
    poll, aggregate, run, fixtures, main,
)

PG = {"service":"pg-replica","engine":"postgresql",
      "metric":"replication_lag","unit":"seconds","value":45}

class ConcurrentTests(unittest.TestCase):
    def bad(self, **kwargs):
        with self.assertRaises(PollError): validate_target({**PG, **kwargs})
    def test_validate(self): self.assertEqual(validate_target(PG).engine,"postgresql")
    def test_validate_delay(self): self.assertEqual(validate_target({**PG,"simulated_delay":0.01}).simulated_delay,0.01)
    def test_bad_engine(self): self.bad(engine="mysql")
    def test_bad_metric(self): self.bad(metric="latency")
    def test_bad_unit(self): self.bad(unit="ms")
    def test_bad_service(self): self.bad(service="=cmd")
    def test_bad_service_unicode(self): self.bad(service="東京")
    def test_bad_bool_value(self): self.bad(value=True)
    def test_bad_bool_delay(self): self.bad(simulated_delay=True)
    def test_bad_string_value(self): self.bad(value="45")
    def test_bad_nan(self): self.bad(value=float("nan"))
    def test_bad_inf(self): self.bad(value=float("inf"))
    def test_bad_negative(self): self.bad(value=-1)
    def test_bad_delay_negative(self): self.bad(simulated_delay=-0.1)
    def test_bad_delay_large(self): self.bad(simulated_delay=1)
    def test_bad_extra(self): self.bad(password="secret")
    def test_missing(self):
        with self.assertRaises(PollError): validate_target({"service":"pg"})
    def test_counters_initial(self):
        self.assertEqual(SafeCounters().snapshot(),{"started":0,"completed":0,"failed":0})
    def test_counters_increment(self):
        c=SafeCounters()
        c.mark_started(); c.mark_completed(); c.mark_failed()
        self.assertEqual(c.snapshot(),{"started":1,"completed":1,"failed":1})
    def test_counters_concurrent(self):
        c=SafeCounters()
        def update(_):
            c.mark_started(); c.mark_completed()
        with ThreadPoolExecutor(max_workers=8) as pool: list(pool.map(update, range(1000)))
        self.assertEqual(c.snapshot(),{"started":1000,"completed":1000,"failed":0})
    def test_poll_pg_warning(self):
        self.assertEqual(poll(fixtures()[0],threading.Event(),SafeCounters()).severity,"warning")
    def test_poll_es_critical(self):
        self.assertEqual(poll(fixtures()[1],threading.Event(),SafeCounters()).severity,"critical")
    def test_poll_kafka_critical(self):
        self.assertEqual(poll(fixtures()[2],threading.Event(),SafeCounters()).severity,"critical")
    def test_poll_healthy(self):
        t=Target("pg","postgresql","replication_lag","seconds",0)
        self.assertEqual(poll(t,threading.Event(),SafeCounters()).severity,"healthy")
    def test_poll_cancelled(self):
        stop=threading.Event(); stop.set()
        c=SafeCounters()
        with self.assertRaises(PollError): poll(fixtures()[0],stop,c)
        self.assertEqual(c.snapshot()["failed"],1)
    def test_poll_delay(self):
        sleeper=Mock()
        t=Target("pg","postgresql","replication_lag","seconds",0,0.01)
        poll(t,threading.Event(),SafeCounters(),sleeper)
        sleeper.assert_called_once_with(0.01)
    def test_poll_sleep_failure(self):
        def sleeper(_): raise RuntimeError("synthetic")
        c=SafeCounters()
        with self.assertRaises(RuntimeError):
            poll(Target("pg","postgresql","replication_lag","seconds",0,0.01),
                 threading.Event(),c,sleeper)
        self.assertEqual(c.snapshot()["failed"],1)
    def test_poll_counter_completed(self):
        c=SafeCounters(); poll(fixtures()[0],threading.Event(),c)
        self.assertEqual(c.snapshot()["completed"],1)
    def test_aggregate_empty(self):
        self.assertEqual(aggregate([],SafeCounters())["total"],0)
    def test_aggregate_counts(self):
        r=[Result("pg","postgresql","warning",45),Result("es","elasticsearch","critical",650)]
        self.assertEqual(aggregate(r,SafeCounters())["counts"]["critical"],1)
    def test_aggregate_sorted(self):
        r=[Result("z","postgresql","warning",45),Result("a","postgresql","healthy",0)]
        self.assertEqual(aggregate(r,SafeCounters())["results"][0]["service"],"a")
    def test_aggregate_dry_run(self):
        self.assertTrue(aggregate([],SafeCounters())["dry_run"])
    def test_run(self): self.assertEqual(run(fixtures())["total"],3)
    def test_run_counts(self):
        self.assertEqual(run(fixtures())["counts"],{"healthy":0,"warning":1,"critical":2})
    def test_run_counters(self):
        self.assertEqual(run(fixtures())["counters"],{"started":3,"completed":3,"failed":0})
    def test_run_empty(self): self.assertEqual(run([])["total"],0)
    def test_run_one_worker(self): self.assertEqual(run(fixtures(),workers=1)["total"],3)
    def test_run_eight_workers(self): self.assertEqual(run(fixtures(),workers=8)["total"],3)
    def test_run_workers_zero(self):
        with self.assertRaises(PollError): run(fixtures(),workers=0)
    def test_run_workers_nine(self):
        with self.assertRaises(PollError): run(fixtures(),workers=9)
    def test_run_workers_bool(self):
        with self.assertRaises(PollError): run(fixtures(),workers=True)
    def test_run_timeout_zero(self):
        with self.assertRaises(PollError): run(fixtures(),timeout=0)
    def test_run_timeout_nan(self):
        with self.assertRaises(PollError): run(fixtures(),timeout=float("nan"))
    def test_run_timeout_bool(self):
        with self.assertRaises(PollError): run(fixtures(),timeout=True)
    def test_run_timeout_large(self):
        with self.assertRaises(PollError): run(fixtures(),timeout=31)
    def test_run_duplicate(self):
        with self.assertRaises(PollError): run([fixtures()[0],fixtures()[0]])
    def test_run_too_many(self):
        targets=[Target(f"pg{i}","postgresql","replication_lag","seconds",1) for i in range(101)]
        with self.assertRaises(PollError): run(targets)
    def test_run_failure_propagates(self):
        def sleeper(_): raise RuntimeError("synthetic")
        target=Target("pg","postgresql","replication_lag","seconds",1,0.01)
        with self.assertRaises(RuntimeError): run([target],sleeper=sleeper)
    def test_run_deadline(self):
        def sleeper(_): time.sleep(0.02)
        target=Target("pg","postgresql","replication_lag","seconds",1,0.01)
        with self.assertRaises(PollError): run([target],timeout=0.001,sleeper=sleeper)
    def test_run_deterministic(self):
        self.assertEqual(run(fixtures())["results"],run(fixtures())["results"])
    def test_run_no_secrets(self):
        self.assertNotIn("password",json.dumps(run(fixtures())))
    def test_main(self): self.assertEqual(main([]),0)
    def test_main_invalid(self): self.assertEqual(main(["--workers","0"]),3)

if __name__=="__main__": unittest.main()

```

## 3. Execute
Linux/macOS/WSL:
```bash
python3 -m py_compile concurrent_ops.py test_concurrent_ops.py
python3 -m unittest -v test_concurrent_ops.py
python3 concurrent_ops.py --workers 3 --timeout 1
```

Windows PowerShell:
```powershell
py -3 -m py_compile concurrent_ops.py test_concurrent_ops.py
py -3 -m unittest -v test_concurrent_ops.py
py -3 concurrent_ops.py --workers 3 --timeout 1
```

Expected synthetic report: 3 total events, 1 warning, 2 critical, counters started=3, completed=3, failed=0. A successful command does not mean any real datastore is healthy.

## 4. Failure injection and incident simulations
1. Run 1,000 counter updates across eight threads; verify exact counts.
2. Remove a training-only lock and inspect potential lost updates; races are timing-dependent and may not reproduce every run.
3. Inject a transient sleeper failure and verify worker exceptions propagate through futures.
4. Simulate a deadline shorter than worker sleep and verify the batch fails closed.
5. Trigger cancellation before worker start.
6. Submit duplicate targets and verify rejection.
7. Exceed worker and task limits.
8. Inject NaN, Infinity, booleans, negative values and wrong metric units.
9. Compare output with 1, 3 and 8 workers; sorted results should match.
10. Check no secrets or mutable infrastructure actions are performed.
11. Capture thread stack traces during a training-only lock contention scenario.
12. Demonstrate that `Future.result(timeout)` does not forcibly stop a running thread.

## 5. Production runbooks
**Pool saturation:** measure queue depth and upstream latency, reduce input rate and restore bounded worker counts.

**Deadlock:** collect thread dumps, inspect lock ordering, remove blocking I/O from critical sections and roll back.

**Timeout:** distinguish executor wait deadline from adapter network timeout; enforce both and verify cleanup.

**Telemetry inconsistency:** stop automatic remediation, restore synchronization and rerun stress tests.

**Rollback:** pin known-good code, replay fixtures, compare deterministic reports and verify no lingering workers.

## 6. 100-point assessment
| Criterion | Points |
|---|---:|
| Syntax and automated tests | 25 |
| ThreadPoolExecutor and Future semantics | 20 |
| Lock-protected shared state | 20 |
| Deadline and cancellation safety | 15 |
| Incident simulations | 10 |
| Troubleshooting and production runbooks | 10 |

Target: **90/100** with all safety tests passing. Tests are published for execution; publication does not establish a passing run.
