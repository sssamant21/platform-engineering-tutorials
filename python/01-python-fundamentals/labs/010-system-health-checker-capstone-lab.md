# Chapter 010 — Hands-on Lab: System Health Checker Capstone

## Objective
Build and test a **read-only** fleet health checker using Python fundamentals. Input is a local synthetic JSON fixture; there are no live host checks or infrastructure changes.

## Prerequisites
Python 3.10+ and a writable lab directory. Standard library only.

## Step 1 — Create `hosts.json`
```json
[
  {"name":"node-a","cpu_pct":45,"memory_pct":60,"disk_pct":50},
  {"name":"node-b","cpu_pct":81,"memory_pct":70,"disk_pct":65},
  {"name":"node-c","cpu_pct":92,"memory_pct":91,"disk_pct":96}
]
```

## Step 2 — Create `health_checker.py`
```python
"""Read-only health-check simulation using a local JSON fixture."""
import argparse
import json
import math
from pathlib import Path

THRESHOLDS = {
    "cpu_pct": (75, 90),
    "memory_pct": (80, 95),
    "disk_pct": (80, 95),
}
EXIT_CODES = {"healthy": 0, "warning": 1, "critical": 2}


def validate(records: object) -> list[dict]:
    if not isinstance(records, list) or not records:
        raise ValueError("expected a nonempty JSON array of hosts")
    clean = []
    seen = set()
    for number, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"host {number} must be an object")
        name = record.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"host {number} requires a nonempty name")
        if name in seen:
            raise ValueError(f"duplicate host name: {name}")
        seen.add(name)
        validated = {"name": name}
        for field in THRESHOLDS:
            value = record.get(field)
            if (isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or not 0 <= value <= 100):
                raise ValueError(f"host {name}: {field} must be finite and in [0, 100]")
            validated[field] = value
        clean.append(validated)
    return sorted(clean, key=lambda item: item["name"])


def classify(host: dict) -> str:
    if any(host[field] >= critical for field, (_, critical) in THRESHOLDS.items()):
        return "critical"
    if any(host[field] >= warning for field, (warning, _) in THRESHOLDS.items()):
        return "warning"
    return "healthy"


def analyze(records: object) -> dict:
    hosts = validate(records)
    counts = {"healthy": 0, "warning": 0, "critical": 0}
    results = []
    for host in hosts:
        severity = classify(host)
        counts[severity] += 1
        results.append({**host, "severity": severity})
    overall = "critical" if counts["critical"] else "warning" if counts["warning"] else "healthy"
    return {"overall": overall, "counts": counts, "hosts": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only simulated host health checker")
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as handle:
            data = json.load(handle)
        report = analyze(data)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return EXIT_CODES[report["overall"]]


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 3 — Create `test_health_checker.py`
```python
import unittest
from health_checker import analyze, classify, validate

def host(name="node-a", cpu=20, memory=30, disk=40):
    return {"name": name, "cpu_pct": cpu, "memory_pct": memory, "disk_pct": disk}

class HealthCheckerTests(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(classify(host()), "healthy")
    def test_cpu_warning_boundary(self):
        self.assertEqual(classify(host(cpu=75)), "warning")
    def test_cpu_critical_boundary(self):
        self.assertEqual(classify(host(cpu=90)), "critical")
    def test_memory_warning_boundary(self):
        self.assertEqual(classify(host(memory=80)), "warning")
    def test_memory_critical_boundary(self):
        self.assertEqual(classify(host(memory=95)), "critical")
    def test_disk_warning_boundary(self):
        self.assertEqual(classify(host(disk=80)), "warning")
    def test_disk_critical_boundary(self):
        self.assertEqual(classify(host(disk=95)), "critical")
    def test_critical_precedence(self):
        self.assertEqual(classify(host(cpu=75, disk=95)), "critical")
    def test_duplicate_names(self):
        with self.assertRaises(ValueError):
            validate([host(), host()])
    def test_missing_metric(self):
        bad = host()
        del bad["cpu_pct"]
        with self.assertRaises(ValueError):
            validate([bad])
    def test_nan(self):
        with self.assertRaises(ValueError):
            validate([host(cpu=float("nan"))])
    def test_boolean(self):
        with self.assertRaises(ValueError):
            validate([host(cpu=True)])
    def test_out_of_range(self):
        with self.assertRaises(ValueError):
            validate([host(cpu=101)])
    def test_empty_input(self):
        with self.assertRaises(ValueError):
            validate([])
    def test_sorted_hosts(self):
        result = analyze([host("z"), host("a")])
        self.assertEqual([item["name"] for item in result["hosts"]], ["a", "z"])
    def test_fleet_overall(self):
        self.assertEqual(analyze([host("a"), host("b", cpu=92)])["overall"], "critical")

if __name__ == "__main__":
    unittest.main()
```

## Step 4 — Execute
```bash
python health_checker.py --input hosts.json
python -m unittest -v test_health_checker.py
python -m py_compile health_checker.py
```

Expected: 1 healthy, 1 warning, 1 critical, overall critical. Exit code 2 for the critical report is intentional. **Sixteen unit tests** should pass.

## Step 5 — Failure injection
1. Remove `disk_pct` from one host: validation error.
2. Set CPU to `101`: validation error.
3. Duplicate a host name: validation error.
4. Use an empty JSON list: validation error.
5. Use malformed JSON: parse error.
6. Restore the original fixture after each test.

## Step 6 — Evidence and assessment
Record your Python version, command outputs, passing test count, one invalid-input example and the JSON summary. Do not include secrets or production hostnames.

| Criterion | Points |
|---|---:|
| Schema validation | 25 |
| Threshold correctness | 25 |
| CLI/JSON output | 15 |
| Tests and failure injection | 20 |
| Operational safety | 15 |

Pass target: at least 85/100, with no missing validation controls.

## Troubleshooting
- Python unavailable: activate the Chapter 002 virtual environment or use `py -3` on Windows.
- `FileNotFoundError`: run from the directory containing `hosts.json` or pass an absolute path.
- `JSONDecodeError`: verify commas, quotes and brackets.
- Unexpected nonzero exit: inspect whether a valid JSON report was printed; the lab intentionally uses exit 2 for critical severity and argparse errors, so automation must distinguish them.

## Operational guardrails
This is a synthetic, point-in-time exercise. It does not measure live CPU, memory or disk usage. Production tooling should enforce fixture size limits, freshness checks, observability SLOs and a distinct error exit code before integration.

## Cleanup
Remove only the files created for this lab.
