# Chapter 057 — Metrics Server and Prometheus

**Track:** Kubernetes Administration · **Part 12 — Observability and Monitoring**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapter 056; kubectl, Windows PowerShell; read-only access to Metrics API and an approved Prometheus endpoint if available

## 1. Production scenario

An API's p95 latency rises during a batch workload. `kubectl top` shows modest CPU use, yet the application reports throttling and memory pressure. Meanwhile, a Prometheus dashboard has missing data for one node because a scrape target is down. The SRE must distinguish short-term resource metrics from historical time series, validate scrape health and use PromQL to correlate application impact with infrastructure behavior.

**Goal:** understand Metrics Server, Prometheus, kube-state-metrics and the metrics pipeline; execute safe diagnostics; design production-grade recording rules, alerts and monitoring acceptance criteria.

### Learning objectives

1. Explain the Kubernetes resource metrics pipeline and Metrics API.
2. Diagnose Metrics Server health and `kubectl top` failures.
3. Explain Prometheus pull-based scraping, service discovery, labels, TSDB and retention.
4. Differentiate node-exporter, kubelet/cAdvisor, kube-state-metrics and application metrics.
5. Write PromQL for CPU usage, throttling, memory, Pod readiness and restart trends.
6. Detect missing targets and stale data without misinterpreting zero values.
7. Design reliable metrics collection, alerting and production troubleshooting runbooks.

## 2. Metrics architecture

```text
                    Kubernetes cluster
  +--------------------------------------------------+
  | kubelet / cAdvisor  application /metrics         |
  | kube-state-metrics  node-exporter  API components |
  +-------------------------+------------------------+
                            |
                   Prometheus scrape
                            |
              TSDB / rules / remote write
                            |
                 Grafana / Alertmanager

  kubelet resource metrics
             |
       Metrics Server
             |
      metrics.k8s.io API
             |
     kubectl top / HPA
```

**Key distinction:** Metrics Server is a lightweight, recent CPU/memory resource metrics provider, not a long-term monitoring database. Prometheus is a time-series monitoring system; it does not automatically replace Metrics Server for Kubernetes resource-metrics-based HPA. Custom/external metrics autoscaling needs separately configured adapters or integrations.

## 3. Component responsibilities

| Component | Main role | Common operational question |
|---|---|---|
| Metrics Server | Aggregate kubelet resource metrics for Metrics API | Why does `kubectl top` fail? |
| kubelet/cAdvisor | Container CPU, memory and filesystem metrics | Is the container throttled or memory-constrained? |
| node-exporter | Host OS metrics | Is disk I/O or host network saturated? |
| kube-state-metrics | Kubernetes object-state metrics | Are desired and Ready replicas diverging? |
| Prometheus | Scrape, store and query time series | What changed over the incident window? |
| Alertmanager | Route, group and silence alerts | Who should be paged and when? |
| Grafana | Visualize and correlate metrics | How did latency, CPU and restarts change? |

Metrics exposure and names vary by Kubernetes version, container runtime, managed provider and installed exporters. Do not assume all component metrics are accessible on managed EKS/AKS/GKE clusters.

## 4. Safety and prerequisites

Core labs are read-only. Do not deploy monitoring agents or expose metrics endpoints to the internet in production without change approval. Prometheus endpoints can reveal internal topology, workloads and labels; use least-privilege authentication and approved network paths.

```powershell
kubectl config current-context
kubectl version
kubectl get nodes -o wide
kubectl auth can-i get --raw /apis/metrics.k8s.io/v1beta1/nodes
kubectl get namespaces
```

The `kubectl auth can-i` raw-path syntax may vary with client version and policy; if rejected, check scoped API permissions through the standard SelfSubjectAccessReview workflow.

## 5. Lab 1 — Verify Metrics Server and Metrics API

```powershell
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl describe apiservice v1beta1.metrics.k8s.io
kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes
kubectl top nodes
kubectl top pods -A
```

**Expected:** an available APIService and current CPU/memory readings. If Metrics Server is not installed or accessible, record the gap rather than treating it as a node outage.

