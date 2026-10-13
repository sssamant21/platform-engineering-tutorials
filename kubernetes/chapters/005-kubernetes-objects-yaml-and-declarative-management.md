# Chapter 005 — Kubernetes Objects, YAML and Declarative Management

**Track:** Kubernetes Administration · **Part:** 01 — Kubernetes Fundamentals · **Level:** Beginner–Intermediate · **Status:** Draft — hands-on lab not independently executed

## 1. Learning objectives

After completing this chapter, you should be able to:
1. Identify Kubernetes object identity, metadata, desired state, observed status, and API versions.
2. Read and write valid multi-document Kubernetes YAML.
3. Distinguish imperative commands from declarative configuration.
4. Apply, inspect, diff, update, and safely delete namespaced resources.
5. Explain reconciliation, labels/selectors, annotations, owner references, finalizers, and field ownership.
6. Use client-side validation, server-side dry runs, and server-side apply responsibly.
7. Diagnose common YAML, API validation, and resource ownership problems.

## 2. Kubernetes API object model

A Kubernetes object is a durable API resource representing desired state or an observed cluster concept. Most workload objects have:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch005
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
    spec:
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - containerPort: 80
```

| Field | Meaning | Operational note |
|---|---|---|
| `apiVersion` | API group and version | E.g. `v1`, `apps/v1`, `batch/v1` |
| `kind` | Resource type | Deployment, Service, ConfigMap, Pod |
| `metadata.name` | Name within resource scope | Namespaced resources use namespace + name |
| `metadata.namespace` | Target namespace | Omit for cluster-scoped resources |
| `metadata.labels` | Selectable key/value metadata | Used by selectors and policy |
| `metadata.annotations` | Non-identifying metadata | Useful for tooling and descriptions |
| `spec` | Desired configuration | Controllers reconcile toward this |
| `status` | Reported observed state | Usually set by controllers/kubelet, not Git |

Some resource types do not have `spec` or `status`. Do not assume every object has identical schema.

### 2.1 Identity, scope, and discovery

```powershell
kubectl api-resources
kubectl api-resources --namespaced=true
kubectl api-resources --namespaced=false
kubectl explain deployment
kubectl explain deployment.spec.template.spec.containers
```

A Namespace is cluster-scoped; a Deployment is namespaced. API resources and supported fields vary by Kubernetes version and installed CRDs.

### 2.2 Desired state versus observed state

- `spec.replicas: 3` is a desired replica count.
- `status.readyReplicas: 2` indicates observed readiness at a point in time.
- The Deployment and ReplicaSet controllers work to reconcile discrepancies.
- A healthy API request does not imply the application is ready; inspect status, events, and endpoints.

### 2.3 Labels, annotations, selectors

Labels support grouping and selecting resources. Service selectors and Deployment selectors must match Pod labels. Annotations hold auxiliary metadata and are not intended for selecting Pods.

**Important:** A Deployment's `spec.selector` is generally immutable after creation; changing it is not a routine rolling update. Plan label contracts carefully.

### 2.4 Owner references and finalizers

Owner references help Kubernetes garbage collection manage dependent objects. Finalizers delay deletion until a controller performs cleanup. A resource stuck in `Terminating` can indicate a failed cleanup controller; removing finalizers manually can orphan infrastructure or data. Never strip production finalizers as a first troubleshooting step.

## 3. YAML fundamentals

YAML is indentation-sensitive and uses mappings, sequences, and scalar values.

```yaml
metadata:
  labels:
    app: web
    tier: frontend
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: nginx
          image: nginx:stable
