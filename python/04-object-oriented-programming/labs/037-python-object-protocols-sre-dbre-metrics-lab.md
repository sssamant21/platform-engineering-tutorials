# Chapter 037 — Python Object Protocols for SRE/DBRE Metrics Lab

**Python 3.10+ | Standard library | Synthetic, offline and read-only**

## Goal

Implement immutable unit-aware metric values, a sequence-like metric series, safe equality/ordering/hash, controlled series addition and a context-managed synthetic session.

## Project files

```text
ch037/
  protocols.py
  cli.py
  sample.json
  test_protocols.py
```

## 1. protocols.py

```python
"""Safe Python data-model protocols for synthetic SRE/DBRE telemetry."""
from dataclasses import dataclass
from functools import total_ordering
import math


def valid_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("metric must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError("metric must be finite and nonnegative")
    return float(value)


UNITS = {
    "postgresql_lag": "seconds",
    "elasticsearch_latency": "milliseconds",
    "kafka_lag": "messages",
}


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class MetricValue:
    kind: str
    unit: str
    value: float

    def __post_init__(self):
        if self.kind not in UNITS or self.unit != UNITS[self.kind]:
            raise ValueError("invalid kind or unit")
        object.__setattr__(self, "value", valid_number(self.value))

    def __eq__(self, other):
        if not isinstance(other, MetricValue):
            return NotImplemented
        return (self.kind, self.unit, self.value) == (other.kind, other.unit, other.value)

    def __lt__(self, other):
        if not isinstance(other, MetricValue):
            return NotImplemented
        if (self.kind, self.unit) != (other.kind, other.unit):
            raise ValueError("cannot compare different metric units")
        return self.value < other.value

    def __hash__(self):
        return hash((self.kind, self.unit, self.value))

    def __repr__(self):
        return f"MetricValue(kind={self.kind!r}, unit={self.unit!r}, value={self.value!r})"


class MetricSeries:
    MAX_SAMPLES = 1000

    def __init__(self, service, kind, samples):
        if not isinstance(service, str) or not service.strip() or len(service) > 64:
            raise ValueError("invalid service")
        if kind not in UNITS:
            raise ValueError("unknown metric kind")
        if not isinstance(samples, (list, tuple)):
            raise TypeError("samples must be a list or tuple")
        if len(samples) > self.MAX_SAMPLES:
            raise ValueError("too many samples")
        self._service = service
        self._kind = kind
        self._samples = tuple(MetricValue(kind, UNITS[kind], v) for v in samples)

    @property
    def identity(self):
        return (self._service, self._kind)

    @property
    def unit(self):
        return UNITS[self._kind]

    def __len__(self):
        return len(self._samples)

    def __iter__(self):
        return iter(self._samples)

    def __getitem__(self, index):
        return self._samples[index]

    def __add__(self, other):
        if not isinstance(other, MetricSeries):
            return NotImplemented
        if self.identity != other.identity:
            raise ValueError("cannot combine different series")
        if len(self) + len(other) > self.MAX_SAMPLES:
            raise ValueError("combined series too large")
        return MetricSeries(self._service, self._kind, [v.value for v in self] + [v.value for v in other])

    def __repr__(self):
        return f"MetricSeries(service={self._service!r}, kind={self._kind!r}, count={len(self)})"

    def to_public_dict(self):
        return {
            "service": self._service,
            "kind": self._kind,
            "unit": self.unit,
            "count": len(self),
            "max_value": max((v.value for v in self), default=None),
        }


class SessionClosed(RuntimeError):
    pass


class SyntheticSession:
    """Single-use context manager. No external resources are acquired."""

    active = 0

    def __init__(self, series):
        if not isinstance(series, MetricSeries):
            raise TypeError("expected MetricSeries")
        self._series = series
        self._state = "new"

    @property
    def state(self):
        return self._state

    def __enter__(self):
        if self._state != "new":
            raise SessionClosed("session cannot be reopened")
        self._state = "open"
        type(self).active += 1
        return self

    def __iter__(self):
        if self._state != "open":
            raise SessionClosed("session not open")
        return iter(self._series)

    def close(self):
        if self._state == "open":
            type(self).active -= 1
        self._state = "closed"

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False


def report(rows):
    if not isinstance(rows, list):
        raise ValueError("expected JSON array")
    seen = set()
    output = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"service", "kind", "samples"}:
            raise ValueError("invalid record schema")
        series = MetricSeries(row["service"], row["kind"], row["samples"])
        if series.identity in seen:
            raise ValueError("duplicate metric series")
        seen.add(series.identity)
        with SyntheticSession(series) as session:
            values = [item.value for item in session]
        result = series.to_public_dict()
        result["max_value"] = max(values, default=None)
        output.append(result)
    output.sort(key=lambda item: (item["kind"], item["service"]))
    return {"schema_version": 1, "series_count": len(output), "series": output}
```

## 2. cli.py

```python
import argparse
import json
from pathlib import Path
from protocols import report


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
    parser = argparse.ArgumentParser(description="Offline Python object-protocol lab")
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
  {"service":"pg-replica","kind":"postgresql_lag","samples":[5,45,125]},
  {"service":"search-api","kind":"elasticsearch_latency","samples":[120,250,650]},
  {"service":"consumer-a","kind":"kafka_lag","samples":[100,1000,10000]}
]
```

## 4. test_protocols.py — 32 unit tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from protocols import MetricValue, MetricSeries, SyntheticSession, SessionClosed, report
from cli import run


