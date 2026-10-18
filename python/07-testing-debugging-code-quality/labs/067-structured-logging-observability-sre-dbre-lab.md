# Chapter 067 — Structured Logging, Diagnostics and Observability SRE/DBRE Lab

**Python 3.11+ | Standard library | Offline and non-destructive**

## Layout
```text
ch067/
  observability_ops.py
  test_observability_ops.py
```

## 1. Complete application: observability_ops.py
```python
"""Offline structured observability: no network calls or production credentials."""
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import math
import re
import time
from typing import Iterator, Mapping

_CORRELATION: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_TRACE: ContextVar[str | None] = ContextVar("trace_id", default=None)
_SPAN: ContextVar[str | None] = ContextVar("span_id", default=None)
SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
SPAN_ID = re.compile(r"^[0-9a-f]{16}$")
POLICY = {"postgresql": ("replication_lag_seconds", 30, 120),
          "elasticsearch": ("search_latency_ms", 200, 500),
          "kafka": ("consumer_lag_messages", 1000, 10000)}
SENSITIVE = re.compile(r"(?i)(password|passwd|token|secret|api[_-]?key|authorization|credential|cookie)")
MAX_MESSAGE = 240

class InvalidTelemetry(ValueError):
    pass

def scrub(value: object, key: str = "") -> object:
    """Allowlisted serialization with defense-in-depth recursive redaction."""
    if SENSITIVE.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k)[:64]: scrub(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub(item) for item in value[:30]]
    if isinstance(value, str):
        # Free-text values are not trustworthy: never log raw user payloads.
        return value[:MAX_MESSAGE] if key in {"event", "severity", "engine", "service"} else "[OMITTED]"
    if type(value) in (int, float) and math.isfinite(float(value)):
        return value
    if isinstance(value, bool) or value is None:
        return value
    return "[OMITTED]"

@contextmanager
def context(correlation_id: str, trace_id: str | None = None,
            span_id: str | None = None) -> Iterator[None]:
    if not isinstance(correlation_id, str) or not SAFE_ID.fullmatch(correlation_id):
        raise InvalidTelemetry("invalid correlation ID")
    if trace_id is not None and (not isinstance(trace_id, str) or not TRACE_ID.fullmatch(trace_id)):
        raise InvalidTelemetry("invalid trace ID")
    if span_id is not None and (not isinstance(span_id, str) or not SPAN_ID.fullmatch(span_id)):
        raise InvalidTelemetry("invalid span ID")
    if (trace_id is None) != (span_id is None):
        raise InvalidTelemetry("trace and span IDs must be paired")
    c = _CORRELATION.set(correlation_id)
    t = _TRACE.set(trace_id)
    s = _SPAN.set(span_id)
    try:
        yield
    finally:
        _SPAN.reset(s)
        _TRACE.reset(t)
        _CORRELATION.reset(c)

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Do not call record.getMessage(): interpolated args can leak secrets.
        event = record.msg if isinstance(record.msg, str) else "non_string_event"
        if not SAFE_ID.fullmatch(event):
            event = "unrecognized_event"
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": event,
            "correlation_id": _CORRELATION.get(),
            "trace_id": _TRACE.get(),
            "span_id": _SPAN.get(),
        }
        fields = getattr(record, "safe_fields", {})
        if isinstance(fields, dict):
            payload["fields"] = scrub(fields)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)

def make_logger(stream) -> logging.Logger:
    # Fresh nonpropagating logger prevents duplicate root-handler emissions.
    logger = logging.Logger("ch067.synthetic", level=logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger

@dataclass(frozen=True)
class Reading:
    engine: str
    service: str
    value: float

def parse(raw: object) -> Reading:
    if not isinstance(raw, dict) or set(raw) != {"engine", "service", "metric", "value"}:
        raise InvalidTelemetry("invalid schema")
    engine, service, value = raw["engine"], raw["service"], raw["value"]
    if not isinstance(engine, str) or engine not in POLICY:
        raise InvalidTelemetry("invalid engine")
    if not isinstance(service, str) or not SAFE_ID.fullmatch(service):
        raise InvalidTelemetry("invalid service")
    if raw["metric"] != POLICY[engine][0]:
        raise InvalidTelemetry("invalid metric")
    if type(value) not in (int, float):
        raise InvalidTelemetry("invalid numeric type")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise InvalidTelemetry("invalid numeric value") from exc
    if not math.isfinite(number) or number < 0:
        raise InvalidTelemetry("invalid numeric value")
    return Reading(engine, service, number)

def severity(reading: Reading) -> str:
    if reading.engine not in POLICY or not math.isfinite(reading.value) or reading.value < 0:
        raise InvalidTelemetry("invalid reading")
    _, warning, critical = POLICY[reading.engine]
    return "critical" if reading.value >= critical else "warning" if reading.value >= warning else "healthy"

class Metrics:
    """In-memory test double. Labels are bounded to avoid cardinality explosions."""
    def __init__(self):
        self.counters: dict[tuple[str, str], int] = {}
        self.duration_ns: list[int] = []
    def record(self, engine: str, level: str, duration_ns: int) -> None:
        if engine not in POLICY or level not in ("healthy", "warning", "critical"):
            raise InvalidTelemetry("invalid metric labels")
        if type(duration_ns) is not int or duration_ns < 0:
            raise InvalidTelemetry("invalid duration")
        key = (engine, level)
        self.counters[key] = self.counters.get(key, 0) + 1
        self.duration_ns.append(duration_ns)

@dataclass(frozen=True)
class Span:
    name: str
    trace_id: str
    span_id: str
    duration_ns: int
    status: str

class TraceSink:
    def __init__(self):
        self.spans: list[Span] = []
    def emit(self, span: Span) -> None:
        if span.duration_ns < 0 or span.status not in ("ok", "error"):
            raise InvalidTelemetry("invalid span")
        self.spans.append(span)

def process(raw: object, logger: logging.Logger, metrics: Metrics,
            traces: TraceSink, clock_ns=time.perf_counter_ns) -> dict[str, object]:
    started = clock_ns()
    trace_id = _TRACE.get()
    span_id = _SPAN.get()
    engine = None
    status = "error"
    try:
        reading = parse(raw)
        engine = reading.engine
        level = severity(reading)
        logger.info("telemetry_classified", extra={"safe_fields":{
            "engine":reading.engine, "service":reading.service,
            "severity":level, "value":reading.value}})
        status = "ok"
        return {"engine":reading.engine, "service":reading.service,
                "severity":level, "dry_run":True}
    except InvalidTelemetry:
        logger.warning("telemetry_rejected", extra={"safe_fields":{"reason":"invalid_input"}})
        raise
    finally:
        elapsed = max(0, clock_ns() - started)
        if engine is not None and status == "ok":
            metrics.record(engine, level, elapsed)
        if trace_id is not None and span_id is not None:
            traces.emit(Span("telemetry.process", trace_id, span_id, elapsed, status))

def samples() -> list[dict[str, object]]:
    return [
        {"engine":"postgresql","service":"pg-replica","metric":"replication_lag_seconds","value":45},
        {"engine":"elasticsearch","service":"es-search","metric":"search_latency_ms","value":650},
        {"engine":"kafka","service":"kafka-worker","metric":"consumer_lag_messages","value":10000},
    ]

def main() -> int:
    import sys
    logger = make_logger(sys.stdout)
    metrics, traces = Metrics(), TraceSink()
    with context("synthetic-run", "1" * 32, "2" * 16):
        for item in samples():
            process(item, logger, metrics, traces)
    print(json.dumps({"dry_run":True, "metrics":len(metrics.duration_ns),
                      "spans":len(traces.spans)}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. Complete automated tests: test_observability_ops.py
```python
"""Deterministic unittest observability acceptance tests (no external dependencies)."""
import asyncio
import io
import json
import logging
import unittest
from unittest.mock import patch
import observability_ops as o

