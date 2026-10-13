# Chapter 025 — Scheduling and Resource Pressure Troubleshooting Lab

**Track:** Kubernetes Administration · **Part 05 — Scheduling and Resource Management**  
**Type:** Integrated production-operations capstone · **Status:** Draft — runtime validation and technical review pending  
**Prerequisites:** Chapters 021–024, Docker Desktop, kind, kubectl, Windows PowerShell

## 1. Mission: recover a degraded application safely

You are the on-call SRE for a Kubernetes service with four concurrent symptoms:

- A new application replica is **Pending** after a placement-policy change.
- A batch Pod is **Pending** even though nodes report low current CPU utilization.
- A worker has been reserved for maintenance with a **NoSchedule** taint.
- A container is repeatedly terminated after exceeding a **memory limit**.

A fifth problem emerges: a namespace **ResourceQuota** rejects a rollout. Your task is to distinguish scheduler decisions from admission and runtime failures, recover each workload with minimal impact, and produce evidence of restoration.

This chapter integrates **021 Scheduler Internals**, **022 Node Selectors and Affinity Rules**, **023 Taints, Tolerations and Topology Spread**, and **024 Resource Requests, Limits, QoS and Quotas**.

**Safety:** Run only against the dedicated disposable kind cluster. Do not inject node pressure, force-delete stateful Pods, or change production taints, quotas or priority policies.

## 2. Learning outcomes

By the end of this capstone you should be able to:

1. Triage a Pod through admission, scheduling, binding, kubelet startup and readiness.
2. Interpret `FailedScheduling` reasons and correlate them with node allocatable capacity.
3. Diagnose node selectors, required affinity, taints and tolerations together.
4. Explain how topology spread changes eligible placement and why replicas can remain Pending.
5. Distinguish CPU scheduling reservation from CPU usage and throttling.
6. Differentiate `OOMKilled` from node-pressure `Evicted`.
7. Diagnose LimitRange and ResourceQuota admission failures.
8. Validate recovery using Pod placement, Ready replicas, Service endpoints and application HTTP.
9. Write an incident timeline, root-cause summary, rollback and prevention plan.

## 3. Architecture and fault domains

```text
                         API server
                             |
                    Admission controls
                  LimitRange / ResourceQuota
                             |
                       Pod accepted?
                      /            \
                    No              Yes
                    |                |
             API rejection       Scheduler
                                   |
                       filter feasible nodes:
                        selectors / affinity
                        taints / tolerations
                        topology spread
                        requests / allocatable
                                   |
                            Node assigned?
                            /           \
                          No             Yes
                          |               |
                   FailedScheduling     kubelet
                                          |
                                   image / runtime
                                          |
                                 OOM / probes / Ready
```

**Key diagnostic rule:** Do not investigate a quota-denied object as a Pending Pod; it may not exist. Do not investigate an already-bound Pod's `OOMKilled` state as a scheduler failure.

## 4. Lab SLOs and acceptance criteria

These are **training targets**, not real production service-level guarantees.

| ID | Test | Expected evidence |
|---|---|---|
| A01 | Isolation | Correct kind context, three Ready nodes |
| A02 | Baseline | 2/2 API replicas Ready, HTTP response |
| A03 | Placement failure | Pending Pod, empty nodeName, selector event |
| A04 | Placement recovery | Corrected Pod Ready on eligible node |
| A05 | Taint failure | Untolerated NoSchedule event |
| A06 | Taint recovery | Narrow toleration plus selector works |
| A07 | Resource request failure | Insufficient CPU event |
| A08 | Resource recovery | Realistic request leads to Ready Pod |
| A09 | Topology failure | Hard spread prevents some replicas |
| A10 | Topology recovery | Eligible domains restored, desired Ready |
| A11 | OOM | Container OOMKilled, or documented environment block |
| A12 | Quota rejection | API denial and quota usage evidence |
| A13 | Quota recovery | Object admitted after controlled capacity release |
| A14 | Final health | API HTTP, Ready Pods, expected endpoints |
| A15 | Evidence/cleanup | Sanitized incident report and cluster deletion |

