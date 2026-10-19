# Chapter 098 — IaC Cost Forecasting, Budget Governance, Anomaly Detection and FinOps Automation

**Part 20 — FinOps · Chapter 098/120 · Enterprise SRE/DBRE**

> **Evidence boundary:** The accompanying executable Python labs are deterministic, offline and synthetic. No provider billing exports, budgets, notification delivery, cloud remediation, IaC apply or database recovery were executed. Offline checks do not establish operational acceptance.

## 1. Outcomes and prerequisites

Building on Chapters 096–097, design an auditable forecast/budget/anomaly system using validated provider billing records, ownership tags and reliability constraints. Distinguish budget **observed spend**, **forecast**, **committed spend**, and **actual invoice**. Implement explainable anomaly review, multi-threshold alert policy, finance approvals and a fail-closed automation gate.

## 2. Enterprise reference architecture

~~~text
Git PR + Terraform/OpenTofu/Pulumi/CFN/Bicep/Ansible
        | owner, environment, application, cost-center tags
AWS CUR/Data Exports | Azure Cost Management | GCP Billing BigQuery
        | immutable raw ledger, credits, usage UTC, ingestion UTC
        v
schema / account / basis / currency / dedup / late data checks
        v
daily cost series + shared allocation + invoice reconciliation
        |                      |
baseline + seasonality    budgets + commitments
        |                      |
forecast + uncertainty    burn-rate + thresholds
        +----------+-----------+
                   v
      anomaly triage / impact and confidence
                   v
      owner route + alert receipt + incident ticket
                   v
    manual SRE/DBRE/Finance approval and safe proposal
                   v
  measured realized savings + SLO/RPO/RTO + audit closure
~~~

**Trust and access:** separate billing reader, policy editor, FinOps reviewer, incident commander, finance approver and IaC deployer. No billing feed or forecast model may have implicit production mutation permission. Protect tenant-specific spend and avoid secrets or personal data in resource tags.

## 3. Billing normalization and forecasting theory

**AWS:** CUR 2.0/Data Exports and AWS Budgets/Cost Anomaly Detection have different refresh and accounting semantics. Check payer/linked account, effective costs, savings plans, reservations, credits, usage period and late-arriving lines.

**Azure:** Cost Management exports and budgets may have differing scope and refresh schedules. Compare actual versus amortized cost consistently; map subscription/resource-group tags to approved ownership.

**GCP:** Cloud Billing export to BigQuery and budgets/alerts are not final invoice settlement. Normalize credits, CUD, project labels, adjustments and effective-dated owner changes.

For daily spend \(x_t\), a simple trailing forecast is \(\hat{x}_{t+1}=\frac{1}{n}\sum_{i=t-n+1}^{t}x_i\). Forecast remaining-month spend as the chosen daily rate multiplied by remaining days. This is a **baseline** rather than a production seasonal forecast. Real systems require weekday/holiday effects, trend, workload growth, product launches, contract pricing, missing days, credits, committed-use discounts and confidence intervals.

A forecast must not fill missing billing days with zero. A late or partial day is **UNKNOWN** until completeness is verified. Train and backtest only on comparable cost basis and stable scope; use rolling holdouts, WAPE/MAE and coverage by service/account, and compare against a naive baseline.

## 4. Budget engineering

- Define budgets by account, environment, cost center, application and shared-platform pool; choose a single declared cost basis.
- Use graduated thresholds (for example 50/80/100 percent), and distinguish actual from forecast breaches.
- Record owner route, acknowledgment, escalation, alert receipt, suppression reason and ticket.
- Budget governance is **not** permission to delete a database, reduce backup retention, shut off production telemetry or violate availability SLO.
- Define SLOs for billing freshness, allocation coverage, anomaly review latency, budget notification delivery and forecast quality; count UNKNOWN as missing evidence, not healthy.

## 5. Anomaly detection and response

Compare observed daily spend to a robust baseline, account for weekday and seasonality, minimum spend floor, statistical variance and a meaningful absolute-dollar threshold. Avoid noisy alerts on tiny denominators. Require a sufficiently long and complete historical window. Correlate candidate anomalies with approved IaC changes, deployment events, capacity changes, billing adjustments and provider incidents. Temporal proximity **is not causation**. Quarantine automation when telemetry is stale, ownership unknown, data incomplete, anomaly confidence low or a DBRE reliability objective is at risk.

