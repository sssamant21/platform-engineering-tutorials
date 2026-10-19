# Chapter 094 — IaC SLO Engineering, Error Budgets, Alerting, Incident Response and Automated Reliability Controls

**Part 19 — Observability and Drift · Chapter 094/120 · SRE / DevOps / DBRE**

> **Evidence boundary:** The Python labs are executable offline exercises using synthetic data. They do not execute Terraform/OpenTofu, query Prometheus, send Alertmanager notifications, control Kubernetes, or restore a database. Native integrations, live paging and RPO/RTO acceptance require authorized staging tests.

## 1. Outcomes

Engineer reliable infrastructure changes through service-level indicators (SLIs), service-level objectives (SLOs), error budgets, multi-window burn-rate alerting, incident response and safe automated reliability controls. Apply these concepts to Terraform/OpenTofu, Pulumi, CloudFormation, Bicep, Ansible, AWS/Azure/GCP, Kubernetes/GitOps, PostgreSQL, Aurora/RDS, MongoDB, Redis, Kafka/MSK, Elasticsearch/OpenSearch and Snowflake.

**Principle:** a successful `terraform apply` is a control-plane event, not proof of customer availability, data correctness or recoverability.

## 2. Enterprise architecture

~~~text
Approved Git revision + immutable plan + change ticket
                 |
CI/CD -> IaC policy -> staged deployment -> GitOps
                 |                     |
       OTel logs/traces/events     service and DBRE telemetry
                 |                     |
         Prometheus / cloud monitoring / audit
                 |
     SLI validity + sample freshness + denominator
                 |
        SLO windows + error-budget ledger
                 |
   multi-window burn-rate + severity + ownership
                 |
      Alertmanager / paging / incident command
                 |
  gate: proceed | hold | quarantine | approved rollback
                 |
   verify customer SLO + DBRE RPO/RTO + audit closure
~~~

Separate the telemetry producer from the gate that evaluates it. Fail closed on absent, stale or contradictory signals; avoid a single metric or pipeline self-report as the sole authority. Keep a bounded, auditable exception process and a manual incident-command override for emergencies.

## 3. Detailed SLI/SLO engineering

### 3.1 SLIs and denominators

- **Request availability:** good eligible requests / all eligible requests, excluding only explicitly documented classes such as health probes.
- **Latency:** proportion of eligible requests meeting a defined threshold; p95 is useful for diagnosis but percentile-of-percentiles must not be averaged.
- **Change failure rate:** distinct eligible production changes requiring incident, hotfix or rollback / distinct eligible production changes. Deduplicate CI retries.
- **Deployment reliability:** approved successful changes / eligible attempted changes. Do not mix development and production.
- **Drift freshness:** scans completed within detection deadline / expected scans; missing scans count as failures, not successes.
- **DBRE restore:** measured RPO and RTO with integrity and application readiness checks, not backup-job status alone.
- **Telemetry coverage:** fresh trusted observations / expected observations.

Example objectives, to be calibrated by service tier: 99.9% 30-day request availability; >=99% safe deployment success; critical drift detection within 15 minutes at least 99.5% of eligible checks; p95 IaC pipeline <=20 minutes; zero destructive auto-remediation; database RPO <=15 minutes and RTO <=60 minutes when measured by a real DR exercise.

### 3.2 Error budgets and burn rates

For an objective `S`, permitted error fraction is `1-S`. Over `N` eligible requests, allowed bad requests are `N*(1-S)`; budget consumed is actual bad requests / allowed bad requests. Burn rate over a short window is observed bad fraction / permitted bad fraction. **Illustrative**: 99.9% availability permits about 43.2 minutes of continuous unavailability in a 30-day window, but request-based error budgets must be measured in requests, not minutes.

Example multi-window policy for a 30-day 99.9% request SLO: page when burn >=14.4 on both 5m and 1h windows, or burn >=6 on both 30m and 6h windows; create a ticket at lower sustained rates such as burn >=1 over 3 days. These are examples, not universal thresholds. Require minimum traffic/sample adequacy, freshness and correct scope. Missing data yields **UNKNOWN** and a telemetry-health alert.

### 3.3 Budget policy and deployment controls

When error budget is healthy, proceed with reviewed changes and staged rollout. Under fast burn, freeze risky changes and notify incident command. Under exhausted budget, hold discretionary production changes while allowing explicitly approved urgent security/recovery work. Never let a synthetic budget, stale dashboard or one metric autonomously delete data, rotate KMS keys, change IAM trust or force-unlock state.