**Mandatory for full validation:** A01–A10, A12–A15. A11 may be Blocked if the disposable environment cannot reproduce the bounded OOM test; full validation requires a compatible environment later. Never mark a test Passed without observed output.

## 5. Phase 0 — Build a disposable environment

**Requirements:** Windows PowerShell, Docker Desktop, kind, kubectl; container image access to `nginx:stable`, `busybox:1.36.1`, and `python:3.12-alpine`.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch025 | Out-Null
Set-Location .\k8s-ch025
@'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
'@ | Set-Content -Encoding ascii .\kind-config.yaml
kind create cluster --name k8s-admin-ch025 --config .\kind-config.yaml --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch025 get nodes -o wide
kubectl --context kind-k8s-admin-ch025 create namespace ch025
kubectl --context kind-k8s-admin-ch025 create namespace ch025-policy
$workers = @((kubectl --context kind-k8s-admin-ch025 get nodes -l '!node-role.kubernetes.io/control-plane' -o json | ConvertFrom-Json).items | ForEach-Object { $_.metadata.name })
if ($workers.Count -ne 2) { throw "Expected exactly two workers" }
foreach ($node in $workers) {
  kubectl --context kind-k8s-admin-ch025 label node $node workload.example.com/pool=training
}
kubectl --context kind-k8s-admin-ch025 get nodes --show-labels
```

**Expected:** current context is `kind-k8s-admin-ch025`, one Ready control plane and two Ready workers. **Stop** if the context is wrong, any node is not Ready, or the cluster is not disposable.

All mutations below explicitly specify the kind context. Keep `$workers` in the same PowerShell session.

## 6. Phase 1 — Healthy application baseline

Create an application Deployment and ClusterIP Service with two replicas:

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: ch025
spec:
  replicas: 2
  minReadySeconds: 3
  progressDeadlineSeconds: 120
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      nodeSelector:
        workload.example.com/pool: training
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: api
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - containerPort: 80
              name: http
          readinessProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 3
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: ch025
spec:
  selector:
    app: api
  ports:
    - port: 80
      targetPort: http
'@ | Set-Content -Encoding ascii .\baseline.yaml

kubectl --context kind-k8s-admin-ch025 apply --dry-run=server -f .\baseline.yaml
kubectl --context kind-k8s-admin-ch025 apply -f .\baseline.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025 rollout status deployment/api --timeout=180s
kubectl --context kind-k8s-admin-ch025 -n ch025 get deployment,replicaset,pod,service -o wide
kubectl --context kind-k8s-admin-ch025 -n ch025 get endpointslices -l kubernetes.io/service-name=api
```

Create a client for in-cluster DNS/HTTP verification:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: ch025
spec:
  containers:
    - name: toolbox
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\client.yaml

kubectl --context kind-k8s-admin-ch025 apply -f .\client.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025 wait --for=condition=Ready pod/client --timeout=180s
kubectl --context kind-k8s-admin-ch025 -n ch025 exec client -- nslookup api.ch025.svc.cluster.local
kubectl --context kind-k8s-admin-ch025 -n ch025 exec client -- wget -qO- http://api.ch025.svc.cluster.local
```

**Expected:** 2/2 Ready replicas and a successful NGINX HTTP response. Capture this baseline before fault injection.

## 7. Phase 2 — Incident A: incorrect required placement

### Inject the fault

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: placement-blocked
  namespace: ch025
spec:
  nodeSelector:
    workload.example.com/pool: nonexistent
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 25m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\placement-blocked.yaml

kubectl --context kind-k8s-admin-ch025 apply -f .\placement-blocked.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025 get pod placement-blocked -o wide
kubectl --context kind-k8s-admin-ch025 -n ch025 describe pod placement-blocked
```

**Expected:** Pending Pod with no node assignment and a `FailedScheduling` event mentioning node affinity/selector mismatch.

### Diagnose and recover

