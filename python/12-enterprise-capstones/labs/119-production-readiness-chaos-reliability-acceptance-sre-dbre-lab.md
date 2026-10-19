# Chapter 119 — Production Readiness, Chaos Engineering and Reliability Acceptance SRE/DBRE Lab

[Offline simulator](119/readiness_lab.py) · [Automated tests](119/test_readiness_lab.py) · [Project guide](119/README.md)

## Mission

A Python API and Kafka/CDC data platform is approaching launch. PostgreSQL pool pressure, Elasticsearch disk IOPS, MongoDB elections, Redis hot keys, Snowflake pipeline lag and Kubernetes resource pressure threaten its SLO. Run an evidence-based production readiness review, design a bounded chaos game day and decide whether to accept or hold the launch. All executable activities are offline.

## Execute

```bash
cd python/12-enterprise-capstones/labs/119
python -m compileall -q readiness_lab.py test_readiness_lab.py
python -m unittest -v test_readiness_lab.py
python readiness_lab.py --dry-run
python readiness_lab.py --failure
```

Record Python version, commit SHA, test output, decision, fingerprint and proof of no network calls or production mutations.

## Hands-on labs

**Lab 1 — Architecture and evidence:** map APIs, workers, data stores, secrets, IAM, queues, CDC, SLO ownership and DR. Populate typed evidence for architecture, deployment, observability, reliability, security, capacity, disaster recovery and operations.

**Lab 2 — Acceptance score:** calculate the 100-point PRR, require all critical controls, enforce a 90-point threshold, approval and tested rollback. Prove that a critical failure cannot be overridden by a high score.

**Lab 3 — SLOs:** calculate availability, remaining event error budget, short/long burn rates and no-traffic unknown state. Design multiwindow alerts and pager routes.

**Lab 4 — Performance gates:** evaluate synthetic p99, 5xx, CPU, memory and PostgreSQL pool utilization. Design real staging load/soak tests with traffic limits.

**Lab 5 — Chaos and incident response:** plan bounded staging pod-kill/network partition/Kafka lag experiments, owner approval, abort triggers and UTC incident timeline. No fault injection is performed.

**Lab 6 — Operational acceptance:** assemble rollback, capacity, security, backup/DR, canary, communication and postmortem evidence for accountable sign-off.

## Forty production incident simulations

| # | Scenario | Expected response |
|---|---|---|
| 1 | Missing architecture evidence | Hold |
| 2 | Invalid evidence owner | Reject |
| 3 | Duplicate control | Reject |
| 4 | Missing deployment gate | Hold |
| 5 | Critical security failure | Hold |
| 6 | Critical DR failure | Hold |
| 7 | Reliability SLO failure | Hold |
| 8 | Readiness score below 90 | Hold |
| 9 | Rollback untested | Hold |
| 10 | Human approval missing | Hold |
| 11 | No request traffic | SLI unknown |
| 12 | Availability breach | Error-budget policy |
| 13 | Fast error-budget burn | Page |
| 14 | Slow error-budget burn | Investigate |
| 15 | API p99 regression | Hold canary |
| 16 | API error rate regression | Roll back |
| 17 | Python CPU saturation | Profile |
| 18 | Python memory leak | Soak test |
| 19 | Kubernetes OOM | Right-size |
| 20 | Kubernetes HPA cap | Protect dependencies |
| 21 | PostgreSQL pool exhaustion | Bound pools |
| 22 | PostgreSQL lock contention | Inspect blockers |
| 23 | MongoDB primary election | Reconcile writes |
| 24 | MongoDB cache eviction | Inspect working set |
| 25 | Elasticsearch search rejection | Reduce fanout |
| 26 | Elasticsearch disk IOPS bottleneck | Storage diagnosis |
| 27 | Redis hot key | Coalesce |
| 28 | Redis cache stampede | Protect origin |
| 29 | Kafka consumer lag | Inspect partitions |
| 30 | Kafka duplicate replay | Idempotency |
| 31 | CDC checkpoint gap | Reconcile |
| 32 | Snowflake task lag | Validate freshness |
| 33 | Secret leaked to logs | Contain/rotate |
| 34 | Unverified supply-chain artifact | Block |
| 35 | Failed restore drill | Hold |
| 36 | Multi-region split-brain risk | Fence writers |
| 37 | Chaos blast radius too large | Reject |
| 38 | Chaos abort guard absent | Reject |
| 39 | Incident owner missing | Assign/escalate |
| 40 | Telemetry outage during canary | Hold/unknown |

## Operational runbooks

**API and Python:** inspect RED, traces, p99, CPU profiling, heap and timeouts; throttle or roll back.

**PostgreSQL:** inspect `pg_stat_activity`, locks, replication, connection budgets and WAL.

**MongoDB:** inspect elections, majority write concern, oplog and WiredTiger cache.

**Elasticsearch:** inspect shards, merge throttling, threadpool rejections, fetch latency and disk IOPS.

**Redis:** inspect hot keys, evictions and origin pressure; add coalescing/jitter.

**Kafka/CDC:** inspect offsets, lag, DLQ, source WAL/oplog and deduplication.

**Snowflake:** inspect tasks, COPY/MERGE, warehouse history, credits and freshness.

**Kubernetes:** inspect events, HPA, PDB, OOM, CPU throttling and node allocatable.

**Security:** isolate compromised workload, revoke/rotate, preserve audit evidence.

**DR:** confirm RPO/RTO, backups, fencing, isolated restore and data reconciliation.

**Incident command:** record SEV, commander, customer impact, UTC timeline, actions, communications and postmortem.

## 100-point reliability acceptance assessment

| Domain | Points |
|---|---:|
| Architecture validation | 10 |
| Deployment and rollback | 10 |
| Observability | 15 |
| SLOs and reliability | 15 |
| Security and compliance | 15 |
| Capacity and performance | 10 |
| Backup and disaster recovery | 15 |
| Operational ownership/runbooks | 10 |
| **Total** | **100** |

**Pass:** 90+, all critical controls pass, evidence and owners present, human approval and tested rollback. The offline score is advisory; production acceptance requires live evidence and sign-off.

**Validation:** Offline source and automated tests published; exact committed execution, CI, real chaos experiments, security review and production acceptance pending.