### Troubleshooting path

1. Confirm APIService availability and backend Service/Endpoints.
2. Identify the Metrics Server namespace and Deployment if installed.
3. Inspect Pod readiness and recent logs with appropriate permissions.
4. Check Metrics Server-to-kubelet connectivity, TLS and certificate trust.
5. Check aggregation-layer authentication and APIService registration.
6. Recheck `kubectl top` and HPA metrics after remediation.

Avoid bypassing kubelet certificate validation as a default production fix; correct certificate trust and address selection.

## 6. Lab 2 — Compare resource usage with requests and limits

```powershell
kubectl top nodes
kubectl top pods -A --containers
kubectl get nodes -o wide
kubectl describe node REPLACE_WITH_NODE
kubectl -n REPLACE_WITH_NAMESPACE describe pod REPLACE_WITH_POD
```

**Expected:** distinguish instantaneous usage from resource requests/limits, allocatable node capacity and eviction conditions.

| Signal | Meaning | Pitfall |
|---|---|---|
| CPU usage | Recent consumed CPU | Does not directly reveal throttling |
| Memory usage | Recent reported memory metric | Not equivalent to RSS, limit or peak |
| CPU request | Scheduling and CPU-share input | Not a usage cap |
| CPU limit | CPU quota enforcement | Can throttle bursty apps |
| Memory request | Scheduling reservation | Not a hard memory cap |
| Memory limit | Container memory boundary | Exceeding can cause OOM kill |

### Incident question

If `kubectl top` reports 400m CPU on a container with a 500m CPU limit, could throttling still occur? **Yes.** Short bursts can hit quota despite modest averaged usage. Use cumulative throttling counters and `rate()` over a suitable window.

## 7. Lab 3 — Discover Prometheus installation and targets

```powershell
kubectl get pods -A | Select-String 'prometheus|metrics|exporter'
kubectl get services -A | Select-String 'prometheus|metrics'
kubectl get servicemonitors,podmonitors -A
```

**Expected:** discover monitoring resources if installed. `ServiceMonitor` and `PodMonitor` are **Prometheus Operator CRDs**, not built-in Kubernetes objects; the last command may return `the server doesn't have a resource type` when the operator is absent.

With an **approved Prometheus URL**, use its Targets page or API:

```powershell
$prom = 'https://REPLACE_WITH_APPROVED_PROMETHEUS'
# Supply approved authentication through your organization's normal tooling.
# Example only for an already authenticated endpoint:
Invoke-RestMethod -Uri "$prom/api/v1/targets?state=active"
```

**Expected:** inspect `health`, `lastScrape`, `lastError`, target labels and scrape URL. Do not assume a scrape target is healthy solely because its Pod is Running.

### Scrape failure checklist

- Service discovery and label selectors.
- Endpoint IP, port, scheme and metrics path.
- NetworkPolicy, TLS, auth and certificates.
- Exporter readiness and scrape timeout.
- Relabeling rules and dropped targets.
- Resource pressure or excessive metric cardinality.

## 8. Lab 4 — Query basic PromQL and target health

Use an approved Prometheus UI or authenticated API. Queries below are examples and assume standard exporter metric names.

```promql
up
count by (job) (up)
sum by (job) (up == 0)
scrape_duration_seconds
scrape_samples_scraped
prometheus_tsdb_head_series
```

**Interpretation:** `up == 0` identifies scraped targets that failed; a target missing entirely from service discovery may not appear as zero. Combine Prometheus target discovery, absent-series alerts and infrastructure inventory to detect monitoring blind spots.

### Query through PowerShell

```powershell
$query = [uri]::EscapeDataString('up')
Invoke-RestMethod -Uri "$prom/api/v1/query?query=$query"
```

**Expected:** a JSON vector of target status when authentication and network access permit. For incident time windows, use `/api/v1/query_range` with explicit UTC timestamps, step and query.

## 9. Lab 5 — CPU, throttling and memory PromQL

