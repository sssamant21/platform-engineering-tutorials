# Chapter 030 — Hands-on Lab: Packaged Production-Oriented SRE CLI Capstone

**Python 3.10+ | Offline synthetic telemetry | No infrastructure changes**

## Goal and project layout

Build a complete installable package, run a CLI with `check`, `batch`, `config`, `plan`, and `version` subcommands, validate synthetic telemetry, produce deterministic JSON, block execution, and test an immutable wheel.

```text
srekit-capstone/
  pyproject.toml
  sample.json
  config.json
  src/srekit/__init__.py
  src/srekit/__main__.py
  src/srekit/models.py
  src/srekit/policy.py
  src/srekit/report.py
  src/srekit/config.py
  src/srekit/instrument.py
  src/srekit/cli.py
  tests/test_core.py
  tests/test_cli.py
```

Create directories: `mkdir -p src/srekit tests` (Linux/WSL/macOS) or `New-Item -ItemType Directory -Force src/srekit,tests` (PowerShell).

### 1. `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "srekit-capstone-lab"
version = "0.1.0"
description = "Offline, read-only SRE CLI capstone"
requires-python = ">=3.10"
dependencies = []

[project.scripts]
srekit = "srekit.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

The build backend version range is instructional. Production CI should pin an approved backend and use a controlled index.

### 2. `src/srekit/models.py`

```python
from dataclasses import dataclass
import math


def finite_nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return float(value)


@dataclass(frozen=True)
class Metric:
    service: str
    latency_ms: float
    errors: int
    requests: int

    @classmethod
    def from_mapping(cls, raw):
        if not isinstance(raw, dict) or set(raw) != {
            "service", "latency_ms", "errors", "requests"
        }:
            raise ValueError("invalid metric schema")
        service = raw["service"]
        if not isinstance(service, str) or not service.strip() or len(service) > 64:
            raise ValueError("invalid service")
        latency = finite_nonnegative(raw["latency_ms"], "latency_ms")
        errors, requests = raw["errors"], raw["requests"]
        if (isinstance(errors, bool) or isinstance(requests, bool)
                or not isinstance(errors, int) or not isinstance(requests, int)):
            raise ValueError("counts must be integers")
        if requests < 1 or errors < 0 or errors > requests:
            raise ValueError("invalid request/error counts")
        return cls(service, latency, errors, requests)
```

### 3. `src/srekit/policy.py`

```python
from .models import Metric, finite_nonnegative


def classify(metric: Metric, *, warning_ms=200, critical_ms=500,
             warning_rate=0.02, critical_rate=0.10):
    warning_ms = finite_nonnegative(warning_ms, "warning_ms")
    critical_ms = finite_nonnegative(critical_ms, "critical_ms")
    warning_rate = finite_nonnegative(warning_rate, "warning_rate")
    critical_rate = finite_nonnegative(critical_rate, "critical_rate")
    if not 0 < warning_ms < critical_ms or not 0 < warning_rate < critical_rate <= 1:
        raise ValueError("invalid thresholds")
    rate = metric.errors / metric.requests

    def severity(value, warning, critical):
        return "critical" if value >= critical else "warning" if value >= warning else "healthy"

    latency_status = severity(metric.latency_ms, warning_ms, critical_ms)
    error_status = severity(rate, warning_rate, critical_rate)
    rank = {"healthy": 0, "warning": 1, "critical": 2}
    return {
        "service": metric.service,
        "latency_ms": metric.latency_ms,
        "error_rate": round(rate, 6),
        "latency_status": latency_status,
        "error_status": error_status,
        "status": max((latency_status, error_status), key=rank.__getitem__),
    }
```

### 4. `src/srekit/report.py`

```python
from .models import Metric
from .policy import classify


def build_report(raw_records):
    if not isinstance(raw_records, list):
        raise ValueError("expected a JSON array")
    seen = set()
    records = []
    for raw in raw_records:
        metric = Metric.from_mapping(raw)
        if metric.service in seen:
            raise ValueError("duplicate service")
        seen.add(metric.service)
        records.append(classify(metric))
    records.sort(key=lambda item: item["service"])
    return {
        "schema_version": 1,
        "service_count": len(records),
        "warning_count": sum(item["status"] == "warning" for item in records),
        "critical_count": sum(item["status"] == "critical" for item in records),
        "services": records,
    }
```

### 5. `src/srekit/config.py`

