# Chapter 023 — Taints, Tolerations and Topology Spread

**Track:** Kubernetes Administration · **Part 05:** Scheduling and Resource Management · **Status:** Draft — hands-on lab validation and technical review pending

## 1. Scenario and learning outcomes

Your platform team operates general-purpose, batch and critical-service node pools across multiple failure domains. A rollout leaves Pods Pending because of untolerated taints, while another service places too many replicas on the same node. You need to restore scheduling without weakening isolation or increasing failure blast radius.

By the end of this chapter, you will:

1. Explain the three taint effects: `NoSchedule`, `PreferNoSchedule`, and `NoExecute`.
2. Distinguish taints (node repulsion) from tolerations (permission) and affinity (placement).
3. Use `Equal` and `Exists` toleration operators and `tolerationSeconds` safely.
4. Explain default node-condition taints and their operational consequences.
5. Configure topology spread constraints with `maxSkew`, `topologyKey`, `whenUnsatisfiable`, and eligibility controls.
6. Diagnose hard topology-spread failures, zone/node skew, and capacity constraints.
7. Complete seven reproducible labs on a disposable multi-node kind cluster and capture incident evidence.

## 2. Mental model

```text
New Pod
   |
   v
Node candidate filtering
   +-- Node labels / required affinity
   +-- Node taints vs Pod tolerations
   +-- Resource requests and allocatable
   +-- Required Pod affinity/anti-affinity
   +-- Storage and topology constraints
   +-- DoNotSchedule topology spread
   |
   v
Score feasible nodes
   +-- Soft affinity
   +-- PreferNoSchedule taints
   +-- ScheduleAnyway topology spread
   +-- Other scheduler scoring plugins
   |
   v
Bind Pod to selected node -> kubelet starts containers
```

Taints and tolerations are **not** a node selector. A Pod tolerating a taint can still be placed on another eligible node unless required node affinity or a selector constrains it. Tolerations also do not override CPU/memory, storage, or required affinity constraints.

## 3. Taints: node-level repulsion

Taint syntax:

```bash
kubectl taint nodes NODE key=value:NoSchedule
kubectl taint nodes NODE key=value:PreferNoSchedule
kubectl taint nodes NODE key=value:NoExecute
kubectl taint nodes NODE key=value:NoSchedule-
```

The last command removes the matching taint. The precise key/value/effect matter: do not remove broad sets of production taints during incident response.

| Effect | New Pod scheduling | Already-running Pods | Operational use |
|---|---|---|---|
| `NoSchedule` | Rejects Pods without matching toleration | Does not evict them by itself | Dedicated or restricted node pools |
| `PreferNoSchedule` | Scheduler attempts to avoid node | Does not evict them by itself | Soft preference for keeping capacity free |
| `NoExecute` | Rejects Pods without matching toleration | Evicts Pods without matching toleration; finite toleration may delay eviction | Node condition or planned isolation |

Taint-based eviction is subject to controller behavior and cluster configuration; do not assume instantaneous termination.

## 4. Toleration anatomy

```yaml
tolerations:
  - key: workload.example.com/dedicated
    operator: Equal
    value: analytics
    effect: NoSchedule
  - key: node.kubernetes.io/not-ready
    operator: Exists
    effect: NoExecute
    tolerationSeconds: 30
```

- `Equal` matches key, value, and optionally effect.
- `Exists` matches the key regardless of value; omitting key with `Exists` can match all keys and should be reviewed carefully.
- An omitted `effect` can match any effect for the specified key/operator.
- `tolerationSeconds` applies to `NoExecute` and controls how long a Pod may remain bound after the matching taint appears. It does not delay initial scheduling.
- Multiple taints are evaluated together. A Pod must tolerate every relevant hard taint to remain eligible.

### Security caution

A broad toleration such as `operator: Exists` without a key can let a Pod be considered for nodes intended for special workloads. Restrict tolerations to known keys/effects and combine with explicit node placement when necessary.

## 5. Node-condition taints

Kubernetes uses taints to represent some node conditions. Common examples include:

- `node.kubernetes.io/not-ready`
- `node.kubernetes.io/unreachable`
- `node.kubernetes.io/memory-pressure`
- `node.kubernetes.io/disk-pressure`
- `node.kubernetes.io/pid-pressure`
- `node.kubernetes.io/unschedulable`

Not every condition produces the same taint effect or lifecycle behavior. Normal Pods may receive default `NoExecute` tolerations for `not-ready` and `unreachable` through admission, typically with a bounded period unless explicitly overridden. DaemonSet Pods have additional tolerations depending on their configuration and Kubernetes version.

