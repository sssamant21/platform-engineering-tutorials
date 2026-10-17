# Chapter 034 — Protocol-Based SRE/DBRE Adapter Lab

**Python 3.10+ | Standard library only | Offline and read-only**

## Goal

Create three structurally compatible metric readers, inject them into a policy-driven reporter, select adapters via a reviewed allowlist, and validate stable JSON output. No database connections, credentials or mutations.

## Files

```text
ch034/
  adapters.py
  cli.py
  sample.json
  test_adapters.py
```

## 1. adapters.py

```python
"""Structural typing and dependency injection for synthetic SRE metrics."""
from dataclasses import dataclass
import math
from typing import Protocol, runtime_checkable


def finite_nonnegative(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return float(value)


@runtime_checkable
class MetricReader(Protocol):
    def read_metric(self) -> float:
        ...


@dataclass(frozen=True)
class ThresholdPolicy:
    warning: float
    critical: float

    def __post_init__(self):
        w = finite_nonnegative(self.warning, "warning")
        c = finite_nonnegative(self.critical, "critical")
        if not 0 < w < c:
            raise ValueError("thresholds must satisfy 0 < warning < critical")

    def classify(self, value):
        value = finite_nonnegative(value, "metric")
        if value >= self.critical:
            return "critical"
        if value >= self.warning:
            return "warning"
        return "healthy"


class PostgreSQLLagReader:
    kind = "postgresql"
    unit = "seconds"

    def __init__(self, sample):
        self._sample = finite_nonnegative(sample, "sample")

    def read_metric(self) -> float:
        return self._sample


class ElasticsearchLatencyReader:
    kind = "elasticsearch"
    unit = "milliseconds"

    def __init__(self, sample):
        self._sample = finite_nonnegative(sample, "sample")

    def read_metric(self) -> float:
        return self._sample


class KafkaLagReader:
    kind = "kafka"
    unit = "messages"

    def __init__(self, sample):
        self._sample = finite_nonnegative(sample, "sample")

    def read_metric(self) -> float:
        return self._sample


READER_TYPES = {
    "postgresql": (PostgreSQLLagReader, ThresholdPolicy(30, 120)),
    "elasticsearch": (ElasticsearchLatencyReader, ThresholdPolicy(200, 500)),
    "kafka": (KafkaLagReader, ThresholdPolicy(1000, 10000)),
}


def make_reader(kind, sample):
    if not isinstance(kind, str) or kind not in READER_TYPES:
        raise ValueError("unknown reader kind")
    cls, policy = READER_TYPES[kind]
    return cls(sample), policy


class HealthReporter:
    def __init__(self, service: str, reader: MetricReader, policy: ThresholdPolicy):
        if not isinstance(service, str) or not service.strip() or len(service) > 64:
            raise ValueError("invalid service")
        if not callable(getattr(reader, "read_metric", None)):
            raise TypeError("reader must provide read_metric")
        if not isinstance(policy, ThresholdPolicy):
            raise TypeError("invalid policy")
        kind = getattr(reader, "kind", None)
        unit = getattr(reader, "unit", None)
        if not isinstance(kind, str) or not kind or not isinstance(unit, str) or not unit:
            raise ValueError("reader must declare kind and unit")
        self._service = service
        self._reader = reader
        self._policy = policy
        self._kind = kind
        self._unit = unit

    def report(self):
        value = finite_nonnegative(self._reader.read_metric(), "metric")
        return {
            "service": self._service,
            "kind": self._kind,
            "unit": self._unit,
            "value": value,
            "status": self._policy.classify(value),
        }


def build_report(rows):
    if not isinstance(rows, list):
        raise ValueError("expected JSON array")
    seen = set()
    results = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"kind", "service", "sample"}:
            raise ValueError("invalid record schema")
        identity = (row["kind"], row["service"])
        if identity in seen:
            raise ValueError("duplicate service and kind")
        reader, policy = make_reader(row["kind"], row["sample"])
        results.append(HealthReporter(row["service"], reader, policy).report())
        seen.add(identity)
    results.sort(key=lambda item: (item["kind"], item["service"]))
    return {"schema_version": 1, "check_count": len(results), "checks": results}
```