PG={"engine":"postgresql","service":"pg-replica","metric":"replication_lag_seconds","value":45}

class ObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.stream=io.StringIO()
        self.logger=o.make_logger(self.stream)
        self.metrics=o.Metrics()
        self.traces=o.TraceSink()
        self.ticks=iter((100,125))
    def process(self, raw=PG):
        return o.process(raw,self.logger,self.metrics,self.traces,lambda:next(self.ticks))
    def logs(self):
        return [json.loads(x) for x in self.stream.getvalue().splitlines()]
    def test_json_fields(self):
        with o.context("request-1","a"*32,"b"*16):
            result=self.process()
        self.assertEqual(result["severity"],"warning")
        entry=self.logs()[0]
        self.assertEqual(entry["event"],"telemetry_classified")
        self.assertEqual(entry["correlation_id"],"request-1")
        self.assertEqual(entry["trace_id"],"a"*32)
        self.assertEqual(entry["span_id"],"b"*16)
        self.assertTrue(entry["timestamp"].endswith("+00:00"))
    def test_counter_duration_and_span(self):
        with o.context("request-1","a"*32,"b"*16):
            self.process()
        self.assertEqual(self.metrics.counters[("postgresql","warning")],1)
        self.assertEqual(self.metrics.duration_ns,[25])
        self.assertEqual(self.traces.spans[0].duration_ns,25)
        self.assertEqual(self.traces.spans[0].status,"ok")
    def test_error_log_and_span(self):
        with o.context("request-2","a"*32,"b"*16):
            with self.assertRaises(o.InvalidTelemetry):
                self.process({**PG,"value":float("nan")})
        self.assertEqual(self.logs()[0]["event"],"telemetry_rejected")
        self.assertEqual(self.traces.spans[0].status,"error")
        self.assertEqual(self.metrics.counters,{})
    def test_context_reset(self):
        with o.context("request-1"):
            self.process()
        self.assertIsNone(o._CORRELATION.get())
        self.assertIsNone(self.logs()[-1]["trace_id"])
    def test_context_nested(self):
        with o.context("outer"):
            with o.context("inner"):
                self.process()
            self.assertEqual(o._CORRELATION.get(),"outer")
        self.assertIsNone(o._CORRELATION.get())
    def test_context_bad_ids(self):
        for bad in ("../secret", "", "a"*65):
            with self.assertRaises(o.InvalidTelemetry): 
                with o.context(bad): pass
        with self.assertRaises(o.InvalidTelemetry):
            with o.context("valid", "bad", "b"*16): pass
        with self.assertRaises(o.InvalidTelemetry):
            with o.context("valid", "a"*32): pass
    def test_redaction(self):
        self.logger.info("security_event",extra={"safe_fields":{
            "password":"abc123","token":"token-1","nested":{"api_key":"XYZ"},
            "authorization":"Bearer xyz","message":"password=abc123"}})
        rendered=self.stream.getvalue()
        for secret in ("abc123","token-1","XYZ","Bearer xyz"):
            self.assertNotIn(secret,rendered)
        self.assertIn("[REDACTED]",rendered)
    def test_unsafe_interpolation_not_emitted(self):
        self.logger.info("security_event %s","secret-value")
        self.assertNotIn("secret-value",self.stream.getvalue())
        self.assertEqual(self.logs()[0]["event"],"unrecognized_event")
    def test_duplicate_handler_prevention(self):
        self.assertFalse(self.logger.propagate)
        self.assertEqual(len(self.logger.handlers),1)
    def test_invalid_schema(self):
        with self.assertRaises(o.InvalidTelemetry): o.parse({"invalid":1})
    def test_invalid_metric(self):
        with self.assertRaises(o.InvalidTelemetry): o.parse({**PG,"metric":"wrong"})
    def test_invalid_engine(self):
        with self.assertRaises(o.InvalidTelemetry): o.parse({**PG,"engine":"mysql"})
    def test_invalid_service(self):
        with self.assertRaises(o.InvalidTelemetry): o.parse({**PG,"service":"=cmd"})
    def test_boolean_rejected(self):
        with self.assertRaises(o.InvalidTelemetry): o.parse({**PG,"value":True})
    def test_negative_rejected(self):
        with self.assertRaises(o.InvalidTelemetry): o.parse({**PG,"value":-1})
    def test_thresholds(self):
        for engine,(metric,warn,critical) in o.POLICY.items():
            for value,expected in ((0,"healthy"),(warn,"warning"),(critical,"critical")):
                self.assertEqual(o.severity(o.parse({"engine":engine,"service":"node",
                    "metric":metric,"value":value})),expected)
    def test_label_cardinality(self):
        with self.assertRaises(o.InvalidTelemetry):
            self.metrics.record("unbounded-user-id","healthy",1)
    def test_bad_duration(self):
        with self.assertRaises(o.InvalidTelemetry):
            self.metrics.record("postgresql","warning",-1)
    def test_bad_span(self):
        with self.assertRaises(o.InvalidTelemetry):
            self.traces.emit(o.Span("x","a"*32,"b"*16,-1,"ok"))
    def test_clock_negative_clamped(self):
        self.ticks=iter((200,100))
        self.process()
        self.assertEqual(self.metrics.duration_ns,[0])
    def test_context_async_propagation(self):
        async def worker():
            return o._CORRELATION.get()
        async def run():
            with o.context("async-request"):
                return await asyncio.create_task(worker())
        self.assertEqual(asyncio.run(run()),"async-request")
    def test_thread_context_explicit_copy(self):
        import concurrent.futures
        from contextvars import copy_context
        with o.context("thread-request"):
            ctx=copy_context()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                result=pool.submit(ctx.run,o._CORRELATION.get).result(timeout=5)
        self.assertEqual(result,"thread-request")
    def test_no_secret_in_failure(self):
        self.ticks=iter((100,125))
        with self.assertRaises(o.InvalidTelemetry):
            self.process({**PG,"password":"SECRET"})
        self.assertNotIn("SECRET",self.stream.getvalue())
    def test_main(self):
        with patch("sys.stdout",new_callable=io.StringIO) as out:
            self.assertEqual(o.main(),0)
        lines=out.getvalue().splitlines()
        self.assertEqual(len(lines),4)
        self.assertEqual(json.loads(lines[-1])["spans"],3)

