# Chapter 094 — Kubernetes Cost Management and FinOps

**Track:** Kubernetes Administration · **Part 19 — GitOps and Platform Automation**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** Kubernetes administrators, SREs, platform engineers, FinOps practitioners  
**Prerequisites:** Chapters 021–025, 046–050, 076–090, 091–093; kubectl, PowerShell, Prometheus or equivalent telemetry, read access to cloud billing exports, disposable staging cluster.

## Learning outcomes

Explain Kubernetes cost drivers; attribute shared spend; collect resource usage and billing evidence; diagnose idle and overprovisioned resources; right-size safely; compare autoscaling strategies; govern storage, networking and managed services; implement cost budgets and GitOps guardrails; demonstrate verified savings without violating SLOs.

## 1. FinOps operating model

FinOps is an ongoing collaboration between engineering, finance and business stakeholders. For Kubernetes, the operating loop is **inform → optimize → operate**. Build a baseline, identify an opportunity, make a controlled change, measure the outcome, and keep ownership and guardrails visible.

Distinguish:
- **Billed cost:** cloud-provider charges, including compute, disks, networking, load balancers, control plane, support and discounts.
- **Allocated cost:** an attribution model that assigns some shared cost to teams, namespaces or workloads.
- **Resource utilization:** CPU, memory, storage and network actually consumed.
- **Resource requests:** scheduler reservations; not a direct measure of usage or universally equivalent to billed cost.
- **Efficiency:** business or workload output per dollar, subject to reliability constraints.

A 30% reduction in CPU requests might enable node consolidation but produce **zero immediate savings** if the node count and purchased commitments do not change. Conversely, shrinking node capacity may reduce cost but cause scheduling failures or lost redundancy.

## 2. Kubernetes cost anatomy

| Driver | Typical billing unit | Important caveat |
|---|---|---|
| Worker nodes / VM instances | Instance-hours or seconds | Reserved/committed discounts change effective cost |
| Managed control plane | Cluster-hour | Varies by cloud and cluster type |
| Persistent storage | Provisioned GiB-month, IOPS, throughput | PVC request is not necessarily actual billed disk size |
| Load balancers | Hours, capacity units, data | Idle LBs may still cost money |
| NAT gateways and egress | Hours, processed data, transferred GiB | Cross-zone and cross-region traffic can dominate |
| Logging and metrics | Ingested/stored volume, retention | High-cardinality metrics amplify cost |
| Registry, backups, snapshots | Storage, transfer, operations | Retention and orphaned assets matter |
| GPUs | Accelerated node-hours | Utilization and scheduling fragmentation are major risks |

Cloud pricing, credits, taxes, discounts and product terms change; obtain current rates from your provider's billing exports rather than relying on static tutorial numbers.

## 3. Lab 01 — Establish a trustworthy baseline

Record cluster, provider, environment, time window, currency, billing account, discounts, amortization convention and whether shared infrastructure is included. Use a 7–30 day window when available, and preserve weekday/weekend seasonality.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get namespaces --show-labels
kubectl get deployments,statefulsets,daemonsets -A
kubectl get pvc -A
kubectl get svc -A
kubectl top nodes
kubectl top pods -A
```

`kubectl top` requires Metrics Server and provides point-in-time measurements, not historical p95 or billing cost. Export historical telemetry separately. Never publish billing account identifiers, sensitive labels or credentials in the tutorial repository.

**Evidence:** baseline date range, billed spend, node-hours, average and p95 utilization, SLO/error budget, workload throughput, and exclusions.

## 4. Lab 02 — Build tenant ownership and allocation

Use the governance labels from Chapter 093. Identify unallocated and shared costs explicitly rather than silently distributing them.

```powershell
kubectl get namespaces -L platform.example.com/team,platform.example.com/environment,platform.example.com/cost-center
kubectl get pods -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODE:.spec.nodeName
```

A useful allocation model is:

```text
Allocated tenant cost
  = directly attributable cloud charges
  + allocated node capacity cost
  + allocated shared platform cost
