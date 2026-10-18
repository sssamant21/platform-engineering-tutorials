# Chapter 095 — Azure Infrastructure and Cloud Operations SRE/DBRE Lab

[Executable project](095/README.md) · [Offline Python](095/azure_lab.py) · [Automated tests](095/test_azure_lab.py) · [Optional Azure SDK inventory](095/live_inventory.py)

## Mission and architecture

Develop safe Azure infrastructure diagnostics for VMs, AKS, PostgreSQL Flexible Server, Azure Monitor, Microsoft Entra ID, managed identity, capacity, FinOps and operational approval.

```text
Approved Entra ID identity -> subscription/resource group
        -> Azure SDK inventory (optional, read-only)
        -> synthetic ARM pages and metrics (default)
        -> capacity and cost policy checks
        -> SHA-256 advisory change plan
        -> simulated approval + rollback evidence
        -> JSON report / zero writes
```

## Lab 1 — Run offline

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/095
python -m compileall -q azure_lab.py live_inventory.py test_azure_lab.py
python -m unittest -v test_azure_lab.py
python azure_lab.py --dry-run
python azure_lab.py --pressure
```

## Lab 2 — Entra ID and managed identity

Compare `AzureCliCredential`, `ManagedIdentityCredential` and `DefaultAzureCredential`. Validate tenant and subscription before inventory. Design resource-group-scoped Reader/Monitoring Reader assignments and an AKS workload identity flow. No real role assignments are created.

## Lab 3 — VM, AKS and PostgreSQL inventory

Exercise synthetic paginated ARM responses with item/page budgets. Reject cross-subscription resources, duplicate IDs and missing state. Optionally execute read-only VM and AKS SDK listing using an explicitly approved staging subscription and resource group (see project README). Design PostgreSQL Flexible Server collection as an extension; the live adapter does not implement it.

## Lab 4 — Azure Monitor and capacity

Validate synthetic metric freshness and numeric integrity. Simulate CPU pressure and low free-storage headroom. Design Azure Monitor queries for VM CPU/disk metrics, AKS node health and PostgreSQL connections/storage/latency. Correlate infrastructure with application SLOs and DBRE evidence. Missing metrics mean unknown, never zero.

## Lab 5 — Cost and governance

Compute a synthetic hourly rate proxy. Explain exclusions: disks, snapshots, network egress, Log Analytics ingestion, reservations, savings plans and taxes. Design a Cost Management Query/Export workflow and budget alert. No live billing query is implemented.

## Lab 6 — Change gate, dry-run and audit

Bind resource ID, subscription, resource group, incident and approved advisory action into a canonical plan digest. Simulate owner approval and rollback evidence. Reject destructive actions. Even an approved simulated plan has **zero mutations**; production approvals require external authentication and expiry.

## Production incident simulations

| # | Scenario | Expected behavior | Mode |
|---|---|---|---|
| 1 | Valid subscription | Accept | Automated |
| 2 | Invalid subscription | Reject | Automated |
| 3 | Invalid resource group | Reject | Automated |
| 4 | Paginated inventory | Combine pages | Automated |
| 5 | Empty inventory | Empty result | Automated |
| 6 | Page/item budget | Fail closed | Automated |
| 7 | Repeated continuation token | Reject | Automated |
| 8 | Malformed page | Reject | Automated |
| 9 | Cross-subscription resource | Reject | Automated |
| 10 | Duplicate resource ID | Reject | Automated |
| 11 | Missing provisioning state | Reject | Automated |
| 12 | Fresh metric | Accept | Automated |
| 13 | Stale/future metric | Reject | Automated |
| 14 | NaN/negative metric | Reject | Automated |
| 15 | CPU/storage pressure | Alert | Automated |
| 16 | Invalid capacity | Reject | Automated |
| 17 | Cost proxy | Calculate | Automated |
| 18 | Negative cost input | Reject | Automated |
| 19 | Invalid change action | Reject | Automated |
| 20 | Cross-resource-group change | Reject | Automated |
| 21 | Missing approval | Hold | Automated |
| 22 | Wrong digest | Hold | Automated |
| 23 | Untested rollback | Hold | Automated |
| 24 | Dry-run | Zero mutations | Automated |
| 25 | Expired Entra ID token | Reauthenticate | Guided |
| 26 | Managed identity federation failure | Inspect identity/role | Guided |
| 27 | Azure RBAC 403 | Inspect scope | Guided |
| 28 | ARM throttling 429 | Bound retries | Guided |
| 29 | VM provisioning failure | Check Activity Log | Guided |
| 30 | AKS node pool unavailable | Check quota, CNI, identity | Guided |
| 31 | PostgreSQL Flexible Server storage pressure | Verify IOPS, backups, HA | Guided |
| 32 | Azure Monitor missing datapoints | Mark unknown | Guided |
| 33 | Cost spike | Validate billing scope | Guided |
| 34 | Elasticsearch Azure disk IOPS bottleneck | Check SKU/throughput/queue | Guided |

## Troubleshooting runbooks

**Authentication:** verify `az account show`, tenant, subscription, managed identity and role assignment. Never log tokens.

**ARM inventory:** validate scope, resource provider, pagination, 429 retry policy and item budgets.

**AKS:** inspect control plane, node pools, CNI, quota, workload identity and Kubernetes RBAC.

**PostgreSQL:** check storage, IOPS, connection saturation, backups, HA and failover health; do not blindly restart.

**Azure Monitor:** validate metric namespace, dimensions, time grain, aggregation and freshness.

**FinOps:** reconcile Cost Management scope, delayed charges, tags, disk and network costs.

**Change control:** require independently authenticated approval, rollback, SLO evidence and resource ownership.

## 100-point assessment

| Competency | Points |
|---|---:|
| Entra ID, managed identity, Azure RBAC | 20 |
| VM/AKS/PostgreSQL inventory and pagination | 20 |
| Azure Monitor, capacity and SLOs | 20 |
| Cost and FinOps governance | 10 |
| Approval, dry-run, idempotency, retries | 15 |
| Automated tests, incidents and runbooks | 15 |
| **Total** | **100** |

**Pass:** ≥90/100, independently executed offline tests, scope validation, no-write evidence and reviewed runbooks.

**Validation:** Files are published; exact committed runtime tests, CI and live Azure SDK integration remain pending.
