# Chapter 093 — IaC Incident Correlation, Root Cause Analysis, Change Failure Detection and Reliability Engineering

**Part 19 — Observability and Drift · Chapter 093/120 · SRE / DevOps / DBRE**

> **Validation boundary:** accompanying Python 3 labs are offline and operate on synthetic, self-declared events. They do not query GitHub/GitLab, Terraform/OpenTofu, cloud audit APIs, Kubernetes, OpenTelemetry backends or databases. Correlation is not proof of causation; production readiness requires native evidence and independent incident review.

## 1. Learning objectives

Build an incident intelligence system connecting infrastructure changes to application and database reliability signals. Learn to collect protected Git revision, pipeline run, reviewed plan digest, target account, resource inventory, deployment outcome, cloud actor, OpenTelemetry trace, Prometheus SLO, drift observation, database health and recovery evidence. Detect change failures, rank plausible hypotheses, preserve a timeline, mitigate safely and write blameless, evidence-backed postmortems.

## 2. Enterprise reference architecture

~~~text
Git / change ticket / CODEOWNERS / artifact provenance
                     |
  Terraform/OpenTofu / Pulumi / CFN / Bicep / Ansible
                     |
  CI/CD events ---- immutable change identity
        |                  |
  provider audit     OTel trace/span context
        |                  |
  AWS/Azure/GCP inventory + K8s/GitOps controllers
        |                  |
        +---- event normalization / UTC ordering ----+
                           |
      SLO/error budget + DBRE telemetry + drift findings
                           |
     temporal correlation + topology + blast radius
                           |
     ranked hypotheses (NOT causal proof)
                           |
  incident commander / DBRE / security triage
                           |
 approved rollback / safe reconciliation / DR restore
                           |
 measured SLO + RPO/RTO + evidence + postmortem
~~~

**Trust boundaries:** telemetry is untrusted until provenance, scope, timestamps, and collector health are checked. Plan/apply identity must be immutable and target-specific. High-impact changes require separate approval. Never auto-rollback a stateful database, PVC, KMS key, IAM boundary, or cross-region failover based only on temporal correlation.

## 3. Detailed theory

### 3.1 Change identity and normalized event schema

Use a stable `change_id` and `run_id`, plus `source_revision`, `artifact_digest`, `target`, `service`, `environment`, `actor_class`, `resource_scope`, `event_type`, `outcome`, `timestamp_utc`, `trace_id`, `evidence_uri`, `policy_version`, and `ticket`. Protect sensitive data; keep high-cardinality resource IDs and trace IDs out of metric labels. Distinguish *event time* from *ingestion time* and track source clock skew.

### 3.2 Correlation versus root cause

A deployment preceding an outage is a **hypothesis**, not proof. Require multiple independent signals: affected dependency/topology, failure onset, provider audit, plan action, observed configuration, rollback or controlled counterfactual, and symptom recovery. Consider unrelated concurrent deploys, capacity changes, traffic shifts, data-plane failures and telemetry gaps. Record confidence, contradictory evidence, alternative hypotheses, and the evidence needed to confirm or reject each one.

### 3.3 Change failure detection

Change failure rate = production changes causing rollback, incident or hotfix / eligible production changes in a defined window. Define eligibility and deduplicate repeated pipeline attempts. Monitor deployment success, time to restore service, p95 plan/apply latency, drift age, error-budget burn, GitOps reconciliation and DBRE replication/restore readiness. Alert on missing evidence and delayed cloud audit, not just observed errors.

### 3.4 Reliability guardrails

Use staged rollout, canary SLO gates, immutable plan promotion, break-glass with expiry, independent approvals and reversible changes. Freeze automated reconciliation during an active critical incident unless incident command explicitly authorizes it. Preserve Terraform state snapshots and cloud audit; do not force-unlock or destroy resources reflexively.

### 3.5 Database and stateful dependency RCA

PostgreSQL/Aurora/RDS: WAL/PITR, lock waits, replication lag, IOPS, KMS, failover and actual RPO/RTO. MongoDB: replica quorum, elections, oplog, restore. Redis: ACL, persistence, eviction, failover. Kafka/MSK: ISR, ACL, consumer lag, broker replacement. Elasticsearch/OpenSearch: snapshots, shards, disk watermarks and query rejection. Snowflake: warehouse queue, grants, CDC task correctness. A green infrastructure deployment does not establish data correctness.

