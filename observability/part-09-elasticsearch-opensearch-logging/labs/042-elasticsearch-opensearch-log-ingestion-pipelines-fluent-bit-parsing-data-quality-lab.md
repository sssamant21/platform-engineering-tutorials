# Chapter 042 — Fluent Bit Log Ingestion, Parsing and Data Quality Lab

**Part 09 — Elasticsearch and OpenSearch Logging.** Use synthetic logs only.

## Offline validation

Copy `healthy.json`, `pipeline_gate.py` and `test_pipeline_gate.py` from [Chapter 042](../042-elasticsearch-opensearch-log-ingestion-pipelines-fluent-bit-parsing-data-quality.md) into `chapter042/`. Execute:

```bash
cd chapter042
python3 pipeline_gate.py healthy.json
python3 -m unittest -v test_pipeline_gate.py
```

Expected: PASS and 26 tests.

## Optional staging ingestion

1. Choose Elasticsearch **or** OpenSearch; record exact versions.
2. Use the chapter's Fluent Bit file input and stdout output with synthetic JSON lines.
3. Validate timestamp parsing, severity normalization and multiline behavior.
4. Create and simulate the version-compatible ingest pipeline.
5. Configure a TLS-authenticated output in approved staging.
6. Send bulk NDJSON and inspect every item response.
7. Simulate transient 429 and nonretryable mapping failures.
8. Confirm bounded retries, protected DLQ and idempotent replay.
9. Revert the pipeline and verify new writes.

## Twelve negative drills

1. Missing owner.
2. Missing source.
3. Missing destination.
4. No redaction verification.
5. No TLS review.
6. No least-privilege review.
7. No retry review.
8. No DLQ replay test.
9. Event size exceeds limit.
10. Queue exceeds capacity.
11. Parse failures exceed budget.
12. Unsafe schema field.

## DBRE incident exercise

Simulate elevated application logs during PostgreSQL query slowness. Diagnose parser errors, bulk partial rejections, ingest pipeline latency and storage saturation. Use staged rollback and DLQ replay without deleting logs.

## Evidence

```text
UTC / operator / environment:
Source and parser validation:
Bulk per-item response:
Retry and DLQ evidence:
Privacy and TLS checks:
Offline gate / 26 tests:
12 drills / rollback / reviewer:
```

Offline governance tests alone do not validate live ingestion.
