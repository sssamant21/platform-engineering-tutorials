# Chapter 075 — Disaster Recovery Simulation Project

**Track:** Kubernetes Administration · **Part 15 — Backup, Disaster Recovery and Business Continuity (final capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, cloud engineers, security engineers and incident commanders  
**Prerequisites:** Chapters 071–074; two explicitly approved staging clusters or a documented tabletop alternative; Windows PowerShell; kubectl; Velero CLI where installed; supported backup repository; monitoring and application test access

## 1. Capstone mission

At 10:00 UTC, the primary Kubernetes region becomes unavailable. The organization must recover a customer-facing application and its persistent data to an independently provisioned recovery cluster. The latest resource backup is recent, but the last independently recoverable volume backup is older. A PostgreSQL database requires point-in-time recovery, cloud identity and CSI settings differ across regions, and an old background worker may still be able to write to the original database.

**Mission:** perform a controlled, evidence-driven disaster recovery simulation that restores service within agreed RPO/RTO, prevents dual writers, validates application and database consistency, and proves that failback can be conducted safely.

**Safety boundary:** This project is **staging-only**. Never simulate an outage by disabling production nodes, deleting production namespaces, revoking real credentials, modifying production DNS, or shutting down a production database. A tabletop is acceptable when an isolated recovery environment is unavailable, but must be labeled **Not run** for runtime tests.

### Objectives

1. Define business-approved RPO/RTO and recovery success criteria.
2. Establish source/target cluster identities and recovery ownership.
3. Inventory Kubernetes resources, PVs, backup locations and external dependencies.
4. Verify backups contain recoverable volume bytes and database logs.
5. Provision/validate an isolated recovery cluster and cloud prerequisites.
6. Restore cluster resources, persistent volumes and database state in dependency order.
7. Prevent split-brain writes and conflicting GitOps reconciliation.
8. Validate application data integrity, functionality and customer SLIs.
9. Rehearse isolated ingress/DNS cutover and a controlled failback decision.
10. Measure actual recovery point, restoration time, cost and remaining risks.

## 2. Reference recovery architecture

```text
Primary staging region                         Secondary staging region
+--------------------------------+             +-------------------------------+
| API / worker / ingress         |             | Recovery ingress / API        |
| PostgreSQL / optional cache    |             | Restored DB / cache           |
| PVCs / CSI / StorageClass      |             | Target CSI / StorageClass     |
| GitOps / Secrets references    |             | GitOps / Secrets references   |
+---------------+----------------+             +---------------+---------------+
                |                                              ^
                |   Independent protected backup repository    |
                +-------------> Object storage ----------------+
                                  |
                          PITR logs / snapshots
                                  |
                    KMS / IAM / DNS / audit / runbook
```

**Core principle:** a successful resource restore does not prove application data recoverability, and an etcd backup does not protect PVC contents. Treat cloud infrastructure, Kubernetes objects, volume bytes and database transaction history as distinct recovery layers.

## 3. Lab 1 — Establish incident roles and RPO/RTO contract

### Scenario assumptions

| Measure | Illustrative objective |
|---|---|
| Customer-facing service RTO | 120 minutes |
| Database RPO | 15 minutes |
| Configuration RPO | 60 minutes |
| Data integrity | No unapproved corruption or dual writes |
| Recovery destination | Independent staging cluster/region |
| Test type | Controlled isolated simulation |

These are example values; replace them with approved objectives.

### Role assignment

- **Incident commander:** declaration, decision log, communications.
- **Platform recovery lead:** cluster, CNI, CSI, Velero, GitOps.
- **DBRE:** database backups, PITR, write fencing and integrity.
- **Application owner:** functional tests and traffic cutover.
- **Security owner:** identities, KMS, secret access and audit.
- **Observer/timekeeper:** timestamps, RPO/RTO evidence and stop conditions.

```text
Exercise ID:
Primary / recovery environments:
Approvers:
Incident declared at (UTC):
RPO/RTO targets:
Test traffic scope:
Data classification:
Maximum spend:
Abort conditions:
Rollback/failback authority:
Evidence storage location:
```

**Expected:** a signed exercise charter before any mutating operation.

## 4. Lab 2 — Verify source and target contexts

```powershell
Get-Date -Format o
kubectl config get-contexts
$source = 'REPLACE_WITH_SOURCE_STAGING_CONTEXT'
$target = 'REPLACE_WITH_RECOVERY_STAGING_CONTEXT'
kubectl --context $source cluster-info
kubectl --context $target cluster-info
kubectl --context $source get nodes -L topology.kubernetes.io/zone -o wide
kubectl --context $target get nodes -L topology.kubernetes.io/zone -o wide
```

**Stop if either context is production or cannot be positively identified.**

### Environment gates

- Source and recovery cloud accounts/subscriptions and regions recorded.
- Recovery identity independent from failed-cluster credentials.
- Network, subnets, routes and private endpoints documented.
- CPU/memory, Pod IP, storage and cloud quotas sufficient.
- Target cluster API, CNI, CoreDNS and CSI operational.
- Container images, Helm charts and CRDs available.
- Backup repository and KMS accessible from recovery region.

**Expected:** cluster identity and foundation prerequisites verified without changing source workloads.

## 5. Lab 3 — Build the complete recovery inventory

```powershell
kubectl --context $source get namespaces
kubectl --context $source get deployments,statefulsets,daemonsets -A
kubectl --context $source get pvc -A
kubectl --context $source get pv
kubectl --context $source get storageclasses
kubectl --context $source get crds
kubectl --context $source get ingress -A
kubectl --context $source get cronjobs -A
```

### Recovery dependency map

```text
Application / owner:
Namespaces and controllers:
CRDs/operators and versions:
GitOps repository and desired revision:
Container image digests:
Secret-manager/KMS references:
Service accounts and cloud workload identities:
PVCs, CSI drivers and StorageClasses:
Database backup, logs and PITR:
Queue/consumer offsets and replay plan:
External DNS, TLS and load balancers:
Third-party allowlists and API dependencies:
Recovery sequence:
Verification owner:
```

**Expected:** the plan identifies dependencies outside Kubernetes, including certificates, DNS, object storage, IAM and database transaction logs.

## 6. Lab 4 — Verify recoverable backups and last safe recovery point

```powershell
kubectl --context $source -n velero get backups
kubectl --context $source -n velero get backupstoragelocations
kubectl --context $source -n velero get schedules
kubectl --context $source get volumesnapshots -A
```

Commands require Velero and snapshot APIs. If absent, record **Not installed** and use the organization's supported backup solution.

With Velero CLI explicitly configured for the source context:

```powershell
kubectl config current-context
velero backup get
velero backup describe REPLACE_WITH_BACKUP --details
velero backup logs REPLACE_WITH_BACKUP
```

**Important:** the Velero CLI uses the current kubeconfig context; confirm it before each operation. A completed Backup may protect API objects but not volume data. Confirm the configured CSI snapshot, snapshot data movement, or file-system backup path and its successful completion.

### Recoverability evidence

| Layer | Required proof |
|---|---|
| Kubernetes objects | Backup metadata and included resources |
| PVC bytes | Snapshot/data mover/repository plus tested restore |
| Database | Valid base backup and complete required WAL/oplog |
| Encryption | Recovery key accessible in target |
| Container images | Referenced digests accessible |
| Cloud resources | Rebuild plan and quotas validated |

**Expected:** select the **latest recoverable** point, not merely the newest backup timestamp.

## 7. Lab 5 — Prepare a safe staging dataset

Use a disposable test application with a known data marker. Never use live customer data without explicit approval.

Save `ch075-source.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch075-source
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
  namespace: ch075-source
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 1Gi
  # storageClassName: REPLACE_WITH_APPROVED_SOURCE_CLASS
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: file-app
  namespace: ch075-source
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: file-app
  template:
    metadata:
      labels:
        app: file-app
    spec:
      containers:
        - name: app
          image: busybox:1.36
          command:
            - /bin/sh
            - -c
            - |
              if [ ! -f /data/marker.txt ]; then
                printf 'ch075-dr-checkpoint-v1\n' > /data/marker.txt
              fi
              sleep 360000
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: data
```

Use a cluster-approved pinned image in real execution; the example tag is illustrative.

```powershell
kubectl --context $source apply -f .\ch075-source.yaml
kubectl --context $source -n ch075-source rollout status deployment/file-app --timeout=180s
kubectl --context $source -n ch075-source get pods,pvc
kubectl --context $source -n ch075-source exec deployment/file-app -- sha256sum /data/marker.txt
```

**Expected:** PVC Bound, Pod Ready and source checksum recorded. The app writes the marker only when absent so a missing restore cannot be hidden by a startup overwrite.

## 8. Lab 6 — Create and validate a staging recovery backup

**Precondition:** source context confirmed, Velero configured, repository permissions approved, and a compatible volume-data mechanism enabled.

```powershell
kubectl config current-context
velero backup create ch075-dr-source --include-namespaces ch075-source --ttl 24h
velero backup describe ch075-dr-source --details
velero backup logs ch075-dr-source
```

A resource backup request does **not** guarantee that PVC data was captured. Inspect Backup resource status, CSI snapshots, PodVolumeBackups or snapshot data movement for the installed version.

```powershell
kubectl --context $source -n velero get backup ch075-dr-source -o yaml
kubectl --context $source -n velero get podvolumebackups
kubectl --context $source -n ch075-source get volumesnapshots
```

Treat missing optional CRDs as conditional, not proof of failure.

**Stop condition:** if recoverable volume bytes cannot be positively established, do not proceed to destructive source simulation. Repair the backup mechanism first.

## 9. Lab 7 — Verify target storage, identities and restore portability

```powershell
kubectl --context $target get storageclasses -o yaml
kubectl --context $target get csidrivers
kubectl --context $target get volumesnapshotclasses
kubectl --context $target get crds
kubectl --context $target get pods -A
kubectl --context $target get events -A --sort-by=.lastTimestamp
```

### Portability decision table

| Issue | Required action |
|---|---|
| Different StorageClass | Map source class to approved target class |
| Snapshot region-bound | Copy snapshot or use independent data mover |
| CSI driver unavailable | Install compatible driver or change recovery path |
| Different KMS key | Verify key grants and recovery key availability |
| Missing CRD/operator | Restore/install compatible prerequisites first |
| Different workload identity | Rebind target-specific service accounts |
| Registry unavailable | Mirror approved image digests |
| GitOps conflict | Pause/reconfigure reconciliation with owner approval |

**Expected:** all recovery prerequisites are available before a restore request is created.

## 10. Lab 8 — Execute isolated cross-cluster restore

**Target staging cluster only.** Verify Velero CLI context and BackupStorageLocation visibility in the target. Backups stored solely in source-region snapshots may not be portable.

```powershell
kubectl config current-context
kubectl --context $target -n velero get backupstoragelocations
kubectl --context $target -n velero get backups
```

Switch kubeconfig only after explicit verification:

```powershell
kubectl config use-context $target
kubectl config current-context
velero backup get
velero restore create ch075-dr-restore --from-backup ch075-dr-source --namespace-mappings ch075-source:ch075-recovery
velero restore get
velero restore describe ch075-dr-restore --details
velero restore logs ch075-dr-restore
```

If the target backup is not visible, **do not fabricate a restore result**. Resolve BSL object access, metadata synchronization, credentials and volume data portability first.

### Validation

```powershell
kubectl --context $target -n ch075-recovery get deployments,pods,pvc
kubectl --context $target -n ch075-recovery get events --sort-by=.lastTimestamp
kubectl --context $target -n ch075-recovery rollout status deployment/file-app --timeout=180s
kubectl --context $target -n ch075-recovery exec deployment/file-app -- cat /data/marker.txt
kubectl --context $target -n ch075-recovery exec deployment/file-app -- sha256sum /data/marker.txt
```

**Expected:** recovered checksum matches the source checksum and the restored PVC is independently usable. If it differs or the file is missing, mark the restore **Failed** even if Velero reports Completed.

## 11. Lab 9 — Database-consistent recovery and single-writer fencing

The disposable marker validates volume data transport, not a transactional database recovery.

### PostgreSQL PITR exercise (design or separately approved DBRE lab)

1. Verify a valid base backup and complete WAL archive.
2. Select a recovery target timestamp within available WAL coverage.
3. Restore into an isolated database environment.
4. Confirm recovery completion and schema/data consistency.
5. Validate application queries and known transaction markers.
6. Keep the former primary fenced from writes.
7. Document replication, pool and connection routing changes.

### Other data systems

- **MongoDB:** replica-set/sharded consistency and oplog coverage.
- **Elasticsearch/OpenSearch:** repository snapshots and shard recovery.
- **Redis:** RDB/AOF or safe cache reconstruction according to RPO.
- **Kafka:** retained messages, schemas, ACLs, consumer offsets and replay behavior.

**Never assume Kubernetes volume restore alone meets database RPO.**

### Split-brain prevention

DNS redirection is not fencing. Background workers, CronJobs, long-lived connections and direct database clients can continue writing to the former primary. Use a documented single-writer mechanism and verify that old write paths are disabled before promotion.

## 12. Lab 10 — Validate application readiness and traffic cutover

### Recovery acceptance probes

```powershell
kubectl --context $target -n ch075-recovery get deployments,pods,pvc
kubectl --context $target -n ch075-recovery get events --sort-by=.lastTimestamp
kubectl --context $target get ingress -A
kubectl --context $target get nodes -o wide
```

For an actual application, verify through an **isolated recovery hostname**:

- TLS/certificate and ingress routing.
- Health, readiness and dependency probes.
- Read-only and controlled write transactions.
- Data integrity and database leader identity.
- Queue consumer behavior and duplicate handling.
- Latency, error rate and sustained throughput.
- DNS TTL, client caching and load balancer propagation.

### Cutover decision gates

1. Data owner confirms recoverable point and consistency.
2. Platform lead confirms recovery capacity and security controls.
3. Application owner confirms functional/SLO acceptance.
4. DBRE confirms single writer and connection budgets.
5. Incident commander approves cutover.
6. Rollback/failback authority and communication plan are explicit.

**Expected:** a documented go/no-go decision. No production DNS changes are performed in this exercise.

## 13. Lab 11 — Measure actual RPO, RTO and recovery critical path

Illustrative timestamps:

```text
Latest recoverable application state: 09:52 UTC
Disaster declaration:             10:00 UTC
Recovery cluster ready:           10:30 UTC
Database/PVC restore complete:    11:05 UTC
Application verified:             11:20 UTC
Recovery endpoint serving:        11:35 UTC

Observed data gap: 8 minutes
Observed service RTO: 95 minutes
```

These are sample calculations, **not actual test results**. Use measured timestamps from your exercise.

### Recovery critical-path table

| Phase | Start | End | Owner | Evidence |
|---|---|---|---|---|
| Declare/authorize | Record | Record | Incident commander | Timeline |
| Cloud/cluster foundation | Record | Record | Platform | Node/API health |
| Identity/CSI/CRDs | Record | Record | Platform/security | Prerequisite checks |
| Database and PVC restore | Record | Record | DBRE/storage | Integrity checks |
| Application rollout | Record | Record | Application | Readiness |
| Traffic verification | Record | Record | Application/SRE | Synthetic SLIs |

**RTO is not satisfied when Pods merely become Running.** Measure to restored customer service at the agreed endpoint. Report RPO separately for configuration and authoritative data when appropriate.

## 14. Lab 12 — Failback and post-disaster reconciliation tabletop

**Scenario:** the original region becomes reachable after recovery service is active. The old database contains stale data and the old GitOps controller wants to reconcile workloads.

### Required sequence

1. Declare the recovery region authoritative.
2. Keep former primary write paths fenced.
3. Compare old and recovered data timelines.
4. Rebuild/reconcile the former cluster without enabling stale writers.
5. Synchronize authoritative data back using approved database procedures.
6. Verify schemas, transaction logs, queue offsets and application versions.
7. Test old region through isolated endpoints.
8. Obtain a separate failback change approval.
9. Fence writes, switch authority, then verify SLOs and integrity.
10. Re-establish backup/replication and document residual risks.

**Expected:** a failback plan that prevents divergence and treats data synchronization as a first-class step, not merely a DNS reversal.

## 15. Disaster simulation injects and evaluation

For a tabletop, the facilitator can introduce the following injects without damaging any cluster:

| Inject | Expected response |
|---|---|
| Primary region unreachable | Activate recovery decision tree |
| Latest Velero backup lacks PVC data | Select latest recoverable data point |
| Target KMS key unavailable | Stop restore; security escalation |
| CSI snapshot region-bound | Use approved copy/data mover |
| Target StorageClass mismatch | Apply reviewed mapping |
| PostgreSQL WAL gap | Recalculate RPO and obtain approval |
| Old CronJob still writing | Fence background writers |
| DNS resolves but 5xx remains high | Validate dependencies and readiness |
| Failback proposed before sync | Reject unsafe cutover |

### Evaluation dimensions

- Correctness of recovery decisions.
- Time to identify latest recoverable point.
- Completeness of dependency and security checks.
- Application data integrity.
- Split-brain prevention.
- RPO/RTO evidence and communications.
- Cost and cloud quota awareness.
- Quality of rollback and failback planning.

## 16. Troubleshooting matrix

| Symptom | Likely domain | Investigation |
|---|---|---|
| Target cannot see backup | BSL/object credentials or metadata | BSL status, bucket access |
| Restore Completed but data missing | Volume backup excluded | CSI/data mover evidence |
| PVC Pending | StorageClass, topology, quota | PVC Events, CSI logs |
| Pod Pending | Requests, taints, IPs, affinity | FailedScheduling |
| ImagePullBackOff | Registry/digest/identity | Pod Events and registry access |
| Secrets unusable | KMS/workload identity mismatch | Key grants and secret manager |
| Database fails startup | Inconsistent backup/missing WAL | DB recovery logs |
| Data differs after restore | Wrong point or split-brain | Checksums and write timeline |
| Recovery endpoint fails | Ingress, TLS, dependencies | Synthetic probes and traces |
| Failback creates stale writes | Incomplete fencing | Database roles and clients |

## 17. Incident commander runbook

### Declare

1. Confirm impact and incident severity.
2. Establish RPO/RTO and authority to recover.
3. Assign platform, DBRE, application, security and communications owners.
4. Freeze destructive changes and preserve evidence.

### Restore

1. Verify backup and last recoverable point.
2. Prepare target cluster and cloud prerequisites.
3. Restore CRDs/operators, identity, storage and data.
4. Recover databases and validate single-writer fencing.
5. Restore workloads and confirm application integrity.
6. Approve traffic cutover only after SLO and security gates.

### Stabilize

1. Monitor latency, errors, queues, database health and cost.
2. Re-enable backup schedules and offsite copies.
3. Record actual RPO/RTO, gaps and customer impact.
4. Plan a separate approved failback.
5. Complete blameless review and assign remediation.

## 18. Final capstone report template

```text
Exercise title and date:
Source/target clusters and regions:
Scenario and failure assumptions:
Participants and approvals:
RPO/RTO targets:
Backup resource timestamp:
Latest verified data recovery point:
Backup mechanism and repository:
Volume restore method and evidence:
Database PITR target and integrity results:
Cluster/CSI/identity compatibility:
Source marker SHA-256:
Restored marker SHA-256:
Application tests and SLIs:
Old-writer fencing evidence:
Cutover go/no-go decision:
Actual RPO:
Actual RTO:
Cloud spend and transfer estimate:
Failed steps / blocked dependencies:
Security findings:
Failback plan:
Remediation owner / due date:
Independent technical reviewer:
Overall result: Pass / Fail / Not run
```

**Do not mark Pass** if volume data is missing, RPO/RTO targets are exceeded without documented acceptance, dual-writer risk remains, or critical validation was skipped.

## 19. Acceptance checklist

- [ ] Exercise charter, roles, RPO/RTO and abort criteria approved.
- [ ] Source and target staging contexts positively verified.
- [ ] Full recovery dependency inventory completed.
- [ ] Latest recoverable resource and volume backup identified.
- [ ] Encryption keys and independent backup access validated.
- [ ] Source staging marker and checksum recorded.
- [ ] Backup coverage and volume bytes verified.
- [ ] Target CSI, StorageClass, CRDs and identities reviewed.
- [ ] Isolated cross-cluster restore completed or marked Not run.
- [ ] Restored PVC data checksum verified.
- [ ] Database-native PITR and consistency assessed.
- [ ] Single-writer fencing and GitOps reconciliation reviewed.
- [ ] Application SLO and isolated endpoint checks completed.
- [ ] Measured RPO/RTO and recovery critical path recorded.
- [ ] Failback and data reconciliation plan documented.
- [ ] Incident injects and tabletop evaluated.
- [ ] Final capstone report and remediation owners recorded.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

## 20. Cleanup and evidence retention

**Never delete production backups, primary clusters, cloud snapshots or KMS keys.** In staging, inspect reclaim policies, legal holds and snapshot retention before deleting PVCs or backup artifacts.

```powershell
kubectl --context $source -n ch075-source get deployments,pods,pvc
kubectl --context $target -n ch075-recovery get deployments,pods,pvc
```

Only after approved evidence retention and cleanup review:

```powershell
kubectl --context $target delete namespace ch075-recovery
kubectl --context $source delete namespace ch075-source
```

The chapter's backup may have a 24-hour TTL, but cloud snapshots and independent repositories can have separate retention policies. Never assume namespace deletion safely cleans up backup storage.

**Part 15 writing milestone:** Chapters 071–075 drafted. Runtime validation and independent technical review remain pending.

## 21. References

- [Kubernetes Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Velero Documentation](https://velero.io/docs/)
- [Velero Restore Reference](https://velero.io/docs/main/restore-reference/)
- [Velero CSI Snapshot Data Movement](https://velero.io/docs/main/csi-snapshot-data-movement/)
- [etcd Disaster Recovery](https://etcd.io/docs/v3.5/op-guide/recovery/)
- [Amazon EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Azure AKS Business Continuity and DR](https://learn.microsoft.com/en-us/azure/aks/operator-best-practices-multi-region)

**Next:** Chapter 076 — Amazon EKS Architecture and Provisioning (Part 16).