```python
from dataclasses import dataclass
import json
import math
from pathlib import Path

DEFAULTS = {
    "environment": "staging",
    "timeout_seconds": 5.0,
    "dry_run": True,
    "secret_ref": "vault://sre/staging/read-only",
}
ENV_KEYS = {
    "SREKIT_ENVIRONMENT": "environment",
    "SREKIT_TIMEOUT_SECONDS": "timeout_seconds",
    "SREKIT_DRY_RUN": "dry_run",
    "SREKIT_SECRET_REF": "secret_ref",
}


@dataclass(frozen=True)
class Config:
    environment: str
    timeout_seconds: float
    dry_run: bool
    secret_ref: str

    def sanitized(self):
        return {
            "environment": self.environment,
            "timeout_seconds": self.timeout_seconds,
            "dry_run": self.dry_run,
            "secret_ref": "<redacted>",
        }


def parse_bool(value):
    if value is True or value == "true":
        return True
    if value is False or value == "false":
        return False
    raise ValueError("dry_run must be true or false")


def load_config(*, file_path=None, environ=None, overrides=None):
    merged = dict(DEFAULTS)
    if file_path is not None:
        try:
            raw = Path(file_path).read_text(encoding="utf-8")
            data = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")))
        except (OSError, UnicodeError, ValueError) as exc:
            raise ValueError("configuration file unreadable or invalid") from exc
        if not isinstance(data, dict) or set(data) - set(DEFAULTS):
            raise ValueError("unknown configuration field")
        merged.update(data)
    source = {} if environ is None else environ
    if any(key.startswith("SREKIT_") and key not in ENV_KEYS for key in source):
        raise ValueError("unknown SREKIT_ environment key")
    for key, field in ENV_KEYS.items():
        if key in source:
            merged[field] = source[key]
    if overrides is not None:
        if not isinstance(overrides, dict) or set(overrides) - set(DEFAULTS):
            raise ValueError("unknown CLI override")
        merged.update({key: value for key, value in overrides.items() if value is not None})
    environment = merged["environment"]
    if not isinstance(environment, str) or environment not in {"dev", "staging", "prod"}:
        raise ValueError("invalid environment")
    raw_timeout = merged["timeout_seconds"]
    if isinstance(raw_timeout, bool) or not isinstance(raw_timeout, (int, float, str)):
        raise ValueError("invalid timeout")
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid timeout") from exc
    if not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise ValueError("timeout must be finite and in (0,60]")
    dry_run = parse_bool(merged["dry_run"])
    secret = merged["secret_ref"]
    if not isinstance(secret, str) or not secret.startswith("vault://") or len(secret) < 9:
        raise ValueError("invalid secret reference")
    if environment == "prod" and not dry_run:
        raise ValueError("production dry_run must be true")
    return Config(environment, timeout, dry_run, secret)
```

### 6. `src/srekit/instrument.py`

```python
from functools import wraps
from time import perf_counter


def measured(clock=perf_counter, observer=None):
    """Opt-in duration observer. No logging or metric emission on import."""
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = clock()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = max(0.0, clock() - start)
                if observer is not None:
                    observer(func.__name__, elapsed)
        return wrapper
    return decorate
```

### 7. `src/srekit/cli.py`

```python
import argparse
import json
import os
from pathlib import Path
from .config import load_config
from .models import Metric
from .policy import classify
from .report import build_report

VERSION = "0.1.0"


def parser_factory():
    parser = argparse.ArgumentParser(prog="srekit", description="Offline read-only SRE CLI")
    parser.add_argument("--config", type=Path, help="reviewed JSON config file")
    parser.add_argument("--environment", choices=("dev", "staging", "prod"))
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="classify one synthetic service")
    check.add_argument("--service", required=True)
    check.add_argument("--latency-ms", type=float, required=True)
    check.add_argument("--errors", type=int, required=True)
    check.add_argument("--requests", type=int, required=True)
    batch = sub.add_parser("batch", help="classify synthetic JSON file")
    batch.add_argument("--input", type=Path, required=True)
    sub.add_parser("config", help="show sanitized configuration")
    plan = sub.add_parser("plan", help="read-only maintenance preview")
    plan.add_argument("--target", choices=("postgresql", "elasticsearch", "kubernetes", "kafka"), required=True)
    plan.add_argument("--execute", action="store_true", help="intentionally blocked")
    sub.add_parser("version", help="print version")
    return parser


def main(argv=None, environ=None):
    parser = parser_factory()
    args = parser.parse_args(argv)
    if args.command == "version":
        print(json.dumps({"schema_version": 1, "version": VERSION}, sort_keys=True))
        return 0
    try:
        cfg = load_config(
            file_path=args.config,
            environ=os.environ if environ is None else environ,
            overrides={"environment": args.environment},
        )
        if args.command == "config":
            result = {"schema_version": 1, "configuration": cfg.sanitized()}
            code = 0
        elif args.command == "plan":
            if args.execute:
                parser.exit(4, "srekit: blocked: execution is disabled\n")
            result = {
                "schema_version": 1,
                "environment": cfg.environment,
                "target": args.target,
                "action": "inspect-health",
                "dry_run": True,
                "mutations": [],
            }
            code = 0
        elif args.command == "check":
            metric = Metric.from_mapping({
                "service": args.service,
                "latency_ms": args.latency_ms,
                "errors": args.errors,
                "requests": args.requests,
            })
            result = {"schema_version": 1, **classify(metric)}
            code = 3 if result["status"] != "healthy" else 0
        else:
            try:
                raw = args.input.read_text(encoding="utf-8")
                records = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")))
            except (OSError, UnicodeError, ValueError):
                parser.exit(5, "srekit: input file unreadable or invalid\n")
            result = build_report(records)
            code = 3 if result["warning_count"] or result["critical_count"] else 0
    except (TypeError, ValueError) as exc:
        # Domain errors contain fixed labels only, never raw secret values.
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return code
```

