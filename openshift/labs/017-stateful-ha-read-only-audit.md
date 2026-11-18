# Lab 017 — Read-only Stateful HA and Storage Audit

**Status:** Draft only. **Time:** 30–40 minutes. **Target:** Authorized non-production or read-only production namespace. No state changes.

## Prerequisites
- `oc` and existing authenticated context; confirm cluster identity with the platform owner.
- Namespace with at least one stateful application; `list` permission for pods, StatefulSets, PVCs, PDBs and events in the approved namespace. `get` permission on an individual named object is separate. Node/StorageClass access is optional and cluster-scoped; check it before querying.
- Do not capture Secrets, environment variables, connection strings, raw kubeconfig or credentials.

## Procedure
```sh
oc whoami
oc config current-context
oc version
NS=approved-project
oc auth can-i list pods -n "$NS"
oc auth can-i list statefulsets.apps -n "$NS"
oc auth can-i list persistentvolumeclaims -n "$NS"
oc auth can-i list poddisruptionbudgets.policy -n "$NS"
oc auth can-i list events -n "$NS"
# Run each collection query only after its corresponding permission returns yes.
oc get sts,pods,pvc,pdb -n "$NS" -o wide
oc get events -n "$NS" --sort-by=.lastTimestamp
oc auth can-i list nodes
oc auth can-i list storageclasses.storage.k8s.io
```
PowerShell:
```powershell
$Ns = "approved-project"
oc whoami
oc config current-context
oc auth can-i list pods -n $Ns
oc auth can-i list statefulsets.apps -n $Ns
oc auth can-i list persistentvolumeclaims -n $Ns
oc auth can-i list poddisruptionbudgets.policy -n $Ns
oc auth can-i list events -n $Ns
# Only run each read when its corresponding check returns yes.
oc get sts,pods,pvc,pdb -n $Ns -o wide
oc get events -n $Ns --sort-by=.lastTimestamp
```
If `oc auth can-i list nodes` and `oc auth can-i list storageclasses.storage.k8s.io` each return `yes`, separately inspect `oc get nodes -L topology.kubernetes.io/zone` and `oc get sc` respectively. For an individual PDB, check `oc auth can-i get poddisruptionbudgets.policy -n <approved-project>` before `oc describe pdb <approved-name> -n <approved-project>`. A `no` response means skip that query; do not request elevated access merely to complete the lab. A combined `oc get` command can partially fail if one resource lacks `list` permission; use individually authorized queries instead.

## Expected versus error conditions
- Expected: pod/node placement and PVC binding can be inventoried; PDB output shows allowed disruptions when PDBs exist.
- `Forbidden`: stop at scope boundary; request minimal read permission from platform security.
- `No resources found`: confirm namespace/workload type; absence of PDB is a finding, not permission to create one.
- `Pending`, `FailedAttachVolume`, `Multi-Attach`, `NotReady`: record event and owner; do not force detach, drain or delete.
- `ALLOWED DISRUPTIONS=0`: voluntary eviction may be blocked; do not weaken PDB to proceed.
- Database replica status and recovery readiness cannot be proven by these `oc` commands; obtain sanitized, database-native evidence from the owner.

## Evidence worksheet
Record date/time UTC, exact OCP version, sanitized context and namespace, command, expected and observed result, workload/Operator owner, PV topology notes, PDB interpretation, database-level quorum/lag verification source, risks, reviewer and approval status. **No runtime evidence has been collected by this repository author.**

## Pass criteria
A reviewer can trace infrastructure health, placement and storage risks to the right owner without disruptive changes. Lab remains **Not run** until actual authorized outputs and review are recorded.