```

For node allocation, document whether you use **requested CPU/memory weighted allocation**, actual usage, or a hybrid. Include idle/unallocated capacity as its own category; do not count the same node cost twice. Namespace labels alone cannot attribute shared NAT, cross-namespace network or control-plane charges accurately.

## 5. Lab 03 — Install or evaluate a cost visibility tool

Options include OpenCost, Kubecost and cloud-native cost dashboards. Use a supported deployment guide and pin chart/application versions. In a disposable cluster, verify the tool's data sources, Prometheus retention, node price configuration and cloud billing integration.

```powershell
helm version
kubectl get pods -A
kubectl get storageclass
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"  "}{.status.capacity.cpu}{" CPU  "}{.status.capacity.memory}{" memory"}{"\n"}{end}'
```

Do not interpret an estimated cost dashboard as reconciled invoices. Compare aggregate estimated spend against the same-period cloud bill, document gaps, and exclude credits/taxes consistently.

**Acceptance:** visible per-namespace allocation, explicit idle/shared category, recorded data freshness and reconciliation variance.

## 6. Lab 04 — CPU and memory request-to-usage analysis

Requests influence scheduling and autoscaler decisions. Limits influence throttling and OOM risk. Analyze at least p50/p95 usage, peak windows, throttling, OOM restarts, replica count, and HPA behavior before modifying requests.

```powershell
kubectl get pods -A -o json
kubectl top pods -A --containers
kubectl describe deployment -n tenant-alpha
kubectl get hpa -A
kubectl get events -A --sort-by=.lastTimestamp
```

Representative PromQL, assuming standard kube-state-metrics and container metrics are available:

```promql
sum by (namespace, pod) (rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m]))
sum by (namespace, pod) (kube_pod_container_resource_requests{resource="cpu",unit="core"})
sum by (namespace, pod) (container_memory_working_set_bytes{container!="",image!=""})
sum by (namespace, pod) (kube_pod_container_resource_requests{resource="memory",unit="byte"})
```

Metric labels and availability vary by exporter version; verify queries against your environment. Do not size memory requests solely from averages. Account for startup spikes, JVM heap/off-heap, caches, batch jobs and failure recovery.

## 7. Lab 05 — Right-size one noncritical workload

Create a controlled experiment for one staging Deployment. Baseline requests, limits, p95 latency, throughput, CPU throttling, memory working set and restart rate. Modify requests in Git, deploy through the approved GitOps process, and compare equivalent traffic windows.

Example patch **for a disposable workload only**:

```powershell
kubectl set resources deployment/demo-api -n tenant-alpha --containers=demo-api --requests=cpu=200m,memory=256Mi --limits=cpu=1,memory=1Gi
kubectl rollout status deployment/demo-api -n tenant-alpha --timeout=180s
kubectl describe deployment demo-api -n tenant-alpha
```

In GitOps-managed environments, make the change in Git instead of relying on an imperative patch that reconciliation will overwrite. The names and values above are examples, **not** sizing recommendations. Roll back if p95 latency, errors, throttling, OOMs or scheduling regress beyond the approved guardrails.

## 8. Lab 06 — Node utilization, bin packing and consolidation

```powershell
kubectl describe nodes
kubectl get pods -A -o wide
kubectl get pdb -A
kubectl get nodes -L topology.kubernetes.io/zone
```

Compare **requested** capacity with **allocatable** capacity, not physical capacity. Account for kube/system reservations, DaemonSet overhead, topology spread, affinity, taints, local storage and PodDisruptionBudgets. Test whether workloads can fit after losing one node or zone according to the service's availability target.

Do not drain a production node merely to demonstrate savings. A proposed consolidation is only an opportunity until an actual node is terminated or a purchased commitment changes.

## 9. Lab 07 — Autoscaling economics

Compare HPA, VPA recommendations, Cluster Autoscaler, Karpenter and provider-managed node autoscaling. Each solves a different problem:
- **HPA:** changes replica counts based on observed metrics.
- **VPA:** recommends or changes Pod resources according to its configured mode and version.
- **Cluster Autoscaler/Karpenter:** changes node capacity based on scheduling requirements and provider constraints.

```powershell
kubectl get hpa -A
kubectl get pdb -A
kubectl get nodes --show-labels
kubectl get events -A --sort-by=.lastTimestamp
```

Model scale-up delay, minimum nodes, consolidation policies, workload disruption, reserved capacity and warm-up time. HPA and VPA interactions require careful review, especially when both affect CPU/memory-based scaling.

**Acceptance:** autoscaling improves utilization while preserving startup time, availability and workload SLOs under peak load.

## 10. Lab 08 — Spot/preemptible and commitment strategy

Use interruptible nodes only for suitable workloads. Evaluate checkpointing, retries, disruption budgets, termination signals, topology spread and minimum on-demand capacity. Reserved Instances/Savings Plans/committed-use discounts affect billing independently of cluster scheduler behavior.

Compare scenarios using a consistent time horizon:

```text
Expected net benefit
  = baseline effective spend
  - projected effective spend
  - migration/operations overhead
  - expected interruption/recovery impact
```

Do not treat a provider's list price as the organization's effective rate when commitments or discounts apply.

## 11. Lab 09 — Storage, snapshots and data lifecycle

```powershell
kubectl get pv,pvc -A
kubectl get storageclass
kubectl describe pvc -n tenant-alpha
kubectl get volumesnapshot -A
```

The VolumeSnapshot CRD may not be installed; an error is not proof that snapshots do not exist in the cloud account. Inspect storage class reclaim policies, provisioned capacity, performance tier, IOPS/throughput charges, orphaned disks, snapshots and retention. PVC deletion can destroy data depending on reclaim policy. Never delete a production volume to prove a cost hypothesis.

For stateful workloads, prioritize recovery point/recovery time requirements over disk-cost reduction.

## 12. Lab 10 — Network, ingress and observability cost

Inventory load balancer Services, Ingress/Gateway objects, external IPs and log retention:

```powershell
kubectl get svc -A -o wide
kubectl get ingress -A
kubectl get gateway -A
kubectl get daemonset -A
```

Gateway API resources may not exist in all clusters. Correlate cloud load balancers, NAT gateways, cross-zone transfer, internet egress, metrics cardinality and log ingestion with real billing line items. An apparently idle Kubernetes Service can still back a billable load balancer.

## 13. Lab 11 — Budgets, alerts and governance

Define monthly budgets by environment/team, variance thresholds, ownership and escalation. Configure provider-native budgets and anomaly detection; use GitOps to enforce requests/limits, labels, quotas and approved instance/storage classes where appropriate.

Example governance contract:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: staging-budget
  namespace: tenant-alpha
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    pods: "20"
```

