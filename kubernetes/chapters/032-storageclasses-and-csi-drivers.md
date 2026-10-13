# Chapter 032 — StorageClasses and CSI Drivers

**Track:** Kubernetes Administration · **Part 07 — Kubernetes Storage**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapter 031, kubectl, PowerShell, disposable Kubernetes cluster with an installed CSI provisioner for dynamic provisioning labs

## 1. Production scenario

A database StatefulSet remains Pending because its PVC cannot be provisioned. Another workload binds successfully but stays ContainerCreating due to FailedAttachVolume. An administrator must isolate whether the failure is in the StorageClass, external provisioner, cloud API permissions, topology constraints, CSI controller, CSI node plugin, or backend storage.

### Learning objectives

1. Explain StorageClass and CSI architecture.
2. Inspect provisioner, reclaimPolicy, volumeBindingMode, allowVolumeExpansion, mountOptions and parameters.
3. Understand CSI controller versus node responsibilities and sidecars.
4. Provision a PVC dynamically and verify its backing PV.
5. Compare Immediate and WaitForFirstConsumer binding.
6. Diagnose provisioning, attachment, mounting and expansion problems.
7. Complete seven labs, including failure injection, safe rollback and acceptance evidence.

## 2. Architecture

```text
Pod -> PVC -> StorageClass -> external-provisioner -> CSI controller -> storage API
 |      |          |                                       |
 |      +--------> PV <-----------------------------------+
 |                    |
 scheduler -------- topology / binding mode
 |
 kubelet -> CSI node plugin -> mount/stage/publish -> container filesystem
```

A StorageClass is cluster-scoped and defines **how** dynamically requested storage is provisioned. A PVC is namespaced and requests storage. A PV is cluster-scoped and represents the provisioned volume.

CSI separates Kubernetes from storage vendors. Common CSI components include:
- **CSI controller plugin:** creates/deletes volumes and may attach/detach or expand them.
- **CSI node plugin:** stages and publishes volumes to nodes and reports node information.
- **external-provisioner:** watches PVC/PV operations and calls CSI CreateVolume/DeleteVolume.
- **external-attacher:** coordinates ControllerPublishVolume when supported.
- **external-resizer:** handles controller-side expansion when supported.
- **external-snapshotter:** supports snapshot APIs when installed; snapshots are covered later.
- **node-driver-registrar:** registers CSI node plugin with kubelet.

Not every driver implements every capability or uses every sidecar. Inspect actual driver deployments rather than assuming a standard topology.

## 3. StorageClass design

Example only; replace provisioner and parameters with those supported by your CSI driver:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: example-csi
provisioner: example.csi.invalid
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
parameters: {}
```

**Do not apply this example.** `example.csi.invalid` is deliberately nonfunctional.

| Field | Meaning | Production implication |
|---|---|---|
| provisioner | Driver/provisioner identity | Must match installed controller |
| reclaimPolicy | Delete or Retain for new PVs | Controls backend deletion behavior |
| volumeBindingMode | Immediate or WaitForFirstConsumer | Determines when topology is selected |
| allowVolumeExpansion | Enables PVC request increase | Driver/filesystem must support expansion |
| parameters | Driver-specific options | May control performance, encryption, tier |
| mountOptions | Filesystem mount options | Invalid options may cause mount failures |

A default StorageClass is indicated by `storageclass.kubernetes.io/is-default-class: "true"`. Multiple defaults can create ambiguity; review cluster policy. `storageClassName: ""` explicitly requests no class, whereas omitting the field can trigger default-class assignment.

## 4. Lab environment and prerequisites

Use an isolated cluster. Dynamic provisioning requires an installed, working provisioner. A kind cluster does not inherently provide a CSI driver; its default local-path provisioning, when present, is not necessarily CSI. To complete CSI-specific labs, install a compatible **lab-only CSI driver** using its official version-pinned instructions, or use a disposable managed cluster with a supported CSI add-on. Do not treat a non-CSI local-path provisioner as evidence of CSI attachment behavior.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get storageclass -o wide
kubectl get csidrivers
kubectl get csinodes
kubectl get pods -A | Select-String 'csi|provisioner|storage'
```

Record:
- Cluster version, CNI, storage provider and CSI driver version.
- Chosen working StorageClass name.
- Whether the driver supports RWO, expansion, snapshots and topology.
- Whether dynamic volumes have a financial cost or Delete reclaim behavior.

```powershell
$ns = "ch032"
kubectl create namespace $ns
$sc = "<replace-with-working-storageclass>"
kubectl get storageclass $sc -o yaml
```

Replace the placeholder in the next manifests before applying.

## 5. Lab 1 — Inspect CSI and StorageClass capabilities

```powershell
kubectl get storageclass -o yaml
kubectl get csidrivers -o yaml
kubectl get csinodes -o yaml
kubectl get volumeattachments
kubectl get pods -A -o wide | Select-String 'csi'
```

