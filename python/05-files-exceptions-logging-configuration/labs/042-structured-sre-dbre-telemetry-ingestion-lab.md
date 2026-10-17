# Chapter 042 — Structured SRE/DBRE Telemetry Ingestion Lab

**Python 3.10+ | Standard library | Offline, synthetic, read-only**

## Goal

Implement a unified, strictly validated CSV/JSON/JSONL ingestion pipeline that produces deterministic datastore health reports. Input is synthetic; no network access, credentials or infrastructure changes.

## Project layout

```text
ch042/
  ingest.py
  cli.py
  telemetry.csv
  telemetry.json
  telemetry.jsonl
  test_ingest.py
```

## 1. ingest.py

```python
"""Strict streaming CSV/JSON/JSONL ingestion for synthetic SRE telemetry."""
import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path

MAX_LINE = 4096
MAX_JSON_BYTES = 1024 * 1024
MAX_PREVIEW = 10
SCHEMA = ("service", "kind", "unit", "value")
POLICIES = {
    "postgresql_lag": ("seconds", 30.0, 120.0),
    "elasticsearch_latency": ("milliseconds", 200.0, 500.0),
    "kafka_lag": ("messages", 1000.0, 10000.0),
}


class DataQualityError(ValueError):
    pass


def unique_pairs(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise DataQualityError("duplicate JSON key")
        output[key] = value
    return output


def strict_json(text):
    try:
        return json.loads(
            text,
            object_pairs_hook=unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(DataQualityError("nonfinite JSON number")),
        )
    except json.JSONDecodeError as exc:
        raise DataQualityError("malformed JSON") from exc


def number(value):
    if isinstance(value, bool):
        raise DataQualityError("boolean is not a metric")
    if isinstance(value, str):
        if not value.strip():
            raise DataQualityError("empty numeric field")
        try:
            value = float(value)
        except ValueError as exc:
            raise DataQualityError("invalid numeric field") from exc
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise DataQualityError("metric must be finite and nonnegative")
    return float(value)


@dataclass(frozen=True, slots=True)
class Observation:
    service: str
    kind: str
    unit: str
    value: float


def normalize(row):
    if not isinstance(row, dict) or set(row) != set(SCHEMA):
        raise DataQualityError("invalid record schema")
    service, kind, unit = row["service"], row["kind"], row["unit"]
    if not isinstance(service, str) or not service.strip() or len(service) > 64:
        raise DataQualityError("invalid service")
    if not isinstance(kind, str) or kind not in POLICIES:
        raise DataQualityError("unknown metric kind")
    if unit != POLICIES[kind][0]:
        raise DataQualityError("invalid metric unit")
    return Observation(service, kind, unit, number(row["value"]))


def from_csv(handle):
    reader = csv.DictReader(handle, strict=True)
    if reader.fieldnames is None or tuple(reader.fieldnames) != SCHEMA:
        raise DataQualityError("invalid CSV header")
    for line, row in enumerate(reader, 2):
        if any(value is None for value in row.values()) or None in row:
            raise DataQualityError(f"CSV record {line}: missing or extra columns")
        yield normalize(row)


def from_jsonl(handle):
    for line, raw in enumerate(handle, 1):
        if len(raw) > MAX_LINE:
            raise DataQualityError(f"JSONL line {line}: oversized")
        if raw.strip():
            yield normalize(strict_json(raw))


def from_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_JSON_BYTES:
        raise DataQualityError("JSON document too large")
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = handle.read(MAX_JSON_BYTES + 1)
    if len(payload.encode("utf-8")) > MAX_JSON_BYTES:
        raise DataQualityError("JSON document too large")
    rows = strict_json(payload)
    if not isinstance(rows, list):
        raise DataQualityError("JSON document must be an array")
    for row in rows:
        yield normalize(row)


def classify(item):
    _, warning, critical = POLICIES[item.kind]
    return "critical" if item.value >= critical else "warning" if item.value >= warning else "healthy"


def summarize(items, preview_limit=5):
    if isinstance(preview_limit, bool) or not isinstance(preview_limit, int) or not 0 <= preview_limit <= MAX_PREVIEW:
        raise DataQualityError("invalid preview limit")
    counts = {"healthy": 0, "warning": 0, "critical": 0}
    preview = []
    total = 0
    for item in items:
        status = classify(item)
        counts[status] += 1
        total += 1
        if status != "healthy" and len(preview) < preview_limit:
            preview.append({"service": item.service, "kind": item.kind, "unit": item.unit, "value": item.value, "status": status})
    return {"schema_version": 1, "total": total, "counts": counts, "preview": preview}


def run(path, fmt, preview_limit=5):
    if fmt not in ("csv", "json", "jsonl"):
        raise DataQualityError("unsupported input format")
    if fmt == "json":
        return summarize(from_json(path), preview_limit)
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        items = from_csv(handle) if fmt == "csv" else from_jsonl(handle)
        return summarize(items, preview_limit)
```

