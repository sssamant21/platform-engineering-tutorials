# Chapter 096 — Google Cloud Infrastructure and Operations SRE/DBRE Lab

[Executable project](096/README.md) · [Offline simulator](096/gcp_lab.py) · [Automated tests](096/test_gcp_lab.py) · [Optional GCP SDK inventory](096/live_inventory.py)

## Objective

Build safe GCP SRE/DBRE infrastructure diagnostics across IAM/ADC, Workload Identity, Compute Engine, GKE, Cloud SQL, Cloud Monitoring, capacity, cost and change governance.

```text
Approved project + zone -> synthetic paginated inventory
  -> fresh metrics + capacity/cost policy
  -> SHA-256 change plan + simulated approval
  -> advisory JSON report / zero cloud writes
```

## Lab 1 — Execute

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/096
python -m compileall -q gcp_lab.py live_inventory.py test_gcp_lab.py
python -m unittest -v test_gcp_lab.py
python gcp_lab.py --dry-run
python gcp_lab.py --pressure
```

## Lab 2 — IAM and Workload Identity

Compare ADC, attached service accounts and Workload Identity Federation for GKE. Validate project, quota project, service principal and least-privilege Compute/GKE/Cloud SQL/Monitoring Viewer roles. Never store service-account JSON keys in the repository.

## Lab 3 — Compute/GKE/Cloud SQL inventory

Paginate fake resource responses, reject malformed pages and duplicate IDs, enforce budgets. Optionally run approved staging read-only Compute and GKE SDK inventory; see project README. Design a Cloud SQL Admin API collector as an extension; no live Cloud SQL API calls are implemented.

## Lab 4 — Cloud Monitoring and capacity

Validate synthetic metric timestamps and values, simulate CPU pressure and storage headroom, and design Cloud Monitoring time-series queries for Compute CPU, GKE nodes and Cloud SQL storage/CPU. Missing data is unknown, not zero.

## Lab 5 — FinOps

Calculate a synthetic hourly-rate planning proxy and identify exclusions: disks, backups, egress, commitments, logging, Cloud SQL HA. Design BigQuery Billing Export reconciliation.

## Lab 6 — Change safety

Create a canonical SHA-256 advisory plan digest. Reject destructive action names; require simulated owner approval and rollback evidence. All modes make **zero cloud mutations**. Production authorization requires authenticated, expiring approvals.

## Incident simulations

| Scenario | Expected result | Mode |
|---|---|---|
| Invalid project or zone | Reject | Automated |
| Paginated/empty inventory | Correct list | Automated |
| Page/item budget exceeded | Fail closed | Automated |
| Repeated pagination token | Reject | Automated |
| Malformed page | Reject | Automated |
| Duplicate or incomplete resource | Reject | Automated |
| Stale/future/NaN metric | Reject | Automated |
| High CPU / low storage headroom | Alert | Automated |
| Invalid capacity or cost | Reject | Automated |
| Destructive change action | Reject | Automated |
| Missing approval / wrong digest | Hold | Automated |
| Untested rollback | Hold | Automated |
| Approved advisory change | No writes | Automated |
| ADC wrong project | Stop | Guided |
| Workload Identity failure | Inspect IAM/federation | Guided |
| Compute API 429 | Bounded retry | Guided |
| GKE control-plane degradation | Inspect node pools | Guided |
| Cloud SQL storage pressure | Validate backups/IOPS | Guided |
| Cloud SQL failover | Check HA and connections | Guided |
| Cloud Monitoring missing series | Mark unknown | Guided |
| Billing spike | Reconcile export | Guided |
| Regional outage | Review DR/RPO/RTO | Guided |
| Elasticsearch/PostgreSQL latency | Correlate disk and workload | Guided |

## Production runbooks

**ADC/IAM:** verify project, quota project, principal and federation; do not log credentials.

**Compute:** inspect VM status, serial logs, operations, quotas, disk and monitoring.

**GKE:** inspect cluster status, node pools, CNI, Pod events, autoscaling and workload identity.

**Cloud SQL:** inspect CPU, storage, connections, backups, HA, PITR and replication.

**Cloud Monitoring:** validate filter, resource labels, time interval, aggregation and freshness.

**FinOps:** verify Billing Export, commitments, labels, egress and delayed charges.

**Change control:** require independently authenticated approval, rollback, SLO evidence and audit before production writes.

## 100-point assessment

| Area | Points |
|---|---:|
| IAM, ADC and Workload Identity | 20 |
| Compute/GKE/Cloud SQL inventory and pagination | 20 |
| Monitoring, capacity and SLOs | 20 |
| Cost governance | 10 |
| Approval, retries, idempotency and dry-run | 15 |
| Automated tests, incidents and runbooks | 15 |
| **Total** | **100** |

**Pass:** ≥90/100 plus independent test execution, scope review and zero-write evidence.

**Validation:** Files are published; committed runtime tests, CI and live GCP integration remain pending.
