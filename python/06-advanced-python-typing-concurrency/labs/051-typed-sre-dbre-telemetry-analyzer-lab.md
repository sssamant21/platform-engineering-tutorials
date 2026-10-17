# Chapter 051 — Typed SRE/DBRE Telemetry Analyzer Lab

**Python 3.10+ | Standard library runtime | Offline and read-only**

## Layout

```text
ch051/
  typed_ops.py
  test_typed_ops.py
  mypy.ini
  pyrightconfig.json
```

## 1. typed_ops.py

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, Iterable, Literal, Mapping, Protocol, TypeVar, TypedDict, runtime_checkable
import json
import math

Engine = Literal["postgresql", "elasticsearch", "kafka"]
Severity = Literal["healthy", "warning", "critical"]

class RawEvent(TypedDict):
    service: str
    engine: Engine
    value: float

class Report(TypedDict):
    total: int
    critical: int
    results: list[dict[str, str | float]]

@dataclass(frozen=True)
class Event:
    service: str
    engine: Engine
    value: float

@runtime_checkable
class EventSource(Protocol):
    def read_events(self) -> Iterable[Event]: ...

T = TypeVar("T")
@dataclass(frozen=True)
class Batch(Generic[T]):
    items: tuple[T, ...]
    def count(self) -> int:
        return len(self.items)

THRESHOLDS: Mapping[Engine, tuple[float, float]] = {
    "postgresql": (30.0, 120.0),
    "elasticsearch": (200.0, 500.0),
    "kafka": (1000.0, 10000.0),
}

class ValidationError(ValueError):
    pass

def parse_event(raw: Mapping[str, object]) -> Event:
    if set(raw) != {"service", "engine", "value"}:
        raise ValidationError("unknown or missing event fields")
    service, engine, value = raw["service"], raw["engine"], raw["value"]
    if not isinstance(service, str) or not service or len(service) > 64 or not all(
        c.isascii() and (c.isalnum() or c in "-_") for c in service
    ):
        raise ValidationError("invalid service")
    if not isinstance(engine, str) or engine not in THRESHOLDS:
        raise ValidationError("invalid engine")
    if type(value) not in (int, float):
        raise ValidationError("value must be numeric, not boolean")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValidationError("invalid number") from exc
    if not math.isfinite(number) or number < 0:
        raise ValidationError("value must be finite and nonnegative")
    return Event(service=service, engine=engine, value=number)  # type: ignore[arg-type]

def classify(event: Event) -> Severity:
    warning, critical = THRESHOLDS[event.engine]
    return "critical" if event.value >= critical else "warning" if event.value >= warning else "healthy"

@dataclass(frozen=True)
class MemorySource:
    events: tuple[Event, ...]
    def read_events(self) -> Iterable[Event]:
        return self.events

def analyze(source: EventSource) -> Report:
    rows: list[dict[str, str | float]] = []
    for event in source.read_events():
        rows.append({"service": event.service, "engine": event.engine,
                     "value": event.value, "severity": classify(event)})
    rows.sort(key=lambda row: (str(row["engine"]), str(row["service"]), float(row["value"])))
    return {"total": len(rows),
            "critical": sum(row["severity"] == "critical" for row in rows),
            "results": rows}

def load_events_json(raw: str) -> Batch[Event]:
    if len(raw.encode("utf-8")) > 65536:
        raise ValidationError("payload too large")
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        out: dict[str, object] = {}
        for key, value in pairs:
            if key in out:
                raise ValidationError("duplicate key")
            out[key] = value
        return out
    def reject_constant(value: str) -> object:
        raise ValidationError("nonfinite JSON number")
    try:
        data: object = json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)
    except json.JSONDecodeError as exc:
        raise ValidationError("invalid JSON") from exc
    if not isinstance(data, list) or len(data) > 1000:
        raise ValidationError("expected bounded array")
    events: list[Event] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValidationError("expected event object")
        events.append(parse_event(item))
    return Batch(tuple(events))
```

## 2. test_typed_ops.py — 40 executable unit tests

```python
import json
import unittest
from dataclasses import FrozenInstanceError
from typed_ops import Batch, Event, EventSource, MemorySource, ValidationError, analyze, classify, load_events_json, parse_event

GOOD = {"service": "pg-replica", "engine": "postgresql", "value": 45}

