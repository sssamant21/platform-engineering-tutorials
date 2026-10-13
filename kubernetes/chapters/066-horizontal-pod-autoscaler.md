# Chapter 066 — Horizontal Pod Autoscaler

**Track:** Kubernetes Administration · **Part 14 — Autoscaling and Capacity Management**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform and application engineers  
**Prerequisites:** Chapters 001–065; kubectl; Windows PowerShell; approved staging namespace; Metrics Server or supported metrics adapter

## 1. Production scenario

A customer-facing API experiences predictable demand spikes. CPU rises, p95 latency breaches the SLO, and request queues grow. The Deployment has three replicas and sufficient node headroom for additional Pods. The team wants to configure Horizontal Pod Autoscaler (HPA) so replica counts respond to demand without triggering excessive scaling, overwhelming PostgreSQL or exhausting Kubernetes node capacity.

**Goal:** design, deploy, observe and troubleshoot HPA using `autoscaling/v2`, with safe staging validation and production readiness gates.

### Learning objectives

1. Explain HPA architecture, controller reconciliation and metrics sources.
2. Calculate CPU utilization against **resource requests**, not CPU limits.
3. Configure CPU, memory and custom/external metric targets.
4. Interpret desired replica calculation and scaling tolerances.
5. Tune scale-up/scale-down policies and stabilization windows.
6. Diagnose missing metrics, Pending Pods, readiness effects and max replica constraints.
7. Plan HPA alongside node autoscaling, PDBs, connection pools and downstream capacity.
8. Verify autoscaling behavior using observable acceptance criteria.

## 2. Architecture and prerequisites

```text
Application traffic -> Deployment Pods -> CPU/memory/custom metrics
                             |                     |
                             |                Metrics Server
                             |                or metrics adapter
                             |                     |
                             +--- HPA controller --+
                                      |
                             Deployment scale subresource
                                      |
                             ReplicaSet creates/removes Pods
                                      |
                         Scheduler / node autoscaler
```

HPA is a control loop in the Kubernetes controller manager. It periodically reads metrics and adjusts the target workload's desired replica count via the scale subresource. It does **not** provision nodes or automatically guarantee that new Pods can schedule.

### Metrics APIs

| Metric type | Typical source | Use case |
|---|---|---|
| Resource CPU | Metrics API / Metrics Server | CPU-bound service |
| Resource memory | Metrics API / Metrics Server | Memory-driven scaling with caution |
| Pods custom metric | Custom Metrics API adapter | Requests per Pod |
| Object custom metric | Custom Metrics API adapter | Queue depth associated with an object |
| External metric | External Metrics API adapter | Kafka lag, cloud queue depth |

Metric adapters and labels vary by implementation; do not assume a custom metric is available simply because Prometheus is installed.

## 3. CPU utilization and desired replicas

For a resource utilization target, HPA compares average observed CPU usage with the Pods' CPU requests.

```text
desiredReplicas = ceil(currentReplicas × currentMetric / targetMetric)
```

Example:

- Current replicas: 4
- Average CPU utilization: 90% of request
- Target CPU utilization: 60%
- Approximate desired replicas: `ceil(4 × 90 / 60) = 6`

This is a simplified illustration. The real controller applies tolerance, missing-metric adjustments, not-yet-ready Pod handling, stabilization windows, scaling policies and min/max bounds.

### Why CPU requests matter

If a container requests 250m CPU and uses 200m, its CPU utilization relative to the request is approximately 80%. Raising CPU limits alone does not change the utilization denominator. Missing CPU requests on relevant containers can prevent a CPU-utilization-based HPA from calculating the metric.

## 4. Lab 1 — Verify HPA prerequisites

```powershell
kubectl config current-context
kubectl version
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
kubectl top pods -A
kubectl get hpa -A
kubectl auth can-i create hpa -n default
Get-Date -Format o
```

**Expected:** Metrics API responds and you can inspect HPA resources. If `kubectl top` fails, investigate Metrics Server before creating CPU-based HPA.

