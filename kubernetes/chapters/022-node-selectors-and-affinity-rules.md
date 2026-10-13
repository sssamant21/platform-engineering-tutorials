# Chapter 022 — Node Selectors and Affinity Rules

**Track:** Kubernetes Administration · **Part 05:** Scheduling and Resource Management · **Status:** Draft — hands-on validation and technical review pending

## 1. Objectives and scenario

A platform team needs to place latency-sensitive application Pods on a dedicated node pool, keep two replicas away from the same failure domain, and colocate a helper with a service when feasible. An incident occurs because a newly introduced required affinity rule cannot match any node.

This chapter teaches you to:

1. Distinguish `nodeName`, `nodeSelector`, required/preferred node affinity, Pod affinity and anti-affinity.
2. Explain scheduling-time versus execution-time behavior and the `IgnoredDuringExecution` semantics.
3. Understand label governance, node trust boundaries, topology domains and namespace selectors.
4. Design hard requirements and soft preferences with an availability-first mindset.
5. Diagnose unschedulable Pods and affinity deadlocks using events and node labels.
6. Apply placement rules safely to Deployments and stateful workloads.
7. Run seven isolated PowerShell/kind labs and produce an SRE acceptance report.

## 2. Placement mechanisms at a glance

| Mechanism | Hard or soft? | Applies to | Primary use |
|---|---|---|---|
| `spec.nodeName` | Direct assignment, bypasses normal scheduler selection | Pod | Rare low-level troubleshooting; avoid in application manifests |
| `nodeSelector` | Hard | Node labels | Simple pool selection |
| Required node affinity | Hard | Node labels/fields supported by node affinity | Rich node selection expressions |
| Preferred node affinity | Soft | Node labels | Placement optimization |
| Required Pod affinity | Hard | Labels of existing Pods and topology | Mandatory colocation |
| Preferred Pod affinity | Soft | Labels of existing Pods and topology | Favor colocation |
| Required Pod anti-affinity | Hard | Labels of existing Pods and topology | Failure-domain separation |
| Preferred Pod anti-affinity | Soft | Labels of existing Pods and topology | Favor spreading |

**Key distinction:** `nodeSelector` and required node affinity must both be satisfied when both are specified. A preference does not override a requirement. A toleration allows a Pod to be considered for a tainted node; it does not select that node.

## 3. Node labels and label governance

Node labels describe scheduling-relevant attributes such as topology, architecture, node pool or hardware capabilities.

```powershell
kubectl get nodes --show-labels
kubectl get node NODE_NAME -o jsonpath='{.metadata.labels}'
```

Common topology keys include:

- `kubernetes.io/hostname` — node identity.
- `topology.kubernetes.io/zone` — zone when exposed by the platform.
- `topology.kubernetes.io/region` — region when exposed by the platform.
- Provider-specific node-pool labels — verify rather than assume the key exists.

### Security boundary

Do not assume arbitrary node labels are trustworthy for security isolation. If a workload must be restricted to specially authorized nodes, use an admission policy and labels protected by the NodeRestriction admission plugin, where appropriately configured. Kubernetes supports the `node-restriction.kubernetes.io/` protected-label pattern; validate the exact cluster authorization/admission setup before treating labels as security controls.

Labels also have operational consequences: changing a node label can make **new** Pods ineligible while existing Pods using `IgnoredDuringExecution` typically continue running.

## 4. nodeSelector: simple required placement

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      nodeSelector:
        workload.example.com/pool: general
      containers:
        - name: api
          image: nginx:stable
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
```

The scheduler selects only nodes whose labels match every key/value in `nodeSelector`. If no node matches, Pods remain Pending with a `FailedScheduling` event. `nodeSelector` is simple but does not express OR alternatives or preferences.

## 5. Node affinity: richer required and preferred rules

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: workload.example.com/pool
              operator: In
              values: ["general", "compute"]
        - matchExpressions:
            - key: workload.example.com/pool
              operator: In
              values: ["gpu"]
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 80
        preference:
          matchExpressions:
            - key: workload.example.com/cost
              operator: In
              values: ["low"]
```

Within a `nodeSelectorTerm`, requirements are ANDed; across `nodeSelectorTerms`, terms are ORed. The example allows `general`, `compute`, or `gpu` pools and prefers low-cost nodes. Multiple preferred terms contribute weights to scoring, alongside other scheduler plugins; they do not guarantee a specific node.

### Supported expression operators

| Operator | Meaning |
|---|---|
| `In` | Label value belongs to listed values |
| `NotIn` | Label value is not in listed values |
| `Exists` | Label key is present |
| `DoesNotExist` | Label key is absent |
| `Gt` / `Lt` | Numeric comparison against an integer-valued label |

