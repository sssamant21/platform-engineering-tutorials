# Chapter 086 — Enterprise GitOps Observability Architecture, Metrics, Logs and Distributed Tracing

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 18:** Observability, SLOs and Troubleshooting  
**Chapter:** 086 / 100  
**Audience:** SREs, Platform Engineers, DevOps, Observability Engineers, Security Engineers and Incident Commanders

> **Safety:** Run labs on isolated staging clusters with synthetic data. Do not enable verbose production logs containing tokens, export sensitive traces, disable audit logging, or deploy unbounded metric labels. Verify telemetry retention, access control, data residency, cardinality and cost before rollout.

## 1. Mission and learning outcomes

Build an observable enterprise GitOps delivery system covering GitLab CI/CD, container registries, Argo CD controllers, ApplicationSets, Kubernetes, ingress/Gateway, applications, databases and provider APIs.

At completion, you can design telemetry pipelines, instrument services, build service and platform dashboards, correlate releases with incidents, detect collector outages, define monitoring ownership and validate an end-to-end troubleshooting workflow.

## 2. Observability reference architecture

~~~text
GitLab pipeline / runners / registry
               |
       CI events and audit
               |
Argo CD API / repo-server / controller / ApplicationSet
               |
         GitOps metrics and logs
               |
Kubernetes nodes / API / CNI / CSI / Gateway
               |
       metrics / logs / traces
               |
     OpenTelemetry collectors
       /         |         \
 Prometheus   log backend   trace backend
       \         |         /
          Grafana dashboards
               |
       SLO and alert routing
               |
        SRE incident command
~~~

Keep local collection and critical alerting available if central telemetry aggregation fails. A central dashboard is not a substitute for independent cloud-provider and cluster-level monitoring.

## 3. Telemetry signals

| Signal | Purpose | Typical sources |
| --- | --- | --- |
| Metrics | Trends, rates, saturation and SLOs | Prometheus, cloud metrics |
| Logs | Discrete errors, state transitions | CI jobs, controllers, apps |
| Traces | Distributed request dependency timing | OpenTelemetry SDKs |
| Events | Kubernetes scheduling and reconciliation | Kubernetes API |
| Audit | Actor, action, time and resource | GitLab, Argo CD, cloud IAM |
| Synthetic | User journey and endpoint validation | External/internal probes |
| Profiles | CPU and allocation investigation | Approved profiling tools |

Correlate these signals using service name, cluster, namespace, environment, region, provider, revision and trace identifiers. Avoid placing personally identifying data in labels.

## 4. Golden signals and USE/RED methods

For user-facing services: latency, traffic, errors and saturation. For resources: utilization, saturation and errors (USE). For services: rate, errors and duration (RED).

A healthy controller or Pod is not proof that user requests succeed. Instrument ingress, application and dependencies.

## 5. Label and attribute contract

~~~yaml
service.name: demo-api
deployment.environment.name: staging
k8s.cluster.name: eks-staging
k8s.namespace.name: demo-staging
cloud.provider: aws
cloud.region: us-east-1
service.version: git-sha-placeholder
team: platform-sre
~~~

These are example semantic attributes, not a guaranteed complete OpenTelemetry semantic convention set for every SDK version. Keep cluster identity stable, and limit cardinality by excluding user IDs, request IDs, raw URLs and Pod UIDs from high-volume metric labels.

## 6. GitLab CI/CD observability

Capture pipeline duration, queue time, runner saturation, failure rate, deployment frequency, artifact digest, job retry count and release approval latency.

Correlate job IDs, commit SHA, MR ID and deployment environment with Argo CD revision. Never export masked CI variables or OIDC tokens.

## 7. GitLab runner telemetry

Monitor runner manager and executor resource utilization, concurrent job limits, Kubernetes executor Pod Pending time, image pull errors, cache availability and job failures.

Distinguish pipeline execution failure from downstream deployment failure.

## 8. Argo CD observability

Collect controller, repo-server, API server, ApplicationSet controller and notifications component telemetry according to the installed version.

~~~bash
kubectl -n argocd get deploy,statefulset,pods
kubectl -n argocd get applications,applicationsets,appprojects
kubectl -n argocd get events --sort-by=.lastTimestamp
kubectl -n argocd logs deploy/argocd-repo-server --since=15m
~~~

