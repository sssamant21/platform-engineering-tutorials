# Chapter 120 — Final Enterprise Python SRE/DevOps/DBRE Assessment Lab

[Simulator](120/platform_lab.py) · [Automated tests](120/test_platform_lab.py) · [Project README](120/README.md) · [Chapter theory](../120-enterprise-python-final-sre-devops-dbre-capstone-operational-assessment.md)

## Mission

Operate a synthetic patient-agnostic Python API/data platform across PostgreSQL/MongoDB (sources), Kafka/CDC (transport), Elasticsearch/Redis (search/cache), Snowflake (analytics) and Kubernetes (compute). Validate tenant isolation, replay/idempotency, reconciliation, performance, SLOs, backup/DR and production change gates. **No actual datastore connections or mutations.**

## Execute

```bash
cd python/12-enterprise-capstones/labs/120
python -m compileall -q platform_lab.py test_platform_lab.py
python -m unittest -v test_platform_lab.py
python platform_lab.py --dry-run
python platform_lab.py --failure
```

Collect commit SHA, Python version, test output, reports and reviewer sign-off. A CLI report's `advisory-ready` state is not production authorization.

## End-to-end labs

**Lab 1 — Architecture:** draw identity/ingress/API, PostgreSQL/MongoDB, outbox/CDC, Kafka, Python workers, Elasticsearch, Redis, Snowflake, Kubernetes, OTel and DR dependencies. Label authoritative data and derived views.

**Lab 2 — Security:** test role/tenant admission, plan workload identity, IAM/RBAC, encryption, secret rotation and audit evidence. Reject cross-tenant writes.

**Lab 3 — Outbox/CDC:** create typed versioned events, enforce bounded admission and simulate stale/duplicate versions. Contrast in-memory operations with real ACID outbox and MongoDB resume tokens.

**Lab 4 — Kafka:** publish to deterministic partitions, observe offsets/lag, simulate sink failure and verify offsets do not advance. Design real DLQ durability and schema compatibility.

**Lab 5 — Reconciliation:** consume events to synthetic search/warehouse, compare keys/version/hash, test missing and mismatched records, define safe replay/backfill.

**Lab 6 — Capacity:** model CPU ms/request, RPS, pod capacity, PostgreSQL connection limits, MongoDB working set, Elasticsearch IOPS, Redis cache, Kafka lag and Snowflake credits.

**Lab 7 — SLO/observability:** compute availability and error budget, design OTel traces/Prometheus RED+USE metrics, correlate API/CDC/index/warehouse freshness and treat missing telemetry as unknown.

**Lab 8 — Disaster recovery:** evaluate RPO/RTO, fencing, verified recovery point and approval; plan PostgreSQL PITR, MongoDB backup/oplog, Kafka offset translation, Elasticsearch snapshot, Redis rebuild and Snowflake failover.

**Lab 9 — Chaos:** design bounded staging pod loss, Kafka lag, DB latency, network partition and region outage experiments with abort triggers and no production faults.

**Lab 10 — Acceptance:** score all nine domains (100 points), require zero unresolved lag/reconciliation errors and all mandatory controls; prepare owner approval and tested rollback evidence.

## Forty enterprise incident simulations

