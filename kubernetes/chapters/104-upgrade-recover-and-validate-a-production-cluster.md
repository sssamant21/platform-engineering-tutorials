# Chapter 104 — Upgrade, Recover and Validate a Production Cluster

**Track:** Kubernetes Administration · **Part 21 — Final Enterprise Kubernetes Capstone**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Kubernetes administrators, SREs, platform engineers, DBREs and change approvers  
**Prerequisites:** Chapters 071–075, 076–090, 096–103; the disposable cluster and HA PostgreSQL lab from Chapters 101–102; GitOps, monitoring, approved backups, IaC and a provider-supported Kubernetes upgrade path.

## Mission

Plan, execute and validate a controlled Kubernetes cluster upgrade in a **production-like, nonproduction environment**. Demonstrate compatibility assessment, safe control-plane/node sequencing, add-on updates, workload and data protection, recovery from upgrade faults, measurable SLO validation and formal operational handoff.

**Important:** This chapter does not authorize an upgrade on a live production cluster. Managed control-plane downgrades are commonly unsupported. A recovery plan may require forward-fix, node rollback, workload rollback or cluster rebuild and restore—not simply reverting a version number.

## 1. Upgrade architecture and change boundaries

```text
      Change approval / architecture review
                       |
           Compatibility + backups
                       |
             Staging rehearsal
                       |
              Control-plane wave
                       |
         Core add-ons and node-pool waves
                       |
           Application and data checks
                       |
           SLO / security / DR acceptance
                       |
                Production handoff
```

Upgrade layers have different ownership:
- **Control plane:** API server, scheduler, controllers, etcd (provider-managed or self-managed).
- **Nodes:** kubelet, OS image, container runtime, device plugins.
- **Add-ons:** CNI, CoreDNS, CSI, ingress, metrics, autoscaler, admission webhooks.
- **Platform controllers:** GitOps, operators, cert-manager, policy engines.
- **Applications:** Deployments, StatefulSets, PostgreSQL and clients.

A green Kubernetes version report does not establish compatibility at all layers.

## 2. Lab 01 — Define upgrade scope and acceptance

Document source/target Kubernetes versions, provider/region, current node images, add-ons, operator versions, workloads, maintenance window, expected impact, owners, approvals, SLOs, RPO/RTO and budget.

```text
Change ID:
Cluster UID / account / region:
Source version:
Target supported version:
Change owner / approver:
Upgrade waves:
Dependency matrix:
Backups and recovery evidence:
Stop/go criteria:
Rollback or forward-fix:
SLO verification:
Communication and escalation:
```

Use current vendor/provider support matrices; do not assume any target minor version is available in all cloud regions.

## 3. Lab 02 — Establish baseline and inventory

```powershell
$Context = "<staging-context>"
kubectl --context $Context version
kubectl --context $Context get nodes -o wide
kubectl --context $Context get deployments,statefulsets,daemonsets -A
kubectl --context $Context get pdb -A
kubectl --context $Context get apiservices
kubectl --context $Context get crds
kubectl --context $Context get events -A --sort-by=.lastTimestamp
```

Capture request error rate, p95/p99 latency, throughput, database primary and replication lag, backup freshness, DNS, ingress, storage, GitOps sync, node resource pressure and cloud costs. Preserve timestamped evidence.

## 4. Lab 03 — Kubernetes version skew and API compatibility

Validate supported control-plane-to-kubelet skew, kube-proxy/CNI compatibility, API deprecations and removed resources. Check:
- `apiVersion` in every GitOps manifest and Helm chart.
- CRD served/storage versions and conversion webhooks.
- Admission webhook compatibility and failure policy.
- Controller/operator supported Kubernetes versions.
- kubectl client version compatibility.

```powershell
kubectl --context $Context get crds
kubectl --context $Context get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl --context $Context get apiservices
```

Use an approved deprecated-API scanner or server-side dry-run against a cluster already on the **target** version. A dry-run on the old cluster does not prove target-version support.

## 5. Lab 04 — Dependency and add-on matrix

