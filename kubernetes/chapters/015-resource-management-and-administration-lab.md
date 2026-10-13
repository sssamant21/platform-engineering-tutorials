# Chapter 015 — Resource Management and Administration Lab

**Track:** Kubernetes Administration · **Part:** 03 — Kubernetes API and Resource Administration · **Type:** Capstone Project · **Level:** Intermediate–Advanced · **Status:** Draft — execution and review pending

## 1. Project mission

Act as the on-call Kubernetes platform engineer responsible for a new application team's namespace and resource lifecycle. Provision a disposable cluster, discover its API capabilities, establish namespace governance, deploy an application, diagnose a Service outage caused by a selector mismatch, inspect managed fields and rollout behavior, investigate owner references and a blocked deletion, and deliver an evidence-backed operational handover.

This is the **Part 03 capstone** integrating Chapters 011–014. The lab is designed for Windows PowerShell with Docker Desktop, kind, and kubectl. **Do not execute disruptive exercises against production, shared, EKS, AKS, or GKE clusters.**

## 2. Learning outcomes

By the end of the project, you should be able to:

1. Discover the Kubernetes API groups, versions, resource scopes, and schemas served by a cluster.
2. Build namespaced application resources with a documented label and annotation taxonomy.
3. Implement namespace ResourceQuota and LimitRange and diagnose admission failures.
4. Use kubectl selectors, JSONPath, diff, server-side dry run, patch, and rollout history safely.
5. Diagnose and recover a Service selector mismatch using Pod labels and EndpointSlices.
6. Distinguish ReplicaSet reconciliation from garbage collection and verify owner references.
7. Reproduce a synthetic finalizer-blocked deletion and resolve only that controlled lab object.
8. Capture evidence, assess impact, document rollback, and deliver a pass/fail acceptance report.

## 3. Architecture and operating boundaries

```text
Windows PowerShell
       |
  kubectl + kubeconfig
       |
   kind API server
       |
   +--- cluster-scoped: Namespace, Node, API resources
   |
   +--- namespace ch015
           |
           +--- ResourceQuota + LimitRange
           +--- Deployment/web (2 replicas)
           |      +--- ReplicaSet
           |              +--- Pods (labels + ownerReferences)
           +--- Service/web --> EndpointSlices --> ready Pods
           +--- ConfigMap/finalizer-demo (synthetic finalizer)
           +--- Pod/client (DNS/HTTP diagnostics)
```

**Isolation caveat:** A namespace provides API resource scope, not automatic network or security isolation. RBAC, policy, and CNI enforcement are separate controls.

## 4. Acceptance matrix

| ID | Test | Pass criteria |
|---|---|---|
| A01 | Context safety | Context is exactly `kind-k8s-admin-ch015` |
| A02 | API discovery | Core, apps, and resource scopes discovered |
| A03 | Namespace governance | Namespace labels, quota, and limits visible |
| A04 | Deployment | 2/2 Ready; Pod labels match selector |
| A05 | Service health | Two ready endpoints and successful in-cluster HTTP |
| A06 | Selector failure | Deliberate mismatch removes ready endpoints |
| A07 | Recovery | Original selector restored; HTTP works |
| A08 | Quota enforcement | Oversized Pod rejected and absent |
| A09 | Advanced kubectl | Diff, JSONPath, managed fields, rollout inspected |
| A10 | Reconciliation | Deleted Pod replaced with a different UID |
| A11 | Finalizer | Synthetic deletion blocks, then completes after cleanup |
| A12 | Handover | Evidence, findings, risks, and cleanup recorded |

**Passing this project is not production certification.** It does not test multi-zone resilience, HA control plane, backup/restore, secure multi-tenancy, or production admission-policy completeness.

## 5. Prerequisites and safety gate

