# Chapter 048 — Kubernetes Version Upgrades

**Track:** Kubernetes Administration · **Part 10 — Node Operations and Troubleshooting**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 041–047; kubectl, Windows PowerShell; approved staging cluster and access to provider documentation for any actual upgrade

## 1. Production scenario

A Kubernetes cluster must move to a supported minor release before its current version reaches end of support. The cluster hosts Deployments, StatefulSets, ingress controllers, CNI/CSI add-ons, admission policies and critical databases. A successful upgrade must maintain availability, preserve persistent data, avoid deprecated API failures and establish a verified recovery plan.

**Goal:** build a reproducible upgrade-readiness and execution process, with a safe lab that does not change cluster versions. Real upgrades require separate change approval, backups and platform-specific runbooks.

### Learning objectives

1. Understand control-plane, kubelet, kubectl and add-on version relationships.
2. Inventory current versions, node pools, API resources and critical components.
3. Detect deprecated or removed API usage before upgrading.
4. Assess compatibility of CNI, CSI, CoreDNS, kube-proxy, ingress and policy controllers.
5. Design a staged control-plane-first upgrade with node rolling maintenance.
6. Validate availability, data safety, security controls and observability after upgrade.
7. Distinguish rollback, recovery and forward-fix strategies.

## 2. Kubernetes upgrade architecture

```text
Preparation
  | inventory + version-skew review + API deprecations
  | backup/restore rehearsal + add-on compatibility + capacity
  v
Staging upgrade and acceptance tests
  |
  v
Production control-plane upgrade
  | API server + controller manager + scheduler
  v
Cluster add-on upgrades in provider-supported order
  | CNI / CSI / CoreDNS / kube-proxy / ingress / policy agents
  v
Worker node pool rolling upgrades
  | cordon -> drain -> replace/upgrade -> validate -> uncordon
  v
Application and SLO acceptance
  | endpoints + errors + latency + storage + security + observability
  v
Post-change observation and closeout
```

Upgrade sequencing is platform-specific. Managed services (EKS, AKS, GKE) often upgrade the managed control plane separately from node groups. Self-managed clusters using kubeadm require a documented sequence for kubeadm, control-plane components, kubelet and kubectl.

**Version-skew rules change across Kubernetes releases.** Check the official version-skew policy for the exact source and target releases; do not assume every component can be arbitrarily older or newer. In general, kubelet must not be newer than the API server, subject to documented exceptions and supported skew.

## 3. Lab safety and environment

**Labs 1–7 are assessment and tabletop exercises. No actual Kubernetes upgrade is performed.** Never execute an upgrade against production based solely on this chapter. Record change ownership, cluster type, version, node groups, backup status and approved maintenance window.

```powershell
kubectl config current-context
kubectl version
kubectl cluster-info
kubectl get nodes -o wide
kubectl get --raw /version
```

Use an isolated staging cluster to test disruptive operations and verify provider-supported upgrade paths.

## 4. Lab 1 — Inventory versions and node pools

```powershell
kubectl version
kubectl get nodes -o custom-columns=NAME:.metadata.name,KUBELET:.status.nodeInfo.kubeletVersion,RUNTIME:.status.nodeInfo.containerRuntimeVersion,OS:.status.nodeInfo.osImage
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get nodes --show-labels
kubectl get --raw /version
```

**Expected:** server version, client version, kubelet versions, runtime and node topology are visible. Group nodes by pool, zone, operating system and workload criticality. Mixed kubelet versions can be normal during a rolling upgrade, but must remain within supported skew.

### Record an upgrade inventory

| Component | Current | Target | Owner | Compatibility evidence |
|---|---|---|---|---|
| API server | From cluster | Approved release | Platform team | Official skew policy |
| Kubelet/node image | Per node pool | Approved release | Node team | OS/runtime support |
| CNI | Installed version | Supported version | Network team | Vendor compatibility |
| CSI | Installed version | Supported version | Storage team | Driver support |
| CoreDNS/kube-proxy | Installed version | Supported version | Platform team | Provider matrix |
| Ingress/controller | Installed version | Supported version | Application platform | Release notes |
| Admission/policy | Installed version | Supported version | Security team | API/CEL/webhook support |

