# Chapter 024 — Resource Requests, Limits, QoS and Quotas

**Track:** Kubernetes Administration · **Part 05 — Scheduling and Resource Management**  
**Status:** Draft — lab execution and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisite:** Chapters 021–023; kubectl, kind, Docker Desktop and Windows PowerShell

## 1. Incident scenario and learning objectives

A new batch deployment is Pending even though worker-node CPU utilization is low. At the same time, an API Pod restarts with `OOMKilled`, another workload experiences CPU throttling, and a team cannot create more Pods because its namespace has reached a quota. These are related but **different control mechanisms**: scheduling reservations, runtime enforcement, node-pressure eviction and namespace admission.

You will learn to:

1. Explain node **capacity**, **allocatable**, Pod **requests**, and **limits**.
2. Trace how CPU, memory, ephemeral-storage and extended-resource requests influence scheduling.
3. Distinguish CPU throttling from memory OOM kills and kubelet eviction.
4. Determine **Guaranteed**, **Burstable** and **BestEffort** QoS classes.
5. Configure and troubleshoot **LimitRange** and **ResourceQuota**.
6. Interpret namespace quotas, admission failures, default resources and aggregate usage.
7. Diagnose Pending, OOMKilled, CPU throttling and Evicted Pods without relying on a single metric.
8. Perform seven controlled labs with expected evidence, cleanup and an incident acceptance checklist.

**Safety:** All fault injection is confined to a new disposable kind cluster. Do not reproduce memory exhaustion or node pressure in shared or production clusters.

## 2. Architecture: four different enforcement layers

```text
                    Pod manifest
                 requests / limits
                        |
           +------------+-------------+
           |                          |
     API admission                Scheduler
   LimitRange / Quota        request vs allocatable
           |                          |
           +------------+-------------+
                        |
                  Pod bound to node
                        |
                      kubelet
                        |
                  Container runtime
               Linux cgroups (CPU/mem)
                        |
          +-------------+-------------+
          |                           |
    CPU throttling             Memory limit OOM
          |
   Node pressure / eviction manager
```

- **Admission:** A namespace LimitRange may supply defaults or reject invalid resource settings. ResourceQuota may reject a new object even when nodes have free capacity.
- **Scheduling:** The scheduler considers requests relative to node allocatable and existing reservations. It does not schedule based solely on current `kubectl top` usage.
- **Runtime:** CPU limits are generally enforced through throttling; memory limits can result in container OOM kills. Exact mechanisms depend on the runtime and cgroup configuration.
- **Node pressure:** The kubelet can evict Pods under memory, disk or PID pressure. This is distinct from a container exceeding its own memory limit.

## 3. CPU and memory units

| Resource | Request example | Meaning |
|---|---|---|
| CPU | `250m` | One-quarter of a logical CPU |
| CPU | `1` | One logical CPU |
| Memory | `256Mi` | 256 mebibytes |
| Memory | `1Gi` | 1 gibibyte |
| Ephemeral storage | `500Mi` | Local ephemeral-storage request |
| GPU extended resource | `nvidia.com/gpu: 1` | Device allocation where supported |

CPU is compressible: when limits are configured, CPU use can be throttled. Memory is not similarly compressible; exceeding a cgroup memory limit can cause OOM termination. For extended resources such as GPUs, resource limits and scheduling semantics differ from ordinary CPU/memory, and overcommit is generally not supported.

**Requests are not utilization measurements.** A Pod requesting 2 CPUs may use 50m most of the time but still consume 2 CPUs of the scheduler's requested-capacity budget.

## 4. Node capacity versus allocatable

```text
Node capacity
  - kube-reserved
  - system-reserved
  - eviction reservation
  = node allocatable
```

The kubelet reports allocatable resources for Pod scheduling. Use:

```powershell
kubectl get nodes -o custom-columns='NODE:.metadata.name,CPU_CAP:.status.capacity.cpu,CPU_ALLOC:.status.allocatable.cpu,MEM_ALLOC:.status.allocatable.memory'
kubectl describe node NODE_NAME
```

