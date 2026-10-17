# Chapter 048 — DST-Safe Maintenance Windows and Scheduling SRE/DBRE Lab

**Python 3.10+ | Standard library | Offline, read-only**

## Goal

Validate aware UTC timestamps, resolve IANA time zones, reject DST gaps, disambiguate repeated hours, calculate half-open maintenance windows and next daily local occurrences. The lab makes **no** scheduler, cloud, database or Kubernetes changes.

## Project layout

```text
ch048/
  time_lab.py
  test_time_lab.py
  request.json
```

## 1. time_lab.py

```python
"""Offline DST-safe maintenance-window and daily schedule calculations."""
import argparse
from datetime import datetime, date, time, timedelta, timezone
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = timezone.utc
MAX_BYTES = 65536
MAX_WINDOW_HOURS = 24

class TimeError(ValueError):
    pass

def parse_instant(value):
    if not isinstance(value, str) or len(value) > 40 or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:Z|[+-][0-9]{2}:[0-9]{2})", value
    ):
        raise TimeError("expected offset-aware ISO timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TimeError("invalid timestamp") from exc
    if result.utcoffset() is None:
        raise TimeError("naive timestamp")
    return result.astimezone(UTC)

def zone(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_+./-]{1,80}", name) or ".." in name:
        raise TimeError("invalid IANA zone")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise TimeError("unknown IANA zone or missing tzdata") from exc

def local_instant(day, clock, zone_name, fold=None):
    if not isinstance(day, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", day):
        raise TimeError("invalid local date")
    if not isinstance(clock, str) or not re.fullmatch(r"[0-9]{2}:[0-9]{2}", clock):
        raise TimeError("invalid local time")
    if fold is not None and (isinstance(fold, bool) or fold not in (0, 1)):
        raise TimeError("fold must be 0 or 1")
    try:
        naive = datetime.combine(date.fromisoformat(day), time.fromisoformat(clock))
    except ValueError as exc:
        raise TimeError("invalid local date or time") from exc
    tz = zone(zone_name)
    candidates = []
    for f in (0, 1):
        aware = naive.replace(tzinfo=tz, fold=f)
        instant = aware.astimezone(UTC)
        if instant.astimezone(tz).replace(tzinfo=None) == naive:
            if instant not in candidates:
                candidates.append(instant)
    if not candidates:
        raise TimeError("nonexistent local time (DST gap)")
    if len(candidates) == 2:
        if fold is None:
            raise TimeError("ambiguous local time: specify fold")
        return naive.replace(tzinfo=tz, fold=fold).astimezone(UTC)
    return candidates[0]

def iso(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

def elapsed_seconds(start, end):
    a, b = parse_instant(start), parse_instant(end)
    if b < a:
        raise TimeError("end precedes start")
    return int((b - a).total_seconds())

def window(day, start, end, zone_name, start_fold=None, end_fold=None):
    a = local_instant(day, start, zone_name, start_fold)
    b = local_instant(day, end, zone_name, end_fold)
    if b <= a:
        raise TimeError("window end must follow start")
    seconds = (b - a).total_seconds()
    if seconds > MAX_WINDOW_HOURS * 3600:
        raise TimeError("window too long")
    return {"schema_version": 1, "dry_run": True, "zone": zone_name,
            "start_utc": iso(a), "end_utc": iso(b), "duration_seconds": int(seconds),
            "end_exclusive": True}

def next_daily(after, clock, zone_name, fold=None):
    current = parse_instant(after)
    tz = zone(zone_name)
    local_day = current.astimezone(tz).date()
    for offset in range(3):
        day = (local_day + timedelta(days=offset)).isoformat()
        try:
            candidate = local_instant(day, clock, zone_name, fold)
        except TimeError as exc:
            if "nonexistent local time" in str(exc):
                raise
            raise
        if candidate > current:
            return {"schema_version": 1, "dry_run": True, "zone": zone_name,
                    "next_utc": iso(candidate), "local_date": day, "local_time": clock}
    raise TimeError("no next occurrence")

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TimeError("duplicate JSON key")
        result[key] = value
    return result

def load_request(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise TimeError("expected regular non-symlink file")
    if path.stat().st_size > MAX_BYTES:
        raise TimeError("request too large")
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise TimeError("request too large")
    try:
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(TimeError("nonfinite JSON")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise TimeError("invalid UTF-8 or JSON") from exc
    if not isinstance(data, dict):
        raise TimeError("expected JSON object")
    return data

def execute(data):
    kind = data.get("operation")
    if kind == "window":
        allowed = {"operation", "date", "start", "end", "zone", "start_fold", "end_fold"}
        if not set(data).issubset(allowed) or not {"operation","date","start","end","zone"}.issubset(data):
            raise TimeError("invalid window schema")
        return window(data["date"], data["start"], data["end"], data["zone"],
                      data.get("start_fold"), data.get("end_fold"))
    if kind == "next_daily":
        allowed = {"operation", "after", "time", "zone", "fold"}
        if not set(data).issubset(allowed) or not {"operation","after","time","zone"}.issubset(data):
            raise TimeError("invalid schedule schema")
        return next_daily(data["after"], data["time"], data["zone"], data.get("fold"))
    if kind == "elapsed":
        if set(data) != {"operation", "start", "end"}:
            raise TimeError("invalid elapsed schema")
        return {"schema_version": 1, "dry_run": True,
                "elapsed_seconds": elapsed_seconds(data["start"], data["end"])}
    raise TimeError("unsupported operation")

def main(argv=None, stdout=None, stderr=None):
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    parser = argparse.ArgumentParser(description="Offline timezone-safe SRE scheduling lab")
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = execute(load_request(args.input))
    except (TimeError, OSError, TypeError) as exc:
        stderr.write("input error: " + str(exc) + "\n")
        return 3
    stdout.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

## 2. request.json — synthetic maintenance request

```json
{"operation":"window","date":"2026-11-01","start":"01:00","end":"02:00","zone":"America/New_York","start_fold":0}
```

Expected result: 2026-11-01 01:00 EDT to 02:00 EST corresponds to **05:00Z–07:00Z**, a two-hour elapsed window despite one hour of wall-clock labels.

## 3. test_time_lab.py — 50 automated tests

```python
import io
import json
from pathlib import Path
import tempfile
import unittest
from time_lab import TimeError, parse_instant, zone, local_instant, iso, elapsed_seconds, window, next_daily, unique_pairs, load_request, execute, main, MAX_BYTES