Create a compatibility matrix:

| Component | Current | Target | Validation owner |
|---|---|---|---|
| Kubernetes control plane | Observed | Provider-supported | Platform |
| Node OS / kubelet | Observed | Compatible | Platform |
| CNI / kube-proxy | Observed | Supported | Network |
| CoreDNS | Observed | Supported | Platform |
| CSI / snapshots | Observed | Supported | Storage |
| Autoscaler / Karpenter | Observed | Supported | Platform |
| GitOps controller | Observed | Supported | Platform |
| Admission / policy | Observed | Supported | Security |
| PostgreSQL operator | Observed | Supported | DBRE |
| Ingress / Gateway API | Observed | Supported | Network |

Record source links and review dates. Do not blindly upgrade all add-ons simultaneously; follow documented provider sequencing.

## 6. Lab 05 — Preflight capacity and disruption safety

```powershell
kubectl --context $Context get nodes -L topology.kubernetes.io/zone
kubectl --context $Context get pdb -A
kubectl --context $Context get hpa -A
kubectl --context $Context get pvc -A
kubectl --context $Context get pods -A --field-selector=status.phase=Pending
kubectl --context $Context top nodes
```

`top` requires Metrics Server. Confirm spare capacity for surge nodes, cloud quotas, available IPs, image pull capacity, zone distribution, eviction budgets and local storage constraints. If one node drain would violate service availability, **stop before upgrading**.

## 7. Lab 06 — Backup and recovery readiness

Validate current backups for:
- Kubernetes configuration and GitOps repositories.
- Control-plane/etcd state where self-managed.
- PostgreSQL database-native backups and WAL archive.
- Persistent volumes/snapshots when appropriate.
- Secrets, encryption keys, DNS/ingress configuration.
- IaC state and node group definitions.

Restore disposable test data to an isolated instance and verify checksums. A successful backup job without a tested restore is not a recovery guarantee.

## 8. Lab 07 — GitOps freeze and change-control readiness

Record the approved Git commit, image digests, chart versions and IaC plan. Prevent overlapping releases and establish an incident bridge/on-call schedule. Validate that emergency application rollback is compatible with GitOps reconciliation.

```powershell
git status
git log -1 --oneline
git diff --check
kubectl --context $Context get deployments -A
```

Document break-glass access and the procedure for reconciling manual emergency changes back into Git. Never leave an untracked production hotfix.

## 9. Lab 08 — Staging upgrade rehearsal

Create or select a disposable clone with representative CNI, CSI, admission, operator and workload configurations. Use the cloud provider's **current supported upgrade mechanism** or self-managed cluster lifecycle tooling. Do not invent generic `kubectl upgrade` commands: Kubernetes has no universal API command to upgrade managed control planes.

Record each command, provider operation ID, duration, node replacement, errors and recovery actions. Validate the exact target version in the test environment before planning production waves.

## 10. Lab 09 — Control-plane upgrade

For EKS/AKS/GKE, execute only the provider-documented control-plane operation with appropriate approvals. For kubeadm/self-managed clusters, follow official version-specific kubeadm and etcd procedures with quorum and backup safeguards.

During the operation, monitor API availability, authentication, controller health, admission, scheduler and operator reconciliation. Do not assume a control-plane upgrade can be rolled back; document the supported forward-fix or rebuild path.

**Acceptance:** target API version reported, authentication works, APIs/webhooks respond and critical workloads remain within SLO.

## 11. Lab 10 — Core add-on validation

Verify CNI, CoreDNS, kube-proxy where applicable, CSI, snapshots, ingress, metrics, autoscaler, admission and certificate controllers after the control-plane change.

```powershell
kubectl --context $Context get pods -n kube-system -o wide
kubectl --context $Context get daemonsets -A
kubectl --context $Context get apiservices
kubectl --context $Context get events -A --sort-by=.lastTimestamp
```

Run positive and negative network tests, DNS resolution, TLS, PVC provisioning and policy admission checks. A healthy DaemonSet count does not prove packet forwarding or storage operations work.

