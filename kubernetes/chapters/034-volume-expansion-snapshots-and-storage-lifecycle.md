# Chapter 034 — Volume Expansion, Snapshots and Storage Lifecycle

**Track:** Kubernetes Administration · **Part 07 — Kubernetes Storage**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 031–033; kubectl, Windows PowerShell, disposable cluster, compatible CSI driver and StorageClass; snapshot controller/CRDs and CSI snapshotter for snapshot labs

## 1. Production scenario

A PostgreSQL data volume is at 90% capacity. An operator expands its PVC, but filesystem free space does not change immediately. Another team needs a point-in-time copy before a migration, but the cluster has no snapshot CRDs. Later, a cleanup removes a claim whose PV has a Delete reclaim policy.

This chapter teaches safe storage lifecycle management with measurable checkpoints, supported-driver checks, backup awareness and recovery validation.

### Learning outcomes

1. Explain capacity request, PV capacity and filesystem free space.
2. Identify expansion prerequisites and controller/node filesystem resize stages.
3. Perform safe PVC growth and verify application-visible capacity.
4. Understand VolumeSnapshotClass, VolumeSnapshot and VolumeSnapshotContent.
5. Restore a new PVC from a ready snapshot where supported.
6. Distinguish snapshots, backups, clones, and application-consistent recovery.
7. Diagnose stuck expansion, snapshot and deletion operations using seven labs.

## 2. Lifecycle architecture

```text
PVC request -> StorageClass -> CSI provisioner -> PV -> backend volume
     |                                                |
     +-- expansion request --> external-resizer ------+
     |                                                |
     +-- VolumeSnapshot --> snapshot-controller --> CSI snapshotter
     |                                              |
     +-- new PVC (dataSource) <--- snapshot content <-+
     |
     +-- PVC deletion -> PV reclaim policy -> Retain or Delete
```

CSI volume snapshots require the snapshot CRDs and controller, the driver's snapshot capability and appropriate VolumeSnapshotClass. Merely seeing a CSI driver installed is insufficient. Volume expansion requires `allowVolumeExpansion: true`, driver support and a suitable filesystem; PVC requests generally cannot be shrunk.

## 3. Core concepts

| Concept | Purpose | Operational caution |
|---|---|---|
| PVC `requests.storage` | Desired provisioned capacity | Not equal to filesystem free bytes |
| PV `capacity.storage` | Capacity represented by bound PV | May update before filesystem expansion |
| StorageClass `allowVolumeExpansion` | Permits claim expansion | Driver may still impose limitations |
| VolumeSnapshotClass | CSI snapshot driver and deletion policy | Cluster-scoped; snapshot-specific |
| VolumeSnapshot | Namespaced request for a snapshot | Must reach `readyToUse: true` |
| VolumeSnapshotContent | Cluster-scoped snapshot binding | May reference backend snapshot asset |
| PVC `dataSource` | Restore from compatible snapshot | New PVC, not overwrite of existing PVC |
| PV reclaimPolicy | Backend behavior after PVC deletion | Delete may destroy data; Retain requires manual recovery |

A snapshot is not necessarily a backup. Snapshots may share the same account, region, storage backend or failure domain. Crash-consistent snapshots are not automatically application-consistent; coordinate database checkpoints, write quiescing, or backup tooling as required.

## 4. Prerequisites and safe boundaries

All labs target a disposable cluster and may incur cloud storage costs. Use a working CSI StorageClass with expansion support for Labs 1–3. Labs 4–6 additionally require VolumeSnapshot APIs and a compatible snapshot-capable CSI driver.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get storageclass
kubectl get csidrivers
kubectl api-resources | Select-String 'volumesnapshot'
kubectl get volumesnapshotclass
kubectl get volumeattachments
```

If `volumesnapshotclass` is not recognized, snapshot APIs are not installed. Do not apply snapshot manifests until a supported snapshot controller, CRDs and driver sidecars are installed using official version-compatible instructions.

```powershell
kubectl create namespace ch034
$sc = "<replace-with-compatible-storageclass>"
kubectl get storageclass $sc -o yaml
```

Replace `REPLACE_STORAGECLASS` in manifests. Record the CSI provisioner, reclaim policy, expansion support, snapshot class, driver version and deletion cost.

## 5. Lab 1 — Provision a baseline persistent volume

Save `ch034-pvc.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: source-data
  namespace: ch034
