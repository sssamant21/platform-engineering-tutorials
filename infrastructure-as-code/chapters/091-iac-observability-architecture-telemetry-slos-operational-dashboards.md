# Chapter 091 — IaC Observability Architecture, Telemetry, SLOs and Operational Dashboards

**Part 19 — Observability and Drift · Chapter 091/120 · Enterprise SRE/DevOps/DBRE**

> The accompanying labs are **offline synthetic exercises**. They do not connect to cloud providers, Prometheus, Grafana, OpenTelemetry collectors, Kubernetes, Terraform/OpenTofu or databases. Native integrations and production reliability acceptance require authorized staging validation.

## 1. Outcomes

Build an enterprise observability architecture for Infrastructure as Code across Terraform/OpenTofu, Pulumi, CloudFormation, Bicep, Ansible, CI/CD, Kubernetes, GitOps, AWS/Azure/GCP and stateful databases. Define actionable metrics, logs, traces, events, SLI/SLO/error-budget policies, alert routing, dashboards, change correlation, incident investigation and cost/cardinality controls.

The core question is not whether an IaC pipeline passed, but whether **the intended infrastructure change reached a safe, observable, reversible and SLO-compliant operating state**.

## 2. Reference architecture

~~~text
Git commit / PR / change ticket / immutable artifact
                |
 CI runners -> plan/validate/policy -> approved apply
                |                |
 structured logs + spans      events and metrics
                |                |
     OTLP collectors / Prometheus / cloud audit
                |
  attribute normalization + sampling + redaction
                |
   traces / time-series / searchable audit events
                |
 IaC SLOs + GitOps health + drift + DBRE telemetry
                |
 Grafana / cloud dashboards / burn-rate alert rules
                |
  on-call SRE + DBRE + security + incident command
                |
  remediation + rollback + restore + audit evidence
~~~

Use a consistent correlation model: `environment`, `service`, `pipeline_id`, `run_id`, `change_id`, `source_revision`, `provider`, `region`, `control_id` and low-cardinality `outcome`. Put high-cardinality identifiers such as resource ARN, database query text, trace IDs and user IDs in **logs/traces**, not metric labels. Redact state, credentials, tokens, sensitive SQL and regulated data before export.

## 3. Telemetry design and data contracts

### 3.1 Metrics

| Metric | Type | Purpose | Safe labels |
|---|---|---|---|
| `iac_pipeline_runs_total` | counter | success/failure by stage | environment, tool, outcome |
| `iac_pipeline_duration_seconds` | histogram | p50/p95/p99 deployment latency | environment, tool, stage |
| `iac_plan_destructive_changes_total` | counter | planned deletes/replacements | environment, risk |
| `iac_state_lock_wait_seconds` | histogram | contention | backend, environment |
| `iac_policy_denials_total` | counter | rejected unsafe changes | policy_family, environment |
| `iac_drift_findings` | gauge | open classified drift | environment, severity |
| `iac_drift_detection_age_seconds` | gauge | observation staleness | environment |
| `iac_gitops_reconcile_duration_seconds` | histogram | reconciliation latency | cluster, controller |
| `iac_resource_orphans` | gauge | leaked test resources | account_tier, owner_team |
| `iac_observability_export_failures_total` | counter | missing telemetry | exporter, outcome |
| `iac_dbre_restore_duration_seconds` | histogram | actual recovery duration | engine, environment |
| `iac_change_slo_breaches_total` | counter | regressions after rollout | service, environment |

Do not attach `resource_id`, `trace_id`, `commit_sha`, `query` or arbitrary tag maps as Prometheus labels. Estimate active series as product of distinct label values and budget per service. Validate histogram buckets against realistic latency distributions and avoid interpreting average latency as tail latency.

### 3.2 Logs, traces and events

Emit structured JSON events for `plan_started`, `policy_denied`, `apply_started`, `apply_failed`, `reconcile_completed`, `drift_detected`, `restore_verified`, `rollback_completed`. Include UTC timestamp, actor class, protected source revision, immutable artifact digest, approved change, target, outcome, sanitized error class and evidence URI. Trace CI stages, provider calls, admission, reconciliation and post-deployment health checks with bounded sampling. Retain **all failures and security-relevant audit events** according to policy; do not depend on sampled traces for legal evidence.

### 3.3 Data quality and missing telemetry

A missing metric is **unknown**, not healthy. Track collector uptime, export queue, dropped spans, scrape coverage, ingestion delay, log source gaps and dashboard freshness. Separate control-plane failures from application/data-plane symptoms.

## 4. SLIs, SLOs and error budgets

