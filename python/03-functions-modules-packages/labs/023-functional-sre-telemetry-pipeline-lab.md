# Chapter 023 — Hands-on Lab: Functional SRE Telemetry Pipeline

**Python 3.10+ | Standard library only | Offline and read-only**

## Objective and architecture
Build a deterministic pipeline:

```text
synthetic JSONL → bounded line reader → JSON parse → strict validation
→ map(normalize) → filter(eligible events) → reduce(aggregate)
→ sorted JSON report
```

Do not send notifications or connect to production. The report is emitted only after full input validation and aggregation succeed.

## 1. Create `events.jsonl`
```jsonl
{"environment":"prod","service":"api","severity":"info","latency_ms":100}
{"environment":"prod","service":"api","severity":"warning","latency_ms":350}
{"environment":"prod","service":"db","severity":"critical","latency_ms":900}
{"environment":"staging","service":"api","severity":"warning","latency_ms":600}
{"environment":"prod","service":"api","severity":"critical","latency_ms":750}
{"environment":"prod","service":"db","severity":"info","latency_ms":80}
```

## 2. Create `functional_pipeline.py`
```python
"""Read-only streaming SRE telemetry pipeline using functional operators."""
import argparse
from collections import Counter
from functools import reduce
import json
import math
from pathlib import Path

FIELDS = {"environment", "service", "severity", "latency_ms"}
SEVERITIES = ("critical", "warning", "info")


def finite_nonnegative(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return value


def parse_line(line, number):
    try:
        record = json.loads(
            line,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError("invalid JSON constant")),
        )
    except ValueError as exc:
        raise ValueError(f"line {number}: invalid JSON: {exc}") from exc
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError(f"line {number}: invalid schema")
    for field in ("environment", "service"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"line {number}: invalid {field}")
    if record["severity"] not in SEVERITIES or not isinstance(record["severity"], str):
        raise ValueError(f"line {number}: invalid severity")
    try:
        finite_nonnegative(record["latency_ms"], "latency_ms")
    except ValueError as exc:
        raise ValueError(f"line {number}: {exc}") from exc
    return record


def read_records(source, max_line_bytes=65536):
    if isinstance(max_line_bytes, bool) or not isinstance(max_line_bytes, int) or max_line_bytes < 1:
        raise ValueError("max_line_bytes must be positive")
    number = 0
    while True:
        raw = source.readline(max_line_bytes + 1)
        if not raw:
            break
        number += 1
        if len(raw) > max_line_bytes:
            raise ValueError(f"line {number}: byte limit exceeded")
        try:
            line = raw.decode("utf-8")
        except UnicodeError as exc:
            raise ValueError(f"line {number}: invalid UTF-8") from exc
        if line.strip():
            yield parse_line(line, number)


def normalize(record):
    """Return a new record, leaving input unchanged."""
    return {
        "environment": record["environment"],
        "service": record["service"],
        "severity": record["severity"],
        "latency_ms": record["latency_ms"],
    }


def include_environment(environment):
    if not isinstance(environment, str) or not environment.strip():
        raise ValueError("environment must be nonempty")
    return lambda record: record["environment"] == environment


def accumulate(state, record):
    key = (record["environment"], record["service"])
    if key not in state["groups"]:
        if len(state["groups"]) >= state["max_groups"]:
            raise ValueError("group cardinality limit exceeded")
        state["groups"][key] = {
            "count": 0, "slow_count": 0, "max_latency_ms": 0,
            "severities": Counter(),
        }
    group = state["groups"][key]
    group["count"] += 1
    group["slow_count"] += int(record["latency_ms"] >= state["slow_ms"])
    group["max_latency_ms"] = max(group["max_latency_ms"], record["latency_ms"])
    group["severities"][record["severity"]] += 1
    state["event_count"] += 1
    return state


def analyze(records, *, environment="prod", slow_ms=250, max_groups=1000):
    finite_nonnegative(slow_ms, "slow_ms")
    if isinstance(max_groups, bool) or not isinstance(max_groups, int) or max_groups < 1:
        raise ValueError("max_groups must be positive")
    predicate = include_environment(environment)
    # Parse and validate all records before filtering; lazy map/filter still stream.
    transformed = map(normalize, records)
    selected = filter(predicate, transformed)
    state = reduce(accumulate, selected, {
        "event_count": 0, "groups": {}, "slow_ms": slow_ms, "max_groups": max_groups
    })
    groups = [
        {
            "environment": env, "service": service,
            "count": bucket["count"], "slow_count": bucket["slow_count"],
            "max_latency_ms": bucket["max_latency_ms"],
            "severities": {name: bucket["severities"][name] for name in SEVERITIES},
        }
        for (env, service), bucket in sorted(state["groups"].items())
    ]
    return {"environment": environment, "event_count": state["event_count"],
            "slow_threshold_ms": slow_ms, "groups": groups}


def main():
    parser = argparse.ArgumentParser(description="Offline functional telemetry pipeline")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--environment", default="prod")
    parser.add_argument("--slow-ms", default=250, type=float)
    parser.add_argument("--max-groups", default=1000, type=int)
    parser.add_argument("--max-line-bytes", default=65536, type=int)
    args = parser.parse_args()
    try:
        with args.input.open("rb") as source:
            report = analyze(
                read_records(source, args.max_line_bytes),
                environment=args.environment,
                slow_ms=args.slow_ms,
                max_groups=args.max_groups,
            )
    except (OSError, ValueError, TypeError, UnicodeError, OverflowError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Note:** `reduce` uses a mutable accumulator internally to keep O(k) aggregate memory, where k is the number of environment/service groups. This is an explicit stateful fold, not a mathematically pure reduction. The pipeline validates every source record through `read_records` before filtering by environment.

## 3. Create `test_functional_pipeline.py`
```python
import io
import json
import unittest
from functional_pipeline import (
    analyze, finite_nonnegative, include_environment, normalize,
    parse_line, read_records,
)


