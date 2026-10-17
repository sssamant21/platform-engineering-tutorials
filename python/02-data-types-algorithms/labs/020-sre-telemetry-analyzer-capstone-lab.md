# Chapter 020 — Hands-on Capstone: SRE Telemetry Analyzer

**Python:** 3.10+ | **Dependencies:** standard library only | **Mode:** offline, read-only

## 1. Directory layout

```text
chapter-020/
  telemetry.jsonl
  telemetry_analyzer.py
  test_telemetry_analyzer.py
```

## 2. Create `telemetry.jsonl`

```jsonl
{"timestamp":0,"environment":"prod","service":"api","severity":"info","latency_ms":40,"is_error":false}
{"timestamp":10,"environment":"prod","service":"api","severity":"warning","latency_ms":260,"is_error":true}
{"timestamp":15,"environment":"prod","service":"db","severity":"critical","latency_ms":950,"is_error":true}
{"timestamp":30,"environment":"prod","service":"api","severity":"critical","latency_ms":800,"is_error":true}
{"timestamp":40,"environment":"prod","service":"api","severity":"info","latency_ms":50,"is_error":false}
{"timestamp":45,"environment":"prod","service":"db","severity":"warning","latency_ms":300,"is_error":false}
{"timestamp":50,"environment":"staging","service":"api","severity":"info","latency_ms":25,"is_error":false}
```

## 3. Create `telemetry_analyzer.py`

```python
"""Offline streaming SRE telemetry capstone. No external side effects."""
import argparse
from collections import Counter, deque
import json
import math
from pathlib import Path

FIELDS = {"timestamp", "environment", "service", "severity", "latency_ms", "is_error"}
SEVERITIES = ("critical", "warning", "info")


def positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected integer") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def finite_nonnegative(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected number") from exc
    if not math.isfinite(value) or value < 0:
        raise argparse.ArgumentTypeError("must be finite and nonnegative")
    return value


def finite_positive(raw: str) -> float:
    value = finite_nonnegative(raw)
    if value == 0:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def rate_arg(raw: str) -> float:
    value = finite_nonnegative(raw)
    if value > 1:
        raise argparse.ArgumentTypeError("rate must be <= 1")
    return value


def bounded_lines(source, max_line_bytes: int):
    """Read physical lines with a byte cap before allocating unbounded strings."""
    if isinstance(max_line_bytes, bool) or not isinstance(max_line_bytes, int) or max_line_bytes < 1:
        raise ValueError("max_line_bytes must be positive")
    line_number = 0
    while True:
        raw = source.readline(max_line_bytes + 1)
        if not raw:
            return
        line_number += 1
        if len(raw) > max_line_bytes:
            raise ValueError(f"line {line_number}: byte limit exceeded")
        try:
            line = raw.decode("utf-8")
        except UnicodeError as exc:
            raise ValueError(f"line {line_number}: invalid UTF-8") from exc
        yield line_number, line


def parse_events(numbered_lines):
    last_timestamp = -1
    for number, line in numbered_lines:
        if not line.strip():
            continue
        try:
            record = json.loads(
                line,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid constant {value}")),
            )
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"line {number}: invalid JSON: {exc}") from exc
        if not isinstance(record, dict) or set(record) != FIELDS:
            raise ValueError(f"line {number}: invalid schema")
        for field in ("environment", "service"):
            value = record[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"line {number}: invalid {field}")
        if not isinstance(record["severity"], str) or record["severity"] not in SEVERITIES:
            raise ValueError(f"line {number}: invalid severity")
        for field in ("timestamp", "latency_ms"):
            value = record[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"line {number}: invalid {field}")
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"line {number}: invalid {field}")
        if not isinstance(record["is_error"], bool):
            raise ValueError(f"line {number}: is_error must be boolean")
        if record["timestamp"] < last_timestamp:
            raise ValueError(f"line {number}: out-of-order timestamp")
        last_timestamp = record["timestamp"]
        yield record


def analyze(events, window_seconds=30.0, slow_threshold_ms=250.0,
            min_samples=2, alert_rate=0.5, max_services=1000,
            max_window_events=100000):
    for name, value in (("window_seconds", window_seconds), ("slow_threshold_ms", slow_threshold_ms),
                        ("alert_rate", alert_rate)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"invalid {name}")
    if window_seconds <= 0 or slow_threshold_ms < 0 or not 0 <= alert_rate <= 1:
        raise ValueError("invalid window/threshold/rate")
    for name, value in (("min_samples", min_samples), ("max_services", max_services),
                        ("max_window_events", max_window_events)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"invalid {name}")
    buckets = {}
    totals = Counter()
    event_count = 0
    last_global_timestamp = -1
    retained_events = 0
    for event in events:
        timestamp = event["timestamp"]
        if timestamp < last_global_timestamp:
            raise ValueError("out-of-order timestamp")
        last_global_timestamp = timestamp
        key = (event["environment"], event["service"])
        if key not in buckets:
            if len(buckets) >= max_services:
                raise ValueError("service cardinality limit exceeded")
            buckets[key] = {
                "total": 0, "slow": 0, "max_latency_ms": 0,
                "severities": Counter(), "window": deque(),
                "window_errors": 0, "last_timestamp": timestamp,
            }
        bucket = buckets[key]
        bucket["total"] += 1
        bucket["slow"] += int(event["latency_ms"] >= slow_threshold_ms)
        bucket["max_latency_ms"] = max(bucket["max_latency_ms"], event["latency_ms"])
        bucket["severities"][event["severity"]] += 1
        totals[event["severity"]] += 1
        event_count += 1
        pending = bucket["window"]
        pending.append((timestamp, event["is_error"]))
        retained_events += 1
        bucket["window_errors"] += int(event["is_error"])
        while pending and pending[0][0] < timestamp - window_seconds:
            _, old_error = pending.popleft()
            retained_events -= 1
            bucket["window_errors"] -= int(old_error)
        if retained_events > max_window_events:
            raise ValueError("retained window event limit exceeded")
        bucket["last_timestamp"] = timestamp

    services = []
    for (environment, service), bucket in sorted(buckets.items()):
        window_count = len(bucket["window"])
        rate = bucket["window_errors"] / window_count
        services.append({
            "environment": environment,
            "service": service,
            "total_events": bucket["total"],
            "slow_events": bucket["slow"],
            "max_latency_ms": bucket["max_latency_ms"],
            "severities": {name: bucket["severities"][name] for name in SEVERITIES},
            "last_event_timestamp": bucket["last_timestamp"],
            "window_events": window_count,
            "window_errors": bucket["window_errors"],
            "window_error_rate": round(rate, 6),
            "would_alert": window_count >= min_samples and rate >= alert_rate,
        })
    return {
        "event_count": event_count,
        "service_count": len(services),
        "slow_threshold_ms": slow_threshold_ms,
        "window_seconds": window_seconds,
        "severity_totals": {name: totals[name] for name in SEVERITIES},
        "services": services,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline read-only SRE telemetry analyzer")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--window-seconds", type=finite_positive, default=30.0)
    parser.add_argument("--slow-threshold-ms", type=finite_nonnegative, default=250.0)
    parser.add_argument("--min-samples", type=positive_int, default=2)
    parser.add_argument("--alert-rate", type=rate_arg, default=0.5)
    parser.add_argument("--max-services", type=positive_int, default=1000)
    parser.add_argument("--max-window-events", type=positive_int, default=100000)
    parser.add_argument("--max-line-bytes", type=positive_int, default=65536)
    args = parser.parse_args()
    try:
        with args.input.open("rb") as source:
            report = analyze(
                parse_events(bounded_lines(source, args.max_line_bytes)),
                window_seconds=args.window_seconds,
                slow_threshold_ms=args.slow_threshold_ms,
                min_samples=args.min_samples,
                alert_rate=args.alert_rate,
                max_services=args.max_services,
                max_window_events=args.max_window_events,
            )
    except (OSError, ValueError, UnicodeError, OverflowError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 4. Create `test_telemetry_analyzer.py`

```python
import argparse
import io
import json
import unittest
from telemetry_analyzer import (
    analyze, bounded_lines, parse_events, finite_nonnegative,
    finite_positive, rate_arg,
)


