# Chapter 012 — Namespaces, Labels and Annotations

**Track:** Kubernetes Administration · **Part:** 03 — Kubernetes API and Resource Administration · **Level:** Intermediate · **Status:** Draft — hands-on validation pending

## 1. Learning objectives

After completing this chapter, you should be able to:

1. Explain namespace scope, isolation boundaries, and namespace lifecycle.
2. Design and apply consistent labels for ownership, environment, application, and cost allocation.
3. Use equality-based and set-based label selectors to find resources and drive controller behavior.
4. Distinguish labels from annotations and avoid storing secrets in either.
5. Understand namespace-level governance using ResourceQuota, LimitRange, RBAC, and NetworkPolicy.
6. Diagnose selector mismatches, quota rejections, and namespace deletion problems.
7. Run a Windows PowerShell lab with safe validation, cleanup, and an operational acceptance checklist.

## 2. Concepts and architecture

```text
Kubernetes cluster
  |
  +-- Cluster-scoped resources
  |     Nodes, Namespaces, PersistentVolumes, ClusterRoles
  |
  +-- Namespace: ch012-dev
  |     Deployment, ReplicaSet, Pods, Services, ConfigMaps
  |     ResourceQuota, LimitRange, Role, RoleBinding
  |
  +-- Namespace: ch012-test
        Deployment, Pods, Services
```

Namespaces group namespaced API objects and provide an important **administrative scope**, but they do not automatically create hard security, network, compute, or storage isolation. Effective multi-tenancy also requires appropriate RBAC, admission controls, quotas, and network policies.

The `default`, `kube-system`, `kube-public`, and `kube-node-lease` namespaces commonly exist in Kubernetes clusters. Do not use system namespaces for training workloads.

## 3. Namespace fundamentals

### 3.1 Namespaced versus cluster-scoped objects

| Resource | Scope | Example |
|---|---|---|
| Pod, Deployment, Service | Namespaced | `ch012-dev/web` |
| ConfigMap, Secret | Namespaced | `ch012-dev/app-config` |
| Role, RoleBinding | Namespaced | `ch012-dev/developer` |
| ResourceQuota, LimitRange | Namespaced | `ch012-dev/compute-budget` |
| NetworkPolicy | Namespaced | `ch012-dev/deny-by-default` |
| Namespace, Node | Cluster | `ch012-dev`, `worker-1` |
| PersistentVolume | Cluster | `pv-example` |
| ClusterRole, ClusterRoleBinding | Cluster | `view` |

Use `kubectl api-resources --namespaced=true` and `--namespaced=false` for authoritative discovery on your target cluster.

### 3.2 Namespace lifecycle

A Namespace typically transitions from `Active` to `Terminating` when deleted. Namespace deletion requests deletion of namespaced content. Finalizers, unavailable API discovery, or controllers that cannot complete cleanup may leave a namespace stuck in `Terminating`.

**Never force-remove namespace finalizers as a routine fix.** Doing so can orphan resources or bypass cleanup guarantees. Investigate remaining resources, APIService health, and the responsible finalizer controller first.

### 3.3 Namespace does not imply network isolation

Pods in different namespaces can generally communicate unless the networking implementation and NetworkPolicy (or other controls) restrict traffic. DNS uses namespace-aware names, but DNS naming is not an authorization boundary.

## 4. Labels and selectors

Labels are indexed, selector-friendly key/value metadata used for grouping, routing, scheduling, policy, and automation.

Example:

```yaml
metadata:
  labels:
    app.kubernetes.io/name: web
    app.kubernetes.io/instance: web-dev
    app.kubernetes.io/part-of: training-platform
    app.kubernetes.io/managed-by: kubectl
    environment: dev
    team: platform
    cost-center: sandbox
```

### 4.1 Recommended label taxonomy

| Key | Purpose | Sample |
|---|---|---|
| `app.kubernetes.io/name` | Application identity | `web` |
| `app.kubernetes.io/instance` | Installation identity | `web-dev` |
| `app.kubernetes.io/component` | Logical component | `frontend` |
| `app.kubernetes.io/part-of` | Parent system | `training-platform` |
| `environment` | Environment classification | `dev` |
| `team` | Operational ownership | `platform` |
| `cost-center` | Allocation/reporting | `sandbox` |

Define allowed values and ownership centrally. Avoid using labels for unbounded, high-cardinality values such as unique request IDs; those are usually better suited to logs/traces, and sometimes annotations.

### 4.2 Equality and set-based selectors

