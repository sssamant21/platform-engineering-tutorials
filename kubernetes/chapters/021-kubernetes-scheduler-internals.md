# Chapter 021 — Kubernetes Scheduler Internals

**Track:** Kubernetes Administration · **Part 05:** Scheduling and Resource Management · **Status:** Draft — lab execution and review pending

## 1. Objectives and operational scenario

You are the on-call SRE for a Kubernetes cluster. An application Deployment reports `Pending` Pods while nodes appear healthy. The incident involves resource requests, placement constraints, and scheduling events. You must determine **why the scheduler cannot bind the Pods**, apply the smallest safe change, and prove recovery.

By the end of this chapter you should be able to:

1. Trace a Pod from creation through scheduling, binding, kubelet admission and startup.
2. Explain the scheduler's queueing, filtering, scoring, reserve/permit/pre-bind/bind/post-bind stages.
3. Interpret scheduling constraints, requests versus limits, and allocatable node resources.
4. Diagnose `FailedScheduling` events without confusing them with image-pull or container failures.
5. Describe preemption, priority classes, nominated nodes, scheduler profiles and scheduling gates.
6. Identify scheduler high-availability, performance and observability considerations.
7. Run six reproducible PowerShell/kind labs and collect incident evidence.

## 2. Scheduler architecture

```text
API server: new Pod (spec.nodeName empty)
                  |
                  v
          Scheduler watches Pods
                  |
          Active / backoff / unschedulable queues
                  |
             Scheduling cycle
                  |
          PreFilter -> Filter feasible nodes
                  |
          PostFilter (e.g. preemption when needed)
                  |
             PreScore -> Score
                  |
             Select preferred node
                  |
              Binding cycle
                  |
       Reserve -> Permit -> PreBind -> Bind -> PostBind
                  |
           API server binding
                  |
           kubelet on chosen node
                  |
       image, volume, sandbox, container setup
```

The default scheduler is typically `kube-scheduler`, a control-plane component. It watches Pods without a node assignment and makes a binding decision based on the cluster's observed state. **The scheduler does not start containers**; the kubelet and runtime do that after binding.

Scheduling is not the same as autoscaling. If no node fits, a cluster autoscaler may provision capacity when configured, but the scheduler alone does not create nodes.

### Scheduling framework extension points

| Stage | Purpose | Operational relevance |
|---|---|---|
| QueueSort | Determine Pod ordering | Priority influences order |
| PreFilter | Precompute Pod scheduling state | Constraints and resource analysis |
| Filter | Eliminate nodes that do not satisfy hard requirements | `0/N nodes available` evidence |
| PostFilter | Attempt recovery when no node is feasible | Preemption may be considered |
| PreScore / Score | Rank feasible nodes | Soft preferences and balancing |
| Reserve | Reserve internal scheduling state | Prevent competing scheduling assumptions |
| Permit | Allow or delay binding | Plugin-controlled admission |
| PreBind | Final preparations before binding | Storage or custom plugins |
| Bind | Assign the Pod to a node | Pod gets `spec.nodeName` |
| PostBind | Notifications and bookkeeping | Scheduler extension behavior |

Plugin names and default weights vary by Kubernetes release and scheduler configuration. Treat this as a conceptual framework, not a fixed execution trace for every Kubernetes version.

## 3. Scheduling decisions: hard constraints versus preferences

A node must pass **all required Filter checks** to be feasible. Examples:

- Node has sufficient **unallocated requested CPU/memory**, relative to allocatable capacity.
- Pod's `nodeSelector` and required node affinity match labels.
- Untolerated `NoSchedule` taints do not exclude the node.
- Required Pod affinity/anti-affinity and topology rules are satisfied.
- Volume topology and access constraints permit placement.
- Node conditions and other plugin constraints permit scheduling.

After filtering, scoring ranks feasible nodes. Preferred affinity and soft topology preferences can influence placement but do not guarantee it.

