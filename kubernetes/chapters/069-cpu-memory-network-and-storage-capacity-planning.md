# Chapter 069 — CPU, Memory, Network and Storage Capacity Planning

**Track:** Kubernetes Administration · **Part 14 — Autoscaling and Capacity Management**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, cloud and platform engineers  
**Prerequisites:** Chapters 024–025 and 066–068; kubectl; Windows PowerShell; Prometheus/Grafana or equivalent monitoring; approved read-only cluster access

## 1. Production scenario

A Kubernetes platform hosts API services, background workers and stateful data services. During a traffic spike, HPA increases API replicas but several Pods remain Pending. Node CPU usage appears moderate, yet the scheduler reports insufficient CPU. Some nodes experience memory pressure; a data pipeline encounters high disk latency; and a cluster running AWS VPC CNI approaches its Pod IP capacity.

**Goal:** create a defensible, multi-dimensional capacity plan that translates observed workloads, Kubernetes scheduling requests, failure-zone resilience and cloud infrastructure limits into actionable headroom and scaling decisions.

### Learning objectives

1. Distinguish node capacity, allocatable resources, requests, limits and observed usage.
2. Model CPU scheduling, throttling, overcommit and burst capacity.
3. Plan memory headroom, eviction thresholds, OOM risk and working-set growth.
4. Calculate Pod density, CNI IP/ENI constraints and network bandwidth needs.
5. Evaluate storage capacity, IOPS, throughput, latency and volume topology.
6. Forecast demand, define SLO-driven headroom and model zone/node failures.
7. Connect HPA, VPA and node autoscaling to real capacity constraints.
8. Design safe capacity controls for PostgreSQL, MongoDB, Elasticsearch, Redis and Kafka.
9. Produce an auditable capacity report and acceptance checklist.

## 2. Capacity dimensions and failure modes

```text
Workload demand
     |
     +-- CPU requests / limits / throttling
     |
     +-- Memory requests / limits / OOM / eviction
     |
     +-- Network bandwidth / packets / conntrack / IPs
     |
     +-- Storage bytes / IOPS / throughput / latency
     |
     +-- Pod count / DaemonSet overhead / scheduling constraints
     |
     +-- Availability zones / node loss / rollout surge
     |
     +-- Cloud quotas / node pools / autoscaling limits
     |
     +-- Downstream database / queue / cache capacity
```

**Core principle:** a cluster can have spare CPU yet be unable to schedule Pods because of memory, taints, affinity, topology, Pod count, IP availability or persistent volume constraints.

## 3. Lab 1 — Inventory cluster and node capacity

```powershell
kubectl config current-context
Get-Date -Format o
kubectl get nodes -L topology.kubernetes.io/zone -o wide
kubectl describe nodes
kubectl top nodes
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
```

### Node capacity versus allocatable

| Concept | Meaning |
|---|---|
| Capacity | Total resource capacity reported by kubelet |
| Allocatable | Resource budget available for Pods after reservations |
| Requests | Scheduler reservation used for placement |
| Limits | Runtime enforcement ceilings where applicable |
| Usage | Measured consumption at a specific time |
| Headroom | Remaining usable capacity after policy and failure reserve |

```powershell
kubectl get nodes -o custom-columns=NAME:.metadata.name,CPU_CAP:.status.capacity.cpu,CPU_ALLOC:.status.allocatable.cpu,MEM_CAP:.status.capacity.memory,MEM_ALLOC:.status.allocatable.memory,PODS_ALLOC:.status.allocatable.pods
```

**Expected:** node allocatable differs from raw instance capacity. Record cluster and zone totals, not only averages.

## 4. Lab 2 — Calculate CPU requests and utilization

```powershell
$ns = 'REPLACE_WITH_NAMESPACE'
kubectl -n $ns get deployments,statefulsets,daemonsets -o wide
kubectl -n $ns get pods -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName,PHASE:.status.phase
kubectl -n $ns top pods --containers
kubectl describe node REPLACE_WITH_NODE
```

### CPU capacity model

```text
Node allocatable CPU: 7.5 cores
System / DaemonSet Pod requests: 0.8 cores
Application Pod requests: 5.9 cores
Remaining schedulable request headroom: 0.8 cores
```

A node may show 40% actual CPU usage but still be unable to schedule a Pod requesting 1 core because the scheduler evaluates requests and placement constraints.

### CPU throttling investigation

CPU throttling is associated with CPU quota enforcement, not simply high CPU utilization. Compare CPU demand, limits and throttling metrics.

```promql
sum by (namespace, pod, container) (
  rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m])
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
  ),
  1e-9
)
```