### 8. `src/srekit/__init__.py`

```python
"""Read-only SRE CLI capstone public API."""
from .models import Metric
from .policy import classify
from .report import build_report

__all__ = ["Metric", "classify", "build_report"]
```

### 9. `src/srekit/__main__.py`

```python
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

### 10. `sample.json`

```json
[
  {"service":"api","latency_ms":100,"errors":1,"requests":100},
  {"service":"db","latency_ms":650,"errors":15,"requests":100},
  {"service":"worker","latency_ms":250,"errors":3,"requests":100}
]
```

### 11. `config.json`

```json
{"environment":"staging","timeout_seconds":8,"dry_run":true,"secret_ref":"vault://sre/staging/read-only"}
```

### 12. `tests/test_core.py`

```python
import unittest
from srekit import Metric, classify, build_report
from srekit.config import load_config
from srekit.instrument import measured


def row(service="api", latency=100, errors=1, requests=100):
    return {"service":service, "latency_ms":latency, "errors":errors, "requests":requests}


class CoreTests(unittest.TestCase):
    def test_healthy(self): self.assertEqual(classify(Metric.from_mapping(row()))["status"], "healthy")
    def test_warning_latency(self): self.assertEqual(classify(Metric.from_mapping(row(latency=200)))["status"], "warning")
    def test_critical_latency(self): self.assertEqual(classify(Metric.from_mapping(row(latency=500)))["status"], "critical")
    def test_critical_errors(self): self.assertEqual(classify(Metric.from_mapping(row(errors=10)))["status"], "critical")
    def test_warning_errors(self): self.assertEqual(classify(Metric.from_mapping(row(errors=2)))["status"], "warning")
    def test_missing_field(self):
        with self.assertRaises(ValueError): Metric.from_mapping({"service":"api"})
    def test_unknown_field(self):
        with self.assertRaises(ValueError): Metric.from_mapping({**row(), "extra":1})
    def test_negative_latency(self):
        with self.assertRaises(ValueError): Metric.from_mapping(row(latency=-1))
    def test_nan_latency(self):
        with self.assertRaises(ValueError): Metric.from_mapping(row(latency=float("nan")))
    def test_bool_latency(self):
        with self.assertRaises(ValueError): Metric.from_mapping(row(latency=True))
    def test_bool_count(self):
        with self.assertRaises(ValueError): Metric.from_mapping(row(errors=True))
    def test_zero_requests(self):
        with self.assertRaises(ValueError): Metric.from_mapping(row(requests=0))
    def test_errors_above_requests(self):
        with self.assertRaises(ValueError): Metric.from_mapping(row(errors=101))
    def test_empty_service(self):
        with self.assertRaises(ValueError): Metric.from_mapping(row(service=""))
    def test_invalid_thresholds(self):
        with self.assertRaises(ValueError): classify(Metric.from_mapping(row()), warning_ms=500, critical_ms=200)
    def test_sorted(self):
        report = build_report([row("z"), row("a")])
        self.assertEqual(report["services"][0]["service"], "a")
    def test_duplicate(self):
        with self.assertRaises(ValueError): build_report([row(), row()])
    def test_empty_batch(self): self.assertEqual(build_report([])["service_count"], 0)
    def test_nonlist_batch(self):
        with self.assertRaises(ValueError): build_report({})
    def test_aggregate(self):
        report = build_report([row("a",latency=650), row("b",latency=250)])
        self.assertEqual((report["critical_count"],report["warning_count"]),(1,1))
    def test_config_defaults(self): self.assertEqual(load_config().environment,"staging")
    def test_env_override(self): self.assertEqual(load_config(environ={"SREKIT_ENVIRONMENT":"dev"}).environment,"dev")
    def test_cli_precedence(self):
        self.assertEqual(load_config(environ={"SREKIT_ENVIRONMENT":"dev"},overrides={"environment":"staging"}).environment,"staging")
    def test_unknown_env(self):
        with self.assertRaises(ValueError): load_config(environ={"SREKIT_UNKNOWN":"x"})
    def test_bad_timeout(self):
        with self.assertRaises(ValueError): load_config(environ={"SREKIT_TIMEOUT_SECONDS":"nan"})
    def test_prod_block(self):
        with self.assertRaises(ValueError):
            load_config(environ={"SREKIT_ENVIRONMENT":"prod","SREKIT_DRY_RUN":"false"})
    def test_redaction(self): self.assertEqual(load_config().sanitized()["secret_ref"],"<redacted>")
    def test_bad_secret_ref(self):
        with self.assertRaises(ValueError): load_config(environ={"SREKIT_SECRET_REF":"plaintext"})
    def test_measured(self):
        ticks = iter([10.0,10.25])
        calls = []
        @measured(clock=lambda:next(ticks),observer=lambda name,duration:calls.append((name,duration)))
        def probe(): return 7
        self.assertEqual(probe(),7)
        self.assertEqual(calls,[("probe",0.25)])
    def test_measured_preserves_name(self):
        @measured(clock=lambda:0.0)
        def probe(): return 1
        self.assertEqual(probe.__name__,"probe")


