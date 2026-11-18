# Runbook — Stateful Workload HA, Quorum and Storage Triage

**Draft — not production-certified.** Applies to OCP 4.22 baseline after verifying the deployed minor version. Incident commander and database/application owners must authorize any state-changing recovery.

## Trigger and first response
Symptoms: database pod NotReady, stuck PVC, multi-attach, node loss, reduced Kafka ISR, PostgreSQL replication lag, MongoDB majority loss or Redis failover alarms. Establish incident severity, affected applications, change freeze and ownership. Do not infer database health from pod readiness.

## Read-only triage
1. Confirm authorized cluster/context: `oc whoami`, `oc config current-context`, `oc version`. Never expose token or kubeconfig contents.
2. Confirm the approved namespace and **separate collection-list permissions** before collecting evidence. `get` on one named object does not authorize `list` on a collection. In Bash/Linux, use `NS=approved-project`; in PowerShell, use `$Ns = 'approved-project'` and substitute `$Ns` for `$NS` in the commands below. Check `oc auth can-i list pods -n "$NS"`, `oc auth can-i list statefulsets.apps -n "$NS"`, `oc auth can-i list persistentvolumeclaims -n "$NS"`, `oc auth can-i list poddisruptionbudgets.policy -n "$NS"`, and `oc auth can-i list events -n "$NS"`. Each must return `yes` before its matching query. Do not assume a positive pods check covers other resource types.
3. Run **only authorized individual reads**, for example `oc get pods -n "$NS" -o wide`, `oc get sts -n "$NS" -o wide`, `oc get pvc -n "$NS"`, `oc get pdb -n "$NS"`, and `oc get events -n "$NS" --sort-by=.lastTimestamp`. Skip any query whose corresponding check returned `no`. Combined `oc get pods,sts,pvc,pdb` can fail partially and obscure the RBAC boundary. `Forbidden` is a permission boundary, not a reason to elevate incident credentials.
4. For optional cluster-scoped reads, separately check `oc auth can-i list nodes` and `oc auth can-i list storageclasses.storage.k8s.io`; only when authorized, run `oc get nodes -L topology.kubernetes.io/zone` and `oc get sc`, respectively. For a named-object `describe`, also verify the applicable `get` permission. If cluster-level inventory is unavailable, ask the platform owner for sanitized evidence instead of broadening access.
5. Ask DBRE/Operator owner for **database-native** replication, leader/quorum, lag, backup freshness and client-error evidence. Avoid credential-bearing logs and full dumps.
6. Correlate timing with MachineConfigPool updates, node maintenance, Operator upgrades, CSI alerts and network incidents.

## Decision matrix
| Finding | Owner / safe next action |
| --- | --- |
| Pod Pending and PVC Pending | Platform + storage: inspect provisioning, topology, CSI; do not delete claim |
| Multi-Attach after node loss | Storage + DBRE: verify old writer is fenced before any supported recovery |
| PDB allowed disruptions zero | Platform + app: postpone voluntary drain; validate replicas and capacity |
| Replica/quorum below safe threshold | DBRE + incident commander: stop automated changes and evaluate vendor-supported recovery |
| Pod healthy but database unavailable | DBRE/app: check database protocol and client routing, not just Kubernetes probes |

## Approval and recovery controls
State-changing steps (drain, restart, failover, detach, scale, restore, PDB/Operator edits) require incident/change authorization, verified single-writer fencing where relevant, backup and RPO/RTO evidence, blast-radius assessment, owner sign-off, stop criteria and a tested or documented recovery/rollback decision. Not all operations are reversible. For split-brain or quorum loss, escalate to database vendor and platform incident commander before action. No generic destructive recovery command is authorized here.

## Post-incident acceptance
Validate app reads/writes, database replication/quorum, no duplicate writers, PVC attachment, node/Operator health, alerts, and agreed RPO/RTO with independent DBRE/app sign-off. Record sanitized evidence, action timeline and follow-up RCA. Do not mark production-approved without independent review and an isolated rehearsal.

References: [OCP 4.22 storage](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/storage/index), [OCP 4.22 nodes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/nodes/index), [Kubernetes PDB semantics](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/).