`NotIn` and `DoesNotExist` can express exclusion, but use taints for stronger node-pool repulsion when appropriate.

### IgnoredDuringExecution

Required node affinity is enforced when scheduling. With `IgnoredDuringExecution`, removing the matching node label later does **not** automatically evict an already-running Pod. It affects future placement and replacements.

## 6. Pod affinity and anti-affinity

Pod affinity/anti-affinity evaluate labels of **other Pods** within a topology domain. A topology domain is defined by a label key on nodes, such as `kubernetes.io/hostname` or `topology.kubernetes.io/zone`.

### Prefer colocation with an existing backend

```yaml
affinity:
  podAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app: backend
          topologyKey: kubernetes.io/hostname
```

This favors nodes hosting a matching backend Pod. It does not require colocation.

### Require separation between replicas

```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: critical-api
        topologyKey: kubernetes.io/hostname
```

This prevents two matching Pods from being scheduled onto the same hostname topology domain, **provided sufficient eligible nodes exist**. A three-replica Deployment on two eligible nodes will have at least one Pending Pod. This is a deliberate tradeoff, not a scheduler malfunction.

### Namespace scope

Pod affinity terms can use `namespaces` and `namespaceSelector`. If neither is specified, matching is limited to the incoming Pod's namespace. Cross-namespace affinity needs explicit review because another team's Pod labels can influence placement. An empty namespace selector has specific broad-match semantics; test the desired scope before production use.

### Self-affinity bootstrap and deadlocks

Required Pod affinity can create bootstrap problems when no matching Pod exists. The scheduler has special handling for certain self-affinity cases, but complex combinations can still prevent scheduling. Prefer a soft rule unless colocation is genuinely mandatory.

## 7. Topology spread versus Pod anti-affinity

Pod anti-affinity is useful for strict separation. `topologySpreadConstraints` offer more explicit control over balancing across zones or nodes, including skew and behavior when constraints cannot be met. Chapter 023 covers topology spread in depth.

**Production decision:** Use hard anti-affinity only when violating the placement rule is worse than leaving a Pod Pending. For many APIs, preferred anti-affinity plus topology spread is more resilient under node failures or reduced capacity.

## 8. Production use cases

| Workload | Example placement | Caution |
|---|---|---|
| Stateless API | Preferred anti-affinity across nodes | Preserve availability during node maintenance |
| Kafka brokers | Required separation by hostname/zone when capacity allows | Coordinate with broker rack awareness and replication |
| MongoDB replica set | Spread voting members across failure domains | Operator and quorum semantics take precedence |
| Elasticsearch data nodes | Separate shard copies and nodes across zones | Shard allocation awareness must align with Kubernetes |
| GPU inference | Required node affinity to GPU pool | Also request GPU resources and match driver/runtime |
| Monitoring agents | DaemonSet with eligibility rules | Avoid blind toleration of all taints |
| Low-priority batch | Prefer lower-cost pool | May need explicit capacity and priority policies |

Do not relax hard placement constraints for databases without reviewing data replication, storage topology and quorum.

## 9. Lab prerequisites and isolation

**Environment:** Windows PowerShell, Docker Desktop, kind, kubectl. Use a three-node kind cluster with two workers.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch022 | Out-Null
Set-Location .\k8s-ch022
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-config.yaml
kind create cluster --name k8s-admin-ch022 --config .\kind-config.yaml --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch022 get nodes -o wide
```

**Stop:** Do not continue if the current context differs from `kind-k8s-admin-ch022`, or the cluster is not disposable. All writes below specify that context.

```powershell
kubectl --context kind-k8s-admin-ch022 create namespace ch022
$workers = @((kubectl --context kind-k8s-admin-ch022 get nodes -l '!node-role.kubernetes.io/control-plane' -o json | ConvertFrom-Json).items | ForEach-Object { $_.metadata.name })
if ($workers.Count -ne 2) { throw "Expected exactly two workers" }
kubectl --context kind-k8s-admin-ch022 label node $workers[0] workload.example.com/pool=general workload.example.com/cost=low
kubectl --context kind-k8s-admin-ch022 label node $workers[1] workload.example.com/pool=compute workload.example.com/cost=high
kubectl --context kind-k8s-admin-ch022 get nodes --show-labels
```

**Expected:** two Ready workers with distinct pool and cost labels. Preserve `$workers` in the same PowerShell session.

## 10. Lab A — nodeSelector successful placement

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: selector-ok
  namespace: ch022
spec:
  nodeSelector:
    workload.example.com/pool: general
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 20m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\selector-ok.yaml

kubectl --context kind-k8s-admin-ch022 apply --dry-run=server -f .\selector-ok.yaml
kubectl --context kind-k8s-admin-ch022 apply -f .\selector-ok.yaml
kubectl --context kind-k8s-admin-ch022 -n ch022 wait --for=condition=Ready pod/selector-ok --timeout=180s
kubectl --context kind-k8s-admin-ch022 -n ch022 get pod selector-ok -o wide
```

