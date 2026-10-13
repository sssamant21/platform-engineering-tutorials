# Chapter 073 — Velero and Persistent Volume Backups

**Track:** Kubernetes Administration · **Part 15 — Backup, Disaster Recovery and Business Continuity**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, storage and cloud platform engineers  
**Prerequisites:** Chapters 036–040, 071–072; kubectl; Windows PowerShell; an approved isolated staging cluster; optional Velero CLI and CSI snapshot support

## 1. Production incident scenario

A production namespace is accidentally deleted. Its Deployments and Services can be recreated from GitOps, but a StatefulSet's PVC held operational data not stored elsewhere. A Velero backup job shows `Completed`; the incident commander needs to know whether it included actual volume bytes, whether the restored volume can attach in another zone, and whether the database state is consistent.

**Mission:** establish what Velero protects, inventory the volume data path, create and inspect a bounded backup in staging, restore into an isolated namespace, validate data integrity, and design operational recovery gates.

**Safety:** All backup creation, restore and destructive tests in this chapter require explicit authorization and an isolated staging environment. Never restore over an active production namespace or database.

### Learning outcomes

1. Explain Velero resource backups, CSI snapshots and file-system backup data movers.
2. Distinguish a backup's `Completed` status from proven application recoverability.
3. Verify BackupStorageLocation, VolumeSnapshotLocation, plugins and CSI prerequisites.
4. Back up namespace resources with explicit scope and retention.
5. Determine whether PVC data is included and how it can be restored.
6. Perform an isolated restore and compare recovered data against a known checksum.
7. Handle namespace remapping, storage classes, restore conflicts and CRD dependencies.
8. Plan cloud-specific EKS/AKS security, portability and recovery operations.
9. Protect database consistency, encryption keys and backup retention.
10. Produce an auditable recovery acceptance report.

## 2. Velero architecture and data protection paths

```text
Velero CLI / schedules
         |
Velero server and controllers
         |
         +-- Kubernetes API resource backup
         |        |
         |     BackupStorageLocation -> object storage
         |
         +-- CSI VolumeSnapshot integration
         |        |
         |     SnapshotClass -> cloud storage snapshot
         |        |
         |     Optional snapshot data movement
         |
         +-- File-system backup / data mover
                  |
             Node agent / repository
                  |
             Backup object storage
```

**Resource backup** stores Kubernetes object definitions and metadata. **Volume backup** protects data bytes through a supported mechanism. A backup can complete while the expected PVC data is excluded, unavailable, inconsistent, or dependent on a snapshot that remains in the original region/account.

### Mechanism comparison

| Method | What is protected | Key limitation |
|---|---|---|
| Kubernetes resources | Namespace objects, RBAC, workloads, PVC definitions | Does not inherently copy volume data |
| CSI VolumeSnapshot | Storage-level volume snapshot | May be crash-consistent and location-bound |
| CSI snapshot data movement | Snapshot content copied to backup repository | Requires supported Velero/data mover configuration |
| File-system backup | Selected mounted volume file content | Requires node agent and accessible filesystem; consistency varies |
| Database-native backup | Application-consistent or PITR-capable database data | Separate procedures and retention dependencies |

The exact features, flags, plugin compatibility and CRDs depend on the installed Velero and CSI versions. Do not assume all mechanisms are enabled.

## 3. Lab 1 — Inventory workloads and persistent state

```powershell
Get-Date -Format o
kubectl config current-context
kubectl get namespaces
kubectl get statefulsets -A
kubectl get pvc -A
kubectl get pv
kubectl get storageclasses
kubectl get volumesnapshotclasses
kubectl get volumesnapshots -A
```

If VolumeSnapshot CRDs are absent, record the missing API rather than treating a command error as an application failure.

### Inventory worksheet

```text
Cluster / cloud / region:
Namespace / application:
Workload controller and replicas:
PVC / PV / StorageClass:
Volume size and access mode:
CSI driver:
Zone topology:
Data owner and classification:
Backup mechanism:
Application quiesce/PITR requirement:
Recovery RPO / RTO:
Cross-region recovery requirement:
Encryption key dependency:
```

**Expected:** every critical PVC maps to a documented protection and restore path.

