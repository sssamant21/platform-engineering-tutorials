# Chapter 070 — Kubernetes Performance and Scaling Project

**Track:** Kubernetes Administration · **Part 14 — Autoscaling and Capacity Management (final capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes platform engineers, application owners  
**Prerequisites:** Chapters 066–069; kubectl; Windows PowerShell; approved staging cluster; Metrics Server; optional Prometheus/Grafana; approved load-generation image

## 1. Capstone scenario and mission

A customer-facing API runs on EKS or AKS with four replicas. Traffic rises by 3×, p95 latency increases from 250 ms to 1.8 s, and 5xx errors reach 4%. HPA recommends twelve replicas, but only eight become Ready; other Pods are Pending. Some nodes are close to memory request saturation. Database connection acquisition latency rises, and a storage-backed batch job competes for throughput. The team must decide whether to change HPA, VPA, node provisioning, workload requests or downstream capacity.

**Mission:** establish a reproducible baseline, identify actual bottlenecks, test bounded scaling changes, verify SLOs and dependency safety, and produce a production-ready scaling plan with cost and failure-zone headroom.

This is a training scenario. Numbers are illustrative, not observed results.

### Learning outcomes

1. Correlate user-facing latency/error rates with resource demand and scheduler state.
2. Measure CPU throttling, memory pressure, network and storage performance.
3. Validate HPA scale decisions and VPA recommendation-only sizing.
4. Diagnose Cluster Autoscaler/Karpenter node provisioning and placement.
5. Model database connections and other downstream scaling limits.
6. Design load tests, rollback triggers and safe production rollout.
7. Calculate zone-loss headroom, forecast growth and estimate cost.
8. Deliver a reviewed performance and scaling acceptance report.

## 2. Safety, ownership and prerequisites

**All load generation and fault exercises are staging-only.** Do not run traffic tests against production services or shared data stores without explicit authorization. Do not change production autoscalers, node pools, database limits or storage provisioning as part of this capstone.

Before proceeding:

- Confirm the correct Kubernetes context and a dedicated namespace.
- Set traffic ceiling, duration, concurrency, maximum replicas and budget.
- Confirm test endpoints do not create sensitive or irreversible records.
- Identify the load-test owner, platform approver, DBRE and incident escalation.
- Ensure node quotas, subnet IPs, resource quotas and monitoring capacity.
- Define abort criteria for error rate, latency, node pressure and database saturation.
- Use pinned, approved container images for executable testing.
- Do not assume HPA scaling can solve network, storage or database bottlenecks.

```powershell
Get-Date -Format o
kubectl config current-context
kubectl cluster-info
kubectl get nodes -L topology.kubernetes.io/zone -o wide
kubectl get hpa -A
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get apiservice v1beta1.metrics.k8s.io
```

**Expected:** the target cluster and monitoring prerequisites are confirmed. If VPA or Karpenter CRDs are absent, complete their sections as design/tabletop exercises.

## 3. Reference architecture and scaling boundaries

```text
Synthetic staging clients
          |
     Ingress / LB
          |
     API Service
          |
     API Deployment <---- HPA (CPU / custom metric)
          |                     |
          |                  Metrics API
          |
     Database / Redis / Queue
          |
    DB pool / IOPS / latency

VPA (Off) ---> CPU/memory recommendations
Scheduler ---> Pending Pods ---> CA or Karpenter ---> Nodes
                                             |
                                      Cloud quota / subnet
                                             |
                                       Zone resilience

Observability: Prometheus + logs + traces + cloud metrics
```

**Scaling ownership:** HPA controls replica count; VPA can recommend or change requests; node autoscaling adds/removes capacity. Avoid uncoordinated changes to the same workload.

## 4. Deliverables and evidence

| Artifact | Required content |
|---|---|
| Baseline | Traffic, latency, errors, resources, replica counts |
| Bottleneck register | Competing hypotheses with supporting and contrary evidence |
| HPA analysis | Targets, decisions, conditions, min/max and behavior |
| VPA review | Recommendations, resource policy and disruption risk |
| Node capacity analysis | Allocatable, requests, Pending causes, node provisioning |
| Dependency budget | Database pool, Redis, Kafka and external rate limits |
| Load-test report | Phases, timestamps, results, abort events |
| Resilience plan | Node/zone loss and rollout surge headroom |
| Cost assessment | Node-hour, instance mix and forecast assumptions |
| Acceptance sign-off | SLO, safety, rollback and operational ownership |

## 5. Lab 1 — Establish customer SLOs and the baseline

Choose a staging service and record a 15–30 minute representative baseline before changes.

```powershell
$ns = 'REPLACE_WITH_STAGING_NAMESPACE'
$deployment = 'REPLACE_WITH_DEPLOYMENT'
kubectl -n $ns get deployment $deployment -o wide
kubectl -n $ns get pods -o wide
kubectl -n $ns get services,endpointslices
kubectl -n $ns get hpa
kubectl -n $ns top pods --containers
kubectl top nodes
```

### Baseline worksheet

```text
Measurement window (UTC):
Requests/sec and peak:
p50 / p95 / p99 latency:
HTTP 5xx and timeout rate:
Current / desired / Ready replicas:
CPU usage / requests / throttling:
Memory working set / requests / limits:
Pending Pods and scheduler reasons:
Node allocatable and requested:
Network bytes/sec, drops, DNS errors:
Storage IOPS / throughput / latency:
DB active connections / pool wait:
Cloud spend per hour:
```

**Expected:** a time-correlated baseline. A snapshot from `kubectl top` is not a substitute for peak historical metrics.

## 6. Lab 2 — Define a safe load-test profile

Use an approved load generator such as k6, Locust, or your organization's standard tool. No load generator is automatically installed by this chapter.

| Phase | Duration | Traffic | Purpose |
|---|---|---|---|
| Baseline | 10 min | 1× | Confirm steady behavior |
| Ramp | 10 min | 1× → 2× | Observe HPA and node response |
| Peak | 10 min | 3× | Measure SLO and capacity |
| Recovery | 10 min | 1× | Observe scale-down and stabilization |
| Optional burst | Approved | Short 4× burst | Test queueing and load shedding |

**Abort immediately** if staging crosses agreed error, latency, memory, DB pool or spend limits; the thresholds must be set before execution. Keep test data isolated and clean up safely.

### Test quality controls

- Use consistent request mixes and representative payload sizes.
- Include read and write paths only when test data is safe.
- Separate warm-up from measurement.
- Capture offered load and successful throughput, not just concurrency.
- Keep database capacity and external API rate limits in scope.
- Record exact UTC phase boundaries.

## 7. Lab 3 — Diagnose CPU and memory constraints

```powershell
kubectl -n $ns top pods --containers
kubectl top nodes
kubectl -n $ns describe deployment $deployment
kubectl -n $ns get pods -o wide
kubectl get events -A --sort-by=.lastTimestamp
```

### Prometheus examples

```promql
sum by (namespace, pod, container) (
  rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m])
)
```

```promql
sum by (namespace, pod, container) (
  container_memory_working_set_bytes{container!="",image!=""}
)
```

```promql
sum by (namespace, pod, container) (
  rate(container_cpu_cfs_throttled_periods_total{container!="",image!=""}[5m])
)
/
clamp_min(
  sum by (namespace, pod, container) (
    rate(container_cpu_cfs_periods_total{container!="",image!=""}[5m])
  ), 1e-9
)
```

Metric names/labels depend on the runtime and monitoring stack. Throttled periods are diagnostic but do not directly quantify lost CPU time.

**Expected:** distinguish CPU saturation, CPU quota throttling, memory working-set growth, OOM kills and scheduler request saturation.

## 8. Lab 4 — Validate HPA scaling decisions

```powershell
kubectl -n $ns get hpa -o wide
kubectl -n $ns describe hpa REPLACE_WITH_HPA
kubectl -n $ns get hpa REPLACE_WITH_HPA -o yaml
kubectl -n $ns get deployment $deployment -o wide
kubectl -n $ns get events --sort-by=.lastTimestamp
```

### Worked example

```text
Current replicas = 4
Observed CPU utilization = 90% of CPU request
Target CPU utilization = 60%
Illustrative recommendation = ceil(4 × 90/60) = 6
```

The real HPA also accounts for metric availability, readiness, tolerance, policies and stabilization.

### HPA acceptance criteria

- Metrics are available and meaningful.
- Scale-up begins before sustained SLO violation where feasible.
- Desired replicas translate into Ready replicas.
- Scale-down avoids oscillation and excessive Pod churn.
- maxReplicas respects downstream connection and cost budgets.
- HPA conditions and Events explain unexpected behavior.

**Expected:** explain both the scaling recommendation and actual application capacity.

## 9. Lab 5 — Review VPA recommendations without disruption

```powershell
kubectl get crd verticalpodautoscalers.autoscaling.k8s.io
kubectl -n $ns get vpa
kubectl -n $ns describe vpa REPLACE_WITH_VPA
```

Skip the last two commands if VPA is not installed.

Use `updateMode: "Off"` for initial analysis. Compare recommended `target`, `lowerBound`, `upperBound` and `uncappedTarget` against measured workload peaks and node capacity.

### Decision worksheet

| Question | Required answer |
|---|---|
| Are requests oversized? | Compare p95/peak and forecast |
| Are requests too low? | Check OOM, pressure and throttling |
| Will request changes affect HPA? | Evaluate utilization denominator |
| Will replacement Pods fit? | Check allocatable and placement |
| Is disruption safe? | Check PDB, replicas, quorum, storage |
| Should updates be automated? | Document evidence and approval |

**Expected:** a recommendation-only sizing proposal, not automatic production evictions.

## 10. Lab 6 — Investigate Pending Pods and node provisioning

```powershell
kubectl get pods -A --field-selector=status.phase=Pending -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl get nodes -L topology.kubernetes.io/zone -o wide
kubectl get nodepools
kubectl get nodeclaims -o wide
```

Karpenter commands require installed CRDs. For Cluster Autoscaler:

```powershell
kubectl -n kube-system get deployments | Select-String -Pattern 'cluster-autoscaler'
kubectl -n kube-system get configmap cluster-autoscaler-status -o yaml
```

### Failure-domain table

| Pending cause | Provisioning investigation |
|---|---|
| Insufficient CPU/memory | Node allocatable, requests, eligible instance types |
| Node-group maximum | CA min/max and cloud group limits |
| Karpenter NodePool limits | NodePool requirements, NodeClaims, limits |
| No cloud instance capacity | Zone/instance availability, quotas |
| Subnet IP exhaustion | CNI allocation, subnet free IPs |
| Taints/affinity | Compatible node labels and tolerations |
| PVC zone mismatch | PV topology and node placement |
| Max Pods per node | Kubelet/CNI Pod density |

**Expected:** distinguish scheduler constraints, autoscaler decisions, cloud launch and node bootstrap.

## 11. Lab 7 — Network and storage performance review

### Network

```promql
sum by (namespace, pod) (rate(container_network_receive_bytes_total[5m]))
```

```promql
sum by (namespace, pod) (rate(container_network_transmit_bytes_total[5m]))
```

Inspect packet drops, retransmits, conntrack pressure, CoreDNS timeouts, Pod IP capacity and cloud networking limits where metrics are available.

### Storage

Review PVC topology, cloud volume IOPS, throughput, latency, queue depth and datastore behavior.

```powershell
kubectl get pvc -A
kubectl get pv
kubectl get storageclasses
kubectl get events -A --sort-by=.lastTimestamp
```

**Expected:** distinguish free disk space from available I/O performance. A disk may have free bytes while being saturated by IOPS or throughput.

## 12. Lab 8 — Model downstream datastore capacity

Assume an API can scale to 20 replicas with a PostgreSQL connection pool maximum of 20 per Pod. Other clients reserve 100 connections, while the database's operational connection budget is 350.

```text
API potential connections = 20 × 20 = 400
Total potential connections = 400 + 100 = 500
Budget = 350
Potential overcommit = 150
```

### Required checks

- PostgreSQL: connection pools, active queries, locks, CPU and I/O.
- Redis: CPU, memory, command latency and eviction.
- Kafka: consumer lag, partitions and broker throughput.
- MongoDB: WiredTiger cache, query latency and replication.
- Elasticsearch/OpenSearch: shard size, thread pools, disk and merge I/O.
- External APIs: rate limits and retry storms.

**Expected:** calculate a safe HPA ceiling and/or pool configuration based on real dependency capacity, not simply CPU utilization.

## 13. Lab 9 — Forecast growth and failure-zone headroom

Assume peak application demand of 60 vCPU, forecast growth of 25%, and a three-zone cluster with 45 vCPU usable per zone.

```text
Forecast demand = 60 × 1.25 = 75 vCPU
Normal usable capacity = 3 × 45 = 135 vCPU
After losing one zone = 2 × 45 = 90 vCPU
Post-failure headroom = 90 - 75 = 15 vCPU
```

### Validate beyond arithmetic

- Pod scheduling/affinity and topology spread.
- Surviving-zone subnet IPs and instance quotas.
- Persistent volume topology and replication.
- DaemonSet overhead and node allocatable.
- Rolling upgrade surge and deployment availability.
- DB quorum and cross-zone dependency capacity.
- Provisioning time relative to recovery objectives.

**Expected:** a capacity plan that survives a realistic zone loss, not only normal load.

## 14. Lab 10 — Staging-only scaling exercise

This small demonstration uses CPU load to observe HPA; it is **not** a representative HTTP performance test.

Save `ch070-hpa.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch070
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scaling-demo
  namespace: ch070
spec:
  replicas: 1
  selector:
    matchLabels:
      app: scaling-demo
  template:
    metadata:
      labels:
        app: scaling-demo
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
  name: scaling-demo
  namespace: ch070
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: scaling-demo
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
      policies:
        - type: Pods
          value: 1
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 120
```

```powershell
kubectl apply -f .\ch070-hpa.yaml
kubectl -n ch070 rollout status deployment/scaling-demo --timeout=120s
kubectl -n ch070 get deployment,hpa,pods
kubectl -n ch070 describe hpa scaling-demo
kubectl -n ch070 top pods --containers
```

Observe scaling for several metrics intervals; do not assume immediate action. Stop if shared node pressure or unintended capacity impact occurs.

**Expected:** demonstrate a bounded HPA scale decision, then compare with a real application load test conducted through an approved tool.

## 15. Lab 11 — Production performance incident tabletop

**Scenario:** customer p95 latency reaches 2 s and error rate 5%. HPA recommends 24 replicas, but only 15 are Ready. Six Pods are Pending due to CPU requests and three fail readiness. Karpenter cannot launch instances because a NodePool limit is reached. PostgreSQL pool waits increase and Redis latency rises.

### Investigation plan

1. Declare incident severity from customer impact.
2. Compare request rate, latency, errors and Ready replicas.
3. Inspect HPA metrics and desired replica calculations.
4. Classify Pending Pods and readiness failures separately.
5. Check node provisioning, NodePool limits and cloud quotas.
6. Compare CPU throttling, memory pressure and storage latency.
7. Calculate downstream connection and cache capacity.
8. Test at least three competing causal hypotheses.
9. Choose one bounded mitigation with approver and rollback.
10. Verify application SLIs and dependency stability.

**Expected:** a defensible diagnosis of multiple bottlenecks without assuming that adding nodes automatically fixes latency.

## 16. Lab 12 — Performance and scaling acceptance report

### Before/after comparison

| Measure | Baseline | Peak test | Post-change | Acceptance |
|---|---|---|---|---|
| Requests/sec | Record | Record | Record | Target sustained |
| p95 latency | Record | Record | Record | Below agreed SLO |
| HTTP 5xx | Record | Record | Record | Below agreed SLO |
| Desired/Ready replicas | Record | Record | Record | No sustained gap |
| Pending Pods | Record | Record | Record | None from capacity |
| CPU throttling | Record | Record | Record | No harmful regression |
| Memory/OOM | Record | Record | Record | No OOM/eviction |
| DB pool wait | Record | Record | Record | Within budget |
| Network errors | Record | Record | Record | No regression |
| Storage latency | Record | Record | Record | Within dependency SLO |
| Cost/hour | Record | Record | Record | Within approved budget |

Fill with actual measurements. Do not fabricate benchmark results.

### Sign-off

```text
Cluster / namespace:
Load profile / test owner:
Test start and end (UTC):
Build / configuration version:
Metrics and dashboard evidence:
Baseline result:
Peak result:
Recovery result:
Bottlenecks confirmed:
Changes tested:
Rollback triggers:
Dependency safety:
Zone failure headroom:
Estimated monthly cost delta:
Outstanding risks:
SRE approval:
Application owner approval:
DBRE approval:
Technical review:
```

## 17. Operational troubleshooting matrix

| Symptom | Likely domain | Next evidence |
|---|---|---|
| HPA shows unknown metrics | Metrics Server/adapter | HPA Events, Metrics API |
| Desired > Ready replicas | Scheduling/startup | Pod Events, readiness |
| CPU low but latency high | DB/network/storage/locks | Traces, pool waits, I/O |
| CPU throttling | CPU limits | CFS throttling and latency |
| Memory OOM | Memory limit/working set | Previous termination, memory peaks |
| Pods Pending despite node headroom | Affinity, taints, PVC, Pod IPs | FailedScheduling |
| NodeClaim stuck | Karpenter/cloud capacity | NodeClaim status, provider errors |
| High DNS timeout rate | CoreDNS/CNI/upstream | Resolver and network metrics |
| Storage p99 rises | IOPS/throughput contention | Cloud volume and DB metrics |
| Costs rise without SLO gain | Scaling inefficiency | Replica, node and cost timelines |

## 18. Production rollout and rollback runbook

### Pre-change

1. Freeze baseline and capture exact versions/configuration.
2. Validate application and datastore capacity budgets.
3. Confirm SLOs, rollout surge, PDBs and graceful termination.
4. Confirm node provisioning, IP headroom and cloud quotas.
5. Establish approvers, maintenance window and rollback trigger.

### Execute

1. Change one control at a time where possible.
2. Use staged rollout/canary with bounded traffic.
3. Observe HPA, scheduler, node autoscaler and dependencies.
4. Stop or roll back if customer SLIs or dependency safety degrade.
5. Preserve change and incident timelines.

### Verify

1. Sustained successful throughput at target demand.
2. Latency/error SLO compliance.
3. Stable Ready replica count and no capacity-related Pending Pods.
4. Acceptable DB pool wait, Redis latency and storage I/O.
5. Stable autoscaler behavior and approved cloud cost.
6. Document operational ownership and follow-up tests.

**Do not roll back blindly** when schema/data changes or stateful failover make reversal unsafe; obtain application/DBRE approval.

## 19. Final capstone acceptance checklist

- [ ] Cluster and namespace verified; staging safety gates documented.
- [ ] Baseline SLIs, resource usage and dependency metrics captured.
- [ ] Load profile and abort thresholds approved.
- [ ] CPU, memory, network and storage bottlenecks assessed.
- [ ] HPA metrics, scaling behavior and conditions evaluated.
- [ ] VPA recommendation-only sizing reviewed or marked not installed.
- [ ] Cluster Autoscaler/Karpenter provisioning assessed.
- [ ] Pending Pods and readiness issues classified separately.
- [ ] PostgreSQL/Redis/Kafka or other dependency budgets modeled.
- [ ] One-node and one-zone failure headroom calculated.
- [ ] Bounded staging scaling demonstration completed or marked not run.
- [ ] Multi-layer incident tabletop completed.
- [ ] Before/after performance and cost evidence documented.
- [ ] Production rollout and rollback plan reviewed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

## 20. Cleanup

Only remove chapter-owned staging resources after capturing results:

```powershell
kubectl -n ch070 get deployments,hpa,pods
kubectl delete namespace ch070
```

Do not delete cluster autoscaler, Karpenter, VPA CRDs, production nodes or monitoring resources.

**Part 14 writing milestone:** Chapters 066–070 drafted. Runtime validation and independent technical review remain pending.

## 21. References

- [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Vertical Pod Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
- [Cluster Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler)
- [Karpenter Documentation](https://karpenter.sh/docs/)
- [Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Kubernetes Observability](https://kubernetes.io/docs/concepts/cluster-administration/observability/)

**Next:** Chapter 071 — Kubernetes Backup Strategy and RPO/RTO (Part 15).
