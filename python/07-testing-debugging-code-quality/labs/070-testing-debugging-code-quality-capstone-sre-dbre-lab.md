# Chapter 070 — Testing, Debugging and Code Quality Enterprise SRE/DBRE Capstone Lab

**Python 3.11+ | Synthetic PostgreSQL, Elasticsearch, Kafka | No live infrastructure**

## File layout
\`\`\`text
ch070/
  capstone.py
  test_capstone.py
  test_properties.py
  pyproject.toml
  requirements-dev.txt
\`\`\`

## 1. Complete application — capstone.py
\`\`\`python
"""Deterministic SRE/DBRE telemetry quality capstone; offline only."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
import logging
import math
import re
import time
from typing import Callable, Final, Mapping, Protocol, TypedDict

IDENTIFIER: Final = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
MAX_BATCH: Final = 100

class Engine(StrEnum):
    POSTGRESQL = "postgresql"
    ELASTICSEARCH = "elasticsearch"
    KAFKA = "kafka"

class Severity(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"

POLICY: Final[Mapping[Engine, tuple[str, str, float, float]]] = {
    Engine.POSTGRESQL: ("replication_lag", "seconds", 30.0, 120.0),
    Engine.ELASTICSEARCH: ("search_latency", "milliseconds", 200.0, 500.0),
    Engine.KAFKA: ("consumer_lag", "messages", 1000.0, 10000.0),
}

class ValidationError(ValueError):
    pass

class InputRow(TypedDict):
    engine: str
    service: str
    metric: str
    unit: str
    value: float

class Summary(TypedDict):
    dry_run: bool
    total: int
    counts: dict[str, int]

@dataclass(frozen=True, slots=True)
class Reading:
    engine: Engine
    service: str
    value: float

def validate(raw: object) -> Reading:
    if not isinstance(raw, dict) or set(raw) != {"engine", "service", "metric", "unit", "value"}:
        raise ValidationError("invalid schema")
    engine_raw, service = raw["engine"], raw["service"]
    if not isinstance(engine_raw, str):
        raise ValidationError("invalid engine")
    try:
        engine = Engine(engine_raw)
    except ValueError as exc:
        raise ValidationError("invalid engine") from exc
    if not isinstance(service, str) or IDENTIFIER.fullmatch(service) is None:
        raise ValidationError("invalid service")
    metric, unit, _, _ = POLICY[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise ValidationError("invalid metric or unit")
    value = raw["value"]
    if type(value) not in (int, float):
        raise ValidationError("invalid numeric type")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValidationError("invalid numeric value") from exc
    if not math.isfinite(number) or number < 0:
        raise ValidationError("invalid numeric value")
    return Reading(engine, service, number)

def classify(reading: Reading) -> Severity:
    if reading.engine not in POLICY or not math.isfinite(reading.value) or reading.value < 0:
        raise ValidationError("invalid reading")
    _, _, warning, critical = POLICY[reading.engine]
    return Severity.CRITICAL if reading.value >= critical else (
        Severity.WARNING if reading.value >= warning else Severity.HEALTHY
    )

def summarize(raw: object) -> Summary:
    if not isinstance(raw, list) or len(raw) > MAX_BATCH:
        raise ValidationError("invalid batch")
    readings = [validate(row) for row in raw]
    if len({(r.engine, r.service) for r in readings}) != len(readings):
        raise ValidationError("duplicate source")
    counts = {severity.value: 0 for severity in Severity}
    for reading in readings:
        counts[classify(reading).value] += 1
    return {"dry_run": True, "total": len(readings), "counts": counts}

class MetricsSink(Protocol):
    def record(self, engine: Engine, severity: Severity, duration_ns: int) -> None: ...

class InMemoryMetrics:
    def __init__(self) -> None:
        self.counters: dict[tuple[Engine, Severity], int] = {}
        self.durations: list[int] = []

    def record(self, engine: Engine, severity: Severity, duration_ns: int) -> None:
        if engine not in POLICY or severity not in Severity or duration_ns < 0:
            raise ValidationError("invalid metric labels")
        key = (engine, severity)
        self.counters[key] = self.counters.get(key, 0) + 1
        self.durations.append(duration_ns)

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Do not interpolate record.args or serialize arbitrary exception details.
        event = record.msg if isinstance(record.msg, str) else "unknown_event"
        if event not in ("batch_processed", "instrumentation_failed"):
            event = "unknown_event"
        return json.dumps({
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "event": event,
            "correlation_id": getattr(record, "correlation_id", None),
        }, sort_keys=True)

def make_logger(stream: object) -> logging.Logger:
    logger = logging.Logger("ch070.capstone", level=logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger

def run(
    rows: object,
    *,
    correlation_id: str,
    logger: logging.Logger,
    metrics: MetricsSink,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
) -> Summary:
    if not isinstance(correlation_id, str) or IDENTIFIER.fullmatch(correlation_id) is None:
        raise ValidationError("invalid correlation ID")
    started = clock_ns()
    result = summarize(rows)
    elapsed = max(0, clock_ns() - started)
    # The output remains authoritative even if the observability sink fails.
    try:
        if not isinstance(rows, list):
            raise ValidationError("invalid batch")
        for raw in rows:
            reading = validate(raw)
            metrics.record(reading.engine, classify(reading), elapsed)
        logger.info("batch_processed", extra={"correlation_id": correlation_id})
    except Exception:
        # A production service should count/report instrumentation drops via
        # a protected fallback. No raw payloads or exception text are logged.
        try:
            logger.warning("instrumentation_failed", extra={"correlation_id": correlation_id})
        except Exception:
            pass
    return result

def fixtures() -> list[InputRow]:
    return [
        {"engine": "postgresql", "service": "pg-replica", "metric": "replication_lag", "unit": "seconds", "value": 45.0},
        {"engine": "elasticsearch", "service": "es-search", "metric": "search_latency", "unit": "milliseconds", "value": 650.0},
        {"engine": "kafka", "service": "kafka-worker", "metric": "consumer_lag", "unit": "messages", "value": 10000.0},
    ]

def main() -> int:
    import sys
    logger = make_logger(sys.stderr)
    result = run(fixtures(), correlation_id="synthetic-capstone", logger=logger, metrics=InMemoryMetrics())
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
\`\`\`

## 2. Complete unittest suite — test_capstone.py
\`\`\`python
import io
import json
import math
import unittest
from unittest.mock import Mock

from capstone import (
    Engine, InMemoryMetrics, Reading, Severity, ValidationError, classify,
    fixtures, make_logger, run, summarize, validate,
)

PG = {"engine": "postgresql", "service": "pg-replica",
      "metric": "replication_lag", "unit": "seconds", "value": 45.0}

class CapstoneTests(unittest.TestCase):
    def setUp(self):
        self.stream = io.StringIO()
        self.logger = make_logger(self.stream)
        self.metrics = InMemoryMetrics()

    def test_summary(self):
        self.assertEqual(summarize(fixtures())["counts"],
                         {"healthy": 0, "warning": 1, "critical": 2})

    def test_empty(self):
        self.assertEqual(summarize([])["total"], 0)

    def test_permutation(self):
        self.assertEqual(summarize(fixtures()), summarize(list(reversed(fixtures()))))

    def test_conservation(self):
        result = summarize(fixtures())
        self.assertEqual(sum(result["counts"].values()), result["total"])

    def test_schema(self):
        with self.assertRaises(ValidationError):
            validate({"wrong": 1})

    def test_bad_engine(self):
        with self.assertRaises(ValidationError):
            validate({**PG, "engine": "mysql"})

    def test_bad_unit(self):
        with self.assertRaises(ValidationError):
            validate({**PG, "unit": "ms"})

    def test_bad_identifier(self):
        with self.assertRaises(ValidationError):
            validate({**PG, "service": "node; rm -rf /"})

    def test_bad_values(self):
        for value in (True, -1, math.nan, math.inf, "45"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate({**PG, "value": value})

    def test_duplicate(self):
        with self.assertRaises(ValidationError):
            summarize([PG, PG])

    def test_oversized(self):
        with self.assertRaises(ValidationError):
            summarize([PG] * 101)

    def test_thresholds(self):
        self.assertEqual(classify(Reading(Engine.POSTGRESQL, "node", 30)), Severity.WARNING)
        self.assertEqual(classify(Reading(Engine.POSTGRESQL, "node", 120)), Severity.CRITICAL)

    def test_metrics(self):
        result = run(fixtures(), correlation_id="request-1", logger=self.logger,
                     metrics=self.metrics, clock_ns=iter((100, 125)).__next__)
        self.assertEqual(result["total"], 3)
        self.assertEqual(len(self.metrics.durations), 3)
        self.assertEqual(self.metrics.durations, [25, 25, 25])

    def test_logging(self):
        run(fixtures(), correlation_id="request-1", logger=self.logger,
            metrics=self.metrics, clock_ns=iter((100, 125)).__next__)
        entry = json.loads(self.stream.getvalue().splitlines()[0])
        self.assertEqual(entry["event"], "batch_processed")
        self.assertEqual(entry["correlation_id"], "request-1")
        self.assertTrue(entry["timestamp"].endswith("+00:00"))

    def test_sink_failure(self):
        sink = Mock()
        sink.record.side_effect = RuntimeError("password=SECRET")
        result = run(fixtures(), correlation_id="request-1", logger=self.logger,
                     metrics=sink, clock_ns=iter((100, 125)).__next__)
        self.assertEqual(result["total"], 3)
        self.assertNotIn("SECRET", self.stream.getvalue())
        self.assertIn("instrumentation_failed", self.stream.getvalue())

    def test_bad_correlation(self):
        with self.assertRaises(ValidationError):
            run(fixtures(), correlation_id="../secret", logger=self.logger, metrics=self.metrics)

    def test_log_interpolation_safe(self):
        self.logger.info("batch_processed %s", "TOKEN-SECRET")
        self.assertNotIn("TOKEN-SECRET", self.stream.getvalue())

    def test_no_secret_in_result(self):
        self.assertNotIn("password", json.dumps(summarize(fixtures())))

if __name__ == "__main__":
    unittest.main()
\`\`\`

## 3. Pytest and Hypothesis properties — test_properties.py
\`\`\`python
from unittest.mock import Mock

import pytest
from hypothesis import given, settings, strategies as st

from capstone import (
    Engine, Reading, Severity, ValidationError, classify, fixtures, summarize, validate,
)

ENGINES = (
    ("postgresql", "replication_lag", "seconds"),
    ("elasticsearch", "search_latency", "milliseconds"),
    ("kafka", "consumer_lag", "messages"),
)

@pytest.fixture
def synthetic_batch():
    return fixtures()

@pytest.mark.parametrize("engine,metric,unit", ENGINES)
def test_valid_engine_schema(engine, metric, unit):
    row = {"engine": engine, "service": "node", "metric": metric, "unit": unit, "value": 1.0}
    assert validate(row).value == 1.0

@pytest.mark.parametrize("value", [True, -1, float("nan"), float("inf"), "1"])
def test_invalid_values(value):
    with pytest.raises(ValidationError):
        validate({**fixtures()[0], "value": value})

def test_mock_sink_failure(synthetic_batch):
    from capstone import make_logger, run
    import io
    sink = Mock()
    sink.record.side_effect = RuntimeError("synthetic failure")
    assert run(synthetic_batch, correlation_id="test", logger=make_logger(io.StringIO()),
               metrics=sink, clock_ns=iter((0, 5)).__next__)["total"] == 3

@settings(max_examples=100, deadline=None)
@given(st.lists(st.floats(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False),
                min_size=0, max_size=50))
def test_property_count_conservation(values):
    # Unique identifiers avoid duplicate-source rejection.
    rows = [{**fixtures()[0], "service": f"node{i}", "value": value}
            for i, value in enumerate(values)]
    result = summarize(rows)
    assert sum(result["counts"].values()) == result["total"] == len(rows)

@settings(max_examples=100, deadline=None)
@given(st.floats(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False))
def test_property_monotonic_severity(value):
    before = classify(Reading(Engine.POSTGRESQL, "node", value))
    after = classify(Reading(Engine.POSTGRESQL, "node", value + 1))
    order = {Severity.HEALTHY: 0, Severity.WARNING: 1, Severity.CRITICAL: 2}
    assert order[after] >= order[before]

@settings(max_examples=100, deadline=None)
@given(st.lists(st.integers(min_value=0, max_value=100000), min_size=0, max_size=30))
def test_property_order_independence(values):
    rows = [{**fixtures()[0], "service": f"node{i}", "value": float(value)}
            for i, value in enumerate(values)]
    assert summarize(rows) == summarize(list(reversed(rows)))
\`\`\`

## 4. Tooling configuration — pyproject.toml
\`\`\`toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "B", "UP", "S"]
ignore = ["S101"]

[tool.ruff.lint.per-file-ignores]
"test_*.py" = ["S101"]

[tool.mypy]
python_version = "3.11"
strict = true
files = ["capstone.py"]
\`\`\`

## 5. requirements-dev.txt
\`\`\`text
pytest>=8,<10
hypothesis>=6,<7
ruff>=0.13,<0.15
mypy>=1.15,<2
bandit>=1.8,<2
pip-audit>=2.8,<3
\`\`\`
These are illustrative ranges, not a tested lockfile. Production CI must pin reviewed versions and hashes.

## 6. Local execution
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m compileall -q capstone.py test_capstone.py test_properties.py
python -m unittest -v test_capstone.py
python -m pytest -v test_capstone.py test_properties.py
ruff check .
ruff format capstone.py test_capstone.py test_properties.py
ruff format --check .
python -m mypy --strict capstone.py
bandit -r capstone.py -ll
python -m pip_audit -r requirements-dev.txt
python capstone.py
\`\`\`
Windows PowerShell: use \`py -3\` and \`.venv\\Scripts\\Activate.ps1\`. Review formatter changes before committing.

## 7. Debugging and profiling
\`\`\`bash
python -m pdb capstone.py
python -m cProfile -s cumulative capstone.py
python -c "import tracemalloc,capstone; tracemalloc.start(); capstone.summarize(capstone.fixtures()); print(tracemalloc.get_traced_memory()); tracemalloc.stop()"
\`\`\`
For a bounded synthetic hang test, run a separate local \`faulthandler.dump_traceback_later\` exercise as described in Chapter 066. Do not attach interactive debuggers or publish raw traceback dumps from production. \`tracemalloc\` does not measure total RSS.

## 8. CI quality/security gate template
\`\`\`yaml
name: chapter-070-capstone
on: workflow_dispatch
jobs:
  acceptance:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Verify materialized files
        run: |
          test -f capstone.py
          test -f test_capstone.py
          test -f test_properties.py
          test -f pyproject.toml
          test -f requirements-dev.txt
      - name: Install
        run: python -m pip install -r requirements-dev.txt
      - name: Tests
        run: python -m pytest -v test_capstone.py test_properties.py
      - name: Ruff lint
        run: ruff check .
      - name: Ruff format
        run: ruff format --check .
      - name: mypy strict
        run: python -m mypy --strict capstone.py
      - name: Bandit
        run: bandit -r capstone.py -ll
      - name: Dependency audit
        run: python -m pip_audit -r requirements-dev.txt
\`\`\`
**Fail-closed template:** source is currently embedded in Markdown. Extract files, pin reviewed action SHAs and dependencies, add approved secrets scanning, and validate the workflow on a trusted runner before enabling it. Do not claim this template has executed.

## 9. Enterprise incident simulations
1. Inject NaN, Infinity, boolean and negative telemetry.
2. Inject unknown engine, metric and unit.
3. Inject shell metacharacters in source identifiers.
4. Inject duplicate source and oversized batch.
5. Change a warning threshold; observe boundary test failure.
6. Reverse input order; verify deterministic summary.
7. Make the metric sink raise; verify sanitized fallback and valid summary.
8. Inject an unsafe correlation ID; verify rejection.
9. Attempt to interpolate a fake token into logs; verify it is omitted.
10. Run cProfile and identify cumulative hot paths.
11. Use tracemalloc and compare with process RSS.
12. Break a type contract and verify mypy detects it.
13. Introduce an unused import and verify Ruff detects it.
14. Introduce a throwaway \`shell=True\` snippet and verify Bandit triage.
15. Simulate pip-audit advisory outage; ensure release blocks, then restore and rerun.

## 10. Production runbooks
**Bad alerts:** stop rollout, reproduce failing input, correct validation/classification, rerun tests and roll back if needed.

**Observability outage:** check handler configuration, drop counters and collector health, restore stable instrumentation.

**Resource regression:** capture bounded profiles, compare with baselines and roll back.

**Security gate failure:** block release, triage Bandit/SCA/secrets findings, remediate and retest.

**Rollback:** restore known-good code and approved dependency lock, rerun acceptance suite, verify SLOs and document change authorization.

## 11. 100-point final assessment
| Category | Points |
|---|---:|
| Validation and deterministic business logic | 15 |
| unittest and pytest fixtures/mocks/parameterization | 15 |
| Hypothesis properties, invariants and shrinking | 15 |
| Structured logging, metrics and failure injection | 15 |
| Debugging, profiling and memory diagnostics | 10 |
| Ruff and mypy quality gates | 10 |
| Bandit, pip-audit and secrets controls | 10 |
| CI, runbooks, incident response and rollback | 10 |

**Pass:** 90/100; no critical unresolved security finding; all tests and required gates independently executed; sanitized evidence and rollback approved. Publication does **not** mean these checks have run. Real PostgreSQL/Redis integration remains covered by the separate Chapter 065 disposable Testcontainers lab.
