# Chapter 019 — StatefulSets, DaemonSets, Jobs and CronJobs

**Track:** Kubernetes Administration | **Part 04:** Pods and Workload Controllers | **Level:** Intermediate–Advanced | **Status:** Draft — hands-on validation pending

## 1. Learning objectives

By completing this chapter, you will be able to:

1. Choose between Deployments, StatefulSets, DaemonSets, Jobs, and CronJobs based on workload semantics.
2. Explain StatefulSet identity, ordered operations, stable storage claims, and headless Service discovery.
3. Diagnose DaemonSet node eligibility, scheduling constraints, and agent coverage.
4. Design bounded batch execution with Job completions, parallelism, backoff, and deadlines.
5. Configure CronJob scheduling, time zones, concurrency policy, history limits, and missed-run behavior.
6. Investigate common failure modes without losing persistent data or duplicating non-idempotent work.
7. Complete disposable kind labs with operational evidence, cleanup, and acceptance criteria.

## 2. Workload controller decision guide

| Controller | Desired behavior | Common use cases | Key risk |
|---|---|---|---|
| Deployment | Replaceable replicas, rolling updates | Web/API services | Assumes replicas are interchangeable |
| StatefulSet | Stable Pod identity, ordered rollout, stable PVCs | Databases, brokers, clustered systems | Persistent data and quorum implications |
| DaemonSet | Pod on each eligible node | Logging, metrics, CNI/CSI agents | Node coverage gaps and privileged agents |
| Job | Run finite work to completion | Migrations, exports, batch processing | Duplicate execution or partial completion |
| CronJob | Create Jobs on a schedule | Periodic maintenance, backups | Overlap, missed runs, timezone errors |

**Operational principle:** The controller ensures Kubernetes execution semantics, not application correctness. StatefulSet does not automatically provide database replication, backup, leader election, or failover. CronJob does not provide exactly-once execution.

## 3. StatefulSet architecture

```text
Headless Service: database.ch019.svc.cluster.local
                |
         StatefulSet database
                |
     +----------+----------+
     |          |          |
 database-0  database-1  database-2
     |          |          |
 data-db-0   data-db-1   data-db-2
   PVC          PVC         PVC
```

StatefulSet Pods have stable ordinal identities such as `database-0` and `database-1`. A headless Service (`clusterIP: None`) provides DNS records for stable discovery when the appropriate readiness and DNS conditions are met. A StatefulSet's `serviceName` identifies the governing Service.

### Key fields

- `replicas`: desired number of Pods.
- `selector` and `template`: workload identity and Pod specification.
- `serviceName`: governing Service name.
- `volumeClaimTemplates`: per-Pod persistent volume claims.
- `podManagementPolicy: OrderedReady|Parallel`: controls ordering for scaling operations; Parallel does not change update ordering semantics.
- `updateStrategy: RollingUpdate|OnDelete`: controls replacement of Pods after template changes.
- `persistentVolumeClaimRetentionPolicy`: configures PVC retention/deletion behavior for scale-down and StatefulSet deletion on supported clusters.

### StatefulSet operational hazards

- Scaling down does not imply safe data removal or cluster rebalancing.
- Deleting a Pod does not delete its PVC by default.
- PVC retention policy may be configured to delete PVCs; verify the actual policy and owner references before scaling or deleting.
- An unhealthy Pod can block an ordered rollout.
- A forced Pod deletion on an unreachable node can create split-brain risks if the original process still accesses storage.
- Stable identity is not equivalent to highly available storage or application-level quorum.

For PostgreSQL, MongoDB, Kafka, and Elasticsearch, follow operator-specific procedures for membership changes and failover.

## 4. StatefulSet rollout and failure recovery

With the default OrderedReady management, Pods are created in ordinal order, and each preceding Pod must become Ready before the next is started. Rolling updates generally proceed from the highest ordinal toward the lowest.

An important recovery trap: when a StatefulSet RollingUpdate becomes stuck because a new template never becomes Ready, reverting the template alone may not be sufficient. Depending on the failure state, you may need to manually delete Pods created with the bad template **after** restoring the known-good template, following the documented StatefulSet forced rollback process. Do not force-delete stateful production Pods without quorum and storage safety checks.

### Inspect stateful resources

```powershell
kubectl get statefulsets
kubectl describe statefulset database
kubectl get pods -l app=database -o wide
kubectl get pvc
kubectl get events --sort-by=.lastTimestamp
```

## 5. DaemonSet architecture and placement