spec:
  storageClassName: REPLACE_STORAGECLASS
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
```

Save `ch034-writer.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: writer
  namespace: ch034
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: source-data
```

```powershell
kubectl apply -f .\ch034-pvc.yaml
kubectl apply -f .\ch034-writer.yaml
kubectl -n ch034 wait --for=condition=Ready pod/writer --timeout=300s
kubectl -n ch034 exec writer -- sh -c 'echo snapshot-source-marker > /data/marker.txt'
kubectl -n ch034 exec writer -- cat /data/marker.txt
kubectl -n ch034 exec writer -- df -h /data
kubectl -n ch034 get pvc source-data -o wide
```

**Expected:** PVC Bound, Pod Ready and marker file present. On `WaitForFirstConsumer`, binding may wait until writer schedules. Confirm the PV uses `spec.csi` before describing the test as CSI-backed.

## 6. Lab 2 — Expand PVC safely

Verify the selected StorageClass has `allowVolumeExpansion: true` and the driver supports expansion. Record current PVC requested size, PV capacity and `df -h` before proceeding.

```powershell
kubectl get storageclass $sc -o jsonpath='{.allowVolumeExpansion}'
kubectl -n ch034 get pvc source-data -o yaml
kubectl -n ch034 exec writer -- df -h /data
```

Only if supported:

```powershell
kubectl -n ch034 patch pvc source-data --type=merge -p '{"spec":{"resources":{"requests":{"storage":"2Gi"}}}}'
kubectl -n ch034 get pvc source-data -w
```

Stop watch with Ctrl+C, then:

```powershell
kubectl -n ch034 describe pvc source-data
kubectl -n ch034 exec writer -- df -h /data
kubectl -n ch034 get events --sort-by=.lastTimestamp
```

**Expected:** PVC request increases and eventually the PV/filesystem capacity reflects growth, subject to driver/filesystem semantics. Some implementations require Pod restart or remount to complete filesystem expansion. A successful API patch is not proof of expanded filesystem capacity. **Shrinking the PVC back to 1Gi is not a supported rollback.**

## 7. Lab 3 — Diagnose incomplete expansion

Inspect conditions and capacity:

```powershell
kubectl -n ch034 get pvc source-data -o jsonpath='{.spec.resources.requests.storage}'
kubectl -n ch034 get pvc source-data -o jsonpath='{.status.capacity.storage}'
kubectl -n ch034 describe pvc source-data
kubectl -n ch034 describe pod writer
kubectl -n ch034 get events --sort-by=.lastTimestamp
kubectl get volumeattachments
```

Troubleshooting order:
1. Check whether StorageClass expansion is enabled.
2. Confirm CSI controller/external-resizer support and health.
3. Inspect storage quota and backend volume resize status.
4. Determine whether filesystem expansion is pending node-side action.
5. Confirm Pod/node remount requirements from the driver's documentation.
6. Validate application-visible free space, not only API capacity.

Do not delete and recreate a production PVC to fix a resize condition. Some recovery paths require correcting an invalid requested size according to the Kubernetes recovery procedure; do not assume a generic rollback is available.

## 8. Lab 4 — Inspect snapshot API and create a snapshot

Run only when the cluster has snapshot CRDs/controller and the CSI driver supports snapshots.

```powershell
kubectl api-resources | Select-String 'volumesnapshot'
kubectl get volumesnapshotclass -o wide
kubectl get storageclass $sc -o jsonpath='{.provisioner}'
```

Select a `VolumeSnapshotClass` whose `driver` matches the PV's CSI driver. Save `ch034-snapshot.yaml` and replace `REPLACE_SNAPSHOTCLASS`:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: source-snapshot
  namespace: ch034
spec:
  volumeSnapshotClassName: REPLACE_SNAPSHOTCLASS
  source:
    persistentVolumeClaimName: source-data
```

For this simple BusyBox lab, the marker file is stable before snapshot creation. For a real database, perform application-consistent quiescing or use database-native backup coordination.

```powershell
kubectl apply -f .\ch034-snapshot.yaml
kubectl -n ch034 get volumesnapshot source-snapshot -w
kubectl -n ch034 describe volumesnapshot source-snapshot
```

**Expected:** `readyToUse: true` after successful snapshot creation. If unsupported, record an explicit skip. Do not claim a snapshot succeeded just because the object was accepted.

## 9. Lab 5 — Restore into a separate PVC

Only after the snapshot is ready. Save `ch034-restore.yaml`, replacing the StorageClass:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restored-data
  namespace: ch034
spec:
  storageClassName: REPLACE_STORAGECLASS
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 2Gi
  dataSource:
    name: source-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
