# Chapter 070 — Hands-on Capstone: Jenkins Observability, Performance and Reliability Acceptance

**Environment:** Disposable Jenkins LTS, Prometheus/Grafana, Alertmanager test receiver, OTel Collector, synthetic Pipelines and optional Kubernetes agents. Never run disruptive tests against production.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory Jenkins and telemetry versions | Baseline |
| 02 | Diagram metrics/logs/traces/alert routing | Architecture |
| 03 | Secure Prometheus scrape | Policy |
| 04 | Discover actual Jenkins metric names | Inventory |
| 05 | Configure independent external probe | Probe |
| 06 | Create controller/JVM dashboard | Screenshot |
| 07 | Create queue/executor dashboard | Screenshot |
| 08 | Create agent/Kubernetes dashboard | Screenshot |
| 09 | Define availability SLI/SLO | Document |
| 10 | Define queue and agent SLI/SLO | Document |
| 11 | Create and lint alert rules | Result |
| 12 | Deliver synthetic Alertmanager notification | Receipt |
| 13 | Validate alert grouping/inhibition | Test |
| 14 | Export synthetic Pipeline traces | Trace ID |
| 15 | Correlate controller, agent and build logs | Evidence |
| 16 | Measure normal/peak performance baseline | Graphs |
| 17 | Inject lab queue/agent bottleneck | Incident |
| 18 | Diagnose root cause with signals | RCA |
| 19 | Recover and compare before/after | Timeline |
| 20 | Complete 100-point assessment and sign-off | Scorecard |

## 20 failure drills

1. Metrics scrape unavailable.
2. UI unavailable with healthy scrape.
3. Queue starvation.
4. Kubernetes agent Pending.
5. Agent OOMKilled.
6. Remoting disconnect.
7. Controller CPU saturation.
8. JVM GC pressure.
9. Jenkins home disk pressure.
10. Plugin metric name regression.
11. OTel exporter unreachable.
12. Missing trace spans.
13. Alertmanager receiver failure.
14. Incorrect inhibition.
15. High-cardinality metric regression.
16. Missing log correlation.
17. SCM checkout latency.
18. Artifact publishing latency.
19. Sensitive telemetry attribute.
20. Post-upgrade performance regression.

## Example Prometheus validation

```sh
promtool check rules monitoring/jenkins-alerts.yaml
amtool check-config monitoring/alertmanager.yaml
```

Install the appropriate CLI versions. Rules must reference verified exporter series; the commands check syntax, not end-to-end alert delivery.

## Evidence template

```text
UTC timestamp:
Jenkins core/plugins/JVM:
Prometheus/Grafana/Alertmanager/OTel versions:
Metrics endpoint and security:
Verified metric names:
External probe:
Dashboard links:
SLO definitions:
Alert fired/delivered/cleared:
Trace/log correlation:
CPU/heap/GC/storage baseline:
Queue/executor/agent p95:
Injected failure:
Root cause and mitigation:
Recovery time:
Assessment score:
Mandatory gate status:
Reviewer and residual risks:
```

## 100-point scorecard

| Domain | Max |
|---|---:|
| Architecture/telemetry inventory | 10 |
| Secure metrics collection | 15 |
| Dashboards and SLIs/SLOs | 15 |
| Alert routing/noise control | 15 |
| Logs/traces/correlation | 10 |
| JVM/queue/agent performance | 15 |
| Failure drills/incident response | 10 |
| Recovery/change/evidence | 10 |
| **Total** | **100** |

Suggested pass: 85 and all mandatory gates from the chapter.

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 20 drills completed or explicitly blocked.
- [ ] Metrics, logs and traces accessible with least privilege.
- [ ] External probe distinguishes service from scrape failure.
- [ ] Test alert delivered and recovered.
- [ ] Performance bottleneck isolated and resolved.
- [ ] No secrets in telemetry or evidence.
- [ ] Rollback/recovery verified.
- [ ] Scorecard and handover signed.

**Related:** [Chapter 070 — Jenkins Observability, Performance and Reliability Acceptance Capstone](../070-jenkins-observability-performance-reliability-acceptance-capstone.md).