**Important:** `kubectl top nodes` shows observed utilization, while scheduling typically uses **requests** and node allocatable capacity, not current CPU usage. A node with low observed CPU can still be unschedulable because requested CPU is already committed.

### Node capacity, allocatable and requests

```text
Node capacity
   - kube/system reservations
   - eviction reservations
   = node allocatable

Sum of Pod requests must fit allocatable for scheduling
```

This simplified model omits additional policy and plugin behavior. Requests influence placement; limits influence runtime enforcement. Memory pressure, ephemeral-storage exhaustion, PID pressure and runtime failures can still affect a Pod after it has been scheduled.

## 4. Pod lifecycle versus scheduling lifecycle

| Observation | Likely stage | Next action |
|---|---|---|
| Pod Pending, `nodeName` empty, FailedScheduling event | Scheduler cannot place | Inspect events, requests, selectors, taints, volumes |
| Pod Pending, nodeName assigned | Scheduler already bound | Inspect kubelet, volume mount, sandbox, image pull |
| Pod `ContainerCreating` | Kubelet/runtime setup | Inspect events and node |
| Pod `ImagePullBackOff` | Image retrieval | Registry, image, credentials |
| Pod `CrashLoopBackOff` | Container repeatedly exits | Logs, exit codes, probes |
| Pod `Running` but unready | Application/probe readiness | Probe, app dependencies, EndpointSlices |

`Pending` is a Pod phase, not a precise diagnosis. Always check conditions, events, `spec.nodeName`, and container status.

## 5. Scheduling queues and backoff

The scheduler manages Pods awaiting scheduling in active, backoff and unschedulable states. A previously unschedulable Pod can be retried when relevant cluster changes occur, such as new node capacity, released resources, or label/taint changes. Queue mechanics and retry triggers depend on the scheduler version and enabled plugins.

**Incident implication:** A scheduling fix might not be reflected instantaneously. Observe the Pod events and node assignment after changes rather than repeatedly deleting Pods without understanding the constraint.

## 6. Priority and preemption

PriorityClasses assign integer priorities to Pods. Higher-priority Pods can be considered earlier and, under suitable conditions, may trigger preemption of lower-priority Pods to make room. Preemption is not guaranteed to resolve every scheduling constraint, especially affinity, storage, or topology conflicts.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: application-important
value: 100000
globalDefault: false
description: "Example only; requires cluster governance approval"
```

Do **not** create production PriorityClasses without governance. Cluster-scoped priorities can displace unrelated workloads. Preemption interacts with disruption and grace periods; `nominatedNodeName` is a scheduling hint, not proof of final placement.

## 7. Scheduler profiles and multiple schedulers

A Pod normally uses `spec.schedulerName: default-scheduler` unless a different scheduler is configured. Clusters can define scheduler profiles and custom schedulers, but misconfiguration can leave Pods unscheduled. Confirm which scheduler is responsible before debugging custom plugin behavior.

```powershell
kubectl get pod example -o jsonpath='{.spec.schedulerName}'
kubectl get pod example -o jsonpath='{.spec.nodeName}'
```

Scheduling gates (`spec.schedulingGates`) deliberately prevent scheduling until the gates are removed by an authorized controller or operator. A Pod gated this way is not necessarily suffering a capacity failure.

## 8. Lab setup and isolation

**Required:** Windows PowerShell, Docker Desktop, kind, kubectl. The lab uses a **two-worker kind cluster** to compare placement. All writes target `kind-k8s-admin-ch021`.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch021 | Out-Null
Set-Location .\k8s-ch021
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-config.yaml
kind create cluster --name k8s-admin-ch021 --config .\kind-config.yaml --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch021 get nodes -o wide
kubectl --context kind-k8s-admin-ch021 get nodes -o json
```

**Expected:** context `kind-k8s-admin-ch021`, three Ready nodes. If Docker capacity cannot support this cluster, stop and record Blocked; do not change the exercises to a shared cluster.