### Metrics Server troubleshooting

```powershell
kubectl -n kube-system get deployments,pods
kubectl get apiservice v1beta1.metrics.k8s.io -o yaml
kubectl get events -A --sort-by=.lastTimestamp
```

Do not change kubelet TLS verification or weaken cluster security as a shortcut for metrics failures.

## 5. Lab 2 — Deploy a CPU-bound test workload

**Approved staging only.** Save `ch066-hpa.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch066
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cpu-demo
  namespace: ch066
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cpu-demo
  template:
    metadata:
      labels:
        app: cpu-demo
    spec:
      containers:
        - name: worker
          image: busybox:1.36
          command: ["/bin/sh", "-c", "while true; do :; done"]
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
            limits:
              cpu: 200m
              memory: 64Mi
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cpu-demo
  namespace: ch066
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cpu-demo
  minReplicas: 1
  maxReplicas: 3
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Pods
          value: 1
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 120
      policies:
        - type: Pods
          value: 1
          periodSeconds: 60
```

```powershell
kubectl apply -f .\ch066-hpa.yaml
kubectl -n ch066 rollout status deployment/cpu-demo --timeout=120s
kubectl -n ch066 get deployment,hpa,pods
kubectl -n ch066 describe hpa cpu-demo
```

**Expected:** HPA observes CPU above the 60% target and may scale to two or three replicas after metrics become available. The workload intentionally burns CPU; use only a staging cluster with spare capacity. Stop and clean up if node pressure develops.

## 6. Lab 3 — Observe scaling decisions

```powershell
kubectl -n ch066 get hpa cpu-demo -w
kubectl -n ch066 get pods -o wide
kubectl -n ch066 describe hpa cpu-demo
kubectl -n ch066 get events --sort-by=.lastTimestamp
kubectl -n ch066 top pods --containers
```

Exit watch with Ctrl+C.

### Expected observations

- HPA reports current versus target CPU utilization.
- Desired replicas increase, subject to scaling policies and maxReplicas.
- ReplicaSet creates new Pods; scheduler places them if capacity exists.
- Scaling may lag because metrics collection and HPA reconciliation are periodic.
- If metrics are unavailable, `<unknown>` may appear in HPA output.

Record time to scale, number of Ready replicas, Pending Pods, node CPU and application impact.

## 7. Lab 4 — Inspect HPA conditions and Events

```powershell
kubectl -n ch066 describe hpa cpu-demo
kubectl -n ch066 get hpa cpu-demo -o yaml
kubectl -n ch066 get deployment cpu-demo -o yaml
kubectl -n ch066 get events --sort-by=.lastTimestamp
```

### HPA conditions

| Condition | Interpretation |
|---|---|
| AbleToScale | HPA can access/adjust target scale |
| ScalingActive | Valid metrics available for scaling |
| ScalingLimited | Desired replicas constrained by min/max or policy |

These conditions are diagnostic, not a substitute for checking Pod readiness and customer SLIs.

### Common Events

- `FailedGetResourceMetric`
- `FailedComputeMetricsReplicas`
- `SuccessfulRescale`
- `FailedRescale`

Event names/messages can vary by Kubernetes version and adapter.

## 8. Lab 5 — Analyze scale-up and scale-down behavior

HPA behavior supports separate scaleUp and scaleDown policies.

```yaml
behavior:
  scaleUp:
    stabilizationWindowSeconds: 0
    selectPolicy: Max
    policies:
      - type: Percent
        value: 100
        periodSeconds: 60
      - type: Pods
        value: 4
        periodSeconds: 60
  scaleDown:
    stabilizationWindowSeconds: 300
    selectPolicy: Min
    policies:
      - type: Percent
        value: 10
        periodSeconds: 60
      - type: Pods
        value: 1
        periodSeconds: 60
```