The **Allocated resources** section in `kubectl describe node` reports requests and limits across Pods on that node. Percentages for limits can exceed 100% when overcommit is allowed. Be mindful of init-container effective requests, Pod overhead, and Pod-level resource settings in Kubernetes versions that support them: effective scheduling resources are not always the simple sum of ordinary app-container requests.

### Scheduler incident example

Node allocatable CPU = 4 cores. Existing scheduled Pod requests total 3.8 cores. A new Pod requests 500m. Even if live CPU usage is only 1 core, the new Pod may receive `Insufficient cpu` because 3.8 + 0.5 exceeds 4 cores.

## 5. Requests, limits and common workload patterns

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
      containers:
        - name: nginx
          image: nginx:stable
          resources:
            requests:
              cpu: 100m
              memory: 64Mi
            limits:
              cpu: 500m
              memory: 128Mi
```

**Interpretation:** Each Pod requests at least 100m CPU and 64Mi memory for placement, and its container is subject to a 500m CPU limit and 128Mi memory limit. These are illustrative training values, not production recommendations.

### Request/limit design

- Set requests from observed workload utilization, peaks, latency and concurrency requirements, not arbitrary percentages.
- Avoid extremely low memory requests for bursty services: they increase overcommit and can expose workloads to node pressure.
- Avoid unnecessarily tight CPU limits for latency-sensitive services; throttling can hurt tail latency even when average CPU looks low.
- Use memory limits based on measured working set, application overhead and failure mode; memory limits can be useful isolation boundaries but should not be copied indiscriminately.
- For JVMs, databases and caches, account for off-heap/native allocations, page cache and operator-specific memory sizing.
- Revisit settings after load tests and during incident analysis.

## 6. QoS classes

Kubernetes derives a Pod's QoS class from CPU/memory requests and limits of its containers.

| QoS class | Typical configuration | Operational implication |
|---|---|---|
| **Guaranteed** | Every container has CPU and memory requests equal to limits, both specified (or defaulted equivalently) | Strongest QoS protection during resource-pressure eviction selection |
| **Burstable** | At least one CPU/memory request or limit exists, but not Guaranteed | Intermediate eviction priority; usage relative to requests matters |
| **BestEffort** | No CPU/memory requests or limits on any container | More vulnerable during node resource pressure |

QoS is **not** an SLA, scheduler priority class, guaranteed availability, or immunity from OOM/eviction. Even Guaranteed Pods can be terminated under certain conditions. Kubernetes eviction ordering also depends on whether usage exceeds requests and on Pod priority; QoS alone does not determine the full eviction order.

```powershell
kubectl get pod POD_NAME -o jsonpath='{.status.qosClass}'
```

## 7. CPU throttling, OOMKilled and Evicted

| Symptom | Primary cause | Evidence | Immediate investigation |
|---|---|---|---|
| Latency rises under load | CPU quota throttling or contention | Container CPU throttling metrics; CPU usage; traces | Inspect CPU limit and latency correlation |
| `OOMKilled`, exit code 137 | Container exceeded effective memory constraints / OOM | Last terminated state, reason, memory trend | Heap, off-heap, cache, spikes and limits |
| `Evicted` Pod | Kubelet resource-pressure eviction | Pod status message, node events/conditions | Node memory/disk/PID pressure and requests |
| Pending `Insufficient cpu` | Scheduler cannot fit request | FailedScheduling event, node allocatable | Requests, reserved capacity, autoscaler |
| Quota admission error | Namespace ResourceQuota exceeded | API error; `describe quota` | Namespace quota and aggregate requests |
| Invalid/denied resource request | LimitRange admission | API error; `describe limitrange` | Defaults, min/max, ratios |

**Do not treat every exit code 137 as proof of a container memory-limit OOM.** Inspect `lastState.terminated.reason`, kubelet events and node context.

### Observability queries to investigate

- Container CPU usage and throttling counters/rates, with matching scrape intervals.
- Working set, RSS, memory limit, OOM event counters and restart counts.
- Node allocatable versus total requests, memory pressure and disk pressure.
- Pending Pod age and `FailedScheduling` reason.
- Namespace ResourceQuota used versus hard values.
- Application latency, error rates and throughput.

Metrics and label names depend on Prometheus, cAdvisor and managed-cluster versions. Confirm your actual telemetry schema before adopting dashboards or alerts.

## 8. LimitRange: per-object policy and defaults

`LimitRange` can define default requests/limits and minimum/maximum values in a namespace.

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: app-defaults
  namespace: example
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: 100m
        memory: 64Mi
      default:
        cpu: 500m
        memory: 256Mi
      min:
        cpu: 25m
        memory: 16Mi
      max:
        cpu: "2"
        memory: 1Gi
```