### CPU usage (cores)

```promql
sum by (namespace, pod, container) (
  rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m])
)
```

### CPU throttling ratio (throttled periods / total periods)

```promql
sum by (namespace, pod, container) (
  rate(container_cpu_cfs_throttled_periods_total{container!=""}[5m])
)
/
clamp_min(
  sum by (namespace, pod, container) (
    rate(container_cpu_cfs_periods_total{container!=""}[5m])
  ),
  1e-9
)
```

This ratio is the fraction of CFS periods that experienced throttling, **not** the fraction of CPU time lost. Metric availability and labels vary by runtime and exporter version.

### Memory working set

```promql
sum by (namespace, pod, container) (
  container_memory_working_set_bytes{container!="",image!=""}
)
```

### Container restart increase

```promql
sum by (namespace, pod) (
  increase(kube_pod_container_status_restarts_total[15m])
)
```

**Expected:** compare CPU throttling, memory pressure and restart trends with application latency and error-rate metrics. Do not use a single point sample to infer incident causality.

## 10. Lab 6 — Workload availability and scheduling PromQL

### Desired versus available replicas

```promql
kube_deployment_spec_replicas
-
kube_deployment_status_replicas_available
```

### Pending Pods

```promql
sum by (namespace) (
  kube_pod_status_phase{phase="Pending"} == 1
)
```

### Node readiness

```promql
kube_node_status_condition{condition="Ready",status="true"} == 0
```

**Caution:** the node readiness expression above returns zero-valued samples for Ready nodes, not a filtered set of unready nodes. To filter to not-ready nodes, compare with `== bool 0` only when you explicitly want a 0/1 result, or use `kube_node_status_condition{condition="Ready",status="true"} == 0` in an alert condition where only matching non-ready series should remain. Verify kube-state-metrics labels and scrape completeness before trusting a dashboard.

### Requests versus usage

```promql
sum by (namespace) (
  kube_pod_container_resource_requests{resource="cpu",unit="core"}
)
```

Combine object-state metrics with measured CPU/memory to assess scheduling reservations and overcommit. Some kube-state-metrics releases differ in resource metric exposure; verify against the installed version.

## 11. Lab 7 — Monitoring gap and incident tabletop

**Scenario:** a node exporter target disappears from Prometheus discovery at 14:03 UTC, while the API's p95 latency increases at 14:05 UTC. Metrics Server continues to serve `kubectl top` data. A dashboard shows an apparent reduction in total node CPU.

### Required investigation

1. Verify whether the missing target is down or undiscovered.
2. Inspect `up`, `absent()`/inventory checks and target health.
3. Confirm whether aggregate CPU dropped only because a node series vanished.
4. Compare `kubectl top` with Prometheus node/container metrics.
5. Check exporter Service/Endpoint, network policy, TLS and scrape errors.
6. Correlate application latency, request errors and deployment changes.
7. Restore observability and annotate the dashboard's missing-data interval.
8. Document whether customer impact and monitoring failure have a common cause.

**Expected:** do not report improved CPU capacity based on incomplete telemetry. Distinguish missing data from a genuine zero value.

## 12. Prometheus collection and scaling architecture

### Service discovery

Prometheus can discover targets through Kubernetes API metadata and, with Prometheus Operator, `ServiceMonitor`, `PodMonitor` and `Probe` resources. The Operator's CRDs require correct namespace selectors, label selectors and RBAC.

### Retention and capacity

Estimate time-series cardinality, samples per second, scrape interval, retention, WAL/storage growth and query load. High-cardinality labels such as request IDs or user IDs can cause severe TSDB memory and storage pressure. Prefer bounded labels and aggregation.

### HA and remote storage

Two Prometheus replicas improve scrape/alert availability but do not automatically provide deduplicated long-term storage. Remote write/long-term storage systems require their own availability, ingestion lag, retention and query consistency design.

### Security

Use TLS/authentication, least-privilege Kubernetes discovery permissions, network isolation and restricted dashboard access. Never expose unprotected metrics endpoints containing sensitive labels.