**Do not remove a node-condition taint to conceal an unhealthy node.** Diagnose node pressure, kubelet connectivity, disk usage and runtime health first.

## 6. Topology spread constraints

Topology spread lets you distribute matching Pods across domains such as hostnames and availability zones.

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: api
```

A topology domain is the set of nodes sharing the same value for the specified `topologyKey`. `maxSkew` bounds the difference in matching Pod counts across eligible domains, according to the scheduler's skew calculation.

### Key fields

| Field | Meaning | Notes |
|---|---|---|
| `maxSkew` | Allowed skew relative to the global minimum | Must be positive; behavior depends on policy |
| `topologyKey` | Node label defining domains | All intended nodes should have the label |
| `whenUnsatisfiable` | `DoNotSchedule` or `ScheduleAnyway` | Hard filtering versus soft scoring |
| `labelSelector` | Which existing Pods count | Must match the workload's own Pod labels |
| `matchLabelKeys` | Additional keys from incoming Pod labels | Useful for revision-aware spread on supported versions |
| `minDomains` | Minimum eligible domains for skew calculation | Relevant with `DoNotSchedule`; compatibility varies |
| `nodeAffinityPolicy` | Whether to honor/ignore incoming Pod's node affinity in eligibility | Verify supported API behavior |
| `nodeTaintsPolicy` | Whether to honor/ignore taints when determining eligible domains | Verify supported API behavior |

### DoNotSchedule versus ScheduleAnyway

- `DoNotSchedule`: a candidate placement violating maxSkew is rejected. Pods may remain Pending.
- `ScheduleAnyway`: scheduler prefers nodes that reduce skew but does not make maxSkew a hard admission limit.

With `ScheduleAnyway`, skew is a scoring preference, not a strict invariant. The actual node choice also depends on other scoring plugins and node feasibility.

### Multiple constraints

Multiple topology spread constraints are combined; a candidate node must satisfy all hard constraints. For example, spreading by both `zone` and `hostname` can provide zone-level and node-level balance but may reduce placement options.

## 7. How skew is calculated

For `DoNotSchedule`, consider three eligible hostname domains with matching Pod counts:

| Node/domain | Existing matching Pods | Candidate Pod makes count | Difference from global minimum (0) |
|---|---:|---:|---:|
| worker-a | 2 | 3 | 3 |
| worker-b | 1 | 2 | 2 |
| worker-c | 0 | 1 | 1 |

With `maxSkew: 1`, only worker-c is eligible for the new Pod in this simplified example. The global minimum depends on eligible domains, `minDomains`, and node affinity/taint eligibility policies; it is not always the count on the least-loaded physical node in the entire cluster.

**Operational implication:** A node can have spare CPU yet reject a Pod because placing it there would violate a hard topology rule.

## 8. Combining taints, affinity and topology spread

Consider a critical service that must run only on `critical` pool nodes, tolerate that pool's dedicated taint, and spread across zones.

```yaml
spec:
  nodeSelector:
    workload.example.com/pool: critical
  tolerations:
    - key: workload.example.com/dedicated
      operator: Equal
      value: critical
      effect: NoSchedule
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: critical-api
  containers:
    - name: api
      image: nginx:stable
      resources:
        requests:
          cpu: 100m
          memory: 128Mi
```

This works only if enough eligible nodes and topology domains exist. The toleration allows use of dedicated nodes; the selector requires the pool; the spread rule distributes matching replicas when feasible. Check that your cluster exposes real zone labels. **Do not fabricate availability-zone labels and claim production zone resilience.**

## 9. Production workload tradeoffs

| Workload | Typical approach | Guardrail |
|---|---|---|
| Stateless API | Soft zone spread and hard/soft hostname spread as availability requires | Ensure enough nodes for desired replicas |
| Kafka brokers | Dedicated pool taints plus zone/rack-aware spread | Align with Kafka replication and rack awareness |
| MongoDB replica set | Spread voting members and protect storage/quorum | Operator-specific policies take precedence |
| Elasticsearch/OpenSearch | Node-pool isolation and data-node spread | Align with shard allocation awareness |
| GPU model serving | Tolerate GPU taints and require GPU node affinity/resources | Check driver, runtime and accelerator resources |
| Telemetry DaemonSet | Target eligible nodes with controlled tolerations | Avoid blanket access to every restricted node |
| Batch processing | Prefer batch nodes, allow flexible fallback where approved | Do not consume critical capacity unintentionally |

A hard rule that leaves Pods Pending can be preferable to unsafe colocation for quorum-sensitive systems. For customer-facing stateless services, an overly strict rule can worsen availability during node loss. Choose based on failure consequences, not a universal default.

## 10. Lab environment and safety

**Requirements:** Windows PowerShell, Docker Desktop, kind, kubectl. The cluster contains one control-plane node and three workers.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch023 | Out-Null
Set-Location .\k8s-ch023
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-config.yaml
kind create cluster --name k8s-admin-ch023 --config .\kind-config.yaml --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch023 get nodes -o wide
```