### 3.4 PromQL examples (custom metrics)

~~~promql
sum(rate(iac_change_failures_total{environment="production"}[1h]))
/
clamp_min(sum(rate(iac_change_attempts_total{environment="production"}[1h])), 0.000001)
~~~

~~~promql
(
 sum(rate(http_requests_total{outcome="error"}[5m]))
 /
 clamp_min(sum(rate(http_requests_total[5m])), 0.000001)
) / 0.001
~~~

A real implementation must account for absent data, low traffic and expected metric naming. Configure recording rules and Alertmanager routes with explicit ownership, runbook URL, severity, deduplication, inhibition, maintenance-window rules and notification-delivery verification. Keep DBRE paging separate from generic deployment alerts when recovery expertise is required.

## 4. Safe reliability automation

**Gate states:** `PROCEED`, `HOLD`, `QUARANTINE`. Reject unknown target, untrusted source, missing telemetry, unsafe plan, active critical incident, unapproved rollback, database destruction, excessive blast radius and missing recovery readiness. Low-risk nonproduction rollback can be proposed; production actions require separate authorization and canary checks.

Use a circuit breaker with cooldown, max attempts, independent approval and audit. A reliability controller should **recommend** an action before it gains tightly scoped permission to execute one. Preserve last known-good artifact, plan digest, backend state version, DB backup identifiers and measured post-change SLO. No self-approving destructive remediation.

## 5. Hands-on labs

### Lab A — Synthetic SLO assurance gate

~~~bash
cd infrastructure-as-code/labs/chapter-094
python3 reliability_gate.py fixtures/safe.json policy.json
python3 reliability_gate.py fixtures/unsafe.json policy.json # expected rejection
bash run-preflight.sh
~~~

The gate checks exact synthetic target, 34 claimed controls, SLO/error-budget data quality, freshness, critical findings, destructive changes, alert delivery claims and DBRE recovery objectives.

### Lab B — Error-budget and burn-rate calculator

`slo_math.py` computes request-based availability, remaining budget and burn rates using strict input validation. It rejects boolean counts, impossible errors, invalid objectives and missing windows.

### Lab C — Multi-window alert policy

`alert_policy.py` evaluates 5m/1h and 30m/6h synthetic burn-rate pairs, requires fresh data and sufficient request counts, and returns `PAGE`, `TICKET`, `OK` or `UNKNOWN`. It does **not** send pages.

### Lab D — Reliability change gate

`change_gate.py` produces `PROCEED`, `HOLD` or `QUARANTINE` for synthetic IaC changes; destructive/database/high-risk/unknown changes are never automatically approved.

### Lab E — Authorized native staging game day (not executed)

1. Use an isolated staging account, pinned IaC revision, read-only monitoring and a capped budget.
2. Export real request SLIs and IaC change metrics into Prometheus; validate scrape freshness, cardinality and error-budget arithmetic.
3. Route a controlled test page through Alertmanager to the assigned staging responder; verify receipt and escalation.
4. Inject reversible canary failures and verify multi-window SLO gates halt promotion.
5. Exercise approved rollback and check application and DBRE health; do not auto-restore or delete production data.
6. Perform isolated PostgreSQL/Aurora/MongoDB/Redis/Kafka recovery as appropriate; measure RPO/RTO and data correctness.
7. Archive native audit, timeline, alerts, runbook execution and independent SRE/DBRE/security sign-off.

## 6. Sixty production incident simulations

