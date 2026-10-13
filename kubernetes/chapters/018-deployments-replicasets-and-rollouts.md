# Chapter 018 — Deployments, ReplicaSets and Rollouts

**Track:** Kubernetes Administration | **Part 04:** Pods and Workload Controllers | **Level:** Intermediate–Advanced | **Status:** Draft — hands-on validation pending

## 1. Learning objectives

By the end of this chapter, you should be able to:

1. Explain how a Deployment manages ReplicaSets and how ReplicaSets reconcile Pods.
2. Design RollingUpdate and Recreate strategies with appropriate availability and capacity tradeoffs.
3. Interpret `maxSurge`, `maxUnavailable`, `minReadySeconds`, and `progressDeadlineSeconds`.
4. Perform image updates, rollout pauses/resumes, status checks, and safe rollback.
5. Diagnose stuck rollouts, bad readiness probes, image pull failures, and quota/capacity constraints.
6. Use `kubectl rollout history`, revision annotations, events, and managed fields as change evidence.
7. Execute a disposable kind-based SRE incident lab with acceptance criteria and cleanup.

## 2. Controller architecture

```text
GitOps / kubectl apply
          |
          v
     Deployment
    spec.replicas: 3
    Pod template: v1
          |
          v
 Deployment controller
          |
          +-- ReplicaSet v1 (old template)
          |       +-- Pod A
          |       +-- Pod B
          |
          +-- ReplicaSet v2 (new template)
                  +-- Pod C
                  +-- Pod D
```

A Deployment describes the desired state of a stateless workload. Its controller creates and scales ReplicaSets as the Pod template changes. A ReplicaSet ensures that a target number of matching Pods exist. Pod replacement is **controller reconciliation**, not a guarantee that a failed container is replaced with a new Pod: containers can restart inside an existing Pod under its restart policy.

### Responsibility boundaries

| Resource | Responsibility | Operational implication |
|---|---|---|
| Deployment | Desired replica count, Pod template, rollout strategy and history | Preferred controller for stateless services |
| ReplicaSet | Maintains replica count for a Pod template | Typically owned and managed by Deployment |
| Pod | Scheduled execution unit | New Pod usually has new UID/IP |
| Service | Stable discovery/routing to selected ready endpoints | Traffic can continue during rollout when old Pods remain ready |
| HPA | Can change Deployment replica count | Manual scale may be overwritten by autoscaling |
| PDB | Limits some voluntary evictions | Does not enforce Deployment rolling-update availability |

Do not edit Deployment-owned ReplicaSets directly in normal operations; the Deployment controller may overwrite or supersede changes.

## 3. Deployment manifest anatomy

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: application
  labels:
    app.kubernetes.io/name: web
spec:
  replicas: 3
  revisionHistoryLimit: 5
  minReadySeconds: 5
  progressDeadlineSeconds: 120
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app.kubernetes.io/name: web
  template:
    metadata:
      labels:
        app.kubernetes.io/name: web
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
              cpu: 50m
              memory: 64Mi
            limits:
              memory: 256Mi