## 6. IaC governance patterns

~~~hcl
variable "cost_tags" {
  type = object({
    owner       = string
    cost_center = string
    application = string
    environment = string
    managed_by  = string
  })
  validation {
    condition = alltrue([for value in values(var.cost_tags) : length(trimspace(value)) > 0])
    error_message = "Every required cost ownership tag must be nonempty."
  }
}
~~~

Apply provider-native tagging rules and periodic read-only observed-state checks. CI cost estimates are advisory: review resource count, region, size, data transfer and expected storage; a plan cost estimate is not a bill. For Kubernetes, account for system and idle nodes, shared storage, network, GPU and reservations. For PostgreSQL, MongoDB, Redis, Kafka, Elasticsearch and Snowflake, include replication, snapshots, RPO/RTO, data integrity, IOPS, retention and service-level performance.

## 7. Hands-on lab sequence

**Lab A — Source contract:** `billing_gate.py` rejects wrong account, period, basis, currency, stale exports, duplicate days, negative/invalid amounts and missing owners.

**Lab B — Forecast:** `forecast.py` calculates a deterministic Decimal trailing-average projection and explicitly refuses incomplete daily series or invalid horizons.

**Lab C — Budget:** `budget_gate.py` classifies actual/forecast usage as OK/WATCH/BREACH using explicit policy thresholds; no live notifications.

**Lab D — Anomaly:** `anomaly.py` returns UNKNOWN/OK/REVIEW based on complete data, minimum absolute change and ratio thresholds.

**Lab E — Automation safety:** `automation_gate.py` produces QUARANTINE/HOLD/PROPOSAL_ONLY; no cloud API, budget mutation or destructive action.

~~~bash
cd infrastructure-as-code/labs/chapter-098
python3 billing_gate.py fixtures/safe.json policy.json
python3 billing_gate.py fixtures/unsafe.json policy.json  # expected rejection
bash run-preflight.sh
~~~

**Native staging lab (manual, not executed):** connect read-only authorized AWS/Azure/GCP exports; compare provider console costs to raw source and normalized ledger; verify late billing corrections, simulate forecast threshold crossings, test notification receipt and owner acknowledgment, run non-destructive change proposals, verify SRE/DBRE SLO and finance reconciliation. Obtain independent approval before production rollout.

## 8. Sixty production SRE/DBRE incident scenarios

