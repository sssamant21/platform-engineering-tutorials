# Chapter 095 — Enterprise IaC Observability, Drift, SLO and Incident Response Reliability Acceptance Capstone

**Part 19 — Observability and Drift · Chapter 095/120 · Final capstone for Part 19**

> **Evidence boundary:** This chapter provides an enterprise acceptance design, offline executable Python reference labs, and a manual native staging game day. The offline labs use synthetic JSON and cannot certify cloud infrastructure, Prometheus/Alertmanager delivery, Terraform state, GitOps or DBRE restore. Publication is not production acceptance.

## 1. Mission and learning outcomes

Integrate Chapters 091–094 into one auditable SRE/DBRE reliability acceptance system. Demonstrate telemetry provenance, three-way IaC drift detection, change-to-incident correlation, customer-facing SLO/error budgets, alert routing, safe remediation, database RPO/RTO, independent approval, and evidence-backed postmortem closure.

**Nonnegotiable safety:** no automatic destructive apply, state surgery, cross-region promotion, PVC deletion, KMS change, database restore or IAM trust expansion. Unknown, incomplete or stale evidence is **UNKNOWN**, never healthy.

## 2. Enterprise architecture

~~~text
Protected Git + CODEOWNERS + ticket + immutable plan
           |                 |
 CI/CD Terraform/OpenTofu/Pulumi/CFN/Bicep/Ansible
           |                 |
 versioned IaC state      AWS/Azure/GCP inventory/audit
           |                 |
    Kubernetes + Argo CD / Flux + DBRE telemetry
           |                 |
        OTel Collector / Prometheus / logs / traces
                         |
         provenance + completeness + UTC freshness
                         |
   desired / managed / actual drift reconciliation
                         |
    incident correlation + alternative hypotheses
                         |
      SLI / SLO / error-budget / burn-rate rules
                         |
   Alertmanager + on-call + incident command + policy
                         |
  HOLD / QUARANTINE / independently approved mitigation
                         |
   measured SLO + RPO/RTO + data integrity + evidence
                         |
      SRE + DBRE + Security + Change approval
~~~

**Trust boundaries:** Separate deployment identity, read-only observability, audit evidence storage and emergency remediation roles. Prefer short-lived OIDC, least privilege, scoped targets, immutable digests, state backend versioning, TLS and redaction. Require independently observed cloud and data-plane facts; CI green is insufficient.

## 3. Acceptance domains and detailed theory

### 3.1 Telemetry architecture and quality

Collect metrics, logs, traces and audit events with a shared change identity, environment, owner and source revision. Preserve both event time and ingestion time; bound clock skew. Avoid unbounded metric labels (resource IDs, trace IDs, user IDs). Track collector drops, scrape failures, log redaction, retention, alert-route ownership and native provider audit coverage. Missing telemetry is an alertable incident.

### 3.2 Three-way drift and reconciliation

Compare reviewed Git desired configuration, versioned IaC-managed state and independently observed actual inventory. Include unmanaged resources, drift in IAM/policy and stateful dependencies. Use Terraform/OpenTofu `plan -refresh-only` plus reviewed normal plan; Pulumi preview; CloudFormation drift with asynchronous status polling; Azure Bicep what-if; GCP asset inventory; Kubernetes diff and GitOps observed revision. Each tool has coverage limits: a clean plan is not proof of complete inventory.

### 3.3 Change intelligence and incident RCA

Normalize source commit, immutable plan digest, cloud actor, change ticket, dependency topology, affected service, incident onset and SLO change. Rank candidate causes; never infer causation from temporal overlap alone. Seek independent provider audit, observed configuration and rollback/counterfactual evidence, while documenting alternatives and contradictory observations.

### 3.4 SLOs, error budgets and alert delivery

Request availability = eligible good requests / eligible total requests. Allowed bad requests = total * (1 - objective). Budget consumption = bad / allowed bad. Burn rate = observed bad fraction / permitted bad fraction. Use paired short/long windows (illustrative 5m/1h at 14.4x, 30m/6h at 6x for a 30-day 99.9% objective). Enforce minimum traffic and telemetry freshness. Verify real Alertmanager paging and escalation in staging; synthetic alerts do not count.