```

A Deployment's selector must match Pod template labels and is generally immutable after creation. Changes to **`spec.template`** create a new rollout revision; changes only to top-level Deployment metadata generally do not.

For production use immutable image digests where practical. Mutable tags can produce different images across nodes or restarts and make rollback harder to reason about.

## 4. ReplicaSet ownership and revision tracking

Inspect the relationship:

```powershell
kubectl get deployment web -o yaml
kubectl get replicasets -l app.kubernetes.io/name=web -o wide
kubectl get pods -l app.kubernetes.io/name=web -o wide
kubectl rollout history deployment/web
```

A Deployment-owned ReplicaSet has an owner reference to the Deployment UID. Pods have owner references to their ReplicaSet. The `deployment.kubernetes.io/revision` annotation helps identify revisions, but the Deployment rollout history is not a substitute for Git change history or an artifact registry.

`revisionHistoryLimit` controls retained old ReplicaSets after cleanup. Setting it too low reduces rollback options; setting it high increases retained objects. A rollback to a revision whose ReplicaSet has been pruned may not be possible.

## 5. RollingUpdate mechanics

For a Deployment with desired replicas **N**, `maxSurge` allows extra Pods above N during rollout, while `maxUnavailable` allows a number of desired replicas to be unavailable during the update.

| Desired replicas | maxSurge | maxUnavailable | Expected planning bound |
|---|---:|---:|---|
| 3 | 1 | 0 | Up to 4 Pods; target at least 3 available |
| 4 | 25% | 25% | Surge rounded up to 1; unavailable rounded down to 1 |
| 10 | 30% | 20% | Surge 3; unavailable 2 |

Percentages are rounded **up** for maxSurge and **down** for maxUnavailable. Both cannot be zero. Availability is influenced by readiness and `minReadySeconds`; the controller's planned bounds do not protect against node failure, runtime crashes, or other external disruptions.

### Operational tradeoffs

- **maxSurge > 0** requires spare scheduling capacity and possibly quota headroom.
- **maxUnavailable = 0** reduces planned unavailability but can stall a rollout if surge Pods cannot schedule or become ready.
- **minReadySeconds** requires a newly Ready Pod to remain Ready for a minimum time before being counted Available.
- **progressDeadlineSeconds** marks a rollout as failing to make progress; it does **not** automatically roll back the Deployment.

A successful `kubectl rollout status` reports the controller's rollout completion, not end-to-end application SLO compliance. Validate request success, latency, errors, and dependencies separately.

## 6. RollingUpdate versus Recreate

| Strategy | Behavior | Best fit | Risk |
|---|---|---|---|
| RollingUpdate | Incrementally adds/removes Pods | Most stateless services | Requires capacity; mixed versions coexist |
| Recreate | Terminates old Pods before creating new Pods | Workloads that cannot overlap versions | Deliberate downtime window |

Recreate is not a zero-downtime strategy. For schema migrations or protocol changes, plan backward/forward compatibility instead of relying solely on Deployment settings.

## 7. Rollout commands and safety

```powershell
kubectl rollout status deployment/web --timeout=180s
kubectl rollout history deployment/web
kubectl rollout history deployment/web --revision=2
kubectl set image deployment/web nginx=nginx:stable
kubectl rollout restart deployment/web
kubectl rollout pause deployment/web
kubectl rollout resume deployment/web
kubectl rollout undo deployment/web
kubectl rollout undo deployment/web --to-revision=2
```

**Guardrails:**

- Check the exact context and namespace before every mutation.
- Confirm the container name before `set image`; a wrong container name fails.
- `rollout restart` triggers a Pod template change; it is not an application repair guarantee.
- Paused Deployments do not complete new Pod template rollouts until resumed.
- `rollout undo` restores a prior Pod template; it does not roll back external databases, ConfigMaps, Secrets, migrations, or network changes.
- Avoid simultaneous imperative changes and GitOps reconciliation without clear ownership.

## 8. Lab prerequisites and stop conditions

**Environment:** Windows PowerShell, Docker Desktop, kind, kubectl.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch018 | Out-Null
Set-Location .\k8s-ch018
kind create cluster --name k8s-admin-ch018 --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch018 get nodes -o wide
```

**Expected:** context `kind-k8s-admin-ch018` and Ready node.

**Stop:** If the active context differs, do not continue. Every mutating command below explicitly targets this disposable cluster. Image downloads require network access; if images cannot be pulled, diagnose the registry/network and record the lab as blocked rather than claiming success.

## 9. Lab A — Deploy, inspect and trace ownership

### Step A1 — Create namespace, Deployment and Service

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch018
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch018
  labels:
    app: web
spec:
  replicas: 3
  revisionHistoryLimit: 5
  minReadySeconds: 3
  progressDeadlineSeconds: 120
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
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
  namespace: ch018
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
'@ | Set-Content -Encoding ascii .\web.yaml

kubectl --context kind-k8s-admin-ch018 apply --dry-run=server -f .\web.yaml
kubectl --context kind-k8s-admin-ch018 apply -f .\web.yaml
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch018 -n ch018 get deployment,replicaset,pod -o wide
kubectl --context kind-k8s-admin-ch018 -n ch018 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** Deployment 3/3 Available, a ReplicaSet owning three Pods, and three ready endpoints.

