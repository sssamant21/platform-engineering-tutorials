# Chapter 021 — Hands-on Lab: Reusable SRE Alert Classification Functions

**Python 3.10+ | Standard library | Read-only**

## Objective
Separate pure decision functions from JSON file I/O. Implement contracts, inclusive thresholds, strict validation, and automated tests. No production alerts are sent.

## Fixture: `metrics.json`
```json
[
  {"service":"api","latency_ms":120,"errors":1,"requests":100},
  {"service":"db","latency_ms":720,"errors":12,"requests":100},
  {"service":"worker","latency_ms":280,"errors":4,"requests":100}
]
```

## Library: `sre_policy.py`
```python
"""Pure SRE metric classification functions with explicit contracts."""
import math


def nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return float(value)


def classify_latency(latency_ms, *, warning_ms=200, critical_ms=500):
    latency = nonnegative(latency_ms, "latency_ms")
    warning = nonnegative(warning_ms, "warning_ms")
    critical = nonnegative(critical_ms, "critical_ms")
    if not 0 < warning < critical:
        raise ValueError("require 0 < warning_ms < critical_ms")
    if latency >= critical:
        return "critical"
    if latency >= warning:
        return "warning"
    return "healthy"


def error_rate(errors, requests):
    if isinstance(errors, bool) or isinstance(requests, bool):
        raise TypeError("counts must be integers")
    if not isinstance(errors, int) or not isinstance(requests, int):
        raise TypeError("counts must be integers")
    if requests < 1 or not 0 <= errors <= requests:
        raise ValueError("require requests >= 1 and 0 <= errors <= requests")
    return errors / requests


def classify_error_rate(rate, *, warning_rate=0.02, critical_rate=0.10):
    fraction = nonnegative(rate, "rate")
    warning = nonnegative(warning_rate, "warning_rate")
    critical = nonnegative(critical_rate, "critical_rate")
    if fraction > 1 or not 0 < warning < critical <= 1:
        raise ValueError("invalid error-rate policy")
    if fraction >= critical:
        return "critical"
    if fraction >= warning:
        return "warning"
    return "healthy"


def classify_service(record, *, warning_ms=200, critical_ms=500,
                     warning_rate=0.02, critical_rate=0.10):
    if not isinstance(record, dict) or set(record) != {"service", "latency_ms", "errors", "requests"}:
        raise ValueError("expected service, latency_ms, errors, requests")
    service = record["service"]
    if not isinstance(service, str) or not service.strip():
        raise ValueError("service must be nonempty")
    latency = nonnegative(record["latency_ms"], "latency_ms")
    rate = error_rate(record["errors"], record["requests"])
    latency_status = classify_latency(latency, warning_ms=warning_ms, critical_ms=critical_ms)
    error_status = classify_error_rate(rate, warning_rate=warning_rate, critical_rate=critical_rate)
    priority = {"healthy": 0, "warning": 1, "critical": 2}
    return {
        "service": service,
        "latency_ms": latency,
        "error_rate": round(rate, 6),
        "latency_status": latency_status,
        "error_status": error_status,
        "overall_status": max((latency_status, error_status), key=priority.__getitem__),
    }


def classify_all(records, **policy):
    if not isinstance(records, list):
        raise ValueError("expected JSON array")
    seen = set()
    decisions = []
    for record in records:
        result = classify_service(record, **policy)
        if result["service"] in seen:
            raise ValueError("duplicate service")
        seen.add(result["service"])
        decisions.append(result)
    decisions.sort(key=lambda item: item["service"])
    return {
        "service_count": len(decisions),
        "critical_count": sum(x["overall_status"] == "critical" for x in decisions),
        "warning_count": sum(x["overall_status"] == "warning" for x in decisions),
        "services": decisions,
    }
```

## CLI: `classify_metrics.py`
```python
import argparse
import json
from pathlib import Path
from sre_policy import classify_all

def main():
    parser = argparse.ArgumentParser(description="Offline SRE metric classifier")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as source:
            report = classify_all(json.load(source))
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

## Automated tests: `test_sre_policy.py`
```python
import unittest
from sre_policy import classify_all, classify_error_rate, classify_latency, classify_service, error_rate

def row(service="api", latency=100, errors=1, requests=100):
    return {"service": service, "latency_ms": latency, "errors": errors, "requests": requests}

