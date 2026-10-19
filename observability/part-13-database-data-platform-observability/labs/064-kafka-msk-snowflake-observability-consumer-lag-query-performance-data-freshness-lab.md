# Chapter 064 — Kafka/MSK and Snowflake Observability Lab

**Part 13 — Database and Data Platform Observability**

## Offline acceptance

Save `healthy.json`, `pipeline_gate.py` and `test_pipeline_gate.py` from [Chapter 064](../064-kafka-msk-snowflake-observability-consumer-lag-query-performance-data-freshness.md) in one directory.

```bash
python3 pipeline_gate.py healthy.json
python3 -m unittest -v test_pipeline_gate.py
```

Expected PASS and 29 authored tests; capture the actual output.

## Approved staging workflow

1. Inventory MSK/Kafka clusters, topic partitions, consumers and connector ownership.
2. Check broker CPU/disk, ISR, under-replicated partitions and producer errors.
3. Measure consumer offsets, lag records, processing throughput and rebalance frequency.
4. Inspect Kafka Connect tasks, DLQ and source CDC watermarks.
5. Inspect Snowflake query history, execution time and warehouse queueing.
6. Compare warehouse load, credit trends, task history and ingestion failures.
7. Implement a source-to-Snowflake visible-data freshness SLI.
8. Verify dashboards and alerts without exposing query text or customer IDs.
9. Simulate bounded staging consumer slowdown and recover without unsafe offset resets.
10. Capture independent freshness recovery, change control and rollback.

## Negative drills

Test the 18 missing review attestations, missing owner/change, production environment, Kafka lag breach, freshness breach, Snowflake queue breach, under-replicated partitions breach and destructive-action prevention.

## Evidence worksheet

```text
UTC / operator / change:
Kafka brokers / partitions / ISR:
Consumer group / lag / processing rate:
Connect tasks / DLQ / CDC source watermark:
Snowflake QUERY_HISTORY / queue / credit:
Source-to-target visible freshness:
Application or downstream SLO impact:
Alerts / security / credentials:
Recovery / duplicate detection / rollback:
Offline gate and unit test output:
```

Do not use this offline gate as proof of production Kafka or Snowflake health.
