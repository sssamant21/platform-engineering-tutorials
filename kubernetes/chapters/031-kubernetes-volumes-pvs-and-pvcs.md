# Chapter 031 — Kubernetes Volumes, PersistentVolumes and PersistentVolumeClaims

**Track:** Kubernetes Administration · **Part 07 — Kubernetes Storage**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 001–030; kubectl, Windows PowerShell, Docker Desktop/kind or an isolated Kubernetes lab

## 1. Production scenario

A database Pod is rescheduled after a node disruption. The replacement Pod starts, but its data directory is empty—or it remains `Pending` because the PVC cannot bind. In another incident, a storage cleanup deletes a PVC and unexpectedly triggers backend volume deletion.

An SRE must distinguish ephemeral container filesystems, Pod-scoped volumes, persistent claims, underlying storage assets, scheduling topology, and reclaim behavior before making changes.

### Learning outcomes

1. Explain `emptyDir`, projected/configuration volumes, persistent volumes and claims.
2. Understand the PV/PVC binding and provisioning lifecycle.
3. Inspect StorageClasses, access modes, volumeMode, capacity and reclaim policies.
4. Demonstrate data persistence across Pod recreation with a static PV.
5. Diagnose Pending PVCs, failed mounts and node-local storage limitations.
6. Apply safe deletion and recovery procedures.
7. Complete seven hands-on labs and a storage acceptance checklist.

## 2. Storage architecture

```text
Application container
       |
       v
volumeMount /data
       |
       v
Pod spec.volumes
       |
       +--> emptyDir (Pod lifetime)
       |
       +--> PVC: app-data
                |
                v
         PersistentVolume (PV)
                |
                +--> CSI driver / cloud block or file / NFS / local / hostPath
                              |
                              v
                       physical storage
```

A **PV** represents a cluster storage resource. A **PVC** requests storage and binds to a compatible PV or triggers dynamic provisioning through a StorageClass. The Pod refers to the PVC, not usually to a particular PV. A **StorageClass** defines provisioning behavior and often determines topology, expansion, reclaim policy and binding mode.

**Important:** PVCs are namespaced; PVs and StorageClasses are cluster-scoped. PV capacity is a requested storage size, not proof of application free space or throughput. PVC binding alone does not guarantee a successful mount.

## 3. Core volume types

| Type | Lifetime / purpose | Operational concern |
|---|---|---|
| Container writable layer | Container lifetime | Lost on container recreation |
| `emptyDir` | Pod lifetime, including container restarts | Lost when Pod is removed from its node |
| `configMap`, `secret`, `projected` | Configuration/credentials | Not database persistence; updates have nuances |
| `persistentVolumeClaim` | Independent of Pod lifetime | Depends on PV, driver and reclaim behavior |
| `hostPath` | Specific node filesystem path | Security risk; not portable or production HA |
| `local` PV | Node-local persistent path | Node affinity; node loss can strand data |
| CSI-backed volume | Driver-dependent block/file storage | Attach, mount, zone, IAM and quota failures |

`emptyDir.medium: Memory` uses memory-backed storage and counts toward memory usage. `emptyDir.sizeLimit` is not a durability guarantee.

## 4. PV/PVC lifecycle and semantics

Typical phases:
- PVC: `Pending` → `Bound` → (possibly `Lost`).
- PV: `Available` → `Bound` → `Released` → possible reuse/deletion based on reclaim policy.

**Binding:** Kubernetes matches requested capacity, `storageClassName`, `accessModes`, `volumeMode`, selector and topology constraints. A PV larger than the claim can bind, but the claim does not necessarily consume the entire PV in the way an application might expect.

**Access modes:** `ReadWriteOnce` (RWO) means read/write mounting by a single **node**, not necessarily one Pod. `ReadWriteOncePod` (RWOP), with supported CSI components, is for single-Pod exclusive access. `ReadOnlyMany` (ROX) and `ReadWriteMany` (RWX) depend on the storage driver. Access modes govern binding/mount capabilities; they are not a general-purpose filesystem authorization system.