Run these in **Windows PowerShell**:

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch015 | Out-Null
Set-Location .\k8s-ch015
kind create cluster --name k8s-admin-ch015 --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch015 get nodes -o wide
```

**Expected:** `kind-k8s-admin-ch015` is the active context, and the node is Ready.

**Stop condition:** Do not continue if the context differs. All subsequent mutations explicitly target the lab context. The commands intentionally create/delete objects and must never be copied into an unrelated environment.

## 6. Lab A — Discover the API and validate resource scope

### Step A1 — Read API discovery

```powershell
kubectl --context kind-k8s-admin-ch015 get --raw /api
kubectl --context kind-k8s-admin-ch015 get --raw /apis
kubectl --context kind-k8s-admin-ch015 api-resources --api-group=apps
kubectl --context kind-k8s-admin-ch015 api-resources --namespaced=true
kubectl --context kind-k8s-admin-ch015 api-resources --namespaced=false
kubectl --context kind-k8s-admin-ch015 explain deployment.spec.selector
```

**Expected:** API groups and resource lists returned; Deployments are namespaced, Namespaces are cluster-scoped.

### Step A2 — Capture baseline

```powershell
kubectl --context kind-k8s-admin-ch015 get nodes
kubectl --context kind-k8s-admin-ch015 get namespaces
kubectl --context kind-k8s-admin-ch015 get apiservices
```

Record the server version, context, timestamp, and any APIService issues. Do not collect or share kubeconfig credentials.

## 7. Lab B — Provision a governed namespace

### Step B1 — Create Namespace, ResourceQuota and LimitRange

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch015
  labels:
    environment: lab
    team: platform
    cost-center: sandbox
  annotations:
    training.example.com/purpose: "Part 03 administration capstone"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: training-quota
  namespace: ch015
spec:
  hard:
    pods: "6"
    requests.cpu: "1"
    requests.memory: 512Mi
    limits.memory: 1Gi
---
apiVersion: v1
kind: LimitRange
metadata:
  name: container-defaults
  namespace: ch015
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

kubectl --context kind-k8s-admin-ch015 apply --dry-run=server -f .\governance.yaml
kubectl --context kind-k8s-admin-ch015 apply -f .\governance.yaml
kubectl --context kind-k8s-admin-ch015 get namespace ch015 --show-labels
kubectl --context kind-k8s-admin-ch015 -n ch015 describe resourcequota training-quota
kubectl --context kind-k8s-admin-ch015 -n ch015 describe limitrange container-defaults
```

**Expected:** namespace Active, quota and limits installed. Admission behavior depends on the resources declared in new Pods.

**Production note:** Quota values here are deliberately small training thresholds, not recommended production defaults.

## 8. Lab C — Deploy application and validate Service discovery

### Step C1 — Create Deployment and Service

```powershell
@'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch015
  labels:
    app.kubernetes.io/name: web
    team: platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: web
  template:
    metadata:
      labels:
        app.kubernetes.io/name: web
        environment: lab
        team: platform
    spec:
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - name: http
              containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: http
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
  namespace: ch015
spec:
  selector:
    app.kubernetes.io/name: web
  ports:
    - port: 80
      targetPort: http
'@ | Set-Content -Encoding ascii .\application.yaml

kubectl --context kind-k8s-admin-ch015 apply --dry-run=server -f .\application.yaml
kubectl --context kind-k8s-admin-ch015 apply -f .\application.yaml
kubectl --context kind-k8s-admin-ch015 -n ch015 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch015 -n ch015 get pods -o wide --show-labels
kubectl --context kind-k8s-admin-ch015 -n ch015 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** two Ready Pods and two ready Service endpoints.

### Step C2 — Create a diagnostic client

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: ch015
spec:
  containers:
    - name: toolbox
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          memory: 64Mi
'@ | Set-Content -Encoding ascii .\client.yaml

kubectl --context kind-k8s-admin-ch015 apply -f .\client.yaml
kubectl --context kind-k8s-admin-ch015 -n ch015 wait --for=condition=Ready pod/client --timeout=180s
kubectl --context kind-k8s-admin-ch015 -n ch015 exec client -- nslookup web.ch015.svc.cluster.local
kubectl --context kind-k8s-admin-ch015 -n ch015 exec client -- wget -qO- http://web.ch015.svc.cluster.local
```

**Expected:** DNS returns the Service IP and HTTP returns NGINX content.

## 9. Lab D — Simulate Service outage and recover

### Step D1 — Inspect healthy routing first

```powershell
kubectl --context kind-k8s-admin-ch015 -n ch015 get service web -o yaml
kubectl --context kind-k8s-admin-ch015 -n ch015 get endpointslices -l kubernetes.io/service-name=web
```

### Step D2 — Introduce a selector mismatch