Define SLI denominator and window precisely. Illustrative objectives (calibrate with measured baseline and business criticality):

| SLI | Illustrative SLO | Measurement |
|---|---|---|
| Safe deployment success | >=99.0% over 30 days | successful approved deployments / eligible attempts |
| Critical drift detection freshness | >=99.5% within 15 min | on-time checks / scheduled checks |
| Policy enforcement availability | >=99.9% | successful policy decisions / requests |
| IaC pipeline p95 | <=20 min | histogram quantile with sufficient samples |
| GitOps reconciliation p95 | <=5 min | controller reconciliation latency |
| DBRE backup restore RTO | <=60 min | **measured** full recovery |
| DBRE RPO | <=15 min | measured recovered-data age |
| Telemetry ingestion freshness | >=99% within 5 min | on-time observed batches / expected batches |

For an availability SLO of 99.9% across 30 days, the approximate time budget is **43.2 minutes** if measured continuously; for request-based SLIs use counts, not time. Burn-rate = observed error fraction / permitted error fraction. Use short/long window multi-window alerts, separate ticket vs page, avoid paging for low-impact planned changes, and route DBRE restore/replication alerts to database responders.

## 5. Dashboards and alerting

**Executive reliability view:** deployments, change failure rate, SLO compliance, error-budget consumption, outstanding critical drift, restore readiness and cost exposure.

**IaC control-plane view:** plan/apply duration, state locks, provider throttling, policy denies, pipeline failures, artifact provenance and OIDC failures.

**Kubernetes/GitOps view:** desired vs observed revisions, OutOfSync count, controller queue, admission denies, RBAC changes, workload readiness and storage.

**DBRE view:** PostgreSQL WAL/replication and PITR; MongoDB elections/oplog/cache; Redis memory/evictions/failover; Kafka ISR/lag; OpenSearch/Elasticsearch shard health, threadpool rejects, IOPS and query latency; Snowflake queue time, credits, CDC reconciliation and grants.

**Audit view:** telemetry source coverage, missing logs, evidence age, exception expiry, policy version drift and retention. Link dashboards to runbooks and incident timelines; do not treat green panels without fresh samples as evidence.

## 6. Prometheus and OpenTelemetry integration

Example PromQL (illustrative metric names, not built-in exporters):

~~~promql
sum(rate(iac_pipeline_runs_total{outcome="failed"}[5m]))
/
clamp_min(sum(rate(iac_pipeline_runs_total[5m])), 0.000001)
~~~

~~~promql
histogram_quantile(
  0.95,
  sum by (le, environment) (rate(iac_pipeline_duration_seconds_bucket[15m]))
)
~~~

~~~promql
max by (environment) (iac_drift_detection_age_seconds) > 900
~~~

Configure OpenTelemetry Collector receivers, processors and exporters with bounded memory, batching, retry/backpressure, TLS, tenant separation and redaction. Use authenticated OTLP exporters and dedicated collector health telemetry. Do not put secrets or sensitive patient/customer data into spans.

## 7. Hands-on labs

### Lab A — Offline observability gate

~~~bash
cd infrastructure-as-code/labs/chapter-091
python3 telemetry_gate.py fixtures/safe.json policy.json
python3 telemetry_gate.py fixtures/unsafe.json policy.json  # expected nonzero
bash run-preflight.sh
~~~

`telemetry_gate.py` checks an exact synthetic environment, required low-cardinality metric families, telemetry freshness, error and SLO thresholds, redaction and claimed DBRE recovery evidence. **Self-declared JSON is not live telemetry.**

### Lab B — SLO and burn-rate calculator

`slo_engine.py` computes request-based availability, error budget and burn rate from numeric counts. Rejects invalid denominators, booleans, negative counts and impossible errors. Compare 5-minute and 1-hour windows against an approved multi-window policy.

### Lab C — Cardinality guard

`cardinality_gate.py` computes the product of allowed label cardinalities and rejects forbidden high-cardinality labels, unexpected metrics, oversized series budgets and invalid dimensions. This is an illustrative preflight, not a live Prometheus TSDB inspection.

### Lab D — Dashboard coverage

`dashboard_gate.py` checks synthetic coverage for pipeline, state, policy, drift, GitOps, DBRE, SLO and audit panels, owner/runbook references and freshness. Does not create Grafana dashboards.

### Lab E — Authorized native staging validation (not executed)

Deploy a pinned OpenTelemetry Collector and Prometheus/Grafana in isolated staging. Instrument CI pipelines and Terraform/OpenTofu wrappers without exposing plan/state secrets. Induce a failed policy test, state-lock contention, GitOps drift and safe test-only DB restore; verify trace correlation, metric cardinality, ingestion delay, alert routing, measured RPO/RTO and audit retention. Roll back the staging changes and obtain SRE/DBRE/security approval.

