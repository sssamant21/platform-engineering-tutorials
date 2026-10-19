# Chapter 114 — CDC Orchestration, Reconciliation and Recovery SRE/DBRE Lab

[Offline simulator](114/pipeline_lab.py) · [Tests](114/test_pipeline_lab.py) · [Project guide](114/README.md)

## Mission

Recover a PostgreSQL/MongoDB CDC -> Kafka -> Elasticsearch/Snowflake pipeline after connector lag, partial sink failure and a risky backfill. Use offline deterministic simulation, not production resources.

## Execute

```bash
cd python/12-enterprise-capstones/labs/114
python -m compileall -q pipeline_lab.py test_pipeline_lab.py
python -m unittest -v test_pipeline_lab.py
python pipeline_lab.py --dry-run
python pipeline_lab.py --partial
```

## Hands-on labs

**Lab 1 — Orchestration:** Build a dependency DAG, reject cycles/missing tasks and document retries, owners and task budgets.

**Lab 2 — CDC:** Validate source event envelopes and independent checkpoints. Design real PostgreSQL LSN and MongoDB resume-token storage; never conflate them with Kafka offsets.

**Lab 3 — Failure and replay:** Apply canonical, search and warehouse projections. Simulate sink failure; verify checkpoint does not advance. Replay idempotently and reconcile.

**Lab 4 — Backfill:** Generate bounded ranges, reject sequence gaps, prevent old data overwriting newer revisions and define a human-approved repair plan.

**Lab 5 — Observability:** Design CDC freshness SLI, Kafka event age/lag, Snowflake load errors, Elasticsearch index lag, OTel trace links and privacy-safe metrics.

## Production incident simulations

| # | Failure | Action |
|---|---|---|
| 1 | Invalid CDC source | Reject |
| 2 | Invalid entity ID | Reject |
| 3 | Invalid sequence | Reject |
| 4 | Duplicate event | Idempotency |
| 5 | Out-of-order event | Version guard |
| 6 | Tombstone/delete | Remove projection |
| 7 | Checkpoint regression | Halt |
| 8 | DAG cycle | Reject |
| 9 | Missing task dependency | Reject |
| 10 | PostgreSQL slot lag | Inspect WAL |
| 11 | PostgreSQL slot loss | Snapshot/recover |
| 12 | MongoDB expired resume token | Backfill/reconcile |
| 13 | MongoDB oplog gap | Rebuild snapshot |
| 14 | Kafka consumer lag | Inspect throughput |
| 15 | Kafka replay duplicate | Deduplicate |
| 16 | Elasticsearch rejection | Bound bulk/IOPS |
| 17 | Elasticsearch alias drift | Validate alias |
| 18 | Snowflake load failure | Inspect load history |
| 19 | Snowflake MERGE duplicates | Deduplicate source |
| 20 | Warehouse outage | Hold checkpoint |
| 21 | Search outage | Hold checkpoint |
| 22 | Partial sink commit | Safe replay |
| 23 | Missing target record | Reconcile |
| 24 | Extra target record | Investigate tombstone |
| 25 | Mismatched target record | Compare normalized data |
| 26 | Backfill overlaps streaming | Fence/version guard |
| 27 | PostgreSQL backfill load | Throttle |
| 28 | MongoDB cursor overload | Bound batches |
| 29 | Elasticsearch bulk saturation | Throttle |
| 30 | Snowflake credit spike | Optimize |
| 31 | Schema drift | Quarantine |
| 32 | TLS expiry | Rotate |
| 33 | OTel outage | Unknown coverage |
| 34 | Worker OOM | Bound memory |
| 35 | Metrics cardinality | Remove unbounded labels |
| 36 | CDC freshness breach | Mitigate |
| 37 | Wrong checkpoint ownership | Fence |
| 38 | DLQ growth | Triage/replay |
| 39 | Retry storm | Backoff/jitter |
| 40 | Cross-region recovery | Fence/reconcile |

## Runbooks

**PostgreSQL:** inspect replication slots, WAL retention and connector offsets before restoring a CDC stream.

**MongoDB:** inspect change-stream token, oplog window and replica health; snapshot/reconcile if resume is impossible.

**Kafka:** inspect consumer offsets, lag, rebalances and DLQ; prevent replay storms.

**Elasticsearch:** inspect mapping, index alias, bulk rejections and disk IOPS; rebuild and validate projections.

**Snowflake:** inspect stage manifests, load history, `MERGE` uniqueness, rejected rows and warehouse cost.

**Checkpoint recovery:** fence writers, restore durable state, replay idempotently and compare canonical source/targets.

**Backfill:** agree owner/window, bound batches, monitor load, checkpoint progress and verify convergence.

## Final assessment (100 points)

| Domain | Points |
|---|---:|
| Orchestration and incremental design | 20 |
| PostgreSQL/MongoDB CDC and Kafka | 20 |
| Checkpointing, idempotency and recovery | 20 |
| Elasticsearch/Snowflake reconciliation | 20 |
| Observability, security and runbooks | 10 |
| Tests and evidence | 10 |
| **Total** | **100** |

Pass at 90+ with locally executed tests, a durable replay plan and approved rollback.

**Validation:** Offline test source published; exact committed execution, CI, live integration and production acceptance pending.
