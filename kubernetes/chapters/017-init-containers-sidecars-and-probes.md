# Chapter 017 — Init Containers, Sidecars and Probes

**Track:** Kubernetes Administration | **Part 04:** Pods and Workload Controllers | **Status:** Draft — lab validation and review pending

## 1. Learning objectives

After completing this chapter, you should be able to:

1. Explain ordinary init containers, native sidecars, and application containers, including their startup and shutdown ordering.
2. Select and configure startup, readiness, and liveness probes for realistic application behavior.
3. Distinguish container health, Pod readiness, Service endpoint readiness, and application dependency health.
4. Debug blocked initialization, sidecar failures, probe flapping, and CrashLoopBackOff.
5. Validate graceful termination and the effects of probe thresholds.
6. Design safer production patterns for service meshes, log agents, secrets/bootstrap, and stateful workloads.
7. Complete a repeatable Windows PowerShell lab and document evidence-based acceptance.

## 2. Architecture and lifecycle

```text
Pod scheduled to node
    |
    v
kubelet creates Pod sandbox, networking and mounts
    |
    +-- Ordinary init container 1: runs to completion
    +-- Ordinary init container 2: runs to completion
    |
    +-- Native sidecar init container: starts and remains running
    |       (restartPolicy: Always, with startup gating)
    |
    +-- Main application container starts
            |
            +-- startupProbe: startup gate
            +-- readinessProbe: can receive Service traffic?
            +-- livenessProbe: should container restart?
```

A Pod's containers share its network namespace and can share mounted volumes, but do not automatically share a filesystem or process namespace. Sidecars are not a separate top-level Kubernetes resource kind; they are containers in a Pod.

**Kubernetes compatibility:** Native sidecars use an entry under `spec.initContainers` with container-level `restartPolicy: Always`. This feature is stable starting with Kubernetes **v1.33**. Verify the target cluster version and admission support before applying the native sidecar lab. Ordinary multi-container sidecars defined in `spec.containers` work across many earlier Kubernetes versions, but have different lifecycle ordering.

## 3. Ordinary init containers

Ordinary init containers run sequentially before regular application containers. Each must complete successfully before the next ordinary init container or app container can proceed. They are useful for generating configuration, checking prerequisites, or preparing shared files.

```yaml
spec:
  initContainers:
    - name: prepare
      image: busybox:1.36.1
      command: ["sh", "-c", "echo ready > /shared/status"]
      volumeMounts:
        - name: shared
          mountPath: /shared
  containers:
    - name: app
      image: nginx:stable
      volumeMounts:
        - name: shared
          mountPath: /shared
  volumes:
    - name: shared
      emptyDir: {}
```

**Operational caution:** A network wait loop without a timeout can keep a Pod in initialization indefinitely. Readiness probes and application retry logic are often better than hard-blocking on a downstream service. Avoid putting passwords or access tokens into init-container command lines, logs, or ConfigMaps.

### Init failure behavior

With `restartPolicy: Always` or `OnFailure`, failed ordinary init containers are retried with backoff. With `restartPolicy: Never`, a failing init container causes the Pod to fail. Inspect `status.initContainerStatuses`, events, and logs using `kubectl logs pod/<name> -c <init-name>`.

## 4. Sidecars: classic and native

| Aspect | Classic sidecar in `containers` | Native sidecar in `initContainers` |
|---|---|---|
| Declaration | Regular container | Init container with `restartPolicy: Always` |
| Startup ordering | No built-in ordering relative to other app containers | Kubelet starts it during init sequence and advances when started (and startup probe succeeds if present) |
| Lifetime | Runs alongside app containers | Continues running alongside app containers |
| Shutdown ordering | No guaranteed sidecar-last semantics | Native sidecars terminate after main containers, in reverse order |
| Job completion | Running classic sidecar may prevent Pod completion | Native sidecar does not block Job completion after main containers finish |
| Version dependency | Broadly supported | Stable from Kubernetes v1.33 |

Native sidecar containers restart independently according to their special restart policy. Do not confuse `restartPolicy: Always` on a native sidecar with the Pod-wide restart policy.

### Production examples

- Service-mesh proxy: intercepts or manages traffic; coordinate readiness and shutdown.
- Log forwarder: tails shared files or forwards stdout-derived logs; ensure backpressure and retention.
- Certificate/secret refresh helper: writes to a shared volume; use approved workload identity and secret management.
- Local adapter/proxy: provides localhost access to an external system.

**Anti-patterns:** sidecars with unbounded CPU/memory use, broad privileges, hidden egress, or no observable health state.

