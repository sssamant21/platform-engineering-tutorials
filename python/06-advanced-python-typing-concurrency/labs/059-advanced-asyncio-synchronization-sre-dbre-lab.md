# Chapter 059 — Advanced AsyncIO Synchronization and Resilient Concurrency Lab

**Python 3.11+ | Standard library | Offline and non-destructive**

## Layout
```text
ch059/
  async_sync_ops.py
  test_async_sync_ops.py
```

## Complete source: async_sync_ops.py
```python
"""Chapter 059 — offline asyncio synchronization and resilient polling. Python 3.11+."""
from __future__ import annotations
import argparse
import asyncio
from collections import Counter
from dataclasses import dataclass
import json
import math
import re
import sys

POLICY = {
    "postgresql": ("replication_lag", "seconds", 30, 120),
    "elasticsearch": ("search_latency", "milliseconds", 200, 500),
    "kafka": ("consumer_lag", "messages", 1000, 10000),
}
class TelemetryError(ValueError): pass
class TransientError(RuntimeError): pass

@dataclass(frozen=True)
class Target:
    service: str
    engine: str
    value: float
    transient_failures: int = 0

@dataclass(frozen=True)
class Reading:
    service: str
    engine: str
    severity: str
    attempts: int

class Metrics:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.started = 0
        self.finished = 0
        self.retried = 0
    async def add(self, name: str) -> None:
        if name not in ("started", "finished", "retried"):
            raise TelemetryError("unknown counter")
        async with self._lock:
            setattr(self, name, getattr(self, name) + 1)
    async def snapshot(self) -> dict[str, int]:
        async with self._lock:
            return {"started": self.started, "finished": self.finished, "retried": self.retried}

class Readiness:
    """Event + Condition illustrate distinct notification contracts."""
    def __init__(self) -> None:
        self.ready = asyncio.Event()
        self.condition = asyncio.Condition()
        self.version = 0
    async def publish(self) -> None:
        async with self.condition:
            self.version += 1
            self.ready.set()
            self.condition.notify_all()
    async def wait_version(self, minimum: int) -> int:
        async with self.condition:
            await self.condition.wait_for(lambda: self.version >= minimum)
            return self.version

def validate(raw: object) -> Target:
    if not isinstance(raw, dict) or set(raw) != {"service", "engine", "metric", "unit", "value", "transient_failures"}:
        raise TelemetryError("invalid schema")
    service, engine = raw["service"], raw["engine"]
    if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise TelemetryError("invalid service")
    if not isinstance(engine, str) or engine not in POLICY:
        raise TelemetryError("invalid engine")
    metric, unit, _, _ = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise TelemetryError("metric/unit mismatch")
    value, failures = raw["value"], raw["transient_failures"]
    if type(value) not in (int, float) or type(failures) is not int:
        raise TelemetryError("invalid numeric type")
    try: value = float(value)
    except (OverflowError, ValueError) as exc: raise TelemetryError("invalid metric") from exc
    if not math.isfinite(value) or value < 0 or not 0 <= failures <= 3:
        raise TelemetryError("invalid value or failure budget")
    return Target(service, engine, value, failures)

async def poll(target: Target, gate: asyncio.Semaphore, metrics: Metrics,
               *, attempts: int = 3, backoff: float = 0.001) -> Reading:
    if type(attempts) is not int or not 1 <= attempts <= 4:
        raise TelemetryError("invalid attempt budget")
    if type(backoff) not in (int, float) or not math.isfinite(backoff) or not 0 <= backoff <= 0.1:
        raise TelemetryError("invalid backoff")
    await metrics.add("started")
    # Limit each simulated I/O operation; never hold semaphore during backoff.
    try:
        for index in range(attempts):
            try:
                async with gate:
                    await asyncio.sleep(0)
                    if index < target.transient_failures:
                        raise TransientError("synthetic transient read failure")
                    _, _, warn, critical = POLICY[target.engine]
                    severity = "critical" if target.value >= critical else "warning" if target.value >= warn else "healthy"
                    return Reading(target.service, target.engine, severity, index + 1)
            except TransientError:
                if index + 1 >= attempts:
                    raise
                await metrics.add("retried")
                await asyncio.sleep(backoff * (2 ** index))
        raise AssertionError("unreachable")
    finally:
        await metrics.add("finished")

def report(readings: list[Reading], counters: dict[str, int]) -> dict[str, object]:
    counts = Counter(r.severity for r in readings)
    return {"schema_version": 1, "dry_run": True, "total": len(readings),
            "counts": {k: counts[k] for k in ("healthy", "warning", "critical")},
            "counters": counters,
            "results": [{"service": r.service, "engine": r.engine,
                         "severity": r.severity, "attempts": r.attempts}
                        for r in sorted(readings, key=lambda x: (x.engine, x.service))]}

async def run(targets: list[Target], *, concurrency: int = 3,
              timeout: float = 2.0, attempts: int = 3) -> dict[str, object]:
    if type(concurrency) is not int or not 1 <= concurrency <= 8:
        raise TelemetryError("concurrency must be 1..8")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise TelemetryError("timeout must be finite in (0,30]")
    if type(attempts) is not int or not 1 <= attempts <= 4:
        raise TelemetryError("attempts must be 1..4")
    if len(targets) > 100 or len({(t.engine, t.service) for t in targets}) != len(targets):
        raise TelemetryError("too many or duplicate targets")
    gate = asyncio.Semaphore(concurrency)
    metrics = Metrics()
    async with asyncio.timeout(timeout):
        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(poll(t, gate, metrics, attempts=attempts)) for t in targets]
        results = [task.result() for task in tasks]
    return report(results, await metrics.snapshot())

def fixtures() -> list[Target]:
    return [Target("pg-replica", "postgresql", 45, 1),
            Target("es-search", "elasticsearch", 650),
            Target("kafka-worker", "kafka", 10000)]

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Offline asyncio synchronization lab")
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--timeout", type=float, default=2)
    p.add_argument("--attempts", type=int, default=3)
    args = p.parse_args(argv)
    try:
        result = asyncio.run(run(fixtures(), concurrency=args.concurrency,
                                 timeout=args.timeout, attempts=args.attempts))
    except (TelemetryError, TimeoutError, ExceptionGroup):
        print("operation failed: sanitized error", file=sys.stderr)
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## Automated tests: test_async_sync_ops.py
```python
import asyncio
import json
import unittest
from async_sync_ops import (
    Target, Reading, TelemetryError, TransientError, Metrics, Readiness,
    validate, poll, report, run, fixtures, main
)