## 2. cli.py

```python
"""Offline JSON fixture adapter."""
import argparse
import json
from pathlib import Path
from adapters import build_report


def run(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
        rows = json.loads(
            raw,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("input file unreadable or invalid") from exc
    return build_report(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline SRE protocol lab")
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
  {"kind":"postgresql","service":"pg-replica","sample":45},
  {"kind":"elasticsearch","service":"search-api","sample":650},
  {"kind":"kafka","service":"consumer-a","sample":100}
]
```

## 4. test_adapters.py — 32 tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from adapters import (
    MetricReader, ThresholdPolicy, PostgreSQLLagReader,
    ElasticsearchLatencyReader, KafkaLagReader,
    HealthReporter, make_reader, build_report,
)
from cli import run


class AdapterTests(unittest.TestCase):
    def test_pg_protocol(self): self.assertIsInstance(PostgreSQLLagReader(1), MetricReader)
    def test_es_protocol(self): self.assertIsInstance(ElasticsearchLatencyReader(1), MetricReader)
    def test_kafka_protocol(self): self.assertIsInstance(KafkaLagReader(1), MetricReader)
    def test_pg_read(self): self.assertEqual(PostgreSQLLagReader(10).read_metric(), 10)
    def test_es_read(self): self.assertEqual(ElasticsearchLatencyReader(20).read_metric(), 20)
    def test_kafka_read(self): self.assertEqual(KafkaLagReader(30).read_metric(), 30)
    def test_pg_healthy(self):
        r,p = make_reader("postgresql", 1)
        self.assertEqual(HealthReporter("pg",r,p).report()["status"],"healthy")
    def test_pg_warning(self):
        r,p = make_reader("postgresql", 30)
        self.assertEqual(HealthReporter("pg",r,p).report()["status"],"warning")
    def test_pg_critical(self):
        r,p = make_reader("postgresql", 120)
        self.assertEqual(HealthReporter("pg",r,p).report()["status"],"critical")
    def test_es_warning(self):
        r,p = make_reader("elasticsearch", 200)
        self.assertEqual(HealthReporter("es",r,p).report()["status"],"warning")
    def test_es_critical(self):
        r,p = make_reader("elasticsearch", 500)
        self.assertEqual(HealthReporter("es",r,p).report()["status"],"critical")
    def test_kafka_warning(self):
        r,p = make_reader("kafka", 1000)
        self.assertEqual(HealthReporter("k",r,p).report()["status"],"warning")
    def test_kafka_critical(self):
        r,p = make_reader("kafka", 10000)
        self.assertEqual(HealthReporter("k",r,p).report()["status"],"critical")
    def test_bad_policy_order(self):
        with self.assertRaises(ValueError): ThresholdPolicy(20,10)
    def test_nan_policy(self):
        with self.assertRaises(ValueError): ThresholdPolicy(float("nan"),10)
    def test_bool_policy(self):
        with self.assertRaises(ValueError): ThresholdPolicy(True,10)
    def test_negative_sample(self):
        with self.assertRaises(ValueError): PostgreSQLLagReader(-1)
    def test_nan_sample(self):
        with self.assertRaises(ValueError): PostgreSQLLagReader(float("nan"))
    def test_infinite_sample(self):
        with self.assertRaises(ValueError): KafkaLagReader(float("inf"))
    def test_bool_sample(self):
        with self.assertRaises(ValueError): ElasticsearchLatencyReader(True)
    def test_unknown_kind(self):
        with self.assertRaises(ValueError): make_reader("unknown",1)
    def test_invalid_service(self):
        with self.assertRaises(ValueError): HealthReporter("",PostgreSQLLagReader(1),ThresholdPolicy(30,120))
    def test_fake_reader(self):
        class Fake:
            kind = "fake"
            unit = "milliseconds"
            def read_metric(self): return 250.0
        self.assertEqual(HealthReporter("fake",Fake(),ThresholdPolicy(200,500)).report()["status"],"warning")
    def test_missing_method(self):
        class Bad:
            kind = "fake"
            unit = "ms"
        with self.assertRaises(TypeError): HealthReporter("x",Bad(),ThresholdPolicy(1,2))
    def test_invalid_return(self):
        class Bad:
            kind = "fake"
            unit = "ms"
            def read_metric(self): return "oops"
        with self.assertRaises(ValueError): HealthReporter("x",Bad(),ThresholdPolicy(1,2)).report()
    def test_missing_unit(self):
        class Bad:
            kind = "fake"
            def read_metric(self): return 1
        with self.assertRaises(ValueError): HealthReporter("x",Bad(),ThresholdPolicy(1,2))
    def test_report_sorted(self):
        rows=[{"kind":"kafka","service":"z","sample":1},{"kind":"elasticsearch","service":"a","sample":1}]
        self.assertEqual(build_report(rows)["checks"][0]["kind"],"elasticsearch")
    def test_report_duplicate(self):
        row={"kind":"postgresql","service":"pg","sample":1}
        with self.assertRaises(ValueError): build_report([row,row])
    def test_report_schema(self):
        with self.assertRaises(ValueError): build_report([{"kind":"postgresql"}])
    def test_report_empty(self): self.assertEqual(build_report([])["check_count"],0)
    def test_cli_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"fixture.json"
            path.write_text(json.dumps([{"kind":"postgresql","service":"pg","sample":45}]),encoding="utf-8")
            self.assertEqual(run(path)["checks"][0]["status"],"warning")
    def test_cli_bad_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"bad.json"
            path.write_text("{bad",encoding="utf-8")
            with self.assertRaises(ValueError): run(path)