## 4. Lab 2 — Verify Velero installation and health

```powershell
kubectl get namespaces | Select-String 'velero'
kubectl -n velero get deployments,pods,daemonsets
kubectl -n velero get backupstoragelocations -o wide
kubectl -n velero get volumesnapshotlocations -o wide
kubectl -n velero get backups
kubectl -n velero get schedules
kubectl -n velero get restores
```

The namespace `velero` is conventional, not guaranteed. Substitute the actual installation namespace.

If the CLI is installed:

```powershell
velero version
velero backup-location get
velero backup get
velero schedule get
velero restore get
```

### Installation validation

- Confirm server and CLI versions and supported compatibility.
- Identify cloud provider plugins and credentials/identity.
- Confirm BackupStorageLocation phase and object storage reachability.
- Determine whether CSI integration and data mover/node agent are installed.
- Check controller logs for permission, repository and plugin errors.
- Confirm backup encryption and object storage retention settings.

**Expected:** Velero components are healthy and their data path is known before any backup is created.

## 5. Lab 3 — Validate backup storage and CSI snapshot support

```powershell
kubectl -n velero get backupstoragelocations -o yaml
kubectl -n velero get volumesnapshotlocations -o yaml
kubectl get volumesnapshotclasses -o yaml
kubectl get csidrivers
kubectl get storageclasses -o yaml
```

### Storage decision gates

1. Is object storage in a separate failure domain?
2. Is access controlled by workload identity rather than long-lived credentials?
3. Are snapshot deletion policies compatible with retention?
4. Is a snapshot portable to another zone, region or cluster?
5. Are snapshot bytes actually moved to independent backup storage?
6. Can the recovery environment access the encryption key?
7. Is the backup repository protected from deletion and ransomware?

**Expected:** document whether recovery depends on the source cluster's cloud snapshot and whether offsite copies exist.

## 6. Lab 4 — Create a disposable staging application

**Staging only.** Save `ch073-app.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch073-source
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
  namespace: ch073-source
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  # storageClassName: REPLACE_WITH_APPROVED_CLASS
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: file-demo
  namespace: ch073-source
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: file-demo
  template:
    metadata:
      labels:
        app: file-demo
    spec:
      containers:
        - name: writer
          image: busybox:1.36
          command:
            - /bin/sh
            - -c
            - |
              if [ ! -f /data/marker.txt ]; then
                printf 'ch073-known-content-v1\n' > /data/marker.txt
              fi
              sleep 360000
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: app-data
```

The PVC requires a functioning default StorageClass unless an approved `storageClassName` is supplied. The demo writes a known marker only if absent, to avoid masking a restore failure by overwriting recovered content.

```powershell
kubectl apply -f .\ch073-app.yaml
kubectl -n ch073-source rollout status deployment/file-demo --timeout=180s
kubectl -n ch073-source get pods,pvc
kubectl -n ch073-source exec deployment/file-demo -- cat /data/marker.txt
kubectl -n ch073-source exec deployment/file-demo -- sha256sum /data/marker.txt
```

**Expected:** PVC Bound, Pod Ready and a recorded checksum for the marker file.

## 7. Lab 5 — Create a scoped Velero backup

**Prerequisite:** Velero installed with an approved data-protection mechanism. Backup only the disposable namespace.

```powershell
velero backup create ch073-source-backup --include-namespaces ch073-source --ttl 24h
velero backup get
velero backup describe ch073-source-backup --details
velero backup logs ch073-source-backup
```

The command above creates a namespace backup request. **It does not by itself guarantee volume data is included.** Inspect Velero version, default snapshot behavior, Backup resource fields, PodVolumeBackups, CSI snapshots and backup logs.

For file-system backup in installations that support the option, review `velero backup create --help` and the installed version's `--default-volumes-to-fs-backup` behavior before creating a separate test backup. CSI data movement likewise requires explicit compatible configuration.

### Evidence to collect

```powershell
kubectl -n velero get backup ch073-source-backup -o yaml
kubectl -n velero get podvolumebackups -o wide
kubectl -n ch073-source get volumesnapshots
```

Some CRDs may not be installed; treat those checks as conditional.

