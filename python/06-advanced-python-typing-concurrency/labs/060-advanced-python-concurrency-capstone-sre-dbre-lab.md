# Chapter 060 — Advanced Python Concurrency Production Capstone Lab

**Python 3.11+ | Standard library | Offline, synthetic and non-destructive**

## Repository layout
```text
ch060/
  capstone_ops.py
  test_capstone_ops.py
```

## 1. Complete executable source: capstone_ops.py
```python
"""Chapter 060 capstone: offline concurrency pipeline, Python 3.11+."""
from __future__ import annotations
import argparse
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import math
from multiprocessing import get_context
import os
import re
import sys
import threading
import time

POLICY = {
    "postgresql": ("replication_lag", "seconds", 30, 120),
    "elasticsearch": ("search_latency", "milliseconds", 200, 500),
    "kafka": ("consumer_lag", "messages", 1000, 10000),
}
MAX_ITEMS = 40
STOP = object()

class CapstoneError(ValueError):
    pass

@dataclass(frozen=True)
class Sample:
    service: str
    engine: str
    value: float

@dataclass(frozen=True)
class Assessment:
    service: str
    engine: str
    severity: str
    digest: str

class ThreadMetrics:
    """threading.Lock protects counters updated from executor workers."""
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.reads = 0
        self.failures = 0
    def record(self, success: bool) -> None:
        with self.lock:
            if success:
                self.reads += 1
            else:
                self.failures += 1
    def snapshot(self) -> dict[str, int]:
        with self.lock:
            return {"reads": self.reads, "failures": self.failures}

def validate(raw: object) -> Sample:
    if not isinstance(raw, dict) or set(raw) != {"service", "engine", "metric", "unit", "value"}:
        raise CapstoneError("invalid telemetry schema")
    service, engine = raw["service"], raw["engine"]
    if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise CapstoneError("invalid service")
    if not isinstance(engine, str) or engine not in POLICY:
        raise CapstoneError("unknown engine")
    metric, unit, _, _ = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise CapstoneError("metric/unit mismatch")
    value = raw["value"]
    if type(value) not in (int, float):
        raise CapstoneError("numeric metric required")
    try:
        value = float(value)
    except (OverflowError, ValueError) as exc:
        raise CapstoneError("invalid metric") from exc
    if not math.isfinite(value) or value < 0:
        raise CapstoneError("invalid metric")
    return Sample(service, engine, value)

def blocking_read(sample: Sample, metrics: ThreadMetrics) -> Sample:
    """Synthetic synchronous adapter: no network, no live infrastructure."""
    try:
        time.sleep(0.0005)
        metrics.record(True)
        return sample
    except Exception:
        metrics.record(False)
        raise

def cpu_assess(sample: Sample) -> Assessment:
    """Picklable, pure CPU worker; deterministic output across processes."""
    if sample.engine not in POLICY or not math.isfinite(sample.value) or sample.value < 0:
        raise CapstoneError("invalid CPU worker input")
    _, _, warn, critical = POLICY[sample.engine]
    severity = "critical" if sample.value >= critical else "warning" if sample.value >= warn else "healthy"
    digest = hashlib.sha256(f"{sample.engine}:{sample.service}:{sample.value:.3f}".encode("ascii")).digest()
    for _ in range(100):
        digest = hashlib.sha256(digest).digest()
    return Assessment(sample.service, sample.engine, severity, digest.hex())

async def producer(items: list[Sample], queue: asyncio.Queue[object],
                   peak: list[int]) -> None:
    for item in items:
        await queue.put(item)
        peak[0] = max(peak[0], queue.qsize())

async def consumer(queue: asyncio.Queue[object], output: list[Assessment],
                   metrics: ThreadMetrics, threads: ThreadPoolExecutor,
                   processes: ProcessPoolExecutor, gate: asyncio.Semaphore) -> None:
    loop = asyncio.get_running_loop()
    while True:
        item = await queue.get()
        try:
            if item is STOP:
                return
            if not isinstance(item, Sample):
                raise CapstoneError("unexpected queue item")
            async with gate:
                fetched = await loop.run_in_executor(threads, blocking_read, item, metrics)
                assessed = await loop.run_in_executor(processes, cpu_assess, fetched)
            output.append(assessed)
        finally:
            queue.task_done()

def summarize(results: list[Assessment], metrics: ThreadMetrics, peak: int) -> dict[str, object]:
    counts = {"healthy": 0, "warning": 0, "critical": 0}
    for item in results:
        if item.severity not in counts:
            raise CapstoneError("unexpected severity")
        counts[item.severity] += 1
    return {
        "schema_version": 1, "dry_run": True, "total": len(results),
        "counts": counts, "thread_metrics": metrics.snapshot(), "peak_queue": peak,
        "results": [
            {"service": r.service, "engine": r.engine, "severity": r.severity, "digest": r.digest}
            for r in sorted(results, key=lambda r: (r.engine, r.service))
        ],
    }

async def pipeline(raw: list[object], *, workers: int = 2,
                   queue_size: int = 2, timeout: float = 15.0) -> dict[str, object]:
    if type(workers) is not int or not 1 <= workers <= 4:
        raise CapstoneError("workers must be 1..4")
    if type(queue_size) is not int or not 1 <= queue_size <= 16:
        raise CapstoneError("queue_size must be 1..16")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise CapstoneError("timeout must be finite in (0,60]")
    if len(raw) > MAX_ITEMS:
        raise CapstoneError("too many telemetry events")
    items = [validate(value) for value in raw]
    if len({(x.engine, x.service) for x in items}) != len(items):
        raise CapstoneError("duplicate telemetry source")
    if not items:
        return summarize([], ThreadMetrics(), 0)
    queue: asyncio.Queue[object] = asyncio.Queue(maxsize=queue_size)
    output: list[Assessment] = []
    metrics = ThreadMetrics()
    peak = [0]
    gate = asyncio.Semaphore(workers)
    # Explicit spawn avoids unsafe fork of an active threaded event-loop process.
    # Pool contexts wait on running work; cancellation is NOT hard termination.
    with ThreadPoolExecutor(max_workers=workers) as threads:
        with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn")) as processes:
            async with asyncio.timeout(timeout):
                async with asyncio.TaskGroup() as group:
                    tasks = [
                        group.create_task(consumer(queue, output, metrics, threads, processes, gate))
                        for _ in range(workers)
                    ]
                    await producer(items, queue, peak)
                    for _ in tasks:
                        await queue.put(STOP)
                    await queue.join()
    if len(output) != len(items) or metrics.snapshot()["reads"] != len(items):
        raise CapstoneError("incomplete batch")
    return summarize(output, metrics, peak[0])

def fixtures() -> list[dict[str, object]]:
    return [
        {"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45},
        {"service":"es-search","engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":650},
        {"service":"kafka-worker","engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000},
    ]

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline concurrency SRE/DBRE capstone")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--queue-size", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(pipeline(fixtures(), workers=args.workers,
                                      queue_size=args.queue_size, timeout=args.timeout))
    except (CapstoneError, TimeoutError, ExceptionGroup, OSError):
        print("capstone failed: sanitized operational error", file=sys.stderr)
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. Complete automated tests: test_capstone_ops.py
```python
"""Chapter 060 unit and end-to-end tests. Run as a file for spawn safety."""
import asyncio
import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from capstone_ops import (
    Sample, Assessment, CapstoneError, ThreadMetrics, validate, blocking_read,
    cpu_assess, summarize, pipeline, fixtures, main
)

