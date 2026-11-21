# Chapter 017 — Stateful Services on OpenShift: HA and Data Safety

**Audience:** Platform administrators, SREs, DBREs | **Duration:** ~60 minutes | **Baseline:** OCP 4.22 (verify exact cluster version).  
**Status:** Drafted; not lab-tested or production-approved.

## Objectives and prerequisites
Understand OpenShift-specific failure domains, CSI topology, Operator ownership, StatefulSet identity, disruption controls and safe incident escalation for PostgreSQL, Kafka, MongoDB and Redis. Prerequisites: Chapters 005, 008, 013 and 016; read-only access to an authorized project, `oc` configured, known cluster/context, and application owner contact. See the existing [Kubernetes track](../../kubernetes/README.md) for generic StatefulSet and scheduling fundamentals.

## 60-minute outline
- 0–10 min: Identify application Operator, database architecture, replica/failover manager, RPO/RTO and backup ownership.
- 10–25 min: Audit pods, StatefulSets, PVCs, StorageClasses and CSI attachment/topology.
- 25–40 min: Inspect placement, topology spread, PDBs, node pressure and capacity headroom.
- 40–50 min: Walk through a node-loss or volume-attachment incident without changing the cluster.
- 50–60 min: Review evidence, escalation and change-control decisions.

## Architecture and operational boundaries
OpenShift manages infrastructure primitives; **a StatefulSet alone does not implement database replication, quorum or safe leader election**. The application/database Operator or designated failover controller owns database-specific HA. Platform team owns node/cluster health, CSI availability, placement and authorized maintenance; DBRE/data owners own replication consistency, backups and recovery acceptance; application owners own user impact and SLOs.

| Workload | Critical checks | Do not assume |
| --- | --- | --- |
| PostgreSQL | primary/standby identity, WAL lag, synchronous policy, fencing and backup restore evidence | pod restart equals safe failover |
| Kafka | broker/controller quorum, ISR, partitions, rack awareness and storage | healthy pods imply healthy partition replication |
| MongoDB | replica set majority, election state, replication lag and storage | Kubernetes readiness proves replica-set consistency |
| Redis | Sentinel/Cluster mode, quorum, persistence, replication offset and client redirection | a replica is automatically promoted safely |

**Do not use** generic pod restarts, forced PVC detach, node drains, scaling, PDB changes, or storage deletion as first-line remediation. A PDB limits eligible voluntary evictions through the eviction API; it does not prevent node failures, direct pod deletion or all forms of disruption. Availability must be verified at the database protocol level.

## Read-only investigation (replace placeholder)
```sh
oc whoami
oc config current-context
oc version
NS=approved-project
oc auth can-i list pods -n "$NS"
oc get pods,statefulsets,pdb -n "$NS" -o wide
oc get pvc -n "$NS"
oc get events -n "$NS" --sort-by=.lastTimestamp
oc get nodes -o wide             # requires cluster-scoped permission
oc get storageclass              # requires cluster-scoped permission
```
PowerShell:
```powershell
$Ns = "approved-project"
oc whoami
oc config current-context
oc auth can-i list pods -n $Ns
oc get pods,statefulsets,pdb -n $Ns -o wide
oc get pvc -n $Ns
oc get events -n $Ns --sort-by=.lastTimestamp
```
**RBAC precision:** `oc get pods -n "$NS"` without an object name performs a collection LIST operation; `oc auth can-i list pods` is the matching preflight, not `get pods`. The combined `oc get pods,statefulsets,pdb` additionally requires `list` on StatefulSets and PodDisruptionBudgets. Cluster-scoped nodes and StorageClasses require separate cluster-scoped `list` permissions; omit those queries if access is not approved.\n\n**Expected:** workload objects show names/status; Bound PVCs only establish provisioning, not database integrity. `Forbidden` indicates insufficient RBAC—request scoped read access, not cluster-admin. `No resources found` may mean wrong namespace. `Pending` PVC, `Multi-Attach` events, `NotReady` pods or PDB `ALLOWED DISRUPTIONS=0` require diagnosis, not immediate mutation. `oc top` requires metrics availability and permission.

## Placement and storage interpretation
Check pod node/zone, topology constraints, anti-affinity and tolerations; inspect StorageClass `volumeBindingMode`, reclaim policy and `allowVolumeExpansion`. Distinguish RWO access mode from guaranteed single-pod exclusivity; RWOP is distinct and depends on CSI support. Verify CSI driver capabilities and zone affinity before planning rescheduling. A healthy PVC and pod are not evidence of application-level consistency.

## Change and rollback gates
Before node drain, rollout, volume resize or Operator upgrade: obtain platform change approval, application/DBRE owner sign-off, tested backup/recovery path, maintenance window, measured replication/quorum health, capacity in alternate failure domains, current PDB budget, defined stop conditions and post-change acceptance criteria. Determine rollback feasibility **per operation**: storage expansion and some upgrades cannot simply be reversed. If quorum is lost or split-brain suspected, freeze changes and engage vendor/DBRE incident command. Never run destructive commands in this chapter.

## Validation and evidence
Use [Lab 017](../labs/017-stateful-ha-read-only-audit.md) and [Stateful HA triage runbook](../runbooks/stateful-workload-ha-triage.md). Record sanitized timestamp, exact OCP version, cluster class, project, RBAC constraints, observed output, database-native health from authorized owner, reviewer and pending follow-ups. Do not commit credentials or raw Secrets.

## Authoritative references (confirm feature compatibility with deployed minor version)
- [Red Hat OCP 4.22 storage](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/storage/index)
- [Red Hat OCP 4.22 nodes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/nodes/index)
- [Red Hat OCP 4.22 Operators](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/operators/index)
- [Kubernetes disruption budgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