```powershell
kubectl --context kind-k8s-admin-ch015 -n ch015 patch service web --type merge -p '{"spec":{"selector":{"app.kubernetes.io/name":"not-web"}}}'
kubectl --context kind-k8s-admin-ch015 -n ch015 describe service web
kubectl --context kind-k8s-admin-ch015 -n ch015 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** no ready endpoints after reconciliation. Existing EndpointSlice objects may disappear or show no ready backends.

### Step D3 — Restore routing

```powershell
kubectl --context kind-k8s-admin-ch015 -n ch015 apply -f .\application.yaml
kubectl --context kind-k8s-admin-ch015 -n ch015 get endpointslices -l kubernetes.io/service-name=web
kubectl --context kind-k8s-admin-ch015 -n ch015 exec client -- wget -qO- http://web.ch015.svc.cluster.local
```

**Expected:** ready endpoints return and HTTP succeeds. If client-side apply does not restore the selector due to field ownership, inspect managed fields and use an explicitly reviewed patch for the lab Service.

**Incident lesson:** Service DNS resolution can succeed while the Service has zero endpoints. Check EndpointSlices and selectors before changing CoreDNS.

## 10. Lab E — Enforce quotas and diagnose admission failures

### Step E1 — Create an intentionally oversized Pod

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: oversized
  namespace: ch015
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

kubectl --context kind-k8s-admin-ch015 apply -f .\oversized.yaml
```

**Expected:** API admission rejects the Pod because the requested CPU exceeds the quota. This is an intentional negative test.

```powershell
kubectl --context kind-k8s-admin-ch015 -n ch015 get pod oversized
kubectl --context kind-k8s-admin-ch015 -n ch015 describe resourcequota training-quota
```

**Expected:** `NotFound` for the oversized Pod; quota remains in force.

## 11. Lab F — Advanced kubectl administration

### Step F1 — Query labels, fields, and JSONPath

```powershell
kubectl --context kind-k8s-admin-ch015 -n ch015 get pods -l app.kubernetes.io/name=web -o wide
kubectl --context kind-k8s-admin-ch015 -n ch015 get pods --field-selector=status.phase=Running
kubectl --context kind-k8s-admin-ch015 -n ch015 get pods -o custom-columns='NAME:.metadata.name,NODE:.spec.nodeName,PHASE:.status.phase'
kubectl --context kind-k8s-admin-ch015 -n ch015 get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.uid}{"\n"}{end}'
```

### Step F2 — Inspect managed fields

```powershell
$web = kubectl --context kind-k8s-admin-ch015 -n ch015 get deployment web -o json | ConvertFrom-Json
$web.metadata.managedFields | Select-Object manager,operation,apiVersion,time
```

### Step F3 — Trigger a safe rollout and inspect history

```powershell
kubectl --context kind-k8s-admin-ch015 -n ch015 patch deployment web --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"training.example.com/revision":"2"}}}}}'
kubectl --context kind-k8s-admin-ch015 -n ch015 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch015 -n ch015 rollout history deployment/web
kubectl --context kind-k8s-admin-ch015 -n ch015 rollout undo deployment/web
kubectl --context kind-k8s-admin-ch015 -n ch015 rollout status deployment/web --timeout=180s
```

**Expected:** new revision created and rollback restores previous Pod template.

### Step F4 — Preview declarative drift

```powershell
kubectl --context kind-k8s-admin-ch015 -n ch015 scale deployment/web --replicas=3
kubectl --context kind-k8s-admin-ch015 -n ch015 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch015 diff -f .\application.yaml
kubectl --context kind-k8s-admin-ch015 apply -f .\application.yaml
kubectl --context kind-k8s-admin-ch015 -n ch015 rollout status deployment/web --timeout=180s
```

**Expected:** diff may show replica drift; `kubectl diff` returns code 1 when differences exist. After apply, desired replicas should return to two. If field ownership prevents reconciliation, inspect `managedFields` before proceeding.

## 12. Lab G — Resource lifecycle and reconciliation

### Step G1 — Trace owner references

```powershell
kubectl --context kind-k8s-admin-ch015 -n ch015 get deployment,replicaset,pod -o wide
kubectl --context kind-k8s-admin-ch015 -n ch015 get replicasets -l app.kubernetes.io/name=web -o jsonpath='{range .items[*]}{.metadata.name}{" owner="}{.metadata.ownerReferences[0].name}{"\n"}{end}'
kubectl --context kind-k8s-admin-ch015 -n ch015 get pods -l app.kubernetes.io/name=web -o jsonpath='{range .items[*]}{.metadata.name}{" owner="}{.metadata.ownerReferences[0].name}{"\n"}{end}'
```

