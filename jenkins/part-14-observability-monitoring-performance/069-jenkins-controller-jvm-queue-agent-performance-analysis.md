# Chapter 069 — Jenkins Controller, JVM, Queue and Agent Performance Analysis

**Part 14 — Observability, Monitoring and Performance**  
**Audience:** Jenkins SRE, platform and performance engineers.  
**Prerequisites:** Chapters 066–068, isolated Jenkins LTS, Prometheus/Grafana, test agents.

## Learning outcomes
Establish performance baselines; analyze controller CPU, JVM heap and garbage collection, threads, Jenkins home I/O, queue wait, executor utilization and Kubernetes agent provisioning. Isolate bottlenecks, conduct bounded tests and validate recovery.

## 1. Performance architecture

```text
Webhook → queue → agent provisioning → executor → checkout → build/test → publish
             |             |               |           |
          labels/locks   K8s/cloud      capacity     SCM/CPU/I/O
Controller: scheduling + CPS Pipeline state + UI/API + plugins + Jenkins home
```

Total delivery time comprises trigger delay, queue wait, provisioning, checkout, execution and publishing. Instrument each separately where supported. Application test failure is not necessarily Jenkins infrastructure failure.

## 2. Controller baseline

| Signal | Collect | Why |
|---|---|---|
| CPU | p50/p95 and saturation | Busy controller/plugin |
| JVM heap | after-GC used/max | Retained memory |
| GC | pause distribution and frequency | Responsiveness |
| Threads | runnable/blocked/waiting | Contention |
| Jenkins home | disk latency, capacity, inodes | Metadata bottleneck |
| Queue | p50/p95/p99 wait and oldest item | Scheduling latency |
| Executors | busy/available per label | Capacity |
| Agents | request-to-ready p95 | Cloud provisioning |
| Pipelines | stage duration and failure category | User impact |

Record core, Java, plugin versions, JVM flags, agent pools, storage class and baseline workload. Compare normal, peak and maintenance windows.

## 3. JVM and thread diagnostics

A high heap occupancy alone does not prove a leak. Correlate **post-GC** occupancy, allocation rate, pause times, native memory, container limit and restarts. Increasing heap without checking memory limits can cause OOMKilled.

```sh
# Run only with approval and appropriate JDK tools.
jcmd <PID> VM.flags
jcmd <PID> GC.heap_info
jcmd <PID> Thread.print -l > thread-dump.txt
```

Replace PID with the Java process. Capture repeated thread samples rather than assuming a single dump proves contention. Dumps can contain sensitive data; secure and expire them. Large heap dumps may pause workloads and consume significant disk.

## 4. Controller and plugin overhead

Controller executors should normally be zero for production builds. Excessive Pipeline CPS work, plugin callbacks, queue scheduling, high job count, slow Jenkins home I/O and controller-side builds can impair responsiveness. Compare plugin changes and controller metrics before/after upgrades; validate on staging before rollback or resizing.

## 5. Queue analysis

Queue growth may indicate:
1. No compatible online executor for the requested label.
2. Lock or throttle restrictions.
3. Kubernetes Pending pods, quotas or image pulls.
4. Cloud API throttling or agent startup delay.
5. Controller CPU/GC/storage pressure.

Check the **oldest queued item and its reason** alongside p95 wait. Low executor utilization with a long queue often means a label or lock issue rather than insufficient total capacity.

## 6. Executor capacity and throughput

A rough homogeneous-pool upper bound:

```text
builds per minute ≈ effective executors / mean execution minutes
```

This omits burst arrivals, heterogeneity, provisioning delays and contention. Capacity decisions must be validated with load tests and latency SLOs. Do not solve agent starvation by increasing controller executors.

## 7. Kubernetes agents

```sh
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl describe pod <agent-pod> -n jenkins-build
kubectl top pods -n jenkins-build
```

