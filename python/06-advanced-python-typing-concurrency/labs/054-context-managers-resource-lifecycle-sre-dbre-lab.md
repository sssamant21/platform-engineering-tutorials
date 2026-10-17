# Chapter 054 — Context Managers and Resource Lifecycle SRE/DBRE Lab

**Python 3.10+ | Standard library | Offline, read-only with respect to infrastructure**

## File layout
```text
ch054/
  lifecycle_ops.py
  test_lifecycle_ops.py
  events.json
  output/
```

Create `output/` before running. This lab writes only a local report and uses an ephemeral in-memory SQLite fixture.

## 1. lifecycle_ops.py

```python
"""Chapter 054: offline, resource-safe SRE/DBRE lab. Python 3.10+."""
from __future__ import annotations
from contextlib import ExitStack, contextmanager, closing
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol, TextIO
import argparse
import json
import math
import os
import re
import sqlite3
import sys
import tempfile

MAX_BYTES = 65536
MAX_EVENTS = 1000
POLICY = {
    "postgresql": ("replication_lag", "seconds", 30.0, 120.0),
    "elasticsearch": ("search_latency", "milliseconds", 200.0, 500.0),
    "kafka": ("consumer_lag", "messages", 1000.0, 10000.0),
}

class LabError(ValueError):
    pass

@dataclass(frozen=True)
class Event:
    service: str
    engine: str
    value: float
    severity: str

class EventReader(Protocol):
    def fetch(self) -> list[Event]: ...
    def close(self) -> None: ...

class ManagedReader:
    """Example of __enter__/__exit__; release even when fetch raises."""
    def __init__(self, events: list[Event]) -> None:
        self.events = events
        self.closed = False
        self.entered = False

    def __enter__(self) -> "ManagedReader":
        if self.closed or self.entered:
            raise LabError("reader already used")
        self.entered = True
        return self

    def fetch(self) -> list[Event]:
        if not self.entered or self.closed:
            raise LabError("reader not active")
        return list(self.events)

    def close(self) -> None:
        self.closed = True

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        self.close()
        return False  # propagate the original exception

def unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise LabError("duplicate JSON key")
        result[key] = value
    return result

def reject_constant(value: str) -> object:
    raise LabError("nonfinite JSON number")

def parse_event(value: object) -> Event:
    if not isinstance(value, dict) or set(value) != {
        "service", "engine", "metric", "unit", "value"
    }:
        raise LabError("invalid event schema")
    service = value["service"]
    engine = value["engine"]
    if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", service):
        raise LabError("invalid service")
    if not isinstance(engine, str) or engine not in POLICY:
        raise LabError("unknown engine")
    metric, unit, warn, critical = POLICY[engine]
    if value["metric"] != metric or value["unit"] != unit:
        raise LabError("metric/unit mismatch")
    number = value["value"]
    if type(number) not in (int, float):
        raise LabError("invalid numeric type")
    try:
        number = float(number)
    except (OverflowError, ValueError) as exc:
        raise LabError("invalid numeric value") from exc
    if not math.isfinite(number) or number < 0:
        raise LabError("invalid numeric value")
    severity = "critical" if number >= critical else "warning" if number >= warn else "healthy"
    return Event(service, engine, number, severity)

@contextmanager
def bounded_json_file(path: Path) -> Iterator[object]:
    """Own the file descriptor; validate bounded UTF-8 JSON before yielding."""
    if not path.is_file() or path.is_symlink():
        raise LabError("expected regular non-symlink file")
    if path.stat().st_size > MAX_BYTES:
        raise LabError("input too large")
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise LabError("input too large")
        try:
            data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_pairs,
                              parse_constant=reject_constant)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise LabError("invalid UTF-8 or JSON") from exc
        yield data

def validated_events(data: object) -> list[Event]:
    if not isinstance(data, list) or len(data) > MAX_EVENTS:
        raise LabError("expected bounded event array")
    return [parse_event(item) for item in data]

@contextmanager
def sqlite_snapshot(events: list[Event]) -> Iterator[sqlite3.Connection]:
    """Ephemeral in-memory SQLite fixture; never connects to production."""
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(
            "CREATE TABLE telemetry (service TEXT, engine TEXT, severity TEXT, value REAL)"
        )
        connection.executemany(
            "INSERT INTO telemetry VALUES (?, ?, ?, ?)",
            [(e.service, e.engine, e.severity, e.value) for e in events]
        )
        connection.commit()
        yield connection
    finally:
        connection.close()

def summarize_db(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute(
        "SELECT severity, COUNT(*) FROM telemetry GROUP BY severity"
    ).fetchall()
    counts = {"healthy": 0, "warning": 0, "critical": 0}
    for name, count in rows:
        if name not in counts:
            raise LabError("unknown severity")
        counts[name] = int(count)
    return counts

def summarize(events: list[Event]) -> dict[str, object]:
    with ManagedReader(events) as reader:
        with sqlite_snapshot(reader.fetch()) as connection:
            counts = summarize_db(connection)
    return {"schema_version": 1, "dry_run": True, "total": len(events), "counts": counts}

def atomic_json(root: Path, name: str, data: dict[str, object]) -> Path:
    if not root.is_dir() or root.is_symlink():
        raise LabError("output directory must be trusted and existing")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}\.json", name):
        raise LabError("invalid output filename")
    target = root / name
    if target.is_symlink():
        raise LabError("symlink output refused")
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=root, prefix=".ch054-",
            delete=False
        ) as handle:
            temporary = Path(handle.name)
            try:
                os.chmod(temporary, 0o600)
            except OSError:
                pass
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        temporary = None
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def run(input_path: Path, output_dir: Path) -> dict[str, object]:
    with bounded_json_file(input_path) as data:
        events = validated_events(data)
    result = summarize(events)
    atomic_json(output_dir, "report.json", result)
    return result

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline resource lifecycle SRE/DBRE lab")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.input, args.output_dir)
    except (LabError, OSError, sqlite3.Error):
        print("operation failed: input, resource, or output error", file=sys.stderr)
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

```