```

- Use spaces, not tabs, for indentation.
- Use `-` to introduce sequence items.
- Quote ambiguous scalar strings (for example, values that might be interpreted as booleans or numbers).
- Use `---` to separate multiple resources in one file.
- Store secrets in an approved secret-management system; Kubernetes Secret YAML using base64 is **not encryption**.
- Keep environment-specific names and values explicit and reviewed.

### API schema validation

```powershell
kubectl explain deployment.spec
kubectl apply --dry-run=client -f .\ch005-resources.yaml
kubectl apply --dry-run=server -f .\ch005-resources.yaml
```

Client-side dry-run is a preliminary check, not a substitute for server-side admission validation. Server-side dry-run contacts the API server and may be rejected if admission webhooks do not support dry-run.

## 4. Imperative versus declarative workflows

| Workflow | Example | Best use |
|---|---|---|
| Imperative | `kubectl create namespace ch005` | Quick disposable labs, one-off tasks |
| Declarative | `kubectl apply -f file.yaml` | Repeatable desired state |
| Preview | `kubectl diff -f file.yaml` | Review changes before apply |
| Server-side apply | `kubectl apply --server-side -f file.yaml` | Explicit field ownership / collaborative controllers |
| GitOps | Reconciler applies approved Git state | Auditable continuous delivery |

### Field management and apply conflicts

Client-side apply traditionally uses the `kubectl.kubernetes.io/last-applied-configuration` annotation for change calculations. Server-side apply tracks field managers in `metadata.managedFields`. When two managers attempt to own conflicting fields, the API may return a conflict.

**Do not automatically use `--force-conflicts` in production.** Determine which controller or team should own the field, and coordinate changes rather than overriding ownership blindly.

## 5. Prerequisites and safety

This lab targets **Windows PowerShell**, Docker Desktop, `kind`, and `kubectl`. Use a disposable local cluster with enough available CPU/memory. Commands intentionally create, modify, and delete resources; do not run them against production.

```powershell
docker version
kind version
kubectl version --client
```

Create a local working directory:

```powershell
New-Item -ItemType Directory -Force .\k8s-ch005 | Out-Null
Set-Location .\k8s-ch005
```

## 6. Lab A — Create a cluster and declarative resources

### Step A1 — Create and verify the lab cluster

```powershell
kind create cluster --name k8s-admin-ch005 --wait 120s
kubectl config current-context
kubectl get nodes
```

**Expected:** context `kind-k8s-admin-ch005` and node `Ready`. **Stop unless the context matches exactly.**

### Step A2 — Write the multi-document YAML

Create `ch005-resources.yaml`:

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch005
  labels:
    purpose: training
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-settings
  namespace: ch005
  labels:
    app: web
data:
  MESSAGE: "hello-kubernetes"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch005
  labels:
    app: web
  annotations:
    training.example.com/owner: "platform-team"
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
        tier: frontend
    spec:
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - name: http
              containerPort: 80
          env:
            - name: MESSAGE
              valueFrom:
                configMapKeyRef:
                  name: web-settings
                  key: MESSAGE
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
            limits:
              cpu: 250m
              memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: ch005
  labels:
    app: web
spec:
  selector:
    app: web
  ports:
    - name: http
      port: 80
      targetPort: http
  type: ClusterIP
'@ | Set-Content -Encoding ascii .\ch005-resources.yaml
```

**Why these objects?** Namespace isolates the exercise; ConfigMap provides a value; Deployment manages replicated Pods; Service provides a stable in-cluster endpoint. The NGINX image does not automatically render the `MESSAGE` environment variable, so do not expect it on the HTTP page.

### Step A3 — Validate and apply

```powershell
kubectl apply --dry-run=client -f .\ch005-resources.yaml
kubectl apply --dry-run=server -f .\ch005-resources.yaml
kubectl apply -f .\ch005-resources.yaml
kubectl -n ch005 rollout status deployment/web --timeout=180s
kubectl -n ch005 get deployment,replicaset,pods,service,configmap
```

**Expected:** namespace and resources created, Deployment `2/2` ready, Service and ConfigMap visible. Exact Pod names differ between runs.

### Step A4 — Inspect labels, selectors and status

