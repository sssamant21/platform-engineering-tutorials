# Chapter 047 — Regex-Based Operational Log Parser and SRE/DBRE Lab

**Python 3.10+ | Standard library | Offline and read-only**

## Goal

Parse synthetic PostgreSQL, Elasticsearch, Kafka and Redis log lines into validated JSON; reject malformed records, verify units and severity, and demonstrate bounded regex parsing. The program does not access live services.

## Project layout
```text
ch047/
  operational_parser.py
  test_operational_parser.py
  sample.log
```

## 1. operational_parser.py

```python
"""Strict synthetic SRE/DBRE log parser. Python 3.10+."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys

MAX_LINE = 512
MAX_FILE = 1048576
POLICY = {
    "postgresql": ("replication_lag", "seconds", 30.0, 120.0),
    "elasticsearch": ("search_latency", "milliseconds", 200.0, 500.0),
    "kafka": ("consumer_lag", "messages", 1000.0, 10000.0),
    "redis": ("latency", "milliseconds", 50.0, 150.0),
}
PATTERN = re.compile(
    r"(?P<timestamp>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z)"
    r" service=(?P<service>[A-Za-z][A-Za-z0-9_-]{0,63})"
    r" engine=(?P<engine>[a-z]+)"
    r" metric=(?P<metric>[a-z_]+)"
    r" value=(?P<value>[0-9]+(?:\.[0-9]+)?)"
    r" unit=(?P<unit>[a-z]+)"
    r" status=(?P<status>healthy|warning|critical)"
)

class ParseError(ValueError):
    pass

def severity(engine, value):
    _, _, warning, critical = POLICY[engine]
    return "critical" if value >= critical else "warning" if value >= warning else "healthy"

def parse_line(line):
    if not isinstance(line, str) or len(line) > MAX_LINE:
        raise ParseError("line too long or not text")
    match = PATTERN.fullmatch(line.rstrip("\r\n"))
    if match is None:
        raise ParseError("record does not match schema")
    row = match.groupdict()
    try:
        stamp = datetime.strptime(row["timestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ParseError("invalid UTC timestamp") from exc
    engine = row["engine"]
    if engine not in POLICY:
        raise ParseError("unknown engine")
    metric, unit, _, _ = POLICY[engine]
    if row["metric"] != metric or row["unit"] != unit:
        raise ParseError("metric/unit mismatch")
    try:
        value = float(row["value"])
    except (ValueError, OverflowError) as exc:
        raise ParseError("invalid numeric value") from exc
    if not math.isfinite(value):
        raise ParseError("nonfinite value")
    if row["status"] != severity(engine, value):
        raise ParseError("status does not match metric threshold")
    return {"timestamp": stamp.isoformat().replace("+00:00", "Z"),
            "service": row["service"], "engine": engine,
            "metric": metric, "value": value, "unit": unit, "status": row["status"]}

def parse_file(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ParseError("expected regular non-symlink file")
    if path.stat().st_size > MAX_FILE:
        raise ParseError("input file too large")
    with path.open("rb") as handle:
        raw = handle.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise ParseError("input file too large")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise ParseError("invalid UTF-8") from exc
    results = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            results.append(parse_line(line))
        except ParseError as exc:
            raise ParseError(f"line {line_number}: {exc}") from exc
    return results

def summarize(rows):
    ordered = sorted(rows, key=lambda r: (r["timestamp"], r["engine"], r["service"]))
    counts = {level: sum(row["status"] == level for row in ordered)
              for level in ("healthy", "warning", "critical")}
    return {"schema_version": 1, "dry_run": True, "total": len(ordered),
            "counts": counts, "results": ordered}

def main(argv=None, stdout=None, stderr=None):
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    parser = argparse.ArgumentParser(description="Offline synthetic operational log parser")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = summarize(parse_file(args.input))
    except (ParseError, OSError) as exc:
        stderr.write(f"input error: {exc}\n")
        return 3
    stdout.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
    return 2 if result["counts"]["critical"] else 1 if result["counts"]["warning"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
```

## 2. sample.log