## 2. events.json

```json
[
  {"service":"pg-replica","engine":"postgresql","metric":"replication_lag","unit":"seconds","value":45},
  {"service":"es-search","engine":"elasticsearch","metric":"search_latency","unit":"milliseconds","value":650},
  {"service":"kafka-worker","engine":"kafka","metric":"consumer_lag","unit":"messages","value":10000}
]
```

## 3. test_lifecycle_ops.py

```python
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifecycle_ops import (
    Event, LabError, ManagedReader, unique_pairs, parse_event, bounded_json_file,
    validated_events, sqlite_snapshot, summarize_db, summarize, atomic_json,
    run, main, MAX_BYTES, MAX_EVENTS,
)

PG = {"service":"pg-replica","engine":"postgresql","metric":"replication_lag",
      "unit":"seconds","value":45}
ES = {"service":"es-search","engine":"elasticsearch","metric":"search_latency",
      "unit":"milliseconds","value":650}
KAFKA = {"service":"kafka-worker","engine":"kafka","metric":"consumer_lag",
         "unit":"messages","value":10000}

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / "events.json"
        self.input.write_text(json.dumps([PG, ES, KAFKA]), encoding="utf-8")

    def bad_event(self, **changes):
        with self.assertRaises(LabError):
            parse_event({**PG, **changes})

    def test_reader_enter(self):
        reader = ManagedReader([])
        with reader as active: self.assertIs(active, reader)
        self.assertTrue(reader.closed)
    def test_reader_fetch(self):
        reader = ManagedReader([Event("pg","postgresql",1,"healthy")])
        with reader as active: self.assertEqual(len(active.fetch()), 1)
    def test_reader_fetch_outside(self):
        with self.assertRaises(LabError): ManagedReader([]).fetch()
    def test_reader_closed_fetch(self):
        reader = ManagedReader([])
        with reader: pass
        with self.assertRaises(LabError): reader.fetch()
    def test_reader_double_enter(self):
        reader = ManagedReader([])
        with reader:
            with self.assertRaises(LabError): reader.__enter__()
    def test_reader_reuse(self):
        reader = ManagedReader([])
        with reader: pass
        with self.assertRaises(LabError): reader.__enter__()
    def test_reader_exception_propagates(self):
        reader = ManagedReader([])
        with self.assertRaises(RuntimeError):
            with reader: raise RuntimeError("synthetic")
        self.assertTrue(reader.closed)
    def test_reader_exception_not_suppressed(self):
        reader = ManagedReader([])
        self.assertFalse(reader.__exit__(RuntimeError, RuntimeError("x"), None))
    def test_duplicate_key(self):
        with self.assertRaises(LabError): unique_pairs([("x",1),("x",2)])
    def test_unique_pairs(self):
        self.assertEqual(unique_pairs([("x",1)]), {"x":1})
    def test_parse_pg(self):
        self.assertEqual(parse_event(PG).severity, "warning")
    def test_parse_pg_healthy(self):
        self.assertEqual(parse_event({**PG,"value":0}).severity, "healthy")
    def test_parse_pg_critical(self):
        self.assertEqual(parse_event({**PG,"value":120}).severity, "critical")
    def test_parse_es(self):
        self.assertEqual(parse_event(ES).severity, "critical")
    def test_parse_kafka(self):
        self.assertEqual(parse_event(KAFKA).severity, "critical")
    def test_parse_unknown_engine(self): self.bad_event(engine="mysql")
    def test_parse_wrong_metric(self): self.bad_event(metric="latency")
    def test_parse_wrong_unit(self): self.bad_event(unit="milliseconds")
    def test_parse_bad_service(self): self.bad_event(service="=1+1")
    def test_parse_unicode_service(self): self.bad_event(service="東京")
    def test_parse_boolean(self): self.bad_event(value=True)
    def test_parse_string(self): self.bad_event(value="45")
    def test_parse_negative(self): self.bad_event(value=-1)
    def test_parse_nan(self): self.bad_event(value=float("nan"))
    def test_parse_inf(self): self.bad_event(value=float("inf"))
    def test_parse_extra(self): self.bad_event(password="secret")
    def test_parse_missing(self):
        data = dict(PG)
        del data["unit"]
        with self.assertRaises(LabError): parse_event(data)
    def test_parse_nonobject(self):
        with self.assertRaises(LabError): parse_event([])
    def test_bounded_read(self):
        with bounded_json_file(self.input) as value: self.assertEqual(len(value), 3)
    def test_bounded_bad_json(self):
        self.input.write_text("{bad")
        with self.assertRaises(LabError):
            with bounded_json_file(self.input): pass
    def test_bounded_duplicate(self):
        self.input.write_text('{"x":1,"x":2}')
        with self.assertRaises(LabError):
            with bounded_json_file(self.input): pass
    def test_bounded_nan(self):
        self.input.write_text("[NaN]")
        with self.assertRaises(LabError):
            with bounded_json_file(self.input): pass
    def test_bounded_utf8(self):
        self.input.write_bytes(b"\xff")
        with self.assertRaises(LabError):
            with bounded_json_file(self.input): pass
    def test_bounded_size(self):
        self.input.write_bytes(b"x" * (MAX_BYTES+1))
        with self.assertRaises(LabError):
            with bounded_json_file(self.input): pass
    def test_bounded_missing(self):
        with self.assertRaises(LabError):
            with bounded_json_file(self.root/"missing"): pass
    def test_bounded_symlink(self):
        link = self.root / "link"
        try: link.symlink_to(self.input)
        except OSError: self.skipTest("symlinks unavailable")
        with self.assertRaises(LabError):
            with bounded_json_file(link): pass
    def test_validated(self):
        self.assertEqual(len(validated_events([PG])), 1)
    def test_validated_empty(self):
        self.assertEqual(validated_events([]), [])
    def test_validated_nonarray(self):
        with self.assertRaises(LabError): validated_events({})
    def test_validated_too_many(self):
        with self.assertRaises(LabError): validated_events([PG]*(MAX_EVENTS+1))
    def test_sqlite_counts(self):
        with sqlite_snapshot([parse_event(PG),parse_event(ES)]) as connection:
            self.assertEqual(summarize_db(connection)["critical"], 1)
    def test_sqlite_empty(self):
        with sqlite_snapshot([]) as connection:
            self.assertEqual(summarize_db(connection)["healthy"], 0)
    def test_sqlite_rollback_cleanup(self):
        with self.assertRaises(RuntimeError):
            with sqlite_snapshot([]): raise RuntimeError("synthetic")
    def test_sqlite_parameterized(self):
        with sqlite_snapshot([Event("safe","postgresql",1,"healthy")]) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0], 1)
    def test_summarize(self):
        self.assertEqual(summarize(list(map(parse_event,[PG,ES,KAFKA])))["total"], 3)
    def test_summarize_counts(self):
        self.assertEqual(summarize(list(map(parse_event,[PG,ES,KAFKA])))["counts"],
                         {"healthy":0,"warning":1,"critical":2})
    def test_summarize_empty(self):
        self.assertEqual(summarize([])["total"], 0)
    def test_summarize_dry_run(self):
        self.assertTrue(summarize([])["dry_run"])
    def test_atomic(self):
        target = atomic_json(self.root, "report.json", {"ok":True})
        self.assertEqual(json.loads(target.read_text()), {"ok":True})
    def test_atomic_replace(self):
        atomic_json(self.root,"report.json",{"v":1})
        atomic_json(self.root,"report.json",{"v":2})
        self.assertEqual(json.loads((self.root/"report.json").read_text())["v"],2)
    def test_atomic_traversal(self):
        with self.assertRaises(LabError): atomic_json(self.root,"../escape.json",{})
    def test_atomic_bad_extension(self):
        with self.assertRaises(LabError): atomic_json(self.root,"x.txt",{})
    def test_atomic_missing_dir(self):
        with self.assertRaises(LabError): atomic_json(self.root/"missing","report.json",{})
    def test_atomic_symlink(self):
        link = self.root/"report.json"
        try: link.symlink_to(self.input)
        except OSError: self.skipTest("symlinks unavailable")
        with self.assertRaises(LabError): atomic_json(self.root,"report.json",{})
    def test_atomic_cleanup(self):
        atomic_json(self.root,"report.json",{"ok":True})
        self.assertFalse(list(self.root.glob(".ch054-*")))
    def test_run(self):
        self.assertEqual(run(self.input,self.root)["total"],3)
    def test_run_writes_report(self):
        run(self.input,self.root)
        self.assertTrue((self.root/"report.json").exists())
    def test_run_no_input_mutation(self):
        before = self.input.read_bytes()
        run(self.input,self.root)
        self.assertEqual(self.input.read_bytes(),before)
    def test_run_no_secret(self):
        run(self.input,self.root)
        self.assertNotIn("password", (self.root/"report.json").read_text())
    def test_cli_success(self):
        self.assertEqual(main(["--input",str(self.input),"--output-dir",str(self.root)]),0)
    def test_cli_failure(self):
        self.input.write_text("{bad")
        self.assertEqual(main(["--input",str(self.input),"--output-dir",str(self.root)]),3)

if __name__ == "__main__":
    unittest.main()

```

