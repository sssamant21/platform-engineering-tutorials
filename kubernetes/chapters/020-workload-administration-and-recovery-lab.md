# Chapter 020 — Workload Administration and Recovery Lab

**Track:** Kubernetes Administration · **Part 04:** Pods and Workload Controllers · **Type:** Integrated capstone · **Status:** Draft — runtime execution and technical review pending

## 1. Mission and scenario

You are the on-call platform engineer for a Kubernetes application namespace. A web application has a stalled rollout, a batch workload is failing, and a node-level telemetry agent needs a coverage check. A stateful service must retain its data through a Pod replacement. Your job is to diagnose each condition, recover service without unsafe deletion, and produce a reproducible incident report.

This capstone integrates Chapters **016–019**: Pod architecture and lifecycle; init containers, sidecars and probes; Deployments, ReplicaSets and rollouts; StatefulSets, DaemonSets, Jobs and CronJobs.

**Important:** This lab intentionally introduces faults. Run it **only** on the dedicated disposable kind cluster defined below. No lab in this chapter is a substitute for a production database recovery drill.

## 2. Outcomes

You should be able to:

1. Verify cluster/context safety, workload inventory, owner references and Pod lifecycle state.
2. Establish a baseline of Deployment replicas, readiness, Service EndpointSlices and request success.
3. Reproduce and recover a stalled rolling update without destroying healthy endpoints.
4. Diagnose an init-container failure and a liveness-induced restart.
5. Distinguish a standalone Pod from a controller-managed Pod during replacement.
6. Validate StatefulSet ordinal identity and persistence across Pod recreation.
7. Evaluate DaemonSet coverage on eligible nodes.
8. Diagnose a failed Job, rerun a corrected idempotent batch task, and manage CronJob scheduling.
9. Preserve evidence, document incident timeline and apply explicit acceptance criteria.

## 3. Reference architecture

```text
Windows PowerShell + kubectl
           |
       kind API server
           |
      Namespace ch020
           |
           +-- Deployment/web (3 replicas) -> ReplicaSets -> Pods
           |            | readiness/startup probes
           |            +-- Service/web -> EndpointSlices
           |
           +-- Pod/client (HTTP/DNS test)
           +-- Pod/init-failure (deliberately failing init)
           +-- Pod/liveness-failure (deliberately bad probe)
           +-- StatefulSet/stateful (1 replica)
           |            +-- PVC data-stateful-0 (when storage available)
           +-- DaemonSet/node-agent
           +-- Job/batch-failure -> Job/batch-recovered
           +-- CronJob/periodic-check
```

The cluster is intentionally small. It does not test multi-zone HA, production CSI recovery, cross-node quorum, autoscaling or security multi-tenancy.

## 4. Prerequisites and safety gate

**Required:** Windows PowerShell, Docker Desktop, kind, kubectl, access to pull `nginx:stable` and `busybox:1.36.1`.

```powershell
docker version
kind version
kubectl version --client
New-Item -ItemType Directory -Force .\k8s-ch020 | Out-Null
Set-Location .\k8s-ch020
kind create cluster --name k8s-admin-ch020 --wait 180s
kubectl config current-context
kubectl --context kind-k8s-admin-ch020 get nodes -o wide
kubectl --context kind-k8s-admin-ch020 get storageclasses
```

**Expected:** current context is `kind-k8s-admin-ch020`; node Ready. Verify the exact context before continuing. All mutation commands explicitly include `--context kind-k8s-admin-ch020`.

**Stop conditions:** Wrong context, shared cluster, unexpected preexisting workloads, insufficient Docker capacity, or unavailable container images. Record a Blocked lab rather than attempting production-like workarounds.

## 5. Acceptance matrix

