# Chapter 024 — Hands-on Lab: Instrumented SRE Probe

**Python 3.10+ | Standard library only | Offline and read-only**

## Architecture
```text
synthetic probe input → retry decorator (transient only) → timing decorator
                     → pure probe result → in-memory bounded metrics → JSON CLI
```
No real cluster calls, network requests or notifications. The lab simulates a transient read failure.

## 1. Create `instrumentation.py`
```python
"""Reusable instrumentation for read-only, idempotent operations."""
from collections import Counter
from functools import wraps
import math
import time


class TransientProbeError(Exception):
    """Synthetic transient read failure."""


def retry(*, attempts=3, delay_seconds=0.0, sleeper=time.sleep):
    """Retry only TransientProbeError; no retry on other exceptions."""
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        raise ValueError("attempts must be positive integer")
    if isinstance(delay_seconds, bool) or not isinstance(delay_seconds, (int, float)):
        raise ValueError("delay_seconds must be numeric")
    if not math.isfinite(delay_seconds) or delay_seconds < 0:
        raise ValueError("delay_seconds must be finite and nonnegative")
    if not callable(sleeper):
        raise TypeError("sleeper must be callable")

    def decorate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for index in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except TransientProbeError:
                    if index + 1 == attempts:
                        raise
                    sleeper(delay_seconds)
            raise AssertionError("unreachable")
        return wrapper
    return decorate


def timed(*, clock=time.perf_counter, record):
    """Record one terminal duration and outcome, then propagate errors."""
    if not callable(clock) or not callable(record):
        raise TypeError("clock and record must be callable")
    def decorate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = clock()
            outcome = "success"
            try:
                return fn(*args, **kwargs)
            except Exception:
                outcome = "failure"
                raise
            finally:
                elapsed = clock() - start
                record(fn.__name__, outcome, elapsed)
        return wrapper
    return decorate


class Metrics:
    """Single-process lab-only metrics; not thread-safe."""
    def __init__(self, max_records=1000):
        if isinstance(max_records, bool) or not isinstance(max_records, int) or max_records < 1:
            raise ValueError("max_records must be positive")
        self.max_records = max_records
        self.counts = Counter()
        self.durations = []

    def record(self, operation, outcome, seconds):
        if operation not in {"probe"} or outcome not in {"success", "failure"}:
            raise ValueError("unexpected metric labels")
        if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError("invalid duration")
        if len(self.durations) >= self.max_records:
            raise ValueError("metrics capacity exceeded")
        self.counts[outcome] += 1
        self.durations.append(round(seconds, 6))

    def snapshot(self):
        return {"success": self.counts["success"], "failure": self.counts["failure"],
                "durations_seconds": list(self.durations)}


def make_probe(*, transient_failures=1):
    """Return isolated synthetic read-only probe state."""
    if isinstance(transient_failures, bool) or not isinstance(transient_failures, int) or transient_failures < 0:
        raise ValueError("transient_failures must be nonnegative integer")
    calls = 0
    def probe():
        nonlocal calls
        calls += 1
        if calls <= transient_failures:
            raise TransientProbeError("synthetic transient failure")
        return {"status": "healthy", "attempts": calls}
    return probe
```

## 2. Create `run_probe.py`
```python
import argparse
import json
from instrumentation import Metrics, TransientProbeError, make_probe, retry, timed


def main():
    parser = argparse.ArgumentParser(description="Synthetic read-only SRE probe")
    parser.add_argument("--transient-failures", type=int, default=1)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args()
    try:
        metrics = Metrics()
        probe = make_probe(transient_failures=args.transient_failures)
        # The timing decorator is outermost: measures the whole retry sequence.
        wrapped = timed(record=metrics.record)(retry(attempts=args.attempts)(probe))
        result = wrapped()
    except (ValueError, TypeError, TransientProbeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"result": result, "metrics": metrics.snapshot()},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 3. Create `test_instrumentation.py`
```python
import unittest
from functools import lru_cache, partial
from instrumentation import Metrics, TransientProbeError, make_probe, retry, timed


