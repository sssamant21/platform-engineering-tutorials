# Chapter 040 — Integrated Object-Oriented SRE/DBRE Production Capstone Lab

**Python 3.10+ | Standard library | Synthetic, offline, read-only**

## Deliverables

Create `capstone.py`, `cli.py`, `sample.jsonl`, and `test_capstone.py` in one local directory. The program performs no network calls and never mutates infrastructure.

## 1. capstone.py

```python
"""Synthetic, read-only SRE/DBRE production-style capstone."""
from abc import ABC, abstractmethod
from collections import Counter
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import json
import math
from typing import Protocol

MAX_LINE = 4096
MAX_PREVIEW = 10


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("metric must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError("metric must be finite and nonnegative")
    return float(value)


@dataclass(frozen=True, slots=True)
class Thresholds:
    warning: float
    critical: float

    def __post_init__(self):
        if not 0 < finite(self.warning) < finite(self.critical):
            raise ValueError("thresholds must satisfy 0 < warning < critical")

    def classify(self, value):
        value = finite(value)
        return ("critical" if value >= self.critical
                else "warning" if value >= self.warning else "healthy")


@dataclass(frozen=True, slots=True)
class Observation:
    service: str
    kind: str
    unit: str
    value: float

    def __post_init__(self):
        if not isinstance(self.service, str) or not self.service.strip() or len(self.service) > 64:
            raise ValueError("invalid service")
        if not isinstance(self.kind, str) or not isinstance(self.unit, str):
            raise ValueError("invalid kind or unit")
        object.__setattr__(self, "value", finite(self.value))


class BaseAdapter(ABC):
    @property
    @abstractmethod
    def kind(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def unit(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def thresholds(self):
        raise NotImplementedError

    def __init__(self):
        if not self.kind or not self.unit or not isinstance(self.thresholds, Thresholds):
            raise ValueError("invalid adapter configuration")

    def evaluate(self, observation):
        if not isinstance(observation, Observation):
            raise TypeError("expected Observation")
        if observation.kind != self.kind or observation.unit != self.unit:
            raise ValueError("adapter kind/unit mismatch")
        return self.thresholds.classify(observation.value)


class PostgreSQLAdapter(BaseAdapter):
    kind = "postgresql_lag"
    unit = "seconds"
    thresholds = Thresholds(30, 120)

    def __init__(self):
        super().__init__()


class ElasticsearchAdapter(BaseAdapter):
    kind = "elasticsearch_latency"
    unit = "milliseconds"
    thresholds = Thresholds(200, 500)

    def __init__(self):
        super().__init__()


class KafkaAdapter(BaseAdapter):
    kind = "kafka_lag"
    unit = "messages"
    thresholds = Thresholds(1000, 10000)

    def __init__(self):
        super().__init__()


ADAPTERS = {
    cls.kind: cls() for cls in (PostgreSQLAdapter, ElasticsearchAdapter, KafkaAdapter)
}


class ReportSink(Protocol):
    def publish(self, report: dict) -> None:
        ...


class MemorySink:
    def __init__(self):
        self.reports = []

    def publish(self, report):
        if not isinstance(report, dict) or report.get("schema_version") != 1:
            raise ValueError("invalid report")
        self.reports.append(report)


class IncidentPreview:
    """Immutable, bounded incident collection with sequence protocols."""
    def __init__(self, items=()):
        values = tuple(items)
        if len(values) > MAX_PREVIEW:
            raise ValueError("preview too large")
        self._items = values

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, index):
        return self._items[index]

    def __repr__(self):
        return f"IncidentPreview(count={len(self)})"


class RunScope:
    active = 0

    def __init__(self, events):
        self.events = events
        self.state = "new"

    def __enter__(self):
        if self.state != "new":
            raise RuntimeError("scope cannot reopen")
        self.state = "open"
        type(self).active += 1
        self.events.append("scope_open")
        return self

    def close(self):
        if self.state == "open":
            type(self).active -= 1
            self.events.append("scope_close")
        self.state = "closed"

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


@contextmanager
def audit_scope(events):
    events.append("audit_start")
    try:
        yield
    except Exception:
        events.append("audit_failure")
        raise
    else:
        events.append("audit_success")
    finally:
        events.append("audit_end")


def parse_jsonl(lines):
    """Single-pass validated generator; no full-file materialization."""
    for line_number, line in enumerate(lines, 1):
        if not isinstance(line, str) or len(line) > MAX_LINE:
            raise ValueError(f"line {line_number}: invalid or oversized")
        if not line.strip():
            continue
        try:
            row = json.loads(
                line,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")),
            )
        except (ValueError, TypeError) as exc:
            raise ValueError(f"line {line_number}: malformed JSON") from exc
        if not isinstance(row, dict) or set(row) != {"service", "kind", "unit", "value"}:
            raise ValueError(f"line {line_number}: invalid schema")
        observation = Observation(**row)
        adapter = ADAPTERS.get(observation.kind)
        if adapter is None:
            raise ValueError(f"line {line_number}: unknown kind")
        if observation.unit != adapter.unit:
            raise ValueError(f"line {line_number}: wrong unit")
        yield observation


class HealthEngine:
    def __init__(self, adapters=None, sink=None, preview_limit=5):
        self.adapters = dict(ADAPTERS if adapters is None else adapters)
        if not self.adapters or any(
            not isinstance(name, str) or not isinstance(adapter, BaseAdapter) or adapter.kind != name
            for name, adapter in self.adapters.items()
        ):
            raise ValueError("invalid adapter registry")
        self.sink = sink if sink is not None else MemorySink()
        if not callable(getattr(self.sink, "publish", None)):
            raise TypeError("sink must implement publish")
        if isinstance(preview_limit, bool) or not isinstance(preview_limit, int) or not 0 <= preview_limit <= MAX_PREVIEW:
            raise ValueError("preview limit must be in 0..10")
        self.preview_limit = preview_limit

    def run(self, observations, events=None):
        events = [] if events is None else events
        counts = Counter()
        incidents = []
        total = 0
        with ExitStack() as stack:
            stack.enter_context(audit_scope(events))
            stack.enter_context(RunScope(events))
            for obs in observations:
                if not isinstance(obs, Observation):
                    raise TypeError("expected Observation")
                adapter = self.adapters.get(obs.kind)
                if adapter is None:
                    raise ValueError("unknown kind")
                status = adapter.evaluate(obs)
                if status not in ("healthy", "warning", "critical"):
                    raise ValueError("invalid adapter status")
                total += 1
                counts[status] += 1
                if status != "healthy" and len(incidents) < self.preview_limit:
                    incidents.append({
                        "service": obs.service,
                        "kind": obs.kind,
                        "status": status,
                        "value": obs.value,
                        "unit": obs.unit,
                    })
            preview = IncidentPreview(incidents)
            result = {
                "schema_version": 1,
                "total": total,
                "counts": {name: counts[name] for name in ("healthy", "warning", "critical")},
                "preview": list(preview),
            }
            self.sink.publish(result)
        return result
```

