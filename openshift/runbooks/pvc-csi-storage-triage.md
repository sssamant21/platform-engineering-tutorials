# Runbook — OpenShift PVC, PV and CSI Storage Triage

**Scope:** OCP 4.x, storage provisioning and mount/attachment incidents. **Change class:** Read-only diagnosis; all remediation requires separate approved change. **Status:** Draft, not runtime validated.

## Trigger and impact

PVC Pending, failed dynamic provisioning, mount/attach errors, stalled filesystem expansion, unexpected volume loss or database pod unavailability.

Identify affected namespace, application, PV/PVC, cluster, incident severity, recovery objective, business owner and storage/DBRE on-call.

## Read-only triage

```bash
oc whoami
oc config current-context
oc whoami --show-server
oc get pvc -n <namespace> -o wide
oc describe pvc <claim-name> -n <namespace>
oc get pods -n <namespace> -o wide
oc describe pod <pod-name> -n <namespace>
oc get events -n <namespace> --sort-by=.lastTimestamp
```

If permitted and applicable:

```bash
oc get sc
oc get pv
oc get csidriver
oc get volumeattachments.storage.k8s.io
oc get clusteroperators
```

`VolumeAttachment` is relevant only to attachable CSI volumes; absence alone does not imply a fault. Confirm the StorageClass `volumeBindingMode` before interpreting a Pending PVC. A `Bound` claim is not proof of successful attachment/mount or database health.

## Decision tree

| Observation | Next action |
| --- | --- |
| `Forbidden` | Record missing RBAC, request scoped investigation by authorized owner |
| Pending PVC + WaitForFirstConsumer | Verify consumer pod, scheduler events, topology; do not provision blindly |
| Pending PVC + provisioner failure | Check StorageClass, CSI Operator/driver availability, backend capacity |
| Bound PVC + pod mount failure | Check pod events, node/zone, CSI driver and backend telemetry |
| Multi-attach or stale attachment | Escalate to storage and workload owners; assess fencing and data corruption risk |
| Expansion blocked | Check class support, PVC conditions and filesystem state; do not attempt shrink |
| Data loss or accidental deletion | Preserve evidence; invoke approved application-consistent restore plan |

## Production guardrails

Do not execute `oc delete pvc`, `oc delete pv`, `oc patch pv`, force detach, manual VolumeAttachment deletion, node drain or database restart as an initial response. Those operations can cause irreversible loss or split-brain. Coordinate with platform, storage and DBRE owners. Confirm approved RPO/RTO, quorum, application replication, backend snapshots and independently tested restore. Never rely on a volume snapshot as proof of a consistent database backup.

## Escalation package

Record sanitized context, time window, impacted service, PVC/PV and StorageClass identifiers, event messages, CSI/Operator health, node/zone, known changes, current data protection state, and proposed next step. Exclude kubeconfig, credentials and secret values.

## Recovery and rollback

This runbook makes no changes, so rollback is not applicable. A separate approved remediation plan must define success criteria, data-consistency checks, recovery point, change authority and rollback feasibility before any state-changing command.

## References

- [Red Hat OpenShift 4.22 storage](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/storage/index)
- [Kubernetes persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
