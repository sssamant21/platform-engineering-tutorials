# Chapter 061 — Kubernetes Troubleshooting Methodology

**Track:** Kubernetes Administration · **Part 13 — Troubleshooting and Incident Response**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, incident commanders and platform engineers  
**Prerequisites:** Chapters 001–060; kubectl, Windows PowerShell; approved read-only cluster access; staging cluster for optional controlled exercises

## 1. Production scenario

A customer-facing application is intermittently unavailable. Some Pods are Pending, others restart, and application p95 latency has increased. A recent Deployment occurred, one node reports pressure and the database has elevated connection wait times. Multiple plausible explanations exist; immediately deleting Pods or increasing limits risks obscuring evidence and making the incident worse.

**Goal:** use a systematic, evidence-driven investigation framework to identify the blast radius, isolate the failing layer, form and test hypotheses, mitigate safely and verify customer recovery.

### Learning objectives

1. Apply an incident-first, symptom-to-root-cause investigation sequence.
2. Separate customer impact from infrastructure symptoms.
3. Identify the failure domain: application, Pod, controller, scheduler, node, network, storage, cluster or external dependency.
4. Collect time-bounded evidence from metrics, logs, Events, traces and object status.
5. Distinguish observations, hypotheses, contributing factors and confirmed causes.
6. Select low-risk mitigations and preserve rollback paths.
7. Produce an incident timeline, acceptance criteria and blameless follow-up report.

## 2. Core troubleshooting framework

```text
Customer impact and incident window
                 |
          Confirm scope
                 |
      Identify failure domain
                 |
      Gather time-bound evidence
                 |
     Form competing hypotheses
                 |
       Test safely / compare
                 |
        Mitigate and verify
                 |
        Document and prevent
```

### The seven questions to answer first

1. **What is broken?** Error rate, latency, data integrity, unavailable functionality or delayed processing.
2. **Who is affected?** Service, tenant, region, cluster, namespace and request type.
3. **When did it start?** Precise timestamps, timezone and deployment/maintenance correlation.
4. **What changed?** Deployments, configuration, traffic, autoscaling, certificates, storage, network and upstream dependencies.
5. **Which layer is failing?** Application, Pod, scheduler, node, networking, storage, control plane or dependency.
6. **What evidence supports the hypothesis?** Independent metrics, logs, Events, traces and reproduction.
7. **How will recovery be verified?** Customer SLIs, Ready endpoints, successful transactions, queue recovery and data consistency.

**Rule:** do not infer root cause from a single Warning Event, high CPU sample or recent deployment alone.

## 3. Safety, permissions and evidence preservation

Default labs are read-only. Production mutations require incident authority, a documented rollback and stateful dependency review.

```powershell
kubectl config current-context
kubectl version
kubectl cluster-info
kubectl auth can-i get pods -A
kubectl auth can-i get pods/log -n default
kubectl auth can-i list events -A
Get-Date -Format o
```

**Expected:** known cluster context, sufficient least-privilege permissions and an investigation timestamp.

### Preserve before changing

- Pod identity, owner, node, zone, restart count and previous termination reason.
- Current and previous container logs (with sensitive content redacted).
- Pod/Node Events, Deployment revision and ReplicaSet changes.
- CPU/memory, saturation, latency and error-rate trends.
- Service endpoints, DNS, network policy and storage status.
- Database/queue/cache state and quorum when relevant.
- Current alert state and customer-facing SLIs.

Do not copy Secrets, tokens, raw patient information or other sensitive application data into tickets. Avoid force deleting stateful Pods or restarting databases before assessing quorum and durability.

## 4. Lab 1 — Establish incident scope and baseline

```powershell
Get-Date -Format o
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get deployments,statefulsets,daemonsets -A
kubectl get events -A --sort-by=.lastTimestamp
kubectl get --raw /readyz
```

**Expected:** determine whether symptoms are isolated to one Pod, namespace, node, zone or the whole cluster. A healthy API `/readyz` response does not prove application health.

### Scope matrix

| Scope | Likely first checks |
|---|---|
| One container | Logs, exit code, probes, limits |
| One Pod | Node placement, volumes, events |
| One Deployment | Rollout, image, ConfigMap/Secret references |
| One node | Conditions, kubelet, runtime, disk/memory |
| One zone | Node pool, storage affinity, subnet, load balancer |
| One namespace | Quota, RBAC, policy, network policy |
| Cluster-wide | API, DNS, CNI, storage controller, capacity |
| Cross-cluster | Upstream service, identity, DNS, cloud service |

