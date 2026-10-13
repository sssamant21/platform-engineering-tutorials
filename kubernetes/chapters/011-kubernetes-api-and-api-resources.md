# Chapter 011 — Kubernetes API and API Resources

**Track:** Kubernetes Administration · **Part:** 03 — Kubernetes API and Resource Administration · **Level:** Intermediate · **Status:** Draft — lab execution pending

## 1. Objectives and scope

After this chapter, you should be able to:

1. Explain the Kubernetes API server, resource endpoints, API groups, versions, kinds, and objects.
2. Distinguish namespaced from cluster-scoped resources, and built-in APIs from CustomResourceDefinitions (CRDs).
3. Discover supported resources and inspect server-provided schemas without relying on stale YAML examples.
4. Use kubectl discovery, explain, get, raw API requests, and dry-run validation.
5. Interpret common API responses and troubleshoot discovery, authentication, authorization, and schema failures.
6. Safely examine API resource lifecycle, including metadata, resourceVersion, generation, and status.
7. Produce an evidence-based API inventory for an SRE incident or platform change review.

**Lab environment:** Windows PowerShell, Docker Desktop, kind, and kubectl. All write operations target a disposable cluster named `k8s-admin-ch011`.

## 2. How the Kubernetes API works

```text
kubectl / application / controller
             |
        HTTPS + authn
             v
        kube-apiserver
             |
   authorization (RBAC)
             |
       admission chain
             |
      object validation
             |
         etcd storage
             |
     watch / list / get
             |
     controllers + kubelet
```

The API server is the front door for cluster management. Clients communicate over HTTPS; controllers watch API objects and reconcile actual state toward desired state. etcd stores cluster state. Kubernetes is not merely a CLI: kubectl is one client of a versioned API.

### API paths

| Resource family | Typical path | Examples |
|---|---|---|
| Core API group | `/api/v1` | Pods, Services, ConfigMaps, Namespaces |
| Named API group | `/apis/<group>/<version>` | Deployments under `apps/v1`, Jobs under `batch/v1` |
| API discovery | `/api`, `/apis` | Supported API groups and versions |
| OpenAPI schema | `/openapi/v3` | Server-published schema documents |

**API version is not the same as Kubernetes server version.** A cluster running a particular Kubernetes release can serve several resource API versions.

## 3. API resource identity

### GVK versus GVR

- **Group / Version / Kind (GVK):** identifies the type in YAML or JSON, such as `apps/v1, Deployment`.
- **Group / Version / Resource (GVR):** identifies a REST collection endpoint, such as `apps/v1, deployments`.
- **Object identity:** namespace (for namespaced resources) plus object name, within the resource type.
- **UID:** immutable identity for a specific object instance; a deleted/recreated object with the same name gets a new UID.

Example:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch011
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

The REST collection path is:

```text
/apis/apps/v1/namespaces/ch011/deployments
```

For a named object, append `/web`. For a core Pod, the collection is `/api/v1/namespaces/ch011/pods`.

### Scope

**Namespaced:** Pods, Deployments, ConfigMaps, Services, Secrets, Roles.

**Cluster-scoped:** Nodes, Namespaces, PersistentVolumes, ClusterRoles, CustomResourceDefinitions.

A namespace is itself cluster-scoped even though it groups namespaced objects. Use discovery rather than assuming a third-party custom resource's scope.

## 4. Object metadata and concurrency

| Field | Meaning | Operational implication |
|---|---|---|
| `metadata.name` | Name within resource scope | May be reused after deletion |
| `metadata.uid` | Identity of one object instance | Useful for incident correlation |
| `metadata.resourceVersion` | Opaque version used for optimistic concurrency and watches | Never treat as a numeric timestamp |
| `metadata.generation` | Desired-state generation for resources supporting it | Compare with observedGeneration where provided |
| `metadata.creationTimestamp` | Object creation time | Not an update timestamp |
| `metadata.labels` | Selector-friendly metadata | Affects matching and scheduling |
| `metadata.annotations` | Non-selector metadata | Avoid placing secrets here |
| `metadata.ownerReferences` | Ownership relationships | Affects garbage collection |
| `metadata.finalizers` | Deletion completion gates | Can leave objects terminating |

**spec** is usually desired state, while **status** is observed state. Not every Kubernetes object has both. Controllers often update the status subresource separately.

### API operations

| HTTP method | Typical operation | Safety |
|---|---|---|
| GET | Read object or collection | Read-only |
| POST | Create object | Mutating |
| PUT | Replace object | Mutating; risk of overwriting fields |
| PATCH | Modify selected fields or apply configuration | Mutating; review field ownership |
| DELETE | Delete object | Destructive |

