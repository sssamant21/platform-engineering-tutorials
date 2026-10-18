# Chapter 045 — Azure Stateful Data, Storage, Resilience and Production Operations Capstone

**Part 09 — Azure Infrastructure as Code · Chapter 045/120**  
**Audience:** DBRE, SRE, platform engineering, cloud security and incident commanders  
**Prerequisites:** Chapters 041–044, Terraform >=1.7, Python >=3.9; approved Azure sandbox for optional integration  
**Scope:** Azure Database for PostgreSQL Flexible Server, Azure SQL, Storage, managed disks, Azure Backup, encryption, private networking, failover and recoverability.

> **Execution boundary:** Required labs run **offline** with Terraform's built-in \`terraform_data\`; AzureRM examples are **review-only**. No database, disk, backup or Key Vault resource is created by the offline exercises. Production recovery is not accepted until a real restore is performed, measured and signed off.

## 1. Learning objectives

By the end, design an Azure data platform with appropriate RPO/RTO, availability zones, backups, point-in-time restore, private DNS, CMK/Key Vault dependencies, retention, audit and cost controls. Demonstrate a fail-closed Terraform policy gate, run negative tests, distinguish an IaC state restore from a database restore, and produce an auditable 100-point SRE/DBRE production acceptance packet.

## 2. Architecture and dependency graph

~~~text
              Enterprise identity / OIDC / Azure Policy
                               |
                 Terraform secure remote state
                               |
       VNet / NSG / UDR / Private DNS / Private endpoints
             |                              |
         AKS / VMSS                  Azure Storage
             |                  Blob / Files / Disks
             |                              |
       Connection pool -> PostgreSQL Flexible Server
             |           Zone-redundant HA where supported
             |           PITR backups / replica strategy
             |
             +-----------> Azure SQL Database / Managed Instance
                            Automated backups / geo-restore
                               |
                    Key Vault / managed identity / CMK
                               |
                 Azure Monitor / Log Analytics / alerts
                               |
                Restore drill / RPO-RTO evidence / audit
~~~

**Recovery dependencies:** a healthy Terraform state cannot recover deleted database rows; a database backup cannot repair missing private DNS, disabled CMK versions, revoked identities or application credentials. Keep an independently testable recovery plan for each layer.

## 3. PostgreSQL Flexible Server architecture

Choose tier, vCores, memory, storage and IOPS based on observed CPU, memory, buffer/cache, WAL, checkpoint pressure, latency and connections. Plan compute scaling and storage growth separately; validate service-specific shrink and downgrade limitations before a change. Use private networking appropriate to the chosen mode: VNet integration with delegated subnet and required DNS, or supported Private Link configuration; they are not interchangeable.

For HA, verify the current regional and tier support for same-zone or zone-redundant configurations, failover behavior and maintenance impact. High availability is **not** a substitute for backup or logical corruption recovery. PostgreSQL point-in-time restore typically provisions a **new server**; plan DNS, applications, users/roles, extensions, firewall/network settings, credentials and controlled cutover. Review service-specific retention limits, geo-redundancy options, PITR granularity and actual restore tests rather than assuming universal values.

**DBRE guardrails:** enforce TLS, least-privilege admin, managed identity where supported, connection pooling (e.g. PgBouncer when appropriate), parameter change review, slow query telemetry, autovacuum and bloat visibility, WAL/replication lag alerts, backup retention and restore rehearsals. Monitor connection storms during AKS autoscaling.

## 4. Azure SQL and Managed Instance

Select Azure SQL Database, elastic pool or Managed Instance based on SQL Server compatibility, cross-database features, operational constraints, performance and migration needs. Review provisioned versus serverless compute, service tier, storage and backup retention. Distinguish PITR, long-term retention, geo-restore, failover groups and active geo-replication. A failover group is not the same as a backup restore and does not prevent application-level corruption replication.

Use Microsoft Entra authentication and private endpoints where feasible, restrict public network access, enforce TLS, audit data-plane access and configure alerts for DTU/vCore, CPU, IO, deadlocks, blocking, storage and failed logins.

## 5. Azure Storage and persistent workloads

- **Blob Storage:** account redundancy (LRS/ZRS/GRS/GZRS as supported), versioning, soft delete, lifecycle rules, immutable retention where required, private endpoints, encryption, RBAC and recovery testing.
- **Azure Files:** SMB/NFS requirements, identity, network, snapshots, share quota and workload compatibility.
- **Managed disks:** performance tiers, throughput/IOPS, encryption, snapshots, zone behavior and VM/AKS attachment constraints. A disk snapshot alone may not be application-consistent.
- **AKS PVs:** CSI driver, StorageClass, reclaim policy, snapshots, topology, detach/attach time and restore workflows. Kubernetes manifests or Helm charts alone do not recover persistent database contents.
- **State backend:** Azure Blob versioning, leases, private networking, Azure AD data-plane authorization, backup and immutable audit trail.

