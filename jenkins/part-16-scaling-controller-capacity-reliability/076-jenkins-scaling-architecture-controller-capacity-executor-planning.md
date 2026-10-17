# Chapter 076 — Jenkins Scaling Architecture, Controller Capacity and Executor Planning

**Part 16 — Scaling, Controller Capacity and Reliability**  
**Audience:** Jenkins SRE, platform engineers, capacity planners and DevOps architects  
**Prerequisites:** Chapters 066–075; disposable Jenkins LTS, Prometheus/Grafana, test agents and representative synthetic jobs.

## Learning objectives

Understand Jenkins controller scaling boundaries, capacity modeling, executor sizing, queueing theory, workload segmentation, ephemeral agents, Kubernetes autoscaling, reliability constraints and production readiness gates.

## 1. Architecture: scale agents, protect controllers

```text
SCM/events → load balancer / ingress → Jenkins controller
                                         |
                               queue + orchestration
                                         |
                    +--------------------+--------------------+
                    |                    |                    |
              static VM agents    ephemeral K8s agents   specialized pools
                    |                    |                    |
               build/test            build/test            GPU/large jobs
```

Jenkins controllers coordinate Pipelines, scheduling, credentials and state. Adding more controller executors is **not** a general scaling strategy. Prefer zero build executors on production controllers where operationally appropriate and move builds to dedicated agents.

Multiple independent controllers partition workloads; they are **not** automatically active-active replicas sharing one `JENKINS_HOME`. Never mount one writable Jenkins home into multiple running controllers.

## 2. Capacity dimensions

| Dimension | Why it matters | Signals |
|---|---|---|
| Controller CPU | Scheduling, Pipeline CPS, plugin work | CPU saturation, threads |
| JVM heap/native memory | Pipeline state, plugin caches, threads | GC, post-GC occupancy, OOM |
| Jenkins home storage | Job config, build metadata, logs | IOPS, latency, disk/inodes |
| Queue throughput | Scheduling efficiency | Arrival rate, queue wait |
| Executor capacity | Parallel build slots | Busy/idle, label compatibility |
| Agent startup | Provisioning, image pull, remoting | Request-to-ready p95 |
| SCM/artifact dependencies | External throughput and latency | Error rate, timeouts |
| Kubernetes nodes | CPU/memory/pod/IP/volume limits | Pending, autoscaler lag |

## 3. Queueing model

For a stable workload, Little's Law states:

`L = λ × W`

where `L` is average jobs in the system, `λ` is arrival rate (jobs/second) and `W` is average time in the system (seconds). This relationship describes long-run averages under suitable stability conditions; it does not size burst capacity or directly provide p95 wait.

Illustrative example:
- 120 jobs/hour arrive: `λ = 2 jobs/minute`.
- Average executor occupation is 8 minutes/job.
- Offered concurrency is approximately `2 × 8 = 16` busy executors at 100% utilization.
- Planning only 16 slots leaves no buffer for variance, bursts, failures or provisioning latency.
- At a planning utilization of 70%, `ceil(16 / 0.70) = 23` compatible slots.

**Important:** 70% is an illustrative planning assumption, not a universal Jenkins threshold. Separate pools by labels, job duration, resource shape and criticality. Model service-time variance and arrival bursts using load tests/simulation rather than a single average.

## 4. Executor sizing

An executor is a scheduling slot, **not** a guaranteed CPU core. A CPU-heavy build may need multiple cores; an I/O-heavy job may tolerate greater concurrency. Start with measured per-build CPU, peak RSS, disk I/O, network and toolchain overhead.

Illustrative pool:

| Workload | Arrival rate | Avg duration | Offered concurrency | Planned slots at 70% |
|---|---:|---:|---:|---:|
| Unit tests | 60/hour | 6 min | 6 | 9 |
| Integration tests | 20/hour | 18 min | 6 | 9 |
| Packaging | 12/hour | 10 min | 2 | 3 |
| Release validation | 6/hour | 20 min | 2 | 3 |

Totals are illustrative and assume isolated pools. Validate actual concurrency, labels and resource availability.

## 5. Controller sizing and vertical scaling

Establish a baseline before increasing CPU, memory or disk performance. Correlate:
1. Controller CPU, load and throttling.
2. Heap occupancy after GC, pause times and native memory.
3. Thread counts, lock contention and Pipeline CPS load.
4. Jenkins home filesystem IOPS, latency and free capacity.
5. Queue time versus executor availability.
6. Plugin, JCasC and job-count growth.

Heap sizing must respect container limits and native overhead. Increasing heap may postpone symptoms without fixing a plugin leak or excessive Pipeline state.

## 6. Horizontal partitioning

Use multiple **independent** controllers for organizational, compliance or workload isolation when justified. Each has separate Jenkins home, credentials, plugin lifecycle, backup, monitoring and upgrade plan. Consider governance overhead and SCM/webhook routing. Jenkins does not provide generic shared-home active-active controller clustering.

## 7. Kubernetes ephemeral agent scaling