```powershell
kubectl get pods -l environment=dev
kubectl get pods -l 'environment!=prod'
kubectl get pods -l 'environment in (dev,test)'
kubectl get pods -l 'team=platform,environment=dev'
kubectl get pods -l 'app.kubernetes.io/name'
kubectl get pods -l '!deprecated'
```

Selectors are ANDed when combined with commas. There is no general OR operator across unrelated keys in a single Kubernetes label selector. PowerShell quoting is important for parentheses, spaces, and exclamation marks.

### 4.3 Selectors are operational contracts

A Service routes traffic to Pods matching its selector. A Deployment's `spec.selector` identifies the Pods it manages and is immutable for `apps/v1` Deployments after creation. A label mismatch can produce zero Service endpoints even when Pods are Ready.

Do not casually relabel Pods managed by a Deployment; the controller can replace them, and Service routing can change immediately.

## 5. Annotations

Annotations hold non-selector metadata, such as deployment provenance, documentation links, policy hints, or controller configuration.

```yaml
metadata:
  annotations:
    example.com/change-ticket: "CHG-2026-010"
    example.com/owner-contact: "platform-oncall"
    example.com/runbook: "https://example.invalid/runbooks/web"
```

Annotations may be read by admission webhooks, ingress controllers, operators, or other automation. They are **not always inert comments**. Never copy untrusted annotations into a production manifest without understanding their consumers.

**Security:** Neither labels nor annotations are encrypted secret stores. They are visible to identities allowed to read the object. Do not put credentials, tokens, patient information, or confidential customer data in either.

## 6. Namespace governance: quotas, defaults, and access

### ResourceQuota

Limits aggregate namespace resource usage, such as requests/limits and counts of objects. It does not replace physical cluster capacity planning.

### LimitRange

Defines defaults and per-object minimum/maximum resource constraints for supported resources. Defaults may be applied during admission; changing a LimitRange does not retroactively rewrite existing Pods.

### RBAC

Roles and RoleBindings constrain actions within a namespace. A ClusterRole can also be referenced by a namespaced RoleBinding to grant permissions only in that namespace.

### NetworkPolicy

NetworkPolicies select Pods within a namespace and express ingress/egress restrictions. Enforcement depends on the installed network plugin. A kind cluster using a default CNI may not enforce NetworkPolicy; do not treat creating one as proof of traffic isolation.

## 7. Lab prerequisites and safety

Run all labs in **Windows PowerShell** with Docker Desktop, kind, and kubectl:

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch012 | Out-Null
Set-Location .\k8s-ch012
kind create cluster --name k8s-admin-ch012 --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch012 get nodes
```

**Expected:** context `kind-k8s-admin-ch012` and a Ready kind node.

**Safety gate:** Stop if the context is not the disposable kind cluster. Every mutating command below uses `--context kind-k8s-admin-ch012`. Never execute these exercises against production or shared namespaces.

## 8. Lab A — Create and inspect namespaces

### Step A1 — Create namespaces declaratively

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch012-dev
  labels:
    environment: dev
    team: platform
    cost-center: sandbox
  annotations:
    example.com/purpose: "Kubernetes administration lab"
---
apiVersion: v1
kind: Namespace
metadata:
  name: ch012-test
  labels:
    environment: test
    team: platform
    cost-center: sandbox
'@ | Set-Content -Encoding ascii .\namespaces.yaml

kubectl --context kind-k8s-admin-ch012 apply --dry-run=server -f .\namespaces.yaml
kubectl --context kind-k8s-admin-ch012 apply -f .\namespaces.yaml
kubectl --context kind-k8s-admin-ch012 get namespaces --show-labels
kubectl --context kind-k8s-admin-ch012 get namespace ch012-dev -o yaml
```

**Expected:** both namespaces Active, with the expected labels and annotation.

### Step A2 — Inspect scope

```powershell
kubectl --context kind-k8s-admin-ch012 api-resources --namespaced=true
kubectl --context kind-k8s-admin-ch012 api-resources --namespaced=false
kubectl --context kind-k8s-admin-ch012 get pods -n ch012-dev
```

**Expected:** namespaced and cluster-scoped resource listings. Initially, `ch012-dev` has no Pods.

## 9. Lab B — Deploy labeled applications

### Step B1 — Create two Deployments and one Service

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch012-dev
  labels:
    app.kubernetes.io/name: web
    environment: dev
    team: platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: web
      environment: dev
  template:
    metadata:
      labels:
        app.kubernetes.io/name: web
        environment: dev
        team: platform
    spec:
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - containerPort: 80
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
  namespace: ch012-dev