**Expected:** `kind-k8s-admin-ch023` context and four Ready nodes. If Docker capacity cannot support the lab, stop and record Blocked; do not use a shared cluster.

```powershell
kubectl --context kind-k8s-admin-ch023 create namespace ch023
$workers = @((kubectl --context kind-k8s-admin-ch023 get nodes -l '!node-role.kubernetes.io/control-plane' -o json | ConvertFrom-Json).items | ForEach-Object { $_.metadata.name })
if ($workers.Count -ne 3) { throw "Expected three worker nodes" }
foreach ($node in $workers) {
  kubectl --context kind-k8s-admin-ch023 label node $node workload.example.com/pool=training
}
kubectl --context kind-k8s-admin-ch023 get nodes --show-labels
```

**Safety:** All mutations below use an explicit disposable context. Never copy the node-taint or deletion commands to production without approval and impact review.

## 11. Lab A — NoSchedule taint blocks a Pod

Taint one worker and create a Pod required to run there:

```powershell
kubectl --context kind-k8s-admin-ch023 taint node $workers[0] workload.example.com/dedicated=training:NoSchedule
@'
apiVersion: v1
kind: Pod
metadata:
  name: taint-blocked
  namespace: ch023
spec:
  nodeSelector:
    kubernetes.io/hostname: PLACEHOLDER
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 20m
          memory: 16Mi
'@.Replace('PLACEHOLDER', $workers[0]) | Set-Content -Encoding ascii .\taint-blocked.yaml

kubectl --context kind-k8s-admin-ch023 apply -f .\taint-blocked.yaml
kubectl --context kind-k8s-admin-ch023 -n ch023 get pod taint-blocked -o wide
kubectl --context kind-k8s-admin-ch023 -n ch023 describe pod taint-blocked
```

**Expected:** Pending, empty nodeName and `FailedScheduling` event indicating an untolerated taint. Other workers are excluded by the required hostname selector.

## 12. Lab B — Matching toleration restores eligibility

Delete the disposable Pod and recreate with a narrow toleration:

```powershell
kubectl --context kind-k8s-admin-ch023 -n ch023 delete pod taint-blocked
@'
apiVersion: v1
kind: Pod
metadata:
  name: taint-blocked
  namespace: ch023
spec:
  nodeSelector:
    kubernetes.io/hostname: PLACEHOLDER
  tolerations:
    - key: workload.example.com/dedicated
      operator: Equal
      value: training
      effect: NoSchedule
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 20m
          memory: 16Mi
'@.Replace('PLACEHOLDER', $workers[0]) | Set-Content -Encoding ascii .\taint-tolerated.yaml

kubectl --context kind-k8s-admin-ch023 apply --dry-run=server -f .\taint-tolerated.yaml
kubectl --context kind-k8s-admin-ch023 apply -f .\taint-tolerated.yaml
kubectl --context kind-k8s-admin-ch023 -n ch023 wait --for=condition=Ready pod/taint-blocked --timeout=180s
kubectl --context kind-k8s-admin-ch023 -n ch023 get pod taint-blocked -o wide
```

**Expected:** Pod schedules to `$workers[0]`. The selector determines the target node; the toleration only removes the taint exclusion.

## 13. Lab C — PreferNoSchedule is a soft preference

Apply a soft taint to the second worker and create a Pod required to use that worker:

```powershell
kubectl --context kind-k8s-admin-ch023 taint node $workers[1] workload.example.com/prefer-avoid=true:PreferNoSchedule
@'
apiVersion: v1
kind: Pod
metadata:
  name: soft-taint
  namespace: ch023
spec:
  nodeSelector:
    kubernetes.io/hostname: PLACEHOLDER
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 20m
          memory: 16Mi
'@.Replace('PLACEHOLDER', $workers[1]) | Set-Content -Encoding ascii .\soft-taint.yaml

kubectl --context kind-k8s-admin-ch023 apply -f .\soft-taint.yaml
kubectl --context kind-k8s-admin-ch023 -n ch023 wait --for=condition=Ready pod/soft-taint --timeout=180s
kubectl --context kind-k8s-admin-ch023 -n ch023 get pod soft-taint -o wide
```

