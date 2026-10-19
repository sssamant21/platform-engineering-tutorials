# Chapter 111 — Enterprise Python SRE/DBRE Capstone Architecture and Project Foundations

**Part 12 — Enterprise Capstone Projects | Chapter 111/120 | Python 3.11+**

[Complete hands-on SRE/DBRE lab](labs/111-enterprise-python-architecture-project-foundations-sre-dbre-lab.md) · [Offline executable project](labs/111/README.md)

## Learning objectives

Design an enterprise Python API/worker platform with explicit dependency contracts, fault domains, trust boundaries, deployment architecture, testable repository structure, bounded concurrency, telemetry and operational recovery. Establish the foundation for Chapters 112–120 with real-world PostgreSQL, Elasticsearch/OpenSearch, MongoDB, Redis, Kafka and Kubernetes patterns. The executable lab is a deterministic **offline architecture evaluator**, not a running production API.

## Architecture

```text
External clients -> Ingress/WAF/TLS -> Python API replicas (stateless)
                                          |
                  +-----------------------+--------------------+
                  |                       |                    |
          PostgreSQL transactions    Elasticsearch search   MongoDB documents
                  |                       |                    |
                  +------------ Redis cache / cache-miss protection
                                          |
                                    Kafka producer
                                          |
                        Kafka partitions / consumer groups
                                          |
                      Python workers / bounded job execution
                                          |
                     PostgreSQL / MongoDB / Elasticsearch
                                          |
             Kubernetes EKS/AKS/GKE: identity, policy, HPA, PDB
                                          |
              OTel Collector / Prometheus / logs / alerting
```

Separate request paths from asynchronous workers; isolate pool budgets, secrets, service accounts and namespaces. A Kubernetes Deployment is appropriate for stateless API/worker pods; persistent data services usually have separate managed or operator-controlled lifecycles.

## 1. Requirements and architecture decisions

Define functional requirements (read/write APIs, search, document access, cache, event processing) and nonfunctional requirements (availability, p99 latency, RPO/RTO, throughput, durability, compliance, multi-tenancy, cost and recoverability). Record architecture decision records (ADRs): chosen data ownership, eventual consistency, delivery semantics, retry policy, cloud/provider, encryption, backup and rollback. Build dependency maps and failure mode analysis before implementation.

**Sample objectives (illustrative, not verified):** API p99 under 200 ms for a specified request class; availability SLO 99.9% monthly; maximum API inflight 50 per pod; Kafka lag within an agreed window; documented PostgreSQL restore RPO/RTO. Real targets require workload baselines and business approval.

## 2. Recommended project layout

```text
enterprise-python-platform/
  pyproject.toml
  README.md
  docs/
    architecture.md
    adr/0001-data-ownership.md
    threat-model.md
    slo.md
    runbooks/
  src/platform_app/
    api/
      routes.py
      schemas.py
      dependencies.py
    workers/
      consumer.py
      jobs.py
    domain/
      models.py
      services.py
    ports/
      repositories.py
      search.py
      events.py
    adapters/
      postgres.py
      elasticsearch.py
      mongodb.py
      redis.py
      kafka.py
    security/
      auth.py
      secrets.py
    telemetry/
      tracing.py
      metrics.py
    config.py
  tests/
    unit/
    contract/
    integration/
    resilience/
    performance/
  deploy/
    kubernetes/
    helm/
  ci/
```

Use ports/adapters to keep domain logic independent of cloud SDKs. Apply typed interfaces, dependency injection, strict configuration validation and environment separation. This is a **target architecture**; the executable Chapter 111 lab contains only the offline evaluator and tests.

## 3. Python API and worker design

Prefer an async-capable web framework where appropriate; do not block the event loop with synchronous database clients. Separate authentication, input validation, request correlation, domain services and persistence adapters. Use bounded async semaphores and thread/process pools. Define idempotency keys, deadlines, per-dependency connection pools, cancellation and graceful shutdown.

Kafka workers must control inflight messages, partition ordering, offset commits and rebalance handling. At-least-once delivery requires idempotent handlers; exactly-once semantics depend on end-to-end system boundaries, not Kafka configuration alone.

## 4. PostgreSQL integration

Use PostgreSQL as authoritative transactional storage for explicitly owned entities. Define migrations, isolation levels, indexes, pool limits, statement timeouts, TLS, IAM/secret rotation, replication, PITR and connection budgets. **Aggregate pool demand = replicas × per-replica max pool**; reserve headroom for migrations, admin and other services. Monitor `pg_stat_activity`, lock waits, slow queries, WAL and replica lag.