**Expected:** ReplicaSet owned by Deployment; Pods owned by ReplicaSet.

### Step G2 — Delete one Pod and observe reconciliation

```powershell
$pod = kubectl --context kind-k8s-admin-ch015 -n ch015 get pods -l app.kubernetes.io/name=web -o jsonpath='{.items[0].metadata.name}'
$uid = kubectl --context kind-k8s-admin-ch015 -n ch015 get pod $pod -o jsonpath='{.metadata.uid}'
kubectl --context kind-k8s-admin-ch015 -n ch015 delete pod $pod
kubectl --context kind-k8s-admin-ch015 -n ch015 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch015 -n ch015 get pods -l app.kubernetes.io/name=web -o custom-columns='NAME:.metadata.name,UID:.metadata.uid'
```

**Expected:** ReplicaSet creates a replacement Pod with a new UID; two Ready replicas restored. Record the original UID as evidence.

## 13. Lab H — Synthetic finalizer and blocked deletion

This exercise deliberately blocks deletion of a **lab-only ConfigMap**. It does not modify production finalizers or cloud resources.

### Step H1 — Create a synthetic finalizer

```powershell
@'
apiVersion: v1
kind: ConfigMap
metadata:
  name: finalizer-demo
  namespace: ch015
  finalizers:
    - training.example.com/cleanup
data:
  purpose: "safe deletion exercise"
'@ | Set-Content -Encoding ascii .\finalizer.yaml

kubectl --context kind-k8s-admin-ch015 apply -f .\finalizer.yaml
kubectl --context kind-k8s-admin-ch015 -n ch015 get configmap finalizer-demo -o yaml
```

### Step H2 — Request deletion and inspect state

```powershell
kubectl --context kind-k8s-admin-ch015 -n ch015 delete configmap finalizer-demo --wait=false
kubectl --context kind-k8s-admin-ch015 -n ch015 get configmap finalizer-demo -o jsonpath='{.metadata.deletionTimestamp}'
kubectl --context kind-k8s-admin-ch015 -n ch015 get configmap finalizer-demo -o jsonpath='{.metadata.finalizers}'
```

**Expected:** deletionTimestamp is set, and the object remains because the synthetic finalizer is present.

### Step H3 — Complete the known synthetic cleanup

```powershell
kubectl --context kind-k8s-admin-ch015 -n ch015 patch configmap finalizer-demo --type=json -p '[{"op":"remove","path":"/metadata/finalizers/0"}]'
kubectl --context kind-k8s-admin-ch015 -n ch015 get configmap finalizer-demo
```

**Expected:** `NotFound` after the finalizer is removed.

**Production warning:** Never generalize this manual patch to unknown finalizers on Namespaces, PVCs, PVs, CRDs, or operator-managed resources. Identify and restore the responsible controller or cleanup dependency instead.

## 14. Incident simulation and evidence-based triage

### Scenario 1 — Application unavailable through Service

1. Verify the correct cluster and namespace.
2. Inspect Deployment/Pod readiness.
3. Inspect Service selector and Pod labels.
4. Inspect EndpointSlices.
5. Query DNS separately from HTTP.
6. Restore the declared selector.
7. Confirm endpoint and HTTP recovery.

### Scenario 2 — Pod creation rejected

1. Read the exact API admission error.
2. Inspect ResourceQuota and LimitRange.
3. Compare requested resources with remaining quota.
4. Confirm the rejected object does not exist.
5. Change the request or quota through an approved process.

### Scenario 3 — Resource stuck Terminating

1. Capture UID, deletionTimestamp, owner references, and finalizers.
2. Identify the finalizer owner/controller.
3. Inspect controller health, RBAC, events, and dependencies.
4. Prefer restoring normal cleanup.
5. Escalate manual removal only with documented owner approval and orphan-risk assessment.

### Read-only evidence commands

```powershell
kubectl --context kind-k8s-admin-ch015 get nodes
kubectl --context kind-k8s-admin-ch015 -n ch015 get deployment,replicaset,pod,service -o wide
kubectl --context kind-k8s-admin-ch015 -n ch015 get endpointslices -l kubernetes.io/service-name=web
kubectl --context kind-k8s-admin-ch015 -n ch015 describe resourcequota training-quota
kubectl --context kind-k8s-admin-ch015 -n ch015 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch015 -n ch015 logs deployment/web --tail=100 --timestamps
```