## 2. cli.py

```python
import argparse
import json
from pathlib import Path
from ingest import DataQualityError, run


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline structured telemetry ingestion")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--format", choices=("csv", "json", "jsonl"), required=True)
    parser.add_argument("--preview", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        report = run(args.input, args.format, args.preview)
    except (OSError, UnicodeError, DataQualityError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 3. telemetry.csv

```csv
service,kind,unit,value
pg-replica,postgresql_lag,seconds,5
pg-replica,postgresql_lag,seconds,45
search-api,elasticsearch_latency,milliseconds,650
consumer-a,kafka_lag,messages,100
consumer-a,kafka_lag,messages,10000
```

## 4. telemetry.json

```json
[
  {"service":"pg-replica","kind":"postgresql_lag","unit":"seconds","value":5},
  {"service":"pg-replica","kind":"postgresql_lag","unit":"seconds","value":45},
  {"service":"search-api","kind":"elasticsearch_latency","unit":"milliseconds","value":650},
  {"service":"consumer-a","kind":"kafka_lag","unit":"messages","value":100},
  {"service":"consumer-a","kind":"kafka_lag","unit":"messages","value":10000}
]
```

## 5. telemetry.jsonl

```jsonl
{"service":"pg-replica","kind":"postgresql_lag","unit":"seconds","value":5}
{"service":"pg-replica","kind":"postgresql_lag","unit":"seconds","value":45}
{"service":"search-api","kind":"elasticsearch_latency","unit":"milliseconds","value":650}
{"service":"consumer-a","kind":"kafka_lag","unit":"messages","value":100}
{"service":"consumer-a","kind":"kafka_lag","unit":"messages","value":10000}
```

## 6. test_ingest.py — automated tests

```python
import io
import json
from pathlib import Path
import tempfile
import unittest
from ingest import (
    DataQualityError, Observation, normalize, number, unique_pairs,
    strict_json, from_csv, from_jsonl, from_json, classify, summarize, run, MAX_LINE,
)
from cli import main


def row(**changes):
    result={"service":"pg","kind":"postgresql_lag","unit":"seconds","value":1}
    result.update(changes)
    return result