spec:
  selector:
    app.kubernetes.io/name: web
    environment: dev
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch012-test
  labels:
    app.kubernetes.io/name: web
    environment: test
    team: platform
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: web
      environment: test
  template:
    metadata:
      labels:
        app.kubernetes.io/name: web
        environment: test
        team: platform
    spec:
      containers:
        - name: nginx
          image: nginx:stable
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
'@ | Set-Content -Encoding ascii .\workloads.yaml

kubectl --context kind-k8s-admin-ch012 apply -f .\workloads.yaml
kubectl --context kind-k8s-admin-ch012 -n ch012-dev rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch012 -n ch012-test rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch012 get pods -A -l app.kubernetes.io/name=web --show-labels
```

**Expected:** two Ready dev Pods and one Ready test Pod; identical Deployment names are valid because they belong to different namespaces.

### Step B2 — Exercise selectors

```powershell
kubectl --context kind-k8s-admin-ch012 get pods -A -l 'environment in (dev,test)'
kubectl --context kind-k8s-admin-ch012 get pods -A -l 'team=platform,environment=dev'
kubectl --context kind-k8s-admin-ch012 get namespaces -l 'cost-center=sandbox'
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get pods -l 'environment!=prod'
```

**Expected:** queries return resources matching the requested labels.

## 10. Lab C — Service selectors and endpoint troubleshooting

### Step C1 — Verify healthy endpoints

```powershell
kubectl --context kind-k8s-admin-ch012 -n ch012-dev describe service web
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** the Service has two ready Pod endpoints.

### Step C2 — Intentionally break the Service selector

```powershell
kubectl --context kind-k8s-admin-ch012 -n ch012-dev patch service web --type merge -p '{"spec":{"selector":{"app.kubernetes.io/name":"web","environment":"prod"}}}'
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get service web -o yaml
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** the Service has no ready application endpoints after reconciliation. EndpointSlice objects may disappear or contain no ready addresses; do not assume a fixed object count.

### Step C3 — Recover declaratively

```powershell
kubectl --context kind-k8s-admin-ch012 apply -f .\workloads.yaml
kubectl --context kind-k8s-admin-ch012 -n ch012-dev describe service web
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** Service selector returns to `environment=dev` and two ready endpoints reappear. If the selector does not revert because of field ownership or apply conflicts, inspect the field managers and patch the selector back explicitly rather than deleting production resources.

## 11. Lab D — Annotations and metadata updates

### Step D1 — Annotate the Deployment

```powershell
kubectl --context kind-k8s-admin-ch012 -n ch012-dev annotate deployment web example.com/change-ticket=CHG-CH012
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get deployment web -o jsonpath='{.metadata.annotations.example\.com/change-ticket}'
kubectl --context kind-k8s-admin-ch012 -n ch012-dev describe deployment web
```

**Expected:** the annotation is present. This changes Deployment object metadata but not the Pod template, so it does not itself trigger a rollout.

### Step D2 — Update a non-selector label

```powershell
kubectl --context kind-k8s-admin-ch012 -n ch012-dev label deployment web cost-center=sandbox
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get deployment web --show-labels
```

**Expected:** Deployment metadata has the new label. Existing Pod labels are unchanged because the label was applied to the Deployment object, not `spec.template.metadata.labels`.

## 12. Lab E — ResourceQuota and LimitRange

### Step E1 — Create namespace governance

```powershell
@'
apiVersion: v1
kind: ResourceQuota
metadata:
  name: training-quota
  namespace: ch012-dev
spec:
  hard:
    requests.cpu: "1"
    requests.memory: 512Mi
    limits.memory: 1Gi
    pods: "5"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: container-defaults
  namespace: ch012-dev
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: 25m
        memory: 32Mi
      default:
        cpu: 250m
        memory: 128Mi
      max:
        memory: 256Mi
'@ | Set-Content -Encoding ascii .\governance.yaml

kubectl --context kind-k8s-admin-ch012 apply -f .\governance.yaml
kubectl --context kind-k8s-admin-ch012 -n ch012-dev describe resourcequota training-quota
kubectl --context kind-k8s-admin-ch012 -n ch012-dev describe limitrange container-defaults
```

**Expected:** quota usage includes the existing dev Pods. Default limits may be injected into **new** Pods, not retroactively applied to existing Pods.

### Step E2 — Simulate quota rejection

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: oversized
  namespace: ch012-dev
spec:
  containers:
    - name: nginx
      image: nginx:stable
      resources:
        requests:
          cpu: "2"
          memory: 32Mi
        limits:
          memory: 128Mi
'@ | Set-Content -Encoding ascii .\oversized.yaml

