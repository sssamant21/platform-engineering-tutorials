# Chapter 071 — Kubernetes Backup Strategy and RPO/RTO

**Track:** Kubernetes Administration · **Part 15 — Backup, Disaster Recovery and Business Continuity**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, security and cloud platform engineers  
**Prerequisites:** Chapters 019, 036–040, 066–070; kubectl; Windows PowerShell; approved read-only access; a dedicated staging recovery environment

## 1. Production scenario

An EKS or AKS cluster runs customer-facing APIs, PostgreSQL, MongoDB, Redis and Kafka integrations. A failed infrastructure change renders one cluster unavailable. GitOps can recreate many Deployments, but several workloads depend on PVCs, database transaction logs, Secrets, external identity configuration, DNS, certificates and cloud resources. The business requires a clear answer: **how much data can be lost, how quickly can service be restored, and has the recovery process actually been tested?**

**Goal:** design a layered Kubernetes backup and disaster recovery strategy with measurable recovery point objectives (RPO), recovery time objectives (RTO), immutable/offsite protection, workload-specific consistency, and repeatable restore validation.

### Learning objectives

1. Distinguish backups, snapshots, replication, high availability and disaster recovery.
2. Define RPO/RTO per application and dependency.
3. Inventory Kubernetes configuration, persistent state and external infrastructure.
4. Compare GitOps/IaC, Velero, CSI snapshots and datastore-native backups.
5. Understand EKS/AKS control-plane backup responsibility boundaries.
6. Design backup retention, encryption, access controls and restore isolation.
7. Validate application-consistent recovery and point-in-time restore.
8. Produce a recovery dependency map, runbook and acceptance report.

## 2. RPO and RTO fundamentals

**Recovery Point Objective (RPO)** is the maximum acceptable data loss measured in time. **Recovery Time Objective (RTO)** is the maximum acceptable time to restore service after a disruption.

```text
Last recoverable point         Incident             Service restored
         |                        |                         |
         +------ data gap --------+--------- outage --------+
                 actual RPO                  actual RTO
```

Example: last recoverable database state is 10:55 UTC, incident occurs at 11:00 UTC, and service is restored at 11:45 UTC. Actual data gap is 5 minutes and service restoration takes 45 minutes. These are illustrative values; actual recovery time may be measured from a defined incident declaration/detection point according to policy.

### Service tier examples

| Tier | Illustrative target RPO | Illustrative target RTO | Strategy |
|---|---|---|---|
| Critical transactional | 5 min | 60 min | Continuous logs/PITR, tested failover |
| Important operational | 1 hour | 4 hours | Frequent backup plus replication |
| Internal tooling | 24 hours | 24 hours | Daily backup and IaC restore |

These are example objectives, not universal recommendations. Business owners must approve actual objectives, regulatory requirements and cost tradeoffs.

## 3. What must be recoverable?

```text
Kubernetes service recovery
  |
  +-- Cloud foundation: VPC/VNet, subnets, IAM, DNS, KMS, quotas
  +-- Cluster: API access, node pools, CNI, CSI, ingress
  +-- Declarative configuration: GitOps, Helm, manifests, CRDs
  +-- Runtime metadata: namespaces, RBAC, policies, service accounts
  +-- Secrets and certificates: secret manager, encryption keys, rotation
  +-- Persistent volumes: CSI snapshots / storage backups
  +-- Databases: PITR, transaction logs, replication and consistency
  +-- External systems: Kafka, object storage, managed databases, APIs
  +-- Observability: metrics/logs/traces and recovery evidence
```

**Critical distinction:** a backup of Kubernetes API objects does not automatically contain persistent volume data, cloud IAM policies, container images or consistent database state.

## 4. Lab 1 — Build the recovery inventory

```powershell
Get-Date -Format o
kubectl config current-context
kubectl get namespaces
kubectl get deployments,statefulsets,daemonsets -A
kubectl get pvc -A
kubectl get pv
kubectl get storageclasses
kubectl get volumesnapshotclasses
kubectl get crds
kubectl get ingress -A
```

Snapshot CRDs may be absent; record that fact rather than treating it as a cluster failure.

### Recovery inventory worksheet

```text
Application / namespace:
Business owner:
Technical owner:
Criticality tier:
Desired RPO / RTO:
Kubernetes objects / Helm release:
Container image registry:
Secrets source and KMS dependencies:
PVCs and storage classes:
Database / queue dependencies:
External DNS and certificates:
Cloud IAM/network dependencies:
Backup mechanism:
Backup location / retention:
Last verified restore:
Recovery runbook:
```

