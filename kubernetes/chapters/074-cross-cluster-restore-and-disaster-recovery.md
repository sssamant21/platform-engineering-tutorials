# Chapter 074 — Cross-Cluster Restore and Disaster Recovery

**Track:** Kubernetes Administration · **Part 15 — Backup, Disaster Recovery and Business Continuity**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, cloud/platform engineers and incident commanders  
**Prerequisites:** Chapters 071–073; two approved staging Kubernetes clusters; kubectl contexts; Windows PowerShell; Velero or equivalent backup tooling where installed; GitOps/IaC access; cloud IAM and storage knowledge

## 1. Production incident scenario

A regional outage makes the primary Kubernetes cluster unavailable. The application team has GitOps manifests and Velero backups, but the recovery cluster runs a different CSI storage class, uses different workload identities, and cannot directly attach the primary region's block volumes. PostgreSQL must be restored to a consistent point, and traffic must not be redirected until application and data integrity checks pass.

**Mission:** design and rehearse a cross-cluster restore that meets business RPO/RTO objectives, prevents split-brain writes, validates restored application state, and includes a controlled failback plan.

**Safety boundary:** all exercises must use isolated staging clusters and nonproduction data. Do not modify production DNS, cloud routes, databases, object storage, backup repositories or active GitOps controllers as part of this chapter.

### Learning outcomes

1. Compare active/passive, warm standby and active/active disaster recovery.
2. Inventory cluster and cloud dependencies required for cross-cluster restoration.
3. Determine Velero resource and volume backup portability.
4. Restore Kubernetes objects into a different cluster without conflicting identities.
5. Handle CSI drivers, StorageClasses, PV topology and snapshot location restrictions.
6. Recover application-consistent databases and avoid dual-writer split-brain.
7. Plan ingress/DNS cutover and verify service SLOs.
8. Model RPO/RTO, replication lag and critical-path recovery time.
9. Design safe failback and post-disaster reconciliation.
10. Produce a tested recovery acceptance report.

## 2. Disaster recovery architectures

| Architecture | Description | Primary tradeoff |
|---|---|---|
| Cold standby | Build recovery cluster after disaster | Lower standby cost, longer RTO |
| Warm standby | Prebuilt cluster with reduced capacity | Faster recovery, ongoing cost |
| Hot standby | Preprovisioned near-production capacity | Faster cutover, higher cost |
| Active/active | Multiple serving regions | Complex consistency, routing and failure handling |

A replicated cluster is not necessarily a backup. Replication can propagate accidental deletions or corruption; independent, versioned backups remain essential.

### Recovery architecture

```text
Primary region / cluster                 Recovery region / cluster
+---------------------------+             +--------------------------+
| Ingress -> Applications   |             | Ingress -> Applications  |
| Stateful dependencies     |             | Restored state / standby |
| CSI volumes               |             | Compatible storage       |
| GitOps + Secrets          |             | GitOps + Secrets         |
+------------+--------------+             +------------+-------------+
             |                                         ^
             | Backup / replication / object copies    |
             +-------------> Protected repository -----+
                                      |
                          KMS, IAM, DNS, runbooks
```

## 3. Lab 1 — Confirm source and recovery contexts

```powershell
kubectl config get-contexts
$source = 'REPLACE_WITH_SOURCE_STAGING_CONTEXT'
$target = 'REPLACE_WITH_TARGET_STAGING_CONTEXT'
kubectl --context $source cluster-info
kubectl --context $target cluster-info
kubectl --context $source get nodes -L topology.kubernetes.io/zone -o wide
kubectl --context $target get nodes -L topology.kubernetes.io/zone -o wide
Get-Date -Format o
```

### Preflight gates

- Confirm both clusters are nonproduction.
- Confirm independent recovery credentials and audit logs.
- Identify regions, VPC/VNet, subnet IPs and cloud quotas.
- Check Kubernetes versions and installed APIs.
- Confirm target storage and networking prerequisites.
- Record authorized recovery owner and rollback contact.

**Expected:** source and target contexts are positively identified before any write command.

## 4. Lab 2 — Build a cross-cluster dependency map

```powershell
kubectl --context $source get namespaces
kubectl --context $source get deployments,statefulsets,daemonsets -A
kubectl --context $source get pvc -A
kubectl --context $source get storageclasses
kubectl --context $source get crds
kubectl --context $source get ingress -A
kubectl --context $target get storageclasses
kubectl --context $target get crds
```

### Dependency worksheet

```text
Service and owner:
Source cluster / region:
Recovery cluster / region:
Business RPO / RTO:
GitOps/IaC source:
CRDs/operators and versions:
Container registry and image availability:
Secrets/KMS/identity dependencies:
Network/DNS/ingress dependencies:
PVCs, CSI driver and snapshot portability:
Database and queue consistency requirements:
External APIs and third-party allowlists:
Backup repository and offsite copy:
Recovery order:
Verification and rollback owner:
```

