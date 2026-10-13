# Chapter 058 — Grafana Dashboards and Alertmanager

**Track:** Kubernetes Administration · **Part 12 — Observability and Monitoring**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, platform engineers, on-call engineers  
**Prerequisites:** Chapters 056–057; read-only Kubernetes access; approved Grafana, Prometheus and Alertmanager endpoints; Windows PowerShell

## 1. Production scenario

A customer-facing API's 5xx error rate rises while two replicas become unavailable. Grafana displays a latency spike, but one dashboard panel silently excludes an unhealthy Prometheus target. Alertmanager sends duplicate pages to two teams, while a planned maintenance alert should have been inhibited.

**Goal:** build trustworthy dashboards, implement SLO-oriented alert rules, configure reliable notification routing, and prove the entire detection-to-response path with a controlled test.

### Learning objectives

1. Explain the roles of Grafana, Prometheus, Prometheus alert rules and Alertmanager.
2. Build workload, node, control-plane and application dashboards.
3. Use Grafana variables, time ranges, annotations and data-source health.
4. Design alerts for customer impact, burn rates and infrastructure symptoms.
5. Configure Alertmanager routes, receivers, grouping, inhibition and silences.
6. Validate alert lifecycle and delivery without paging real responders.
7. Troubleshoot missing panels, duplicate notifications and noisy alerts.

## 2. Architecture and responsibility boundaries

```text
Kubernetes / exporters / application instrumentation
                      |
                 Prometheus
            scrape + rule evaluation
                 /          \
                /            \
          Grafana          Alertmanager
       visualization      group / route /
       annotations        inhibit / silence
                                |
                       approved receivers
                    on-call / email / ticket
                                |
                       incident response
```

Grafana can also evaluate **Grafana-managed alerts**, which use Grafana's own evaluation and notification configuration. This chapter focuses on **Prometheus-managed alert rules sent to Alertmanager**. Avoid assuming Grafana notification policies and Alertmanager routes are interchangeable; document which engine owns each rule.

## 3. Safety and access

