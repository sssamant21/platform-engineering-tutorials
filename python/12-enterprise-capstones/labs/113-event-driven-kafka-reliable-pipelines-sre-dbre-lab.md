# Chapter 113 — Kafka Workers and Reliable Data Pipelines: SRE/DBRE Lab

[Simulator](113/event_lab.py) · [Tests](113/test_event_lab.py) · [Project guide](113/README.md)

## Mission

A Python API commits PostgreSQL business updates and an outbox; a publisher/CDC pipeline sends events to Kafka; workers build Elasticsearch/MongoDB projections and invalidate Redis. A broker disruption and consumer lag expose ordering, idempotency and backpressure risks. The lab is entirely offline and synthetic.

## Lab 1 — Run

```bash
cd python/12-enterprise-capstones/labs/113
python -m compileall -q event_lab.py test_event_lab.py
python -m unittest -v test_event_lab.py
python event_lab.py --dry-run
```

## Lab 2 — Event contracts and partitions

Validate event envelope and aggregate versions. Confirm stable per-key partition assignment, ordered offsets and duplicate-event rejection. Explain the limits of per-partition ordering and what happens when partition count changes.

## Lab 3 — Outbox and CDC

Commit aggregate revision plus outbox event in the in-memory model, drain batches and publish. Design a real PostgreSQL transaction, outbox schema, replication slot/CDC connector, restart checkpoint, WAL retention and backfill strategy. Verify that the simulator does not prove atomicity or crash durability.

## Lab 4 — Consumer, retry, DLQ

Consume partition offsets sequentially; suppress duplicate event IDs; reject out-of-order versions; simulate poison events. Design a production DLQ write-then-offset-commit policy, idempotent external DB effects, bounded retries with jitter and authorized replay. The simulator commits after an in-memory DLQ entry only; do not deploy that behavior.

## Lab 5 — Backpressure and SLO

Model bounded active workers, queued and rejected events, consumer lag and success SLO. Define an event-age SLI and Kafka/CDC monitoring plan with OpenTelemetry trace propagation, low-cardinality metrics and privacy-safe logs.

## Incident simulations

| # | Incident | Expected response |
|---|---|---|
| 1 | Malformed event | Reject schema |
| 2 | Invalid event ID | Reject |
| 3 | Invalid aggregate version | Reject |
| 4 | Duplicate outbox event | Reject |
| 5 | Out-of-order aggregate | Quarantine/reconcile |
| 6 | Invalid partition count | Reject |
| 7 | Partition key remapping | Plan migration |
| 8 | Producer acknowledgment lost | Verify delivery/idempotency |
| 9 | Broker leader change | Inspect ISR/elections |
| 10 | Producer buffer saturation | Backpressure |
| 11 | Kafka 429/throttling | Bound retries |
| 12 | Consumer lag spike | Inspect partitions/throughput |
| 13 | Consumer rebalance loop | Inspect poll/heartbeat |
| 14 | Consumer crash before commit | Reprocess idempotently |
| 15 | Offset committed before effect | Detect data loss risk |
| 16 | Duplicate event ID | Suppress side effect |
| 17 | Poison message | Durable DLQ before commit |
| 18 | DLQ growth | Triage and own replay |
| 19 | DLQ replay duplication | Check idempotency |
| 20 | Retry storm | Cap attempts and jitter |
| 21 | Worker queue overload | Reject/shed load |
| 22 | Worker OOM | Bound batch/inflight |
| 23 | PostgreSQL outbox backlog | Inspect locks/publisher |
| 24 | CDC connector down | Restore checkpoint |
| 25 | Replication slot WAL growth | Investigate slot lag |
| 26 | Schema incompatible producer | Roll back/compatibility |
| 27 | Event ordering violation | Version guard |
| 28 | Elasticsearch projection lag | Replay/reconcile |
| 29 | MongoDB projection drift | Compare source revisions |
| 30 | Redis invalidation missed | Repair cache safely |
| 31 | TLS/SASL authentication failure | Check identity/certs |
| 32 | Kafka ACL denial | Least-privilege review |
| 33 | Kafka partition skew | Inspect keys/hot partitions |
| 34 | CPU-bound Python consumer | Profile and isolate work |
| 35 | Kubernetes HPA overscaling | Respect partitions/DB pools |
| 36 | Worker shutdown interruption | Drain/commit safely |
| 37 | Trace propagation broken | Inspect headers |
| 38 | High-cardinality metrics | Reduce labels |
| 39 | Event-age SLO breach | Mitigate and alert |
| 40 | Multi-region DR replay | Fence, reconcile, audit |

## Runbooks

**Lag:** inspect end/committed offsets, event age, processing throughput, partitions, DB waits, CPU and rebalances. Scale only within partition and downstream limits.

**Outbox/CDC:** check PostgreSQL locks, connector offsets, replication slots and WAL retention; restart from durable checkpoint without losing ordering.

**Poison/DLQ:** quarantine safely, durably publish failure state, commit only after confirmation, define owner and replay audit.

**Duplicate effects:** inspect idempotency records, unique constraints and offset commit ordering; reconcile authoritative data.

**Kafka outage:** inspect brokers, ISR, TLS/SASL, producer buffering and retry amplification; preserve backpressure.

**Projection drift:** compare PostgreSQL aggregate versions against search/document projections, replay safely and validate cache invalidation.

## Final assessment — 100 points

| Domain | Points |
|---|---:|
| Producer/consumer architecture and partitions | 20 |
| Offsets, ordering, idempotency and delivery semantics | 20 |
| Transactional outbox, CDC and reconciliation | 20 |
| Backpressure, retries, DLQ and recovery | 15 |
| Observability, SLOs, security and runbooks | 15 |
| Automated tests and reproducibility | 10 |
| **Total** | **100** |

Pass at 90+ with local tests executed, no-live-write evidence, a durable outbox/DLQ design, reviewed replay controls and incident rollback plan.

**Validation:** Offline tests published; exact committed execution, CI, live Kafka/CDC integration and production acceptance pending.