### Step A2 — Verify owner references and revision

```powershell
kubectl --context kind-k8s-admin-ch018 -n ch018 get replicasets -l app=web -o jsonpath='{range .items[*]}{.metadata.name}{" owner="}{.metadata.ownerReferences[0].name}{" revision="}{.metadata.annotations.deployment\.kubernetes\.io/revision}{"\n"}{end}'
kubectl --context kind-k8s-admin-ch018 -n ch018 get pods -l app=web -o jsonpath='{range .items[*]}{.metadata.name}{" owner="}{.metadata.ownerReferences[0].name}{"\n"}{end}'
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout history deployment/web
```

**Expected:** ReplicaSet owned by `web`; Pods owned by the ReplicaSet. Record revision number and UIDs.

## 10. Lab B — Trigger and observe a successful rolling update

Instead of relying on a mutable image tag, change a Pod template annotation to create a deterministic new revision.

```powershell
kubectl --context kind-k8s-admin-ch018 -n ch018 patch deployment web --type=merge -p '{"spec":{"template":{"metadata":{"annotations":{"training.example.com/revision":"v2"}}}}}'
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch018 -n ch018 get replicasets -l app=web -o wide
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout history deployment/web
kubectl --context kind-k8s-admin-ch018 -n ch018 get deployment web -o jsonpath='{.status.availableReplicas}'
```

**Expected:** a second ReplicaSet is created; new revision reaches three Available replicas and the old ReplicaSet scales to zero.

For a live view, run `kubectl ... get pods -l app=web -w` in a separate terminal before applying the patch. Exit the watch with Ctrl+C.

## 11. Lab C — Reproduce a stalled rollout

### Step C1 — Introduce a bad readiness probe

```powershell
kubectl --context kind-k8s-admin-ch018 -n ch018 patch deployment web --type=json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/does-not-exist"}]'
kubectl --context kind-k8s-admin-ch018 -n ch018 get deployment web
kubectl --context kind-k8s-admin-ch018 -n ch018 get pods -l app=web -o wide
kubectl --context kind-k8s-admin-ch018 -n ch018 get replicasets -l app=web
kubectl --context kind-k8s-admin-ch018 -n ch018 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** the new Pod template's readiness check fails. Because `maxUnavailable: 0`, healthy old Pods are expected to remain available while new unready Pods cannot advance the rollout. The new ReplicaSet may have one extra Pod from `maxSurge: 1`. The Service should retain ready old endpoints; **do not claim total outage**.

### Step C2 — Confirm the failure mode

```powershell
kubectl --context kind-k8s-admin-ch018 -n ch018 describe deployment web
kubectl --context kind-k8s-admin-ch018 -n ch018 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout status deployment/web --timeout=20s
```

**Expected:** the short rollout-status wait times out because the rollout has not completed. This is an intentional negative test; it does not imply the application has zero available endpoints. After the configured progress deadline, the Deployment may report `ProgressDeadlineExceeded`; Kubernetes does not automatically roll back.

## 12. Lab D — Recover by rollback

### Step D1 — Identify revisions

```powershell
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout history deployment/web
kubectl --context kind-k8s-admin-ch018 -n ch018 get replicasets -l app=web -o wide
```

### Step D2 — Roll back the bad template

```powershell
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout undo deployment/web
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch018 -n ch018 get deployment web
kubectl --context kind-k8s-admin-ch018 -n ch018 get pods -l app=web -o wide
kubectl --context kind-k8s-admin-ch018 -n ch018 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** the prior healthy Pod template returns, three replicas become Available, and Service endpoints remain healthy.

**Production lesson:** Confirm error rate, latency, request success, and dependencies after rollback. A successful rollout status is only one recovery signal.

## 13. Lab E — Pause, stage, resume and inspect rollout

### Step E1 — Pause and stage a change

```powershell
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout pause deployment/web
kubectl --context kind-k8s-admin-ch018 -n ch018 patch deployment web --type=merge -p '{"spec":{"template":{"metadata":{"annotations":{"training.example.com/change":"paused-stage"}}}}}'
kubectl --context kind-k8s-admin-ch018 -n ch018 get deployment web -o jsonpath='{.spec.paused}'
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout history deployment/web
```

