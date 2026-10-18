# Chapter 045 — Elasticsearch/OpenSearch Production Logging Capstone Lab

**Part 09 final capstone.** Use synthetic data and an approved staging cluster only.

## Offline gate

Copy `healthy.json`, `capstone_gate.py` and `test_capstone_gate.py` from [Chapter 045](../045-elasticsearch-opensearch-production-logging-reliability-security-troubleshooting-capstone.md) into `chapter045/`:

```bash
cd chapter045
python3 capstone_gate.py healthy.json
python3 -m unittest -v test_capstone_gate.py
```

Expected PASS and 30 tests.

## Staging integration

1. Pin Elasticsearch **or** OpenSearch version.
2. Ingest synthetic Kubernetes/application/PostgreSQL logs.
3. Test TLS, RBAC and redaction using fake secrets.
4. Inspect per-item bulk responses, retries and protected DLQ.
5. Verify template/mapping and shard-size policy.
6. Measure query p95 and storage/merge pressure.
7. Inspect ILM or ISM lifecycle and approved retention.
8. Restore a disposable snapshot and measure RPO/RTO.
9. Execute synthetic incident drill and versioned rollback.

## Twelve negative drills

1. Missing data owner approval.
2. Missing privacy validation.
3. TLS or RBAC untested.
4. Bulk 429 without backoff.
5. Bulk mapping 400.
6. DLQ replay untested.
7. Shard exceeds 50 GB.
8. Query p95 exceeds budget.
9. Lifecycle policy stuck.
10. Retention approval missing.
11. Snapshot restore fails.
12. Rollback not validated.

## Evidence

```text
UTC / operator / change ID:
Distribution/version / environment:
Sources / bulk / mapping / shard size:
Query latency / disk / merges:
Security / retention / backup restore:
Offline gate / 30 tests:
12 drills / rollback / reviewer / score:
```

Offline checks do not prove a production logging platform is reliable.
