# Chapter 035 — Storage Failure and Recovery Lab

**Track:** Kubernetes Administration · **Part 07 — Kubernetes Storage (final capstone)**  
**Status:** Draft — hands-on execution and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 031–034; Windows PowerShell, kubectl; isolated Kubernetes cluster with a functioning dynamic provisioner; optional CSI snapshot capability

## 1. Production incident scenario

A stateful service becomes unavailable during a maintenance window. Its Pod is Pending, a replacement claim cannot bind, and the team is considering deleting its PVC to recover. Disk capacity is also increasing. The incident commander must recover service without deleting data or allowing two writers to access the same database files.

**Goal:** execute a reproducible storage incident, identify distinct failure domains, preserve a known-good marker, recover safely, and deliver evidence for an SRE acceptance review.

### Learning objectives

1. Establish a known-good dynamically provisioned persistent volume.
2. Verify data survives Pod replacement.
3. Reproduce and diagnose an unsatisfiable PVC.
4. Diagnose mount and attachment symptoms without destructive shortcuts.
5. Reproduce a storage configuration fault and restore service.
6. Assess capacity pressure, expansion, backup and snapshot options.
7. Validate data integrity, reclaim policy and recovery objectives.

## 2. Architecture and fault domains

```text
Client -> Stateful Pod -> PVC -> PV -> CSI driver -> backend disk
               |          |      |        |
           scheduling   binding  attach   provisioner / cloud API
               |                         |
            node/zone                 quota/permissions
               |
             kubelet -> CSI node plugin -> mount -> filesystem
```

Do not confuse:
- **PVC Pending:** no compatible PV or failed/delayed provisioning.
- **Pod Pending:** unschedulable Pod, possibly due to PVC or topology.
- **ContainerCreating:** may indicate attach/mount failure, but inspect events.
- **VolumeAttachment failure:** driver, existing attachment, node fencing, or cloud API.
- **Filesystem full:** application-visible bytes/inodes exhausted, independent of PVC phase.
- **Data unavailable:** not necessarily data lost. Preserve source storage until verified.

## 3. Safety boundaries and prerequisites

**Run only in a disposable cluster and namespace.** A dynamic StorageClass may create billable cloud disks and use a `Delete` reclaim policy. Never run fault injection against an existing production database.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get storageclass
kubectl get csidrivers
kubectl get csinodes
kubectl get volumeattachments
kubectl get pods -A | Select-String 'csi|provisioner'
```

Choose a functioning StorageClass that supports `ReadWriteOnce`. The capstone does **not** require a CSI driver for basic provisioning tests, but CSI-specific attach/mount/snapshot exercises require a real supported CSI driver. For `WaitForFirstConsumer`, PVC may remain Pending until its Pod is scheduled.

```powershell
$ns = "ch035"
$sc = "<replace-with-working-storageclass>"
kubectl create namespace $ns
kubectl get storageclass $sc -o yaml
```

Record provisioner, volumeBindingMode, reclaimPolicy, allowVolumeExpansion, cluster version and available snapshots. Replace `REPLACE_STORAGECLASS` in the manifests.

## 4. Lab 1 — Establish baseline, recovery marker and SLI

Save `ch035-baseline.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
  namespace: ch035
spec:
  storageClassName: REPLACE_STORAGECLASS
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: database-sim
  namespace: ch035
  labels:
    app: database-sim
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
        claimName: data