**Expected:** Pod runs on `$workers[0]`. Record its assigned node and UID.

## 11. Lab B — Diagnose and recover an impossible selector

```powershell
(Get-Content .\selector-ok.yaml -Raw).Replace('selector-ok','selector-blocked').Replace('pool: general','pool: nonexistent') | Set-Content -Encoding ascii .\selector-blocked.yaml
kubectl --context kind-k8s-admin-ch022 apply -f .\selector-blocked.yaml
kubectl --context kind-k8s-admin-ch022 -n ch022 describe pod selector-blocked
kubectl --context kind-k8s-admin-ch022 -n ch022 get pod selector-blocked -o wide
```

**Expected:** Pending, empty nodeName, and FailedScheduling due to label mismatch.

For recovery, fix the **Pod template** rather than weakening production node labels. A standalone Pod's node selector cannot generally be changed in place:

```powershell
kubectl --context kind-k8s-admin-ch022 -n ch022 delete pod selector-blocked
(Get-Content .\selector-blocked.yaml -Raw).Replace('pool: nonexistent','pool: compute') | Set-Content -Encoding ascii .\selector-fixed.yaml
kubectl --context kind-k8s-admin-ch022 apply -f .\selector-fixed.yaml
kubectl --context kind-k8s-admin-ch022 -n ch022 wait --for=condition=Ready pod/selector-blocked --timeout=180s
kubectl --context kind-k8s-admin-ch022 -n ch022 get pod selector-blocked -o wide
```

**Expected:** Pod schedules on `$workers[1]`.

## 12. Lab C — Required node affinity with OR and AND

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: required-node
  namespace: ch022
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: workload.example.com/pool
                operator: In
                values: ["general"]
              - key: workload.example.com/cost
                operator: In
                values: ["low"]
          - matchExpressions:
              - key: workload.example.com/pool
                operator: In
                values: ["compute"]
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 20m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\required-node.yaml

kubectl --context kind-k8s-admin-ch022 apply -f .\required-node.yaml
kubectl --context kind-k8s-admin-ch022 -n ch022 wait --for=condition=Ready pod/required-node --timeout=180s
kubectl --context kind-k8s-admin-ch022 -n ch022 get pod required-node -o wide
```

**Expected:** either worker is valid: `general AND low` OR `compute`. The selected node is not deterministic.

## 13. Lab D — Preferred affinity is not a hard guarantee

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: preferred-node
  namespace: ch022
spec:
  affinity:
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          preference:
            matchExpressions:
              - key: workload.example.com/pool
                operator: In
                values: ["nonexistent"]
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 20m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\preferred-node.yaml

kubectl --context kind-k8s-admin-ch022 apply -f .\preferred-node.yaml
kubectl --context kind-k8s-admin-ch022 -n ch022 wait --for=condition=Ready pod/preferred-node --timeout=180s
kubectl --context kind-k8s-admin-ch022 -n ch022 get pod preferred-node -o wide
```

**Expected:** Pod schedules even though no node matches its preferred pool. This is the central difference between a preference and a requirement.

## 14. Lab E — Required Pod anti-affinity and capacity limits

Create a Deployment with two replicas that must occupy different worker hostnames. Constrain it to the two worker pools to avoid using the control plane:

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: separated
  namespace: ch022
spec:
  replicas: 2
  selector:
    matchLabels:
      app: separated
  template:
    metadata:
      labels:
        app: separated
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: workload.example.com/pool
                    operator: In
                    values: ["general", "compute"]
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: separated
              topologyKey: kubernetes.io/hostname
      containers:
        - name: app
          image: nginx:stable
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
'@ | Set-Content -Encoding ascii .\separated.yaml

