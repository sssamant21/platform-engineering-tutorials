# Chapter 065 — Production Incident Investigation Project

**Track:** Kubernetes Administration · **Part 13 — Troubleshooting and Incident Response (final capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, platform engineers, incident commanders and on-call responders  
**Prerequisites:** Chapters 061–064; kubectl; Windows PowerShell; approved read-only production access and an isolated staging cluster for optional exercises

## 1. Capstone mission

A customer-facing API on Kubernetes has 12% HTTP 5xx errors and p95 latency has risen from 250 ms to 5 seconds. During the same 20-minute window:

- A rollout changed the application image and environment configuration.
- Two replacement Pods are Pending.
- One container reports `ImagePullBackOff`.
- One worker repeatedly exits and enters `CrashLoopBackOff`.
- A node reports MemoryPressure and another is NotReady.
- Some application requests report DNS timeouts.
- PostgreSQL connection pool wait time increases.
- The API server is slower than normal for some clients.

**Your mission:** act as the incident response team, establish impact, preserve evidence, separate concurrent failure domains, select safe mitigations, verify customer recovery and produce a defensible blameless incident report.

This project is deliberately multi-causal. A single warning Event or recently deployed change is not sufficient evidence of root cause.

## 2. Learning objectives and required deliverables

By the end of this capstone, the learner should be able to:

1. Run an incident bridge with explicit technical and communications roles.
2. Scope impact using customer SLIs, cluster topology and workload health.
3. Classify image pull, startup, scheduling, eviction, OOM, network and control-plane symptoms.
4. Build a timestamped evidence timeline from Events, logs, metrics and traces.
5. Test competing hypotheses and identify contradictory evidence.
6. Apply approved, low-blast-radius mitigations with rollback plans.
7. Verify recovery at the application, infrastructure and dependency layers.
8. Write a blameless RCA and preventive action plan.

### Required artifacts

- Incident declaration and severity worksheet.
- Cluster and application baseline snapshot.
- Failure-domain matrix and hypothesis register.
- Time-correlated evidence table.
- Remediation decision and rollback record.
- Recovery verification report.
- Blameless RCA and action tracker.
- Final acceptance sign-off.

## 3. Reference architecture

```text
Users -> Ingress / Load Balancer -> Service -> API Pods
                                              |
                              +---------------+----------------+
                              |               |                |
                          PostgreSQL        Redis           Kafka
                              |
                     Connection pool waits

Kubernetes:
  API server -> Scheduler / Controllers -> Deployments / Pods
                    |
                  Nodes
                    |
             kubelet / CRI / CNI
                    |
                CoreDNS

Observability:
  Metrics -> Prometheus / Grafana
  Logs -> central log backend
  Traces -> OpenTelemetry / trace backend
  Events -> Kubernetes API / event pipeline
  Alerts -> Alertmanager / approved on-call receiver
```

This architecture is illustrative; adapt service names, dependencies and topology to the actual environment.

## 4. Safety gates and operational boundaries

**Production commands in this chapter are read-only by default.** The learner must not force delete Pods, restart CoreDNS, change CNI, drain nodes, alter database replicas, disable admission webhooks or apply blanket resource increases without an approved change and rollback.

Before optional staging experiments:

- Confirm the cluster context, namespace, owner and isolation boundary.
- Use an approved test namespace with resource quota and clear cleanup ownership.
- Avoid live customer traffic, production credentials and sensitive data.
- Define abort conditions: unintended cross-namespace impact, resource pressure or loss of telemetry.
- Preserve healthy workload capacity and stateful quorum.
- Ensure incident communications and change authority are documented.

```powershell
Get-Date -Format o
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl auth can-i get pods -A
kubectl auth can-i get pods/log -n default
kubectl auth can-i list events -A
```

**Expected:** the responder can identify the target cluster and knows which diagnostics are permitted.

## 5. Lab 1 — Declare the incident and establish customer impact

### Incident intake

Record:

```text
Incident ID:
Start time (UTC):
Incident commander:
Technical lead:
Communications owner:
Affected service / cluster / region:
Customer-facing error ratio:
p95 / p99 latency:
Request volume:
Estimated blast radius:
Data integrity risk:
Current severity and rationale:
Next update time:
```

Use approved application dashboards to establish baseline request rate, HTTP 5xx ratio and latency. If the metrics backend is degraded, use load-balancer logs, application logs or synthetic checks as independent evidence.

### Initial questions

1. Which users, endpoints and regions are affected?
2. Is the error rate rising, stable or recovering?
3. Did the issue begin before or after the rollout?
4. Is there a risk of lost, duplicated or inconsistent writes?
5. Are telemetry gaps creating false healthy signals?

**Expected:** a severity decision supported by impact, not merely the number of unhealthy Pods.

## 6. Lab 2 — Capture the cluster baseline

```powershell
Get-Date -Format o
kubectl get nodes -L topology.kubernetes.io/zone -o wide
kubectl get pods -A -o wide
kubectl get deployments,statefulsets,daemonsets -A
kubectl get services,endpointslices -A
kubectl get events -A --sort-by=.lastTimestamp
kubectl top nodes
kubectl get --raw /readyz
```

**Expected:** record the affected namespaces, nodes, zones, desired/available replicas and API readiness. If `kubectl top` is unavailable, log the monitoring gap; do not interpret missing metrics as zero usage.

### Evidence quality

- Preserve timestamps and timezone.
- Identify the exact object UID when Pods have been recreated.
- Prefer bounded logs and time-series views to unbounded output.
- Do not export Secret values or sensitive application payloads.
- Note the age and completeness of each signal.

## 7. Lab 3 — Investigate the failed rollout and image pull

```powershell
$ns = 'REPLACE_WITH_NAMESPACE'
$deployment = 'REPLACE_WITH_DEPLOYMENT'
kubectl -n $ns get deployment $deployment -o wide
kubectl -n $ns describe deployment $deployment
kubectl -n $ns rollout history deployment/$deployment
kubectl -n $ns get replicasets,pods -o wide
kubectl -n $ns get events --sort-by=.lastTimestamp
```

For an affected Pod:

```powershell
$pod = 'REPLACE_WITH_POD'
kubectl -n $ns describe pod $pod
kubectl -n $ns get pod $pod -o jsonpath='{range .spec.containers[*]}{.name}{" image="}{.image}{" policy="}{.imagePullPolicy}{"\n"}{end}'
kubectl -n $ns get pod $pod -o jsonpath='{range .status.containerStatuses[*]}{.name}{" waiting="}{.state.waiting.reason}{" message="}{.state.waiting.message}{"\n"}{end}'
```

### Hypotheses

| Hypothesis | Supporting evidence | Counter-evidence |
|---|---|---|
| Image tag does not exist | Manifest unknown Event | Registry confirms digest exists |
| Registry auth expired | Unauthorized Event | Same identity successfully pulls |
| Node egress broken | Pull timeouts on one subnet | Other registry traffic succeeds |
| Rollout config incompatible | Failure begins at new revision | Old revision shows same errors |

**Expected:** separate registry failures from application startup and readiness failures. Never print registry credentials.

## 8. Lab 4 — Investigate Pending Pods and node pressure

```powershell
kubectl get pods -A --field-selector=status.phase=Pending -o wide
kubectl describe node REPLACE_WITH_NODE
kubectl get nodes -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl top nodes
kubectl -n $ns get resourcequota,limitrange,pvc
```

### Decision matrix

| Symptom | Evidence | Next action |
|---|---|---|
| Pending with FailedScheduling | Insufficient CPU/memory, taint, affinity | Verify requests and eligible capacity |
| Pending after scheduling | Image, volume, CNI or runtime Events | Diagnose startup stage |
| Node MemoryPressure | Node condition and eviction messages | Check headroom and noisy neighbors |
| Node NotReady | Heartbeat/kubelet/cloud health | Check runtime/network/node state |
| Evicted Pod | Pod reason=Evicted | Identify node pressure and replacement |
| OOMKilled container | Last termination reason | Investigate container memory and limits |

**Expected:** do not conflate Pending with CrashLoopBackOff or container OOM with node eviction.

## 9. Lab 5 — Investigate CrashLoopBackOff and dependency health

```powershell
kubectl -n $ns get pod $pod -o wide
kubectl -n $ns describe pod $pod
kubectl -n $ns logs $pod --all-containers=true --previous --timestamps --tail=200
kubectl -n $ns logs $pod --all-containers=true --timestamps --since=30m --tail=200
```

### Interpret startup failure

1. Determine exit code and previous termination reason.
2. Check startup/liveness probe failures separately from readiness.
3. Inspect missing ConfigMap/Secret references without revealing values.
4. Correlate database connection errors with PostgreSQL availability and pool wait.
5. Determine whether the dependency is failing or the application is exhausting its own connection pool.
6. Confirm whether a rollout changed connection pool settings or retry behavior.

**Expected:** identify whether the crash loop is an application/configuration failure, dependency failure or resource/probe problem.

## 10. Lab 6 — Investigate DNS, Service routing and CNI

```powershell
kubectl -n $ns get services -o wide
kubectl -n $ns get endpointslices
kubectl -n $ns get networkpolicies
kubectl -n kube-system get pods -o wide
kubectl -n kube-system get services
kubectl -n kube-system logs deployment/coredns --since=15m --tail=200
```

CoreDNS deployment names may vary.

### Network hypothesis tests

- Does DNS fail for internal Service names, external names or both?
- Is the issue isolated to one node, zone or namespace?
- Does the Service have Ready endpoints?
- Do selectors and `targetPort` match application Pods?
- Are CNI agents healthy and Pod IPs assigned?
- Do NetworkPolicies permit intended DNS and application traffic?
- Is the upstream resolver or NAT/egress path saturated?

**Expected:** distinguish DNS lookup failure from successful resolution followed by TCP timeout. Avoid changing cluster DNS configuration based only on one timeout.

## 11. Lab 7 — Investigate control-plane and admission symptoms

```powershell
kubectl get --raw /readyz
kubectl get apiservices
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl get events -A --sort-by=.lastTimestamp
```

Review approved API-server metrics:

```promql
histogram_quantile(
  0.99,
  sum by (le, verb) (rate(apiserver_request_duration_seconds_bucket[5m]))
)
```

```promql
sum by (code, verb) (rate(apiserver_request_total{code=~"5.."}[5m]))
```

**Expected:** determine whether API latency is causal, coincident or secondary to incident-driven client retries. Managed EKS/AKS control-plane logs and etcd diagnostics may require cloud-provider tooling; do not assume direct host access.

## 12. Lab 8 — Build the incident evidence timeline

Use timestamps from Prometheus, logs, traces, Events and rollout metadata.

| UTC | Signal | Observation | Confidence | Source |
|---|---|---|---|---|
| 14:00 | Deployment | New image revision begins | High | Rollout history |
| 14:02 | Pod Event | Registry unauthorized | High | Describe Pod |
| 14:03 | Scheduler | Insufficient CPU for replacements | High | FailedScheduling |
| 14:04 | Node | MemoryPressure condition changes | High | Node status |
| 14:05 | App logs | DB connection acquisition timeouts | Medium | Previous logs |
| 14:06 | DNS | Intermittent lookup timeout | Medium | Resolver/log evidence |
| 14:07 | API metrics | Elevated p99 latency | Medium | Prometheus |

The table is a fictional training timeline. Replace with observed evidence when conducting a real exercise.

### Hypothesis register

```text
Hypothesis ID:
Proposed causal chain:
Supporting observations:
Contradictory observations:
Evidence gaps:
Safe test:
Result:
Confidence:
Owner:
```

**Expected:** at least three competing hypotheses and a documented reason to accept or reject each.

## 13. Lab 9 — Select mitigations with explicit change gates

### Candidate mitigations

| Confirmed condition | Potential mitigation | Gate |
|---|---|---|
| Registry auth failure | Repair approved image-pull identity | Credential owner, least privilege |
| Invalid rollout | Roll back compatible revision | Schema/API/data compatibility |
| Insufficient schedulable capacity | Add eligible nodes or correct requests | Cloud quota, cost, autoscaler |
| Node pressure | Reduce pressure or replace unhealthy node | PDB, quorum, volume safety |
| DB pool exhaustion | Reduce concurrency or fix pool/dependency | DB capacity and application owner |
| DNS/CNI failure | Restore failing component/path | Network change approval |
| Admission latency | Repair webhook backend | Security/platform approval |

**Never perform multiple uncontrolled changes simultaneously.** Capture before/after SLIs and state. A rollback may be unsafe after irreversible schema or data changes.

### Mitigation decision record

```text
Chosen action:
Evidence supporting action:
Expected customer benefit:
Blast radius:
Approver:
Pre-change state:
Rollback trigger:
Rollback procedure:
Success criteria:
Owner and timestamp:
```

## 14. Lab 10 — Optional isolated staging fault exercises

The following exercises are intentionally small and isolated. Do not deploy them to production or shared critical namespaces.

Save `ch065-staging.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch065
---
apiVersion: v1
kind: Pod
metadata:
  name: pending-demo
  namespace: ch065
spec:
  restartPolicy: Never
  nodeSelector:
    ch065.example.com/unavailable-node: "required"
  containers:
    - name: demo
      image: busybox:1.36
      command: ["/bin/sh", "-c", "sleep 300"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: crash-demo
  namespace: ch065
spec:
  restartPolicy: Always
  containers:
    - name: demo
      image: busybox:1.36
      command: ["/bin/sh", "-c", "echo ch065-failure; exit 42"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: bad-image-demo
  namespace: ch065
spec:
  restartPolicy: Never
  containers:
    - name: demo
      image: registry.k8s.io/pause:ch065-nonexistent-tag
      imagePullPolicy: Always
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
```

```powershell
kubectl apply -f .\ch065-staging.yaml
kubectl -n ch065 get pods -o wide
kubectl -n ch065 describe pod pending-demo
kubectl -n ch065 describe pod crash-demo
kubectl -n ch065 describe pod bad-image-demo
kubectl -n ch065 get events --sort-by=.lastTimestamp
kubectl -n ch065 logs crash-demo --previous --timestamps --tail=30
```

**Expected:** Pending due to unsatisfied node selector, repeated exit code 42 with restart backoff, and image pull failure. Registry reachability and runtime behavior can affect exact messages.

These exercises **do not simulate real node failure, DNS outage, DB saturation or control-plane degradation**. Those components must be tested through an approved tabletop or dedicated fault-injection environment.

## 15. Lab 11 — Recovery verification and monitoring

### Customer recovery

- HTTP 5xx ratio returns below the incident threshold.
- p95/p99 latency returns to the agreed SLO range.
- Traffic and request success are stable for an agreed observation window.
- No unresolved data integrity, backlog or delayed-write risk remains.

### Kubernetes recovery

```powershell
kubectl -n $ns get deployment $deployment -o wide
kubectl -n $ns get pods -o wide
kubectl -n $ns get endpointslices
kubectl get nodes -o wide
kubectl -n $ns get events --sort-by=.lastTimestamp
```

### Dependency and observability recovery

- PostgreSQL pool wait, connections and query latency normalize.
- DNS lookup error/timeout rates return to baseline.
- Prometheus targets and log/trace ingestion are healthy.
- Alertmanager incident state resolves without masking active impact.

**Expected:** distinguish “Pods are Ready” from “customer impact has ended.” Require independent customer-facing verification.

## 16. Lab 12 — Blameless RCA and corrective action project

### RCA template

```text
Title:
Incident ID:
Date / duration:
Customer impact:
Detection source and delay:
Incident severity:
Systems involved:
Timeline (UTC):
Primary triggering event:
Confirmed causal mechanism:
Contributing factors:
Why safeguards did not prevent impact:
Mitigation and recovery:
What worked well:
What could improve:
Evidence gaps / unknowns:
Corrective actions with owners and due dates:
Acceptance tests:
Review and approval:
```

### Corrective action examples

| Gap | Action | Acceptance evidence |
|---|---|---|
| Invalid image release | Verify digest and registry auth in CI | Failed release blocked |
| Insufficient rollout headroom | Capacity and surge scheduling test | Replacement replicas schedule |
| Unbounded DB retries | Backoff/jitter and connection budget | Load test |
| Missing DNS visibility | DNS latency/error dashboards | Alert exercise |
| Unclear incident ownership | On-call runbook and escalation | Tabletop sign-off |
| Incomplete telemetry | Target coverage and trace propagation checks | Acceptance report |

Avoid attributing incidents to individuals. Focus on system design, operating conditions, change controls and detection gaps.

## 17. Incident response roles and communication

| Role | Responsibility |
|---|---|
| Incident commander | Scope, priorities, decision log, escalation |
| Kubernetes lead | Workload, scheduler, node and control-plane diagnosis |
| Network/platform lead | CNI, DNS, ingress and cloud network |
| Application lead | Logs, probes, rollouts and code/config |
| DBRE | PostgreSQL/Redis/Kafka health, data safety and dependency capacity |
| Communications owner | Stakeholder updates and incident chronology |
| Scribe | Timestamped decisions, evidence and action items |

### Example update structure

```text
Time (UTC):
Customer impact:
Current severity:
What we know:
What remains uncertain:
Mitigation underway:
Risks and approvals:
Next update:
```

Do not communicate an unverified root cause as confirmed.

## 18. Final capstone acceptance matrix

| Test | Pass criterion | Evidence |
|---|---|---|
| Incident declaration | Impact, scope and severity documented | Intake record |
| Baseline | Cluster, workloads, nodes and Events captured | Snapshot |
| Image/startup diagnosis | Waiting reason and registry/config evidence classified | Pod investigation |
| Pending/pressure diagnosis | Scheduler, node and memory evidence separated | Event/metric matrix |
| DNS/network diagnosis | Resolver versus Service/CNI failure distinguished | Network worksheet |
| Control plane | API/admission health assessed | API metrics and checks |
| Correlation | Timestamped evidence and competing hypotheses | Timeline/register |
| Safe mitigation | Owner, approval, rollback and blast radius | Change record |
| Recovery | Customer SLIs and infrastructure verified | Before/after evidence |
| RCA | Blameless causal analysis and action owners | RCA report |
| Staging lab | Isolated exercises completed or marked not run | Lab evidence |
| Review | Independent technical review recorded | Sign-off |

Mark each row **Pass**, **Fail**, **Not run** or **Not applicable**, with timestamp, owner and evidence link. A tabletop pass does not imply live runtime validation.

## 19. Troubleshooting and decision pitfalls

| Pitfall | Why it fails | Correct practice |
|---|---|---|
| Restarting all Pods | Destroys evidence and capacity | Classify failure first |
| Treating a recent rollout as proven cause | Confuses correlation with causation | Compare revisions and timelines |
| Raising all memory limits | Can worsen scheduling/eviction | Analyze actual memory behavior |
| Deleting Evicted Pods immediately | Loses useful status evidence | Capture reason and node pressure |
| Ignoring DB pool waits | Misattributes dependency latency | Compare trace and DB metrics |
| Disabling admission security | Introduces security exposure | Escalate with controlled approval |
| Draining unhealthy node blindly | Risks stateful quorum and PDB | Validate durability and disruption |
| Trusting a single dashboard | Missing targets can hide impact | Cross-check independent signals |
| Declaring success at Pod Ready | Customer errors may persist | Verify end-to-end SLIs |

## 20. Project submission and handover checklist

- [ ] Incident scope, severity and roles established.
- [ ] Cluster context and baseline evidence preserved.
- [ ] Image pull, container startup and rollout symptoms investigated.
- [ ] Pending, Evicted, OOMKilled and CrashLoopBackOff differentiated.
- [ ] Node, DNS, Service, CNI and control-plane failure paths reviewed.
- [ ] Dependency latency and database safety assessed.
- [ ] Metrics, logs, Events and traces correlated.
- [ ] At least three competing hypotheses tested or documented.
- [ ] Approved mitigation and rollback criteria recorded.
- [ ] Customer SLIs, endpoints and dependency recovery verified.
- [ ] Blameless RCA, action owners and acceptance tests documented.
- [ ] Isolated staging exercise completed or explicitly marked not run.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Part 13 writing milestone:** Chapters 061–065 drafted. Runtime validation and independent technical review remain pending.

## 21. Cleanup

Only remove resources created for this chapter in the approved staging cluster:

```powershell
kubectl -n ch065 get pods
kubectl delete namespace ch065
```

Do not delete production resources, cluster-system Pods, incident evidence or monitoring data.

## 22. References

- [Kubernetes Troubleshooting](https://kubernetes.io/docs/tasks/debug/)
- [Debug Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)
- [Debug Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/)
- [Debug Cluster](https://kubernetes.io/docs/tasks/debug/debug-cluster/)
- [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Kubernetes Observability](https://kubernetes.io/docs/concepts/cluster-administration/observability/)
- [DNS Debugging](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/)

**Next:** Chapter 066 — Horizontal Pod Autoscaler (Part 14).