Labs 1–5 are read-only/design-oriented. Lab 6 uses a **dedicated non-production Alertmanager receiver**. Lab 7 is an incident tabletop. Do not send synthetic alerts to production paging routes, disable real alerts, or silence an entire production namespace.

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get pods -A | Select-String 'grafana|prometheus|alertmanager'
kubectl get services -A | Select-String 'grafana|prometheus|alertmanager'
```

Record Grafana and Prometheus ownership, version, authentication method, data-source permissions, alerting engine and change approval. If no stack exists, perform design/tabletop labs without deploying monitoring software to production.

## 4. Lab 1 — Inspect observability components and access

```powershell
kubectl get pods -A | Select-String 'grafana|prometheus|alertmanager'
kubectl get services -A | Select-String 'grafana|prometheus|alertmanager'
kubectl get prometheusrules -A
kubectl get alertmanagerconfigs -A
```

**Expected:** inventory installed components and optional Prometheus Operator CRDs. The last two commands can fail if the Operator's CRDs are not installed; that is not itself a monitoring outage.

Check approved endpoints with existing authenticated access. For an authorized Prometheus endpoint:

```powershell
$prom = 'https://REPLACE_WITH_APPROVED_PROMETHEUS'
$query = [uri]::EscapeDataString('up')
Invoke-RestMethod -Uri "$prom/api/v1/query?query=$query"
```

**Expected:** data-source connectivity and active scrape targets. Never put long-lived credentials in URLs or commit Grafana API keys to a repository.

## 5. Lab 2 — Design a Kubernetes workload dashboard

Build a Grafana dashboard with the following panels and a consistent time range:

| Panel | Example PromQL | Interpretation |
|---|---|---|
| Available replicas | `kube_deployment_status_replicas_available` | Current available replicas |
| Desired replicas | `kube_deployment_spec_replicas` | Expected workload size |
| CPU usage | `sum by(namespace,pod)(rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m]))` | CPU cores consumed |
| Memory working set | `sum by(namespace,pod)(container_memory_working_set_bytes{container!="",image!=""})` | Memory pressure trend |
| Restarts | `sum by(namespace,pod)(increase(kube_pod_container_status_restarts_total[15m]))` | Recent restart increase |
| Scrape health | `up` | Target availability |

### Grafana dashboard design

1. Create variables for cluster, namespace and workload from available labels.
2. Restrict query labels to avoid accidentally mixing multiple clusters.
3. Use units: CPU cores, bytes, requests/second, seconds or percent.
4. Include thresholds only where SLOs or validated operational limits exist.
5. Add deployment/change annotations and relevant runbook links.
6. Use an explicit No Data presentation; do not silently convert missing telemetry to zero.
7. Validate panel queries and labels against the actual Prometheus installation.

**Expected:** a dashboard that allows an on-call engineer to identify unhealthy workloads, their resource context and missing telemetry within minutes.

## 6. Lab 3 — Build a customer-impact dashboard

An SRE dashboard should lead with customer-facing SLIs rather than node CPU.

### Request rate

```promql
sum(rate(http_requests_total{service="example-api"}[5m]))
```

### Error ratio

```promql
sum(rate(http_requests_total{service="example-api",status=~"5.."}[5m]))
/
clamp_min(sum(rate(http_requests_total{service="example-api"}[5m])), 1e-9)
```

### p95 request latency (classic histogram)

```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket{service="example-api"}[5m]))
)
```

These metric names and labels are **illustrative**. Adapt to actual application instrumentation, histogram type, status label and scrape configuration. Native histograms require different PromQL than classic `_bucket` histograms.

### Acceptance questions

- Does the dashboard show error rate, latency and throughput together?
- Can it identify affected region/zone, workload version and namespace?
- Does it expose scrape gaps and target failures?
- Are time ranges, time zones and deployment annotations consistent?
- Are dashboard variables safe against expensive high-cardinality queries?

## 7. Lab 4 — Design actionable Prometheus alert rules

Save `ch058-rules.yaml` for **review and validation only**:

```yaml
groups:
  - name: ch058-application-availability
    interval: 30s
    rules:
      - alert: Ch058DeploymentUnavailable
        expr: |
          kube_deployment_spec_replicas{namespace="ch058"}
          - kube_deployment_status_replicas_available{namespace="ch058"} > 0
        for: 10m
        labels:
          severity: warning
          team: training
        annotations:
          summary: "Training deployment has unavailable replicas"
          description: "Check scheduling, readiness, events and recent changes."
          runbook_url: "https://kubernetes.io/docs/tasks/debug/debug-application/"
      - alert: Ch058ScrapeTargetDown
        expr: up{job="ch058-training"} == 0
        for: 5m
        labels:
          severity: warning
          team: training
        annotations:
          summary: "Training scrape target is down"
```

**Important:** this file is a **Prometheus rule-file format**, not a Kubernetes `PrometheusRule` custom resource. If using Prometheus Operator, wrap the groups under `spec.groups` of a `monitoring.coreos.com/v1` `PrometheusRule` and ensure the Prometheus rule selector selects it. Do not apply this example to production without a reviewed route and actual test namespace.

Validate with `promtool check rules ch058-rules.yaml` where `promtool` is available.

### Alert design principles

- Page on actionable customer-impacting conditions; use warning/ticket for lower urgency.
- Apply a `for` period to avoid transient noise when appropriate.
- Include severity, service, team, cluster, runbook and useful labels.
- Do not embed credentials or personally identifiable data in alert labels.
- Use SLO error-budget burn alerts for important services.
- Check rule evaluation and scrape completeness before assuming a missing alert means health.

## 8. Lab 5 — Alertmanager routing, grouping and inhibition

The following is an **illustrative Alertmanager configuration fragment**, not a complete production file:

```yaml
route:
  receiver: training-null
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - receiver: training-webhook
      matchers:
        - team="training"
      continue: false

receivers:
  - name: training-null
  - name: training-webhook
    webhook_configs:
      - url: 'http://training-receiver.ch058.svc.cluster.local:8080/alerts'
        send_resolved: true

inhibit_rules:
  - source_matchers:
      - alertname="Ch058ParentIncident"
  - target_matchers:
      - severity="warning"
    equal: ['cluster', 'service']
