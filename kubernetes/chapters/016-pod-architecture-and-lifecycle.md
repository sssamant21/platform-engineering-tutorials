# Chapter 016 — Pod Architecture and Lifecycle

**Track:** Kubernetes Administration | **Part 04:** Pods and Workload Controllers | **Status:** Draft — hands-on lab and review pending

## 1. Learning outcomes

By the end of this chapter, you will be able to:

1. Explain the Pod as Kubernetes' smallest deployable unit and distinguish it from a container and a controller.
2. Identify the pause/sandbox infrastructure, shared Pod network namespace, storage, and container runtime interactions.
3. Trace scheduling, Pod conditions, phases, container states, probes, and termination.
4. Investigate Pending, ContainerCreating, Running, CrashLoopBackOff, and Terminating symptoms without confusing phase with kubectl's STATUS column.
5. Configure resource requests/limits, termination grace periods, and application shutdown behavior.
6. Perform controlled Pod failure and recovery exercises and capture operational evidence.
7. Explain why production workloads generally need controllers instead of standalone Pods.

## 2. Pod architecture

```text
API server <- Deployment/ReplicaSet or direct Pod manifest
      |
      v
  Scheduler assigns spec.nodeName
      |
      v
    kubelet on selected node
      |
      +-- CRI -> containerd -> sandbox / network namespace
      |                    |
      |                    +-- application container
      |                    +-- optional sidecar(s)
      |                    +-- init containers (run before app startup)
      |
      +-- CNI attaches Pod network
      +-- CSI / kubelet mounts volumes
      +-- probes + lifecycle handling
      +-- status reported to API server
```

A **Pod** groups one or more closely coupled containers that share networking and can share mounted volumes. Containers in the same Pod share an IP address and port space and can reach each other using `localhost`. They do **not** automatically share a process namespace or filesystem. Process namespace sharing requires explicit configuration; shared data requires volumes.

The sandbox or infrastructure container establishes the Pod-level execution environment. Its exact implementation varies by runtime and platform. A Pod is scheduled as a unit onto **one node**; its containers are not independently distributed across nodes.

### Pod versus container versus controller

| Concept | Role | SRE implication |
|---|---|---|
| Container | Runs a process/image | Can restart within the same Pod |
| Pod | Scheduling and networking unit | Replacement usually gets a new UID and IP |
| ReplicaSet | Maintains a target count of Pods | Recreates deleted Pods |
| Deployment | Manages ReplicaSets and rollout history | Preferred for stateless applications |
| StatefulSet | Stable identity and ordered management | Common for stateful workloads |
| DaemonSet | Runs Pods across eligible nodes | Agents and node services |
| Job/CronJob | Finite or scheduled execution | Batch semantics differ from long-running services |

**Production rule:** A standalone Pod is suitable for controlled experiments, but is not automatically recreated if deleted. A Deployment-managed Pod is recreated by its controller.

## 3. Pod specification essentials

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example
  namespace: training
  labels:
    app: example
spec:
  restartPolicy: Always
  terminationGracePeriodSeconds: 30
  containers:
    - name: web
      image: nginx:stable
      ports:
        - containerPort: 80
      resources:
        requests:
          cpu: 50m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 256Mi
      readinessProbe:
        httpGet:
          path: /
          port: 80
        periodSeconds: 5