| # | Scenario | First action |
|---|---|---|
| 1 | Terraform apply duration breaches deployment SLO | Verify denominator, freshness, paging and incident impact |
| 2 | OpenTofu state lock contention exhausts change window | Correlate immutable IaC change, policy, plan, runtime SLO |
| 3 | Provider 429 errors drive deployment failure rate | DBRE checks data-plane SLI and measured recovery |
| 4 | Terraform plan replacement exceeds blast-radius policy | Correlate immutable IaC change, policy, plan, runtime SLO |
| 5 | Pulumi preview fails to detect downstream outage | Correlate immutable IaC change, policy, plan, runtime SLO |
| 6 | CloudFormation rollback stalls after timeout | Correlate immutable IaC change, policy, plan, runtime SLO |
| 7 | Azure Bicep what-if reports unsafe resource deletion | Correlate immutable IaC change, policy, plan, runtime SLO |
| 8 | GCP API quota causes partial deployment | Correlate immutable IaC change, policy, plan, runtime SLO |
| 9 | Ansible rollout causes 5xx spike | Correlate immutable IaC change, policy, plan, runtime SLO |
| 10 | GitHub Actions OIDC token expires mid-deployment | Correlate immutable IaC change, policy, plan, runtime SLO |
| 11 | GitLab CI job retries double-count change attempts | Correlate immutable IaC change, policy, plan, runtime SLO |
| 12 | Prometheus scrape target disappears during outage | Verify denominator, freshness, paging and incident impact |
| 13 | OpenTelemetry collector drops deployment spans | DBRE checks data-plane SLI and measured recovery |
| 14 | SLO dashboard silently uses stale series | Verify denominator, freshness, paging and incident impact |
| 15 | Error budget calculation uses wrong denominator | Verify denominator, freshness, paging and incident impact |
| 16 | Burn-rate alert fires on one low-volume error | Verify denominator, freshness, paging and incident impact |
| 17 | Critical burn-rate alert never reaches on-call | Verify denominator, freshness, paging and incident impact |
| 18 | Alertmanager inhibition suppresses DBRE incident | Verify denominator, freshness, paging and incident impact |
| 19 | Paging route points to off-duty responder | Correlate immutable IaC change, policy, plan, runtime SLO |
| 20 | Canary analysis ignores database latency | DBRE checks data-plane SLI and measured recovery |
| 21 | Progressive rollout advances despite SLO failure | Verify denominator, freshness, paging and incident impact |
| 22 | Rollback trigger references outdated revision | Correlate immutable IaC change, policy, plan, runtime SLO |
| 23 | Automatic rollback attempts destructive database change | DBRE checks data-plane SLI and measured recovery |
| 24 | State backend loses consistency during recovery | Correlate immutable IaC change, policy, plan, runtime SLO |
| 25 | Terraform force-unlock collides with active apply | Correlate immutable IaC change, policy, plan, runtime SLO |
| 26 | Policy-as-code evaluation becomes unavailable | Correlate immutable IaC change, policy, plan, runtime SLO |
| 27 | OPA deny enforcement is downgraded to audit | Correlate immutable IaC change, policy, plan, runtime SLO |
| 28 | Sentinel override lacks independent approval | Correlate immutable IaC change, policy, plan, runtime SLO |
| 29 | AWS IAM role trust expands to untrusted repo | Correlate immutable IaC change, policy, plan, runtime SLO |
| 30 | Azure Policy assignment stops enforcing encryption | Correlate immutable IaC change, policy, plan, runtime SLO |
| 31 | GCP Org Policy exception expires unnoticed | Correlate immutable IaC change, policy, plan, runtime SLO |
| 32 | EKS workload fails readiness after IaC change | Correlate immutable IaC change, policy, plan, runtime SLO |
| 33 | AKS CNI regression causes pod network errors | Correlate immutable IaC change, policy, plan, runtime SLO |
| 34 | GKE autoscaler hits regional quota | Correlate immutable IaC change, policy, plan, runtime SLO |
| 35 | Argo CD application stuck OutOfSync | Correlate immutable IaC change, policy, plan, runtime SLO |
| 36 | Flux controller loops on invalid desired state | Correlate immutable IaC change, policy, plan, runtime SLO |
| 37 | Kubernetes admission webhook latency breaches SLO | Verify denominator, freshness, paging and incident impact |
| 38 | PostgreSQL replication lag consumes RPO budget | DBRE checks data-plane SLI and measured recovery |
| 39 | Aurora failover exceeds RTO | DBRE checks data-plane SLI and measured recovery |
| 40 | RDS backup retention falls below recovery policy | DBRE checks data-plane SLI and measured recovery |
| 41 | MongoDB primary election exceeds availability objective | DBRE checks data-plane SLI and measured recovery |
| 42 | MongoDB oplog window threatens recovery point | DBRE checks data-plane SLI and measured recovery |
| 43 | Redis eviction storm raises latency | DBRE checks data-plane SLI and measured recovery |
| 44 | Redis failover creates connection failures | DBRE checks data-plane SLI and measured recovery |
| 45 | Kafka MSK ISR loss threatens durability | DBRE checks data-plane SLI and measured recovery |
| 46 | Kafka consumer lag exceeds freshness SLO | DBRE checks data-plane SLI and measured recovery |
| 47 | Elasticsearch shard relocation saturates IOPS | DBRE checks data-plane SLI and measured recovery |
| 48 | OpenSearch snapshot fails during DR drill | DBRE checks data-plane SLI and measured recovery |
| 49 | Snowflake warehouse queue breaches query SLO | DBRE checks data-plane SLI and measured recovery |
| 50 | Snowflake CDC task falls behind freshness objective | DBRE checks data-plane SLI and measured recovery |
| 51 | Cross-region DR restores wrong encryption key | DBRE checks data-plane SLI and measured recovery |
| 52 | SLO burn rate rises after harmless scheduled maintenance | Verify denominator, freshness, paging and incident impact |
| 53 | Low-traffic service has statistically unstable SLI | Correlate immutable IaC change, policy, plan, runtime SLO |
| 54 | Multi-window alert uses mismatched time windows | Verify denominator, freshness, paging and incident impact |
| 55 | Reliability gate accepts missing metric as zero | Verify denominator, freshness, paging and incident impact |
| 56 | Synthetic telemetry fixture falsely certifies live health | Verify denominator, freshness, paging and incident impact |
| 57 | Remediation controller repeatedly toggles resources | Correlate immutable IaC change, policy, plan, runtime SLO |
| 58 | Unmanaged cloud resources inflate monthly spend | Correlate immutable IaC change, policy, plan, runtime SLO |
| 59 | Incident evidence timestamps conflict across sources | Correlate immutable IaC change, policy, plan, runtime SLO |
| 60 | Post-incident corrective action misses deadline | Correlate immutable IaC change, policy, plan, runtime SLO |

