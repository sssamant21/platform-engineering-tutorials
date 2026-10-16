# Chapter 067 — Jenkins Prometheus, Grafana Dashboards and Alertmanager Integration

**Part 14 — Observability, Monitoring and Performance**  
**Audience:** Jenkins SRE, observability engineers, platform engineers and on-call teams  
**Prerequisites:** Chapter 066; disposable Jenkins controller with Prometheus plugin; Prometheus, Grafana and Alertmanager lab; optional Kubernetes.

## Learning objectives

Configure a secure Jenkins metrics pipeline; discover real plugin metric names; design useful PromQL recording and alerting rules; build operational Grafana dashboards; route actionable notifications with Alertmanager; verify alert firing, recovery and incident ownership.

## 1. End-to-end architecture

```text
Jenkins Prometheus plugin ----JVM / process exporter --------> Prometheus ----> Grafana
Kubernetes / node exporters --/       |
Synthetic external probe -------------|--> Alert rules --> Alertmanager --> On-call
                                      |
                             Recording rules / SLI
```

Metrics are not enough: pair them with Jenkins logs, agent/pod events, security audit and SCM delivery evidence. Treat the monitoring path itself as a service with scrape and notification health.

## 2. Metric discovery before dashboards

Jenkins Prometheus plugin metrics, endpoint path, namespace and label conventions vary by plugin version. On an isolated controller:
1. Verify installed plugin version and endpoint settings.
2. Confirm the configured metrics URL and network access.
3. Query `/api/v1/label/__name__/values` on your authorized Prometheus endpoint or explore Metrics in Grafana.
4. Capture actual queue, executor, JVM and job metric names.
5. Record units, labels, histogram buckets and cardinality.
6. Create stable recording rules for dashboard and alert queries.

**Do not copy assumed Jenkins metric names into production alerts.** The examples below use explicit lab recording rules and standard Prometheus `up`.

## 3. Secure Prometheus scrape

Illustrative Kubernetes scrape:

```yaml
scrape_configs:
  - job_name: jenkins-controller
    scheme: https
    metrics_path: /prometheus/
    scrape_interval: 30s
    scrape_timeout: 10s
    static_configs:
      - targets: ['jenkins.example.test']
    # Configure tls_config and an approved auth mechanism
    # for the actual Jenkins metrics endpoint.
```

Confirm whether the installed plugin endpoint is `/prometheus/` or another path. Use TLS, network policies and least-privilege credentials. Do not expose scrape tokens in Prometheus YAML committed to Git; use secret mounts/injection. A failed scrape (`up == 0`) is not proof that the Jenkins UI is down.

## 4. Optional Kubernetes ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: jenkins
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames: [jenkins]
  selector:
    matchLabels:
      app.kubernetes.io/name: jenkins
  endpoints:
    - port: http
      path: /prometheus/
      interval: 30s
```

Requires Prometheus Operator CRDs, a matching Jenkins Service and a **named** port `http`. Configure authentication/TLS as appropriate. The sample uses HTTP for a trusted lab only.

## 5. SLI and recording-rule design

Recommended indicators:
- Controller external availability (blackbox probe).
- Queue wait p50/p95/p99 by bounded workload class.
- Executor utilization and offline ratio.
- Agent provisioning latency.
- Infrastructure-caused build failure ratio.
- Controller restart frequency, JVM GC pause and storage headroom.

Avoid per-build or per-commit metric labels. Prefer team/pool/environment, with a controlled vocabulary.

**Illustrative recording rules** (inputs must be mapped to real exported series):

```yaml
groups:
  - name: jenkins-sli
    interval: 30s
    rules:
      - record: jenkins:scrape_available:ratio
        expr: avg(up{job="jenkins-controller"})
      - record: jenkins:queue_wait_p95:seconds
        expr: histogram_quantile(0.95, sum by (le) (rate(jenkins_queue_wait_seconds_bucket[5m])))
```

`jenkins_queue_wait_seconds_bucket` is a placeholder. Histogram quantiles require actual bucket metrics; if your plugin exports only gauges, do not fabricate histograms. `jenkins:scrape_available:ratio` is scrape health, not user-facing availability.

## 6. Grafana dashboard specification

| Panel | Query concept | Interpretation |
|---|---|---|
| Metrics target | `up{job="jenkins-controller"}` | Scrape reachability |
| External availability | Probe success rate | User-facing access |
| Queue depth | Discovered queue gauge | Backlog |
| Queue wait p95 | Validated histogram/recording rule | Scheduling latency |
| Executor busy ratio | Busy/total available executors | Capacity |
| Offline agents | Discovered agent series | Agent health |
| JVM heap | JVM exporter heap used/max | Memory pressure |
| JVM GC | GC pause rate/percentile | Runtime pressure |
| Agent provisioning | Validated provisioning metric | Elasticity |
| Pipeline infra failures | Controlled failure classification | Reliability |
| Plugin/controller changes | Deployment annotation | Correlation |

Include time range, environment/pool variables, change annotations and links to runbooks. Set reasonable query intervals and label cardinality budgets.

## 7. Alert rules

```yaml
groups:
  - name: jenkins-availability
    rules:
      - alert: JenkinsMetricsScrapeDown
        expr: up{job="jenkins-controller"} == 0
        for: 5m
        labels:
          severity: warning
          service: jenkins
        annotations:
          summary: "Jenkins Prometheus scrape unavailable"
          runbook_url: "https://runbooks.example.test/jenkins/scrape"
      - alert: JenkinsQueueWaitSustained
        expr: jenkins:queue_wait_p95:seconds > 300
        for: 15m
        labels:
          severity: warning
          service: jenkins
        annotations:
          summary: "Jenkins queue wait p95 above 5 minutes"