A ResourceQuota is a **capacity governance** mechanism, not a dollar budget. Pair it with billing alerts. Before enforcement, check that burst capacity, emergency scaling and availability requirements remain possible.

## 14. Lab 12 — Forecast growth and capacity

Forecast separately for baseline traffic, peak traffic, data growth, redundancy and new services. Model at least three scenarios: current trend, optimized workload, and peak/DR event.

```text
Forecast spend = projected node-hours × effective node rate
               + projected storage and IOPS charges
               + projected networking and platform charges
               + other billed services
```

For uncertainty, provide a range and assumptions rather than a single precise number. Track cost per request/job/customer only when the denominator is defined consistently and does not incentivize unsafe underprovisioning.

## 15. Lab 13 — Cost regression incident simulation

In staging, create an intentionally oversized resource request or excessive replicas for a disposable application. Observe unschedulable Pods or capacity growth **without enabling uncontrolled cloud spend**. Set strict node limits or use a fixed-size disposable cluster.

Capture:
1. Detection source and timestamp.
2. Workload/commit causing the regression.
3. Resource request or replica delta.
4. Estimated vs billed impact, clearly distinguished.
5. GitOps rollback and recovery time.
6. SLO and capacity impact.
7. Preventive guardrail and owner.

Troubleshooting matrix:

| Symptom | Check first | Common explanation |
|---|---|---|
| Bill rises while CPU stays flat | Node-hours, LB, NAT, disks | Non-CPU cost drivers |
| Requests fall but bill does not | Actual node count, commitments | No capacity removed |
| Pods Pending after right-sizing | Events, allocatable, affinity, quota | Scheduler constraints |
| Latency rises after savings change | Throttling, OOM, saturation | Underprovisioning |
| Cost dashboard differs from bill | Time zone, discounts, idle allocation | Different accounting model |
| Autoscaler fails to consolidate | PDBs, topology, DaemonSets, reservations | Safe disruption constraints |

## 16. Lab 14 — FinOps acceptance and executive reporting

Produce a one-page change report:

| Measure | Baseline | After | Source |
|---|---|---|---|
| Effective billed cost | Record | Record | Cloud billing export |
| Node-hours | Record | Record | Cloud inventory/billing |
| Requested CPU/memory | Record | Record | kube-state-metrics |
| p95 latency / error rate | Record | Record | Application monitoring |
| Pending Pods / OOMs | Record | Record | Kubernetes and telemetry |
| Unallocated spend | Record | Record | Allocation model |
| Cost per business unit | Record | Record | Billing + business metrics |

**Acceptance checklist:**
- [ ] Baseline and comparison windows are equivalent and documented.
- [ ] Effective billing rates, discounts, currency and shared costs reconciled.
- [ ] Every optimization has an owner, hypothesis and rollback.
- [ ] Production SLOs, resilience and DR capacity preserved.
- [ ] Idle/shared/unallocated costs reported honestly.
- [ ] Node, storage, network and observability costs included.
- [ ] Alerts, anomaly response and governance approvals verified.
- [ ] Actual savings are distinguished from estimates.
- [ ] Runtime lab evidence and independent technical review recorded.

## Cleanup and recovery

Delete only disposable objects created for the labs. Restore test resource requests and replicas through GitOps. Verify autoscaler settings, PDBs, service health and billing alerts. **Never delete production PVCs, nodes, load balancers or snapshots merely to complete a tutorial.**

## Production runbook: monthly cost review

1. Reconcile cloud invoice and cost-allocation report for the same time window.
2. Review top spend changes by service, team, environment and billing SKU.
3. Identify idle resources, overrequests, orphaned storage and data-transfer anomalies.
4. Rank opportunities by verified dollar impact, engineering effort and SLO risk.
5. Approve one controlled change at a time; preserve rollback.
6. Validate node-hours/billed savings and service reliability after the change.
7. Update budget forecast, exceptions, ownership and the incident backlog.

## Production takeaways

FinOps succeeds when teams optimize **verified effective spend** while protecting reliability. Requests, utilization and allocation are evidence, but cloud billing is the source of truth for charges. Treat every optimization as a reversible production change.

**Draft status:** this chapter has not been runtime-validated or independently reviewed.

**Next:** Chapter 095 — GitOps and Governance Project (Part 19 capstone).