NY="America/New_York"
class TimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"request.json"
        self.write({"operation":"elapsed","start":"2026-10-17T12:00:00Z","end":"2026-10-17T12:00:30Z"})
    def write(self, data): self.path.write_text(json.dumps(data), encoding="utf-8")
    def test_utc(self): self.assertEqual(iso(parse_instant("2026-10-17T12:00:00Z")),"2026-10-17T12:00:00Z")
    def test_offset(self): self.assertEqual(iso(parse_instant("2026-10-17T08:00:00-04:00")),"2026-10-17T12:00:00Z")
    def test_naive(self):
        with self.assertRaises(TimeError): parse_instant("2026-10-17T12:00:00")
    def test_invalid_date(self):
        with self.assertRaises(TimeError): parse_instant("2026-02-30T12:00:00Z")
    def test_invalid_type(self):
        with self.assertRaises(TimeError): parse_instant(123)
    def test_utc_zone(self): self.assertEqual(zone("UTC").key,"UTC")
    def test_bad_zone(self):
        with self.assertRaises(TimeError): zone("Mars/Colony")
    def test_zone_traversal(self):
        with self.assertRaises(TimeError): zone("../etc/passwd")
    def test_zone_type(self):
        with self.assertRaises(TimeError): zone(12)
    def test_spring_gap(self):
        with self.assertRaisesRegex(TimeError,"nonexistent"): local_instant("2026-03-08","02:30",NY)
    def test_fall_ambiguous(self):
        with self.assertRaisesRegex(TimeError,"ambiguous"): local_instant("2026-11-01","01:30",NY)
    def test_fall_first(self): self.assertEqual(iso(local_instant("2026-11-01","01:30",NY,0)),"2026-11-01T05:30:00Z")
    def test_fall_second(self): self.assertEqual(iso(local_instant("2026-11-01","01:30",NY,1)),"2026-11-01T06:30:00Z")
    def test_fall_difference(self): self.assertEqual((local_instant("2026-11-01","01:30",NY,1)-local_instant("2026-11-01","01:30",NY,0)).total_seconds(),3600)
    def test_fold_bool(self):
        with self.assertRaises(TimeError): local_instant("2026-11-01","01:30",NY,True)
    def test_fold_high(self):
        with self.assertRaises(TimeError): local_instant("2026-11-01","01:30",NY,2)
    def test_bad_clock(self):
        with self.assertRaises(TimeError): local_instant("2026-10-17","25:00",NY)
    def test_bad_day(self):
        with self.assertRaises(TimeError): local_instant("2026-02-30","12:00",NY)
    def test_regular_time(self): self.assertEqual(iso(local_instant("2026-10-17","09:00",NY)),"2026-10-17T13:00:00Z")
    def test_elapsed(self): self.assertEqual(elapsed_seconds("2026-10-17T12:00:00Z","2026-10-17T12:01:00Z"),60)
    def test_elapsed_negative(self):
        with self.assertRaises(TimeError): elapsed_seconds("2026-10-17T12:01:00Z","2026-10-17T12:00:00Z")
    def test_elapsed_zero(self): self.assertEqual(elapsed_seconds("2026-10-17T12:00:00Z","2026-10-17T12:00:00Z"),0)
    def test_elapsed_dst(self): self.assertEqual(elapsed_seconds("2026-11-01T05:30:00Z","2026-11-01T06:30:00Z"),3600)
    def test_window(self): self.assertEqual(window("2026-10-17","09:00","10:00",NY)["duration_seconds"],3600)
    def test_window_exclusive(self): self.assertTrue(window("2026-10-17","09:00","10:00",NY)["end_exclusive"])
    def test_window_zero(self):
        with self.assertRaises(TimeError): window("2026-10-17","09:00","09:00",NY)
    def test_window_reverse(self):
        with self.assertRaises(TimeError): window("2026-10-17","10:00","09:00",NY)
    def test_window_gap(self):
        with self.assertRaises(TimeError): window("2026-03-08","02:30","03:30",NY)
    def test_window_fold(self):
        with self.assertRaises(TimeError): window("2026-11-01","01:00","02:00",NY)
    def test_window_fold_explicit(self): self.assertEqual(window("2026-11-01","01:00","02:00",NY,0)["duration_seconds"],7200)
    def test_daily_same_day(self): self.assertEqual(next_daily("2026-10-17T12:00:00Z","09:00",NY)["next_utc"],"2026-10-17T13:00:00Z")
    def test_daily_next_day(self): self.assertEqual(next_daily("2026-10-17T14:00:00Z","09:00",NY)["next_utc"],"2026-10-18T13:00:00Z")
    def test_daily_strictly_after(self): self.assertEqual(next_daily("2026-10-17T13:00:00Z","09:00",NY)["next_utc"],"2026-10-18T13:00:00Z")
    def test_daily_gap(self):
        with self.assertRaises(TimeError): next_daily("2026-03-08T05:00:00Z","02:30",NY)
    def test_daily_ambiguous(self):
        with self.assertRaises(TimeError): next_daily("2026-11-01T04:00:00Z","01:30",NY)
    def test_daily_fold(self): self.assertEqual(next_daily("2026-11-01T04:00:00Z","01:30",NY,1)["next_utc"],"2026-11-01T06:30:00Z")
    def test_duplicate_keys(self):
        with self.assertRaises(TimeError): unique_pairs([("x",1),("x",2)])
    def test_load(self): self.assertEqual(load_request(self.path)["operation"],"elapsed")
    def test_load_missing(self):
        self.path.unlink()
        with self.assertRaises(TimeError): load_request(self.path)
    def test_load_large(self):
        self.path.write_bytes(b" "*(MAX_BYTES+1))
        with self.assertRaises(TimeError): load_request(self.path)
    def test_load_invalid(self):
        self.path.write_text("{bad")
        with self.assertRaises(TimeError): load_request(self.path)
    def test_load_nonobject(self):
        self.path.write_text("[]")
        with self.assertRaises(TimeError): load_request(self.path)
    def test_execute_elapsed(self): self.assertEqual(execute(load_request(self.path))["elapsed_seconds"],30)
    def test_execute_window(self): self.assertEqual(execute({"operation":"window","date":"2026-10-17","start":"09:00","end":"10:00","zone":NY})["duration_seconds"],3600)
    def test_execute_daily(self): self.assertIn("next_utc",execute({"operation":"next_daily","after":"2026-10-17T12:00:00Z","time":"09:00","zone":NY}))
    def test_execute_bad(self):
        with self.assertRaises(TimeError): execute({"operation":"delete"})
    def test_execute_unknown_key(self):
        with self.assertRaises(TimeError): execute({"operation":"elapsed","start":"x","end":"y","secret":"z"})
    def test_cli(self):
        out,err=io.StringIO(),io.StringIO()
        self.assertEqual(main(["--input",str(self.path)],out,err),0)
        self.assertEqual(json.loads(out.getvalue())["elapsed_seconds"],30)
    def test_cli_invalid(self):
        self.path.write_text("{bad")
        out,err=io.StringIO(),io.StringIO()
        self.assertEqual(main(["--input",str(self.path)],out,err),3)
        self.assertIn("input error",err.getvalue())
    def test_no_mutation(self):
        before=self.path.read_bytes()
        main(["--input",str(self.path)],io.StringIO(),io.StringIO())
        self.assertEqual(self.path.read_bytes(),before)

