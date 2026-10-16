# Chapter 070 — Jenkins Observability, Performance and Reliability Acceptance Capstone

**Part 14 — Observability, Monitoring and Performance (final capstone)**  
**Audience:** Jenkins SRE, platform engineering, observability, on-call, security and change management  
**Prerequisites:** Chapters 066–069; isolated Jenkins LTS, Prometheus/Grafana, Alertmanager test receiver, OpenTelemetry Collector, synthetic Pipelines and test agents.

## Mission

Design and validate an end-to-end Jenkins reliability observability platform with metrics, logs, traces, alerts, capacity baselines and operational runbooks. Demonstrate failure detection, investigation, recovery and a **100-point enterprise acceptance assessment**.

**Safety:** All load tests, failure injection, credential tests and rollbacks occur in a disposable lab. Do not perform disruptive experiments on shared production controllers.

## 1. Reference architecture

```text
SCM webhook → Jenkins controller → queue → Kubernetes/VM agents → Pipeline
                    |                 |                  |
              JVM/HTTP metrics     queue/agent        spans/logs
                    \                 |                  /
                     Prometheus + OTel Collector + log backend
                                   |
                        Grafana dashboards + SLOs
                                   |
                          Alertmanager → on-call
                                   |
                       incident/change/rollback evidence
```

External synthetic probes must be independent of Jenkins metrics scrapes. Jenkins OpenTelemetry plugin coverage and Prometheus metric names depend on installed versions: discover actual series/spans before writing production queries.

## 2. Required deliverables

| Deliverable | Minimum proof |
|---|---|
| Telemetry topology | Data flow, ownership and trust boundaries |
| Metrics inventory | Verified names, units and labels |
| Dashboards | Controller, JVM, queue, agents, Pipeline |
| Logs and traces | Build-to-stage correlation, redaction |
| SLI/SLO | Availability, queue wait, provisioning, infra failure |
| Alert routing | Test delivery, inhibition and recovery |
| Performance baseline | Normal/peak percentiles, resource limits |
| Failure drills | Detection, diagnosis, mitigation, verification |
| Runbooks | On-call first steps, rollback and escalation |
| Evidence | Timestamped results, reviewer and residual risks |

## 3. Service-level indicators

Define four independent service outcomes:

1. **Controller availability:** fraction of successful external synthetic checks. Scrape `up` is a telemetry SLI, not user availability.
2. **Queue responsiveness:** p95 queue wait per workload class and compatible agent pool.
3. **Agent readiness:** p95 time from provisioning request to ready executor.
4. **Infrastructure build reliability:** infrastructure-attributable failures divided by eligible builds, excluding application/test failures.

Optional indicators: controller restart rate, JVM GC pause, storage I/O latency, telemetry loss and alert delivery. Derive objectives from workload expectations, not copied defaults.

## 4. Example SLOs and error budget

Illustrative monthly SLOs:

| SLI | Example objective | Measurement |
|---|---|---|
| Synthetic controller availability | 99.9% | External probe |
| CI queue wait | p95 under 120 s | Verified queue telemetry |
| Warm-pool agent readiness | p95 under 90 s | Provisioning instrumentation |
| Infrastructure build success | 99% | Classified builds |

A 99.9% availability SLO over 30 days permits roughly **43.2 minutes** of unavailability if every minute is eligible. Specify maintenance exclusions, measurement gaps and low-traffic behavior in the SLO policy. Use multi-window burn-rate alerts only after implementing correct request/check-based numerator and denominator series.

## 5. Metrics, dashboard and alert acceptance

Verify:
- Prometheus scrapes via TLS and approved auth.
- Actual Jenkins plugin metric names/labels documented.
- External availability probe independent of scrape health.
- Grafana service, capacity, JVM, agent and Pipeline dashboards show real data.
- Recording rules map to supported histograms/gauges.
- Alertmanager routes a synthetic test alert to a configured receiver.
- Inhibition does not suppress unrelated incidents.
- Metric cardinality avoids raw build IDs and commit hashes.

Example **standard** Prometheus scrape-health alert:

```yaml
groups:
  - name: jenkins-capstone
    rules:
      - alert: JenkinsMetricsTargetDown
        expr: up{job="jenkins-controller"} == 0
        for: 5m
        labels:
          severity: warning
          service: jenkins
        annotations:
          summary: "Jenkins metrics target cannot be scraped"
```

This does **not** prove the Jenkins UI is unavailable. Alert on external probe failure separately.

## 6. Logs, traces and context

Use the Jenkins OpenTelemetry plugin with a compatible Collector and trace backend. Validate trace span coverage empirically; not all Jenkins stages or shell steps may be instrumented. Correlate build URL/ID in logs, not as an unbounded Prometheus label. Apply access controls and redaction to build console, controller logs, agent logs and exported spans.

## 7. Performance baseline and bottleneck isolation

Record normal and peak controller CPU, post-GC heap occupancy, GC pauses, thread contention, Jenkins home I/O, queue p95, executor utilization and agent provisioning p95. Distinguish:
- Controller bottleneck: CPU/GC/thread/I/O saturation.
- Queue bottleneck: labels, locks, throttling, executor mismatch.
- Agent bottleneck: Pending pods, image pulls, quota, remoting.
- Build bottleneck: checkout, compilation, tests, artifact repository.

