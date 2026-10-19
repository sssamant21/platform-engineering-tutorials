# Chapter 118 — Multi-Region HA, Failover and Recovery SRE/DBRE Lab

[Offline simulator](118/failover_lab.py) · [Tests](118/test_failover_lab.py) · [Project guide](118/README.md)

## Mission

A primary region suffers a network partition while standby PostgreSQL/MongoDB replicas lag, Kafka cross-region replication is behind, Elasticsearch search projections are stale and Redis/Snowflake require recovery. Prevent split-brain, quantify RPO/RTO and plan a controlled failover without production actions.

## Execute

```bash
cd python/12-enterprise-capstones/labs/118
python -m compileall -q failover_lab.py test_failover_lab.py
python -m unittest -v test_failover_lab.py
python failover_lab.py --dry-run
python failover_lab.py --failure
```

## Hands-on labs

**Lab 1 — Topology:** compare active-passive and active-active; define writer ownership, traffic routing, read consistency and failure domains.

**Lab 2 — Fencing/quorum:** simulate lease epochs and quorum decisions; reject stale writers. Explain why real fencing must be enforced by the datastore and why a vote tally is not a consensus algorithm.

**Lab 3 — DR gates:** evaluate target health, replication lag/RPO, restore time/RTO, old-writer fencing, quorum, approval and reconciliation. Exercise failure holds.

**Lab 4 — Recovery DAG:** order identity, networking, PostgreSQL, Kafka, API and derived services; reject cycles/missing prerequisites.

**Lab 5 — Chaos and reconciliation:** label synthetic region outage/partition, compare source-target records, design staged fault injection and define measured RPO/RTO evidence.

## Forty production incident simulations

| # | Incident | Required response |
|---|---|---|
| 1 | Region health probe fails | Corroborate |
| 2 | Primary region outage | Declare incident |
| 3 | Partial network partition | Prevent dual writes |
| 4 | Expired lease | Reject writer |
| 5 | Stale epoch | Fence |
| 6 | Conflicting leaders | Halt promotion |
| 7 | Quorum lost | Hold |
| 8 | Standby unhealthy | Hold |
| 9 | Replication lag exceeds RPO | Hold |
| 10 | Restore exceeds RTO | Escalate |
| 11 | Old writer not fenced | Hold |
| 12 | Missing approval | Hold |
| 13 | Data verification missing | Hold |
| 14 | Recovery DAG cycle | Reject |
| 15 | Recovery dependency missing | Reject |
| 16 | PostgreSQL WAL replay lag | Inspect LSN |
| 17 | PostgreSQL timeline divergence | Rebuild/reconcile |
| 18 | PostgreSQL split brain | Fence old primary |
| 19 | MongoDB election storm | Inspect majority |
| 20 | MongoDB rollback risk | Validate writes |
| 21 | MongoDB oplog gap | Restore snapshot |
| 22 | Kafka DR replication lag | Inspect mirroring |
| 23 | Kafka offset translation error | Reconcile |
| 24 | Kafka duplicate replay | Deduplicate |
| 25 | Elasticsearch CCR lag | Validate freshness |
| 26 | Elasticsearch snapshot mismatch | Restore safely |
| 27 | Elasticsearch alias drift | Validate aliases |
| 28 | Redis cache cold start | Protect origin |
| 29 | Redis data loss | Validate persistence |
| 30 | Snowflake refresh lag | Verify replication |
| 31 | Snowflake failover object missing | Validate roles/integrations |
| 32 | Kubernetes node pool unavailable | Rebuild capacity |
| 33 | Cloud IAM unavailable | Restore identity |
| 34 | KMS key inaccessible | Hold restore |
| 35 | DNS propagation delayed | Validate routing |
| 36 | API error-budget burn | Roll back/mitigate |
| 37 | Missing target record | Reconcile |
| 38 | Mismatched target record | Reconcile |
| 39 | Staging chaos abort threshold | Stop experiment |
| 40 | Region repatriation | Fence/rebuild/verify |

## Operational runbooks

**Failover command:** establish commander, UTC timeline, customer impact, decision authority, region health, quorum and fencing evidence.

**PostgreSQL:** inspect WAL/timeline, replication slots and PITR; use approved HA promotion, reconcile old primary.

**MongoDB:** inspect replica voting majority, write concern, lag and rollback; verify post-election writes.

**Kafka:** inspect cross-region replication, schemas/ACLs, consumer offset translation and replay duplicates.

**Elasticsearch:** inspect CCR/snapshot, mapping, alias and index freshness; rebuild derived search as needed.

**Redis:** verify persistence or safe cache rebuild, TTL and origin protection.

**Snowflake:** validate replication/failover groups, refreshed objects, roles and analytical freshness.

**Traffic cutover:** confirm application SLO, DNS/load-balancer routing, client retries, data reconciliation and rollback.

**Repatriation:** rebuild former primary from authoritative state, test, schedule approved failback and audit.

## Final assessment — 100 points

| Domain | Points |
|---|---:|
| Multi-region architecture and failure domains | 20 |
| Quorum, fencing and split-brain prevention | 25 |
| PostgreSQL/MongoDB/Kafka/Elasticsearch/Redis/Snowflake DR | 20 |
| RPO/RTO, recovery DAG and reconciliation | 15 |
| Chaos testing, observability and runbooks | 10 |
| Automated tests and reproducibility | 10 |
| **Total** | **100** |

Pass at 90+ with locally executed tests, a reviewed fencing plan, measurable RPO/RTO, staged chaos plan, owner approval and rollback evidence.

**Validation:** Offline source and tests published; exact committed execution, CI, staging DR drills and production acceptance pending.