Create a namespace and record the worker names:

```powershell
kubectl --context kind-k8s-admin-ch021 create namespace ch021
$workers = @(kubectl --context kind-k8s-admin-ch021 get nodes -l '!node-role.kubernetes.io/control-plane' -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | Where-Object { $_ })
$workers
if ($workers.Count -ne 2) { throw "Expected exactly two worker nodes" }
```

**Note:** The command filters the control-plane role label; inspect returned node labels if the topology differs. The variable `$workers` is reused in later labs within the same PowerShell session.

## 9. Lab A — Observe normal scheduling and binding

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: baseline
  namespace: ch021
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 25m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\baseline.yaml

kubectl --context kind-k8s-admin-ch021 apply --dry-run=server -f .\baseline.yaml
kubectl --context kind-k8s-admin-ch021 apply -f .\baseline.yaml
kubectl --context kind-k8s-admin-ch021 -n ch021 wait --for=condition=Ready pod/baseline --timeout=180s
kubectl --context kind-k8s-admin-ch021 -n ch021 get pod baseline -o wide
kubectl --context kind-k8s-admin-ch021 -n ch021 get pod baseline -o jsonpath='{.spec.nodeName}'
kubectl --context kind-k8s-admin-ch021 -n ch021 get events --sort-by=.lastTimestamp
```

**Expected:** Pod has a nodeName and reaches Ready. The selected node can vary. Capture the `Scheduled` event and Pod UID.

## 10. Lab B — Required node selector prevents scheduling

### B1. Create an impossible placement constraint

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: selector-blocked
  namespace: ch021
spec:
  nodeSelector:
    training.example.com/pool: nonexistent
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 25m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\selector-blocked.yaml

kubectl --context kind-k8s-admin-ch021 apply -f .\selector-blocked.yaml
kubectl --context kind-k8s-admin-ch021 -n ch021 get pod selector-blocked -o wide
kubectl --context kind-k8s-admin-ch021 -n ch021 describe pod selector-blocked
```

**Expected:** Pod Pending with no assigned node; FailedScheduling event refers to node affinity/selector mismatch.

### B2. Resolve by labeling a disposable worker

```powershell
kubectl --context kind-k8s-admin-ch021 label node $workers[0] training.example.com/pool=lab
kubectl --context kind-k8s-admin-ch021 -n ch021 wait --for=condition=Ready pod/selector-blocked --timeout=180s
kubectl --context kind-k8s-admin-ch021 -n ch021 get pod selector-blocked -o wide
```

**Expected:** Pod schedules onto the labeled worker. **Do not label production nodes merely to satisfy an unreviewed application request.** Review workload policy and placement requirements first.

## 11. Lab C — Taints and tolerations

### C1. Add a NoSchedule taint to the other worker

```powershell
kubectl --context kind-k8s-admin-ch021 taint nodes $workers[1] training.example.com/dedicated=restricted:NoSchedule
kubectl --context kind-k8s-admin-ch021 describe node $workers[1]
```

Create a Pod requiring the tainted worker, but without a toleration:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: taint-blocked
  namespace: ch021
spec:
  nodeSelector:
    kubernetes.io/hostname: PLACEHOLDER
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 25m
          memory: 16Mi
'@.Replace('PLACEHOLDER', $workers[1]) | Set-Content -Encoding ascii .\taint-blocked.yaml

kubectl --context kind-k8s-admin-ch021 apply -f .\taint-blocked.yaml
kubectl --context kind-k8s-admin-ch021 -n ch021 describe pod taint-blocked
```

**Expected:** Pending because it targets the tainted node and lacks a matching toleration. Confirm the event rather than inferring from the Pod phase.

### C2. Recreate with explicit toleration

Pod scheduling constraints are not freely mutable. Replace this **disposable** Pod with a corrected manifest:

```powershell
kubectl --context kind-k8s-admin-ch021 -n ch021 delete pod taint-blocked
@'
apiVersion: v1
kind: Pod
metadata:
  name: taint-blocked
  namespace: ch021