The exact controller workload name may be a StatefulSet, and component metrics ports/services vary by chart/version. Inspect the installed release rather than assuming one universal service name.

## 9. Argo CD health versus sync

**Synced** indicates desired-state comparison, while **Healthy** reflects supported resource health assessments. Both can be green during an application-level outage.

Track OutOfSync age, sync failures, repo fetch failures, application health, cluster API connectivity and actual synthetic user checks.

## 10. ApplicationSet observability

Record generator type, target count, expected versus actual Applications, reconciliation errors, controller restarts and unexpected deletion events.

Alert on fleet-wide target count spikes or unexpected production destinations, not merely on controller CPU.

## 11. Kubernetes infrastructure metrics

Track node Ready, CPU, memory, disk pressure, Pod Pending, restart counts, HPA, autoscaler, API server availability, kubelet, CoreDNS, CNI, CSI, ingress/Gateway and PVC capacity.

Resource requests and limits influence scheduling and autoscaling; interpret usage against requests, limits and actual node allocatable.

## 12. Prometheus Operator monitoring

~~~yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: demo-api
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames: [demo-staging]
  selector:
    matchLabels:
      app.kubernetes.io/name: demo-api
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
~~~

Requires installed ServiceMonitor CRD, matching Service labels and named port, and permitted network access. Validate scrape target status before writing alerts.

## 13. OpenTelemetry Collector

~~~yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 256
  batch: {}
exporters:
  otlp:
    endpoint: telemetry-gateway.example.internal:4317
    tls:
      insecure: false
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp]
~~~

Example only: configure TLS trust, workload identity and credentials. Use an appropriate collector distribution; component availability and configuration change across versions.

## 14. Collector deployment patterns

| Pattern | Benefit | Risk |
| --- | --- | --- |
| DaemonSet | Local node collection | Node pressure |
| Deployment gateway | Central filtering/batching | Shared bottleneck |
| Sidecar | Per-workload isolation | High overhead |
| Agent plus gateway | Balanced topology | More moving parts |

Bound memory, batch sizes, retry queues and egress. Test collector outages and backpressure to avoid disrupting applications.

## 15. PromQL essentials

~~~promql
sum by (service) (rate(http_requests_total[5m]))

sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))

histogram_quantile(
  0.99,
  sum by (le, service) (rate(http_request_duration_seconds_bucket[5m]))
)
~~~

Queries require application-specific metric names and labels. Validate histogram type and bucket aggregation before relying on percentile calculations.

## 16. Alert rule example

~~~yaml
groups:
  - name: demo-api
    rules:
      - alert: DemoApiHighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{service="demo-api",status=~"5.."}[5m]))
            /
            clamp_min(sum(rate(http_requests_total{service="demo-api"}[5m])), 0.001)
          ) > 0.05
        for: 10m
        labels:
          severity: warning
          team: platform-sre
        annotations:
          summary: Demo API 5xx error fraction above 5%
          runbook_url: https://runbooks.example.internal/demo-api-errors
~~~

This is an illustrative Prometheus rule, not a complete SLO burn-rate alert. Scope to environment and cluster as required and validate low-traffic behavior.

## 17. Grafana dashboard design

Provide fleet overview, GitLab delivery, Argo CD reconciliation, Kubernetes health, ingress, application RED, database dependencies, security audit, backup and cost views.

Every dashboard should include owner, datasource, time range, units, query links and relevant runbook. Prefer ratios and rates over raw counter values.

## 18. Structured application logging

~~~json
{
  "timestamp": "2026-10-15T10:00:00Z",
  "level": "ERROR",
  "service": "demo-api",
  "environment": "staging",
  "cluster": "eks-staging",
  "trace_id": "00000000000000000000000000000001",
  "message": "dependency timeout",
  "dependency": "synthetic-database",
  "duration_ms": 1800
}
~~~

Use a valid trace ID from the instrumentation library in real systems. Never log passwords, bearer tokens, session cookies or raw patient/customer data.

## 19. Log collection and retention

Use approved collectors and backends (for example Fluent Bit, OpenTelemetry Collector or provider agents). Set parsing, redaction, retention, access and storage tiers.

Avoid infinite retry loops and unbounded disk buffers. Protect audit evidence from ordinary application operators.

## 20. Distributed tracing

