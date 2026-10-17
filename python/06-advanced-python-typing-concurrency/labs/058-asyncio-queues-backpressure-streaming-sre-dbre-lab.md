# Chapter 058 — AsyncIO Queues, Backpressure and Streaming SRE/DBRE Lab

**Python 3.11+ | Standard library | Offline synthetic telemetry**

## Lab layout
```text
ch058/
  async_queue_ops.py
  test_async_queue_ops.py
```

## 1. Complete source: async_queue_ops.py

```python
"""Chapter 058: offline bounded async telemetry pipeline. Python 3.11+."""
from __future__ import annotations
import argparse
import asyncio
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
MAX_EVENTS = 100
MAX_WORKERS = 8
MAX_QUEUE = 32
SENTINEL = object()

class PipelineError(ValueError):
    pass

@dataclass(frozen=True)
class Event:
    service: str
    engine: str
    value: float
    severity: str

@dataclass
class Counters:
    produced: int = 0
    processed: int = 0
    peak_queue: int = 0

def validate(raw: object) -> Event:
    if not isinstance(raw, dict) or set(raw) != {"service", "engine", "metric", "unit", "value"}:
        raise PipelineError("invalid event schema")
    service, engine = raw["service"], raw["engine"]
    if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise PipelineError("invalid service")
    if not isinstance(engine, str) or engine not in POLICY:
        raise PipelineError("invalid engine")
    metric, unit, warn, critical = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise PipelineError("metric/unit mismatch")
    value = raw["value"]
    if type(value) not in (int, float):
        raise PipelineError("numeric value required")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise PipelineError("invalid value") from exc
    if not math.isfinite(number) or number < 0:
        raise PipelineError("nonfinite or negative value")
    severity = "critical" if number >= critical else "warning" if number >= warn else "healthy"
    return Event(service, engine, number, severity)

async def producer(raw_events: list[object], queue: asyncio.Queue[object],
                   counters: Counters) -> None:
    for raw in raw_events:
        event = validate(raw)
        await queue.put(event)  # backpressure when bounded queue is full
        counters.produced += 1
        counters.peak_queue = max(counters.peak_queue, queue.qsize())

async def consumer(queue: asyncio.Queue[object], output: list[Event],
                   counters: Counters, delay: float) -> None:
    while True:
        item = await queue.get()
        try:
            if item is SENTINEL:
                return
            if not isinstance(item, Event):
                raise PipelineError("unexpected queue payload")
            if delay:
                await asyncio.sleep(delay)
            output.append(item)
            counters.processed += 1
        finally:
            queue.task_done()

def summarize(events: list[Event], counters: Counters) -> dict[str, object]:
    counts = {"healthy": 0, "warning": 0, "critical": 0}
    for event in events:
        counts[event.severity] += 1
    return {
        "schema_version": 1, "dry_run": True, "total": len(events),
        "counts": counts,
        "queue": {"produced": counters.produced, "processed": counters.processed,
                  "peak_depth": counters.peak_queue},
        "results": [
            {"service": event.service, "engine": event.engine,
             "severity": event.severity, "value": event.value}
            for event in sorted(events, key=lambda e: (e.engine, e.service))
        ],
    }

async def pipeline(raw_events: list[object], *, workers: int = 3,
                   queue_size: int = 4, timeout: float = 2.0,
                   consumer_delay: float = 0.0) -> dict[str, object]:
    if type(workers) is not int or not 1 <= workers <= MAX_WORKERS:
        raise PipelineError("workers must be 1..8")
    if type(queue_size) is not int or not 1 <= queue_size <= MAX_QUEUE:
        raise PipelineError("queue_size must be 1..32")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise PipelineError("timeout must be finite in (0,30]")
    if type(consumer_delay) not in (int, float) or not math.isfinite(consumer_delay) or not 0 <= consumer_delay <= 0.1:
        raise PipelineError("consumer_delay must be in [0,0.1]")
    if len(raw_events) > MAX_EVENTS:
        raise PipelineError("too many events")
    queue: asyncio.Queue[object] = asyncio.Queue(maxsize=queue_size)
    counters = Counters()
    output: list[Event] = []
    # A TaskGroup cancels siblings and waits for cleanup if validation/worker fails.
    async with asyncio.timeout(timeout):
        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(consumer(queue, output, counters, consumer_delay))
                     for _ in range(workers)]
            await producer(raw_events, queue, counters)
            # All real items have been enqueued. Send one shutdown token per worker.
            for _ in tasks:
                await queue.put(SENTINEL)
            # Every successful get, including shutdown tokens, calls task_done.
            await queue.join()
        # TaskGroup ensures all workers have exited before report publication.
    if counters.produced != counters.processed or len(output) != counters.processed:
        raise PipelineError("incomplete processing")
    return summarize(output, counters)

def fixtures() -> list[dict[str, object]]:
    return [
        {"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45},
        {"service":"es-search","engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":650},
        {"service":"kafka-worker","engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000},
    ]

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline bounded asyncio pipeline")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--queue-size", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(pipeline(fixtures(), workers=args.workers,
                                      queue_size=args.queue_size, timeout=args.timeout))
    except (PipelineError, TimeoutError, ExceptionGroup):
        print("pipeline failed: sanitized operational error", file=sys.stderr)
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. Complete tests: test_async_queue_ops.py

```python
"""Chapter 058 unittest suite; Python 3.11+."""
import asyncio
import json
import unittest
from async_queue_ops import Event, Counters, PipelineError, SENTINEL, validate, producer, consumer, summarize, pipeline, fixtures, main

