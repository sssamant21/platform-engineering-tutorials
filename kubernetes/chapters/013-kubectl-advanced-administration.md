# Chapter 013 — kubectl Advanced Administration

**Track:** Kubernetes Administration · **Part:** 03 — Kubernetes API and Resource Administration · **Level:** Intermediate–Advanced · **Status:** Draft — lab execution pending

## 1. Objectives

This chapter develops practical kubectl skills for day-to-day SRE and platform operations. By the end, you should be able to:

1. Operate safely across clusters, namespaces, and multiple kubeconfig files.
2. Use advanced output formats, selectors, JSONPath, custom columns, and sorting.
3. Inspect rollout history, events, logs, resource utilization, and live resource state.
4. Distinguish imperative commands, client/server dry runs, apply, patch, edit, replace, and diff.
5. Use server-side apply and understand managed fields and field ownership.
6. Diagnose workloads with describe, logs, exec, port-forward, and ephemeral debug containers.
7. Perform controlled rollout, scale, wait, drain, and rollback operations.
8. Build a reproducible evidence-collection workflow without leaking credentials.

## 2. How kubectl interacts with the cluster

```text
PowerShell / terminal
       |
    kubectl
       |
  kubeconfig: context + cluster + user
       |
   HTTPS -> API server
       |
  authentication -> authorization -> admission
       |
    Kubernetes resources
       |
 controllers reconcile desired state
```

kubectl is a Kubernetes API client. Most commands send requests to the API server; `kubectl logs`, `exec`, `attach`, and `port-forward` also involve streaming or proxying through the API server to node/runtime endpoints.

### Safety tiers

| Tier | Commands | Operational posture |
|---|---|---|
| Read-only | `get`, `describe`, `api-resources`, `auth can-i`, `logs`, `top` | Usually safe; watch output volume and sensitive data |
| Validation | `diff`, `apply --dry-run=server`, `create --dry-run=client` | Validate before writes; admission behavior can vary |
| Mutating | `apply`, `patch`, `scale`, `annotate`, `label`, `rollout restart` | Review scope, impact, and rollback |
| Potentially disruptive | `delete`, `drain`, `replace --force`, `exec` with mutations, debug privileged nodes | Change control and explicit authorization required |

**Rule:** Always verify the cluster context and namespace before mutating resources.

## 3. Contexts and kubeconfig administration

```powershell
kubectl config get-contexts
kubectl config current-context
kubectl config view --minify
kubectl config get-clusters
kubectl config get-users
```

Use explicit targeting for operational scripts:

```powershell
kubectl --context kind-k8s-admin-ch013 -n ch013 get pods
```

Kubeconfig supports multiple clusters and users. On Windows, the `KUBECONFIG` environment variable uses a semicolon-separated list of files. A merged kubeconfig can create name collisions; inspect effective contexts and user references before use.

**Security:** Kubeconfig can contain bearer tokens, client certificates, or credential-exec configuration. Do not print raw secrets into incident reports or commit kubeconfig files to Git.

## 4. Output formats, selectors, and filtering

### Output formats

```powershell
kubectl get pods -o wide
kubectl get pods -o yaml
kubectl get pods -o json
kubectl get pods -o name
kubectl get pods -o custom-columns='NAME:.metadata.name,NODE:.spec.nodeName,PHASE:.status.phase'
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'
```

### Selectors

```powershell
kubectl get pods -l app=web
kubectl get pods -l 'environment in (dev,test)'
kubectl get pods --field-selector=status.phase=Running
kubectl get pods --sort-by=.metadata.creationTimestamp
```

**Label selectors** operate on labels. **Field selectors** support only fields implemented for the resource type; they are not arbitrary JSON queries. JSONPath formats client output, but complex filtering is often easier using PowerShell's `ConvertFrom-Json` and object pipelines.

### PowerShell-native JSON processing

```powershell
$pods = kubectl get pods -o json | ConvertFrom-Json
$pods.items | Select-Object @{Name='Pod';Expression={$_.metadata.name}}, @{Name='Node';Expression={$_.spec.nodeName}}
```

Always use an explicit `--context` in scripts that might run in multiple environments.

## 5. Imperative versus declarative operations

| Command | Behavior | Common use |
|---|---|---|
| `kubectl create` | Create object; fails if already exists | Quick labs, initial creation |
| `kubectl apply -f` | Reconcile declared configuration | Repeatable management |
| `kubectl apply --server-side` | Server-side apply with managed fields | Multi-manager ownership |
| `kubectl patch` | Modify selected fields | Scoped emergency change |
| `kubectl edit` | Open editor and update object | Manual change; audit carefully |
| `kubectl replace` | Replace entire resource representation | Specialized use; overwrite risk |
| `kubectl diff -f` | Show proposed differences | Change review |
| `kubectl delete` | Request deletion | Cleanup, controlled replacement |

