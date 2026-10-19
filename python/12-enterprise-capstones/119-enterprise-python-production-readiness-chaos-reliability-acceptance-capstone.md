# Chapter 119 — Enterprise Python Production Readiness, Chaos Engineering and Reliability Acceptance Capstone

**Part 12 — Enterprise Capstone Projects | Chapter 119/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/119-production-readiness-chaos-reliability-acceptance-sre-dbre-lab.md) · [Executable offline project and tests](labs/119/README.md)

## Learning objectives

Establish evidence-based production readiness reviews (PRRs) for Python API services, event workers, CDC pipelines and cloud data platforms. Validate architecture, security, delivery, observability, reliability, performance, capacity, backup/DR, on-call ownership and operational acceptance. Design safe chaos experiments and incident simulations; require measured SLOs, approvals and rollback plans before a production launch.

## 1. Enterprise readiness architecture

```text
   Product/business requirements + service ownership + data classification
                               |
               Architecture / threat / dependency review
                               |
    +-------------+------------+-------------+-------------+
    |             |            |             |             |
  CI/CD        Security      SLO/OTel      Capacity      Backup/DR
  SBOM         IAM/RBAC      RED/USE       load/soak     RPO/RTO
  signed       secrets       burn alerts   IOPS/pools    restore test
  artifacts    isolation     dashboards    FinOps        fencing
    |             |            |             |             |
    +-------------+------------+-------------+-------------+
                               |
                  Evidence + accountable owners
                               |
            100-point PRR score + mandatory critical gates
                               |
            human approval + tested rollback + canary
                               |
        progressive rollout -> monitoring -> accept/rollback
```

**Design rule:** A numerical readiness score is never a substitute for mandatory safety controls. Critical failure in deployment, security, reliability or disaster recovery blocks approval regardless of total points. Evidence must be attributable to a named owner and linked to a real artifact. The offline simulator evaluates sample metadata, not actual infrastructure.

## 2. Architecture validation and service boundaries

Document context/container/deployment diagrams, API contracts, data ownership, tenancy boundaries, authentication, message schemas, idempotency, retries, dead-letter handling, rate limits, timeout budgets, backpressure and dependency graphs. For PostgreSQL, MongoDB, Elasticsearch/OpenSearch, Redis, Kafka, Snowflake and Kubernetes, specify the system of record, read consistency, write ownership, disaster recovery tier, credential boundary and responsible team. Review synchronous fanout, cyclic dependencies, shared failure modes and blast radius. Use ADRs for tradeoffs.

## 3. Production readiness review (PRR)

Gather: architecture diagram and ADRs; threat model and access review; signed artifacts/SBOM/dependency scan; CI test evidence; runbooks; on-call rotation; SLO document and alert routes; capacity/load/soak evidence; backup restore drill and RPO/RTO; incident exercises; deployment and rollback rehearsal; cost and data retention controls. Define owners, dates, evidence links, risk acceptance and exception expiration. PRR is a repeatable process for major architectural changes, not a one-time checklist.

## 4. Deployment gates and progressive delivery

Require deterministic builds, protected branches, code review, pinned dependencies, vulnerability triage, immutable images, least-privilege CI, staging integration tests, database migration rollback compatibility, change window, canary analysis and rollback automation. Define progressive traffic stages (for example 1%, 5%, 25%, 100%) only after measuring stable cohorts and sufficient sample size; percentages are illustrative, not universal defaults. Stop on 5xx, p99, saturation, DB pool exhaustion, Kafka lag, stale CDC or security anomalies. Production promotion requires a human or approved governance process, not merely a passing script.

## 5. Observability and SLO acceptance

Instrument OpenTelemetry traces with propagation across API -> Kafka -> CDC -> database, structured logs with secret/PII redaction, Prometheus RED metrics for request rate/errors/duration, USE metrics for CPU/memory/IOPS/queue saturation, and business freshness/availability SLIs. Define SLO windows, measurement source, low-traffic/no-data policy, error-budget ownership and burn-rate alert routing. Calculate remaining budget as allowed bad events minus observed bad events; burn rate compares current bad-event ratio to the permitted fraction. Use multiwindow confirmation and distinguish alert quality from service quality. No traffic is **unknown**, not automatic success.

## 6. Security and compliance acceptance

Review workload identity federation, IAM/RBAC, tenant authorization, network policies, TLS, KMS/secret rotation, artifact signatures, SBOMs, dependency scanning, audit retention, sensitive-data access, backup encryption and break-glass. Capture security review owner, critical findings and approved mitigations. Regulatory mappings (e.g., HIPAA, SOC 2, ISO 27001) require organizational evidence and expert review; a green checklist is not a certification.

## 7. Capacity and performance acceptance

