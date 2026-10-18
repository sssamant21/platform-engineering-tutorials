# Chapter 095 — Python Azure Infrastructure and Cloud Operations Automation

**Part 10 — Kubernetes, AWS, Azure and GCP | Chapter 095 of 120 | Python 3.11+**

[Hands-on lab](labs/095-azure-infrastructure-cloud-operations-sre-dbre-lab.md) · [Executable project](labs/095/README.md)

## Objectives

Build least-privilege Azure operational automation using the Azure SDK for Python, Microsoft Entra ID, managed identities, Azure Resource Manager (ARM), Virtual Machines, AKS, Azure Database for PostgreSQL Flexible Server, Azure Monitor, cost and capacity analysis. Apply pagination, retries, approval gates, idempotency, dry-run and auditability. The lab is **offline by default**; optional live inventory is read-only.

## Architecture

```text
Operator / scheduled workload
   -> Entra ID credential (managed identity / approved az login)
   -> tenant + subscription + resource-group allowlist
   -> Azure SDK clients and ARM pagination
   -> VM / AKS / PostgreSQL Flexible Server inventory
   -> Azure Monitor metrics (design exercise)
   -> capacity and cost policy evaluation
   -> advisory change plan + deterministic SHA-256 digest
   -> external approval and rollback evidence (production extension)
   -> JSON audit; zero mutations in supplied code
```

## 1. Authentication and Microsoft Entra ID

Azure SDK clients accept `TokenCredential`. In Azure-hosted workloads, prefer **ManagedIdentityCredential** with a user-assigned identity or workload identity federation. On a workstation, use `AzureCliCredential` after `az login` and explicit `az account set --subscription ...`. `DefaultAzureCredential` is convenient but its chain may select an unexpected identity; verify tenant, subscription, principal and role assignment. Do not store client secrets in code, commit token caches, disable TLS or log bearer tokens.

**Authorization:** Entra ID authenticates the principal; Azure RBAC grants actions at management-group, subscription, resource-group or resource scope. A Reader role can enumerate many resources, while Monitoring Reader supports metrics; some resource-provider operations have additional requirements. Use least privilege, Privileged Identity Management, Azure Policy and scope restrictions. A managed identity cannot automatically access Kubernetes objects: AKS authentication and Kubernetes RBAC/Azure RBAC are separate checks.

## 2. Azure SDK packages and clients

Install reviewed/pinned versions of `azure-identity`, `azure-mgmt-compute`, `azure-mgmt-containerservice`, `azure-mgmt-rdbms`, `azure-monitor-query` and `azure-mgmt-resource`. Examples:

```python
from azure.identity import AzureCliCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.rdbms.postgresql_flexibleservers import PostgreSQLManagementClient

credential = AzureCliCredential()
compute = ComputeManagementClient(credential, subscription_id)
aks = ContainerServiceClient(credential, subscription_id)
postgres = PostgreSQLManagementClient(credential, subscription_id)
```

SDK import paths and API versions vary; pin and test the chosen releases. The optional adapter implements VM and AKS listing; PostgreSQL Flexible Server collection is a production extension because package compatibility and permissions vary.

## 3. VM, AKS and PostgreSQL inventory

**VMs:** `virtual_machines.list(resource_group_name)` returns pageable results. Record VM name, resource ID, location, size and provisioning state; power state may require an instance-view request. Do not assume `provisioning_state` means the VM is running.

**AKS:** `managed_clusters.list_by_resource_group(resource_group_name)` returns managed clusters. Record Kubernetes version, provisioning state, node-pool count and location. Diagnose node pools, identities, networking, upgrades and control-plane API separately.

**PostgreSQL Flexible Server:** use the supported `PostgreSQLManagementClient.servers.list_by_resource_group` for the installed SDK version. Record SKU, storage, HA, backup retention, state and maintenance configuration. Azure Database for PostgreSQL Single Server is retired; do not use old Single Server examples.

Every inventory run must enforce subscription, resource-group, region and item/page/time budgets. SDK pageable iterators may fetch additional pages lazily; limit processing and avoid dumping full resource objects with sensitive configuration.

## 4. Azure Monitor and diagnostics