LimitRange is admission-time policy. Existing Pods are not automatically rewritten when a LimitRange changes. Defaults may also be affected by API defaulting rules when only limits are supplied. Review the **effective admitted Pod spec**, not just the source manifest.

## 9. ResourceQuota: aggregate namespace budget

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-budget
  namespace: example
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 2Gi
    limits.cpu: "4"
    limits.memory: 4Gi
    pods: "10"
    persistentvolumeclaims: "5"
```

ResourceQuota is an **admission and accounting mechanism**, not a physical reservation of dedicated node capacity. It can restrict object counts and total requested/limited resources. When quota is configured for compute resources, Pods may need explicit or defaulted resource settings to be admitted.

**Operational distinction:** A Pod can be denied by ResourceQuota before the scheduler sees it. The resulting API error is not a `FailedScheduling` event.

### Namespace governance considerations

- Combine LimitRange defaults with ResourceQuota for consistent onboarding.
- Ensure namespace budgets accommodate rollout surge and Jobs/CronJobs.
- Account for init containers, sidecars and generated workload Pods.
- Review quota scopes, scope selectors and priority-based policies where applicable.
- Avoid using namespace quotas as the only protection against node pressure.

## 10. Lab prerequisites and safety

Use a **disposable kind cluster**, Windows PowerShell and Docker Desktop. All writes use the explicit context `kind-k8s-admin-ch024`.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch024 | Out-Null
Set-Location .\k8s-ch024
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-config.yaml
kind create cluster --name k8s-admin-ch024 --config .\kind-config.yaml --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch024 get nodes -o wide
kubectl --context kind-k8s-admin-ch024 create namespace ch024
```

**Stop conditions:** Wrong context, non-disposable cluster, nodes not Ready, insufficient Docker resources, image pull failure, or an unexpected policy. Do not attempt to disable shared-cluster admission policies.

## 11. Lab A — Inspect node allocatable and Pod requests

```powershell
kubectl --context kind-k8s-admin-ch024 get nodes -o custom-columns='NAME:.metadata.name,CPU:.status.allocatable.cpu,MEMORY:.status.allocatable.memory'
kubectl --context kind-k8s-admin-ch024 describe nodes
@'
apiVersion: v1
kind: Pod
metadata:
  name: requests-demo
  namespace: ch024
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 250m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
'@ | Set-Content -Encoding ascii .\requests-demo.yaml
kubectl --context kind-k8s-admin-ch024 apply --dry-run=server -f .\requests-demo.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\requests-demo.yaml
kubectl --context kind-k8s-admin-ch024 -n ch024 wait --for=condition=Ready pod/requests-demo --timeout=180s
kubectl --context kind-k8s-admin-ch024 -n ch024 get pod requests-demo -o wide
kubectl --context kind-k8s-admin-ch024 -n ch024 get pod requests-demo -o jsonpath='{.status.qosClass}'
```

**Expected:** Pod Ready, assigned node, QoS `Burstable`. Inspect the assigned node's allocated resources to see the request contribution.

## 12. Lab B — Impossible CPU request and safe correction