```

**Correction before use:** an `inhibit_rules` entry must contain `source_matchers`, `target_matchers` and `equal` in the **same mapping**. The intended form is:

```yaml
inhibit_rules:
  - source_matchers:
      - alertname="Ch058ParentIncident"
    target_matchers:
      - severity="warning"
    equal: ['cluster', 'service']
```

The webhook URL is a placeholder for an approved isolated receiver; it is not a live endpoint. Do not deploy this fragment as-is.

### Operational semantics

| Feature | Purpose | Risk |
|---|---|---|
| Routing | Send alerts to owning team | Wrong labels can misroute pages |
| Grouping | Consolidate related alerts | Over-grouping hides independent incidents |
| Inhibition | Suppress child alerts when parent is firing | Broad match can hide real failures |
| Silence | Temporarily suppress matched notifications | Expiry and match scope must be explicit |
| Repeat interval | Control repeat notifications | Too frequent causes noise; too slow hides prolonged issues |
| HA Alertmanager | Improve notification availability | Requires correct clustering and deduplication |

**Silence versus inhibition:** a silence is time-bounded and explicitly configured; inhibition is conditional on another firing alert. Neither should be used to conceal unresolved incidents.

## 9. Lab 6 — Test alert lifecycle without production paging

**Non-production only.** Establish a training-only receiver and route, then test a synthetic alert through an approved Alertmanager endpoint. For a dedicated isolated Alertmanager instance:

```powershell
$am = 'https://REPLACE_WITH_NONPROD_ALERTMANAGER'
$payload = @(
  @{
    labels = @{
      alertname = 'Ch058SyntheticAlert'
      team = 'training'
      severity = 'warning'
      cluster = 'lab'
      service = 'ch058'
    }
    annotations = @{
      summary = 'Synthetic training alert'
    }
    startsAt = (Get-Date).ToUniversalTime().ToString('o')
    endsAt = (Get-Date).ToUniversalTime().AddMinutes(10).ToString('o')
  }
) | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "$am/api/v2/alerts" -ContentType 'application/json' -Body $payload
```

**Expected:** the synthetic alert appears in the non-production Alertmanager API/UI and routes only to the training receiver. Directly posting an alert tests **Alertmanager routing**, not Prometheus rule evaluation. Separately test rule evaluation in an isolated Prometheus environment if full end-to-end coverage is required.

### Acceptance evidence

1. Alert received and labeled correctly.
2. Grouping behavior observed.
3. Notification delivered to the training receiver.
4. Resolved notification behavior confirmed.
5. Silence/inhibition behavior tested only with synthetic labels.
6. No production pager or unrelated team received a notification.

## 10. Lab 7 — Dashboard gap and duplicate paging tabletop

**Scenario:** API p95 latency rises at 10:00 UTC. One Prometheus target disappears from discovery at 10:01. A dashboard incorrectly shows lower total CPU. At 10:02, the same customer incident triggers both `ApiHighErrorRate` and `DeploymentUnavailable`, paging two teams separately.

### Investigation sequence

1. Verify Prometheus target discovery, `up` and absent-series coverage.
2. Inspect Grafana query labels, data-source health and No Data handling.
3. Correlate request success, latency, throughput, restarts and deployment revisions.
4. Determine alert ownership and whether grouping labels align with service identity.
5. Decide whether a parent incident alert should inhibit symptom alerts.
6. Review route matchers, `continue`, grouping and receiver configuration.
7. Verify any active silences are scoped and time-bounded.
8. Test revised rules and routes in non-production.
9. Confirm dashboards show missing telemetry as unknown, not healthy.

**Expected:** one clear primary incident page with supporting diagnostic alerts, while unrelated critical failures remain visible.

## 11. SLO burn-rate alerting

For a 99.9% availability SLO, the error budget fraction is 0.001. A burn rate compares the observed error ratio against this budget. For example, an observed error ratio of 1% corresponds to a burn rate of 10.

```promql
(
  sum(rate(http_requests_total{service="example-api",status=~"5.."}[5m]))
  /
  clamp_min(sum(rate(http_requests_total{service="example-api"}[5m])), 1e-9)
) / 0.001
```

Use multiple windows to distinguish fast severe outages from slower sustained degradation. Set burn thresholds and windows from the service SLO and paging policy. Beware low-traffic services where a handful of requests can cause volatile ratios; use traffic gating and appropriate statistical judgment.

## 12. Production dashboard and alert standards

### Dashboard minimum

- Customer SLIs: request rate, errors, latency and saturation.
- Workload state: desired/available replicas, restarts and Pending Pods.
- Resource pressure: CPU, throttling, memory, storage and network.
- Infrastructure dependencies: nodes, ingress, DNS, database and external services.
- Data quality: target health, scrape freshness and No Data behavior.
- Change context: deployment annotations and incident markers.
- Navigation: ownership, runbook and escalation links.

### Alert minimum

- Clear condition, severity, owner and customer-impact interpretation.
- Correct cluster/namespace/service labels.
- Evaluation duration and appropriate thresholds.
- Route/receiver ownership and fallback.
- Grouping/inhibition review.
- Test evidence and safe silence process.
- Runbook link and documented expected responder action.

## 13. Troubleshooting matrix

| Symptom | Likely cause | Verification |
|---|---|---|
| Grafana panel empty | Wrong data source/labels or no scrape | Explore query, target health |
| Grafana displays zero for missing data | Query transform/fill behavior | Compare raw PromQL |
| Alert never fires | Expression, `for`, scrape gap | Rule evaluation and series |
| Duplicate pages | Multiple rules/routes/grouping | Alertmanager status and routing tree |
| Alert sent to wrong team | Matcher/label mismatch | Route test and alert labels |
| Alerts suppressed unexpectedly | Silence/inhibition | Active silences and source alerts |
| Alert resolves too quickly | Flapping condition | Evaluation interval and `for` |
| Notification delayed | Group wait or receiver outage | Alertmanager logs and metrics |
| Alertmanager cluster unhealthy | Peer/network/config issue | Cluster status and peer logs |
| Prometheus rule invalid | YAML/PromQL syntax | `promtool check rules` |

## 14. Production incident runbook

### Detect

1. Verify customer impact through SLI panels and independent probes.
2. Confirm Prometheus scrape and rule evaluation health.
3. Inspect active alerts, grouping and receiver delivery status.

### Correlate

1. Match service/cluster labels across dashboards and alerts.
2. Compare error rate, latency, replicas, throttling and restarts.
3. Review deployment changes, logs and Kubernetes Events.
4. Identify missing telemetry and avoid false conclusions.

### Mitigate

1. Address the application or infrastructure issue using approved runbooks.
2. Adjust notification routing only through authorized incident procedures.
3. Use narrowly scoped, expiring silences for justified maintenance.
4. Verify recovery in SLIs, dashboards and resolved alerts.

### Close

Record alert detection delay, notification latency, false positives, duplicate pages, monitoring blind spots and follow-up owners.

## 15. Acceptance checklist

- [ ] Grafana, Prometheus and Alertmanager responsibilities documented.
- [ ] Data-source and scrape health verified.
- [ ] Workload dashboard with resource and readiness panels designed.
- [ ] Customer SLI dashboard with errors, latency and throughput designed.
- [ ] Prometheus alert rules reviewed and syntax-validated.
- [ ] Alertmanager route, grouping, inhibition and silence behavior understood.
- [ ] Synthetic alert delivered only to non-production receiver.
- [ ] Rule evaluation distinguished from direct Alertmanager API injection.
- [ ] No Data and missing-series behavior explicitly handled.
- [ ] Duplicate paging tabletop completed.
- [ ] SLO burn-rate strategy and runbook ownership recorded.
- [ ] Runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 16. References

- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Grafana Dashboard Variables](https://grafana.com/docs/grafana/latest/dashboards/variables/)
- [Prometheus Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Prometheus Recording Rules](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [Alertmanager API](https://prometheus.io/docs/alerting/latest/management_api/)
- [Prometheus Best Practices for Alerting](https://prometheus.io/docs/practices/alerting/)

**Next:** Chapter 059 — OpenTelemetry and Distributed Tracing.
