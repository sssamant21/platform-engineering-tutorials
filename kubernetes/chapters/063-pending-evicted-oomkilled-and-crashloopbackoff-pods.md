# Chapter 063 — Pending, Evicted, OOMKilled and CrashLoopBackOff Pods

**Track:** Kubernetes Administration · **Part 13 — Troubleshooting and Incident Response**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapters 061–062; kubectl, Windows PowerShell; approved staging cluster and read-only production access

## 1. Production scenario

A customer-facing API has three Pending replacement Pods, one Evicted Pod, two containers showing OOMKilled in their last termination state and a worker in CrashLoopBackOff. Some nodes report MemoryPressure and the database connection pool is saturated. A single blanket action—restarting everything or raising memory limits—could worsen capacity pressure and obscure the actual causes.

**Goal:** identify the distinct failure domains, gather precise evidence, reproduce safe cases in staging, choose appropriate mitigations and verify customer recovery without jeopardizing stateful services.

### Learning objectives

1. Explain the differences among Pod phase, Pod status reason, container state and restart backoff.
2. Diagnose Pending Pods caused by scheduling, PVC binding, admission and container startup.
3. Diagnose Evicted Pods and node-pressure eviction signals.
4. Distinguish container OOMKilled from node-level eviction and other SIGKILL exits.
5. Troubleshoot CrashLoopBackOff using previous logs, exit codes, probes and dependencies.
6. Relate resource requests, limits, QoS classes, node allocatable and eviction policy.
7. Apply safe mitigation, validation and prevention practices.

## 2. Failure taxonomy

| Condition | Where it appears | What it means | Key evidence |
|---|---|---|---|
| Pending | Pod phase | Pod accepted but not yet running; may be unscheduled or initializing | Pod conditions, scheduler Events |
| Evicted | Pod status reason | Kubelet terminated Pod, commonly due to node pressure | Pod reason/message, node conditions |
| OOMKilled | Container last terminated reason | Container process killed by OOM handling | Exit 137, memory limit, metrics, kernel evidence |
| CrashLoopBackOff | Container waiting reason | Repeated container failure with restart delay | Previous logs, exit code, Events |
| ContainerCreating | Container waiting reason | Sandbox, image, network or mount preparation | Kubelet Events, CSI/CNI |
| ImagePullBackOff | Container waiting reason | Image pull retries | Registry error and pull Events |

**Critical distinction:** `CrashLoopBackOff` is not a Pod phase; `OOMKilled` is typically a container termination reason; `Evicted` is usually a Pod status reason. A Pod may be Pending while image pulling or mounting volumes, even when the scheduler has already assigned a node.

## 3. Safety and preflight

Default production investigation is read-only. Avoid deleting Evicted Pods before evidence capture, blindly raising memory limits, disabling probes or force deleting stateful Pods. Review node capacity, PDBs, database quorum, application SLOs and change approvals before remediation.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
Get-Date -Format o
```

**Expected:** capture cluster scope and a UTC-correlatable investigation timestamp. `kubectl top` depends on Metrics Server and may be unavailable; record that gap rather than treating it as proof of no resource pressure.

## 4. Lab 1 — Collect status and termination evidence

Select an authorized Pod:

```powershell
$ns = 'REPLACE_WITH_NAMESPACE'
$pod = 'REPLACE_WITH_POD'
kubectl -n $ns get pod $pod -o wide
kubectl -n $ns describe pod $pod
kubectl -n $ns get pod $pod -o jsonpath='{.status.phase}{" reason="}{.status.reason}{" message="}{.status.message}{"
"}'
kubectl -n $ns get pod $pod -o jsonpath='{range .status.containerStatuses[*]}{.name}{" waiting="}{.state.waiting.reason}{" last="}{.lastState.terminated.reason}{" exit="}{.lastState.terminated.exitCode}{" restarts="}{.restartCount}{"
"}{end}'
kubectl -n $ns get events --sort-by=.lastTimestamp
```

### Interpret evidence

- `status.phase` describes the Pod lifecycle stage.
- `status.reason` may identify Evicted or another Pod-level outcome.
- `state.waiting.reason` may show CrashLoopBackOff or ContainerCreating.
- `lastState.terminated.reason` can show OOMKilled.
- Exit code 137 alone is not conclusive proof of OOM; check reason and context.
- Event timestamps and object identities must be correlated with the incident window.

**Expected:** one clear classification for each failing workload.

## 5. Lab 2 — Diagnose Pending Pods

```powershell
kubectl get pods -A --field-selector=status.phase=Pending -o wide
kubectl -n $ns describe pod $pod
kubectl -n $ns get pvc
kubectl -n $ns get resourcequota,limitrange
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get events -A --sort-by=.lastTimestamp
```

### Pending investigation branches

| Observation | Next check |
|---|---|
| `FailedScheduling: Insufficient cpu` | Requests versus allocatable; autoscaler |
| `FailedScheduling: Insufficient memory` | Requests, reserved capacity, quotas |
| Untolerated taint | Tolerations and node conditions |
| Node affinity mismatch | Labels, required rules, topology |
| PVC unbound | StorageClass, provisioner, capacity, binding mode |
| PV node affinity conflict | Zone and volume topology |
| PodScheduled=True but Pending | Image pull, volume mount, sandbox or container config |
| Admission rejection | API create error or controller Events; rejected Pods may not exist |

**Expected:** identify whether the Pod is unscheduled, waiting on storage, or blocked after scheduling. Do not infer scheduling failure from the Pending phase alone.

## 6. Lab 3 — Reproduce a scheduling failure in staging

**Staging only.** Save `ch063-pending.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch063
---
apiVersion: v1
kind: Pod
metadata:
  name: pending-affinity
  namespace: ch063