## 2. cli.py

```python
import argparse
import json
from pathlib import Path
from capstone import HealthEngine, parse_jsonl


def run(path, preview=5):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return HealthEngine(preview_limit=preview).run(parse_jsonl(handle))
    except (OSError, UnicodeError) as exc:
        raise ValueError("input file unreadable") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline OOP SRE/DBRE capstone")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--preview", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        result = run(args.input, args.preview)
    except (TypeError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 3. sample.jsonl

```json
{"service":"pg-replica","kind":"postgresql_lag","unit":"seconds","value":5}
{"service":"pg-replica","kind":"postgresql_lag","unit":"seconds","value":45}
{"service":"search-api","kind":"elasticsearch_latency","unit":"milliseconds","value":650}
{"service":"consumer-a","kind":"kafka_lag","unit":"messages","value":100}
{"service":"consumer-a","kind":"kafka_lag","unit":"messages","value":10000}
```

## 4. test_capstone.py — 40 automated tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from capstone import (
    Thresholds, Observation, BaseAdapter, PostgreSQLAdapter,
    ElasticsearchAdapter, KafkaAdapter, MemorySink, IncidentPreview,
    RunScope, audit_scope, parse_jsonl, HealthEngine, MAX_LINE,
)
from cli import run


def row(kind="postgresql_lag", unit="seconds", value=1, service="pg"):
    return json.dumps({"service":service,"kind":kind,"unit":unit,"value":value}) + "\n"


class CapstoneTests(unittest.TestCase):
    def obs(self, value=1):
        return Observation("pg","postgresql_lag","seconds",value)

    def test_thresholds(self): self.assertEqual(Thresholds(1,2).classify(0),"healthy")
    def test_warning_boundary(self): self.assertEqual(Thresholds(1,2).classify(1),"warning")
    def test_critical_boundary(self): self.assertEqual(Thresholds(1,2).classify(2),"critical")
    def test_bad_thresholds(self):
        with self.assertRaises(ValueError): Thresholds(3,2)
    def test_bool_thresholds(self):
        with self.assertRaises(ValueError): Thresholds(True,2)
    def test_observation(self): self.assertEqual(self.obs().value,1.0)
    def test_frozen(self):
        with self.assertRaises(FrozenInstanceError): self.obs().value=2
    def test_bad_service(self):
        with self.assertRaises(ValueError): Observation("","postgresql_lag","seconds",1)
    def test_negative(self):
        with self.assertRaises(ValueError): self.obs(-1)
    def test_nan(self):
        with self.assertRaises(ValueError): self.obs(float("nan"))
    def test_infinite(self):
        with self.assertRaises(ValueError): self.obs(float("inf"))
    def test_boolean(self):
        with self.assertRaises(ValueError): self.obs(True)
    def test_abc(self):
        with self.assertRaises(TypeError): BaseAdapter()
    def test_pg_adapter(self): self.assertEqual(PostgreSQLAdapter().evaluate(self.obs(30)),"warning")
    def test_es_adapter(self):
        obs=Observation("es","elasticsearch_latency","milliseconds",500)
        self.assertEqual(ElasticsearchAdapter().evaluate(obs),"critical")
    def test_kafka_adapter(self):
        obs=Observation("k","kafka_lag","messages",100)
        self.assertEqual(KafkaAdapter().evaluate(obs),"healthy")
    def test_wrong_adapter(self):
        with self.assertRaises(ValueError): KafkaAdapter().evaluate(self.obs())
    def test_parse(self): self.assertEqual(len(list(parse_jsonl([row()]))),1)
    def test_blank_line(self): self.assertEqual(len(list(parse_jsonl(["\n",row()]))),1)
    def test_parse_lazy(self): self.assertEqual(next(parse_jsonl([row()])).service,"pg")
    def test_bad_json(self):
        with self.assertRaises(ValueError): list(parse_jsonl(["{bad"]))
    def test_bad_schema(self):
        with self.assertRaises(ValueError): list(parse_jsonl(['{"service":"pg"}']))
    def test_bad_kind(self):
        with self.assertRaises(ValueError): list(parse_jsonl([row(kind="unknown")]))
    def test_bad_unit(self):
        with self.assertRaises(ValueError): list(parse_jsonl([row(unit="ms")]))
    def test_oversized(self):
        with self.assertRaises(ValueError): list(parse_jsonl(["x"*(MAX_LINE+1)]))
    def test_preview_len(self): self.assertEqual(len(IncidentPreview([1,2])),2)
    def test_preview_iter(self): self.assertEqual(list(IncidentPreview([1,2])),[1,2])
    def test_preview_index(self): self.assertEqual(IncidentPreview([1,2])[0],1)
    def test_preview_repr(self): self.assertIn("count=2",repr(IncidentPreview([1,2])))
    def test_preview_cap(self):
        with self.assertRaises(ValueError): IncidentPreview(range(11))
    def test_sink(self):
        sink=MemorySink()
        HealthEngine(sink=sink).run([self.obs()])
        self.assertEqual(len(sink.reports),1)
    def test_no_partial_publish(self):
        sink=MemorySink()
        with self.assertRaises(ValueError):
            HealthEngine(sink=sink).run(parse_jsonl([row(),"{bad"]))
        self.assertEqual(len(sink.reports),0)
    def test_counts(self):
        result=HealthEngine().run([self.obs(1),self.obs(30),self.obs(120)])
        self.assertEqual(result["counts"],{"healthy":1,"warning":1,"critical":1})
    def test_preview_bound(self):
        result=HealthEngine(preview_limit=2).run([self.obs(120)]*20)
        self.assertEqual(len(result["preview"]),2)
    def test_bad_preview(self):
        with self.assertRaises(ValueError): HealthEngine(preview_limit=11)
    def test_scope_cleanup(self):
        events=[]
        with RunScope(events): pass
        self.assertEqual(events,["scope_open","scope_close"])
    def test_scope_exception(self):
        events=[]
        with self.assertRaises(RuntimeError):
            with RunScope(events): raise RuntimeError("injected")
        self.assertEqual(events[-1],"scope_close")
    def test_audit_failure(self):
        events=[]
        with self.assertRaises(RuntimeError):
            with audit_scope(events): raise RuntimeError("injected")
        self.assertIn("audit_failure",events)
    def test_engine_failure_cleanup(self):
        events=[]
        with self.assertRaises(ValueError):
            HealthEngine().run(parse_jsonl([row(),"{bad"]),events)
        self.assertEqual(events[-2:],["scope_close","audit_end"])
    def test_cli_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"sample.jsonl"
            path.write_text(row(value=30),encoding="utf-8")
            self.assertEqual(run(path)["counts"]["warning"],1)
    def test_cli_bad_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"bad.jsonl"
            path.write_text("{bad",encoding="utf-8")
            with self.assertRaises(ValueError): run(path)


if __name__ == "__main__":
    unittest.main()
```