## 4. Practical SLO and incident signals

| Signal | Diagnostic purpose |
|---|---|
| `iac_change_failures_total` | change failure rate by service/tool |
| `iac_change_to_incident_seconds` | time from change to symptom |
| `iac_rollback_duration_seconds` | mitigation time |
| `iac_incident_evidence_gaps` | missing native evidence |
| `iac_provider_api_errors_total` | provider throttling and auth |
| `iac_state_lock_wait_seconds` | backend contention |
| `iac_gitops_reconcile_failures_total` | desired/observed divergence |
| `iac_drift_detection_age_seconds` | stale detection |
| `iac_dbre_restore_duration_seconds` | measured recovery |
| `iac_service_slo_burn_rate` | user-impacting failure |

Instrument CI, provider wrappers and GitOps with OTel spans; propagate correlation IDs without logging secrets. Example PromQL for a *custom* metric, not an exporter default:

~~~promql
sum(rate(iac_change_failures_total[1h]))
/
clamp_min(sum(rate(iac_change_attempts_total[1h])), 0.000001)
~~~

Prefer multi-window SLO alerts with real denominators; an absent metric is UNKNOWN, not zero incidents.

## 5. Hands-on labs

### Lab A — Synthetic event intake and provenance

~~~bash
cd infrastructure-as-code/labs/chapter-093
python3 incident_gate.py fixtures/safe.json policy.json
python3 incident_gate.py fixtures/unsafe.json policy.json  # expected nonzero
bash run-preflight.sh
~~~

The gate enforces exact synthetic target, event freshness, 32 claimed controls, zero unapproved destructive changes, evidence completeness, measured-SLO claims and DBRE RPO/RTO thresholds.

### Lab B — Correlation candidate ranking

`correlate.py` ranks **candidate** changes by service, environment, topology overlap, UTC time window, evidence completeness and incident onset. It deliberately returns hypotheses rather than claiming causation.

### Lab C — Timeline validation

`timeline.py` rejects invalid UTC timestamps, unordered events, duplicate IDs, missing change identifiers and impossible onset sequences. Native clock synchronization remains out of scope.

### Lab D — Change failure rate and error budget

`reliability.py` calculates change failure rate and request-based error budget with strict numeric validation. Avoid mixing pipeline retries and production changes in the denominator.

### Lab E — Authorized staging incident game day (manual, not executed)

1. Provision isolated staging with a protected OIDC identity, unique test lease and bounded budget.
2. Deploy a reversible IaC change; capture immutable plan, Git commit, pipeline and cloud audit events.
3. Inject a controlled non-destructive failure and observe application SLO, OTel trace, cloud audit and GitOps health.
4. Create competing change candidates to validate correlation uncertainty and clock-skew handling.
5. Practice rollback with incident-command approval and verify SLO restoration.
6. Restore an isolated database from a real backup; measure RPO, RTO and consistency.
7. Preserve trusted native evidence and publish a blameless postmortem with owners and due dates.

## 6. Production SRE/DBRE incident simulations