Instrument ingress, API, database calls and queue consumers. Propagate W3C trace context and capture service/dependency span timing.

Use sampling appropriate to traffic and incident goals; ensure error traces are sufficiently represented. Correlate trace IDs with structured logs.

## 21. Trace propagation failures

Missing parent spans may indicate proxy header stripping, SDK mismatch, sampling, async context loss or exporter outage. Confirm propagation at each hop with a synthetic request.

## 22. Synthetics and black-box probes

Probe health and critical user workflows from approved regions. Distinguish liveness from real business transaction success.

Use non-sensitive synthetic accounts and ensure tests do not mutate production data or create costly workloads.

## 23. Security and audit telemetry

Monitor cloud IAM changes, Kubernetes RBAC changes, GitLab protected branch events, Argo CD AppProject edits, ApplicationSet changes, admission denials and secret access failures.

Preserve who, what, when, where and approved change reference. Audit logging must be tested, not assumed enabled.

## 24. Telemetry reliability and FinOps

Set sampling, retention, cardinality budgets, collector capacity, compression and egress constraints. Estimate cost per provider and region.

Monitoring infrastructure is production infrastructure: give it SLOs, backup/recovery procedures, ownership and safe change management.

## 25. Operational acceptance

The system should detect a synthetic bad rollout, identify its GitLab revision, show Argo CD drift/sync state, trace user latency to a dependency, retain cloud/Kubernetes audit context and support recovery with documented evidence.

## 26. Lab A — Telemetry inventory

1. List GitLab, Argo CD, Kubernetes and app telemetry sources.
2. Record provider, cluster and environment.
3. Identify missing metrics/logs/traces/audit.
4. Check retention and access.
5. Review collector resources and costs.
6. Archive redacted inventory.

**Pass:** coverage and ownership documented.

## 27. Lab B — GitLab pipeline instrumentation

1. Run protected synthetic pipeline.
2. Record queue, execution and retry duration.
3. Associate commit SHA and MR ID.
4. Capture artifact digest.
5. Simulate a failing test.
6. Verify dashboard attribution.

**Pass:** delivery failure traceable to pipeline.

## 28. Lab C — Argo CD metrics

1. Inspect installed Argo CD chart/version.
2. Discover actual metrics Services.
3. Configure supported scraping.
4. Trigger harmless OutOfSync state.
5. Observe sync and health metrics.
6. Restore desired state.

**Pass:** reconciliation visible.

## 29. Lab D — ApplicationSet telemetry

1. Record expected target count.
2. Reconcile disposable ApplicationSet.
3. Observe generated Applications.
4. Introduce invalid selector fixture.
5. Verify reconciliation error or target diff.
6. Restore inventory.

**Pass:** fleet placement anomalies observable.

## 30. Lab E — Kubernetes metrics

1. Inspect node and Pod metrics.
2. Deploy synthetic resource-constrained workload.
3. Generate controlled CPU demand.
4. Observe requests, limits and HPA.
5. Verify alerts.
6. Remove workload.

**Pass:** saturation and scheduling correlated.

## 31. Lab F — Prometheus ServiceMonitor

1. Expose synthetic /metrics endpoint.
2. Verify named Service port.
3. Apply ServiceMonitor.
4. Confirm target Up.
5. Deny scrape traffic temporarily.
6. Restore and verify samples.

**Pass:** discovery and failure detection work.

## 32. Lab G — OpenTelemetry collector

1. Deploy supported collector.
2. Configure OTLP receiver and TLS exporter.
3. Generate synthetic spans.
4. Inspect collector memory and queue.
5. Simulate destination outage.
6. Restore export and verify recovery.

**Pass:** telemetry pipeline bounded and resilient.

## 33. Lab H — Structured logs

1. Emit synthetic JSON application logs.
2. Add service, cluster, release and trace_id.
3. Verify parsing and search.
4. Inject a fake secret pattern.
5. Confirm redaction.
6. Check retention controls.

**Pass:** logs searchable without secret exposure.

## 34. Lab I — Distributed tracing

1. Instrument frontend and API.
2. Propagate W3C trace context.
3. Add synthetic slow dependency.
4. Identify high-latency span.
5. Correlate log by trace ID.
6. Verify sampling and redaction.

**Pass:** latency root cause traceable.

## 35. Lab J — Grafana service dashboard