### 3.5 Stateful DBRE acceptance

For PostgreSQL/RDS/Aurora verify WAL/PITR, replication, KMS, restore consistency and measured application-ready RPO/RTO. For MongoDB verify replica elections, oplog continuity and restore. For Redis verify ACL, persistence, failover and cache recovery. For Kafka/MSK verify ISR, durable acknowledgments and consumer lag. For Elasticsearch/OpenSearch verify snapshot restores and shard health; for Snowflake verify grants, CDC and data correctness. A completed backup job alone is not a successful restore.

### 3.6 Reliability controls and incident command

Automated controllers may classify, alert and propose non-destructive mitigations. Require human authorization for production rollback and high-risk changes. Circuit-break repeated actions; preserve immutable evidence and last-known-good state. Document RACI: incident commander owns coordination; SRE owns service SLO; DBRE owns data safety and recovery; security owns identity/audit risk; change authority owns release approval.

## 4. Native command and operational patterns (manual staging only)

~~~bash
terraform fmt -check -recursive
terraform validate
terraform plan -refresh-only -out=refresh.tfplan
terraform show -json refresh.tfplan > refresh.json
terraform plan -out=review.tfplan
terraform show -json review.tfplan > review.json
# OpenTofu: equivalent tofu commands.
pulumi preview --diff
aws cloudformation detect-stack-drift --stack-name disposable-staging-stack
az deployment group what-if --resource-group disposable-staging-rg --template-file main.bicep
kubectl diff -f ./manifests/
argocd app diff disposable-staging-app
flux get kustomizations -A
~~~

All commands require explicitly authorized environments and correctly configured identities. Do not execute against production as a lab. Protect generated plans/state; plan JSON may contain secrets. Check cloud inventory pagination, clock skew, permission errors and API throttling.

## 5. Executable capstone labs

**Lab A — Acceptance manifest gate:** `acceptance_gate.py` enforces exact synthetic target, 36 declared controls, evidence freshness, no critical/destructive actions, no missing evidence, bounded SLO/error budget and claimed DBRE RPO/RTO. A pass is *only* a fixture validation.

**Lab B — Three-way drift coverage:** `drift_assess.py` detects unmanaged, missing remote, state-only and mismatched synthetic resources. Require complete inventory before claiming zero drift.

**Lab C — SLO and burn-rate arithmetic:** `slo_assess.py` calculates request availability, allowed/remaining error budget and window burn rates with strict numeric checks.

**Lab D — Incident timeline and RCA hypothesis:** `incident_assess.py` validates ordered UTC events, unique evidence IDs and bounded candidate change windows. It returns candidate scores with `causal_proof=false`.

**Lab E — Remediation circuit breaker:** `remediation_assess.py` returns `QUARANTINE`, `HOLD` or `PROPOSAL_ONLY` and never applies infrastructure changes.

~~~bash
cd infrastructure-as-code/labs/chapter-095
python3 acceptance_gate.py fixtures/safe.json policy.json
python3 acceptance_gate.py fixtures/unsafe.json policy.json  # expected rejection
bash run-preflight.sh
~~~

## 6. Production-style staging game day (requires live execution)

1. Create a disposable cloud account/project/resource group, GitOps cluster and isolated database with owner, TTL, budget and cleanup lease.
2. Pin source commit, plan digest, backend state version, IAM/OIDC identity, approved ticket and policy version.
3. Configure OTel collector, Prometheus, Alertmanager, audit sinks and read-only cloud inventory. Validate source freshness, pagination and cardinality.
4. Deploy a reversible IaC change and observe native plan/apply, provider audit, application SLI and database telemetry.
5. Inject benign tag drift, a stale scanner, missing audit records and a competing change candidate. Verify UNKNOWN/quarantine, correct incident correlation and no automatic destructive reconciliation.
6. Inject controlled application error-rate degradation; validate 5m/1h and 30m/6h alert behavior, page delivery, ownership, escalation and change freeze.
7. Execute an approved canary rollback; preserve state and ensure customer SLO recovery.
8. Restore a **disposable** database backup; measure RPO, RTO, data consistency and application readiness. Do not simulate a restore and call it complete.
9. Check provider costs, orphan resources, exception expiry, audit immutability, owner sign-off and cleanup evidence.
10. Submit 100-point assessment with independent SRE/DBRE/security reviewers and residual-risk record.

