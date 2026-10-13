# Chapter 033 — Dynamic Provisioning and Volume Access Modes

**Track:** Kubernetes Administration · **Part 07 — Kubernetes Storage**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 031–032; kubectl, Windows PowerShell; isolated Kubernetes cluster with a functional StorageClass and a CSI driver for RWOP exercises

## 1. Production scenario

A PostgreSQL Pod uses a dynamically provisioned block disk. During a rollout, an additional Pod tries to mount the same PVC. An engineer assumes ReadWriteOnce (RWO) means only one Pod can write, but two Pods scheduled on the same node may both mount the volume. A separate RWX claim stays Pending because the selected driver does not support shared writable mounts.

The administrator must choose the right access mode, identify actual driver capabilities, prevent simultaneous database writers, and troubleshoot binding and attachment safely.

### Learning objectives

1. Trace dynamic provisioning from PVC through StorageClass to PV and backend.
2. Distinguish RWO, ROX, RWX and RWOP.
3. Understand access modes as volume capabilities, not user-level file permissions.
4. Verify binding, access-mode compatibility and topology.
5. Explain Filesystem versus Block volumeMode.
6. Diagnose multi-attach, unsatisfied PVC and shared-volume failures.
7. Complete seven labs and produce production acceptance evidence.

## 2. Dynamic provisioning architecture

```text
Pod --> PVC (namespace)
           |
           v
      StorageClass (cluster)
           |
           v
    CSI provisioner --> backend storage volume
           |
           v
       PV (cluster)
           |
           v
   scheduler / attach / mount --> Pod filesystem or block device
```

A PVC requests storage size, access modes, volumeMode and a StorageClass. The provisioner creates a suitable PV. The scheduler accounts for binding mode and topology. Kubelet and CSI node components handle staging and publishing. A `Bound` PVC does not guarantee a healthy attachment or filesystem.

## 3. Access modes and guarantees

| Mode | Meaning | Common fit | Caveat |
|---|---|---|---|
| ReadWriteOnce (RWO) | Read/write mount by a single node | Single-node-attached block disk | Multiple Pods on that node may mount it |
| ReadOnlyMany (ROX) | Read-only mount by many nodes | Shared reference data | Driver must support |
| ReadWriteMany (RWX) | Read/write mount by many nodes | Shared filesystems | Application must handle concurrent writes |
| ReadWriteOncePod (RWOP) | Read/write use by one Pod cluster-wide | Single-writer CSI workload | Requires CSI support and compatible sidecars |

RWOP is supported for CSI volumes, with sufficiently recent Kubernetes and CSI sidecars; check driver compatibility and cluster version. **None of these modes provides application-level transaction fencing, distributed locks, or a database consistency guarantee.**

`volumeMounts.readOnly: true` controls a container mount and is distinct from the PV/PVC access mode. Read-only mounts do not make the underlying storage immutable.

## 4. Lab setup and safety

Use a disposable cluster and identify a working StorageClass. Do not assume kind's default local provisioner is CSI or supports RWX/RWOP.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get storageclass
kubectl get csidrivers
kubectl get csinodes
kubectl get volumeattachments
kubectl create namespace ch033
$sc = "<replace-with-working-storageclass>"
kubectl get storageclass $sc -o yaml
```

Replace `REPLACE_STORAGECLASS` in all manifests with a real class. Record driver, access modes, topology, binding mode, reclaim policy, cost and cleanup approval. Labs requiring unsupported features must be **skipped with evidence**, not falsely marked passed.

## 5. Lab 1 — Dynamically provision an RWO PVC

Save as `ch033-rwo-pvc.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rwo-data
  namespace: ch033
spec:
  storageClassName: REPLACE_STORAGECLASS
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
```

```powershell
kubectl apply -f .\ch033-rwo-pvc.yaml
kubectl -n ch033 get pvc rwo-data
kubectl -n ch033 describe pvc rwo-data
```

**Expected:** `Bound` for Immediate provisioning; `Pending` can be normal for `WaitForFirstConsumer` until a Pod is scheduled. Inspect events and StorageClass binding mode before diagnosing failure.

## 6. Lab 2 — First consumer and persistence

Save `ch033-writer.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: writer
  namespace: ch033
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
        claimName: rwo-data
```

```powershell
kubectl apply -f .\ch033-writer.yaml
kubectl -n ch033 wait --for=condition=Ready pod/writer --timeout=300s
kubectl -n ch033 exec writer -- sh -c 'echo persistent-033 > /data/marker.txt'
kubectl -n ch033 exec writer -- cat /data/marker.txt
kubectl -n ch033 get pod writer -o wide
kubectl -n ch033 get pvc rwo-data -o wide
```

Now delete and recreate the Pod, not the PVC:

```powershell
kubectl -n ch033 delete pod writer
kubectl apply -f .\ch033-writer.yaml
kubectl -n ch033 wait --for=condition=Ready pod/writer --timeout=300s
kubectl -n ch033 exec writer -- cat /data/marker.txt
```

**Expected:** same file persists. This does not prove replication, backup, zone failover or database consistency.

## 7. Lab 3 — RWO versus single-Pod exclusivity

RWO is a **single-node** restriction. On a single-node lab, another Pod may mount the same RWO claim concurrently. Do not run this exercise with a real database or production data.

Save `ch033-second-reader.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: second-reader
  namespace: ch033
