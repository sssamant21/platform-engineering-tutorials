# Chapter 047 — Cordon, Drain and Node Maintenance

**Track:** Kubernetes Administration · **Part 10 — Node Operations and Troubleshooting**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapters 019, 023–025, 031–035 and 046; kubectl and Windows PowerShell; isolated multi-worker test cluster for disruptive labs

## 1. Production scenario

A worker node must be patched during an approved maintenance window. It hosts a replicated application, a database StatefulSet, and node-local monitoring agents. A direct reboot could interrupt customer traffic, violate PodDisruptionBudgets (PDBs), or strand a volume attachment. The SRE must inspect capacity and availability, cordon the node, drain it safely, validate service health, perform infrastructure maintenance, then return the node to service.

**Goal:** execute a controlled node-maintenance workflow without treating `--force`, `--disable-eviction`, or `--delete-emptydir-data` as routine shortcuts.

### Learning objectives

1. Distinguish cordon, drain, uncordon and node deletion.
2. Explain the Eviction API and PodDisruptionBudget protections.
3. Inventory workload owners, local data, storage topology and replacement capacity.
4. Understand DaemonSet, mirror Pod and unmanaged Pod behavior during drain.
5. Perform a safe maintenance rehearsal in an isolated cluster.
6. Diagnose blocked drains, Pending replacements and volume-attachment problems.
7. Validate application SLIs and document maintenance rollback.

## 2. Architecture and maintenance lifecycle

```text
Preflight: capacity + PDB + workload/storage inventory + change approval
    |
    v
kubectl cordon NODE
    |  prevents ordinary new Pod scheduling
    v
kubectl drain NODE --ignore-daemonsets
    |  Eviction API (default) + PDB evaluation
    |  controller creates replacement Pods elsewhere
    v
Verify replicas, endpoints, storage and application SLIs
    |
    v
Approved OS / kubelet / VM / node-pool maintenance
    |
    v
Verify Node Ready, runtime, CNI/CSI, kubelet and workloads
    |
    v
kubectl uncordon NODE
    |
    v
Post-change observation and evidence
```

**Cordon** sets `spec.unschedulable=true`; existing Pods remain. **Drain** marks the node unschedulable and attempts to evict eligible Pods. **Uncordon** allows ordinary scheduling again; it does not automatically move Pods back. **Deleting a Node object** is not a safe substitute for draining or powering down its underlying machine.

## 3. Eviction semantics and disruption budgets

By default, `kubectl drain` uses the Eviction API when available, so PDBs can restrict voluntary disruption. PDBs govern disruptions, not the availability of every application dependency; they cannot protect against every involuntary node failure. Deployment strategy, readiness, replica placement, topology spread and spare capacity still matter.

| Situation | Drain behavior / risk |
|---|---|
| Deployment/ReplicaSet Pod | Usually evicted; controller creates replacement |
| StatefulSet Pod | Evicted when permitted; storage and identity need special care |
| DaemonSet Pod | Drain refuses without `--ignore-daemonsets`; DaemonSet Pod stays on node |
| Static/mirror Pod | Cannot be deleted through normal API drain |
| Unmanaged Pod | Drain refuses unless `--force`; may not be recreated |
| Pod using `emptyDir` | Drain may refuse unless `--delete-emptydir-data`; data is lost on eviction |
| PDB with zero allowed disruptions | Eviction waits/retries; investigate before proceeding |
| Pod with long termination grace | Drain waits; review graceful shutdown and timeout |

`--disable-eviction` bypasses PDB protections by using deletion; it is not a normal production maintenance option. `--force` only changes how unmanaged Pods are handled; it does not make data loss safe. Never use `--grace-period=0` casually.

## 4. Lab setup and safety gates