A DaemonSet ensures a Pod runs on each **eligible** node. Eligibility depends on selectors, affinity, taints/tolerations, and controller/scheduler behavior. It is not a guarantee that every cluster node always has a Ready DaemonSet Pod.

```text
DaemonSet: node-agent
       |
       +-- eligible node A --> node-agent Pod
       +-- eligible node B --> node-agent Pod
       +-- ineligible node C --> no Pod
```

Common DaemonSets include log forwarders, metrics collectors, node security agents, and networking/storage plugins. Agents may need host mounts or privileges; use least privilege and review their security posture carefully.

### Important status fields

- `desiredNumberScheduled`: eligible nodes where a Pod should run.
- `currentNumberScheduled`: nodes currently running at least one DaemonSet Pod.
- `numberReady`: nodes with Ready DaemonSet Pods.
- `numberAvailable`: nodes with Available DaemonSet Pods.
- `numberMisscheduled`: nodes running DaemonSet Pods that should not run them.

Node taints and DaemonSet tolerations matter during maintenance. DaemonSets are generally ignored by `kubectl drain` only when `--ignore-daemonsets` is provided; that flag does not delete those Pods.

## 6. Job architecture and execution guarantees

A Job manages one or more Pods until the specified completion criteria are met.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: sample
spec:
  completions: 3
  parallelism: 2
  backoffLimit: 3
  activeDeadlineSeconds: 180
  ttlSecondsAfterFinished: 300
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: worker
          image: busybox:1.36.1
          command: ["sh", "-c", "echo batch-task"]
```

- `completions`: successful Pod completions required for a non-indexed Job.
- `parallelism`: maximum desired concurrent active Pods.
- `backoffLimit`: failed attempts before the Job is considered failed (subject to Job behavior).
- `activeDeadlineSeconds`: limits overall Job active time.
- `ttlSecondsAfterFinished`: requests cleanup of a completed/failed Job and dependents after TTL, when the TTL controller is active.
- `completionMode: Indexed`: assigns completion indexes for workloads that need stable per-task identities.

**At-least-once risk:** Even with `parallelism: 1` and `completions: 1`, duplicate Pod starts or overlapping execution can occur under failure conditions. Make external writes idempotent, use transaction keys or leases when appropriate, and do not assume exactly-once semantics.

## 7. CronJob scheduling and policy

A CronJob creates Jobs according to a cron schedule interpreted in the configured time zone.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-report
spec:
  schedule: "0 2 * * *"
  timeZone: "Etc/UTC"
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 600
  successfulJobsHistoryLimit: 2
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: report
              image: busybox:1.36.1
              command: ["sh", "-c", "date; echo report"]
```

### Concurrency policies

| Policy | Behavior | Tradeoff |
|---|---|---|
| Allow | Overlapping Jobs allowed | Requires idempotency/concurrency safety |
| Forbid | Skip a new run while previous Job remains active | Can miss schedules |
| Replace | Replace the currently running Job with a new one | May interrupt work; external effects may persist |

These policies apply to Jobs created by the **same CronJob**; they do not coordinate different CronJobs or external systems.

### Scheduling details

- `timeZone` uses an IANA time-zone name; `Etc/UTC` is predictable for labs.
- `startingDeadlineSeconds` bounds how late a missed schedule may be started.
- `suspend: true` prevents future schedules while suspended; it does not stop already running Jobs.
- History limits control retained completed/failed Jobs, not necessarily all data they created.
- The controller evaluates schedules periodically; very short starting deadlines can cause missed runs.
- Daylight-saving time and missed schedule behavior require explicit production testing.
- Backups and migrations must not rely solely on CronJob scheduling as a correctness guarantee.

## 8. Lab prerequisites and safety gate

