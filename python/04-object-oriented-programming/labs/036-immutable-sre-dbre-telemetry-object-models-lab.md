# Chapter 036 — Immutable SRE/DBRE Telemetry Object Models Lab

**Python 3.10+ | Standard library | Offline, synthetic and read-only**

## Goal

Build immutable telemetry snapshots, validated threshold policies, computed properties, safe explicit JSON serialization and a bounded mutable buffer. No network connections, credentials or destructive operations.

## Project layout

```text
ch036/
  models.py
  cli.py
  sample.json
  test_models.py
```

## 1. models.py

```python
"""Validated SRE telemetry value objects and bounded state."""
from dataclasses import dataclass, field, FrozenInstanceError, replace
import math


def nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return float(value)


@dataclass(frozen=True, slots=True)
class ThresholdPolicy:
    warning_ms: float = 200.0
    critical_ms: float = 500.0
    warning_error_rate: float = 0.02
    critical_error_rate: float = 0.10

    def __post_init__(self):
        w, c, we, ce = (
            nonnegative(self.warning_ms, "warning_ms"),
            nonnegative(self.critical_ms, "critical_ms"),
            nonnegative(self.warning_error_rate, "warning_error_rate"),
            nonnegative(self.critical_error_rate, "critical_error_rate"),
        )
        if not (0 < w < c and 0 < we < ce <= 1):
            raise ValueError("thresholds must be ordered and positive")


@dataclass(frozen=True, slots=True)
class MetricSnapshot:
    service: str
    latency_ms: float
    errors: int
    requests: int
    labels: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if not isinstance(self.service, str) or not self.service.strip() or len(self.service) > 64:
            raise ValueError("invalid service")
        nonnegative(self.latency_ms, "latency_ms")
        if (isinstance(self.errors, bool) or isinstance(self.requests, bool)
                or not isinstance(self.errors, int) or not isinstance(self.requests, int)
                or self.requests <= 0 or not 0 <= self.errors <= self.requests):
            raise ValueError("invalid error/request counts")
        if not isinstance(self.labels, tuple):
            raise ValueError("labels must be an immutable tuple")
        for pair in self.labels:
            if (not isinstance(pair, tuple) or len(pair) != 2
                    or not all(isinstance(item, str) for item in pair)):
                raise ValueError("labels must contain string pairs")
        if len({key for key, _ in self.labels}) != len(self.labels):
            raise ValueError("duplicate label key")

    @classmethod
    def from_mapping(cls, data):
        if not isinstance(data, dict) or set(data) != {"service", "latency_ms", "errors", "requests", "labels"}:
            raise ValueError("invalid snapshot schema")
        raw_labels = data["labels"]
        if not isinstance(raw_labels, dict):
            raise ValueError("labels must be a mapping")
        labels = tuple(sorted(raw_labels.items()))
        return cls(data["service"], data["latency_ms"], data["errors"], data["requests"], labels)

    @property
    def error_rate(self):
        return self.errors / self.requests


@dataclass(frozen=True, slots=True)
class HealthEvaluation:
    snapshot: MetricSnapshot
    policy: ThresholdPolicy = field(default_factory=ThresholdPolicy, repr=False)

    @property
    def status(self):
        if (self.snapshot.latency_ms >= self.policy.critical_ms
                or self.snapshot.error_rate >= self.policy.critical_error_rate):
            return "critical"
        if (self.snapshot.latency_ms >= self.policy.warning_ms
                or self.snapshot.error_rate >= self.policy.warning_error_rate):
            return "warning"
        return "healthy"

    def to_public_dict(self):
        return {
            "service": self.snapshot.service,
            "latency_ms": float(self.snapshot.latency_ms),
            "error_rate": round(self.snapshot.error_rate, 6),
            "labels": dict(self.snapshot.labels),
            "status": self.status,
        }


@dataclass(slots=True)
class SnapshotBuffer:
    limit: int = 10
    _items: list[MetricSnapshot] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        if isinstance(self.limit, bool) or not isinstance(self.limit, int) or not 1 <= self.limit <= 1000:
            raise ValueError("limit must be in 1..1000")

    @property
    def items(self):
        return tuple(self._items)

    def append(self, snapshot):
        if not isinstance(snapshot, MetricSnapshot):
            raise TypeError("expected MetricSnapshot")
        self._items.append(snapshot)
        if len(self._items) > self.limit:
            del self._items[:-self.limit]


def evaluate_batch(rows):
    if not isinstance(rows, list):
        raise ValueError("expected JSON array")
    seen = set()
    evaluations = []
    for row in rows:
        snapshot = MetricSnapshot.from_mapping(row)
        if snapshot.service in seen:
            raise ValueError("duplicate service")
        seen.add(snapshot.service)
        evaluations.append(HealthEvaluation(snapshot).to_public_dict())
    evaluations.sort(key=lambda row: row["service"])
    return {"schema_version": 1, "service_count": len(evaluations), "services": evaluations}
```