```text
2026-10-17T12:00:00Z service=pg-replica engine=postgresql metric=replication_lag value=5 unit=seconds status=healthy
2026-10-17T12:01:00Z service=pg-replica engine=postgresql metric=replication_lag value=45 unit=seconds status=warning
2026-10-17T12:02:00Z service=search-api engine=elasticsearch metric=search_latency value=650 unit=milliseconds status=critical
2026-10-17T12:03:00Z service=kafka-worker engine=kafka metric=consumer_lag value=10000 unit=messages status=critical
2026-10-17T12:04:00Z service=redis-cache engine=redis metric=latency value=20 unit=milliseconds status=healthy
```

## 3. test_operational_parser.py — 50 automated tests

```python
import io
import json
from pathlib import Path
import tempfile
import unittest
from operational_parser import PATTERN, MAX_LINE, MAX_FILE, ParseError, POLICY, parse_line, parse_file, severity, summarize, main

BASE="2026-10-17T12:00:00Z service=pg-replica engine=postgresql metric=replication_lag value=5 unit=seconds status=healthy"

class ParserTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"events.log"
        self.path.write_text(BASE+"\n", encoding="utf-8")
    def check_invalid(self,line):
        with self.assertRaises(ParseError): parse_line(line)
    def test_pattern_compiled(self): self.assertIsNotNone(PATTERN.fullmatch(BASE))
    def test_parse(self): self.assertEqual(parse_line(BASE)["service"],"pg-replica")
    def test_timestamp(self): self.assertEqual(parse_line(BASE)["timestamp"],"2026-10-17T12:00:00Z")
    def test_value(self): self.assertEqual(parse_line(BASE)["value"],5.0)
    def test_status(self): self.assertEqual(parse_line(BASE)["status"],"healthy")
    def test_metric(self): self.assertEqual(parse_line(BASE)["metric"],"replication_lag")
    def test_engine(self): self.assertEqual(parse_line(BASE)["engine"],"postgresql")
    def test_unit(self): self.assertEqual(parse_line(BASE)["unit"],"seconds")
    def test_newline(self): self.assertEqual(parse_line(BASE+"\n")["service"],"pg-replica")
    def test_crlf(self): self.assertEqual(parse_line(BASE+"\r\n")["service"],"pg-replica")
    def test_nonstring(self): self.check_invalid(None)
    def test_oversize_line(self): self.check_invalid("x"*(MAX_LINE+1))
    def test_prefix(self): self.check_invalid("prefix "+BASE)
    def test_suffix(self): self.check_invalid(BASE+" suffix")
    def test_unknown_engine(self): self.check_invalid(BASE.replace("postgresql","mysql"))
    def test_wrong_metric(self): self.check_invalid(BASE.replace("replication_lag","latency"))
    def test_wrong_unit(self): self.check_invalid(BASE.replace("seconds","milliseconds"))
    def test_wrong_status(self): self.check_invalid(BASE.replace("healthy","critical"))
    def test_negative(self): self.check_invalid(BASE.replace("value=5","value=-5"))
    def test_nan(self): self.check_invalid(BASE.replace("value=5","value=NaN"))
    def test_infinity(self): self.check_invalid(BASE.replace("value=5","value=Infinity"))
    def test_bad_date(self): self.check_invalid(BASE.replace("2026-10-17","2026-02-30"))
    def test_bad_hour(self): self.check_invalid(BASE.replace("T12:","T25:"))
    def test_bad_service(self): self.check_invalid(BASE.replace("pg-replica","=SUM(1)"))
    def test_empty_service(self): self.check_invalid(BASE.replace("pg-replica",""))
    def test_unicode_digits(self): self.check_invalid(BASE.replace("value=5","value=５"))
    def test_space(self): self.check_invalid(BASE.replace(" service=","  service="))
    def test_pg_warning(self): self.assertEqual(severity("postgresql",30),"warning")
    def test_pg_critical(self): self.assertEqual(severity("postgresql",120),"critical")
    def test_es_warning(self): self.assertEqual(severity("elasticsearch",200),"warning")
    def test_es_critical(self): self.assertEqual(severity("elasticsearch",500),"critical")
    def test_kafka_warning(self): self.assertEqual(severity("kafka",1000),"warning")
    def test_kafka_critical(self): self.assertEqual(severity("kafka",10000),"critical")
    def test_redis_warning(self): self.assertEqual(severity("redis",50),"warning")
    def test_redis_critical(self): self.assertEqual(severity("redis",150),"critical")
    def test_file(self): self.assertEqual(len(parse_file(self.path)),1)
    def test_blank_lines(self):
        self.path.write_text("\n"+BASE+"\n\n")
        self.assertEqual(len(parse_file(self.path)),1)
    def test_invalid_second_line(self):
        self.path.write_text(BASE+"\nBAD\n")
        with self.assertRaisesRegex(ParseError,"line 2"): parse_file(self.path)
    def test_missing_file(self):
        self.path.unlink()
        with self.assertRaises(ParseError): parse_file(self.path)
    def test_invalid_utf8(self):
        self.path.write_bytes(b"\xff")
        with self.assertRaises(ParseError): parse_file(self.path)
    def test_large_file(self):
        self.path.write_bytes(b"x"*(MAX_FILE+1))
        with self.assertRaises(ParseError): parse_file(self.path)
    def test_symlink(self):
        link=self.path.parent/"link.log"
        try: link.symlink_to(self.path)
        except OSError: self.skipTest("symlink unavailable")
        with self.assertRaises(ParseError): parse_file(link)
    def test_summary(self): self.assertEqual(summarize([parse_line(BASE)])["counts"]["healthy"],1)
    def test_summary_empty(self): self.assertEqual(summarize([])["total"],0)
    def test_summary_dry_run(self): self.assertTrue(summarize([])["dry_run"])
    def test_cli_healthy(self):
        out,err=io.StringIO(),io.StringIO()
        self.assertEqual(main(["--input",str(self.path)],out,err),0)
    def test_cli_warning(self):
        self.path.write_text(BASE.replace("value=5","value=45").replace("status=healthy","status=warning"))
        self.assertEqual(main(["--input",str(self.path)],io.StringIO(),io.StringIO()),1)
    def test_cli_critical(self):
        self.path.write_text(BASE.replace("value=5","value=120").replace("status=healthy","status=critical"))
        self.assertEqual(main(["--input",str(self.path)],io.StringIO(),io.StringIO()),2)
    def test_cli_invalid(self):
        self.path.write_text("BAD")
        out,err=io.StringIO(),io.StringIO()
        self.assertEqual(main(["--input",str(self.path)],out,err),3)
        self.assertIn("line 1",err.getvalue())
    def test_cli_json(self):
        out=io.StringIO()
        main(["--input",str(self.path)],out,io.StringIO())
        self.assertEqual(json.loads(out.getvalue())["total"],1)

if __name__=="__main__": unittest.main()
```