def event(env="prod", service="api", severity="info", latency=100):
    return {"environment": env, "service": service,
            "severity": severity, "latency_ms": latency}


def encoded(*rows):
    return io.BytesIO("".join(json.dumps(row) + "\n" for row in rows).encode())


class PipelineTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_line(json.dumps(event()), 1)["service"], "api")
    def test_invalid_json(self):
        with self.assertRaises(ValueError):
            parse_line("{bad", 1)
    def test_non_object(self):
        with self.assertRaises(ValueError):
            parse_line("[]", 1)
    def test_missing_field(self):
        with self.assertRaises(ValueError):
            parse_line('{"service":"api"}', 1)
    def test_unknown_field(self):
        row = event()
        row["extra"] = 1
        with self.assertRaises(ValueError):
            parse_line(json.dumps(row), 1)
    def test_invalid_severity(self):
        with self.assertRaises(ValueError):
            parse_line(json.dumps(event(severity="urgent")), 1)
    def test_boolean_latency(self):
        with self.assertRaises(ValueError):
            parse_line(json.dumps(event(latency=True)), 1)
    def test_negative_latency(self):
        with self.assertRaises(ValueError):
            parse_line(json.dumps(event(latency=-1)), 1)
    def test_nan_latency(self):
        with self.assertRaises(ValueError):
            finite_nonnegative(float("nan"), "latency")
    def test_inf_latency(self):
        with self.assertRaises(ValueError):
            finite_nonnegative(float("inf"), "latency")
    def test_blank_lines(self):
        self.assertEqual(list(read_records(io.BytesIO(b"\n"))), [])
    def test_line_limit(self):
        with self.assertRaises(ValueError):
            list(read_records(io.BytesIO(b"x" * 20), 10))
    def test_invalid_utf8(self):
        with self.assertRaises(ValueError):
            list(read_records(io.BytesIO(b"\xff\n")))
    def test_laziness(self):
        stream = read_records(encoded(event()))
        self.assertEqual(next(stream)["service"], "api")
        self.assertEqual(list(stream), [])
    def test_normalize_no_mutation(self):
        original = event()
        result = normalize(original)
        self.assertEqual(original, result)
        self.assertIsNot(original, result)
    def test_predicate(self):
        self.assertTrue(include_environment("prod")(event()))
    def test_predicate_invalid(self):
        with self.assertRaises(ValueError):
            include_environment("")
    def test_empty(self):
        self.assertEqual(analyze([])["event_count"], 0)
    def test_counts(self):
        result = analyze([event(), event(latency=300)])
        self.assertEqual(result["groups"][0]["count"], 2)
    def test_slow_boundary(self):
        result = analyze([event(latency=250)])
        self.assertEqual(result["groups"][0]["slow_count"], 1)
    def test_filter_environment(self):
        result = analyze([event(), event(env="staging")])
        self.assertEqual(result["event_count"], 1)
    def test_max_latency(self):
        result = analyze([event(latency=20), event(latency=900)])
        self.assertEqual(result["groups"][0]["max_latency_ms"], 900)
    def test_severity_counts(self):
        result = analyze([event(severity="critical")])
        self.assertEqual(result["groups"][0]["severities"]["critical"], 1)
    def test_sort_groups(self):
        result = analyze([event(service="z"), event(service="a")])
        self.assertEqual(result["groups"][0]["service"], "a")
    def test_cardinality_limit(self):
        with self.assertRaises(ValueError):
            analyze([event(service="a"), event(service="b")], max_groups=1)
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            analyze([], slow_ms=-1)
    def test_invalid_group_limit(self):
        with self.assertRaises(ValueError):
            analyze([], max_groups=0)
    def test_deterministic(self):
        rows = [event(), event(service="db")]
        self.assertEqual(analyze(rows), analyze(rows))
    def test_filtered_bad_record_rejected(self):
        bad = event(env="staging", latency=-1)
        with self.assertRaises(ValueError):
            analyze(read_records(encoded(bad)), environment="prod")
    def test_reduction_empty_initializer(self):
        self.assertEqual(analyze(iter(()))["groups"], [])