```

A Pod spec describes containers, images, commands, environment, volumes, service account, security context, resources, scheduling constraints, probes, and restart policy. Most Pod spec fields are immutable after creation; controllers generally replace Pods to apply template changes.

### Requests and limits

CPU requests influence scheduling and CPU shares; CPU limits can throttle workloads. Memory requests influence placement and QoS; exceeding memory limits can lead to OOM termination. Node memory pressure may trigger evictions independently of a container's limit. The scheduler evaluates requests against **allocatable** node resources, not observed free memory.

### Restart policies

`Always`, `OnFailure`, and `Never` apply to containers in the Pod, subject to workload type and Kubernetes semantics. Deployment Pod templates use `Always`. A container restart does not mean the Pod object was recreated.

## 4. Lifecycle states: phases, conditions, and container states

### Pod phases

| Phase | Meaning | Common interpretation |
|---|---|---|
| Pending | Accepted, but one or more containers not ready to run | Scheduling, volumes, image setup |
| Running | Bound to node and at least one container started or is starting/restarting | Does **not** guarantee application readiness |
| Succeeded | All containers terminated successfully; won't restart | Typical completed batch Pod |
| Failed | All containers terminated and at least one failed | Terminal failure |
| Unknown | Pod state could not be obtained | Node/kubelet communication problems |

The `STATUS` column shown by `kubectl get pods` is a human-oriented summary and may show `CrashLoopBackOff`, `ImagePullBackOff`, `Terminating`, or `ContainerCreating`. These are **not Pod phases**.

### Conditions

Important Pod conditions include `PodScheduled`, `Initialized`, `ContainersReady`, and `Ready`. Some clusters expose additional conditions such as `PodReadyToStartContainers`. Inspect the actual condition list; do not assume every condition exists on every Kubernetes version.

### Container states

- **Waiting:** not currently running; reason can include `ContainerCreating` or `CrashLoopBackOff`.
- **Running:** process started, with a start timestamp.
- **Terminated:** process exited; inspect exit code, reason, start and finish times.

`restartCount` counts container restarts in the Pod; the count is not the number of Pod recreations.

## 5. Scheduling and startup sequence

1. Client creates the Pod through the API server.
2. Admission validates/defaults the object.
3. Scheduler chooses an eligible node and binds the Pod.
4. Kubelet observes the assigned Pod and asks the runtime to establish a sandbox.
5. Network setup, volume mounts, image pulls, and init-container processing occur.
6. Application containers start.
7. Startup, readiness, and liveness probes run according to their configuration.
8. Kubelet reports status; Services select Ready endpoints where applicable.

The sequence can overlap internally; avoid assuming a single universal order for every runtime, volume driver, or init/sidecar configuration.

## 6. Probes and application availability

| Probe | Question answered | Failure effect |
|---|---|---|
| Startup | Has the application finished starting? | Eventually restarts container if threshold exceeded; suppresses other probes until success |
| Readiness | Should this Pod receive Service traffic? | Removes unready Pod from ready Service endpoints |
| Liveness | Should this container be restarted? | Repeated failures restart the container |

**Probe design:** Use a lightweight, reliable readiness endpoint; avoid liveness checks that fail during transient dependency outages. Overaggressive liveness checks can amplify incidents. HTTP 200 alone does not guarantee the application's downstream dependencies are healthy.

## 7. Termination and graceful shutdown

A Pod deletion normally begins a grace period. Kubelet asks the runtime to stop containers (typically SIGTERM followed by forced termination after the grace period). If configured, `preStop` runs before termination signaling and consumes the same grace-period budget. Endpoint readiness and traffic removal can be asynchronous, so applications should stop accepting new work and finish in-flight work appropriately.

Important distinctions:

- A deletion timestamp indicates deletion was requested, not that all cleanup finished.
- Finalizers can block API object removal.
- `kubectl delete pod --force --grace-period=0` bypasses normal graceful termination assumptions and may leave processes running temporarily on an unreachable node. **Do not use it as a default production fix.**
- PodDisruptionBudgets govern certain voluntary evictions, not every Pod deletion or node failure.

## 8. Lab prerequisites and safety

**Environment:** Windows PowerShell, Docker Desktop, kind, kubectl. Run in a disposable cluster only.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch016 | Out-Null
Set-Location .\k8s-ch016
kind create cluster --name k8s-admin-ch016 --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch016 get nodes -o wide
```

**Expected:** active context is `kind-k8s-admin-ch016` and the node is Ready. Stop if the context differs. All write commands below explicitly use the disposable context.

## 9. Lab A — Inspect Pod anatomy and shared networking

### Step A1 — Create namespace and multi-container Pod

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch016
---
apiVersion: v1
kind: Pod
metadata:
  name: shared-pod
  namespace: ch016
  labels:
    app: shared-pod
spec:
  containers:
    - name: web
      image: nginx:stable
      ports:
        - containerPort: 80
      resources:
        requests:
          cpu: 25m
          memory: 32Mi
    - name: toolbox
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\shared-pod.yaml