| # | Scenario | First investigation |
|---|---|---|
| 1 | Terraform apply changes a production subnet route | Correlate immutable change, native audit, dependency and SLO |
| 2 | OpenTofu provider update causes unintended replacement | Correlate immutable change, native audit, dependency and SLO |
| 3 | Remote state backend loses locking | Correlate immutable change, native audit, dependency and SLO |
| 4 | Terraform plan is approved for wrong AWS account | Correlate immutable change, native audit, dependency and SLO |
| 5 | Pulumi stack refresh reports deleted resources | Correlate immutable change, native audit, dependency and SLO |
| 6 | CloudFormation rollback gets stuck | Correlate immutable change, native audit, dependency and SLO |
| 7 | Azure Bicep deployment removes NSG rule | Correlate immutable change, native audit, dependency and SLO |
| 8 | GCP IAM policy binding expands permissions | Correlate immutable change, native audit, dependency and SLO |
| 9 | Ansible playbook changes fleet DNS settings | Correlate immutable change, native audit, dependency and SLO |
| 10 | Terratest teardown deletes a shared resource | Correlate immutable change, native audit, dependency and SLO |
| 11 | Molecule test misses privilege escalation | Correlate immutable change, native audit, dependency and SLO |
| 12 | GitLab runner credentials expire mid-deploy | Correlate immutable change, native audit, dependency and SLO |
| 13 | GitHub Actions OIDC subject is too broad | Correlate immutable change, native audit, dependency and SLO |
| 14 | CI artifact digest differs from reviewed plan | Correlate immutable change, native audit, dependency and SLO |
| 15 | Policy bundle changed between plan and apply | Correlate immutable change, native audit, dependency and SLO |
| 16 | OPA admission webhook fails open | Correlate immutable change, native audit, dependency and SLO |
| 17 | Sentinel policy runs in advisory mode | Correlate immutable change, native audit, dependency and SLO |
| 18 | AWS Config recorder stops reporting drift | Correlate immutable change, native audit, dependency and SLO |
| 19 | Azure Activity Log exporter loses access | Correlate immutable change, native audit, dependency and SLO |
| 20 | GCP audit log sink stops delivering | Correlate immutable change, native audit, dependency and SLO |
| 21 | OpenTelemetry traces lack change ID | Check event provenance, freshness and alternate hypotheses |
| 22 | Prometheus cardinality spike obscures incident | Check event provenance, freshness and alternate hypotheses |
| 23 | Alertmanager routes DBRE alerts to wrong team | Check event provenance, freshness and alternate hypotheses |
| 24 | Grafana dashboard shows stale green panels | Check event provenance, freshness and alternate hypotheses |
| 25 | Argo CD sync overwrites emergency fix | Correlate immutable change, native audit, dependency and SLO |
| 26 | Flux reconciliation loops after invalid commit | Correlate immutable change, native audit, dependency and SLO |
| 27 | Kubernetes admission rejects valid rollout | Correlate immutable change, native audit, dependency and SLO |
| 28 | EKS node drain stalls on PodDisruptionBudget | Correlate immutable change, native audit, dependency and SLO |
| 29 | AKS CNI update breaks pod networking | Correlate immutable change, native audit, dependency and SLO |
| 30 | GKE service account permissions regress | Correlate immutable change, native audit, dependency and SLO |
| 31 | PostgreSQL WAL archive fails after IaC change | DBRE validates data-plane evidence and recovery |
| 32 | Aurora failover exceeds RTO | DBRE validates data-plane evidence and recovery |
| 33 | RDS storage IOPS throttles after resizing | DBRE validates data-plane evidence and recovery |
| 34 | MongoDB replica election stalls | DBRE validates data-plane evidence and recovery |
| 35 | MongoDB backup restore has missing oplog entries | DBRE validates data-plane evidence and recovery |
| 36 | Redis ACL rotation disconnects clients | DBRE validates data-plane evidence and recovery |
| 37 | Redis maxmemory eviction policy changes | DBRE validates data-plane evidence and recovery |
| 38 | Kafka ISR falls below minimum | DBRE validates data-plane evidence and recovery |
| 39 | MSK broker replacement increases consumer lag | DBRE validates data-plane evidence and recovery |
| 40 | OpenSearch snapshot repository is inaccessible | DBRE validates data-plane evidence and recovery |
| 41 | Elasticsearch shard relocation saturates disks | DBRE validates data-plane evidence and recovery |
| 42 | Snowflake warehouse queue grows after downsizing | DBRE validates data-plane evidence and recovery |
| 43 | Snowflake CDC task silently stops | DBRE validates data-plane evidence and recovery |
| 44 | Cross-region failover creates dual primaries | Correlate immutable change, native audit, dependency and SLO |
| 45 | KMS key permissions block DR restore | DBRE validates data-plane evidence and recovery |
| 46 | Unmanaged security group allows public database ingress | DBRE validates data-plane evidence and recovery |
| 47 | IAM role trust policy changes outside Git | Correlate immutable change, native audit, dependency and SLO |
| 48 | Drift detector misses resource pagination | Correlate immutable change, native audit, dependency and SLO |
| 49 | Remediation controller retries destructive action | Correlate immutable change, native audit, dependency and SLO |
| 50 | Deployment failure rate increases after provider upgrade | Correlate immutable change, native audit, dependency and SLO |
| 51 | SLO burn rate alert is suppressed | Check event provenance, freshness and alternate hypotheses |
| 52 | Incident timeline uses inconsistent clock offsets | Check event provenance, freshness and alternate hypotheses |
| 53 | Correlation engine joins unrelated changes | Check event provenance, freshness and alternate hypotheses |
| 54 | Causal attribution assumes temporal coincidence | Correlate immutable change, native audit, dependency and SLO |
| 55 | Change ticket links to wrong Git commit | Correlate immutable change, native audit, dependency and SLO |
| 56 | Backup RPO calculated from stale metadata | DBRE validates data-plane evidence and recovery |
| 57 | RTO excludes application readiness | DBRE validates data-plane evidence and recovery |
| 58 | Ephemeral test environment exceeds budget | Correlate immutable change, native audit, dependency and SLO |
| 59 | Evidence signature verification is skipped | Check event provenance, freshness and alternate hypotheses |
| 60 | Post-incident corrective action lacks owner | Correlate immutable change, native audit, dependency and SLO |

