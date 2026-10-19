# Chapter 065 — Enterprise Database and Data Platform Observability Capstone Lab

**Part 13 final capstone**

## Offline validation

Copy `healthy.json`, `capstone_gate.py` and `test_capstone_gate.py` from [Chapter 065](../065-enterprise-database-data-platform-observability-incident-response-reliability-capstone.md).

```bash
python3 capstone_gate.py healthy.json
python3 -m unittest -v test_capstone_gate.py
```

Expected PASS and 29 authored tests. Capture actual output.

## Approved staging game day

1. Record change ID, incident commander, owners and affected services.
2. Establish independent application latency/error SLO and error budget.
3. Review PostgreSQL waits, WAL, connections and storage.
4. Review MongoDB cache, oplog and replication.
5. Review Redis p99 latency, evictions and hot keys.
6. Review Elasticsearch/OpenSearch search rejections, shards and merges.
7. Review Kafka/MSK ISR, consumer lag and Connect tasks.
8. Review Snowflake warehouse queueing, query failures and credits.
9. Measure source-to-Snowflake visible data freshness.
10. Simulate a bounded exporter failure and validate fallback monitoring.
11. Conduct an approved backup/restore drill, measure RPO/RTO and rollback.
12. Score 100-point acceptance and document evidence.

## Negative drills

Missing review of each of 18 platform/security/recovery controls, missing owner, unsafe environment, RPO/RTO breach, freshness breach, coverage breach and unapproved destructive action.

## Evidence

```text
UTC / incident commander / change:
Independent API RED SLO:
PostgreSQL / MongoDB / Redis / Elasticsearch/OpenSearch:
Kafka ISR / consumer lag / Connect:
Snowflake queue / credits / source-target freshness:
Exporter health / logs / traces:
Tenant security / sensitive-data redaction:
Backup / restore / measured RPO and RTO:
Rollback and postmortem:
Offline gate and 29 unit test outcomes:
Final assessment score / reviewer:
```

Synthetic review results are not production certification.
