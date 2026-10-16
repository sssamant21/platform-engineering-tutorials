# Chapter 004 — Hands-on Lab: CPU Request Headroom Calculator

## Goal
Create a read-only, dependency-free CLI for comparing simulated Kubernetes CPU requests against allocatable millicores. **This does not measure actual CPU usage or contact a cluster.**

## Prerequisites
Python 3.10+, a writable workspace, and optionally the Chapter 002 virtual environment.

## Step 1: Create `headroom.py`
```python
import argparse
import json
import math

def finite_nonnegative(raw: str) -> float:
    try:
        number = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a number") from exc
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("expected a finite nonnegative number")
    return number

def calculate(requested: float, allocatable: float,
              warning: float = 75, critical: float = 90) -> dict:
    if not all(math.isfinite(x) for x in (requested, allocatable, warning, critical)):
        raise ValueError("all values must be finite")
    if requested < 0 or allocatable <= 0:
        raise ValueError("requested >= 0 and allocatable > 0 required")
    if not 0 <= warning < critical <= 100:
        raise ValueError("invalid thresholds")
    percent = requested / allocatable * 100
    status = "critical" if percent >= critical else "warning" if percent >= warning else "healthy"
    return {"requested_millicores": requested,
            "allocatable_millicores": allocatable,
            "headroom_millicores": allocatable - requested,
            "request_ratio_pct": round(percent, 2),
            "overcommitted": requested > allocatable,
            "status": status}

def main() -> int:
    parser = argparse.ArgumentParser(description="Simulated CPU request headroom")
    parser.add_argument("--requested", type=finite_nonnegative, required=True)
    parser.add_argument("--allocatable", type=finite_nonnegative, required=True)
    parser.add_argument("--warning", type=finite_nonnegative, default=75)
    parser.add_argument("--critical", type=finite_nonnegative, default=90)
    args = parser.parse_args()
    try:
        result = calculate(args.requested, args.allocatable, args.warning, args.critical)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return {"healthy": 0, "warning": 1, "critical": 2}[result["status"]]

if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 2: Create `test_headroom.py`
```python
import argparse
import unittest
from headroom import calculate, finite_nonnegative

class TestHeadroom(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(calculate(1000, 4000)["status"], "healthy")
    def test_warning(self):
        self.assertEqual(calculate(3000, 4000)["status"], "warning")
    def test_critical(self):
        self.assertEqual(calculate(3600, 4000)["status"], "critical")
    def test_overcommit(self):
        self.assertEqual(calculate(5000, 4000)["headroom_millicores"], -1000)
    def test_zero_capacity(self):
        with self.assertRaises(ValueError):
            calculate(100, 0)
    def test_negative_request(self):
        with self.assertRaises(ValueError):
            calculate(-1, 100)
    def test_nan(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            finite_nonnegative("nan")
    def test_bad_thresholds(self):
        with self.assertRaises(ValueError):
            calculate(50, 100, 95, 90)

if __name__ == "__main__":
    unittest.main()
```

## Step 3: Run the lab
```bash
python headroom.py --requested 1000 --allocatable 4000
python headroom.py --requested 3000 --allocatable 4000
python headroom.py --requested 3600 --allocatable 4000
python headroom.py --requested 5000 --allocatable 4000
python -m unittest -v test_headroom.py
python -m py_compile headroom.py
```

Expected statuses: healthy, warning, critical, critical. Exit codes are 0, 1, 2, 2 respectively; nonzero status is intentional. Expected: eight passing tests.

## Step 4: Negative scenarios
```bash
python headroom.py --requested 100 --allocatable 0
python headroom.py --requested nan --allocatable 4000
python headroom.py --requested -10 --allocatable 4000
python headroom.py --requested 100 --allocatable 4000 --warning 95 --critical 90
```
Each command should reject invalid input with a clear usage error.

## Step 5: Exercises and acceptance
- [ ] Test exact 75% and 90% threshold boundaries
- [ ] Test overcommit and negative headroom
- [ ] Confirm all eight unit tests pass
- [ ] Explain the difference between requested-to-allocatable ratio and observed CPU utilization
- [ ] Add an optional node label without changing calculations
- [ ] Confirm no cloud or Kubernetes credentials are used

## Troubleshooting
`ModuleNotFoundError`: run tests in the same directory as the script. `python` missing: use the Chapter 002 venv interpreter or `py -3` on Windows. Nonzero warning/critical exit codes are expected; invalid values are errors.

## Cleanup
Remove only the local files created for this lab.