1. Build RED panels.
2. Add deployment revision annotation.
3. Display error fraction and p99 latency.
4. Link logs and traces.
5. Link runbook.
6. Review with service owner.

**Pass:** dashboard supports incident triage.

## 36. Lab K — Alert routing

1. Create staging error alert.
2. Generate synthetic 5xx.
3. Verify threshold and duration.
4. Confirm team routing.
5. Recover workload.
6. Verify resolved notification.

**Pass:** alerts actionable and deduplicated.

## 37. Lab L — Synthetic user journey

1. Create approved synthetic endpoint.
2. Run regional black-box probe.
3. Record TLS, DNS and request timing.
4. Simulate endpoint failure.
5. Verify alert.
6. Restore and compare metrics.

**Pass:** user impact detectable.

## 38. Lab M — Audit correlation

1. Generate approved Kubernetes RBAC change.
2. Trigger denied cloud IAM access.
3. Find GitLab/Argo CD change context.
4. Correlate actor, cluster and timestamp.
5. Verify audit retention.
6. Archive redacted evidence.

**Pass:** change history attributable.

## 39. Lab N — Cardinality and cost

1. Measure current series count and ingestion.
2. Add synthetic high-cardinality label in staging.
3. Observe growth and cost proxy.
4. Remove label or relabel.
5. Verify series count stabilizes.
6. Document guardrail.

**Pass:** cardinality explosion controlled.

## 40. Lab O — End-to-end incident

1. Deploy synthetic bad revision through GitLab.
2. Observe Argo CD sync and application regression.
3. Trigger user-facing error alert.
4. Trace failing request to dependency.
5. Revert through reviewed GitOps MR.
6. Verify recovery and write RCA.

**Pass:** all telemetry supports a complete incident timeline.

## 41. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Prometheus target Down | ServiceMonitor/NetworkPolicy | Check discovery |
| 2 | Metrics absent | Exporter/port mismatch | Inspect endpoint |
| 3 | Metrics cardinality spikes | Unbounded labels | Drop label |
| 4 | Incorrect p99 | Histogram aggregation | Correct query |
| 5 | Argo CD metrics missing | Component service/version | Inspect chart |
| 6 | ApplicationSet drift invisible | Missing target metric | Add diff checks |
| 7 | GitLab pipeline dashboard empty | No exporter/API | Restore source |
| 8 | Collector OOM | Queue/batch pressure | Bound memory |
| 9 | OTLP export fails | TLS/endpoint/auth | Repair trust |
| 10 | Trace parent missing | Context propagation | Inspect headers |
| 11 | Logs unparseable | Schema mismatch | Fix parser |
| 12 | Secret appears in logs | Redaction gap | Contain and rotate |
| 13 | Alerts never fire | Query/route mismatch | Test rule |
| 14 | Alert storm | Grouping/silence issue | Tune routing |
| 15 | Synthetics false positive | Probe dependency | Cross-check |
| 16 | Cloud audit missing | Sink/category disabled | Restore collection |
| 17 | Dashboard slow | Expensive query | Reduce cardinality |
| 18 | Telemetry cost spike | Retention/egress | Apply budget |

## 42. Runbook — GitLab pipeline observability incident

1. Identify project, pipeline, runner and commit.
2. Inspect queue time, runner health and job logs.
3. Verify artifact digest and registry availability.
4. Distinguish CI failure from Argo CD deployment failure.
5. Restore scoped runner or pipeline dependency.
6. Confirm new synthetic job succeeds.
7. Document RCA.

## 43. Runbook — Argo CD reconciliation monitoring failure

1. Identify affected controller and cluster.
2. Check Argo CD component health and metrics Services.
3. Inspect repo-server and controller logs.
4. Verify scrape permissions and NetworkPolicy.
5. Restore metrics without altering app desired state.
6. Test OutOfSync detection.
7. Record evidence.

## 44. Runbook — metrics or collector outage

1. Determine affected signals and clusters.
2. Inspect collector Pods, CPU, memory and queues.
3. Verify endpoints, TLS, credentials and egress.
4. Restore provider-local critical alerts.
5. Apply bounded retry/memory configuration.
6. Generate synthetic metrics/traces.
7. Document missing-data window.

## 45. Runbook — distributed tracing gap