class PolicyTests(unittest.TestCase):
    def test_latency_healthy(self): self.assertEqual(classify_latency(100), "healthy")
    def test_latency_warning(self): self.assertEqual(classify_latency(200), "warning")
    def test_latency_critical(self): self.assertEqual(classify_latency(500), "critical")
    def test_latency_negative(self):
        with self.assertRaises(ValueError): classify_latency(-1)
    def test_latency_boolean(self):
        with self.assertRaises(TypeError): classify_latency(True)
    def test_latency_nan(self):
        with self.assertRaises(ValueError): classify_latency(float("nan"))
    def test_threshold_order(self):
        with self.assertRaises(ValueError): classify_latency(10, warning_ms=500, critical_ms=200)
    def test_keyword_only(self):
        with self.assertRaises(TypeError): classify_latency(100, 200, 500)
    def test_error_rate(self): self.assertEqual(error_rate(2, 100), 0.02)
    def test_zero_requests(self):
        with self.assertRaises(ValueError): error_rate(0, 0)
    def test_excess_errors(self):
        with self.assertRaises(ValueError): error_rate(5, 4)
    def test_boolean_count(self):
        with self.assertRaises(TypeError): error_rate(True, 10)
    def test_error_warning(self): self.assertEqual(classify_error_rate(0.02), "warning")
    def test_error_critical(self): self.assertEqual(classify_error_rate(0.10), "critical")
    def test_error_over_one(self):
        with self.assertRaises(ValueError): classify_error_rate(1.1)
    def test_service_latency_critical(self): self.assertEqual(classify_service(row(latency=700))["overall_status"], "critical")
    def test_service_error_critical(self): self.assertEqual(classify_service(row(errors=15))["overall_status"], "critical")
    def test_service_warning(self): self.assertEqual(classify_service(row(latency=250))["overall_status"], "warning")
    def test_missing_field(self):
        with self.assertRaises(ValueError): classify_service({"service": "api"})
    def test_empty_service(self):
        with self.assertRaises(ValueError): classify_service(row(service=""))
    def test_sort(self): self.assertEqual(classify_all([row("z"), row("a")])["services"][0]["service"], "a")
    def test_duplicate(self):
        with self.assertRaises(ValueError): classify_all([row(), row()])
    def test_empty(self): self.assertEqual(classify_all([])["service_count"], 0)
    def test_summary(self):
        result = classify_all([row("a", latency=700), row("b", latency=250)])
        self.assertEqual((result["critical_count"], result["warning_count"]), (1, 1))
    def test_no_mutation(self):
        sample = row()
        classify_service(sample)
        self.assertEqual(sample["latency_ms"], 100)
    def test_invalid_root(self):
        with self.assertRaises(ValueError): classify_all({})

if __name__ == "__main__":
    unittest.main()
```

## Run and verify
```bash
python classify_metrics.py --input metrics.json
python -m unittest -v test_sre_policy.py
python -m py_compile sre_policy.py classify_metrics.py
```

Expected: three services, `api` healthy, `db` critical, `worker` warning. Summary: one critical, one warning. **26 automated tests** are included.

## Failure injection
1. Set `requests` to 0 or `errors > requests`: reject.
2. Set latency to `true`, `-1` or `NaN`: reject.
3. Duplicate service name: reject.
4. Remove `errors`: reject.
5. Pass malformed JSON: nonzero CLI exit without success report.

## Troubleshooting
| Symptom | Cause | Action |
|---|---|---|
| Missing argument | Required keyword omitted | Pass named thresholds |
| Invalid threshold order | Warning >= critical | Correct policy |
| Unexpected healthy | Input validation missing | Reject bad metrics |
| Flaky tests | External dependencies | Keep pure logic separate |
| Duplicate output | Duplicate service records | Reject or define aggregation policy |

## Production caveats
Thresholds are educational, not approved alert policies. No telemetry freshness, multiwindow burn-rate, notification routing or incident lifecycle management is implemented. Review policy and test independently before production use.

## Acceptance
- [ ] Pure functions separated from I/O
- [ ] Explicit input and return contracts
- [ ] Deterministic, read-only JSON report
- [ ] 26 tests pass
- [ ] Failure injection rejects invalid data
