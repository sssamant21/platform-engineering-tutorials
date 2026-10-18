# Chapter 100 — Cloud-Native Platform Engineering Production Capstone Lab

[Project README](100/README.md) · [Python engine](100/capstone.py) · [51 automated tests](100/test_capstone.py)

## Scenario

You are the on-call SRE/DBRE responsible for a patient-facing application spanning AWS RDS, Azure AKS, GCP Cloud SQL and Kubernetes. A new deployment coincides with increased errors, low storage headroom, inconsistent GitOps revisions and an overdue credential rotation. Produce a safe incident report and a reviewable advisory change plan.

## Reference architecture

```text
AWS / Azure / GCP / Kubernetes synthetic inventory
       -> scoped identity and bounded pagination
       -> normalized resources + complete/partial snapshots
       -> GitOps / IAM / audit / rotation / capacity policy
       -> synthetic CloudWatch / Azure Monitor / GCP metrics
       -> SLO/error budget + incident correlation hypotheses
       -> FinOps estimate + SHA-256 scoped advisory plan
       -> independent approval + expiry + rollback evidence
       -> deterministic JSON, zero secret reads or writes
```

## Lab 1 — Execute

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/100
python -m compileall -q capstone.py test_capstone.py
python -m unittest -v test_capstone.py
python capstone.py --dry-run
python capstone.py --partial
```

Record test output, Python version, source revision, JSON output and zero-write evidence in the change ticket.

## Lab 2 — Inventory, cloud identity and GitOps

Validate AWS account, Azure subscription, GCP project and Kubernetes namespace; compare provider-native identifiers and duplicate detection. Exercise page and item budgets, malformed responses and repeated continuation tokens. Compare desired and observed GitOps revisions; investigate Argo CD/Flux sync and Kubernetes rollout health as a **guided extension**, not a live operation.

## Lab 3 — Telemetry, SLOs and incident correlation

Use synthetic AWS/Azure/GCP request counters. Calculate availability and budget consumption at a 99.9% target; verify stale/future and invalid counters fail closed. Deduplicate repeated signals, correlate by service/time and explicitly retain `causality=not-established`. Design a production OpenTelemetry trace and multi-window burn-rate alert.

## Lab 4 — IAM, secrets and compliance

Detect static workload identity, disabled audit, overdue rotation and missing production owner. Discuss AWS IAM roles/Secrets Manager, Azure Entra/Key Vault, GCP IAM/Secret Manager and Kubernetes RBAC/Secrets. Plan a PostgreSQL password rotation with version overlap, consumer verification and rollback; **do not retrieve or rotate credentials**.

## Lab 5 — Capacity and FinOps

Investigate simulated RDS storage headroom at 12%. Build a DBRE checklist for PostgreSQL WAL, connection pools, replication, backups, disk IOPS and latency. Compare with Elasticsearch shard/merge pressure. Reconcile synthetic costs against actual AWS CUR, Azure Cost Management and GCP Billing Export in a future production integration.

## Lab 6 — Approval, dry-run and idempotency

Bind a safe advisory action to provider, scope, resource ID, incident ticket and expected revision. Verify deterministic SHA-256 digest, separate owner/approver, approval expiry and rollback evidence. Reject `delete-db` and other destructive actions. Simulated approval **never** authorizes a write.

## Production incident simulations

| # | Scenario | Expected behavior | Mode |
|---|---|---|---|
| 1 | Four-provider resource inventory | Normalize | Automated |
| 2 | Invalid cloud provider | Reject | Automated |
| 3 | Invalid resource scope | Reject | Automated |
| 4 | Negative/NaN cost | Reject | Automated |
| 5 | Invalid storage headroom | Reject | Automated |
| 6 | Negative secret age | Reject | Automated |
| 7 | Azure ARM ID case variation | Compare correctly | Automated |
| 8 | Multi-page inventory | Collect | Automated |
| 9 | Page/item budget exceeded | Fail closed | Automated |
| 10 | Pagination loop | Reject | Automated |
| 11 | Malformed page | Reject | Automated |
| 12 | Duplicate or invalid record | Reject | Automated |
| 13 | Resource removal in complete snapshot | Detect | Automated |
| 14 | Removal in partial snapshot | Unknown | Automated |
| 15 | Resource ownership drift | Detect | Automated |
| 16 | Storage pressure | Finding | Automated |
| 17 | GitOps revision drift | Finding | Automated |
| 18 | Credential rotation overdue | Finding | Automated |
| 19 | Static identity or disabled audit | Finding | Automated |
| 20 | Missing production owner | Finding | Automated |
| 21 | Stale/future/invalid telemetry | Reject | Automated |
| 22 | Breached SLO | Flag | Automated |
| 23 | Missing SLO data | Unknown/error | Automated |
| 24 | Invalid SLO target | Reject | Automated |
| 25 | Repeated alerts | Deduplicate | Automated |
| 26 | Uncertain causality | Not established | Automated |
| 27 | Different services | Separate incidents | Automated |
| 28 | Synthetic FinOps | Aggregate | Automated |
| 29 | Destructive action | Reject | Automated |
| 30 | Missing/expired/self approval | Hold | Automated |
| 31 | Wrong plan digest or no rollback | Hold | Automated |
| 32 | Approved advisory | Zero writes | Automated |
| 33 | Wrong AWS STS account | Stop | Guided |
| 34 | Azure Entra/AKS RBAC denial | Investigate identity | Guided |
| 35 | GCP ADC wrong project | Stop | Guided |
| 36 | Kubernetes rollout failure | Inspect probes, PDB, events | Guided |
| 37 | Argo CD/Flux sync failure | Inspect desired revision | Guided |
| 38 | OpenTelemetry trace gaps | Inspect sampling/exporter | Guided |
| 39 | RDS/PostgreSQL connection exhaustion | Check pools, locks, HA | Guided |
| 40 | Cloud SQL disk saturation | Check IOPS, storage, backup | Guided |
| 41 | Elasticsearch oversized shards | Check merges, IOPS, search | Guided |
| 42 | Secret rotation outage | Halt revocation, restore consumers | Guided |
| 43 | Cloud API throttling | Bounded backoff | Guided |
| 44 | Multi-cloud cost anomaly | Reconcile billing | Guided |
| 45 | Regional outage | Follow tested DR/RPO/RTO | Guided |

## Production runbooks

**Identity failure:** validate principal, AWS account/Azure subscription/GCP project/Kubernetes context, permissions and quotas. Stop on mismatch.

**Inventory incomplete:** preserve last complete snapshot, mark unknown, investigate pagination and IAM. Never infer deletions.

**GitOps drift:** check desired Git revision, rollout, Argo CD/Flux health, probes, PDB and owner-approved emergency changes.

**SLO incident:** validate eligible traffic, metric freshness, time windows, trace context and customer impact. Escalate per error budget.

**DBRE saturation:** inspect storage IOPS, throughput, WAL, connections, replication, backups and shard pressure before scaling/failover.

**Secrets incident:** preserve audit, contain, identify consumers, stage rotation, validate and roll back as necessary.

**FinOps spike:** reconcile billing export, tags, discounts, egress, backups and observability.

**Approval hold:** require authenticated independent approval, expiry, exact plan fingerprint, rollback and audit. No write.

## Final 100-point enterprise assessment

| Area | Points |
|---|---:|
| Multi-cloud inventory and Kubernetes/GitOps | 20 |
| Observability, SLOs and incident correlation | 20 |
| IAM, secrets and compliance | 15 |
| DBRE capacity and FinOps | 15 |
| Safety, approval, dry-run and idempotency | 15 |
| Automated tests, simulations and runbooks | 15 |
| **Total** | **100** |

**Pass:** ≥90 points, 51 offline tests passing, no-write evidence, incident runbook review and explicit statement of missing live integration acceptance.

**Part 10 acceptance:** Theory, hands-on lab and executable project are published for Chapters 091–100. Live SDKs, CI and production readiness require separate engineering and security sign-off.
