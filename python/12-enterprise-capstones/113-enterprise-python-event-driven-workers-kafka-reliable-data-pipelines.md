# Chapter 113 — Enterprise Python Event-Driven Workers, Kafka Integration and Reliable Data Pipelines

**Part 12 — Enterprise Capstone Projects | Chapter 113/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/113-event-driven-kafka-reliable-pipelines-sre-dbre-lab.md) · [Executable offline project](labs/113/README.md)

## Objectives

Design and operate reliable Python Kafka producers/consumers and event-driven workers. Cover topics, partitions, ordering, offsets, consumer groups, delivery guarantees, idempotency, transactional outbox, CDC, backpressure, retries, DLQ, schema evolution, observability, SLOs and incident response. Implement a deterministic standard-library simulator and tests, then design a separately authorized staging integration.

## Architecture

```text
Python API -> PostgreSQL transaction: business row + outbox row
                                          |
                      CDC connector / polling publisher
                                          |
                              Kafka topic partitions
                                          |
                       Python consumer group (workers)
                         |              |            |
                 idempotency store  DLQ/retry     derived stores
                         |              |      Elasticsearch/MongoDB
                         +--------------+
                              |
                OTel traces + metrics + structured logs
                              |
            lag, failures, retries, age, error budget alerts
```

**Critical guarantee:** A relational business update and its outbox entry can share one database transaction. Publishing from the outbox to Kafka is usually at least once, so downstream handlers must be idempotent. The simulator's in-memory `Outbox.commit` is a teaching model, **not a real database transaction**.

## 1. Kafka topics, partitions and producers

Choose partition count from throughput, consumer parallelism, ordering requirements and growth. A key-based partitioner keeps events for one aggregate together within a topic under a stable partitioning scheme; adding partitions may remap keys, so plan migration. Define replication factor, `min.insync.replicas`, `acks=all`, producer idempotence, batching, compression and delivery timeouts. Kafka producer acknowledgment is not proof that a downstream business operation completed. Secure brokers with TLS, SASL/IAM as appropriate, ACLs and secret rotation.

For production Python, use an actively maintained Kafka client (such as `confluent-kafka`) with explicit configuration, callbacks and bounded producer buffers. Do not hardcode secrets or blindly retry non-idempotent side effects.

## 2. Consumers, offsets and ordering

Consumer groups divide partitions among members. Each partition has a monotonically increasing offset. Commit offsets **after** durable processing and idempotency evidence; avoid committing ahead of effects. Handle rebalances, cooperative assignment, graceful shutdown and in-flight work. Distinguish consumer position, committed offset, end offset and consumer lag. Kafka ordering is per partition, not global. Concurrent processing of one partition requires a careful commit frontier and ordering policy.

The offline consumer uses a single sequential loop per partition; it is not thread-safe or crash-durable. Its synthetic DLQ behavior commits a failed offset after recording an in-memory DLQ entry; **production must durably publish the DLQ record or persist failure state before advancing the offset**.

## 3. Delivery semantics and idempotency

At-most-once can lose events; at-least-once can duplicate; exactly-once claims are scoped to particular Kafka transactional flows and do not automatically cover external PostgreSQL, Elasticsearch, MongoDB, Redis or HTTP side effects. Use event IDs, aggregate versions, unique constraints and idempotency records with the same transaction as effects where possible. Treat uncertain outcomes as a reconciliation problem rather than automatic replay.

## 4. Transactional outbox and CDC

Write business state and outbox row in one PostgreSQL transaction. A publisher or CDC connector streams committed outbox changes into Kafka, with retries, checkpointing and replay. Debezium/Kafka Connect are examples, subject to deployment/version-specific support. Design schema, `event_id`, `aggregate_id`, aggregate version, timestamps, tenant, correlation IDs and payload version. Maintain retention, cleanup, ordering, replication slot/WAL monitoring, connector restart and backfill plans. Avoid unsafe direct dual writes (DB then Kafka) without recovery logic.

## 5. Python worker architecture