if __name__ == "__main__":
    unittest.main()
```

## 5. Run

Linux/macOS/WSL:

```bash
python3 -m venv .venv
./.venv/bin/python -m unittest -v test_adapters.py
./.venv/bin/python cli.py --input sample.json
./.venv/bin/python -m py_compile adapters.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m unittest -v test_adapters.py
.\.venv\Scripts\python.exe cli.py --input sample.json
.\.venv\Scripts\python.exe -m py_compile adapters.py cli.py
```

Expected synthetic classifications: PostgreSQL warning, Elasticsearch critical, Kafka healthy. The lab includes **32 unit tests**; local execution remains pending.

## 6. Failure injection and troubleshooting

1. Remove `read_metric` from a fake: reporter rejects the missing callable.
2. Return a string from `read_metric`: reporter rejects the value.
3. Return NaN or infinity: finite validation fails.
4. Change the unit metadata: review and reject incorrect adapter/policy mapping.
5. Use unknown adapter kind: allowlist blocks it.
6. Duplicate a `(kind, service)` record: fail closed.
7. Add unexpected input field: reject schema.

| Symptom | Likely cause | Resolution |
|---|---|---|
| Protocol check succeeds but reader fails | Runtime structural check is shallow | Validate results and contract-test |
| Unexpected live API calls | Hidden concrete dependency | Inject offline fake |
| Wrong severity | Unit or threshold mismatch | Review policy and sample units |
| `AttributeError` | Missing reader method | Fix adapter contract |
| Unknown kind | Unreviewed adapter selection | Add only through code review |

## 7. Production runbooks

**Adapter regression:** stop report emission, preserve sanitized fixture and package version, compare with contract tests, revert incompatible adapter.

**Classification incident:** confirm metric unit, sample freshness, threshold policy and expected inclusive boundaries; correlate with authoritative metrics.

**Release:** run unit tests and static checks, verify dependency provenance, approve read-only identity, pin artifact and retain rollback.

## 8. Acceptance

- [ ] All 32 tests pass locally.
- [ ] Independent reader implementations satisfy the same protocol.
- [ ] Reporter works with injected fake without inheritance.
- [ ] Unknown adapters and malformed metrics fail closed.
- [ ] JSON schema is deterministic and sanitized.
- [ ] No credentials, network access or mutations.