spec:
  nodeSelector:
    kubernetes.io/hostname: PLACEHOLDER
  tolerations:
    - key: training.example.com/dedicated
      operator: Equal
      value: restricted
      effect: NoSchedule
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 25m
          memory: 16Mi
'@.Replace('PLACEHOLDER', $workers[1]) | Set-Content -Encoding ascii .\taint-tolerated.yaml

kubectl --context kind-k8s-admin-ch021 apply -f .\taint-tolerated.yaml
kubectl --context kind-k8s-admin-ch021 -n ch021 wait --for=condition=Ready pod/taint-blocked --timeout=180s
kubectl --context kind-k8s-admin-ch021 -n ch021 get pod taint-blocked -o wide
```

**Expected:** Pod schedules on the tainted worker. Tolerations **permit** scheduling but do not by themselves **attract** Pods; the nodeSelector supplies the required placement.

## 12. Lab D — Resource requests exceed node allocatable

Use an intentionally impossible request without creating real memory pressure:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: resource-blocked
  namespace: ch021
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: "1000"
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\resource-blocked.yaml

kubectl --context kind-k8s-admin-ch021 apply -f .\resource-blocked.yaml
kubectl --context kind-k8s-admin-ch021 -n ch021 describe pod resource-blocked
kubectl --context kind-k8s-admin-ch021 describe node $workers[0]
```

**Expected:** Pending with `Insufficient cpu` (assuming kind nodes have fewer than 1000 allocatable CPU cores). This request reserves no actual CPU because the Pod never schedules.

**Recovery:** Delete the disposable Pod and recreate with a realistic request:

```powershell
kubectl --context kind-k8s-admin-ch021 -n ch021 delete pod resource-blocked
(Get-Content .\resource-blocked.yaml -Raw).Replace('cpu: "1000"','cpu: 25m') | Set-Content -Encoding ascii .\resource-fixed.yaml
kubectl --context kind-k8s-admin-ch021 apply -f .\resource-fixed.yaml
kubectl --context kind-k8s-admin-ch021 -n ch021 wait --for=condition=Ready pod/resource-blocked --timeout=180s
kubectl --context kind-k8s-admin-ch021 -n ch021 get pod resource-blocked -o wide
```

**Expected:** Pod schedules and becomes Ready. This tests scheduling admission, **not** a CPU stress benchmark.

## 13. Lab E — Preferred node affinity versus required affinity

Create two Pods that differ only in affinity semantics:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: preferred-affinity
  namespace: ch021
spec:
  affinity:
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          preference:
            matchExpressions:
              - key: training.example.com/nonexistent
                operator: In
                values: ["yes"]
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 25m
          memory: 16Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: required-affinity
  namespace: ch021
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: training.example.com/nonexistent
                operator: In
                values: ["yes"]
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 25m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\affinity.yaml

kubectl --context kind-k8s-admin-ch021 apply -f .\affinity.yaml
kubectl --context kind-k8s-admin-ch021 -n ch021 wait --for=condition=Ready pod/preferred-affinity --timeout=180s
kubectl --context kind-k8s-admin-ch021 -n ch021 get pods preferred-affinity required-affinity -o wide
kubectl --context kind-k8s-admin-ch021 -n ch021 describe pod required-affinity
```

**Expected:** preferred-affinity schedules despite no matching preference; required-affinity remains Pending. This demonstrates soft versus hard placement, not a deterministic node ranking.

## 14. Lab F — Scheduling gates and intentional delay

A scheduling gate deliberately holds a Pod before scheduler placement:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: gated
  namespace: ch021
spec:
  schedulingGates:
    - name: training.example.com/approval
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 25m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\gated.yaml

kubectl --context kind-k8s-admin-ch021 apply --dry-run=server -f .\gated.yaml
kubectl --context kind-k8s-admin-ch021 apply -f .\gated.yaml
kubectl --context kind-k8s-admin-ch021 -n ch021 get pod gated -o wide
kubectl --context kind-k8s-admin-ch021 -n ch021 describe pod gated
```