Separate polling, decoding, validation, domain processing, persistence and offset management. Use typed schemas, bounded concurrency, cooperative cancellation and graceful shutdown. Set `max.poll.interval.ms`, heartbeat/session timeouts, fetch sizes and batch sizes to match processing time. Avoid CPU-bound work blocking heartbeats; isolate expensive transforms into worker pools. Partition-key affinity and bounded queues preserve order and prevent OOM.

## 6. Backpressure, retry and DLQ

Apply bounded in-flight messages, worker count, queue depth and retry budgets. Classify transient failures (broker unavailable, retryable DB timeout) separately from permanent errors (invalid schema, unauthorized tenant, poison message). Use exponential backoff with jitter and finite attempts; consider retry topics with delays while respecting partition-order semantics. A DLQ should include original topic/partition/offset, event ID, safe error category, attempt count and correlation ID, without secrets or sensitive payload leakage. Define DLQ ownership, retention, replay authorization and audit.

The offline lab models deterministic capped exponential delays, not real timers/jitter or Kafka retry topics. Production jitter must be added.

## 7. Schema governance and data consistency

Version event schemas with compatibility policy, schema registry, validation and contract tests. Plan rolling producer/consumer upgrades, unknown fields, tombstones, deletions and replay/backfill. For PostgreSQL->Kafka->Elasticsearch, index using aggregate version checks and reconciliation; protect against late events. For MongoDB and Redis projections, define eventual consistency SLOs, cache invalidation and source-of-truth recovery.

## 8. Observability and SLOs

Emit producer errors/retries, send latency, broker request throttling, consumer lag and **age of oldest unprocessed event**, rebalance frequency, batch duration, processing error rate, DLQ growth, outbox backlog/age, CDC connector lag, PostgreSQL replication-slot WAL retention and worker CPU/memory. Correlate HTTP request traces with Kafka propagation using safe headers. Define low-cardinality metrics and privacy-safe logs. Example SLI: fraction of valid events processed within 60 seconds; measure eligible events and time windows explicitly. Use burn-rate alerting and distinguish traffic spikes from stalled consumers.

## 9. Security and deployment

Use separate producer/consumer identities and topic ACLs, encrypted broker connections, least-privilege database accounts, secret management, immutable image digests, Kubernetes resource requests/limits, HPA/KEDA based on justified lag signals, PDB and readiness. Limit aggregate DB connection pools as replicas scale. Review data classification before including patient/customer data in messages, traces or DLQ.

## 10. Incident response runbooks

**Consumer lag:** inspect end offsets vs committed offsets, partition skew, processing CPU, DB pool waits, rebalance frequency and autoscaling; throttle producers or scale carefully within partition and DB limits.

**Poison message:** classify permanent failure, preserve safe evidence, durably quarantine before committing and define controlled replay.

**Duplicate side effects:** verify idempotency keys/unique constraints and offset commit ordering; reconcile external effects before retry.

**Outbox backlog:** inspect source DB locks, polling/CDC connector state, replication slot WAL retention and Kafka producer errors; preserve ordering.

**Broker outage:** inspect ISR, leader election, network/TLS, buffer limits and retry amplification; avoid unbounded producer queues.

**Search projection drift:** compare authoritative PostgreSQL aggregate revisions to search index versions, replay safely and verify alias state.

**Kubernetes worker crash:** inspect OOM, CPU throttling, shutdown/rebalance behavior and duplicate processing; validate recovery.

## 11. Labs and acceptance

The [full lab](labs/113-event-driven-kafka-reliable-pipelines-sre-dbre-lab.md) and [executable project](labs/113/README.md) implement schema checks, deterministic partition routing, in-memory outbox, broker offsets, consumer idempotency, synthetic DLQ, lag, admission/backpressure, retry delays, SLO budget and automated tests.

**Validation boundary:** The simulator has no real Kafka broker, PostgreSQL transaction, Debezium connector, Kubernetes workload, network, durable DLQ, transactional offset commit or production mutation. Published test source requires execution. CI, live integration, security review and operational acceptance remain pending.

**Next:** Chapter 114 — Enterprise Python Data Pipeline Orchestration, CDC Reconciliation and Recovery.