kubectl --context kind-k8s-admin-ch022 apply -f .\separated.yaml
kubectl --context kind-k8s-admin-ch022 -n ch022 rollout status deployment/separated --timeout=180s
kubectl --context kind-k8s-admin-ch022 -n ch022 get pods -l app=separated -o wide
```

**Expected:** two Ready Pods, one on each worker.

Now request a third replica:

```powershell
kubectl --context kind-k8s-admin-ch022 -n ch022 scale deployment/separated --replicas=3
kubectl --context kind-k8s-admin-ch022 -n ch022 get deployment separated
kubectl --context kind-k8s-admin-ch022 -n ch022 get pods -l app=separated -o wide
kubectl --context kind-k8s-admin-ch022 -n ch022 get events --sort-by=.lastTimestamp
```

**Expected:** only two Pods can be placed; third remains Pending due to hard anti-affinity. Do not wait for `rollout status` to succeed while the third replica is impossible.

Restore the feasible count:

```powershell
kubectl --context kind-k8s-admin-ch022 -n ch022 scale deployment/separated --replicas=2
kubectl --context kind-k8s-admin-ch022 -n ch022 rollout status deployment/separated --timeout=180s
```

**Expected:** 2/2 Ready.

## 15. Lab F — Preferred Pod colocation

A helper Pod should prefer a node that already hosts a `separated` Pod, without making colocation mandatory:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: helper
  namespace: ch022
spec:
  affinity:
    podAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchLabels:
                app: separated
            topologyKey: kubernetes.io/hostname
  containers:
    - name: helper
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 20m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\helper.yaml

kubectl --context kind-k8s-admin-ch022 apply -f .\helper.yaml
kubectl --context kind-k8s-admin-ch022 -n ch022 wait --for=condition=Ready pod/helper --timeout=180s
kubectl --context kind-k8s-admin-ch022 -n ch022 get pods -o wide
```

**Expected:** helper becomes Ready. Since both workers host a matching Pod, either worker is a reasonable outcome. A control-plane node may also be eligible depending on other scheduler scores and taints; a preferred rule is never an absolute placement guarantee.

## 16. Lab G — IgnoredDuringExecution and label changes

Record the Pod UID and node for `selector-ok`, then remove its matching node label:

```powershell
$oldNode = kubectl --context kind-k8s-admin-ch022 -n ch022 get pod selector-ok -o jsonpath='{.spec.nodeName}'
$oldUid = kubectl --context kind-k8s-admin-ch022 -n ch022 get pod selector-ok -o jsonpath='{.metadata.uid}'
kubectl --context kind-k8s-admin-ch022 label node $workers[0] workload.example.com/pool-
kubectl --context kind-k8s-admin-ch022 -n ch022 get pod selector-ok -o wide
Write-Output "Original node=$oldNode UID=$oldUid"
```

**Expected:** existing Pod normally continues running despite node label removal; the label requirement is evaluated when scheduling, not continuously evicting the Pod.

Now create a **new** Pod with the same selector but a different name:

```powershell
(Get-Content .\selector-ok.yaml -Raw).Replace('selector-ok','selector-after-label-change') | Set-Content -Encoding ascii .\selector-after.yaml
kubectl --context kind-k8s-admin-ch022 apply -f .\selector-after.yaml
kubectl --context kind-k8s-admin-ch022 -n ch022 describe pod selector-after-label-change
```

**Expected:** new Pod Pending because no node has `pool=general`. This illustrates scheduling-time enforcement. Restore the disposable label and verify:

```powershell
kubectl --context kind-k8s-admin-ch022 label node $workers[0] workload.example.com/pool=general
kubectl --context kind-k8s-admin-ch022 -n ch022 wait --for=condition=Ready pod/selector-after-label-change --timeout=180s
```

**Expected:** new Pod becomes Ready.

## 17. Troubleshooting decision matrix

| Symptom | Evidence | Interpretation | Safe response |
|---|---|---|---|
| `0/N nodes available` selector mismatch | Pod events, node labels | Hard node rule unsatisfied | Correct Pod template or approved node labels |
| Required affinity mismatch | `describe pod` | No feasible node expression match | Review AND/OR terms and pool availability |
| Third replica Pending | Pod anti-affinity event | Too few topology domains | Add eligible nodes or review availability policy |
| Unexpected node choice | Node affinity is preferred | Scheduler uses other scoring inputs | Verify hard requirements and scoring assumptions |
| Running Pod remains after label removal | Pod UID and node | Scheduling-time rule | Expected under IgnoredDuringExecution |
| Colocation never occurs | Pod labels, topologyKey, namespaces | No matching peer or domain | Fix labels/scope or use preference |
| Stateful Pod stuck | PVC, volume topology, anti-affinity | Combined placement constraints | Review storage/quorum before relaxing |
| Node label drift | Audit/change records | Manual changes or node replacement | Use declarative node-pool governance |

### Diagnostic commands