Replace namespace and pod placeholders. `kubectl top` requires metrics support. Correlate Pending/ImagePullBackOff/OOMKilled/eviction events with queue wait and remoting logs. Review IAM/RBAC, PVCs, node selectors, autoscaler/Karpenter and image registry latency.

## 8. Controlled load experiment

1. Capture 15-minute baseline.
2. Run synthetic lightweight Pipelines at a low arrival rate.
3. Increase arrivals in bounded steps while measuring queue p95, throughput, CPU, GC and agent startup.
4. Inject a **lab-only** label mismatch or reduced agent capacity.
5. Identify the dominant latency component and stop at preset CPU, memory, queue-age or error thresholds.
6. Restore configuration and compare recovery against baseline.

Never load-test a shared production controller.

## 9. Example SLOs

- Synthetic controller availability >= 99.9% monthly.
- CI p95 queue wait < 120 seconds during supported hours.
- Warm-pool agent provisioning p95 < 90 seconds.
- Infrastructure-attributable build failures < 1% over seven days.

These are illustrative targets, not Jenkins defaults. Agree on objectives by workload class and baseline.

## 10. Troubleshooting matrix

| Symptom | Suspect | Validate |
|---|---|---|
| Slow UI | GC, CPU, plugin, I/O | JVM and storage |
| Heap grows after GC | Retained memory | Post-GC trend |
| Long pauses | GC pressure | GC logs |
| CPU saturated | Groovy/plugin/GC | Thread samples |
| Blocked threads | Contention | Repeated dumps |
| Home disk latency | Storage contention | I/O metrics |
| Disk full | Logs/artifacts | Retention inventory |
| Queue grows | Agents/labels/locks | Queue reasons |
| Idle agents + queue | Label mismatch | Job constraints |
| Pending pods | Quota/scheduler | K8s events |
| Image pulls slow | Registry/network | Pod events |
| Agent OOMKilled | Limits/workload | Pod status |
| Remoting disconnects | Network/version | Logs |
| Slow stages | SCM/build workload | Stage timings |
| Post-upgrade regression | Plugin/core | Version diff |
| Scaling ineffective | Wrong bottleneck | Before/after |

## 11. Five production runbooks

### A. Controller CPU/GC incident
Verify user impact and recent changes; inspect CPU, GC, heap and threads; isolate plugin/Pipeline overhead; apply approved remediation or rollback; confirm UI, queue and representative build recovery.

### B. Queue starvation
Identify oldest queued jobs and labels; inspect compatible executors, locks, quotas and agent provisioning; restore correct pool capacity or fix constraints; verify p95 queue recovery.

### C. Jenkins home I/O saturation
Measure disk latency, capacity and filesystem errors; identify backup/log/retention spikes; preserve state; make approved storage or retention changes; verify latency and headroom. Never delete state ad hoc.

### D. Kubernetes agent failures
Review pod events, scheduling, image pulls, RBAC, network and resource limits; restore templates or pool; validate remoting and synthetic build.

### E. Performance regression after upgrade
Compare core/Java/plugins and baseline percentiles; reproduce in staging; identify changed components; roll back approved image/config if warranted; record RCA and acceptance gate.

## 12. Acceptance criteria

- [ ] Baseline and peak measurements documented.
- [ ] JVM CPU/heap/GC/threads and Jenkins home observable.
- [ ] Queue reasons and percentiles measured.
- [ ] Executors segmented by compatible label/pool.
- [ ] Agent provisioning and Kubernetes events correlated.
- [ ] Bounded load test with stop conditions performed.
- [ ] Infrastructure versus application failures separated.
- [ ] Bottleneck confirmed with evidence.
- [ ] Recovery measured against baseline.
- [ ] Runbooks and owner sign-off complete.

**Companion:** [Chapter 069 hands-on lab](labs/069-jenkins-controller-jvm-queue-agent-performance-analysis-check.md).  
**Next:** Chapter 070 — Jenkins Observability, Performance and Reliability Acceptance Capstone.