```powershell
kubectl -n ch005 get pods --show-labels
kubectl -n ch005 get pods -l app=web
kubectl -n ch005 get deployment web -o jsonpath='{.spec.replicas}'
kubectl -n ch005 get deployment web -o jsonpath='{.status.readyReplicas}'
kubectl -n ch005 describe service web
kubectl -n ch005 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** two Pods with `app=web`, desired and ready replica counts of 2, and EndpointSlices associated with the Service. Endpoint readiness is a better signal of routing eligibility than Pod phase alone.

### Step A5 — Verify ConfigMap injection

```powershell
$pod = kubectl -n ch005 get pods -l app=web -o jsonpath='{.items[0].metadata.name}'
kubectl -n ch005 exec $pod -- printenv MESSAGE
```

**Expected:** `hello-kubernetes`. Environment variables sourced from a ConfigMap are resolved when the container starts; updating the ConfigMap alone does **not** dynamically change those existing process environment variables.

## 7. Lab B — Declarative update, diff, reconciliation

### Step B1 — Inspect and modify desired state

Preview the current Deployment:

```powershell
kubectl -n ch005 get deployment web -o yaml
```

Update the YAML file's replica count from 2 to 3:

```powershell
(Get-Content .\ch005-resources.yaml -Raw) -replace 'replicas: 2', 'replicas: 3' | Set-Content -Encoding ascii .\ch005-resources.yaml
```

Review before applying:

```powershell
kubectl diff -f .\ch005-resources.yaml
```

**Expected:** diff shows `replicas: 2` changing to `replicas: 3`. `kubectl diff` normally returns exit code **1** when differences exist; that is not necessarily an error.

Apply:

```powershell
kubectl apply -f .\ch005-resources.yaml
kubectl -n ch005 rollout status deployment/web --timeout=180s
kubectl -n ch005 get deployment web
```

**Expected:** `3/3` ready.

### Step B2 — Demonstrate reconciliation

```powershell
$pod = kubectl -n ch005 get pods -l app=web -o jsonpath='{.items[0].metadata.name}'
kubectl -n ch005 delete pod $pod
kubectl -n ch005 get pods -l app=web -w
```

**Expected:** the ReplicaSet creates a replacement Pod to restore three replicas. Press Ctrl+C to stop watching.

### Step B3 — Inspect owner references and managed fields

```powershell
kubectl -n ch005 get replicasets
kubectl -n ch005 get pods -l app=web -o custom-columns='NAME:.metadata.name,OWNER:.metadata.ownerReferences[0].name,NODE:.spec.nodeName'
kubectl -n ch005 get deployment web -o jsonpath='{range .metadata.managedFields[*]}{.manager}{"  "}{.operation}{"\n"}{end}'
```

**Expected:** Pods are owned by a ReplicaSet and managed fields identify API field managers. Exact managers and field sets vary by version and apply mode.

## 8. Lab C — Server-side apply in an isolated resource

To avoid conflicting with the client-side-managed Deployment, create a separate ConfigMap managed through server-side apply.

```powershell
@'
apiVersion: v1
kind: ConfigMap
metadata:
  name: server-side-demo
  namespace: ch005
data:
  mode: "declarative"
  owner: "platform-team"
'@ | Set-Content -Encoding ascii .\ch005-server-side.yaml

kubectl apply --server-side --field-manager=chapter005-lab -f .\ch005-server-side.yaml
kubectl -n ch005 get configmap server-side-demo -o yaml
kubectl -n ch005 get configmap server-side-demo -o jsonpath='{range .metadata.managedFields[*]}{.manager}{"  "}{.operation}{"\n"}{end}'
```

**Expected:** ConfigMap created; `chapter005-lab` appears among the managed-field managers with operation `Apply`.

Repeat the same apply:

```powershell
kubectl apply --server-side --field-manager=chapter005-lab -f .\ch005-server-side.yaml
```

**Expected:** no unintended change. Declarative apply is designed to be repeatable, though external controllers and defaulting can affect observed state.

## 9. Lab D — Diagnose invalid YAML and schema errors

Create an intentionally invalid Deployment **without applying it**:

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: invalid-demo
  namespace: ch005
spec:
  replicas: "three"
  selector:
    matchLabels:
      app: invalid-demo
  template:
    metadata:
      labels:
        app: invalid-demo
    spec:
      containers:
        - name: nginx
          image: nginx:stable
'@ | Set-Content -Encoding ascii .\ch005-invalid.yaml

kubectl apply --dry-run=server -f .\ch005-invalid.yaml
```

**Expected:** validation or decoding error because `spec.replicas` requires an integer, not `"three"`. The exact error text varies by Kubernetes version.

Fix the file and validate again:

```powershell
(Get-Content .\ch005-invalid.yaml -Raw) -replace 'replicas: "three"', 'replicas: 1' | Set-Content -Encoding ascii .\ch005-invalid.yaml
kubectl apply --dry-run=server -f .\ch005-invalid.yaml
```