| ID | Test | Expected evidence |
|---|---|---|
| A01 | Isolation | Correct disposable context and Ready node |
| A02 | Baseline | 3/3 Deployment Ready; three ready endpoints |
| A03 | Application access | In-cluster HTTP to Service succeeds |
| A04 | Failed rollout | New revision unready, old endpoints remain available |
| A05 | Rollback | 3/3 Ready and HTTP restored/maintained |
| A06 | Init failure | Init container fails; main container does not start |
| A07 | Init recovery | Recreated Pod becomes Ready |
| A08 | Liveness failure | Container restartCount increases |
| A09 | Pod reconciliation | Managed Pod replaced with new UID |
| A10 | Stateful identity | Ordinal name stable; UID changes after recreation |
| A11 | Stateful persistence | Data survives replacement, or explicit storage block |
| A12 | DaemonSet coverage | Desired and Ready match eligible nodes |
| A13 | Failed batch | Failure reason, exit code and retries captured |
| A14 | Batch recovery | Corrected new Job completes and output verified |
| A15 | CronJob | Manual trigger succeeds; schedule and suspend recorded |
| A16 | Handover | Evidence, timeline, remediation and cleanup documented |

An acceptance item passes only after observed execution. A blocked optional PVC test must be documented, not marked passed. **All mandatory tests must pass for full lab acceptance.**

## 6. Phase 1 — Establish the application baseline

### 6.1 Create the namespace and application

```powershell
@'
apiVersion: v1
kind: Namespace
metadata:
  name: ch020
  labels:
    environment: lab
    team: platform
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ch020
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
            - name: http
              containerPort: 80
          startupProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 3
            failureThreshold: 20
          readinessProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 3
            failureThreshold: 2
          livenessProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 10
            failureThreshold: 3
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
  namespace: ch020
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: http
'@ | Set-Content -Encoding ascii .\baseline.yaml

kubectl --context kind-k8s-admin-ch020 apply --dry-run=server -f .\baseline.yaml
kubectl --context kind-k8s-admin-ch020 apply -f .\baseline.yaml
kubectl --context kind-k8s-admin-ch020 -n ch020 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch020 -n ch020 get deployment,replicaset,pod,service -o wide
kubectl --context kind-k8s-admin-ch020 -n ch020 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** three Ready web Pods, one active ReplicaSet and three ready Service endpoints. Capture the Deployment UID and revision before changes.

### 6.2 Create an in-cluster HTTP client

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: ch020
spec:
  containers:
    - name: toolbox
      image: busybox:1.36.1
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\client.yaml

kubectl --context kind-k8s-admin-ch020 apply -f .\client.yaml
kubectl --context kind-k8s-admin-ch020 -n ch020 wait --for=condition=Ready pod/client --timeout=180s
kubectl --context kind-k8s-admin-ch020 -n ch020 exec client -- nslookup web.ch020.svc.cluster.local
kubectl --context kind-k8s-admin-ch020 -n ch020 exec client -- wget -qO- http://web.ch020.svc.cluster.local
```

**Expected:** DNS resolves the Service and HTTP returns the NGINX welcome content.

## 7. Phase 2 — Simulate a stalled Deployment rollout

### 7.1 Introduce an invalid readiness path

```powershell
kubectl --context kind-k8s-admin-ch020 -n ch020 patch deployment web --type=json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/missing-health"}]'
kubectl --context kind-k8s-admin-ch020 -n ch020 get deployment web
kubectl --context kind-k8s-admin-ch020 -n ch020 get replicasets -l app=web
kubectl --context kind-k8s-admin-ch020 -n ch020 get pods -l app=web -o wide
kubectl --context kind-k8s-admin-ch020 -n ch020 get endpointslices -l kubernetes.io/service-name=web
```

**Expected:** a new ReplicaSet creates an unready Pod; the old Ready Pods continue serving because `maxUnavailable: 0`. **Do not claim the Service has zero endpoints**; this failure mode deliberately tests safe rollout behavior.

### 7.2 Investigate the incident

```powershell
kubectl --context kind-k8s-admin-ch020 -n ch020 describe deployment web
kubectl --context kind-k8s-admin-ch020 -n ch020 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch020 -n ch020 rollout history deployment/web
kubectl --context kind-k8s-admin-ch020 -n ch020 rollout status deployment/web --timeout=20s
kubectl --context kind-k8s-admin-ch020 -n ch020 exec client -- wget -qO- http://web.ch020.svc.cluster.local
```

