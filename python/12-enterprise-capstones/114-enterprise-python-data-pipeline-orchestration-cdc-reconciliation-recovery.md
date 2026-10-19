# Chapter 114 — Enterprise Python Data Pipeline Orchestration, CDC Reconciliation and Recovery

**Part 12 — Enterprise Capstone Projects | Chapter 114/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/114-data-pipeline-orchestration-cdc-reconciliation-recovery-sre-dbre-lab.md) · [Executable offline project](labs/114/README.md)

## Learning objectives

Design recoverable Python data pipelines with dependency-aware orchestration, incremental extraction, PostgreSQL/MongoDB change data capture, Kafka event transport, Elasticsearch/OpenSearch search projections, Snowflake analytical loading, checkpointing, idempotency, reconciliation, backfill, observability and disaster recovery. Understand the difference between an offline teaching model and live transactional/durable systems.

## Architecture

```text
 PostgreSQL OLTP / outbox             MongoDB change streams
      | WAL logical decoding                 | resume tokens
      v                                      v
 Debezium/CDC connector               MongoDB CDC connector
      |                                      |
      +----------> Kafka topics <------------+
                         |
                Python orchestration
        plan -> extract -> validate -> transform
                         |
            idempotent projection workers
                  |                 |
       Elasticsearch/OpenSearch   Snowflake
          alias/versioning        staging/MERGE
                  |                 |
                  +---- reconciliation ----+
                            |
             alerts / checkpoints / audit
```

**Source-of-truth and boundary:** PostgreSQL and MongoDB own their respective business entities; Kafka transports events; Elasticsearch is a derived search projection; Snowflake is an analytical target. Choose source precedence explicitly when entities overlap. Do not imply that independent PostgreSQL and MongoDB commits are atomic.

## 1. Orchestration architecture

Represent workflows as DAGs with declared dependencies, retry policy, scheduling, idempotency, owner, SLA and rollback. Distinguish event-driven streaming from batch workflows. Use an orchestrator such as Airflow, Dagster or Argo Workflows when appropriate; avoid building an undocumented scheduler inside an API pod. Separate control plane (schedules, metadata, state) from data plane (workers, connectors, storage). Use least-privilege workload identities, bounded task queues and resource quotas.

## 2. Incremental pipelines and CDC

For PostgreSQL, use a reviewed logical decoding connector, publication/replication slot and durable offsets. Track WAL retention, slot lag, schema changes, transaction ordering and snapshot-to-stream transition. For MongoDB, use change streams and resume tokens with appropriate majority commit semantics and oplog retention. Define what happens when a resume token expires or a replication slot is lost: stop, assess the gap, perform approved snapshot/backfill and reconcile before declaring recovery.

**Important:** A monotonically increasing integer in the offline lab is an illustrative sequence. Real PostgreSQL LSNs, Kafka offsets and MongoDB resume tokens are different types and must not be conflated or advanced interchangeably.

## 3. Kafka transport and ordering

Partition by stable entity key when per-entity order matters. Record topic, partition, offset, event ID, source position, schema version and event timestamp. Commit consumer offsets only after durable side effects or durable failure quarantine. Handle rebalances, duplicates, poison messages, retries and schema compatibility. Exactly-once guarantees are scoped; external Elasticsearch and Snowflake writes need idempotency/reconciliation.

## 4. Checkpointing and idempotency

Store checkpoints durably with ownership/lease fencing and compare-and-swap or transactional commit as needed. Advance only after verified sink completion; never advance beyond a failed event. Preserve replayability, event IDs, per-entity versions and audit evidence. A sink that succeeded before a downstream failure must tolerate replay. The offline `Pipeline` models this with a checkpoint that does not advance on simulated sink failure; it is not crash-safe and not atomic across sinks.

## 5. Elasticsearch/OpenSearch projection

Use versioned mappings, index aliases, external version or equivalent ordering guard, bounded bulk indexing, refresh policy and dead-letter handling. Compare authoritative source revisions and counts with index state. For rebuilds, create a new index, backfill, replay tail changes, validate, then atomically swap aliases where supported. Monitor shard size, merge pressure, disk IOPS, rejections and indexing lag.

