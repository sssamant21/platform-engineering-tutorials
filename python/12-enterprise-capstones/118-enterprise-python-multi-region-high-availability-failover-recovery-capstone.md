# Chapter 118 — Enterprise Python Multi-Region High Availability, Failover and Recovery Capstone

**Part 12 — Enterprise Capstone Projects | Chapter 118/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/118-multi-region-ha-failover-recovery-sre-dbre-lab.md) · [Executable offline project](labs/118/README.md)

## Outcomes

Design multi-region Python platform architectures with active-passive and active-active routing, workload identity, quorum, lease-based leadership, fencing, split-brain prevention, safe failover, PostgreSQL/MongoDB/Kafka/Elasticsearch/Redis/Snowflake recovery integration, RPO/RTO measurement, chaos experiments, observability and audit-ready runbooks.

## Reference architecture

```text
               Global DNS / health-based traffic manager
                          |
              +-----------+-----------+
              |                       |
       Region A (primary)        Region B (standby)
       API / workers / K8s       API / workers / K8s
              |                       |
       PostgreSQL primary ---> async/sync replica (design dependent)
       MongoDB replica set ---> voting/replication topology
       Kafka cluster ---------> DR replication / offset translation
       Elasticsearch ---------> snapshots / CCR where licensed
       Redis -----------------> replica/rebuild strategy
       Snowflake -------------> replication/failover groups
              |                       |
              +---- independent witness/quorum ----+
                           |
               fenced writer epoch/lease
                           |
             OTel / SLO / lag / RPO / RTO evidence
```

## 1. Availability models

**Active-passive:** a single writable primary region and warm/hot standby. Simpler write ownership but promotion incurs RTO and replication lag can cause RPO. **Active-active:** multiple regions serve traffic; for multi-writer state require explicit conflict resolution, global ordering or partitioned ownership. Active-active APIs with a single-writer datastore are not multi-master data storage. Use region-local reads only with documented staleness budgets. Plan network partitions, region isolation, DNS TTL, client caches, load balancer health checks, cloud control-plane failure and data sovereignty.

## 2. Leader election, quorum and fencing

Use a proven distributed consensus system (e.g., etcd/Raft or supported datastore leader-election mechanism) rather than inventing election logic. A majority quorum prevents conflicting decisions in a properly configured consensus group. **Fencing is mandatory:** each new leader obtains a monotonically increasing epoch/token, and the storage/write path must reject stale epochs. Merely checking an in-memory lease is not sufficient for real split-brain prevention; fencing must be enforced by the authoritative sink or infrastructure. If quorum, epoch enforcement or old-writer isolation cannot be proved, do not promote. Clock skew, network partitions and delayed writes must be considered.

The offline lab implements an illustrative lease/epoch decision and simple vote tally; it is **not** a consensus algorithm, distributed lock or production fencing implementation.

## 3. Failover state machine

Use explicit states: HEALTHY -> SUSPECT -> CONFIRMED_FAILURE -> FREEZE_WRITES -> FENCE_OLD_PRIMARY -> VERIFY_STANDBY -> APPROVAL -> PROMOTE -> ROUTE_TRAFFIC -> RECONCILE -> OBSERVE -> COMPLETE. Provide ABORT/HOLD paths at every gate. Promotion requires owner approval, data consistency evidence, validated quorum/fencing, known RPO/RTO, rollback plan and communications. Automate reversible verification before enabling mutation; production promotion should be controlled by vendor-supported mechanisms and reviewed operational tooling.

## 4. PostgreSQL cross-region

Choose synchronous vs asynchronous replication based on latency and data-loss tolerance. Inspect WAL replay position, replication slots, replication lag, timeline history, connection draining, role/extension consistency and PITR backups. Patroni or managed HA services may orchestrate supported promotion, but still require independent fencing and client routing. Prevent old-primary rejoin as writable; use `pg_rewind` or rebuild where supported, after verifying timeline divergence. RPO is based on committed transactions not present in promoted region, not merely a healthy replica flag.

## 5. MongoDB cross-region

Design replica-set voting topology with failure domains and an odd number of votes where appropriate. Evaluate majority write concern, election timeouts, replication lag, primary stepdown, rollback windows, retryable writes and read preferences. A partitioned minority must not accept majority-committed writes. Sharded deployments add config server and shard election dependencies. Backups and oplog continuity remain necessary; a replica is not a substitute for recovery evidence.

## 6. Kafka multi-region