PG={"service":"pg-replica","engine":"postgresql","metric":"replication_lag",
    "unit":"seconds","value":45,"transient_failures":1}

class ValidationTests(unittest.TestCase):
    def bad(self, **updates):
        with self.assertRaises(TelemetryError): validate({**PG,**updates})
    def test_valid(self): self.assertEqual(validate(PG).transient_failures,1)
    def test_engine(self): self.bad(engine="mysql")
    def test_metric(self): self.bad(metric="latency")
    def test_unit(self): self.bad(unit="ms")
    def test_service(self): self.bad(service="=cmd")
    def test_boolean(self): self.bad(value=True)
    def test_string(self): self.bad(value="45")
    def test_nan(self): self.bad(value=float("nan"))
    def test_inf(self): self.bad(value=float("inf"))
    def test_negative(self): self.bad(value=-1)
    def test_failure_budget(self): self.bad(transient_failures=4)
    def test_failure_boolean(self): self.bad(transient_failures=True)
    def test_extra(self): self.bad(password="secret")
    def test_missing(self):
        d=dict(PG); del d["unit"]
        with self.assertRaises(TelemetryError): validate(d)
    def test_nonobject(self):
        with self.assertRaises(TelemetryError): validate([])
    def test_report(self):
        self.assertEqual(report([Reading("a","postgresql","healthy",1)],{})["total"],1)
    def test_report_empty(self): self.assertEqual(report([],{})["total"],0)
    def test_fixture(self): self.assertEqual(len(fixtures()),3)
    def test_main(self): self.assertEqual(main([]),0)
    def test_main_bad(self): self.assertEqual(main(["--attempts","0"]),3)