Create a Pod with a CPU request intentionally larger than any realistic kind node:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: cpu-blocked
  namespace: ch024
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: "1000"
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\cpu-blocked.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\cpu-blocked.yaml
kubectl --context kind-k8s-admin-ch024 -n ch024 get pod cpu-blocked -o wide
kubectl --context kind-k8s-admin-ch024 -n ch024 describe pod cpu-blocked
```

**Expected:** Pending, no `spec.nodeName`, `FailedScheduling` event with `Insufficient cpu`. The unscheduled Pod does not consume the requested CPU at runtime.

Correct the immutable Pod spec by deleting **only this disposable Pod** and recreating:

```powershell
kubectl --context kind-k8s-admin-ch024 -n ch024 delete pod cpu-blocked
(Get-Content .\cpu-blocked.yaml -Raw).Replace('cpu: "1000"','cpu: 25m') | Set-Content -Encoding ascii .\cpu-fixed.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\cpu-fixed.yaml
kubectl --context kind-k8s-admin-ch024 -n ch024 wait --for=condition=Ready pod/cpu-blocked --timeout=180s
```

**Expected:** corrected Pod becomes Ready.

## 13. Lab C — Guaranteed, Burstable and BestEffort QoS

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: qos-guaranteed
  namespace: ch024
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 100m
          memory: 64Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: qos-burstable
  namespace: ch024
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 50m
          memory: 32Mi
        limits:
          memory: 128Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: qos-besteffort
  namespace: ch024
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
'@ | Set-Content -Encoding ascii .\qos.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\qos.yaml
kubectl --context kind-k8s-admin-ch024 -n ch024 wait --for=condition=Ready pod/qos-guaranteed --timeout=180s
kubectl --context kind-k8s-admin-ch024 -n ch024 wait --for=condition=Ready pod/qos-burstable --timeout=180s
kubectl --context kind-k8s-admin-ch024 -n ch024 wait --for=condition=Ready pod/qos-besteffort --timeout=180s
kubectl --context kind-k8s-admin-ch024 -n ch024 get pods -o custom-columns='NAME:.metadata.name,QOS:.status.qosClass,STATUS:.status.phase'
```

**Expected:** `Guaranteed`, `Burstable`, `BestEffort` respectively. Compare the admitted specs and note that QoS does not by itself measure application reliability.

## 14. Lab D — Controlled container memory-limit OOM

This is a **small bounded fault injection**: a container has a 32Mi memory limit and attempts to allocate more memory using a disposable Python process. Do not increase the allocation or run on production.

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: oom-demo
  namespace: ch024
spec:
  restartPolicy: Never
  containers:
    - name: app
      image: python:3.12-alpine
      command:
        - python
        - -c
        - "x = bytearray(96 * 1024 * 1024); print(len(x)); import time; time.sleep(10)"
      resources:
        requests:
          cpu: 20m
          memory: 16Mi
        limits:
          memory: 32Mi
'@ | Set-Content -Encoding ascii .\oom-demo.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\oom-demo.yaml
kubectl --context kind-k8s-admin-ch024 -n ch024 get pod oom-demo
kubectl --context kind-k8s-admin-ch024 -n ch024 describe pod oom-demo
kubectl --context kind-k8s-admin-ch024 -n ch024 get pod oom-demo -o jsonpath='{.status.containerStatuses[0].state.terminated.reason}'
```

**Expected:** after the allocation attempt, the container should terminate with `OOMKilled` on a typical Linux/cgroup kind environment. If the process exits for another reason or the image cannot be pulled, record the actual result and investigate rather than marking success. Because `restartPolicy: Never`, the container is not repeatedly restarted.

**Recovery:** In a real incident, measure peak working set and investigate memory growth before adjusting limits. For this disposable demonstration, delete the Pod:

```powershell
kubectl --context kind-k8s-admin-ch024 -n ch024 delete pod oom-demo --ignore-not-found
```

## 15. Lab E — LimitRange defaulting and admission rejection

Create a separate namespace to avoid changing resource defaults for earlier labs:

```powershell
kubectl --context kind-k8s-admin-ch024 create namespace ch024-policy
@'
apiVersion: v1
kind: LimitRange
metadata:
  name: app-limits
  namespace: ch024-policy
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: 50m
        memory: 32Mi
      default:
        cpu: 250m
        memory: 128Mi
      min:
        cpu: 10m
        memory: 16Mi
      max:
        cpu: 500m
        memory: 256Mi