spec:
  restartPolicy: Never
  nodeSelector:
    ch063.example.com/nonexistent-node-label: "required"
  containers:
    - name: demo
      image: busybox:1.36
      command: ["/bin/sh", "-c", "sleep 120"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
```

```powershell
kubectl apply -f .\ch063-pending.yaml
kubectl -n ch063 get pod pending-affinity -o wide
kubectl -n ch063 describe pod pending-affinity
kubectl -n ch063 get events --sort-by=.lastTimestamp
```

**Expected:** Pod remains Pending with FailedScheduling due to node selector mismatch, assuming no node has that exact training label. If a node already has the label, use a distinct approved selector.

### Remediation decision

Fix incorrect scheduling constraints, supply compatible node capacity or change workload placement through reviewed configuration. Do not remove security or dedicated-pool node selectors simply to make a Pod run.

## 7. Lab 4 — Diagnose Evicted Pods and node pressure

```powershell
kubectl get pods -A --field-selector=status.phase=Failed -o wide
kubectl get nodes -o wide
kubectl describe node REPLACE_WITH_NODE
kubectl get events -A --sort-by=.lastTimestamp
kubectl top nodes
```

Inspect failed Pods individually for `status.reason=Evicted`; `status.phase=Failed` includes many other causes.

### Pressure signals

| Node condition | Typical concern |
|---|---|
| MemoryPressure | Available node memory below eviction threshold |
| DiskPressure | Node filesystem/image filesystem space or inodes |
| PIDPressure | Process ID exhaustion |
| Ready=False/Unknown | Kubelet/node connectivity or health issue |

### QoS and eviction nuance

Kubernetes assigns `Guaranteed`, `Burstable` or `BestEffort` QoS based on requests and limits. QoS affects eviction prioritization, but actual selection also considers resource usage relative to requests and Pod priority. Do not assume every BestEffort Pod is always evicted first under every condition.

### Evidence

Record node condition transitions, eviction messages, resource availability, affected Pods, zone, PDBs and workload replacement behavior.

**Expected:** distinguish kubelet eviction from container OOM and API-driven Pod deletion.

## 8. Lab 5 — Diagnose OOMKilled

```powershell
kubectl -n $ns describe pod $pod
kubectl -n $ns get pod $pod -o jsonpath='{range .status.containerStatuses[*]}{.name}{" lastReason="}{.lastState.terminated.reason}{" exit="}{.lastState.terminated.exitCode}{" finished="}{.lastState.terminated.finishedAt}{"
"}{end}'
kubectl -n $ns logs $pod --all-containers=true --previous --timestamps --tail=200
kubectl -n $ns get pod $pod -o jsonpath='{range .spec.containers[*]}{.name}{" req="}{.resources.requests.memory}{" limit="}{.resources.limits.memory}{"
"}{end}'
kubectl top pods -n $ns --containers
```

### OOM investigation

1. Confirm OOMKilled reason, timestamp and container identity.
2. Compare memory limits, requests and observed working set trends.
3. Check peak memory and application heap/off-heap behavior.
4. Look for batch spikes, cache growth, concurrency or memory leaks.
5. Assess node pressure and whether multiple containers are affected.
6. Check whether OOM followed a deployment or workload change.
7. Decide between memory optimization, controlled scaling or reviewed limit adjustment.

**Caution:** `kubectl top` provides recent measurements and may miss short memory spikes. Exit code 137 can also result from other SIGKILL scenarios; confirm OOM-specific evidence.

## 9. Lab 6 — Reproduce a controlled container OOM in staging

**Optional, isolated staging only.** This exercise intentionally exceeds a small container memory limit; do not run on shared constrained production nodes. Save `ch063-oom.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: oom-demo
  namespace: ch063
spec:
  restartPolicy: Never
  containers:
    - name: demo
      image: python:3.12-alpine
      command:
        - python
        - -c
        - |
          import time
          chunks = []
          while True:
              chunks.append(bytearray(8 * 1024 * 1024))
              time.sleep(0.1)
      resources:
        requests:
          cpu: 20m
          memory: 32Mi
        limits:
          cpu: 200m
          memory: 64Mi
```

```powershell
kubectl apply -f .\ch063-oom.yaml
kubectl -n ch063 get pod oom-demo -w
kubectl -n ch063 describe pod oom-demo
kubectl -n ch063 get pod oom-demo -o jsonpath='{.status.containerStatuses[0].state.terminated.reason}{" exit="}{.status.containerStatuses[0].state.terminated.exitCode}{"
"}'
```

**Expected:** the container is typically OOMKilled after memory consumption exceeds its cgroup limit. Exact behavior depends on runtime and cluster policies. Exit watch with Ctrl+C. Because `restartPolicy: Never`, the container should not enter CrashLoopBackOff.

## 10. Lab 7 — Diagnose CrashLoopBackOff

```powershell
kubectl -n $ns get pod $pod -o wide
kubectl -n $ns describe pod $pod
kubectl -n $ns logs $pod --all-containers=true --previous --timestamps --tail=200
kubectl -n $ns logs $pod --all-containers=true --timestamps --tail=100
kubectl -n $ns get events --sort-by=.lastTimestamp
```

### Crash-loop classification

| Signal | Hypothesis | Validation |
|---|---|---|
| Exit 1 | Application/config error | Previous logs, env references |
| Exit 137 | SIGKILL/OOM possibility | Termination reason, memory data |
| Exit 143 | SIGTERM | Rollout, graceful shutdown, probe |
| Liveness failures | Health check too strict or application hung | Probe Events, endpoint behavior |
| Startup failures | Slow initialization or dependency unavailable | Startup probe and dependency metrics |
| Missing binary | Command/entrypoint failure | Events, image contents |
| Database connection errors | Dependency or credential issue | DB health, Secret references |

**Important:** a readiness probe failure alone does not restart a container. Liveness/startup failures can restart it. The reason is often in **previous** container logs, not current logs.

## 11. Lab 8 — Reproduce a simple crash loop in staging

Save `ch063-crash.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: crash-demo
  namespace: ch063
spec:
  restartPolicy: Always
  containers:
    - name: demo
      image: busybox:1.36
      command: ["/bin/sh", "-c", "echo 'ch063 simulated failure'; exit 42"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
```

```powershell
kubectl apply -f .\ch063-crash.yaml
kubectl -n ch063 get pod crash-demo -w
kubectl -n ch063 describe pod crash-demo
kubectl -n ch063 logs crash-demo --previous --timestamps --tail=30
```

**Expected:** repeated exit code 42, increasing restart count and eventually CrashLoopBackOff waiting status. Backoff timing varies by Kubernetes version and kubelet configuration.

## 12. Lab 9 — Correlate application SLIs with resource failures

Use approved Grafana/Prometheus and application traces alongside kubectl.

### Recent restarts

```promql
sum by (namespace, pod) (
  increase(kube_pod_container_status_restarts_total[15m])
)
```

### OOMKilled last termination reason

```promql
kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1
```

### Node memory pressure

```promql
kube_node_status_condition{condition="MemoryPressure",status="true"} == 1
```

### Pending Pods

```promql
sum by (namespace) (
  kube_pod_status_phase{phase="Pending"} == 1
)
```

These kube-state-metrics metrics and labels must be verified against the installed exporter version. `last_terminated_reason` is not a count of all OOM events; use suitable counters/events and time windows for incident rates.

**Expected:** connect workload failures to customer latency/error rates, replica availability, autoscaling and node pressure. Do not claim causality from correlation alone.

## 13. Lab 10 — Multi-symptom production incident tabletop

**Scenario:** a service has 10 desired replicas but only 6 available. Two replacement Pods are Pending due to insufficient CPU requests capacity, one Pod was Evicted after DiskPressure, and one container was OOMKilled. A separate worker is CrashLoopBackOff because its database connection pool cannot initialize.

### Required actions

1. Establish customer impact and incident severity.
2. Record available/desired replicas, affected nodes and zones.
3. Separate scheduling, eviction, OOM and crash-loop failure mechanisms.
4. Check whether the autoscaler can provision nodes.
5. Verify DiskPressure and image filesystem/inode conditions.
6. Assess application memory and database connection behavior.
7. Preserve healthy replicas and respect PDB/stateful quorum.
8. Choose low-risk mitigations with approvers and rollback.
9. Verify error rate, p95 latency, Ready endpoints and DB health.
10. Produce a blameless timeline and action register.

**Expected:** multiple independently supported contributing causes; no single generic “Pod failure” RCA.

## 14. Mitigation and prevention matrix

| Condition | Safe mitigation | Prevention |
|---|---|---|
| Pending: insufficient capacity | Add eligible capacity or review requests | Capacity headroom and autoscaling tests |
| Pending: placement constraints | Correct verified selector/affinity mismatch | Policy checks in CI |
| Pending: PVC | Repair storage provisioning/topology | StorageClass and zone design |
| Evicted: memory | Restore node headroom, reduce pressure | Requests, QoS, alerts |
| Evicted: disk | Reclaim safe node disk usage, investigate images/logs | Disk/inode monitoring |
| OOMKilled | Fix memory behavior, tune limits after evidence | Profiling, load tests, memory alerts |
| CrashLoopBackOff | Fix app/config/dependency or probes | Startup validation and dependency tests |

**Do not** respond to every OOMKilled by increasing limits; doing so can reduce node schedulability or increase eviction risk. Do not force delete a database Pod to clear a crash loop without quorum and storage checks.

## 15. Production runbook

### Detect and classify

1. Confirm customer SLIs and desired/available replicas.
2. Inspect Pod phase, status reason and container waiting/termination states.
3. Check node conditions, scheduler Events and storage status.

### Investigate

1. For Pending: identify unscheduled versus initialization blockage.
2. For Evicted: inspect node pressure, eviction message and affected workloads.
3. For OOMKilled: inspect limits, memory trends and peak behavior.
4. For CrashLoopBackOff: inspect previous logs, exit codes and probes.
5. Correlate changes, dependency health and telemetry gaps.

### Mitigate and verify

1. Apply approved targeted change with rollback.
2. Verify Pods become Ready and Service EndpointSlices are healthy.
3. Confirm customer latency/error rates and dependency health recover.
4. Continue monitoring for recurring pressure and restarts.

### Close

Record exact failure reasons, impact, contributing factors, capacity/probe/config improvements and owners.

## 16. Evidence template

```text
Incident ID:
Cluster / namespace / workload:
Incident window (UTC):
Pod UID / node / zone:
Pod phase / status reason:
Container waiting / terminated reason:
Exit code / restart count:
Events / previous logs:
Requests / limits / QoS:
Node conditions / allocatable:
PVC / topology / scheduling constraints:
Customer SLIs / available replicas:
Hypotheses and supporting evidence:
Chosen mitigation / approver:
Rollback plan:
Recovery verification:
Follow-up owners:
```

## 17. Acceptance checklist

- [ ] Pod phase versus container waiting/termination state distinguished.
- [ ] Pending scheduling and initialization causes classified.
- [ ] Evicted Pods correlated with node pressure and eviction evidence.
- [ ] OOMKilled confirmed using termination reason and memory evidence.
- [ ] CrashLoopBackOff investigated using previous logs and exit code.
- [ ] QoS, requests, limits and node allocatable implications understood.
- [ ] Pending lab completed or marked not run.
- [ ] Optional isolated OOM lab completed or marked not run.
- [ ] CrashLoopBackOff lab completed or marked not run.
- [ ] Prometheus and customer SLI correlation reviewed.
- [ ] Multi-symptom incident tabletop and runbook completed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

## 18. Cleanup

Delete only the isolated training namespace after preserving approved evidence:

```powershell
kubectl -n ch063 get pods
kubectl delete namespace ch063
```

Do not remove production failed Pods, node logs or monitoring data as part of training cleanup.

**Status:** Draft — runtime validation and technical review pending.

## 19. References

- [Kubernetes Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Pod Quality of Service Classes](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/)
- [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Assign Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [Debug Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)
- [Configure Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

**Next:** Chapter 064 — Node, Network, DNS and Control Plane Failures.
