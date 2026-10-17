# Chapter 052 — Streaming SRE/DBRE Telemetry Pipeline Lab

**Python 3.10+ | Standard library | Offline, read-only**

## Project layout

```text
ch052/
  stream_ops.py
  test_stream_ops.py
  events.ndjson
```

## 1. stream_ops.py

```python
"""Chapter 052: bounded, lazy, read-only operational telemetry streaming."""
from __future__ import annotations
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import islice
import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import TypeVar

MAX_LINE_BYTES = 4096
MAX_EVENTS = 100000
ENGINES = {"postgresql": ("replication_lag", "seconds", 30, 120),
           "elasticsearch": ("search_latency", "milliseconds", 200, 500),
           "kafka": ("consumer_lag", "messages", 1000, 10000)}
T = TypeVar("T")

class StreamError(ValueError):
    pass

@dataclass(frozen=True)
class Event:
    service: str
    engine: str
    metric: str
    value: float
    unit: str
    timestamp: str
    severity: str

def unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StreamError("duplicate JSON key")
        result[key] = value
    return result

def reject_constant(value: str) -> object:
    raise StreamError("nonfinite JSON value")

def parse_event(line: str) -> Event:
    try:
        raw = json.loads(line, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    except json.JSONDecodeError as exc:
        raise StreamError("malformed JSON") from exc
    if not isinstance(raw, dict) or set(raw) != {"service", "engine", "metric", "value", "unit", "timestamp"}:
        raise StreamError("invalid schema")
    service = raw["service"]
    if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise StreamError("invalid service")
    engine = raw["engine"]
    if not isinstance(engine, str) or engine not in ENGINES:
        raise StreamError("unknown engine")
    metric, unit, warning, critical = ENGINES[engine]
    if raw["metric"] != metric or raw["unit"] != unit:
        raise StreamError("metric/unit mismatch")
    value = raw["value"]
    if type(value) not in (int, float):
        raise StreamError("value must be numeric")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise StreamError("invalid numeric value") from exc
    if not math.isfinite(number) or number < 0:
        raise StreamError("nonfinite or negative value")
    stamp = raw["timestamp"]
    if not isinstance(stamp, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", stamp
    ):
        raise StreamError("invalid UTC timestamp syntax")
    from datetime import datetime
    try:
        datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise StreamError("invalid calendar date") from exc
    severity = "critical" if number >= critical else "warning" if number >= warning else "healthy"
    return Event(service, engine, metric, number, unit, stamp, severity)

def stream_lines(path: Path, max_events: int = MAX_EVENTS) -> Iterator[Event]:
    if type(max_events) is not int or not 1 <= max_events <= MAX_EVENTS:
        raise StreamError("invalid event limit")
    if not path.is_file() or path.is_symlink():
        raise StreamError("expected regular non-symlink input")
    with path.open("rb") as handle:
        count = 0
        for line_no, raw in enumerate(handle, 1):
            if len(raw) > MAX_LINE_BYTES:
                raise StreamError(f"line {line_no}: too long")
            if not raw.strip():
                continue
            count += 1
            if count > max_events:
                raise StreamError("event limit exceeded")
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise StreamError(f"line {line_no}: invalid UTF-8") from exc
            try:
                yield parse_event(line)
            except StreamError as exc:
                raise StreamError(f"line {line_no}: {exc}") from exc

def batch(iterable: Iterable[T], size: int) -> Iterator[tuple[T, ...]]:
    if type(size) is not int or not 1 <= size <= 10000:
        raise StreamError("batch size must be 1..10000")
    source = iter(iterable)
    while True:
        chunk = tuple(islice(source, size))
        if not chunk:
            break
        yield chunk

def summarize(events: Iterable[Event]) -> dict[str, object]:
    counts: Counter[str] = Counter()
    by_engine: Counter[str] = Counter()
    total = 0
    for event in events:
        total += 1
        counts[event.severity] += 1
        by_engine[event.engine] += 1
    return {"schema_version": 1, "dry_run": True, "total": total,
            "counts": {key: counts[key] for key in ("healthy", "warning", "critical")},
            "engines": {key: by_engine[key] for key in sorted(ENGINES)}}

def summarize_batches(chunks: Iterable[tuple[Event, ...]]) -> dict[str, object]:
    def flatten() -> Iterator[Event]:
        for chunk in chunks:
            yield from chunk
    return summarize(flatten())

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline streaming SRE/DBRE telemetry analyzer")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-events", type=int, default=MAX_EVENTS)
    args = parser.parse_args(argv)
    try:
        output = summarize_batches(batch(stream_lines(args.input, args.max_events), args.batch_size))
    except (StreamError, OSError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

## 2. events.ndjson

```jsonl
{"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45,"timestamp":"2026-10-17T12:00:00Z"}
{"service":"es-search","engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":650,"timestamp":"2026-10-17T12:01:00Z"}
{"service":"kafka-worker","engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000,"timestamp":"2026-10-17T12:02:00Z"}
```

## 3. test_stream_ops.py — automated tests

```python
import json
from pathlib import Path
import tempfile
import unittest
from itertools import count
from stream_ops import Event, StreamError, parse_event, stream_lines, batch, summarize, summarize_batches, main

PG={"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45,"timestamp":"2026-10-17T12:00:00Z"}
ES={"service":"es-search","engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":650,"timestamp":"2026-10-17T12:01:00Z"}
KAFKA={"service":"kafka-worker","engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000,"timestamp":"2026-10-17T12:02:00Z"}

class StreamTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"events.ndjson"
        self.path.write_text("\n".join(map(json.dumps,(PG,ES,KAFKA)))+"\n",encoding="utf-8")
    def bad(self,**updates):
        with self.assertRaises(StreamError):
            parse_event(json.dumps({**PG,**updates}))
    def test_pg(self): self.assertEqual(parse_event(json.dumps(PG)).severity,"warning")
    def test_pg_healthy(self): self.assertEqual(parse_event(json.dumps({**PG,"value":5})).severity,"healthy")
    def test_pg_critical(self): self.assertEqual(parse_event(json.dumps({**PG,"value":120})).severity,"critical")
    def test_es(self): self.assertEqual(parse_event(json.dumps(ES)).severity,"critical")
    def test_kafka(self): self.assertEqual(parse_event(json.dumps(KAFKA)).severity,"critical")
    def test_pg_boundary(self): self.assertEqual(parse_event(json.dumps({**PG,"value":30})).severity,"warning")
    def test_es_boundary(self): self.assertEqual(parse_event(json.dumps({**ES,"value":200})).severity,"warning")
    def test_kafka_boundary(self): self.assertEqual(parse_event(json.dumps({**KAFKA,"value":1000})).severity,"warning")
    def test_bad_engine(self): self.bad(engine="mysql")
    def test_bad_unit(self): self.bad(unit="milliseconds")
    def test_bad_metric(self): self.bad(metric="latency")
    def test_bad_service(self): self.bad(service="pg replica")
    def test_bad_service_type(self): self.bad(service=42)
    def test_negative(self): self.bad(value=-1)
    def test_bool(self): self.bad(value=True)
    def test_string(self): self.bad(value="45")
    def test_nan(self): self.bad(value=float("nan"))
    def test_infinity(self): self.bad(value=float("inf"))
    def test_date(self): self.bad(timestamp="2026-02-30T12:00:00Z")
    def test_naive(self): self.bad(timestamp="2026-10-17T12:00:00")
    def test_extra(self): self.bad(password="secret")
    def test_missing(self):
        d=dict(PG); d.pop("value")
        with self.assertRaises(StreamError): parse_event(json.dumps(d))
    def test_duplicate(self):
        with self.assertRaises(StreamError): parse_event(json.dumps(PG)[:-1]+',"value":99}')
    def test_malformed(self):
        with self.assertRaises(StreamError): parse_event("{bad")
    def test_nonobject(self):
        with self.assertRaises(StreamError): parse_event("[]")
    def test_stream(self): self.assertEqual(len(list(stream_lines(self.path))),3)
    def test_lazy(self):
        stream=stream_lines(self.path)
        self.assertEqual(next(stream).service,"pg-replica")
        stream.close()
    def test_blank(self):
        self.path.write_text("\n"+json.dumps(PG)+"\n\n")
        self.assertEqual(len(list(stream_lines(self.path))),1)
    def test_line_number(self):
        self.path.write_text(json.dumps(PG)+"\nBAD\n")
        with self.assertRaisesRegex(StreamError,"line 2"): list(stream_lines(self.path))
    def test_line_limit(self):
        self.path.write_bytes(b"x"*4097+b"\n")
        with self.assertRaisesRegex(StreamError,"too long"): list(stream_lines(self.path))
    def test_utf8(self):
        self.path.write_bytes(b"\xff\n")
        with self.assertRaisesRegex(StreamError,"UTF-8"): list(stream_lines(self.path))
    def test_event_limit(self):
        with self.assertRaisesRegex(StreamError,"event limit"): list(stream_lines(self.path,2))
    def test_limit_zero(self):
        with self.assertRaises(StreamError): list(stream_lines(self.path,0))
    def test_limit_bool(self):
        with self.assertRaises(StreamError): list(stream_lines(self.path,True))
    def test_missing_file(self):
        with self.assertRaises(StreamError): list(stream_lines(self.path.parent/"missing"))
    def test_symlink(self):
        link=self.path.parent/"link"
        try: link.symlink_to(self.path)
        except OSError: self.skipTest("symlinks unavailable")
        with self.assertRaises(StreamError): list(stream_lines(link))
    def test_batch(self): self.assertEqual(list(batch(range(5),2)),[(0,1),(2,3),(4,)])
    def test_batch_empty(self): self.assertEqual(list(batch([],2)),[])
    def test_batch_one(self): self.assertEqual(list(batch([1,2],1)),[(1,),(2,)])
    def test_batch_invalid(self):
        with self.assertRaises(StreamError): list(batch([1],0))
    def test_batch_bool(self):
        with self.assertRaises(StreamError): list(batch([1],True))
    def test_batch_high(self):
        with self.assertRaises(StreamError): list(batch([1],10001))
    def test_batch_lazy(self):
        source=count()
        self.assertEqual(next(batch(source,3)),(0,1,2))
        self.assertEqual(next(source),3)
    def test_summary(self): self.assertEqual(summarize(stream_lines(self.path))["total"],3)
    def test_summary_critical(self): self.assertEqual(summarize(stream_lines(self.path))["counts"]["critical"],2)
    def test_summary_warning(self): self.assertEqual(summarize(stream_lines(self.path))["counts"]["warning"],1)
    def test_summary_empty(self): self.assertEqual(summarize([])["total"],0)
    def test_summary_batches(self): self.assertEqual(summarize_batches(batch(stream_lines(self.path),2))["total"],3)
    def test_summary_dry_run(self): self.assertTrue(summarize([])["dry_run"])
    def test_cli(self): self.assertEqual(main(["--input",str(self.path),"--batch-size","2"]),0)
    def test_cli_bad(self):
        self.path.write_text("BAD")
        self.assertEqual(main(["--input",str(self.path)]),3)
    def test_input_unchanged(self):
        before=self.path.read_bytes()
        summarize(stream_lines(self.path))
        self.assertEqual(self.path.read_bytes(),before)

if __name__=="__main__": unittest.main()
```

## 4. Run the lab

Linux/macOS/WSL:

```bash
python3 -m py_compile stream_ops.py test_stream_ops.py
python3 -m unittest -v test_stream_ops.py
python3 stream_ops.py --input events.ndjson --batch-size 2
```

Windows PowerShell:

```powershell
py -3 -m unittest -v test_stream_ops.py
py -3 stream_ops.py --input events.ndjson --batch-size 2
```

Expected: total 3, warning 1, critical 2, healthy 0. Exit code 0 means successful processing, **not** healthy datastores.

## 5. Failure injection

1. Insert malformed JSON on line 2 and verify the reported line number.
2. Insert a duplicate key or unknown field.
3. Change a metric unit, engine or service name.
4. Insert NaN, Infinity, negative or boolean values.
5. Supply invalid UTC calendar dates.
6. Exceed the per-line or total-event limit.
7. Supply invalid UTF-8.
8. Point at a missing file or symlink.
9. Stop consuming a generator early and explicitly close it.
10. Compare batches of size 1, 2 and 100.
11. Verify source files are unchanged.
12. Measure memory on a larger synthetic input while avoiding `list(stream_lines(...))`.

## 6. Operational runbooks

**Parser error:** stop downstream decisions, identify the sanitized line number, repair the source export and replay from an immutable copy.

**Memory pressure:** check for unintended materialization, reduce batch size, measure process RSS and use bounded I/O framing.

**File descriptor leak:** ensure suspended generators are closed and inspect process open-file counts.

**Rollback:** restore the last known-good parser, rerun the suite and compare event counts.

## 7. 100-point assessment

| Area | Points |
|---|---:|
| Automated tests and syntax validation | 30 |
| Iterator and generator correctness | 20 |
| Lazy batching and memory design | 20 |
| Schema and input safety | 15 |
| Failure injection and runbooks | 15 |

Target: 90/100 with all safety checks passing. The test suite is published for learner execution; publication alone does not establish that the tests have passed.
