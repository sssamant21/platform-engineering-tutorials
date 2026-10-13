# Chapter 060 — Production Observability and Alerting Project

**Track:** Kubernetes Administration · **Part 12 — Observability and Monitoring (final capstone)**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, platform engineers, on-call responders  
**Prerequisites:** Chapters 056–059; Kubernetes staging cluster, Windows PowerShell, approved monitoring endpoints, RBAC access

## 1. Production scenario and capstone objective

A customer-facing Kubernetes API reports elevated p95 latency, intermittent HTTP 5xx errors and Pod restarts. A Prometheus target disappears, making an aggregate CPU dashboard misleading. At the same time, application traces show a slow database dependency, while Alertmanager sends duplicate pages.

**Goal:** design, validate and operate an end-to-end observability system that combines Kubernetes Events, logs, Metrics Server, Prometheus, Grafana, Alertmanager and OpenTelemetry. Demonstrate that it can detect customer impact, identify telemetry gaps, correlate a request across components, route actionable alerts and support a safe incident response.

### Project deliverables

1. Architecture and telemetry source inventory.
2. SLI/SLO definitions and ownership.
3. Prometheus target and metric-quality acceptance report.
4. Grafana dashboard specification.
5. Alert rules, routing and notification test evidence.
6. Trace/log/Event correlation workflow.
7. Controlled failure-simulation results and incident timeline.
8. Production runbook, data-handling controls and handover checklist.

## 2. Reference architecture

```text
                         Customer requests
                                |
                        Ingress / Gateway
                                |
                   Application API / workers
                         |             |
                    PostgreSQL      Queue/Cache
                         |
          +--------------+------------------+
          |              |                  |
        Metrics         Logs             Traces
          |              |                  |
   kubelet/cAdvisor   Log agent        OTel SDK
   node-exporter         |                 |
   kube-state-metrics  Log backend    OTel Collector
          |              |                 |
       Prometheus        |            Trace backend
          |              |                 |
       Grafana <---------+-----------------+
          |
   Prometheus alert rules
          |
      Alertmanager
          |
    Approved on-call routes

   Kubernetes Events -> Event collector / incident timeline
   Metrics Server -> metrics.k8s.io -> kubectl top / HPA
```

**Architecture boundaries:** Metrics Server is not a historical monitoring backend; Kubernetes Events are not durable audit logs; Prometheus does not automatically capture application logs or traces; Grafana can have a separate alerting engine, so the ownership of each alert rule must be explicit.

## 3. Project safety and change gates

**Default execution is read-only plus isolated staging resources.** Do not deliberately fail production nodes, drop real network traffic, overload databases, suppress customer alerts or route synthetic notifications to real on-call receivers.

Before live staging tests:

- Obtain application/platform owner approval and an agreed maintenance window if needed.
- Confirm namespace isolation, resource quota, rollback authority and monitoring access.
- Define explicit abort conditions: unexpected external impact, missing telemetry, unhealthy cluster or uncontrolled resource consumption.
- Verify production data and sensitive identifiers cannot enter trace/log attributes.
- Record baseline SLIs and alert-routing ownership.

```powershell
kubectl config current-context
kubectl version
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl auth can-i create namespaces
```

If staging mutation permissions are unavailable, complete tabletop and read-only portions only.

## 4. Lab 1 — Inventory the telemetry pipeline

```powershell
Get-Date -Format o
kubectl get nodes -o wide
kubectl get pods -A | Select-String 'metrics-server|prometheus|grafana|alertmanager|otel|collector|fluent|vector'
kubectl get services -A | Select-String 'metrics|prometheus|grafana|alertmanager|otel'
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
kubectl get events -A --sort-by=.lastTimestamp
```

**Expected:** identify installed components, cluster/namespace ownership, Metrics API status and current Events. Component naming differs across distributions; absence from a name-filtered list is not proof that a service is uninstalled.

### Inventory worksheet