**Expected:** Pod remains unscheduled with a scheduling-gated condition/message, not necessarily a FailedScheduling event. To approve scheduling in this **disposable** lab:

```powershell
kubectl --context kind-k8s-admin-ch021 -n ch021 patch pod gated --type=json -p '[{"op":"remove","path":"/spec/schedulingGates"}]'
kubectl --context kind-k8s-admin-ch021 -n ch021 wait --for=condition=Ready pod/gated --timeout=180s
kubectl --context kind-k8s-admin-ch021 -n ch021 get pod gated -o wide
```

**Expected:** after removing the gate, the Pod can be scheduled. This feature requires a compatible Kubernetes server; if the API rejects the field, mark this exercise **Blocked — unsupported version** rather than claiming a scheduler defect.

## 15. Scheduler observability and diagnostics

### Essential read-only commands

```powershell
kubectl --context kind-k8s-admin-ch021 -n ch021 get pods -o wide
kubectl --context kind-k8s-admin-ch021 -n ch021 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch021 -n ch021 describe pod required-affinity
kubectl --context kind-k8s-admin-ch021 get nodes -o wide
kubectl --context kind-k8s-admin-ch021 describe nodes
kubectl --context kind-k8s-admin-ch021 get priorityclasses
```

For self-managed control planes, scheduler logs and metrics may be available from `kube-scheduler` static Pods or component endpoints, subject to access controls. Managed Kubernetes platforms may not expose control-plane logs directly; use provider-specific logging, audit trails and metrics.

### Useful metrics and signals

- Scheduling attempts, successes, failures and unschedulable Pods.
- Scheduling duration distributions (including queue and framework plugin latency where exposed).
- Pending Pod age and event reasons.
- Node allocatable versus sum of Pod requests.
- Autoscaler decisions, provisioning latency and scale-up failures.
- Node conditions, taints, volume topology and resource fragmentation.

Do not assume metric names remain identical across Kubernetes versions. Confirm the actual scheduler metrics endpoint and label schema before writing alerts.

## 16. Incident investigation decision tree

```text
Pod Pending?
   |
   +-- spec.nodeName set?
   |      |
   |      +-- YES -> kubelet/runtime/volume/image path, not initial scheduling
   |      +-- NO
   |            |
   |            +-- schedulingGates present? -> intended hold
   |            +-- FailedScheduling event?
   |                    |
   |                    +-- Insufficient cpu/memory -> requests, allocatable, quota, autoscaler
   |                    +-- selector/affinity mismatch -> labels and hard rules
   |                    +-- untolerated taint -> taints/tolerations policy
   |                    +-- volume conflict -> PVC, CSI, topology, access modes
   |                    +-- other -> inspect scheduler/profile/plugin events
   |
   +-- After correction -> confirm node assignment, Pod Ready, Service endpoints
```

### Evidence table

| Evidence | What it tells you | Pitfall |
|---|---|---|
| Pod events | Scheduler rejection reasons | Events expire; capture promptly |
| `spec.nodeName` | Whether binding occurred | Node assignment does not mean container started |
| Node allocatable | Scheduling resource budget | Not the same as capacity or live utilization |
| Pod requests | Resources reserved for scheduling | Limits and real usage differ |
| Node labels/taints | Placement eligibility | Changing labels can affect many workloads |
| Pod affinity rules | Required vs preferred placement | Soft preference is not a guarantee |
| PVC/volume topology | Storage feasibility | Requires CSI/storage context |
| Scheduler metrics/logs | Queue/plugin behavior | Access varies by platform |

## 17. Production remediation runbook