**Reclaim:** `Delete` may delete the backend storage when a claim is removed; `Retain` preserves the PV and backend for deliberate administrator recovery. Always check the actual PV reclaim policy and provisioner behavior before deleting a PVC.

**Binding mode:** `Immediate` binds/provisions early; `WaitForFirstConsumer` defers binding/provisioning until Pod scheduling context is known, useful for zonal volumes.

## 5. Lab prerequisites

Use a disposable cluster. The static `hostPath` PV below is **lab-only** and works most predictably on a single-node kind cluster. It is not a production storage architecture.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get storageclass
kubectl get pv
kubectl get pvc -A
kubectl get csidrivers
```

Do not proceed against a production context. In a single-node kind cluster, identify the actual node:

```powershell
$node = (kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
$node
```

This chapter uses namespace `ch031`, a dedicated lab PV `ch031-static-pv`, and a lab-only host path `/tmp/ch031-pv-data` inside the kind node.

## 6. Lab 1 — Ephemeral `emptyDir` and container restart

Save `ch031-emptydir.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch031
---
apiVersion: v1
kind: Pod
metadata:
  name: ephemeral
  namespace: ch031
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
      volumeMounts:
        - name: scratch
          mountPath: /scratch
  volumes:
    - name: scratch
      emptyDir: {}
```

```powershell
kubectl apply -f .\ch031-emptydir.yaml
kubectl -n ch031 wait --for=condition=Ready pod/ephemeral --timeout=120s
kubectl -n ch031 exec ephemeral -- sh -c 'echo retained-across-container-restart > /scratch/check.txt'
kubectl -n ch031 exec ephemeral -- cat /scratch/check.txt
```

Expected: file exists. A container restart inside the **same Pod** normally retains `emptyDir`, whereas deleting and recreating the Pod does not. Test Pod deletion only after recording the expected data loss:

```powershell
kubectl -n ch031 delete pod ephemeral
kubectl apply -f .\ch031-emptydir.yaml
kubectl -n ch031 wait --for=condition=Ready pod/ephemeral --timeout=120s
kubectl -n ch031 exec ephemeral -- sh -c 'test ! -e /scratch/check.txt && echo ephemeral-data-gone'
```

Expected: `ephemeral-data-gone`. A recreated Pod receives a new `emptyDir`.

## 7. Lab 2 — Create a static PV and PVC

On a **single-node kind lab cluster only**, save `ch031-static-storage.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: ch031-static-pv
  labels:
    lab: ch031
spec:
  capacity:
    storage: 1Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ""
  hostPath:
    path: /tmp/ch031-pv-data
    type: DirectoryOrCreate
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
  namespace: ch031
spec:
  storageClassName: ""
  selector:
    matchLabels:
      lab: ch031
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

```powershell
kubectl apply -f .\ch031-static-storage.yaml
kubectl get pv ch031-static-pv -o wide
kubectl -n ch031 get pvc data -o wide
kubectl -n ch031 describe pvc data
```

Expected: PV and PVC become `Bound`. Explicit `storageClassName: ""` prevents default StorageClass dynamic provisioning for this static lab. `hostPath` data is node-specific and should not be used for a real database.

## 8. Lab 3 — Mount PVC and prove Pod replacement persistence

Save `ch031-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: storage-writer
  namespace: ch031
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
kubectl apply -f .\ch031-pod.yaml
kubectl -n ch031 wait --for=condition=Ready pod/storage-writer --timeout=120s
kubectl -n ch031 exec storage-writer -- sh -c 'date > /data/persist.txt'
kubectl -n ch031 exec storage-writer -- cat /data/persist.txt
kubectl -n ch031 delete pod storage-writer
kubectl apply -f .\ch031-pod.yaml
kubectl -n ch031 wait --for=condition=Ready pod/storage-writer --timeout=120s
kubectl -n ch031 exec storage-writer -- cat /data/persist.txt
```

Expected: the same file contents remain after Pod recreation on the same kind node. This demonstrates persistence beyond the Pod lifecycle, **not** node-failure durability, replication, or backup.

## 9. Lab 4 — Reproduce a Pending PVC

Save `ch031-pending.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: impossible-claim
  namespace: ch031
spec:
  storageClassName: ""
  accessModes: [ReadWriteMany]
  resources:
    requests:
      storage: 50Gi
```

```powershell
kubectl apply -f .\ch031-pending.yaml
kubectl -n ch031 get pvc impossible-claim
kubectl -n ch031 describe pvc impossible-claim
kubectl get pv -o wide
```

Expected: PVC remains `Pending` because no matching static PV offers the requested size and access mode. Investigate `storageClassName`, capacity, access modes, volumeMode, selectors and events. Remove the intentionally unsatisfiable claim:

```powershell
kubectl -n ch031 delete pvc impossible-claim
```

For dynamic provisioning, also inspect StorageClass provisioner, `WaitForFirstConsumer`, CSI controller logs, cloud quota and permissions.

## 10. Lab 5 — Storage topology, attachment and mount diagnosis

```powershell
kubectl -n ch031 describe pod storage-writer
kubectl -n ch031 describe pvc data
kubectl describe pv ch031-static-pv
kubectl -n ch031 get events --sort-by=.lastTimestamp
kubectl get storageclass -o yaml
kubectl get csinodes
kubectl get volumeattachments
```

The lab `hostPath` volume will not create a CSI `VolumeAttachment`; an empty result is normal. On CSI-backed platforms, diagnose:
- `FailedScheduling`: unbound PVC, zone/node affinity or storage topology mismatch.
- `FailedAttachVolume`: driver/controller, cloud API, attachment quota or volume already attached.
- `FailedMount`: node plugin, filesystem, device, permission or missing Secret.
- `Multi-Attach`: access mode, existing attachment or rescheduling conflict.
- `ContainerCreating`: inspect events; do not assume the image is at fault.

**Safety:** Do not force-detach a volume or remove finalizers before confirming the old node is fenced and no writer remains. Forced detach can cause filesystem corruption.

## 11. Lab 6 — Reclaim policy and deletion safety

Inspect the claim-to-volume mapping:

```powershell
kubectl -n ch031 get pvc data -o jsonpath='{.spec.volumeName}'
kubectl get pv ch031-static-pv -o jsonpath='{.spec.persistentVolumeReclaimPolicy}'
kubectl -n ch031 get pod storage-writer -o wide
```

Expected: claim points to `ch031-static-pv`, reclaim policy is `Retain`. Stop the writer **before** deleting the claim:

```powershell
kubectl -n ch031 delete pod storage-writer
kubectl -n ch031 delete pvc data
kubectl get pv ch031-static-pv
```

Expected: PV becomes `Released` and retains its `claimRef`; it does **not** automatically become available for a new claim. Reusing retained PV data requires a controlled recovery procedure: verify the data and owner, confirm no active writer, clear the old claimRef only when safe, and bind a new PVC deliberately. This chapter does not automate that potentially destructive step.

**Production warning:** With `Delete`, deleting a PVC may delete the underlying cloud volume. Check snapshots, backups, reclaim policy, owner and data-retention requirements before proceeding.

## 12. Lab 7 — Storage incident acceptance exercise

Simulate a report: “The application is Pending and data might be lost.”

Gather evidence in this order:

```powershell
kubectl -n ch031 get pods,pvc -o wide
kubectl get pv,storageclass
kubectl -n ch031 get events --sort-by=.lastTimestamp
kubectl -n ch031 describe pvc data
kubectl describe pv ch031-static-pv
kubectl get csidrivers,csinodes
```

The `data` PVC is intentionally deleted in Lab 6, so `describe pvc data` will return NotFound. Record that as an **expected finding**, not as a failure of the lab. Confirm PV `Released` and reclaim policy `Retain`. Explain why a new PVC will not automatically reclaim the released PV. Produce a recovery plan without modifying or deleting the retained data.

Acceptance evidence:

| Check | Expected |
|---|---|
| Ephemeral volume behavior | Data lost after Pod recreation |
| Static PV/PVC binding | Bound when compatible |
| Pod replacement | Persistent file survives on same node |
| Unsatisfiable PVC | Pending with actionable diagnostics |
| CSI vs hostPath | Correct distinction |
| PV reclaim policy | Retain verified before PVC deletion |
| Released PV | Data preserved; manual recovery required |
| Incident response | No forced detach or unreviewed finalizer removal |

## 13. Production troubleshooting matrix

| Symptom | Likely cause | Verification |
|---|---|---|
| PVC Pending | No matching PV, missing provisioner, quota, topology | PVC events, StorageClass, CSI controller |
| Pod Pending | Unbound PVC or volume node affinity | Pod scheduling events |
| Pod stuck ContainerCreating | Attach/mount issue | Pod events, CSI node logs |
| Multi-Attach error | Volume attached elsewhere | VolumeAttachment, node/pod state |
| Read-only filesystem | Storage or filesystem fault | Kernel/CSI events, volume health |
| Data missing after restart | Wrong mount, emptyDir, new claim or path | Pod spec, PVC/PV UID, mount paths |
| Volume deleted unexpectedly | Delete reclaim policy or cleanup automation | PV history, cloud audit logs |
| Permission denied | UID/GID, fsGroup, root-squash, driver behavior | Pod securityContext, mount permissions |

## 14. Production operating practices

- Use CSI-backed, supported storage drivers and version compatibility matrices.
- Choose storage class by workload IOPS, throughput, latency, topology and recovery requirements.
- Define backup, snapshot, restore testing, RPO and RTO separately from PV persistence.
- Monitor PVC capacity and filesystem usage; capacity requests do not guarantee available free space.
- Track attach/mount latency, CSI controller health, volume errors and disk saturation.
- Treat stateful application consistency carefully: storage snapshots alone may not be application-consistent.
- Document reclaim policy and deletion approval for every critical storage class.
- Prefer `WaitForFirstConsumer` for topology-aware dynamic provisioning where supported.
- Avoid `hostPath` for production database durability or multi-node high availability.
- For database failover, coordinate application fencing and volume attachment before starting a replacement writer.

## 15. Cleanup

Only in the disposable lab. Lab 6 already removed `data` PVC and `storage-writer` Pod.

```powershell
kubectl delete namespace ch031
kubectl get pv ch031-static-pv
```

Because the lab PV uses `Retain`, deleting the PV object does not necessarily delete its host directory. **Only after verifying the cluster is disposable and data is unneeded**:

```powershell
kubectl delete pv ch031-static-pv
# Optional on a disposable kind node only; replace with the verified node name:
$node = (kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
docker exec $node sh -c 'rm -rf /tmp/ch031-pv-data'
```

Never run that host-path removal against a production node or a directory containing other workloads' data.

## 16. Acceptance checklist

- [ ] Explain volume lifetime differences.
- [ ] Create and bind static PV/PVC.
- [ ] Mount PVC and verify persistence after Pod replacement.
- [ ] Diagnose a Pending PVC with events and matching constraints.
- [ ] Identify CSI attachment and mount troubleshooting paths.
- [ ] Verify reclaim policy before any destructive operation.
- [ ] Demonstrate safe handling of a Released PV.
- [ ] Document production monitoring, backups, ownership and rollback.
- [ ] Execute labs and attach evidence before marking Lab Validated.

**Status:** Draft; runtime validation and technical review pending.

## 17. References

- [Kubernetes Volumes](https://kubernetes.io/docs/concepts/storage/volumes/)
- [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [CSI Volumes](https://kubernetes.io/docs/concepts/storage/volumes/#csi)

**Next:** Chapter 032 — StorageClasses and CSI Drivers.
