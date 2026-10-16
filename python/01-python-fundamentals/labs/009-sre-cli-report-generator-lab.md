# Chapter 009 — Hands-on Lab: SRE CLI Report Generator

## Scenario
Build a read-only CLI that accepts a local JSON list of services and latency measurements and emits deterministic JSON, CSV or text reports. No cloud, Kubernetes or production API access.

## Prerequisites
Python 3.10+; standard library only.

## Step 1 — Create `services.json`
```json
[
  {"service": "api", "latency_ms": 125, "environment": "prod"},
  {"service": "worker", "latency_ms": 850, "environment": "staging"},
  {"service": "scheduler", "latency_ms": 410, "environment": "prod"}
]
```

## Step 2 — Create `service_report.py`
```python
"""Read-only service latency report; local fixture input only."""
import argparse
import csv
import io
import json
import math
from pathlib import Path

ENVIRONMENTS = {"dev", "staging", "prod"}


def validate(records: object) -> list[dict]:
    if not isinstance(records, list):
        raise ValueError("expected a JSON array")
    result = []
    seen = set()
    for number, row in enumerate(records, 1):
        if not isinstance(row, dict):
            raise ValueError(f"entry {number} must be an object")
        name, env, latency = row.get("service"), row.get("environment"), row.get("latency_ms")
        if not isinstance(name, str) or not name or not name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"entry {number}: invalid service")
        if env not in ENVIRONMENTS:
            raise ValueError(f"entry {number}: invalid environment")
        if isinstance(latency, bool) or not isinstance(latency, (int, float)):
            raise ValueError(f"entry {number}: invalid latency")
        if not math.isfinite(latency) or latency < 0:
            raise ValueError(f"entry {number}: latency must be finite and nonnegative")
        key = (env, name)
        if key in seen:
            raise ValueError(f"duplicate service in environment: {env}/{name}")
        seen.add(key)
        result.append({"service": name, "environment": env, "latency_ms": latency})
    return sorted(result, key=lambda item: (item["environment"], item["service"]))


def render(rows: list[dict], output_format: str) -> str:
    if output_format == "json":
        return json.dumps({"count": len(rows), "services": rows}, indent=2, allow_nan=False) + "\n"
    if output_format == "csv":
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=["environment", "service", "latency_ms"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue()
    if output_format == "text":
        return "".join(f"{row['environment']:<10} {row['service']:<20} {row['latency_ms']:>10.1f} ms\n" for row in rows)
    raise ValueError("unsupported format")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only service latency report")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--format", choices=("json", "csv", "text"), default="json")
    parser.add_argument("--environment", choices=sorted(ENVIRONMENTS))
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as handle:
            data = json.load(handle)
        rows = validate(data)
        if args.environment:
            rows = [row for row in rows if row["environment"] == args.environment]
        output = render(rows, args.format)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 3 — Create `test_service_report.py`
```python
import csv
import io
import json
import unittest
from service_report import render, validate

def entry(name="api", env="prod", latency=100):
    return {"service": name, "environment": env, "latency_ms": latency}

class ServiceReportTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(len(validate([entry()])), 1)
    def test_sorted(self):
        rows = validate([entry("z"), entry("a")])
        self.assertEqual([row["service"] for row in rows], ["a", "z"])
    def test_empty(self):
        self.assertEqual(validate([]), [])
    def test_invalid_root(self):
        with self.assertRaises(ValueError):
            validate({})
    def test_missing_name(self):
        with self.assertRaises(ValueError):
            validate([entry(name="")])
    def test_invalid_environment(self):
        with self.assertRaises(ValueError):
            validate([entry(env="unknown")])
    def test_negative_latency(self):
        with self.assertRaises(ValueError):
            validate([entry(latency=-1)])
    def test_nan_latency(self):
        with self.assertRaises(ValueError):
            validate([entry(latency=float("nan"))])
    def test_bool_latency(self):
        with self.assertRaises(ValueError):
            validate([entry(latency=True)])
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            validate([entry(), entry()])
    def test_json_output(self):
        self.assertEqual(json.loads(render(validate([entry()]), "json"))["count"], 1)
    def test_csv_output(self):
        rows = list(csv.DictReader(io.StringIO(render(validate([entry()]), "csv"))))
        self.assertEqual(rows[0]["service"], "api")
    def test_text_output(self):
        self.assertIn("api", render(validate([entry()]), "text"))
    def test_invalid_format(self):
        with self.assertRaises(ValueError):
            render([], "xml")

if __name__ == "__main__":
    unittest.main()
```

## Step 4 — Execute
```bash
python service_report.py --input services.json --format json
python service_report.py --input services.json --format csv
python service_report.py --input services.json --format text
python service_report.py --input services.json --format json --environment prod
python -m unittest -v test_service_report.py
python -m py_compile service_report.py
```
Expected: three services overall, two for prod, and fourteen passing tests. All successful commands exit 0.

## Step 5 — Failure injection
1. Change latency to `-1`: rejected.
2. Duplicate an environment/service pair: rejected.
3. Supply an invalid JSON document: parser error.
4. Use a missing file: parser error.
5. Request `--format xml`: argparse usage error.

## Operational considerations
- No production system calls or writes.
- JSON and CSV are deterministic and machine-readable.
- Missing telemetry is a validation error, not a healthy result.
- The fixture uses trusted service identifiers. If exporting arbitrary strings to spreadsheets, address CSV formula injection explicitly.
- Empty input currently produces an empty report; production monitoring should define a separate no-data policy.

## Acceptance checklist
- [ ] JSON, CSV and text outputs work
- [ ] Environment filter works
- [ ] Fourteen unit tests pass
- [ ] Invalid data rejected
- [ ] Output contains no diagnostics on stdout
- [ ] No infrastructure changed

## Cleanup
Delete only files created for this lab.