'@ | Set-Content -Encoding ascii .\limitrange.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\limitrange.yaml
kubectl --context kind-k8s-admin-ch024 -n ch024-policy describe limitrange app-limits
@'
apiVersion: v1
kind: Pod
metadata:
  name: defaulted
  namespace: ch024-policy
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
'@ | Set-Content -Encoding ascii .\defaulted.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\defaulted.yaml
kubectl --context kind-k8s-admin-ch024 -n ch024-policy get pod defaulted -o jsonpath='{.spec.containers[0].resources}'
```

**Expected:** admission inserts CPU/memory requests and limits from the LimitRange.

Try a Pod exceeding the namespace maximum:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: exceeds-limitrange
  namespace: ch024-policy
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: "1"
          memory: 128Mi
'@ | Set-Content -Encoding ascii .\exceeds-limitrange.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\exceeds-limitrange.yaml
```

**Expected:** API admission **rejects** the object because 1 CPU exceeds the LimitRange maximum of 500m. The command's nonzero result is the expected negative-test evidence; no Pod is created.

## 16. Lab F — ResourceQuota admission failure and recovery

Apply a namespace quota that permits only two Pods and a modest aggregate resource budget:

```powershell
@'
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-budget
  namespace: ch024-policy
spec:
  hard:
    pods: "2"
    requests.cpu: 200m
    requests.memory: 128Mi
    limits.cpu: "1"
    limits.memory: 512Mi
'@ | Set-Content -Encoding ascii .\quota.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\quota.yaml
kubectl --context kind-k8s-admin-ch024 -n ch024-policy describe resourcequota team-budget
```

The existing `defaulted` Pod consumes one Pod and its admitted default resources. Create one additional Pod:

```powershell
(Get-Content .\defaulted.yaml -Raw).Replace('name: defaulted','name: quota-second') | Set-Content -Encoding ascii .\quota-second.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\quota-second.yaml
kubectl --context kind-k8s-admin-ch024 -n ch024-policy describe resourcequota team-budget
```

**Expected:** two Pods admitted, using two slots of the Pod-count quota and their corresponding aggregate requests/limits.

Attempt a third Pod:

```powershell
(Get-Content .\defaulted.yaml -Raw).Replace('name: defaulted','name: quota-third') | Set-Content -Encoding ascii .\quota-third.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\quota-third.yaml
```

**Expected:** API rejects the third Pod with a ResourceQuota exceeded message. This is an **admission** failure, not a Pending Pod. Inspect quota used/hard counters and the returned error.

Recover by deleting the disposable second Pod and retrying:

```powershell
kubectl --context kind-k8s-admin-ch024 -n ch024-policy delete pod quota-second
kubectl --context kind-k8s-admin-ch024 apply -f .\quota-third.yaml
kubectl --context kind-k8s-admin-ch024 -n ch024-policy wait --for=condition=Ready pod/quota-third --timeout=180s
kubectl --context kind-k8s-admin-ch024 -n ch024-policy describe resourcequota team-budget
```

**Expected:** third Pod is now admitted and becomes Ready. If quota accounting has not converged yet, wait briefly and inspect actual usage before retrying; do not increase the quota blindly.

## 17. Lab G — CPU limit inspection and throttling evidence

A CPU limit can throttle a CPU-bound container. This lab demonstrates the configuration and provides **optional metrics-based verification**, because kind does not guarantee a metrics stack.

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: cpu-throttle
  namespace: ch024
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "while true; do :; done"]
      resources:
        requests:
          cpu: 25m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
