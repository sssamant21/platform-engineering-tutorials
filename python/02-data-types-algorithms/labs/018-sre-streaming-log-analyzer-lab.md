# Chapter 018 — Hands-on Lab: SRE Streaming Log Analyzer

**Environment:** Python 3.10+, standard library, local synthetic data only.

## Goal
Stream JSONL events, validate records and produce a deterministic per-service report. The analyzer must not load the whole file into memory or emit a partial report after validation failure.

## 1. Fixture: `events.jsonl`

Save each JSON object on its own line:

```jsonl
{"service":"api","severity":"warning","latency_ms":220}
{"service":"db","severity":"critical","latency_ms":950}
{"service":"api","severity":"info","latency_ms":35}
{"service":"db","severity":"warning","latency_ms":300}
{"service":"api","severity":"critical","latency_ms":800}
```

## 2. Application: `stream_logs.py`

```python
"""Read-only JSONL SRE event aggregator with bounded per-line parsing."""
import argparse
from collections import Counter
from contextlib import contextmanager
import json
import math
from pathlib import Path

SEVERITIES = ("critical", "warning", "info")
REQUIRED = {"service", "severity", "latency_ms"}


def positive_int(raw: str) -> int:
    try:
        number = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def nonnegative_number(raw: str) -> float:
    try:
        number = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected number") from exc
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be finite and nonnegative")
    return number


def validate_event(value: object, line_number: int) -> dict:
    if not isinstance(value, dict) or set(value) != REQUIRED:
        raise ValueError(f"line {line_number}: expected service, severity, latency_ms")
    service = value["service"]
    severity = value["severity"]
    latency = value["latency_ms"]
    if not isinstance(service, str) or not service.strip():
        raise ValueError(f"line {line_number}: invalid service")
    if not isinstance(severity, str) or severity not in SEVERITIES:
        raise ValueError(f"line {line_number}: invalid severity")
    if isinstance(latency, bool) or not isinstance(latency, (int, float)):
        raise ValueError(f"line {line_number}: latency must be numeric")
    if not math.isfinite(latency) or latency < 0:
        raise ValueError(f"line {line_number}: latency must be finite and nonnegative")
    return {"service": service, "severity": severity, "latency_ms": latency}


def iter_events(lines, max_line_bytes: int = 65536):
    if isinstance(max_line_bytes, bool) or not isinstance(max_line_bytes, int) or max_line_bytes < 1:
        raise ValueError("max_line_bytes must be positive")
    for line_number, line in enumerate(lines, 1):
        if not isinstance(line, str):
            raise ValueError(f"line {line_number}: expected text")
        if len(line.encode("utf-8")) > max_line_bytes:
            raise ValueError(f"line {line_number}: size limit exceeded")
        if not line.strip():
            continue
        try:
            raw = json.loads(line, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"invalid constant {token}")))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"line {line_number}: invalid JSON: {exc}") from exc
        yield validate_event(raw, line_number)


def aggregate(events, threshold_ms: float = 250, max_services: int = 1000) -> dict:
    if isinstance(threshold_ms, bool) or not isinstance(threshold_ms, (int, float)):
        raise ValueError("invalid threshold")
    if not math.isfinite(threshold_ms) or threshold_ms < 0:
        raise ValueError("invalid threshold")
    if isinstance(max_services, bool) or not isinstance(max_services, int) or max_services < 1:
        raise ValueError("max_services must be positive")
    by_service = {}
    total = 0
    slow = 0
    severity_totals = Counter()
    for event in events:
        service = event["service"]
        if service not in by_service:
            if len(by_service) >= max_services:
                raise ValueError("distinct service limit exceeded")
            by_service[service] = {
                "count": 0, "slow_count": 0, "max_latency_ms": 0,
                "severities": Counter()
            }
        bucket = by_service[service]
        bucket["count"] += 1
        bucket["max_latency_ms"] = max(bucket["max_latency_ms"], event["latency_ms"])
        bucket["severities"][event["severity"]] += 1
        severity_totals[event["severity"]] += 1
        total += 1
        if event["latency_ms"] >= threshold_ms:
            slow += 1
            bucket["slow_count"] += 1
    services = [
        {
            "service": name, "count": bucket["count"],
            "slow_count": bucket["slow_count"],
            "max_latency_ms": bucket["max_latency_ms"],
            "severities": {severity: bucket["severities"][severity] for severity in SEVERITIES},
        }
        for name, bucket in sorted(by_service.items())
    ]
    return {
        "event_count": total,
        "slow_event_count": slow,
        "threshold_ms": threshold_ms,
        "severity_totals": {severity: severity_totals[severity] for severity in SEVERITIES},
        "services": services,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only streaming JSONL analyzer")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--threshold", type=nonnegative_number, default=250)
    parser.add_argument("--max-services", type=positive_int, default=1000)
    parser.add_argument("--max-line-bytes", type=positive_int, default=65536)
    args = parser.parse_args()
    try:
        with args.input.open("r", encoding="utf-8") as source:
            report = aggregate(
                iter_events(source, max_line_bytes=args.max_line_bytes),
                threshold_ms=args.threshold,
                max_services=args.max_services,
            )
    except (OSError, ValueError, UnicodeError, OverflowError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Design note:** `iter_events` is a generator; the file is opened and consumed inside `main`'s `with` block. No file handle escapes the scope. The line-size limit is checked after the file iterator has read a line; it prevents unbounded *accepted* records but does not cap the peak allocation for an extremely long physical line. A production hardened reader should use bounded `readline(max_bytes+1)` and reject overlong lines before fully allocating them.

## 3. Unit tests: `test_stream_logs.py`

```python
import argparse
import io
import unittest
from stream_logs import aggregate, iter_events, nonnegative_number, positive_int, validate_event


