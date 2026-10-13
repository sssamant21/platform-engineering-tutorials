# Chapter 056 — Kubernetes Metrics, Logs and Events

**Track:** Kubernetes Administration · **Part 12 — Observability and Monitoring**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapters 016–020, 021–025, 046–055; kubectl, Windows PowerShell; read-only cluster access; approved isolated staging namespace for the optional failure lab

## 1. Production scenario

A production API shows intermittent 5xx errors and high p95 latency. Some Pods restart with OOMKilled, new Pods remain Pending, and one node reports MemoryPressure. The SRE needs a defensible incident timeline that correlates container resource usage, application logs, kubelet/scheduler Events, and infrastructure metrics without confusing correlation with causation.

**Goal:** establish a repeatable Kubernetes triage workflow, distinguish metric/log/Event data models, gather evidence safely, and build observability acceptance criteria for production incidents.

### Learning objectives

1. Identify Kubernetes resource, component and application metric sources.
2. Explain Metrics Server versus Prometheus and monitoring backends.
3. Inspect container and previous-container logs safely.
4. Use Kubernetes Events to investigate scheduling, probes, volume and image failures.
5. Correlate timestamps, namespaces, nodes, Pods and deployment revisions.
6. Diagnose CPU throttling, memory OOM, restarts and scheduling pressure.
7. Design production monitoring, retention, alerting and incident evidence standards.

## 2. Observability architecture

```text
Application / Pod / Node / Control plane
              |       |        |
           Metrics   Logs    Events
              |       |        |
   Metrics Server   Log agents  Kubernetes API
     (kubectl top)    |             |
              |    Log backend   Event collector
              |       |             |
        Prometheus / Grafana / APM / alerting
                        |
             Correlated incident timeline
```

**Important:** Metrics Server primarily supplies short-term CPU/memory resource metrics for autoscaling and `kubectl top`; it is **not** a long-term metrics database or a substitute for Prometheus. Prometheus scraping and retention are separate responsibilities. Events are best-effort, short-lived diagnostic records, not durable audit logs.

| Signal | Answers | Common source | Limitation |
|---|---|---|---|
| Metrics | How much, how often, how fast? | kubelet, cAdvisor, components, apps | Sampling and cardinality |
| Logs | What did a process report? | Container stdout/stderr, node journals | Missing context, rotation |
| Events | What noteworthy Kubernetes transition occurred? | Scheduler, kubelet, controllers | TTL, aggregation, best effort |
| Traces | Where was request time spent? | OpenTelemetry/APM | Requires instrumentation |
| Audit logs | Who called the API and what was allowed? | API audit pipeline | Different from Events; access-controlled |

## 3. Safety and access prerequisites

Core labs are read-only. Do not dump entire cluster logs or Secret values into tickets. Mask credentials, patient information, tokens and identifiers. Restrict `kubectl logs`, `kubectl describe` and monitoring queries to approved namespaces and workloads.

```powershell
kubectl config current-context
kubectl version
kubectl get nodes -o wide
kubectl auth can-i get pods -A
kubectl auth can-i get pods/log -n default
kubectl auth can-i list events -A
```

**Expected:** known context and sufficient least-privilege access. If an API call is denied, record the RBAC gap and request scoped permissions rather than escalating to cluster-admin by default.

## 4. Lab 1 — Build a baseline cluster health snapshot

```powershell
Get-Date -Format o
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get deployments,statefulsets,daemonsets -A
kubectl get events -A --sort-by=.lastTimestamp
kubectl get --raw /readyz
```

**Expected:** current health, workload placement, control-plane reachability and recent Events. `lastTimestamp` can be absent for newer Event representations; also inspect `eventTime`, `series.lastObservedTime` and `metadata.creationTimestamp` where relevant.

### Evidence requirements

- Record investigation start and end time with timezone.
- Capture cluster/context, namespace, workload and node identity.
- Separate currently failing Pods from historical Events.
- Record whether the API itself was reachable.
- Avoid assuming a single snapshot establishes a trend.

