# Chapter 038 — Streaming SRE/DBRE Telemetry Pipeline Lab

**Python 3.10+ | Standard library | Offline, synthetic, read-only**

## Goal

Implement a single-pass, memory-bounded JSONL telemetry pipeline with generator stages, an explicit iterator class, strict validation, severity classification and a bounded summary. No credentials, network calls or infrastructure mutations.

## Project layout

```text
ch038/
  pipeline.py
  cli.py
  sample.jsonl
  test_pipeline.py
```

## 1. pipeline.py

```python
"""Offline lazy telemetry pipeline; no network or infrastructure operations."""
from collections import Counter
import json
import math

UNITS = {
    "postgresql_lag": ("seconds", 30.0, 120.0),
    "elasticsearch_latency": ("milliseconds", 200.0, 500.0),
    "kafka_lag": ("messages", 1000.0, 10000.0),
}
MAX_LINE_CHARS = 4096
MAX_PREVIEW = 20


class RangeIterator:
    """Single-use integer iterator demonstrating __iter__ and __next__."""
    def __init__(self, stop):
        if isinstance(stop, bool) or not isinstance(stop, int) or stop < 0:
            raise ValueError("stop must be a nonnegative integer")
        self._stop = stop
        self._current = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._current >= self._stop:
            raise StopIteration
        result = self._current
        self._current += 1
        return result


def finite_metric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("metric must be numeric")
    if not math.isfinite(value) or value < 0:
        raise ValueError("metric must be finite and nonnegative")
    return float(value)


def parse_lines(lines):
    """Yield validated records one at a time; fail closed on malformed input."""
    for number, raw in enumerate(lines, 1):
        if not isinstance(raw, str) or len(raw) > MAX_LINE_CHARS:
            raise ValueError(f"line {number}: invalid or oversized line")
        if not raw.strip():
            continue
        try:
            item = json.loads(
                raw,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")),
            )
        except (ValueError, TypeError) as exc:
            raise ValueError(f"line {number}: malformed JSON") from exc
        if not isinstance(item, dict) or set(item) != {"service", "kind", "unit", "value"}:
            raise ValueError(f"line {number}: invalid record schema")
        service = item["service"]
        kind = item["kind"]
        if not isinstance(service, str) or not service.strip() or len(service) > 64:
            raise ValueError(f"line {number}: invalid service")
        if not isinstance(kind, str) or kind not in UNITS:
            raise ValueError(f"line {number}: invalid kind")
        if item["unit"] != UNITS[kind][0]:
            raise ValueError(f"line {number}: invalid unit")
        value = finite_metric(item["value"])
        yield {"service": service, "kind": kind, "unit": item["unit"], "value": value}


def classify(records):
    for item in records:
        _, warning, critical = UNITS[item["kind"]]
        value = item["value"]
        severity = "critical" if value >= critical else "warning" if value >= warning else "healthy"
        yield {**item, "severity": severity}


def nonhealthy(records):
    for item in records:
        if item["severity"] != "healthy":
            yield item


def take(records, limit):
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("limit must be nonnegative integer")
    iterator = iter(records)
    for _ in range(limit):
        try:
            yield next(iterator)
        except StopIteration:
            return


def summarize(records, preview_limit=5):
    if isinstance(preview_limit, bool) or not isinstance(preview_limit, int) or not 0 <= preview_limit <= MAX_PREVIEW:
        raise ValueError("preview limit must be in 0..20")
    counts = Counter()
    preview = []
    total = 0
    for item in records:
        total += 1
        counts[item["severity"]] += 1
        if len(preview) < preview_limit and item["severity"] != "healthy":
            preview.append(item)
    return {
        "schema_version": 1,
        "total": total,
        "counts": {name: counts[name] for name in ("healthy", "warning", "critical")},
        "preview": preview,
    }


def process(lines, preview_limit=5):
    return summarize(classify(parse_lines(lines)), preview_limit)
```

## 2. cli.py