## 5. Elasticsearch/OpenSearch integration

Use search indexes as derived projections, not the transactional source of truth. Define index mappings, analyzers, shard sizes, alias-based versioned rollouts, refresh strategy and reindex workflows. Protect cluster capacity with bounded fanout, `search_after` for deep pagination, query timeouts and retries with jitter for retryable rejections. Monitor search threadpool rejections, fetch latency, disk IOPS, shard growth and merge pressure.

## 6. MongoDB integration

Own document-centric records and enforce schema validation, index design, TTL/retention, read/write concern, driver pool caps, replica-set failover and backups. Avoid cross-database dual writes without an outbox/CDC or compensating reconciliation design. Monitor WiredTiger cache/eviction, query plans, replication lag, connection wait and oplog retention.

## 7. Redis integration

Treat Redis as a cache or explicitly designed state service, not a substitute for transactional durability. Define key namespaces, TTL, invalidation, stampede protection, cache-aside/read-through/write-through tradeoffs and fail-open/fail-closed semantics. Monitor memory pressure, evictions, latency, hot keys and source DB overload during cache misses.

## 8. Kafka integration

Define event schemas, compatibility, partitions, consumer groups, delivery guarantees, dead-letter policy, retry topics, idempotency, backpressure, offsets and lag SLOs. Use transactional outbox or CDC where data/event atomicity is required. Distinguish producer acknowledgment from downstream business completion.

## 9. Kubernetes and cloud boundaries

Use namespace isolation, workload identity (IRSA/Pod Identity, Azure Workload Identity, GKE Workload Identity Federation), least-privilege RBAC, NetworkPolicies, secrets integration, resource requests/limits, HPA, PDBs, probes and topology spread. Separate app delivery from DB infrastructure lifecycle and apply GitOps review/approval. Define readiness that reflects the ability to serve traffic without cascading dependency checks.

## 10. Observability and SRE reliability

Implement OTel spans across API, worker, database and messaging boundaries; structured redacted logs; Prometheus RED/USE metrics; service-level SLIs, SLOs and error budgets. Alert on sustained user impact, pool exhaustion, Kafka lag, disk latency, CPU throttling and data correctness. Use sampling and bounded labels to manage cardinality and privacy. Establish incident ownership, escalation, rollback, backup/restore drills and evidence retention.

## 11. Security and compliance

Threat-model ingress, CI/CD, identity, data stores and event pipelines. Apply TLS, encryption, secret rotation, dependency pinning, SBOM/provenance verification, audit logging and supply-chain policy gates. Handle PHI/PII according to applicable organizational controls. Fail closed when required evidence is unknown; no teaching simulator substitutes for real authentication or policy enforcement.

## 12. Architecture review and operational runbooks

**PostgreSQL saturation:** inspect connection pools, locks, slow queries, total replica demand; throttle API and recover without amplifying load.

**Elasticsearch rejection/IOPS:** inspect shard fanout, search rejection counters and disk latency; reduce page size/concurrency and validate search SLO.

**MongoDB failover:** check driver retry behavior, primary election, write concern and oplog; reconcile uncertain writes.

**Redis stampede:** bound cache misses, singleflight/hot-key protections and source DB concurrency.

**Kafka lag:** inspect consumer CPU, partition skew, rebalance, batch size and commit correctness.

**Kubernetes outage:** inspect deployment rollout, probes, HPA, CPU throttling, OOM and node availability; revert immutable image if necessary.

**Telemetry outage:** mark missing evidence unknown and preserve application health; investigate Collector/exporter queue and credentials.

## 13. Lab and assessment

The [complete lab](labs/111-enterprise-python-architecture-project-foundations-sre-dbre-lab.md) and [offline Python project](labs/111/README.md) implement validated dependency topology, per-edge timeout/concurrency/retry contracts, connection budget checks, queue admission, p99/SLO analysis, identity/rotation/trace/rollback gates, synthetic failure classification and automated tests.

**Validation boundary:** The Chapter 111 project has no live API, Kafka consumer, database drivers, Kubernetes manifests, OTel exporter or production mutations. Test code is published; exact committed runtime execution, integration tests, architecture/security review and production acceptance remain pending.

**Next:** Chapter 112 — Enterprise Python API Services, Contracts and Data Access Integration.