Metric availability and labels depend on the container runtime and monitoring pipeline. Throttled-period ratio alone does not quantify lost CPU time or prove customer impact.

**Expected:** separate request saturation, actual CPU saturation and CPU limit throttling.

## 5. Lab 3 — Model memory capacity and eviction risk

```powershell
kubectl top nodes
kubectl -n $ns top pods --containers
kubectl describe node REPLACE_WITH_NODE
kubectl get nodes -o wide
kubectl get events -A --sort-by=.lastTimestamp
```

### Memory model

```text
Node allocatable memory: 30 GiB
System / DaemonSet requests: 2 GiB
Application requests: 24 GiB
Schedulable request headroom: 4 GiB

Observed working set peak: 28 GiB
Memory pressure risk: high despite request headroom
```

### Memory-specific cautions

- Memory is not CPU: sustained memory overuse cannot be time-shared safely.
- Requests affect scheduling and eviction priority; limits can trigger container OOM.
- Page cache and reclaimable memory require careful interpretation.
- `kubectl top` is a point-in-time snapshot, not peak usage history.
- Node-level `MemoryPressure` and container `OOMKilled` are different failure modes.
- Bursty workloads need peak-aware sizing and sufficient failover reserve.

### Prometheus example

```promql
sum by (namespace, pod, container) (
  container_memory_working_set_bytes{container!="",image!=""}
)
```

**Expected:** estimate working-set peaks, OOM history, eviction exposure and memory headroom per zone.

## 6. Lab 4 — Pod density and scheduling fragmentation

```powershell
kubectl get nodes -o custom-columns=NAME:.metadata.name,PODS_ALLOC:.status.allocatable.pods
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl get daemonsets -A
```

### Pod density constraints

1. Kubelet `maxPods` and node allocatable Pod count.
2. CNI IP address allocation and per-instance interface limits.
3. CPU/memory request fragmentation.
4. DaemonSet overhead on each additional node.
5. Taints, selectors, topology spread and affinity.
6. PVC/volume attachment limits and zone placement.
7. OS and runtime limits, including PID and conntrack capacity.

**Expected:** a Pod may be Pending even when CPU and memory are available.

## 7. Lab 5 — Network bandwidth, packets and IP capacity

### Network capacity checklist

| Dimension | Measurement |
|---|---|
| Throughput | Bytes/s ingress and egress |
| Packet rate | Packets/s and drops |
| Connections | Active connections and conntrack usage |
| Latency | Pod-to-Pod, Pod-to-Service, external dependencies |
| Errors | Retransmits, interface drops, CNI failures |
| IP capacity | Available subnet IPs and Pod IP allocation |
| DNS | CoreDNS queries, latency, errors and upstream timeouts |

```powershell
kubectl -n kube-system get pods -o wide
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
```

### Prometheus network examples

```promql
sum by (namespace, pod) (
  rate(container_network_receive_bytes_total[5m])
)
```

```promql
sum by (namespace, pod) (
  rate(container_network_transmit_bytes_total[5m])
)
```

```promql
sum by (namespace, pod) (
  rate(container_network_receive_errors_total[5m])
)
```

### EKS and AKS notes

- **EKS:** verify AWS VPC CNI mode, subnet free IPs, ENI/prefix capacity, security groups and per-instance Pod limits.
- **AKS:** verify Azure CNI or overlay mode, subnet/IP allocation, VMSS limits and NSG/routing constraints.
- Network bandwidth is instance-dependent and shared across workload traffic, storage and cluster operations.
- High packet rate or conntrack exhaustion can degrade services even below nominal byte-throughput limits.

**Expected:** network capacity assessment includes IP availability, packets and connections, not bandwidth alone.

## 8. Lab 6 — Storage capacity, IOPS, throughput and latency

```powershell
kubectl get storageclasses
kubectl get pv
kubectl get pvc -A
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
```

### Storage capacity dimensions

| Dimension | Impact |
|---|---|
| Volume bytes | Data retention and free-space reserve |
| IOPS | Small random reads/writes |
| Throughput | Sequential transfer, snapshots, merges |
| Latency | Query/transaction response time |
| Queue depth | Storage saturation and waiting I/O |
| Volume attachments | Pod scheduling and failover |
| Zone topology | Stateful placement and recovery |
| Snapshot/backup capacity | Recovery and data protection |

### Throughput and IOPS illustration

```text
Average I/O size = 16 KiB
Demand = 4,000 IOPS
Approximate data rate = 4,000 × 16 KiB = 62.5 MiB/s

A disk rated for 5,000 IOPS but only 50 MiB/s throughput
may saturate throughput before reaching its IOPS limit.
```