Do not increase controller executors to fix missing agent capacity.

## 8. Controlled failure scenarios

| # | Failure | Expected detection/recovery |
|---|---|---|
| 01 | Metrics scrape blocked | Target alert, restore auth/network |
| 02 | UI unavailable but metrics up | External probe catches outage |
| 03 | Queue starvation | p95 alert and label/agent fix |
| 04 | Agent pod Pending | Kubernetes event correlation |
| 05 | Agent OOMKilled | Pod status and resource correction |
| 06 | Remoting disconnect | Controller/agent log correlation |
| 07 | Controller CPU saturation | CPU and latency alert |
| 08 | JVM GC pressure | Heap/GC correlation |
| 09 | Jenkins home disk pressure | Storage capacity/latency |
| 10 | Plugin metrics schema change | Inventory/dashboards repair |
| 11 | OTel exporter unreachable | Collector export failure |
| 12 | Trace gaps | Sampling/instrumentation investigation |
| 13 | Alertmanager receiver misconfigured | Test delivery fails |
| 14 | Overbroad alert inhibition | Independent alert restored |
| 15 | High-cardinality metrics | Series review and relabel |
| 16 | Missing log correlation | Log pipeline fix |
| 17 | SCM checkout regression | Stage trace/log diagnosis |
| 18 | Slow artifact publishing | Stage timing and backend check |
| 19 | Untrusted data in telemetry | Redact/revoke/purge |
| 20 | Post-upgrade performance regression | Baseline comparison/rollback |

## 9. Five production runbooks

### A. Controller outage
1. Verify external synthetic probe and scrape independently.
2. Check controller process/pod, ingress, auth and recent changes.
3. Inspect JVM, storage, plugin startup and JCasC logs.
4. Recover via approved restart or known-good rollback.
5. Validate login, queue, agents and representative Pipeline.

### B. Queue and agent starvation
1. Inspect oldest queue reasons and p95 wait.
2. Match job labels to compatible online executors.
3. Check Kubernetes Pending events, quotas and image pulls.
4. Restore pool capacity or constraints.
5. Verify queue drain and agent readiness SLI.

### C. JVM/controller performance incident
1. Capture CPU, GC, heap and storage I/O.
2. Review thread samples and recent plugin changes.
3. Apply safe mitigation or approved rollback.
4. Monitor post-GC heap and queue latency.
5. Document root cause and prevention.

### D. Telemetry or alert delivery outage
1. Confirm Prometheus scrape and Collector receiver/exporter health.
2. Check TLS/auth, target discovery and metric schema.
3. Verify Alertmanager route, receiver and silences.
4. Send synthetic test notification.
5. Confirm restored end-to-end visibility and ownership.

### E. Sensitive data in telemetry
1. Restrict access and stop offending export.
2. Identify affected logs, spans and recipients.
3. Revoke/rotate exposed secrets as appropriate.
4. Purge data per retention/security policy and add filtering.
5. Re-test redaction and document incident.

## 10. Operational change and evidence

Every monitoring change should have Git SHA, reviewer, dashboard/rule diff, plugin/exporter version, synthetic validation, rollout time, alert routing test and rollback path. Store sanitized evidence with defined retention and RBAC. Dashboard screenshots alone do not prove alerts or recovery.

## 11. 100-point acceptance scorecard

| Domain | Points |
|---|---:|
| Architecture and telemetry inventory | 10 |
| Prometheus metrics and secure collection | 15 |
| Grafana dashboards and SLI/SLO definitions | 15 |
| Alertmanager routing and noise control | 15 |
| Logs, traces and correlation | 10 |
| JVM, queue and agent performance analysis | 15 |
| Failure drills and incident response | 10 |
| Recovery, change control and evidence | 10 |
| **Total** | **100** |

Suggested pass: **85/100**, plus mandatory gates:
- No secrets exposed in metrics, logs, traces or evidence.
- External availability probe independent of metrics scrape.
- Actual exporter metric names verified.
- Test alert delivered and acknowledged.
- Queue/agent failure investigated and recovered.
- Performance baseline and rollback evidence recorded.

Mark unsupported features **not tested** rather than passed.

## 12. Handover checklist

- [ ] Controller and telemetry components inventoried.
- [ ] Secure metrics, logs and traces verified.
- [ ] Dashboard owners and on-call routes assigned.
- [ ] SLO definitions and thresholds reviewed.
- [ ] Alert delivery and inhibition tested.
- [ ] Queue, JVM, agent and storage baselines documented.
- [ ] 20 synthetic failure scenarios exercised or blocked.
- [ ] Incident recovery and rollback demonstrated.
- [ ] 100-point assessment signed.
- [ ] Residual risks and follow-up owners recorded.

**Companion:** [Chapter 070 capstone lab](labs/070-jenkins-observability-performance-reliability-acceptance-capstone-check.md).  
**Part 14 complete:** Chapters 066–070.  
**Next:** Chapter 071 — Jenkins Troubleshooting Methodology, Diagnostics and Incident Triage (Part 15).
