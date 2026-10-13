# Chapter 053 — PodDisruptionBudgets and Graceful Shutdown

**Track:** Kubernetes Administration · **Part 11 — High Availability and Disaster Recovery**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers  
**Prerequisites:** Chapters 017–020, 046–047, 051–052; kubectl and Windows PowerShell; isolated multi-node lab cluster for eviction tests

## 1. Production scenario

During a planned worker-node upgrade, an application Deployment has three replicas, but only two are Ready. Its PodDisruptionBudget (PDB) requires at least two available replicas. A drain stalls because another eviction would violate the budget. Separately, a stateful application has a 30-second termination grace period but needs time to relinquish leadership and flush writes.

**Goal:** design and test disruption budgets, graceful termination, readiness and safe maintenance so that node operations do not turn expected voluntary disruption into an avoidable outage.

### Learning objectives

1. Distinguish voluntary and involuntary disruptions.
2. Configure `minAvailable` and `maxUnavailable` PDBs and understand selector scope.
3. Read PDB `disruptionsAllowed`, `currentHealthy` and `desiredHealthy`.
4. Explain the Eviction API, drain behavior and when PDBs do not apply.
5. Understand SIGTERM, `preStop`, termination grace, readiness and endpoint draining.
6. Design shutdown for HTTP services, workers and stateful applications.
7. Troubleshoot blocked drains, stuck terminating Pods and replacement scheduling.

## 2. Availability and eviction architecture

```text
Maintenance request
       |
kubectl drain NODE
       |
Eviction API -> PDB controller evaluates disruption allowance
       |                        |
   allowed                  denied (429 / retry)
       |                        |
Pod deletion begins       Restore availability / capacity
       |
Pod marked terminating
       |
EndpointSlice terminating state / endpoint readiness changes
       |
preStop hook (if configured), SIGTERM, grace countdown
       |
Application stops accepting new work, drains inflight requests
       |
Container exits cleanly or is killed at grace deadline
       |
Controller ensures replacement Pods become Ready
```

**Important timing nuance:** the termination grace countdown starts when the Pod begins terminating; `preStop` consumes part of that budget. Endpoint updates and external load balancer propagation are asynchronous. A readiness probe alone does not guarantee zero dropped connections.

## 3. PDB semantics and limitations

| Feature | Meaning | Operational caution |
|---|---|---|
| `minAvailable: 2` | At least two matching Pods should remain healthy during allowed evictions | May block maintenance if only two are Ready |
| `maxUnavailable: 1` | At most one disruption relative to expected replicas | Requires correct controller and replica expectations |
| `disruptionsAllowed` | Current permitted voluntary evictions | Can change rapidly; check immediately before drain |
| `unhealthyPodEvictionPolicy` | How unhealthy Pods are treated during eviction | `AlwaysAllow` can help remove already unhealthy Pods; review version/support |
| Eviction API | Checks PDB before deleting eligible Pod | Direct delete and some controllers do not honor PDB the same way |
| Involuntary failure | Node crash, hardware loss, zone failure | PDB cannot prevent the failure |
| Deployment rolling update | Controlled by Deployment rollout strategy | PDB does not directly limit Deployment controller's rollout deletions |

A PDB does not create capacity or guarantee replicas land in separate zones. For a single-replica critical workload, `minAvailable: 1` can intentionally block voluntary eviction indefinitely; this protects availability but may make maintenance impossible without an application-specific failover or downtime plan.

## 4. Lab prerequisites and safety