`kubectl replace --force` deletes and recreates resources; it is not an ordinary update and can cause disruption or new object UIDs.

### Dry-run modes

- `--dry-run=client`: build or validate locally without submitting a live mutation; cannot reproduce all server validation/admission.
- `--dry-run=server`: send a dry-run request to the API server, running supported validation and admission without persisting the object.
- Neither mode guarantees the later live request will succeed if cluster state changes.

## 6. Server-side apply and field management

Kubernetes tracks field ownership in `metadata.managedFields`. Server-side apply allows different field managers to own distinct fields. A conflict can occur when a manager tries to change a field owned by another manager.

```powershell
kubectl apply --server-side --field-manager=platform-lab -f .\deployment.yaml
kubectl get deployment web -o json | ConvertFrom-Json
```

Do not use `--force-conflicts` casually. It can take ownership away from another controller or GitOps reconciler. Review managed fields and change intent before resolving conflicts.

## 7. Troubleshooting command patterns

### Workload inspection

```powershell
kubectl get deployments,replicasets,pods -o wide
kubectl describe deployment web
kubectl describe pod <pod-name>
kubectl get events --sort-by=.lastTimestamp
```

### Logs

```powershell
kubectl logs deployment/web --tail=100 --timestamps
kubectl logs deployment/web --since=10m
kubectl logs pod/<pod-name> -c <container-name> --previous
```

`--previous` is useful for a previously terminated container instance, when one exists. `kubectl logs deployment/web` may choose one Pod; for a multi-replica incident, collect logs from all relevant Pods using a label selector and `--prefix` when supported.

### Interactive diagnostics

```powershell
kubectl exec -it <pod-name> -- sh
kubectl port-forward service/web 18013:80
kubectl debug pod/<pod-name> -it --image=busybox:1.36.1 --target=<container-name>
```

`exec` requires a shell or command available in the target container. Ephemeral debug containers depend on Kubernetes support, RBAC, Pod security policy/admission, and runtime compatibility. They can expose sensitive workload context; use approved diagnostic images and avoid production without authorization.

### Metrics

```powershell
kubectl top nodes
kubectl top pods -A
```

These require the metrics API (usually metrics-server). A `Metrics API not available` error does not necessarily indicate a broken cluster.

## 8. Lab prerequisites and safety

This lab uses **Windows PowerShell**, Docker Desktop, kind, and kubectl. All mutating operations target a disposable kind cluster.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch013 | Out-Null
Set-Location .\k8s-ch013
kind create cluster --name k8s-admin-ch013 --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch013 get nodes
```

**Expected:** `kind-k8s-admin-ch013` context and a Ready node.

**Stop condition:** Do not continue if the current context differs. Never use the lab's disruptive operations against a production, shared, EKS, AKS, or GKE cluster.

## 9. Lab A — Build an application and inspect objects

### Step A1 — Create the manifest

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch013
  labels:
    environment: lab
    team: platform
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch013
  labels:
    app: web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
        environment: lab
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
            limits:
              memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: ch013
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
'@ | Set-Content -Encoding ascii .\ch013-app.yaml

kubectl --context kind-k8s-admin-ch013 apply --dry-run=server -f .\ch013-app.yaml
kubectl --context kind-k8s-admin-ch013 apply -f .\ch013-app.yaml
kubectl --context kind-k8s-admin-ch013 -n ch013 rollout status deployment/web --timeout=180s
```

**Expected:** two Ready Pods and one ClusterIP Service.

### Step A2 — Advanced filtering

```powershell
kubectl --context kind-k8s-admin-ch013 -n ch013 get pods -o wide
kubectl --context kind-k8s-admin-ch013 -n ch013 get pods -l app=web -o custom-columns='NAME:.metadata.name,NODE:.spec.nodeName,IP:.status.podIP'
kubectl --context kind-k8s-admin-ch013 -n ch013 get pods --sort-by=.metadata.creationTimestamp
kubectl --context kind-k8s-admin-ch013 -n ch013 get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'
```

**Expected:** both Pods appear; output formatting changes but resource state does not.

## 10. Lab B — Diff, patch, and field ownership

### Step B1 — Preview a declarative change

```powershell
kubectl --context kind-k8s-admin-ch013 -n ch013 scale deployment/web --replicas=3
kubectl --context kind-k8s-admin-ch013 -n ch013 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch013 diff -f .\ch013-app.yaml
```

**Expected:** a diff may show the declared replica count of 2 versus live count of 3. `kubectl diff` normally exits with code 1 when differences exist.

### Step B2 — Restore declared state

```powershell
kubectl --context kind-k8s-admin-ch013 apply -f .\ch013-app.yaml
kubectl --context kind-k8s-admin-ch013 -n ch013 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch013 -n ch013 get deployment web
```