## 4. Execute

Linux/macOS/WSL:
```bash
mkdir -p output
python3 -m py_compile lifecycle_ops.py test_lifecycle_ops.py
python3 -m unittest -v test_lifecycle_ops.py
python3 lifecycle_ops.py --input events.json --output-dir output
python3 -m json.tool output/report.json
```

Windows PowerShell:
```powershell
New-Item -ItemType Directory -Force output
py -3 -m unittest -v test_lifecycle_ops.py
py -3 lifecycle_ops.py --input events.json --output-dir output
Get-Content output/report.json
```

Expected synthetic results: 3 events, 0 healthy, 1 warning and 2 critical. Exit code 0 indicates a successful report, not healthy infrastructure.

## 5. Failure injection
1. Raise inside `ManagedReader` and verify `close()` is invoked and the exception propagates.
2. Attempt to reuse a closed reader and verify rejection.
3. Raise inside the SQLite fixture context and verify cleanup.
4. Inject duplicate JSON keys, NaN, invalid UTF-8 and oversized input.
5. Add an unknown field or wrong unit.
6. Inject negative, boolean and nonfinite metrics.
7. Attempt a path-traversal output filename.
8. Attempt a symlink input or output path.
9. Run twice and verify the report is replaced, not appended.
10. Confirm no temporary file remains after successful replacement.
11. Verify the source input remains unchanged.
12. Deliberately return `True` from a training-only `__exit__` to observe suppression; never use that pattern for real operational failures.

## 6. Production runbooks
**Leaked file handle:** identify the failing lifecycle, ensure `with` or `finally`, rerun cleanup tests.

**Database session leak:** inspect driver transaction/connection semantics, close sessions and restore pool limits.

**Interrupted report write:** preserve last known-good report, verify output directory and regenerate idempotently.

**Malformed telemetry:** quarantine the export, validate schema and units, then replay.

**Rollback:** pin last known-good code, execute unit tests and inspect resource counts.

## 7. Final 100-point assessment
| Criterion | Points |
|---|---:|
| Automated tests and syntax checks | 25 |
| Context manager protocol and cleanup | 20 |
| File and database resource ownership | 20 |
| Input safety and atomic output | 15 |
| Incident simulations | 10 |
| Troubleshooting and runbooks | 10 |

Passing target: **90/100** with all safety checks passing. Test execution must be independently verified; publishing source and tests alone does not establish a passing suite.
