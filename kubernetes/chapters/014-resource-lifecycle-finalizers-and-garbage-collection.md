# Chapter 014 — Resource Lifecycle, Finalizers and Garbage Collection

**Track:** Kubernetes Administration · **Part:** 03 — Kubernetes API and Resource Administration · **Level:** Intermediate–Advanced · **Status:** Draft — lab execution pending

## 1. Learning objectives

After completing this chapter, you should be able to:

1. Trace a Kubernetes object's lifecycle from creation through reconciliation and deletion.
2. Explain `metadata.uid`, `resourceVersion`, `generation`, `deletionTimestamp`, owner references, and finalizers.
3. Compare foreground, background, and orphan deletion propagation.
4. Distinguish garbage collection from controller reconciliation and namespace cleanup.
5. Investigate resources stuck in `Terminating` without bypassing safeguards.
6. Practice owner-reference and finalizer behavior safely in a disposable kind cluster.
7. Produce an SRE deletion-incident runbook, evidence record, rollback decision, and acceptance report.

## 2. Lifecycle architecture

```text
Client / GitOps
    |
    v
kube-apiserver -- authentication, authorization, admission, validation
    |
    v
etcd object stored
    |
    +--> controller observes desired state --> creates/updates dependents
    |                                            |
    |                                            +--> ownerReferences
    |
    +--> DELETE request
              |
              +--> deletionTimestamp (if deletion is delayed)
              +--> finalizers must be cleared by responsible controllers
              +--> garbage collector handles dependent resources
              |
              v
        object removed from API
```

A successful `kubectl delete` request does not always mean the object has already disappeared. Deletion may be asynchronous. Finalizers and deletion propagation can delay removal while controllers complete required cleanup.

### Key metadata

| Field | Meaning | Operational use |
|---|---|---|
| `metadata.uid` | Unique identity of this object instance | Detect delete/recreate, correlate owners |
| `metadata.resourceVersion` | Opaque concurrency/watch token | Detect conflicting updates |
| `metadata.generation` | Desired-state generation where supported | Compare with controller observed generation |
| `metadata.ownerReferences` | References to owning objects | Dependency and garbage-collection analysis |
| `metadata.finalizers` | Cleanup gates before deletion completes | Diagnose terminating objects |
| `metadata.deletionTimestamp` | Deletion has been requested | Determine whether deletion is in progress |
| `metadata.deletionGracePeriodSeconds` | Grace period for supported deletions | Understand shutdown timing |

**Do not interpret resourceVersion as a clock or monotonically comparable number across arbitrary objects.**

## 3. Controller reconciliation versus garbage collection

A Deployment controller creates ReplicaSets, and ReplicaSets create Pods. When a Pod disappears while the ReplicaSet still desires replicas, the ReplicaSet creates a replacement. This is **reconciliation**, not garbage collection.

The Kubernetes garbage collector handles dependents of deleted owners according to owner references and deletion propagation. A replacement Pod may receive a new UID even if its logical application role is unchanged.

### Owner-reference rules

- Namespaced dependents may reference namespaced owners in the **same namespace**, or cluster-scoped owners.
- Cluster-scoped dependents cannot validly reference namespaced owners.
- An owner reference contains `apiVersion`, `kind`, `name`, and `uid`; the UID prevents accidental association with a recreated object of the same name.
- `controller: true` identifies the managing owner; a dependent can have at most one controlling owner.
- `blockOwnerDeletion: true` is relevant to foreground deletion and subject to admission/RBAC controls.

Avoid manually changing owner references on production resources without understanding controller behavior and the garbage collector.

## 4. Deletion propagation policies

| Policy | Expected behavior | Operational risk |
|---|---|---|
| Background | Owner removed first; dependents cleaned up asynchronously | Temporary orphan-looking dependents |
| Foreground | Owner stays in deletion until blocking dependents are deleted | Owner can remain Terminating |
| Orphan | Owner removed; dependents remain and owner references are adjusted | Unmanaged objects may continue consuming resources |