| Signal | Source | Collection path | Retention | Owner | Health evidence |
|---|---|---|---|---|---|
| Node metrics | kubelet/node-exporter | Prometheus | Define | Platform | Scrape targets |
| Workload state | kube-state-metrics | Prometheus | Define | Platform | Target + samples |
| App SLIs | Application exporter | Prometheus | Define | Application | Request/error metrics |
| Logs | Container stdout/stderr | Collector/backend | Define | Application | Ingestion status |
| Events | Kubernetes API | Event collector | Define | Platform | Recent Event coverage |
| Traces | OTel SDK | Collector/backend | Define | Application | End-to-end trace |
| Alerts | Prometheus rules | Alertmanager | Define | On-call | Test notification |

## 5. Lab 2 — Establish baseline metrics and SLIs

Use an approved Prometheus endpoint and Grafana. Adapt metric names and labels to the actual application.

### Request throughput

```promql
sum(rate(http_requests_total{service="example-api"}[5m]))
```

### Error ratio

```promql
sum(rate(http_requests_total{service="example-api",status=~"5.."}[5m]))
/
clamp_min(sum(rate(http_requests_total{service="example-api"}[5m])), 1e-9)
```

### p95 latency (classic histogram)

```promql
histogram_quantile(0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket{service="example-api"}[5m]))
)
```

### Available replicas

```promql
kube_deployment_status_replicas_available
```

### Target health

```promql
up
```

**Expected:** record 30–60 minutes of baseline where practical. Ensure dashboards show no-data states and scrape gaps instead of treating missing metrics as zero.

### Example SLO worksheet (illustrative)

| SLI | Example objective | Measurement |
|---|---|---|
| Availability | 99.9% successful requests / 30 days | HTTP success ratio |
| Latency | 95% of requests under 500 ms | Request duration histogram |
| Monitoring coverage | Critical targets monitored | Target inventory + absence checks |
| Alert delivery | Test reaches approved receiver within 2 min | End-to-end timestamp |
| Trace coverage | Sampled traces span key dependencies | Trace backend verification |

Choose actual objectives with service owners. Monitoring coverage and notification delay are operational acceptance goals, not substitutes for customer SLOs.

## 6. Lab 3 — Create the observability dashboard specification

Build a Grafana dashboard with these rows:

| Row | Panels | Investigation purpose |
|---|---|---|
| Customer SLIs | RPS, error ratio, p95/p99 | Is the customer affected? |
| Workload | Desired/Ready replicas, restarts, Pending | Are workloads healthy? |
| Compute | CPU usage, throttling, memory working set | Is resource pressure involved? |
| Nodes | Ready, pressure, capacity, disk/network | Is the infrastructure constrained? |
| Dependencies | DB pool wait, query latency, cache errors | Is a downstream service slow? |
| Telemetry health | `up`, missing series, Collector failures | Can we trust the data? |
| Change timeline | Deployments, incidents, config changes | What changed? |

### Dashboard acceptance

- Use explicit cluster, namespace, service and environment variables.
- Display correct units and UTC/local time handling.
- Link dashboard panels to runbooks and logs/traces where supported.
- Validate p95 histogram aggregation, label cardinality and sampling coverage.
- Annotate known deployment and maintenance windows.
- Demonstrate behavior when one exporter target disappears.

## 7. Lab 4 — Validate Prometheus scrape and alert rules

Use read-only Prometheus API/UI to inspect active targets, rule evaluation and alert state.

```powershell
$prom = 'https://REPLACE_WITH_APPROVED_PROMETHEUS'
# The following requires an already authenticated approved endpoint.
Invoke-RestMethod -Uri "$prom/api/v1/targets?state=active"
Invoke-RestMethod -Uri "$prom/api/v1/rules"
Invoke-RestMethod -Uri "$prom/api/v1/alerts"
```

**Expected:** target health, last scrape errors, evaluation status and alert state. A missing target may not appear as `up == 0`; monitor discovery completeness separately.

### Example alert rules (review-only)

Save `ch060-rules.yaml`:

