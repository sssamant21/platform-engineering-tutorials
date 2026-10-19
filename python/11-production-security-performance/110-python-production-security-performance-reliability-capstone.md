# Chapter 110 — Python Production Security, Performance and Reliability Capstone

**Part 11 — Production Security and Performance | Chapter 110/120 | Python 3.11+**

[Complete SRE/DBRE capstone lab](labs/110-production-security-performance-reliability-capstone-sre-dbre-lab.md) · [Executable project](labs/110/README.md)

## Capstone mission

Integrate the controls and operational methods of Chapters 101–109 into a coherent Python production-readiness workflow for SRE, DevOps, DBRE and platform engineers. Evaluate a fictional Python API and worker stack backed by PostgreSQL, Elasticsearch/OpenSearch, MongoDB, Redis, Kafka and Kubernetes. The offline project produces evidence and a **non-executing** release decision; it does not deploy or change resources.

## Reference architecture

```text
Git commit -> dependency manifest / SBOM / provenance / security checks
                |
       identity + least privilege + secret lifecycle
                |
       compliance evidence + policy-as-code gates
                |
   profiling + latency budgets + bounded concurrency
                |
     OTel traces + structured logs + Prometheus RED/USE
                |
       SLI/SLO + error budget + resilience controls
                |
       advisory release gate + independent approval
                |
   staging canary -> progressive production release
                |
      monitoring, rollback, incident runbooks
```

## Integration map: Chapters 101–109

| Chapter | Capability | Capstone acceptance |
|---|---|---|
| 101 | Secure coding and threat modeling | Input validation, data classification and risk register |
| 102 | Identity, authentication and authorization | Least-privilege workload roles, denied unauthorized action |
| 103 | Secrets, encryption and key lifecycle | Metadata-only rotation check; no secrets exported |
| 104 | Security auditing, compliance and policy-as-code | Evidence completeness, fail/unknown control handling |
| 105 | Secure software supply chain | Dependency metadata, hashes, SBOM/provenance review |
| 106 | Performance profiling and optimization | p50/p95/p99, representative benchmark and regression budget |
| 107 | Async, threading and parallel processing | Bounded workers/queues and overload rejection |
| 108 | Observability, tracing and reliability | Structured logs, RED/USE, SLI/SLO and burn-rate alert design |
| 109 | Resilience and fault injection | Bounded retries, circuit breakers, bulkheads and safe chaos gates |

## 1. Threat model and security boundaries

Document trust boundaries: user -> API -> service identity -> data stores; developer -> source repository -> CI runner -> artifact registry -> Kubernetes admission. Assess injection, privilege escalation, secrets exposure, dependency compromise, lateral movement, unsafe deserialization and audit-log tampering. Apply least privilege, authentication, authorization, network policy, TLS, encryption and immutable release artifacts. No single check proves security.

## 2. Identity, secrets and key management

Use workload identities and short-lived tokens instead of static shared credentials. Validate role assignment and separation of duties; never treat possession of a service token as permission to perform arbitrary database administration. Store secrets in approved vaults, audit access, rotate based on risk and test rollback across versions. The executable simulator inspects metadata only; it never reads or rotates real secrets.

## 3. Compliance and evidence governance

Map illustrative CIS, NIST SP 800-53 and SOC 2 controls to evidence owners, systems, collection timestamps, provenance and retention. Missing evidence is **unknown**, not pass. Track approved exceptions with scope, reason, expiry and compensating controls. A technical evidence report is not an audit certification; confirm mapping with compliance owners.

## 4. Software supply chain

Use pinned dependency versions and hashes, reviewed indexes, SBOMs (CycloneDX/SPDX), vulnerability scanning and SLSA-style provenance. Validate publisher identity, build provenance, signatures and release digest through approved tooling. A SHA-256 digest detects changes; it **does not authenticate the publisher**. The offline simulator validates hash syntax and trust flags only, not actual artifact bytes or cryptographic signatures.

## 5. Performance and concurrency

Baseline request classes, load, throughput, p95/p99 and errors. Use `cProfile`, `tracemalloc` and approved sampling profilers to isolate CPU/memory bottlenecks; do not mistake a microbenchmark for production proof. Size `asyncio` semaphores, thread/process pools and database connections within Kubernetes quotas and backend limits. Reject overload rather than creating unbounded queues.

## 6. Observability and SLOs

Instrument OpenTelemetry spans with safe context propagation; structured logs with redaction; Prometheus counters/histograms/gauges; RED/USE dashboards; and actionable SLO burn-rate alerts. Compare trace and resource evidence across PostgreSQL locks/pool waits, Elasticsearch search rejections/IOPS, MongoDB pool waits, Kafka consumer lag and Kubernetes CPU throttling. Never average per-pod p99 into fleet p99.

## 7. Resilience and change management

Apply deadlines, idempotent retries, bounded exponential backoff with jitter, circuit breakers, bulkheads, queue admission and graceful degradation. Define canary thresholds, rollback conditions, owner approval and data consistency checks. Fault injection belongs in approved isolated environments with explicit stop conditions. The capstone has no live chaos or release operations.

## 8. Release-readiness decision

Treat identity, secrets, compliance, supply chain, latency and SLOs as separate gates. Unknown evidence blocks readiness. Approval is an independent requirement; no automatic deployment occurs even if the advisory gate is ready. Preserve immutable evidence, code commit, change ticket, environment, timestamps and human decision.

## 9. Production incident playbooks

**Credential compromise:** restrict access, rotate/revoke through approved workflows, preserve logs and verify workload recovery.

**Dependency compromise:** block artifact promotion, compare SBOM/provenance, rebuild from trusted sources and revoke affected credentials.

**PostgreSQL pool exhaustion:** inspect aggregate connections, locks, query latency and retry amplification; cap inflight work.

**Elasticsearch latency:** inspect search fanout, shard size, disk IOPS and rejections before changing concurrency.

**MongoDB failover:** validate retryable writes, driver behavior and data consistency.

**Kafka lag:** investigate CPU-bound consumers, partition ordering, rebalance and offset commits.

**Kubernetes regression:** inspect rollout, resource limits, OOM/throttling, readiness and revert if SLO gates fail.

**Telemetry outage:** classify evidence coverage as unknown; protect request path from exporter failures.

## 10. Hands-on assessment

The [complete lab](labs/110-production-security-performance-reliability-capstone-sre-dbre-lab.md) and [executable project](labs/110/README.md) include identity, secret metadata, compliance, package metadata, latency, bounded concurrency, SLO, retry, log redaction and release gate modules, automated tests, incident simulations, troubleshooting and a 100-point final assessment.

**Limitations:** The code is an educational offline simulator, not a production-grade security scanner, identity provider, cryptographic verifier, profiler, OTel SDK, CI pipeline or deployment controller. Automated tests are published; exact committed runtime validation, live integrations, security review and operational acceptance remain pending.

**Next:** Chapter 111 — Enterprise Python SRE/DBRE Capstone Architecture and Project Foundations, beginning Part 12.