| # | Scenario | First safe investigation |
|---|---|---|
| 1 | AWS CUR/Data Exports: missing daily export | Verify provider source, currency/basis, completeness and lineage |
| 2 | AWS CUR/Data Exports: budget threshold crossed | Verify provider source, currency/basis, completeness and lineage |
| 3 | Azure Cost Management: late adjustment changes baseline | Verify provider source, currency/basis, completeness and lineage |
| 4 | Azure Cost Management: critical budget page undelivered | Verify provider source, currency/basis, completeness and lineage |
| 5 | GCP Billing BigQuery: duplicate usage lines | Verify provider source, currency/basis, completeness and lineage |
| 6 | GCP Billing BigQuery: anomaly detector false positive | Verify provider source, currency/basis, completeness and lineage |
| 7 | Terraform: amortized versus actual mismatch | Inspect ownership, IaC change, SLO and budget alert evidence |
| 8 | Terraform: anomaly detector false negative | Inspect ownership, IaC change, SLO and budget alert evidence |
| 9 | OpenTofu: credit counted twice | Verify provider source, currency/basis, completeness and lineage |
| 10 | OpenTofu: forecast underestimates storage growth | Inspect ownership, IaC change, SLO and budget alert evidence |
| 11 | Pulumi: wrong billing account | Verify provider source, currency/basis, completeness and lineage |
| 12 | Pulumi: forecast overestimates savings | Inspect ownership, IaC change, SLO and budget alert evidence |
| 13 | CloudFormation: unknown cost center | Inspect ownership, IaC change, SLO and budget alert evidence |
| 14 | CloudFormation: unsafe optimization proposed | Inspect ownership, IaC change, SLO and budget alert evidence |
| 15 | Bicep: ownership tag drift | Inspect ownership, IaC change, SLO and budget alert evidence |
| 16 | Bicep: unapproved automation action | Inspect ownership, IaC change, SLO and budget alert evidence |
| 17 | Ansible: stale forecast window | Inspect ownership, IaC change, SLO and budget alert evidence |
| 18 | Ansible: missing evidence for finance review | Inspect ownership, IaC change, SLO and budget alert evidence |
| 19 | EKS: seasonality ignored | Inspect ownership, IaC change, SLO and budget alert evidence |
| 20 | EKS: currency basis mismatch | Verify provider source, currency/basis, completeness and lineage |
| 21 | AKS: holiday peak overlooked | Inspect ownership, IaC change, SLO and budget alert evidence |
| 22 | AKS: refund treated as spend | Inspect ownership, IaC change, SLO and budget alert evidence |
| 23 | GKE: budget threshold crossed | Inspect ownership, IaC change, SLO and budget alert evidence |
| 24 | GKE: usage units changed | Inspect ownership, IaC change, SLO and budget alert evidence |
| 25 | PostgreSQL: critical budget page undelivered | Preserve durability, capacity and DBRE recovery objectives |
| 26 | PostgreSQL: zero baseline causes division error | Preserve durability, capacity and DBRE recovery objectives |
| 27 | Aurora: anomaly detector false positive | Preserve durability, capacity and DBRE recovery objectives |
| 28 | Aurora: partial billing day mistaken for savings | Preserve durability, capacity and DBRE recovery objectives |
| 29 | RDS: anomaly detector false negative | Preserve durability, capacity and DBRE recovery objectives |
| 30 | RDS: network egress spike | Preserve durability, capacity and DBRE recovery objectives |
| 31 | MongoDB: forecast underestimates storage growth | Preserve durability, capacity and DBRE recovery objectives |
| 32 | MongoDB: capacity reservation idle | Preserve durability, capacity and DBRE recovery objectives |
| 33 | Redis: forecast overestimates savings | Preserve durability, capacity and DBRE recovery objectives |
| 34 | Redis: backup cost growth | Preserve durability, capacity and DBRE recovery objectives |
| 35 | Kafka: unsafe optimization proposed | Preserve durability, capacity and DBRE recovery objectives |
| 36 | Kafka: tenant allocation skew | Preserve durability, capacity and DBRE recovery objectives |
| 37 | MSK: unapproved automation action | Preserve durability, capacity and DBRE recovery objectives |
| 38 | MSK: SLO degraded after cost change | Preserve durability, capacity and DBRE recovery objectives |
| 39 | Elasticsearch: missing evidence for finance review | Preserve durability, capacity and DBRE recovery objectives |
| 40 | Elasticsearch: missing daily export | Preserve durability, capacity and DBRE recovery objectives |
| 41 | OpenSearch: currency basis mismatch | Preserve durability, capacity and DBRE recovery objectives |
| 42 | OpenSearch: late adjustment changes baseline | Preserve durability, capacity and DBRE recovery objectives |
| 43 | Snowflake: refund treated as spend | Preserve durability, capacity and DBRE recovery objectives |
| 44 | Snowflake: duplicate usage lines | Preserve durability, capacity and DBRE recovery objectives |
| 45 | Kubernetes PVC: usage units changed | Inspect ownership, IaC change, SLO and budget alert evidence |
| 46 | Kubernetes PVC: amortized versus actual mismatch | Inspect ownership, IaC change, SLO and budget alert evidence |
| 47 | Cloud NAT: zero baseline causes division error | Inspect ownership, IaC change, SLO and budget alert evidence |
| 48 | Cloud NAT: credit counted twice | Verify provider source, currency/basis, completeness and lineage |
| 49 | Cross-region egress: partial billing day mistaken for savings | Verify provider source, currency/basis, completeness and lineage |
| 50 | Cross-region egress: wrong billing account | Verify provider source, currency/basis, completeness and lineage |
| 51 | OpenTelemetry: network egress spike | Inspect ownership, IaC change, SLO and budget alert evidence |
| 52 | OpenTelemetry: unknown cost center | Inspect ownership, IaC change, SLO and budget alert evidence |
| 53 | Prometheus: capacity reservation idle | Inspect ownership, IaC change, SLO and budget alert evidence |
| 54 | Prometheus: ownership tag drift | Inspect ownership, IaC change, SLO and budget alert evidence |
| 55 | GPU platform: backup cost growth | Inspect ownership, IaC change, SLO and budget alert evidence |
| 56 | GPU platform: stale forecast window | Inspect ownership, IaC change, SLO and budget alert evidence |
| 57 | Reserved Instances: tenant allocation skew | Inspect ownership, IaC change, SLO and budget alert evidence |
| 58 | Reserved Instances: seasonality ignored | Inspect ownership, IaC change, SLO and budget alert evidence |
| 59 | Savings Plans: SLO degraded after cost change | Inspect ownership, IaC change, SLO and budget alert evidence |
| 60 | Savings Plans: holiday peak overlooked | Inspect ownership, IaC change, SLO and budget alert evidence |