**Expected:** Pod can schedule on the softly tainted worker because `PreferNoSchedule` is not a hard exclusion. This does not imply the scheduler would prefer that node without the hostname selector.

## 14. Lab D — NoExecute eviction and tolerationSeconds

This exercise changes only a disposable worker. First create a Pod pinned to `$workers[2]` with a finite `NoExecute` toleration:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: finite-toleration
  namespace: ch023
spec:
  nodeSelector:
    kubernetes.io/hostname: PLACEHOLDER
  tolerations:
    - key: workload.example.com/maintenance
      operator: Equal
      value: planned
      effect: NoExecute
      tolerationSeconds: 20
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 20m
          memory: 16Mi
'@.Replace('PLACEHOLDER', $workers[2]) | Set-Content -Encoding ascii .\finite-toleration.yaml

kubectl --context kind-k8s-admin-ch023 apply -f .\finite-toleration.yaml
kubectl --context kind-k8s-admin-ch023 -n ch023 wait --for=condition=Ready pod/finite-toleration --timeout=180s
kubectl --context kind-k8s-admin-ch023 taint node $workers[2] workload.example.com/maintenance=planned:NoExecute
kubectl --context kind-k8s-admin-ch023 -n ch023 get pod finite-toleration -o wide
kubectl --context kind-k8s-admin-ch023 -n ch023 get events --sort-by=.lastTimestamp
```

**Expected:** the Pod is eligible to remain for roughly the configured toleration period, after which taint-based eviction should occur. Controller processing is asynchronous; do not claim exact 20-second termination timing.

Remove the taint immediately after observing the behavior:

```powershell
kubectl --context kind-k8s-admin-ch023 taint node $workers[2] workload.example.com/maintenance=planned:NoExecute-
```

**Important:** `NoExecute` can evict other Pods on that worker if they do not tolerate the taint. Only use it on this disposable cluster.

## 15. Lab E — Hard hostname topology spread

Create a Deployment with three replicas and `DoNotSchedule` skew 1, constrained to labeled workers:

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spread-hard
  namespace: ch023
spec:
  replicas: 3
  selector:
    matchLabels:
      app: spread-hard
  template:
    metadata:
      labels:
        app: spread-hard
    spec:
      nodeSelector:
        workload.example.com/pool: training
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: spread-hard
      containers:
        - name: nginx
          image: nginx:stable
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
'@ | Set-Content -Encoding ascii .\spread-hard.yaml

kubectl --context kind-k8s-admin-ch023 apply -f .\spread-hard.yaml
kubectl --context kind-k8s-admin-ch023 -n ch023 rollout status deployment/spread-hard --timeout=180s
kubectl --context kind-k8s-admin-ch023 -n ch023 get pods -l app=spread-hard -o wide
```

**Expected:** three replicas become Ready, normally one on each worker. Note that the taint on `$workers[0]` remains; it is **not** tolerated by these Pods, so that worker is ineligible. With two eligible workers and three replicas, a 2/1 split is allowed by maxSkew 1. Record actual distribution rather than assuming one per node.

For a clean three-domain experiment, remove the Lab A taint and restart the Deployment:

```powershell
kubectl --context kind-k8s-admin-ch023 taint node $workers[0] workload.example.com/dedicated=training:NoSchedule-
kubectl --context kind-k8s-admin-ch023 -n ch023 rollout restart deployment/spread-hard
kubectl --context kind-k8s-admin-ch023 -n ch023 rollout status deployment/spread-hard --timeout=180s
kubectl --context kind-k8s-admin-ch023 -n ch023 get pods -l app=spread-hard -o wide
```

**Expected:** three eligible worker domains. A one-per-node distribution is expected at steady state if no other constraints interfere, but check actual scheduling events.

## 16. Lab F — Hard topology spread under node loss of eligibility

For a deterministic blocked case, use two eligible worker domains and a stricter topology configuration that requires at least three domains. This exercise relies on `minDomains` support.

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spread-min-domains
  namespace: ch023