'@ | Set-Content -Encoding ascii .\cpu-throttle.yaml
kubectl --context kind-k8s-admin-ch024 apply -f .\cpu-throttle.yaml
kubectl --context kind-k8s-admin-ch024 -n ch024 wait --for=condition=Ready pod/cpu-throttle --timeout=180s
kubectl --context kind-k8s-admin-ch024 -n ch024 describe pod cpu-throttle
kubectl --context kind-k8s-admin-ch024 -n ch024 top pod cpu-throttle
```

**Expected:** Pod Ready with CPU limit 100m. `kubectl top` works only if Metrics Server is installed; an unavailable metrics API is an **observability limitation**, not a Pod failure.

On Linux cgroup v2 environments, inspect throttling from inside the container if exposed:

```powershell
kubectl --context kind-k8s-admin-ch024 -n ch024 exec cpu-throttle -- cat /sys/fs/cgroup/cpu.stat
```

**Expected where available:** counters such as `nr_throttled` and `throttled_usec` increase during CPU saturation. Cgroup v1 exposes different files; the container may not expose the cgroup path. If metrics are unavailable, mark **throttling measurement Blocked**, not Passed.

Stop the CPU loop promptly:

```powershell
kubectl --context kind-k8s-admin-ch024 -n ch024 delete pod cpu-throttle
```

## 18. Troubleshooting matrix

| Incident | First checks | Common mistake | Safe remediation |
|---|---|---|---|
| Pod Pending with Insufficient CPU | `describe pod`, node allocatable, aggregate requests | Assuming low live CPU means schedulable | Right-size requests or add approved capacity |
| OOMKilled | Termination reason, memory usage, heap/cache, limit | Raising limit without finding leak | Profile usage, correct memory sizing/code |
| CPU latency regression | Throttling, CPU quota, application p95/p99 | Using average CPU alone | Review limit and request under load |
| Pod Evicted | Node conditions, kubelet events, ephemeral storage | Confusing eviction with container OOM | Fix node pressure and workload reservations |
| Quota exceeded | API error, `describe quota` | Debugging scheduler for nonexistent Pod | Adjust workload or reviewed quota |
| LimitRange denied | API error, `describe limitrange` | Assuming manifest resources were accepted | Correct values or approved policy |
| Unexpected QoS | Effective admitted Pod resources | Ignoring init containers/defaults | Inspect every container and admission defaults |
| Rollout stalled after quota | Deployment events, quota used/hard | Ignoring maxSurge budget | Reserve quota for rollout surge |

## 19. SRE/DBRE production runbook

### Phase A — Classify the failure

1. Confirm cluster, namespace, workload owner, incident time and user impact.
2. Determine whether the Pod **exists** (admission), is **unscheduled** (scheduler), is **terminated** (runtime), or is **evicted** (kubelet).
3. Capture sanitized Pod spec/status, events, node allocatable, quota/LimitRange, workload revisions and metrics.

### Phase B — Analyze resource demand

1. Compare requests to observed p50/p95/p99 CPU and memory under representative load.
2. Compare total requests to node allocatable; account for daemon overhead and rollout surge.
3. Inspect CPU throttling and latency correlation; inspect memory OOM events and restarts.
4. Check namespace ResourceQuota `used` versus `hard` and LimitRange effective defaults.
5. For databases, review operator-managed settings, caches, off-heap memory and storage pressure.

### Phase C — Stabilize and validate

1. Prefer a reviewed manifest/source-of-truth change rather than ad hoc `kubectl edit`.
2. For Pending workloads, correct unrealistic requests or provision capacity without removing isolation constraints.
3. For OOM, address workload memory behavior and size the limit with evidence.
4. For quota, coordinate with namespace owners; ensure the budget supports expected replica and rollout counts.
5. Confirm Pod Ready, Service endpoints, request success, latency, errors and restart stability.
6. Record rollback steps, changes, residual risk and alert improvements.

### Special notes for stateful systems

Redis, PostgreSQL, MongoDB, Kafka and Elasticsearch often use substantial caches, native memory, JVM heaps or page cache. Do not set memory limits equal to application heap size without accounting for additional memory. A database Pod being `Guaranteed` does not eliminate the need for capacity planning, backups, replica health and recovery drills.

## 20. Evidence and acceptance rubric

| ID | Exercise | Pass evidence |
|---|---|---|
| A01 | Cluster isolation | Correct context and Ready nodes |
| A02 | Requests/allocatable | Assigned Pod and node resource snapshot |
| A03 | CPU scheduling rejection | FailedScheduling then successful correction |
| A04 | QoS classes | Guaranteed, Burstable, BestEffort statuses |
| A05 | OOM fault injection | Observed OOMKilled or documented environment block |
| A06 | LimitRange defaults | Effective admitted resource fields |
| A07 | LimitRange rejection | Expected API denial |
| A08 | ResourceQuota enforcement | Third Pod denied, then admitted after cleanup |
| A09 | CPU limit/throttling | Limit confirmed; counters captured or measurement blocked |
| A10 | Handover and cleanup | Sanitized evidence and deleted disposable cluster |

**Pass criteria:** A01–A04, A06–A08 and A10 must pass. A05 and the throttling-measurement portion of A09 may be recorded as **Blocked** if the environment prevents deterministic observation; a full validation requires rerunning those tests on a compatible disposable environment. Do not mark blocked tests passed.

### Acceptance report template

```markdown
# Chapter 024 Acceptance Report
Operator:
Reviewer:
Date:
Context: kind-k8s-admin-ch024
Kubernetes version:
Namespace(s): ch024, ch024-policy