## 5. Lab 2 — Classify Pod and workload failure

Select an approved namespace and Pod:

```powershell
$ns = 'REPLACE_WITH_NAMESPACE'
$pod = 'REPLACE_WITH_POD'
kubectl -n $ns get pod $pod -o wide
kubectl -n $ns describe pod $pod
kubectl -n $ns get pod $pod -o json
kubectl -n $ns logs $pod --all-containers=true --since=30m --timestamps --tail=200
kubectl -n $ns logs $pod --all-containers=true --previous --timestamps --tail=100
```

**Expected:** identify Pod phase, container waiting/terminated reason, readiness, restart count and relevant Events. The `--previous` option may fail if no terminated container instance is retained.

### Failure classification

| Symptom | First investigation |
|---|---|
| Pending | Scheduler, requests, affinity, taints, PVC, quota |
| ImagePullBackOff | Registry auth, image reference, network |
| CreateContainerConfigError | Missing ConfigMap/Secret key, environment |
| CrashLoopBackOff | Previous logs, exit code, probes, dependencies |
| OOMKilled | Memory limits, workload behavior, node pressure |
| Running but NotReady | Readiness probe, application dependencies |
| Terminating for too long | Finalizers, preStop, volume detach |
| Completed unexpectedly | Job versus long-running workload intent |

**Important:** `CrashLoopBackOff` is a backoff condition, not the root cause. An OOM kill is different from a node-pressure eviction.

## 6. Lab 3 — Analyze rollout and controller behavior

```powershell
kubectl -n $ns get deployments,replicasets,pods -o wide
kubectl -n $ns rollout history deployment/REPLACE_WITH_DEPLOYMENT
kubectl -n $ns describe deployment REPLACE_WITH_DEPLOYMENT
kubectl -n $ns get events --sort-by=.lastTimestamp
```

**Expected:** establish desired versus available replicas, revision timing, image/config changes and readiness behavior.

### Rollback decision gate

A rollback may be appropriate when evidence strongly links a recent revision to failure, the previous revision is known healthy, and database schema or API compatibility permits reversal. **Do not automatically rollback** if data migrations or irreversible side effects have occurred.

A production rollback command is intentionally not executed in this read-only lab. Document the proposed change, approver, expected effect and verification plan.

## 7. Lab 4 — Investigate scheduling and capacity

```powershell
kubectl get pods -A --field-selector=status.phase=Pending -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl describe node REPLACE_WITH_NODE
kubectl get events -A --sort-by=.lastTimestamp
kubectl top nodes
kubectl top pods -A --containers
```

**Expected:** distinguish unschedulable requests, taints/tolerations, affinity, topology spread, quota, insufficient CPU/memory and storage topology. `kubectl top` requires a working Metrics API and shows recent usage, not requested capacity.

### Scheduling hypothesis worksheet

| Hypothesis | Evidence that supports it | Evidence that refutes it |
|---|---|---|
| Insufficient CPU requests capacity | FailedScheduling insufficient CPU | Eligible nodes with allocatable capacity |
| Untolerated taint | Scheduler Event names taint | Pod has matching toleration |
| Zone spread constraint | Topology spread scheduling rejection | Eligible domains and placement satisfied |
| PVC topology mismatch | PV node affinity conflict | PV accessible in target zone |
| Namespace quota | Quota exceeded Event | Quota headroom exists |
| Autoscaler blocked | Provisioning errors, subnet/quotas | New nodes successfully join |

## 8. Lab 5 — Investigate node health and resource pressure

```powershell
kubectl get nodes -o wide
kubectl describe node REPLACE_WITH_NODE
kubectl top nodes
kubectl get pods -A -o wide --field-selector spec.nodeName=REPLACE_WITH_NODE
kubectl get events -A --sort-by=.lastTimestamp
```

**Expected:** inspect Ready, MemoryPressure, DiskPressure, PIDPressure, allocatable capacity, recent evictions and workload concentration.

### Node-level investigation branches