if __name__ == "__main__":
    unittest.main()
```

## 4. Run
```bash
python functional_pipeline.py --input events.jsonl
python functional_pipeline.py --input events.jsonl --environment staging
python -m unittest -v test_functional_pipeline.py
python -m py_compile functional_pipeline.py
```

Expected default output: **5 prod events**; `prod/api` has 3 events, 2 slow (350 and 750), maximum 750; `prod/db` has 2 events, 1 slow (900), maximum 900. The staging event is excluded from counts but still validated. **30 unit tests** are included.

## 5. Failure injection
1. Append malformed JSON: reject without outputting a report.
2. Put a negative latency in a staging record while filtering prod: still reject.
3. Set `--slow-ms nan`: reject.
4. Set `--max-groups 1`: reject when a second prod service appears.
5. Set `--max-line-bytes 10`: reject oversized record.
6. Use invalid UTF-8: reject with line number.
7. Re-run with identical input: output must be deterministic.

## 6. Troubleshooting
| Issue | Cause | Response |
|---|---|---|
| Missing service | Wrong environment filter | Check `--environment` |
| Empty second pass | Iterator exhausted | Rebuild pipeline |
| Unexpected parse failure | Invalid record in excluded environment | Validate whole input; correct fixture |
| High memory | Unbounded service cardinality | Enforce `--max-groups` |
| `TypeError` in custom callback | Wrong record contract | Validate before map/filter |

## 7. Production limitations
This is an educational, read-only batch pipeline. It does not implement telemetry timestamps, freshness, deduplication, checkpointing, late arrivals, distributed state, alert routing, or SLO burn-rate policy. Do not interpret slow-event counts as approved incident thresholds.

## Acceptance checklist
- [ ] 30 tests pass locally.
- [ ] JSONL processed incrementally.
- [ ] All records validated before filtering.
- [ ] Map, filter and reduce used intentionally.
- [ ] Deterministic summaries.
- [ ] Cardinality and physical-line limits.
- [ ] No external side effects.
