# Chapter 067 — Vertical Pod Autoscaler

**Track:** Kubernetes Administration · **Part 14 — Autoscaling and Capacity Management**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapter 066; kubectl; Windows PowerShell; isolated staging environment; VPA components installed for executable labs

## 1. Production scenario

A Kubernetes application has been configured with CPU requests of 2 cores and memory requests of 8 GiB per Pod, yet typical usage is much lower. Meanwhile, a separate worker repeatedly experiences memory pressure during batch processing. The team needs reliable resource recommendations without unexpectedly restarting critical Pods or exceeding node capacity.

**Goal:** understand how Vertical Pod Autoscaler (VPA) recommends and, when configured, adjusts CPU/memory requests; adopt it safely through recommendation-only evaluation, staging validation and controlled rollout.

### Learning objectives

1. Explain VPA architecture: recommender, updater, admission controller and metrics history.
2. Distinguish resource requests, limits, observed utilization and VPA recommendations.
3. Interpret `lowerBound`, `target`, `upperBound` and `uncappedTarget`.
4. Configure recommendation-only VPA and resource policies.
5. Understand `Off`, `Initial`, `Recreate` and `InPlaceOrRecreate` update modes and version support.
6. Evaluate Pod disruption, eviction, scheduling, PDBs and stateful quorum.
7. Plan VPA alongside HPA and node autoscaling.
8. Apply production SRE/DBRE capacity and rollback controls.

## 2. VPA architecture and installation model

```text
Pod CPU / memory usage history
             |
     VPA Recommender
             |
  Recommendation in VPA status
             |
     +-------+------------------+
     |                          |
Off / recommendation       Automated updates
only                         |
                         VPA Updater
                              |
                      Eviction / replacement
                              |
                       Admission Controller
                              |
                  Adjusted requests on new Pods
```

VPA is **not a built-in controller automatically enabled in every Kubernetes cluster**. It is an add-on whose CustomResourceDefinition and components must be installed and operated. Managed EKS/AKS availability varies with platform configuration.

### Components

| Component | Responsibility |
|---|---|
| Recommender | Derives CPU/memory requests from usage history |
| Updater | Determines when running Pods should receive updated resources |
| Admission controller | Applies recommendations to newly admitted Pods |
| VPA CRD | Stores target, policy, mode and recommendation status |
| Metrics source | Supplies resource usage history; setup varies |

**Important:** VPA recommendations are not the same as CPU/memory limits and are not a guarantee of SLO compliance. Some implementations support in-place resize paths, subject to Kubernetes and VPA versions.

## 3. Requests, limits and scheduling

- **CPU request:** scheduler capacity reservation and CPU share weighting.
- **Memory request:** scheduler capacity reservation and a factor in eviction behavior.
- **CPU limit:** throttling ceiling where enforced.
- **Memory limit:** container memory ceiling, potentially causing OOM kills.
- **VPA target:** recommended request value based on observed workload behavior and policy.

### Example

| Resource | Existing request | Observed pattern | Illustrative VPA target |
|---|---:|---:|---:|
| CPU | 2000m | 200–500m | 600m |
| Memory | 8 GiB | 2–3 GiB | 4 GiB |

These are fictional numbers for learning. Do not apply them without workload-specific measurements and burst analysis.

## 4. Lab 1 — Verify VPA prerequisites

```powershell
kubectl config current-context
kubectl get crd verticalpodautoscalers.autoscaling.k8s.io
kubectl api-resources | Select-String -Pattern 'verticalpodautoscaler'
kubectl get vpa -A
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
kubectl top pods -A
```

**Expected:** if VPA is installed, its CRD and resources are visible. If the CRD is absent, do not apply VPA manifests; use the conceptual labs and follow your platform team's approved installation process.

### Optional component discovery

```powershell
kubectl -n kube-system get deployments,pods | Select-String -Pattern 'vpa'
kubectl get deployments -A | Select-String -Pattern 'vpa'
```

VPA components may be deployed outside `kube-system`. Confirm actual names and installation topology before collecting logs.

## 5. Lab 2 — Inspect resource usage and existing requests

Choose an authorized namespace and workload:

```powershell
$ns = 'REPLACE_WITH_NAMESPACE'
$deployment = 'REPLACE_WITH_DEPLOYMENT'
kubectl -n $ns get deployment $deployment -o yaml
kubectl -n $ns get pods -o wide
kubectl -n $ns top pods --containers
kubectl -n $ns describe deployment $deployment
```

**Expected:** compare per-container requests/limits with measured usage and business traffic. `kubectl top` is a recent snapshot; use Prometheus history for peaks, percentiles and seasonality.

### Measurement worksheet

```text
Workload:
Container:
Current CPU request / limit:
Current memory request / limit:
CPU p50 / p95 / peak:
Memory working set p50 / p95 / peak:
Restart / OOM history:
Traffic pattern:
Node utilization:
SLO:
Measurement window:
```

## 6. Lab 3 — Create an isolated workload for VPA evaluation

**Approved staging only.** Save `ch067-workload.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch067
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vpa-demo
  namespace: ch067
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vpa-demo
  template:
    metadata:
      labels:
        app: vpa-demo
    spec:
      containers:
        - name: worker
          image: busybox:1.36
          command: ["/bin/sh", "-c", "while true; do :; done"]
          resources:
            requests:
              cpu: 200m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
```

```powershell
kubectl apply -f .\ch067-workload.yaml
kubectl -n ch067 rollout status deployment/vpa-demo --timeout=120s
kubectl -n ch067 get deployments,pods
kubectl -n ch067 top pods --containers
```

**Expected:** two CPU-consuming test Pods run in the staging namespace. This is intentionally synthetic load and should not be used on production nodes or constrained shared clusters.

## 7. Lab 4 — Configure recommendation-only VPA

**Requires installed VPA CRD and recommender.** Save `ch067-vpa.yaml`:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: vpa-demo
  namespace: ch067
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vpa-demo
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
      - containerName: worker
        minAllowed:
          cpu: 50m
          memory: 64Mi
        maxAllowed:
          cpu: 500m
          memory: 512Mi
        controlledResources: ["cpu", "memory"]
```

```powershell
kubectl apply -f .\ch067-vpa.yaml
kubectl -n ch067 get vpa vpa-demo
kubectl -n ch067 describe vpa vpa-demo
kubectl -n ch067 get vpa vpa-demo -o yaml
```

**Expected:** VPA remains recommendation-only and does not automatically evict Pods. Recommendations may be absent initially until sufficient usage history is collected. If no recommendation appears, inspect VPA components and metrics availability rather than forcing Pod restarts.

## 8. Lab 5 — Interpret VPA recommendations

A typical VPA status contains a recommendation per container:

```yaml
status:
  recommendation:
    containerRecommendations:
      - containerName: worker
        lowerBound:
          cpu: 100m
          memory: 96Mi
        target:
          cpu: 250m
          memory: 192Mi
        upperBound:
          cpu: 450m
          memory: 384Mi
        uncappedTarget:
          cpu: 300m
          memory: 256Mi
```

This is illustrative output, not a measured result.

### Meaning

| Field | Interpretation |
|---|---|
| `target` | Recommended resource request after applicable constraints |
| `lowerBound` | Lower range boundary for recommendation |
| `upperBound` | Upper range boundary for recommendation |
| `uncappedTarget` | Recommendation before configured min/max policy caps |

```powershell
kubectl -n ch067 get vpa vpa-demo -o jsonpath='{.status.recommendation.containerRecommendations}'
kubectl -n ch067 describe vpa vpa-demo
```

**Expected:** compare recommendation with real traffic, memory peaks and application performance. A recommendation is an input to engineering judgment, not an automatic production change authorization.

## 9. Lab 6 — Evaluate VPA update modes and disruption

| Update mode | Operational behavior | Production consideration |
|---|---|---|
| `Off` | Recommendation only | Preferred starting point |
| `Initial` | Applies on Pod creation | No proactive eviction for resizing |
| `Recreate` | Updates through Pod replacement/eviction | Disruption and rescheduling risk |
| `InPlaceOrRecreate` | Attempts in-place resize, may recreate | Version and feature support required |

Supported update modes depend on VPA release and Kubernetes capabilities. Some older releases document `Auto` as an alias or historical mode; verify the installed CRD schema rather than assuming portability.

### Disruption gates

Before enabling automated updates:

1. Confirm PodDisruptionBudget and sufficient healthy replicas.
2. Verify readiness, graceful shutdown and termination behavior.
3. Confirm node capacity for recommended requests.
4. Assess storage attach/detach and topology constraints.
5. Validate database quorum, replication lag and failover semantics.
6. Establish rollback and observation window.
7. Check VPA updater behavior against PDBs and deployment policies.

**Do not enable automated eviction for production databases as a generic rightsizing exercise.**

## 10. Lab 7 — Analyze resource policy and limit behavior

```yaml
resourcePolicy:
  containerPolicies:
    - containerName: worker
      mode: Auto
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: "2"
        memory: 2Gi
      controlledResources:
        - cpu
        - memory
      controlledValues: RequestsOnly