**Expected:** every critical service has named dependencies and a recovery owner.

## 5. Lab 2 — Map backup and restore dependencies

Recovery order matters. Restoring application Pods before storage, identities or DNS may result in CrashLoopBackOff, missing credentials or data corruption.

### Illustrative dependency sequence

1. Recover cloud account/subscription access, KMS and backup repository access.
2. Recreate network, cluster, node pools and core add-ons.
3. Restore CRDs/operators and required admission components.
4. Restore namespaces, service accounts, RBAC and policies.
5. Restore secret-manager references and encryption dependencies.
6. Restore storage classes, snapshots/PVCs and database state.
7. Restore application workloads, ingress and DNS routing.
8. Verify dependencies, data integrity and customer SLIs.
9. Resume ingestion, scheduled jobs and external traffic after approval.

**Expected:** dependency order is documented, with parallelizable tasks and critical path identified.

## 6. Lab 3 — Evaluate Kubernetes resource backups

### GitOps and IaC

Git repositories and IaC can recreate many desired-state resources, but may omit runtime-generated resources, PVC contents, dynamic certificates and external provider state.

### Velero

Velero can back up Kubernetes resources and, depending on configured plugins and data movers, persistent volume data. Its capabilities depend on installation, cloud provider and version.

```powershell
kubectl get namespaces | Select-String -Pattern 'velero'
kubectl -n velero get deployments,pods
kubectl -n velero get backupstoragelocations
kubectl -n velero get backups
kubectl -n velero get schedules
```

Run these only if Velero is installed and access is approved.

### Velero CLI examples (only when installed)

```powershell
velero version
velero backup get
velero schedule get
velero backup describe REPLACE_WITH_BACKUP --details
velero backup logs REPLACE_WITH_BACKUP
```

**Expected:** determine what resource types and data paths are included, where backups reside and whether the latest backups completed successfully.

## 7. Lab 4 — CSI snapshots and persistent volume protection

CSI VolumeSnapshot resources provide storage snapshots when supported by the CSI driver, snapshot controller and VolumeSnapshotClass.

```powershell
kubectl get volumesnapshotclasses
kubectl get volumesnapshots -A
kubectl get volumesnapshotcontents
kubectl get pvc -A
kubectl get storageclasses
```

### Important limitations

- A CSI snapshot is often crash-consistent, not application-consistent.
- Snapshots may reside in the same region/account/failure domain.
- Snapshot deletion policy, encryption and retention require review.
- Snapshot creation success does not prove PVC restoration or application integrity.
- Some storage backends need specific drivers and credentials.
- Snapshots do not automatically protect data outside the volume.

### Design-only VolumeSnapshot example

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: app-data-snapshot
  namespace: staging-recovery
spec:
  volumeSnapshotClassName: REPLACE_WITH_SNAPSHOT_CLASS
  source:
    persistentVolumeClaimName: app-data