A list/watch operation is foundational to controllers. A watch may need to restart when its resourceVersion becomes too old; clients must handle expiration and relist.

## 5. API discovery and schema validation

Use server discovery to confirm which resources and versions are supported:

```powershell
kubectl api-versions
kubectl api-resources
kubectl api-resources --namespaced=true
kubectl api-resources --namespaced=false
kubectl api-resources --api-group=apps
kubectl explain deployment
kubectl explain deployment.spec
kubectl explain deployment.spec.strategy
```

**Expected:** supported API groups and resource kinds; `kubectl explain` describes fields from the cluster's published schema.

Common pitfalls:
- Assuming `kind: Deployment` belongs to `v1` rather than `apps/v1`.
- Confusing the singular Kind `Pod` with plural REST resource `pods`.
- Using an API version removed from the target cluster.
- Treating a CRD schema as interchangeable with a built-in resource schema.
- Assuming `kubectl explain` documents every possible admission policy or webhook validation.

## 6. Lab prerequisites and safety gate

Run from **Windows PowerShell**:

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch011 | Out-Null
Set-Location .\k8s-ch011
kind create cluster --name k8s-admin-ch011 --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch011 get nodes
```

**Expected:** context `kind-k8s-admin-ch011` and one Ready control-plane node.

**Stop if the active context differs.** Every subsequent cluster operation explicitly specifies `--context kind-k8s-admin-ch011`. Never run the exercises against production.

## 7. Lab A — Explore the API server

### Step A1 — Confirm version and discovery

```powershell
kubectl --context kind-k8s-admin-ch011 version
kubectl --context kind-k8s-admin-ch011 get --raw /api
kubectl --context kind-k8s-admin-ch011 get --raw /apis
kubectl --context kind-k8s-admin-ch011 get --raw /api/v1
```

**Expected:** JSON describing supported versions, API groups, and core resources. Output can be long.

### Step A2 — Inspect a named group

```powershell
kubectl --context kind-k8s-admin-ch011 get --raw /apis/apps/v1
kubectl --context kind-k8s-admin-ch011 api-resources --api-group=apps -o wide
kubectl --context kind-k8s-admin-ch011 explain deployment.spec.replicas
```

**Expected:** `deployments`, `replicasets`, and related API resources; replicas schema description.

### Step A3 — Check schema availability

```powershell
kubectl --context kind-k8s-admin-ch011 get --raw /openapi/v3
```

**Expected:** OpenAPI v3 discovery document listing schema URLs. API-server support can vary by release. Do not assume one enormous schema document is returned directly.

## 8. Lab B — Create objects declaratively and inspect API identity

### Step B1 — Create a namespace and Deployment

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch011
  labels:
    tutorial: api-resources
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch011
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
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
'@ | Set-Content -Encoding ascii .\ch011-objects.yaml

kubectl --context kind-k8s-admin-ch011 apply --dry-run=server -f .\ch011-objects.yaml
kubectl --context kind-k8s-admin-ch011 apply -f .\ch011-objects.yaml
kubectl --context kind-k8s-admin-ch011 -n ch011 rollout status deployment/web --timeout=180s
```

**Expected:** namespace and Deployment created; two Ready replicas. The server-side dry run validates admission and schema but does not guarantee a later live operation will succeed under changing conditions.

### Step B2 — Inspect metadata, desired state, and observed state

```powershell
kubectl --context kind-k8s-admin-ch011 -n ch011 get deployment web -o yaml
kubectl --context kind-k8s-admin-ch011 -n ch011 get deployment web -o jsonpath='{.metadata.uid}'
kubectl --context kind-k8s-admin-ch011 -n ch011 get deployment web -o jsonpath='{.metadata.resourceVersion}'
kubectl --context kind-k8s-admin-ch011 -n ch011 get deployment web -o jsonpath='{.metadata.generation}'
kubectl --context kind-k8s-admin-ch011 -n ch011 get deployment web -o jsonpath='{.status.observedGeneration}'
```

**Expected:** UID, resourceVersion, generation, and observedGeneration. The controller should eventually observe the current generation; allow time for reconciliation.

### Step B3 — Read the REST endpoint directly

```powershell
kubectl --context kind-k8s-admin-ch011 get --raw /apis/apps/v1/namespaces/ch011/deployments/web
kubectl --context kind-k8s-admin-ch011 get --raw /api/v1/namespaces/ch011/pods
```

**Expected:** JSON representations of the Deployment and Pod collection.

## 9. Lab C — Distinguish scope and authorization

### Step C1 — Inspect namespaced resources