```

### Policy controls

- `minAllowed` prevents recommendations below an approved floor.
- `maxAllowed` caps recommendations.
- `controlledResources` selects CPU and/or memory.
- `controlledValues: RequestsOnly` modifies requests rather than requests and limits, where supported.
- Container policy `mode: Off` can exclude a container from VPA resource adjustments.

**Important:** changing requests without limits can affect QoS and scheduling. Changing both requests and limits may affect throttling and OOM behavior. Validate actual VPA version semantics and admission output in staging.

## 11. Lab 8 — VPA and HPA interaction

HPA typically changes **replica count**; VPA changes **resource requests**. Running both on the same workload can be appropriate or problematic depending on metrics and versions.

### Common conflict

If HPA scales on CPU utilization relative to CPU requests while VPA changes CPU requests, the denominator changes. This can cause feedback and unstable scaling decisions.

### Safer design patterns

| Workload | Candidate approach |
|---|---|
| CPU-based HPA | VPA Off for CPU recommendations, or carefully separate resource ownership |
| HPA on external queue depth | VPA for requests, with tested interactions |
| Batch Job | VPA recommendations or Initial mode |
| Stateful database | Recommendation-only, reviewed maintenance |
| Stable background service | VPA Initial/Recreate after disruption testing |

**Rule:** avoid independent controllers fighting over the same effective scaling signal. Confirm interactions with installed HPA/VPA versions and resource ownership.

## 12. Lab 9 — VPA and node capacity planning

Assume a Deployment has 10 replicas. VPA recommends changing each Pod request from 500m CPU/1Gi memory to 1000m CPU/2Gi memory.

```text
Before:
  CPU requested = 10 × 0.5 = 5 vCPU
  Memory requested = 10 × 1 GiB = 10 GiB

After:
  CPU requested = 10 × 1 = 10 vCPU
  Memory requested = 10 × 2 GiB = 20 GiB

Increase:
  +5 vCPU and +10 GiB requested