Consider egress, transactions, replication, snapshots, Log Analytics ingestion and cross-region backup costs. Budget the cost of **restore drills**, not just steady-state storage.

## 6. Security and encryption

Azure-managed encryption at rest is common but does not automatically satisfy customer-managed key policy. CMK designs require Key Vault availability, soft delete, purge protection, rotation policy, managed identity grants and tested recovery. Deleting or disabling a key may render data inaccessible. Keep vault, DNS and identity recovery procedures independent of the data workload.

Use Azure Policy for allowed regions, TLS, public access, diagnostics and tagging. Do not store database passwords, storage keys or connection strings in Terraform state, examples, \`.tfvars\` or CI output. Terraform \`sensitive\` does not remove values from state. Prefer workload identities, Entra auth and controlled secret injection.

## 7. Backup, replication, PITR and disaster recovery

**Define objectives:** RPO = maximum tolerable data loss; RTO = maximum tolerable service interruption. Record observed values during a drill. HA failover, asynchronous replicas, PITR, long-term backups and cross-region recovery address different failures. An asynchronous replica may carry the same logical corruption as primary; a backup retained before corruption is often necessary.

~~~text
Incident -> stop writes / preserve evidence -> identify last-good recovery point
         -> confirm backup availability + key + private DNS + identity
         -> restore to isolated target -> integrity and application validation
         -> approve cutover -> controlled traffic shift -> monitor -> retrospective
~~~

For PostgreSQL, validate schema, row counts, constraints, roles, extensions, WAL consistency and application queries; for Azure SQL, run DBCC/integrity checks as appropriate and test application access. For Storage, validate object versions, checksums, metadata, permissions and lifecycle controls. Protect the last good copy from accidental deletion.

## 8. Terraform ownership and change safety

Separate \`foundation\` (state, identities), \`network\`, \`data\`, \`backup\`, \`monitoring\` and \`applications\` stacks with explicit outputs and stable versioned module contracts. Pin AzureRM and Terraform versions. Use \`prevent_destroy\` for critical resources as defense-in-depth, but remember it is not a complete guardrail: configuration removal can bypass intended protection unless an external plan gate also denies deletion.

Production applies require peer-reviewed plan, resource replacement inspection, DBRE approval, maintenance window, backup verification and rollback/cutover design. Do not use \`terraform destroy\` in production data roots.

## 9. Executable capstone lab

~~~text
labs/chapter-045/
  versions.tf, variables.tf, main.tf, outputs.tf
  environments/dev.tfvars, environments/prod.tfvars
  examples/azurerm-stateful-data.tf.example
  examples/azure-data-preflight.sh.example
  data-policy.json
  fixtures/data-safe.json, data-unsafe.json
  fixtures/plan-safe.json, plan-destructive.json
  data_gate.py, test_data_gate.py, run-preflight.sh
  runbook.md, acceptance.md, .gitignore
~~~

### Lab A — Offline architecture and resilience contracts

~~~bash
cd infrastructure-as-code/labs/chapter-045
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter045.tfplan
terraform apply chapter045.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "plan_exit=$?"
~~~

Four \`terraform_data\` contracts cover PostgreSQL/SQL data tiers, storage and encryption, backup/DR, and observability/approvals. Production variable preconditions reject unsafe declarations. Do **not** switch to production variables against the dev state.

### Lab B — Positive and negative policy tests

~~~bash
python3 data_gate.py fixtures/data-safe.json fixtures/plan-safe.json data-policy.json
python3 data_gate.py fixtures/data-unsafe.json fixtures/plan-destructive.json data-policy.json
python3 -m unittest -v test_data_gate.py
bash run-preflight.sh
~~~

Expected: safe passes; unsafe and destructive inputs fail. The Python gate checks **declared** subscription/state isolation, private networking, TLS, HA, backups, PITR, encryption, Key Vault recovery, storage access, diagnostics, change tickets, SRE/DBRE approvals, and destructive actions. Its simplified plan fixtures are **not** full AzureRM plan validation or live compliance evidence.

### Lab C — Optional sandbox AzureRM plan review

1. Verify Azure tenant/subscription, approved region, PostgreSQL/SQL availability, SKU/zone quotas, pricing, delegated subnet or private endpoint design, and Key Vault grants.
2. Inspect \`examples/azurerm-stateful-data.tf.example\` in a separate approved root. It is a minimal **review-only** sketch, not a production-complete deployment.
3. Configure OIDC/managed identity and encrypted private state; run \`terraform init\`, \`terraform validate\`, \`terraform plan\` with no automatic apply.
4. Review public network access, HA, backups, storage redundancy, encryption, diagnostics and delete/replace actions with DBRE and Security.
5. If formally approved for a disposable sandbox, deploy, write non-sensitive test records, trigger a controlled restore to a separate target, validate integrity and record measured RPO/RTO.
6. Retain evidence of cleanup, backup retention and residual billing.

## 10. Production SRE/DBRE failure scenarios

| Scenario | Signal | First response | Recovery validation |
|---|---|---|---|
| PostgreSQL accidental delete | missing rows, audit event | stop writes, identify PITR timestamp | isolated restore, row/query checks |
| PostgreSQL HA failover | connection resets, replica transition | retry/backoff, assess pool | read/write and latency SLO |
| Azure SQL logical corruption | integrity/query errors | freeze changes, identify clean backup | isolated restore, DB integrity |
| Storage object deletion | 404 / missing object | version/soft-delete inventory | checksum and ACL verification |
| CMK revoked or disabled | database/storage unavailable | restore authorized key path | decrypt and application tests |
| Private DNS regression | NXDOMAIN / public IP | inspect zone links/forwarders | TLS + DB query |
| AKS PV lost | pod Pending / mount errors | protect disk/snapshot evidence | volume and application recovery |
| Terraform state outage | blob 403 / lease errors | inspect identity/DNS/lock | state read and drift validation |
| Region disruption | service unavailable | invoke DR and data-loss decision | measured RPO/RTO |
| Backup retention gap | desired point unavailable | escalate, preserve remaining copies | updated backup policy/drill |

## 11. Troubleshooting matrix

| Symptom | Inspect | Avoid |
|---|---|---|
| PostgreSQL connection timeouts | private DNS, delegated subnet, NSG, TLS, DB health | opening public access |
| PITR target inaccessible | restore state, target network, identity, extensions | cutting over before validation |
| Storage 403 | RBAC data actions, firewall, private endpoint | distributing account keys |
| SQL failover errors | failover group, DNS, application retries | assuming zero data loss |
| Key Vault denies decrypt | managed identity, RBAC, key version, private DNS | disabling CMK |
| High storage latency | tier, IOPS, throughput, throttling, app IO | scaling CPU blindly |
| Backup job failed | policy, service limits, credentials, quotas | marking backup as successful |
| Terraform proposes delete | state/address drift, immutable properties | blind apply |

## 12. Operational runbooks

**Change preflight:** identify owner, change ticket, SLO, DB size, backup age, last successful restore, retention, encryption, private DNS and IAM. Run policy/test/plan. Freeze if destructive actions or missing evidence. Obtain DBRE, SRE, Security and change-management approval.

**Accidental PostgreSQL deletion:** stop affected writes, preserve logs, determine exact timestamp and scope, restore to isolated server, validate schema/roles/row counts and application queries, then approve cutover. Never overwrite the original before evidence preservation.

**Azure SQL restore:** identify recovery objective and clean point, create isolated restored database, validate integrity, logins and application behavior, update routing only after sign-off.

**CMK outage:** declare high severity, freeze key operations, inspect Key Vault and managed identity, recover soft-deleted or disabled key where authorized, restore private network/RBAC, verify decrypt and DB writes.

**Storage data loss:** inspect blob versions, soft delete, immutability, replication and backup, restore into isolated container and compare checksums.

**Region failover:** check last recoverable point and business-approved data loss, recover DNS, identities, keys and private network, then application and database, measure actual RPO/RTO.

**State backend failure:** preserve state versions and blob lease; verify identity, DNS, storage network and encryption; do not force-unlock without verifying no active writer.

## 13. Observability and reliability acceptance

Alert on backup failures/age, storage utilization, PostgreSQL CPU/memory/IO, failed connections, replication lag where available, SQL storage and deadlocks, Key Vault failures, private DNS resolution, application error budget and recovery test staleness. Retain evidence in a secured audit location. Record runbook owner, escalation, service dependency map, tested restore duration, test data integrity, and outstanding exceptions.

## 14. 100-point capstone assessment

| Domain | Points |
|---|---:|
| PostgreSQL and Azure SQL data architecture | 20 |
| Storage, private networking, identity and encryption | 20 |
| Backup, PITR, HA and DR design | 20 |
| Executable Terraform and automated negative tests | 15 |
| SRE/DBRE incidents and measured restore drills | 15 |
| Observability, cost, change approval and audit | 10 |

**Pass:** >=85/100 and zero critical failures. Critical: unapproved public data access, missing backup/restore evidence, untested CMK recovery, plaintext secrets in state, destructive production plan, or no DBRE approval. Publication of this chapter is **not** production acceptance.

## 15. Cleanup and final review

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Destroy only the offline contract lab or explicitly disposable sandbox resources. Review: Why is HA not a backup? Why does PITR restore require cutover? What dependencies can prevent decrypt after regional recovery? How does Azure Blob state versioning differ from PostgreSQL PITR? What evidence proves an RTO rather than an estimate?

**Part 09 — Azure Infrastructure as Code (Chapters 041–045) publication complete.**  
**Next: Chapter 046 — Google Cloud Infrastructure as Code Foundations and Terraform Google Provider** (confirm exact roadmap title before publication).