## 9. Twelve production runbooks

### R01 — Billing data completeness and freshness

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

### R02 — AWS CUR budgets and anomaly triage

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

### R03 — Azure Cost Management budget and forecast

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

### R04 — GCP Billing BigQuery budgets and anomalies

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

### R05 — Terraform/OpenTofu/Pulumi cost policy in CI

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

### R06 — CloudFormation/Bicep/Ansible cost governance

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

### R07 — Kubernetes EKS/AKS/GKE capacity forecast

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

### R08 — Shared network, NAT, storage and GPU cost anomaly

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

### R09 — PostgreSQL/Aurora/RDS/MongoDB DBRE budget response

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

### R10 — Redis/Kafka/MSK/Elasticsearch/OpenSearch growth

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

### R11 — Snowflake credit burn and warehouse capacity

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

### R12 — FinOps incident command, finance reconciliation and closure

**Trigger:** forecast overrun, unexpected spend, missed budget page, missing billing data or cost-related service degradation. **Owner:** FinOps with service SRE; DBRE joins stateful risks and Finance approves financial decisions. **Detect:** identify exact account, billing period, currency/basis, source export, freshness, cost center and threshold. **Contain:** suspend unsafe optimization; preserve raw records and audit. **Diagnose:** compare actual versus forecast, baseline, seasonality, credits, IaC change, owner, service SLO and RPO/RTO. **Recover:** repair ingestion or propose approved non-destructive optimization, never automatically delete stateful resources. **Verify:** source reconciliation, owner alert receipt, no SLO regression and invoice follow-up. **Close:** incident timeline, finance sign-off, evidence retention and corrective action.

## 10. Troubleshooting guide

| Symptom | Likely cause | Response |
|---|---|---|
| Forecast drops to zero | missing export treated as zero | UNKNOWN, restore source |
| Forecast doubles | duplicate days or mixed cost basis | deduplicate and reconcile |
| Budget alarm missing | wrong route or stale feed | test receipt end-to-end |
| Frequent tiny anomalies | missing dollar floor | tune absolute and relative thresholds |
| Unexpected savings | credit/refund or late adjustment | separate financial adjustments |
| Database latency worsens | unsafe rightsizing | stop automation and restore capacity |
| Cloud total differs from forecast | tax, amortization or seasonality | compare like-for-like and document variance |
| Alert fatigue | poor owner routing and no dedupe | group by scope and incident |

## 11. 100-point final assessment

| Domain | Points |
|---|---:|
| Architecture, provenance, IAM and billing semantics | 15 |
| Forecasting, completeness and backtesting | 20 |
| Budget thresholds, ownership and alert delivery | 20 |
| Offline labs, tests and anomaly logic | 20 |
| Automation safety and SRE/DBRE reliability | 15 |
| Incident runbooks, reconciliation and independent review | 10 |
| **Total** | **100** |

Pass >=85 with no critical failure. Critical: wrong account, invented zero-spend, unsupported currency/basis, false budget receipt, destructive automated cost change, degraded SLO, or DBRE RPO/RTO breach. Native provider, alert and database acceptance remain pending.

## 12. Next

**Chapter 099 — IaC Cost Optimization, Rightsizing, Commitments and Reliability-Aware FinOps Engineering.**
