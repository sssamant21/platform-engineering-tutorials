# Chapter 025 — Hands-on Lab: Package a Reusable SRE Health Classifier

**Python 3.10+ | Offline synthetic input | No cloud or database access**

## Goal and structure
Build a standard-library-only package that classifies synthetic service latency and error rates. Separate validation, classification, reporting and CLI I/O.

```text
sre-probe-kit/
  pyproject.toml
  sample.json
  src/sre_probe_kit/__init__.py
  src/sre_probe_kit/__main__.py
  src/sre_probe_kit/models.py
  src/sre_probe_kit/policy.py
  src/sre_probe_kit/reporting.py
  src/sre_probe_kit/cli.py
  tests/test_policy.py
  tests/test_cli.py
```

Create directories with `mkdir -p src/sre_probe_kit tests` on Linux/macOS/WSL, or `New-Item -ItemType Directory -Force src/sre_probe_kit,tests` in PowerShell.

## 1. `pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "sre-probe-kit-lab"
version = "0.1.0"
description = "Offline SRE health classification lab"
requires-python = ">=3.10"
dependencies = []

[project.scripts]
sre-probe = "sre_probe_kit.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

The setuptools version range is educational; production CI should pin an approved build-tool version and index.

## 2. `src/sre_probe_kit/models.py`
```python
"""Strict validation of synthetic telemetry records."""
from dataclasses import dataclass
import math


def nonnegative(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return float(value)


@dataclass(frozen=True)
class ServiceMetric:
    service: str
    latency_ms: float
    errors: int
    requests: int

    @classmethod
    def from_dict(cls, data: object) -> "ServiceMetric":
        expected = {"service", "latency_ms", "errors", "requests"}
        if not isinstance(data, dict) or set(data) != expected:
            raise ValueError("record must contain exactly service, latency_ms, errors, requests")
        service = data["service"]
        if not isinstance(service, str) or not service.strip():
            raise ValueError("service must be a nonempty string")
        latency = nonnegative(data["latency_ms"], "latency_ms")
        errors, requests = data["errors"], data["requests"]
        if isinstance(errors, bool) or isinstance(requests, bool):
            raise TypeError("counts must be integers")
        if not isinstance(errors, int) or not isinstance(requests, int):
            raise TypeError("counts must be integers")
        if requests < 1 or not 0 <= errors <= requests:
            raise ValueError("require requests >= 1 and 0 <= errors <= requests")
        return cls(service, latency, errors, requests)
```

## 3. `src/sre_probe_kit/policy.py`
```python
"""Pure SRE classification policy."""
from .models import ServiceMetric


def classify(metric: ServiceMetric, *, warning_ms=200.0, critical_ms=500.0,
             warning_rate=0.02, critical_rate=0.10) -> dict:
    if not 0 < warning_ms < critical_ms:
        raise ValueError("latency thresholds must increase")
    if not 0 < warning_rate < critical_rate <= 1:
        raise ValueError("error-rate thresholds must increase")
    rate = metric.errors / metric.requests
    def level(value, warning, critical):
        return "critical" if value >= critical else "warning" if value >= warning else "healthy"
    latency_status = level(metric.latency_ms, warning_ms, critical_ms)
    error_status = level(rate, warning_rate, critical_rate)
    rank = {"healthy": 0, "warning": 1, "critical": 2}
    return {
        "service": metric.service,
        "latency_ms": metric.latency_ms,
        "error_rate": round(rate, 6),
        "latency_status": latency_status,
        "error_status": error_status,
        "overall_status": max((latency_status, error_status), key=rank.__getitem__),
    }
```