def event(service="api", severity="info", latency=10):
    return {"service": service, "severity": severity, "latency_ms": latency}


class StreamingLogTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_event(event(), 1)["service"], "api")

    def test_missing_field(self):
        with self.assertRaises(ValueError):
            validate_event({"service": "api"}, 1)

    def test_unknown_field(self):
        bad = event()
        bad["extra"] = "x"
        with self.assertRaises(ValueError):
            validate_event(bad, 1)

    def test_boolean_latency(self):
        with self.assertRaises(ValueError):
            validate_event(event(latency=True), 1)

    def test_negative_latency(self):
        with self.assertRaises(ValueError):
            validate_event(event(latency=-1), 1)

    def test_nan_latency(self):
        with self.assertRaises(ValueError):
            validate_event(event(latency=float("nan")), 1)

    def test_unknown_severity(self):
        with self.assertRaises(ValueError):
            validate_event(event(severity="urgent"), 1)

    def test_skip_blank_lines(self):
        records = list(iter_events(io.StringIO('\n{"service":"api","severity":"info","latency_ms":10}\n')))
        self.assertEqual(len(records), 1)

    def test_malformed_json(self):
        with self.assertRaisesRegex(ValueError, "line 1"):
            list(iter_events(["not json\n"]))

    def test_nonfinite_json_constant(self):
        with self.assertRaises(ValueError):
            list(iter_events(['{"service":"api","severity":"info","latency_ms":NaN}\n']))

    def test_line_limit(self):
        with self.assertRaisesRegex(ValueError, "size limit"):
            list(iter_events([" " * 50], max_line_bytes=10))

    def test_aggregation(self):
        rows = [event("api", "warning", 250), event("db", "critical", 100)]
        report = aggregate(rows, threshold_ms=250)
        self.assertEqual(report["event_count"], 2)
        self.assertEqual(report["slow_event_count"], 1)

    def test_sorted_services(self):
        report = aggregate([event("z"), event("a")])
        self.assertEqual([x["service"] for x in report["services"]], ["a", "z"])

    def test_severity_counts(self):
        report = aggregate([event("api", "critical")])
        self.assertEqual(report["severity_totals"]["critical"], 1)

    def test_empty(self):
        self.assertEqual(aggregate([])["event_count"], 0)

    def test_cardinality_limit(self):
        with self.assertRaises(ValueError):
            aggregate([event("a"), event("b")], max_services=1)

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            aggregate([event()], threshold_ms=-1)

    def test_invalid_cardinality(self):
        with self.assertRaises(ValueError):
            aggregate([], max_services=True)

    def test_bad_cli_threshold(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            nonnegative_number("nan")

    def test_bad_cli_limit(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_int("0")


if __name__ == "__main__":
    unittest.main()
```

## 4. Run commands

```bash
python stream_logs.py --input events.jsonl
python stream_logs.py --input events.jsonl --threshold 500
python -m unittest -v test_stream_logs.py
python -m py_compile stream_logs.py
```

Expected default results: **5 events**, **3 slow events** at or above 250 ms (950, 300 and 800; 220 and 35 are below threshold), **2 critical**, **2 warning**, **1 info**, and services sorted `api`, `db`.

## 5. Failure injection
1. Add a malformed JSONL line: fail the report, with line number.
2. Set `latency_ms` to `true` or `-1`: reject.
3. Use `--max-services 1`: reject when the second service appears.
4. Use `--max-line-bytes 10`: reject the first nonempty record.
5. Use `--threshold nan`: reject the CLI argument.
6. Use an empty file: return zero totals and an empty services list (not a claim that production is healthy).

## 6. Troubleshooting
| Issue | Explanation | Remedy |
|---|---|---|
| `JSONDecodeError` | Invalid JSONL | Validate each line |
| No events | Empty file or blank lines | Check fixture and source |
| Limit exceeded | Too many distinct services | Investigate cardinality; do not blindly raise limit |
| Memory still grows | Aggregates retain distinct service keys | Use bounded keys or external aggregation |
| Missing partial report | Fail-closed behavior | Correct input and rerun |
| Generator unexpectedly exhausted | One-shot iteration | Create a fresh iterator |

## 7. Acceptance checklist
- [ ] Reads JSONL incrementally.
- [ ] Validates schema, types, severities and finite nonnegative latency.
- [ ] Counts events and slow events correctly.
- [ ] Produces deterministic per-service summaries.
- [ ] Enforces line and distinct-service limits.
- [ ] All 20 unit tests pass locally.
- [ ] No production calls, notifications or changes.

## 8. Production hardening backlog
Use bounded `readline` to enforce physical line limits, streaming decompression for compressed logs, maximum total input bytes, telemetry timestamps/freshness, structured error metrics, checkpointing and a dead-letter policy. Add representative large-fixture performance tests before production use.

## Cleanup
Delete only files created for this lab.