## 8. Production incident simulations

| # | Scenario | First action |
|---|---|---|
| 1 | Terraform apply latency exceeds deployment SLO | Correlate source revision, plan, target, policy and SLO |
| 2 | Terraform plan reports unexpected destructive action | Correlate source revision, plan, target, policy and SLO |
| 3 | OpenTofu state lock wait spikes | Correlate source revision, plan, target, policy and SLO |
| 4 | State backend read latency degrades | Correlate source revision, plan, target, policy and SLO |
| 5 | Terraform provider API returns 429 | Correlate source revision, plan, target, policy and SLO |
| 6 | Provider authentication expires during apply | Correlate source revision, plan, target, policy and SLO |
| 7 | Pulumi preview disagrees with deployed resources | Correlate source revision, plan, target, policy and SLO |
| 8 | CloudFormation stack update stalls | Correlate source revision, plan, target, policy and SLO |
| 9 | Azure Bicep what-if omits changed property | Correlate source revision, plan, target, policy and SLO |
| 10 | Ansible playbook fails halfway through fleet | Correlate source revision, plan, target, policy and SLO |
| 11 | Terratest ephemeral environment leaks resources | Correlate source revision, plan, target, policy and SLO |
| 12 | Molecule idempotence regression | Correlate source revision, plan, target, policy and SLO |
| 13 | GitHub Actions runner queue saturates | Correlate source revision, plan, target, policy and SLO |
| 14 | GitLab pipeline artifact upload fails | Correlate source revision, plan, target, policy and SLO |
| 15 | OIDC token audience mismatch | Correlate source revision, plan, target, policy and SLO |
| 16 | Policy evaluation latency breaches budget | Correlate source revision, plan, target, policy and SLO |
| 17 | OPA decision logs stop flowing | Check freshness, loss, cardinality and evidence |
| 18 | Sentinel deny rate suddenly drops | Correlate source revision, plan, target, policy and SLO |
| 19 | AWS CloudTrail ingestion lag increases | Correlate source revision, plan, target, policy and SLO |
| 20 | Azure Activity Log export stops | Check freshness, loss, cardinality and evidence |
| 21 | GCP Audit Log sink fails | Check freshness, loss, cardinality and evidence |
| 22 | AWS Config recorder disabled | Correlate source revision, plan, target, policy and SLO |
| 23 | Azure Policy assignment scope changes | Correlate source revision, plan, target, policy and SLO |
| 24 | GCP Org Policy constraint bypass | Correlate source revision, plan, target, policy and SLO |
| 25 | EKS Kubernetes audit logs disabled | Check freshness, loss, cardinality and evidence |
| 26 | AKS workload identity errors surge | Correlate source revision, plan, target, policy and SLO |
| 27 | GKE node pool reconciliation fails | Correlate source revision, plan, target, policy and SLO |
| 28 | Argo CD application stays OutOfSync | Correlate source revision, plan, target, policy and SLO |
| 29 | Flux source controller reconciliation loops | Correlate source revision, plan, target, policy and SLO |
| 30 | Kubernetes admission webhook times out | Correlate source revision, plan, target, policy and SLO |
| 31 | Prometheus metrics endpoint disappears | Check freshness, loss, cardinality and evidence |
| 32 | OpenTelemetry collector memory limit hit | Check freshness, loss, cardinality and evidence |
| 33 | OTLP exporter returns backpressure | Correlate source revision, plan, target, policy and SLO |
| 34 | Metric cardinality explosion from resource IDs | Check freshness, loss, cardinality and evidence |
| 35 | Tracing samples omit failed deployments | Correlate source revision, plan, target, policy and SLO |
| 36 | Dashboard shows stale telemetry as healthy | Check freshness, loss, cardinality and evidence |
| 37 | Alert rule fires during planned maintenance | Correlate source revision, plan, target, policy and SLO |
| 38 | Alert routing sends DBRE incident to wrong team | Correlate source revision, plan, target, policy and SLO |
| 39 | SLO burn-rate alert remains suppressed | Correlate source revision, plan, target, policy and SLO |
| 40 | Drift detection misses unmanaged resources | Correlate source revision, plan, target, policy and SLO |
| 41 | Drift scanner has stale credentials | Correlate source revision, plan, target, policy and SLO |
| 42 | Remediation controller performs repeated rollbacks | Correlate source revision, plan, target, policy and SLO |
| 43 | Auto-remediation attempts database replacement | DBRE validates data-plane impact and recovery |
| 44 | PostgreSQL replication lag exceeds SLO | DBRE validates data-plane impact and recovery |
| 45 | Aurora PITR retention below RPO | DBRE validates data-plane impact and recovery |
| 46 | RDS storage IOPS saturates | DBRE validates data-plane impact and recovery |
| 47 | MongoDB replication majority unavailable | DBRE validates data-plane impact and recovery |
| 48 | MongoDB oplog window shrinks | DBRE validates data-plane impact and recovery |
| 49 | Redis failover increases client errors | DBRE validates data-plane impact and recovery |
| 50 | Redis eviction spikes after configuration drift | DBRE validates data-plane impact and recovery |
| 51 | Kafka/MSK ISR drops below minimum | DBRE validates data-plane impact and recovery |
| 52 | Kafka consumer lag increases after IaC update | DBRE validates data-plane impact and recovery |
| 53 | Elasticsearch search threadpool rejects requests | DBRE validates data-plane impact and recovery |
| 54 | OpenSearch shard allocation stalls | DBRE validates data-plane impact and recovery |
| 55 | Snowflake warehouse queue time increases | DBRE validates data-plane impact and recovery |
| 56 | Snowflake CDC reconciliation diverges | DBRE validates data-plane impact and recovery |
| 57 | Multi-region failover RTO exceeds objective | DBRE validates data-plane impact and recovery |
| 58 | Evidence retention expires prematurely | Check freshness, loss, cardinality and evidence |
| 59 | FinOps budget alarm misses orphan resources | Correlate source revision, plan, target, policy and SLO |
| 60 | Incident timeline has inconsistent timestamps | Correlate source revision, plan, target, policy and SLO |