**Expected:** recovery prerequisites include cloud resources and external dependencies, not only Kubernetes YAML.

## 5. Lab 3 — Verify recovery cluster foundations

```powershell
kubectl --context $target get nodes -o wide
kubectl --context $target get storageclasses -o yaml
kubectl --context $target get csidrivers
kubectl --context $target get ingressclasses
kubectl --context $target get crds
kubectl --context $target get pods -A
kubectl --context $target get events -A --sort-by=.lastTimestamp
```

### Foundation checks

1. Kubernetes API, RBAC and admission work.
2. Nodes have sufficient allocatable CPU/memory and Pod IP capacity.
3. CNI, CoreDNS and ingress controller are healthy.
4. CSI driver and snapshot controller are compatible.
5. StorageClasses and volume topology are mapped.
6. Required CRDs/operators exist at supported versions.
7. Secrets manager, KMS and workload identity are accessible.
8. Container images and Helm charts are available.
9. External DNS and certificate management are planned.
10. Backup repository access is read-only where possible.

**Expected:** recovery cluster is capable of running the restored application before data restore begins.

## 6. Lab 4 — Verify backup availability from the target cluster

Velero's resource backup and persistent data mechanisms may have different portability properties. A BackupStorageLocation can point to object storage, but CSI snapshots may remain tied to the source cloud account or region.

```powershell
kubectl --context $target -n velero get backupstoragelocations
kubectl --context $target -n velero get backups
kubectl --context $target -n velero get restores
kubectl --context $target get volumesnapshotclasses
```

These commands require Velero/CSI resources to be installed. If the target does not have them, document the prerequisite rather than assuming a failure.

### Backup portability checklist

| Backup component | Cross-cluster requirement |
|---|---|
| Kubernetes objects | Compatible APIs, CRDs, admission and RBAC |
| Velero object storage | Target can access backup bucket/prefix |
| CSI snapshot | Snapshot can be copied/shared or restored by target driver |
| File-system backup | Repository accessible; node agent/data mover compatible |
| Secrets | Encryption keys and identity permissions available |
| Database PITR | Base backup and continuous logs available |
| Images | Registry reachable and images retained |

**Expected:** identify the latest backup that is actually recoverable in the target environment.

## 7. Lab 5 — StorageClass, PVC and topology migration

A PVC restored from another cluster may reference a StorageClass or CSI driver not present in the target. Cloud disk snapshots can be region-specific, and a PV may contain source-specific identifiers.

### Storage migration plan

```text
Source StorageClass:
Source CSI driver:
Source volume/snapshot:
Target StorageClass:
Target CSI driver:
Snapshot copy or file-level restore method:
Target availability zone:
Volume encryption key:
Expected capacity/IOPS/throughput:
Data consistency procedure:
Validation checksum/query:
```

### Design-only PVC example

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
  namespace: ch074-restore
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: REPLACE_WITH_TARGET_STORAGE_CLASS
  resources:
    requests:
      storage: 10Gi