PG={"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45}

class UnitTests(unittest.TestCase):
    def bad(self, **updates):
        with self.assertRaises(CapstoneError): validate({**PG,**updates})
    def test_valid(self): self.assertEqual(validate(PG).engine,"postgresql")
    def test_engine(self): self.bad(engine="mysql")
    def test_metric(self): self.bad(metric="latency")
    def test_unit(self): self.bad(unit="ms")
    def test_service(self): self.bad(service="=cmd")
    def test_unicode(self): self.bad(service="東京")
    def test_bool(self): self.bad(value=True)
    def test_string(self): self.bad(value="45")
    def test_nan(self): self.bad(value=float("nan"))
    def test_inf(self): self.bad(value=float("inf"))
    def test_negative(self): self.bad(value=-1)
    def test_extra(self): self.bad(secret="x")
    def test_missing(self):
        raw=dict(PG); del raw["unit"]
        with self.assertRaises(CapstoneError): validate(raw)
    def test_nonobject(self):
        with self.assertRaises(CapstoneError): validate([])
    def test_cpu_warning(self):
        self.assertEqual(cpu_assess(validate(PG)).severity,"warning")
    def test_cpu_healthy(self):
        self.assertEqual(cpu_assess(Sample("pg","postgresql",0)).severity,"healthy")
    def test_cpu_critical(self):
        self.assertEqual(cpu_assess(Sample("pg","postgresql",120)).severity,"critical")
    def test_cpu_bad(self):
        with self.assertRaises(CapstoneError): cpu_assess(Sample("pg","postgresql",-1))
    def test_cpu_deterministic(self):
        self.assertEqual(cpu_assess(validate(PG)),cpu_assess(validate(PG)))
    def test_digest_length(self):
        self.assertEqual(len(cpu_assess(validate(PG)).digest),64)
    def test_thread_metrics(self):
        m=ThreadMetrics()
        m.record(True); m.record(False)
        self.assertEqual(m.snapshot(),{"reads":1,"failures":1})
    def test_thread_metrics_stress(self):
        m=ThreadMetrics()
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: m.record(True), range(1000)))
        self.assertEqual(m.snapshot()["reads"],1000)
    def test_blocking_read(self):
        m=ThreadMetrics()
        self.assertEqual(blocking_read(validate(PG),m),validate(PG))
        self.assertEqual(m.snapshot()["reads"],1)
    def test_summarize_empty(self):
        self.assertEqual(summarize([],ThreadMetrics(),0)["total"],0)
    def test_summarize_sorted(self):
        rows=[Assessment("z","postgresql","warning","a"),Assessment("a","postgresql","healthy","b")]
        self.assertEqual(summarize(rows,ThreadMetrics(),1)["results"][0]["service"],"a")
    def test_summarize_invalid(self):
        with self.assertRaises(CapstoneError):
            summarize([Assessment("a","postgresql","bad","x")],ThreadMetrics(),0)
    def test_fixture(self): self.assertEqual(len(fixtures()),3)
    def test_main_invalid(self): self.assertEqual(main(["--workers","0"]),3)