**Labs 1–3 and 7 can be performed as read-only checks. Labs 4–6 require an isolated cluster with at least two schedulable worker nodes, sufficient spare capacity, and authorization to disrupt a test workload.** Do not drain a production node simply to complete a tutorial.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl auth can-i patch nodes
kubectl auth can-i create pods/eviction -n default
kubectl create namespace ch047
```

Choose an approved test worker explicitly; never assume the first Node is safe:

```powershell
$node = "REPLACE_WITH_APPROVED_TEST_WORKER"
kubectl get node $node -o wide
kubectl get node $node -o jsonpath='{.spec.unschedulable}'
```

Record the original `unschedulable` state. Do **not** uncordon a node that was already cordoned for another reason. Confirm the chosen node is not a control-plane node and is not hosting an irreplaceable singleton or local-storage database.

## 5. Lab 1 — Node and workload maintenance inventory

```powershell
kubectl describe node $node
kubectl get pods -A --field-selector spec.nodeName=$node -o wide
kubectl get pdb -A
kubectl get pv
kubectl get storageclass
kubectl get nodes -L topology.kubernetes.io/zone
kubectl top nodes
```

**Expected:** a record of workloads, controllers, resource pressure, PDBs, PVs and topology. `kubectl top` requires Metrics Server; use approved monitoring if unavailable.

For each Pod on the node, identify its owner reference, namespace, replicas, termination grace, PDB coverage, volume types, readiness and criticality. Review EBS/Azure Disk/GCE PD attachment and zone constraints for stateful workloads.

### Preflight gate

Proceed only if:
- spare capacity can host replacements;
- disruption budgets allow the intended migration;
- replica placement and topology permit scheduling;
- storage attachments and local data risks are understood;
- rollback owner and application SLI checks are identified.

## 6. Lab 2 — Build a replicated, disruption-protected test application

Save `ch047-workload.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: maintenance-demo
  namespace: ch047
spec:
  replicas: 3
  selector:
    matchLabels:
      app: maintenance-demo
  template:
    metadata:
      labels:
        app: maintenance-demo
    spec:
      terminationGracePeriodSeconds: 20
      containers:
        - name: web
          image: nginx:1.27
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              memory: 128Mi
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 5
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: maintenance-demo
  namespace: ch047
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: maintenance-demo
---
apiVersion: v1
kind: Service
metadata:
  name: maintenance-demo
  namespace: ch047
spec:
  selector:
    app: maintenance-demo
  ports:
    - port: 80
      targetPort: 80