**Expected:** server-side dry-run succeeds. No `invalid-demo` Deployment is persisted because both commands used dry-run.

## 10. Troubleshooting and production runbook

| Symptom | Evidence | Safe next step |
|---|---|---|
| `no matches for kind` | API version / CRD availability | `kubectl api-resources`, check CRD installation |
| Unknown field or invalid type | Server-side validation output | `kubectl explain`, correct schema |
| Deployment has zero Ready Pods | Events, Pod describe, container logs | Diagnose scheduling, pulls, probes, limits |
| Service has no endpoints | Service selector, Pod labels/readiness | Correct selector/labels and verify readiness |
| Apply conflict | Managed fields and error details | Resolve field ownership with responsible controller |
| Changes overwritten by GitOps | Reconciler status and source revision | Change Git source of truth, not only live object |
| Resource stuck Terminating | Finalizers and controller logs | Diagnose cleanup controller; avoid blindly removing finalizers |
| ConfigMap update not reflected | Pod env/volume consumption method | Restart Pods if environment variables must refresh |

### Production-safe change sequence

1. Verify cluster, context, namespace, and intended target.
2. Review source-controlled manifest and ownership.
3. Run schema checks and `kubectl diff` against the intended environment.
4. Obtain approvals for risky changes and ensure rollback artifacts exist.
5. Apply through the designated controller/GitOps process.
6. Validate rollout, readiness, endpoints, and application SLIs.
7. Record changes and rollback if acceptance criteria fail.

**Important:** `kubectl apply` and `kubectl delete` can cause real outages if run against the wrong cluster. `kubectl delete -f` only deletes objects defined in the file, but deleting a Namespace cascades to its namespaced resources.

## 11. Cleanup and rollback

First verify:

```powershell
kubectl config current-context
```

Proceed **only** when output is `kind-k8s-admin-ch005`:

```powershell
kubectl delete namespace ch005
kind delete cluster --name k8s-admin-ch005
kind get clusters
```

Optionally remove generated local YAML files:

```powershell
Remove-Item .\ch005-resources.yaml, .\ch005-server-side.yaml, .\ch005-invalid.yaml
```

**Warning:** `kind delete cluster` permanently removes the local cluster and its data. Do not delete clusters that you intend to preserve.

## 12. Acceptance checklist

- [ ] Tooling verified and kind context checked.
- [ ] Namespace, ConfigMap, Deployment and Service defined declaratively.
- [ ] Client and server dry-runs succeeded.
- [ ] Deployment reached 2/2 Ready.
- [ ] Labels, selectors, status, EndpointSlices and ConfigMap env inspected.
- [ ] Diff reviewed and Deployment scaled to 3/3.
- [ ] Deleted Pod was replaced by reconciliation.
- [ ] Owner references and managed fields inspected.
- [ ] Server-side apply completed on isolated ConfigMap.
- [ ] Invalid manifest rejected by server-side dry-run and corrected.
- [ ] All lab resources cleaned up.

## 13. Knowledge check

1. What is the difference between `spec` and `status`?
2. Why are label selectors essential to Deployments and Services?
3. How do annotations differ from labels?
4. Why is `kubectl diff` useful before `kubectl apply`?
5. What problem does server-side apply field ownership solve?
6. Why can a resource remain in `Terminating`?
7. Why does a ConfigMap environment variable not update automatically in an existing process?
8. What are the dangers of deleting a Namespace?
9. Why should GitOps-managed objects be changed through Git?
10. How can you confirm a YAML file is valid without persisting resources?

## 14. Part 01 completion checkpoint

Part 01 contains five foundational chapters:

| Chapter | Title | Writing status |
|---|---|---|
| 001 | What Is Kubernetes? | Draft |
| 002 | Containers, Images and Container Runtimes | Draft |
| 003 | Kubernetes Architecture and Components | Draft |
| 004 | Control Plane, Worker Nodes and etcd | Draft |
| 005 | Kubernetes Objects, YAML and Declarative Management | Draft |

**Writing milestone:** Part 01's five chapter drafts are written. **Lab validation and editorial review remain outstanding**, so Part 01 is not yet marked fully complete.

**Next:** Chapter 006 — kubectl Installation and kubeconfig.