Do not invent target versions; select them from the provider's current supported upgrade matrix.

## 5. Lab 2 — Inspect API versions and deprecated resource risk

```powershell
kubectl api-versions
kubectl api-resources -o wide
kubectl get crds
kubectl get apiservices
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
```

**Expected:** currently served API groups, custom resources and admission dependencies are inventoried.

Check manifests and Helm charts in Git for removed API versions. For example, older `extensions/v1beta1` Ingress manifests must be migrated to `networking.k8s.io/v1` before running on releases that no longer serve the old API.

### Deprecated API checklist

- Identify removed API versions between **current and target** Kubernetes releases.
- Inspect CRDs and conversion webhooks.
- Review Helm templates and GitOps render output, not only live objects.
- Search API server deprecation metrics and audit logs where available.
- Validate controller compatibility with new API server behavior.
- Apply migrated manifests in staging and verify controller reconciliation.

Tools such as Pluto or kubent may help find deprecated APIs, but tool output is supplementary; official release notes and live API use are authoritative.

## 6. Lab 3 — Inventory system add-ons and admission dependencies

```powershell
kubectl -n kube-system get deployments,daemonsets -o wide
kubectl get pods -A -o wide
kubectl get storageclasses
kubectl get csidrivers
kubectl get ingressclasses
kubectl get validatingadmissionpolicies
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
```

**Expected:** critical agents and admission services are identified. Some API resources may not exist on older clusters or be restricted by RBAC; record those limitations.

### Operational dependencies

- **CNI:** Pod networking, IP allocation, network policy and node initialization.
- **CSI:** volume attachment, mounts, snapshots and stateful failover.
- **CoreDNS:** internal name resolution and service discovery.
- **kube-proxy or eBPF dataplane:** Service traffic routing.
- **Ingress/Gateway controllers:** external traffic availability.
- **Metrics/logging agents:** post-upgrade observability.
- **Admission webhooks:** API availability and policy compatibility.
- **Autoscaler:** node-pool provisioning and scale-down behavior.

Upgrading the API server without checking add-on compatibility can leave workloads apparently healthy while networking, storage or admissions fail for newly created Pods.

## 7. Lab 4 — Prepare backup, restore and stateful-workload readiness

Read-only inventory:

```powershell
kubectl get statefulsets -A
kubectl get pvc -A
kubectl get pv
kubectl get pdb -A
kubectl get volumesnapshotclasses
kubectl get volumesnapshots -A
```

**Expected:** StatefulSets, persistent volumes, disruption budgets and snapshot capabilities are documented. VolumeSnapshot CRDs may be absent; that does not prove a backup strategy is unnecessary.

### Required backup evidence

1. Control-plane/etcd backup or provider-supported recovery mechanism.
2. Application database backups, verified independently of Kubernetes.
3. Backup integrity and **restore test** in a separate environment.
4. Persistent volume snapshot and recovery plan where appropriate.
5. GitOps/IaC, Helm values, Secrets and encryption-key recovery procedures.
6. RPO/RTO objectives and owner sign-off.

**Do not equate a successful snapshot with a verified database-consistent backup.** Coordinate with DBREs for PostgreSQL, MongoDB, Elasticsearch/OpenSearch and other stateful platforms.

## 8. Lab 5 — Evaluate capacity, PDBs and rolling node upgrade strategy

```powershell
kubectl get nodes -o wide
kubectl top nodes
kubectl get pdb -A -o wide
kubectl get deployments -A
kubectl get statefulsets -A
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
```

**Expected:** available node capacity, healthy replicas, disruption allowances and scheduling blockers are visible. `kubectl top` requires Metrics Server.

### Node upgrade planning