if __name__=="__main__":
    unittest.main()

```

## 3. Execute
Linux/macOS/WSL:
```bash
python3 -m py_compile observability_ops.py test_observability_ops.py
python3 -m unittest -v test_observability_ops.py
python3 observability_ops.py
```

Windows PowerShell: replace `python3` with `py -3`.

Expected offline summary: three synthetic readings, three metric recordings, three spans; warning for PostgreSQL, critical for Elasticsearch and Kafka. Actual test pass counts require execution.

## 4. Logging handlers and correlation lab
1. Observe JSON-lines with `timestamp`, `level`, `event`, `correlation_id`, `trace_id` and `span_id`.
2. Validate `StreamHandler` and `JsonFormatter` with an `io.StringIO` sink.
3. Confirm `propagate=False` prevents duplicate root-handler emission.
4. Run nested `context()` blocks; verify token resets after exit.
5. Compare async `create_task` propagation with explicit `copy_context` for thread pools.
6. Inject `password`, `token`, `api_key` and `authorization` canaries; confirm no secret bytes in emitted JSON.

## 5. Metrics and tracing lab
7. Use an injected nanosecond clock for deterministic duration assertions.
8. Verify exactly one counter increment and span per successful request.
9. Verify a rejected record produces an error span but no success counter.
10. Reject unbounded metric labels and negative durations.
11. Test correlation and trace IDs as separate concepts.
12. Verify that trace data is synthetic and no exporter or network access occurs.

## 6. Incident simulations
- **Secret leak attempt:** call `logger.info("security_event %s", "secret-value")`; verify the unsafe interpolation is never emitted.
- **Context leak:** remove `ContextVar.reset` in a disposable copy and observe nested-context regression tests.
- **Duplicate logging:** attach a second handler in a disposable copy; demonstrate duplicate event count.
- **Metric cardinality:** attempt an unapproved engine label and observe rejection.
- **Trace gap:** omit span emission in a disposable copy; observe span-count test failure.
- **Invalid telemetry:** inject NaN, boolean, negative and unknown-engine inputs.
- **Clock skew:** inject decreasing monotonic timestamps and observe nonnegative clamping.

## 7. CI quality gate example
This tutorial stores Python source in Markdown; materialize both source blocks as files before enabling a CI workflow:
```yaml
name: chapter-067-observability
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Materialize source
        run: |
          echo 'Extract observability_ops.py and test_observability_ops.py from the Chapter 067 lab'
          exit 1
      - name: Validate
        run: |
          python -m py_compile observability_ops.py test_observability_ops.py
          python -m unittest -v test_observability_ops.py
```
The workflow intentionally fails closed until reviewed source files are present; it is **not** ready to enable unchanged.

## 8. Production runbooks
**Sensitive logging:** restrict log access, inspect canary exposure, rotate affected credentials, patch allowlist and rerun tests.

**Missing correlation:** inspect middleware, async task boundaries and thread context injection, replay tests.

**Telemetry saturation:** inspect queue/collector health and dropped-event counters, reduce cardinality and sampling.

**Trace mismatch:** validate trace/span IDs and exporter propagation, verify sampling and clock semantics.

**Rollback:** restore known-good instrumentation, rerun tests, verify dashboards and alerts, record change approval.

## 9. 100-point assessment
| Category | Points |
|---|---:|
| Structured JSON logging and handlers | 20 |
| Correlation/context propagation | 20 |
| Redaction and sensitive-data protection | 20 |
| Metric invariants and cardinality | 15 |
| Trace/span testing and clock injection | 15 |
| Incident simulations and production runbooks | 10 |

**Pass:** 90/100, all security tests passing, no production connections and verified test execution. Publication alone does not prove tests were run.
