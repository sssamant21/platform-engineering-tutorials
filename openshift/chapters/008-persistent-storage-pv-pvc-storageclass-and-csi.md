# Chapter 008 — OpenShift Persistent Storage: PV, PVC, StorageClass and CSI

**Audience:** OCP platform administrators, SREs and DBREs · **Duration:** 60 minutes · **Scope:** OpenShift 4.x (reference baseline: Red Hat 4.22) · **Status:** Draft, not runtime validated.

## Learning outcomes

Understand the distinction between PV, PVC, StorageClass and CSI; audit storage provisioning without mutations; diagnose Pending claims, attach/mount errors and stateful workload impact; and design a safe change request.

**Prerequisite:** [Chapter 006](006-projects-pods-deployments-and-workload-lifecycle.md) and [Kubernetes storage fundamentals](../../../kubernetes/chapters/031-kubernetes-volumes-pvs-and-pvcs.md). This chapter focuses on OCP platform administration rather than repeating Kubernetes basics.

## 1. Storage control path

A workload requests storage through a PersistentVolumeClaim (PVC). The StorageClass describes a provisioner and parameters; the CSI driver and backend provision a PersistentVolume (PV) when supported. The PV is cluster-scoped; the PVC is namespaced. Binding is not the same as successful node attachment, mounting, filesystem health or application consistency.

- **PV:** PersistentVolume object representing a storage resource, with capacity, access modes, reclaim policy and claim reference.
- **PVC:** Namespaced request for storage; status typically Pending, Bound or Lost.
- **StorageClass:** Provisioner, reclaim policy, volume binding mode, expansion setting and backend parameters. The default class can differ by cluster and platform.
- **CSI:** Controller/node driver components used to provision, attach and mount volumes. OCP operators may manage platform CSI drivers.
- **VolumeAttachment:** Kubernetes attachment object for attachable CSI volumes; its presence depends on driver capabilities and mode.
- **VolumeSnapshot:** Requires installed snapshot APIs/controller and compatible CSI snapshot support. A snapshot alone is not a complete, application-consistent backup.

Important: `ReadWriteOnce` describes node-level mount eligibility, not an exclusive single-pod guarantee. `ReadWriteOncePod` is a separate mode with driver and Kubernetes compatibility requirements. `ReadWriteMany` is not universally available.

## 2. Access and context verification (read-only)

Never paste a token, password, or kubeconfig into an incident ticket. Replace placeholders with authorized values. The cluster may deny cluster-scoped PV/StorageClass inspection to tenant users; record the RBAC limitation instead of requesting broad privileges.

```bash
oc whoami
oc config current-context
oc whoami --show-server
oc auth can-i list persistentvolumeclaims -n <namespace>
oc auth can-i list persistentvolumes
oc auth can-i list storageclasses.storage.k8s.io
oc auth can-i list csidrivers.storage.k8s.io
```

For PowerShell, the same `oc` commands work; avoid using bash-only shell expansions. Do not change project context during investigation; use explicit `-n <namespace>` for namespaced resources.

## 3. Safe inventory

```bash
oc get pvc -n <namespace> -o wide
oc get pv
oc get storageclass
oc get csidriver
oc get volumesnapshotclass
oc get volumesnapshot -n <namespace>
oc get pods -n <namespace> -o wide
oc get events -n <namespace> --sort-by=.lastTimestamp
```

The snapshot commands may return "the server doesn't have a resource type" when the CRDs are absent; that is a capability discovery result, not proof of storage failure. On a cluster with many resources, narrow the namespace and time range and avoid dumping sensitive object YAML into shared channels.

Inspect a specific PVC and its backing PV:

```bash
oc describe pvc <claim-name> -n <namespace>
oc get pvc <claim-name> -n <namespace> -o jsonpath='{.spec.volumeName}{"\n"}'
oc describe pv <pv-name>
oc describe storageclass <storageclass-name>
```

The PV name may be empty while the claim is Pending. Treat `oc describe pv` as a separate step only after obtaining a real name. On PowerShell, JSONPath quote escaping differs; use `oc get pvc <claim-name> -n <namespace> -o wide` if quoting is problematic.

## 4. Interpret conditions

| Symptom | Plausible causes | First safe check |
| --- | --- | --- |
| PVC Pending | No matching class/capacity, missing provisioner, unsupported access mode, WaitForFirstConsumer with no scheduled consumer | `oc describe pvc`; inspect events and StorageClass binding mode |
| PVC Bound but pod Pending | Scheduling, affinity, quota, topology or other pod constraints | `oc describe pod`; node and topology conditions |
| Pod ContainerCreating with mount error | CSI node plugin, credentials, backend connectivity, volume attachment or filesystem | Pod events; driver/VolumeAttachment diagnostics |
| Multi-attach error | Existing attachment to another node, node fencing/recovery, backend behavior | Pod events and safe attachment inventory; do not force detach |
| PVC expansion not complete | Unsupported expansion, backend resize failure, filesystem resize pending | PVC conditions, StorageClass allowVolumeExpansion, CSI events |
| Data unavailable after recovery | Missing backup consistency, reclaim/delete, backend fault, wrong claim | Stop mutation and engage storage/database owners |

**WaitForFirstConsumer:** `Pending` can be expected until a consumer pod is scheduled; do not treat it as an automatic incident.

## 5. Storage and database reliability

For Kafka, PostgreSQL, MongoDB, Redis and other stateful workloads, distinguish **application replication** from **volume durability** and **recoverable backups**. Confirm RPO/RTO, CSI topology, AZ/zone placement, StorageClass reclaim policy, retention, backup verification and database consistency. A replicated StatefulSet is not by itself a backup.

Before changing a StorageClass, deleting a PVC/PV, expanding storage, moving a pod, draining a node or force-detaching a volume, require a change ticket with owner approvals, current state capture, restore point and tested rollback/recovery plan. PV/PVC deletion and reclaim behavior may be irreversible. Never assume an in-place volume shrink or rollback is supported.

## 6. Guided diagnostic scenario

**Incident:** PostgreSQL pod remains in `ContainerCreating` after a node replacement, and its PVC is `Bound`.

1. Verify cluster identity, namespace, claim name and incident impact.
2. Run `oc get pod -n <namespace> -o wide` and `oc describe pod <pod-name> -n <namespace>`.
3. Run `oc describe pvc <claim-name> -n <namespace>` and inspect the PV's CSI driver, node affinity and access modes.
4. Check `oc get volumeattachments.storage.k8s.io` if RBAC allows and the driver supports attach operations.
5. Correlate recent node changes, zone placement, CSI Operator health and storage-backend alerts.
6. Escalate to platform/storage/DBRE with sanitized evidence; **do not** force detach, delete the PVC, edit PV claim references, or restart the database without a coordinated recovery plan.

## 7. Lab and acceptance

Perform [Lab 008 — Read-only storage audit](../labs/008-persistent-storage-read-only-audit.md) and use the [Storage triage runbook](../runbooks/pvc-csi-storage-triage.md) for incidents.

Pass criteria: identify at least one namespace PVC, distinguish Bound from mounted, record binding mode/reclaim policy, classify one expected versus anomalous Pending condition, and produce an owner/escalation decision. No live execution has been performed for this draft.

## Official references

- [Red Hat OCP 4.22 Storage documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/storage/index)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes CSI volumes](https://kubernetes.io/docs/concepts/storage/volumes/#csi)