## 7. Twelve production runbooks

**R1 — Declare SLO incident and establish command:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

**R2 — Validate SLI denominator and telemetry freshness:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

**R3 — Compute error budgets and multi-window burn rates:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

**R4 — Prometheus/Alertmanager and OTel delivery recovery:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

**R5 — IaC plan/apply failure and safe freeze:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

**R6 — State locks, providers and cloud throttling:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

**R7 — Progressive delivery and canary rollback:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

**R8 — Kubernetes, Argo CD and Flux reconciliation:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

**R9 — AWS/Azure/GCP identity, audit and policy:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

**R10 — PostgreSQL/Aurora/MongoDB/Redis recovery:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

**R11 — Kafka/OpenSearch/Elasticsearch/Snowflake recovery:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

**R12 — Automated controls, audit evidence and postmortem:** Identify service tier, incident commander, change ID, blast radius and active SLO window. Verify trusted metric provenance, UTC event time, freshness, denominator, error-budget consumption and alert route. Preserve Git revision, immutable plan, state snapshot, provider audit, traces and database telemetry. Freeze unsafe automation, obtain independent approval for rollback/DR, execute a bounded mitigation, and measure post-action application SLO, data integrity and actual RPO/RTO. Close with evidence, corrective owner and follow-up date.

## 8. Troubleshooting

| Symptom | Check | Response |
|---|---|---|
| False SLO green | missing series, staleness, denominator | UNKNOWN; restore telemetry |
| Burn-rate noise | low request volume, short windows | sample floor, paired windows |
| Alert not delivered | route, receiver, inhibition, silence | test escalation end to end |
| CI green, customer errors | missing canary/DBRE signal | block promotion |
| Repeated rollbacks | controller retry loop, state version | circuit breaker and human review |
| Terraform state locked | active runner, backend lease | preserve evidence; coordinated recovery |
| Database RTO breach | KMS, WAL/oplog, storage, application readiness | DBRE DR command |
| Emergency exception abused | approval, TTL, compensating controls | security review and expiry |

## 9. 100-point assessment

| Domain | Points |
|---|---:|
| Enterprise architecture and SLI definitions | 15 |
| Error-budget mathematics and SLO policies | 20 |
| Multi-window alerting and delivery | 20 |
| Offline labs, negative tests and safe automation | 20 |
| DBRE recovery and incident game days | 15 |
| Runbooks, audit and independent acceptance | 10 |
| **Total** | **100** |

**Pass >=85 with zero critical failures.** Critical failures include wrong-target changes, false-green missing telemetry, undelivered critical alerts, unsafe destructive auto-remediation, unapproved rollback, or missed DBRE RPO/RTO. Operational acceptance requires native evidence, executed drills and SRE/DBRE/security sign-off.

**Next:** Chapter 095 — Enterprise IaC Observability, Drift, SLO and Incident Response Reliability Acceptance Capstone.