```

### Operational implications

- Scheduler must find sufficient allocatable capacity.
- Cluster Autoscaler or Karpenter may need to provision nodes.
- Larger Pod requests can reduce bin-packing efficiency.
- Node quotas, subnet IPs, instance limits and zone constraints can block scheduling.
- Stateful volume topology may prevent placement on a new node.
- VPA recommendations can increase cost or expose hidden capacity shortages.

**Expected:** calculate aggregate resource impact before adopting a VPA recommendation.

## 13. Lab 10 — Troubleshoot missing or unexpected recommendations

```powershell
kubectl -n ch067 get vpa vpa-demo -o yaml
kubectl -n ch067 describe vpa vpa-demo
kubectl -n ch067 get pods -o wide
kubectl -n ch067 top pods --containers
kubectl get crd verticalpodautoscalers.autoscaling.k8s.io
kubectl get events -A --sort-by=.lastTimestamp
```

### Troubleshooting matrix

| Symptom | Likely cause | First investigation |
|---|---|---|
| VPA CRD missing | VPA not installed | Platform add-on inventory |
| No recommendations | Insufficient history or recommender issue | VPA status/logs, metrics |
| Recommendations at maxAllowed | Policy cap reached | Compare uncappedTarget |
| Unexpectedly high memory | Bursty workload or memory retention | Working set history |
| Updater not changing Pods | Off/Initial mode, PDB, updater issue | Update mode and Events |
| Replacement Pods Pending | Increased requests exceed capacity | Scheduler/node autoscaler |
| OOM after rightsizing | Limit too low or memory spike | Termination reason and peak memory |
| HPA instability | CPU request changes affect utilization | HPA/VPA metric interaction |

**Expected:** distinguish recommendation quality from application behavior and scheduler constraints.

## 14. Lab 11 — Stateful database adoption tabletop

**Scenario:** a PostgreSQL StatefulSet has three replicas across zones. VPA recommends increasing memory requests by 50% and decreasing CPU requests by 30%. A maintenance window is proposed to enable automated updates.

### Required review

1. Identify leader/primary and replica roles.
2. Verify synchronous/asynchronous replication and failover ownership.
3. Check quorum, replica lag and transaction durability.
4. Confirm PodDisruptionBudget and storage zone affinity.
5. Estimate capacity after changing requests.
6. Review memory usage, shared buffers, OS cache and OOM history.
7. Choose recommendation-only, manual rolling change or controlled automation.
8. Define maintenance approval, backup, rollback and acceptance tests.

**Expected:** recommendation-only remains the default until database-specific safety, failover and performance validation are complete.

## 15. Lab 12 — Production rightsizing incident tabletop

**Scenario:** a team enables VPA Recreate mode for an API Deployment. Pods are evicted for request updates, replacements remain Pending due to capacity, and customer p95 latency rises. HPA simultaneously requests more replicas.

### Investigation tasks

1. Establish customer impact and incident timeline.
2. Inspect VPA update mode, recommendations and updater Events.
3. Inspect HPA desired/current replicas and scaling metrics.
4. Check scheduler Events, node allocatable and autoscaler limits.
5. Assess PDB and available Ready endpoints.
6. Select low-risk mitigation with owner and rollback.
7. Verify customer SLIs and stable replica placement.
8. Document preventive policy and staged rollout requirements.

**Expected:** identify autoscaler interactions and resource capacity as separate but related failure domains.

## 16. Production runbook

### Detect

- Resource request over/under-provisioning.
- CPU throttling, OOM, scheduling failures or node waste.
- VPA recommendation changes and updater actions.
- HPA instability or workload unavailability after rightsizing.

### Diagnose

1. Confirm VPA installation, target and update mode.
2. Inspect recommendation status and resource policies.
3. Compare measured resource history with SLO and bursts.
4. Assess HPA, PDB, rollout and node autoscaler interactions.
5. Calculate aggregate requests and node capacity.

### Mitigate

1. Prefer Off mode for initial evaluation.
2. Require reviewed change for production resource adjustments.
3. Apply changes through GitOps/approved deployment processes.
4. Avoid concurrent uncoordinated HPA/VPA/resource edits.
5. Preserve database quorum and storage safety.

### Verify

- Pods schedule and become Ready.
- CPU throttling/OOM and memory pressure improve.
- Customer latency/error rate remains within SLO.
- No unexpected eviction or HPA oscillation occurs.
- Node utilization and cost remain acceptable.

## 17. Production adoption checklist

- [ ] VPA version and CRD support confirmed.
- [ ] Resource usage history covers peak and normal periods.
- [ ] CPU/memory requests and limits documented.
- [ ] Off mode recommendations collected and reviewed.
- [ ] Resource policy min/max bounds established.
- [ ] HPA metric interactions assessed.
- [ ] Node capacity and autoscaler behavior validated.
- [ ] PDB, rollout and graceful termination reviewed.
- [ ] Stateful quorum/storage/failover risks assessed.
- [ ] Rollback, dashboards and alerting prepared.
- [ ] Staging adoption completed before production automation.
- [ ] Independent technical review and runtime validation recorded.

## 18. Cleanup

Delete only the isolated staging namespace after evidence collection:

```powershell
kubectl -n ch067 get deployments,pods,vpa
kubectl delete namespace ch067
```

Do not uninstall cluster-wide VPA components or CRDs as part of chapter cleanup.

**Status:** Draft — runtime validation and technical review pending.

## 19. References

- [Kubernetes Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/)
- [Vertical Pod Autoscaler (Autoscaler repository)](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
- [VPA README and deployment guidance](https://github.com/kubernetes/autoscaler/blob/master/vertical-pod-autoscaler/README.md)
- [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [In-place Pod Resize](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/)

**Next:** Chapter 068 — Cluster Autoscaler and Karpenter.