kubectl --context kind-k8s-admin-ch012 apply -f .\oversized.yaml
```

**Expected:** admission rejects the Pod because its CPU request exceeds the namespace's remaining and total request quota. Record the error and verify that no `oversized` Pod exists:

```powershell
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get pod oversized
```

A `NotFound` result is expected. Quota and LimitRange checks are admission-time controls; they do not guarantee sufficient physical node capacity.

## 13. Troubleshooting runbook

| Symptom | Evidence | Diagnosis |
|---|---|---|
| `NotFound` for existing-looking object | `-n`, `-A`, current context | Wrong namespace/context/name |
| Service has zero endpoints | Service selector, Pod labels, EndpointSlices | Label mismatch or unready Pods |
| Deployment does not manage expected Pods | Deployment selector, Pod template labels | Selector mismatch or ownership |
| Pod creation `Forbidden` due to quota | ResourceQuota status, API error | Requested resources exceed quota |
| Unexpected Pod limits | LimitRange and Pod spec | Admission defaulting |
| Cross-namespace access fails | RBAC, NetworkPolicy, Service DNS | Authorization or network control |
| Namespace stuck Terminating | Namespace conditions, finalizers, APIService health | Cleanup dependency |
| Relabeling has no expected effect | Object vs Pod template labels | Wrong metadata level changed |

### Production-safe diagnostic commands

```powershell
kubectl --context kind-k8s-admin-ch012 get namespaces --show-labels
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get pods --show-labels
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get service web -o yaml
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get endpointslices -l kubernetes.io/service-name=web
kubectl --context kind-k8s-admin-ch012 -n ch012-dev describe resourcequota
kubectl --context kind-k8s-admin-ch012 -n ch012-dev get events --sort-by=.lastTimestamp
```

**Do not force-delete terminating namespaces or remove finalizers without understanding what is blocked.**

## 14. Production SRE governance practices

1. Standardize required labels and allowed values through documented policy.
2. Use namespaces to organize workloads, not as a substitute for RBAC or network segmentation.
3. Keep Service and Deployment selectors stable and review selector changes like application routing changes.
4. Define quotas and limits based on capacity and workload needs; monitor rejected admissions and utilization.
5. Avoid broad label selectors in scripts that could accidentally target unrelated applications.
6. Document annotation consumers and controller-specific effects.
7. Track ownership, environment, data sensitivity, and cost allocation without storing sensitive information in metadata.
8. Use GitOps/policy-as-code for consistent namespace provisioning and change history.

## 15. Cleanup and rollback

Verify the disposable context:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch012 get nodes
```

Delete only the lab namespaces and cluster:

```powershell
kubectl --context kind-k8s-admin-ch012 delete namespace ch012-dev ch012-test
kind delete cluster --name k8s-admin-ch012
kind get clusters
Remove-Item .\namespaces.yaml, .\workloads.yaml, .\governance.yaml, .\oversized.yaml
```

**Warning:** Namespace deletion removes namespaced resources, potentially including persistent data references. This procedure is only for disposable lab resources.

## 16. Acceptance checklist

- [ ] Created and verified a disposable kind cluster.
- [ ] Created two namespaces with consistent labels.
- [ ] Distinguished namespaced and cluster-scoped resources.
- [ ] Deployed identically named applications into different namespaces.
- [ ] Queried resources using equality and set-based selectors.
- [ ] Verified Service endpoints before and after a selector mismatch.
- [ ] Restored Service routing through the declared manifest.
- [ ] Added annotations and distinguished object labels from Pod-template labels.
- [ ] Configured ResourceQuota and LimitRange.
- [ ] Observed a quota admission rejection without creating the Pod.
- [ ] Documented security and namespace lifecycle caveats.
- [ ] Cleaned up all disposable resources.

## 17. Knowledge check

1. Why does a namespace not guarantee network isolation?
2. What is the difference between a label and an annotation?
3. Why is a Deployment selector an operational contract?
4. Why can a Service exist without ready endpoints?
5. What is the difference between a label on a Deployment and one on its Pod template?
6. How do ResourceQuota and LimitRange differ?
7. Why can a namespace remain Terminating?
8. Why is removing finalizers a risky recovery shortcut?
9. Which metadata fields should be standardized for FinOps and ownership?
10. What additional controls are required for secure multi-tenancy?

## 18. Chapter status and next chapter

**Draft written; labs have not been independently executed or validated.** Mark **Lab Validated** after running acceptance checks and **Complete** after technical review.

**Next:** Chapter 013 — kubectl Advanced Administration.