```

**Do not apply** without checking target storage provisioning and ensuring it will not conflict with restored PV binding. Use Velero resource modifiers or an approved migration workflow for controlled transformations; do not blindly edit bound PVs.

**Expected:** a storage migration approach that preserves data and avoids invalid source volume handles.

## 8. Lab 6 — Restore resources into an isolated namespace

**Staging-only.** Before execution, verify a completed backup, volume data protection and target prerequisites.

With the Velero CLI configured for the **target** cluster:

```powershell
kubectl config current-context
velero backup get
velero restore create ch074-recovery-test --from-backup REPLACE_WITH_BACKUP --namespace-mappings SOURCE_NAMESPACE:ch074-restore
velero restore get
velero restore describe ch074-recovery-test --details
velero restore logs ch074-recovery-test
```

**Important:** `velero` CLI uses the current kubeconfig context. Confirm it points to the target cluster immediately before restore. The backup must be visible in the target's BackupStorageLocation, and namespace mapping must be supported by the installed Velero version.

### Restore conflict controls

- Never restore over an active production namespace.
- Review cluster-scoped resources and CRDs separately.
- Prevent GitOps from immediately replacing restored state.
- Avoid restoring source-region LoadBalancer addresses and provider-specific annotations unchanged.
- Ensure Secrets reference target identities and keys.
- Validate restored PVC data before starting write-capable applications.

**Expected:** restore finishes without unreviewed conflicts, and the target namespace contains expected resources.

## 9. Lab 7 — Validate data and application readiness

```powershell
kubectl --context $target -n ch074-restore get deployments,statefulsets,pods,pvc
kubectl --context $target -n ch074-restore get events --sort-by=.lastTimestamp
kubectl --context $target -n ch074-restore describe pvc REPLACE_WITH_PVC
kubectl --context $target -n ch074-restore rollout status deployment/REPLACE_WITH_DEPLOYMENT --timeout=180s
```

### Data validation requirements

- Verify known checksums or database record counts.
- Validate application schema and migration version.
- Confirm transaction-log replay/PITR completion.
- Check replication status, consumer offsets and cache consistency.
- Confirm application reads and controlled writes in staging.
- Compare recovered timestamp against RPO.
- Capture application latency/error SLIs.

**Expected:** data is usable and application semantics are correct—not just that Pods are Running.

## 10. Lab 8 — Stateful database and queue recovery

### PostgreSQL

Restore a validated base backup and WAL archive/PITR to the approved target. Verify recovery timeline, read/write role, replication slots and connection pooling. Prevent the old primary from accepting writes after cutover.

### MongoDB

Use supported replica-set/sharded-cluster recovery tooling. Verify replica set identity, oplog coverage, indexes and application consistency.

### Elasticsearch/OpenSearch

Use repository snapshots and supported restore APIs. Validate cluster version compatibility, shard allocation and recovery throughput.

### Redis

Decide whether cache rewarming or RDB/AOF recovery is required. Validate persistence, memory capacity and client routing.

### Kafka

Protect required messages, topic configs, ACLs, schemas and consumer recovery metadata. Validate replay and idempotency; broker replication alone is not a backup.

**Expected:** each stateful service has a separate data owner, consistency procedure and cutover gate.

## 11. Lab 9 — Prevent split-brain and dual writers

A disaster may be partial: the primary cluster can become reachable again after recovery traffic has moved to the secondary cluster. Two writable primaries can corrupt data or diverge.

### Fencing and cutover sequence

1. Declare disaster and identify authoritative data source.
2. Disable or fence primary write paths where technically possible.
3. Confirm recovery data point and accepted data loss.
4. Restore/promote secondary datastore using approved vendor procedure.
5. Validate single-writer ownership and application connection routing.
6. Enable writes in recovery cluster.
7. Shift ingress/DNS traffic in a controlled manner.
8. Monitor error rates, replication and data integrity.
9. Keep old primary fenced until a formal failback plan is approved.

**DNS changes alone do not guarantee fencing.** Long-lived connections, background jobs, queues and direct database clients may continue writing to the old environment.

## 12. Lab 10 — DNS, ingress and traffic cutover

### Traffic cutover checklist

```text
Target ingress endpoint:
Certificate and TLS validation:
Health/readiness checks:
DNS TTL and propagation assumptions:
Load balancer configuration:
Firewall/allowlist dependencies:
Session affinity and client reconnect:
Queue consumers / CronJobs / background workers:
Database write ownership:
Rollback/failback decision owner:
Customer communications:
```

### Safe validation

- Test recovery endpoints through an isolated hostname.
- Verify TLS certificates and target routing.
- Run synthetic transactions with nonproduction data.
- Confirm dependencies and rate limits.
- Shift traffic gradually where supported.
- Track latency, 5xx, queue lag and database health.

**Expected:** service restoration is measured at the customer-facing endpoint, not only at the Kubernetes API.

## 13. Lab 11 — RPO/RTO and recovery cost model

### Illustrative timeline

```text
Last recoverable database point: 09:55 UTC
Disaster declared: 10:00 UTC
Recovery cluster foundation ready: 10:25 UTC
Data restore complete: 11:05 UTC
Application verification complete: 11:20 UTC
Traffic cutover complete: 11:30 UTC