```powershell
kubectl --context kind-k8s-admin-ch011 api-resources --namespaced=true -o wide
kubectl --context kind-k8s-admin-ch011 -n ch011 get pods
kubectl --context kind-k8s-admin-ch011 -n ch011 get deployments.apps
```

### Step C2 — Inspect cluster-scoped resources

```powershell
kubectl --context kind-k8s-admin-ch011 api-resources --namespaced=false -o wide
kubectl --context kind-k8s-admin-ch011 get nodes
kubectl --context kind-k8s-admin-ch011 get namespaces
```

### Step C3 — Check permissions

```powershell
kubectl --context kind-k8s-admin-ch011 auth can-i list pods -n ch011
kubectl --context kind-k8s-admin-ch011 auth can-i get nodes
kubectl --context kind-k8s-admin-ch011 auth whoami
```

**Expected:** authorization responses for the lab identity. `auth whoami` depends on server support for SelfSubjectReview; if unavailable, record that limitation.

**Security note:** A local kind admin identity commonly has broad privileges. That does not reflect least-privilege production RBAC.

## 10. Lab D — Validation failures and safe API troubleshooting

### Step D1 — Intentionally use an invalid API version

```powershell
@'
apiVersion: apps/v99
kind: Deployment
metadata:
  name: invalid
  namespace: ch011
spec:
  replicas: 1
  selector:
    matchLabels:
      app: invalid
  template:
    metadata:
      labels:
        app: invalid
    spec:
      containers:
        - name: nginx
          image: nginx:stable
'@ | Set-Content -Encoding ascii .\invalid-api-version.yaml

kubectl --context kind-k8s-admin-ch011 apply --dry-run=server -f .\invalid-api-version.yaml
```

**Expected:** failure because the API server does not recognize `apps/v99` Deployment. Exact error text varies by kubectl and server version. No object should be created.

### Step D2 — Intentionally use an invalid schema field

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: invalid-field
  namespace: ch011
spec:
  replicas: 1
  totallyNotAValidField: true
  selector:
    matchLabels:
      app: invalid-field
  template:
    metadata:
      labels:
        app: invalid-field
    spec:
      containers:
        - name: nginx
          image: nginx:stable
'@ | Set-Content -Encoding ascii .\invalid-field.yaml

kubectl --context kind-k8s-admin-ch011 apply --dry-run=server --validate=strict -f .\invalid-field.yaml
```

**Expected:** strict validation rejects the unknown field. Some admission or validation behavior varies across server versions; record the observed error.

### Step D3 — Query a nonexistent resource

```powershell
kubectl --context kind-k8s-admin-ch011 -n ch011 get deployment does-not-exist
```

**Expected:** `NotFound`. This is not an authentication or API availability failure.

## 11. Lab E — Inspect reconciliation and version changes

### Step E1 — Scale the Deployment

```powershell
kubectl --context kind-k8s-admin-ch011 -n ch011 scale deployment/web --replicas=3
kubectl --context kind-k8s-admin-ch011 -n ch011 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch011 -n ch011 get deployment web -o jsonpath='{.metadata.generation}'
kubectl --context kind-k8s-admin-ch011 -n ch011 get deployment web -o jsonpath='{.status.observedGeneration}'
kubectl --context kind-k8s-admin-ch011 -n ch011 get deployment web -o jsonpath='{.status.readyReplicas}'
```

**Expected:** three Ready replicas; generation and observedGeneration converge. A spec change increments generation for the Deployment; resourceVersion changes on writes, including status updates.

### Step E2 — Understand declarative drift

The original manifest still requests two replicas. Preview the effect of reapplying it:

```powershell
kubectl --context kind-k8s-admin-ch011 diff -f .\ch011-objects.yaml
```

**Expected:** a difference may be reported for `spec.replicas` and managed fields, depending on field ownership and apply history. `kubectl diff` commonly returns exit code 1 when differences exist; this is not necessarily an execution failure.

Restore declared state:

```powershell
kubectl --context kind-k8s-admin-ch011 apply -f .\ch011-objects.yaml
kubectl --context kind-k8s-admin-ch011 -n ch011 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch011 -n ch011 get deployment web
```

**Expected:** desired replicas return to two. Be aware that field ownership can affect the exact apply behavior; inspect the Deployment if the value does not revert.

## 12. CRDs, API aggregation, and API evolution

### Built-in APIs

Kubernetes ships built-in resources such as Pods, Deployments, and Services. The API server handles their schema and storage according to the Kubernetes release.

### CustomResourceDefinitions

A CRD extends the Kubernetes API with new resource kinds. Once installed, custom resources can be discovered with `kubectl api-resources` and described with `kubectl explain` when schemas are available. A CRD alone does not guarantee a controller is reconciling its resources.

### Aggregated APIs

API aggregation allows additional API servers to serve registered API groups. The metrics API used by `kubectl top` is a familiar example when metrics-server is installed.

### Deprecation and removal

Before upgrading a cluster, inventory APIs actually in use, inspect release-specific deprecation notices, and migrate manifests/controllers to supported API versions. A deprecated API may continue to work temporarily; a removed API will fail discovery or requests after an upgrade.

## 13. Troubleshooting decision matrix

| Symptom | Meaning | Investigation |
|---|---|---|
| `the server doesn't have a resource type` | Unknown GVR or discovery issue | `api-resources`, API groups, CRD presence |
| `no matches for kind` | GVK not recognized | `apiVersion`, Kind, CRD installation |
| `Unauthorized` / 401 | Authentication failed | Credential/exec plugin/session |
| `Forbidden` / 403 | Authenticated but not authorized | RBAC, `auth can-i`, admission distinctions |
| `NotFound` / 404 | Resource or object missing | Namespace, name, GVR |
| `Conflict` / 409 | Concurrent update or field conflict | resourceVersion, field managers, retry safely |
| `Unprocessable Entity` / 422 | Schema or semantic validation failure | Object spec, API version |
| Timeout / connection refused | API endpoint unreachable | Context, DNS, network, API server health |
| Discovery failure | API group unavailable or stale cache | `api-resources`, aggregated APIs, APIService health |