**Interpretation:** scale-up policies limit growth; scale-down stabilization reduces oscillation by retaining a higher recent recommendation. `selectPolicy` chooses how policies combine. These values are examples, not universal production defaults.

### Tradeoffs

| Setting | Too aggressive | Too conservative |
|---|---|---|
| Scale up | Capacity spikes, downstream overload | Slow recovery under traffic |
| Scale down | Oscillation, cold-start churn | Higher steady cost |
| CPU target | Too many Pods | Late scaling / SLO breaches |
| maxReplicas | Database and node saturation | Insufficient application capacity |

## 9. Lab 6 — Diagnose HPA that does not scale

```powershell
kubectl -n ch066 get hpa cpu-demo -o wide
kubectl -n ch066 describe hpa cpu-demo
kubectl -n ch066 get deployment cpu-demo
kubectl -n ch066 get pods -o wide
kubectl -n ch066 top pods --containers
kubectl get apiservice v1beta1.metrics.k8s.io
```

### Decision tree

```text
HPA not scaling?
  |
  +-- Target missing? -> scaleTargetRef, scale subresource, RBAC
  |
  +-- Metrics unknown? -> Metrics Server, adapter, requests
  |
  +-- Utilization below target? -> no scale expected
  |
  +-- At maxReplicas? -> capacity policy / SLO tradeoff
  |
  +-- Desired replicas increase but Pods Pending?
  |      -> scheduler / node autoscaler / quota / PVC
  |
  +-- Pods Running but NotReady?
  |      -> probes, startup, dependency health
  |
  +-- Scaling oscillates?
         -> stabilization, workload metric, readiness
```

**Expected:** separate HPA decision problems from node scheduling or application readiness problems.

## 10. Lab 7 — Custom and external metrics design

For request-driven applications, CPU may not reflect the true bottleneck. A service waiting on database connections can show low CPU despite high latency.

### Example custom Pods metric

```yaml
metrics:
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: "50"
```

### Example external queue metric

```yaml
metrics:
  - type: External
    external:
      metric:
        name: queue_depth
      target:
        type: AverageValue
        averageValue: "100"
```

These fragments require a correctly configured custom/external metrics adapter exposing the exact metric name and semantics. They are **design examples**, not standalone working manifests.

### Multiple metrics

When multiple metrics are configured, HPA generally uses the largest desired replica recommendation. If a metric cannot be converted into a desired replica count, scale-down may be skipped even if another metric suggests fewer replicas; scale-up may still proceed when a valid metric recommends it.

## 11. Lab 8 — HPA and cluster/node autoscaling

HPA adds Pods; node autoscaling provisions capacity when unschedulable Pods require it.

```powershell
kubectl -n ch066 get pods -o wide
kubectl get nodes -L topology.kubernetes.io/zone -o wide
kubectl -n ch066 get events --sort-by=.lastTimestamp
kubectl get events -A --sort-by=.lastTimestamp
```

### Failure modes

- HPA scales Deployment but Pods remain Pending.
- Node autoscaler cannot provision due to cloud quota, subnet IPs, limits or affinity.
- Pods schedule but remain NotReady because of dependency or startup issues.
- Excessive scaling overwhelms PostgreSQL connection pools, Redis, Kafka or upstream APIs.
- Scale-down conflicts with long-running requests, graceful termination or PDB constraints.

**Important:** HPA alone cannot solve a database bottleneck, an unavailable external dependency or a cluster without eligible node capacity.

## 12. Lab 9 — Production SRE/DBRE capacity modeling

Assume:

- Per-Pod maximum database connections: 20
- HPA maxReplicas: 15
- Other services reserve 100 database connections
- Database practical connection budget: 300

```text
Potential application connections = 15 × 20 = 300
Total potential connections = 300 + 100 = 400
Practical budget = 300
Potential overcommit = 100 connections
```

### Safe design choices