## 9. Production runbooks

**R1 — IaC deployment latency and failure triage:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

**R2 — Terraform/OpenTofu state and provider telemetry:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

**R3 — Multi-cloud audit and identity telemetry:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

**R4 — OpenTelemetry collector and trace pipeline:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

**R5 — Prometheus cardinality and scrape failures:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

**R6 — SLO burn-rate and paging hygiene:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

**R7 — Kubernetes and GitOps reconciliation:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

**R8 — PostgreSQL/RDS/Aurora recovery and saturation:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

**R9 — MongoDB/Redis/Kafka operational signals:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

**R10 — Elasticsearch/OpenSearch/Snowflake reliability:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

**R11 — Drift, compliance and auto-remediation safety:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

**R12 — Incident evidence, dashboards and final handoff:** Identify service, target, change ID, severity and incident commander; preserve logs, spans, native audit and state; verify telemetry freshness and alert coverage; correlate IaC plan/apply, provider, GitOps and DBRE health; contain unsafe changes; choose approved rollback or recovery; measure SLI, RPO/RTO and error-budget impact; document remediation and independent sign-off.

## 10. Troubleshooting

| Symptom | Investigation | Response |
|---|---|---|
| No traces for failed deploy | sampling, exporter errors, missing span context | preserve logs; fix propagation/export |
| Prometheus OOM | series cardinality and scrape churn | remove unbounded labels, enforce budgets |
| Green dashboard, stale data | last sample timestamp, collector outage | mark UNKNOWN and page telemetry owner |
| Alert fatigue | thresholds, burn windows, route labels | calibrate against SLO and incident history |
| Terraform plan slow | lock, API 429, refresh latency | inspect state/provider spans and quotas |
| GitOps OutOfSync | revision, permissions, controller errors | reconcile approved source |
| DBRE restore SLA fails | KMS, backup age, WAL/oplog, bandwidth | invoke DR and measure real RPO/RTO |
| Sensitive data in telemetry | log fields, spans, exporters | revoke, redact, contain and audit |

## 11. 100-point acceptance

| Domain | Points |
|---|---:|
| Enterprise observability architecture and trust | 15 |
| Metrics/logs/traces/events and correlation | 20 |
| SLIs/SLOs, burn-rate alerts and error budgets | 20 |
| Offline labs, negative tests and cardinality | 20 |
| DBRE recovery and cross-platform dashboards | 15 |
| Incident runbooks, audit and sign-off | 10 |
| **Total** | **100** |

**Pass >=85 with zero critical failures.** Critical: telemetry leakage, stale dashboards falsely marked healthy, missing audit, unapproved destructive remediation, fabricated restore evidence, RPO/RTO failure or uncontrolled series explosion. Production acceptance requires native evidence and independent SRE/DBRE/security sign-off.

**Next:** Chapter 092 — IaC Drift Observability, State Reconciliation, Change Intelligence and Automated Detection.