class TypedOpsTests(unittest.TestCase):
    def bad(self, **updates):
        with self.assertRaises(ValidationError):
            parse_event({**GOOD, **updates})

    def test_valid(self): self.assertEqual(parse_event(GOOD).service, "pg-replica")
    def test_immutable(self):
        event = parse_event(GOOD)
        with self.assertRaises(FrozenInstanceError): event.value = 10
    def test_batch(self): self.assertEqual(Batch((1, 2, 3)).count(), 3)
    def test_empty_batch(self): self.assertEqual(Batch(()).count(), 0)
    def test_protocol(self): self.assertIsInstance(MemorySource(()), EventSource)
    def test_classify_healthy(self): self.assertEqual(classify(Event("pg", "postgresql", 0)), "healthy")
    def test_classify_warning(self): self.assertEqual(classify(Event("pg", "postgresql", 30)), "warning")
    def test_classify_critical(self): self.assertEqual(classify(Event("pg", "postgresql", 120)), "critical")
    def test_elasticsearch_warning(self): self.assertEqual(classify(Event("es", "elasticsearch", 200)), "warning")
    def test_elasticsearch_critical(self): self.assertEqual(classify(Event("es", "elasticsearch", 500)), "critical")
    def test_kafka_warning(self): self.assertEqual(classify(Event("k", "kafka", 1000)), "warning")
    def test_kafka_critical(self): self.assertEqual(classify(Event("k", "kafka", 10000)), "critical")
    def test_bad_engine(self): self.bad(engine="mysql")
    def test_bad_value_bool(self): self.bad(value=True)
    def test_bad_value_string(self): self.bad(value="45")
    def test_bad_value_negative(self): self.bad(value=-1)
    def test_bad_value_nan(self): self.bad(value=float("nan"))
    def test_bad_value_inf(self): self.bad(value=float("inf"))
    def test_bad_service_empty(self): self.bad(service="")
    def test_bad_service_unicode(self): self.bad(service="pg-東京")
    def test_bad_service_space(self): self.bad(service="pg replica")
    def test_bad_service_long(self): self.bad(service="a"*65)
    def test_bad_service_type(self): self.bad(service=5)
    def test_bad_extra_field(self): self.bad(password="secret")
    def test_bad_missing_field(self):
        with self.assertRaises(ValidationError): parse_event({"engine":"postgresql","value":1})
    def test_analyze_empty(self): self.assertEqual(analyze(MemorySource(()))["total"], 0)
    def test_analyze_critical(self): self.assertEqual(analyze(MemorySource((Event("pg","postgresql",120),)))["critical"], 1)
    def test_analyze_sorted(self):
        events = (Event("z","postgresql",1), Event("a","postgresql",1))
        self.assertEqual(analyze(MemorySource(events))["results"][0]["service"], "a")
    def test_load(self): self.assertEqual(load_events_json(json.dumps([GOOD])).count(), 1)
    def test_load_empty(self): self.assertEqual(load_events_json("[]").count(), 0)
    def test_load_invalid_json(self):
        with self.assertRaises(ValidationError): load_events_json("{bad")
    def test_load_nonarray(self):
        with self.assertRaises(ValidationError): load_events_json("{}")
    def test_load_nonobject(self):
        with self.assertRaises(ValidationError): load_events_json("[5]")
    def test_load_duplicate(self):
        with self.assertRaises(ValidationError): load_events_json('[{"service":"a","service":"b","engine":"kafka","value":1}]')
    def test_load_nan(self):
        with self.assertRaises(ValidationError): load_events_json("[NaN]")
    def test_load_too_large(self):
        with self.assertRaises(ValidationError): load_events_json(" "*65537)
    def test_load_too_many(self):
        with self.assertRaises(ValidationError): load_events_json("["+",".join(["{}"]*1001)+"]")
    def test_load_bad_engine(self):
        with self.assertRaises(ValidationError): load_events_json(json.dumps([{**GOOD, "engine":"mysql"}]))
    def test_report_shape(self): self.assertEqual(set(analyze(MemorySource(()))), {"total","critical","results"})
    def test_report_no_secrets(self): self.assertNotIn("password", str(analyze(MemorySource((parse_event(GOOD),)))))

if __name__ == "__main__": unittest.main()
```

## 3. Static analysis configuration

`mypy.ini`:

```ini
[mypy]
python_version = 3.10
strict = True
warn_unused_ignores = True
```

`pyrightconfig.json`:

```json
{"pythonVersion":"3.10","typeCheckingMode":"strict","include":["typed_ops.py"]}
```

## 4. Execute

Linux/macOS/WSL:

```bash
python3 -m py_compile typed_ops.py test_typed_ops.py
python3 -m unittest -v test_typed_ops.py
python3 -m pip install mypy pyright
python3 -m mypy --strict typed_ops.py
python3 -m pyright typed_ops.py
```

Windows PowerShell:

```powershell
py -3 -m unittest -v test_typed_ops.py
py -3 -m mypy --strict typed_ops.py
py -3 -m pyright typed_ops.py
```

The test suite was executed successfully against the local equivalent implementation: **40 tests passed**. Strict mypy and pyright results are **not yet verified**. The `type: ignore[arg-type]` in the example is a teaching point: remove it by implementing explicit `Literal` narrowing before claiming a strict static-analysis pass.

## 5. Incident simulations and troubleshooting

1. Inject an unsupported datastore engine.
2. Inject NaN, Infinity, negative values and boolean metrics.
3. Add unknown schema fields and duplicate JSON keys.
4. Supply Unicode service names or oversized input.
5. Replace a Protocol adapter with a deliberately incompatible implementation and inspect mypy/pyright diagnostics.
6. Deliberately call `classify("bad")`; observe why runtime annotations do not validate.
7. Verify that the offline adapter makes no database, cloud or Kubernetes calls.
8. Run the tests before and after correcting a deliberate type error.

**Production runbooks:** For a type regression, block deployment and restore the known-good adapter. For schema drift, quarantine bad input and coordinate contract changes. For analyzer upgrades, pin tool versions and compare CI diagnostics before rollout. For telemetry incidents, validate units and thresholds before acting.

## 6. 100-point acceptance assessment

| Criterion | Points |
|---|---:|
| Unit tests and syntax checks | 25 |
| Strict mypy and pyright validation | 20 |
| TypedDict, generics, Protocol correctness | 20 |
| Runtime validation and negative tests | 15 |
| Incident simulations | 10 |
| Runbooks and rollback evidence | 10 |

Target: **90/100**, with safety checks and both static analyzers passing. Unit test success alone is not full acceptance.