**Environment:** Windows PowerShell, Docker Desktop, kind, kubectl. All labs run only in a disposable cluster.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch019 | Out-Null
Set-Location .\k8s-ch019
kind create cluster --name k8s-admin-ch019 --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch019 get nodes -o wide
kubectl --context kind-k8s-admin-ch019 get storageclasses
```

**Expected:** context `kind-k8s-admin-ch019`, node Ready. A default StorageClass may be present in kind, but verify it before running PVC tests.

**Stop condition:** Do not continue if the active context differs. The labs create and delete workloads, Jobs, and PVCs; never copy these commands into shared or production environments.

## 9. Lab A — StatefulSet identity and headless Service

This first lab uses `emptyDir` to demonstrate identity without relying on storage provisioning. **emptyDir is ephemeral and not persistent storage.**

### Step A1 — Create namespace, headless Service and StatefulSet

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch019
---
apiVersion: v1
kind: Service
metadata:
  name: identity
  namespace: ch019
spec:
  clusterIP: None
  selector:
    app: identity
  ports:
    - name: http
      port: 80
      targetPort: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: identity
  namespace: ch019
spec:
  serviceName: identity
  replicas: 2
  selector:
    matchLabels:
      app: identity
  template:
    metadata:
      labels:
        app: identity
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
          volumeMounts:
            - name: scratch
              mountPath: /scratch
      volumes:
        - name: scratch
          emptyDir: {}
'@ | Set-Content -Encoding ascii .\stateful-identity.yaml

kubectl --context kind-k8s-admin-ch019 apply --dry-run=server -f .\stateful-identity.yaml
kubectl --context kind-k8s-admin-ch019 apply -f .\stateful-identity.yaml
kubectl --context kind-k8s-admin-ch019 -n ch019 rollout status statefulset/identity --timeout=180s
kubectl --context kind-k8s-admin-ch019 -n ch019 get pods -l app=identity -o wide
kubectl --context kind-k8s-admin-ch019 -n ch019 get service identity -o yaml
```

**Expected:** `identity-0` and `identity-1` are Ready, with stable ordinal names.

### Step A2 — Inspect DNS and ownership

```powershell
kubectl --context kind-k8s-admin-ch019 -n ch019 get pod identity-0 -o jsonpath='{.metadata.ownerReferences[0].name}'
kubectl --context kind-k8s-admin-ch019 -n ch019 get pod identity-1 -o jsonpath='{.metadata.name}'
kubectl --context kind-k8s-admin-ch019 -n ch019 get endpointslices -l kubernetes.io/service-name=identity
```

**Expected:** both Pods are owned by StatefulSet `identity`; EndpointSlices expose ready endpoints for the headless Service.

### Step A3 — Delete a Pod and observe stable name, new UID

```powershell
$oldUid = kubectl --context kind-k8s-admin-ch019 -n ch019 get pod identity-1 -o jsonpath='{.metadata.uid}'
kubectl --context kind-k8s-admin-ch019 -n ch019 delete pod identity-1
kubectl --context kind-k8s-admin-ch019 -n ch019 rollout status statefulset/identity --timeout=180s
$newUid = kubectl --context kind-k8s-admin-ch019 -n ch019 get pod identity-1 -o jsonpath='{.metadata.uid}'
Write-Output "old=$oldUid new=$newUid"
```

**Expected:** name remains `identity-1`, UID changes. Its `emptyDir` content would not survive replacement.

## 10. Lab B — StatefulSet persistent volume claims

**Compatibility gate:** Run only when a working default StorageClass/provisioner exists. If no default StorageClass exists, mark this lab **Blocked** and do not guess a provider-specific storage class.

### Step B1 — Create a PVC-backed StatefulSet

```powershell
@'
apiVersion: v1
kind: Service
metadata:
  name: persistent
  namespace: ch019
spec:
  clusterIP: None
  selector:
    app: persistent
  ports:
    - name: http
      port: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: persistent
  namespace: ch019
spec:
  serviceName: persistent
  replicas: 1
  selector:
    matchLabels:
      app: persistent
  template:
    metadata:
      labels:
        app: persistent
    spec:
      containers:
        - name: app
          image: busybox:1.36.1
          command: ["sh", "-c", "sleep 3600"]
          volumeMounts:
            - name: data
              mountPath: /data
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 100Mi
'@ | Set-Content -Encoding ascii .\stateful-pvc.yaml

kubectl --context kind-k8s-admin-ch019 apply -f .\stateful-pvc.yaml
kubectl --context kind-k8s-admin-ch019 -n ch019 rollout status statefulset/persistent --timeout=180s
kubectl --context kind-k8s-admin-ch019 -n ch019 get pvc
```

**Expected:** PVC `data-persistent-0` is Bound and Pod `persistent-0` Ready.

### Step B2 — Write data, replace Pod, verify persistence

```powershell
kubectl --context kind-k8s-admin-ch019 -n ch019 exec persistent-0 -- sh -c 'echo persistent-data > /data/check.txt'
kubectl --context kind-k8s-admin-ch019 -n ch019 delete pod persistent-0
kubectl --context kind-k8s-admin-ch019 -n ch019 rollout status statefulset/persistent --timeout=180s
kubectl --context kind-k8s-admin-ch019 -n ch019 exec persistent-0 -- cat /data/check.txt
kubectl --context kind-k8s-admin-ch019 -n ch019 get pvc data-persistent-0
```