Use `kubectl delete --cascade=background|foreground|orphan` for explicit behavior. Defaults and controller-specific deletion behavior should be verified on the target Kubernetes version.

**Important:** `--wait=false` only changes whether kubectl waits; it does not change the API's deletion propagation or guarantee that deletion completed.

## 5. Finalizers: purpose and safety

Finalizers are strings in `metadata.finalizers`. On deletion, the API server records a deletion timestamp and retains the object until finalizers are removed. A controller responsible for a finalizer performs cleanup, then removes its finalizer entry.

Common examples include storage protection, namespace lifecycle cleanup, and operator-specific cloud resource teardown.

**Finalizers are not a retry counter, lock timeout, or permission bypass.** Manually removing a finalizer may leave cloud resources, persistent volumes, external identities, or other dependencies behind.

### Safe finalizer triage

1. Confirm exact context, namespace, kind, name, UID, and deletion timestamp.
2. Inspect finalizers, owner references, events, and controller logs.
3. Identify the controller responsible for each finalizer.
4. Determine whether cleanup is progressing, blocked, or already completed.
5. Restore the responsible controller or dependency when possible.
6. Escalate any manual finalizer removal through documented change control, backup, and owner approval.

Do not blindly use `kubectl patch ... -p '{"metadata":{"finalizers":[]}}'` in production.

## 6. Lab prerequisites and safety gate

Use **Windows PowerShell**, Docker Desktop, kind, and kubectl. All mutations target a disposable cluster named `k8s-admin-ch014`.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch014 | Out-Null
Set-Location .\k8s-ch014
kind create cluster --name k8s-admin-ch014 --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch014 get nodes
```

**Expected:** current context `kind-k8s-admin-ch014`, node Ready.

**Stop condition:** If the context differs, do not proceed. Never run the deletion/finalizer exercises against shared, staging, or production resources.

## 7. Lab A — Inspect the ownership chain

### Step A1 — Create a namespace and Deployment

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch014
  labels:
    training: resource-lifecycle
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch014
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
      terminationGracePeriodSeconds: 10
      containers:
        - name: nginx
          image: nginx:stable
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
            limits:
              memory: 128Mi
'@ | Set-Content -Encoding ascii .\ch014-deployment.yaml

kubectl --context kind-k8s-admin-ch014 apply --dry-run=server -f .\ch014-deployment.yaml
kubectl --context kind-k8s-admin-ch014 apply -f .\ch014-deployment.yaml
kubectl --context kind-k8s-admin-ch014 -n ch014 rollout status deployment/web --timeout=180s
```

**Expected:** two Ready Pods.

### Step A2 — Inspect Deployment, ReplicaSet, and Pod owner references

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 get deployment,replicaset,pod -o wide
kubectl --context kind-k8s-admin-ch014 -n ch014 get replicaset -o jsonpath='{range .items[*]}{.metadata.name}{" owner="}{.metadata.ownerReferences[0].name}{" uid="}{.metadata.ownerReferences[0].uid}{"\n"}{end}'
kubectl --context kind-k8s-admin-ch014 -n ch014 get pods -l app=web -o jsonpath='{range .items[*]}{.metadata.name}{" owner="}{.metadata.ownerReferences[0].name}{"\n"}{end}'
kubectl --context kind-k8s-admin-ch014 -n ch014 get deployment web -o jsonpath='{.metadata.uid}'
```

**Expected:** ReplicaSet owned by Deployment; Pods owned by ReplicaSet. The owner UID matches the owning object's UID.

### Step A3 — Observe reconciliation

```powershell
$pod = kubectl --context kind-k8s-admin-ch014 -n ch014 get pods -l app=web -o jsonpath='{.items[0].metadata.name}'
kubectl --context kind-k8s-admin-ch014 -n ch014 delete pod $pod
kubectl --context kind-k8s-admin-ch014 -n ch014 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch014 -n ch014 get pods -l app=web -o wide
```

**Expected:** ReplicaSet creates a replacement Pod with a different UID. This is reconciliation, not garbage collection.

## 8. Lab B — Background deletion propagation

Use a standalone training Deployment to avoid affecting the web workload.

### Step B1 — Create a disposable Deployment

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 create deployment background-demo --image=nginx:stable --replicas=1
kubectl --context kind-k8s-admin-ch014 -n ch014 rollout status deployment/background-demo --timeout=180s
kubectl --context kind-k8s-admin-ch014 -n ch014 get replicasets,pods -l app=background-demo
```