## 5. Lab 2 — Inspect CPU and memory metrics

```powershell
kubectl top nodes
kubectl top pods -A
kubectl top pods -n kube-system --containers
kubectl get nodes -o wide
```

**Expected:** recent CPU and memory usage if Metrics Server and its API are functioning. If `kubectl top` fails, verify metrics API availability and use the organization's approved monitoring platform.

```powershell
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl describe apiservice v1beta1.metrics.k8s.io
kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes
```

**Important:** `kubectl top` shows measured resource usage, **not** CPU throttling, memory limits, historical p95, or guaranteed node headroom. Compare usage with requests, limits, capacity and allocatable resources.

### Node pressure interpretation

| Signal | What to check | Typical consequence |
|---|---|---|
| CPU saturation | Node CPU, per-container usage, throttling | High latency |
| MemoryPressure | Node condition, working set, eviction | Pod eviction / OOM |
| DiskPressure | Filesystem, imagefs/nodefs, inode use | Evictions, image failures |
| PIDPressure | Node PID usage | Process creation failure |
| Network pressure | Drops, retransmits, DNS, CNI | Timeouts and connection failures |

## 6. Lab 3 — Inspect application logs and restarts

Select an approved namespace and Pod:

```powershell
$ns = 'REPLACE_WITH_NAMESPACE'
$pod = 'REPLACE_WITH_POD'
kubectl -n $ns get pod $pod -o wide
kubectl -n $ns describe pod $pod
kubectl -n $ns logs $pod --all-containers=true --since=30m --timestamps --tail=200
kubectl -n $ns logs $pod --all-containers=true --previous --timestamps --tail=100
```

**Expected:** current and previous container logs when available. `--previous` is only useful if the runtime retains a terminated container instance. For multi-container Pods, narrow to `-c CONTAINER` if logs are too large or sensitive.

### Restart diagnosis