## 2. cli.py

```python
import argparse
import json
from pathlib import Path
from models import evaluate_batch


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
    parser = argparse.ArgumentParser(description="Offline immutable SRE telemetry lab")
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
  {"service":"postgresql","latency_ms":100,"errors":1,"requests":100,"labels":{"engine":"postgresql"}},
  {"service":"elasticsearch","latency_ms":650,"errors":2,"requests":100,"labels":{"engine":"elasticsearch"}},
  {"service":"api","latency_ms":250,"errors":1,"requests":100,"labels":{"tier":"frontend"}}
]
```

## 4. test_models.py — 32 unit tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from models import ThresholdPolicy, MetricSnapshot, HealthEvaluation, SnapshotBuffer, evaluate_batch
from cli import run


class ModelTests(unittest.TestCase):
    def snap(self, **changes):
        data = {"service":"api","latency_ms":100,"errors":1,"requests":100,"labels":{}}
        data.update(changes)
        return MetricSnapshot.from_mapping(data)

    def test_defaults(self): self.assertEqual(ThresholdPolicy().warning_ms,200)
    def test_policy_frozen(self):
        with self.assertRaises(FrozenInstanceError): ThresholdPolicy().warning_ms = 1
    def test_policy_bad_order(self):
        with self.assertRaises(ValueError): ThresholdPolicy(500,200)
    def test_policy_nan(self):
        with self.assertRaises(ValueError): ThresholdPolicy(warning_ms=float("nan"))
    def test_policy_bool(self):
        with self.assertRaises(ValueError): ThresholdPolicy(warning_ms=True)
    def test_snapshot(self): self.assertEqual(self.snap().service,"api")
    def test_snapshot_frozen(self):
        with self.assertRaises(FrozenInstanceError): self.snap().errors = 5
    def test_snapshot_equality(self): self.assertEqual(self.snap(),self.snap())
    def test_snapshot_replace(self): self.assertEqual(replace(self.snap(),latency_ms=200).latency_ms,200)
    def test_error_rate(self): self.assertEqual(self.snap(errors=5).error_rate,0.05)
    def test_negative_latency(self):
        with self.assertRaises(ValueError): self.snap(latency_ms=-1)
    def test_nan_latency(self):
        with self.assertRaises(ValueError): self.snap(latency_ms=float("nan"))
    def test_bool_latency(self):
        with self.assertRaises(ValueError): self.snap(latency_ms=True)
    def test_zero_requests(self):
        with self.assertRaises(ValueError): self.snap(requests=0)
    def test_more_errors_than_requests(self):
        with self.assertRaises(ValueError): self.snap(errors=101)
    def test_boolean_errors(self):
        with self.assertRaises(ValueError): self.snap(errors=True)
    def test_invalid_service(self):
        with self.assertRaises(ValueError): self.snap(service="")
    def test_immutable_labels(self): self.assertIsInstance(self.snap(labels={"env":"dev"}).labels,tuple)
    def test_duplicate_labels(self):
        with self.assertRaises(ValueError): MetricSnapshot("api",1,0,1,(("env","a"),("env","b")))
    def test_unknown_field(self):
        with self.assertRaises(ValueError): self.snap(unexpected=1)
    def test_healthy(self): self.assertEqual(HealthEvaluation(self.snap()).status,"healthy")
    def test_warning_latency(self): self.assertEqual(HealthEvaluation(self.snap(latency_ms=200)).status,"warning")
    def test_critical_latency(self): self.assertEqual(HealthEvaluation(self.snap(latency_ms=500)).status,"critical")
    def test_warning_errors(self): self.assertEqual(HealthEvaluation(self.snap(errors=2)).status,"warning")
    def test_critical_errors(self): self.assertEqual(HealthEvaluation(self.snap(errors=10)).status,"critical")
    def test_public_schema(self): self.assertEqual(HealthEvaluation(self.snap()).to_public_dict()["service"],"api")
    def test_buffer_isolation(self):
        a,b=SnapshotBuffer(),SnapshotBuffer()
        a.append(self.snap())
        self.assertEqual(len(b.items),0)
    def test_buffer_bounded(self):
        b=SnapshotBuffer(limit=2)
        for n in (10,20,30): b.append(self.snap(latency_ms=n))
        self.assertEqual([x.latency_ms for x in b.items],[20,30])
    def test_buffer_type(self):
        with self.assertRaises(TypeError): SnapshotBuffer().append({})
    def test_duplicate_services(self):
        row={"service":"api","latency_ms":1,"errors":0,"requests":1,"labels":{}}
        with self.assertRaises(ValueError): evaluate_batch([row,row])
    def test_cli_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"fixture.json"
            path.write_text(json.dumps([{"service":"api","latency_ms":1,"errors":0,"requests":1,"labels":{}}]),encoding="utf-8")
            self.assertEqual(run(path)["service_count"],1)
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
./.venv/bin/python -m unittest -v test_models.py
./.venv/bin/python cli.py --input sample.json
./.venv/bin/python -m py_compile models.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m unittest -v test_models.py
.\.venv\Scripts\python.exe cli.py --input sample.json
.\.venv\Scripts\python.exe -m py_compile models.py cli.py
```

Expected synthetic statuses: PostgreSQL healthy, Elasticsearch critical, API warning.

## 6. Failure injection and troubleshooting

1. Try assigning to a frozen snapshot: `FrozenInstanceError`.
2. Supply NaN, infinity, boolean or negative latency: reject input.
3. Set `requests=0` or `errors>requests`: reject invalid counts.
4. Provide duplicate label keys through direct construction: reject.
5. Add unknown JSON field: reject schema.
6. Append three snapshots to a buffer with `limit=2`: retain only two.
7. Duplicate a service in the input: reject batch.
8. Attempt to log raw objects containing sensitive fields: use allowlisted public serializer instead.

## 7. Production runbooks

**Unexpected mutation:** trace shared references, normalize nested collections to tuples, add frozen-object regression tests.

**Schema drift:** preserve sanitized fixture, compare fields and version, fail closed until schema is reviewed.

**Incorrect status:** verify unit, error-rate denominator and inclusive thresholds; reproduce with boundary tests.

**Capacity:** bound in-memory buffers and use approved retention policies; do not use unbounded telemetry histories.

## 8. Acceptance

- [ ] All 32 unit tests pass locally.
- [ ] Frozen dataclasses reject ordinary attribute mutation.
- [ ] Nested labels are normalized to immutable tuples.
- [ ] Derived status and error-rate properties behave correctly.
- [ ] Bounded buffer does not share mutable state.
- [ ] Output is deterministic, sanitized and schema-stable.
- [ ] No network access, secrets or infrastructure mutations.

**Execution status:** Tests are included in this published lab; local execution remains pending.