Potential data gap: 5 minutes
Measured customer service RTO: 90 minutes
```

These are example timestamps, not test results.

### Capacity and cost dimensions

- Recovery cluster node/Pod capacity and one-zone headroom.
- Storage copy and restore throughput.
- Object storage transfer and cross-region egress.
- Database recovery CPU/memory/IOPS requirements.
- Cloud quotas and instance availability.
- Warm standby costs versus cold rebuild RTO.
- Backup retention, immutable copies and KMS costs.

**Expected:** compare actual recoverable point and end-to-end restoration time with business-approved RPO/RTO.

## 14. Lab 12 — Controlled failback planning

Failback is **not** simply reversing DNS. The former primary may have stale data, incompatible cluster state or divergent database writes.

### Failback runbook

1. Declare the recovery region authoritative until proven otherwise.
2. Repair/rebuild the former primary cluster without exposing stale writers.
3. Establish replication or backup-based synchronization from current primary.
4. Validate schema, data integrity, offsets and replication lag.
5. Verify workload identity, storage and network compatibility.
6. Test restored applications on isolated endpoints.
7. Schedule a change window and obtain application/DBRE approval.
8. Fence writes, perform controlled cutover and verify SLIs.
9. Re-enable backups and replication in the final topology.
10. Record measured failback duration and residual risks.

**Expected:** no dual writers and no unreviewed data regression during failback.

## 15. Production incident tabletop

**Scenario:** primary EKS cluster is unavailable after a regional networking event. Velero resource backups are current, but EBS snapshots remain in the primary region. PostgreSQL WAL archives and a previous full backup are accessible in the recovery region. A legacy batch job continues retrying writes to the old database endpoint.

### Investigation tasks

1. Identify the last **recoverable** application/database state.
2. Determine whether CSI snapshot data is portable.
3. Restore prerequisites in the recovery region.
4. Fence legacy batch jobs and direct DB writers.
5. Restore database with PITR and validate integrity.
6. Reconcile GitOps without overwriting recovered state.
7. Verify application health through isolated endpoints.
8. Obtain approval for traffic cutover.
9. Measure RPO/RTO and communicate any breach.
10. Plan failback and long-term remediation.

**Expected:** recognize backup portability and writer fencing as critical gates, not optional details.

## 16. Troubleshooting matrix

| Symptom | Likely cause | First investigation |
|---|---|---|
| Target cannot see Velero backup | BSL credentials/prefix mismatch | BSL status, object access |
| Restore fails on CRDs | Operator/API missing or incompatible | CRD inventory and versions |
| PVC remains Pending | StorageClass/CSI/topology mismatch | PVC Events and CSI logs |
| Snapshot not accessible | Region/account restrictions | Cloud snapshot copy permissions |
| Secrets unreadable | KMS/key mismatch | Key and workload identity |
| Image pull fails | Registry access/retention | ImagePullBackOff Events |
| Application Ready but data wrong | Wrong restore point/schema | Checksums and DB queries |
| DNS points to target but errors persist | TLS, routing, dependencies | Ingress and synthetic tests |
| Both regions accept writes | Incomplete fencing | DB leader and client routing |
| Failback causes data regression | Stale former primary | Replication and integrity checks |

## 17. Operational runbook

### Detect and decide

1. Confirm customer impact and disaster declaration criteria.
2. Assign incident commander, platform owner, DBRE and communications lead.
3. Establish RPO/RTO and authoritative data source.
4. Confirm recovery region access and backup portability.

### Restore

1. Build or validate recovery cluster foundations.
2. Restore CRDs/operators, identities, networking and storage.
3. Recover application-consistent database and volume state.
4. Restore workloads into isolated target namespaces.
5. Verify data integrity and customer-facing health.
6. Fence old writers and authorize traffic cutover.

### Stabilize and fail back

1. Monitor SLIs, queue lag, DB health and cloud spend.
2. Re-establish backups and replication.
3. Rebuild former primary safely.
4. Execute separately approved failback.
5. Document actual RPO/RTO and blameless RCA.

## 18. Cross-cluster DR acceptance checklist

- [ ] Two staging contexts and owners verified.
- [ ] RPO/RTO and disaster declaration criteria approved.
- [ ] Recovery dependency map completed.
- [ ] Target cluster CNI, CSI, CRDs and identities validated.
- [ ] BackupStorageLocation and volume data portability verified.
- [ ] Target StorageClass and snapshot conversion plan documented.
- [ ] Isolated restore performed or marked not run.
- [ ] Restored data integrity and application behavior verified.
- [ ] Stateful database/queue recovery validated.
- [ ] Primary write fencing and split-brain prevention reviewed.
- [ ] DNS/ingress cutover plan and rollback gates documented.
- [ ] Measured RPO/RTO and cost model recorded.
- [ ] Controlled failback procedure reviewed.
- [ ] Incident tabletop completed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

## 19. Cleanup and safety

Do not delete source backups, production snapshots, primary-region resources or recovery evidence. Remove only lab-owned resources from the **verified staging target context** after owner approval:

```powershell
kubectl --context $target -n ch074-restore get all,pvc
kubectl --context $target delete namespace ch074-restore
```

Before deletion, inspect PVC reclaim policies, snapshot retention and object storage dependencies. Avoid deleting the recovery cluster itself unless it was created specifically for the lab and a separate decommission plan is approved.

**Status:** Draft — runtime validation and independent technical review pending.

## 20. References

- [Velero Documentation](https://velero.io/docs/)
- [Velero Restore Reference](https://velero.io/docs/main/restore-reference/)
- [Velero CSI Snapshot Data Movement](https://velero.io/docs/main/csi-snapshot-data-movement/)
- [Kubernetes Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes Disaster Recovery Considerations](https://kubernetes.io/docs/concepts/cluster-administration/)
- [Amazon EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Azure AKS Business Continuity and DR](https://learn.microsoft.com/en-us/azure/aks/operator-best-practices-multi-region)

**Next:** Chapter 075 — Disaster Recovery Simulation Project (Part 15 capstone).
