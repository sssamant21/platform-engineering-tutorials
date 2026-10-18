# Chapter 053 — Grafana Tempo Object Storage, TraceQL and Query Operations Lab

**Part 11 — Distributed Tracing with Jaeger and Tempo.**

## Offline acceptance

Copy `healthy.json`, `tempo_gate.py` and `test_tempo_gate.py` from [Chapter 053](../053-grafana-tempo-deployment-object-storage-traceql-query-operations.md):

```bash
cd chapter053
python3 tempo_gate.py healthy.json
python3 -m unittest -v test_tempo_gate.py
```

Expected PASS and 25 authored tests.

## Staging Tempo integration

1. Pin Tempo and Grafana versions.
2. Validate a single-binary disposable local config.
3. Generate synthetic OTLP traces.
4. Query by trace ID in Grafana.
5. Execute service-name, error and latency TraceQL filters.
6. Verify object-storage permissions and block persistence in staging.
7. Inspect compactor and WAL state.
8. Measure query p95 and ingest success.
9. Simulate object-store read/write failure.
10. Restore approved configuration and verify trace retrieval.

## Twelve negative drills

1. Invalid object storage backend.
2. Empty bucket name.
3. Retention disabled.
4. Retention exceeds review limit.
5. Query latency above budget.
6. Ingest success below threshold.
7. TraceQL query untested.
8. Object storage read untested.
9. Object storage write untested.
10. Tenant isolation unreviewed.
11. Privacy redaction unreviewed.
12. Rollback untested.

## Evidence

```text
UTC / operator / Tempo version:
OTLP ingestion / trace ID:
TraceQL result / query latency:
Object storage read/write / WAL / compaction:
Retention / tenancy / TLS:
Restore / rollback:
Offline gate / 25 tests:
Reviewer / change ID:
```

Offline checks cannot prove Tempo operational readiness.