Labs 1–3 and 7 are read-only or non-disruptive. Labs 4–6 require an **approved isolated test namespace**; the optional node drain must run only on an approved disposable worker after inventorying **all Pods across namespaces**.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl auth can-i create deployments -n default
kubectl auth can-i create poddisruptionbudgets.policy -n default
kubectl auth can-i create pods/eviction -n default
```

Use a multi-node cluster with sufficient headroom. Do not force-delete production Pods or bypass a PDB to finish a lab.

## 5. Lab 1 — Inventory disruption and availability risks

```powershell
kubectl get deployments -A
kubectl get statefulsets -A
kubectl get pdb -A -o wide
kubectl get pods -A -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get events -A --sort-by=.lastTimestamp
```

**Expected:** identify single replicas, PDB coverage gaps, unhealthy replicas, concentrated placement and Pending workloads.

### Assessment questions

- Which workloads have only one Ready replica?
- Does each PDB selector match the intended Pods, and only those Pods?
- Do topology constraints place replicas on different nodes/zones?
- Can surviving nodes schedule replacements?
- Are database quorum and storage attachments protected?
- Are there long-running requests or in-flight jobs requiring graceful shutdown?

## 6. Lab 2 — Create a replicated service with a PDB

Save `ch053-app.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch053
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: graceful-web
  namespace: ch053
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  selector:
    matchLabels:
      app: graceful-web
  template:
    metadata:
      labels:
        app: graceful-web
    spec:
      terminationGracePeriodSeconds: 40
      containers:
        - name: web
          image: nginx:1.27
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 5
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 5"]
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: graceful-web
  namespace: ch053
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: graceful-web
---
apiVersion: v1
kind: Service
metadata:
  name: graceful-web
  namespace: ch053
spec:
  selector:
    app: graceful-web
  ports:
    - port: 80
      targetPort: 80