## 12. Lab 11 — Canary node pool and replacement

Provision a small, disposable canary node pool at the target kubelet/OS version using approved IaC or provider tooling. Schedule a test workload there and verify CNI, CSI, DNS, image pulls and workload identity.

```powershell
kubectl --context $Context get nodes -o wide
kubectl --context $Context get nodes -L topology.kubernetes.io/zone
kubectl --context $Context get pods -A -o wide
```

Use a provider-supported rolling node replacement process. Do not manually drain database primary nodes without operator approval and verified failover readiness.

## 13. Lab 12 — Controlled node drain and PDB verification

On an **approved disposable test node**, after capacity and data checks:

```powershell
kubectl --context $Context get pdb -A
kubectl --context $Context cordon <test-node>
kubectl --context $Context drain <test-node> --ignore-daemonsets --timeout=5m
kubectl --context $Context uncordon <test-node>
```

If a PDB blocks eviction, treat it as a safety signal. Do not add `--force` or `--delete-emptydir-data` merely to finish. Validate replacement node readiness, zone distribution, application error budget and operator health.

## 14. Lab 13 — Stateful PostgreSQL continuity

Before/after the node wave, verify:
- Exactly one writable primary.
- Replica streaming and lag.
- WAL archiving and backup freshness.
- Persistent volume attachment and topology.
- Client transaction success and reconnect behavior.
- Operator compatibility with the upgraded Kubernetes API.

Example PostgreSQL SQL on the **primary**:

```sql
SELECT pg_is_in_recovery();
SELECT application_name, state, sync_state, write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
```

Do not infer data integrity from StatefulSet Ready replicas. Run application-level reads/writes and checksums using disposable test data.

## 15. Lab 14 — Failure during upgrade: node pool regression

In the disposable staging cluster, deliberately misconfigure a **test-only** node label or taint so a canary workload becomes Pending. Capture scheduler events, affected replicas, autoscaler decisions and user impact.

```powershell
kubectl --context $Context get pods -A --field-selector=status.phase=Pending
kubectl --context $Context describe pod <canary-pod> -n <test-namespace>
kubectl --context $Context get nodes --show-labels
```

**Recover:** revert the test configuration in IaC/GitOps, verify workload placement and stop the upgrade wave until acceptance passes. Do not use a cluster-wide label mutation as fault injection.

## 16. Lab 15 — Failure during upgrade: incompatible webhook

Use a dedicated test webhook or controlled **tabletop** scenario in which an admission/conversion webhook is unavailable after upgrade. Diagnose API service availability, certificate validity, webhook backend health and operator reconciliation.

```powershell
kubectl --context $Context get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl --context $Context get apiservices
kubectl --context $Context get events -A --sort-by=.lastTimestamp
```

**Recover:** repair the test webhook deployment or revert its approved Git change. Never globally disable security admission or delete CRDs to bypass the fault.

## 17. Lab 16 — Upgrade rollback, forward-fix and rebuild decision

Distinguish:
1. **Workload rollback:** revert application Git revision.
2. **Node rollback:** replace canary nodes with a supported prior image/version when permitted.
3. **Add-on rollback:** use vendor-supported version compatibility and migration procedures.
4. **Control-plane forward-fix:** repair compatible components when downgrade is unsupported.
5. **Cluster rebuild:** provision a new supported cluster, restore configuration and data, then validate traffic cutover.

For each path, document decision owner, last safe rollback point, data/schema compatibility, RTO/RPO and expected impact. **Do not claim `terraform apply` or Helm rollback can reverse a completed managed control-plane or database data-format upgrade.**

## 18. Lab 17 — Post-upgrade reliability and security validation

Run the same synthetic transactions and load profile used in the baseline. Compare p95/p99 latency, error rate, throughput, CPU throttling, memory, storage latency, replication lag and capacity. Validate:
- TLS/certificates and workload identity.
- RBAC, Pod Security Admission and NetworkPolicy enforcement.
- DNS/ingress, CNI and CSI behavior.
- GitOps convergence and operator status.
- Backups, alerts, logs and traces.
- Node topology and failover behavior.