```yaml
groups:
  - name: ch060-service
    rules:
      - alert: Ch060ServiceHighErrorRatio
        expr: |
          (
            sum(rate(http_requests_total{service="example-api",status=~"5.."}[5m]))
            /
            clamp_min(sum(rate(http_requests_total{service="example-api"}[5m])), 1e-9)
          ) > 0.05
        for: 5m
        labels:
          severity: warning
          team: training
        annotations:
          summary: "Example API error ratio above 5%"
          description: "Investigate request errors and correlate traces, logs and deployment changes."
      - alert: Ch060DeploymentUnavailable
        expr: |
          kube_deployment_spec_replicas{namespace="ch060"}
          - kube_deployment_status_replicas_available{namespace="ch060"} > 0
        for: 10m
        labels:
          severity: warning
          team: training
        annotations:
          summary: "Training deployment has unavailable replicas"
```

Validate with `promtool check rules ch060-rules.yaml` if available. This is a **Prometheus rule-file format**, not a Kubernetes `PrometheusRule` custom resource. Never apply directly to production without rule-owner review and safe routing.

## 8. Lab 5 — Verify Alertmanager routing without paging production

Use a dedicated non-production Alertmanager and training receiver.

```powershell
$am = 'https://REPLACE_WITH_NONPROD_ALERTMANAGER'
$now = (Get-Date).ToUniversalTime()
$payload = @(
  @{
    labels = @{
      alertname = 'Ch060SyntheticAlert'
      team = 'training'
      severity = 'warning'
      cluster = 'staging'
      service = 'ch060'
    }
    annotations = @{ summary = 'Observability capstone synthetic alert' }
    startsAt = $now.ToString('o')
    endsAt = $now.AddMinutes(10).ToString('o')
  }
) | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "$am/api/v2/alerts" -ContentType 'application/json' -Body $payload
```

**Expected:** synthetic alert reaches only the training receiver. Record ingestion time, group delay, notification delivery and resolution. Direct API injection tests Alertmanager routing **but not Prometheus rule evaluation**; validate rule evaluation separately in an isolated Prometheus environment.

### Route review

- Correct team/service/cluster labels.
- Grouping by meaningful incident identity.
- Inhibition suppresses symptoms only when appropriate parent alert is firing.
- Silences have precise matchers, owners and expiry.
- Receiver outage and fallback behavior are documented.
- No duplicate pages for the same incident.

## 9. Lab 6 — Correlate logs, Events and traces

Choose a staging workload and approved incident window:

```powershell
$ns = 'REPLACE_WITH_STAGING_NAMESPACE'
$pod = 'REPLACE_WITH_STAGING_POD'
kubectl -n $ns get pod $pod -o wide
kubectl -n $ns describe pod $pod
kubectl -n $ns logs $pod --all-containers=true --timestamps --since=30m --tail=200
kubectl -n $ns logs $pod --all-containers=true --previous --timestamps --tail=100
kubectl -n $ns get events --sort-by=.lastTimestamp
```

### Trace correlation procedure

1. Select a slow request trace from the approved trace backend.
2. Compare root span duration with downstream critical-path spans.
3. Check propagation across ingress, service and DB client boundaries.
4. Search structured logs by trace ID where supported.
5. Compare span timing with database query execution and pool-wait metrics.
6. Inspect Kubernetes Events for restarts, readiness or scheduling changes.
7. State which evidence supports each hypothesis and what remains unknown.

**Expected:** a timestamped correlation worksheet that distinguishes slow DB execution from connection-pool wait, network delay or application processing.

## 10. Lab 7 — Controlled staging application failure

**Isolated staging only.** Create a short-lived Pod that exits nonzero, generating observable logs and Events without touching production workloads.

Save `ch060-failure.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ch060
---
apiVersion: v1
kind: Pod
metadata:
  name: observability-failure
  namespace: ch060
  labels:
    app: observability-failure
spec:
  restartPolicy: Always
  containers:
    - name: demo
      image: busybox:1.36
      command: ["/bin/sh", "-c", "echo 'ch060 simulated application error'; exit 42"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
```

