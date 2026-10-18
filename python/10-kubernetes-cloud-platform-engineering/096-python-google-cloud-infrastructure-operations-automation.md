# Chapter 096 — Python Google Cloud Infrastructure and Operations Automation

**Part 10 — Kubernetes, AWS, Azure and GCP | Chapter 096/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/096-gcp-infrastructure-operations-sre-dbre-lab.md) · [Executable project](labs/096/README.md)

## Learning objectives

Implement safe Google Cloud operations using Python SDKs, Application Default Credentials (ADC), IAM and Workload Identity Federation, Compute Engine, GKE, Cloud SQL for PostgreSQL, Cloud Monitoring, inventory, capacity, FinOps and incident diagnostics. Apply pagination, bounded retries, approval gates, dry-run, idempotency and audit evidence.

## Architecture

```text
Workstation / CI / GKE workload
   -> ADC / Workload Identity Federation / attached service account
   -> project + region + zone allowlist
   -> read-only Google Cloud Python clients
   -> Compute Engine + GKE + Cloud SQL inventory
   -> Cloud Monitoring observations and cost context
   -> capacity/SLO policy -> advisory change fingerprint
   -> independently approved plan (production extension)
   -> audit JSON / no cloud writes in lab
```

The executable project provides a fully offline fake API and an optional explicitly authorized **read-only** Google Cloud SDK adapter. It does not modify GCP resources.

## 1. Authentication, IAM and Workload Identity

Use `google.auth.default()` for ADC after selecting the correct identity. Workstations may use `gcloud auth application-default login` with approved user credentials. Production workloads should use attached service accounts or **Workload Identity Federation** (including Workload Identity Federation for GKE) rather than downloaded service-account JSON keys. A GKE Kubernetes service account can be authorized through federation and IAM policies; Kubernetes RBAC and Google Cloud IAM are distinct.

Validate `project_id`, quota project, principal and allowed resource scope. Avoid logging tokens or service-account keys. Restrict service account impersonation, use IAM Conditions where appropriate and monitor IAM audit logs.

## 2. Google Cloud Python SDK clients

Representative packages: `google-cloud-compute`, `google-cloud-container`, `google-cloud-sql-connector` (for database connections, not Cloud SQL Admin inventory), `google-api-python-client` (Cloud SQL Admin API), `google-cloud-monitoring` and `google-auth`.

```python
import google.auth
from google.cloud import compute_v1, container_v1, monitoring_v3

credentials, adc_project = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
instances = compute_v1.InstancesClient(credentials=credentials)
clusters = container_v1.ClusterManagerClient(credentials=credentials)
metrics = monitoring_v3.MetricServiceClient(credentials=credentials)
```

The broad OAuth scope does not grant IAM permissions; IAM roles still determine allowed operations. Prefer the least-privilege roles needed for Compute Viewer, Kubernetes Engine Viewer, Cloud SQL Viewer and Monitoring Viewer, scoped to approved projects.

## 3. Compute Engine inventory

List VM instances per approved zone using `InstancesClient.list(project=...,zone=...)` or an aggregated list with proper scope filtering. Inspect instance name, machine type, status, zone, disk attachments and labels. VM `RUNNING` is not evidence that the application is healthy. Enforce maximum zones, pages, records and runtime. Never print startup scripts or instance metadata containing secrets.

## 4. GKE inventory and reliability

Use `ClusterManagerClient.list_clusters(parent="projects/PROJECT/locations/LOCATION")` to enumerate GKE clusters. Inspect status, release channel, control-plane version, node-pool health, autoscaling and networking. Distinguish zonal and regional clusters; GKE node pools and Kubernetes workloads require additional API calls and permissions.

For SRE incidents, correlate GKE control plane, nodes, HPA/VPA, Pod scheduling, CNI, persistent disks, Cloud Monitoring and app-level SLIs. Do not blindly delete nodes or restart stateful workloads.

## 5. Cloud SQL for PostgreSQL

