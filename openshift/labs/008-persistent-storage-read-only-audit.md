# Lab 008 — Read-only PV/PVC, StorageClass and CSI Audit

**Environment:** Authorized OCP 4.x cluster. **Duration:** 25–30 minutes. **Risk:** Read-only. **Status:** Not executed.

## Prerequisites

An approved namespace, `oc` access, and permission to inspect its PVCs and pods. Cluster-level PV, StorageClass and CSI permissions are optional; record denied results rather than expanding privileges.

## Steps

1. Verify context: `oc whoami`, `oc config current-context`, `oc whoami --show-server`.
2. Confirm namespace permission: `oc auth can-i list pvc -n <namespace>`.
3. Inventory claims: `oc get pvc -n <namespace> -o wide`.
4. If permitted, inspect `oc get sc`, `oc get pv`, `oc get csidriver`.
5. For one authorized claim, run `oc describe pvc <claim-name> -n <namespace>`. Record status, storage request, access mode, StorageClass, volume name and events.
6. If bound and permitted, `oc describe pv <pv-name>`. Record capacity, reclaim policy, node affinity and CSI driver without exposing sensitive backend details.
7. Inspect consumers: `oc get pods -n <namespace> -o wide` and `oc describe pod <pod-name> -n <namespace>` if relevant.
8. Explain whether Pending is expected for a WaitForFirstConsumer class, and identify escalation if attach/mount failures appear.

## Expected observations (illustrative, not actual output)

- A PVC may be `Bound` while its consumer pod is unable to mount it.
- A StorageClass with `WaitForFirstConsumer` may legitimately defer binding.
- A tenant user may receive `Forbidden` when listing cluster-scoped PVs or CSI drivers.
- Snapshot resources may be unavailable if the snapshot CRDs are not installed.

## Evidence worksheet

| Evidence | Actual result |
| --- | --- |
| Timestamp and sanitized cluster ID | Not executed |
| OCP server and CLI versions | Not executed |
| Context / namespace verified | Not executed |
| PVC status and access mode | Not executed |
| StorageClass provisioner / binding mode | Not executed |
| PV reclaim policy (if authorized) | Not executed |
| CSI driver and attachment status (if applicable) | Not executed |
| Workload and incident impact | Not executed |
| RBAC / missing API limitations | Not executed |
| Reviewer | Pending |

## Safety and acceptance

No PVC/PV creation, deletion, patching, forced detach, pod restart, node drain or resize is permitted in this lab. Do not include secret values or storage credentials in evidence. Completion requires actual sanitized observations and a reviewer; a written procedure is not a passed lab.