kubectl --context kind-k8s-admin-ch016 apply --dry-run=server -f .\shared-pod.yaml
kubectl --context kind-k8s-admin-ch016 apply -f .\shared-pod.yaml
kubectl --context kind-k8s-admin-ch016 -n ch016 wait --for=condition=Ready pod/shared-pod --timeout=180s
kubectl --context kind-k8s-admin-ch016 -n ch016 get pod shared-pod -o wide
```

**Expected:** Pod shows `2/2` containers Ready.

### Step A2 — Verify localhost networking

```powershell
kubectl --context kind-k8s-admin-ch016 -n ch016 exec shared-pod -c toolbox -- wget -qO- http://127.0.0.1:80
kubectl --context kind-k8s-admin-ch016 -n ch016 exec shared-pod -c toolbox -- hostname
kubectl --context kind-k8s-admin-ch016 -n ch016 get pod shared-pod -o jsonpath='{.status.podIP}'
```

**Expected:** BusyBox retrieves the NGINX welcome page through localhost despite running in a different container. This demonstrates shared Pod networking, not shared filesystem or process namespace.

### Step A3 — Inspect container states

```powershell
kubectl --context kind-k8s-admin-ch016 -n ch016 describe pod shared-pod
kubectl --context kind-k8s-admin-ch016 -n ch016 get pod shared-pod -o jsonpath='{range .status.containerStatuses[*]}{.name}{" ready="}{.ready}{" restarts="}{.restartCount}{"\n"}{end}'
kubectl --context kind-k8s-admin-ch016 -n ch016 get pod shared-pod -o jsonpath='{range .status.conditions[*]}{.type}{"="}{.status}{"\n"}{end}'
```

## 10. Lab B — Pod phases and controlled completion

Create a short-lived Pod with `restartPolicy: Never`:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: completed-task
  namespace: ch016
spec:
  restartPolicy: Never
  containers:
    - name: task
      image: busybox:1.36.1
      command: ["sh", "-c", "echo task-complete; sleep 2; exit 0"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\completed-task.yaml

kubectl --context kind-k8s-admin-ch016 apply -f .\completed-task.yaml
kubectl --context kind-k8s-admin-ch016 -n ch016 wait --for=jsonpath='{.status.phase}'=Succeeded pod/completed-task --timeout=180s
kubectl --context kind-k8s-admin-ch016 -n ch016 get pod completed-task -o jsonpath='{.status.phase}'
kubectl --context kind-k8s-admin-ch016 -n ch016 logs completed-task
```

**Expected:** `Succeeded` and `task-complete`. A completed standalone Pod remains in the API until deleted or otherwise cleaned up.

## 11. Lab C — Diagnose CrashLoopBackOff versus Pod phase

### Step C1 — Create a deliberately failing container

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: crash-demo
  namespace: ch016
spec:
  restartPolicy: Always
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "echo intentional-failure; exit 1"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\crash-demo.yaml

kubectl --context kind-k8s-admin-ch016 apply -f .\crash-demo.yaml
kubectl --context kind-k8s-admin-ch016 -n ch016 get pod crash-demo
kubectl --context kind-k8s-admin-ch016 -n ch016 describe pod crash-demo
kubectl --context kind-k8s-admin-ch016 -n ch016 logs crash-demo -c app --previous
```

**Expected:** container repeatedly exits with code 1 and enters restart backoff. Depending on timing, `kubectl get` may show `Error`, `Running`, or `CrashLoopBackOff`; the Pod phase and container waiting/terminated state are distinct. `--previous` becomes available after at least one restart.

### Step C2 — Inspect precise status

```powershell
kubectl --context kind-k8s-admin-ch016 -n ch016 get pod crash-demo -o jsonpath='{.status.phase}'
kubectl --context kind-k8s-admin-ch016 -n ch016 get pod crash-demo -o jsonpath='{.status.containerStatuses[0].restartCount}'
kubectl --context kind-k8s-admin-ch016 -n ch016 get pod crash-demo -o yaml
```

**Expected:** restart count increases over time; record the actual container state and exit reason.

## 12. Lab D — Scheduling failure and recovery

### Step D1 — Create an unschedulable Pod

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: pending-demo
  namespace: ch016
spec:
  nodeSelector:
    training.example.com/nonexistent-node: "true"
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\pending-demo.yaml

kubectl --context kind-k8s-admin-ch016 apply -f .\pending-demo.yaml
kubectl --context kind-k8s-admin-ch016 -n ch016 get pod pending-demo -o wide
kubectl --context kind-k8s-admin-ch016 -n ch016 describe pod pending-demo
```

