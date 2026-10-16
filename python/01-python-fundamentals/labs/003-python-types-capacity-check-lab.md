# Chapter 003 — Hands-on Lab: Disk Capacity Alert CLI

## Scenario
Create a dependency-free, read-only Python CLI that accepts disk usage values, classifies them, emits JSON, and uses meaningful exit codes. This lab does not access actual production disks.

## Prerequisites
Python 3.10+ and a local workspace. Use the virtual environment created in Chapter 002 when available.

## Step 1 — Create `capacity_check.py`
```python
"""Read-only disk capacity classification exercise."""
import argparse
import json
import math


def finite_number(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be numeric") from exc
    if not math.isfinite(value):
        raise argparse.ArgumentTypeError("must be finite")
    return value


def classify(used: float, total: float, warning: float = 80.0,
             critical: float = 90.0) -> dict[str, float | str]:
    if not all(math.isfinite(x) for x in (used, total, warning, critical)):
        raise ValueError("all values must be finite")
    if total <= 0 or used < 0 or used > total:
        raise ValueError("require 0 <= used <= total and total > 0")
    if not 0 <= warning < critical <= 100:
        raise ValueError("require 0 <= warning < critical <= 100")
    pct = used / total * 100
    status = "critical" if pct >= critical else "warning" if pct >= warning else "healthy"
    return {"used": used, "total": total, "percent": round(pct, 2), "status": status}


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulated disk capacity alert")
    parser.add_argument("--used", type=finite_number, required=True)
    parser.add_argument("--total", type=finite_number, required=True)
    parser.add_argument("--warning", type=finite_number, default=80.0)
    parser.add_argument("--critical", type=finite_number, default=90.0)
    args = parser.parse_args()
    try:
        result = classify(args.used, args.total, args.warning, args.critical)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return {"healthy": 0, "warning": 1, "critical": 2}[str(result["status"])]


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 2 — Create `test_capacity_check.py`
```python
import unittest
from capacity_check import classify, finite_number
import argparse


class CapacityCheckTests(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(classify(40, 100)["status"], "healthy")

    def test_warning_boundary(self):
        self.assertEqual(classify(80, 100)["status"], "warning")

    def test_critical_boundary(self):
        self.assertEqual(classify(90, 100)["status"], "critical")

    def test_invalid_total(self):
        with self.assertRaises(ValueError):
            classify(1, 0)

    def test_over_capacity(self):
        with self.assertRaises(ValueError):
            classify(101, 100)

    def test_nan_rejected(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            finite_number("nan")

    def test_bad_thresholds(self):
        with self.assertRaises(ValueError):
            classify(50, 100, 95, 90)


if __name__ == "__main__":
    unittest.main()
```

## Step 3 — Execute and validate
Run:
```bash
python capacity_check.py --used 40 --total 100
python capacity_check.py --used 80 --total 100
python capacity_check.py --used 90 --total 100
python -m unittest -v test_capacity_check.py
python -m py_compile capacity_check.py
```

Expected CLI classifications are `healthy`, `warning`, and `critical`. Exit codes are 0, 1, and 2 respectively; nonzero codes are intentional alert states. Run commands separately so your shell doesn't treat an alert state as an unexpected pipeline failure.

## Step 4 — Negative testing
```bash
python capacity_check.py --used 101 --total 100
python capacity_check.py --used nan --total 100
python capacity_check.py --used 5 --total 0
python capacity_check.py --used 10 --total 100 --warning 95 --critical 90
```
Each should reject input with a clear usage error and nonzero exit status. The lab is intentionally simulation-only.

## Step 5 — Exercises
1. Change thresholds to 75 and 85 and repeat boundary tests.
2. Add a `--volume` label that is safe for logs.
3. Explain why percentages are computed from numeric types, not strings.
4. Add a test for negative usage.

## Troubleshooting
- `python` not found: invoke the Chapter 002 virtual environment interpreter.
- `ValueError` for bad inputs: expected defensive validation.
- A warning/critical command returns nonzero: expected classification behavior, not a Python crash.
- Unit test import failure: run from the directory containing both files.

## Acceptance checklist
- [ ] Python 3.10+ confirmed
- [ ] Healthy, warning, critical outputs verified
- [ ] Seven unit tests pass
- [ ] Invalid inputs rejected
- [ ] Exit codes checked
- [ ] Exercises completed

## Cleanup
Remove only the local lab files you created. Do not run this simulated checker as a production alert source without additional design and testing.