An upgrade is not accepted until user-visible health and security checks pass.

## 19. Lab 18 — Disaster recovery and operational handoff

Execute a controlled restore test to an isolated recovery environment. Confirm the new cluster version can read restored manifests, secrets and data; validate PostgreSQL recovery compatibility and application transactions. Record recovery times and remaining gaps.

Prepare:
- Final change record and version matrix.
- IaC/Git revisions and cloud operation IDs.
- Before/after dashboards and test results.
- Backup/restore evidence.
- Runbook and escalation updates.
- Known issues, remediation owners and due dates.
- Cost and temporary-resource cleanup.

## 20. Upgrade acceptance matrix

| Domain | Minimum evidence | Pass condition |
|---|---|---|
| Versions | API, kubelet, add-on inventory | Supported combinations |
| Control plane | API/auth/admission health | Operations functional |
| Networking | DNS, ingress, policy tests | Correct routing/isolation |
| Storage | PVC and snapshot tests | Durable operations |
| Scheduling | PDB, topology, canary drain | Capacity and resilience |
| Stateful service | Primary/replicas and transactions | Single-writer integrity |
| GitOps/operators | Reconciliation and CR status | Intended state converged |
| Observability | Synthetic alerts and telemetry | Detection operational |
| Security | RBAC, TLS, admission, identities | No regression |
| Recovery | Restore test, RTO/RPO | Targets evaluated |
| FinOps | Node hours and cloud resource inventory | Cost accounted for |

**Final acceptance checklist:**
- [ ] Source and target versions confirmed provider-supported.
- [ ] Deprecated API and CRD compatibility reviewed.
- [ ] Add-on and operator matrix approved.
- [ ] Preflight capacity, PDBs and backups validated.
- [ ] Staging rehearsal completed with evidence.
- [ ] Control-plane and node waves executed safely.
- [ ] PostgreSQL single-writer safety and data integrity preserved.
- [ ] Failure simulations detected and recovered.
- [ ] Application SLOs and security controls revalidated.
- [ ] Restore and recovery path independently tested.
- [ ] Change record and runbooks updated.
- [ ] Independent reviewer signed off on acceptance.

## 21. Troubleshooting runbook

| Symptom | First checks | Response |
|---|---|---|
| API errors after upgrade | Version, auth, webhooks, provider events | Halt waves; repair supported dependencies |
| Nodes fail to join | IAM, image, bootstrap, CNI, quotas | Repair canary pool |
| Pods Pending | Events, requests, taints, affinity, PDB | Restore scheduling/capacity |
| DNS/ingress regression | CoreDNS, CNI, endpoints, TLS | Roll back supported add-on/config |
| PVC attach failure | CSI, topology, driver logs | Restore storage compatibility |
| PostgreSQL unhealthy | Operator, role, replication, WAL, storage | Protect data; follow DBRE runbook |
| GitOps drift | Repo revision, controller logs | Reconcile approved state |
| SLO degradation | App metrics, traces, dependencies | Stop promotion; rollback/forward-fix |
| Cost spike | Surge nodes, LB, disks, logs | Remove only approved temporary resources |

## 22. Cleanup and lessons learned

Remove test-only canary resources and old node pools **only after** workloads, volumes and backups are confirmed safe. Verify no unexpected public IPs, disks, load balancers or billable nodes remain. Preserve logs, change records and recovery evidence. Conduct a blameless review of technical and process gaps.

## 23. Production takeaways

A Kubernetes upgrade is a coordinated lifecycle change across the API, nodes, add-ons, operators and applications. Success requires verified service health, single-writer data safety, security parity and a supported recovery path—not simply an upgraded version number.

**Draft status:** upgrade commands, fault injections and acceptance tests have not been executed or independently reviewed in this publication workflow.

**Next:** Chapter 105 — Kubernetes Administrator and SRE Final Assessment.
