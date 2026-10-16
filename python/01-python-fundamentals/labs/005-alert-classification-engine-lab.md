# Chapter 005 — Hands-on Lab: SRE Alert Classification Engine

## Scenario
Build a deterministic, read-only command-line tool that classifies CPU, memory, and application error-rate percentages. It simulates telemetry input and does not connect to production monitoring systems.

## Prerequisites
Python 3.10+, a terminal, and a writable lab directory. No third-party dependencies.

## Step 1 — Create `alert_engine.py`
```python
"""SRE alert classification simulation. No external side effects."""
import argparse
import json
import math
from typing import Any

SEVERITY_EXIT = {"healthy": 0, "warning": 1, "critical": 2, "unknown": 3}


def classify(cpu: float | None, memory: float | None,
             error_rate: float | None) -> dict[str, Any]:
    metrics = {"cpu_pct": cpu, "memory_pct": memory, "error_rate_pct": error_rate}
    for name, value in metrics.items():
        if value is None:
            return {"severity": "unknown", "reason": f"missing {name}", "metrics": metrics}
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return {"severity": "unknown", "reason": f"invalid {name}", "metrics": metrics}
        if not math.isfinite(value) or not 0 <= value <= 100:
            return {"severity": "unknown", "reason": f"out-of-range {name}", "metrics": metrics}

    if cpu >= 95 or memory >= 95 or error_rate >= 10:
        severity = "critical"
    elif cpu >= 80 or memory >= 85 or error_rate >= 5:
        severity = "warning"
    else:
        severity = "healthy"

    return {"severity": severity, "reason": "threshold policy", "metrics": metrics}


def percentage(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected numeric percentage") from exc
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise argparse.ArgumentTypeError("expected finite percentage from 0 to 100")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only SRE alert simulation")
    parser.add_argument("--cpu", type=percentage)
    parser.add_argument("--memory", type=percentage)
    parser.add_argument("--errors", type=percentage)
    args = parser.parse_args()
    result = classify(args.cpu, args.memory, args.errors)
    print(json.dumps(result, sort_keys=True))
    return SEVERITY_EXIT[result["severity"]]


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 2 — Create `test_alert_engine.py`
```python
import argparse
import unittest
from alert_engine import classify, percentage, SEVERITY_EXIT


class AlertEngineTests(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(classify(30, 40, 0)["severity"], "healthy")

    def test_cpu_warning_boundary(self):
        self.assertEqual(classify(80, 40, 0)["severity"], "warning")

    def test_memory_warning_boundary(self):
        self.assertEqual(classify(30, 85, 0)["severity"], "warning")

    def test_error_warning_boundary(self):
        self.assertEqual(classify(30, 40, 5)["severity"], "warning")

    def test_cpu_critical_boundary(self):
        self.assertEqual(classify(95, 40, 0)["severity"], "critical")

    def test_memory_critical_boundary(self):
        self.assertEqual(classify(30, 95, 0)["severity"], "critical")

    def test_error_critical_boundary(self):
        self.assertEqual(classify(30, 40, 10)["severity"], "critical")

    def test_critical_precedes_warning(self):
        self.assertEqual(classify(80, 95, 5)["severity"], "critical")

    def test_missing_metric_unknown(self):
        self.assertEqual(classify(None, 40, 0)["severity"], "unknown")

    def test_nan_unknown(self):
        self.assertEqual(classify(float("nan"), 40, 0)["severity"], "unknown")

    def test_invalid_bool_unknown(self):
        self.assertEqual(classify(True, 40, 0)["severity"], "unknown")

    def test_out_of_range_unknown(self):
        self.assertEqual(classify(101, 40, 0)["severity"], "unknown")

    def test_cli_parser_rejects_nan(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            percentage("nan")

    def test_exit_code_mapping(self):
        self.assertEqual(SEVERITY_EXIT["critical"], 2)
        self.assertEqual(SEVERITY_EXIT["unknown"], 3)


if __name__ == "__main__":
    unittest.main()
```

## Step 3 — Run
```bash
python alert_engine.py --cpu 30 --memory 40 --errors 0
python alert_engine.py --cpu 80 --memory 40 --errors 0
python alert_engine.py --cpu 95 --memory 40 --errors 0
python alert_engine.py --cpu 30 --memory 40
python -m unittest -v test_alert_engine.py
python -m py_compile alert_engine.py
```

Expected severities: healthy, warning, critical, unknown. Exit codes: 0, 1, 2, 3 respectively. These nonzero codes are intentional classifications.

## Step 4 — Failure injection
```bash
python alert_engine.py --cpu nan --memory 40 --errors 0
python alert_engine.py --cpu 101 --memory 40 --errors 0
python alert_engine.py --cpu abc --memory 40 --errors 0
```
Each command should fail argument validation with a clear usage error. Note that argparse's default error exit code is 2, also used here for critical severity; **consumers must inspect JSON output as well as exit status**, or choose a distinct exit-code scheme before production integration.

## Step 5 — Design review
- Severity precedence: critical > warning > healthy.
- Missing or invalid telemetry: unknown, not healthy.
- A point-in-time sample does not establish sustained SLO violation.
- No paging, ticket creation, remediation or production mutation occurs.
- Thresholds are examples and must be calibrated to workload baselines and alert policy.

## Step 6 — Exercises
1. Add a latency metric with documented thresholds.
2. Add a test for exactly 79.99% CPU.
3. Add a test that `memory=94.99` is warning.
4. Add an optional `--service` identifier and safely include it in JSON.

## Acceptance checklist
- [ ] All four severity paths verified
- [ ] Fourteen unit tests pass
- [ ] Missing/invalid input handled
- [ ] Critical precedence validated
- [ ] JSON parsed successfully
- [ ] No production side effects

## Troubleshooting
`python` not found: use `py -3` on Windows or the Chapter 002 virtual environment. Import error: run the tests from the directory containing both files. Unexpected alert code: inspect JSON severity, not just the process exit status.

## Cleanup
Remove only files created for this lab when finished.