## 4. `src/sre_probe_kit/reporting.py`
```python
"""Deterministic batch reporting with duplicate rejection."""
from .models import ServiceMetric
from .policy import classify


def build_report(records: object) -> dict:
    if not isinstance(records, list):
        raise ValueError("expected a JSON array")
    seen = set()
    decisions = []
    for raw in records:
        metric = ServiceMetric.from_dict(raw)
        if metric.service in seen:
            raise ValueError(f"duplicate service: {metric.service}")
        seen.add(metric.service)
        decisions.append(classify(metric))
    decisions.sort(key=lambda record: record["service"])
    return {
        "service_count": len(decisions),
        "critical_count": sum(item["overall_status"] == "critical" for item in decisions),
        "warning_count": sum(item["overall_status"] == "warning" for item in decisions),
        "services": decisions,
    }
```

## 5. `src/sre_probe_kit/cli.py`
```python
"""Explicit CLI boundary; no I/O on import."""
import argparse
import json
from pathlib import Path
from .reporting import build_report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read-only SRE health classifier")
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with args.input.open(encoding="utf-8") as source:
            records = json.load(source)
        report = build_report(records)
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0
```

## 6. `src/sre_probe_kit/__main__.py`
```python
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

## 7. `src/sre_probe_kit/__init__.py`
```python
"""Public interface for the offline SRE health classifier."""
from .models import ServiceMetric
from .policy import classify
from .reporting import build_report

__all__ = ["ServiceMetric", "classify", "build_report"]
```

## 8. `sample.json`
```json
[
  {"service":"api","latency_ms":120,"errors":1,"requests":100},
  {"service":"db","latency_ms":720,"errors":12,"requests":100},
  {"service":"worker","latency_ms":280,"errors":4,"requests":100}
]
```

## 9. `tests/test_policy.py`
```python
import unittest
from sre_probe_kit import ServiceMetric, classify, build_report


def row(service="api", latency=100, errors=1, requests=100):
    return {"service": service, "latency_ms": latency, "errors": errors, "requests": requests}


class PolicyTests(unittest.TestCase):
    def test_model(self):
        self.assertEqual(ServiceMetric.from_dict(row()).service, "api")
    def test_frozen_model(self):
        from dataclasses import FrozenInstanceError
        metric = ServiceMetric.from_dict(row())
        with self.assertRaises(FrozenInstanceError):
            metric.service = "db"
    def test_missing_field(self):
        with self.assertRaises(ValueError):
            ServiceMetric.from_dict({"service": "api"})
    def test_unknown_field(self):
        record = row()
        record["extra"] = 1
        with self.assertRaises(ValueError):
            ServiceMetric.from_dict(record)
    def test_empty_service(self):
        with self.assertRaises(ValueError):
            ServiceMetric.from_dict(row(service=""))
    def test_boolean_latency(self):
        with self.assertRaises(TypeError):
            ServiceMetric.from_dict(row(latency=True))
    def test_negative_latency(self):
        with self.assertRaises(ValueError):
            ServiceMetric.from_dict(row(latency=-1))
    def test_nan_latency(self):
        with self.assertRaises(ValueError):
            ServiceMetric.from_dict(row(latency=float("nan")))
    def test_zero_requests(self):
        with self.assertRaises(ValueError):
            ServiceMetric.from_dict(row(requests=0))
    def test_excess_errors(self):
        with self.assertRaises(ValueError):
            ServiceMetric.from_dict(row(errors=200))
    def test_boolean_count(self):
        with self.assertRaises(TypeError):
            ServiceMetric.from_dict(row(errors=True))
    def test_healthy(self):
        self.assertEqual(classify(ServiceMetric.from_dict(row()))["overall_status"], "healthy")
    def test_warning(self):
        self.assertEqual(classify(ServiceMetric.from_dict(row(latency=200)))["overall_status"], "warning")
    def test_critical(self):
        self.assertEqual(classify(ServiceMetric.from_dict(row(latency=500)))["overall_status"], "critical")
    def test_error_critical(self):
        self.assertEqual(classify(ServiceMetric.from_dict(row(errors=10)))["error_status"], "critical")
    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            classify(ServiceMetric.from_dict(row()), warning_ms=500, critical_ms=200)
    def test_sorted_report(self):
        report = build_report([row("z"), row("a")])
        self.assertEqual(report["services"][0]["service"], "a")
    def test_duplicate_service(self):
        with self.assertRaises(ValueError):
            build_report([row(), row()])
    def test_empty_report(self):
        self.assertEqual(build_report([])["service_count"], 0)
    def test_nonlist(self):
        with self.assertRaises(ValueError):
            build_report({})
    def test_counts(self):
        report = build_report([row("a", latency=600), row("b", latency=250)])
        self.assertEqual((report["critical_count"], report["warning_count"]), (1, 1))
    def test_no_mutation(self):
        record = row()
        build_report([record])
        self.assertEqual(record["latency_ms"], 100)