1. Identify service and trace propagation boundary.
2. Inspect W3C trace context at each hop.
3. Verify SDK sampling and exporter status.
4. Restore context and secure export.
5. Generate synthetic transaction.
6. Confirm full span tree and log correlation.
7. Record prevention.

## 46. Runbook — alert noise or blind spot

1. Identify service SLI and alert rule.
2. Review numerator, denominator and windows.
3. Inspect routing, grouping and inhibition.
4. Test synthetic degradation.
5. Tune thresholds without hiding user impact.
6. Confirm resolved notification.
7. Update runbook.

## 47. Runbook — telemetry data exposure

1. Contain affected logs/traces and restrict access.
2. Identify secret or sensitive field and affected retention.
3. Rotate exposed credentials through approved security process.
4. Repair application redaction and collector filters.
5. Verify negative tests.
6. Preserve compliant audit evidence.
7. Complete incident review.

## 48. Evidence template

~~~text
Change/incident ID:
GitLab pipeline, MR, commit and artifact digest:
Argo CD ApplicationSet/Application and revision:
Provider, region, cluster, namespace and service:
Metric source, query and retention:
Log source, parsing and redaction:
Trace ID, sampling and dependency:
Synthetic check and endpoint:
Alert rule, threshold and routing:
Audit event and actor:
Collector status and missing-data window:
Recovery timeline and SLO:
Cost, owner and approval:
~~~

## 49. Scored observability readiness

| Domain | Points | Evidence |
| --- | ---: | --- |
| Architecture and source inventory | 15 | Ownership and topology |
| Metrics and GitOps monitoring | 20 | Prometheus/Argo CD |
| Logs, traces and correlation | 20 | End-to-end trace |
| Dashboards and synthetics | 15 | User-facing health |
| Alerting and incident response | 20 | Synthetic failure |
| Security, cost and recovery | 10 | Redaction and budget |
| **Total** | **100** | |

**Pass:** at least 85/100 with mandatory gates: user-impacting outage detectable, GitOps change traceable, sensitive fields redacted, required audit logs available and critical alerts not dependent on a single telemetry backend.

## 50. Final acceptance checklist

- [ ] GitLab, Argo CD, Kubernetes and application signals inventoried.
- [ ] Provider/cluster/environment label contract enforced.
- [ ] Prometheus targets and Argo CD metrics verified.
- [ ] ApplicationSet target count monitored.
- [ ] OpenTelemetry collector bounded and secured.
- [ ] Structured logs parsed and redacted.
- [ ] Distributed traces correlate dependencies.
- [ ] Grafana dashboards include release annotations.
- [ ] Synthetic checks validate user journeys.
- [ ] Alerts tested and routed to owners.
- [ ] Cloud and Kubernetes audit evidence collected.
- [ ] Telemetry failure and cardinality limits tested.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Six production runbooks validated.
- [ ] Readiness score signed off.

## 51. Knowledge check

1. How do metrics, logs and traces complement each other?
2. Why does Argo CD Synced not prove user-facing availability?
3. What labels should be normalized across EKS, AKS and GKE?
4. Why are unbounded metric labels dangerous?
5. How does a ServiceMonitor select scrape targets?
6. What does the OpenTelemetry Collector memory limiter protect?
7. How can you correlate a GitLab release with a slow request?
8. Why do you need independent synthetic checks?
9. How should audit data be protected from ordinary application operators?
10. What happens when central telemetry aggregation fails?

## 52. References

- [OpenTelemetry](https://opentelemetry.io/docs/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Prometheus](https://prometheus.io/docs/)
- [Prometheus alerting](https://prometheus.io/docs/alerting/latest/overview/)
- [Grafana](https://grafana.com/docs/grafana/latest/)
- [Argo CD metrics](https://argo-cd.readthedocs.io/en/stable/operator-manual/metrics/)
- [Argo CD ApplicationSet](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/)
- [GitLab CI/CD](https://docs.gitlab.com/ci/)
- [Kubernetes observability](https://kubernetes.io/docs/concepts/cluster-administration/observability/)
- [Google SRE workbook](https://sre.google/workbook/table-of-contents/)

---

**Chapter 086 complete — Part 18 started.**

**Next:** Chapter 087 — GitOps Service-Level Indicators, SLOs, Error Budgets and Reliability Alerting.