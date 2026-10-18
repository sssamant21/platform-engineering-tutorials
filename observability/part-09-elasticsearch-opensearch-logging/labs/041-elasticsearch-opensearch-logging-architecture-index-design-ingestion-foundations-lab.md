# Chapter 041 — Elasticsearch and OpenSearch Logging Architecture Lab

**Part 09 — Elasticsearch and OpenSearch Logging.**

## 1. Offline design gate

Copy `healthy.json`, `index_gate.py`, and `test_index_gate.py` from [Chapter 041](../041-elasticsearch-opensearch-logging-architecture-index-design-ingestion-foundations.md) into `chapter041/`.

```bash
cd chapter041
python3 index_gate.py healthy.json
python3 -m unittest -v test_index_gate.py
```

Expected PASS and 25 authored unit tests.

## 2. Optional version-pinned staging cluster

Choose **either** Elasticsearch or OpenSearch and record the exact distribution/version. Configure an authenticated HTTPS test endpoint and a nonproduction role with only required index/template/pipeline privileges. Do not paste credentials into shell history or GitHub.

1. Create an explicit index template compatible with the chosen distribution.
2. Create and simulate a normalization ingest pipeline.
3. Index a synthetic log event with a timestamp, service, level and message.
4. Send a two-event bulk NDJSON payload and inspect **every item** for errors.
5. Query by timestamp and service keyword.
6. Inspect primary shard size and replica allocation.
7. Review ILM (Elasticsearch) or ISM (OpenSearch) separately.
8. Restore the original template/pipeline and confirm safe writes.

## 3. Twelve negative drills

1. Wrong timestamp type.
2. Invalid date.
3. Mapping conflict.
4. Dynamic field explosion.
5. Too many small shards.
6. Oversized shard.
7. Bulk item-level 429.
8. Pipeline processor failure.
9. Replica unassigned.
10. Disk watermark.
11. Retention unapproved.
12. Missing redaction review.

## 4. DBRE incident game day

Simulate application log volume growth during PostgreSQL query slowness. Separate source-side error rates from indexing health; inspect mapping, merge pressure, bulk retries, disk I/O and shard allocation. Use staged rollback rather than deleting indices.

## 5. Evidence

```text
UTC / owner / change ID:
Elasticsearch or OpenSearch distribution/version:
Template and mapping:
Pipeline simulate result:
Bulk per-item errors:
Shard size / replicas / disk:
ILM or ISM state:
Offline gate / 25 tests:
12 drills / rollback / reviewer:
```

Offline tests alone do not certify a production logging system.