These are illustrative figures. Real storage limits vary by cloud volume, provisioned performance, instance caps, queueing and workload pattern.

**Expected:** identify which resource is the binding constraint rather than interpreting free disk space as sufficient storage capacity.

## 9. Lab 7 — Stateful datastore capacity planning

### PostgreSQL

- CPU, memory and shared buffers versus OS page cache.
- Connection pool size and query concurrency.
- WAL generation, retention and replication slots.
- Storage latency, checkpoints, vacuum and failover reserve.
- PVC topology and recovery time.

### MongoDB

- WiredTiger cache, working set and memory headroom.
- Oplog retention, replication lag and disk capacity.
- Journal and checkpoint I/O.
- Replica set quorum and failover placement.

### Elasticsearch / OpenSearch

- Heap versus filesystem cache.
- Shard count/size, merge and recovery I/O.
- Query concurrency and thread-pool rejections.
- Disk watermark headroom and replica placement.
- Capacity to recover after a node/zone failure.

### Redis

- Memory fragmentation, eviction policy and persistence overhead.
- CPU saturation on command execution paths.
- Replica/sentinel/cluster topology and failover.
- Headroom for fork, snapshot or AOF rewrite.

### Kafka

- Partition count, broker CPU/network and disk throughput.
- Replication factor and inter-broker replication bandwidth.
- Retention, ISR health and recovery capacity.
- Zone-aware placement and broker failure reserve.

**Rule:** do not increase application replicas without checking downstream datastore and queue capacity.

## 10. Lab 8 — Forecast growth and reserve headroom

### Forecasting model

```text
Current peak demand = 60 vCPU
Expected growth over 6 months = 30%
Forecast peak = 60 × 1.30 = 78 vCPU

Planned usable capacity = 110 vCPU
Headroom after forecast peak = 110 - 78 = 32 vCPU
Headroom fraction = 32 / 110 = 29.1%
```

The 30% growth rate is an example. Use measured trends, known launches, batch schedules and confidence ranges.

### Required forecasts

1. Normal weekday demand.
2. Peak hour and burst demand.
3. Batch/ingestion overlap.
4. Rolling upgrade surge.
5. One-node and one-zone failure.
6. Seasonal or release-driven growth.
7. Backup, reindex and recovery operations.
8. Cloud quota and budget constraints.

**Expected:** a forecast with assumptions, sensitivity analysis and refresh cadence.

## 11. Lab 9 — Zone failure and N+1 resilience planning

Assume a three-zone cluster with 30 vCPU usable per zone and peak demand of 55 vCPU.

```text
Normal total usable capacity = 3 × 30 = 90 vCPU
After one zone fails = 2 × 30 = 60 vCPU
Peak demand = 55 vCPU
Remaining after zone loss = 5 vCPU
```

The arithmetic indicates potential capacity, but workload placement, Pod IPs, storage zone constraints, PDBs and actual node allocatable resources still determine recoverability.

### Resilience checks

- Can replacement Pods schedule in surviving zones?
- Do anti-affinity/topology rules block placement?
- Are subnet IPs and cloud quotas sufficient?
- Can stateful PVCs attach or replicate across zones?
- Does the load balancer rebalance traffic?
- Can databases preserve quorum and write durability?
- Does the autoscaler provision quickly enough for the SLO?

**Expected:** failure headroom is validated through placement and dependency constraints, not only aggregate CPU.

## 12. Lab 10 — HPA, VPA and node autoscaler coordination

```powershell
kubectl get hpa -A
kubectl get vpa -A
kubectl get nodes -o wide
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
```

The VPA command requires the VPA CRD; skip if not installed.

### Control-loop interactions

| Controller | Changes | Capacity implication |
|---|---|---|
| HPA | Replica count | More Pods and dependency connections |
| VPA | Resource requests | Changes Pod scheduling footprint |
| Cluster Autoscaler | Node group size | Adds/removes nodes |
| Karpenter | NodeClaims and nodes | Dynamic instance provisioning |

**Expected:** identify cases where HPA demand, VPA request changes and node autoscaling create Pending Pods or unexpected cloud spend.

## 13. Lab 11 — Capacity incident tabletop

**Scenario:** an application rollout coincides with a batch ingestion job. HPA scales from 12 to 24 Pods. CPU usage averages 55%, but eight Pods remain Pending due to memory requests. Redis memory usage is near its limit, Elasticsearch merges saturate disk throughput, and a zone has only a few remaining subnet IPs.

### Investigation tasks