- **Memory:** node pressure, container OOM, working set, eviction threshold.
- **CPU:** utilization, throttling, noisy neighbors, requests/limits.
- **Storage:** disk/inode pressure, image garbage collection, PV I/O.
- **Runtime:** containerd/CRI health and image unpack failures.
- **Kubelet:** registration, certificate, status updates, probe failures.
- **Network:** CNI readiness, packet drops, conntrack, DNS.

Managed nodes may require approved cloud logging/SSM/diagnostics; do not assume SSH or privileged node access.

## 9. Lab 6 — Investigate Services, DNS and network path

```powershell
kubectl -n $ns get services -o wide
kubectl -n $ns get endpointslices
kubectl -n $ns get ingress
kubectl -n $ns get networkpolicies
kubectl -n kube-system get pods -o wide
kubectl -n $ns describe service REPLACE_WITH_SERVICE
```

**Expected:** verify Service selector, Ready EndpointSlices, ports, ingress routing and applicable NetworkPolicies.

### Layered network checklist

1. Does the application listen on the expected port and address?
2. Is the Pod Ready and included in EndpointSlices?
3. Does Service selector match Pod labels?
4. Are `port` and `targetPort` correct?
5. Is cluster DNS resolution working?
6. Are NetworkPolicies/CNI rules blocking traffic?
7. Is ingress/LB routing healthy and are backends registered?
8. Are TLS, certificates and external dependencies valid?

A Service with no Ready endpoints can cause failures even when its Deployment reports Pods in the Running phase.

## 10. Lab 7 — Investigate storage and stateful dependencies

```powershell
kubectl -n $ns get pvc
kubectl get pv
kubectl get storageclasses
kubectl -n $ns get statefulsets,pods -o wide
kubectl -n $ns get events --sort-by=.lastTimestamp
```

**Expected:** identify Pending PVCs, volume attach/mount failures, PV topology, CSI controller issues and StatefulSet readiness.

### DBRE safety gates

- Check database quorum and replication before Pod or node maintenance.
- Distinguish zonal PV unavailability from a database corruption problem.
- Confirm backup/restore and recovery ownership.
- Do not force delete a stateful Pod to resolve a storage attachment conflict without verifying the old process is stopped.
- Assess write consistency, RPO and RTO before failover.

## 11. Lab 8 — Correlate metrics, logs, Events and traces

```powershell
Get-Date -Format o
kubectl -n $ns get pod $pod -o wide
kubectl -n $ns logs $pod --all-containers=true --since=30m --timestamps --tail=200
kubectl -n $ns get events --sort-by=.lastTimestamp
kubectl top pods -n $ns --containers
```

Use approved Prometheus/Grafana and OpenTelemetry dashboards to compare:

- Customer request rate, error ratio and p95/p99 latency.
- CPU throttling, memory working set and restarts.
- Desired/Ready replicas and scheduling failures.
- Trace critical-path spans and dependency timing.
- Database lock waits, connection pool waits, queue backlog or cache latency.
- Deployment revisions and change annotations.

### Example incident timeline

| UTC | Observation | Hypothesis | Next validation |
|---|---|---|---|
| 14:00 | New rollout starts | Regression | Compare revisions |
| 14:02 | Readiness failures rise | Dependency not ready | Probe and app logs |
| 14:03 | p95 latency increases | Downstream saturation | Trace critical path |
| 14:04 | DB pool wait rises | Connection pool exhausted | DB sessions/pool metrics |
| 14:05 | Pending replacement Pods | Capacity shortage | Scheduler Events |

**Expected:** separate temporal correlation from proven causation and record contradictory evidence.

## 12. Lab 9 — Controlled troubleshooting tabletop

**Scenario:** a production API has 8% HTTP 5xx errors, one Pod in CrashLoopBackOff, two Pending replicas, high node memory pressure and elevated PostgreSQL pool wait times.

### Required exercise

1. Declare incident severity from customer SLIs.
2. Identify scope, recent changes and available healthy capacity.
3. Preserve failing Pod's previous logs and restart reason.
4. Inspect scheduling Events for Pending replicas.
5. Assess node pressure and whether autoscaling can restore capacity.
6. Correlate DB connection pool wait with actual DB query time.
7. Decide whether rollback, capacity increase, traffic shaping or DB remediation is lowest risk.
8. Specify approval and rollback for the selected mitigation.
9. Verify error rate, p95, Ready endpoints and database health.
10. Produce a blameless incident timeline and action register.

**Expected:** an evidence-based decision and recovery criteria; no production fault injection.