```powershell
kubectl --context kind-k8s-admin-ch025 get nodes --show-labels
kubectl --context kind-k8s-admin-ch025 -n ch025 delete pod placement-blocked
(Get-Content .\placement-blocked.yaml -Raw).Replace('pool: nonexistent','pool: training') | Set-Content -Encoding ascii .\placement-fixed.yaml
kubectl --context kind-k8s-admin-ch025 apply -f .\placement-fixed.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025 wait --for=condition=Ready pod/placement-blocked --timeout=180s
kubectl --context kind-k8s-admin-ch025 -n ch025 get pod placement-blocked -o wide
```

**Expected:** Pod becomes Ready. The root cause was an impossible hard selector, not a node outage.

## 8. Phase 3 — Incident B: taint without toleration

### Inject

```powershell
kubectl --context kind-k8s-admin-ch025 taint node $workers[0] workload.example.com/dedicated=training:NoSchedule
@'
apiVersion: v1
kind: Pod
metadata:
  name: taint-blocked
  namespace: ch025
spec:
  nodeSelector:
    kubernetes.io/hostname: PLACEHOLDER
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 25m
          memory: 16Mi
'@.Replace('PLACEHOLDER', $workers[0]) | Set-Content -Encoding ascii .\taint-blocked.yaml

kubectl --context kind-k8s-admin-ch025 apply -f .\taint-blocked.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025 describe pod taint-blocked
```

**Expected:** Pod Pending due to untolerated taint. The hostname selector excludes other nodes.

### Recover with narrow toleration

```powershell
kubectl --context kind-k8s-admin-ch025 -n ch025 delete pod taint-blocked
@'
apiVersion: v1
kind: Pod
metadata:
  name: taint-blocked
  namespace: ch025
spec:
  nodeSelector:
    kubernetes.io/hostname: PLACEHOLDER
  tolerations:
    - key: workload.example.com/dedicated
      operator: Equal
      value: training
      effect: NoSchedule
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 25m
          memory: 16Mi
'@.Replace('PLACEHOLDER', $workers[0]) | Set-Content -Encoding ascii .\taint-fixed.yaml

kubectl --context kind-k8s-admin-ch025 apply -f .\taint-fixed.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025 wait --for=condition=Ready pod/taint-blocked --timeout=180s
kubectl --context kind-k8s-admin-ch025 -n ch025 get pod taint-blocked -o wide
```

**Expected:** Pod Ready on `$workers[0]`. The toleration permits the tainted node; the hostname selector enforces the target.

**Restore node policy after the test:**

```powershell
kubectl --context kind-k8s-admin-ch025 taint node $workers[0] workload.example.com/dedicated=training:NoSchedule-
```

## 9. Phase 4 — Incident C: unrealistic CPU request

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: request-blocked
  namespace: ch025
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: "1000"
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\request-blocked.yaml