if __name__=="__main__": unittest.main()
```

## 4. Execute

Linux/macOS/WSL:

```bash
python3 -m unittest -v test_time_lab.py
python3 -m py_compile time_lab.py test_time_lab.py
python3 time_lab.py --input request.json
```

Windows PowerShell:

```powershell
py -3 -m unittest -v test_time_lab.py
py -3 time_lab.py --input request.json
```

If `ZoneInfoNotFoundError` occurs on Windows or a minimal container, install the `tzdata` Python package in the lab virtual environment, then rerun the tests.

## 5. Failure injection

1. Replace a timestamp with a naive timestamp: reject.
2. Schedule `2026-03-08 02:30` in New York: reject nonexistent time.
3. Schedule `2026-11-01 01:30` without fold: reject ambiguous time.
4. Compare fold 0 and fold 1: exactly one hour difference in UTC.
5. Reverse the maintenance window: reject.
6. Use an unknown IANA zone: reject.
7. Supply malformed JSON or duplicate keys: reject.
8. Supply a file larger than 64 KiB or invalid UTF-8: reject.
9. Compare elapsed UTC duration across DST transition.
10. Verify CLI does not mutate the request file.

## 6. Production runbooks

**DST incident:** suspend the actual scheduled job, inspect IANA zone and fold policy, choose an approved UTC instant and obtain change authorization.

**Clock skew:** inspect NTP synchronization and host time; use monotonic clocks for timeouts.

**Timezone database drift:** identify runtime and tzdata versions, test upcoming transitions and deploy consistently.

**Rollback:** restore the previous scheduler configuration; verify both UTC and operator-local times.

**Reliability warning:** this tool only calculates candidate times; it does not persist, execute or guarantee jobs.

## 7. Acceptance (100 points)

| Check | Points |
|---|---:|
| 50 automated tests pass | 30 |
| UTC and offset correctness | 20 |
| DST gap/fold handling | 20 |
| Half-open windows and daily recurrence | 15 |
| Failure injection and runbooks | 15 |

Target: **90/100**, with all safety tests passing. The published code and tests require execution in the learner's environment; no local execution is claimed here.