def row(ts=0, env="prod", service="api", severity="info", latency=10, error=False):
    return {"timestamp": ts, "environment": env, "service": service,
            "severity": severity, "latency_ms": latency, "is_error": error}


def parse(rows):
    text = "".join(json.dumps(item) + "\n" for item in rows)
    return parse_events(bounded_lines(io.BytesIO(text.encode()), 65536))


class TelemetryCapstoneTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(analyze([])["event_count"], 0)

    def test_single(self):
        self.assertEqual(analyze(parse([row()]))["service_count"], 1)

    def test_composite_identity(self):
        report = analyze(parse([row(0), row(1, env="staging")]))
        self.assertEqual(report["service_count"], 2)

    def test_sorted_output(self):
        report = analyze(parse([row(0, service="z"), row(1, service="a")]))
        self.assertEqual(report["services"][0]["service"], "a")

    def test_severity_counts(self):
        report = analyze(parse([row(0, severity="critical")]))
        self.assertEqual(report["severity_totals"]["critical"], 1)

    def test_slow_inclusive(self):
        report = analyze(parse([row(0, latency=250)]))
        self.assertEqual(report["services"][0]["slow_events"], 1)

    def test_max_latency(self):
        report = analyze(parse([row(0, latency=5), row(1, latency=20)]))
        self.assertEqual(report["services"][0]["max_latency_ms"], 20)

    def test_window_inclusive_boundary(self):
        report = analyze(parse([row(0, error=True), row(30)]))
        self.assertEqual(report["services"][0]["window_events"], 2)

    def test_window_eviction(self):
        report = analyze(parse([row(0, error=True), row(31)]))
        self.assertEqual(report["services"][0]["window_errors"], 0)

    def test_error_rate(self):
        report = analyze(parse([row(0, error=True), row(1)]))
        self.assertEqual(report["services"][0]["window_error_rate"], 0.5)

    def test_alert_minimum(self):
        report = analyze(parse([row(0, error=True)]))
        self.assertFalse(report["services"][0]["would_alert"])

    def test_alert_true(self):
        report = analyze(parse([row(0, error=True), row(1, error=True)]))
        self.assertTrue(report["services"][0]["would_alert"])

    def test_invalid_schema(self):
        with self.assertRaises(ValueError):
            list(parse([{"timestamp": 0}]))

    def test_boolean_timestamp(self):
        with self.assertRaises(ValueError):
            list(parse([row(ts=True)]))

    def test_boolean_latency(self):
        with self.assertRaises(ValueError):
            list(parse([row(latency=True)]))

    def test_negative_latency(self):
        with self.assertRaises(ValueError):
            list(parse([row(latency=-1)]))

    def test_invalid_severity(self):
        with self.assertRaises(ValueError):
            list(parse([row(severity="urgent")]))

    def test_invalid_error_type(self):
        with self.assertRaises(ValueError):
            list(parse([row(error=1)]))

    def test_out_of_order(self):
        with self.assertRaises(ValueError):
            list(parse([row(2), row(1)]))

    def test_invalid_json(self):
        with self.assertRaises(ValueError):
            list(parse_events([(1, "{bad")]))

    def test_line_limit(self):
        with self.assertRaises(ValueError):
            list(bounded_lines(io.BytesIO(b"x" * 20), 10))

    def test_cardinality_limit(self):
        with self.assertRaises(ValueError):
            analyze(parse([row(0, service="a"), row(1, service="b")]), max_services=1)

    def test_window_capacity(self):
        with self.assertRaises(ValueError):
            analyze(parse([row(0), row(1)]), max_window_events=1)

    def test_rate_argument(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            rate_arg("nan")

    def test_nonnegative_argument(self):
        self.assertEqual(finite_nonnegative("0"), 0)

    def test_positive_argument(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            finite_positive("0")

    def test_repeatable(self):
        rows = [row(0), row(1, severity="warning")]
        self.assertEqual(analyze(parse(rows)), analyze(parse(rows)))

    def test_blank_lines(self):
        self.assertEqual(list(parse_events([(1, "\n")])), [])

    def test_utf8_failure(self):
        with self.assertRaises(ValueError):
            list(bounded_lines(io.BytesIO(b"\xff\n"), 100))

    def test_nonfinite_json(self):
        line = json.dumps(row()).replace('"latency_ms": 10', '"latency_ms": NaN')
        with self.assertRaises(ValueError):
            list(parse_events([(1, line)]))


if __name__ == "__main__":
    unittest.main()
```

## 5. Execute

```bash
python --version
python telemetry_analyzer.py --input telemetry.jsonl
python -m unittest -v test_telemetry_analyzer.py
python -m py_compile telemetry_analyzer.py
```

**Expected:** 7 total events; 3 distinct environment/service identities; 4 slow events (260, 950, 800, 300); 2 critical, 2 warning and 3 info.

Per-service expected results:
- `prod/api`: 4 total, 2 slow, maximum latency 800, latest window at t=40 includes t=10/30/40, 2 errors / 3 events, rate 0.666667, `would_alert=true`.
- `prod/db`: 2 total, 2 slow, maximum latency 950, latest window at t=45 includes t=15/45, 1 error / 2 events, rate 0.5, `would_alert=true`.
- `staging/api`: 1 total, 0 slow, maximum latency 25, latest window 0 errors / 1 event, `would_alert=false`.

**30 unit tests** are provided. Run them locally before treating this lab as validated.

## 6. Failure injection
1. Duplicate a malformed field or remove `severity`: validation error.
2. Change timestamp order: reject the entire report.
3. Set `latency_ms` to `true`, `-1` or `NaN`: reject.
4. Run `--max-services 1`: reject excess cardinality.
5. Run `--max-window-events 1`: reject excessive retained window state.
6. Run `--max-line-bytes 10`: reject oversized physical input line.
7. Run `--alert-rate 2`: reject invalid CLI argument.
8. Replace the fixture with malformed JSON: nonzero exit, no success report.

## 7. Acceptance checklist
- [ ] All 30 tests pass.
- [ ] Fixture counts match expected results.
- [ ] Same fixture yields identical JSON across runs.
- [ ] Malformed input produces no success report.
- [ ] Inclusive time-window boundaries verified.
- [ ] Service cardinality and retained-event budgets enforced.
- [ ] No network calls, production writes or alert delivery.

## 8. Production limitations and next steps
This project is not a production telemetry collector. It lacks deduplication IDs, replay guarantees, out-of-order event buffering, durable checkpoints, synchronized fleet-wide snapshot semantics, request-weighted SLO accounting, backpressure and distributed alert routing. Implement these with architecture review and representative load testing before production use.

## Cleanup
Delete only the three local lab files.