spec:
  replicas: 3
  selector:
    matchLabels:
      app: spread-min-domains
  template:
    metadata:
      labels:
        app: spread-min-domains
    spec:
      nodeSelector:
        workload.example.com/pool: training
      topologySpreadConstraints:
        - maxSkew: 1
          minDomains: 3
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: spread-min-domains
      containers:
        - name: nginx
          image: nginx:stable
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
'@ | Set-Content -Encoding ascii .\spread-min-domains.yaml

kubectl --context kind-k8s-admin-ch023 apply --dry-run=server -f .\spread-min-domains.yaml
kubectl --context kind-k8s-admin-ch023 apply -f .\spread-min-domains.yaml
kubectl --context kind-k8s-admin-ch023 -n ch023 rollout status deployment/spread-min-domains --timeout=180s
```

**Expected:** with three eligible domains, three replicas become Ready.

Now remove the training pool label from one worker and restart the Deployment to create new Pods under the reduced eligible-domain set:

```powershell
kubectl --context kind-k8s-admin-ch023 label node $workers[2] workload.example.com/pool-
kubectl --context kind-k8s-admin-ch023 -n ch023 rollout restart deployment/spread-min-domains
kubectl --context kind-k8s-admin-ch023 -n ch023 get pods -l app=spread-min-domains -o wide
kubectl --context kind-k8s-admin-ch023 -n ch023 get events --sort-by=.lastTimestamp
```

**Expected:** scheduling may stall when a candidate would exceed maxSkew relative to the global minimum of zero because fewer than three domains are eligible. Existing Pods can remain on the relabeled node under `IgnoredDuringExecution`, and rolling-update surge behavior affects the exact observed counts. Do not assert a specific number of Pending Pods without observing it.

Restore the label:

```powershell
kubectl --context kind-k8s-admin-ch023 label node $workers[2] workload.example.com/pool=training
kubectl --context kind-k8s-admin-ch023 -n ch023 rollout status deployment/spread-min-domains --timeout=180s
```

**Expected:** the Deployment completes after sufficient eligible topology domains are restored.

**Compatibility:** If `minDomains` is rejected by server-side dry-run, mark this lab Blocked due to cluster API compatibility and skip the mutation. Do not weaken production policies to make a demonstration pass.

## 17. Lab G — Soft topology spread and practical tradeoffs

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spread-soft
  namespace: ch023
spec:
  replicas: 4
  selector:
    matchLabels:
      app: spread-soft
  template:
    metadata:
      labels:
        app: spread-soft
    spec:
      nodeSelector:
        workload.example.com/pool: training
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: spread-soft
      containers:
        - name: nginx
          image: nginx:stable
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
'@ | Set-Content -Encoding ascii .\spread-soft.yaml

kubectl --context kind-k8s-admin-ch023 apply -f .\spread-soft.yaml
kubectl --context kind-k8s-admin-ch023 -n ch023 rollout status deployment/spread-soft --timeout=180s
kubectl --context kind-k8s-admin-ch023 -n ch023 get pods -l app=spread-soft -o wide
```

**Expected:** four replicas schedule if capacity permits. The scheduler prefers lower skew but may choose a nonideal distribution. This is a soft scoring policy, not a hard 2/1/1 guarantee.

## 18. Incident investigation and troubleshooting

| Symptom | Likely reason | Evidence | Safe action |
|---|---|---|---|
| Pod Pending with untolerated taint | No matching toleration | `describe pod`, node taints | Review node pool and toleration |
| Pod lands on unexpected node | Toleration without selector | Pod spec and node labels | Add approved required affinity |
| Pod evicted after node taint | `NoExecute` | Events, tolerationSeconds | Diagnose taint source and workload policy |
| Hard spread leaves Pods Pending | Insufficient eligible domains or skew | Pod events, topology labels | Restore domains/capacity or review policy |
| Soft spread uneven | Scoring and competing constraints | Pod node placement | Inspect scheduler preferences and feasibility |
| Zone spread not working | Missing/mismatched zone labels | Node labels | Correct infrastructure label contract |
| Workload cannot use GPU pool | GPU taint or resource mismatch | Events, GPU allocatable | Fix resource requests, toleration and node affinity |
| Node condition taint present | Node unhealthy | Node conditions and kubelet events | Remediate node health, not just taint |

### Read-only evidence commands

```powershell
kubectl --context kind-k8s-admin-ch023 get nodes -o wide
kubectl --context kind-k8s-admin-ch023 get nodes --show-labels
kubectl --context kind-k8s-admin-ch023 describe nodes
kubectl --context kind-k8s-admin-ch023 -n ch023 get pods -o wide
kubectl --context kind-k8s-admin-ch023 -n ch023 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch023 -n ch023 describe deployment spread-min-domains
kubectl --context kind-k8s-admin-ch023 -n ch023 get deployments
```