## 7. Sixty SRE/DBRE incident simulations

| # | Incident | First containment |
|---|---|---|
| 1 | Terraform production plan introduces destructive database replacement | Freeze data-risk changes; DBRE validates restore and consistency |
| 2 | OpenTofu remote state serial rolls backward | Preserve immutable change, inventory and state; block unsafe remediation |
| 3 | Terraform lock remains after interrupted apply | Preserve immutable change, inventory and state; block unsafe remediation |
| 4 | Provider throttling causes partial resource discovery | Preserve immutable change, inventory and state; block unsafe remediation |
| 5 | AWS IAM trust policy expands outside protected Git | Preserve immutable change, inventory and state; block unsafe remediation |
| 6 | Azure Policy assignment changes to audit-only | Mark UNKNOWN, preserve evidence, restore telemetry and escalation |
| 7 | GCP Org Policy exception silently expires | Preserve immutable change, inventory and state; block unsafe remediation |
| 8 | CloudFormation drift detection omits unsupported resource | Freeze data-risk changes; DBRE validates restore and consistency |
| 9 | Bicep what-if flags unsafe storage deletion | Preserve immutable change, inventory and state; block unsafe remediation |
| 10 | Pulumi preview misses manually created resource | Preserve immutable change, inventory and state; block unsafe remediation |
| 11 | Ansible rollout alters TLS on critical hosts | Preserve immutable change, inventory and state; block unsafe remediation |
| 12 | CI OIDC subject admits untrusted branches | Preserve immutable change, inventory and state; block unsafe remediation |
| 13 | Immutable plan digest differs at apply time | Preserve immutable change, inventory and state; block unsafe remediation |
| 14 | GitOps sync overrides approved emergency mitigation | Preserve immutable change, inventory and state; block unsafe remediation |
| 15 | Argo CD reconciles to wrong cluster | Preserve immutable change, inventory and state; block unsafe remediation |
| 16 | Flux source artifact digest changes unexpectedly | Preserve immutable change, inventory and state; block unsafe remediation |
| 17 | Kubernetes admission webhook fails open | Preserve immutable change, inventory and state; block unsafe remediation |
| 18 | EKS pod networking breaks during node replacement | Preserve immutable change, inventory and state; block unsafe remediation |
| 19 | AKS workload identity permission regresses | Preserve immutable change, inventory and state; block unsafe remediation |
| 20 | GKE controller loses cloud API permissions | Preserve immutable change, inventory and state; block unsafe remediation |
| 21 | Prometheus metrics go stale during outage | Mark UNKNOWN, preserve evidence, restore telemetry and escalation |
| 22 | OTel exporter drops spans from deployments | Freeze data-risk changes; DBRE validates restore and consistency |
| 23 | Grafana shows false-green panel after scrape failure | Mark UNKNOWN, preserve evidence, restore telemetry and escalation |
| 24 | Alertmanager critical route is silenced | Mark UNKNOWN, preserve evidence, restore telemetry and escalation |
| 25 | Multi-window burn alert has wrong denominator | Mark UNKNOWN, preserve evidence, restore telemetry and escalation |
| 26 | Change failure rate double-counts retries | Preserve immutable change, inventory and state; block unsafe remediation |
| 27 | SLO budget is exhausted before deployment | Mark UNKNOWN, preserve evidence, restore telemetry and escalation |
| 28 | Canary analysis excludes database query errors | Freeze data-risk changes; DBRE validates restore and consistency |
| 29 | Remediation controller loops on drift | Freeze data-risk changes; DBRE validates restore and consistency |
| 30 | Rollback pipeline targets wrong environment | Preserve immutable change, inventory and state; block unsafe remediation |
| 31 | PostgreSQL WAL archive stalls | Freeze data-risk changes; DBRE validates restore and consistency |
| 32 | Aurora cross-AZ failover exceeds RTO | Freeze data-risk changes; DBRE validates restore and consistency |
| 33 | RDS PITR retention is reduced below policy | Freeze data-risk changes; DBRE validates restore and consistency |
| 34 | MongoDB primary election exceeds SLO | Freeze data-risk changes; DBRE validates restore and consistency |
| 35 | MongoDB oplog gap blocks recovery | Freeze data-risk changes; DBRE validates restore and consistency |
| 36 | Redis ACL change causes authentication errors | Freeze data-risk changes; DBRE validates restore and consistency |
| 37 | Redis eviction spike causes p99 latency breach | Freeze data-risk changes; DBRE validates restore and consistency |
| 38 | Kafka ISR falls below durability threshold | Freeze data-risk changes; DBRE validates restore and consistency |
| 39 | MSK broker rotation causes lag and rebalance storm | Freeze data-risk changes; DBRE validates restore and consistency |
| 40 | Elasticsearch shards breach high disk watermark | Freeze data-risk changes; DBRE validates restore and consistency |
| 41 | OpenSearch snapshot repository loses access | Freeze data-risk changes; DBRE validates restore and consistency |
| 42 | Snowflake warehouse resizing raises queue latency | Freeze data-risk changes; DBRE validates restore and consistency |
| 43 | Snowflake CDC pipeline silently stalls | Freeze data-risk changes; DBRE validates restore and consistency |
| 44 | KMS key rotation prevents database restore | Freeze data-risk changes; DBRE validates restore and consistency |
| 45 | DR cross-region fencing fails | Freeze data-risk changes; DBRE validates restore and consistency |
| 46 | CloudTrail delivery gap hides IAM mutation | Mark UNKNOWN, preserve evidence, restore telemetry and escalation |
| 47 | Azure Activity Log export is delayed | Preserve immutable change, inventory and state; block unsafe remediation |
| 48 | GCP Cloud Asset Inventory is incomplete | Preserve immutable change, inventory and state; block unsafe remediation |
| 49 | Drift scanner ignores paginated inventory | Freeze data-risk changes; DBRE validates restore and consistency |
| 50 | Evidence bundle digest is tampered | Mark UNKNOWN, preserve evidence, restore telemetry and escalation |
| 51 | Clock skew changes incident ordering | Mark UNKNOWN, preserve evidence, restore telemetry and escalation |
| 52 | Correlation model mistakes coincidence for causation | Preserve immutable change, inventory and state; block unsafe remediation |
| 53 | Policy exception lacks owner or expiry | Preserve immutable change, inventory and state; block unsafe remediation |
| 54 | Service owner cannot be paged | Preserve immutable change, inventory and state; block unsafe remediation |
| 55 | Emergency change bypasses independent approval | Preserve immutable change, inventory and state; block unsafe remediation |
| 56 | Ephemeral test cluster leaks expensive resources | Preserve immutable change, inventory and state; block unsafe remediation |
| 57 | Audit retention falls below requirement | Mark UNKNOWN, preserve evidence, restore telemetry and escalation |
| 58 | Recovery reports RPO without data consistency | Freeze data-risk changes; DBRE validates restore and consistency |
| 59 | Production SLO recovers but data corruption remains | Mark UNKNOWN, preserve evidence, restore telemetry and escalation |
| 60 | Postmortem corrective action has no accountable owner | Preserve immutable change, inventory and state; block unsafe remediation |