class IngestTests(unittest.TestCase):
    def test_normalize(self): self.assertEqual(normalize(row()).value,1.0)
    def test_number_string(self): self.assertEqual(number("12.5"),12.5)
    def test_number_empty(self):
        with self.assertRaises(DataQualityError): number("")
    def test_number_bool(self):
        with self.assertRaises(DataQualityError): number(True)
    def test_number_negative(self):
        with self.assertRaises(DataQualityError): number(-1)
    def test_number_nan(self):
        with self.assertRaises(DataQualityError): number(float("nan"))
    def test_number_inf(self):
        with self.assertRaises(DataQualityError): number(float("inf"))
    def test_unknown_kind(self):
        with self.assertRaises(DataQualityError): normalize(row(kind="unknown"))
    def test_wrong_unit(self):
        with self.assertRaises(DataQualityError): normalize(row(unit="milliseconds"))
    def test_missing_field(self):
        value=row(); del value["value"]
        with self.assertRaises(DataQualityError): normalize(value)
    def test_extra_field(self):
        with self.assertRaises(DataQualityError): normalize(row(secret="x"))
    def test_bad_service(self):
        with self.assertRaises(DataQualityError): normalize(row(service=""))
    def test_duplicate_key(self):
        with self.assertRaises(DataQualityError): strict_json('{"x":1,"x":2}')
    def test_bad_json(self):
        with self.assertRaises(DataQualityError): strict_json("{bad")
    def test_json_nan(self):
        with self.assertRaises(DataQualityError): strict_json('{"x":NaN}')
    def test_json_infinity(self):
        with self.assertRaises(DataQualityError): strict_json('{"x":Infinity}')
    def test_csv(self):
        source=io.StringIO("service,kind,unit,value\npg,postgresql_lag,seconds,30\n")
        self.assertEqual(len(list(from_csv(source))),1)
    def test_csv_header(self):
        with self.assertRaises(DataQualityError): list(from_csv(io.StringIO("wrong,value\nx,1\n")))
    def test_csv_extra(self):
        with self.assertRaises(DataQualityError): list(from_csv(io.StringIO("service,kind,unit,value\npg,postgresql_lag,seconds,1,extra\n")))
    def test_csv_missing(self):
        with self.assertRaises(DataQualityError): list(from_csv(io.StringIO("service,kind,unit,value\npg,postgresql_lag,seconds\n")))
    def test_csv_quoted(self):
        source=io.StringIO('service,kind,unit,value\n"pg,cluster",postgresql_lag,seconds,1\n')
        self.assertEqual(next(from_csv(source)).service,"pg,cluster")
    def test_jsonl(self):
        self.assertEqual(len(list(from_jsonl([json.dumps(row())+"\n"]))),1)
    def test_jsonl_blank(self):
        self.assertEqual(len(list(from_jsonl(["\n",json.dumps(row())]))),1)
    def test_jsonl_large(self):
        with self.assertRaises(DataQualityError): list(from_jsonl(["x"*(MAX_LINE+1)]))
    def test_pg_warning(self): self.assertEqual(classify(normalize(row(value=30))),"warning")
    def test_pg_critical(self): self.assertEqual(classify(normalize(row(value=120))),"critical")
    def test_es_critical(self): self.assertEqual(classify(normalize(row(kind="elasticsearch_latency",unit="milliseconds",value=500))),"critical")
    def test_kafka_warning(self): self.assertEqual(classify(normalize(row(kind="kafka_lag",unit="messages",value=1000))),"warning")
    def test_summary(self):
        result=summarize([normalize(row(value=1)),normalize(row(value=30)),normalize(row(value=120))])
        self.assertEqual(result["counts"],{"healthy":1,"warning":1,"critical":1})
    def test_preview_limit(self):
        result=summarize([normalize(row(value=120))]*20,2)
        self.assertEqual(len(result["preview"]),2)
    def test_invalid_preview(self):
        with self.assertRaises(DataQualityError): summarize([],11)
    def test_json_array(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"sample.json"; path.write_text(json.dumps([row()]),encoding="utf-8")
            self.assertEqual(len(list(from_json(path))),1)
    def test_json_not_array(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"sample.json"; path.write_text(json.dumps(row()),encoding="utf-8")
            with self.assertRaises(DataQualityError): list(from_json(path))
    def test_csv_run(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"sample.csv"; path.write_text("service,kind,unit,value\npg,postgresql_lag,seconds,1\n",encoding="utf-8")
            self.assertEqual(run(path,"csv")["total"],1)
    def test_jsonl_run(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"sample.jsonl"; path.write_text(json.dumps(row())+"\n",encoding="utf-8")
            self.assertEqual(run(path,"jsonl")["total"],1)
    def test_unsupported_format(self):
        with self.assertRaises(DataQualityError): run("x","xml")
    def test_cli_bad_format(self):
        with self.assertRaises(SystemExit): main(["--input","x","--format","xml"])
    def test_jsonl_malformed_after_valid(self):
        with self.assertRaises(DataQualityError): summarize(from_jsonl([json.dumps(row()),"{bad"]))
    def test_jsonl_boolean_value(self):
        with self.assertRaises(DataQualityError): list(from_jsonl([json.dumps(row(value=True))]))


if __name__ == "__main__":
    unittest.main()
```

## 7. Run

Linux/macOS/WSL:

```bash
python3 -m venv .venv
./.venv/bin/python -m unittest -v test_ingest.py
./.venv/bin/python cli.py --input telemetry.csv --format csv
./.venv/bin/python cli.py --input telemetry.json --format json
./.venv/bin/python cli.py --input telemetry.jsonl --format jsonl
./.venv/bin/python -m py_compile ingest.py cli.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m unittest -v test_ingest.py
.\.venv\Scripts\python.exe cli.py --input telemetry.csv --format csv
.\.venv\Scripts\python.exe cli.py --input telemetry.json --format json
.\.venv\Scripts\python.exe cli.py --input telemetry.jsonl --format jsonl
```

Expected for each format: 5 records, healthy 2, warning 1, critical 2.

## 8. Failure injection

1. Remove the CSV `value` column.
2. Append an extra CSV field.
3. Add duplicate JSON object keys.
4. Add NaN/Infinity, negative or boolean values.
5. Change a PostgreSQL metric unit to milliseconds.
6. Insert a malformed JSONL record after a valid record.
7. Create a JSONL line larger than 4,096 characters.
8. Request preview limit 11.
9. Use a JSON document instead of an array.
10. Compare reports across all three input formats.

## 9. Production runbooks

**Schema drift:** fail closed, inspect safe line number and schema contract, update producer or parser, replay sanitized fixtures.

**Data quality degradation:** capture rejection counts without exposing sensitive payloads, investigate unit and numeric conversion, do not silently skip rows.

**High memory:** prefer CSV/JSONL streaming, cap line sizes and preview, use bounded JSON document limits.

**Deployment rollback:** restore previous parser, verify fixture compatibility, and require data-owner signoff before using real exports.

## 10. Acceptance

- [ ] All automated tests pass locally.
- [ ] CSV, JSON and JSONL yield equivalent counts.
- [ ] Duplicate JSON keys and invalid numeric values are rejected.
- [ ] Unit and schema validation are enforced.
- [ ] Bounded preview and JSONL line-size checks work.
- [ ] No real infrastructure is accessed or modified.

**Execution status:** Tests are published but local execution is required.