## 4. Execute

Linux/macOS/WSL:
```bash
python3 -m unittest -v test_operational_parser.py
python3 -m py_compile operational_parser.py test_operational_parser.py
python3 operational_parser.py --input sample.log
```

Windows PowerShell:
```powershell
py -3 -m unittest -v test_operational_parser.py
py -3 operational_parser.py --input sample.log
```

Expected: 5 records, healthy 2, warning 1, critical 2. CLI exits 2 for a critical result; default argparse also exits 2 for usage errors, so production automation should use distinct exit codes or inspect structured output and stderr.

## 5. Failure injection

1. Insert a malformed second line: fail with line number.
2. Change a PostgreSQL metric to Elasticsearch units: reject.
3. Insert NaN, Infinity or negative values: reject.
4. Change the status to disagree with the threshold: reject.
5. Insert a nonexistent calendar date: reject.
6. Add a prefix or suffix: `fullmatch` must reject.
7. Insert Unicode digits where ASCII is required: reject.
8. Supply a line exceeding 512 characters or file exceeding 1 MiB.
9. Supply malformed UTF-8 or a symlink path.
10. Compare severity boundary values for all four datastore engines.

## 6. Troubleshooting and production runbooks

**Schema drift:** stop ingestion, inspect sanitized line number and producer version, update tests before parser rollout.

**Regex CPU issue:** cap input and avoid nested quantifiers; prefer structured logs or deterministic tokenization.

**Severity mismatch:** verify units and threshold provenance; these synthetic thresholds must not be used as real alert policies.

**Data exposure:** do not print raw rejected records or unredacted secrets.

**Rollback:** pin last known-good parser, replay fixtures and verify dashboards before production rollout.

## 7. Acceptance (100 points)

| Check | Points |
|---|---:|
| Automated test suite passes | 30 |
| Strict regex and schema validation | 20 |
| Correct datastore classification | 15 |
| Input size/encoding safety | 15 |
| Failure-injection evidence | 10 |
| Troubleshooting and rollback runbooks | 10 |

Target: 90/100 with all safety checks passing. **Tests are published for learner execution; no execution result is claimed here.**