class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty(self): self.assertEqual((await pipeline([]))["total"],0)
    async def test_bad_workers(self):
        with self.assertRaises(CapstoneError): await pipeline([],workers=0)
    async def test_many_workers(self):
        with self.assertRaises(CapstoneError): await pipeline([],workers=5)
    async def test_bool_workers(self):
        with self.assertRaises(CapstoneError): await pipeline([],workers=True)
    async def test_bad_queue(self):
        with self.assertRaises(CapstoneError): await pipeline([],queue_size=0)
    async def test_big_queue(self):
        with self.assertRaises(CapstoneError): await pipeline([],queue_size=17)
    async def test_bool_queue(self):
        with self.assertRaises(CapstoneError): await pipeline([],queue_size=True)
    async def test_bad_timeout(self):
        with self.assertRaises(CapstoneError): await pipeline([],timeout=0)
    async def test_nan_timeout(self):
        with self.assertRaises(CapstoneError): await pipeline([],timeout=float("nan"))
    async def test_bool_timeout(self):
        with self.assertRaises(CapstoneError): await pipeline([],timeout=True)
    async def test_many_items(self):
        with self.assertRaises(CapstoneError): await pipeline([PG]*41)
    async def test_duplicate(self):
        with self.assertRaises(CapstoneError): await pipeline([PG,PG])
    async def test_invalid_input(self):
        with self.assertRaises(CapstoneError): await pipeline([{"bad":1}])
    async def test_end_to_end(self):
        r=await pipeline(fixtures())
        self.assertEqual(r["counts"],{"healthy":0,"warning":1,"critical":2})
    async def test_bounded_queue(self):
        r=await pipeline(fixtures(),workers=1,queue_size=1)
        self.assertLessEqual(r["peak_queue"],1)
    async def test_thread_counter(self):
        r=await pipeline(fixtures())
        self.assertEqual(r["thread_metrics"],{"reads":3,"failures":0})
    async def test_ordering(self):
        r=await pipeline(fixtures())
        self.assertEqual([x["engine"] for x in r["results"]],["elasticsearch","kafka","postgresql"])
    async def test_determinism(self):
        a=await pipeline(fixtures(),workers=1)
        b=await pipeline(fixtures(),workers=3)
        self.assertEqual(a["results"],b["results"])
    async def test_no_secrets(self):
        self.assertNotIn("password",json.dumps(await pipeline(fixtures())))
    async def test_no_live_io(self):
        self.assertTrue((await pipeline(fixtures()))["dry_run"])