**Expected:** backup reaches a terminal state, object coverage is documented, and **volume bytes protection is positively verified** before any destructive exercise.

## 8. Lab 6 — Determine whether data was actually backed up

A `Completed` Backup is necessary but insufficient evidence.

### Evidence matrix

| Evidence | What it establishes |
|---|---|
| Backup resource count | API objects were selected |
| BackupStorageLocation healthy | Repository connection exists |
| CSI VolumeSnapshot ReadyToUse | Storage snapshot was created |
| PodVolumeBackup completed | File-system data path was exercised |
| Snapshot data movement completed | Volume data was copied to backup repository |
| Restore to new PVC succeeds | Storage recovery path works |
| Marker checksum matches | Selected data was recovered intact |
| Application starts and passes checks | Workload-level recovery works |

```powershell
velero backup describe ch073-source-backup --details
velero backup logs ch073-source-backup
kubectl -n velero get backup ch073-source-backup -o yaml
```

**Stop condition:** if you cannot prove volume bytes are protected, **do not delete the source namespace or PVC**. Correct the backup mechanism and rerun validation.

## 9. Lab 7 — Plan namespace remapping and restore isolation

Restoring a backup into an existing active namespace can overwrite or conflict with resources. Use a separate recovery namespace.

### Preflight

```text
Source namespace: ch073-source
Target namespace: ch073-restore
Source PVC/PV/StorageClass:
Target StorageClass and CSI driver:
Backup name and completion:
Volume data method:
Snapshot / repository access:
KMS key and cloud permissions:
Expected marker checksum:
Restore object conflicts:
Recovery owner and approval:
```

For a cross-namespace restore, verify the Velero version's namespace mapping support and any resource-specific name/namespace references. Namespace mapping does not automatically rewrite every application-level URL, Secret reference, external identity or embedded namespace value.

**Expected:** an isolated target and explicit conflict policy are defined before restore.

## 10. Lab 8 — Restore into a separate namespace

**Execute only after Lab 6 positively confirms a usable volume backup.**

```powershell
velero restore create ch073-isolated-restore --from-backup ch073-source-backup --namespace-mappings ch073-source:ch073-restore
velero restore get
velero restore describe ch073-isolated-restore --details
velero restore logs ch073-isolated-restore
kubectl -n ch073-restore get deployments,pods,pvc
```

A restore may need cluster-scoped dependencies such as StorageClasses, CRDs and CSI drivers to exist beforehand. Avoid running two applications against the same writable volume or production data source.

### Verify the data

```powershell
kubectl -n ch073-restore rollout status deployment/file-demo --timeout=180s
kubectl -n ch073-restore exec deployment/file-demo -- cat /data/marker.txt
kubectl -n ch073-restore exec deployment/file-demo -- sha256sum /data/marker.txt
```

Compare the recovered checksum with the source checksum recorded in Lab 4.

**Expected:** recovered Pod becomes Ready, PVC is Bound, marker content and checksum match. If volume data is missing, treat the restore as failed even if Kubernetes objects were restored successfully.

## 11. Lab 9 — Inspect CSI snapshot and restore portability

```powershell
kubectl get volumesnapshots -A
kubectl get volumesnapshotcontents
kubectl get volumesnapshotclasses -o yaml
kubectl get pv -o wide
kubectl -n ch073-restore describe pvc app-data
```

### Common portability blockers

- Snapshot exists only in the original account or region.
- StorageClass names or CSI drivers differ.
- Snapshot handles are provider-specific.
- Snapshot and PVC are in incompatible availability zones.
- KMS keys are inaccessible from the recovery environment.
- Snapshot content deletion policy removed the backing snapshot.
- Cloud quotas prevent provisioning restored disks.
- Volume attachment limits or topology prevent Pod scheduling.

**Expected:** document what can be restored in the same cluster, a different cluster in the same region, and a different region.

## 12. Lab 10 — Database-consistent backups and recovery

A filesystem or CSI snapshot of a running database may capture an inconsistent point unless the database/storage combination provides a supported consistency mechanism.

### PostgreSQL

Prefer a validated base backup plus WAL archiving/PITR strategy where required. A raw PVC snapshot without coordination is not equivalent to a PostgreSQL-native backup. Verify database startup, recovery completion and transaction consistency.