kubectl --context kind-k8s-admin-ch025 apply -f .\request-blocked.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025 describe pod request-blocked
kubectl --context kind-k8s-admin-ch025 describe node $workers[0]
```

**Expected:** `Insufficient cpu` scheduling event. The Pod has not consumed 1000 cores; it is rejected because its request cannot fit allocatable resources.

```powershell
kubectl --context kind-k8s-admin-ch025 -n ch025 delete pod request-blocked
(Get-Content .\request-blocked.yaml -Raw).Replace('cpu: "1000"','cpu: 25m') | Set-Content -Encoding ascii .\request-fixed.yaml
kubectl --context kind-k8s-admin-ch025 apply -f .\request-fixed.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025 wait --for=condition=Ready pod/request-blocked --timeout=180s
```

**Expected:** Pod Ready with corrected request. The change is intentionally made in the Pod spec rather than hiding capacity pressure.

## 10. Phase 5 — Incident D: topology spread versus eligible domains

### Baseline placement

The `api` Deployment already uses hard hostname spread with `maxSkew: 1` and only worker-pool nodes are eligible. Verify:

```powershell
kubectl --context kind-k8s-admin-ch025 -n ch025 get pods -l app=api -o wide
kubectl --context kind-k8s-admin-ch025 get nodes --show-labels
```

**Expected:** two API replicas on separate workers under normal capacity.

### Remove one eligible worker domain

Temporarily remove the training-pool label from the second worker, then request a third API replica:

```powershell
kubectl --context kind-k8s-admin-ch025 label node $workers[1] workload.example.com/pool-
kubectl --context kind-k8s-admin-ch025 -n ch025 scale deployment/api --replicas=3
kubectl --context kind-k8s-admin-ch025 -n ch025 get deployment api
kubectl --context kind-k8s-admin-ch025 -n ch025 get pods -l app=api -o wide
kubectl --context kind-k8s-admin-ch025 -n ch025 get events --sort-by=.lastTimestamp
```

**Interpretation:** An existing Pod on the relabeled worker is not automatically evicted. With only one currently eligible hostname domain, `maxSkew: 1` alone **does not guarantee a Pending Pod**, because skew is evaluated across eligible domains and a single domain can satisfy the rule. Do not claim this is a deterministic failure.

### Deterministic hard-spread fault using minDomains

Create a separate Deployment requiring at least two eligible hostname domains:

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: strict-spread
  namespace: ch025
spec:
  replicas: 2
  selector:
    matchLabels:
      app: strict-spread
  template:
    metadata:
      labels:
        app: strict-spread
    spec:
      nodeSelector:
        workload.example.com/pool: training
      topologySpreadConstraints:
        - maxSkew: 1
          minDomains: 2
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: strict-spread
      containers:
        - name: nginx
          image: nginx:stable
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
'@ | Set-Content -Encoding ascii .\strict-spread.yaml

kubectl --context kind-k8s-admin-ch025 apply --dry-run=server -f .\strict-spread.yaml
kubectl --context kind-k8s-admin-ch025 apply -f .\strict-spread.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025 get pods -l app=strict-spread -o wide
kubectl --context kind-k8s-admin-ch025 -n ch025 get events --sort-by=.lastTimestamp
```

**Expected:** with only one eligible worker and `minDomains: 2`, the global minimum for skew is zero. The first Pod may schedule, while the second is blocked by `maxSkew: 1`. Capture the actual FailedScheduling event. If server-side dry-run rejects `minDomains`, record this test **Blocked — incompatible Kubernetes API** and do not run the subsequent strict-spread commands.

### Recover eligibility

```powershell
kubectl --context kind-k8s-admin-ch025 label node $workers[1] workload.example.com/pool=training
kubectl --context kind-k8s-admin-ch025 -n ch025 rollout status deployment/strict-spread --timeout=180s
kubectl --context kind-k8s-admin-ch025 -n ch025 scale deployment/api --replicas=2
kubectl --context kind-k8s-admin-ch025 -n ch025 rollout status deployment/api --timeout=180s
kubectl --context kind-k8s-admin-ch025 -n ch025 get pods -l app=api -o wide
```

**Expected:** two eligible domains are restored; strict-spread reaches 2/2 Ready, and API returns to 2/2 Ready. Verify the application HTTP endpoint after recovery.

## 11. Phase 6 — Incident E: bounded OOM fault injection

This exercise deliberately exceeds a **small 32Mi container memory limit**. It does not attempt to exhaust the host or kind node.

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: oom-demo
  namespace: ch025
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

kubectl --context kind-k8s-admin-ch025 apply -f .\oom-demo.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025 get pod oom-demo
kubectl --context kind-k8s-admin-ch025 -n ch025 describe pod oom-demo
kubectl --context kind-k8s-admin-ch025 -n ch025 get pod oom-demo -o jsonpath='{.status.containerStatuses[0].state.terminated.reason}'
```

**Expected on a typical Linux cgroup kind cluster:** terminated reason `OOMKilled`. The Pod may transition to Failed because restartPolicy is Never. If the image cannot be pulled or the runtime reports another reason, document the actual result.

**Root-cause distinction:** This is a container memory-limit event, not a node-pressure eviction or a scheduler rejection. In production, investigate heap, off-heap allocations, page cache and application memory spikes before changing limits.

```powershell
kubectl --context kind-k8s-admin-ch025 -n ch025 delete pod oom-demo --ignore-not-found
```

## 12. Phase 7 — Incident F: quota rejection and recovery

Use a separate policy namespace so the application baseline remains unaffected.

```powershell
@'
apiVersion: v1
kind: LimitRange
metadata:
  name: defaults
  namespace: ch025-policy
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: 50m
        memory: 32Mi
      default:
        cpu: 250m
        memory: 128Mi
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: budget
  namespace: ch025-policy
