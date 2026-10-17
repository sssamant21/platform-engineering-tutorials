# Chapter 053 — Decorators, Closures and Instrumentation SRE/DBRE Lab

**Python 3.10+ | Standard library | Offline and read-only**

## Architecture and file layout

```text
ch053/
  decorator_ops.py
  test_decorator_ops.py
```

This lab does not access real PostgreSQL, Elasticsearch, Kafka or cloud infrastructure. No external credentials are needed.

## 1. decorator_ops.py

```python
"""Chapter 053: safe decorators and operational instrumentation, Python 3.10+."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from functools import wraps
import json
import math
import time
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

class OperationalError(Exception):
    """Base class for expected operational failures."""

class TransientReadError(OperationalError):
    """A retryable failure on an explicitly read-only operation."""

class PermanentReadError(OperationalError):
    """A non-retryable read failure."""

@dataclass
class Metrics:
    calls: Counter[str] = field(default_factory=Counter)
    failures: Counter[str] = field(default_factory=Counter)
    durations_ms: dict[str, list[float]] = field(default_factory=dict)
    attempts: Counter[str] = field(default_factory=Counter)

    def record(self, operation: str, elapsed_ms: float, failed: bool) -> None:
        self.calls[operation] += 1
        self.durations_ms.setdefault(operation, []).append(elapsed_ms)
        if failed:
            self.failures[operation] += 1

    def snapshot(self) -> dict[str, object]:
        names = sorted(set(self.calls) | set(self.attempts))
        return {
            "schema_version": 1,
            "operations": {
                name: {
                    "calls": self.calls[name],
                    "failures": self.failures[name],
                    "attempts": self.attempts[name],
                    "duration_ms_total": round(sum(self.durations_ms.get(name, [])), 3),
                } for name in names
            },
        }

def valid_operation(name: str) -> str:
    if not isinstance(name, str) or not name or len(name) > 64:
        raise ValueError("invalid operation name")
    if not all(c.isascii() and (c.isalnum() or c in "_-") for c in name):
        raise ValueError("operation name must be safe ASCII")
    return name

def instrument(metrics: Metrics, name: str,
               clock: Callable[[], float] = time.perf_counter
               ) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Measure one logical invocation; never record arguments or return values."""
    operation = valid_operation(name)

    def decorate(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = clock()
            failed = False
            try:
                return fn(*args, **kwargs)
            except Exception:
                failed = True
                raise
            finally:
                elapsed = max(0.0, (clock() - start) * 1000.0)
                if not math.isfinite(elapsed):
                    elapsed = 0.0
                metrics.record(operation, elapsed, failed)
        return wrapper
    return decorate

def read_only_retry(metrics: Metrics, name: str, *,
                    max_attempts: int = 3,
                    base_delay: float = 0.01,
                    sleep: Callable[[float], None] = time.sleep
                    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry ONLY TransientReadError; caller must guarantee read-only semantics."""
    operation = valid_operation(name)
    if type(max_attempts) is not int or not 1 <= max_attempts <= 4:
        raise ValueError("max_attempts must be 1..4")
    if type(base_delay) not in (int, float) or not math.isfinite(base_delay) or not 0 <= base_delay <= 1:
        raise ValueError("base_delay must be finite in 0..1")

    def decorate(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for index in range(max_attempts):
                metrics.attempts[operation] += 1
                try:
                    return fn(*args, **kwargs)
                except TransientReadError:
                    if index + 1 == max_attempts:
                        raise
                    sleep(min(base_delay * (2 ** index), 2.0))
            raise AssertionError("unreachable")
        return wrapper
    return decorate

def compose_read_operation(metrics: Metrics, name: str, fn: Callable[P, R],
                           *, attempts: int = 3,
                           clock: Callable[[], float] = time.perf_counter,
                           sleep: Callable[[float], None] = time.sleep
                           ) -> Callable[P, R]:
    """One logical timed call, with attempts counted independently."""
    return instrument(metrics, name, clock)(
        read_only_retry(metrics, name, max_attempts=attempts, sleep=sleep)(fn)
    )

POLICY = {
    "postgresql": ("replication_lag", "seconds", 30.0, 120.0),
    "elasticsearch": ("search_latency", "milliseconds", 200.0, 500.0),
    "kafka": ("consumer_lag", "messages", 1000.0, 10000.0),
}

def classify(engine: str, metric: str, unit: str, value: object) -> str:
    if engine not in POLICY:
        raise ValueError("unknown engine")
    expected_metric, expected_unit, warning, critical = POLICY[engine]
    if metric != expected_metric or unit != expected_unit:
        raise ValueError("metric/unit mismatch")
    if type(value) not in (int, float):
        raise ValueError("value must be numeric, not boolean")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError("invalid number") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError("value must be finite and nonnegative")
    return "critical" if number >= critical else "warning" if number >= warning else "healthy"

def read_synthetic_events() -> list[dict[str, object]]:
    """Deterministic offline fixtures; no infrastructure calls or mutations."""
    return [
        {"service": "pg-replica", "engine": "postgresql",
         "metric": "replication_lag", "unit": "seconds", "value": 45},
        {"service": "es-search", "engine": "elasticsearch",
         "metric": "search_latency", "unit": "milliseconds", "value": 650},
        {"service": "kafka-worker", "engine": "kafka",
         "metric": "consumer_lag", "unit": "messages", "value": 10000},
    ]

def build_report(rows: list[dict[str, object]], metrics: Metrics) -> dict[str, object]:
    severities = {"healthy": 0, "warning": 0, "critical": 0}
    for row in rows:
        if set(row) != {"service", "engine", "metric", "unit", "value"}:
            raise ValueError("unexpected telemetry schema")
        service, engine, metric, unit = (
            row["service"], row["engine"], row["metric"], row["unit"]
        )
        if not all(isinstance(x, str) for x in (service, engine, metric, unit)):
            raise ValueError("invalid text field")
        if not isinstance(service, str) or not service or len(service) > 64:
            raise ValueError("invalid service")
        if not all(c.isascii() and (c.isalnum() or c in "_-") for c in service):
            raise ValueError("unsafe service name")
        severity = classify(engine, metric, unit, row["value"])
        severities[severity] += 1
    return {
        "schema_version": 1,
        "dry_run": True,
        "total": len(rows),
        "severities": severities,
        "instrumentation": metrics.snapshot(),
    }

def main() -> int:
    metrics = Metrics()
    read = compose_read_operation(metrics, "read_synthetic_telemetry",
                                  read_synthetic_events)
    try:
        rows = read()
        result = build_report(rows, metrics)
    except (OperationalError, ValueError):
        print("operation failed: sanitized operational error")
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. test_decorator_ops.py

```python
"""Unit tests for Chapter 053; no external services."""
import json
import math
import unittest
from collections import Counter
from unittest.mock import Mock