For each node pool, determine:
- surge capacity and zone placement;
- PDB `disruptionsAllowed`;
- replicas, topology spread and anti-affinity;
- local PersistentVolumes, `emptyDir` and volume attachments;
- GPU/device plugins, OS/kernel and runtime compatibility;
- system DaemonSet compatibility;
- termination grace and application drain behavior.

**Example planned sequence:** cordon one worker, drain through the Eviction API, upgrade or replace the worker, verify Node Ready and Lease renewal, validate workloads, then proceed to the next node. Do not use `--disable-eviction` or force deletion as a normal upgrade shortcut.

## 9. Lab 6 — Staging upgrade acceptance rehearsal

This lab is a **tabletop and test-plan exercise**, not an actual version change.

### Pre-upgrade acceptance

```powershell
kubectl get nodes
kubectl get pods -A
kubectl get pdb -A
kubectl get pvc -A
kubectl get events -A --sort-by=.lastTimestamp
```

Define baseline service metrics: request success rate, p95/p99 latency, ingress health, DNS resolution, storage operations, database replication/quorum, API admission success, and logging/monitoring availability.

### Staging execution plan

1. Verify source and target releases are a supported upgrade hop.
2. Verify recovery and backup evidence.
3. Apply compatibility fixes to manifests, charts, CRDs and controllers.
4. Upgrade staging control plane using the provider's documented process.
5. Upgrade supported add-ons in the prescribed order.
6. Roll worker nodes one at a time with capacity and PDB checks.
7. Run application smoke tests, stateful transaction tests and security-policy checks.
8. Record version skew, warnings, time taken and failures.
9. Approve production only after staging acceptance passes.

**Expected:** a signed readiness decision and an explicit list of blocking findings.

## 10. Lab 7 — Upgrade incident tabletop and recovery

**Scenario:** after the control-plane upgrade, a workload controller cannot create new Pods. Existing Pods continue serving traffic, but replacements fail due to an incompatible validating webhook. A separate node pool is still on the old kubelet release.

### Investigation commands

```powershell
kubectl version
kubectl get nodes -o wide
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
kubectl get apiservices
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
kubectl get deployments -A
```

### Response

1. Freeze additional upgrade stages.
2. Capture API error, webhook name, service endpoint, TLS error and timeout evidence.
3. Check webhook controller health and supported API versions.
4. Determine whether webhook `failurePolicy` causes admission failure.
5. Repair or roll forward the webhook using the tested compatibility version.
6. Do not disable a security webhook globally without approved emergency risk assessment.
7. Verify new Pods can be created and application SLIs recover.
8. Reassess node-version skew and decide when it is safe to resume.
9. Document change outcome, blast radius and follow-up actions.

**Critical rollback distinction:** managed control-plane upgrades often cannot be downgraded in place. Recovery may require forward-fixing incompatible add-ons or restoring/rebuilding into a supported cluster, not a simple `kubectl rollout undo`. Worker node pools may support replacement with a prior approved node image, subject to control-plane skew and provider constraints.

## 11. Managed versus self-managed upgrades

| Platform | Control-plane path | Node path | Key checks |
|---|---|---|---|
| Amazon EKS | Managed cluster-version update | Managed node group or self-managed node rotation | Supported add-on versions, VPC CNI, CoreDNS, kube-proxy, IAM/Pod Identity |
| Azure AKS | AKS-supported cluster upgrade | Node pool upgrade and surge | Azure CNI, CSI, node image, PDBs, maintenance windows |
| Google GKE | Release channel / supported control-plane update | Node auto-upgrade or controlled pool upgrade | Release channel, node pool strategy, Workload Identity, CSI |
| kubeadm | Documented sequential control-plane upgrade | kubeadm/kubelet upgrade on workers | etcd backup, version skew, CNI, static Pods |

Do not treat the above as an executable provider command sequence. Retrieve current documentation for the exact cluster configuration, region, release channel and target version before scheduling a change.

## 12. Upgrade failure patterns