if __name__ == "__main__":
    unittest.main()
```

### 13. `tests/test_cli.py`

```python
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from srekit.cli import main, parser_factory


def invoke(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv, environ={})
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def test_version(self):
        code, out, _ = invoke(["version"])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out)["version"],"0.1.0")
    def test_healthy(self):
        self.assertEqual(invoke(["check","--service","api","--latency-ms","100","--errors","1","--requests","100"])[0],0)
    def test_warning(self):
        self.assertEqual(invoke(["check","--service","api","--latency-ms","300","--errors","1","--requests","100"])[0],3)
    def test_invalid(self):
        self.assertEqual(invoke(["check","--service","api","--latency-ms","nan","--errors","1","--requests","100"])[0],2)
    def test_config_redacted(self):
        code,out,_ = invoke(["config"])
        self.assertEqual(code,0)
        self.assertIn("<redacted>",out)
        self.assertNotIn("vault://",out)
    def test_plan(self):
        code,out,_ = invoke(["plan","--target","postgresql"])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out)["mutations"],[])
    def test_block_execute(self):
        code,out,_ = invoke(["plan","--target","kafka","--execute"])
        self.assertEqual(code,4)
        self.assertEqual(out,"")
    def test_missing_file(self):
        self.assertEqual(invoke(["batch","--input","nonexistent-ch030.json"])[0],5)
    def test_bad_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"bad.json"
            path.write_text("{bad",encoding="utf-8")
            self.assertEqual(invoke(["batch","--input",str(path)])[0],5)
    def test_batch_warning(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"input.json"
            path.write_text(json.dumps([{"service":"api","latency_ms":250,"errors":1,"requests":100}]),encoding="utf-8")
            code,out,_=invoke(["batch","--input",str(path)])
            self.assertEqual(code,3)
            self.assertEqual(json.loads(out)["warning_count"],1)
    def test_batch_healthy(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"input.json"
            path.write_text(json.dumps([{"service":"api","latency_ms":100,"errors":0,"requests":100}]),encoding="utf-8")
            self.assertEqual(invoke(["batch","--input",str(path)])[0],0)
    def test_cli_environment(self):
        code,out,_=invoke(["--environment","dev","config"])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out)["configuration"]["environment"],"dev")
    def test_help(self):
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                parser_factory().parse_args(["--help"])
        self.assertEqual(raised.exception.code,0)
    def test_unknown_command(self):
        self.assertEqual(invoke(["unknown"])[0],2)
    def test_missing_required(self):
        self.assertEqual(invoke(["check"])[0],2)