class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_metrics(self):
        m=Metrics()
        await m.add("started"); await m.add("finished"); await m.add("retried")
        self.assertEqual((await m.snapshot())["retried"],1)
    async def test_metrics_invalid(self):
        with self.assertRaises(TelemetryError): await Metrics().add("bad")
    async def test_metrics_concurrent(self):
        m=Metrics()
        await asyncio.gather(*(m.add("started") for _ in range(1000)))
        self.assertEqual((await m.snapshot())["started"],1000)
    async def test_readiness_event(self):
        r=Readiness()
        await r.publish()
        await asyncio.wait_for(r.ready.wait(),1)
        self.assertEqual(r.version,1)
    async def test_readiness_condition(self):
        r=Readiness()
        waiter=asyncio.create_task(r.wait_version(2))
        await asyncio.sleep(0)
        await r.publish(); await r.publish()
        self.assertEqual(await asyncio.wait_for(waiter,1),2)
    async def test_readiness_wait_timeout(self):
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(Readiness().wait_version(1),0.001)
    async def test_poll_retry(self):
        m=Metrics()
        r=await poll(fixtures()[0],asyncio.Semaphore(1),m)
        self.assertEqual(r.attempts,2)
        self.assertEqual((await m.snapshot())["retried"],1)
    async def test_poll_success(self):
        r=await poll(fixtures()[1],asyncio.Semaphore(1),Metrics())
        self.assertEqual(r.severity,"critical")
    async def test_poll_exhausted(self):
        with self.assertRaises(TransientError):
            await poll(Target("pg","postgresql",1,3),asyncio.Semaphore(1),Metrics(),attempts=2)
    async def test_poll_bad_attempts(self):
        with self.assertRaises(TelemetryError):
            await poll(fixtures()[0],asyncio.Semaphore(1),Metrics(),attempts=0)
    async def test_poll_bad_backoff(self):
        with self.assertRaises(TelemetryError):
            await poll(fixtures()[0],asyncio.Semaphore(1),Metrics(),backoff=-1)
    async def test_run(self): self.assertEqual((await run(fixtures()))["total"],3)
    async def test_run_counts(self):
        self.assertEqual((await run(fixtures()))["counts"],{"healthy":0,"warning":1,"critical":2})
    async def test_run_counters(self):
        self.assertEqual((await run(fixtures()))["counters"],{"started":3,"finished":3,"retried":1})
    async def test_run_empty(self): self.assertEqual((await run([]))["total"],0)
    async def test_run_single(self): self.assertEqual((await run(fixtures(),concurrency=1))["total"],3)
    async def test_run_eight(self): self.assertEqual((await run(fixtures(),concurrency=8))["total"],3)
    async def test_run_zero_workers(self):
        with self.assertRaises(TelemetryError): await run([],concurrency=0)
    async def test_run_many_workers(self):
        with self.assertRaises(TelemetryError): await run([],concurrency=9)
    async def test_run_bool_workers(self):
        with self.assertRaises(TelemetryError): await run([],concurrency=True)
    async def test_run_zero_timeout(self):
        with self.assertRaises(TelemetryError): await run([],timeout=0)
    async def test_run_nan_timeout(self):
        with self.assertRaises(TelemetryError): await run([],timeout=float("nan"))
    async def test_run_bool_timeout(self):
        with self.assertRaises(TelemetryError): await run([],timeout=True)
    async def test_run_bad_attempts(self):
        with self.assertRaises(TelemetryError): await run([],attempts=0)
    async def test_run_duplicate(self):
        with self.assertRaises(TelemetryError): await run([fixtures()[0],fixtures()[0]])
    async def test_run_too_many(self):
        with self.assertRaises(TelemetryError):
            await run([Target(f"pg{i}","postgresql",1) for i in range(101)])
    async def test_run_exhausted_group(self):
        with self.assertRaises(ExceptionGroup):
            await run([Target("pg","postgresql",1,3)],attempts=2)
    async def test_run_timeout(self):
        with self.assertRaises(TimeoutError):
            await run([Target("pg","postgresql",1,2)],timeout=0.00001)
    async def test_run_sorted(self):
        a=await run(fixtures(),concurrency=1)
        b=await run(fixtures(),concurrency=8)
        self.assertEqual(a["results"],b["results"])
    async def test_no_secrets(self):
        self.assertNotIn("password",json.dumps(await run(fixtures())))
    async def test_barrier(self):
        barrier=asyncio.Barrier(3)
        async def participant():
            await barrier.wait()
            return True
        self.assertEqual(await asyncio.gather(*(participant() for _ in range(3))),[True]*3)

if __name__=="__main__":
    unittest.main()

```

## Run
```bash
python3 -m py_compile async_sync_ops.py test_async_sync_ops.py
python3 -m unittest -v test_async_sync_ops.py
python3 async_sync_ops.py --concurrency 3 --timeout 2 --attempts 3
```

Windows PowerShell: replace `python3` with `py -3`. Requires Python 3.11+ for `TaskGroup` and `asyncio.Barrier`.

Expected synthetic results: three events, one warning, two critical, three started and finished, one retry. Exit code zero means offline computation succeeded, not that infrastructure is healthy.

## Failure injection
1. Run 1,000 concurrent Lock-protected counter updates.
2. Demonstrate a read–await–write race in a disposable copy without locking.
3. Wait for Event readiness and Condition version two.
4. Time out a Condition predicate that never becomes true.
5. Synchronize three Barrier participants.
6. Reduce Barrier parties incorrectly in a disposable experiment and observe deadline behavior.
7. Inject one transient failure and verify a successful retry.
8. Exhaust the retry budget and inspect TaskGroup ExceptionGroup.
9. Set an overall deadline shorter than retry backoff.
10. Compare one and eight concurrent tasks for deterministic results.
11. Inject invalid units, NaN, Infinity, boolean and negative values.
12. Confirm sanitized output and absence of production side effects.

## Runbooks
**Synchronization hang:** inspect task stacks, condition predicates and lock ownership; restore correct signal ordering.

**Retry overload:** lower attempt budget, increase bounded backoff, introduce jitter for real adapters, and halt unsafe write retries.

**Deadline exceeded:** distinguish I/O timeout from overall deadline and verify cancellation cleanup.

**Rollback:** restore prior async synchronization logic, replay fixtures and rerun tests.

## 100-point assessment
| Category | Points |
|---|---:|
| Syntax and automated tests | 25 |
| Lock, Event and Condition correctness | 20 |
| Semaphore and Barrier safety | 20 |
| Retry, timeout and TaskGroup handling | 15 |
| Failure injection | 10 |
| Troubleshooting and runbooks | 10 |

Target 90/100 with all safety checks passing. Test execution must be verified independently.