| Symptom | Likely cause | Investigation |
|---|---|---|
| API resource no longer recognized | Removed/deprecated API | Manifests, release notes, CRDs |
| Admission denies new Pods | Webhook/policy incompatibility | API errors, webhook endpoints |
| Node NotReady after upgrade | Kubelet/runtime/CNI incompatibility | Node conditions, kubelet logs |
| Pods stuck ContainerCreating | CNI/CSI/runtime issue | Pod events and node agents |
| StatefulSet stuck | PVC attach, quorum, topology | PV, CSI, DB replication |
| DNS failures | CoreDNS/network mismatch | CoreDNS logs, DNS tests |
| Service routing errors | kube-proxy/eBPF/CNI issue | Dataplane and endpoint health |
| PDB blocks drain | Insufficient healthy replicas | PDB status, readiness |
| Cluster autoscaler fails | Unsupported controller version | Autoscaler logs and API compatibility |
| Monitoring gaps | Agent/version mismatch | Metrics/log pipelines |

## 13. Production upgrade runbook

### Phase A — Prepare

1. Record cluster/provider, current versions, target release and supported upgrade path.
2. Inventory all node pools, zones, OS images, workloads and add-ons.
3. Review version-skew policy and API deprecation reports.
4. Test backup and restore; document RPO/RTO and rollback constraints.
5. Confirm capacity, PDBs, storage topology and application failover.
6. Run a complete staging upgrade and acceptance suite.
7. Approve change window, owners, communications and abort thresholds.

### Phase B — Execute

1. Establish SLI baseline and incident bridge.
2. Upgrade control plane using supported provider/self-managed procedure.
3. Validate API, authentication, RBAC, admission and core controllers.
4. Upgrade add-ons in vendor-supported order.
5. Roll worker pools gradually with safe drain and capacity checks.
6. Validate each node Ready/Lease, Pod scheduling, CNI/CSI and workload health.
7. Stop immediately on unexpected error-budget consumption or data risk.

### Phase C — Validate

1. Confirm desired control-plane and kubelet versions within supported skew.
2. Verify Deployments, StatefulSets, DaemonSets and Jobs.
3. Check ingress, DNS, Service endpoints, networking and volume mounts.
4. Verify database replication, quorum, reads/writes and backup continuity.
5. Test admission, workload identity and security controls.
6. Confirm logging, metrics, tracing and alerts remain functional.
7. Record customer-facing SLIs and observation-window stability.

### Phase D — Recover or close

For failure, freeze subsequent upgrades, preserve evidence and choose a **provider-supported** forward-fix, node-pool rollback/replacement or cluster recovery plan. Do not promise a control-plane downgrade without explicit provider support. For success, close the change with actual times, versions, exceptions and outstanding risks.

## 14. Upgrade acceptance checklist

- [ ] Current and target versions verified against provider support.
- [ ] Kubernetes version-skew policy checked.
- [ ] Deprecated APIs and CRDs reviewed.
- [ ] CNI/CSI/CoreDNS/kube-proxy compatibility documented.
- [ ] Admission, ingress and autoscaler compatibility reviewed.
- [ ] etcd/control-plane and application backups verified through restore.
- [ ] Stateful quorum, storage topology and PDBs assessed.
- [ ] Staging upgrade and rollback/recovery rehearsal completed.
- [ ] Node pool surge and safe drain plan approved.
- [ ] Security and workload identity tested post-upgrade.
- [ ] Production SLI acceptance and observation plan documented.
- [ ] Actual lab execution and independent review completed before marking Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 15. References

- [Kubernetes Version Skew Policy](https://kubernetes.io/releases/version-skew-policy/)
- [Kubernetes Deprecation Guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)
- [Upgrading kubeadm Clusters](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/)
- [Safely Drain a Node](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)
- [Amazon EKS Update Cluster Version](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [Azure AKS Upgrade Cluster](https://learn.microsoft.com/en-us/azure/aks/upgrade-cluster)
- [GKE Cluster Upgrades](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-upgrades)

**Next:** Chapter 049 — Certificate Management and Rotation.