Use Azure Monitor Metrics Query clients (such as `MetricsQueryClient` for a resource URI, subject to installed SDK/API version) to request CPU, memory where available, disk latency/IOPS, AKS node metrics and PostgreSQL CPU/storage/connections. Validate aggregation, unit, time grain, dimension, timestamp freshness, empty series and missing-data policy. Azure Monitor diagnostic settings, Log Analytics and Application Insights provide complementary logs/traces; do not assume metrics are enabled or complete.

For DBRE, correlate PostgreSQL connections, locks, replication, storage and latency with VM/AKS node pressure. For Elasticsearch/OpenSearch on Azure VMs, storage SKU, provisioned IOPS/throughput and disk queue depth are critical; CPU-only scaling is insufficient.

## 5. Capacity and FinOps

Evaluate utilization, storage headroom, quotas, AKS node-pool capacity, VM SKU availability and zone redundancy. Use Cost Management Query/Exports for authoritative subscription costs and budgets, with appropriate permissions and billing latency. A synthetic hourly-rate calculation is a **planning proxy**, not actual Azure billing. Consider disks, snapshots, network egress, Log Analytics ingestion, reservations, savings plans and licensing.

## 6. Pagination, retries and idempotency

Azure SDK pageable operations should be consumed with explicit resource budgets. Handle transient 429/500/502/503/504 with capped exponential backoff and jitter, respecting Retry-After where available. Do not retry authorization failures (401/403) or invalid requests. Use request timeouts and per-service concurrency limits. For real mutations, Azure ARM long-running operations return pollers; record operation IDs, inspect final state, and do not repeat ambiguous writes blindly.

## 7. Dry-run, approvals and audit

Bind a proposed change to subscription, resource group, resource ID, action, incident ID, expected state, rollback plan and approver. Hash canonical JSON to produce a deterministic plan fingerprint; **the hash is not authorization**. Require authenticated, expiring approval outside the program, independent change governance, backup and SLO checks. The lab accepts simulated approval flags but **never calls write APIs**.

## 8. Production incident simulations

| Scenario | Required response |
|---|---|
| Wrong subscription/tenant | Stop before inventory |
| Managed identity token unavailable | Diagnose federation/identity, no secret fallback |
| Azure RBAC 403 | Inspect scoped role assignments |
| ARM API 429 | Bounded retry and reduce concurrency |
| Pageable API loop or item flood | Fail closed |
| VM provisioning failed | Check Activity Log, VM extensions, disk/network |
| AKS node pool not ready | Inspect quota, CNI, identity and events |
| AKS API login fails | Check Entra ID and Kubernetes authorization |
| PostgreSQL storage saturation | Validate capacity, HA, backup, IOPS |
| PostgreSQL failover | Inspect HA and replication before remediation |
| Azure Monitor missing metrics | Mark unknown, not healthy |
| Cost spike | Correlate Cost Management and resource changes |
| Elasticsearch on Standard SSD | Investigate IOPS, throughput and queue |
| Unauthorized production change | Reject, audit, escalate |

## 9. Troubleshooting runbooks

**Identity/RBAC:** verify `az account show`, tenant, subscription, managed identity, role scope and token audience. Do not grant Owner to fix read access.

**VM/AKS:** inspect provisioning status, Activity Log, node-pool health, quota, identity, CNI and storage before change.

**PostgreSQL:** inspect HA, storage headroom, active sessions, IOPS/latency, backups and replication. Never restart a primary solely because one metric is high.

**Azure Monitor:** verify resource URI, metric namespace, dimensions, time grain, aggregation and data freshness; label missing telemetry unknown.

**Cost:** verify resource tags, scope, billing delay, disk and egress costs, reservations and budget alerts.

**Change approval:** check exact resource ID, expected state, rollback evidence, expiry and authenticated authorization before any production mutation.

## 10. Lab and assessment

The [Chapter 095 hands-on lab](labs/095-azure-infrastructure-cloud-operations-sre-dbre-lab.md) provides executable Python, offline tests, optional read-only VM/AKS SDK adapter, incident drills, runbooks and a **100-point assessment**.

**Scope:** Live PostgreSQL inventory, Azure Monitor queries and Cost Management integration are documented extension exercises, not implemented API calls. No live Azure mutation is included.

**Next proposed:** Chapter 096 — Python Google Cloud Infrastructure and Operations Automation.