## 5. Execute

Linux/macOS/WSL:

```bash
python3 -m venv .venv
./.venv/bin/python -m unittest -v test_capstone.py
./.venv/bin/python cli.py --input sample.jsonl
./.venv/bin/python -m py_compile capstone.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m unittest -v test_capstone.py
.\.venv\Scripts\python.exe cli.py --input sample.jsonl
.\.venv\Scripts\python.exe -m py_compile capstone.py cli.py
```

Expected sample: `total=5`, `healthy=2`, `warning=1`, `critical=2`. The report contains only approved fields and a bounded incident preview.

## 6. Incident game days

1. **PostgreSQL lag spike:** change a synthetic lag value to 120 seconds; verify critical classification.
2. **Elasticsearch latency:** set latency to 500 milliseconds; verify critical boundary.
3. **Kafka backlog:** set lag to 1,000 messages; verify warning boundary.
4. **Schema drift:** insert unknown JSON key halfway through; verify no sink publication.
5. **Invalid telemetry:** inject NaN, infinity, negative and boolean values; verify failure.
6. **Adapter failure:** create a subclass overriding `evaluate` to raise; inject it and verify audit failure and scope cleanup.
7. **Sink failure:** inject a sink whose `publish` raises; verify error propagation.
8. **Capacity:** generate 100,000 synthetic lines and verify preview remains capped at 5.

## 7. Troubleshooting and production runbooks

**Classification error:** verify kind, unit, thresholds and boundary tests. Never silently convert units.

**Resource leak:** inspect `RunScope.active` before and after injected failure, check `ExitStack` cleanup.

**Partial report:** preserve sanitized line number and fixture, fail closed, fix schema and replay.

**Sink failure:** mark run unsuccessful, retry only under an explicit idempotency policy, preserve audit evidence.

**Production rollout:** require service-owner approval, least-privilege access, explicit timeouts, telemetry freshness checks, deployment rollback and observability before replacing synthetic adapters.

## 8. Acceptance checklist

- [ ] All published automated tests pass locally.
- [ ] Immutable domain objects and ABC contracts are enforced.
- [ ] Protocol-compatible sink is injected.
- [ ] Lazy JSONL parsing and bounded preview work at scale.
- [ ] Context managers release resources after failure.
- [ ] No partial report is published on invalid input.
- [ ] CLI emits deterministic JSON and no sensitive fields.
- [ ] Four or more incident game days documented.
- [ ] Assessment score at least 85/100 with all safety gates met.

**Execution status:** Tests and acceptance steps are published; local execution is required before claiming they pass.