Do not collect Secret contents or raw kubeconfig credentials in the acceptance report.

## 15. Operational handover template

Create a local `CH015-ACCEPTANCE-REPORT.md` after executing the lab:

```markdown
# Chapter 015 — Kubernetes Resource Administration Acceptance

Date/time:
Operator:
Reviewer:
Cluster/context: kind-k8s-admin-ch015
Namespace: ch015
Kubernetes server version:

| Test ID | Status (Pass/Fail/Blocked) | Evidence | Notes |
|---|---|---|---|
| A01 | | | |
| A02 | | | |
| A03 | | | |
| A04 | | | |
| A05 | | | |
| A06 | | | |
| A07 | | | |
| A08 | | | |
| A09 | | | |
| A10 | | | |
| A11 | | | |
| A12 | | | |

Incidents reproduced:
Root cause(s):
Remediation(s):
Rollback / recovery:
Risks and open issues:
Cleanup confirmation:
Final acceptance decision:
```

**Acceptance rule:** A test passes only with observed evidence. Mark unexecuted steps **Blocked/Not Run**, never Pass. If any required test fails, record the failure and remediation before declaring the project validated.

## 16. Production hardening checklist

- Use explicit contexts, namespace scoping, and least-privilege RBAC.
- Standardize labels for application identity, ownership, environment, and FinOps.
- Treat Service selectors and Deployment selectors as routing/control-plane contracts.
- Review quotas and defaults against real workload requirements.
- Use server-side dry runs and diffs before changes.
- Track field ownership when GitOps/controllers share resource management.
- Prefer controlled rollouts over manual Pod deletion.
- Inspect owner references and deletion propagation before destructive actions.
- Avoid forced deletion or finalizer removal without cleanup verification.
- Audit changes and preserve sanitized incident evidence.

## 17. Cleanup and rollback

Verify the exact disposable cluster:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch015 get nodes
```

After confirming all synthetic finalizers have been cleared, delete the training namespace and cluster:

```powershell
kubectl --context kind-k8s-admin-ch015 delete namespace ch015
kind delete cluster --name k8s-admin-ch015
kind get clusters
Remove-Item .\governance.yaml, .\application.yaml, .\client.yaml, .\oversized.yaml, .\finalizer.yaml
```

**Warning:** Namespace and cluster deletion are destructive. Use only the disposable lab environment and retain your acceptance report before cleanup.

## 18. Final acceptance checklist

- [ ] API discovery and resource scope verified.
- [ ] Namespace, labels, annotations, quota, and limits created.
- [ ] Two-replica application deployed and healthy.
- [ ] Service DNS, endpoints, and HTTP verified.
- [ ] Selector mismatch reproduced and recovered.
- [ ] Quota admission rejection reproduced.
- [ ] Advanced kubectl filtering, diff, and managed fields inspected.
- [ ] Deployment rollout and rollback verified.
- [ ] Owner references and Pod reconciliation verified.
- [ ] Synthetic finalizer blocked and then completed deletion.
- [ ] Evidence report written with pass/fail outcomes.
- [ ] Disposable cluster and resources cleaned up.

## 19. Knowledge check

1. Why is namespace isolation insufficient for multi-tenancy security?
2. What is the operational impact of a Service selector mismatch?
3. How do ResourceQuota and LimitRange differ?
4. Why can `kubectl diff` exit with code 1?
5. What is the difference between `resourceVersion` and UID?
6. How is ReplicaSet reconciliation different from garbage collection?
7. Why can a deleted resource remain visible with deletionTimestamp?
8. What risks arise from manually removing a real finalizer?
9. What evidence should be preserved before production remediation?
10. What is required to promote a chapter from Draft to Lab Validated?

## 20. Part 03 writing milestone and next chapter

| Chapter | Title | Writing status |
|---|---|---|
| 011 | Kubernetes API and API Resources | Draft |
| 012 | Namespaces, Labels and Annotations | Draft |
| 013 | kubectl Advanced Administration | Draft |
| 014 | Resource Lifecycle, Finalizers and Garbage Collection | Draft |
| 015 | Resource Management and Administration Lab | Draft |

**Part 03 writing milestone reached:** all five chapter drafts are written. **Execution, technical review, and acceptance evidence are pending.** Do not mark Part 03 fully validated or complete until those steps pass.

**Next:** Chapter 016 — Pod Architecture and Lifecycle.