spec:
  hard:
    pods: "1"
    requests.cpu: 100m
    requests.memory: 64Mi
    limits.cpu: 500m
    limits.memory: 256Mi
'@ | Set-Content -Encoding ascii .\policy.yaml

kubectl --context kind-k8s-admin-ch025 apply -f .\policy.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025-policy describe limitrange defaults
kubectl --context kind-k8s-admin-ch025 -n ch025-policy describe resourcequota budget
@'
apiVersion: v1
kind: Pod
metadata:
  name: policy-first
  namespace: ch025-policy
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
'@ | Set-Content -Encoding ascii .\policy-first.yaml

kubectl --context kind-k8s-admin-ch025 apply -f .\policy-first.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025-policy wait --for=condition=Ready pod/policy-first --timeout=180s
kubectl --context kind-k8s-admin-ch025 -n ch025-policy get pod policy-first -o jsonpath='{.spec.containers[0].resources}'
```

**Expected:** LimitRange defaults the resources, and the first Pod is admitted.

Try to create a second Pod:

```powershell
(Get-Content .\policy-first.yaml -Raw).Replace('name: policy-first','name: policy-second') | Set-Content -Encoding ascii .\policy-second.yaml
kubectl --context kind-k8s-admin-ch025 apply -f .\policy-second.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025-policy describe resourcequota budget
```

**Expected:** the API rejects the second Pod because the namespace quota allows only one Pod. This object is not Pending; it was denied before scheduling.

Recover by removing the disposable first Pod, then retry:

```powershell
kubectl --context kind-k8s-admin-ch025 -n ch025-policy delete pod policy-first
kubectl --context kind-k8s-admin-ch025 apply -f .\policy-second.yaml
kubectl --context kind-k8s-admin-ch025 -n ch025-policy wait --for=condition=Ready pod/policy-second --timeout=180s
kubectl --context kind-k8s-admin-ch025 -n ch025-policy describe resourcequota budget
```

**Expected:** the second Pod is admitted after the first Pod's quota usage is released. If quota accounting is delayed, inspect `used` and retry after reconciliation.

## 13. Phase 8 — Final application recovery verification

```powershell
kubectl --context kind-k8s-admin-ch025 -n ch025 rollout status deployment/api --timeout=180s
kubectl --context kind-k8s-admin-ch025 -n ch025 get deployment api
kubectl --context kind-k8s-admin-ch025 -n ch025 get pods -l app=api -o wide
kubectl --context kind-k8s-admin-ch025 -n ch025 get endpointslices -l kubernetes.io/service-name=api
kubectl --context kind-k8s-admin-ch025 -n ch025 exec client -- wget -qO- http://api.ch025.svc.cluster.local
kubectl --context kind-k8s-admin-ch025 get nodes --show-labels
kubectl --context kind-k8s-admin-ch025 -n ch025 get events --sort-by=.lastTimestamp
```

**Expected:** API 2/2 Ready, two healthy Service endpoints, HTTP success, and training pool labels restored on both workers. Confirm there are no lingering taints from the test.

**Application health is more than Pod readiness.** In a real incident, also verify p95/p99 latency, error rate, throughput, data integrity and downstream dependencies.

## 14. Incident decision tree

```text
Workload unhealthy
 |
 +-- Was Pod creation rejected by API?
 |      +-- Yes -> ResourceQuota, LimitRange, policy/admission error
 |      +-- No
 |           |
 |           +-- Pod has spec.nodeName?
 |                 +-- No -> scheduling
 |                 |       +-- selector/affinity mismatch
 |                 |       +-- untolerated taint
 |                 |       +-- insufficient requests capacity
 |                 |       +-- topology spread / storage constraint
 |                 +-- Yes -> kubelet/runtime/application
 |                         +-- ImagePullBackOff
 |                         +-- ContainerCreating/volume
 |                         +-- OOMKilled / exit code
 |                         +-- probes and application readiness
 |
 +-- Recovery validated?
        +-- Ready replicas, endpoints, HTTP and SLO metrics