**Expected:** Deployment is paused; the staged Pod template change does not proceed as a normal rollout while paused.

### Step E2 — Resume

```powershell
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout resume deployment/web
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout history deployment/web
```

**Expected:** rollout resumes and reaches Available state. Never leave a production Deployment paused unintentionally.

## 14. Lab F — Scale and inspect capacity behavior

```powershell
kubectl --context kind-k8s-admin-ch018 -n ch018 scale deployment/web --replicas=4
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch018 -n ch018 get deployment web
kubectl --context kind-k8s-admin-ch018 -n ch018 get pods -l app=web -o wide
kubectl --context kind-k8s-admin-ch018 -n ch018 scale deployment/web --replicas=3
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout status deployment/web --timeout=180s
```

**Expected:** desired replica count changes from three to four and back to three. `kubectl rollout status` checks rollout status; separately verify the desired and ready replica counts when evaluating a scale operation.

If HPA manages replicas in production, avoid fighting it with repeated manual scaling. Investigate autoscaler target and metric behavior first.

## 15. Lab G — Recreate strategy and downtime tradeoff

Use a separate Deployment to avoid disrupting `web`.

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: recreate-demo
  namespace: ch018
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: recreate-demo
  template:
    metadata:
      labels:
        app: recreate-demo
    spec:
      containers:
        - name: nginx
          image: nginx:stable
          resources:
            requests:
              cpu: 25m
              memory: 32Mi
'@ | Set-Content -Encoding ascii .\recreate.yaml

kubectl --context kind-k8s-admin-ch018 apply -f .\recreate.yaml
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout status deployment/recreate-demo --timeout=180s
kubectl --context kind-k8s-admin-ch018 -n ch018 patch deployment recreate-demo --type=merge -p '{"spec":{"template":{"metadata":{"annotations":{"training.example.com/revision":"v2"}}}}}'
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout status deployment/recreate-demo --timeout=180s
kubectl --context kind-k8s-admin-ch018 -n ch018 get replicasets -l app=recreate-demo
```

**Expected:** a new revision is created with Recreate semantics. Because this lab has no Service or continuous traffic generator for `recreate-demo`, **do not claim a measured downtime duration**. The strategy can introduce downtime by design.

## 16. Production troubleshooting matrix

| Symptom | First evidence | Likely issue |
|---|---|---|
| Deployment stuck progressing | `describe deployment`, conditions | Readiness, image, quota, scheduling |
| New Pods Pending | Pod events, requests, node allocatable | Insufficient surge capacity |
| New Pods ImagePullBackOff | Pod events, imagePullSecrets | Invalid tag, registry or credentials |
| New Pods CrashLoopBackOff | Previous logs, exit code | Startup/configuration failure |
| New Pods Running but not Ready | Probe events and EndpointSlices | Readiness failure |
| Rollout exceeds deadline | `Progressing=False`, reason | ProgressDeadlineExceeded |
| Rollback revision unavailable | ReplicaSet history | Pruned history or missing prior revision |
| Scale repeatedly overwritten | HPA events and status | Autoscaler ownership |
| Revisions grow unexpectedly | Pod template diffs | Frequent restart/annotation mutations |
| Availability drops unexpectedly | Node health, Pod events, topology | External failure outside rollout bounds |

### Incident evidence commands

```powershell
kubectl --context kind-k8s-admin-ch018 -n ch018 get deployment web -o yaml
kubectl --context kind-k8s-admin-ch018 -n ch018 rollout history deployment/web
kubectl --context kind-k8s-admin-ch018 -n ch018 get replicasets -l app=web -o wide
kubectl --context kind-k8s-admin-ch018 -n ch018 get pods -l app=web -o wide
kubectl --context kind-k8s-admin-ch018 -n ch018 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch018 -n ch018 get endpointslices -l kubernetes.io/service-name=web
kubectl --context kind-k8s-admin-ch018 -n ch018 logs deployment/web --tail=100 --timestamps
```

Capture cluster/context, namespace, Deployment UID, revision, ReplicaSet UIDs, Pod image/digest, readiness results, node assignments, rollout conditions, relevant logs and change timestamps. Redact secrets and customer data.

## 17. Production rollout and rollback runbook

### Pre-change

1. Confirm change ticket, target cluster, namespace, maintenance window and ownership.
2. Verify SLOs, current error rate, latency, capacity, quota and ready endpoints.
3. Review image digest, security scan, configuration and database compatibility.
4. Review `maxSurge`, `maxUnavailable`, readiness, startup and grace periods.
5. Confirm rollback revision or artifact availability, including external dependencies.
6. Run `kubectl diff` and server-side dry-run where supported.

### Execute

1. Apply the reviewed Deployment manifest through the approved delivery process.
2. Watch rollout conditions, ReplicaSet scaling, Pod scheduling, readiness and endpoints.
3. Monitor application request success, latency, errors and resource saturation.
4. Stop or roll back if guardrail thresholds are breached; do not wait blindly for deadline expiration.

### Recover

1. Capture current revision and evidence before changes.
2. Use `rollout undo` only when the previous template is known to be compatible.
3. Verify available replicas, ready endpoints and application SLO recovery.
4. Record residual risks and investigate root cause.

### Post-change

Confirm stable revision, desired replica count, no unexpected restarts, no stale paused Deployment, and sufficient capacity. Update incident/change records with exact commands and outcomes.

## 18. Common mistakes to avoid

- Treating a ReplicaSet as the primary configuration interface for a Deployment-managed workload.
- Assuming `Running` means Ready or that rollout status proves business-level availability.
- Using `maxUnavailable: 0` without surge headroom.
- Expecting `progressDeadlineSeconds` to trigger automatic rollback.
- Assuming a PDB prevents all rolling-update disruption.
- Rolling back a Pod template while ignoring irreversible schema or data changes.
- Using mutable tags without traceable image digests.
- Making simultaneous manual and GitOps changes without field ownership discipline.
- Leaving Deployments paused after emergency changes.

## 19. Cleanup and rollback

Verify the disposable context before cleanup:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch018 get nodes
```