```python
import argparse
import json
from pathlib import Path
from pipeline import process


def run(path, preview_limit=5):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return process(handle, preview_limit)
    except (OSError, UnicodeError) as exc:
        raise ValueError("input file unreadable") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline streaming SRE telemetry")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--preview", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        result = run(args.input, args.preview)
    except (TypeError, ValueError) as exc:
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

## 4. test_pipeline.py — 32 tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from pipeline import (
    RangeIterator, parse_lines, classify, nonhealthy, take,
    summarize, process, finite_metric, MAX_LINE_CHARS,
)
from cli import run


def row(kind="postgresql_lag", unit="seconds", value=1, service="pg"):
    return json.dumps({"service":service,"kind":kind,"unit":unit,"value":value}) + "\n"


class PipelineTests(unittest.TestCase):
    def test_range(self): self.assertEqual(list(RangeIterator(3)),[0,1,2])
    def test_range_empty(self): self.assertEqual(list(RangeIterator(0)),[])
    def test_range_invalid(self):
        with self.assertRaises(ValueError): RangeIterator(-1)
    def test_range_exhausted(self):
        it=RangeIterator(1)
        next(it)
        with self.assertRaises(StopIteration): next(it)
    def test_parse_one(self): self.assertEqual(len(list(parse_lines([row()]))),1)
    def test_parse_blank(self): self.assertEqual(list(parse_lines(["\n",row()] ))[0]["service"],"pg")
    def test_parse_lazy(self):
        generator=parse_lines([row()])
        self.assertFalse(isinstance(generator,list))
        self.assertEqual(next(generator)["value"],1)
    def test_parse_bad_json(self):
        with self.assertRaises(ValueError): list(parse_lines(["{bad"]))
    def test_parse_bad_schema(self):
        with self.assertRaises(ValueError): list(parse_lines(['{"service":"pg"}']))
    def test_parse_bad_kind(self):
        with self.assertRaises(ValueError): list(parse_lines([row(kind="unknown")]))
    def test_parse_bad_unit(self):
        with self.assertRaises(ValueError): list(parse_lines([row(unit="ms")]))
    def test_parse_bad_service(self):
        with self.assertRaises(ValueError): list(parse_lines([row(service="")]))
    def test_parse_oversized(self):
        with self.assertRaises(ValueError): list(parse_lines(["x"*(MAX_LINE_CHARS+1)]))
    def test_negative(self):
        with self.assertRaises(ValueError): finite_metric(-1)
    def test_nan(self):
        with self.assertRaises(ValueError): finite_metric(float("nan"))
    def test_infinity(self):
        with self.assertRaises(ValueError): finite_metric(float("inf"))
    def test_bool(self):
        with self.assertRaises(ValueError): finite_metric(True)
    def test_pg_healthy(self): self.assertEqual(next(classify(parse_lines([row(value=1)])))["severity"],"healthy")
    def test_pg_warning(self): self.assertEqual(next(classify(parse_lines([row(value=30)])))["severity"],"warning")
    def test_pg_critical(self): self.assertEqual(next(classify(parse_lines([row(value=120)])))["severity"],"critical")
    def test_es_warning(self): self.assertEqual(next(classify(parse_lines([row("elasticsearch_latency","milliseconds",200)])))["severity"],"warning")
    def test_es_critical(self): self.assertEqual(next(classify(parse_lines([row("elasticsearch_latency","milliseconds",500)])))["severity"],"critical")
    def test_kafka_warning(self): self.assertEqual(next(classify(parse_lines([row("kafka_lag","messages",1000)])))["severity"],"warning")
    def test_kafka_critical(self): self.assertEqual(next(classify(parse_lines([row("kafka_lag","messages",10000)])))["severity"],"critical")
    def test_nonhealthy(self):
        values=nonhealthy(classify(parse_lines([row(value=1),row(value=30)])))
        self.assertEqual(len(list(values)),1)
    def test_take(self): self.assertEqual(list(take(iter(range(10)),3)),[0,1,2])
    def test_take_zero(self): self.assertEqual(list(take(iter(range(10)),0)),[])
    def test_summary(self):
        result=process([row(value=1),row(value=30),row(value=120)])
        self.assertEqual(result["counts"],{"healthy":1,"warning":1,"critical":1})
    def test_preview_bound(self): self.assertEqual(len(process([row(value=120)]*10,2)["preview"]),2)
    def test_invalid_preview(self):
        with self.assertRaises(ValueError): process([row()],21)
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

## 5. Run

Linux/macOS/WSL:

```bash
python3 -m venv .venv
./.venv/bin/python -m unittest -v test_pipeline.py
./.venv/bin/python cli.py --input sample.jsonl --preview 5
./.venv/bin/python -m py_compile pipeline.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m unittest -v test_pipeline.py
.\.venv\Scripts\python.exe cli.py --input sample.jsonl --preview 5
.\.venv\Scripts\python.exe -m py_compile pipeline.py cli.py
```

Expected synthetic counts: healthy 2, warning 1, critical 2. Output is a deterministic JSON object.

## 6. Failure injection

1. Provide a malformed JSONL line after valid lines: entire CLI run fails without publishing a partial report.
2. Supply a line larger than 4,096 characters: reject it.
3. Use an unknown metric kind or incorrect unit: reject the record.
4. Pass negative, NaN, infinity or boolean metric values: fail closed.
5. Request preview larger than 20: reject configuration.
6. Consume a `RangeIterator` twice: second iteration is exhausted.
7. Use `take` to verify early termination of a lazy iterator.
8. Process 100,000 generated lines with preview 5 and confirm the preview remains bounded.

## 7. Production runbooks

**Memory pressure:** inspect materialization, preview caps, source line size and retained state; replace eager transforms with generators.

**Schema drift:** stop report emission, record safe line number, fix producer or parser and replay sanitized fixture.

**Unexpected partial data:** confirm source completeness and avoid emitting successful status on failed streams; use checkpointing for live sources.

**Operational safety:** this lab uses only synthetic data; live adapters need scoped read-only credentials, bounded timeouts, retry budgets and explicit offset semantics.

## 8. Acceptance

- [ ] All 32 tests pass locally.
- [ ] Iterator and generator protocols behave correctly.
- [ ] One-pass summary has bounded preview memory.
- [ ] Invalid telemetry fails closed.
- [ ] JSONL file handle closes on error.
- [ ] No network, credentials or infrastructure mutations.

**Execution status:** Tests are included but require local execution.