| # | Scenario | Expected action |
|---|---|---|
| 1 | Unauthorized API tenant | Deny/audit |
| 2 | Expired workload identity | Reauthenticate |
| 3 | Leaked secret | Revoke/rotate |
| 4 | Unsigned container | Block |
| 5 | Incompatible API change | Hold |
| 6 | Duplicate outbox event | Idempotent apply |
| 7 | Stale event version | Reject |
| 8 | Outbox queue full | Backpressure |
| 9 | Source/outbox partial commit | Use real ACID outbox |
| 10 | Kafka partition skew | Repartition plan |
| 11 | Kafka consumer lag | Investigate |
| 12 | Sink failure before offset commit | Retry |
| 13 | Poison event | Durable DLQ |
| 14 | Missing CDC resume token | Resnapshot/reconcile |
| 15 | PostgreSQL pool exhaustion | Bound pools |
| 16 | PostgreSQL lock waits | Diagnose |
| 17 | PostgreSQL WAL/PITR gap | Hold restore |
| 18 | MongoDB election | Verify majority |
| 19 | MongoDB cache pressure | Profile |
| 20 | MongoDB oplog expiry | Reconcile |
| 21 | Elasticsearch search rejection | Throttle |
| 22 | Elasticsearch disk IOPS saturation | Storage remediation |
| 23 | Elasticsearch stale index | Replay |
| 24 | Redis hot-key stampede | Coalesce |
| 25 | Redis eviction storm | Rebuild safely |
| 26 | Snowflake MERGE replay | Version-aware upsert |
| 27 | Snowflake warehouse cost spike | Attribute |
| 28 | Snowflake freshness breach | Investigate |
| 29 | Kubernetes OOM | Resize |
| 30 | Kubernetes HPA cap | Backpressure |
| 31 | Python CPU hotspot | Profile |
| 32 | Python event-loop blocking | Isolate IO/CPU |
| 33 | SLO error-budget breach | Freeze risky rollout |
| 34 | Telemetry unavailable | Unknown/hold |
| 35 | Source/search mismatch | Reconcile |
| 36 | Source/warehouse mismatch | Reconcile |
| 37 | Region failure | Invoke DR |
| 38 | Unfenced old primary | Hold promotion |
| 39 | RPO/RTO exceeded | Escalate |
| 40 | Rollback/approval missing | Hold release |

## Production runbooks

**API/Kubernetes:** inspect deployments, probes, HPA, CPU throttling, OOM, p99, traces and rollback status.

**PostgreSQL:** inspect `pg_stat_activity`, `pg_stat_statements`, locks, WAL/replication and PITR.

**MongoDB:** inspect elections, write concern, cache/eviction, oplog and change-stream resume state.

**Kafka:** inspect partitions, offsets, DLQ, lag, connector checkpoint and idempotent replay.

**Elasticsearch/OpenSearch:** inspect shard sizing, disk IOPS/queue, merge throttling, threadpool rejections and aliases.

**Redis:** inspect hot keys, eviction, fragmentation and origin-protection behavior.

**Snowflake:** inspect task/query history, COPY/MERGE, warehouse credits and reconciliation.

**Security:** contain, preserve evidence, revoke/rotate, verify workload and tenant permissions.

**DR:** declare incident commander, fence writers, validate backups/RPO/RTO, restore isolated dependencies, reconcile and approve cutover.

**Postmortem:** document UTC timeline, customer impact, detection gap, contributing factors, remediation owners and verification.

## Final 100-point operational assessment

| Domain | Points |
|---|---:|
| API/event/CDC and reconciliation | 15 |
| Capacity/performance | 10 |
| SLOs/reliability | 15 |
| Disaster recovery | 15 |
| Security/tenant isolation | 15 |
| Observability | 10 |
| Automated tests | 10 |
| Rollback/change plan | 5 |
| Owner approval/evidence | 5 |
| **Total** | **100** |

**Passing threshold:** 90+ and all mandatory domain gates passing. Real operational acceptance additionally requires executed tests, security review, staging integration, backup/restore drills, game days, and accountable sign-off.

## Curriculum audit checklist

- [x] Chapter 120 tutorial and offline executable project published
- [x] Automated test source and incident/runbook lab published
- [ ] Execute exact committed code and capture local test results
- [ ] Configure and run CI across supported Python versions
- [ ] Audit all 120 chapter links, code paths, tests and formatting against GitHub tree
- [ ] Conduct security/dependency review and cloud staging integrations
- [ ] Complete live load, restore, DR, failover and chaos drills
- [ ] Obtain production owner acceptance

**Publication completion is distinct from operational validation.** Do not mark pending validation tasks as passed.