1. Reduce per-Pod pool size based on concurrency and query behavior.
2. Set HPA maxReplicas from both application and dependency capacity.
3. Apply connection pooling/proxying where appropriate.
4. Rate-limit or shed load rather than scaling into downstream saturation.
5. Monitor DB pool wait, active connections, queue depth and request SLIs.
6. Test realistic load with autoscaling and graceful termination.

**Expected:** a capacity model linking replica count to dependency budgets.

## 13. Lab 10 — HPA incident tabletop

**Scenario:** API p95 latency breaches the SLO. HPA increases desired replicas from 4 to 12, but only 7 Pods become Ready. Five are Pending due to insufficient node capacity. PostgreSQL connection wait rises as Ready Pods increase, while CPU falls below the HPA target.

### Investigation tasks

1. Confirm current HPA target, metrics and desired replicas.
2. Inspect scheduler Events and node autoscaler limits.
3. Correlate Ready replica count with p95 latency and error ratio.
4. Estimate database connections at maxReplicas.
5. Determine whether additional Pods would help or worsen DB saturation.
6. Select a mitigation with approval and rollback.
7. Verify customer SLIs, database health and stable replica behavior.
8. Record corrective actions for capacity, metrics and alerting.

**Expected:** evidence-backed recognition that autoscaling can amplify a downstream bottleneck.

## 14. Production troubleshooting matrix

| Symptom | Likely cause | First check |
|---|---|---|
| HPA TARGETS `<unknown>` | Metrics unavailable or missing requests | `describe hpa`, Metrics API |
| HPA scales but no Ready Pods | Pending or probe failures | Scheduler Events, Pod readiness |
| HPA stuck at max | Demand or target too low | Metrics, maxReplicas, SLO |
| HPA oscillates | Metric noise, scale-down behavior | HPA behavior and history |
| CPU low but latency high | I/O, DB, queue or lock waits | Traces, dependency metrics |
| Memory HPA never scales down | Memory not reclaimed | Memory profile and metric design |
| HPA fights manual replicas | Competing desired replica writers | GitOps and scale ownership |
| Sudden DB overload after scaling | Per-Pod connection multiplication | Pool budget and maxReplicas |

## 15. Production deployment checklist

- CPU/memory requests are defined and justified.
- Metrics API/adapter availability is monitored.
- HPA target reflects measured workload behavior.
- minReplicas and maxReplicas match SLO and capacity requirements.
- Scale-up/down behavior is tested under load.
- Scheduler and node autoscaler can supply eligible capacity.
- Readiness, startup and graceful termination are validated.
- PDB and rollout surge interactions are reviewed.
- PostgreSQL/Redis/Kafka and external dependency budgets are modeled.
- Dashboards cover desired/Ready replicas, HPA conditions, Pending Pods, latency and error rate.
- Rollback and emergency traffic-shaping procedures are documented.

## 16. Acceptance checklist

- [ ] HPA architecture and metrics APIs understood.
- [ ] CPU utilization relative to requests calculated correctly.
- [ ] Metrics Server and HPA prerequisites verified.
- [ ] Isolated staging workload deployed or marked not run.
- [ ] HPA scaling behavior and conditions observed.
- [ ] Scale-up/down policies and stabilization explained.
- [ ] Missing metrics and Pending Pod failure paths diagnosed.
- [ ] Custom/external metric designs reviewed.
- [ ] HPA and node autoscaler responsibilities distinguished.
- [ ] Database capacity model completed.
- [ ] Incident tabletop and recovery criteria completed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

## 17. Cleanup

Stop the CPU-intensive staging workload after capturing evidence:

```powershell
kubectl -n ch066 get hpa,deployments,pods
kubectl delete namespace ch066
```

Only delete resources created for this chapter. Do not modify production HPA settings as part of training cleanup.

**Status:** Draft — runtime validation and technical review pending.

## 18. References

- [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [HPA Walkthrough](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/)
- [Resource Metrics Pipeline](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)
- [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)

**Next:** Chapter 067 — Vertical Pod Autoscaler.