PG={"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45}

class ValidationTests(unittest.TestCase):
    def bad(self, **changes):
        with self.assertRaises(PipelineError): validate({**PG,**changes})
    def test_valid(self): self.assertEqual(validate(PG).severity,"warning")
    def test_healthy(self): self.assertEqual(validate({**PG,"value":0}).severity,"healthy")
    def test_critical(self): self.assertEqual(validate({**PG,"value":120}).severity,"critical")
    def test_engine(self): self.bad(engine="mysql")
    def test_metric(self): self.bad(metric="unknown")
    def test_unit(self): self.bad(unit="ms")
    def test_service(self): self.bad(service="=cmd")
    def test_unicode(self): self.bad(service="東京")
    def test_bool(self): self.bad(value=True)
    def test_string(self): self.bad(value="45")
    def test_negative(self): self.bad(value=-1)
    def test_nan(self): self.bad(value=float("nan"))
    def test_inf(self): self.bad(value=float("inf"))
    def test_extra(self): self.bad(password="secret")
    def test_missing(self):
        raw=dict(PG); del raw["unit"]
        with self.assertRaises(PipelineError): validate(raw)
    def test_nonobject(self):
        with self.assertRaises(PipelineError): validate([])
    def test_summary(self):
        r=summarize([validate(PG)],Counters(1,1,1))
        self.assertEqual(r["counts"]["warning"],1)
    def test_summary_empty(self): self.assertEqual(summarize([],Counters())["total"],0)
    def test_fixture(self): self.assertEqual(len(fixtures()),3)
    def test_main(self): self.assertEqual(main([]),0)
    def test_main_bad(self): self.assertEqual(main(["--queue-size","0"]),3)

class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline(self): self.assertEqual((await pipeline(fixtures()))["total"],3)
    async def test_counts(self):
        self.assertEqual((await pipeline(fixtures()))["counts"],{"healthy":0,"warning":1,"critical":2})
    async def test_queue_counters(self):
        self.assertEqual((await pipeline(fixtures()))["queue"]["processed"],3)
    async def test_queue_bounded(self):
        r=await pipeline(fixtures(),workers=1,queue_size=1,consumer_delay=0.001)
        self.assertLessEqual(r["queue"]["peak_depth"],1)
    async def test_one_worker(self): self.assertEqual((await pipeline(fixtures(),workers=1))["total"],3)
    async def test_eight_workers(self): self.assertEqual((await pipeline(fixtures(),workers=8))["total"],3)
    async def test_empty(self): self.assertEqual((await pipeline([]))["total"],0)
    async def test_sorted(self):
        r=await pipeline(fixtures())
        self.assertEqual([x["engine"] for x in r["results"]],["elasticsearch","kafka","postgresql"])
    async def test_deterministic(self):
        a=await pipeline(fixtures(),workers=1)
        b=await pipeline(fixtures(),workers=8)
        self.assertEqual(a["results"],b["results"])
    async def test_bad_workers(self):
        with self.assertRaises(PipelineError): await pipeline([],workers=0)
    async def test_too_many_workers(self):
        with self.assertRaises(PipelineError): await pipeline([],workers=9)
    async def test_bool_workers(self):
        with self.assertRaises(PipelineError): await pipeline([],workers=True)
    async def test_bad_queue(self):
        with self.assertRaises(PipelineError): await pipeline([],queue_size=0)
    async def test_big_queue(self):
        with self.assertRaises(PipelineError): await pipeline([],queue_size=33)
    async def test_bool_queue(self):
        with self.assertRaises(PipelineError): await pipeline([],queue_size=True)
    async def test_zero_timeout(self):
        with self.assertRaises(PipelineError): await pipeline([],timeout=0)
    async def test_nan_timeout(self):
        with self.assertRaises(PipelineError): await pipeline([],timeout=float("nan"))
    async def test_bool_timeout(self):
        with self.assertRaises(PipelineError): await pipeline([],timeout=True)
    async def test_big_timeout(self):
        with self.assertRaises(PipelineError): await pipeline([],timeout=31)
    async def test_bad_delay(self):
        with self.assertRaises(PipelineError): await pipeline([],consumer_delay=-1)
    async def test_big_delay(self):
        with self.assertRaises(PipelineError): await pipeline([],consumer_delay=1)
    async def test_many(self):
        with self.assertRaises(PipelineError): await pipeline([PG]*101)
    async def test_timeout(self):
        with self.assertRaises(TimeoutError):
            await pipeline(fixtures(),workers=1,queue_size=1,timeout=0.001,consumer_delay=0.1)
    async def test_bad_event_group(self):
        with self.assertRaises(ExceptionGroup): await pipeline([{"x":1}])
    async def test_bad_event_no_report(self):
        with self.assertRaises(ExceptionGroup): await pipeline([PG,{"x":1}])
    async def test_queue_join(self):
        q=asyncio.Queue(maxsize=1)
        c=Counters()
        out=[]
        task=asyncio.create_task(consumer(q,out,c,0))
        await q.put(validate(PG))
        await q.put(SENTINEL)
        await asyncio.wait_for(q.join(),1)
        await task
        self.assertEqual(c.processed,1)
    async def test_consumer_failure_ack(self):
        q=asyncio.Queue()
        await q.put("invalid")
        with self.assertRaises(PipelineError): await consumer(q,[],Counters(),0)
        await asyncio.wait_for(q.join(),1)
    async def test_producer_backpressure(self):
        q=asyncio.Queue(maxsize=1)
        c=Counters()
        t=asyncio.create_task(producer([PG,PG],q,c))
        await asyncio.sleep(0)
        self.assertFalse(t.done())
        self.assertEqual(q.qsize(),1)
        q.get_nowait(); q.task_done()
        await asyncio.wait_for(t,1)
        self.assertEqual(c.produced,2)
        q.get_nowait(); q.task_done()
        await q.join()
    async def test_cancel_producer(self):
        q=asyncio.Queue(maxsize=1)
        t=asyncio.create_task(producer([PG,PG],q,Counters()))
        await asyncio.sleep(0)
        t.cancel()
        with self.assertRaises(asyncio.CancelledError): await t
    async def test_no_secrets(self):
        self.assertNotIn("password",json.dumps(await pipeline(fixtures())))
    async def test_graceful_no_pending(self):
        await pipeline(fixtures())
        self.assertEqual(len([t for t in asyncio.all_tasks() if t is not asyncio.current_task()]),0)

if __name__=="__main__":
    unittest.main()

```

## 3. Execute
Linux/macOS/WSL:
```bash
python3 --version
python3 -m py_compile async_queue_ops.py test_async_queue_ops.py
python3 -m unittest -v test_async_queue_ops.py
python3 async_queue_ops.py --workers 3 --queue-size 4 --timeout 2
```

Windows PowerShell:
```powershell
py -3 --version
py -3 -m py_compile async_queue_ops.py test_async_queue_ops.py
py -3 -m unittest -v test_async_queue_ops.py
py -3 async_queue_ops.py --workers 3 --queue-size 4 --timeout 2
```

Expected synthetic output: 3 events, 0 healthy, 1 warning, 2 critical; queue produced=3 and processed=3. Exit code 0 means offline processing succeeded, not that production services are healthy.

## 4. Failure injection and verification
1. Set queue size to one, consumer count to one, and introduce 1 ms consumer delay; verify peak queue depth never exceeds one.
2. Block the producer behind a full queue, then drain one item to release it.
3. Omit `task_done` in a disposable training script and demonstrate that `join` hangs.
4. Double-call `task_done` in a disposable script and observe `ValueError`.
5. Use an invalid queue payload and verify acknowledgement in `finally`.
6. Inject a malformed event and verify `ExceptionGroup` propagates rather than producing a partial report.
7. Force a 1 ms overall deadline against a 100 ms consumer delay.
8. Cancel a blocked producer and confirm cancellation propagation.
9. Compare output ordering with one and eight workers.
10. Attempt to submit more than 100 events, 8 workers or queue size 32.
11. Inject boolean, NaN, Infinity, negative and wrong-unit metrics.
12. Confirm that no workers remain pending after normal graceful shutdown.

## 5. Troubleshooting and runbooks
**Producer blocked:** inspect queue depth, downstream rate and consumer health; reduce input rate and replay safely.

**Join never returns:** trace each successful `get` and exactly one matching `task_done`.

**Cancellation:** use TaskGroup ownership and allow cancellation to propagate through await points.

**Invalid telemetry:** reject and quarantine input; do not publish partial healthy reports.

**Rollback:** restore prior bounded configuration and rerun the full test suite before enabling scheduled polling.

## 6. 100-point assessment
| Criterion | Points |
|---|---:|
| Syntax and automated tests | 25 |
| Producer–consumer design | 20 |
| Backpressure and queue accounting | 20 |
| Cancellation and graceful shutdown | 15 |
| Failure simulations | 10 |
| Troubleshooting and runbooks | 10 |

Target **90/100** with all safety tests passing. Publishing tests is not proof of successful execution.