## 5. Startup, readiness and liveness probes

### What each probe controls

| Probe | Purpose | On failure |
|---|---|---|
| Startup | Allow slow initialization without premature liveness/readiness evaluation | Restart container when failure threshold reached |
| Readiness | Determine whether container is ready for traffic | Pod readiness can become false; Service ready endpoints change |
| Liveness | Detect an irrecoverably unhealthy process | Restart container after failure threshold |

A readiness failure does **not** restart the container. A liveness failure does **not** by itself remove the Pod from Service endpoints before termination; configure readiness separately. Startup probes suppress liveness/readiness execution until startup succeeds.

### Probe types

- **HTTP GET:** successful response codes are 200–399.
- **TCP socket:** checks whether a TCP connection can be established; not full application correctness.
- **Exec:** executes a command in the container; can be costly and prone to timeouts.
- **gRPC:** uses the gRPC health checking protocol; requires supported Kubernetes and app behavior.

Probe success does not prove that a distributed application is globally healthy. Choose checks that represent the purpose of each probe.

### Timing and failure budget

For a probe with `periodSeconds: 5` and `failureThreshold: 6`, six consecutive failed checks ordinarily represent about 30 seconds of probing, but actual wall-clock timing depends on initial delay, probe duration, scheduling, and startup behavior. `timeoutSeconds` defaults to 1 second unless explicitly set. Avoid treating threshold multiplication as an exact SLA.

## 6. Probe design for production

A typical web workload:

```yaml
startupProbe:
  httpGet:
    path: /startup
    port: 8080
  periodSeconds: 5
  failureThreshold: 24
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 3
livenessProbe:
  httpGet:
    path: /live
    port: 8080
  periodSeconds: 10
  timeoutSeconds: 2
  failureThreshold: 3
```

This is a design example; the endpoints must actually exist in the application. A startup budget of approximately two minutes is appropriate only when supported by measured startup distributions. Avoid liveness checks that depend on transient database/network availability: they can trigger mass restarts during downstream incidents.

### Stateful workload considerations

For PostgreSQL, Elasticsearch, Kafka, and MongoDB, define readiness according to safe service participation, not just process existence. A process can be alive but not ready for reads or writes. Do not automatically restart an instance merely because cluster-wide dependencies are briefly unavailable. Validate operator-specific probe semantics before customizing managed workloads.

## 7. Lab prerequisites and safety gate

**Environment:** Windows PowerShell, Docker Desktop, kind, kubectl.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch017 | Out-Null
Set-Location .\k8s-ch017
kind create cluster --name k8s-admin-ch017 --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch017 get nodes -o wide
kubectl --context kind-k8s-admin-ch017 version
```

**Expected:** context `kind-k8s-admin-ch017`, node Ready. Record the server version for native-sidecar compatibility.

**Safety:** Stop if the current context is not the disposable kind cluster. Every mutating command explicitly targets `kind-k8s-admin-ch017`.

## 8. Lab A — Ordinary init container and shared volume

### Step A1 — Create namespace and init workload

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch017
---
apiVersion: v1
kind: Pod
metadata:
  name: init-demo
  namespace: ch017
  labels:
    app: init-demo
spec:
  volumes:
    - name: shared
      emptyDir: {}
  initContainers:
    - name: prepare
      image: busybox:1.36.1
      command: ["sh", "-c", "echo initialized > /shared/status"]
      volumeMounts:
        - name: shared
          mountPath: /shared
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
  containers:
    - name: reader
      image: busybox:1.36.1
      command: ["sh", "-c", "cat /shared/status; sleep 3600"]
      volumeMounts:
        - name: shared
          mountPath: /shared
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\init-demo.yaml

kubectl --context kind-k8s-admin-ch017 apply --dry-run=server -f .\init-demo.yaml
kubectl --context kind-k8s-admin-ch017 apply -f .\init-demo.yaml
kubectl --context kind-k8s-admin-ch017 -n ch017 wait --for=condition=Ready pod/init-demo --timeout=180s
kubectl --context kind-k8s-admin-ch017 -n ch017 logs init-demo -c prepare
kubectl --context kind-k8s-admin-ch017 -n ch017 logs init-demo -c reader
kubectl --context kind-k8s-admin-ch017 -n ch017 get pod init-demo -o jsonpath='{.status.initContainerStatuses[0].state.terminated.reason}'
```

**Expected:** reader logs `initialized`, init container state is `Completed`, and Pod is Ready.