```powershell
kubectl -n $ns get pod $pod -o jsonpath='{range .status.containerStatuses[*]}{.name}{" restarts="}{.restartCount}{" lastReason="}{.lastState.terminated.reason}{" lastExit="}{.lastState.terminated.exitCode}{"`n"}{end}'
```

**Interpretation:** `OOMKilled` indicates a memory-related termination, but distinguish container memory-limit enforcement from node memory pressure and eviction. A nonzero exit code alone does not establish root cause. Compare application logs, kubelet Events and metrics before concluding.

## 7. Lab 4 — Analyze Kubernetes Events

```powershell
kubectl get events -A --sort-by=.lastTimestamp
kubectl -n $ns get events --field-selector involvedObject.name=$pod
kubectl -n $ns describe pod $pod
kubectl -n $ns get events -o yaml
```

**Expected:** scheduling, image pull, probe, eviction, mount and restart clues where still retained. Event schemas vary between core/v1 and events.k8s.io/v1, and Events can be aggregated or expired.

| Event/reason | Investigation path |
|---|---|
| FailedScheduling | Requests, taints, affinity, topology, PVC, quotas |
| BackOff | Container crash and restart logs |
| Unhealthy | Probe path, timeout, dependency, CPU pressure |
| FailedMount | CSI, PVC, PV zone affinity, credentials |
| FailedPull / ImagePullBackOff | Registry, auth, image reference, network |
| Evicted | Node pressure, eviction threshold |
| Killing | Lifecycle termination reason and controller actions |

**Caution:** an Event describes an observed condition, not necessarily the root cause. A `FailedScheduling` Event can coexist with an independent application error.

## 8. Lab 5 — Correlate workload, node and controller evidence

```powershell
kubectl -n $ns get deployment -o wide
kubectl -n $ns get replicasets
kubectl -n $ns get pods -o wide
kubectl get node REPLACE_WITH_NODE -o yaml
kubectl get events -A --sort-by=.lastTimestamp
```

**Expected:** map a failing Pod to its owning ReplicaSet/Deployment, node, rollout revision and resource pressure. For production evidence, prefer targeted `kubectl describe node` or selected JSONPath over collecting full Node YAML if it contains unnecessary metadata.

### Timeline example

| Time (UTC) | Evidence | Interpretation |
|---|---|---|
| 10:02 | Deployment revision changed | Candidate triggering change |
| 10:03 | Pods start failing readiness | Traffic capacity decreases |
| 10:04 | Node CPU saturation rises | Possible contention |
| 10:05 | App p95 increases and 5xx rise | Customer-visible impact |
| 10:06 | Pods restart | Consequence or additional cause |

**Expected:** a hypothesis with timestamps and cross-signal support. Do not claim causation merely because two metrics moved at the same time.

## 9. Lab 6 — Investigate a scheduling and resource-pressure incident

**Scenario:** a Deployment has two Pending Pods, one existing Pod is OOMKilled, and a node has MemoryPressure. Perform read-only triage:

```powershell
kubectl get pods -A --field-selector=status.phase=Pending -o wide
kubectl get nodes -o wide
kubectl describe node REPLACE_WITH_NODE
kubectl get events -A --sort-by=.lastTimestamp
kubectl top nodes
kubectl top pods -A --containers
```

### Required decisions

1. Determine whether Pending Pods are blocked by memory requests, taints, affinity, quota, PV or image issues.
2. Inspect actual memory usage, memory limits, restarts and node pressure.
3. Check for recent rollout, batch-job or autoscaler changes.
4. Distinguish OOMKilled from eviction and application crash.
5. Determine whether capacity expansion, workload rollback, right-sizing or traffic mitigation is safest.
6. Verify error rate, latency and Ready endpoints after remediation.

**Expected:** an incident triage record with evidence and a safe remediation decision; do not increase limits or delete Pods blindly.

## 10. Lab 7 — Isolated observability failure demonstration

**Optional staging-only exercise.** Create a namespace and a deliberately failing Pod to observe Events and logs. Save `ch056-failure.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch056
---
apiVersion: v1
kind: Pod
metadata:
  name: intentional-failure
  namespace: ch056
