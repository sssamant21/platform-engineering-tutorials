# Lab 017 — Read-only Stateful HA and Storage Audit

**Status:** Draft only. **Time:** 30–40 minutes. **Target:** Authorized non-production or read-only production namespace. No state changes.

## Prerequisites
- `oc` and existing authenticated context; confirm cluster identity with the platform owner.
- Namespace with at least one stateful application; permission to `get/list` pods, StatefulSets, PVCs, PDBs and events. Node/StorageClass access optional; use `oc auth can-i` before cluster-scoped reads.
- Do not capture Secrets, environment variables, connection strings, raw kubeconfig or credentials.

## Procedure
```sh
oc whoami
oc config current-context
oc version
NS=approved-project
oc auth can-i list pods -n "$NS"
oc auth can-i list persistentvolumeclaims -n "$NS"
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
oc get sts,pods,pvc,pdb -n $Ns -o wide
oc get events -n $Ns --sort-by=.lastTimestamp
```
If permitted, separately inspect `oc get nodes -L topology.kubernetes.io/zone` and `oc get sc`. Inspect an individual PDB using `oc describe pdb <approved-name> -n <approved-project>` only if authorized.

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