class ProtocolTests(unittest.TestCase):
    def value(self, n=1):
        return MetricValue("postgresql_lag","seconds",n)

    def series(self, samples=(1,2)):
        return MetricSeries("pg","postgresql_lag",samples)

    def test_value(self): self.assertEqual(self.value().value,1)
    def test_frozen(self):
        with self.assertRaises(FrozenInstanceError): self.value().value = 5
    def test_equal(self): self.assertEqual(self.value(2),self.value(2))
    def test_not_equal(self): self.assertNotEqual(self.value(1),self.value(2))
    def test_hash(self): self.assertEqual(hash(self.value(2)),hash(self.value(2)))
    def test_set_dedup(self): self.assertEqual(len({self.value(1),self.value(1)}),1)
    def test_less_than(self): self.assertLess(self.value(1),self.value(2))
    def test_greater_than(self): self.assertGreater(self.value(3),self.value(2))
    def test_cross_unit_comparison(self):
        with self.assertRaises(ValueError): self.value() < MetricValue("kafka_lag","messages",1)
    def test_wrong_unit(self):
        with self.assertRaises(ValueError): MetricValue("postgresql_lag","milliseconds",1)
    def test_negative(self):
        with self.assertRaises(ValueError): self.value(-1)
    def test_nan(self):
        with self.assertRaises(ValueError): self.value(float("nan"))
    def test_bool(self):
        with self.assertRaises(ValueError): self.value(True)
    def test_len(self): self.assertEqual(len(self.series()),2)
    def test_iter(self): self.assertEqual([v.value for v in self.series()],[1,2])
    def test_index(self): self.assertEqual(self.series()[0].value,1)
    def test_slice(self): self.assertEqual(len(self.series()[0:1]),1)
    def test_repr_safe(self): self.assertIn("count=2",repr(self.series()))
    def test_add(self): self.assertEqual(len(self.series([1])+self.series([2])),2)
    def test_add_different_service(self):
        with self.assertRaises(ValueError): self.series()+MetricSeries("other","postgresql_lag",[1])
    def test_add_wrong_type(self):
        with self.assertRaises(TypeError): self.series()+1
    def test_bad_service(self):
        with self.assertRaises(ValueError): MetricSeries("","postgresql_lag",[])
    def test_bad_samples(self):
        with self.assertRaises(TypeError): MetricSeries("pg","postgresql_lag","bad")
    def test_sample_limit(self):
        with self.assertRaises(ValueError): self.series([1]*1001)
    def test_session_context(self):
        s=SyntheticSession(self.series())
        with s as opened: self.assertEqual(len(list(opened)),2)
        self.assertEqual(s.state,"closed")
    def test_session_exception_cleanup(self):
        s=SyntheticSession(self.series())
        with self.assertRaisesRegex(RuntimeError,"injected"):
            with s: raise RuntimeError("injected")
        self.assertEqual(s.state,"closed")
    def test_session_closed_iteration(self):
        with self.assertRaises(SessionClosed): list(SyntheticSession(self.series()))
    def test_session_reopen(self):
        s=SyntheticSession(self.series())
        with s: pass
        with self.assertRaises(SessionClosed):
            with s: pass
    def test_duplicate_report(self):
        row={"service":"pg","kind":"postgresql_lag","samples":[1]}
        with self.assertRaises(ValueError): report([row,row])
    def test_report_sorted(self):
        rows=[{"service":"pg","kind":"postgresql_lag","samples":[1]},{"service":"es","kind":"elasticsearch_latency","samples":[2]}]
        self.assertEqual(report(rows)["series"][0]["kind"],"elasticsearch_latency")
    def test_cli_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"fixture.json"
            path.write_text(json.dumps([{"service":"pg","kind":"postgresql_lag","samples":[1]}]),encoding="utf-8")
            self.assertEqual(run(path)["series_count"],1)
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
./.venv/bin/python -m unittest -v test_protocols.py
./.venv/bin/python cli.py --input sample.json
./.venv/bin/python -m py_compile protocols.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m unittest -v test_protocols.py
.\.venv\Scripts\python.exe cli.py --input sample.json
.\.venv\Scripts\python.exe -m py_compile protocols.py cli.py
```

Expected output: three synthetic series with stable units and maximum values; session count returns to zero.

## 6. Failure injection and troubleshooting

1. Compare metrics with different units: reject comparison.
2. Add series for different services: reject aggregation.
3. Pass a string, negative, NaN, infinity or boolean metric: reject input.
4. Add more than 1,000 samples: reject the unbounded series.
5. Iterate a session before opening or after closing: lifecycle error.
6. Raise inside `with`: verify cleanup and exception propagation.
7. Duplicate a series identity in JSON: reject report.
8. Inspect `repr`: verify it includes only safe metadata.

## 7. Production runbooks

**Unit mismatch:** stop aggregation, inspect metric identity, require explicit reviewed conversion.

**Session leak:** compare enter/exit paths, verify exception cleanup and idempotent close.

**Unexpected operator behavior:** inspect special method contracts, return `NotImplemented` for unsupported types, add regression tests.

**Resource pressure:** cap series size and replace materialized collections with streaming implementations when appropriate.

## 8. Acceptance

- [ ] All 32 tests pass locally.
- [ ] Equality/hash/order obey contracts.
- [ ] Mixed-unit operations fail closed.
- [ ] Iteration and indexing are deterministic.
- [ ] Context manager cleans up after exceptions.
- [ ] JSON output is sanitized and deterministic.
- [ ] No real service connections or mutations.

**Execution status:** Unit tests are published but require local execution.
