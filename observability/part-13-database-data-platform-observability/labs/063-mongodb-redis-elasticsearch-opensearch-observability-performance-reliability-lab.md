# Chapter 063 — MongoDB, Redis and Elasticsearch/OpenSearch Companion Lab

**Part 13 — Database and Data Platform Observability**

## Offline lab

Copy `healthy.json`, `telemetry_gate.py` and `test_telemetry_gate.py` from [Chapter 063](../063-mongodb-redis-elasticsearch-opensearch-observability-performance-reliability.md). Then run:

```bash
python3 telemetry_gate.py healthy.json
python3 -m unittest -v test_telemetry_gate.py
```

Expected PASS and **28 authored tests**. Do not report tests as executed without recording results.

## Staging exercises

1. Record change ID, namespace, cluster versions, node roles and approved monitoring credentials.
2. Compare independent API RED SLOs with MongoDB command latency and WiredTiger cache.
3. Inspect MongoDB replica lag, oplog window and disk saturation.
4. Compare Redis INFO stats/memory/replication with command latency and blocked clients.
5. Check Redis slowlog metadata without exposing arguments.
6. Review Elasticsearch/OpenSearch health, search rejections, JVM and shard sizes.
7. Correlate search slow logs, IOPS/throughput, merge throttling and query fan-out.
8. Create Grafana panels with low-cardinality labels and source links.
9. Trigger a bounded staging latency or exporter-failure drill with approved rollback.
10. Record SLO recovery, alerts, ownership and follow-up actions.

## Negative drills

Test missing ownership, unsafe production environment, each of the 17 missing review attestations, breaches of MongoDB lag/Redis p99/search rejection/shard size budgets and destructive-action protection.

## Evidence

```text
UTC / owner / change:
MongoDB topology / cache / replication / storage:
Redis ops/sec / latency / evictions / replication:
Elasticsearch/OpenSearch search rejections / shard size / JVM / merge:
Independent application p95 / error rate:
Exporter and dashboard health:
Alerts / SLO burn:
Mitigation and rollback:
Offline gate output and test results:
Reviewer and approval:
```

**Safety:** staging-only fault drills; no destructive production operations or sensitive query logging.