1. **Scope and safety:** Confirm cluster, namespace, workload owner, business impact, and recent change.
2. **Classify:** Is the Pod unscheduled or already assigned to a node? Inspect `spec.nodeName`.
3. **Capture:** Pod YAML (without secrets), events, requests, node allocatable, selectors, affinity, taints, PVC status.
4. **Determine constraint:** Resource shortage, placement mismatch, volume topology, gate, priority, or scheduler/plugin issue.
5. **Review change:** Prefer correcting incorrect Pod templates, adjusting planned capacity, or fixing authorized node labels/taints. Do not indiscriminately remove security/isolation constraints.
6. **Execute safely:** Apply approved change through the source of truth; account for GitOps and HPA/autoscaler ownership.
7. **Validate:** New Pod binds, starts, becomes Ready, enters expected Service endpoints and meets application SLOs.
8. **Prevent:** Add capacity forecasting, placement policy checks, admission tests, Pending-age alerts and operational runbooks.

### SRE/DBRE considerations

Stateful workloads can be blocked by PVC zone affinity, `ReadWriteOnce` attachment constraints, anti-affinity, and quorum-aware placement. For Elasticsearch/OpenSearch, Kafka and databases, reducing hard anti-affinity to force scheduling can undermine failure-domain isolation. Review data safety and topology before relaxing rules.

## 18. Cleanup and rollback

Verify the disposable cluster:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch021 get nodes
```

Remove the temporary node changes and namespace:

```powershell
kubectl --context kind-k8s-admin-ch021 label node $workers[0] training.example.com/pool-
kubectl --context kind-k8s-admin-ch021 taint nodes $workers[1] training.example.com/dedicated=restricted:NoSchedule-
kubectl --context kind-k8s-admin-ch021 delete namespace ch021
kind delete cluster --name k8s-admin-ch021
kind get clusters
Remove-Item .\kind-config.yaml, .\baseline.yaml, .\selector-blocked.yaml, .\taint-blocked.yaml, .\taint-tolerated.yaml, .\resource-blocked.yaml, .\resource-fixed.yaml, .\affinity.yaml, .\gated.yaml -ErrorAction SilentlyContinue
```

If the PowerShell session was restarted and `$workers` is missing, **do not guess node names**. Re-run the worker discovery step before cleanup. The namespace and cluster deletion permanently remove lab resources.

## 19. Acceptance checklist

- [ ] Created and verified isolated three-node kind cluster.
- [ ] Observed successful Pod scheduling and node binding.
- [ ] Reproduced nodeSelector mismatch and fixed it with a disposable node label.
- [ ] Reproduced untolerated NoSchedule taint and recovered with explicit toleration.
- [ ] Demonstrated impossible CPU request and corrected the Pod specification.
- [ ] Compared preferred and required node affinity outcomes.
- [ ] Demonstrated scheduling gate and removal, or recorded compatibility block.
- [ ] Distinguished scheduler rejection from kubelet/container startup failure.
- [ ] Collected sanitized events, node allocatable and Pod placement evidence.
- [ ] Removed disposable node mutations, namespace and cluster.

## 20. Knowledge check

1. Which component binds a Pod to a node, and which starts its containers?
2. What is the difference between Filter and Score?
3. Why can a node with low observed CPU still reject a Pod for insufficient CPU?
4. What is the difference between required and preferred node affinity?
5. Why does a toleration not force a Pod onto a tainted node?
6. What does a scheduling gate do?
7. When might preemption fail to resolve an unschedulable Pod?
8. Why is `spec.nodeName` useful in incident triage?
9. How can PVC topology make a Pod Pending?
10. What should be validated beyond a successful scheduling event?

## 21. Status and next chapter

**Draft published.** Labs and production claims have not been runtime-verified. Mark **Lab Validated** only after observed acceptance evidence and **Complete** after technical review.

**Next:** Chapter 022 — Node Selectors and Affinity Rules.