if __name__ == "__main__":
    unittest.main()
```

## 10. `tests/test_cli.py`
```python
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from sre_probe_kit.cli import main


class CliTests(unittest.TestCase):
    def test_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text(json.dumps([
                {"service": "api", "latency_ms": 100, "errors": 0, "requests": 10}
            ]), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--input", str(path)]), 0)
            self.assertEqual(json.loads(output.getvalue())["service_count"], 1)

    def test_missing_file(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(["--input", "/unlikely-to-exist-ch025.json"])
        self.assertEqual(raised.exception.code, 2)

    def test_bad_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{bad", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(["--input", str(path)])
            self.assertEqual(raised.exception.code, 2)

    def test_import_metadata(self):
        import sre_probe_kit
        self.assertTrue(hasattr(sre_probe_kit, "build_report"))

    def test_public_api(self):
        from sre_probe_kit import __all__
        self.assertEqual(__all__, ["ServiceMetric", "classify", "build_report"])


if __name__ == "__main__":
    unittest.main()
```

## 11. Install and run
From the project root:

```bash
python -m venv .venv
# Linux/macOS/WSL:
source .venv/bin/activate
# Windows PowerShell, instead:
# .venv\Scripts\Activate.ps1

python -m pip install -e .
python -m sre_probe_kit --input sample.json
sre-probe --input sample.json
python -m unittest discover -s tests -v
python -m compileall -q src
python -m pip show sre-probe-kit-lab
```

Expected: **3 services**, one critical (`db`), one warning (`worker`), one healthy (`api`). **27 unit tests** are included. Local test execution is required.

## 12. Failure injection
1. Run `python src/sre_probe_kit/cli.py --input sample.json`: relative-import failure illustrates why direct module-file execution is wrong.
2. Use a nonexistent input path: exit 2, no success JSON.
3. Corrupt the JSON: exit 2, no success JSON.
4. Set `requests` to 0: fail validation.
5. Duplicate a service: fail closed.
6. Rename a local file `json.py` and observe shadowing in an isolated disposable directory; restore the filename immediately.
7. Run tests from outside the repository root after editable installation to verify package resolution.

## 13. Troubleshooting
| Symptom | Cause | Resolution |
|---|---|---|
| No module named sre_probe_kit | Wrong interpreter or missing install | Activate venv and reinstall |
| Attempted relative import | Direct script execution | Use `python -m sre_probe_kit` |
| Missing sre-probe executable | CLI installed in different venv | Check interpreter and PATH |
| Unexpected JSON import | Local `json.py` shadows stdlib | Rename file |
| Tests pass only from repo root | Import path leakage | Use src layout and installed package |

## 14. Production-readiness checklist
- [ ] Package import has no network, credential or file I/O side effects.
- [ ] All 27 tests pass in an isolated environment.
- [ ] `python -m` and console entry point produce equivalent JSON.
- [ ] Validation rejects malformed or duplicate records.
- [ ] Wheel build and dependency provenance reviewed in CI.
- [ ] No production credentials, network calls or infrastructure changes.

## Cleanup
Deactivate the virtual environment and delete only this disposable lab directory. Never remove shared Python installations or production environments.