```

## 15. Production troubleshooting matrix

| Symptom | Evidence | Likely cause | First safe action |
|---|---|---|---|
| Pending, nodeName empty | FailedScheduling, node labels | Required selector mismatch | Compare labels to Pod template |
| Pending, untolerated taint | Pod events, node taints | Dedicated node without toleration | Review pool policy |
| Pending, Insufficient cpu | Requests and allocatable | Overcommitted request budget | Right-size or provision capacity |
| Pending, topology skew | Pod events, topology labels | Too few eligible domains | Restore capacity/domain |
| Pod OOMKilled | Container termination reason | Memory limit exceeded | Profile memory, inspect limit |
| Pod Evicted | Pod status and node events | Node resource pressure | Remediate node pressure |
| API quota denial | kubectl apply error, quota used/hard | Namespace admission budget | Free approved budget or review quota |
| High latency, low CPU | Throttling counters and traces | CPU limit contention | Review limit and application profile |
| New replicas blocked during rollout | Deployment events, quota | Surge Pods exceed quota | Reserve rollout headroom |

## 16. Evidence capture and incident handover

Create a local evidence directory:

```powershell
New-Item -ItemType Directory -Force .\evidence | Out-Null
(Get-Date).ToUniversalTime().ToString("o") | Set-Content .\evidence\capture-time-utc.txt
kubectl --context kind-k8s-admin-ch025 get nodes -o wide > .\evidence\nodes.txt
kubectl --context kind-k8s-admin-ch025 -n ch025 get pods -o wide > .\evidence\pods.txt
kubectl --context kind-k8s-admin-ch025 -n ch025 get events --sort-by=.lastTimestamp > .\evidence\events.txt
kubectl --context kind-k8s-admin-ch025 -n ch025 get deployments -o wide > .\evidence\deployments.txt
kubectl --context kind-k8s-admin-ch025 -n ch025 get endpointslices > .\evidence\endpointslices.txt
kubectl --context kind-k8s-admin-ch025 -n ch025-policy describe resourcequota budget > .\evidence\quota.txt
```

These are **read-only** snapshots. Review and sanitize names, internal IPs and metadata before sharing. Do not export Secret contents or customer data.

### Incident report template

```markdown
# Chapter 025 — Scheduling and Resource Pressure Acceptance

Operator:
Reviewer:
Date/time:
Context: kind-k8s-admin-ch025
Namespace(s): ch025, ch025-policy
Kubernetes version:

## Timeline
| UTC time | Symptom | Evidence | Action | Outcome |
|---|---|---|---|---|
| | Healthy baseline | | | |
| | Placement failure | | | |
| | Taint failure | | | |
| | CPU request failure | | | |
| | Topology failure | | | |
| | OOM | | | |
| | Quota denial | | | |
| | Recovery verification | | | |

## Acceptance
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
| A11 | | |
| A12 | | |
| A13 | | |
| A14 | | |
| A15 | | |

Root causes:
Contributing factors:
Customer impact (simulated):
Actions and rollback:
Detection gaps:
Preventive controls:
Cleanup confirmation:
Reviewer decision:
```

## 17. Capstone scoring rubric

| Area | Points |
|---|---:|
| Safety, context verification and baseline | 15 |
| Selector/taint diagnosis and recovery | 20 |
| Resource requests and scheduler reasoning | 15 |
| Topology spread diagnosis and recovery | 15 |
| OOM versus eviction and quota admission | 15 |
| Application validation and SLO reasoning | 10 |
| Evidence, RCA, cleanup and handover | 10 |
| **Total** | **100** |

**Training pass target:** at least 85 points, all mandatory acceptance items Passed, and no unsafe production-like actions. A compatibility block on `minDomains` means A09/A10 remain Blocked and full capstone validation must be completed later on a supported disposable cluster. The scoring rubric is a course assessment, not a professional certification.

## 18. Production prevention checklist

- Define documented node-pool label and taint contracts.
- Verify workload selectors and tolerations in CI before rollout.
- Test hard topology spread against node/zone loss and rollout surge.
- Track node allocatable versus requested capacity and resource fragmentation.
- Use measured CPU/memory requests, realistic limits and workload-specific sizing.
- Monitor Pod Pending age, FailedScheduling, OOMKilled, evictions and quota utilization.
- Reserve quota for rollout surge and scheduled Jobs.
- Avoid blanket tolerations or removal of node-condition taints.
- Align database Pod placement with PVC topology, replication and quorum.
- Use GitOps/source-of-truth changes and record rollback conditions.

## 19. Cleanup and rollback

**Destructive operations below apply only to the disposable kind cluster.** Confirm:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch025 get nodes
$workers
```