```

```powershell
kubectl apply -f .\ch035-baseline.yaml
kubectl -n ch035 wait --for=condition=Ready pod/database-sim --timeout=300s
kubectl -n ch035 exec database-sim -- sh -c 'echo ch035-recovery-marker > /data/marker.txt'
kubectl -n ch035 exec database-sim -- sha256sum /data/marker.txt
kubectl -n ch035 exec database-sim -- df -h /data
kubectl -n ch035 get pod,pvc -o wide
kubectl -n ch035 describe pvc data
```

**Expected:** Pod Ready, claim Bound, checksum recorded. Save the checksum in incident notes. A BusyBox marker proves file preservation, **not database transaction consistency**.

Define lab SLI: ability to read the marker through the running Pod. Lab RTO: time from injected failure to successful read after recovery. Lab RPO: zero loss of the marker file.

## 5. Lab 2 — Recreate Pod without losing data

```powershell
kubectl -n ch035 delete pod database-sim
kubectl apply -f .\ch035-baseline.yaml
kubectl -n ch035 wait --for=condition=Ready pod/database-sim --timeout=300s
kubectl -n ch035 exec database-sim -- sha256sum /data/marker.txt
```

**Expected:** checksum matches baseline. On multi-node clusters, rescheduling may expose zone or attach constraints; inspect events if the Pod does not become Ready. Never treat Pod recreation as a backup.

## 6. Lab 3 — Reproduce Pending PVC and isolate provisioning

Save `ch035-broken-claim.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: broken-claim
  namespace: ch035
spec:
  storageClassName: ""
  accessModes: [ReadWriteMany]
  resources:
    requests:
      storage: 100Ti
