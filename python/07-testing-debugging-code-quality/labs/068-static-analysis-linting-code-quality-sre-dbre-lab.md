# Chapter 068 — Static Analysis, Linting and Code Quality SRE/DBRE Lab

**Python 3.11+ | Ruff, mypy, unittest | No external service calls**

## File layout
\`\`\`text
ch068/
  telemetry_quality.py
  test_telemetry_quality.py
  pyproject.toml
  .pre-commit-config.yaml
\`\`\`

## 1. telemetry_quality.py
\`\`\`python
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import math
import re
from typing import Final, Mapping, TypedDict

MAX_BATCH: Final = 100
SERVICE_PATTERN: Final = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")

class Engine(StrEnum):
    POSTGRESQL = "postgresql"
    ELASTICSEARCH = "elasticsearch"
    KAFKA = "kafka"

class Severity(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"

class InputRow(TypedDict):
    service: str
    engine: str
    metric: str
    unit: str
    value: float

class ResultRow(TypedDict):
    service: str
    engine: str
    value: float
    severity: str

class Summary(TypedDict):
    dry_run: bool
    total: int
    counts: dict[str, int]
    results: list[ResultRow]

POLICY: Final[Mapping[Engine, tuple[str, str, float, float]]] = {
    Engine.POSTGRESQL: ("replication_lag", "seconds", 30.0, 120.0),
    Engine.ELASTICSEARCH: ("search_latency", "milliseconds", 200.0, 500.0),
    Engine.KAFKA: ("consumer_lag", "messages", 1000.0, 10000.0),
}

class ValidationError(ValueError):
    pass

@dataclass(frozen=True, slots=True)
class Reading:
    service: str
    engine: Engine
    value: float

def parse(raw: object) -> Reading:
    if not isinstance(raw, dict) or set(raw) != {"service", "engine", "metric", "unit", "value"}:
        raise ValidationError("invalid schema")
    service = raw["service"]
    if not isinstance(service, str) or SERVICE_PATTERN.fullmatch(service) is None:
        raise ValidationError("invalid service")
    engine_raw = raw["engine"]
    if not isinstance(engine_raw, str):
        raise ValidationError("invalid engine")
    try:
        engine = Engine(engine_raw)
    except ValueError as exc:
        raise ValidationError("invalid engine") from exc
    metric, unit, _, _ = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise ValidationError("invalid metric or unit")
    value = raw["value"]
    if type(value) not in (int, float):
        raise ValidationError("invalid value type")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValidationError("invalid numeric value") from exc
    if not math.isfinite(number) or number < 0:
        raise ValidationError("invalid numeric value")
    return Reading(service, engine, number)

def classify(reading: Reading) -> Severity:
    if reading.engine not in POLICY or not math.isfinite(reading.value) or reading.value < 0:
        raise ValidationError("invalid reading")
    _, _, warning, critical = POLICY[reading.engine]
    if reading.value >= critical:
        return Severity.CRITICAL
    if reading.value >= warning:
        return Severity.WARNING
    return Severity.HEALTHY

def summarize(raw: object) -> Summary:
    if not isinstance(raw, list) or len(raw) > MAX_BATCH:
        raise ValidationError("invalid batch")
    readings = [parse(row) for row in raw]
    if len({(r.engine, r.service) for r in readings}) != len(readings):
        raise ValidationError("duplicate source")
    counts: dict[str, int] = {s.value: 0 for s in Severity}
    results: list[ResultRow] = []
    for reading in sorted(readings, key=lambda r: (r.engine.value, r.service)):
        level = classify(reading)
        counts[level.value] += 1
        results.append({"service": reading.service, "engine": reading.engine.value,
                        "value": reading.value, "severity": level.value})
    return {"dry_run": True, "total": len(results), "counts": counts, "results": results}

def fixtures() -> list[InputRow]:
    return [
        {"service": "pg-replica", "engine": "postgresql", "metric": "replication_lag", "unit": "seconds", "value": 45.0},
        {"service": "es-search", "engine": "elasticsearch", "metric": "search_latency", "unit": "milliseconds", "value": 650.0},
        {"service": "kafka-worker", "engine": "kafka", "metric": "consumer_lag", "unit": "messages", "value": 10000.0},
    ]

def main() -> int:
    print(json.dumps(summarize(fixtures()), sort_keys=True, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
\`\`\`

## 2. test_telemetry_quality.py
\`\`\`python
from __future__ import annotations

import json
import math
import unittest

from telemetry_quality import (
    Engine,
    Reading,
    Severity,
    ValidationError,
    classify,
    fixtures,
    parse,
    summarize,
)

class QualityTests(unittest.TestCase):
    def test_fixtures(self) -> None:
        report = summarize(fixtures())
        self.assertEqual(report["total"], 3)
        self.assertEqual(report["counts"], {"healthy": 0, "warning": 1, "critical": 2})

    def test_empty(self) -> None:
        self.assertEqual(summarize([])["total"], 0)

    def test_permutation(self) -> None:
        self.assertEqual(summarize(fixtures()), summarize(list(reversed(fixtures()))))

    def test_conservation(self) -> None:
        report = summarize(fixtures())
        self.assertEqual(sum(report["counts"].values()), report["total"])

    def test_json(self) -> None:
        json.dumps(summarize(fixtures()), allow_nan=False)

    def test_parse(self) -> None:
        self.assertEqual(parse(fixtures()[0]).engine, Engine.POSTGRESQL)

    def test_invalid_values(self) -> None:
        for value in (True, -1, math.nan, math.inf, "secret"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    parse({**fixtures()[0], "value": value})

    def test_unknown_engine(self) -> None:
        with self.assertRaises(ValidationError):
            parse({**fixtures()[0], "engine": "mysql"})

    def test_bad_unit(self) -> None:
        with self.assertRaises(ValidationError):
            parse({**fixtures()[0], "unit": "milliseconds"})

    def test_bad_metric(self) -> None:
        with self.assertRaises(ValidationError):
            parse({**fixtures()[0], "metric": "wrong"})

    def test_bad_service(self) -> None:
        with self.assertRaises(ValidationError):
            parse({**fixtures()[0], "service": "=cmd"})

    def test_duplicate(self) -> None:
        with self.assertRaises(ValidationError):
            summarize([fixtures()[0], fixtures()[0]])

    def test_oversized(self) -> None:
        with self.assertRaises(ValidationError):
            summarize([fixtures()[0]] * 101)

    def test_invalid_batch(self) -> None:
        with self.assertRaises(ValidationError):
            summarize({})

    def test_boundaries(self) -> None:
        for engine, warning, critical in (
            (Engine.POSTGRESQL, 30.0, 120.0),
            (Engine.ELASTICSEARCH, 200.0, 500.0),
            (Engine.KAFKA, 1000.0, 10000.0),
        ):
            self.assertEqual(classify(Reading("node", engine, math.nextafter(warning, -math.inf))), Severity.HEALTHY)
            self.assertEqual(classify(Reading("node", engine, warning)), Severity.WARNING)
            self.assertEqual(classify(Reading("node", engine, math.nextafter(critical, -math.inf))), Severity.WARNING)
            self.assertEqual(classify(Reading("node", engine, critical)), Severity.CRITICAL)

    def test_no_secrets(self) -> None:
        self.assertNotIn("password", json.dumps(summarize(fixtures())))

if __name__ == "__main__":
    unittest.main()
\`\`\`

## 3. pyproject.toml
\`\`\`toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "B", "UP", "SIM", "S"]
ignore = ["S101"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_configs = true
files = ["telemetry_quality.py", "test_telemetry_quality.py"]
\`\`\`

## 4. .pre-commit-config.yaml
\`\`\`yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.13.2 # Example tag; replace with reviewed immutable revision
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: local
    hooks:
      - id: mypy-strict
        name: mypy strict
        entry: python -m mypy --strict telemetry_quality.py test_telemetry_quality.py
        language: system
        pass_filenames: false
\`\`\`

## 5. Execute
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install 'ruff>=0.13,<0.15' 'mypy>=1.15,<2' 'pre-commit>=4,<5'
ruff check .
ruff format telemetry_quality.py test_telemetry_quality.py
ruff format --check .
python -m mypy --strict telemetry_quality.py test_telemetry_quality.py
python -m unittest -v test_telemetry_quality.py
python telemetry_quality.py
pre-commit run --all-files
\`\`\`
Windows: use \`py -3 -m venv .venv\` and \`.venv\\Scripts\\Activate.ps1\`. Run Ruff formatting locally before enforcing its check in CI; review changes. Dependency versions are examples, not a verified lockfile.

## 6. CI quality gate example
\`\`\`yaml
name: chapter-068-quality
on: workflow_dispatch
jobs:
  quality:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Require materialized lab sources
        run: |
          test -f telemetry_quality.py
          test -f test_telemetry_quality.py
          test -f pyproject.toml
      - name: Install
        run: python -m pip install 'ruff>=0.13,<0.15' 'mypy>=1.15,<2'
      - name: Ruff lint
        run: ruff check .
      - name: Ruff formatting
        run: ruff format --check .
      - name: mypy strict
        run: python -m mypy --strict telemetry_quality.py test_telemetry_quality.py
      - name: Unit tests
        run: python -m unittest -v test_telemetry_quality.py
\`\`\`
**Template only:** Extract the code blocks to real files and pin approved action SHAs/dependencies before enabling. The job intentionally fails if source files are absent.

## 7. Failure injection
1. Add an unused import and detect F401.
2. Shuffle imports and detect import-order failure.
3. Introduce inconsistent formatting and verify format gate failure.
4. Pass a string to a typed function and verify mypy rejection.
5. Remove a function return annotation and verify strict checking.
6. Add a disposable \`shell=True\` example and review security lint.
7. Insert a fake hardcoded token and compare lint versus dedicated secrets scanning.
8. Bypass pre-commit and verify protected CI still enforces gates.
9. Change PostgreSQL units and verify runtime rejection.
10. Inject NaN/Infinity/boolean and verify runtime validation.
11. Inject duplicate sources and oversized batches.
12. Restore clean code, rerun gates and record evidence.

## 8. Runbooks
**Lint/type failure:** reproduce with pinned tools, repair source, review diff and rerun all gates.

**Security finding:** block release, review exploitability, remediate and add regression.

**CI drift:** compare interpreter, dependencies and tool versions; rebuild on trusted runner.

**Rollback:** revert to known-good revision, rerun gates and document change approval.

## 9. 100-point assessment
| Area | Points |
|---|---:|
| Ruff lint/format/import hygiene | 20 |
| mypy strict typing | 20 |
| Automated tests and runtime validation | 20 |
| Security lint and supply chain | 15 |
| Pre-commit and CI quality gates | 15 |
| Incident simulations and runbooks | 10 |

**Pass:** 90/100 with all mandatory security checks passing. Execution and quality-gate verification remain pending until actually run.
