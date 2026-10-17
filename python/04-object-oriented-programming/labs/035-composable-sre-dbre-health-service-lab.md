# Chapter 035 — Composable SRE/DBRE Health Service Lab

**Python 3.10+ · Standard library · Offline, synthetic and read-only**

## Goal and layout

Create an ABC-based metric source contract, three synthetic adapters, a policy strategy, a sink interface, a composed health service and a deterministic JSON CLI.

```text
ch035/
  health.py
  cli.py
  sample.json
  test_health.py
```

## 1. health.py

```python
"""Composable, synthetic SRE/DBRE health evaluation."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import math


def metric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("metric must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError("metric must be finite and nonnegative")
    return float(value)


class MetricSource(ABC):
    kind = None
    unit = None

    @abstractmethod
    def read(self) -> float:
        raise NotImplementedError


class SyntheticPostgreSQL(MetricSource):
    kind = "postgresql"
    unit = "seconds"

    def __init__(self, value):
        self._value = metric(value)

    def read(self):
        return self._value


class SyntheticElasticsearch(MetricSource):
    kind = "elasticsearch"
    unit = "milliseconds"

    def __init__(self, value):
        self._value = metric(value)

    def read(self):
        return self._value


class SyntheticKafka(MetricSource):
    kind = "kafka"
    unit = "messages"

    def __init__(self, value):
        self._value = metric(value)

    def read(self):
        return self._value


@dataclass(frozen=True)
class ThresholdPolicy:
    warning: float
    critical: float

    def __post_init__(self):
        if not 0 < metric(self.warning) < metric(self.critical):
            raise ValueError("thresholds must satisfy 0 < warning < critical")

    def classify(self, value):
        value = metric(value)
        if value >= self.critical:
            return "critical"
        if value >= self.warning:
            return "warning"
        return "healthy"


class ReportSink(ABC):
    @abstractmethod
    def publish(self, report):
        raise NotImplementedError


class MemorySink(ReportSink):
    def __init__(self):
        self._reports = []

    @property
    def reports(self):
        return tuple(self._reports)

    def publish(self, report):
        if not isinstance(report, dict) or report.get("schema_version") != 1:
            raise ValueError("invalid report")
        self._reports.append(report)


class HealthService:
    def __init__(self, service, source: MetricSource, policy: ThresholdPolicy):
        if not isinstance(service, str) or not service.strip() or len(service) > 64:
            raise ValueError("invalid service")
        if not isinstance(source, MetricSource):
            raise TypeError("source must implement MetricSource ABC")
        if not isinstance(policy, ThresholdPolicy):
            raise TypeError("invalid policy")
        if not isinstance(source.kind, str) or not source.kind:
            raise ValueError("missing source kind")
        if not isinstance(source.unit, str) or not source.unit:
            raise ValueError("missing source unit")
        self._service = service
        self._source = source
        self._policy = policy

    def evaluate(self):
        value = metric(self._source.read())
        return {
            "service": self._service,
            "kind": self._source.kind,
            "unit": self._source.unit,
            "value": value,
            "status": self._policy.classify(value),
        }


REGISTRY = {
    "postgresql": (SyntheticPostgreSQL, ThresholdPolicy(30, 120)),
    "elasticsearch": (SyntheticElasticsearch, ThresholdPolicy(200, 500)),
    "kafka": (SyntheticKafka, ThresholdPolicy(1000, 10000)),
}


def create_service(kind, service, value):
    if not isinstance(kind, str) or kind not in REGISTRY:
        raise ValueError("unknown source kind")
    cls, policy = REGISTRY[kind]
    return HealthService(service, cls(value), policy)


def evaluate_batch(rows, sink=None):
    if not isinstance(rows, list):
        raise ValueError("expected JSON array")
    if sink is not None and not isinstance(sink, ReportSink):
        raise TypeError("invalid sink")
    seen = set()
    checks = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"kind", "service", "value"}:
            raise ValueError("invalid record schema")
        identity = (row["kind"], row["service"])
        if identity in seen:
            raise ValueError("duplicate check")
        checks.append(create_service(row["kind"], row["service"], row["value"]).evaluate())
        seen.add(identity)
    checks.sort(key=lambda item: (item["kind"], item["service"]))
    result = {"schema_version": 1, "check_count": len(checks), "checks": checks}
    if sink is not None:
        sink.publish(result)
    return result
```

## 2. cli.py