```

```powershell
kubectl apply -f .\ch053-app.yaml
kubectl -n ch053 rollout status deployment/graceful-web --timeout=180s
kubectl -n ch053 get pods -o wide
kubectl -n ch053 get pdb graceful-web -o wide
kubectl -n ch053 get endpointslices -l kubernetes.io/service-name=graceful-web
```

**Expected:** three Ready Pods and normally one allowed disruption. The `sleep 5` hook is **only a timing demonstration**; production applications need an application-aware shutdown protocol, not a blind sleep.

## 7. Lab 3 — Inspect PDB calculations and endpoint readiness

```powershell
kubectl -n ch053 describe pdb graceful-web
kubectl -n ch053 get pdb graceful-web -o jsonpath='{.status.currentHealthy}'
kubectl -n ch053 get pdb graceful-web -o jsonpath='{.status.desiredHealthy}'
kubectl -n ch053 get pdb graceful-web -o jsonpath='{.status.disruptionsAllowed}'
kubectl -n ch053 get deployment graceful-web
kubectl -n ch053 get pods -o wide
```

**Expected:** `currentHealthy=3`, `desiredHealthy=2`, and `disruptionsAllowed` commonly 1 after reconciliation. If fewer than three Pods are Ready, actual values differ.

### Worked examples

| Ready replicas | minAvailable | Allowed evictions (simplified) |
|---:|---:|---:|
| 3 | 2 | 1 |
| 2 | 2 | 0 |
| 1 | 2 | 0 |

Actual PDB status also accounts for expected Pods, disruptions in progress and controller observations. Treat the live `status.disruptionsAllowed` as authoritative for the moment, not a fixed calculation from replica count alone.

## 8. Lab 4 — Rehearse a voluntary Pod eviction

**Only in the isolated `ch053` namespace.** Choose a Pod owned by the demo Deployment:

```powershell
$pod = (kubectl -n ch053 get pods -l app=graceful-web -o jsonpath='{.items[0].metadata.name}')
kubectl -n ch053 get pod $pod -o wide
kubectl -n ch053 get pdb graceful-web -o wide
```

Use a Kubernetes client or authorized API method that sends a `policy/v1` Eviction object to `/api/v1/namespaces/ch053/pods/$pod/eviction`. One PowerShell approach with `kubectl create --raw` is:

```powershell
$body = '{"apiVersion":"policy/v1","kind":"Eviction","metadata":{"name":"' + $pod + '","namespace":"ch053"}}'
$body | Set-Content -Path .\ch053-eviction.json -Encoding utf8
kubectl create --raw "/api/v1/namespaces/ch053/pods/$pod/eviction" -f .\ch053-eviction.json
kubectl -n ch053 get pods -w
```

**Expected:** eviction is accepted when PDB allows it, the Pod terminates gracefully, and the Deployment creates a replacement. If admission or PDB blocks eviction, the API can return a conflict or rate-limiting response; investigate rather than forcing deletion. The raw API endpoint and RBAC support depend on cluster configuration.

Inspect status in another terminal:

```powershell
kubectl -n ch053 get pdb graceful-web -o wide
kubectl -n ch053 get endpointslices -l kubernetes.io/service-name=graceful-web
kubectl -n ch053 rollout status deployment/graceful-web --timeout=180s
```

Do not repeatedly evict Pods without waiting for readiness and PDB allowance to recover.

## 9. Lab 5 — Test graceful termination and request draining

The lab's `preStop` hook waits five seconds before the container receives SIGTERM. In a real application, graceful shutdown should coordinate request draining and leadership/job ownership.

### Observe termination

```powershell
kubectl -n ch053 get pods -o wide
kubectl -n ch053 get events --sort-by=.lastTimestamp
kubectl -n ch053 describe deployment graceful-web
kubectl -n ch053 get endpointslices -l kubernetes.io/service-name=graceful-web -o yaml
```

**Expected:** replacement Pods become Ready, and terminating endpoints are marked accordingly when observed during the transition. EndpointSlice propagation is asynchronous, so a short-lived transition may be missed by a one-time snapshot.

### Application shutdown design

1. Mark the instance unavailable for new work through application/controller mechanisms.
2. Stop accepting new connections/jobs.
3. Allow existing requests or jobs to complete within a bounded deadline.
4. Release leases/leadership and flush durable state.
5. Exit cleanly before `terminationGracePeriodSeconds` expires.
6. Verify client retries, load balancer draining and idempotency behavior.

**Caution:** `preStop` and SIGTERM are not a substitute for correct database failover or transactional guarantees.

## 10. Lab 6 — Optional node-drain acceptance rehearsal

This lab is **optional and disruptive**. Only run on a disposable worker where **all assigned workloads** are approved for eviction.

```powershell
$node = "REPLACE_WITH_APPROVED_DISPOSABLE_WORKER"
kubectl get node $node -o wide
kubectl get pods -A --field-selector spec.nodeName=$node -o wide
kubectl get pdb -A
kubectl -n ch053 get pods -o wide
```

Verify the worker hosts a demo Pod, has enough replacement capacity elsewhere, and does not host unapproved workloads or irreplaceable local storage. Record its original schedulability.

```powershell
kubectl cordon $node
kubectl drain $node --ignore-daemonsets --timeout=5m
```

**Expected:** eligible Pods are evicted only when disruption constraints permit. Drain can fail due to unmanaged Pods, `emptyDir`, PDBs, topology or storage constraints. Do **not** automatically add `--force`, `--delete-emptydir-data` or `--disable-eviction`.

After verifying workloads and obtaining approval to return the node to service:

```powershell
kubectl -n ch053 rollout status deployment/graceful-web --timeout=180s
kubectl -n ch053 get pdb graceful-web -o wide
kubectl uncordon $node
kubectl get node $node -o wide
```

Never uncordon a node that was already intentionally cordoned before the lab.

## 11. Lab 7 — Blocked drain and stateful shutdown incident

**Scenario:** a three-replica API has only two Ready Pods under `minAvailable: 2`. A node drain is blocked. The same node hosts a database leader that needs 90 seconds to transfer leadership, but its Pod has a 30-second grace period.

### Read-only evidence

```powershell
kubectl get pdb -A -o wide
kubectl get pods -A -o wide
kubectl get statefulsets -A
kubectl get events -A --sort-by=.lastTimestamp
kubectl get nodes -o wide
```

### Required response

1. Stop drain escalation; do not bypass the PDB.
2. Identify why the third API replica is not Ready (capacity, probes, image, network or storage).
3. Restore healthy API capacity and wait for PDB allowance.
4. Confirm database leader transfer, replication health, quorum and backup state.
5. Increase grace period only through an approved workload change and validated shutdown test.
6. Consider DB-specific maintenance/failover procedures rather than relying on Kubernetes eviction alone.
7. Resume maintenance only when SLOs, PDB and data-safety checks pass.
8. Validate API request success, latency and database reads/writes after maintenance.

**Expected:** an explicit no-go decision until both application availability and stateful safety are satisfied.

## 12. Graceful shutdown mechanics and failure patterns

### Pod termination sequence

The API marks the Pod for deletion; the kubelet initiates termination. When configured, `preStop` executes and consumes grace-period time. The runtime sends SIGTERM to the container's PID 1 (or equivalent signal on the platform). If the process remains after the grace period, it can be forcibly terminated. EndpointSlice and traffic routing changes occur asynchronously.

### Common problems

| Symptom | Cause | Remediation |
|---|---|---|
| Drain waits indefinitely | PDB allowance zero | Restore healthy replicas/capacity |
| Pod remains Terminating | Slow shutdown, finalizer, volume issue | Events, app logs, finalizers |
| Requests fail during drain | Inflight requests cut off | Application drain + LB behavior |
| Database leader killed | Grace too short/no failover | DB-aware leadership handoff |
| New Pods Pending | Taints, affinity, quotas, PVCs | Scheduler events |
| PDB matches no Pods | Incorrect selector | Verify labels and namespace |
| PDB matches too many Pods | Broad selector | Narrow labels and ownership |
| Eviction bypasses protection | Direct deletion/unsafe flag | Use Eviction API and approval |
| Jobs duplicate work | Missing lease/idempotency | Safe worker shutdown protocol |

## 13. PDB policy design patterns

### Stateless API

Use at least two or three replicas, topology spread, readiness probes and a PDB aligned with SLO. Ensure enough spare capacity for maintenance. Test real traffic during eviction.

### Stateful quorum service

Base PDB on **application quorum and replication**, not only Kubernetes Pod count. For a three-voter database, a PDB may limit voluntary disruption to one Pod, but the application must verify the remaining voters are healthy before leadership handoff.

### Singleton or local-storage workload

A PDB cannot create redundancy. A singleton with `minAvailable: 1` blocks eviction by design. Schedule a planned outage or implement application-level HA/storage migration rather than bypassing the budget.

### Background worker

Implement job leasing, graceful stop-accepting-work, completion checkpointing and idempotent retries. A PDB protects Pod count but does not guarantee in-flight task correctness.

## 14. Production disruption runbook

### Before maintenance

1. Inventory workloads, controllers, PDBs, storage and node topology.
2. Confirm healthy replicas, `disruptionsAllowed` and replacement capacity.
3. Verify readiness, graceful termination and application failover behavior.
4. Establish error-rate/latency baseline, owner and abort thresholds.
5. For stateful services, confirm backups, quorum and leader transfer.

### During maintenance

1. Cordon the approved node.
2. Drain through the Eviction API; do not bypass PDBs casually.
3. Monitor terminating Pods, EndpointSlices and replacement scheduling.
4. Verify application transactions and customer-facing SLIs.
5. Stop if error budgets or data-safety gates are violated.

### After maintenance

1. Verify node health, Pod readiness, endpoints and storage.
2. Uncordon only when intended and approved.
3. Confirm application and database health.
4. Record disruption duration, PDB behavior and incident follow-ups.

## 15. Cleanup

```powershell
kubectl -n ch053 get deployment,pdb,service,pods
kubectl delete namespace ch053
Remove-Item .\ch053-eviction.json -ErrorAction SilentlyContinue
```

If the optional drain lab cordoned a node, confirm it is restored to the intended scheduling state. Do not delete or uncordon unrelated nodes as cleanup.

## 16. Acceptance checklist

- [ ] Voluntary versus involuntary disruptions explained.
- [ ] PDB selector and `minAvailable`/`maxUnavailable` understood.
- [ ] `disruptionsAllowed` and healthy replica status inspected.
- [ ] Eviction API exercised in an isolated namespace.
- [ ] Grace period, `preStop` and SIGTERM sequence understood.
- [ ] Endpoint and application request-drain behavior assessed.
- [ ] Stateful quorum and leadership handoff reviewed.
- [ ] Blocked drain incident resolved without bypassing safety.
- [ ] Optional node-drain rehearsal completed only with approval.
- [ ] Production runbook and application SLI acceptance documented.
- [ ] Actual runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 17. References

- [Disruptions and PodDisruptionBudgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Pod Lifecycle and Termination](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Container Lifecycle Hooks](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/)
- [Safely Drain a Node](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)
- [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)

**Next:** Chapter 054 — Multi-Zone Availability and Failure Domains.