Inspect:
- Agent pod template labels, requests/limits, security context and image digest.
- ResourceQuota, LimitRange, topology and affinity.
- Cluster Autoscaler/Karpenter node provisioning time.
- Pod scheduling, image pulls, PVC binding and remoting.
- Cloud API quotas, IP exhaustion and node pool max size.
- Warm pools versus cold starts.

Autoscaling is not instantaneous. Include image-pull, node launch and registration latency in p95 queue-to-start budgets. Keep agents least-privileged and disposable.

## 8. Workload isolation and fairness

Create compatible pools for trusted builds, untrusted PRs, release signing, memory-heavy integration tests and special hardware. Apply job concurrency limits and priority policies deliberately. Avoid starving critical builds with unbounded retries or long-running test jobs.

## 9. SLOs and scaling triggers

Suggested candidate SLIs:
- p95 queue wait per workload class.
- p95 agent provisioning latency.
- Queue oldest age and queue depth.
- Executor utilization by compatible label.
- Infrastructure-caused build failure rate.
- Controller user-facing availability and JVM/IO health.

Trigger capacity changes from sustained signals and predicted load, not one queue spike. Use error budgets and business impact to prioritize.

## 10. Load and stress testing

Run only in an isolated lab:
1. Record baseline controller, queue and agent metrics.
2. Generate fixed synthetic workload with controlled arrival rate.
3. Measure 50%, 70%, 85% and burst utilization scenarios.
4. Record p50/p95 queue wait, provisioning p95, CPU, GC and I/O.
5. Reduce compatible agent pool and observe backpressure.
6. Restore capacity and verify queue drain.
7. Validate no secret leakage or excessive metric cardinality.
8. Document a capacity forecast and rollback.

Use bounded load and an abort threshold for CPU, memory, disk, queue and cloud spend.

## 11. Failure and troubleshooting scenarios

| # | Scenario | Diagnosis |
|---|---|---|
| 01 | Queue grows with idle executors | Label mismatch |
| 02 | Queue grows with all busy | Pool saturation |
| 03 | Controller CPU saturated | Threads/plugins |
| 04 | JVM GC thrashing | Heap and allocations |
| 05 | Native memory OOM | Container limits |
| 06 | Jenkins home IOPS bound | Storage latency |
| 07 | Build logs grow without bound | Retention |
| 08 | Agent pod Pending | Scheduler/quota |
| 09 | Cluster autoscaler delayed | Node launch |
| 10 | Registry pull bottleneck | Image size/cache |
| 11 | Node IP exhaustion | CNI/IP allocation |
| 12 | Cloud instance quota | Provider limits |
| 13 | High retry storm | Backoff policy |
| 14 | Long-running builds starve releases | Pool fairness |
| 15 | Executor overcommit | CPU/memory pressure |
| 16 | Workspace collisions | Isolation/concurrency |
| 17 | Controller executor overload | Agent migration |
| 18 | Multi-controller webhook misrouting | Routing |
| 19 | SCM rate limit | Dependency throughput |
| 20 | Artifact storage bottleneck | Dependency metrics |

## 12. Five production runbooks

### A. Queue saturation
Identify oldest queue reason and compatible labels; inspect executor utilization, build duration and arrival rate; add approved compatible capacity or throttle noncritical work; validate p95 queue wait.

### B. Controller CPU/GC bottleneck
Inspect JVM/threads/plugins and storage; mitigate workload and high-cost Pipelines; apply tested vertical scaling or plugin fix; verify GC, CPU and queue recovery.

### C. Kubernetes agent provisioning lag
Inspect pod events, quotas, autoscaler and image pulls; restore node/pod capacity and agent template; verify request-to-ready p95.

### D. Capacity forecast breach
Compare trend and peak workload to tested limits; model cost, headroom and failure scenarios; plan approved scaling; verify with load test and rollback.

### E. Multi-controller reliability
Confirm independent homes and routing; validate backup, access, monitoring and upgrade policies for each controller; recover impacted partition without unsafe shared-state writes.

## 13. Capacity worksheet

```text
Workload class / label:
Arrival rate (jobs/hour):
Average and p95 executor duration:
Peak burst rate and duration:
Per-build CPU / RSS / disk I/O:
Offered concurrency = arrivals/hour × duration_hours:
Target planning utilization:
Required compatible slots:
Current compatible slots:
Agent startup p95:
Controller CPU/GC/storage baseline:
Node/cloud quota and cost:
SLO and rollback:
Owner / review date:
```

## 14. Acceptance criteria

- [ ] Controller and agent scaling boundaries explained.
- [ ] No shared writable Jenkins home across controllers.
- [ ] Executor sizing based on measured resource demand.
- [ ] Little's Law applied with assumptions stated.
- [ ] Burst and variance assessed.
- [ ] Queue/agent p95 baselines measured.
- [ ] Kubernetes/cloud constraints validated.
- [ ] Load test bounded and recoverable.
- [ ] Capacity forecast and cost recorded.
- [ ] SLO, rollback and owner approved.

**Companion:** [Chapter 076 hands-on lab](labs/076-jenkins-scaling-architecture-controller-capacity-executor-planning-check.md).  
**Next:** Chapter 077 — Jenkins Kubernetes Agent Autoscaling, Dynamic Provisioning and Capacity Optimization.
