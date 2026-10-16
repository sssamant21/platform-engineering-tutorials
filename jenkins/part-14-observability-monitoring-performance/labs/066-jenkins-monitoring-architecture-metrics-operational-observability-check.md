# Chapter 066 — Hands-on Lab: Jenkins Monitoring Architecture and Operational Observability

**Environment:** Disposable Jenkins LTS controller, Prometheus plugin, Prometheus/Grafana lab, synthetic Pipeline, optional Kubernetes agents. Never expose metrics publicly or use production secrets.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Capture core/plugin versions | Baseline |
| 02 | Architecture | Diagram signal/alert flow | Diagram |
| 03 | Endpoint | Enable supported metrics endpoint | HTTP result |
| 04 | Security | Restrict metrics access | Policy |
| 05 | Scrape | Add Prometheus target | Target status |
| 06 | Availability | Configure external probe | Result |
| 07 | JVM | Observe heap/GC/process | Dashboard |
| 08 | Queue | Generate synthetic queue load | Graph |
| 09 | Executors | Observe idle/busy capacity | Graph |
| 10 | Agents | Inspect online/offline state | Graph |
| 11 | Kubernetes | Inspect pending pod/events | Evidence |
| 12 | Pipelines | Run synthetic successful build | Result |
| 13 | Failures | Classify synthetic infrastructure failure | Taxonomy |
| 14 | Latency | Measure Pipeline stage duration | Chart |
| 15 | Cardinality | Review metric labels | Report |
| 16 | Dashboard | Build service overview | Screenshot |
| 17 | Alert | Test scrape failure alert | Fired |
| 18 | Queue | Test sustained wait alert | Fired |
| 19 | Recovery | Restore scrape/agent availability | Cleared |
| 20 | Handover | Complete operational sign-off | Report |

## 12 troubleshooting drills

1. Metrics endpoint 404 or incorrect context path.
2. Metrics endpoint denied by auth.
3. Prometheus TLS failure.
4. Scrape target missing.
5. UI unavailable while metrics still scrape.
6. Queue starvation from label mismatch.
7. Kubernetes agent pending due to quota.
8. Agent remoting disconnect.
9. Controller JVM heap pressure.
10. Plugin metric name changes.
11. High-cardinality label explosion.
12. Alert storm due to routing/inhibition.

## Lab configuration example

```yaml
scrape_configs:
  - job_name: jenkins-controller
    metrics_path: /prometheus/
    scrape_interval: 30s
    static_configs:
      - targets: ['jenkins.monitoring.svc.cluster.local:8080']
```

The address and endpoint are examples. Confirm the actual Jenkins Prometheus plugin path, TLS, authorization and service discovery.

## Evidence template

```text
UTC timestamp:
Jenkins core/plugin versions:
Metrics endpoint and access policy:
Prometheus target:
External synthetic probe:
Queue/executor/agent metrics:
JVM/GC metrics:
Pipeline failure classification:
Dashboard URL:
Alert fired and cleared:
Injected failure:
Recovery time:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Metrics endpoint access restricted.
- [ ] Service probe independent of metrics scrape.
- [ ] Queue and agent signals validated.
- [ ] Alert fired and recovered in lab.
- [ ] No unbounded build IDs in metric labels.
- [ ] No secrets in dashboards or evidence.
- [ ] Reviewer signs off.

**Related:** [Chapter 066 — Jenkins Monitoring Architecture, Metrics and Operational Observability](../066-jenkins-monitoring-architecture-metrics-operational-observability.md).
