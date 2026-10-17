# Chapter 019 — Hands-on Lab: Rolling SRE Error Rate Analyzer

## Scenario
Build a read-only, offline JSONL analyzer that computes the rolling error rate per service over an inclusive trailing time window. It uses deques and frequency maps and emits a deterministic summary. **It does not page on-call staff or mutate infrastructure.**

## Prerequisites
Python 3.10+, standard library.

## 1. Create `events.jsonl`
```jsonl
{"timestamp":0,"service":"api","is_error":false}
{"timestamp":10,"service":"api","is_error":true}
{"timestamp":15,"service":"db","is_error":true}
{"timestamp":30,"service":"api","is_error":true}
{"timestamp":40,"service":"api","is_error":false}
{"timestamp":45,"service":"db","is_error":false}
```

## 2. Create `rolling_errors.py`
```python
"""Read-only event-time rolling error-rate analyzer for sorted JSONL."""
import argparse
from collections import Counter, deque
import json
import math
from pathlib import Path

FIELDS = {"timestamp", "service", "is_error"}


def positive_number(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected number") from exc
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return value


def positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected integer") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def events_from_lines(lines):
    last_timestamp = -1.0
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON: {exc}") from exc
        if not isinstance(event, dict) or set(event) != FIELDS:
            raise ValueError(f"line {line_number}: incorrect fields")
        timestamp = event["timestamp"]
        service = event["service"]
        is_error = event["is_error"]
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            raise ValueError(f"line {line_number}: timestamp must be numeric")
        if not math.isfinite(timestamp) or timestamp < 0:
            raise ValueError(f"line {line_number}: invalid timestamp")
        if timestamp < last_timestamp:
            raise ValueError(f"line {line_number}: timestamps out of order")
        if not isinstance(service, str) or not service.strip():
            raise ValueError(f"line {line_number}: invalid service")
        if not isinstance(is_error, bool):
            raise ValueError(f"line {line_number}: is_error must be boolean")
        last_timestamp = timestamp
        yield {"timestamp": timestamp, "service": service, "is_error": is_error}


def analyze(events, window_seconds=30.0, min_samples=2, alert_rate=0.5):
    if isinstance(window_seconds, bool) or not isinstance(window_seconds, (int, float)) or not math.isfinite(window_seconds) or window_seconds <= 0:
        raise ValueError("window_seconds must be finite and positive")
    if isinstance(min_samples, bool) or not isinstance(min_samples, int) or min_samples < 1:
        raise ValueError("min_samples must be positive")
    if isinstance(alert_rate, bool) or not isinstance(alert_rate, (int, float)) or not math.isfinite(alert_rate) or not 0 <= alert_rate <= 1:
        raise ValueError("alert_rate must be between zero and one")
    windows = {}
    errors = Counter()
    total = Counter()
    latest = {}
    last_timestamp = -1.0
    for event in events:
        timestamp = event["timestamp"]
        if timestamp < last_timestamp:
            raise ValueError("timestamps out of order")
        last_timestamp = timestamp
        service = event["service"]
        pending = windows.setdefault(service, deque())
        pending.append((timestamp, event["is_error"]))
        total[service] += 1
        errors[service] += int(event["is_error"])
        while pending and pending[0][0] < timestamp - window_seconds:
            _, old_error = pending.popleft()
            total[service] -= 1
            errors[service] -= int(old_error)
        count = total[service]
        error_count = errors[service]
        rate = error_count / count
        latest[service] = {
            "service": service,
            "window_event_count": count,
            "window_error_count": error_count,
            "window_error_rate": round(rate, 6),
            "last_event_timestamp": timestamp,
            "would_alert": count >= min_samples and rate >= alert_rate,
        }
    return {
        "window_seconds": window_seconds,
        "min_samples": min_samples,
        "alert_rate": alert_rate,
        "services": [latest[name] for name in sorted(latest)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only rolling SRE error rate analyzer")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--window-seconds", type=positive_number, default=30.0)
    parser.add_argument("--min-samples", type=positive_int, default=2)
    parser.add_argument("--alert-rate", type=float, default=0.5)
    args = parser.parse_args()
    try:
        with args.input.open("r", encoding="utf-8") as source:
            report = analyze(events_from_lines(source), args.window_seconds, args.min_samples, args.alert_rate)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### Important interpretation
This implementation reports each service's trailing window **as of that service's most recent event**, not a single shared global timestamp. If a service has not emitted recently, its result is stale. For a fleet-wide snapshot at a common time, expire windows against one global observation time and add freshness checks.

The implementation assumes validated events from `events_from_lines`. Direct callers of `analyze` should supply the same schema. Production systems must also cap service cardinality and events retained per window; the time interval alone is not a memory bound.

## 3. Create `test_rolling_errors.py`
```python
import io
import unittest
from rolling_errors import analyze, events_from_lines