```python
import argparse
import json
from pathlib import Path
from health import evaluate_batch


def run(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
        rows = json.loads(
            raw,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("input file unreadable or invalid") from exc
    return evaluate_batch(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline composable SRE health lab")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.input)
    except (ValueError, TypeError) as exc:
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

## 4. test_health.py — 32 unit tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from health import (
    MetricSource, ReportSink, SyntheticPostgreSQL, SyntheticElasticsearch,
    SyntheticKafka, ThresholdPolicy, MemorySink, HealthService,
    create_service, evaluate_batch,
)
from cli import run


class HealthTests(unittest.TestCase):
    def test_source_abstract(self):
        with self.assertRaises(TypeError): MetricSource()
    def test_sink_abstract(self):
        with self.assertRaises(TypeError): ReportSink()
    def test_pg_read(self): self.assertEqual(SyntheticPostgreSQL(4).read(), 4)
    def test_es_read(self): self.assertEqual(SyntheticElasticsearch(4).read(), 4)
    def test_kafka_read(self): self.assertEqual(SyntheticKafka(4).read(), 4)
    def test_pg_healthy(self): self.assertEqual(create_service("postgresql","pg",1).evaluate()["status"],"healthy")
    def test_pg_warning(self): self.assertEqual(create_service("postgresql","pg",30).evaluate()["status"],"warning")
    def test_pg_critical(self): self.assertEqual(create_service("postgresql","pg",120).evaluate()["status"],"critical")
    def test_es_warning(self): self.assertEqual(create_service("elasticsearch","es",200).evaluate()["status"],"warning")
    def test_es_critical(self): self.assertEqual(create_service("elasticsearch","es",500).evaluate()["status"],"critical")
    def test_kafka_warning(self): self.assertEqual(create_service("kafka","k",1000).evaluate()["status"],"warning")
    def test_kafka_critical(self): self.assertEqual(create_service("kafka","k",10000).evaluate()["status"],"critical")
    def test_custom_policy(self): self.assertEqual(ThresholdPolicy(2,4).classify(3),"warning")
    def test_bad_policy(self):
        with self.assertRaises(ValueError): ThresholdPolicy(10,2)
    def test_nan_policy(self):
        with self.assertRaises(ValueError): ThresholdPolicy(float("nan"),2)
    def test_bool_policy(self):
        with self.assertRaises(ValueError): ThresholdPolicy(True,2)
    def test_negative_value(self):
        with self.assertRaises(ValueError): SyntheticPostgreSQL(-1)
    def test_infinite_value(self):
        with self.assertRaises(ValueError): SyntheticKafka(float("inf"))
    def test_bool_value(self):
        with self.assertRaises(ValueError): SyntheticElasticsearch(True)
    def test_unknown_kind(self):
        with self.assertRaises(ValueError): create_service("unknown","svc",1)
    def test_invalid_service(self):
        with self.assertRaises(ValueError): create_service("postgresql","",1)
    def test_invalid_source(self):
        with self.assertRaises(TypeError): HealthService("x",object(),ThresholdPolicy(1,2))
    def test_injected_fake(self):
        class Fake(MetricSource):
            kind = "fake"
            unit = "milliseconds"
            def read(self): return 250
        self.assertEqual(HealthService("fake",Fake(),ThresholdPolicy(200,500)).evaluate()["status"],"warning")
    def test_invalid_fake_return(self):
        class Fake(MetricSource):
            kind = "fake"
            unit = "ms"
            def read(self): return "bad"
        with self.assertRaises(ValueError): HealthService("x",Fake(),ThresholdPolicy(1,2)).evaluate()
    def test_sink_publish(self):
        sink = MemorySink()
        evaluate_batch([],sink)
        self.assertEqual(len(sink.reports),1)
    def test_sink_invalid(self):
        with self.assertRaises(ValueError): MemorySink().publish({})
    def test_no_partial_publish(self):
        sink = MemorySink()
        with self.assertRaises(ValueError):
            evaluate_batch([{"kind":"postgresql","service":"a","value":1},{"bad":1}],sink)
        self.assertEqual(len(sink.reports),0)
    def test_duplicate(self):
        row={"kind":"postgresql","service":"pg","value":1}
        with self.assertRaises(ValueError): evaluate_batch([row,row])
    def test_sorted(self):
        rows=[{"kind":"kafka","service":"z","value":1},{"kind":"elasticsearch","service":"a","value":1}]
        self.assertEqual(evaluate_batch(rows)["checks"][0]["kind"],"elasticsearch")
    def test_bad_schema(self):
        with self.assertRaises(ValueError): evaluate_batch([{"kind":"postgresql"}])
    def test_cli_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"fixture.json"
            path.write_text(json.dumps([{"kind":"postgresql","service":"pg","value":45}]),encoding="utf-8")
            self.assertEqual(run(path)["checks"][0]["status"],"warning")
    def test_cli_bad_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"bad.json"
            path.write_text("{bad",encoding="utf-8")
            with self.assertRaises(ValueError): run(path)


if __name__ == "__main__":
    unittest.main()
```

## 5. Execute

Linux/macOS/WSL:

```bash
python3 -m venv .venv
./.venv/bin/python -m unittest -v test_health.py
./.venv/bin/python cli.py --input sample.json
./.venv/bin/python -m py_compile health.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m unittest -v test_health.py
.\.venv\Scripts\python.exe cli.py --input sample.json
.\.venv\Scripts\python.exe -m py_compile health.py cli.py
```

Expected classifications: PostgreSQL warning, Elasticsearch critical, Kafka healthy.

## 6. Failure injection

1. Instantiate `MetricSource` or `ReportSink`: ABC enforcement fails.
2. Inject a fake returning a string: validation rejects the result.
3. Pass NaN, infinity, negative or boolean values: fail closed.
4. Add an unknown plugin name: registry rejects it.
5. Supply duplicate records: batch rejects duplicates.
6. Include a malformed second row: sink receives **no partial report**.
7. Supply invalid thresholds: policy construction fails.

## 7. Troubleshooting and production runbooks

**Interface mismatch:** identify missing abstract method, inspect implementation signature, add contract tests.

**Misclassification:** compare approved units, threshold boundaries and sample freshness; reproduce offline.

**Sink incident:** stop publication, verify full-batch validation and downstream atomicity, roll back if necessary.

**Plugin governance:** use code-reviewed registry, read-only service identities, bounded timeouts and pinned artifacts.

## 8. Acceptance

- [ ] All 32 tests pass locally.
- [ ] Abstract contracts are enforced.
- [ ] Three adapters can be swapped without changing `HealthService`.
- [ ] Policy and sink are independently injected.
- [ ] Invalid batches never reach sink.
- [ ] Deterministic JSON, no network access or mutations.

**Execution status:** Unit tests are included; local execution must be performed.