## 19. Production SRE runbook

### Pre-change review

1. Identify node pool ownership, workloads, SLOs, capacity and topology.
2. Inspect taints, tolerations, selectors, affinity and topology spread together.
3. Confirm eligible domain count supports the desired replica count and maxSkew.
4. Assess stateful replication, quorum and PVC zone constraints.
5. Obtain approval for any `NoExecute` taint or broad toleration.
6. Record rollback commands and the source of truth.

### Incident response

1. Confirm the Pod is unscheduled (`spec.nodeName` empty) versus bound but unready.
2. Capture FailedScheduling events, node taints, Pod tolerations and topology rules.
3. Calculate eligible nodes/domains after all hard constraints.
4. Decide whether capacity, labels, or workload policy is incorrect.
5. Apply the smallest approved correction; avoid blindly removing isolation controls.
6. Watch scheduling, readiness, EndpointSlices and application SLOs.
7. Record before/after evidence and root cause.

### Prevention

- Standardize node-pool taints and corresponding workload tolerations.
- Alert on Pending age and scheduling failures.
- Test topology constraints with reduced eligible-domain scenarios.
- Use capacity planning for surge Pods and multi-zone resilience.
- Review node replacement/autoscaler behavior and label contracts.
- Coordinate with application operators for data services.

## 20. Cleanup and rollback

Verify context and worker variables before destructive operations:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch023 get nodes
$workers
```

If `$workers` was lost, rerun the worker discovery from Section 10; do not guess names.

```powershell
kubectl --context kind-k8s-admin-ch023 taint node $workers[0] workload.example.com/dedicated=training:NoSchedule- 2>$null
kubectl --context kind-k8s-admin-ch023 taint node $workers[1] workload.example.com/prefer-avoid=true:PreferNoSchedule- 2>$null
kubectl --context kind-k8s-admin-ch023 taint node $workers[2] workload.example.com/maintenance=planned:NoExecute- 2>$null
foreach ($node in $workers) {
  kubectl --context kind-k8s-admin-ch023 label node $node workload.example.com/pool- 2>$null
}
kubectl --context kind-k8s-admin-ch023 delete namespace ch023
kind delete cluster --name k8s-admin-ch023
kind get clusters
Remove-Item .\kind-config.yaml, .\taint-blocked.yaml, .\taint-tolerated.yaml, .\soft-taint.yaml, .\finite-toleration.yaml, .\spread-hard.yaml, .\spread-min-domains.yaml, .\spread-soft.yaml -ErrorAction SilentlyContinue
```

**Destructive warning:** These commands are for the disposable cluster only. Do not delete shared namespaces or alter production node taints as part of this lab.

## 21. Acceptance checklist

- [ ] Four-node kind cluster created and exact context verified.
- [ ] Three worker nodes labeled for training.
- [ ] `NoSchedule` taint blocked a Pod without toleration.
- [ ] Narrow toleration restored scheduling eligibility.
- [ ] `PreferNoSchedule` did not hard-block placement.
- [ ] `NoExecute` finite toleration and eventual eviction observed.
- [ ] Hard topology spread evaluated across eligible hostnames.
- [ ] `minDomains` scenario tested or compatibility block recorded.
- [ ] Soft topology spread tested without assuming guaranteed distribution.
- [ ] Captured node taints, events, placement and readiness evidence.
- [ ] Restored node labels/taints and removed disposable resources.

## 22. Knowledge check

1. Why does a toleration not guarantee placement on a dedicated node?
2. How do `NoSchedule`, `PreferNoSchedule` and `NoExecute` differ?
3. What does `tolerationSeconds` control?
4. Why should you not remove a node-pressure taint to fix scheduling?
5. What does `maxSkew` mean for hostname spread?
6. How does `ScheduleAnyway` differ from `DoNotSchedule`?
7. How can `minDomains` affect skew when a zone becomes ineligible?
8. Why might an existing Pod remain on a relabeled node?
9. What must be considered when combining taints, affinity and PVC topology?
10. What evidence proves a topology scheduling incident has recovered?

## 23. Status and next chapter

**Draft published.** Labs have not been executed or independently validated. Mark **Lab Validated** only after collecting acceptance evidence and **Complete** after technical review.

**Next:** Chapter 024 — Resource Requests, Limits, QoS and Quotas.
