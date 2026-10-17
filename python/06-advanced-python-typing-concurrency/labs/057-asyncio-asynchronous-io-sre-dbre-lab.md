# Chapter 057 — AsyncIO and Asynchronous I/O SRE/DBRE Lab

**Python 3.11+ | Standard library | Offline and read-only**

## Project layout
```text
ch057/
  async_ops.py
  test_async_ops.py
```

## 1. async_ops.py
```python
"""Chapter 057 — safe offline asynchronous SRE/DBRE telemetry polling (Python 3.11+)."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import math
import re
import sys
from typing import AsyncIterator

POLICY = {
    "postgresql": ("replication_lag", "seconds", 30, 120),
    "elasticsearch": ("search_latency", "milliseconds", 200, 500),
    "kafka": ("consumer_lag", "messages", 1000, 10000),
}
MAX_TASKS = 100
MAX_CONCURRENCY = 16

class TelemetryError(ValueError):
    pass

@dataclass(frozen=True)
class Target:
    service: str
    engine: str
    metric: str
    unit: str
    value: float
    delay: float = 0.0

@dataclass(frozen=True)
class Reading:
    service: str
    engine: str
    severity: str
    value: float

class AsyncResource:
    """Synthetic async session with observable cleanup; no network access."""
    def __init__(self) -> None:
        self.open = False
        self.closed = False

    async def __aenter__(self) -> "AsyncResource":
        if self.open or self.closed:
            raise TelemetryError("resource already used")
        self.open = True
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        self.open = False
        self.closed = True
        return False

    async def read(self, target: Target) -> Reading:
        if not self.open or self.closed:
            raise TelemetryError("resource not active")
        if target.delay:
            await asyncio.sleep(target.delay)
        _, _, warning, critical = POLICY[target.engine]
        severity = "critical" if target.value >= critical else "warning" if target.value >= warning else "healthy"
        return Reading(target.service, target.engine, severity, target.value)

def validate_target(raw: dict[str, object]) -> Target:
    if not isinstance(raw, dict) or set(raw) not in (
        {"service", "engine", "metric", "unit", "value"},
        {"service", "engine", "metric", "unit", "value", "delay"},
    ):
        raise TelemetryError("invalid target schema")
    service, engine = raw["service"], raw["engine"]
    if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise TelemetryError("invalid service")
    if not isinstance(engine, str) or engine not in POLICY:
        raise TelemetryError("unknown engine")
    metric, unit, _, _ = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise TelemetryError("metric/unit mismatch")
    value, delay = raw["value"], raw.get("delay", 0)
    if type(value) not in (int, float) or type(delay) not in (int, float):
        raise TelemetryError("numeric values required")
    try:
        number, seconds = float(value), float(delay)
    except (OverflowError, ValueError) as exc:
        raise TelemetryError("invalid numeric values") from exc
    if not math.isfinite(number) or number < 0:
        raise TelemetryError("invalid metric value")
    if not math.isfinite(seconds) or not 0 <= seconds <= 0.1:
        raise TelemetryError("delay outside 0..0.1")
    return Target(service, engine, metric, unit, number, seconds)

async def collect_one(target: Target, gate: asyncio.Semaphore) -> Reading:
    async with gate:
        async with AsyncResource() as resource:
            return await resource.read(target)

async def collect(targets: list[Target], *, concurrency: int = 3,
                  timeout: float = 2.0) -> list[Reading]:
    if type(concurrency) is not int or not 1 <= concurrency <= MAX_CONCURRENCY:
        raise TelemetryError("concurrency must be 1..16")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise TelemetryError("timeout must be finite in (0,30]")
    if len(targets) > MAX_TASKS:
        raise TelemetryError("too many targets")
    if len({(t.engine, t.service) for t in targets}) != len(targets):
        raise TelemetryError("duplicate target")
    gate = asyncio.Semaphore(concurrency)
    # asyncio.timeout covers task creation, execution, cancellation and cleanup.
    async with asyncio.timeout(timeout):
        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(collect_one(target, gate)) for target in targets]
        return [task.result() for task in tasks]

def report(readings: list[Reading]) -> dict[str, object]:
    counts = Counter(item.severity for item in readings)
    if set(counts) - {"healthy", "warning", "critical"}:
        raise TelemetryError("unexpected severity")
    return {
        "schema_version": 1,
        "dry_run": True,
        "total": len(readings),
        "counts": {key: counts[key] for key in ("healthy", "warning", "critical")},
        "results": [
            {"service": item.service, "engine": item.engine,
             "severity": item.severity, "value": item.value}
            for item in sorted(readings, key=lambda r: (r.engine, r.service))
        ],
    }

def fixtures() -> list[Target]:
    return [
        Target("pg-replica", "postgresql", "replication_lag", "seconds", 45),
        Target("es-search", "elasticsearch", "search_latency", "milliseconds", 650),
        Target("kafka-worker", "kafka", "consumer_lag", "messages", 10000),
    ]

async def pipeline(*, concurrency: int = 3, timeout: float = 2.0) -> dict[str, object]:
    return report(await collect(fixtures(), concurrency=concurrency, timeout=timeout))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline asyncio telemetry lab")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args(argv)
    try:
        output = asyncio.run(pipeline(concurrency=args.concurrency, timeout=args.timeout))
    except (TelemetryError, TimeoutError, OSError, ExceptionGroup):
        print("async operation failed: sanitized error", file=sys.stderr)
        return 3
    print(json.dumps(output, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. test_async_ops.py
```python
"""Offline unittest.IsolatedAsyncioTestCase coverage for Chapter 057."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch
from async_ops import (
    AsyncResource, TelemetryError, Target, Reading, validate_target,
    collect_one, collect, report, fixtures, pipeline, main,
)

PG={"service":"pg-replica","engine":"postgresql","metric":"replication_lag",
    "unit":"seconds","value":45}

class ValidationTests(unittest.TestCase):
    def bad(self, **changes):
        with self.assertRaises(TelemetryError): validate_target({**PG, **changes})
    def test_valid(self): self.assertEqual(validate_target(PG).engine,"postgresql")
    def test_delay(self): self.assertEqual(validate_target({**PG,"delay":0.01}).delay,0.01)
    def test_bad_engine(self): self.bad(engine="mysql")
    def test_bad_metric(self): self.bad(metric="latency")
    def test_bad_unit(self): self.bad(unit="milliseconds")
    def test_bad_service(self): self.bad(service="=cmd")
    def test_bad_unicode(self): self.bad(service="東京")
    def test_bad_bool_value(self): self.bad(value=True)
    def test_bad_string_value(self): self.bad(value="45")
    def test_bad_nan(self): self.bad(value=float("nan"))
    def test_bad_inf(self): self.bad(value=float("inf"))
    def test_bad_negative(self): self.bad(value=-1)
    def test_bad_bool_delay(self): self.bad(delay=True)
    def test_bad_negative_delay(self): self.bad(delay=-0.01)
    def test_bad_long_delay(self): self.bad(delay=1)
    def test_bad_extra(self): self.bad(secret="x")
    def test_missing(self):
        raw=dict(PG); del raw["unit"]
        with self.assertRaises(TelemetryError): validate_target(raw)
    def test_report_empty(self): self.assertEqual(report([])["total"],0)
    def test_report_sorted(self):
        rows=[Reading("z","postgresql","healthy",0),Reading("a","postgresql","warning",30)]
        self.assertEqual(report(rows)["results"][0]["service"],"a")
    def test_report_invalid(self):
        with self.assertRaises(TelemetryError): report([Reading("x","postgresql","unknown",1)])
    def test_report_dry_run(self): self.assertTrue(report([])["dry_run"])
    def test_fixture_count(self): self.assertEqual(len(fixtures()),3)
    def test_main_success(self): self.assertEqual(main([]),0)
    def test_main_failure(self): self.assertEqual(main(["--concurrency","0"]),3)

class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_resource_initial(self):
        r=AsyncResource()
        self.assertFalse(r.open)
    async def test_resource_enter(self):
        r=AsyncResource()
        async with r: self.assertTrue(r.open)
        self.assertTrue(r.closed)
    async def test_resource_reuse(self):
        r=AsyncResource()
        async with r: pass
        with self.assertRaises(TelemetryError):
            async with r: pass
    async def test_resource_read_outside(self):
        with self.assertRaises(TelemetryError):
            await AsyncResource().read(fixtures()[0])
    async def test_resource_read(self):
        async with AsyncResource() as r:
            reading=await r.read(fixtures()[0])
        self.assertEqual(reading.severity,"warning")
    async def test_resource_exception_cleanup(self):
        r=AsyncResource()
        with self.assertRaises(ValueError):
            async with r: raise ValueError("synthetic")
        self.assertTrue(r.closed)
    async def test_resource_cancel_cleanup(self):
        r=AsyncResource()
        async def task():
            async with r:
                await asyncio.sleep(1)
        t=asyncio.create_task(task())
        await asyncio.sleep(0)
        t.cancel()
        with self.assertRaises(asyncio.CancelledError): await t
        self.assertTrue(r.closed)
    async def test_collect_one(self):
        result=await collect_one(fixtures()[0],asyncio.Semaphore(1))
        self.assertEqual(result.severity,"warning")
    async def test_collect(self):
        self.assertEqual(len(await collect(fixtures())),3)
    async def test_collect_counts(self):
        self.assertEqual(report(await collect(fixtures()))["counts"],
                         {"healthy":0,"warning":1,"critical":2})
    async def test_collect_empty(self):
        self.assertEqual(await collect([]),[])
    async def test_collect_one_concurrency(self):
        self.assertEqual(len(await collect(fixtures(),concurrency=1)),3)
    async def test_collect_max_concurrency(self):
        self.assertEqual(len(await collect(fixtures(),concurrency=16)),3)
    async def test_collect_bad_concurrency(self):
        with self.assertRaises(TelemetryError): await collect(fixtures(),concurrency=0)
    async def test_collect_large_concurrency(self):
        with self.assertRaises(TelemetryError): await collect(fixtures(),concurrency=17)
    async def test_collect_bool_concurrency(self):
        with self.assertRaises(TelemetryError): await collect(fixtures(),concurrency=True)
    async def test_collect_zero_timeout(self):
        with self.assertRaises(TelemetryError): await collect(fixtures(),timeout=0)
    async def test_collect_nan_timeout(self):
        with self.assertRaises(TelemetryError): await collect(fixtures(),timeout=float("nan"))
    async def test_collect_bool_timeout(self):
        with self.assertRaises(TelemetryError): await collect(fixtures(),timeout=True)
    async def test_collect_large_timeout(self):
        with self.assertRaises(TelemetryError): await collect(fixtures(),timeout=31)
    async def test_collect_duplicate(self):
        with self.assertRaises(TelemetryError): await collect([fixtures()[0],fixtures()[0]])
    async def test_collect_many(self):
        targets=[Target(f"pg{i}","postgresql","replication_lag","seconds",1) for i in range(101)]
        with self.assertRaises(TelemetryError): await collect(targets)
    async def test_collect_timeout(self):
        target=Target("pg","postgresql","replication_lag","seconds",1,0.1)
        with self.assertRaises(TimeoutError): await collect([target],timeout=0.001)
    async def test_collect_delayed(self):
        target=Target("pg","postgresql","replication_lag","seconds",1,0.001)
        self.assertEqual(len(await collect([target])),1)
    async def test_collect_deterministic(self):
        self.assertEqual(report(await collect(fixtures())),report(await collect(fixtures())))
    async def test_collect_failure_group(self):
        bad=Target("pg","unknown","x","y",1)
        with self.assertRaises(ExceptionGroup):
            await collect([bad])
    async def test_pipeline(self):
        self.assertEqual((await pipeline())["total"],3)
    async def test_pipeline_no_secrets(self):
        self.assertNotIn("password",json.dumps(await pipeline()))
    async def test_gather(self):
        result=await asyncio.gather(
            collect_one(fixtures()[0],asyncio.Semaphore(1)),
            collect_one(fixtures()[1],asyncio.Semaphore(1)))
        self.assertEqual(len(result),2)
    async def test_semaphore_bounds(self):
        gate=asyncio.Semaphore(1)
        active=0
        peak=0
        async def worker():
            nonlocal active,peak
            async with gate:
                active+=1
                peak=max(peak,active)
                await asyncio.sleep(0)
                active-=1
        await asyncio.gather(*(worker() for _ in range(20)))
        self.assertEqual(peak,1)

if __name__=="__main__":
    unittest.main()

```

## 3. Execute
Linux/macOS/WSL:
```bash
python3 --version  # Python 3.11 or later
python3 -m py_compile async_ops.py test_async_ops.py
python3 -m unittest -v test_async_ops.py
python3 async_ops.py --concurrency 3 --timeout 2
```

Windows PowerShell:
```powershell
py -3 --version
py -3 -m py_compile async_ops.py test_async_ops.py
py -3 -m unittest -v test_async_ops.py
py -3 async_ops.py --concurrency 3 --timeout 2
```

Expected synthetic result: 3 events, 0 healthy, 1 warning, 2 critical. Exit 0 means successful offline processing, not healthy production services.

## 4. Failure injection and incident simulations
1. Compare `asyncio.gather` and `TaskGroup` sibling-failure behavior.
2. Cancel a task inside `async with`; verify resource cleanup.
3. Use a 1 ms deadline with a 100 ms simulated I/O delay.
4. Run with concurrency 1, 3 and 16; verify identical sorted results.
5. Test a semaphore protecting a shared active-count invariant.
6. Inject an unknown engine into a worker to trigger `ExceptionGroup`.
7. Inject NaN, Infinity, boolean, negative and wrong-unit telemetry.
8. Submit duplicate targets and more than 100 tasks.
9. Try a training-only `time.sleep` inside a coroutine and observe event-loop lag.
10. Create an unawaited coroutine in a disposable script and inspect the warning.
11. Use `asyncio.all_tasks()` during a training-only run to inspect task ownership.
12. Verify no secrets, infrastructure writes or external connections occur.

## 5. Troubleshooting and production runbooks
**Stalled event loop:** locate blocking operations and replace them with async drivers or bounded thread offloading.

**Leaked sessions:** enforce `async with`, verify cleanup on cancellation and inspect active resource counters.

**Timeout:** check the overall deadline and per-adapter I/O timeout; do not suppress cancellation.

**Task overload:** enforce a fixed concurrency gate, task cap and bounded queue.

**Rollback:** restore the previous async adapter and task limits; rerun tests and compare sanitized reports.

## 6. 100-point assessment
| Criterion | Points |
|---|---:|
| Syntax and automated tests | 25 |
| Event loop, tasks and gather | 20 |
| TaskGroup and cancellation semantics | 20 |
| Semaphore and bounded concurrency | 15 |
| Incident simulations | 10 |
| Production runbooks and rollback | 10 |

Target **90/100** with all safety tests passing. The tests are published for learner execution; publication alone does not establish a passing run.