## 13. Production alerts and recording rules

### Illustrative Prometheus alert rules

```yaml
groups:
  - name: kubernetes-observability
    rules:
      - alert: PrometheusTargetDown
        expr: up == 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Prometheus target is down"
          description: "Scrape failed for job={{ $labels.job }} instance={{ $labels.instance }}"
      - alert: DeploymentUnavailableReplicas
        expr: kube_deployment_spec_replicas - kube_deployment_status_replicas_available > 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Deployment has unavailable replicas"
```

These are **examples**, not universally production-ready rules. Scope by namespace, workload criticality, expected maintenance and scrape health; avoid duplicate pages and false alerts from intentionally scaled-down Deployments.

### Recording-rule examples

```yaml
groups:
  - name: workload-recording
    interval: 30s
    rules:
      - record: namespace_pod:container_cpu_usage_cores:rate5m
        expr: sum by (namespace, pod) (rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m]))
```

Validate expressions with `promtool check rules` where available and test alert behavior before deployment.

## 14. Troubleshooting matrix

| Symptom | Candidate cause | Safe checks |
|---|---|---|
| `kubectl top` unavailable | Metrics API/Server unhealthy | APIService, Metrics Server logs |
| Metrics API 503 | Aggregation or backend issue | APIService conditions, TLS, endpoints |
| Prometheus target DOWN | Exporter/network/auth | Targets API, Service, NetworkPolicy |
| Missing metrics | Discovery/relabeling/retention | Target inventory, `absent()`, labels |
| High CPU throttling | Tight CPU limit | CFS throttling ratio and usage |
| Memory near limit | Workload pressure | Working set, OOM, node condition |
| Prometheus OOM | High cardinality/query load | TSDB series, memory, queries |
| Slow PromQL | Expensive cardinality/range | Query plan, aggregation, retention |
| Alert not firing | Rule evaluation/routing | Rule status, Alertmanager, silence |
| False low CPU aggregate | Missing target | Scrape completeness and inventory |

## 15. Incident runbook

### Detect

1. Confirm application/customer SLIs and investigation window.
2. Verify Metrics API and Prometheus health separately.
3. Identify missing targets, stale series and scrape failures.

### Correlate

1. Compare CPU/memory, throttling, restarts and scheduling metrics.
2. Inspect workload/Node Events and application logs.
3. Match Pod, Node, namespace, zone and deployment revision labels.
4. Form and test competing root-cause hypotheses.

### Mitigate

1. Fix scrape visibility gaps without masking customer-impacting incidents.
2. Remediate proven resource/capacity constraints using approved changes.
3. Validate application request success, latency and data safety.
4. Confirm telemetry and alerting recover after mitigation.

### Close

Record SLI impact, monitoring blind spots, query/rule changes, ownership and follow-up capacity actions.

## 16. Acceptance checklist

- [ ] Metrics Server and Prometheus roles distinguished.
- [ ] Metrics API health and `kubectl top` verified.
- [ ] Resource usage compared with requests, limits and allocatable.
- [ ] Prometheus targets and scrape health inspected.
- [ ] PromQL for CPU, throttling, memory and restarts reviewed.
- [ ] kube-state-metrics object-state queries validated.
- [ ] Missing-series versus zero-value behavior understood.
- [ ] Monitoring gap incident tabletop completed.
- [ ] Retention, cardinality, security and HA architecture reviewed.
- [ ] Alert and recording rules checked against actual metric labels.
- [ ] Incident runbook and SLO acceptance documented.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 17. References

- [Kubernetes Resource Metrics Pipeline](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)
- [Metrics Server](https://github.com/kubernetes-sigs/metrics-server)
- [Prometheus Overview](https://prometheus.io/docs/introduction/overview/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Prometheus Functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Prometheus Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [kube-state-metrics](https://github.com/kubernetes/kube-state-metrics)
- [Prometheus Operator](https://prometheus-operator.dev/)

**Next:** Chapter 058 — Grafana Dashboards and Alertmanager.