class InstrumentationTests(unittest.TestCase):
    def test_success_first_attempt(self):
        self.assertEqual(retry()(make_probe(transient_failures=0))()["attempts"], 1)

    def test_success_after_retry(self):
        self.assertEqual(retry(attempts=3)(make_probe(transient_failures=2))()["attempts"], 3)

    def test_retry_exhausted(self):
        with self.assertRaises(TransientProbeError):
            retry(attempts=2)(make_probe(transient_failures=3))()

    def test_no_retry_other_error(self):
        calls = []
        def broken():
            calls.append(1)
            raise ValueError("bad input")
        with self.assertRaises(ValueError):
            retry(attempts=3)(broken)()
        self.assertEqual(len(calls), 1)

    def test_invalid_attempts_zero(self):
        with self.assertRaises(ValueError):
            retry(attempts=0)

    def test_invalid_attempts_bool(self):
        with self.assertRaises(ValueError):
            retry(attempts=True)

    def test_invalid_delay(self):
        with self.assertRaises(ValueError):
            retry(delay_seconds=-1)

    def test_invalid_delay_nan(self):
        with self.assertRaises(ValueError):
            retry(delay_seconds=float("nan"))

    def test_invalid_sleeper(self):
        with self.assertRaises(TypeError):
            retry(sleeper=None)

    def test_injected_sleep(self):
        sleeps = []
        result = retry(attempts=3, delay_seconds=0.2, sleeper=sleeps.append)(
            make_probe(transient_failures=2)
        )()
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(sleeps, [0.2, 0.2])

    def test_metadata(self):
        wrapped = retry()(make_probe(transient_failures=0))
        self.assertEqual(wrapped.__name__, "probe")
        self.assertTrue(hasattr(wrapped, "__wrapped__"))

    def test_timed_success(self):
        records = []
        clock = iter([10.0, 10.5])
        fn = timed(clock=lambda: next(clock), record=lambda *args: records.append(args))(lambda: 1)
        self.assertEqual(fn(), 1)
        self.assertEqual(records[0][1:], ("success", 0.5))

    def test_timed_failure(self):
        records = []
        clock = iter([1.0, 2.0])
        def broken():
            raise RuntimeError("failure")
        fn = timed(clock=lambda: next(clock), record=lambda *args: records.append(args))(broken)
        with self.assertRaises(RuntimeError):
            fn()
        self.assertEqual(records[0][1:], ("failure", 1.0))

    def test_timed_invalid_clock(self):
        with self.assertRaises(TypeError):
            timed(clock=None, record=lambda *args: None)

    def test_metrics_snapshot(self):
        metrics = Metrics()
        metrics.record("probe", "success", 0.1)
        self.assertEqual(metrics.snapshot()["success"], 1)

    def test_metrics_failure(self):
        metrics = Metrics()
        metrics.record("probe", "failure", 0.2)
        self.assertEqual(metrics.snapshot()["failure"], 1)

    def test_metrics_bad_label(self):
        with self.assertRaises(ValueError):
            Metrics().record("request-123", "success", 0.1)

    def test_metrics_negative_duration(self):
        with self.assertRaises(ValueError):
            Metrics().record("probe", "success", -1)

    def test_metrics_capacity(self):
        metrics = Metrics(max_records=1)
        metrics.record("probe", "success", 0.1)
        with self.assertRaises(ValueError):
            metrics.record("probe", "success", 0.2)

    def test_metrics_invalid_capacity(self):
        with self.assertRaises(ValueError):
            Metrics(max_records=0)

    def test_probe_state_isolation(self):
        first = make_probe(transient_failures=0)
        second = make_probe(transient_failures=0)
        self.assertEqual((first()["attempts"], first()["attempts"], second()["attempts"]), (1, 2, 1))

    def test_probe_negative_failures(self):
        with self.assertRaises(ValueError):
            make_probe(transient_failures=-1)

    def test_partial(self):
        def threshold(value, *, limit):
            return value >= limit
        checker = partial(threshold, limit=250)
        self.assertTrue(checker(300))

    def test_lru_cache(self):
        calls = []
        @lru_cache(maxsize=4)
        def normalize(value):
            calls.append(value)
            return value.upper()
        self.assertEqual((normalize("ok"), normalize("ok")), ("OK", "OK"))
        self.assertEqual(len(calls), 1)

    def test_decorator_order(self):
        metrics = Metrics()
        wrapped = timed(record=metrics.record)(
            retry(attempts=2)(make_probe(transient_failures=1))
        )
        self.assertEqual(wrapped()["attempts"], 2)
        self.assertEqual(metrics.snapshot()["success"], 1)

    def test_snapshot_copy(self):
        metrics = Metrics()
        snapshot = metrics.snapshot()
        snapshot["durations_seconds"].append(999)
        self.assertEqual(metrics.snapshot()["durations_seconds"], [])


if __name__ == "__main__":
    unittest.main()
```

## 4. Execute
```bash
python run_probe.py
python run_probe.py --transient-failures 0
python -m unittest -v test_instrumentation.py
python -m py_compile instrumentation.py run_probe.py
```

Expected default: `status=healthy`, `attempts=2`, metrics `success=1` and `failure=0`. Duration is measured at runtime and is not fixed. **26 unit tests** are included.

## 5. Failure injection
1. `python run_probe.py --transient-failures 4 --attempts 3` — terminal transient failure, nonzero exit.
2. `python run_probe.py --attempts 0` — reject invalid retry policy.
3. `python run_probe.py --transient-failures -1` — reject invalid fixture.
4. Change the probe to raise `ValueError` — confirm no retry.
5. Use `Metrics(max_records=1)` and record twice — fail closed.
6. Verify decorator order changes the timing measurement scope.

## 6. Troubleshooting and runbook
- Retry exhaustion: inspect whether failure is transient; reduce request rate and check service health; do not increase attempts blindly.
- Unexpected multiple calls: inspect decorator stacking and operation idempotency.
- Metric capacity error: rotate/export approved metrics, not unbounded in-memory buffers.
- Incorrect elapsed duration: use `perf_counter` and injected clocks for tests.
- Sensitive labels: allowlist operation names and outcome labels only.

## 7. Production limitations
This educational wrapper has fixed delay, no exponential backoff/jitter, no total deadline, no concurrency synchronization, and no distributed metrics export. It must not be applied to production write operations without idempotency and reliability review. Add bounded exponential backoff, deadlines, cancellation, metrics backend and rate limiting before operational deployment.

## Acceptance
- [ ] 26 unit tests pass locally.
- [ ] Function metadata preserved.
- [ ] Only transient exception is retried.
- [ ] Nontransient failures propagate.
- [ ] Monotonic duration measured once per outer call.
- [ ] Synthetic probe performs no external I/O.