```powershell
kubectl apply -f .\ch060-failure.yaml
kubectl -n ch060 get pod observability-failure -w
kubectl -n ch060 describe pod observability-failure
kubectl -n ch060 logs observability-failure --previous --timestamps --tail=30
kubectl -n ch060 get events --sort-by=.lastTimestamp
```

**Expected:** repeated exits with code 42 and eventual CrashLoopBackOff behavior. The exact timing varies. This lab demonstrates logs/Events/restarts; it does **not** prove customer SLO alerting, tracing or external notification delivery unless those systems are independently instrumented and tested.

## 11. Lab 8 — Missing-metrics and latency incident tabletop

**Scenario timeline**

| Time (UTC) | Observation |
|---|---|
| 14:00 | API p95 rises from 200 ms to 4 seconds |
| 14:01 | One Prometheus target disappears from discovery |
| 14:02 | Grafana aggregate CPU appears to decrease |
| 14:03 | Application logs show DB connection-pool waits |
| 14:04 | Traces show long database client spans |
| 14:05 | Alertmanager sends two duplicate pages |

### Required decisions

1. Confirm customer impact from independent request SLIs.
2. Identify which telemetry is incomplete and why.
3. Restore scrape visibility or mark missing series explicitly.
4. Correlate slow spans with DB pool and query metrics.
5. Distinguish database execution delay from client-side waiting.
6. Review grouping/inhibition and eliminate duplicate pages safely.
7. Validate recovery using error rate, latency, Ready replicas and telemetry coverage.
8. Document incident timeline, evidence, root-cause confidence and owners.

**Expected:** a blameless, evidence-based investigation with separate customer-impact and observability-reliability conclusions.

## 12. Lab 9 — Validate telemetry failure modes

Review these conditions in a tabletop or approved isolated observability environment:

| Failure | Expected detection | Safe response |
|---|---|---|
| Metrics Server unavailable | `kubectl top`/HPA resource metric errors | Check APIService, backend and kubelet path |
| Prometheus scrape target down | `up == 0` where target remains discovered | Inspect exporter/network/TLS |
| Prometheus target missing | Inventory/absent-series mismatch | Restore discovery and alert coverage |
| Prometheus TSDB pressure | Series count, WAL/storage/ingestion metrics | Reduce cardinality, scale storage |
| Log collector stalled | Backlog/dropped-log indicators | Restore ingestion, preserve audit needs |
| OTel Collector exporter down | Queue/refused/dropped span metrics | Repair backend, apply backpressure safeguards |
| Trace context lost | Partial traces and new roots | Fix propagation across boundaries |
| Alertmanager receiver down | Delivery failures/retry metrics | Validate fallback and escalation |
| Grafana unavailable | Dashboard query failure | Use Prometheus API/alternate access |

**Expected:** monitoring must itself be monitored. Document out-of-band checks for critical telemetry systems.

## 13. Observability SLO and capacity planning

### Reliability objectives

- Define allowable telemetry ingestion delay for critical signals.
- Define target coverage and alert notification latency.
- Define dashboard query availability and retention requirements.
- Document acceptable sampling rates and trace loss.
- Test alert routing after configuration changes.

### Cost and performance

- Control high-cardinality metric labels and Prometheus series growth.
- Set log retention by operational and compliance needs.
- Sample traces deliberately; retain errors/slow traces where justified.
- Monitor Collector CPU, memory, queues and dropped spans.
- Avoid broad unbounded PromQL queries during incidents.
- Plan long-term metrics storage separately from Metrics Server.

### Security and privacy

Do not put tokens, credentials, patient data, personal identifiers or raw SQL parameters into metric labels, logs or span attributes. Apply least-privilege RBAC, TLS/auth, encryption, redaction and access audits.

## 14. Production incident response runbook

### Phase 1 — Detect and scope