from decorator_ops import (
    Metrics, OperationalError, TransientReadError, PermanentReadError,
    valid_operation, instrument, read_only_retry, compose_read_operation,
    classify, read_synthetic_events, build_report, main,
)

class DecoratorTests(unittest.TestCase):
    def setUp(self):
        self.metrics = Metrics()

    def test_metrics_initially_empty(self):
        self.assertEqual(self.metrics.snapshot()["operations"], {})
    def test_metrics_record_call(self):
        self.metrics.record("read", 5.0, False)
        self.assertEqual(self.metrics.calls["read"], 1)
    def test_metrics_record_failure(self):
        self.metrics.record("read", 5.0, True)
        self.assertEqual(self.metrics.failures["read"], 1)
    def test_metrics_duration(self):
        self.metrics.record("read", 1.5, False)
        self.assertEqual(self.metrics.snapshot()["operations"]["read"]["duration_ms_total"], 1.5)
    def test_metrics_sorted(self):
        self.metrics.record("z", 0, False)
        self.metrics.record("a", 0, False)
        self.assertEqual(list(self.metrics.snapshot()["operations"]), ["a", "z"])
    def test_operation_valid(self):
        self.assertEqual(valid_operation("pg-read_1"), "pg-read_1")
    def test_operation_empty(self):
        with self.assertRaises(ValueError): valid_operation("")
    def test_operation_space(self):
        with self.assertRaises(ValueError): valid_operation("read events")
    def test_operation_unicode(self):
        with self.assertRaises(ValueError): valid_operation("read-東京")
    def test_operation_too_long(self):
        with self.assertRaises(ValueError): valid_operation("a"*65)
    def test_operation_type(self):
        with self.assertRaises(ValueError): valid_operation(12)
    def test_instrument_return(self):
        @instrument(self.metrics, "read", clock=lambda: 1.0)
        def read(): return 42
        self.assertEqual(read(), 42)
    def test_instrument_count(self):
        @instrument(self.metrics, "read", clock=lambda: 1.0)
        def read(): return 1
        read(); read()
        self.assertEqual(self.metrics.calls["read"], 2)
    def test_instrument_failure(self):
        @instrument(self.metrics, "read", clock=lambda: 1.0)
        def read(): raise PermanentReadError("private detail")
        with self.assertRaises(PermanentReadError): read()
        self.assertEqual(self.metrics.failures["read"], 1)
    def test_instrument_preserves_name(self):
        @instrument(self.metrics, "read")
        def original(): return 1
        self.assertEqual(original.__name__, "original")
    def test_instrument_preserves_doc(self):
        @instrument(self.metrics, "read")
        def original():
            """Safe doc."""
            return 1
        self.assertEqual(original.__doc__, "Safe doc.")
    def test_instrument_args(self):
        @instrument(self.metrics, "read")
        def add(a, b=0): return a+b
        self.assertEqual(add(2, b=3), 5)
    def test_instrument_duration(self):
        clock=Mock(side_effect=[1.0, 1.25])
        @instrument(self.metrics, "read", clock=clock)
        def read(): return None
        read()
        self.assertEqual(self.metrics.durations_ms["read"], [250.0])
    def test_instrument_clock_backward(self):
        clock=Mock(side_effect=[2.0, 1.0])
        @instrument(self.metrics, "read", clock=clock)
        def read(): return None
        read()
        self.assertEqual(self.metrics.durations_ms["read"], [0.0])
    def test_instrument_clock_nan(self):
        clock=Mock(side_effect=[1.0, float("nan")])
        @instrument(self.metrics, "read", clock=clock)
        def read(): return None
        read()
        self.assertEqual(self.metrics.durations_ms["read"], [0.0])
    def test_instrument_does_not_record_arguments(self):
        @instrument(self.metrics, "read")
        def read(secret): return len(secret)
        read("synthetic-secret")
        self.assertNotIn("synthetic-secret", json.dumps(self.metrics.snapshot()))
    def test_retry_success(self):
        @read_only_retry(self.metrics, "read", sleep=lambda _: None)
        def read(): return 42
        self.assertEqual(read(), 42)
    def test_retry_one_attempt(self):
        @read_only_retry(self.metrics, "read", sleep=lambda _: None)
        def read(): return 42
        read()
        self.assertEqual(self.metrics.attempts["read"], 1)
    def test_retry_transient_then_success(self):
        fn=Mock(side_effect=[TransientReadError("retry"), 42])
        wrapped=read_only_retry(self.metrics, "read", sleep=lambda _: None)(fn)
        self.assertEqual(wrapped(), 42)
        self.assertEqual(fn.call_count, 2)
    def test_retry_exhausted(self):
        fn=Mock(side_effect=TransientReadError("retry"))
        wrapped=read_only_retry(self.metrics, "read", max_attempts=3,
                                sleep=lambda _: None)(fn)
        with self.assertRaises(TransientReadError): wrapped()
        self.assertEqual(fn.call_count, 3)
    def test_retry_permanent_no_retry(self):
        fn=Mock(side_effect=PermanentReadError("stop"))
        wrapped=read_only_retry(self.metrics, "read", sleep=lambda _: None)(fn)
        with self.assertRaises(PermanentReadError): wrapped()
        self.assertEqual(fn.call_count, 1)
    def test_retry_unexpected_no_retry(self):
        fn=Mock(side_effect=RuntimeError("stop"))
        wrapped=read_only_retry(self.metrics, "read", sleep=lambda _: None)(fn)
        with self.assertRaises(RuntimeError): wrapped()
        self.assertEqual(fn.call_count, 1)
    def test_retry_delays(self):
        sleep=Mock()
        fn=Mock(side_effect=[TransientReadError(), TransientReadError(), 42])
        wrapped=read_only_retry(self.metrics, "read", base_delay=0.1,
                                sleep=sleep)(fn)
        self.assertEqual(wrapped(), 42)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.1, 0.2])
    def test_retry_max_one(self):
        fn=Mock(side_effect=TransientReadError())
        wrapped=read_only_retry(self.metrics, "read", max_attempts=1)(fn)
        with self.assertRaises(TransientReadError): wrapped()
        self.assertEqual(fn.call_count, 1)
    def test_retry_max_zero(self):
        with self.assertRaises(ValueError): read_only_retry(self.metrics, "read", max_attempts=0)
    def test_retry_max_five(self):
        with self.assertRaises(ValueError): read_only_retry(self.metrics, "read", max_attempts=5)
    def test_retry_max_bool(self):
        with self.assertRaises(ValueError): read_only_retry(self.metrics, "read", max_attempts=True)
    def test_retry_negative_delay(self):
        with self.assertRaises(ValueError): read_only_retry(self.metrics, "read", base_delay=-1)
    def test_retry_nan_delay(self):
        with self.assertRaises(ValueError): read_only_retry(self.metrics, "read", base_delay=float("nan"))
    def test_retry_bool_delay(self):
        with self.assertRaises(ValueError): read_only_retry(self.metrics, "read", base_delay=True)
    def test_retry_preserves_name(self):
        @read_only_retry(self.metrics, "read")
        def original(): return 1
        self.assertEqual(original.__name__, "original")
    def test_compose_success(self):
        wrapped=compose_read_operation(self.metrics, "read", lambda: 42,
                                       clock=lambda: 1.0, sleep=lambda _: None)
        self.assertEqual(wrapped(), 42)
        self.assertEqual(self.metrics.calls["read"], 1)
        self.assertEqual(self.metrics.attempts["read"], 1)
    def test_compose_retry_counts_logical_once(self):
        fn=Mock(side_effect=[TransientReadError(), 42])
        wrapped=compose_read_operation(self.metrics, "read", fn,
                                       clock=lambda: 1.0, sleep=lambda _: None)
        self.assertEqual(wrapped(), 42)
        self.assertEqual(self.metrics.calls["read"], 1)
        self.assertEqual(self.metrics.attempts["read"], 2)
    def test_compose_failure_once(self):
        fn=Mock(side_effect=PermanentReadError())
        wrapped=compose_read_operation(self.metrics, "read", fn,
                                       clock=lambda: 1.0, sleep=lambda _: None)
        with self.assertRaises(PermanentReadError): wrapped()
        self.assertEqual(self.metrics.failures["read"], 1)
    def test_pg_healthy(self):
        self.assertEqual(classify("postgresql","replication_lag","seconds",1),"healthy")
    def test_pg_warning(self):
        self.assertEqual(classify("postgresql","replication_lag","seconds",30),"warning")
    def test_pg_critical(self):
        self.assertEqual(classify("postgresql","replication_lag","seconds",120),"critical")
    def test_es_warning(self):
        self.assertEqual(classify("elasticsearch","search_latency","milliseconds",200),"warning")
    def test_es_critical(self):
        self.assertEqual(classify("elasticsearch","search_latency","milliseconds",500),"critical")
    def test_kafka_warning(self):
        self.assertEqual(classify("kafka","consumer_lag","messages",1000),"warning")
    def test_kafka_critical(self):
        self.assertEqual(classify("kafka","consumer_lag","messages",10000),"critical")
    def test_bad_engine(self):
        with self.assertRaises(ValueError): classify("mysql","x","y",1)
    def test_bad_unit(self):
        with self.assertRaises(ValueError): classify("postgresql","replication_lag","ms",1)
    def test_bad_metric(self):
        with self.assertRaises(ValueError): classify("postgresql","latency","seconds",1)
    def test_bad_bool(self):
        with self.assertRaises(ValueError): classify("postgresql","replication_lag","seconds",True)
    def test_bad_nan(self):
        with self.assertRaises(ValueError): classify("postgresql","replication_lag","seconds",float("nan"))
    def test_bad_inf(self):
        with self.assertRaises(ValueError): classify("postgresql","replication_lag","seconds",float("inf"))
    def test_bad_negative(self):
        with self.assertRaises(ValueError): classify("postgresql","replication_lag","seconds",-1)
    def test_bad_string(self):
        with self.assertRaises(ValueError): classify("postgresql","replication_lag","seconds","1")
    def test_fixture_count(self):
        self.assertEqual(len(read_synthetic_events()), 3)
    def test_report_count(self):
        self.assertEqual(build_report(read_synthetic_events(), self.metrics)["total"],3)
    def test_report_severities(self):
        self.assertEqual(build_report(read_synthetic_events(),self.metrics)["severities"],
                         {"healthy":0,"warning":1,"critical":2})
    def test_report_dry_run(self):
        self.assertTrue(build_report([], self.metrics)["dry_run"])
    def test_report_extra_field(self):
        rows=read_synthetic_events()
        rows[0]["secret"]="synthetic"
        with self.assertRaises(ValueError): build_report(rows, self.metrics)
    def test_report_unsafe_service(self):
        rows=read_synthetic_events()
        rows[0]["service"]="=1+1"
        with self.assertRaises(ValueError): build_report(rows, self.metrics)
    def test_report_secret_safe(self):
        self.assertNotIn("secret", json.dumps(build_report(read_synthetic_events(),self.metrics)))
    def test_main_success(self):
        self.assertEqual(main(), 0)

