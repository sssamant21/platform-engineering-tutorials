# Chapter 015 — Hands-on Lab: SRE Latency Sorting and Search

## Mission
Analyze synthetic latency samples from a local JSON file. Validate all records, rank the slowest requests, calculate nearest-rank percentiles and count samples at or above a configurable threshold using `bisect_left`. No production telemetry or cloud access.

## Step 1 — Create `latencies.json`
```json
[
  {"id":"req-003","service":"api","latency_ms":250},
  {"id":"req-001","service":"api","latency_ms":40},
  {"id":"req-004","service":"db","latency_ms":800},
  {"id":"req-002","service":"db","latency_ms":100},
  {"id":"req-005","service":"api","latency_ms":250}
]
```

## Step 2 — Create `latency_report.py`
```python
"""Read-only deterministic latency analysis using sorting and bisect."""
import argparse
from bisect import bisect_left
import json
import math
from pathlib import Path


def nonnegative_number(raw: str) -> float:
    try:
        number = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a number") from exc
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("value must be finite and nonnegative")
    return number


def positive_integer(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an integer") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("value must be positive")
    return value


def validate(records: object) -> list[dict]:
    if not isinstance(records, list) or not records:
        raise ValueError("expected a nonempty JSON array")
    seen = set()
    clean = []
    for position, record in enumerate(records, 1):
        if not isinstance(record, dict) or set(record) != {"id", "service", "latency_ms"}:
            raise ValueError(f"record {position}: expected id, service and latency_ms")
        identifier = record["id"]
        service = record["service"]
        latency = record["latency_ms"]
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"record {position}: invalid id")
        if identifier in seen:
            raise ValueError(f"duplicate id: {identifier}")
        if not isinstance(service, str) or not service.strip():
            raise ValueError(f"record {position}: invalid service")
        if isinstance(latency, bool) or not isinstance(latency, (int, float)):
            raise ValueError(f"record {position}: latency must be numeric")
        if not math.isfinite(latency) or latency < 0:
            raise ValueError(f"record {position}: latency must be finite and nonnegative")
        seen.add(identifier)
        clean.append({"id": identifier, "service": service, "latency_ms": latency})
    return clean


def nearest_rank(sorted_values: list[float], percentile: int) -> float:
    if not sorted_values or not 1 <= percentile <= 100:
        raise ValueError("invalid percentile input")
    index = math.ceil(percentile * len(sorted_values) / 100) - 1
    return sorted_values[index]


def analyze(records: object, threshold: float = 200, top: int = 3) -> dict:
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("invalid threshold")
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError("invalid threshold")
    if isinstance(top, bool) or not isinstance(top, int) or top < 1:
        raise ValueError("invalid top")
    rows = validate(records)
    values = sorted(row["latency_ms"] for row in rows)
    ranked = sorted(rows, key=lambda row: (-row["latency_ms"], row["id"]))
    return {
        "sample_count": len(rows),
        "threshold_ms": threshold,
        "at_or_above_threshold": len(values) - bisect_left(values, threshold),
        "percentile_method": "nearest_rank",
        "p50_ms": nearest_rank(values, 50),
        "p95_ms": nearest_rank(values, 95),
        "p99_ms": nearest_rank(values, 99),
        "top_slowest": ranked[:top],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only SRE latency report")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--threshold", type=nonnegative_number, default=200)
    parser.add_argument("--top", type=positive_integer, default=3)
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as source:
            rows = json.load(source)
        report = analyze(rows, args.threshold, args.top)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 3 — Create `test_latency_report.py`
```python
import argparse
import unittest
from latency_report import analyze, nearest_rank, nonnegative_number, positive_integer, validate

def row(identifier="r1", latency=100, service="api"):
    return {"id": identifier, "service": service, "latency_ms": latency}

class LatencyTests(unittest.TestCase):
    def test_sorted_top(self):
        report = analyze([row("a", 20), row("b", 90)])
        self.assertEqual(report["top_slowest"][0]["id"], "b")
    def test_tie_break(self):
        report = analyze([row("z", 90), row("a", 90)])
        self.assertEqual(report["top_slowest"][0]["id"], "a")
    def test_inclusive_threshold(self):
        self.assertEqual(analyze([row(latency=200)])["at_or_above_threshold"], 1)
    def test_threshold_above_all(self):
        self.assertEqual(analyze([row(latency=5)], threshold=6)["at_or_above_threshold"], 0)
    def test_percentile(self):
        self.assertEqual(nearest_rank([1, 2, 3, 4, 5], 50), 3)
    def test_p95_small_sample(self):
        self.assertEqual(analyze([row("a", 10), row("b", 100)])["p95_ms"], 100)
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            validate([row(), row()])
    def test_empty(self):
        with self.assertRaises(ValueError):
            validate([])
    def test_missing_field(self):
        with self.assertRaises(ValueError):
            validate([{"id": "a", "latency_ms": 10}])
    def test_bool(self):
        with self.assertRaises(ValueError):
            validate([row(latency=True)])
    def test_nan(self):
        with self.assertRaises(ValueError):
            validate([row(latency=float("nan"))])
    def test_negative(self):
        with self.assertRaises(ValueError):
            validate([row(latency=-1)])
    def test_bad_threshold(self):
        with self.assertRaises(ValueError):
            analyze([row()], threshold=-1)
    def test_bad_top(self):
        with self.assertRaises(ValueError):
            analyze([row()], top=0)
    def test_parser_nan(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            nonnegative_number("nan")
    def test_parser_top(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_integer("0")
    def test_invalid_percentile(self):
        with self.assertRaises(ValueError):
            nearest_rank([1, 2], 101)
    def test_input_unchanged(self):
        records = [row()]
        analyze(records)
        self.assertEqual(records[0]["latency_ms"], 100)

if __name__ == "__main__":
    unittest.main()
```

## Step 4 — Execute
```bash
python latency_report.py --input latencies.json --threshold 200 --top 3
python -m unittest -v test_latency_report.py
python -m py_compile latency_report.py
```
Expected: five samples, three at or above 200 ms, p50=250 ms, p95=800 ms, p99=800 ms, top slowest req-004 followed by req-003 then req-005. **18 unit tests** are provided.

## Step 5 — Failure injection
1. Duplicate an ID: reject input.
2. Set latency to `-1`, `true` or `null`: reject input.
3. Use `--threshold nan`: reject argument.
4. Use an empty array: reject input.
5. Use malformed JSON: reject input.

## Troubleshooting
- Different p95 from your monitoring system: verify its percentile algorithm and sampling method.
- Unexpected threshold count: comparison is inclusive (`>=`).
- Incorrect tie order: sort by negative latency then request ID.
- Invalid file: verify UTF-8 and strict JSON syntax.

## Acceptance checklist
- [ ] Correct stable ranking
- [ ] Binary-search threshold counts
- [ ] Documented nearest-rank quantiles
- [ ] All 18 tests pass
- [ ] Invalid telemetry rejected
- [ ] No live infrastructure changes

## Cleanup
Delete only the files created for this lab.