1. Confirm affected service, cluster, namespace, zone and incident window.
2. Measure request success, latency, throughput and customer impact.
3. Check Prometheus target coverage and alert delivery health.

### Phase 2 — Correlate evidence

1. Compare application SLIs with resource and object-state metrics.
2. Review current and previous container logs.
3. Inspect Kubernetes Events and node conditions.
4. Find representative slow traces and identify critical-path spans.
5. Check DB/cache/queue dependencies and recent changes.

### Phase 3 — Mitigate

1. Choose lowest-risk evidence-backed application or infrastructure action.
2. Protect stateful quorum and avoid blind force deletion.
3. Restore missing monitoring without hiding the application incident.
4. Use approved alert silences only with scoped matchers and expiry.
5. Validate SLI and telemetry recovery.

### Phase 4 — Close

Record impact, detection delay, time to mitigate, alert quality, trace/log coverage, monitoring gaps, remediation owners and follow-up test schedule.

## 15. Acceptance matrix

| Acceptance test | Pass criterion | Evidence |
|---|---|---|
| Metrics API | Accessible or documented exception | APIService + `kubectl top` |
| Prometheus coverage | All critical targets accounted for | Targets + inventory |
| Grafana dashboard | Customer SLIs and resource health visible | Panel review |
| Alert rules | Syntax valid and relevant metrics present | `promtool` + rule evaluation |
| Notification route | Synthetic alert reaches training receiver only | Delivery timestamps |
| Logs/Events | Staging failure observable | Logs, Events, restart count |
| Trace correlation | One end-to-end trace and linked logs | Trace/log evidence |
| Missing-data detection | Missing target not shown as healthy | Gap tabletop |
| Incident workflow | Timeline and hypotheses documented | Runbook exercise |
| Security | No sensitive telemetry leakage | Review sign-off |

A test marked tabletop is not equivalent to live runtime validation. Mark individual rows **Pass**, **Fail**, **Not run** or **Not applicable**, with an owner and evidence link.

## 16. Capstone deliverable template

```text
Project: Chapter 060 — Production Observability and Alerting
Cluster / environment:
Service / namespace:
Owner / reviewer:
Date and time window:
Change approval:

SLIs and SLOs:
Telemetry sources and retention:
Prometheus target health:
Dashboard links:
Alert rules and routing:
Synthetic notification test:
Trace and log correlation:
Staging failure test:
Missing-metrics tabletop:
RTO / detection / notification results:
Known limitations:
Follow-up actions / owners:
Independent technical review:
```

## 17. Final Part 12 acceptance checklist

- [ ] Chapter 056: metrics, logs and Events correlation demonstrated.
- [ ] Chapter 057: Metrics Server and Prometheus pipeline validated.
- [ ] Chapter 058: Grafana dashboards and Alertmanager routes reviewed.
- [ ] Chapter 059: OpenTelemetry trace context and Collector pipeline reviewed.
- [ ] SLI/SLO dashboard and telemetry quality checks documented.
- [ ] Alert rule evaluation and notification routing tested separately.
- [ ] Isolated staging failure exercise completed or marked not run.
- [ ] Monitoring gap and duplicate-page tabletop completed.
- [ ] Incident runbook, privacy controls and operational handover completed.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Part 12 writing milestone:** Chapters 056–060 drafted. Runtime validation and independent technical review remain pending.

## 18. Cleanup

```powershell
kubectl -n ch060 get pods
kubectl delete namespace ch060
```

Delete only resources created for this chapter. Do not remove existing Prometheus, Grafana, Alertmanager or OpenTelemetry installations. Archive approved test evidence without sensitive data.

## 19. References

- [Kubernetes Observability](https://kubernetes.io/docs/concepts/cluster-administration/observability/)
- [Kubernetes Resource Metrics Pipeline](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)
- [Prometheus Overview](https://prometheus.io/docs/introduction/overview/)
- [Prometheus Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/)

**Next:** Chapter 061 — Kubernetes Troubleshooting Methodology (Part 13).