```powershell
kubectl --context kind-k8s-admin-ch022 -n ch022 get pods -o wide
kubectl --context kind-k8s-admin-ch022 -n ch022 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch022 -n ch022 describe deployment separated
kubectl --context kind-k8s-admin-ch022 -n ch022 describe pod selector-after-label-change
kubectl --context kind-k8s-admin-ch022 get nodes --show-labels
kubectl --context kind-k8s-admin-ch022 describe nodes
```

Capture timestamps, Pod UIDs, placement expressions, node labels, events and final Ready state. Redact sensitive metadata.

## 18. SRE/DBRE operational runbook

1. **Identify scope:** affected Deployment/StatefulSet, cluster, namespace, desired versus Ready replicas, SLO impact.
2. **Confirm scheduling state:** Pending Pods with empty `spec.nodeName` and FailedScheduling events.
3. **Extract constraints:** nodeSelector, required/preferred node affinity, Pod affinity/anti-affinity, topologyKey, namespace scope, taints, resources, PVC topology.
4. **Inspect supply:** eligible nodes, node labels, failure domains, allocatable capacity, storage and node health.
5. **Assess tradeoff:** whether hard separation is necessary for quorum, data safety or regulatory isolation.
6. **Remediate through source of truth:** correct erroneous rules, provision eligible capacity, or make reviewed label changes. Do not bypass controls during incidents without approval.
7. **Verify:** desired Pods scheduled, Ready, endpoints healthy, service error rate/latency stable, and failure-domain placement as intended.
8. **Prevent recurrence:** validate label contracts, node-pool changes, minimum eligible topology domains and admission tests before release.

### Production best practices

- Use stable, documented node-pool label contracts.
- Prefer soft rules for optimization; use hard rules only for true invariants.
- Validate replica count against the number of eligible topology domains.
- Use explicit topology labels and verify provider-specific zone exposure.
- Treat Pod affinity across namespaces as a cross-team dependency.
- For stateful workloads, coordinate Kubernetes placement with storage, application replication and operator semantics.
- Alert on unschedulable Pod age and repeated FailedScheduling events.
- Review placement after autoscaler node replacement and upgrades.

## 19. Cleanup and rollback

**Confirm the disposable cluster and workers before deletion:**

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch022 get nodes
$workers
```

If `$workers` was lost, rerun the worker-discovery command from Section 9; never guess names.

```powershell
kubectl --context kind-k8s-admin-ch022 label node $workers[0] workload.example.com/pool- workload.example.com/cost-
kubectl --context kind-k8s-admin-ch022 label node $workers[1] workload.example.com/pool- workload.example.com/cost-
kubectl --context kind-k8s-admin-ch022 delete namespace ch022
kind delete cluster --name k8s-admin-ch022
kind get clusters
Remove-Item .\kind-config.yaml, .\selector-ok.yaml, .\selector-blocked.yaml, .\selector-fixed.yaml, .\required-node.yaml, .\preferred-node.yaml, .\separated.yaml, .\helper.yaml, .\selector-after.yaml -ErrorAction SilentlyContinue
```

**Warning:** Deleting the namespace and kind cluster permanently destroys disposable lab resources. Do not run against shared or production environments.

## 20. Acceptance checklist

- [ ] Three-node kind cluster created; exact context confirmed.
- [ ] Two workers labeled with distinct pool and cost attributes.
- [ ] nodeSelector Pod scheduled to the intended worker.
- [ ] Impossible nodeSelector reproduced and corrected.
- [ ] Required node affinity OR/AND semantics demonstrated.
- [ ] Unmatched preferred node affinity did not block scheduling.
- [ ] Two replicas separated across worker hostnames by required anti-affinity.
- [ ] Third replica remained Pending due to topology constraint.
- [ ] Preferred Pod colocation tested without assuming deterministic placement.
- [ ] Running Pod survived node label removal; new Pod was blocked.
- [ ] Sanitized scheduling events and recovery evidence collected.
- [ ] Temporary node labels, namespace and cluster removed.

## 21. Knowledge check

1. How does nodeSelector differ from node affinity?
2. How are matchExpressions combined within and across nodeSelectorTerms?
3. Why can a preferred rule select a nonpreferred node?
4. How does Pod anti-affinity differ from node affinity?
5. Why might three replicas with required hostname anti-affinity leave one Pending on two nodes?
6. What happens to a running Pod when a required node label is removed?
7. What are the risks of using untrusted node labels for security isolation?
8. Why do namespaceSelector and topologyKey matter in Pod affinity?
9. When should a database operator's placement policy override a generic affinity example?
10. What operational evidence proves a placement incident has been resolved?

## 22. Status and next chapter

**Draft published.** Runtime labs and technical review remain pending; do not mark validated until acceptance evidence is collected.

**Next:** Chapter 023 — Taints, Tolerations and Topology Spread.