1. Capture customer SLIs and incident scope.
2. Compare CPU requests/usage and memory requests/usage.
3. Identify scheduler constraints for Pending Pods.
4. Inspect network IP availability and CNI health.
5. Correlate storage IOPS, throughput and latency.
6. Evaluate Redis and Elasticsearch bottlenecks.
7. Model capacity after a node/zone failure.
8. Choose safe mitigation with approver and rollback.
9. Verify recovery across applications and data services.
10. Document preventive headroom and alert thresholds.

**Expected:** distinguish the multiple independent bottlenecks and avoid assuming that more CPU solves the incident.

## 14. Lab 12 — Build the capacity report

### Capacity report template

```text
Report date / owner:
Cluster / region / environment:
Measurement window:
Current node count and instance types:
CPU capacity / allocatable / requested / p95 usage:
Memory capacity / allocatable / requested / peak working set:
Pod count limits and peak density:
Network throughput / packet rate / conntrack:
Subnet and Pod IP headroom:
Storage bytes / IOPS / throughput / p99 latency:
Cloud quotas / autoscaler bounds:
Workload growth forecast:
One-node / one-zone failure scenario:
Stateful dependency bottlenecks:
SLO and cost implications:
Recommended changes:
Change owner / target date:
Validation and rollback plan:
```

### Acceptance evidence

- Source dashboards and timestamps.
- Per-zone and per-node breakdowns.
- Forecast assumptions and sensitivity range.
- Explicit bottleneck ranking.
- Approved action owners and verification criteria.

## 15. Production troubleshooting matrix

| Symptom | Capacity dimension | First check |
|---|---|---|
| Pending despite low CPU usage | CPU/memory requests, placement | `describe pod`, allocatable |
| CPU throttling and high latency | CPU limits | CFS metrics and SLO |
| OOMKilled during peak | Memory limits/working set | Termination reason and memory peaks |
| Node MemoryPressure | Node memory | Node conditions, evictions |
| CNI IP allocation failure | Network IP capacity | CNI logs and subnet IPs |
| High retransmits | Network congestion/path | Interface and network metrics |
| High disk latency with free space | Storage IOPS/throughput | Volume metrics and queueing |
| PVC attach failures | Storage topology/limits | Events, CSI, zone |
| HPA maxed but latency high | App/dependency capacity | HPA and downstream metrics |
| Cloud spend spike | Autoscaling/capacity policy | Node claims, instance mix |

## 16. Operational runbook

### Detect

- SLO breach, sustained Pending Pods or throttling.
- Node pressure, Pod IP exhaustion or network drops.
- Disk I/O saturation, PVC pressure or datastore backlogs.
- Node autoscaler limits or cloud quota exhaustion.

### Diagnose

1. Confirm blast radius and measurement window.
2. Compare requests, allocatable and usage by node/zone.
3. Identify the binding resource and placement constraints.
4. Evaluate cloud and network limits.
5. Inspect downstream dependencies and storage.
6. Model failure reserve and rollout surge.

### Mitigate

1. Choose a low-risk, reversible action.
2. Avoid blind limit increases or unbounded autoscaling.
3. Preserve stateful quorum, replication and backup safety.
4. Confirm cloud quota, cost and security approvals.
5. Verify customer SLIs and resource headroom after the change.

### Prevent

- Quarterly capacity review plus release-triggered reforecast.
- Alerts on resource headroom, not only usage.
- SLO-aware scaling and dependency capacity budgets.
- Per-zone resilience tests and node provisioning drills.
- Storage performance acceptance before production migrations.

## 17. Capacity acceptance checklist

- [ ] Capacity versus allocatable understood.
- [ ] CPU requests, usage and throttling evaluated.
- [ ] Memory requests, limits, OOM and eviction risk evaluated.
- [ ] Pod density and scheduling fragmentation reviewed.
- [ ] Network bandwidth, packet rate, conntrack and IP headroom assessed.
- [ ] Storage bytes, IOPS, throughput and latency evaluated.
- [ ] Stateful datastore bottlenecks documented.
- [ ] Growth forecast with assumptions completed.
- [ ] One-node and one-zone failure headroom modeled.
- [ ] HPA/VPA/node autoscaler interactions reviewed.
- [ ] Capacity incident tabletop completed.
- [ ] Capacity report, action owners and verification plan produced.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

## 18. Cleanup

This chapter uses read-only commands and paper-based modeling; no cluster resources need to be created or deleted. If additional diagnostics are deployed in a dedicated staging environment, remove only those approved temporary resources after collecting evidence.

**Status:** Draft — runtime validation and technical review pending.

## 19. References

- [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Node Allocatable Resources](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Scheduling, Preemption and Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/)
- [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Cluster Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler)
- [Karpenter Documentation](https://karpenter.sh/docs/)

**Next:** Chapter 070 — Kubernetes Performance and Scaling Project (Part 14 capstone).