Use Cloud SQL Admin API `instances.list(project=...)` to inspect PostgreSQL engine, instance state, region, tier, HA, backups, storage and flags. The Python Cloud SQL Connector manages database connectivity; it does not replace the Admin API for infrastructure inventory. Before failover or maintenance, verify backup/PITR, replicas, RPO/RTO, storage headroom and application reconnect behavior.

## 6. Cloud Monitoring and SLOs

Use `MetricServiceClient.list_time_series` for resource metric types such as Compute CPU utilization, Cloud SQL CPU/storage and GKE resource metrics where enabled. Specify project, filter, interval, aggregation and view. Reject stale, empty or mismatched time series; missing data means **unknown**, not healthy. For service reliability, correlate request availability, p95/p99 latency, saturation and error-budget burn with infrastructure metrics.

## 7. Capacity and FinOps

Assess Compute machine type, disk size/IOPS, GKE node-pool capacity, Cloud SQL storage and HA headroom, quotas and regional availability. Billing Export to BigQuery provides detailed cost analysis; Cloud Billing APIs and budgets have distinct capabilities and access. A synthetic hourly-rate cost proxy is **not** actual billed cost. Include network egress, logging, persistent disks, reservations/commitments, licensing and storage backups.

## 8. Pagination, retries and idempotency

Google Cloud client iterators may automatically fetch pages. Bound page/item budgets and API deadlines. Retry transient 429/500/502/503/504 with exponential backoff and jitter; respect retry hints. Do not retry 403. For mutations, use request IDs where supported, poll long-running operations and reconcile authoritative state after ambiguous results. The lab intentionally has no write API path.

## 9. Dry-run, approval and audit

Bind a plan to project, zone/location, resource ID, action, incident, expected state, owner and rollback evidence. Hash canonical JSON to identify the exact proposal. The digest does **not** authenticate approval. Require externally authenticated, expiring approvals and least-privilege service identities before production writes. All lab actions remain advisory, including when simulated approval is true.

## 10. Production incident simulations

| Incident | Expected investigation |
|---|---|
| ADC resolves wrong project | Stop and verify identity |
| Workload Identity permission denied | Inspect IAM binding and federation |
| Compute API throttling | Bounded retry and quota |
| GKE control-plane degradation | Inspect cluster/node-pool state |
| GKE Pod scheduling failure | Diagnose quota, affinity, CNI and PVC |
| Cloud SQL disk pressure | Check storage growth, IOPS and backups |
| Cloud SQL failover | Validate HA and reconnect |
| Cloud Monitoring missing samples | Mark unknown |
| Cost spike | Reconcile Billing Export and changes |
| Region outage | Apply reviewed DR/RPO/RTO plan |
| Elasticsearch on GCE disk latency | Correlate disk limits and query load |
| PostgreSQL connection exhaustion | Check Cloud SQL limits, pooling, locks |

## 11. Operational runbooks

**ADC/IAM:** inspect principal, ADC project, quota project, IAM role and federation. Avoid JSON key fallback.

**Compute:** inspect instance state, serial console/operations, disks, quotas and monitoring. No blind restart.

**GKE:** inspect cluster, node pools, Kubernetes events, networking, workloads and control-plane permissions.

**Cloud SQL:** inspect storage, CPU, sessions, replication, backup/PITR, HA and maintenance windows.

**Cloud Monitoring:** validate filter, metric type, resource labels, interval, aggregation and sample freshness.

**FinOps:** reconcile project labels, BigQuery Billing Export, commitments and billing delay.

**Change governance:** confirm exact scope, independent approval, rollback, SLO and audit before any write.

## 12. Assessment and validation

The [complete lab](labs/096-gcp-infrastructure-operations-sre-dbre-lab.md) includes executable offline Python, unit tests, optional read-only SDK inventory, incident drills, runbooks and a **100-point final assessment**.

**Boundary:** Cloud SQL Admin, Cloud Monitoring and billing live adapters are explained as extension exercises, not implemented. Live GCP write operations are not provided.

**Next proposed:** Chapter 097 — Python Multi-Cloud Infrastructure Inventory and Governance.