### MongoDB

Use supported replica-set/sharded backup mechanisms with appropriate oplog consistency. Validate collection/index integrity and application reads after restore.

### Elasticsearch / OpenSearch

Use the platform's supported snapshot repository API for index recovery. Do not copy live data directories as a replacement for repository snapshots.

### Redis

Check RDB/AOF persistence and recovery requirements. A cache-only Redis deployment may have different RPO from an authoritative Redis datastore.

### Kafka

Replication is not a standalone backup. Protect required messages, configurations, ACLs, schemas and consumer recovery metadata using an approved design.

**Expected:** backup strategy is selected according to datastore consistency and RPO, not merely the presence of a PVC.

## 13. Lab 11 — EKS and AKS storage integration review

| Concern | EKS | AKS |
|---|---|---|
| Block volumes | EBS CSI | Azure Disk CSI |
| Shared files | EFS CSI | Azure Files CSI |
| Object storage | S3 | Azure Blob |
| Cloud identity | IAM roles / Pod Identity or IRSA | Workload identity / managed identity |
| Encryption | KMS | Azure Key Vault / managed keys |
| Portability | Region/account/snapshot copy rules | Subscription/region/disk copy rules |
| Network dependencies | VPC endpoints, IAM, subnet | Private endpoints, RBAC, VNet |

Verify actual cloud provider plugins, backup credentials and version support. **Do not assume** EBS and Azure Disk snapshots are directly interchangeable or that cloud snapshots are automatically replicated across regions.

### Security checks

- Least-privilege backup writer and restore reader.
- Separate deletion permissions.
- Encryption in transit and at rest.
- Object retention/immutability.
- Protected recovery keys and break-glass access.
- Restore test in a separately authorized namespace/account.
- No credentials or snapshot contents in GitHub.

## 14. Lab 12 — Recovery incident tabletop

**Scenario:** a production namespace is deleted at 14:00 UTC. The latest Velero resource backup is 13:50 UTC. Its CSI snapshots are still in the source region, but the region is unavailable. A second backup from 12:00 UTC contains file-system data copied to offsite object storage.

### Required decisions

1. Declare incident and confirm business RPO/RTO.
2. Inventory resource backups versus recoverable volume data.
3. Determine the latest usable recovery point for each data source.
4. Identify cross-region storage, IAM and KMS prerequisites.
5. Decide whether to recover at 12:00 UTC or use database-native logs.
6. Calculate the resulting data-loss gap and escalate RPO breach.
7. Restore CRDs/operators/storage prerequisites before workloads.
8. Restore into an isolated target; validate data and application SLIs.
9. Obtain approval before DNS/traffic cutover.
10. Record actual recovery duration, data integrity and preventive actions.

**Expected:** reject the false assumption that a newer resource-only backup necessarily provides a newer recoverable database state.

## 15. Backup schedule, retention and recovery cost

### Example policy worksheet

```text
Workload:
Business owner:
RPO:
RTO:
Resource backup frequency:
Volume backup frequency:
Database-native backup/log cadence:
Retention:
Immutable copy:
Cross-region copy:
Encryption key owner:
Last restore drill:
Estimated storage/transfer cost:
Backup and restore service owner:
```

Velero schedules and TTLs govern backup lifecycle within the configured system, but cloud object-lock policies, snapshot retention, backup repository rules and legal holds must be evaluated separately.

### Monitoring signals

- Last successful backup age.
- Backup duration, warnings and errors.
- Failed or missing volume backups.
- Snapshot ReadyToUse state and orphaned snapshots.
- Repository capacity and object availability.
- Restore test age and restore duration.
- Database WAL/oplog coverage and PITR continuity.
- Unexpected backup deletions or permission changes.

## 16. Production troubleshooting matrix