**Expected:** `persistent-data` survives Pod replacement because the PVC is reused. This does not prove storage availability after node loss or provide a backup.

### Step B3 — Inspect retention and cleanup deliberately

```powershell
kubectl --context kind-k8s-admin-ch019 -n ch019 get statefulset persistent -o yaml
kubectl --context kind-k8s-admin-ch019 -n ch019 get pvc data-persistent-0 -o yaml
```

**Safety:** Deleting a StatefulSet does not necessarily delete PVCs. The final cleanup section explicitly deletes the disposable PVC **only after** removing the StatefulSet and verifying the context.

## 11. Lab C — DaemonSet coverage and node eligibility

### Step C1 — Deploy a minimal agent

```powershell
@'
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-agent
  namespace: ch019
spec:
  selector:
    matchLabels:
      app: node-agent
  template:
    metadata:
      labels:
        app: node-agent
    spec:
      containers:
        - name: agent
          image: busybox:1.36.1
          command: ["sh", "-c", "while true; do echo agent-alive; sleep 30; done"]
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
'@ | Set-Content -Encoding ascii .\daemonset.yaml

kubectl --context kind-k8s-admin-ch019 apply -f .\daemonset.yaml
kubectl --context kind-k8s-admin-ch019 -n ch019 rollout status daemonset/node-agent --timeout=180s
kubectl --context kind-k8s-admin-ch019 -n ch019 get daemonset node-agent -o wide
kubectl --context kind-k8s-admin-ch019 -n ch019 get pods -l app=node-agent -o wide
```

**Expected:** agent Pods on eligible nodes. A one-node kind cluster generally has one eligible node, but check actual `DESIRED`, `CURRENT`, and `READY` counts.

### Step C2 — Inspect scheduling

```powershell
kubectl --context kind-k8s-admin-ch019 -n ch019 describe daemonset node-agent
kubectl --context kind-k8s-admin-ch019 get nodes --show-labels
kubectl --context kind-k8s-admin-ch019 -n ch019 logs daemonset/node-agent --tail=20
```

**Expected:** logs show `agent-alive`; desired coverage matches eligible node count. Do not infer full cluster coverage from a one-node lab.

## 12. Lab D — Job completions, parallelism and TTL

### Step D1 — Run a bounded Job

```powershell
@'
apiVersion: batch/v1
kind: Job
metadata:
  name: batch-demo
  namespace: ch019
spec:
  completions: 3
  parallelism: 2
  backoffLimit: 2
  activeDeadlineSeconds: 180
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: task
          image: busybox:1.36.1
          command: ["sh", "-c", "echo started; sleep 3; echo completed"]
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
'@ | Set-Content -Encoding ascii .\job.yaml

kubectl --context kind-k8s-admin-ch019 apply -f .\job.yaml
kubectl --context kind-k8s-admin-ch019 -n ch019 wait --for=condition=complete job/batch-demo --timeout=180s
kubectl --context kind-k8s-admin-ch019 -n ch019 get job batch-demo
kubectl --context kind-k8s-admin-ch019 -n ch019 get pods -l batch.kubernetes.io/job-name=batch-demo
kubectl --context kind-k8s-admin-ch019 -n ch019 logs job/batch-demo --tail=20
```

**Expected:** Job completes 3/3. The `kubectl logs job/...` command may display logs from only one matching Pod; inspect each Pod when collecting complete batch evidence.

### Step D2 — Inspect status

```powershell
kubectl --context kind-k8s-admin-ch019 -n ch019 get job batch-demo -o jsonpath='{.status.succeeded}'
kubectl --context kind-k8s-admin-ch019 -n ch019 describe job batch-demo
```

**Expected:** succeeded count is 3. TTL cleanup may remove the Job later; do not depend on it for immediate lab cleanup.

## 13. Lab E — Job failure and controlled retry

```powershell
@'
apiVersion: batch/v1
kind: Job
metadata:
  name: failed-batch
  namespace: ch019
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 90
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: task
          image: busybox:1.36.1
          command: ["sh", "-c", "echo intentional-failure; exit 2"]
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
'@ | Set-Content -Encoding ascii .\job-failure.yaml

kubectl --context kind-k8s-admin-ch019 apply -f .\job-failure.yaml
kubectl --context kind-k8s-admin-ch019 -n ch019 get jobs,pods
kubectl --context kind-k8s-admin-ch019 -n ch019 describe job failed-batch
kubectl --context kind-k8s-admin-ch019 -n ch019 get pods -l batch.kubernetes.io/job-name=failed-batch
```