```

**Do not apply** until the class, source PVC, permissions, backup policy and staging environment are verified.

## 8. Lab 5 — Application-consistent database backups

### PostgreSQL

- Base backups plus WAL archiving enable point-in-time recovery when correctly configured.
- Confirm WAL retention, archive health, timeline handling and restore targets.
- Verify consistency by starting the restored instance and querying known records.
- Coordinate backup ownership if PostgreSQL is managed outside Kubernetes.

### MongoDB

- Use supported backup tooling and replica set/sharded cluster procedures.
- Confirm oplog coverage, snapshot consistency and replica set topology.
- Validate restore of collections, indexes and application reads.

### Elasticsearch / OpenSearch

- Use repository snapshots for supported consistent index/cluster recovery.
- Do not treat raw filesystem copies of live data directories as reliable backups.
- Validate snapshot repository access, index restore and shard recovery.

### Redis

- Determine whether RDB, AOF, managed backups or a combination meets RPO.
- Validate persistence settings, replication and restore compatibility.
- Cache-only data may have a different recovery requirement from authoritative data.

### Kafka

- Broker replication is not an independent backup.
- Protect topic configurations, ACLs, schemas, offsets and required retained messages using an approved recovery design.
- Validate consumer replay, duplicate handling and offset restoration.

**Expected:** each datastore has its own recovery procedure and data-consistency test; a Kubernetes snapshot alone is not accepted as proof of recoverability.

## 9. Lab 6 — RPO and backup frequency modeling

Assume daily full backup plus continuous WAL archiving every minute.

```text
Full backup: 00:00 UTC
Incident: 15:00 UTC
Latest successfully archived WAL: 14:58 UTC
Potential recoverable point: 14:58 UTC
Actual data gap: 2 minutes
```

This only holds if the base backup, WAL chain, encryption keys and restore procedure are valid.

### RPO verification

1. Identify last successful recoverable point, not last backup start time.
2. Confirm incremental/log continuity.
3. Verify backup object availability and checksums.
4. Check replication lag where replication is part of recovery.
5. Restore to a controlled timestamp and validate records.
6. Compare observed gap with approved RPO.

**Expected:** measured RPO based on an actual restore or defensible recovery-point evidence.

## 10. Lab 7 — RTO and recovery critical path

### Example recovery timeline

| Phase | Illustrative duration |
|---|---:|
| Incident declaration and authorization | 10 min |
| Cloud/cluster foundation | 25 min |
| Identity, CNI, CSI and operators | 15 min |
| Database/PVC restore | 40 min |
| Application rollout and DNS | 15 min |
| Integrity and SLO verification | 15 min |

If strictly sequential, total is 120 minutes. Parallel work can shorten the critical path, but dependencies, cloud quotas and data restore throughput may dominate.

### RTO test requirements

- Start timer at the agreed incident point.
- Capture restore step timestamps.
- Measure data volume and transfer throughput.
- Include validation and traffic restoration.
- Record human approvals and credential retrieval delays.
- Compare actual RTO with business objective.

**Expected:** recovery time is measured end-to-end, not merely until Pods become Running.

## 11. Lab 8 — EKS and AKS responsibility boundaries

### EKS

- AWS manages the EKS control plane; users generally cannot directly snapshot managed etcd.
- Protect workload state, manifests, GitOps, EBS/EFS data, external databases and AWS configuration separately.
- Review EBS snapshot, S3 backup storage, IAM/KMS and cross-region protection.
- Verify VPC, subnet, security group, node role and CNI recovery prerequisites.

### AKS

- Azure manages the AKS control plane; users generally cannot directly operate etcd backups.
- Protect workload resources, managed disks/files, identities, Key Vault and Azure networking.
- Review Azure Backup/CSI capabilities appropriate to the deployment.
- Verify managed identities, Azure CNI, node pools and storage recovery prerequisites.

**Do not assume** that cloud control-plane availability guarantees customer data recovery or that a managed cluster exposes the same etcd restore procedure as self-managed Kubernetes.

## 12. Lab 9 — Backup security, retention and immutability

### Security controls

- Encrypt backups in transit and at rest.
- Restrict read, write, delete and restore permissions.
- Separate production admin access from backup deletion authority.
- Protect KMS keys, secret-manager credentials and recovery break-glass access.
- Use immutable/WORM retention where supported and required.
- Keep a protected offsite or cross-region copy for disaster recovery.
- Monitor backup deletion, policy changes and unusual access.
- Avoid embedding secrets in runbooks, logs or exported manifests.

### Retention worksheet

```text
Data classification:
Legal/compliance requirements:
Operational retention:
Long-term retention:
Cross-region copy:
Immutability period:
Encryption key owner:
Backup deletion approver:
Restore access approver:
Periodic access review:
```

**Expected:** backups remain accessible after the primary cluster or region is unavailable, without creating unrestricted data access.

## 13. Lab 10 — Backup observability and alerting

### Minimum signals

| Signal | Alert condition |
|---|---|
| Last successful backup | Older than policy |
| Backup job status | Failed or incomplete |
| Backup duration | Exceeds expected window |
| Repository free space / quota | Below safety threshold |
| WAL/oplog continuity | Gap threatens RPO |
| Replication lag | Exceeds recovery assumption |
| Snapshot errors | Repeated failures |
| Restore drill age | Older than test cadence |
| Key access | Recovery key unavailable or expired |

**Expected:** backup health is measured by recoverability and restore tests, not merely by successful CronJobs.

## 14. Lab 11 — Isolated staging recovery tabletop

**Scenario:** the primary Kubernetes cluster is unavailable. GitOps repositories and backup storage remain accessible, but one database's latest backup is incomplete and an encryption key is unavailable.

### Tasks

1. Declare disaster severity and confirm RPO/RTO targets.
2. Select the last verified recoverable backup.
3. Identify cloud, IAM, KMS and DNS prerequisites.
4. Choose a recovery cluster/region and validate quota.
5. Restore CRDs/operators before custom resources.
6. Restore database/PVC state with integrity checks.
7. Reconcile GitOps without overwriting restored state.
8. Verify application reads/writes and dependent queues.
9. Record actual recoverable timestamp and recovery duration.
10. Escalate the key and backup gaps without inventing success.

**Expected:** a documented decision tree for incomplete backups, unavailable keys and safe partial-service recovery.

## 15. Lab 12 — Disaster recovery readiness assessment

### Assessment matrix

| Control | Pass evidence |
|---|---|
| RPO/RTO ownership | Approved service objectives |
| Backup inventory | All critical dependencies mapped |
| Configuration recovery | GitOps/IaC and runtime objects covered |
| Persistent data | PVC and database-native backups covered |
| Cross-failure-domain storage | Offsite copy and access verified |
| Encryption | Keys and break-glass recovery tested |
| Restore test | Isolated restore with data validation |
| Automation | Repeatable runbook and owners |
| Monitoring | Backup failures and age alerting |
| Cost | Backup/restore storage and transfer budget |
| Compliance | Retention and deletion policy approved |
| Review | Independent technical sign-off |

Mark each control Pass, Fail, Not run or Not applicable. A tabletop is not equivalent to a real restore test.

## 16. Production backup and recovery runbook

### Before an incident

1. Maintain an up-to-date recovery inventory.
2. Test backup creation, repository access and restore permissions.
3. Verify datastore-specific consistency and log continuity.
4. Keep infrastructure definitions and image artifacts available.
5. Test cross-zone/cross-region recovery within approved windows.

### During an incident

1. Declare severity and assign incident commander, platform lead and DBRE.
2. Freeze destructive operations and preserve evidence.
3. Identify last recoverable point and data integrity risk.
4. Select recovery target and obtain change authorization.
5. Restore foundation, stateful dependencies and applications in dependency order.
6. Verify customer SLIs and data consistency before traffic cutover.
7. Record actual RPO/RTO and communicate residual risk.

### After recovery

1. Re-establish backup schedules and replication.
2. Verify recovery copies and access controls.
3. Conduct blameless RCA and update runbooks.
4. Track remediation owners, dates and acceptance tests.

## 17. Common failure patterns

| Failure | Why it matters | Prevention |
|---|---|---|
| Backups only in primary region | Regional outage removes copies | Cross-region/offsite strategy |
| Only Kubernetes manifests backed up | Persistent data missing | Volume/datastore-native backups |
| Only PVC snapshots | DB may be inconsistent | App-consistent backup/PITR |
| Backup job reports success but objects missing | False recovery confidence | Repository verification |
| WAL archive gap | PITR target unavailable | Continuity alerts |
| Missing KMS key | Encrypted backup unreadable | Key recovery drill |
| Restore requires unavailable identity | Circular dependency | Break-glass access |
| Unverified image/Helm version | Rebuilt cluster incompatible | Artifact retention |
| Restore never tested | RTO unknown | Scheduled isolated drills |
| DNS switched before validation | Customer impact/data divergence | Gated cutover |

## 18. Chapter acceptance checklist

- [ ] RPO and RTO defined for critical services.
- [ ] Cluster, cloud, storage and dependency inventory completed.
- [ ] GitOps/IaC and Kubernetes resource recovery strategy documented.
- [ ] CSI/Velero capabilities and limitations assessed.
- [ ] Database-native backup and PITR requirements documented.
- [ ] Last recoverable point calculation completed.
- [ ] Recovery critical path and RTO estimate completed.
- [ ] EKS/AKS responsibility boundaries reviewed.
- [ ] Backup encryption, retention and offsite protection assessed.
- [ ] Backup monitoring and alerting designed.
- [ ] Recovery tabletop completed.
- [ ] Real isolated restore drill scheduled or executed with evidence.
- [ ] Independent technical review and runtime validation completed before marking Lab Validated.

## 19. Cleanup and safety

This chapter's diagnostics are read-only and do not create resources. If a separate approved recovery lab creates test clusters, namespaces, snapshots or storage copies, remove them only after data validation, evidence retention and owner approval. Never delete production backups, KMS keys or recovery repositories as training cleanup.

**Status:** Draft — runtime validation and technical review pending.

## 20. References

- [Kubernetes Backup and Restore Considerations](https://kubernetes.io/docs/concepts/cluster-administration/cluster-administration-overview/)
- [Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Velero Documentation](https://velero.io/docs/)
- [etcd Disaster Recovery](https://etcd.io/docs/)
- [Kubernetes Disaster Recovery](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [AKS Business Continuity and Disaster Recovery](https://learn.microsoft.com/en-us/azure/aks/operator-best-practices-multi-region)

**Next:** Chapter 072 — etcd Backup and Restore.