Choose independent regional clusters with MirrorMaker 2, Cluster Linking or vendor-supported replication as appropriate. Account for asynchronous replication, partition-key ordering, consumer offset translation, topic/ACL/schema replication, producer idempotency, duplicate events and connector checkpoints. External sinks require idempotency and reconciliation. Avoid blindly reusing offsets across distinct clusters; verify mapping and consumer group cutover.

## 7. Elasticsearch/OpenSearch

Plan snapshot repositories and tested restores, or cross-cluster replication where supported by version/licensing. Understand leader/follower index limitations, mappings/templates, aliases, security configuration and index freshness. Rebuild derived indexes from authoritative stores when cheaper/safer. Protect against oversized shards, merge pressure, disk watermarks and cross-region network cost. Do not copy live data paths.

## 8. Redis and Snowflake

For Redis, decide whether cache can be invalidated/rebuilt or requires persisted state. Evaluate replica promotion, asynchronous loss, Sentinel/Cluster behavior and regional client redirection; guard against cache stampede after failover. For Snowflake, validate account/region replication and failover-group features, refresh schedules, supported objects, stages/integrations, security roles and RPO/RTO. Analytics may tolerate a different recovery objective from OLTP; define per-system tiers.

## 9. Recovery dependencies and orchestration

Order prerequisites: cloud identity/KMS -> network/DNS -> Kubernetes control plane -> stateful primary/replica verification -> Kafka/CDC -> API/workers -> derived search/cache -> Snowflake analytics -> end-to-end reconciliation. Some dependencies can recover in parallel, but write ownership and security must be established first. Use declarative runbooks and immutable artifacts. The offline DAG validator detects cycles/missing dependencies and returns a deterministic order.

## 10. RPO, RTO and reconciliation

RPO is measured data loss (e.g., missing acknowledged transactions or events); RTO is measured time to restore acceptable service. Replication lag is a useful proxy but not a complete measurement. Verify backup age, source/sink offsets, entity versions, CDC checkpoints, tombstones, counts and content hashes. Reconcile divergent writes before reintroducing old primary or enabling both regions. Define acceptance thresholds and immutable audit evidence.

## 11. Chaos testing and fault injection

Run approved staging experiments: region outage, network partition, stale replica, expired leader lease, storage outage and telemetry gap. Set blast-radius limits, timeboxes, abort criteria, stakeholder notification and no-production-write safeguards. Test under traffic, verify client retries/backoff, measure RPO/RTO, check split-brain fencing, and observe recovery SLOs. The offline `chaos` helper only labels synthetic faults and performs no injection.

## 12. Observability

Track region health, synthetic probes, control-plane availability, write leader epoch, quorum, replication lag, PostgreSQL WAL positions, MongoDB election/majority writes, Kafka consumer/replication lag, Elasticsearch CCR/index age, Redis cache warmup, Snowflake refresh lag, API RED metrics, p99, error budgets, DNS propagation and data divergence. Correlate logs/traces/metrics by incident and region. Unknown telemetry is not permission to promote.

## 13. Production runbooks

**Region failure:** declare incident, confirm independent evidence, establish incident command, freeze conflicting writes and verify quorum.

**Fencing:** revoke old region's write access at authoritative datastore/network, validate epoch rejection and record evidence before promotion.

**PostgreSQL:** compare WAL/timelines, confirm promotable standby and PITR; promote using supported HA tooling, then reconcile.

**MongoDB:** inspect voting majority, election, replication lag and rollback risk; validate writes after election.

**Kafka:** inspect cross-region replication, offset translation, topic/schema/ACL parity and duplicate handling.

**Elasticsearch:** inspect CCR/snapshot freshness, aliases, mappings and search correctness; restore/rebuild as needed.

**Redis:** verify persistence or controlled cache rebuild, connection routing and origin protection.

**Snowflake:** validate failover-group refresh, objects, roles and analytical freshness before enabling dependent workloads.

**Repatriation:** fence new/old writers appropriately, rebuild former primary from authoritative timeline and test rollback.

## 14. Lab and assessment

The [complete lab](labs/118-multi-region-ha-failover-recovery-sre-dbre-lab.md) and [offline Python project](labs/118/README.md) model regional health, leases/epochs, simple quorum decisions, recovery gates, DAG dependencies, reconciliation and synthetic chaos, with automated tests, 40 incident scenarios and 100-point assessment.

**Validation boundary:** No real consensus, distributed locks, cloud services, failover, database promotion, chaos injection or production writes. Exact committed tests, CI, staging DR drills and operational acceptance remain pending.

**Next:** Chapter 119 — Enterprise Python Production Readiness, Chaos Engineering and Reliability Acceptance Capstone.