## 6. Snowflake analytical load

Stage events/files with immutable batch IDs and manifest checksums. Validate schema and types, then use reviewed `COPY INTO` and `MERGE` patterns for idempotent incremental application, including delete semantics and late-arriving updates. Avoid assuming that stream/task history alone provides permanent recovery. Track warehouse cost, task lag, query history, rejected rows, ingestion duplicates and table reconciliation. A `MERGE` must have a unique deterministic source key; deduplicate source batches to avoid ambiguous matches.

## 7. Backfills and recovery

Plan bounded time/offset ranges, batch size, rate limits, priority, snapshot consistency and dependency load. Do not overwrite newer state with older backfill data. Reconcile by entity key, version, row counts and optionally canonical content hash, accounting for legitimate schema transforms and eventual-consistency windows. For partial failure, replay from last durable checkpoint, deduplicate already applied sinks, quarantine poison events and verify convergence before resuming normal throughput.

## 8. Data quality and reconciliation

Compare missing, extra and mismatched records. Define normalization for nulls, timestamps, arrays, numeric precision and tombstones. Reconciliation should generate evidence, not silently mutate production data. Require approval for bulk repairs, record before/after snapshots, and keep an immutable audit trail. A clean count alone does not prove data equivalence.

## 9. Observability, SLO and error budgets

Track source-to-target freshness, CDC lag (LSN/resume-token progress), Kafka event age and consumer lag, task duration/retries, DLQ count, missing/mismatched record count, Elasticsearch index lag, Snowflake load latency, failed `MERGE` and storage/compute cost. Use OTel trace links between batch/event stages, redacted logs, Prometheus RED/USE metrics and low-cardinality labels. Example SLI: fraction of eligible changes visible in each target within an agreed interval. Mark telemetry gaps unknown rather than pass.

## 10. Security and compliance

Use TLS, cloud workload identity, narrow DB publication/change-stream permissions, Kafka ACLs, Snowflake role segregation and encrypted staging. Prevent PHI/PII leakage into logs, DLQ and tracing attributes. Protect CDC credentials and Snowflake keys with approved secret management. Retain evidence and apply access controls to replay/backfill operations.

## 11. Production runbooks

**PostgreSQL slot lag/WAL growth:** inspect replication slots, retained WAL, connector state and disk; restore connector and checkpoint safely, never drop slots without recovery analysis.

**MongoDB resume failure:** inspect change stream token age, oplog window and replica health; rebuild snapshot and resume with reconciliation.

**Kafka lag:** inspect partition skew, worker throughput, DB pool waits and rebalances; bound replay rate.

**Elasticsearch drift:** compare source revisions, reindex into new alias target, replay tail and validate before swap.

**Snowflake load failure:** inspect stage manifest, load history, rejected rows, `MERGE` duplicates and task history; retry idempotently.

**Checkpoint corruption:** stop writers, restore verified durable checkpoint, fence old workers, replay and reconcile.

**Backfill overload:** throttle workers, monitor DB IO/CPU and pause safely; preserve progress.

**Cross-region recovery:** validate source fencing, offset continuity, RPO/RTO and sink consistency before reopening writes.

## 12. Executable lab and assessment

The [complete lab](labs/114-data-pipeline-orchestration-cdc-reconciliation-recovery-sre-dbre-lab.md) and [offline Python project](labs/114/README.md) implement a DAG planner, event validation, source-specific checkpoints, per-entity versioned projections, simulated sink failures, safe replay, reconciliation, bounded backfill ranges, advisory release gates and automated tests.

**Validation boundary:** No actual CDC connectors, PostgreSQL/MongoDB/Snowflake/Elasticsearch drivers, Kafka broker, production write, orchestration engine or network access are included. Test source is published; exact committed execution, CI, live integrations and security/operational acceptance remain pending.

**Next:** Chapter 115 — Enterprise Python Observability, SLOs, Incident Response and Reliability Operations.