```

The queue rule requires the recording rule and actual histogram mapping. Tune thresholds from a measured baseline and distinguish scheduled load bursts from sustained starvation. Use a separate external probe alert for customer-facing outage.

## 8. Alertmanager routing

```yaml
route:
  receiver: platform-default
  group_by: ['alertname', 'service', 'environment']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - matchers:
        - service="jenkins"
        - severity="critical"
      receiver: jenkins-oncall
receivers:
  - name: platform-default
  - name: jenkins-oncall
```

This is a routing skeleton; add a supported receiver integration and secret-backed credentials before expecting delivery. A receiver without an integration does not notify anyone. Configure inhibition for downstream queue/agent symptoms during confirmed controller outages; test carefully to avoid suppressing independent incidents.

## 9. Alert quality and ownership

Each page should include affected environment, user impact, current value/threshold, dashboard, runbook, change correlation, escalation and silence policy. Use critical for actionable, sustained user impact; warning/ticket for trends. Track alert precision, duplicates, missed incidents, time-to-detect and time-to-acknowledge.

## 10. Dashboard and alert deployment as code

Store Prometheus rules, Alertmanager config and Grafana dashboards in Git; lint YAML, run `promtool check rules` and `amtool check-config` where available, review dashboards, test against staging data and promote with approval. Restrict write access to alert routing and Grafana datasources.

```sh
promtool check rules monitoring/jenkins-alerts.yaml
amtool check-config monitoring/alertmanager.yaml
```

The binaries must be installed in the validation environment. Verify current CLI syntax for the installed versions.

## 11. Troubleshooting matrix

| Symptom | First checks | Likely fix |
|---|---|---|
| Target DOWN | URL, TLS, network, auth | Correct scrape |
| Scrape UP, UI DOWN | External probe, proxy, SSO | Restore frontend |
| Queue panel empty | Metric names/labels | Re-map query |
| p95 graph absent | No histogram buckets | Use supported metric |
| Grafana no data | Datasource/time range | Fix source/query |
| Alert never fires | Expression/for/evaluation | Test rule |
| Alert fires continuously | No baseline/for | Tune threshold |
| Alertmanager no delivery | Receiver missing | Configure integration |
| Duplicate pages | Grouping/route overlap | Adjust routes |
| Silent incident | Overbroad inhibition | Review inhibition |
| High Prometheus RAM | Cardinality explosion | Remove high-cardinality labels |
| Series disappear after upgrade | Plugin metric schema changed | Update rules |
| Unauthorized metrics exposure | Endpoint ACL | Restrict immediately |
| Scrape latency | Large response/controller pressure | Reduce scope |
| TLS errors | Certificate/CA/SNI | Fix trust |
| Missing annotations | Deployment pipeline absent | Add change markers |

## 12. Five production runbooks

### A. Metrics target down
1. Confirm scrape error and endpoint reachability.
2. Check plugin health, proxy, TLS and credentials.
3. Compare external user-facing probe.
4. Restore trusted scrape path without opening public access.
5. Confirm `up` recovers and alert resolves.

### B. Sustained queue wait
1. Validate queue metric and affected workload classes.
2. Inspect executor availability, labels and agent provisioning.
3. Check Kubernetes quota, autoscaler and pending pods.
4. Restore capacity or throttle incoming load safely.
5. Verify p95 recovery and alert closure.

### C. Alertmanager delivery failure
1. Check firing alert in Prometheus.
2. Inspect Alertmanager route, receiver and silences.
3. Validate receiver credentials and external endpoint.
4. Send a synthetic test alert through approved test path.
5. Confirm on-call acknowledgment and close incident.

### D. Dashboard metric regression
1. Identify plugin/exporter upgrade.
2. Compare pre/post metric inventory and label schema.
3. Update recording rules and dashboard queries in staging.
4. Deploy reviewed changes.
5. Verify alert continuity.

### E. Alert storm
1. Identify root cause and downstream symptoms.
2. Apply scoped, expiring silence if necessary.
3. Fix grouping, inhibition and thresholds.
4. Replay synthetic alerts and confirm routing.
5. Document noise reduction and missed-risk assessment.

## 13. Acceptance criteria

- [ ] Prometheus securely scrapes Jenkins.
- [ ] Actual plugin metric names documented.
- [ ] External probe separate from scrape health.
- [ ] Queue/executor/JVM/agent dashboards validated.
- [ ] Recording rules map to real series.
- [ ] Alert rules linted and tested.
- [ ] Alertmanager receiver delivers test notification.
- [ ] Inhibition and grouping tested.
- [ ] Cardinality and secret exposure reviewed.
- [ ] Runbooks, owners and evidence retained.

**Companion:** [Chapter 067 hands-on lab](labs/067-jenkins-prometheus-grafana-alertmanager-integration-check.md).  
**Next:** Chapter 068 — Jenkins Pipeline Observability, Logs, Traces and OpenTelemetry Integration.