Profile Python CPU/heap and async blocking; baseline throughput, p95/p99, memory RSS, disk IOPS/throughput and queue age. Budget Kubernetes replicas and node headroom, PostgreSQL connections (pods × pool), MongoDB cache, Elasticsearch shard/merge pressure, Redis hot-key load, Kafka partitions/lag and Snowflake credits. Run staging ramp/spike/soak tests with synthetic data and explicit traffic limits. Gate on latency, errors, CPU, memory and DB connection utilization; preserve N+1 failure headroom and rollback capacity.

## 8. Backup, disaster recovery and data correctness

Define RPO/RTO for each service and end-to-end business workflow. Verify actual recoverability: PostgreSQL PITR/WAL, MongoDB snapshot/oplog, Elasticsearch snapshot/CCR where supported, Redis persistence or controlled cache rebuild, Kafka topic/schema/ACL/offset reconciliation, Snowflake replication/failover capabilities, Kubernetes manifests and identity/KMS prerequisites. Test isolated restores and writer fencing; avoid split-brain and double CDC ingestion. Confirm data counts/checksums and idempotent replay before reopening traffic.

## 9. Chaos engineering

Begin with a falsifiable steady-state hypothesis, measurable SLI, fault scope, expected recovery, experiment owner and explicit abort trigger. Use approved staging experiments for pod kill, node loss, region outage, network partition, database latency, Kafka lag, Redis outage and telemetry gap. Limit blast radius, duration and concurrent faults; preserve evidence and stop when SLO/error-budget or safety limits are breached. Fault injection must be implemented with reviewed tooling in isolated environments; the included Python lab only **plans** faults, never injects them.

## 10. Incident response and reliability game days

Assign incident commander, operations lead, communications and scribe. Define SEV1/SEV2/SEV3 based on impact and urgency, with escalation, status cadence, UTC timeline, hypothesis/evidence separation, mitigations, customer communication and postmortem action tracking. Run game days covering database connection exhaustion, Elasticsearch IOPS saturation, MongoDB elections, Redis stampede, Kafka lag, Snowflake pipeline freshness, Kubernetes OOM, credential compromise and multi-region failover. Validate on-call paging and service ownership; a runbook without a practiced responder is incomplete.

## 11. Reliability acceptance scoring

| Control domain | Points | Critical |
|---|---:|---|
| Architecture and dependency validation | 10 | No |
| Deployment/rollback and CI/CD | 10 | Yes |
| Observability and incident detection | 15 | No |
| Reliability, SLOs and error budgets | 15 | Yes |
| Security and compliance controls | 15 | Yes |
| Capacity and performance | 10 | No |
| Backup and disaster recovery | 15 | Yes |
| Operational ownership and runbooks | 10 | No |
| **Total** | **100** | |

Acceptance: **90+ points**, all mandatory critical domains passing, named owners and evidence for every domain, approval recorded, and rollback tested. A missing domain, critical failure, untested rollback or absent approval means HOLD. Real acceptance additionally requires security/DBRE/SRE sign-off and live staging evidence.

## 12. Production troubleshooting runbooks

**API regression:** inspect RED, trace critical path, p99, recent changes, DB pool and retries; throttle/rollback safely.

**PostgreSQL:** inspect `pg_stat_activity`, locks, replication lag, pool budgets and WAL; preserve admin connections.

**MongoDB:** inspect elections, replication lag, WiredTiger cache, query plans and write concern; reconcile uncertain writes.

**Elasticsearch:** inspect shard fanout, fetch latency, disk IOPS/queue, merges and threadpool rejections; reduce query pressure.

**Redis:** inspect hot keys, evictions and origin amplification; apply request coalescing and TTL jitter.

**Kafka/CDC:** inspect partition skew, offsets, lag, DLQ, source WAL/oplog and idempotency; replay under bounded rate.

**Snowflake:** inspect warehouse credits, query/task history, COPY/MERGE errors and data freshness.

**Kubernetes:** inspect events, probes, resource limits, HPA, PDBs and node allocatable; revert unsafe rollouts.

**DR invocation:** declare commander, verify backup and RPO/RTO, fence old writers, restore isolated dependencies, reconcile and approve cutover.

**Security incident:** isolate, revoke, rotate, preserve evidence, verify tenant boundaries and notify owners.

## 13. Hands-on capstone

The [full lab](labs/119-production-readiness-chaos-reliability-acceptance-sre-dbre-lab.md) and [offline project](labs/119/README.md) provide a typed evidence model, 100-point scoring, critical-domain gates, SLO/burn calculations, load-test guardrails, synthetic chaos plans, incident triage and automated regression tests. Exercise 40 production-style scenarios and document acceptance evidence.

**Validation boundary:** No real CI/CD gates, IAM validation, OTel/Prometheus integrations, cloud API calls, fault injection, live load testing or production writes. Source and tests published; exact committed execution, staging validation, CI and production acceptance remain pending.

**Next:** Chapter 120 — Enterprise Python Final SRE/DevOps/DBRE Capstone, Operational Assessment and Curriculum Completion.