**Expected:** two desired/Ready replicas. If apply ownership prevents a change, inspect managed fields and resolve deliberately rather than forcing ownership.

### Step B3 — Patch metadata safely

```powershell
kubectl --context kind-k8s-admin-ch013 -n ch013 patch deployment web --type merge -p '{"metadata":{"annotations":{"example.com/change-ticket":"CH013"}}}'
kubectl --context kind-k8s-admin-ch013 -n ch013 get deployment web -o jsonpath='{.metadata.annotations.example\.com/change-ticket}'
```

**Expected:** annotation `CH013`. Changing Deployment metadata outside the Pod template does not trigger a rollout.

### Step B4 — Inspect field managers

```powershell
$deployment = kubectl --context kind-k8s-admin-ch013 -n ch013 get deployment web -o json | ConvertFrom-Json
$deployment.metadata.managedFields | Select-Object manager,operation,apiVersion,time
```

**Expected:** entries for the tools/controllers that have managed fields on the Deployment. Do not assume exact manager names across Kubernetes releases.

## 11. Lab C — Rollout, status, and rollback

### Step C1 — Trigger a new revision

```powershell
kubectl --context kind-k8s-admin-ch013 -n ch013 patch deployment web --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"example.com/revision":"2"}}}}}'
kubectl --context kind-k8s-admin-ch013 -n ch013 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch013 -n ch013 rollout history deployment/web
```

**Expected:** a new ReplicaSet revision and two Ready replicas.

### Step C2 — Roll back

```powershell
kubectl --context kind-k8s-admin-ch013 -n ch013 rollout undo deployment/web
kubectl --context kind-k8s-admin-ch013 -n ch013 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch013 -n ch013 get deployment web
```

**Expected:** prior Pod template restored. Inspect rollout history and Pod readiness to confirm recovery.

## 12. Lab D — Logs, exec, and port-forward

### Step D1 — Inspect logs and events

```powershell
kubectl --context kind-k8s-admin-ch013 -n ch013 logs deployment/web --tail=30 --timestamps
kubectl --context kind-k8s-admin-ch013 -n ch013 get events --sort-by=.lastTimestamp
$pod = kubectl --context kind-k8s-admin-ch013 -n ch013 get pods -l app=web -o jsonpath='{.items[0].metadata.name}'
kubectl --context kind-k8s-admin-ch013 -n ch013 describe pod $pod
```

**Expected:** container logs and descriptive Pod information. NGINX may emit few request logs until traffic is generated.

### Step D2 — Inspect a running container

```powershell
kubectl --context kind-k8s-admin-ch013 -n ch013 exec $pod -- sh -c 'hostname; cat /etc/resolv.conf'
```

**Expected:** hostname and DNS resolver configuration.

### Step D3 — Forward a Service port

In **PowerShell terminal 1**:

```powershell
kubectl --context kind-k8s-admin-ch013 -n ch013 port-forward service/web 18013:80
```

In **PowerShell terminal 2**:

```powershell
(Invoke-WebRequest http://localhost:18013 -UseBasicParsing).StatusCode
```

**Expected:** HTTP `200`. Stop the port-forward session with Ctrl+C.

## 13. Lab E — Wait, JSON, and PowerShell automation

### Step E1 — Wait for readiness

```powershell
kubectl --context kind-k8s-admin-ch013 -n ch013 wait --for=condition=Available deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch013 -n ch013 wait --for=condition=Ready pod -l app=web --timeout=180s
```

**Expected:** all selected Pods become Ready.

### Step E2 — Build a read-only inventory

```powershell
$inventory = kubectl --context kind-k8s-admin-ch013 -n ch013 get pods -o json | ConvertFrom-Json
$inventory.items | ForEach-Object {
    [pscustomobject]@{
        Namespace = $_.metadata.namespace
        Pod       = $_.metadata.name
        Node      = $_.spec.nodeName
        Phase     = $_.status.phase
        PodIP     = $_.status.podIP
    }
} | Format-Table -AutoSize
```

**Expected:** a concise Pod inventory. For production scripts, handle command failures and JSON parsing errors explicitly before reporting success.

### Step E3 — Inspect API permissions

```powershell
kubectl --context kind-k8s-admin-ch013 auth can-i get pods -n ch013
kubectl --context kind-k8s-admin-ch013 auth can-i patch deployments -n ch013
```

**Expected:** authorization results for the current local identity. Broad kind-admin permissions do not imply production users should have the same access.

## 14. Lab F — Safe disruption and recovery

### Step F1 — Delete one managed Pod

```powershell
$pod = kubectl --context kind-k8s-admin-ch013 -n ch013 get pods -l app=web -o jsonpath='{.items[0].metadata.name}'
kubectl --context kind-k8s-admin-ch013 -n ch013 delete pod $pod
kubectl --context kind-k8s-admin-ch013 -n ch013 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch013 -n ch013 get pods -o wide
```

