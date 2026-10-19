# Chapter 110 — Production Security, Performance and Reliability: SRE/DBRE Capstone Lab

[Python evaluator](110/capstone.py) · [Automated tests](110/test_capstone.py) · [Project guide](110/README.md)

## Scenario

An enterprise Python service on Kubernetes serves API requests and background jobs. It depends on PostgreSQL, Elasticsearch, MongoDB, Redis and Kafka. A new release must pass security, identity, secrets, compliance, dependency trust, latency and reliability checks before an independently approved staging rollout. The local lab evaluates synthetic evidence only.

## Lab 1 — Baseline

```bash
cd python/11-production-security-performance/labs/110
python -m compileall -q capstone.py test_capstone.py
python -m unittest -v test_capstone.py
python capstone.py --dry-run
python capstone.py --partial
```

Confirm zero network calls, zero mutations and an advisory release decision. Record report SHA-256, source revision, timestamp and Python version for your own validation notes.

## Lab 2 — Security and supply chain

Exercise role-based authorization and least-privilege checks, secret rotation metadata, compliance pass/fail/unknown, dependency package version and hash-format checks. Explain what additional production validation is needed: real signature/provenance verification, SBOM completeness, vulnerability triage, OIDC trust, key custody and compliance exception approvals.

## Lab 3 — Performance and concurrency

Compute p50/p95/p99 and compare with a synthetic p99 budget. Model bounded inflight work, queue length and rejection. Write a real staging benchmark design with representative dataset, CPU quota, memory, downstream pool limits, throughput and rollback criteria.

## Lab 4 — Observability and reliability

Compute availability SLI, remaining error budget and retry classification. Design real OpenTelemetry trace context, structured log privacy controls, Prometheus RED/USE dashboards and multi-window burn alerts. Missing evidence must hold the release.

## Lab 5 — Production incident simulation workshop

| # | Incident | Expected investigation and response |
|---|---|---|
| 1 | Overprivileged service identity | Deny action; reduce roles |
| 2 | Missing role | Fail authorization |
| 3 | Stale secret | Require approved rotation |
| 4 | Unknown compliance control | Hold release and collect evidence |
| 5 | Failed compliance control | Remediate and reassess |
| 6 | Untrusted dependency | Quarantine artifact |
| 7 | Duplicate package | Reject manifest |
| 8 | Invalid package digest | Reject metadata |
| 9 | p99 regression | Halt canary |
| 10 | Unbounded queue pressure | Shed load and cap inflight |
| 11 | SLO budget breach | Block promotion |
| 12 | Non-idempotent retry | Block automatic replay |
| 13 | Sensitive log field | Redact and investigate privacy risk |
| 14 | Missing release approval | Hold |
| 15 | PostgreSQL pool exhaustion | Inspect pool wait, locks and aggregate replicas |
| 16 | PostgreSQL uncertain commit | Verify transaction outcome |
| 17 | Elasticsearch search rejection | Bound fanout and retries |
| 18 | Elasticsearch storage saturation | Inspect IOPS and queue depth |
| 19 | MongoDB primary transition | Verify write semantics and read preference |
| 20 | Redis cache outage | Protect origin from stampede |
| 21 | Kafka consumer lag | Inspect partition order and processing CPU |
| 22 | Kubernetes OOMKilled | Inspect RSS, limits and rollout |
| 23 | Kubernetes CPU throttling | Tune worker budget |
| 24 | OTel exporter outage | Preserve app health and mark coverage unknown |
| 25 | Credential compromise | Contain, rotate and audit |
| 26 | Dependency compromise | Verify provenance, rebuild and revoke |
| 27 | Retry storm | Apply jitter, attempt caps and load shedding |
| 28 | Circuit breaker flapping | Validate probes and dependency health |
| 29 | Cross-region failover | Verify fencing and consistency |
| 30 | Failed canary | Roll back and validate SLO recovery |

## Troubleshooting runbooks

**Identity/secret failure:** confirm affected principal, permissions, rotation metadata and access logs; never expose raw secret values in incident tickets.

**Supply-chain compromise:** stop artifact promotion, inspect verified SBOM and signatures, rebuild from trusted sources, assess affected deployments and preserve evidence.

**Performance regression:** correlate p99, CPU/memory profiling, Kubernetes throttling and database query/queue latency; restore previous release if gates fail.

**Data-store incident:** inspect PostgreSQL locks and pool wait, Elasticsearch shard/disk pressure, MongoDB connection waits and Kafka lag; avoid multiplying retry traffic.

**SLO burn:** validate good/eligible event definitions and telemetry completeness, mitigate user impact, preserve incident timeline and verify recovery.

**Rollback:** identify immutable prior release, confirm migration compatibility, restore traffic gradually, verify data consistency and capture approval/audit records.

## Final assessment — 100 points

| Domain | Points |
|---|---:|
| Secure architecture, threat model and least privilege | 15 |
| Secrets, compliance and evidence governance | 15 |
| Supply-chain controls and release provenance | 15 |
| Profiling, latency and concurrency design | 15 |
| Observability, SLOs and error budgets | 15 |
| Resilience, incidents and operational runbooks | 15 |
| Automated tests, validation and evidence | 10 |
| **Total** | **100** |

Pass: at least 90 points, local tests executed, no-write evidence, documented security/privacy limitations, and independently reviewed staging/production rollout and rollback plans.

**Validation:** This is a complete offline educational capstone, not a production-certified implementation. Exact committed test execution, CI, real integrations, cryptographic verification and production acceptance remain pending.