## 9. Lab B — Diagnose failed initialization

### Step B1 — Create a deliberately failing init container

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: init-failure
  namespace: ch017
spec:
  restartPolicy: Always
  initContainers:
    - name: prerequisite
      image: busybox:1.36.1
      command: ["sh", "-c", "echo prerequisite-unavailable; exit 1"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
'@ | Set-Content -Encoding ascii .\init-failure.yaml

kubectl --context kind-k8s-admin-ch017 apply -f .\init-failure.yaml
kubectl --context kind-k8s-admin-ch017 -n ch017 get pod init-failure
kubectl --context kind-k8s-admin-ch017 -n ch017 describe pod init-failure
kubectl --context kind-k8s-admin-ch017 -n ch017 logs init-failure -c prerequisite
```

**Expected:** Pod does not initialize; status may show `Init:Error` or `Init:CrashLoopBackOff` depending on timing. App container does not start.

### Step B2 — Recover safely

Ordinary Pod init-container commands cannot generally be changed in place. Delete this disposable Pod and recreate a corrected copy:

```powershell
kubectl --context kind-k8s-admin-ch017 -n ch017 delete pod init-failure
(Get-Content .\init-failure.yaml -Raw).Replace('echo prerequisite-unavailable; exit 1','echo prerequisite-restored; exit 0') | Set-Content -Encoding ascii .\init-recovered.yaml
kubectl --context kind-k8s-admin-ch017 apply --dry-run=server -f .\init-recovered.yaml
kubectl --context kind-k8s-admin-ch017 apply -f .\init-recovered.yaml
kubectl --context kind-k8s-admin-ch017 -n ch017 wait --for=condition=Ready pod/init-failure --timeout=180s
kubectl --context kind-k8s-admin-ch017 -n ch017 logs init-failure -c prerequisite
```

**Expected:** corrected init completes and app container starts. Confirm the replacement text before applying if the shell command was edited manually.

## 10. Lab C — Native sidecar lifecycle

**Compatibility gate:** Only run this lab when the Kubernetes server supports native sidecars (stable in v1.33+). On older versions, skip and mark **Blocked — incompatible server**, rather than rewriting the manifest into a different lifecycle model.

### Step C1 — Create native sidecar and app

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: native-sidecar-demo
  namespace: ch017
spec:
  volumes:
    - name: shared
      emptyDir: {}
  initContainers:
    - name: sidecar
      image: busybox:1.36.1
      restartPolicy: Always
      command: ["sh", "-c", "echo sidecar-started > /shared/sidecar; while true; do sleep 10; done"]
      startupProbe:
        exec:
          command: ["sh", "-c", "test -f /shared/sidecar"]
        periodSeconds: 2
        failureThreshold: 15
      volumeMounts:
        - name: shared
          mountPath: /shared
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "cat /shared/sidecar; sleep 3600"]
      volumeMounts:
        - name: shared
          mountPath: /shared
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\native-sidecar.yaml

kubectl --context kind-k8s-admin-ch017 apply --dry-run=server -f .\native-sidecar.yaml
kubectl --context kind-k8s-admin-ch017 apply -f .\native-sidecar.yaml
kubectl --context kind-k8s-admin-ch017 -n ch017 wait --for=condition=Ready pod/native-sidecar-demo --timeout=180s
kubectl --context kind-k8s-admin-ch017 -n ch017 logs native-sidecar-demo -c app
kubectl --context kind-k8s-admin-ch017 -n ch017 get pod native-sidecar-demo -o jsonpath='{range .status.initContainerStatuses[*]}{.name}{" ready="}{.ready}{"\n"}{end}'
```

**Expected:** app reads `sidecar-started`; sidecar remains running. A successful native sidecar startup probe allows later init/app containers to proceed; it does not require sidecar termination.

## 11. Lab D — Readiness probe failure and Service endpoint removal

### Step D1 — Deploy healthy app

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch017
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
            periodSeconds: 3
            failureThreshold: 2
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: ch017
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
'@ | Set-Content -Encoding ascii .\web.yaml

kubectl --context kind-k8s-admin-ch017 apply -f .\web.yaml
kubectl --context kind-k8s-admin-ch017 -n ch017 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch017 -n ch017 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** two Ready Pods and two ready endpoints.

### Step D2 — Break readiness without crashing the process

Patch the Pod template to probe a nonexistent path:

```powershell
kubectl --context kind-k8s-admin-ch017 -n ch017 patch deployment web --type=json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/not-found"}]'
kubectl --context kind-k8s-admin-ch017 -n ch017 get pods -l app=web
kubectl --context kind-k8s-admin-ch017 -n ch017 get endpointslices -l kubernetes.io/service-name=web
kubectl --context kind-k8s-admin-ch017 -n ch017 describe deployment web
```

**Expected:** newly created Pods fail readiness (HTTP 404). During rolling update, the original healthy Pods may remain serving because the Deployment will not replace all healthy replicas with unready ones. **Do not expect zero Service endpoints** in this scenario; the key observation is that the unready new Pods are excluded from ready endpoints.

### Step D3 — Restore the declared template

```powershell
kubectl --context kind-k8s-admin-ch017 apply -f .\web.yaml
kubectl --context kind-k8s-admin-ch017 -n ch017 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch017 -n ch017 get pods -l app=web
kubectl --context kind-k8s-admin-ch017 -n ch017 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** two Ready replicas and healthy endpoints. If field ownership prevents apply from restoring the path, inspect managed fields and use an explicitly reviewed patch in this disposable cluster.

## 12. Lab E — Liveness failure and container restarts

Create a standalone Pod whose liveness probe always fails while the NGINX process itself remains healthy:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: liveness-demo
  namespace: ch017
spec:
  containers:
    - name: nginx
      image: nginx:stable
      livenessProbe:
        httpGet:
          path: /missing-health
          port: 80
        initialDelaySeconds: 3
        periodSeconds: 5
        failureThreshold: 2
      resources:
        requests:
          cpu: 25m
          memory: 32Mi
'@ | Set-Content -Encoding ascii .\liveness-demo.yaml

kubectl --context kind-k8s-admin-ch017 apply -f .\liveness-demo.yaml
kubectl --context kind-k8s-admin-ch017 -n ch017 get pod liveness-demo
kubectl --context kind-k8s-admin-ch017 -n ch017 describe pod liveness-demo
kubectl --context kind-k8s-admin-ch017 -n ch017 get pod liveness-demo -o jsonpath='{.status.containerStatuses[0].restartCount}'
```

**Expected:** liveness failures eventually restart NGINX and increment restartCount. This may take several probe periods. Avoid aggressive liveness settings on production workloads.

## 13. Lab F — Startup probe budget

A startup probe can protect a slow-starting application from premature liveness restarts. Demonstrate the configuration using a disposable Pod with an application that becomes ready after a delay:

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: startup-demo
  namespace: ch017
spec:
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 12; touch /tmp/started; sleep 3600"]
      startupProbe:
        exec:
          command: ["sh", "-c", "test -f /tmp/started"]
        periodSeconds: 3
        failureThreshold: 10
      livenessProbe:
        exec:
          command: ["sh", "-c", "test -f /tmp/started"]
        periodSeconds: 5
      readinessProbe:
        exec:
          command: ["sh", "-c", "test -f /tmp/started"]
        periodSeconds: 3
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\startup-demo.yaml

kubectl --context kind-k8s-admin-ch017 apply -f .\startup-demo.yaml
kubectl --context kind-k8s-admin-ch017 -n ch017 wait --for=condition=Ready pod/startup-demo --timeout=180s
kubectl --context kind-k8s-admin-ch017 -n ch017 describe pod startup-demo
kubectl --context kind-k8s-admin-ch017 -n ch017 get pod startup-demo -o jsonpath='{.status.containerStatuses[0].restartCount}'
```

**Expected:** initial startup probe failures, followed by success after the file appears. Readiness then succeeds without an avoidable restart.

## 14. Troubleshooting decision matrix

| Symptom | Evidence | Likely cause |
|---|---|---|
| `Init:CrashLoopBackOff` | initContainerStatuses, init logs | Failed prerequisite, invalid command, permissions |
| App never starts | init status and events | Init blocked or sidecar startup probe failing |
| Sidecar starts but app fails | Container logs, shared volume, port conflicts | Incorrect startup dependency |
| Running but not Ready | Readiness failures, Pod conditions | App not accepting traffic |
| Service endpoints missing | EndpointSlices and Pod readiness | Unready Pods or selector mismatch |
| Restart count increases | Liveness events, lastState, logs | Liveness failure or process exit |
| Slow app restarts during initialization | Startup/liveness config | Startup budget too short |
| Job never completes | Container lifecycle | Classic sidecar stays running |
| Shutdown hangs | preStop, grace period, sidecar order | Slow drain or blocked termination |
| Probe success but user errors persist | Application traces, dependencies | Probe not representative of user path |

### Read-only triage commands

```powershell
kubectl --context kind-k8s-admin-ch017 -n ch017 get pods -o wide
kubectl --context kind-k8s-admin-ch017 -n ch017 describe pod init-failure
kubectl --context kind-k8s-admin-ch017 -n ch017 logs init-failure -c prerequisite --previous
kubectl --context kind-k8s-admin-ch017 -n ch017 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch017 -n ch017 get endpointslices -l kubernetes.io/service-name=web
kubectl --context kind-k8s-admin-ch017 -n ch017 get deployment web -o yaml
```

`--previous` only works when a previous terminated instance is available; use current logs otherwise.

## 15. Production incident response: probe-induced outage

1. **Confirm scope:** context, namespace, workload, image, deployment revision, affected replicas, user-facing error rate.
2. **Separate failure types:** application crash versus probe-driven restart versus readiness-only traffic removal.
3. **Inspect evidence:** Pod conditions, probe events, restart counts, previous logs, EndpointSlices, node pressure.
4. **Check recent changes:** rollout history, probe path/port, thresholds, application startup time, sidecar injection.
5. **Stabilize safely:** roll back a faulty rollout or correct probe configuration through reviewed manifests.
6. **Validate recovery:** Ready endpoints, request success, latency, error rate, restart stability, and logs.
7. **Prevent recurrence:** use startup budgets, readiness contracts, measured thresholds, and alerting on probe failure spikes.

Avoid disabling probes indefinitely as a blanket fix. If a probe is causing harm, document the risk and use a controlled temporary change with rollback and monitoring.

## 16. SRE/DBRE design checklist

- Init tasks should be deterministic, idempotent, bounded, and observable.
- Prefer application retry/backoff to endless init-time dependency waits.
- Give sidecars explicit resource requests and limits appropriate to workload behavior.
- Treat native-sidecar version compatibility as a deployment gate.
- Use startup probes for measured slow initialization.
- Use readiness for traffic eligibility and liveness for genuine local process deadlock.
- Avoid downstream dependency checks in liveness that trigger cascading restarts.
- Monitor probe failures, restarts, Ready endpoint counts, rollout progress, and startup latency.
- Validate graceful shutdown and sidecar termination ordering before production rollout.
- For stateful databases and brokers, follow operator/vendor guidance before changing probes.

## 17. Cleanup and rollback

Verify the exact disposable context:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch017 get nodes
```

Then remove only lab resources:

```powershell
kubectl --context kind-k8s-admin-ch017 delete namespace ch017
kind delete cluster --name k8s-admin-ch017
kind get clusters
Remove-Item .\init-demo.yaml, .\init-failure.yaml, .\init-recovered.yaml, .\native-sidecar.yaml, .\web.yaml, .\liveness-demo.yaml, .\startup-demo.yaml -ErrorAction SilentlyContinue
```

Deleting the namespace or kind cluster destroys its disposable resources and data. Do not run equivalent commands on shared or production clusters.

## 18. Acceptance checklist

- [ ] Verified disposable cluster context and Kubernetes server version.
- [ ] Created an ordinary init container and validated shared-volume output.
- [ ] Reproduced failed init and recovered through Pod recreation.
- [ ] Tested native sidecar lifecycle on a compatible cluster or recorded a compatibility block.
- [ ] Deployed readiness-gated application and inspected ready EndpointSlices.
- [ ] Demonstrated unready new Pods during a rolling update without claiming all endpoints disappear.
- [ ] Restored readiness and completed rollout.
- [ ] Triggered liveness-driven restarts and inspected restartCount.
- [ ] Validated startup probe gating for delayed initialization.
- [ ] Recorded sanitized logs, events, and probe settings.
- [ ] Cleaned up disposable resources.

## 19. Knowledge check

1. What differentiates ordinary init containers from native sidecars?
2. Why might a classic sidecar prevent a Job from completing?
3. What Kubernetes version made native sidecars stable?
4. Why does readiness failure not restart a container?
5. How does a startup probe affect liveness/readiness execution?
6. Why can a bad readiness rollout leave old Pods serving?
7. What evidence distinguishes probe-induced restart from application crash?
8. Why should liveness avoid transient database dependency checks?
9. What risks come from an unbounded init-container wait loop?
10. What must be validated before introducing a sidecar into a production stateful workload?

## 20. Status and next chapter

**Draft published; lab commands have not been independently executed.** Mark **Lab Validated** only after observed acceptance results and **Complete** after technical review.

**Next:** Chapter 018 — Deployments, ReplicaSets and Rollouts.