| ID | Pass / Fail / Blocked / Not Run | Evidence |
|---|---|---|
| A01 | | |
| A02 | | |
| A03 | | |
| A04 | | |
| A05 | | |
| A06 | | |
| A07 | | |
| A08 | | |
| A09 | | |
| A10 | | |

Incident timeline:
Root causes:
Remediation and rollback:
Observability gaps:
Cleanup confirmation:
Reviewer decision:
```

## 21. Cleanup and rollback

**Destructive operations below are restricted to the disposable kind cluster.** Verify context:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch024 get nodes
kubectl --context kind-k8s-admin-ch024 delete namespace ch024 ch024-policy --ignore-not-found
kind delete cluster --name k8s-admin-ch024
kind get clusters
Remove-Item .\kind-config.yaml, .\requests-demo.yaml, .\cpu-blocked.yaml, .\cpu-fixed.yaml, .\qos.yaml, .\oom-demo.yaml, .\limitrange.yaml, .\defaulted.yaml, .\exceeds-limitrange.yaml, .\quota.yaml, .\quota-second.yaml, .\quota-third.yaml, .\cpu-throttle.yaml -ErrorAction SilentlyContinue
```

Retain the sanitized acceptance report before cleanup. Never remove namespace quota or resource policies from production to make a lab pass.

## 22. Knowledge check

1. Why can a Pod be Pending on a node with low observed CPU usage?
2. What is the difference between node capacity and allocatable?
3. How do CPU and memory limits behave differently at runtime?
4. How does a container OOM kill differ from kubelet eviction?
5. What makes a Pod Guaranteed rather than Burstable?
6. Can a Guaranteed Pod still be terminated under resource pressure?
7. What does LimitRange defaulting change in an admitted Pod?
8. Why does a ResourceQuota error differ from FailedScheduling?
9. How do rollout surge Pods affect namespace quota requirements?
10. What should you measure before changing PostgreSQL or Elasticsearch memory limits?

## 23. Status and next chapter

**Draft published.** Commands and acceptance expectations are instructional; they have **not** been executed in a live kind cluster. Keep the tracker at Draft until lab execution and technical review.

**Next:** Chapter 025 — Scheduling and Resource Pressure Troubleshooting Lab, the Part 05 capstone.