## 8. Twelve detailed production runbooks

### R01 — Enterprise incident command and change freeze

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

### R02 — Telemetry provenance and missing-signal triage

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

### R03 — SLO, error-budget and multi-window alert response

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

### R04 — Terraform/OpenTofu plan/state safety

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

### R05 — Pulumi/CloudFormation/Bicep/Ansible incident

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

### R06 — Cloud identity, policy and audit integrity

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

### R07 — Kubernetes, Argo CD and Flux reconciliation

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

### R08 — Drift inventory, change intelligence and correlation

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

### R09 — PostgreSQL/Aurora/RDS restore and failover

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

### R10 — MongoDB/Redis/Kafka/MSK data-plane recovery

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

### R11 — Elasticsearch/OpenSearch/Snowflake and cross-region DR

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

### R12 — Evidence attestation, postmortem and final acceptance

**Trigger:** failed acceptance control, alert, drift finding or customer-impacting symptom. **Owner:** incident commander delegates to SRE, DBRE, security and change authority. **Detect:** confirm exact environment, resource, source commit, plan digest, service tier, timestamp and owner; validate independent native signals and coverage. **Contain:** pause unsafe automation, prevent wrong-target apply and preserve backend version, audit events, traces and metrics. **Diagnose:** reconstruct UTC timeline; compare desired, managed and actual state; inspect SLO/error budget, topology, policy and alternative causes. **Recover:** require independent approval before rollback or DR; use staged changes and explicit stop conditions. **Verify:** customer-facing SLO, telemetry freshness, database data correctness and measured RPO/RTO when applicable. **Close:** evidence hashes, residual risk, cleanup, corrective owner, postmortem and independent sign-off.