```

```powershell
kubectl apply -f .\ch035-broken-claim.yaml
kubectl -n ch035 get pvc
kubectl -n ch035 describe pvc broken-claim
kubectl get pv -o wide
kubectl -n ch035 get events --sort-by=.lastTimestamp
```

**Expected:** broken-claim Pending if no matching static PV exists. Explain mismatch in requested size, access mode and explicit no-class selection. The healthy `data` PVC remains unchanged.

```powershell
kubectl -n ch035 delete pvc broken-claim
```

## 7. Lab 4 — Inject a safe application mount configuration failure

This lab simulates an application configured to read the wrong mount path without changing or detaching the storage. Delete only the lab Pod and create an intentionally misconfigured Pod using the **same PVC**.

```powershell
kubectl -n ch035 delete pod database-sim
```

Save `ch035-wrong-mount.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: database-sim
  namespace: ch035
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "test -f /data/marker.txt || { echo missing-expected-file; exit 1; }; sleep 36000"]
      volumeMounts:
        - name: data
          mountPath: /wrong-path
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: data
```

```powershell
kubectl apply -f .\ch035-wrong-mount.yaml
kubectl -n ch035 get pod database-sim
kubectl -n ch035 describe pod database-sim
kubectl -n ch035 logs database-sim --previous
kubectl -n ch035 get events --sort-by=.lastTimestamp
```

**Expected:** container exits with `missing-expected-file` and may enter CrashLoopBackOff. This is **not** a CSI mount failure: the PVC is mounted at `/wrong-path`, while the application expects `/data`. `--previous` may be unavailable until the container has restarted; use ordinary logs if necessary.

**Targeted recovery:**

```powershell
kubectl -n ch035 delete pod database-sim
kubectl apply -f .\ch035-baseline.yaml
kubectl -n ch035 wait --for=condition=Ready pod/database-sim --timeout=300s
kubectl -n ch035 exec database-sim -- sha256sum /data/marker.txt
```

**Expected:** service returns and checksum matches. Do not delete the PVC.

## 8. Lab 5 — Investigate real attach/mount fault domains (read-only)

This lab is an investigation exercise rather than forced failure injection. Not all clusters use attachable CSI volumes.

```powershell
kubectl -n ch035 describe pod database-sim
kubectl -n ch035 describe pvc data
kubectl -n ch035 get events --sort-by=.lastTimestamp
kubectl get pv,storageclass
kubectl get csidrivers,csinodes,volumeattachments
```

Identify the driver and its controller/node Pods:

```powershell
kubectl get pods -A -o wide | Select-String 'csi'
```

If the environment has a CSI controller and node plugin, inspect the relevant logs by substituting real names:

```powershell
kubectl -n <driver-namespace> logs <controller-pod> --all-containers --tail=100
kubectl -n <driver-namespace> logs <node-plugin-pod> --all-containers --tail=100
```

Interpretation:
- `FailedScheduling`: scheduling, claim binding or topology.
- `FailedAttachVolume`: CSI controller/cloud API, attachment quota, existing attachment.
- `FailedMount`: CSI node plugin, filesystem, device, mount permissions or secrets.
- `Multi-Attach`: check all writers, volume attachments and node fencing.
- `CrashLoopBackOff`: inspect application command and logs before blaming CSI.

**Never force-detach an actively written volume, delete VolumeAttachment objects, or remove PVC/PV protection finalizers as a generic recovery step.**

## 9. Lab 6 — Capacity, expansion, snapshot and retention decision

```powershell
kubectl -n ch035 exec database-sim -- df -h /data
kubectl -n ch035 exec database-sim -- df -i /data
kubectl -n ch035 get pvc data -o yaml
kubectl get storageclass $sc -o yaml
kubectl api-resources | Select-String volumesnapshot
kubectl get volumesnapshotclass
```

The last command may report an unknown resource if snapshot APIs are absent; document this as an unsupported capability, not a lab failure.

Decision sequence:
1. Is the application actually low on bytes or inodes? Compare growth and free space.
2. Does the StorageClass allow expansion and does the driver support it?
3. Is there a verified backup, snapshot or application-consistent recovery point?
4. What are PV reclaimPolicy and snapshot deletionPolicy?
5. Can the application tolerate remount/restart if filesystem expansion requires it?
6. What is the rollback plan if capacity changes fail?

**Optional disposable-cluster expansion:** only with verified driver support and cost approval:

```powershell
kubectl -n ch035 patch pvc data --type=merge -p '{"spec":{"resources":{"requests":{"storage":"2Gi"}}}}'
kubectl -n ch035 describe pvc data
kubectl -n ch035 exec database-sim -- df -h /data
```

PVC size reduction is generally unsupported; skip if the driver does not support expansion. Snapshot/restore exercises from Chapter 034 may be reused here only if snapshot controller, CRDs, driver and VolumeSnapshotClass are verified. Do not claim snapshots are backups or application-consistent by default.

## 10. Lab 7 — Full incident acceptance and recovery report

Simulate an incident ticket:

> Stateful service unavailable after a storage configuration change; PVC is healthy but Pod repeatedly restarts. Another claim is Pending. A responder proposes deleting all PVCs.

### Required investigation

```powershell
kubectl -n ch035 get pod,pvc -o wide
kubectl -n ch035 describe pod database-sim
kubectl -n ch035 describe pvc data
kubectl -n ch035 get events --sort-by=.lastTimestamp
kubectl get pv,storageclass
kubectl get volumeattachments
kubectl -n ch035 exec database-sim -- sha256sum /data/marker.txt
```

If Pod is unavailable during an injected fault, defer the checksum command until recovery; do not misinterpret an exec failure as data loss.

### Acceptance matrix

| Check | Evidence required |
|---|---|
| Healthy baseline | Bound PVC, Ready Pod, checksum recorded |
| Pod replacement | Same marker checksum |
| Broken PVC | Pending claim explained by matching constraints |
| Mount-path fault | Application error identified without blaming CSI |
| Recovery | Corrected Pod configuration, unchanged PVC |
| CSI fault domains | Scheduling, attach, mount and application distinguished |
| Capacity review | Bytes/inodes, expansion support and backend limits |
| Data protection | Reclaim policy, backups/snapshots and fencing reviewed |
| Final integrity | Original marker checksum preserved |
| Cleanup | No unintended backend deletion |

Record **RTO** as observed recovery duration and **RPO** as actual marker data loss (expected zero). Do not invent measurements.

## 11. Production incident runbook

1. **Declare impact:** affected workload, namespace, cluster, customers, read/write symptoms, first error and recovery objectives.
2. **Freeze risky changes:** pause automated rollouts or cleanup only through approved procedures; protect backup and volume assets.
3. **Map storage chain:** Pod → PVC → PV → StorageClass → CSI → backend volume; capture resource UIDs and timestamps.
4. **Classify failure:** provisioning, scheduling, attachment, mounting, filesystem, permission or application configuration.
5. **Preserve data:** inspect reclaim policy and backup/snapshot status; identify existing writer and node fencing state.
6. **Choose narrow fix:** correct wrong mount path, provisioner permissions, quota or topology; use supported detach/resize steps only when justified.
7. **Validate:** application readiness, file/database integrity, latency, capacity, expected read/write path and no concurrent writer.
8. **Close:** record timeline, cause, contributing factors, corrective actions, prevention, RTO/RPO and owner.

### Escalation checklist

- **CSI/controller:** provisioner errors, attach failures, cloud API/IAM/quota.
- **Node team:** kubelet mount failures, filesystem health, node connectivity.
- **DBRE:** database recovery, consistency, replication and WAL/redo status.
- **Security/cloud:** encryption keys, IAM, backend deletion and audit events.
- **Incident commander:** rollback approval, customer communication and data-loss risk.

## 12. Preventive controls and observability

- Alert on PVC Pending age, failed attach/mount events and CSI controller/node availability.
- Monitor disk bytes, inode usage, storage latency, IOPS, throughput and backend errors.
- Use workload-specific free-space thresholds and growth forecasts.
- Review StorageClass reclaim policies and expansion behavior before adoption.
- Use GitOps/admission controls for storage configuration changes and critical claim deletion.
- Maintain backups with restore drills; snapshots alone are insufficient for cross-region DR.
- Define single-writer fencing for database failover; RWO alone is not exclusive to one Pod.
- Include volume topology, driver versions, cloud limits and quota in runbooks.
- Track storage incident SLI/SLO, RTO/RPO and change failure rate.

## 13. Cleanup

**Only after confirming lab data is disposable** and checking PV reclaim policy:

```powershell
kubectl -n ch035 get pod,pvc
kubectl -n ch035 get pvc data -o jsonpath='{.spec.volumeName}'
kubectl get pv -o wide
kubectl -n ch035 delete pod database-sim --ignore-not-found
```

If the associated PV uses `Delete`, deleting the PVC may delete its backend disk. Once explicitly approved for the disposable lab:

```powershell
kubectl delete namespace ch035
```

Verify whether the provisioner deleted the backing volume as intended. Do not delete shared CSI controllers, StorageClasses or unrelated PVs.

## 14. Part 07 acceptance checklist

- [ ] Chapter 031 PV/PVC and volume lifecycle fundamentals demonstrated.
- [ ] Chapter 032 StorageClass and CSI component roles explained.
- [ ] Chapter 033 access-mode and concurrent-writer limitations understood.
- [ ] Chapter 034 expansion, snapshots and reclaim safeguards evaluated.
- [ ] Capstone baseline and recovery checksum recorded.
- [ ] Pending PVC fault diagnosed.
- [ ] Application mount-path failure reproduced and recovered.
- [ ] CSI attach/mount fault domains investigated safely.
- [ ] Capacity, backup, snapshot and data-loss risks reviewed.
- [ ] Incident report includes observed RTO/RPO and corrective actions.
- [ ] All lab resources cleaned up without unintended deletion.
- [ ] Runtime validation and independent technical review completed before marking Part 07 complete.

**Part 07 writing milestone:** Chapters 031–035 drafted. **Lab validation and technical review remain pending.**

## 15. References

- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Kubernetes Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [Kubernetes Volumes](https://kubernetes.io/docs/concepts/storage/volumes/)

**Next:** Chapter 036 — ConfigMaps and Secrets (Part 08 — Configuration Management).
