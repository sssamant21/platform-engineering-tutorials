# Chapter 089 — Python Reliability Engineering, SLO Automation and Operational Readiness

**Part 09 — DevOps, SRE and Automation | Chapter 089/120 | Python 3.11+**

[Hands-on lab](labs/089-slo-reliability-operational-readiness-sre-dbre-lab.md) · [Executable Python project](labs/089/README.md)

## Learning objectives

Define reliable SLIs and SLOs, compute error budgets, detect fast and slow burn, evaluate operational readiness, gate unsafe releases, test missing-data behavior, and respond to incidents using deterministic Python automation. The chapter emphasizes safe read-only evaluation and explicit human approval for operational changes.

## 1. Reliability engineering architecture

\`\`\`text
requests / probes / telemetry -> validated SLI events
    -> windowed availability and latency aggregators
    -> objective target + rolling error budget
    -> short/long window burn rates
    -> policy engine: readiness and deployment gate
    -> alert evidence / runbook / incident commander
    -> manual remediation / controlled rollout
\`\`\`

An SLO is a user-centric objective, not a promise of zero failures. Define service boundary, eligible requests, exclusions, target, measurement window and ownership. Do not silently exclude failed requests from the denominator.

## 2. Service-level indicators

**Availability SLI** = good eligible requests / total eligible requests. Classify eligible, good and bad outcomes using explicit policy. A 5xx response is generally bad; an intentional client 4xx may or may not be eligible depending on the service contract. Missing telemetry is unknown, **not healthy**.

**Latency SLI** = eligible requests completed within the latency threshold / all eligible requests. A percentile such as p99 is useful diagnostically but the threshold-based good-event ratio maps directly to error budgets. Select threshold based on user experience, not arbitrary infrastructure utilization.

**Freshness SLI** for pipelines = expected datasets/partitions delivered before deadline / eligible expected deliveries. For DBRE workloads, combine availability with data correctness, lag, recovery point and restore confidence.

## 3. Error budgets

For SLO target \`T\` and \`N\` eligible requests, permitted bad events = \`N × (1 - T)\`. Actual bad events = \`N - good\`. Remaining budget = permitted - actual. The fractional remaining budget = \`(permitted - actual)/permitted\`. A negative number indicates budget overspend. For \`T=0.999\` and \`N=100000\`, budget is about 100 bad requests. If 150 are bad, budget is exhausted by 50. In a low-traffic service, fractional budgets can be smaller than one event; establish minimum sample thresholds and time-based monitoring policies before paging.

**Burn rate** = observed bad-event fraction / allowed bad-event fraction. Burn rate 1 consumes the budget at the planned rate; burn rate 14.4 means roughly 14.4 times the allowed rate. The lab implements two-window burn evaluation with a minimum-event gate. It is an educational model, not a complete Prometheus multiwindow, multi-burn alert design.

## 4. Alerting and operational gates

A fast-burn alert should require a high burn rate in both a short and a longer corroborating window to avoid noise. A slow-burn alert uses lower burn thresholds across longer windows. Production systems commonly combine 1h/5m, 6h/30m, and 3d/6h windows; tune for SLO period, traffic and response capacity. Use Alertmanager grouping, routing and inhibition, not one alert per request.

A release gate should evaluate: recent burn, remaining budget, monitoring health, rollback plan, deployment ownership, current incident severity and dependency status. Fail closed on missing evidence, but allow explicit, auditable emergency override by authorized personnel. A Python CLI flag is **not** an authentication mechanism.

## 5. Readiness dimensions

- **Observability:** SLI source healthy, scrape freshness, traces, logs and paging route tested.
- **Resilience:** tested backup/restore, HA and DR procedures with realistic RPO/RTO.
- **Capacity:** headroom, workload baselines, storage growth, queue depth and autoscaling limits.
- **Change management:** immutable artifacts, rollback plan, staged rollout, approval and audit.
- **Security:** least-privilege identities, secrets, TLS and change permissions.
- **Operations:** ownership, runbooks, escalation, incident response, maintenance windows and SLO review.

Readiness is not the same as Kubernetes readiness probes. A green Pod can coexist with severe database lag or an exhausted error budget.

## 6. Production SRE/DBRE scenarios

| Service | Relevant SLI and guardrails |
|---|---|
| PostgreSQL | successful transactions, query latency, replica lag, restore tests, WAL growth |
| Elasticsearch/OpenSearch | search success/latency, rejection rate, disk IOPS and shard allocation |
| MongoDB | read/write success, election stability, replication lag, restore point |
| Kafka/MSK | produce/fetch success, consumer freshness, ISR and partition availability |
| Snowflake | pipeline freshness, task success, warehouse queueing, credits |
| Kubernetes | workload availability, API error rate, Pod readiness, node pressure |

Do not use host CPU as a direct substitute for user-visible service reliability. Correlate infrastructure saturation with SLI degradation.

## 7. Common failure modes

1. Wrong denominator; 2. success-only instrumentation; 3. stale metrics; 4. missing telemetry treated as zero failures; 5. no-traffic window; 6. low-volume false alarms; 7. window boundary errors; 8. late-arriving events; 9. duplicated events; 10. counter resets; 11. 4xx classification mismatch; 12. latency threshold drift; 13. timezone confusion; 14. negative budget; 15. fast burn; 16. slow burn; 17. simultaneous alerts; 18. alert routing failure; 19. error-budget policy bypass; 20. rollback unavailable; 21. backup restore not tested; 22. database quorum risk; 23. storage IOPS saturation; 24. cross-region dependency failure; 25. maintenance exclusion misuse; 26. false green readiness; 27. capacity forecasting error; 28. unauthorized release override; 29. collector outage; 30. deployment-induced SLO regression.

## 8. Troubleshooting matrix

| Symptom | Investigation | Response |
|---|---|---|
| SLO shows 100% during outage | denominator and missing samples | Correct instrumentation; fail closed |
| Error budget unexpectedly negative | eligibility, window, duplicate events | Recompute from source of truth |
| Fast burn after deployment | release timeline, dependencies, 5xx | Pause rollout; consider approved rollback |
| Slow burn without incidents | background failures, latency, retries | Investigate systemic degradation |
| Readiness green but restore untested | backup/DR evidence | Block high-risk change until tested |
| High disk with good SLI | storage trend, IOPS, capacity | Plan capacity; avoid unnecessary paging |
| Burn alert storm | thresholds, dedup, routing | Tune sustained windows and grouping |

## 9. Operational runbooks

**SLO breach:** validate telemetry and eligibility, quantify impact, identify recent changes, assign incident commander, mitigate, record timeline and postmortem.

**Release gate blocked:** collect fresh evidence, confirm budget, investigate active incidents, verify rollback and escalate; never bypass via unreviewed script changes.

**Missing telemetry:** treat reliability as unknown, restore instrumentation and scrape health before declaring recovery.

**Database saturation:** check lag, quorum, storage latency, queue depth and backups; avoid blind restart or destructive cleanup.

**Error-budget policy:** slow or freeze nonessential releases while budget is exhausted; document exceptions with independent approval.

## 10. Executable lab and assessment

The [Chapter 089 lab](labs/089-slo-reliability-operational-readiness-sre-dbre-lab.md) contains actual standalone Python code and offline tests for SLI windows, budgets, burn rates, readiness gates and incident scenarios. The 100-point assessment requires tests and an operator-reviewed runbook. No live cloud or database mutation is part of this chapter.

**Next proposed:** Chapter 090 — Python DevOps/SRE Automation Production Capstone.