## 9. Troubleshooting and failure interpretation

| Symptom | Likely issue | Required response |
|---|---|---|
| Green pipeline, failing service | deployment-only success criterion | verify customer SLO and DBRE |
| Zero drift with partial inventory | API pagination or permissions | UNKNOWN, restore coverage |
| Incorrect incident cause | coincident change / skew | competing hypotheses and audit |
| Alert rule works, page absent | routing, inhibition or silence | test real notification |
| SLO budget seems too large | wrong denominator/window | recompute from eligible requests |
| Terraform state conflict | concurrent writer/backend lock | preserve version, coordinate owner |
| Restore appears successful | unverified data/application readiness | measure actual RPO/RTO |
| Reconciliation causes churn | two controllers or bad desired state | freeze and review ownership |
| Evidence digest mismatch | tampering or serialization mismatch | quarantine and recollect |
| Lab fixture passes | synthetic self-report | do not claim native acceptance |

## 10. Final 100-point enterprise reliability acceptance

| Category | Points | Evidence required |
|---|---:|---|
| Enterprise architecture, IAM and provenance | 15 | reviewed design, least privilege, immutable target |
| Native telemetry and complete three-way drift | 20 | fresh OTel/Prometheus, provider inventory and drift |
| Change intelligence and incident RCA | 15 | auditable timeline, alternatives and cause validation |
| SLO, burn-rate alerting and real paging | 20 | correct denominators, windows and delivered page |
| Offline lab tests and remediation safety | 15 | passing tests, negative cases, no destructive action |
| DBRE restore, RPO/RTO and data correctness | 10 | actual isolated restore and measured evidence |
| Audit, cleanup, runbooks and sign-off | 5 | retained evidence, zero orphans, independent review |
| **Total** | **100** | |

**Passing threshold:** >=85/100 **and zero critical failures**. Automatic failure: wrong target, missing/false-green telemetry, critical policy/identity drift, unapproved destructive action, undelivered critical page, unverified data integrity, missed RPO/RTO or forged evidence. A passing offline lab is not a 100-point production pass.

## 11. Completion and handoff

Part 19 content spans **091 telemetry and dashboards, 092 drift, 093 incident RCA, 094 SLO/error budgets, 095 enterprise reliability capstone**. Curriculum publication completes Part 19; live integration, test execution, security review and production acceptance remain independent, pending milestones.

**Next:** Chapter 096 — IaC Cost Observability, Cloud Billing Data, Tagging and FinOps Fundamentals (Part 20 — FinOps).