### Step B2 — Delete with background propagation

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 delete deployment background-demo --cascade=background --wait=false
kubectl --context kind-k8s-admin-ch014 -n ch014 get deployments,replicasets,pods
```

**Expected:** Deployment deletion is requested without waiting; ReplicaSet/Pod cleanup proceeds asynchronously. They may already be gone by the time you inspect them. Do not depend on observing a transient state.

## 9. Lab C — Orphan dependents intentionally

### Step C1 — Create a Deployment and record ownership

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 create deployment orphan-demo --image=nginx:stable --replicas=1
kubectl --context kind-k8s-admin-ch014 -n ch014 rollout status deployment/orphan-demo --timeout=180s
kubectl --context kind-k8s-admin-ch014 -n ch014 get replicasets,pods -l app=orphan-demo -o wide
```

### Step C2 — Delete the owner but retain dependents

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 delete deployment orphan-demo --cascade=orphan --wait=true
kubectl --context kind-k8s-admin-ch014 -n ch014 get replicasets,pods -l app=orphan-demo -o wide
```

**Expected:** Deployment disappears; ReplicaSet and Pod remain. The orphaned ReplicaSet's owner reference to the Deployment is removed by garbage-collection processing.

### Step C3 — Inspect orphaned ReplicaSet

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 get replicasets -l app=orphan-demo -o yaml
```

**Expected:** ReplicaSet no longer has the deleted Deployment as owner. **Do not create another Deployment with matching selectors while the orphan exists**; controllers can adopt matching resources under some conditions.

### Step C4 — Clean up orphaned resources

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 delete replicasets -l app=orphan-demo --cascade=background
kubectl --context kind-k8s-admin-ch014 -n ch014 get pods -l app=orphan-demo
```

**Expected:** the orphaned ReplicaSet and its dependent Pod are removed. Recheck after asynchronous garbage collection.

## 10. Lab D — Safe finalizer demonstration

This lab uses a **ConfigMap created only for training**, with a synthetic finalizer. No external cleanup is required.

### Step D1 — Create a ConfigMap with a training finalizer

```powershell
@'
apiVersion: v1
kind: ConfigMap
metadata:
  name: finalizer-demo
  namespace: ch014
  finalizers:
    - training.example.com/cleanup
data:
  purpose: finalizer-lab
'@ | Set-Content -Encoding ascii .\ch014-finalizer.yaml

kubectl --context kind-k8s-admin-ch014 apply -f .\ch014-finalizer.yaml
kubectl --context kind-k8s-admin-ch014 -n ch014 get configmap finalizer-demo -o yaml
```

**Expected:** ConfigMap exists with `training.example.com/cleanup` finalizer.

### Step D2 — Request deletion without waiting

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 delete configmap finalizer-demo --wait=false
kubectl --context kind-k8s-admin-ch014 -n ch014 get configmap finalizer-demo -o jsonpath='{.metadata.deletionTimestamp}'
kubectl --context kind-k8s-admin-ch014 -n ch014 get configmap finalizer-demo -o jsonpath='{.metadata.finalizers}'
```

**Expected:** deletion timestamp is set and finalizer remains; the object stays visible while termination is blocked.

### Step D3 — Resolve the synthetic finalizer

