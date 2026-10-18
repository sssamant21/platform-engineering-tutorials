# Chapter 100 — Python Cloud-Native Platform Engineering Production Capstone

**Part 10 final chapter | Chapter 100/120 | Python 3.11+**

[Complete hands-on lab](labs/100-cloud-native-platform-engineering-production-capstone-lab.md) · [Executable capstone project](labs/100/README.md)

## Learning outcomes and scope

Integrate Chapters 091–099 into an enterprise SRE/DevOps/DBRE operating model spanning Kubernetes, AWS, Azure and GCP. Design reliable read-only cloud inventory, GitOps reconciliation, OpenTelemetry and cloud monitoring, SLO/error-budget analysis, IAM and secrets governance, capacity/FinOps, incident correlation, approval-gated remediation and reproducible runbooks.

**Execution boundary:** The runnable capstone is an **offline, deterministic simulation**, not a live production controller. It contains no provider SDK integrations, Kubernetes API writes, secret value retrieval or cloud mutation functions. Real production adapters are an explicitly separate engineering phase.

## Architecture

```text
AWS STS / EC2 / EKS / RDS / CloudWatch ──┐
Azure Entra / AKS / PostgreSQL / Monitor ├─> scoped collectors (design)
GCP IAM / GKE / Cloud SQL / Monitoring ──┤             |
Kubernetes API / Argo CD / Flux ─────────┘             v
                                     normalized resource inventory
                                               |
                     ┌─────────────────────────┼──────────────────────┐
                     v                         v                      v
             GitOps revision drift     telemetry/SLO/incident   IAM/secrets audit
                     |                         |                      |
                     └─────────────────────────┼──────────────────────┘
                                               v
                              capacity + synthetic FinOps + policy
                                               |
                              SHA-256 scoped advisory change plan
                                               |
                     owner + independent approver + expiry + rollback
                                               |
                        immutable report; ZERO writes in published lab
```

## 1. Inventory and cloud identity

AWS boto3 STS `GetCallerIdentity`, EC2/RDS/EKS read-only paginators; Azure `azure-identity` and management clients scoped by tenant/subscription/resource group; GCP ADC and Compute/GKE/Cloud SQL read-only SDKs scoped by project/zone. Kubernetes Python client lists workloads with explicit cluster context and namespace. **These SDK integrations are architectural exercises, not executable code in the published simulator.**

Use a composite identity of provider, scope and native ID; preserve original resource IDs, audit provenance and collection completeness. A partial inventory must never imply a resource was deleted. Bound pages/items, deadlines and retries; retry transient 429/5xx with jitter and respect Retry-After, not authorization failures.

## 2. Kubernetes and GitOps reconciliation

Represent desired Git revision and observed workload revision. Argo CD and Flux continuously reconcile declared desired state with Kubernetes. Detect drift, health degradation, failed syncs, unhealthy Pods, readiness failures, insufficient PDBs and rollback constraints. Use immutable image digests, change ownership, promotion gates and staged canaries.

**Do not blindly auto-revert drift:** production emergencies and uncommitted hotfixes require human reconciliation. The offline lab compares two revision strings and raises a finding; it does not connect to Argo CD, Flux or Kubernetes.

## 3. Observability, OpenTelemetry and SLOs

AWS CloudWatch, Azure Monitor and Google Cloud Monitoring expose different dimensions, time grains and quotas. Normalize metric semantics, validate freshness and preserve source evidence. Use OpenTelemetry traces to correlate dependencies; a shared timestamp or service name is **not proof of causality**.

For request availability, `SLI = (total−bad)/total`. For target `T`, budget events `= total × (1−T)`. A measured-window consumption ratio `= bad/budget`. Production SLO paging should use multi-window burn-rate thresholds and appropriate minimum traffic, not only a single-window consumption ratio. Treat missing data as unknown, not zero or healthy.

## 4. Incident automation and deduplication

Normalize provider, scope, service and time. Deduplicate exact repeated signals and group service/time buckets to propose incident clusters. Preserve tenant/environment, trace IDs and source alerts in production. Correlate with deployment timeline, database latency, storage throughput and application SLIs before attributing root cause.

Examples: RDS PostgreSQL connection exhaustion; Azure AKS Pod scheduling failure; GCP Cloud SQL disk saturation; Elasticsearch shard/merge pressure; cross-cloud API latency and Kafka backlog. Always establish impact and blast radius before action.

## 5. IAM, secrets and compliance