if __name__ == "__main__":
    unittest.main()

```

## 3. Execute
Run from saved Python files, not an interactive notebook, so `spawn` workers can import the module.

Linux/macOS/WSL:
```bash
python3 --version  # Python 3.11+
python3 -m py_compile capstone_ops.py test_capstone_ops.py
python3 -m unittest -v test_capstone_ops.py
python3 capstone_ops.py --workers 2 --queue-size 2 --timeout 15
```

Windows PowerShell:
```powershell
py -3 -m py_compile capstone_ops.py test_capstone_ops.py
py -3 -m unittest -v test_capstone_ops.py
py -3 capstone_ops.py --workers 2 --queue-size 2 --timeout 15
```

Expected synthetic result: 3 readings; 0 healthy, 1 warning, 2 critical; thread_metrics.reads=3 and failures=0. `peak_queue` is at most the configured queue size. Exit code zero indicates the offline pipeline succeeded, not that production infrastructure is healthy.

## 4. Incident simulations
1. Run the real spawn-pool integration tests.
2. Run 1,000 thread-safe counter updates and verify no lost increments.
3. Compare output with one and three workers; sorted results must match.
4. Set queue size one and confirm peak depth is at most one.
5. Inject an invalid event and verify validation fails before pool creation.
6. Submit duplicate engine/service pairs and verify rejection.
7. Exceed the 40-event, 4-worker or 16-slot limits.
8. Inject NaN, Infinity, booleans, negative values and invalid metric units.
9. In a disposable copy, remove `task_done` and observe that `queue.join` cannot complete.
10. In a disposable copy, force a CPU worker failure and inspect TaskGroup ExceptionGroup.
11. Use a tiny timeout and observe the difference between cooperative cancellation and executor shutdown; avoid treating it as a hard kill.
12. Record memory and CPU consumption under container limits and tune process count.
13. Verify no credentials, live network connections or infrastructure mutations.
14. Roll back to a previous implementation and replay deterministic checksums.

## 5. Operational runbooks
**Queue saturation:** throttle producer, inspect downstream latency and queue wait time, replay idempotently.

**Thread leak or race:** inspect worker stacks and shared state, enforce lock-protected counters and driver timeouts.

**Broken process pool:** stop submissions, inspect crashes and memory limits, replace the pool and rerun fixtures.

**Timeout:** apply per-adapter I/O timeouts and a supervisor for hard process deadlines; do not assume executor cancellation kills work.

**Rollback:** pin known-good implementation, restore worker and queue budgets, run acceptance suite and compare deterministic reports.

## 6. 100-point enterprise acceptance assessment
| Criterion | Points |
|---|---:|
| Syntax, automated tests and integration run | 25 |
| AsyncIO queue, TaskGroup and shutdown correctness | 20 |
| Thread synchronization and I/O isolation | 15 |
| Process isolation, pickling and deterministic CPU work | 15 |
| Cancellation, timeouts and failure simulations | 10 |
| Observability, safety and production runbooks | 15 |

**Pass:** 90/100, no failed safety tests, verified execution on Python 3.11+, and reviewed runbooks. Publication alone does not establish a passing suite.
