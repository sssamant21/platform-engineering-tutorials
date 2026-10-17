# Chapter 042 — File Formats, CSV, JSON and Structured Data Processing

**Part 05 — Files, Exceptions, Logging and Configuration | Python 3.10+**

## Outcomes

Parse and validate CSV, JSON, and JSON Lines operational exports; enforce explicit schemas and metric units; normalize heterogeneous telemetry; produce deterministic, privacy-conscious reports; implement streaming input and atomic output; test data-quality failure modes.

## 1. Why formats matter in SRE/DBRE

PostgreSQL query/replication exports, Elasticsearch slow-log extracts, Kafka consumer-lag snapshots, Kubernetes events and cloud cost reports frequently arrive as CSV or JSON. Correct parsing is an operational safety control: a malformed value, unknown unit, or silently dropped row can turn an incident report into misinformation.

## 2. CSV semantics

Use `csv.DictReader` with `newline=""` and `encoding="utf-8-sig"` when accepting optional UTF-8 BOM. CSV has no intrinsic types: values arrive as strings and require explicit conversion. Check required headers, duplicates, extra columns, missing values and line counts. Never assume `split(",")` handles quoted commas.

```python
import csv
with open("telemetry.csv", newline="", encoding="utf-8-sig") as source:
    reader = csv.DictReader(source)
    for row in reader:
        print(row["service"], row["value"])
```

For spreadsheet exports, formula injection is a risk: prefix dangerous cells beginning with `=`, `+`, `-`, `@` when the output is destined for Excel-like software, and document the chosen escaping policy. The lab outputs JSON only.

## 3. JSON and JSONL

`json.load` materializes an entire document. JSON Lines supports incremental processing of one object per line. Reject NaN/Infinity via `parse_constant`; Python's default decoder accepts them despite strict JSON forbidding them. Limit line sizes and file sizes, reject duplicate JSON keys when data integrity matters, and validate schema after parsing.

```python
def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result
```

## 4. Schema contracts

The lab normalizes each record to:

```json
{"service":"pg-replica","kind":"postgresql_lag","unit":"seconds","value":45}
```

Required keys must match exactly. Numeric values must be finite, nonnegative and not booleans. Valid kinds/units are PostgreSQL lag in seconds, Elasticsearch latency in milliseconds and Kafka lag in messages. Synthetic warning/critical thresholds are not universal SLO recommendations.

## 5. Data quality gates

- **Completeness:** reject missing columns, fields and empty required values.
- **Uniqueness:** reject duplicate JSON object keys; allow repeated telemetry samples by design.
- **Validity:** reject unknown metrics, units, NaN, infinity, negative values and malformed rows.
- **Consistency:** normalize CSV strings and JSON numeric types to one canonical model.
- **Freshness:** real systems must verify observation timestamps and sampling gaps; the lab uses untimestamped synthetic records.
- **Volume:** cap record sizes and output preview; do not load an entire export unnecessarily.

## 6. Architecture

```text
CSV / JSONL / bounded JSON
        |
   strict decoder
        |
   schema validation
        |
 normalized Observation
        |
 one-pass severity counters
        |
 deterministic JSON report
```

A format adapter yields observations. A common classifier and report builder make behavior independent of input encoding.

## 7. Operational scenarios

| Input | Example | Risk |
|---|---|---|
| CSV | PostgreSQL replication export | Quoted values and missing columns |
| JSONL | Elasticsearch latency events | Corrupt line halfway through |
| JSON array | Kafka lag snapshot | Oversized document and duplicate keys |
| Mixed source | Daily datastore inventory | Unit mismatch |
| Spreadsheet CSV | Incident evidence | Formula injection on export |

## 8. Troubleshooting

| Symptom | Likely cause | Mitigation |
|---|---|---|
| Unexpected column count | Quoting or delimiter issue | Use `csv.DictReader`, reject extras |
| Invalid numeric value | Empty, NaN, bool, negative | Strict conversion |
| Silent JSON overwrite | Duplicate key | `object_pairs_hook` rejection |
| Wrong severity | Incorrect unit | Enforce kind/unit contract |
| Memory growth | Full-file materialization | Prefer JSONL or CSV streaming |
| Encoding failure | BOM or non-UTF-8 | Specify encoding; reject invalid bytes |
| Truncated report | Output written before validation | Complete validation before publishing |
| Sensitive fields leak | Unreviewed schema | Allowlist fields only |

## 9. Production runbooks

**Schema drift:** halt report publication, identify safe row/line number, compare producer contract, fix parser or upstream data, replay sanitized fixture.

**Data quality incident:** preserve counts and rejected reasons without sensitive payloads; determine whether a bad sample is isolated or systematic; do not silently skip bad records.

**Memory pressure:** inspect eager parsing and retained rows; use JSONL/CSV streaming, line-size limits, capped preview and bounded counters.

**CSV formula risk:** ensure any future CSV export applies a reviewed spreadsheet-cell escaping policy, and test with leading `=`, `+`, `-`, `@` values.

**Release:** run tests, review schema version, sample representative sanitized exports, pin dependency versions, and verify rollback.

## 10. Hands-on lab

[Chapter 042 — Structured SRE/DBRE Telemetry Ingestion Lab](labs/042-structured-sre-dbre-telemetry-ingestion-lab.md) provides executable Python, CSV/JSON/JSONL fixtures, automated tests, failure injection, CLI and production runbooks.

**Next: Chapter 043 — Python Exceptions, Custom Errors and Resilient Failure Handling.**
