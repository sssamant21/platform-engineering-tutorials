# Chapter 033 — Inheritance and SRE/DBRE Health Adapters Lab

**Python 3.10+ · Standard library only · Synthetic data · Read-only**

## Objectives

Implement an abstract base class, three specialized SRE/DBRE health adapters, overridden classification, cooperative `super()` and C3 method resolution, a deterministic JSON CLI, unit tests and operational failure injection. No credentials, network requests or mutations.

## Project layout

```text
ch033/
  checks.py
  cli.py
  sample.json
  test_checks.py
```

## 1. checks.py

```python
from abc import ABC, abstractmethod
import math


def finite_nonnegative(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return float(value)


class BaseHealthCheck(ABC):
    kind = None
    unit = None

    def __init__(self, service, warning, critical):
        if not isinstance(service, str) or not service.strip() or len(service) > 64:
            raise ValueError("invalid service")
        warning = finite_nonnegative(warning, "warning")
        critical = finite_nonnegative(critical, "critical")
        if not 0 < warning < critical:
            raise ValueError("thresholds must satisfy 0 < warning < critical")
        self._service = service
        self._warning = warning
        self._critical = critical

    @property
    def service(self):
        return self._service

    @abstractmethod
    def classify(self, value):
        """Return healthy, warning, or critical."""

    def _severity(self, value):
        value = finite_nonnegative(value, "metric")
        if value >= self._critical:
            return "critical"
        if value >= self._warning:
            return "warning"
        return "healthy"

    def summary(self, value):
        status = self.classify(value)
        if status not in ("healthy", "warning", "critical"):
            raise ValueError("subclass violated status contract")
        return {
            "service": self.service,
            "kind": self.kind,
            "unit": self.unit,
            "value": finite_nonnegative(value, "metric"),
            "status": status,
        }


class PostgreSQLLagCheck(BaseHealthCheck):
    kind = "postgresql_replication_lag"
    unit = "seconds"

    def __init__(self, service, warning=30, critical=120):
        super().__init__(service, warning, critical)

    def classify(self, value):
        return self._severity(value)


class ElasticsearchLatencyCheck(BaseHealthCheck):
    kind = "elasticsearch_search_latency"
    unit = "milliseconds"

    def __init__(self, service, warning=200, critical=500):
        super().__init__(service, warning, critical)

    def classify(self, value):
        return self._severity(value)


class KafkaConsumerLagCheck(BaseHealthCheck):
    kind = "kafka_consumer_lag"
    unit = "messages"

    def __init__(self, service, warning=1000, critical=10000):
        super().__init__(service, warning, critical)

    def classify(self, value):
        return self._severity(value)


KINDS = {
    "postgresql": PostgreSQLLagCheck,
    "elasticsearch": ElasticsearchLatencyCheck,
    "kafka": KafkaConsumerLagCheck,
}


def make_check(kind, service, warning=None, critical=None):
    if kind not in KINDS:
        raise ValueError("unknown check kind")
    kwargs = {}
    if warning is not None:
        kwargs["warning"] = warning
    if critical is not None:
        kwargs["critical"] = critical
    return KINDS[kind](service, **kwargs)


def report(rows):
    if not isinstance(rows, list):
        raise ValueError("expected JSON array")
    seen = set()
    results = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"kind", "service", "value"}:
            raise ValueError("invalid record schema")
        identity = (row["kind"], row["service"])
        if identity in seen:
            raise ValueError("duplicate check")
        check = make_check(row["kind"], row["service"])
        results.append(check.summary(row["value"]))
        seen.add(identity)
    results.sort(key=lambda r: (r["kind"], r["service"]))
    return {"schema_version": 1, "check_count": len(results), "checks": results}


class Root:
    def tags(self):
        return ["root"]


class AuditMixin(Root):
    def tags(self):
        return ["audit", *super().tags()]


class RetryMixin(Root):
    def tags(self):
        return ["retry", *super().tags()]


class CooperativeTool(AuditMixin, RetryMixin):
    pass
```

## 2. cli.py