**Expected:** failed Pods with exit code 2; after retries/backoff the Job reports failure. Timing varies. Inspect failed Pod logs individually; do not assume `kubectl logs job/failed-batch` selects every failed attempt.

**Recovery pattern:** Correct the Job template and create a **new** Job with a new name; do not assume a failed Job's Pod template is mutable. Ensure external writes are safe to retry before rerunning real batch work.

## 14. Lab F — CronJob schedule, history and manual trigger

### Step F1 — Create a safe UTC CronJob

```powershell
@'
apiVersion: batch/v1
kind: CronJob
metadata:
  name: periodic-report
  namespace: ch019
spec:
  schedule: "*/5 * * * *"
  timeZone: "Etc/UTC"
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 120
  successfulJobsHistoryLimit: 2
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 1
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: report
              image: busybox:1.36.1
              command: ["sh", "-c", "date -u; echo periodic-report"]
              resources:
                requests:
                  cpu: 10m
                  memory: 16Mi
'@ | Set-Content -Encoding ascii .\cronjob.yaml

kubectl --context kind-k8s-admin-ch019 apply -f .\cronjob.yaml
kubectl --context kind-k8s-admin-ch019 -n ch019 get cronjob periodic-report
kubectl --context kind-k8s-admin-ch019 -n ch019 describe cronjob periodic-report
```

**Expected:** CronJob is present and not suspended. The next scheduled run can be several minutes away; do not wait for it to prove the Job template works.

### Step F2 — Trigger a Job manually

```powershell
kubectl --context kind-k8s-admin-ch019 -n ch019 create job --from=cronjob/periodic-report manual-report
kubectl --context kind-k8s-admin-ch019 -n ch019 wait --for=condition=complete job/manual-report --timeout=180s
kubectl --context kind-k8s-admin-ch019 -n ch019 logs job/manual-report
kubectl --context kind-k8s-admin-ch019 -n ch019 get jobs
```

**Expected:** manually created Job completes and prints UTC time and `periodic-report`. A manual Job does **not** validate the CronJob controller's scheduled trigger or concurrency policy.

### Step F3 — Suspend future schedules

```powershell
kubectl --context kind-k8s-admin-ch019 -n ch019 patch cronjob periodic-report --type=merge -p '{"spec":{"suspend":true}}'
kubectl --context kind-k8s-admin-ch019 -n ch019 get cronjob periodic-report
```

**Expected:** `SUSPEND=True`; already running Jobs are not automatically stopped.

## 15. Production troubleshooting matrix

| Symptom | Evidence | Likely cause |
|---|---|---|
| StatefulSet Pod Pending | PVC, events, node and volume constraints | Storage provisioner, attachment, scheduling |
| StatefulSet rollout stuck | Pod readiness, ControllerRevision, status | Bad template, ordered update blockage |
| Stable Pod name but data missing | PVC UID, mounts, retention policy | Wrong volume or ephemeral storage |
| DaemonSet DESIRED less than node count | Node selectors, affinity, taints | Ineligible nodes |
| DaemonSet Pods unready | Agent logs, host dependencies | Runtime/permissions/configuration |
| Job stays Active | Pod logs, deadlines, external service | Hung process or dependency |
| Job fails repeatedly | Failed Pod logs, exit codes | Application error or retry policy |
| Job duplicates external writes | Retries, logs, transaction IDs | Non-idempotent execution |
| CronJob not running | schedule, suspend, deadline, controller events | Missed schedule or configuration |
| CronJobs overlap | concurrency policy, active Jobs | Allow policy or separate CronJobs |
| Backup Job reports success but restore fails | Artifact checks, restore test | Missing validation of backup integrity |

## 16. SRE/DBRE operational runbooks

### StatefulSet scale or restart

1. Confirm workload owner/operator, cluster membership, quorum, backup state, and data replication health.
2. Inspect StatefulSet strategy, ordinal identities, PVC names, VolumeAttachments, and readiness.
3. Verify maintenance window and application-level failover procedure.
4. Change one thing at a time; watch membership and storage recovery.
5. Never force-delete a database Pod solely to clear `Terminating`.
6. Validate application consistency, lag, and read/write service after recovery.

### DaemonSet coverage incident