If the PowerShell session was restarted, rediscover the worker names using Section 5 rather than guessing.

```powershell
kubectl --context kind-k8s-admin-ch025 taint node $workers[0] workload.example.com/dedicated=training:NoSchedule- 2>$null
foreach ($node in $workers) {
  kubectl --context kind-k8s-admin-ch025 label node $node workload.example.com/pool- 2>$null
}
kubectl --context kind-k8s-admin-ch025 delete namespace ch025 ch025-policy --ignore-not-found
kind delete cluster --name k8s-admin-ch025
kind get clusters
Remove-Item .\kind-config.yaml, .\baseline.yaml, .\client.yaml, .\placement-blocked.yaml, .\placement-fixed.yaml, .\taint-blocked.yaml, .\taint-fixed.yaml, .\request-blocked.yaml, .\request-fixed.yaml, .\strict-spread.yaml, .\oom-demo.yaml, .\policy.yaml, .\policy-first.yaml, .\policy-second.yaml -ErrorAction SilentlyContinue
```

Retain the sanitized acceptance report and evidence directory. Never delete a shared namespace or change production node labels as part of this lab.

## 20. Final acceptance checklist

- [ ] Disposable three-node cluster created; exact context verified.
- [ ] Healthy API baseline established with two replicas and successful HTTP.
- [ ] Selector mismatch reproduced and corrected.
- [ ] Untolerated NoSchedule taint reproduced and corrected.
- [ ] Unrealistic CPU request rejected and corrected.
- [ ] Topology spread and minDomains incident demonstrated.
- [ ] Eligible domains restored; strict-spread and API healthy.
- [ ] Bounded OOM test observed or environment block documented.
- [ ] ResourceQuota denial reproduced and corrected.
- [ ] API 2/2 Ready, EndpointSlices and HTTP revalidated.
- [ ] Sanitized evidence, incident timeline and RCA completed.
- [ ] All disposable node changes, namespaces and cluster cleaned up.

## 21. Knowledge check

1. Why can a Pod be Pending despite low live CPU usage?
2. How does a ResourceQuota denial differ from a FailedScheduling event?
3. Why does a toleration not force a Pod onto a tainted node?
4. How do hard affinity and topology spread interact?
5. What does `minDomains` change when eligible domains disappear?
6. Why may a running Pod remain after a node label is removed?
7. What evidence distinguishes OOMKilled from node-pressure eviction?
8. How can rollout surge exceed a namespace quota?
9. Why is Pod Ready insufficient as the sole recovery signal?
10. What placement and resource rules should be reviewed for PostgreSQL, Kafka and Elasticsearch?

## 22. Part 05 milestone and next chapter

| Chapter | Topic | Writing status |
|---|---|---|
| 021 | Kubernetes Scheduler Internals | Draft |
| 022 | Node Selectors and Affinity Rules | Draft |
| 023 | Taints, Tolerations and Topology Spread | Draft |
| 024 | Resource Requests, Limits, QoS and Quotas | Draft |
| 025 | Scheduling and Resource Pressure Troubleshooting Lab | Draft |

**Part 05 writing milestone reached:** all five chapter drafts are published. Runtime execution, evidence-based acceptance and technical review are still pending.

**Next:** Chapter 026 — Kubernetes Networking Architecture and CNI, the first chapter of Part 06 — Kubernetes Networking.