**Only because this is a disposable ConfigMap with a known synthetic finalizer**, remove it to model the responsible controller completing cleanup:

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 patch configmap finalizer-demo --type=json -p '[{"op":"remove","path":"/metadata/finalizers/0"}]'
kubectl --context kind-k8s-admin-ch014 -n ch014 get configmap finalizer-demo
```

**Expected:** the ConfigMap disappears; `NotFound` is the desired result.

**Production warning:** This is **not** an approved remediation pattern for unknown or real finalizers. Removing a real finalizer without cleanup can orphan cloud infrastructure, volumes, or external records.

## 11. Lab E — Foreground deletion and dependent blocking

Foreground deletion may complete too quickly to observe with a simple Deployment. Instead, inspect the concept with a disposable Deployment and capture metadata/events without relying on timing.

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 create deployment foreground-demo --image=nginx:stable --replicas=1
kubectl --context kind-k8s-admin-ch014 -n ch014 rollout status deployment/foreground-demo --timeout=180s
kubectl --context kind-k8s-admin-ch014 -n ch014 delete deployment foreground-demo --cascade=foreground --wait=false
kubectl --context kind-k8s-admin-ch014 -n ch014 get deployment foreground-demo -o yaml
kubectl --context kind-k8s-admin-ch014 -n ch014 get replicasets,pods -l app=foreground-demo
```

**Expected:** foreground deletion is requested. If the owner is still present, inspect `deletionTimestamp` and `foregroundDeletion` finalizer. It is also valid for the Deployment and dependents to have already disappeared by the time commands run. A `NotFound` response is not a lab failure.

## 12. Lab F — Diagnose a terminating resource

### Step F1 — Inspect resource and namespace status

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 get configmaps -o wide
kubectl --context kind-k8s-admin-ch014 get namespace ch014 -o yaml
kubectl --context kind-k8s-admin-ch014 -n ch014 get events --sort-by=.lastTimestamp
```

### Step F2 — Inspect API discovery health

```powershell
kubectl --context kind-k8s-admin-ch014 get apiservices
kubectl --context kind-k8s-admin-ch014 api-resources --namespaced=true
```

### Step F3 — Read-only finalizer inventory

```powershell
$objects = kubectl --context kind-k8s-admin-ch014 -n ch014 get configmaps -o json | ConvertFrom-Json
$objects.items | Where-Object { $_.metadata.finalizers -and $_.metadata.finalizers.Count -gt 0 } |
  Select-Object @{Name='Name';Expression={$_.metadata.name}},
                @{Name='Finalizers';Expression={$_.metadata.finalizers -join ','}},
                @{Name='DeletionTimestamp';Expression={$_.metadata.deletionTimestamp}}