**Expected:** `Pending` and `FailedScheduling` because no node matches the selector.

### Step D2 — Recover by recreating the standalone Pod

A Pod's nodeSelector is not generally mutable. Delete and recreate the **lab-only** Pod with a corrected manifest:

```powershell
kubectl --context kind-k8s-admin-ch016 -n ch016 delete pod pending-demo
(Get-Content .\pending-demo.yaml -Raw) -replace '(?m)^  nodeSelector:\r?\n    training.example.com/nonexistent-node: "true"\r?\n','' | Set-Content -Encoding ascii .\pending-fixed.yaml
kubectl --context kind-k8s-admin-ch016 apply --dry-run=server -f .\pending-fixed.yaml
kubectl --context kind-k8s-admin-ch016 apply -f .\pending-fixed.yaml
kubectl --context kind-k8s-admin-ch016 -n ch016 wait --for=condition=Ready pod/pending-demo --timeout=180s
```

**Expected:** Pod schedules and becomes Ready. If the PowerShell replacement did not remove the selector, inspect `pending-fixed.yaml` before applying; never assume text substitution succeeded.

## 13. Lab E — Readiness and Service endpoint behavior

### Step E1 — Deploy a managed application

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch016
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 5
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: ch016
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
'@ | Set-Content -Encoding ascii .\web.yaml

kubectl --context kind-k8s-admin-ch016 apply -f .\web.yaml
kubectl --context kind-k8s-admin-ch016 -n ch016 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch016 -n ch016 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** two Ready Pods and two ready Service endpoints.

### Step E2 — Contrast controller-managed replacement

```powershell
$pod = kubectl --context kind-k8s-admin-ch016 -n ch016 get pods -l app=web -o jsonpath='{.items[0].metadata.name}'
$uid = kubectl --context kind-k8s-admin-ch016 -n ch016 get pod $pod -o jsonpath='{.metadata.uid}'
kubectl --context kind-k8s-admin-ch016 -n ch016 delete pod $pod
kubectl --context kind-k8s-admin-ch016 -n ch016 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch016 -n ch016 get pods -l app=web -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,READY:.status.containerStatuses[0].ready'
```

**Expected:** ReplicaSet creates a replacement with a different UID. Deleting `shared-pod` (standalone) would not cause automatic recreation.

## 14. Lab F — Graceful termination and deletion observation

Create a Pod whose shell traps termination and delays exit briefly. This is a controlled demonstration; actual shutdown behavior varies by image, shell, and runtime.

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: shutdown-demo
  namespace: ch016
spec:
  terminationGracePeriodSeconds: 20
  containers:
    - name: app
      image: busybox:1.36.1
      command:
        - sh
        - -c
        - |
          trap 'echo SIGTERM-received; sleep 5; exit 0' TERM
          echo started
          while true; do sleep 1; done
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\shutdown-demo.yaml