spec:
  nodeName: REPLACE_NODE_NAME
  containers:
    - name: reader
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
      volumeMounts:
        - name: data
          mountPath: /data
          readOnly: true
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: rwo-data
        readOnly: true
```

Use the node on which `writer` is running, and replace `REPLACE_NODE_NAME` in the manifest. This explicit node assignment is for an **already bound** lab volume only; it is not appropriate for WaitForFirstConsumer provisioning.

```powershell
kubectl -n ch033 get pod writer -o wide
kubectl apply -f .\ch033-second-reader.yaml
kubectl -n ch033 get pod second-reader -o wide
kubectl -n ch033 describe pod second-reader
kubectl -n ch033 exec second-reader -- cat /data/marker.txt
```

**Expected if the driver permits the shared same-node mount:** second-reader reads the marker while writer is still running. Some drivers or security controls may disallow this; record the observed behavior. **Do not infer that RWO protects against concurrent writers.**

```powershell
kubectl -n ch033 delete pod second-reader
```

## 8. Lab 4 — ReadWriteOncePod (RWOP)

This lab requires a CSI driver that explicitly supports RWOP and compatible sidecars. It uses a **separate** claim; do not try to mutate the existing bound RWO claim's access modes.

Save `ch033-rwop.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rwop-data
  namespace: ch033
spec:
  storageClassName: REPLACE_STORAGECLASS
  accessModes: [ReadWriteOncePod]
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: rwop-owner
  namespace: ch033
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
        claimName: rwop-data
```

```powershell
kubectl apply -f .\ch033-rwop.yaml
kubectl -n ch033 get pod,pvc
kubectl -n ch033 describe pvc rwop-data
```

After owner is Ready, create a second Pod with a different name that references `rwop-data` and observe scheduler/volume events. **Expected on a correctly supported RWOP driver:** a second Pod cannot concurrently use the same claim. Delete the second Pod before cleanup. If provisioning fails due to unsupported access mode, record a skipped/unsupported lab, not a successful exclusivity test.

## 9. Lab 5 — RWX and ROX capability assessment

Shared access requires a driver and backend that support the requested mode. **Do not assume block-disk CSI drivers support RWX or ROX.**

Save `ch033-rwx.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-data
  namespace: ch033
spec:
  storageClassName: REPLACE_STORAGECLASS
  accessModes: [ReadWriteMany]
  resources:
    requests:
      storage: 1Gi
```

Apply only if the selected driver documents RWX support:

```powershell
kubectl apply -f .\ch033-rwx.yaml
kubectl -n ch033 describe pvc shared-data
kubectl -n ch033 get pvc shared-data
```

**Expected with RWX-capable storage:** claim binds (immediately or after consumer scheduling). If unsupported, the claim may stay Pending or provisioning may fail; inspect events and driver docs. Do not repeatedly retry an unsupported request. For ROX, verify driver support and create a **separate** claim with `ReadOnlyMany` when appropriate. Test concurrent mounting only in a dedicated shared-storage lab.

## 10. Lab 6 — Filesystem versus Block volumeMode

`volumeMode: Filesystem` is the default. It provides a mounted filesystem path through `volumeMounts`. `volumeMode: Block` provides a raw block device through `volumeDevices` and is supported only by suitable drivers.

Example raw-block PVC and Pod fragments (**illustrative; do not apply without driver support**):

```yaml
# PVC spec fragment
spec:
  storageClassName: REPLACE_BLOCK_STORAGECLASS
  volumeMode: Block
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
---
# Container and volume spec fragments
# containers:
# - name: app
#   volumeDevices:
#   - name: raw
#     devicePath: /dev/xvdb
# volumes:
# - name: raw
#   persistentVolumeClaim:
#     claimName: raw-block-claim
```

Never format a raw device or run destructive filesystem commands on a shared or production volume. For this chapter, inspect the capabilities and document whether the driver supports raw block mode. A PVC with `volumeMode: Block` cannot bind to an incompatible filesystem PV.

## 11. Lab 7 — Failure injection and recovery acceptance

Create an intentionally incompatible static claim to demonstrate matching constraints without allocating backend storage:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: impossible
  namespace: ch033
spec:
  storageClassName: ""
  accessModes: [ReadWriteMany]
  resources:
    requests:
      storage: 100Ti
```

