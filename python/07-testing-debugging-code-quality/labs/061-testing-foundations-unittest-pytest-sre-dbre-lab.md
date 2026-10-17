# Chapter 061 — Testing Foundations with unittest and pytest SRE/DBRE Lab

**Python 3.11+ | Standard library + pytest | Offline, read-only**

## Layout
```text
ch061/
  telemetry_tests_lab.py
  test_unittest_telemetry.py
  test_pytest_telemetry.py
```

## 1. Application: telemetry_tests_lab.py
```python
"""Chapter 061: pure, offline SRE/DBRE alert classification and dependency injection."""
from __future__ import annotations
from dataclasses import dataclass
import argparse
import json
import math
import re
import sys
from typing import Callable, Protocol

POLICIES = {
    "postgresql": ("replication_lag", "seconds", 30, 120),
    "elasticsearch": ("search_latency", "milliseconds", 200, 500),
    "kafka": ("consumer_lag", "messages", 1000, 10000),
}

class ValidationError(ValueError):
    pass

@dataclass(frozen=True)
class Sample:
    service: str
    engine: str
    value: float

@dataclass(frozen=True)
class Alert:
    service: str
    engine: str
    severity: str
    value: float

class Reader(Protocol):
    def __call__(self) -> list[dict[str, object]]: ...

def validate(raw: object) -> Sample:
    if not isinstance(raw, dict) or set(raw) != {"service", "engine", "metric", "unit", "value"}:
        raise ValidationError("invalid telemetry schema")
    service, engine = raw["service"], raw["engine"]
    if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise ValidationError("invalid service")
    if not isinstance(engine, str) or engine not in POLICIES:
        raise ValidationError("unknown engine")
    metric, unit, _, _ = POLICIES[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise ValidationError("metric/unit mismatch")
    value = raw["value"]
    if type(value) not in (int, float):
        raise ValidationError("metric must be numeric")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValidationError("invalid numeric value") from exc
    if not math.isfinite(number) or number < 0:
        raise ValidationError("invalid metric value")
    return Sample(service, engine, number)

def classify(sample: Sample) -> Alert:
    if sample.engine not in POLICIES:
        raise ValidationError("unknown engine")
    if not math.isfinite(sample.value) or sample.value < 0:
        raise ValidationError("invalid metric")
    _, _, warning, critical = POLICIES[sample.engine]
    severity = "critical" if sample.value >= critical else "warning" if sample.value >= warning else "healthy"
    return Alert(sample.service, sample.engine, severity, sample.value)

def analyze(raw: list[object]) -> dict[str, object]:
    if not isinstance(raw, list) or len(raw) > 100:
        raise ValidationError("expected at most 100 telemetry records")
    samples = [validate(item) for item in raw]
    if len({(s.engine, s.service) for s in samples}) != len(samples):
        raise ValidationError("duplicate telemetry source")
    alerts = sorted((classify(s) for s in samples), key=lambda a: (a.engine, a.service))
    counts = {key: sum(a.severity == key for a in alerts) for key in ("healthy", "warning", "critical")}
    return {"schema_version": 1, "dry_run": True, "total": len(alerts),
            "counts": counts,
            "alerts": [{"service": a.service, "engine": a.engine,
                        "severity": a.severity, "value": a.value} for a in alerts]}

def fixtures() -> list[dict[str, object]]:
    return [
        {"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45},
        {"service":"es-search","engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":650},
        {"service":"kafka-worker","engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000},
    ]

def execute(reader: Reader) -> dict[str, object]:
    """Dependency injection makes infrastructure adapters easy to mock."""
    return analyze(reader())

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline testable telemetry analyzer")
    parser.add_argument("--format", choices=("json",), default="json")
    parser.parse_args(argv)
    try:
        result = execute(fixtures)
    except ValidationError:
        print("validation failed: sanitized operational error", file=sys.stderr)
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. Standard library tests: test_unittest_telemetry.py
```python
"""Chapter 061 stdlib unittest suite: no external services."""
import json
import unittest
from unittest.mock import Mock, patch
from telemetry_tests_lab import (
    ValidationError, Sample, validate, classify, analyze, fixtures, execute, main
)
PG={"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45}

class ValidationTests(unittest.TestCase):
    def bad(self, **kwargs):
        with self.assertRaises(ValidationError): validate({**PG, **kwargs})
    def test_valid(self): self.assertEqual(validate(PG).engine,"postgresql")
    def test_service(self): self.bad(service="=cmd")
    def test_unicode(self): self.bad(service="東京")
    def test_engine(self): self.bad(engine="mysql")
    def test_metric(self): self.bad(metric="wrong")
    def test_unit(self): self.bad(unit="ms")
    def test_bool(self): self.bad(value=True)
    def test_string(self): self.bad(value="45")
    def test_negative(self): self.bad(value=-1)
    def test_nan(self): self.bad(value=float("nan"))
    def test_inf(self): self.bad(value=float("inf"))
    def test_extra(self): self.bad(password="secret")
    def test_missing(self):
        d=dict(PG); del d["unit"]
        with self.assertRaises(ValidationError): validate(d)
    def test_not_dict(self):
        with self.assertRaises(ValidationError): validate([])
    def test_healthy(self): self.assertEqual(classify(Sample("pg","postgresql",0)).severity,"healthy")
    def test_warning_boundary(self): self.assertEqual(classify(Sample("pg","postgresql",30)).severity,"warning")
    def test_critical_boundary(self): self.assertEqual(classify(Sample("pg","postgresql",120)).severity,"critical")
    def test_bad_classify(self):
        with self.assertRaises(ValidationError): classify(Sample("pg","postgresql",-1))
    def test_bad_classify_engine(self):
        with self.assertRaises(ValidationError): classify(Sample("pg","mysql",1))
    def test_empty(self): self.assertEqual(analyze([])["total"],0)
    def test_fixture(self): self.assertEqual(len(fixtures()),3)
    def test_counts(self):
        self.assertEqual(analyze(fixtures())["counts"],{"healthy":0,"warning":1,"critical":2})
    def test_sorted(self):
        self.assertEqual([a["engine"] for a in analyze(fixtures())["alerts"]],
                         ["elasticsearch","kafka","postgresql"])
    def test_duplicate(self):
        with self.assertRaises(ValidationError): analyze([PG,PG])
    def test_too_many(self):
        with self.assertRaises(ValidationError): analyze([PG]*101)
    def test_non_list(self):
        with self.assertRaises(ValidationError): analyze({})
    def test_mock_reader(self):
        reader=Mock(return_value=[PG])
        self.assertEqual(execute(reader)["total"],1)
        reader.assert_called_once_with()
    def test_mock_reader_failure(self):
        reader=Mock(side_effect=RuntimeError("synthetic adapter failure"))
        with self.assertRaises(RuntimeError): execute(reader)
    def test_patch_fixture(self):
        with patch("telemetry_tests_lab.fixtures", return_value=[PG]) as reader:
            self.assertEqual(execute(reader)["total"],1)
    def test_dry_run(self): self.assertTrue(execute(fixtures)["dry_run"])
    def test_no_secrets(self): self.assertNotIn("password",json.dumps(execute(fixtures)))
    def test_main(self): self.assertEqual(main([]),0)

if __name__ == "__main__":
    unittest.main()

```

## 3. pytest tests: test_pytest_telemetry.py
```python
"""Chapter 061 pytest suite: install pytest; pytest-cov optional."""
import math
from unittest.mock import Mock
import pytest
from telemetry_tests_lab import ValidationError, Sample, validate, classify, analyze, execute, fixtures

@pytest.fixture
def pg_record():
    return {"service":"pg-replica","engine":"postgresql",
            "metric":"replication_lag","unit":"seconds","value":45}

@pytest.fixture
def sample_records():
    return fixtures()

@pytest.mark.parametrize("value,severity", [
    (0,"healthy"), (29.99,"healthy"), (30,"warning"),
    (119.99,"warning"), (120,"critical"), (999,"critical"),
])
def test_postgresql_boundaries(value,severity):
    assert classify(Sample("pg","postgresql",value)).severity == severity

@pytest.mark.parametrize("engine,metric,unit,warning,critical", [
    ("postgresql","replication_lag","seconds",30,120),
    ("elasticsearch","search_latency","milliseconds",200,500),
    ("kafka","consumer_lag","messages",1000,10000),
])
def test_engine_thresholds(engine,metric,unit,warning,critical):
    raw={"service":"test","engine":engine,"metric":metric,"unit":unit,"value":warning}
    assert classify(validate(raw)).severity == "warning"
    raw["value"]=critical
    assert classify(validate(raw)).severity == "critical"

@pytest.mark.parametrize("bad_value", [True, "45", -1, float("nan"), float("inf")])
def test_reject_bad_values(pg_record,bad_value):
    pg_record["value"]=bad_value
    with pytest.raises(ValidationError):
        validate(pg_record)

def test_fixture_report(sample_records):
    result=analyze(sample_records)
    assert result["total"] == 3
    assert result["counts"] == {"healthy":0,"warning":1,"critical":2}

def test_mocked_reader(pg_record):
    reader=Mock(return_value=[pg_record])
    assert execute(reader)["total"] == 1
    reader.assert_called_once_with()

def test_mocked_reader_error():
    reader=Mock(side_effect=RuntimeError("synthetic"))
    with pytest.raises(RuntimeError,match="synthetic"):
        execute(reader)

def test_no_secret_fields(sample_records):
    assert "password" not in str(analyze(sample_records))

def test_deterministic(sample_records):
    assert analyze(sample_records) == analyze(list(reversed(sample_records)))

def test_duplicate(pg_record):
    with pytest.raises(ValidationError,match="duplicate"):
        analyze([pg_record,pg_record])

```

## 4. Execute
```bash
python3 -m py_compile telemetry_tests_lab.py test_unittest_telemetry.py test_pytest_telemetry.py
python3 -m unittest discover -v -p 'test_unittest_*.py'
python3 -m pip install pytest pytest-cov
python3 -m pytest -q
python3 -m pytest -q --cov=telemetry_tests_lab --cov-branch --cov-report=term-missing
python3 telemetry_tests_lab.py
```

Windows PowerShell: replace `python3` with `py -3`. Use a virtual environment and pin `pytest` and `pytest-cov` in your real project. Do not install packages globally on shared production hosts.

Expected offline result: three synthetic readings, one warning and two critical. Test commands must be executed to establish pass counts and coverage.

## 5. Failure injection
1. Change PostgreSQL warning boundary from 30 to 31 in a disposable copy; verify boundary tests fail.
2. Change critical comparison from `>=` to `>`; verify the exact-boundary test fails.
3. Remove the service validation regex; verify malformed-name tests fail.
4. Inject NaN, Infinity, boolean and negative telemetry.
5. Inject duplicate engine/service records and more than 100 inputs.
6. Replace the Reader with a Mock that raises a synthetic adapter error.
7. Patch `fixtures` at the module lookup site and verify one call.
8. Introduce a test-order dependency in a disposable test and repair fixture isolation.
9. Run coverage with branch measurement and inspect missing lines.
10. Run unittest discovery and pytest collection independently.
11. Reverse input order and verify deterministic reports.
12. Confirm no live database calls or credentials are required.

## 6. Production runbooks
**Failing CI:** reproduce in pinned environment, identify regression, block unsafe release and restore known-good code.

**Flaky tests:** remove wall-clock sleeps, global mutable fixtures and external dependencies; capture reproducible cases.

**Coverage gap:** prioritize validation, boundary and exception paths rather than only increasing line coverage.

**Mock drift:** validate test doubles against adapter contracts and keep integration tests in a separate isolated stage.

**Rollback:** restore code and tests, rerun all required gates, and document approval.

## 7. 100-point assessment
| Area | Points |
|---|---:|
| Syntax and unittest suite | 20 |
| pytest fixtures and parameterization | 20 |
| Mocking and dependency injection | 20 |
| Coverage and CI quality gates | 15 |
| Incident simulations | 15 |
| Troubleshooting and runbooks | 10 |

Target 90/100 with all safety tests passing. Publication is not proof of test execution or a coverage percentage.