kubectl --context kind-k8s-admin-ch016 apply -f .\shutdown-demo.yaml
kubectl --context kind-k8s-admin-ch016 -n ch016 wait --for=condition=Ready pod/shutdown-demo --timeout=180s
kubectl --context kind-k8s-admin-ch016 -n ch016 delete pod shutdown-demo --wait=false
kubectl --context kind-k8s-admin-ch016 -n ch016 get pod shutdown-demo -o yaml
```

**Expected:** if inspected before removal, `deletionTimestamp` is visible. It is also valid for the Pod to disappear before the inspection. Container logs may not remain accessible after deletion; capture logs beforehand or use centralized logging when evidence is required.

**Do not** use `--force --grace-period=0` to speed up this exercise.

## 15. Troubleshooting decision matrix

| Symptom | First evidence | Likely area |
|---|---|---|
| Pod Pending, no node | `describe pod` / FailedScheduling | Selectors, affinity, taints, requests |
| Pod Pending, node assigned | Events, init status, image and volume details | Image, CSI, CNI, runtime |
| ContainerCreating | Events, kubelet/runtime logs | Sandbox, network, volume |
| ImagePullBackOff | Events and imagePullSecrets | Registry, credentials, image tag |
| CrashLoopBackOff | `logs --previous`, exit code, restart count | Process crash, configuration, probes |
| Running but not Ready | Conditions, readiness probe, EndpointSlices | App readiness |
| OOMKilled | Container lastState, memory limit | Memory pressure/limit |
| Evicted | Pod reason/message, node conditions | Node resource pressure |
| Terminating too long | deletionTimestamp, finalizers, node reachability | Cleanup and shutdown |
| Pod deleted but reappears | OwnerReferences, ReplicaSet | Expected controller reconciliation |

### Production-safe read-only triage

```powershell
kubectl --context kind-k8s-admin-ch016 -n ch016 get pods -o wide
kubectl --context kind-k8s-admin-ch016 -n ch016 describe pod crash-demo
kubectl --context kind-k8s-admin-ch016 -n ch016 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch016 -n ch016 logs crash-demo -c app --previous --tail=100
kubectl --context kind-k8s-admin-ch016 -n ch016 get pods -o json
kubectl --context kind-k8s-admin-ch016 get nodes -o wide
```

Always capture context, namespace, Pod name/UID, node, image, timestamps, container state, exit code, events, and relevant logs before remediation. Redact credentials and sensitive application data.

## 16. Production SRE/DBRE considerations

- Use Deployments for stateless services; use StatefulSets/Jobs where their semantics fit.
- Set resource requests based on observed workloads and capacity; review limits for CPU throttling and OOM risk.
- Design readiness and graceful shutdown for connection draining and in-flight requests.
- Keep liveness independent of transient downstream failures where possible.
- Use PodDisruptionBudgets and topology spread to reduce voluntary disruption, while ensuring spare capacity.
- Monitor restart rates, Pending time, readiness, OOM kills, evictions, and Pod startup latency.
- For PostgreSQL, Kafka, Elasticsearch, and other stateful systems, understand data ownership and storage attachment before deleting Pods.
- Never assume `Running` means healthy or `CrashLoopBackOff` is a Pod phase.

## 17. Cleanup and rollback

Verify the exact lab context:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch016 get nodes
```

Then remove only disposable resources:

```powershell
kubectl --context kind-k8s-admin-ch016 delete namespace ch016
kind delete cluster --name k8s-admin-ch016
kind get clusters
Remove-Item .\shared-pod.yaml, .\completed-task.yaml, .\crash-demo.yaml, .\pending-demo.yaml, .\pending-fixed.yaml, .\web.yaml, .\shutdown-demo.yaml -ErrorAction SilentlyContinue
```

Cluster deletion permanently removes local workloads and cluster data. Do not execute these commands in shared environments.

## 18. Acceptance checklist

- [ ] Created disposable kind cluster and verified context.
- [ ] Deployed a two-container Pod and demonstrated localhost networking.
- [ ] Inspected Pod phases, conditions, and container states.
- [ ] Ran a finite Pod to Succeeded.
- [ ] Reproduced a container restart/backoff and inspected previous logs.
- [ ] Reproduced FailedScheduling and recovered with a corrected manifest.
- [ ] Deployed a two-replica Deployment and verified Service endpoints.
- [ ] Deleted a managed Pod and verified controller replacement and new UID.
- [ ] Observed graceful deletion semantics without force deletion.
- [ ] Captured sanitized diagnostic evidence.
- [ ] Cleaned up disposable resources.

## 19. Knowledge check

1. Why are all containers in a Pod scheduled to one node?
2. What do containers in the same Pod share automatically?
3. Why is CrashLoopBackOff not a Pod phase?
4. What is the difference between a container restart and a Pod replacement?
5. Why can a Running Pod be unavailable to Service traffic?
6. How do requests and limits affect scheduling and runtime behavior?
7. Why should liveness and readiness checks serve different purposes?
8. What happens when a standalone Pod is deleted versus a Deployment-managed Pod?
9. What are the risks of force-deleting a Pod on an unreachable node?
10. What evidence should an SRE capture before changing a failing Pod?

## 20. Chapter status and next

**Draft published.** Lab commands and acceptance outcomes are **not yet runtime-verified**. Promote to Lab Validated only after execution and evidence review.

**Next:** Chapter 017 — Init Containers, Sidecars and Probes.