1. Compare eligible nodes with `desiredNumberScheduled` and `numberReady`.
2. Check node labels, taints, tolerations, affinity, resource pressure and admission.
3. Inspect failing agent logs and host dependencies.
4. Restore the agent or scheduling policy through reviewed manifests.
5. Confirm per-node coverage and telemetry ingestion, not only Pod status.

### Job/CronJob missed or duplicate execution

1. Capture CronJob schedule, timezone, suspend flag, lastScheduleTime and Jobs.
2. Inspect concurrency policy, deadlines, Job failures, and controller events.
3. Determine whether external side effects occurred before retry.
4. Re-run only with idempotency or explicit business approval.
5. Verify final output, not merely Job completion.
6. Document whether missed scheduled work must be backfilled.

## 17. Production best practices

- Use StatefulSets only when stable identity/storage semantics are needed; prefer a proven operator for complex databases.
- Verify PVC retention, backup, restore, storage topology and recovery before stateful changes.
- Keep DaemonSet agents minimal, least-privileged, and observable.
- Use resource requests/limits and node eligibility rules for critical agents.
- Bound Jobs with deadlines and retry limits appropriate to the business task.
- Design idempotent Job execution and unique external transaction identifiers.
- Use explicit CronJob time zones, overlap policies and history limits.
- Alert on missed schedules, failed Jobs, overdue work and absent DaemonSet coverage.
- Test restores for backup CronJobs; a successful exit code is not proof of recoverability.
- Treat Kubernetes controller health as one signal among application-level correctness and SLOs.

## 18. Cleanup and rollback

**Verify the disposable context first:**

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch019 get nodes
```

Stop the CronJob and remove stateful workloads before deleting disposable PVCs:

```powershell
kubectl --context kind-k8s-admin-ch019 -n ch019 patch cronjob periodic-report --type=merge -p '{"spec":{"suspend":true}}'
kubectl --context kind-k8s-admin-ch019 -n ch019 delete statefulset persistent --wait=true
kubectl --context kind-k8s-admin-ch019 -n ch019 get pvc
kubectl --context kind-k8s-admin-ch019 -n ch019 delete pvc data-persistent-0
kubectl --context kind-k8s-admin-ch019 delete namespace ch019
kind delete cluster --name k8s-admin-ch019
kind get clusters
Remove-Item .\stateful-identity.yaml, .\stateful-pvc.yaml, .\daemonset.yaml, .\job.yaml, .\job-failure.yaml, .\cronjob.yaml -ErrorAction SilentlyContinue
```

**Destructive warning:** PVC deletion destroys the disposable test data and may trigger underlying volume deletion depending on reclaim policy. Do not run these commands against any real database or shared cluster.

## 19. Acceptance checklist

- [ ] Created kind cluster and verified context.
- [ ] Created StatefulSet with stable ordinal names and headless Service.
- [ ] Deleted and recreated a StatefulSet Pod, confirming same name and new UID.
- [ ] Verified persistent data survives replacement on a working PVC-backed StatefulSet, or recorded a storage compatibility block.
- [ ] Deployed DaemonSet and inspected eligible-node coverage.
- [ ] Completed Job with 3 successful completions and parallelism 2.
- [ ] Reproduced a failed Job and inspected retry/failure evidence.
- [ ] Created UTC CronJob with Forbid concurrency and history limits.
- [ ] Manually triggered a Job from CronJob and confirmed output.
- [ ] Suspended future CronJob schedules.
- [ ] Captured sanitized evidence and failure/recovery notes.
- [ ] Cleaned up disposable namespace, PVC and cluster.

## 20. Knowledge check

1. What guarantees does StatefulSet provide, and what does it not provide?
2. Why can deleting a StatefulSet Pod be risky for a database cluster?
3. What is the relationship between `volumeClaimTemplates` and per-Pod PVCs?
4. How do DaemonSet node eligibility and desiredNumberScheduled differ from total node count?
5. Why is a Job not an exactly-once execution mechanism?
6. What are the tradeoffs between CronJob Allow, Forbid and Replace?
7. Why does a manually triggered Job not prove the CronJob schedule works?
8. What happens when a CronJob is suspended while Jobs are active?
9. Why must backup Jobs be validated with restore tests?
10. What evidence is required before re-running a failed migration or data export Job?

## 21. Status and next chapter

**Draft published.** Runtime lab execution and technical review are pending; do not mark validated without observed acceptance evidence.

**Next:** Chapter 020 — Workload Administration and Recovery Lab.
