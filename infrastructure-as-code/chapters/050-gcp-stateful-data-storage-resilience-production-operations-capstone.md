# Chapter 050 — GCP Stateful Data, Storage, Resilience and Production Operations Capstone

**Part 10 — GCP Infrastructure as Code | Chapter 050/120 | Final GCP capstone**  
**Audience:** DBRE, SRE, platform engineering, security, incident command, FinOps  
**Prerequisites:** Chapters 046–049; Terraform >=1.7, Python >=3.9, GCP sandbox only for optional approved integration.

> **Evidence boundary:** The mandatory lab is **offline**: Terraform \`terraform_data\` contracts and JSON policy fixtures create **no GCP infrastructure**. Review-only Google provider examples illustrate resource types but are not production-ready. Backups, RPO/RTO, CMEK, service reliability, restore success and security approvals must be proven in a real approved environment. Do not use Terraform state as a database backup or put credentials in Terraform inputs.

## 1. Learning objectives and capstone scenario

Design, deploy and operate resilient GCP data services with Terraform: Cloud SQL for PostgreSQL/MySQL, AlloyDB for PostgreSQL, Spanner, Bigtable, Firestore, Memorystore, Cloud Storage, Persistent Disk/Hyperdisk, Filestore and GKE CSI integration. Choose by transaction semantics, scaling, latency, consistency, geographic scope and operational ownership. Implement private connectivity, IAM/WIF, CMEK, backup/PITR, regional availability, disaster recovery, retention, observability, change management and FinOps. Perform fail-closed plan reviews and SRE/DBRE incident simulations.

**Capstone case:** A regulated application uses private GKE workloads, Cloud SQL for PostgreSQL as its transactional source, Cloud Storage for backup exports and artifacts, and Memorystore for cache. The platform must survive a zone failure and restore from data corruption; recovery targets are *illustrative design requirements*, not measured results: **RPO <=15 minutes** and **RTO <=60 minutes**. Verify each target in drills, including DNS, IAM, KMS and application cutover.

## 2. Reference architecture

~~~text
             CI/CD OIDC -> Workload Identity Federation
                             |
               Terraform plan + policy + approval
                             |
                  Private GCS state (versioned)
                             |
            Shared VPC / private service connectivity
                 /                     \
        Private GKE workloads       Operations project
                 |                 Audit/metrics/alerts
        Connection pooling                 |
                 |                Incident + DR runbooks
       Cloud SQL PostgreSQL HA -------- Cloud KMS/CMEK
           |           |
    automated backup   read replica (as appropriate)
           |           |
       PITR / WAL    async replication and failover plan
           |
    Approved isolated restore environment
           |
    integrity checks + application cutover + RPO/RTO evidence

  Cloud Storage: uniform bucket-level access, public access prevention,
  versioning, lifecycle/retention, replication class and optional CMEK
  Memorystore: private access, sizing, HA and cache-rebuild plan
  GKE PVC: CSI, zone topology, reclaim policy and snapshots
~~~

**Failure-domain rule:** High availability, backup, read replica and disaster recovery are different. HA addresses local component failure; a replica can copy corruption; backup/PITR addresses recoverable history; cross-region DR needs separate identity, network, KMS and tested application cutover.

## 3. Service-selection matrix

| Service | Good fit | Operational risks | Recovery design |
|---|---|---|---|
| Cloud SQL PostgreSQL | relational OLTP, managed Postgres | connection limits, storage/IOPS, maintenance, replica lag | HA, backups, PITR, validated restore |
| AlloyDB for PostgreSQL | high-throughput PostgreSQL-compatible workloads | architecture, cost, compatibility, cluster lifecycle | service-specific backup/replica/DR |
| Spanner | globally distributed transactional workloads | schema/query model, cost, operational semantics | instance configuration and backup strategy |
| Bigtable | low-latency wide-column/time-series at scale | row-key hotspots, replication and schema design | cluster replication, backups as supported |
| Firestore | document/mobile/serverless workloads | query/index constraints, pricing, consistency choices | exports, PITR/backup where supported |
| Memorystore | cache and selected in-memory workloads | eviction, failover, cache stampede | HA where available; rebuild from source |
| Cloud Storage | objects, exports, archival | accidental delete, public access, lifecycle misconfiguration | versioning, soft delete/retention and replication |
| Persistent Disk/Hyperdisk | VM/GKE block storage | zone attachment, performance provisioning, snapshots | snapshot policy, restore, regional disk where appropriate |
| Filestore | shared NFS for supported workloads | throughput, tier/zone dependencies | backup/replication strategy |

Product features, editions, quotas and regional support change: verify current service documentation and pinned Terraform provider schema. Do not assume AlloyDB, Spanner or Redis failover has the same semantics as Cloud SQL.

## 4. Cloud SQL and AlloyDB architecture

Cloud SQL PostgreSQL HA uses service-managed failover with regional configuration as supported by edition and region. Plan maintenance, connection draining, application retry and DNS/connection recovery. Read replicas are for read scaling or DR strategies, not a substitute for backups. For Cloud SQL, distinguish automated backup retention, transaction-log-based PITR retention, export and cross-region replica; availability and limits vary by edition. PITR restore typically creates a new instance and requires application cutover and validation, not an in-place undo.

For AlloyDB, validate cluster/instance topology, primary and read pool, automated backups, continuous backup, CMEK, networking and compatible extensions. Model connection pools carefully: HPA scaling from 10 to 100 pods with 20 connections each can overwhelm a managed database even when compute looks healthy. Protect credentials with Secret Manager and Workload Identity; avoid service-account keys and passwords in Terraform state.

## 5. Storage architecture and lifecycle

Cloud Storage buckets use globally unique names and a location/storage class/replication design. Select regional, dual-region or multi-region location based on latency, durability, recovery and cost; understand that location does not replace object versioning, retention or an isolated backup copy. Enable public access prevention, uniform bucket-level access, audit logging and versioning/soft delete as appropriate. Lifecycle policies can **delete data**: simulate and peer-review retention and age filters. Retention policies and Bucket Lock can be irreversible; never lock a bucket in a lab without approval.

For GKE: use the supported Persistent Disk CSI driver, correct StorageClass binding mode, disk topology and Pod scheduling. \`WaitForFirstConsumer\` helps align volumes to selected nodes. Distinguish PV reclaim policy \`Delete\` versus \`Retain\`, CSI snapshots and database-consistent backups. A volume snapshot without WAL consistency is not guaranteed to restore a healthy PostgreSQL instance.

## 6. Private connectivity, identity and encryption

Private Cloud SQL connectivity may use private services access or Private Service Connect depending on instance/service support and project design; validate service networking, DNS, firewall, TLS and connection method. GKE nodes and workloads require scoped IAM and Workload Identity Federation. Use CMEK only after reviewing KMS key location, permissions for Google-managed service agents, key version lifecycle, service availability and recovery. A disabled or destroyed CMEK key version can render stored data inaccessible; test key-access recovery in a sandbox. Protect GCS Terraform state with access control, versioning, encryption, restricted logging and locking.

## 7. Backup, PITR and DR engineering

Define workload-specific RPO/RTO, retention, legal hold, immutable/offline copies where supported, restore isolation, key availability and approval ownership. Document **what** is protected (data, schema, IAM, configuration, DNS, certificates), **how** it is restored and **who** approves cutover. For Cloud SQL: inventory backups, PITR settings and recovery windows; restore to isolated test instance, verify tables/row counts/checksums/application queries, measure elapsed time, and decide promotion/cutover. Never overwrite a healthy production instance as a first restore attempt.

DR runbook phases: declare incident; freeze writes when required; identify last-known-good recovery point; confirm KMS/IAM/network dependencies; restore into isolated region/project; validate consistency and replication; switch application endpoints; measure RPO/RTO; monitor; perform reconciliation and post-incident review. **Do not equate a successful backup job with a tested restore.**

## 8. Terraform architecture and change safety

~~~text
gcp-data-platform/
  foundations/          # projects, APIs, WIF, state and org policy
  network/              # Shared VPC, PSA/PSC, DNS, firewall
  encryption/           # KMS, service-agent grants
  database/             # Cloud SQL/AlloyDB, backups, PITR, HA
  object-storage/       # buckets, IAM, lifecycle, retention
  cache/                # Memorystore, private access
  gke-storage/          # CSI StorageClasses, snapshot policy
  observability/        # metrics, logging, alerts, budgets
  dr-validation/        # isolated restore drill evidence
~~~

Review resource types such as \`google_sql_database_instance\`, \`google_sql_database\`, \`google_storage_bucket\`, \`google_storage_bucket_iam_member\`, \`google_kms_crypto_key\`, \`google_redis_instance\`, \`google_compute_disk\`, \`google_compute_snapshot\`, \`google_filestore_instance\` and service-specific resources. Use version pinning, separate environment state, CI OIDC, review gates, \`prevent_destroy\` for selected critical objects, and organizational guardrails. **\`prevent_destroy\` is not a backup, and removing a resource block can remove its lifecycle guard**; independently block delete/replace plans.

## 9. Executable hands-on labs

Directory: \`infrastructure-as-code/labs/chapter-050/\`.

### Lab A — Offline Terraform contracts

~~~bash
cd infrastructure-as-code/labs/chapter-050
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter050.tfplan
terraform apply chapter050.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
~~~

Four \`terraform_data\` contracts model database availability, storage protection, private security and DR/operations. Production preconditions deny public database ingress, missing PITR/HA, insecure storage, missing restore evidence and unapproved changes. The lab creates **no Cloud SQL, buckets, Redis or GKE volumes**. Keep dev/prod state directories separate.

### Lab B — Adversarial policy fixtures

~~~bash
python3 data_gate.py fixtures/data-safe.json fixtures/plan-safe.json data-policy.json
python3 data_gate.py fixtures/data-unsafe.json fixtures/plan-destructive.json data-policy.json
python3 -m unittest -v test_data_gate.py
bash run-preflight.sh
~~~

Safe fixture must pass; unsafe and destructive fixture must fail. This is a **declared-evidence** gate with simplified plan actions; do not pass raw \`terraform show -json\` into it without implementing and testing a provider-aware parser.

### Lab C — Optional GCP sandbox plan

1. Verify project, APIs, billing, IAM/WIF, quotas, approved region, KMS key and private network connectivity.
2. Review \`examples/google-data.tf.example\` as a **separate root**. It may create billable services if applied. Never place credentials in variables or state.
3. Inspect Cloud SQL HA/PITR/backup/maintenance settings, Cloud Storage access/lifecycle and deletion protection; peer-review plan.
4. With change approval, deploy disposable data only; generate test transactions, simulate loss and restore to an isolated instance.
5. Measure RPO/RTO, application connection recovery, IAM/KMS and data integrity; document cleanup, costs and evidence.

### Lab D — DR tabletop and recovery acceptance

Use \`runbook.md\` and \`acceptance.md\`. Assign incident commander, DBRE, SRE, security and application owner. Inject (a) accidental deletion, (b) region outage, (c) disabled CMEK version, (d) connection exhaustion. Require actual evidence, not checkboxes, for recovery time, recovery point, consistency and application cutover.

## 10. Production SRE/DBRE incidents

| Failure | Signals | Investigate | Recovery |
|---|---|---|---|
| Cloud SQL CPU/IOPS saturation | p95 query latency, disk queue | Query Insights, metrics, explain, workload | tune queries/indexes, rightsize |
| Connection pool exhaustion | connection refused/too many clients | pool fan-out, max connections, GKE HPA | cap pools, backpressure, pooler |
| Storage growth | capacity alert, write errors | table/index bloat, retention, disk growth | cleanup with owner, scale |
| PostgreSQL replication lag | stale reads, delayed replica | WAL generation, apply lag, I/O | reduce workload, resync as approved |
| Cloud SQL HA failover | reconnect errors | instance events, DNS, driver retries | reconnect, validate writes |
| PITR restore fails | backup unavailable | retention, recovery window, IAM/KMS | alternate recovery point, escalate |
| Object lifecycle deletes data | missing objects | lifecycle history, audit logs, versions | restore versions/isolated copy |
| GCS public exposure | security alert | IAM, public access prevention | block public access, audit |
| CMEK key disabled | database/object unavailable | KMS state, service-agent access | restore authorized key access |
| GKE PV zone mismatch | Pod Pending | PV node affinity, CSI events | migrate/restore correctly |
| Memorystore eviction | cache misses, backend surge | memory, TTL, hit rate | throttle, rebuild cache |
| Terraform destructive plan | delete/replace database | diff, drift, immutable args | block apply, migration plan |
| Region outage | service unavailable | region status, data replication | execute tested DR cutover |

## 11. Troubleshooting commands

~~~bash
gcloud sql instances list --project=PROJECT_ID
gcloud sql instances describe INSTANCE --project=PROJECT_ID
gcloud sql backups list --instance=INSTANCE --project=PROJECT_ID
gcloud storage buckets list --project=PROJECT_ID
gcloud storage buckets describe gs://BUCKET
gcloud kms keys list --keyring=RING --location=REGION --project=PROJECT_ID
gcloud redis instances list --region=REGION --project=PROJECT_ID
gcloud compute disks list --project=PROJECT_ID
kubectl get pvc,pv -A
kubectl get volumesnapshot -A
kubectl get events -A --sort-by=.lastTimestamp
terraform state list
~~~

Commands require scoped access and valid resource names; some commands/features vary by installed gcloud version and API. Avoid logging secrets, database passwords or sensitive backup contents.

## 12. Production runbooks

**Pre-change:** confirm data owner, region, RPO/RTO, backup/PITR, latest restore evidence, CMEK, service-agent IAM, private network, budget, state version, Terraform diff, ticket, security and DBRE approval. Deny delete/replace of protected resources.

**Cloud SQL slow queries:** correlate CPU, IOPS, connections, waits, query fingerprints and plans; throttle expensive callers, add indexes with change review, confirm p95 and error-budget recovery.

**Database connection storm:** inspect GKE HPA/MIG scale and per-process pools, enforce backpressure, cap connections, recover transaction throughput and validate no partial writes.

**PITR/data corruption:** isolate affected writers, identify known-good time, restore to new instance, validate schema/data and application behavior, cut over under approval, measure RPO/RTO.

**KMS incident:** freeze key operations, check version state and service-agent access, recover access if possible, verify decrypt/read/write; do not destroy versions.

**GCS accidental deletion:** inspect audit/lifecycle, object versions/soft-delete availability and retention; recover safely and verify checksums.

**GKE persistent volume incident:** inspect topology, CSI, snapshots and reclaim policy; coordinate DBRE for consistent restore and zone migration.

**Regional DR:** fail over network, IAM/KMS, database, cache and app in dependency order; confirm business transactions, measure RPO/RTO, document failback.

## 13. 100-point final Part 10 assessment

| Domain | Points | Required evidence |
|---|---:|---|
| Stateful service selection and architecture | 15 | ADR and data-flow diagram |
| Database HA, backup, PITR and integrity | 20 | tested restore and query checks |
| Storage, encryption, identity and private access | 20 | reviewed configuration and access tests |
| Terraform labs, policy and destructive-change controls | 15 | logs, fixtures and reviewed plan |
| SRE/DBRE incidents, DR and measured RPO/RTO | 20 | timeline, drills, recovery metrics |
| Monitoring, FinOps, audit and change approval | 10 | dashboards, cost estimate, sign-off |
| **Total** | **100** | |

**Pass >=85/100 with zero critical failures:** no proven restore, public database access, unapproved data deletion, inaccessible CMEK recovery, missing DBRE/security sign-off or missed mandatory RPO/RTO. Do not award points for tests merely authored but not run.

## 14. Cleanup and final review

~~~bash
terraform destroy -var-file=environments/dev.tfvars
~~~

Only destroy offline contract state or a disposable approved sandbox. Questions: How is HA different from PITR? Why does a read replica not prevent corruption propagation? Why can CMEK disablement cause an outage? How can GKE HPA exhaust Cloud SQL? Why are CSI snapshots not automatically transaction-consistent? How do you measure real RPO/RTO?

**Part 10 complete upon publication: Chapters 046–050.** Live security, data restoration and DR acceptance remain pending. **Next: Chapter 051 — consult the master roadmap before naming the next topic.**