## 7. Production runbooks

**R1 — Declare and scope change-linked incident:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

**R2 — Correlate CI, Git, plan and cloud audit:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

**R3 — Terraform/OpenTofu state and rollback safety:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

**R4 — Pulumi/CloudFormation/Bicep and Ansible:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

**R5 — OpenTelemetry, metrics and evidence gaps:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

**R6 — SLO burn rate, alert routing and escalation:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

**R7 — Kubernetes/Argo CD/Flux incident:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

**R8 — AWS/Azure/GCP identity and policy incident:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

**R9 — PostgreSQL/RDS/Aurora recovery:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

**R10 — MongoDB/Redis/Kafka/OpenSearch/Snowflake recovery:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

**R11 — Change failure analysis and safe mitigation:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

**R12 — Postmortem, corrective action and acceptance:** Declare severity, incident commander, owner, impacted services and blast radius. Freeze unsafe automation and preserve immutable plan, Git revision, cloud/K8s audit, trace, SLO and database telemetry. Normalize UTC timestamps; compare multiple candidate changes and alternative causes. Obtain independent approval before rollback, state repair, identity changes or DR. Verify recovered application SLO and, when applicable, actual DBRE RPO/RTO and data integrity. Document confidence, contradictory evidence, corrective actions, audit retention and independent closure.

## 8. Troubleshooting decision table

| Symptom | Possible cause | Response |
|---|---|---|
| Incident has no matching change | missing audit, unknown resource, delayed telemetry | mark UNKNOWN and expand inventory |
| Many matching changes | overlapping deploys and broad correlation window | use topology, audit and symptoms |
| False causal conclusion | temporal coincidence | test alternative hypotheses |
| CI green but service unhealthy | post-deploy checks absent | inspect SLO and DBRE signals |
| Terraform rollback unsafe | stateful replacement, stale state | halt and involve DBRE/state owner |
| Timeline ordering inconsistent | clock skew or ingestion delay | preserve event and ingestion time |
| Missing traces | collector/exporter failure | use independent logs and audit |
| Restore exceeds RTO | KMS, WAL/oplog, dependencies | execute approved DR runbook |

## 9. 100-point assessment

| Domain | Points |
|---|---:|
| Architecture, threat model and event provenance | 15 |
| Multi-tool change correlation and native telemetry | 20 |
| Root-cause hypotheses, alternatives and timeline | 20 |
| Offline labs, negative tests and reliability metrics | 20 |
| DBRE recovery, SLO and incident game day | 15 |
| Runbooks, audit and blameless postmortem | 10 |
| **Total** | **100** |

**Pass >=85 with zero critical failures.** Critical: unsupported causal certainty, unapproved destructive rollback, wrong target, tampered evidence, hidden telemetry gap, failed DBRE restore, or SLO/RPO/RTO breach. Operational acceptance requires executed native integrations, measured recovery and SRE/DBRE/security sign-off.

**Next:** Chapter 094 — IaC SLO Engineering, Error Budgets, Alerting, Incident Response and Automated Reliability Controls.