spec:
  restartPolicy: Always
  containers:
    - name: demo
      image: busybox:1.36
      command: ["/bin/sh", "-c", "echo 'simulated application failure'; exit 42"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
```

```powershell
kubectl apply -f .\ch056-failure.yaml
kubectl -n ch056 get pods -w
kubectl -n ch056 describe pod intentional-failure
kubectl -n ch056 logs intentional-failure -c demo --previous --timestamps --tail=30
kubectl -n ch056 get events --sort-by=.lastTimestamp
```

**Expected:** container exits with code 42, restarts under `Always`, and eventually shows BackOff/CrashLoopBackOff behavior. Exact timing and Event aggregation vary. This is a **simulated application crash**, not an OOM or node-failure test.

Clean up after collecting evidence:

```powershell
kubectl delete namespace ch056
```

## 11. Metrics collection architecture and retention

### Metrics Server

Provides resource metrics for HPA/VPA integrations and `kubectl top` where configured. It is not a full observability backend.

### Prometheus

Scrapes instrumented application, node, kube-state-metrics and control-plane endpoints where exposed. Supports time-series queries and alert rules. Design labels, scrape intervals, retention and remote storage for scale and cost.

### kube-state-metrics

Exposes Kubernetes object-state metrics (desired replicas, Pod phases, resource requests and other API object status). It does **not** replace node resource metrics or application request instrumentation.

### Log aggregation

Use a supported collector (for example Fluent Bit, Vector or OpenTelemetry Collector) to forward container logs to a centralized backend. Define log rotation, retention, indexing, access control, redaction and ingestion-failure monitoring.

### Events

Use Event collectors/exporters if longer history is required. Events are ephemeral and best-effort, so they should complement, not replace, durable monitoring and audit logs.

## 12. Production alerting and dashboards

| Layer | Recommended signal | Alerting objective |
|---|---|---|
| API server | Request errors/latency | Detect control-plane unavailability |
| Node | Ready, pressure, CPU/memory, filesystem | Detect resource and scheduling risk |
| Workload | Ready versus desired replicas, restart trend | Detect availability regression |
| Application | Request success, p95/p99, queue depth | Detect customer impact |
| Scheduling | Pending Pods, unschedulable reasons | Detect capacity/configuration failures |
| Storage | PV capacity, CSI failures, latency | Detect mount and I/O incidents |
| Logs | Collector backlog/drop rate | Detect blind spots |
| Events | Critical reasons and trends | Enrich diagnosis |

Set thresholds from measured baselines, service SLOs and error budgets. Avoid paging on every transient restart or Warning Event; alert on sustained customer-impacting conditions and actionable infrastructure failures.

## 13. Troubleshooting matrix

| Symptom | Metrics | Logs | Events / other |
|---|---|---|---|
| Pod OOMKilled | Working set and limit | Previous container | Last termination reason |
| High CPU latency | CPU and throttling | Request timing | Node pressure if any |
| Pods Pending | Allocatable and requests | Scheduler logs if accessible | FailedScheduling |
| Pod CrashLoopBackOff | Restart count | Previous container | BackOff |
| ImagePullBackOff | Registry/network | Runtime/kubelet | FailedPull |
| PVC mount failure | CSI and storage metrics | CSI controller/node | FailedMount |
| Probe failures | App latency and CPU | App startup/errors | Unhealthy |
| API timeout | API latency/error | API/controller logs | Independent control-plane metrics |

## 14. Incident investigation runbook

### Phase A — Scope

1. Confirm incident window, timezone, cluster, namespace, workload and customer impact.
2. Record current API health and node/workload status.
3. Identify recent changes and known batch/maintenance windows.

### Phase B — Correlate

1. Compare application SLIs with infrastructure metrics.
2. Review current and previous container logs with timestamps.
3. Inspect Pod/Node Events and controller conditions.
4. Map affected Pods to nodes, zones, ReplicaSets and PVCs.
5. Form competing hypotheses and gather discriminating evidence.

### Phase C — Mitigate

1. Choose the lowest-risk mitigation supported by evidence.
2. Protect stateful quorum and avoid blind force deletion.
3. Validate application request success, latency, readiness and data safety.
4. Continue monitoring after recovery and record unresolved risks.

### Phase D — Close

Capture timeline, contributing factors, root-cause confidence, missing telemetry, follow-up owners and SLO impact. Maintain a blameless distinction between observed facts and hypotheses.

## 15. Acceptance checklist

- [ ] Cluster context and investigation window recorded.
- [ ] Metrics Server availability and limitations understood.
- [ ] CPU/memory usage compared with requests and limits.
- [ ] Current and previous container logs inspected safely.
- [ ] Events interpreted with retention and aggregation limitations.
- [ ] Pod restarts, OOM, eviction and scheduling errors distinguished.
- [ ] Application, Node and controller evidence correlated.
- [ ] Isolated failure lab completed or explicitly marked not executed.
- [ ] Monitoring, log retention and access controls documented.
- [ ] Alerting mapped to SLIs/SLOs and actionable conditions.
- [ ] Incident runbook and evidence package produced.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 16. References

- [Kubernetes Observability](https://kubernetes.io/docs/concepts/cluster-administration/observability/)
- [Resource Metrics Pipeline](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)
- [kubectl top](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_top/)
- [kubectl logs](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_logs/)
- [Debug Running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/)
- [Kubernetes Events](https://kubernetes.io/docs/reference/kubernetes-api/cluster-resources/event-v1/)
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)

**Next:** Chapter 057 — Metrics Server and Prometheus.