**Expected:** rollout status times out in this intentionally negative test; HTTP should still succeed through healthy old endpoints. After the configured progress deadline, the Deployment may report `ProgressDeadlineExceeded`. The controller does **not** automatically roll back.

### 7.3 Recover with a reviewed rollback

```powershell
kubectl --context kind-k8s-admin-ch020 -n ch020 rollout undo deployment/web
kubectl --context kind-k8s-admin-ch020 -n ch020 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch020 -n ch020 get deployment web
kubectl --context kind-k8s-admin-ch020 -n ch020 get endpointslices -l kubernetes.io/service-name=web
kubectl --context kind-k8s-admin-ch020 -n ch020 exec client -- wget -qO- http://web.ch020.svc.cluster.local
```

**Expected:** three Ready replicas, healthy endpoints and successful HTTP. Record the failed revision, rollback revision, timestamps and readiness events.

## 8. Phase 3 — Init-container failure and recovery

### 8.1 Create a failing init container

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: init-demo
  namespace: ch020
spec:
  restartPolicy: Always
  initContainers:
    - name: prepare
      image: busybox:1.36.1
      command: ["sh", "-c", "echo prerequisite-failed; exit 1"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
  containers:
    - name: app
      image: busybox:1.36.1
      command: ["sh", "-c", "echo app-started; sleep 3600"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
'@ | Set-Content -Encoding ascii .\init-demo.yaml

kubectl --context kind-k8s-admin-ch020 apply -f .\init-demo.yaml
kubectl --context kind-k8s-admin-ch020 -n ch020 get pod init-demo
kubectl --context kind-k8s-admin-ch020 -n ch020 describe pod init-demo
kubectl --context kind-k8s-admin-ch020 -n ch020 logs init-demo -c prepare
```

**Expected:** Pod reports an init failure/backoff; the app container has not started. Record `initContainerStatuses` and restart count.

### 8.2 Correct the immutable init command

```powershell
kubectl --context kind-k8s-admin-ch020 -n ch020 delete pod init-demo
(Get-Content .\init-demo.yaml -Raw).Replace('echo prerequisite-failed; exit 1','echo prerequisite-ready; exit 0') | Set-Content -Encoding ascii .\init-fixed.yaml
kubectl --context kind-k8s-admin-ch020 apply --dry-run=server -f .\init-fixed.yaml
kubectl --context kind-k8s-admin-ch020 apply -f .\init-fixed.yaml
kubectl --context kind-k8s-admin-ch020 -n ch020 wait --for=condition=Ready pod/init-demo --timeout=180s
kubectl --context kind-k8s-admin-ch020 -n ch020 logs init-demo -c prepare
kubectl --context kind-k8s-admin-ch020 -n ch020 logs init-demo -c app
```

**Expected:** init completes and the application starts. If the replacement text did not match, inspect the generated file before applying.

## 9. Phase 4 — Liveness failure versus application crash

### 9.1 Reproduce a probe-induced restart

```powershell
@'
apiVersion: v1
kind: Pod
metadata:
  name: liveness-demo
  namespace: ch020
spec:
  containers:
    - name: nginx
      image: nginx:stable
      livenessProbe:
        httpGet:
          path: /not-found
          port: 80
        initialDelaySeconds: 3
        periodSeconds: 5
        failureThreshold: 2
      resources:
        requests:
          cpu: 25m
          memory: 32Mi
'@ | Set-Content -Encoding ascii .\liveness-demo.yaml

kubectl --context kind-k8s-admin-ch020 apply -f .\liveness-demo.yaml
kubectl --context kind-k8s-admin-ch020 -n ch020 get pod liveness-demo
kubectl --context kind-k8s-admin-ch020 -n ch020 describe pod liveness-demo
kubectl --context kind-k8s-admin-ch020 -n ch020 get pod liveness-demo -o jsonpath='{.status.containerStatuses[0].restartCount}'
```

**Expected:** after several probe intervals, restartCount increases. NGINX can be healthy while the **incorrect probe path** forces restarts. Distinguish this from a process crash by reviewing probe events and previous container termination details.

### 9.2 Remove the disposable failure Pod

```powershell
kubectl --context kind-k8s-admin-ch020 -n ch020 delete pod liveness-demo
```

## 10. Phase 5 — Controller reconciliation and Pod identity

### 10.1 Trace owner references

```powershell
kubectl --context kind-k8s-admin-ch020 -n ch020 get replicasets -l app=web -o jsonpath='{range .items[*]}{.metadata.name}{" owned-by="}{.metadata.ownerReferences[0].name}{"\n"}{end}'
kubectl --context kind-k8s-admin-ch020 -n ch020 get pods -l app=web -o jsonpath='{range .items[*]}{.metadata.name}{" owned-by="}{.metadata.ownerReferences[0].name}{"\n"}{end}'
```

### 10.2 Delete one managed Pod

```powershell
$pod = kubectl --context kind-k8s-admin-ch020 -n ch020 get pods -l app=web -o jsonpath='{.items[0].metadata.name}'
$oldUid = kubectl --context kind-k8s-admin-ch020 -n ch020 get pod $pod -o jsonpath='{.metadata.uid}'
kubectl --context kind-k8s-admin-ch020 -n ch020 delete pod $pod
kubectl --context kind-k8s-admin-ch020 -n ch020 rollout status deployment/web --timeout=180s
kubectl --context kind-k8s-admin-ch020 -n ch020 get pods -l app=web -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,READY:.status.containerStatuses[0].ready'
Write-Output "Deleted Pod UID: $oldUid"
```

**Expected:** a replacement Pod has a new UID and the Deployment returns to three Ready replicas. A standalone Pod such as `init-demo` has no ReplicaSet owner and would not be automatically recreated after deletion.

## 11. Phase 6 — StatefulSet identity and persistence

### 11.1 Storage compatibility gate

```powershell
kubectl --context kind-k8s-admin-ch020 get storageclasses
```

Continue only if the cluster has a functioning default StorageClass/provisioner. Otherwise record **A11 Blocked — no dynamic storage** and complete the other tests.

### 11.2 Create a PVC-backed StatefulSet

```powershell
@'
apiVersion: v1
kind: Service
metadata:
  name: stateful
  namespace: ch020
spec:
  clusterIP: None
  selector:
    app: stateful
  ports:
    - port: 80
      name: service
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: stateful
  namespace: ch020
spec:
  serviceName: stateful
  replicas: 1
  selector:
    matchLabels:
      app: stateful
  template:
    metadata:
      labels:
        app: stateful
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
'@ | Set-Content -Encoding ascii .\stateful.yaml

kubectl --context kind-k8s-admin-ch020 apply -f .\stateful.yaml
kubectl --context kind-k8s-admin-ch020 -n ch020 rollout status statefulset/stateful --timeout=180s
kubectl --context kind-k8s-admin-ch020 -n ch020 get pod stateful-0
kubectl --context kind-k8s-admin-ch020 -n ch020 get pvc data-stateful-0
```

**Expected:** `stateful-0` Ready and PVC Bound.

### 11.3 Verify persistence after Pod replacement

```powershell
kubectl --context kind-k8s-admin-ch020 -n ch020 exec stateful-0 -- sh -c 'echo retained-data > /data/check.txt'
$statefulOldUid = kubectl --context kind-k8s-admin-ch020 -n ch020 get pod stateful-0 -o jsonpath='{.metadata.uid}'
kubectl --context kind-k8s-admin-ch020 -n ch020 delete pod stateful-0
kubectl --context kind-k8s-admin-ch020 -n ch020 rollout status statefulset/stateful --timeout=180s
$statefulNewUid = kubectl --context kind-k8s-admin-ch020 -n ch020 get pod stateful-0 -o jsonpath='{.metadata.uid}'
kubectl --context kind-k8s-admin-ch020 -n ch020 exec stateful-0 -- cat /data/check.txt
Write-Output "old=$statefulOldUid new=$statefulNewUid"
```

**Expected:** stable name `stateful-0`, different UID, and `retained-data` from the same PVC. This proves persistence across a Pod replacement in the lab, **not** multi-node disaster recovery or backup correctness.

## 12. Phase 7 — DaemonSet node coverage

```powershell
@'
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-agent
  namespace: ch020
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
          command: ["sh", "-c", "while true; do echo node-agent-alive; sleep 30; done"]
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
'@ | Set-Content -Encoding ascii .\daemonset.yaml

kubectl --context kind-k8s-admin-ch020 apply -f .\daemonset.yaml
kubectl --context kind-k8s-admin-ch020 -n ch020 rollout status daemonset/node-agent --timeout=180s
kubectl --context kind-k8s-admin-ch020 -n ch020 get daemonset node-agent -o wide
kubectl --context kind-k8s-admin-ch020 -n ch020 get pods -l app=node-agent -o wide
kubectl --context kind-k8s-admin-ch020 -n ch020 logs daemonset/node-agent --tail=20
```

**Expected:** desired/current/ready agent counts reflect eligible nodes. On a typical one-node kind cluster, one node is eligible. Check selectors, affinity and taints before concluding a missing Pod indicates failure.

## 13. Phase 8 — Failed Job and idempotent recovery

### 13.1 Run a deliberately failing batch task

```powershell
@'
apiVersion: batch/v1
kind: Job
metadata:
  name: batch-failure
  namespace: ch020
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 90
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: task
          image: busybox:1.36.1
          command: ["sh", "-c", "echo validation-failed; exit 2"]
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
'@ | Set-Content -Encoding ascii .\batch-failure.yaml

kubectl --context kind-k8s-admin-ch020 apply -f .\batch-failure.yaml
kubectl --context kind-k8s-admin-ch020 -n ch020 get jobs,pods
kubectl --context kind-k8s-admin-ch020 -n ch020 describe job batch-failure
kubectl --context kind-k8s-admin-ch020 -n ch020 get pods -l batch.kubernetes.io/job-name=batch-failure
```

**Expected:** failed Pods with exit code 2; Job ultimately fails after its backoff policy. Capture the logs of each failed Pod separately if needed.

### 13.2 Create a corrected new Job

```powershell
@'
apiVersion: batch/v1
kind: Job
metadata:
  name: batch-recovered
  namespace: ch020
spec:
  completions: 2
  parallelism: 1
  backoffLimit: 2
  activeDeadlineSeconds: 180
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: task
          image: busybox:1.36.1
          command: ["sh", "-c", "echo validated-idempotent-task; exit 0"]
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
'@ | Set-Content -Encoding ascii .\batch-recovered.yaml

kubectl --context kind-k8s-admin-ch020 apply -f .\batch-recovered.yaml
kubectl --context kind-k8s-admin-ch020 -n ch020 wait --for=condition=complete job/batch-recovered --timeout=180s
kubectl --context kind-k8s-admin-ch020 -n ch020 get job batch-recovered
kubectl --context kind-k8s-admin-ch020 -n ch020 get pods -l batch.kubernetes.io/job-name=batch-recovered
kubectl --context kind-k8s-admin-ch020 -n ch020 logs job/batch-recovered
```

**Expected:** Job completes 2/2; output shows `validated-idempotent-task`. The demonstration command has no external side effects, but real Jobs must implement application-level idempotency and transaction safeguards.

## 14. Phase 9 — CronJob scheduling and controlled execution

```powershell
@'
apiVersion: batch/v1
kind: CronJob
metadata:
  name: periodic-check
  namespace: ch020
spec:
  schedule: "*/5 * * * *"
  timeZone: "Etc/UTC"
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 120
  successfulJobsHistoryLimit: 2
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: check
              image: busybox:1.36.1
              command: ["sh", "-c", "date -u; echo periodic-check-ok"]
              resources:
                requests:
                  cpu: 10m
                  memory: 16Mi
'@ | Set-Content -Encoding ascii .\cronjob.yaml

kubectl --context kind-k8s-admin-ch020 apply -f .\cronjob.yaml
kubectl --context kind-k8s-admin-ch020 -n ch020 get cronjob periodic-check
kubectl --context kind-k8s-admin-ch020 -n ch020 create job --from=cronjob/periodic-check manual-check
kubectl --context kind-k8s-admin-ch020 -n ch020 wait --for=condition=complete job/manual-check --timeout=180s
kubectl --context kind-k8s-admin-ch020 -n ch020 logs job/manual-check
kubectl --context kind-k8s-admin-ch020 -n ch020 patch cronjob periodic-check --type=merge -p '{"spec":{"suspend":true}}'
kubectl --context kind-k8s-admin-ch020 -n ch020 get cronjob periodic-check
```

**Expected:** manually created Job completes, output contains `periodic-check-ok`, CronJob is suspended. Manual execution validates the Job template, **not** scheduled execution, missed-run handling or concurrency semantics.

## 15. Phase 10 — Evidence collection and operational assessment

### 15.1 Read-only diagnostic snapshot

```powershell
kubectl --context kind-k8s-admin-ch020 get nodes -o wide
kubectl --context kind-k8s-admin-ch020 -n ch020 get deployment,replicaset,statefulset,daemonset,job,cronjob,pod,service -o wide
kubectl --context kind-k8s-admin-ch020 -n ch020 get endpointslices
kubectl --context kind-k8s-admin-ch020 -n ch020 get pvc
kubectl --context kind-k8s-admin-ch020 -n ch020 get events --sort-by=.lastTimestamp
kubectl --context kind-k8s-admin-ch020 -n ch020 rollout history deployment/web
kubectl --context kind-k8s-admin-ch020 -n ch020 describe deployment web
```

Capture context, namespace, timestamp, affected object names and UIDs, revisions, probe events, exit codes, ready endpoints, storage claims, Job status and recovery results. Avoid collecting Secret contents or customer data.

### 15.2 Incident report template

Create `CH020-ACCEPTANCE-REPORT.md` locally:

```markdown
# Chapter 020 — Workload Administration and Recovery Acceptance

Operator:
Reviewer:
Date/time:
Cluster/context: kind-k8s-admin-ch020
Namespace: ch020
Kubernetes server version:

## Timeline
| Time | Event | Impact | Evidence |
|---|---|---|---|
| | Baseline | | |
| | Failed rollout | | |
| | Rollback | | |
| | Init failure/recovery | | |
| | Probe failure | | |
| | Stateful test | | |
| | Batch failure/recovery | | |

## Acceptance
| ID | Pass / Fail / Blocked / Not Run | Evidence |
|---|---|---|
| A01 | | |
| A02 | | |
| A03 | | |
| A04 | | |
| A05 | | |
| A06 | | |
| A07 | | |
| A08 | | |
| A09 | | |
| A10 | | |
| A11 | | |
| A12 | | |
| A13 | | |
| A14 | | |
| A15 | | |
| A16 | | |

Root causes:
Actions and rollback:
Residual risks:
Cleanup confirmation:
Final reviewer decision:
```

### 15.3 Scoring and pass criteria

| Category | Points |
|---|---:|
| Safety, isolation, baseline | 15 |
| Rollout incident and rollback | 25 |
| Init/probe and Pod reconciliation | 20 |
| StatefulSet and DaemonSet | 15 |
| Job/CronJob operations | 15 |
| Evidence, handover and cleanup | 10 |
| **Total** | **100** |

**Pass threshold:** 85 points with all mandatory tests passed, no safety violations, and no unreviewed data-loss operations. A11 can be Blocked only when storage prerequisites are unavailable; a full capstone validation then requires a later PVC-capable environment. This is a training assessment rubric, not an industry certification.

## 16. Production incident-response runbook

### Step 1 — Establish scope

Confirm context, namespace, incident start time, service SLO impact, affected workload and recent changes. Avoid making changes before collecting the initial state.

### Step 2 — Distinguish failure domains

- **Deployment:** revision, ReplicaSets, readiness, progress deadline, surge capacity.
- **Pod:** phase, conditions, init statuses, container states, restarts, exit codes.
- **Service:** selector, ready EndpointSlices, DNS versus HTTP reachability.
- **StatefulSet:** ordinals, PVC binding, volume attachment, quorum/application membership.
- **DaemonSet:** desired/ready eligible-node coverage.
- **Job/CronJob:** retries, deadlines, schedule, time zone, idempotency and side effects.

### Step 3 — Stabilize

Prefer rollback of a bad stateless rollout; restore the correct init/probe configuration through approved manifests; protect stateful data and quorum; pause harmful scheduled jobs when appropriate.

### Step 4 — Validate recovery

Confirm Ready replicas, endpoint health, request success, application error rate and latency, restart stability, storage health, data integrity and batch output correctness. A Kubernetes `Ready` status alone is insufficient.

### Step 5 — Prevent recurrence

Document root cause, change ownership, test gaps, guardrail failures, rollback criteria, monitoring improvements, and runbook updates.

## 17. Production safeguards and common anti-patterns

- Do not force-delete stateful Pods to bypass a stuck rollout or storage issue.
- Do not equate a successful Pod restart with application recovery.
- Do not let liveness depend on transient downstream outages.
- Do not assume a failed Job is safe to rerun without idempotency.
- Do not assume CronJob provides exactly-once execution.
- Do not scale StatefulSets without considering quorum and data placement.
- Do not use DaemonSet Pod count alone to prove complete telemetry coverage.
- Do not trust a successful backup Job without a tested restore.
- Do not use mutable image tags as the only record of a production release.
- Do not mark training labs complete before collecting observed evidence.

## 18. Cleanup and rollback

**Destructive operations below apply only to the disposable kind cluster.** Confirm the exact context:

```powershell
kubectl config current-context
kubectl --context kind-k8s-admin-ch020 get nodes
```

Suspend scheduled work and remove the StatefulSet before deleting its disposable PVC:

```powershell
kubectl --context kind-k8s-admin-ch020 -n ch020 patch cronjob periodic-check --type=merge -p '{"spec":{"suspend":true}}'
kubectl --context kind-k8s-admin-ch020 -n ch020 delete statefulset stateful --ignore-not-found
kubectl --context kind-k8s-admin-ch020 -n ch020 get pvc
kubectl --context kind-k8s-admin-ch020 -n ch020 delete pvc data-stateful-0 --ignore-not-found
kubectl --context kind-k8s-admin-ch020 delete namespace ch020
kind delete cluster --name k8s-admin-ch020
kind get clusters
Remove-Item .\baseline.yaml, .\client.yaml, .\init-demo.yaml, .\init-fixed.yaml, .\liveness-demo.yaml, .\stateful.yaml, .\daemonset.yaml, .\batch-failure.yaml, .\batch-recovered.yaml, .\cronjob.yaml -ErrorAction SilentlyContinue
```

Deleting PVCs may delete underlying storage depending on the StorageClass reclaim policy. Retain the acceptance report and sanitized evidence before cleanup.

## 19. Final acceptance checklist

- [ ] Disposable cluster and context verified.
- [ ] Baseline web Deployment healthy at three replicas.
- [ ] Service DNS and HTTP verified.
- [ ] Stalled rollout reproduced with old ready endpoints preserved.
- [ ] Rollback restored healthy revision.
- [ ] Init failure diagnosed and corrected by Pod recreation.
- [ ] Probe-driven container restart demonstrated.
- [ ] Controller-managed Pod recreated with new UID.
- [ ] StatefulSet ordinal identity verified.
- [ ] PVC data survived Pod replacement, or compatibility block recorded.
- [ ] DaemonSet eligible-node coverage verified.
- [ ] Failed Job diagnosed and new corrected Job completed.
- [ ] CronJob manually triggered and suspended.
- [ ] Incident timeline, evidence, and root causes documented.
- [ ] Disposable resources cleaned up safely.

## 20. Part 04 writing milestone and next chapter

| Chapter | Topic | Writing status |
|---|---|---|
| 016 | Pod Architecture and Lifecycle | Draft |
| 017 | Init Containers, Sidecars and Probes | Draft |
| 018 | Deployments, ReplicaSets and Rollouts | Draft |
| 019 | StatefulSets, DaemonSets, Jobs and CronJobs | Draft |
| 020 | Workload Administration and Recovery Lab | Draft |

**Part 04 writing milestone reached:** all five chapters have been drafted. **Hands-on execution, technical review, and acceptance evidence remain pending.**

**Next:** Chapter 021 — Kubernetes Scheduler Internals.