Then:

```powershell
kubectl --context kind-k8s-admin-ch018 delete namespace ch018
kind delete cluster --name k8s-admin-ch018
kind get clusters
Remove-Item .\web.yaml, .\recreate.yaml -ErrorAction SilentlyContinue
```

**Warning:** Namespace and cluster deletion permanently remove lab resources. Never run equivalent commands on shared or production clusters.

## 20. Acceptance checklist

- [ ] Created disposable kind cluster and verified context.
- [ ] Deployed three-replica RollingUpdate Deployment and Service.
- [ ] Traced Deployment → ReplicaSet → Pod owner references.
- [ ] Observed revision history and successful new ReplicaSet rollout.
- [ ] Reproduced bad-readiness rollout and recorded conditions/events.
- [ ] Verified healthy old endpoints were retained during the stalled rollout.
- [ ] Rolled back and confirmed three Available replicas.
- [ ] Paused, staged and resumed a Deployment rollout.
- [ ] Scaled replicas up and down and inspected counts.
- [ ] Exercised Recreate strategy in a separate Deployment.
- [ ] Captured sanitized evidence and operational conclusions.
- [ ] Cleaned up all disposable resources.

## 21. Knowledge check

1. How do Deployments, ReplicaSets and Pods divide responsibilities?
2. What triggers creation of a new Deployment revision?
3. How are percentage maxSurge and maxUnavailable values rounded?
4. Why can a zero-unavailable rollout stall?
5. Does progressDeadlineSeconds automatically roll back a Deployment?
6. Why can healthy old endpoints remain during a bad readiness rollout?
7. What is the difference between Recreate and RollingUpdate?
8. What does rollout undo restore, and what does it not restore?
9. Why might manual scaling conflict with an HPA?
10. What evidence and SLOs should be verified after a rollback?

## 22. Status and next chapter

**Draft published.** Lab execution and technical review remain pending; do not mark the chapter validated until acceptance results are observed.

**Next:** Chapter 019 — StatefulSets, DaemonSets, Jobs and CronJobs.