**Expected:** ReplicaSet replaces the Pod and restores two Ready replicas. A Pod deletion can briefly reduce redundancy; do not generalize this as a safe production action.

### Step F2 — Inspect events after recovery

```powershell
kubectl --context kind-k8s-admin-ch013 -n ch013 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch013 -n ch013 describe deployment web
```

**Expected:** evidence of scheduling, container startup, and reconciliation.

## 15. Advanced command patterns and guardrails

### `kubectl debug`

Use only on approved test workloads. Ephemeral containers may require elevated privileges, access to process namespaces, or special security settings. A debug container can remain attached to the Pod until the Pod is deleted; it is not a harmless temporary shell in every environment.

### `kubectl drain`

Use for planned node maintenance after evaluating PodDisruptionBudgets, local data, DaemonSets, capacity, and topology constraints. Drain can leave workloads Pending if no replacement capacity exists. The dedicated drain exercise is covered in Chapter 010.

### `kubectl replace --force`

Avoid in routine production operations. It deletes and recreates objects, potentially causing downtime, new UIDs, and loss of unmanaged fields or attached state.

### `kubectl apply --prune`

Treat pruning as destructive. Ensure selectors, ownership, and allowlists are reviewed before removing resources that are absent from a manifest set.

### `kubectl get --raw`

Useful for API diagnostics, but raw endpoints can expose sensitive information depending on permissions. Record sanitized responses and avoid collecting Secrets or credentials.

## 16. Troubleshooting decision matrix

| Symptom | First command | Likely cause |
|---|---|---|
| Wrong cluster | `kubectl config current-context` | Context or kubeconfig precedence |
| `Forbidden` | `kubectl auth can-i` | RBAC or policy |
| `NotFound` | `kubectl get -A` | Wrong namespace/name |
| No matching Pods | `kubectl get pods --show-labels` | Selector mismatch |
| `ImagePullBackOff` | `kubectl describe pod` | Image, registry, auth, DNS |
| `CrashLoopBackOff` | `kubectl logs --previous` | Repeated container exit |
| Rollout stalled | `kubectl describe deployment` | Readiness, scheduling, capacity |
| No metrics | `kubectl get apiservices` | metrics-server/API unavailable |
| Port-forward fails | Pod/Service endpoints and local port | No ready backend, port conflict |
| Apply conflict | `metadata.managedFields` | Field ownership conflict |

### SRE evidence checklist

Capture context, namespace, timestamp, resource UID, image digest/tag, node, events, relevant logs, rollout history, managed fields, and the exact change applied. Redact tokens, kubeconfigs, Secret contents, and patient/customer data.

## 17. Cleanup and rollback

Verify the disposable cluster before deleting resources:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch013 get nodes
```

Then:

```powershell
kubectl --context kind-k8s-admin-ch013 delete namespace ch013
kind delete cluster --name k8s-admin-ch013
kind get clusters
Remove-Item .\ch013-app.yaml
```

**Warning:** Cluster deletion permanently removes local workloads and data. Never run the equivalent commands against a shared or production environment.

## 18. Acceptance checklist

- [ ] Created and verified disposable kind cluster and context.
- [ ] Deployed a two-replica application and Service.
- [ ] Used custom columns, JSONPath, label and field selectors.
- [ ] Previewed declarative drift using `kubectl diff`.
- [ ] Restored desired state and inspected managed fields.
- [ ] Patched metadata without changing Pod template.
- [ ] Triggered a rollout and completed a rollback.
- [ ] Inspected logs, events, and Pod details.
- [ ] Used exec and port-forward safely.
- [ ] Waited for readiness and generated a PowerShell inventory.
- [ ] Verified RBAC authorization with `auth can-i`.
- [ ] Observed ReplicaSet recovery after Pod deletion.
- [ ] Cleaned up disposable resources.

## 19. Knowledge check

1. Why should production scripts use explicit contexts and namespaces?
2. When would you choose JSONPath over custom columns or PowerShell JSON processing?
3. What is the difference between `apply`, `patch`, and `replace`?
4. What does server-side apply field ownership protect?
5. Why is `--force-conflicts` potentially dangerous?
6. Why can `kubectl diff` exit nonzero without an operational failure?
7. When does `kubectl logs --previous` help?
8. Why might `kubectl top` fail in an otherwise healthy cluster?
9. Why is `replace --force` different from a normal update?
10. What should be captured before restarting or deleting a production Pod?

## 20. Chapter status and next chapter

**Draft written; hands-on execution has not been independently verified.** Promote to **Lab Validated** after acceptance checks and to **Complete** after technical review.

**Next:** Chapter 014 — Resource Lifecycle, Finalizers and Garbage Collection.