```

**Expected:** a table of ConfigMaps with finalizers, if any remain. This example inventories ConfigMaps only; an actual namespace incident requires checking **all** namespaced resource types and CRDs, including unavailable API groups.

## 13. Production incident runbook: stuck Terminating

### Step 1 — Scope and impact

Record cluster, namespace, resource type, name, UID, deletion timestamp, finalizers, owner references, and business impact. Determine whether the object is a PVC/PV, Namespace, CRD, custom resource, or controller-managed workload.

### Step 2 — Identify blocking cleanup

```powershell
kubectl --context kind-k8s-admin-ch014 -n ch014 get configmap finalizer-demo -o yaml
kubectl --context kind-k8s-admin-ch014 get apiservices
kubectl --context kind-k8s-admin-ch014 get crds
```

The ConfigMap command is illustrative and returns NotFound after Lab D. For real incidents, substitute the exact resource and context.

### Step 3 — Investigate responsible controller

Inspect its Deployment/Pod health, logs, RBAC, API errors, cloud provider permissions, and external dependencies. For PVC/PV cases, inspect CSI controller/node plugin health, VolumeAttachments, and workload usage.

### Step 4 — Restore normal cleanup

Prefer restoring a broken controller, webhook, APIService, or external dependency so cleanup can finish normally.

### Step 5 — Escalate manual intervention

If finalizer removal is the only remaining option, require documented owner approval, confirmation of external cleanup or orphan acceptance, evidence capture, and an explicit rollback/remediation plan. Some deletions cannot be rolled back; recreation may create a new UID and different semantics.

## 14. Failure patterns and decision matrix

| Symptom | First evidence | Likely investigation |
|---|---|---|
| Pod reappears after deletion | Owner references, ReplicaSet desired count | Controller reconciliation |
| Deployment deleted but Pods remain briefly | Propagation policy, owner references | Asynchronous background GC |
| Deployment deleted but ReplicaSet persists | Owner refs, orphan policy | Intentional orphaning or adoption |
| Object stuck Terminating | deletionTimestamp, finalizers | Controller cleanup failure |
| Namespace stuck Terminating | Namespace conditions, remaining resources | Discovery failures, finalizers, APIService |
| PVC/PV cannot be deleted | Protection finalizers, mounts, attachments | Storage use or CSI issues |
| CRD deletion blocked | CRD finalizers, custom resources | Custom resource cleanup |
| 409 conflict on update | resourceVersion/managed fields | Concurrent writes |
| Unexpected deletion blast radius | ownerReferences, cascade policy | Ownership or propagation misunderstanding |

## 15. Safety and operational best practices

- Prefer GitOps-managed lifecycle and approved maintenance windows.
- Inspect owner references before deleting a resource with dependents.
- Use explicit `--cascade` where behavior matters.
- Do not confuse `--wait=false` with successful cleanup.
- Capture UID and owner references to distinguish replacement from resurrection.
- Monitor controllers responsible for cleanup finalizers.
- Keep CRD/operator upgrade plans compatible with resource finalizers.
- Avoid force deletion, direct etcd edits, or finalizer stripping as generic troubleshooting shortcuts.
- Validate that storage, cloud, and security cleanup actually completed before closing incidents.

## 16. Cleanup

Verify the disposable context:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch014 get nodes
```

Clean up only the lab resources:

```powershell
kubectl --context kind-k8s-admin-ch014 delete namespace ch014
kind delete cluster --name k8s-admin-ch014
kind get clusters
Remove-Item .\ch014-deployment.yaml, .\ch014-finalizer.yaml
```

**Warning:** Namespace and cluster deletion are destructive. If a lab-created finalizer is unexpectedly still present, resolve that known synthetic finalizer before deleting the namespace. Never apply this procedure to an unknown production finalizer.

## 17. Acceptance checklist

- [ ] Created and verified the disposable kind cluster.
- [ ] Deployed a workload and traced Deployment → ReplicaSet → Pod ownership.
- [ ] Inspected UID, owner references, and desired/observed state.
- [ ] Deleted a Pod and observed controller reconciliation.
- [ ] Tested background deletion and observed asynchronous cleanup.
- [ ] Orphaned a ReplicaSet and then removed its dependent resources.
- [ ] Created a synthetic finalizer on a disposable ConfigMap.
- [ ] Observed deletionTimestamp and blocked deletion.
- [ ] Cleared only the known synthetic finalizer and verified removal.
- [ ] Tested foreground deletion without relying on transient timing.
- [ ] Reviewed namespace/API discovery and stuck-deletion diagnostics.
- [ ] Documented production finalizer-removal risks and incident evidence.
- [ ] Cleaned up all disposable resources.

## 18. Knowledge check

1. How is controller reconciliation different from garbage collection?
2. Why does an owner reference include a UID?
3. What happens when a Deployment is deleted with `--cascade=orphan`?
4. How do foreground and background propagation differ?
5. Why can `kubectl delete` return while an object remains visible?
6. What does a deletionTimestamp tell you?
7. Why is removing a real finalizer without cleanup dangerous?
8. What can cause a namespace to remain Terminating?
9. Why might a Pod with the same application label reappear with a different UID?
10. What evidence must be captured before manual deletion intervention?

## 19. Chapter status and next chapter

**Draft written; hands-on execution has not been independently verified.** Promote to **Lab Validated** after completing acceptance tests and to **Complete** after technical review.

**Next:** Chapter 015 — Resource Management and Administration Lab.