if __name__=="__main__":
    unittest.main()

```

## 3. Execute

Linux, macOS or WSL:

```bash
python3 -m py_compile decorator_ops.py test_decorator_ops.py
python3 -m unittest -v test_decorator_ops.py
python3 decorator_ops.py
```

Windows PowerShell:

```powershell
py -3 -m py_compile decorator_ops.py test_decorator_ops.py
py -3 -m unittest -v test_decorator_ops.py
py -3 decorator_ops.py
```

Expected synthetic report: 3 events, 1 warning, 2 critical, and one logical read invocation with one attempt. Exit code 0 means successful execution, **not** healthy infrastructure.

## 4. Failure-injection labs

1. Inject a `TransientReadError` twice, then succeed; verify three attempts but one logical call.
2. Exhaust the retry budget; verify the last transient exception is propagated.
3. Inject `PermanentReadError`; verify no retry.
4. Inject unexpected `RuntimeError`; verify no retry.
5. Reverse decorator ordering and observe the different call-count semantics.
6. Inject a clock that moves backward; verify negative duration is clamped.
7. Pass invalid operation names and unsafe metric labels.
8. Inject NaN, Infinity, booleans and negative metric values.
9. Deliberately remove `@wraps`; observe changed `__name__` and `__doc__`.
10. Verify secret-bearing arguments do not appear in metrics.
11. Compare fixed operation names with high-cardinality dynamic labels.
12. Confirm all data is synthetic and no external infrastructure is changed.

## 5. Troubleshooting and production runbooks

**Unexpected retries:** check the exception taxonomy and decorator placement; do not catch all exceptions as transient.

**Latency inflation:** compare total logical-call duration with attempts; tune deadlines and retry budget, not just delay.

**Metrics growth:** replace unbounded in-memory samples with bounded histograms, cap label cardinality and centralize metric export.

**Sensitive telemetry:** stop exporting unsafe labels, restrict stored artifacts and rotate compromised credentials if necessary.

**Rollback:** restore the prior decorator configuration, run the unit suite and verify sanitized reports before redeployment.

## 6. 100-point acceptance assessment

| Criterion | Points |
|---|---:|
| Syntax checks and automated tests | 25 |
| Decorator factories, closures and `@wraps` | 20 |
| Logical-call timing and metrics | 20 |
| Bounded retry and safety controls | 15 |
| Incident simulations | 10 |
| Production runbooks and rollback | 10 |

**Passing target:** 90/100, with all safety tests passing. The code and tests are published for execution; passing test results are not claimed until independently verified.