```python
import argparse
import json
from pathlib import Path
from checks import report


def run(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
        rows = json.loads(
            raw,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("input file unreadable or invalid") from exc
    return report(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline inheritance health lab")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.input)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 3. sample.json

```json
[
  {"kind":"postgresql","service":"pg-replica","value":45},
  {"kind":"elasticsearch","service":"search-api","value":650},
  {"kind":"kafka","service":"consumer-a","value":100}
]
```

## 4. test_checks.py — 32 tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from checks import (
    BaseHealthCheck, PostgreSQLLagCheck, ElasticsearchLatencyCheck,
    KafkaConsumerLagCheck, CooperativeTool, make_check, report,
)
from cli import run


class CheckTests(unittest.TestCase):
    def test_pg_healthy(self): self.assertEqual(PostgreSQLLagCheck("pg").classify(1), "healthy")
    def test_pg_warning(self): self.assertEqual(PostgreSQLLagCheck("pg").classify(30), "warning")
    def test_pg_critical(self): self.assertEqual(PostgreSQLLagCheck("pg").classify(120), "critical")
    def test_es_healthy(self): self.assertEqual(ElasticsearchLatencyCheck("es").classify(10), "healthy")
    def test_es_warning(self): self.assertEqual(ElasticsearchLatencyCheck("es").classify(200), "warning")
    def test_es_critical(self): self.assertEqual(ElasticsearchLatencyCheck("es").classify(500), "critical")
    def test_kafka_healthy(self): self.assertEqual(KafkaConsumerLagCheck("k").classify(10), "healthy")
    def test_kafka_warning(self): self.assertEqual(KafkaConsumerLagCheck("k").classify(1000), "warning")
    def test_kafka_critical(self): self.assertEqual(KafkaConsumerLagCheck("k").classify(10000), "critical")
    def test_custom_thresholds(self): self.assertEqual(PostgreSQLLagCheck("pg", 5, 10).classify(7), "warning")
    def test_base_abstract(self):
        with self.assertRaises(TypeError): BaseHealthCheck("base", 1, 2)
    def test_inherited_property(self): self.assertEqual(PostgreSQLLagCheck("pg").service, "pg")
    def test_summary_unit(self): self.assertEqual(PostgreSQLLagCheck("pg").summary(1)["unit"], "seconds")
    def test_summary_kind(self): self.assertEqual(ElasticsearchLatencyCheck("es").summary(1)["kind"], "elasticsearch_search_latency")
    def test_empty_service(self):
        with self.assertRaises(ValueError): PostgreSQLLagCheck("")
    def test_bad_thresholds(self):
        with self.assertRaises(ValueError): PostgreSQLLagCheck("pg", 20, 10)
    def test_negative(self):
        with self.assertRaises(ValueError): PostgreSQLLagCheck("pg").classify(-1)
    def test_nan(self):
        with self.assertRaises(ValueError): PostgreSQLLagCheck("pg").classify(float("nan"))
    def test_infinite(self):
        with self.assertRaises(ValueError): PostgreSQLLagCheck("pg").classify(float("inf"))
    def test_boolean(self):
        with self.assertRaises(ValueError): PostgreSQLLagCheck("pg").classify(True)
    def test_unknown_kind(self):
        with self.assertRaises(ValueError): make_check("unknown", "svc")
    def test_factory_pg(self): self.assertIsInstance(make_check("postgresql", "pg"), PostgreSQLLagCheck)
    def test_factory_es(self): self.assertIsInstance(make_check("elasticsearch", "es"), ElasticsearchLatencyCheck)
    def test_factory_kafka(self): self.assertIsInstance(make_check("kafka", "k"), KafkaConsumerLagCheck)
    def test_sort(self):
        rows = [{"kind":"kafka","service":"z","value":1},{"kind":"elasticsearch","service":"a","value":1}]
        self.assertEqual(report(rows)["checks"][0]["kind"], "elasticsearch_search_latency")
    def test_duplicate(self):
        row = {"kind":"postgresql","service":"pg","value":1}
        with self.assertRaises(ValueError): report([row, row])
    def test_bad_schema(self):
        with self.assertRaises(ValueError): report([{"kind":"postgresql"}])
    def test_empty(self): self.assertEqual(report([])["check_count"], 0)
    def test_mro(self):
        self.assertEqual([c.__name__ for c in CooperativeTool.__mro__[:4]],
                         ["CooperativeTool","AuditMixin","RetryMixin","Root"])
    def test_super_chain(self): self.assertEqual(CooperativeTool().tags(), ["audit","retry","root"])
    def test_cli_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.json"
            path.write_text(json.dumps([{"kind":"postgresql","service":"pg","value":45}]), encoding="utf-8")
            self.assertEqual(run(path)["checks"][0]["status"], "warning")
    def test_cli_bad_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text("{bad", encoding="utf-8")
            with self.assertRaises(ValueError): run(path)


if __name__ == "__main__":
    unittest.main()
```

## 5. Run and verify

Linux/macOS/WSL:

```bash
python3 -m venv .venv
./.venv/bin/python -m unittest -v test_checks.py
./.venv/bin/python cli.py --input sample.json
./.venv/bin/python -m py_compile checks.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m unittest -v test_checks.py
.\.venv\Scripts\python.exe cli.py --input sample.json
.\.venv\Scripts\python.exe -m py_compile checks.py cli.py
```

Expected synthetic statuses: PostgreSQL warning, Elasticsearch critical, Kafka healthy. Tests are provided but have not been independently executed.

## 6. Failure injection and troubleshooting

1. Remove a subclass's `classify` implementation: abstract base instantiation fails.
2. Set warning greater than critical: constructor rejects invalid thresholds.
3. Supply negative, NaN, infinity or boolean metric: validation fails closed.
4. Duplicate a `(kind, service)` pair: report rejects the duplicate.
5. Add an unknown record field: schema validation rejects it.
6. Inspect `CooperativeTool.__mro__` and `tags()`: verify cooperative `super()` behavior.
7. Make an override return `"unknown"`: the base report contract rejects it.

| Symptom | Root cause | Response |
|---|---|---|
| Abstract class cannot instantiate | Required override missing | Implement required method |
| Wrong method called | Unexpected MRO | Inspect `__mro__` |
| Base state missing | Constructor skipped `super()` | Restore cooperative initialization |
| Report schema changed | Incompatible override | Add contract test and revert |
| Unexpected threshold | Incorrect unit or policy | Verify reviewed service policy |

## 7. Production runbooks

**MRO regression:** stop deployment, inspect the linearized MRO, restore cooperative `super()`, run regression tests and redeploy approved artifact.

**Adapter contract breach:** block report publication, compare status/schema contract, revert the subclass and verify deterministic output.

**Threshold incident:** verify unit and approved warning/critical levels, correlate with authoritative metrics and obtain service-owner approval before changing policy.

**Safety:** synthetic data only. Real adapters require read-only identity, explicit target, bounded timeouts, logging controls and review.

## 8. Acceptance

- [ ] 32 tests pass locally.
- [ ] ABC contract and subclass overrides validated.
- [ ] `super()` and MRO verified.
- [ ] Invalid data rejected.
- [ ] Deterministic sanitized JSON output.
- [ ] No real credentials, network access or mutations.