def row(ts, service="api", error=False):
    return {"timestamp": ts, "service": service, "is_error": error}


class RollingErrorsTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(analyze([])["services"], [])
    def test_single_below_min_samples(self):
        self.assertFalse(analyze([row(1, error=True)])["services"][0]["would_alert"])
    def test_two_errors_alert(self):
        rows = [row(0, error=True), row(1, error=True)]
        self.assertTrue(analyze(rows)["services"][0]["would_alert"])
    def test_rate_half(self):
        rows = [row(0), row(1, error=True)]
        self.assertEqual(analyze(rows)["services"][0]["window_error_rate"], 0.5)
    def test_inclusive_left_boundary(self):
        rows = [row(0, error=True), row(30)]
        self.assertEqual(analyze(rows, window_seconds=30)["services"][0]["window_event_count"], 2)
    def test_eviction(self):
        rows = [row(0, error=True), row(31)]
        self.assertEqual(analyze(rows, window_seconds=30)["services"][0]["window_error_count"], 0)
    def test_independent_services(self):
        rows = [row(0, "api", True), row(1, "db", False)]
        self.assertEqual(len(analyze(rows)["services"]), 2)
    def test_sorted_services(self):
        rows = [row(0, "z"), row(1, "a")]
        self.assertEqual(analyze(rows)["services"][0]["service"], "a")
    def test_out_of_order_analysis(self):
        with self.assertRaises(ValueError):
            analyze([row(2), row(1)])
    def test_bad_window(self):
        with self.assertRaises(ValueError):
            analyze([], window_seconds=0)
    def test_bad_min_samples(self):
        with self.assertRaises(ValueError):
            analyze([], min_samples=True)
    def test_bad_alert_rate(self):
        with self.assertRaises(ValueError):
            analyze([], alert_rate=2)
    def test_jsonl_parse(self):
        lines = io.StringIO('{"timestamp":0,"service":"api","is_error":true}\n')
        self.assertTrue(list(events_from_lines(lines))[0]["is_error"])
    def test_blank_line(self):
        self.assertEqual(list(events_from_lines(["\n"])), [])
    def test_bad_json(self):
        with self.assertRaises(ValueError):
            list(events_from_lines(["{bad"]))
    def test_bad_schema(self):
        with self.assertRaises(ValueError):
            list(events_from_lines(['{"timestamp":1}\n']))
    def test_bad_bool_timestamp(self):
        with self.assertRaises(ValueError):
            list(events_from_lines(['{"timestamp":true,"service":"api","is_error":false}\n']))
    def test_bad_error_type(self):
        with self.assertRaises(ValueError):
            list(events_from_lines(['{"timestamp":1,"service":"api","is_error":1}\n']))
    def test_out_of_order_input(self):
        lines = [
            '{"timestamp":2,"service":"api","is_error":false}\n',
            '{"timestamp":1,"service":"api","is_error":false}\n'
        ]
        with self.assertRaises(ValueError):
            list(events_from_lines(lines))
    def test_no_input_mutation(self):
        rows = [row(1)]
        analyze(rows)
        self.assertEqual(rows[0]["timestamp"], 1)


if __name__ == "__main__":
    unittest.main()
```

## 4. Run
```bash
python rolling_errors.py --input events.jsonl
python rolling_errors.py --input events.jsonl --window-seconds 10 --min-samples 2
python -m unittest -v test_rolling_errors.py
python -m py_compile rolling_errors.py
```

Expected default results with 30-second windows:
- `api` latest at t=40: three events (t=10, 30, 40), two errors, rate 0.666667, `would_alert=true`.
- `db` latest at t=45: two events (t=15, 45), one error, rate 0.5, `would_alert=true`.
- Twenty unit tests are provided.

## 5. Failure injection
1. Swap timestamps to make input unsorted: reject the batch.
2. Set `is_error` to `1`: reject the record.
3. Use a negative timestamp: reject the record.
4. Set `--window-seconds 0`: reject the argument.
5. Set `--alert-rate 2`: reject before output.
6. Feed malformed JSON: fail with line number.

## 6. Production readiness limitations
This is an offline educational simulation. It has no late-event handling, checkpointing, durable state, common-time snapshots, bounded event-count capacity, or alert routing. Never interpret `would_alert` as an actual production page. To productionize, add ingestion ordering guarantees, cardinality caps, window memory limits, metrics, retries, observability and audited alert policy.

## Acceptance checklist
- [ ] Strict JSONL schema and timestamp ordering
- [ ] Inclusive window boundary behavior
- [ ] Independent per-service windows
- [ ] Correct error counts and ratios
- [ ] Twenty tests pass
- [ ] No external side effects

## Cleanup
Delete only the local lab files.