Save `ch033-impossible.yaml`.

```powershell
kubectl apply -f .\ch033-impossible.yaml
kubectl -n ch033 get pvc impossible
kubectl -n ch033 describe pvc impossible
kubectl -n ch033 get events --sort-by=.lastTimestamp
kubectl get pv,storageclass
kubectl get volumeattachments
```

**Expected:** Pending unless a preexisting matching static PV is present (unlikely in an isolated lab). Explain mismatch across size, class, access mode and volumeMode. Remove only the lab claim:

```powershell
kubectl -n ch033 delete pvc impossible
```

### Acceptance matrix

| Check | Required evidence |
|---|---|
| Dynamic provisioning | PVC/PV binding and actual provisioner |
| Pod mount | Read/write marker in filesystem |
| Pod recreation | Marker survives |
| RWO same-node behavior | Actual observed result, not assumption |
| RWOP exclusivity | Supported-driver test or documented skip |
| RWX/ROX | Supported-driver result or documented skip |
| Raw block | Driver capability and safe distinction |
| Incompatible claim | Pending plus event analysis |
| Recovery safety | No force detach or unsafe deletion |

## 12. Production troubleshooting runbook

1. **Scope:** identify namespace, PVC, PV, StorageClass, CSI driver, Pod and node.
2. **Check binding:** `kubectl describe pvc`; inspect events, requested mode, capacity, class, selector and volumeMode.
3. **Check scheduling:** inspect Pod events, zone topology and binding mode.
4. **Check attachment:** inspect VolumeAttachment and CSI controller logs where applicable.
5. **Check mount:** inspect kubelet-facing Pod events, CSI node plugin, filesystem and permissions.
6. **Check concurrent use:** identify all Pods referencing the PVC; check RWOP versus RWO semantics and existing writers.
7. **Recover narrowly:** resolve the actual scheduling, attach or driver issue; do not remove PV protection finalizers or force-detach without fencing.
8. **Validate:** confirm read/write operation, application integrity, and that unauthorized concurrent access remains blocked where required.

### Useful commands

```powershell
kubectl -n ch033 get pvc,pods -o wide
kubectl -n ch033 describe pvc rwo-data
kubectl -n ch033 describe pod writer
kubectl -n ch033 get events --sort-by=.lastTimestamp
kubectl get pv -o wide
kubectl get volumeattachments
kubectl get csidrivers,csinodes
```

## 13. Production design guidance

- Use RWOP when single-Pod volume access is required **and supported**, but also implement application-level fencing for stateful failover.
- Use RWX only for workloads designed for shared filesystem concurrency.
- Do not interpret RWO as a one-writer-per-cluster guarantee.
- Select StorageClass by durability, IOPS, throughput, topology, encryption, cost and restore requirements.
- Prefer `WaitForFirstConsumer` for zonal storage when supported.
- Monitor PVC Pending duration, provisioner failures, attach/mount errors, volume capacity and storage latency.
- Establish reclaim policy, backup, snapshots, restore drills and deletion approval.
- Avoid sharing a database data directory between independently running writers.
- Audit workload controllers for accidental overlapping rollouts that could create concurrent storage users.

## 14. Cleanup

Before deletion, check the dynamically provisioned PV's reclaim policy and cloud resource cost. Delete only disposable lab resources:

```powershell
kubectl -n ch033 get pod,pvc
kubectl -n ch033 delete pod writer rwop-owner --ignore-not-found
kubectl -n ch033 delete pod second-reader --ignore-not-found
kubectl -n ch033 get pvc -o wide
kubectl get pv -o wide
```

Delete PVCs **only after confirming lab data is disposable**; a `Delete` reclaim policy may delete backend storage:

```powershell
kubectl delete namespace ch033
```

Verify the backend volumes have been cleaned up by the provisioner if deletion was intended. Do not uninstall a shared CSI driver or StorageClass.

## 15. Acceptance checklist

- [ ] Dynamic PVC binding verified.
- [ ] Data survives Pod replacement.
- [ ] RWO node-scoped semantics understood.
- [ ] RWOP capability and exclusivity validated or explicitly skipped.
- [ ] RWX/ROX capabilities validated or explicitly skipped.
- [ ] Filesystem versus raw Block behavior explained.
- [ ] Pending PVC failure diagnosed without destructive action.
- [ ] CSI driver and reclaim behavior recorded.
- [ ] Production recovery and monitoring documented.
- [ ] Hands-on execution and independent technical review completed before status becomes Lab Validated.

**Status:** Draft; runtime validation and technical review pending.

## 16. References

- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Kubernetes CSI Volumes](https://kubernetes.io/docs/concepts/storage/volumes/#csi)
- [Kubernetes Volume Modes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#volume-mode)

**Next:** Chapter 034 — Volume Expansion, Snapshots and Storage Lifecycle.