---
apiVersion: v1
kind: Pod
metadata:
  name: restore-reader
  namespace: ch034
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: restored-data
```

```powershell
kubectl apply -f .\ch034-restore.yaml
kubectl -n ch034 wait --for=condition=Ready pod/restore-reader --timeout=300s
kubectl -n ch034 exec restore-reader -- cat /data/marker.txt
kubectl -n ch034 get pvc restored-data
```

**Expected:** restored PVC Bound and marker file present. Requested restored size must be at least the snapshot's restore size and meet driver requirements. This lab restores to a **new** PVC; it does not overwrite the source.

## 10. Lab 6 — Snapshot failure and deletion policy analysis

Read-only checks:

```powershell
kubectl -n ch034 describe volumesnapshot source-snapshot
kubectl -n ch034 get volumesnapshot source-snapshot -o yaml
kubectl get volumesnapshotcontents
kubectl get volumesnapshotclass -o yaml
kubectl -n ch034 get events --sort-by=.lastTimestamp
```

If snapshot creation is stuck:
- Confirm snapshot controller and CRDs are installed and version compatible.
- Confirm the CSI driver and external-snapshotter support snapshots.
- Verify VolumeSnapshotClass driver matches the PV driver.
- Inspect snapshot controller/driver logs and backend permissions/quota.
- Check `status.error` and `readyToUse` fields.
- Avoid deleting a potentially needed snapshot before verifying retention and backup policy.

A VolumeSnapshotClass `deletionPolicy` of `Delete` may delete the backend snapshot when the snapshot content is deleted; `Retain` preserves the backend snapshot for manual management. This is distinct from PV reclaimPolicy.

## 11. Lab 7 — Storage lifecycle acceptance and incident exercise

Simulate the following review: a database's disk is full, expansion was requested, a snapshot is needed before a risky migration, and an operator proposes deleting the PVC.

Collect evidence:

```powershell
kubectl -n ch034 get pod,pvc -o wide
kubectl get pv,storageclass
kubectl -n ch034 describe pvc source-data
kubectl -n ch034 exec writer -- df -h /data
kubectl -n ch034 get events --sort-by=.lastTimestamp
kubectl get volumeattachments
kubectl get volumesnapshotclass
kubectl -n ch034 get volumesnapshot
```

If snapshot APIs are absent, the last commands may fail; document the missing prerequisite and the alternative backup strategy.

### Acceptance evidence

| Check | Expected result |
|---|---|
| Source volume | Bound, writable, marker present |
| Expansion capability | Confirmed or documented unsupported |
| Expanded capacity | API and filesystem checked separately |
| Snapshot API | Controller/CRDs/driver verified or skipped |
| Snapshot creation | readyToUse true if supported |
| Restore | Separate PVC and marker verified if supported |
| Reclaim policy | Inspected before any deletion |
| Recovery plan | No destructive shortcut; RPO/RTO and backup considered |

## 12. Production troubleshooting runbook

1. **Assess risk:** application writes, disk utilization, database health, I/O errors, available backups and recovery objectives.
2. **Identify resources:** namespace, PVC, PV, StorageClass, CSI driver, node, zone, backend volume ID.
3. **Check lifecycle state:** PVC conditions, PV reclaimPolicy, VolumeAttachment, VolumeSnapshot status.
4. **Validate capacity:** PVC request, PV capacity, filesystem capacity, inode availability and backend quotas.
5. **Inspect CSI:** controller/node logs, resizer, snapshotter and cloud API errors.
6. **Recover safely:** use supported resize/remount/restore procedures; protect the existing source until validation.
7. **Verify:** application reads/writes, restored data integrity, latency, free space and snapshot retention.
8. **Document:** incident timeline, evidence, corrective action, change approvals and prevention.

## 13. Production best practices

- Alert on both percentage and absolute free bytes/inodes, using workload-specific thresholds.
- Forecast volume growth and resize before capacity exhaustion.
- Keep filesystem, CSI driver, Kubernetes version and expansion support documented.
- Require verified backups and restore drills; snapshots alone are not a complete DR strategy.
- Use database-native consistency mechanisms for transactional snapshots.
- Test snapshot restore to a separate PVC and validate application data.
- Define retention, deletion approvals and ownership for PVs and snapshots.
- Protect critical volumes against accidental deletion with governance and change review.
- Monitor CSI resizer and snapshot controller failures, cloud quotas, API throttling and storage costs.
- Plan cross-zone/cross-region recovery separately from in-place snapshots.

## 14. Cleanup

**Disposable cluster only.** Check PV reclaim policies and snapshot deletion policies first; deletion may destroy backend data or incur retained-snapshot costs.

```powershell
kubectl -n ch034 get pvc
kubectl get pv
kubectl get volumesnapshotclass
kubectl -n ch034 get volumesnapshot
kubectl -n ch034 delete pod writer restore-reader --ignore-not-found
```

If lab data and snapshots are confirmed disposable, remove the snapshot and claims in the provider-recommended order, verify backend cleanup, then remove namespace:

```powershell
kubectl -n ch034 delete volumesnapshot source-snapshot --ignore-not-found
kubectl -n ch034 delete pvc restored-data source-data --ignore-not-found
kubectl delete namespace ch034
```

Skip snapshot commands if the snapshot API is not installed. Do not delete cluster-scoped shared StorageClasses or CSI components.

## 15. Acceptance checklist

- [ ] StorageClass expansion capability verified.
- [ ] Baseline PVC and filesystem capacity recorded.
- [ ] PVC growth executed or documented unsupported.
- [ ] Expanded filesystem capacity independently checked.
- [ ] Snapshot CRDs/controller/CSI support verified.
- [ ] Snapshot readiness verified or documented skipped.
- [ ] Separate PVC restored and data checked or documented skipped.
- [ ] PV reclaim and snapshot deletion policies reviewed.
- [ ] Incident runbook and backup/restore strategy documented.
- [ ] Labs executed and reviewed before status changes to Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 16. References

- [Kubernetes Persistent Volumes — Expanding Claims](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#expanding-persistent-volumes-claims)
- [Kubernetes Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [Kubernetes StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [CSI Specification](https://github.com/container-storage-interface/spec)

**Next:** Chapter 035 — Storage Failure and Recovery Lab (Part 07 capstone).
