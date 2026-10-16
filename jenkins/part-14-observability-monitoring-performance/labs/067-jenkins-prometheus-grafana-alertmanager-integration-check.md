# Chapter 067 — Hands-on Lab: Jenkins Prometheus, Grafana and Alertmanager

**Environment:** Disposable Jenkins LTS + Prometheus plugin, Prometheus, Grafana, Alertmanager, synthetic Pipelines, optional Prometheus Operator. Use a test notification receiver.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record versions/endpoints | Baseline |
| 02 | Security | Restrict metrics endpoint | Policy |
| 03 | Scrape | Configure Prometheus target | Target |
| 04 | Discovery | Enumerate actual metric names | Inventory |
| 05 | Labels | Review metric cardinality | Report |
| 06 | Probe | Add independent external health probe | Result |
| 07 | Queue | Generate synthetic backlog | Graph |
| 08 | Executors | Observe busy/idle ratio | Graph |
| 09 | JVM | Inspect heap/GC metrics | Graph |
| 10 | Agents | Observe online/offline state | Graph |
| 11 | Recording | Create valid SLI rule | Query |
| 12 | Dashboard | Build service overview | Screenshot |
| 13 | Dashboard | Build agent/capacity view | Screenshot |
| 14 | Alert | Add scrape-down alert | Rule |
| 15 | Alert | Add sustained queue alert | Rule |
| 16 | Route | Configure test Alertmanager receiver | Config |
| 17 | Notification | Verify delivered test alert | Receipt |
| 18 | Inhibition | Test scoped suppression | Result |
| 19 | Recovery | Restore target and clear alert | Timeline |
| 20 | Review | Complete acceptance and handover | Report |

## 12 troubleshooting drills

1. Wrong metrics endpoint path.
2. TLS certificate failure.
3. Metrics endpoint access denied.
4. Prometheus target absent.
5. Scrape healthy but UI down.
6. Missing queue metric.
7. Histogram bucket mismatch.
8. Grafana datasource failure.
9. Alert expression never fires.
10. Alertmanager receiver missing.
11. Duplicate or suppressed notifications.
12. High-cardinality metric regression.

## Example validation commands

```sh
promtool check rules monitoring/jenkins-alerts.yaml
amtool check-config monitoring/alertmanager.yaml
```

These tools must be installed. Do not assume illustrative metrics exist; map them to the real exporter before testing.

## Evidence template

```text
UTC timestamp:
Jenkins/Prometheus/Grafana/Alertmanager versions:
Metrics endpoint and access policy:
Actual metric names:
Prometheus target status:
External probe:
Recording rule results:
Dashboard links:
Alert firing timestamp:
Alertmanager receiver and delivery proof:
Recovery timestamp:
Cardinality review:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Metrics endpoint protected.
- [ ] Queries use verified metric names.
- [ ] Grafana dashboards show real data.
- [ ] Test notification delivered and recovered.
- [ ] Alert routing and inhibition validated.
- [ ] No secrets in evidence.
- [ ] Reviewer signs off.

**Related:** [Chapter 067 — Jenkins Prometheus, Grafana Dashboards and Alertmanager Integration](../067-jenkins-prometheus-grafana-alertmanager-integration.md).