Prefer AWS IAM roles, Azure managed identities, GCP Workload Identity Federation and Kubernetes workload identities over static keys. Review RBAC and policy scopes. Never log credentials or fetch secret payloads merely to assess compliance. Enforce production ownership, audit logging, credential age and reviewed rotation policy. Kubernetes Secret base64 encoding is not encryption.

A real rotation requires staged issuance, consumer validation, overlapping credentials when supported, version-aware rollback, application connection pool refresh and post-rotation monitoring. The simulator reports metadata-only policy findings.

## 6. Capacity and FinOps

Review CPU, memory, storage headroom, IOPS, throughput, quota, HA/replica headroom, backup retention and workload growth. For DBRE, differentiate query latency from storage saturation and account for large Elasticsearch shards, PostgreSQL WAL/replication lag and MongoDB cache behavior.

The lab sums **synthetic** monthly cost estimates; it does not query AWS CUR/Cost Explorer, Azure Cost Management or GCP Billing Export. Production rightsizing requires billing reconciliation, reserved/committed discounts, egress, backups, observability charges and SLO evidence.

## 7. Approval, idempotency, safety and audit

Separate `observe → propose → approve → execute → verify → rollback`. The published simulator implements **observe/propose** and a simulated approval gate only. A SHA-256 plan fingerprint binds provider, scope, resource, action, ticket and expected revision; it is not an authenticated signature. Require independent approver, expiry, reviewed rollback and blast-radius constraints. Even if `dry_run=False` and simulated approval succeeds, the lab returns zero writes.

Production integration must add authenticated approvals, scoped write adapters, leader election/leases, conflict detection, audit retention, bounded retry, idempotency keys, verification, rollback and security review.

## 8. Production incident scenarios

| Scenario | Safe investigation |
|---|---|
| AWS STS wrong account | Stop, validate role and account allowlist |
| Azure wrong subscription | Stop before collection |
| GCP ADC wrong project | Verify principal and project |
| Kubernetes API 403 | Review context, namespace and RBAC |
| Partial inventory | Mark unknown, suppress deletion conclusions |
| GitOps revision mismatch | Review deployment, drift and sync health |
| SLO budget exhaustion | Validate traffic, burn window and impact |
| Repeated multi-cloud alerts | Deduplicate and preserve provenance |
| RDS PostgreSQL storage pressure | Inspect storage, WAL, IOPS and backup |
| Azure AKS scheduling failure | Inspect node capacity, taints, quotas, PVCs |
| GCP Cloud SQL latency | Inspect CPU, storage, connections and HA |
| Elasticsearch shard pressure | Review shard size, merge, IOPS and queries |
| Credential rotation outage | Stop revocation, validate consumer rollback |
| Audit logging disabled | Open compliance incident and investigate gap |
| Cost anomaly | Reconcile cloud billing and resource ownership |
| Unauthorized remediation | Hold and audit |

## 9. Operational runbooks

**Collector outage:** validate scope, IAM/RBAC, quota, API latency, clock skew, pagination and completeness. Keep last good snapshot with freshness metadata.

**GitOps deployment failure:** check desired revision, controller sync, rollout health, probes, PDBs, canary SLO and rollback feasibility.

**SLO/incident response:** establish customer impact, telemetry completeness, trace/deployment context and escalation. Document uncertain causality.

**DBRE saturation:** review disk latency, IOPS, connections, locks, replica lag, shard pressure, backups and RPO/RTO before failover or scaling.

**Secrets incident:** contain, audit, identify consumers, rotate with staged validation and rollback; never print values.

**Cost/capacity:** compare provider billing exports, demand, headroom, discounts and service SLO before rightsizing.

**Approval failure:** check plan digest, exact resource, ticket, expected revision, approver independence, expiry and rollback; no writes.

## 10. Capstone deliverables and acceptance

The [hands-on lab](labs/100-cloud-native-platform-engineering-production-capstone-lab.md) and [executable project](labs/100/README.md) include a deterministic offline multi-cloud inventory, drift, SLO, incident, IAM/secrets and FinOps pipeline, **51 automated tests**, production simulations, runbooks and a 100-point assessment.

**Local validation:** The equivalent Python simulator passed 51 unit tests after fixing a resource ID validation issue. GitHub CI, execution of the exact committed revision, real SDK integrations and live production validation remain pending.

**Part 10 milestone:** Chapters 091–100 are published. **Next proposed: Chapter 101 — Python Production Security Architecture and Secure Coding.**