### SRE triage commands

```powershell
kubectl --context kind-k8s-admin-ch011 config view --minify
kubectl --context kind-k8s-admin-ch011 cluster-info
kubectl --context kind-k8s-admin-ch011 api-resources
kubectl --context kind-k8s-admin-ch011 get apiservices
kubectl --context kind-k8s-admin-ch011 get crds
kubectl --context kind-k8s-admin-ch011 get events -A --sort-by=.lastTimestamp
```

**Do not paste raw kubeconfig or bearer tokens into incident records.** Capture timestamps, HTTP status, group/version/resource, namespace, request intent, and sanitized response.

## 14. Production administration guardrails

- Use explicit `--context` and `--namespace` for changes.
- Prefer declarative manifests with schema validation and Git review.
- Use least-privilege identities; audit mutating requests.
- Avoid blind `kubectl replace --force` or finalizer removal.
- Treat `resourceVersion` as an opaque concurrency token.
- Plan for API removals and CRD conversion webhook dependencies during upgrades.
- Confirm controllers are healthy before assuming a successful API write achieved the desired runtime state.
- Never store credentials in object annotations or committed kubeconfig files.

## 15. Cleanup

Verify the disposable cluster:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch011 get nodes
```

Then clean up only the training environment:

```powershell
kubectl --context kind-k8s-admin-ch011 delete namespace ch011
kind delete cluster --name k8s-admin-ch011
kind get clusters
Remove-Item .\ch011-objects.yaml, .\invalid-api-version.yaml, .\invalid-field.yaml
```

**Warning:** Deleting a kind cluster permanently removes its local workloads and cluster data. Never use these destructive commands against an unrelated context.

## 16. Acceptance checklist

- [ ] Created and verified disposable kind cluster.
- [ ] Discovered core and named API groups.
- [ ] Distinguished GVK, GVR, Kind, and resource scope.
- [ ] Used `kubectl explain` and server API discovery.
- [ ] Created namespaced and cluster-scoped resources appropriately.
- [ ] Inspected metadata UID, resourceVersion, generation, and status.
- [ ] Queried REST endpoints with `kubectl get --raw`.
- [ ] Reproduced invalid API version and strict schema failures.
- [ ] Checked authorization using `kubectl auth can-i`.
- [ ] Observed desired-state reconciliation after scaling.
- [ ] Documented production API troubleshooting and upgrade risks.
- [ ] Cleaned up disposable resources.

## 17. Knowledge check

1. What is the difference between GVK and GVR?
2. Why is `apiVersion: apps/v1` used for Deployments?
3. Why does `kubectl api-resources` matter during a Kubernetes upgrade?
4. What is the difference between `metadata.uid` and `metadata.resourceVersion`?
5. How do generation and observedGeneration help during troubleshooting?
6. Why does a successful API write not guarantee a healthy workload?
7. How would you distinguish 401, 403, 404, 409, and 422 responses?
8. Why does installing a CRD not necessarily create a functioning operator?

## 18. Chapter status and next chapter

**Draft written; labs have not been independently executed or validated.** Mark **Lab Validated** after completing acceptance tests and **Complete** after technical review.

**Next:** Chapter 012 — Namespaces, Labels and Annotations.