Identify provisioner name, binding mode, reclaim policy, expansion setting, and default class. Inspect actual controller and node plugin names and their namespaces. Do not assume a driver has an external-attacher: some drivers do not require one.

**Expected:** a compatible StorageClass and a healthy provisioner/driver deployment. If absent, stop and install an appropriate driver in the disposable cluster before continuing.

## 6. Lab 2 — Dynamic PVC provisioning

Create `ch032-pvc.yaml` and replace `REPLACE_STORAGECLASS`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-data
  namespace: ch032
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: REPLACE_STORAGECLASS
  resources:
    requests:
      storage: 1Gi
```

```powershell
kubectl apply -f .\ch032-pvc.yaml
kubectl -n ch032 get pvc dynamic-data -w
```

For `Immediate`, the claim should bind when provisioning succeeds. For `WaitForFirstConsumer`, **Pending is expected until a Pod consuming the claim can be scheduled**; stop the watch with Ctrl+C.

```powershell
kubectl -n ch032 describe pvc dynamic-data
kubectl get pv -o wide
```

Record PV name, driver, reclaim policy, requested capacity, and event history.

## 7. Lab 3 — Schedule a consumer and verify mount

Save `ch032-consumer.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: writer
  namespace: ch032
spec:
  containers:
    - name: writer
      image: busybox:1.36
      command: ["sh", "-c", "sleep 36000"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: dynamic-data
```

```powershell
kubectl apply -f .\ch032-consumer.yaml
kubectl -n ch032 wait --for=condition=Ready pod/writer --timeout=300s
kubectl -n ch032 get pvc dynamic-data -o wide
kubectl -n ch032 describe pod writer
kubectl -n ch032 exec writer -- sh -c 'echo csi-lab-data > /data/probe.txt; cat /data/probe.txt'
kubectl -n ch032 exec writer -- df -h /data
```

**Expected:** PVC Bound, Pod Ready and data written. Verify `kubectl get pv <pv-name> -o yaml` shows `spec.csi` for a CSI-backed PV. If the PV uses `hostPath` or another source, this test did not validate CSI.

## 8. Lab 4 — Binding mode and topology

Inspect:

```powershell
kubectl get storageclass $sc -o jsonpath='{.volumeBindingMode}'
kubectl -n ch032 get pod writer -o wide
kubectl -n ch032 get pvc dynamic-data -o jsonpath='{.spec.volumeName}'
kubectl get nodes --show-labels
```

Inspect the resulting PV `nodeAffinity` if present, and compare with the Pod's node and zone. Do not infer zonal constraints for drivers that provide network-accessible or topology-independent storage.

**Exercise:** describe why `WaitForFirstConsumer` is safer for zone-constrained disks and why specifying `nodeName` directly on a Pod can bypass scheduling and prevent expected delayed binding. Use `nodeSelector` when an intentional scheduling constraint is needed.

## 9. Lab 5 — Failure injection: invalid provisioner

Create a deliberately nonfunctional StorageClass and claim **only in the lab**:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ch032-broken
provisioner: ch032.invalid.example
reclaimPolicy: Retain
volumeBindingMode: Immediate
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: broken-data
  namespace: ch032
spec:
  storageClassName: ch032-broken
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
```

Save as `ch032-broken.yaml`.

```powershell
kubectl apply -f .\ch032-broken.yaml
kubectl -n ch032 get pvc broken-data
kubectl -n ch032 describe pvc broken-data
kubectl get storageclass ch032-broken -o yaml
```

**Expected:** claim remains Pending because no provisioner implements `ch032.invalid.example`. Events may vary and may not always explain the absence immediately. Do not wait indefinitely.

```powershell
kubectl -n ch032 delete pvc broken-data
kubectl delete storageclass ch032-broken
```

## 10. Lab 6 — Expansion capability and safety

Check `allowVolumeExpansion` and driver support **before** requesting a resize:

```powershell
kubectl get storageclass $sc -o jsonpath='{.allowVolumeExpansion}'
kubectl -n ch032 get pvc dynamic-data -o yaml
```

Only if the driver and StorageClass support online or offline expansion, and only in the disposable environment:

```powershell
kubectl -n ch032 patch pvc dynamic-data --type=merge -p '{"spec":{"resources":{"requests":{"storage":"2Gi"}}}}'
kubectl -n ch032 get pvc dynamic-data -w
kubectl -n ch032 describe pvc dynamic-data
kubectl -n ch032 exec writer -- df -h /data
```

Expected: requested size increases; status capacity and filesystem size eventually reflect expansion according to driver and filesystem behavior. Some drivers require Pod restart/remount for filesystem resize. **PVC shrinking is not generally supported**; do not treat this as reversible. Skip this lab if unsupported or costly, and record why.

## 11. Lab 7 — CSI incident investigation and recovery acceptance

Simulated incident: PVC Pending or Pod stuck ContainerCreating.

```powershell
kubectl -n ch032 get pod,pvc -o wide
kubectl -n ch032 describe pod writer
kubectl -n ch032 describe pvc dynamic-data
kubectl -n ch032 get events --sort-by=.lastTimestamp
kubectl get pv,storageclass
kubectl get csidrivers,csinodes,volumeattachments
kubectl get pods -A | Select-String 'csi|provisioner'
```

Then inspect the actual driver controller/node logs (substitute discovered namespace and resource):

```powershell
kubectl -n <driver-namespace> get pods -o wide
kubectl -n <driver-namespace> logs <controller-pod> --all-containers --tail=100
kubectl -n <driver-namespace> logs <node-plugin-pod> --all-containers --tail=100
```

Replace placeholders; use read-only inspection first. Distinguish:
1. **Provisioning:** missing provisioner, IAM/identity, cloud quota, storage parameters, API errors.
2. **Scheduling:** delayed binding, node/zone affinity, insufficient node resources.
3. **Attachment:** existing attachment, node fencing, driver attach errors, volume limits.
4. **Mounting:** filesystem errors, permission/security context, missing secrets, node plugin.
5. **Application:** wrong mount path, UID/GID mismatch, data corruption, application locks.

### Recovery guardrails

- Never force-detach a volume while a previous writer might still be active.
- Never delete PVC/PV or remove protection finalizers as an initial troubleshooting step.
- Validate snapshots/backups and reclaim policy before storage cleanup.
- Record exact error, event time, affected node, PV/PVC UID and cloud volume ID.
- Recheck data consistency after recovery; a successful mount is not proof of database consistency.

## 12. Production troubleshooting matrix

| Symptom | Suspect | First evidence |
|---|---|---|
| PVC Pending with Immediate | Provisioner, class, quota, parameters | PVC events, controller logs |
| PVC Pending with WaitForFirstConsumer | No schedulable consumer, topology | Pod events, scheduler, PV affinity |
| FailedAttachVolume | Driver/cloud API, node conflict | VolumeAttachment, controller logs |
| FailedMount | Node plugin, filesystem, permissions | Pod events, node plugin logs |
| Expansion stuck | Resizer, quota, filesystem | PVC conditions, controller/node logs |
| Unexpected volume deletion | Delete reclaim policy, automation | PV spec, audit and cloud logs |
| Bound PVC, app fails | Mount path, app ownership, I/O errors | Pod mount, app logs, node storage metrics |

## 13. Production design and observability

- Choose CSI driver versions compatible with Kubernetes and provider releases.
- Define StorageClasses by workload needs: latency, IOPS, throughput, replication, topology, encryption and cost.
- Prefer `WaitForFirstConsumer` for topology-sensitive storage where supported.
- Choose `Retain` or `Delete` deliberately; record deletion ownership and approval.
- Monitor CSI controller and node plugin availability, provisioning latency, attach/mount failures, expansion failures, PVC capacity and backend I/O saturation.
- Track cloud API throttling, volume attachment limits, storage quota and zone outages.
- Maintain tested backup/restore, fencing, disaster recovery and rollback procedures.
- Treat encryption, key management and storage access permissions as separate controls.
- Do not change an existing StorageClass and assume already provisioned PVs inherit new settings.

## 14. Cleanup

**Disposable cluster only.** First inspect PV reclaim policy and whether any backend volume must be retained:

```powershell
kubectl -n ch032 delete pod writer
kubectl -n ch032 get pvc dynamic-data -o jsonpath='{.spec.volumeName}'
kubectl -n ch032 get pvc dynamic-data -o yaml
```

If the associated PV uses `Delete`, deleting the PVC may delete the backend volume. If the data must be preserved, stop and follow your provider's retention procedure. For disposable lab data only:

```powershell
kubectl -n ch032 delete pvc dynamic-data
kubectl delete namespace ch032
```

Do not uninstall a shared CSI driver or delete cluster-wide StorageClasses during cleanup.

## 15. Acceptance checklist

- [ ] Driver/provisioner identity and version recorded.
- [ ] StorageClass fields and reclaim behavior explained.
- [ ] Dynamic PVC provisioned and verified as CSI-backed.
- [ ] Pod scheduled, mounted and able to write/read data.
- [ ] Binding mode and topology behavior documented.
- [ ] Invalid provisioner failure reproduced and diagnosed.
- [ ] Expansion tested if supported, otherwise explicitly skipped.
- [ ] Provision/attach/mount failure domains distinguished.
- [ ] Data-protection and recovery guardrails documented.
- [ ] Runtime evidence and technical review completed before marking validated.

**Status:** Draft published; runtime validation, driver-specific testing and technical review pending.

## 16. References

- [Kubernetes StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Kubernetes CSI Volumes](https://kubernetes.io/docs/concepts/storage/volumes/#csi)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [CSI specification](https://github.com/container-storage-interface/spec)

**Next:** Chapter 033 — Dynamic Provisioning and Volume Access Modes.
