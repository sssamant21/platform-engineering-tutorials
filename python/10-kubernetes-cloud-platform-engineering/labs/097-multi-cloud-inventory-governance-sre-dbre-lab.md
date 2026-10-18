# Chapter 097 — Multi-Cloud Infrastructure Inventory and Governance SRE/DBRE Lab

[Executable project](097/README.md) · [Python source](097/multicloud.py) · [Automated tests](097/test_multicloud.py)

## Mission

Integrate AWS, Azure and GCP infrastructure inventory into a normalized, scoped, deterministic governance workflow for SRE/DBRE teams. Diagnose drift, ownership, compliance, storage pressure and cost while ensuring zero cloud writes.

```text
AWS / Azure / GCP fake inventory -> bounded pagination
 -> normalized composite identity -> complete/partial snapshots
 -> drift + ownership/tagging/capacity policy
 -> synthetic FinOps report -> SHA-256 advisory plan
 -> simulated approval -> no mutation
```

## Lab 1 — Execute and validate

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/097
python -m compileall -q multicloud.py test_multicloud.py
python -m unittest -v test_multicloud.py
python multicloud.py --dry-run
python multicloud.py --partial
```

## Lab 2 — Identity, normalization and pagination

Examine AWS account, Azure subscription and GCP project scope; compare provider-native IDs, including Azure ARM case-insensitivity. Reject malformed records and duplicate composite IDs. Exercise page and item budgets, repeated continuation tokens and incomplete inventories.

## Lab 3 — Drift and compliance

Create two snapshots and detect added, removed, changed and unchanged resources. Mark a collection incomplete and verify that resource disappearance is **unknown**, not a confirmed deletion. Flag missing production owner, missing cost center and storage free percentage below the illustrative 15% threshold. Design time-bounded exemptions.

## Lab 4 — Capacity and FinOps

Compute synthetic monthly cost by provider. Explain why this is not actual billing: AWS CUR/Cost Explorer, Azure Cost Management and GCP Billing Export are the authoritative cost data sources. Add a DBRE review checklist for Elasticsearch disk IOPS, PostgreSQL storage and replica lag, and MongoDB WiredTiger cache pressure.

## Lab 5 — Approval, dry-run and idempotency

Hash sorted normalized resources into a canonical advisory plan. Require simulated owner approval, matching plan digest and rollback evidence. Reject any action other than `review-findings`. Verify zero mutations even with approval.

## Production incident simulations

| # | Scenario | Expected result | Mode |
|---|---|---|---|
| 1 | AWS/Azure/GCP records | Normalize | Automated |
| 2 | Unsupported provider | Reject | Automated |
| 3 | Invalid scope/identity | Reject | Automated |
| 4 | Negative/NaN cost | Reject | Automated |
| 5 | Invalid storage headroom | Reject | Automated |
| 6 | Azure ARM ID casing | Normalize comparison | Automated |
| 7 | AWS ID casing | Preserve | Automated |
| 8 | Paginated inventory | Combine pages | Automated |
| 9 | Page/item budget | Fail closed | Automated |
| 10 | Repeated pagination token | Reject | Automated |
| 11 | Malformed page | Reject | Automated |
| 12 | Duplicate resource | Reject | Automated |
| 13 | Added/removed resource | Detect | Automated |
| 14 | Partial inventory | Suppress deletion claim | Automated |
| 15 | Owner drift | Detect | Automated |
| 16 | Missing production owner | Finding | Automated |
| 17 | Missing cost center | Finding | Automated |
| 18 | Storage pressure | Finding | Automated |
| 19 | Synthetic cost by cloud | Aggregate | Automated |
| 20 | Plan order variation | Same digest | Automated |
| 21 | Destructive action | Reject | Automated |
| 22 | Missing/mismatched approval | Hold | Automated |
| 23 | Missing rollback evidence | Hold | Automated |
| 24 | Simulated approval | Advisory only | Automated |
| 25 | AWS STS wrong account | Stop | Guided |
| 26 | Azure Entra ID wrong subscription | Stop | Guided |
| 27 | GCP ADC wrong project | Stop | Guided |
| 28 | Cloud API 429 | Bounded retry | Guided |
| 29 | Missing CloudWatch/Monitor data | Unknown | Guided |
| 30 | Multi-cloud cost spike | Reconcile billing | Guided |
| 31 | Elasticsearch IOPS bottleneck | Investigate disk latency/queue | Guided |
| 32 | PostgreSQL HA/failover risk | Check backups and replication | Guided |
| 33 | Orphaned production database | Owner review; no deletion | Guided |

## Operational runbooks

**Collection outage:** validate account/project, identity, IAM/RBAC, region, pagination and deadline. Mark snapshot incomplete.

**Drift spike:** check collector completeness, normalizer version, source-of-truth and recent approved changes.

**Orphaned resource:** confirm application dependency, backups, retention, ownership and approved ticket before any lifecycle action.

**Cost anomaly:** reconcile provider billing, tags, commitments, network and monitoring costs.

**Capacity risk:** check storage, IOPS, throughput, CPU/memory, failover headroom and service SLOs.

**Approval failure:** verify exact plan fingerprint, owner, authenticated approver, expiry and rollback; do not modify resources.

## 100-point final assessment

| Competency | Points |
|---|---:|
| Multi-cloud identity and normalization | 20 |
| Pagination, snapshot completeness and drift | 20 |
| Ownership, tagging and compliance | 20 |
| Capacity and FinOps | 15 |
| Approval, dry-run and idempotency | 15 |
| Incident response, tests and runbooks | 10 |
| **Total** | **100** |

**Pass:** ≥90/100, independently executed offline tests, correct partial-inventory behavior, no-write evidence and reviewed production runbooks.

**Validation:** Files are published. Exact committed runtime tests, CI and live AWS/Azure/GCP integrations remain pending.