| Symptom | Likely cause | Investigation |
|---|---|---|
| BackupStorageLocation unavailable | Credentials, network, bucket permissions | BSL status and controller logs |
| Backup Completed but PVC empty | Volume data excluded | Backup details, PodVolumeBackup, CSI |
| Snapshot stuck | CSI driver/snapshot controller issue | VolumeSnapshot conditions, CSI logs |
| File-system backup fails | Node agent, mount or repository issue | Node-agent logs and repository status |
| Restore partially failed | CRD missing, RBAC, conflicts | Restore warnings/errors |
| Restored PVC Pending | StorageClass, topology, quota | PVC Events, CSI, cloud volume |
| Pod Pending after restore | Affinity, taints, attach limits | Scheduler Events |
| Data checksum mismatch | Wrong backup, overwritten data | Source and restore evidence |
| DB cannot start | Inconsistent backup or missing logs | Datastore recovery logs |
| Cross-region restore blocked | Snapshot/KMS/identity constraints | Cloud permissions and snapshot copy |
| Backup deleted unexpectedly | TTL/retention/deletion policy | Backup and cloud audit logs |

## 17. Production runbook

### Detect

1. Confirm customer impact, missing resources and affected PVCs.
2. Freeze destructive cleanup and conflicting GitOps reconciliation.
3. Identify the latest **recoverable** resource and data backups.
4. Confirm RPO/RTO and ownership.

### Diagnose

1. Inspect Velero Backup, Restore, BSL and logs.
2. Identify the actual volume data path and snapshot/repository location.
3. Validate KMS keys, cloud identity, CSI and target StorageClass.
4. Assess database consistency and available transaction logs.
5. Confirm isolated recovery environment and resource quotas.

### Restore

1. Obtain change and data owner approval.
2. Recreate prerequisites: cluster, CRDs, CSI, storage and identities.
3. Restore resources and data into isolated target.
4. Validate PVC content, checksum, application health and dependencies.
5. Measure actual RPO/RTO and approve cutover.
6. Re-establish schedules, alerts and backup protection.

### Prevent

- Periodic restore drills with data integrity evidence.
- Backup coverage audits after new PVCs and operators are introduced.
- Offsite immutable copies and key recovery tests.
- Alerting on missing volume backups, not only backup-job failures.
- Standardized recovery runbooks with tested cloud portability.

## 18. Cleanup

After collecting evidence and obtaining staging owner approval:

```powershell
kubectl -n ch073-source get deployment,pods,pvc
kubectl -n ch073-restore get deployment,pods,pvc
kubectl delete namespace ch073-restore
kubectl delete namespace ch073-source
```

**Important:** deletion of PVCs may delete underlying PVs and cloud disks depending on reclaim policy. Inspect the reclaim policy, snapshot deletion policy, backup retention and any legal hold before deleting. Do **not** delete Velero backups, cloud snapshots or backup repositories as routine tutorial cleanup.

## 19. Final acceptance checklist

- [ ] Source cluster and isolated staging context verified.
- [ ] Velero version, plugins, credentials and BSL inspected.
- [ ] CSI snapshot and file-system backup mechanisms identified.
- [ ] PVC inventory and data consistency requirements recorded.
- [ ] Disposable application deployed and checksum captured.
- [ ] Scoped backup created and resource coverage inspected.
- [ ] Actual volume byte protection positively confirmed.
- [ ] Namespace-remapped restore executed or marked not run.
- [ ] Restored PVC Bound and checksum verified.
- [ ] Cloud region, topology, identity and encryption portability reviewed.
- [ ] Database-native recovery and PITR requirements assessed.
- [ ] Incident tabletop and RPO/RTO evidence completed.
- [ ] Cleanup reviewed for PV reclaim and snapshot retention.
- [ ] Independent technical review and runtime validation completed before marking Lab Validated.

**Status:** Draft — runtime validation and independent technical review pending.

## 20. References

- [Velero Documentation](https://velero.io/docs/)
- [Velero Backup Reference](https://velero.io/docs/main/backup-reference/)
- [Velero File System Backup](https://velero.io/docs/main/file-system-backup/)
- [Velero CSI Snapshot Data Movement](https://velero.io/docs/main/csi-snapshot-data-movement/)
- [Kubernetes Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Amazon EKS Storage](https://docs.aws.amazon.com/eks/latest/userguide/storage.html)
- [Azure AKS Storage](https://learn.microsoft.com/en-us/azure/aks/concepts-storage)

**Next:** Chapter 074 — Cross-Cluster Restore and Disaster Recovery.