```

```powershell
kubectl apply -f .\ch047-workload.yaml
kubectl -n ch047 rollout status deployment/maintenance-demo --timeout=180s
kubectl -n ch047 get pods -o wide
kubectl -n ch047 get pdb maintenance-demo -o wide
kubectl -n ch047 get endpointslices -l kubernetes.io/service-name=maintenance-demo
```

**Expected:** three Ready replicas and `disruptionsAllowed` typically 1 when all three are healthy. PDB calculations depend on actual health and controller state. A three-replica Deployment does **not** guarantee one replica is scheduled on the chosen node; inspect placement first. For this lab, a drain is meaningful only if the selected test node hosts an eligible demo Pod. Do not force placement by changing shared scheduling policies.

## 7. Lab 3 — Examine disruption allowance and failure conditions

```powershell
kubectl -n ch047 describe pdb maintenance-demo
kubectl -n ch047 get pdb maintenance-demo -o jsonpath='{.status.disruptionsAllowed}'
kubectl -n ch047 get deployment maintenance-demo -o jsonpath='{.status.readyReplicas}'
kubectl -n ch047 get pods -o wide
```

**Expected:** a measurable disruption budget. If `disruptionsAllowed=0`, pause and investigate missing Ready replicas, PDB selector, rollout state or insufficient capacity.

### PDB failure drill (read-only)

Discuss what happens if only two of three replicas are Ready under `minAvailable: 2`: voluntary eviction is blocked until a healthy replacement becomes available. Do not delete application Pods to manufacture the failure on a shared cluster.

**Important:** a PDB protects matching Pods during voluntary eviction, but a rolling Deployment update follows its own rollout strategy and does not rely on PDB eviction checks in the same way.

## 8. Lab 4 — Cordon the approved worker

Only after the preflight gate:

```powershell
kubectl cordon $node
kubectl get node $node
kubectl get node $node -o jsonpath='{.spec.unschedulable}'
kubectl get pods -A --field-selector spec.nodeName=$node -o wide
```

**Expected:** node shows `SchedulingDisabled` and `spec.unschedulable=true`; existing Pods remain running. DaemonSets and certain explicitly bound workloads have special scheduling behavior, so cordon is not an absolute guarantee no new Pod can appear.

**Rollback if stopping here:** uncordon **only if this lab cordoned the node** and no separate operational restriction exists:

```powershell
kubectl uncordon $node
```

If continuing to Lab 5, leave the node cordoned.

## 9. Lab 5 — Drain safely and observe PDB-aware eviction

**Safety gate:** ensure the selected worker hosts only workloads approved for disruption. Inspect the complete Pod list immediately before drain, not just `ch047`. The command affects **all eligible Pods on that node across namespaces**.

```powershell
kubectl get pods -A --field-selector spec.nodeName=$node -o wide
kubectl get pdb -A
kubectl drain $node --ignore-daemonsets --timeout=5m
```

**Expected:** drain evicts eligible controller-managed Pods and waits for termination. DaemonSet-managed Pods remain. The command may fail if unmanaged Pods or `emptyDir` data exist, or if a PDB prevents eviction. **Do not automatically add `--force` or `--delete-emptydir-data` to make it succeed.**

In a lab cluster where you have reviewed and accepted **all** affected ephemeral data loss, `--delete-emptydir-data` may be appropriate; document that decision explicitly. If a drain stalls, keep the node cordoned, inspect PDB status and events, and choose an approved recovery path.

```powershell
kubectl -n ch047 get pods -o wide
kubectl -n ch047 get pdb maintenance-demo -o wide
kubectl -n ch047 get deployment maintenance-demo
kubectl get pods -A --field-selector spec.nodeName=$node -o wide
```

**Expected:** eligible demo replicas are recreated on other schedulable nodes if resources and topology permit. A successful drain does not prove the application is healthy: check endpoints, traffic, latency and error rates.

## 10. Lab 6 — Maintenance verification and controlled uncordon

In this tutorial, **do not reboot or patch a node** unless you are executing a separately approved infrastructure change. Simulate the maintenance window by verifying state after drain.

```powershell
kubectl get node $node -o wide
kubectl -n ch047 rollout status deployment/maintenance-demo --timeout=180s
kubectl -n ch047 get pods -o wide
kubectl -n ch047 get pdb maintenance-demo -o wide
kubectl -n ch047 get endpointslices -l kubernetes.io/service-name=maintenance-demo
```

If actual maintenance was performed, verify kubelet/runtime, CNI, CSI, Node Ready, Lease freshness and application SLIs before reopening scheduling.

When authorized and after confirming the node should return to service:

```powershell
kubectl uncordon $node
kubectl get node $node -o wide
kubectl get node $node -o jsonpath='{.spec.unschedulable}'
kubectl -n ch047 get pods -o wide
```

**Expected:** scheduling is re-enabled. Existing replacement Pods do not automatically move back. Do not uncordon a node that should remain isolated because of a failed maintenance or security investigation.

## 11. Lab 7 — Node-maintenance incident tabletop

**Scenario:** a drain has been running for 10 minutes. One StatefulSet Pod is protected by a PDB, a DaemonSet remains on the node, and a replacement Pod is Pending due to zone-constrained storage. The maintenance window is nearly over.

### Investigation commands

```powershell
kubectl get nodes -o wide
kubectl get pods -A --field-selector spec.nodeName=$node -o wide
kubectl get pdb -A
kubectl get pods -A --field-selector=status.phase=Pending -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl describe node $node
```

### Decision process

1. **Stop escalation:** do not force-delete stateful Pods or bypass the PDB.
2. Identify which Pod blocks drain and whether it is controller-managed.
3. Check PDB `disruptionsAllowed` and application readiness.
4. Inspect Pending Pod scheduling events, PV node affinity, topology and attach/detach state.
5. Determine whether replacement capacity in the correct zone can be added.
6. Check StatefulSet quorum, leader placement, replication health and failover readiness.
7. Decide whether to extend the approved window, abort, or perform a reviewed storage-safe failover.
8. If aborting, restore scheduling only after confirming the node is healthy and should accept new Pods.
9. Validate service-level SLIs and record remaining risk.

**Expected:** a defensible recovery decision that prioritizes data safety and availability over completing the maintenance on schedule.

## 12. Special workload considerations

### StatefulSets and databases

StatefulSets preserve Pod identity and often use persistent volumes. Verify database replication, leader/follower topology, quorum, backup state, failover procedures and volume attachment behavior before eviction. For single-replica stateful workloads, drain may cause unavoidable downtime unless an application-level migration plan exists. **Never assume Kubernetes rescheduling alone guarantees safe database failover.**

### DaemonSets

Drain ignores DaemonSet-managed Pods only when `--ignore-daemonsets` is provided; it does not delete them. Monitoring, log shipping, CNI and storage agents may remain until the node is stopped or replaced. Their presence is expected and not proof that drain failed.

### Local storage

`emptyDir` contents are lost when the Pod is removed. Local PersistentVolumes can be pinned to a node and may prevent safe rescheduling. Treat local PV migration as a separate storage operation.

### PodDisruptionBudgets

Check both selector correctness and current `disruptionsAllowed`. Overlapping or misconfigured PDBs can block eviction. Do not bypass PDB protections to make a maintenance deadline without explicit incident-level authorization and risk assessment.

### Cloud-managed node groups

EKS managed node groups, AKS node pools and GKE node pools may orchestrate drains and upgrades automatically. Coordinate with the provider's upgrade settings, surge capacity, node termination behavior and maintenance windows. Avoid running conflicting manual drains during managed operations.

## 13. Troubleshooting matrix

| Symptom | Likely cause | Response |
|---|---|---|
| Drain blocked by PDB | Zero allowed disruptions | Restore replica health/add capacity |
| Drain refuses unmanaged Pod | No recognized controller owner | Identify owner; approved migration |
| Drain refuses `emptyDir` | Ephemeral data loss protection | Evaluate data loss before flag |
| DaemonSet Pod remains | Expected behavior | Use `--ignore-daemonsets`; do not force delete |
| Replacement Pending | Capacity, taints, affinity, topology | Scheduler events and node inventory |
| StatefulSet replacement stuck | PV attach/zone/quorum constraints | Storage and DB runbooks |
| Pod termination slow | Grace period, preStop, finalizer | Pod events, app shutdown behavior |
| Node still unschedulable | Cordon not reversed | Uncordon only after approval |
| Service errors after drain | Insufficient endpoints or bad readiness | App SLIs, Service endpoints |
| Node Ready but unhealthy | Kubelet/CSI/CNI or app issue | Node/Pod/infra metrics |

## 14. Production maintenance runbook

### Before change

1. Confirm change ticket, maintenance window, owner, communications and rollback authority.
2. Record cluster, node pool, zone, Kubernetes/kubelet version and node identity.
3. Inventory all Pods, owners, PDBs, PVs, local storage and critical services.
4. Check replica health, quorum, backups, topology, resource headroom and replacement capacity.
5. Define SLI thresholds, expected disruption and abort conditions.

### During change

1. Cordon the approved node.
2. Drain using Eviction API with `--ignore-daemonsets`; review any blocked Pod rather than adding unsafe flags.
3. Validate replacements, endpoints and application health.
4. Perform approved infrastructure maintenance.
5. Verify node OS, kubelet, runtime, network, storage and Ready/Lease status.
6. Uncordon only when the node is healthy and cleared for service.

### After change

1. Confirm node conditions and no unexpected taints.
2. Verify desired/available replicas and StatefulSet health.
3. Check customer-facing SLIs, error rate, latency and capacity.
4. Record disruptions, exceptions, actual duration and remediation items.
5. Keep monitoring through the agreed observation window.

### Abort / rollback criteria

Abort if PDB protections cannot be satisfied, quorum is at risk, replacement Pods cannot schedule, persistent storage cannot attach safely, or application error budgets are being exhausted. A partially completed drain does **not** automatically reverse evictions; recovery may require rescheduling, restoring capacity and application-level validation.

## 15. Cleanup

Delete only the disposable lab namespace after confirming the node is in its intended scheduling state:

```powershell
kubectl get node $node -o wide
kubectl -n ch047 get deployment,pdb,service,pods
kubectl delete namespace ch047
```

If the lab cordoned a node and it is still cordoned, obtain confirmation that it should return to service before running `kubectl uncordon $node`. Do not uncordon a node that was already unschedulable before the lab.

## 16. Acceptance checklist

- [ ] Cordon, drain, uncordon and Node deletion distinguished.
- [ ] Full node workload and storage inventory recorded.
- [ ] PDB and disruption allowance checked before drain.
- [ ] Replicated test workload deployed with readiness probe and PDB.
- [ ] Node cordoned without evicting existing Pods.
- [ ] Safe drain attempted only on an approved disposable worker.
- [ ] DaemonSet and local-data behaviors explained.
- [ ] Replacement scheduling, endpoints and application SLIs validated.
- [ ] StatefulSet and volume-attachment risks reviewed.
- [ ] Rollback/abort criteria documented.
- [ ] Node restored to its intended scheduling state.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 17. References

- [Safely Drain a Node](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)
- [Disruptions and PodDisruptionBudgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Nodes](https://kubernetes.io/docs/concepts/architecture/nodes/)
- [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
- [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)

**Next:** Chapter 048 — Kubernetes Version Upgrades.