if __name__ == "__main__":
    unittest.main()
```

## 14. Install, test, build and smoke-test

**Linux / macOS / WSL**
```bash
python3 -m venv .venv
./.venv/bin/python -m pip install 'setuptools>=68' wheel
./.venv/bin/python -m pip install -e . --no-build-isolation
./.venv/bin/python -m unittest discover -s tests -v
./.venv/bin/python -m compileall -q src
./.venv/bin/python -m pip wheel --no-deps --no-build-isolation -w dist .
./.venv/bin/python -m srekit --config config.json batch --input sample.json
./.venv/bin/python -m srekit plan --target postgresql
sha256sum dist/*.whl
python3 -m venv .venv-smoke
./.venv-smoke/bin/python -m pip install --no-index --no-deps dist/srekit_capstone_lab-0.1.0-py3-none-any.whl
(cd /tmp && "$OLDPWD/.venv-smoke/bin/python" -m srekit check --service api --latency-ms 100 --errors 0 --requests 100)
```

**Windows PowerShell**
```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install "setuptools>=68" wheel
.\.venv\Scripts\python.exe -m pip install -e . --no-build-isolation
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q src
.\.venv\Scripts\python.exe -m pip wheel --no-deps --no-build-isolation -w dist .
.\.venv\Scripts\python.exe -m srekit --config config.json batch --input sample.json
Get-FileHash dist\*.whl -Algorithm SHA256
py -3 -m venv .venv-smoke
.\.venv-smoke\Scripts\python.exe -m pip install --no-index --no-deps dist\srekit_capstone_lab-0.1.0-py3-none-any.whl
$python = (Resolve-Path .\.venv-smoke\Scripts\python.exe).Path
Push-Location $env:TEMP
& $python -m srekit check --service api --latency-ms 100 --errors 0 --requests 100
Pop-Location
```

Build-tool installation can require an approved index or preprovisioned wheelhouse. The **fresh wheel installation** uses no index. Before a production release, compare the observed digest with a trusted, independently recorded release digest; a self-generated hash alone is not authentication.

Expected sample report: **3 services, 1 critical, 1 warning, 1 healthy**; batch exits **3** because there are breaches. The lab publishes **45 unit tests** (30 core + 15 CLI); learners must execute them.

## 15. Failure injection

1. `--latency-ms nan` → exit 2, no JSON.
2. Duplicate service in batch → exit 2.
3. Invalid JSON or missing input file → exit 5.
4. `plan --target kafka --execute` → exit 4, no mutation.
5. `SREKIT_ENVIRONMENT=prod` plus `SREKIT_DRY_RUN=false` → exit 2.
6. Invalid `SREKIT_SECRET_REF` → exit 2, no secret echo.
7. Alter a copy of the wheel after recording its digest → mismatch; stop promotion.
8. Execute from outside the checkout after wheel installation → no source-tree leakage.

## 16. Troubleshooting and runbooks

| Issue | Likely cause | Resolution |
|---|---|---|
| `No module named srekit` | Wrong interpreter | Use venv Python and install package |
| CLI flag rejected | Global `--config` placed after subcommand | Place global flags before subcommand |
| Unexpected exit 3 | Valid but degraded synthetic input | Inspect JSON status |
| Production config blocked | Intentional fail-closed policy | Use approved dry-run settings |
| No `srekit` executable | Venv scripts not on PATH | Use `python -m srekit` |
| Wheel install fails offline | Artifact missing | Rebuild and verify exact file |
| Secret printed by external tooling | Logging outside this lab | Review logging/CI masking |

**Incident response:** stop automation, preserve sanitized output, command version, artifact hash and exit code, compare expected policy, roll back to the previous approved wheel, and escalate before any real infrastructure action.

## 17. Acceptance assessment (100 points)

| Criterion | Points |
|---|---:|
| Correct modular package architecture | 15 |
| Strict validation and deterministic policy | 20 |
| Layered configuration and redaction | 15 |
| CLI JSON and exit-code behavior | 15 |
| Blocked execution and dry-run policy | 10 |
| 45 automated tests and failure injection | 15 |
| Clean wheel install and documented runbooks | 10 |

**Pass:** at least 85 points **and** all mandatory safety checks: no mutations, no real secrets, no production access, and execution blocked. Record local test output and wheel digest as evidence.

## 18. Cleanup

Remove only disposable lab virtual environments and build artifacts. Do not delete system Python installations or shared caches. No production resources are created by this exercise.