## 13. Root cause and hypothesis discipline

Use the following classifications:

- **Observation:** directly measured, e.g. `FailedScheduling` reports insufficient CPU.
- **Hypothesis:** plausible explanation requiring tests, e.g. autoscaler quota prevented new nodes.
- **Contributing factor:** worsened the incident, e.g. insufficient zone headroom.
- **Root cause:** supported causal mechanism that explains the failure.
- **Unknown:** missing evidence, e.g. exporter outage removed node metrics.

Avoid treating a restart, high CPU or an Event reason as a complete RCA. Distinguish primary trigger from latent design weaknesses and monitoring gaps.

## 14. Production incident command workflow

### Detect and triage

1. Confirm service/customer impact and start an incident timeline.
2. Identify incident commander, technical leads and communications owner.
3. Freeze unrelated changes when warranted.
4. Assess data integrity, quorum and safety risks.

### Diagnose

1. Work from broad scope to the narrowest failing layer.
2. Collect bounded, timestamped evidence.
3. Rank hypotheses by explanatory power and testability.
4. Avoid simultaneous uncontrolled changes.

### Mitigate and recover

1. Select a low-risk, reversible action with an explicit owner.
2. Capture before/after SLIs and health.
3. Verify traffic, readiness, dependency state and data consistency.
4. Monitor for recurrence and residual risk.

### Close and prevent

1. Document timeline, customer impact and contributing factors.
2. Record what evidence was missing and why.
3. Assign remediation actions with measurable acceptance.
4. Update runbooks, alerts, capacity and resilience tests.

## 15. Common troubleshooting mistakes

| Mistake | Why it is harmful | Better approach |
|---|---|---|
| Restarting Pods first | Destroys transient evidence | Collect status and previous logs |
| Force deleting stateful Pods | Risks split-brain/data loss | Check quorum and fencing |
| Treating Running as healthy | Readiness can still fail | Check probes and endpoints |
| Treating `kubectl top` as history | Only recent metrics | Use Prometheus time series |
| Assuming Event equals root cause | Event may be consequence | Correlate multiple signals |
| Ignoring timezones | Breaks incident chronology | Normalize timestamps |
| Changing multiple variables | Obscures causality | One controlled change at a time |
| Ignoring monitoring gaps | Creates false healthy signals | Check target coverage |
| Scaling without capacity checks | Can worsen resource pressure | Check allocatable/quotas |
| Declaring recovery from Pod Ready | Customer SLI may still fail | Verify request success and latency |

## 16. Evidence collection template

```text
Incident ID:
Date/time window (UTC):
Cluster / context:
Environment / region / zones:
Namespace / service:
Incident commander / owners:
Customer-facing SLIs:
Blast radius:
Recent changes:
Pod/Deployment/Node status:
Events:
Logs (current and previous):
Metrics / dashboards:
Trace IDs and dependency findings:
Storage/database state:
Confirmed facts:
Hypotheses:
Contradictory evidence:
Chosen mitigation / approver:
Rollback plan:
Recovery verification:
Root cause confidence:
Follow-up actions and owners:
```

## 17. Acceptance checklist

- [ ] Customer impact and investigation window established.
- [ ] Scope classified by Pod, node, namespace, zone or cluster.
- [ ] Read-only baseline evidence collected before mutation.
- [ ] Pod status, restart reasons, probes and logs reviewed.
- [ ] Rollout and controller state examined.
- [ ] Scheduling and node-pressure hypotheses tested.
- [ ] Service, DNS, CNI and ingress path assessed.
- [ ] Storage and stateful quorum risks assessed.
- [ ] Metrics, logs, Events and traces correlated.
- [ ] Competing hypotheses and contradictory evidence recorded.
- [ ] Mitigation approval, rollback and recovery SLIs defined.
- [ ] Blameless incident report and follow-up actions completed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 18. References

- [Kubernetes Troubleshooting](https://kubernetes.io/docs/tasks/debug/)
- [Debug Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)
- [Debug Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/)
- [Debug Cluster](https://kubernetes.io/docs/tasks/debug/debug-cluster/)
- [Kubernetes Observability](https://kubernetes.io/docs/concepts/cluster-administration/observability/)
- [Resource Metrics Pipeline](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)
- [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)

**Next:** Chapter 062 — Container Startup and Image Pull Failures.
