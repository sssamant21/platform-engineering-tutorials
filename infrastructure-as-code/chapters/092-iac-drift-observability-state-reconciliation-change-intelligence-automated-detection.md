# Chapter 092 — IaC Drift Observability, State Reconciliation, Change Intelligence and Automated Detection

**Part 19 — Observability and Drift · Chapter 092/120 · SRE / DevOps / DBRE**

> **Scope:** production-grade architecture and procedures plus an offline Python lab. The lab evaluates **synthetic snapshots and self-declared observations**, not actual Terraform state, cloud inventory, Kubernetes, GitOps, or database telemetry. Native validation, cloud authorization, restore testing and independent operational acceptance are pending.

## 1. Learning outcomes and threat model

Implement reliable drift discovery and reconciliation across Terraform/OpenTofu, Pulumi, CloudFormation, Bicep, Ansible, Kubernetes/GitOps, AWS/Azure/GCP, and stateful data services. Distinguish intentional emergency change, benign provider normalization, unauthorized mutation, stale inventory, IaC state corruption, policy drift, and data-plane degradation. Detect changes **without granting the detector mutation rights**. Preserve source revision, state serial, observation timestamp, inventory scope, policy version, owner, ticket and evidence integrity.

Threats include compromised cloud identity, forged self-reported compliance, partial API pagination, provider refresh errors, race conditions, eventual consistency, state lock contention, reconciliation loops, unsafe database replacement, and attackers disabling telemetry.

## 2. Enterprise architecture

~~~text
Git desired state + immutable revision + change approval
             |             |
       IaC state       policy baseline
             |             |
 Terraform/OpenTofu plan -refresh-only + plan
 Pulumi preview / CloudFormation drift / Bicep what-if
             |
   read-only AWS Config / Azure Resource Graph /
   GCP Cloud Asset Inventory / Kubernetes API / GitOps
             |
    snapshot completeness + freshness + provenance
             |
 normalize -> compare -> classify -> risk -> deduplicate
             |
  change-intelligence correlation:
  ticket / actor / time / provider / audit / deployment
             |
 low-risk notify | high-risk quarantine | reviewed PR
             |
   controlled reconciliation + canary + rollback
             |
  SLO + DBRE RPO/RTO + zero orphan + audit closure
~~~

Separate **desired state** (reviewed Git), **managed state** (IaC backend), **actual state** (read-only provider inventory), **effective policy** (enforced controls) and **runtime health** (metrics/logs/traces). Two-way comparisons are insufficient: a clean Terraform plan can coexist with unmanaged cloud resources or policy controls applied outside IaC.

## 3. Drift taxonomy and reconciliation semantics

| Drift type | Example | Preferred response |
|---|---|---|
| Configuration | manual instance resize | inspect ticket, diff and performance |
| State | stale or incorrectly imported resource | backup state, refresh and review |
| Identity | IAM wildcard or changed OIDC trust | quarantine, revoke exposure |
| Policy | OPA/Sentinel/cloud deny becomes advisory | block deployment, verify enforcement |
| GitOps | Argo CD/Flux observed revision differs | validate source and controller ownership |
| Database | parameter/backup/replication divergence | DBRE review, backup and measured restore |
| Security | public ingress, encryption disabled | incident response and bounded rollback |
| Cost | orphan resource or unapproved capacity | validate owner and impact before cleanup |
| Evidence | stale audit or broken integrity chain | treat state as UNKNOWN, recollect |
| Unknown | incomplete inventory/provider failure | fail closed; never auto-remediate |

**Detection is not authorization.** A finding alone must not trigger `terraform apply`, `destroy`, state manipulation, cluster recreation or data deletion. Emergency change can be legitimate; record owner, ticket, expiration, compensating controls and a planned merge-back to source of truth.

## 4. Native detection patterns

### Terraform/OpenTofu

~~~bash
terraform fmt -check -recursive
terraform validate
terraform plan -refresh-only -out=refresh.tfplan
terraform show -json refresh.tfplan > refresh.json
terraform plan -out=review.tfplan
terraform show -json review.tfplan > review.json
# Do not apply either plan without independent review.
~~~

For OpenTofu, use corresponding `tofu` commands. Protect backend versions and state snapshots. Refresh-only shows remote-to-state differences; normal plan evaluates configuration-to-remote actions. Validate `resource_changes[].change.actions` for `delete`/`replace`, but account for provider limitations and unknown values. Never interpret plan exit code alone as a complete cloud inventory.

### Pulumi, CloudFormation, Bicep

~~~bash
pulumi preview --diff
aws cloudformation detect-stack-drift --stack-name example-stack
az deployment group what-if --resource-group example-rg --template-file main.bicep
~~~

These commands require authenticated, authorized **non-production** environments and may have incomplete resource coverage. Review cloud-native inventory and audit independently; CloudFormation drift detection is asynchronous and requires status polling. For GCP, use Cloud Asset Inventory exports and organization-policy evaluation. For AWS, compare AWS Config/CloudTrail and resource-specific APIs; for Azure, Resource Graph, Policy and Activity Logs.

### Kubernetes and GitOps

~~~bash
kubectl diff -f ./manifests/
kubectl get events -A --sort-by=.lastTimestamp
argocd app diff example-app
flux get kustomizations -A
~~~

Use read-only permissions where possible; avoid changing live objects to "test" drift. Validate GitOps ownership, resource exclusions, admission and RBAC. A controller reconciling to an **unsafe desired state** is not success.

## 5. Change intelligence and risk model

Join findings to Git commits, pipeline runs, cloud audit actors, change tickets, service owner, time window, exception status, policy decisions, topology and business impact. Record **detection latency** (change time to first observation), **classification latency**, **time to safe resolution**, false-positive rate, coverage and evidence freshness. A change without a matching ticket is not automatically malicious, but it must not be silently approved.

Recommended risk dimensions: production scope, public exposure, regulated data, destructive plan, privileged identity, database/DR dependency, missing backup, missing telemetry, stale inventory and blast radius. Missing fields yield **UNKNOWN/quarantine**. Do not auto-reconcile critical, destructive, database, identity, policy or unknown findings.

## 6. Observability and SLOs

| Signal | Purpose |
|---|---|
| `iac_drift_scan_total{outcome}` | scanner health and errors |
| `iac_drift_findings{severity,environment}` | outstanding risk |
| `iac_drift_detection_latency_seconds` | time to discover change |
| `iac_drift_snapshot_age_seconds` | stale observation |
| `iac_drift_inventory_coverage_ratio` | completeness |
| `iac_drift_reconciliation_total{outcome}` | rollback/closure quality |
| `iac_drift_auto_remediation_block_total{reason}` | safety breaker |
| `iac_drift_audit_evidence_gaps` | missing provenance |
| `iac_dbre_recovery_readiness` | verified backup/restore status |

Illustrative SLOs: critical drift discovered within 15 minutes at least 99.5% of eligible observations; 100% of destructive changes blocked from automatic remediation; >=99% inventory completeness for declared scope; zero unowned orphan resources after test cleanup; DBRE RPO <=15 min and RTO <=60 min **only after real recovery drill**. Alert on **no scan data** and partial inventory, not merely on nonzero drift counts. Keep resource IDs in logs/traces rather than metric labels.

## 7. Executable hands-on labs

### Lab A — Synthetic drift observation gate

~~~bash
cd infrastructure-as-code/labs/chapter-092
python3 drift_gate.py fixtures/safe.json policy.json
python3 drift_gate.py fixtures/unsafe.json policy.json # expected rejection
bash run-preflight.sh
~~~

The gate enforces exact lab target, freshness, coverage, critical findings, destructive action count, missing evidence and claimed recovery thresholds. It validates declared JSON, **not native observations**.

### Lab B — Three-way snapshot comparison

`snapshot_diff.py` compares synthetic desired/managed/actual dictionaries with strict key/value typing. Flags unmanaged, state-only, remote-only and desired-versus-actual changes, rather than declaring a clean plan proof of a clean cloud.

### Lab C — Change-intelligence correlation

`change_intel.py` checks synthetic findings for approved ticket, matching immutable commit, authorized actor, bounded time skew and policy version. Missing or mismatched evidence is untrusted.

### Lab D — Risk-based remediation decision

`remediation_gate.py` rejects automatic remediation of production, database, destructive, identity, policy, high/critical, stale or unknown findings. Only explicitly allowlisted, reviewed, low-risk non-production configuration findings are eligible for a **simulated** proposal, never an apply.

### Lab E — Native staging drift game day (manual, not executed)

1. Establish a disposable account, read-only scanner identity, unique lease, state backend and cloud inventory scope.
2. Deploy a benign tagged test resource from protected Git; capture signed source, plan and audit records.
3. Make an approved, reversible tag change directly in the provider and measure detection latency and inventory coverage.
4. Simulate missing pagination, expired credentials and stale snapshots; verify UNKNOWN/quarantine, not false-green dashboards.
5. Generate a reviewed reconciliation PR, validate no destructive plan, apply only after separate authorization and confirm runtime SLO.
6. Exercise a DBRE **non-destructive** parameter change in a disposable database, verify backup and recovery readiness, and measure real RPO/RTO in a dedicated DR drill.
7. Verify no orphan resources, archive trusted native evidence and obtain SRE/DBRE/security sign-off.

## 8. Sixty production incident scenarios

| # | Scenario | Immediate containment |
|---|---|---|
| 1 | Terraform detects an unapproved RDS instance class change | Freeze unsafe database changes; DBRE validates recovery |
| 2 | OpenTofu state references a deleted VPC | Quarantine unsafe reconciliation; verify source, target and actor |
| 3 | AWS console security group opens database ingress | Freeze unsafe database changes; DBRE validates recovery |
| 4 | Azure NSG rule bypasses approved Bicep template | Quarantine unsafe reconciliation; verify source, target and actor |
| 5 | GCP IAM grants project-wide owner access | Quarantine unsafe reconciliation; verify source, target and actor |
| 6 | Pulumi stack output diverges from provider resource | Quarantine unsafe reconciliation; verify source, target and actor |
| 7 | CloudFormation drift scan skips unsupported resource | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 8 | Terraform refresh fails on expired provider credentials | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 9 | Remote state lock remains after crashed runner | Quarantine unsafe reconciliation; verify source, target and actor |
| 10 | State backend object version is rolled back | Quarantine unsafe reconciliation; verify source, target and actor |
| 11 | Terraform import creates incorrect ownership mapping | Quarantine unsafe reconciliation; verify source, target and actor |
| 12 | Plan reports replacement of PostgreSQL storage | Freeze unsafe database changes; DBRE validates recovery |
| 13 | GitOps controller reverts approved emergency patch | Quarantine unsafe reconciliation; verify source, target and actor |
| 14 | Argo CD ApplicationSet targets wrong cluster | Quarantine unsafe reconciliation; verify source, target and actor |
| 15 | Flux source digest changes without code review | Quarantine unsafe reconciliation; verify source, target and actor |
| 16 | Kubernetes ConfigMap modified by an operator | Quarantine unsafe reconciliation; verify source, target and actor |
| 17 | Admission policy changes from enforce to audit | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 18 | Kubernetes Secret rotated outside managed workflow | Quarantine unsafe reconciliation; verify source, target and actor |
| 19 | AWS Config recorder stops sending events | Quarantine unsafe reconciliation; verify source, target and actor |
| 20 | Azure Policy compliance data becomes stale | Quarantine unsafe reconciliation; verify source, target and actor |
| 21 | GCP Cloud Asset Inventory export delayed | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 22 | CloudTrail logging disabled by IAM change | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 23 | Azure Activity Log diagnostic sink removed | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 24 | GCP Audit Logs sink excluded for critical service | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 25 | OIDC federation trust expands to all branches | Quarantine unsafe reconciliation; verify source, target and actor |
| 26 | IAM role permission boundary removed | Quarantine unsafe reconciliation; verify source, target and actor |
| 27 | Policy exception expires but scanner accepts it | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 28 | OPA policy bundle hash changes without approval | Quarantine unsafe reconciliation; verify source, target and actor |
| 29 | Sentinel enforcement level downgraded | Quarantine unsafe reconciliation; verify source, target and actor |
| 30 | Drift scan misses resources due to pagination | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 31 | Cloud API throttling produces partial inventory | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 32 | Resource tags lose ownership and TTL metadata | Quarantine unsafe reconciliation; verify source, target and actor |
| 33 | Terratest environment leaks a load balancer | Quarantine unsafe reconciliation; verify source, target and actor |
| 34 | Molecule run modifies shared staging host | Quarantine unsafe reconciliation; verify source, target and actor |
| 35 | Unmanaged S3 bucket appears in production account | Quarantine unsafe reconciliation; verify source, target and actor |
| 36 | Unmanaged Azure Key Vault key is created | Quarantine unsafe reconciliation; verify source, target and actor |
| 37 | GCP KMS policy changes outside Git | Quarantine unsafe reconciliation; verify source, target and actor |
| 38 | EKS node group scaled outside Terraform | Quarantine unsafe reconciliation; verify source, target and actor |
| 39 | AKS upgrade initiated outside change window | Quarantine unsafe reconciliation; verify source, target and actor |
| 40 | GKE workload identity binding changes | Quarantine unsafe reconciliation; verify source, target and actor |
| 41 | PostgreSQL parameter group drifts to unsafe setting | Freeze unsafe database changes; DBRE validates recovery |
| 42 | Aurora PITR retention falls below RPO | Freeze unsafe database changes; DBRE validates recovery |
| 43 | MongoDB replica set membership changed manually | Freeze unsafe database changes; DBRE validates recovery |
| 44 | MongoDB TLS disabled by emergency configuration | Freeze unsafe database changes; DBRE validates recovery |
| 45 | Redis maxmemory policy changes unexpectedly | Freeze unsafe database changes; DBRE validates recovery |
| 46 | Redis ACL grants wildcard access | Freeze unsafe database changes; DBRE validates recovery |
| 47 | Kafka broker min.insync.replicas reduced | Freeze unsafe database changes; DBRE validates recovery |
| 48 | MSK client authentication changes | Freeze unsafe database changes; DBRE validates recovery |
| 49 | Elasticsearch index template replica count drops | Freeze unsafe database changes; DBRE validates recovery |
| 50 | OpenSearch snapshot lifecycle policy disabled | Freeze unsafe database changes; DBRE validates recovery |
| 51 | Snowflake warehouse size changed without approval | Freeze unsafe database changes; DBRE validates recovery |
| 52 | Snowflake masking policy detached | Freeze unsafe database changes; DBRE validates recovery |
| 53 | Cross-region failover routing points to stale primary | Quarantine unsafe reconciliation; verify source, target and actor |
| 54 | DR backup KMS key deleted outside IaC | Freeze unsafe database changes; DBRE validates recovery |
| 55 | Cloud cost rises after autoscaling drift | Quarantine unsafe reconciliation; verify source, target and actor |
| 56 | Telemetry collector fails to emit drift evidence | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 57 | Drift alert route silently points to wrong on-call | Quarantine unsafe reconciliation; verify source, target and actor |
| 58 | Automatic reconciliation tries to destroy a PVC | Quarantine unsafe reconciliation; verify source, target and actor |
| 59 | Evidence hash mismatch after collection | Mark UNKNOWN, preserve native evidence and restore scan coverage |
| 60 | Change ticket references the wrong artifact digest | Quarantine unsafe reconciliation; verify source, target and actor |

## 9. Twelve production runbooks

**R1 — Detect and scope drift safely:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

**R2 — Terraform/OpenTofu state and provider reconciliation:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

**R3 — AWS/Azure/GCP inventory freshness and completeness:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

**R4 — Identity and policy drift containment:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

**R5 — Kubernetes and GitOps ownership reconciliation:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

**R6 — PostgreSQL/RDS/Aurora drift and recovery:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

**R7 — MongoDB/Redis/Kafka configuration drift:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

**R8 — Elasticsearch/OpenSearch/Snowflake drift:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

**R9 — Change-intelligence and risk scoring:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

**R10 — Auto-remediation circuit breaker and rollback:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

**R11 — Audit provenance, retention and evidence gaps:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

**R12 — Incident acceptance, cleanup and SLO verification:** Confirm incident severity, environment, source revision, ticket, owner and resource blast radius. Freeze unsafe auto-remediation; preserve provider inventory, IaC state/version, GitOps revision, audit logs and timestamps. Validate scan completeness, identity and policy. Compare desired, managed and actual state; distinguish authorized exception from unapproved mutation. Obtain independent approval before any reconcile or rollback. Validate canary, application SLO, database backup and measured RPO/RTO where relevant. Archive evidence, close exception and verify no orphan resources.

## 10. Troubleshooting decision table

| Symptom | Diagnose | Response |
|---|---|---|
| Clean plan but unexpected resource | unmanaged inventory / import gap | compare native cloud inventory |
| Excessive false positives | computed fields / normalization / eventual consistency | bounded retries, explicit exclusions |
| Scanner silent | API 429, permissions, expired identity | UNKNOWN alert; repair read-only access |
| State conflict | lock, serial, backend version | preserve snapshot and coordinate state owner |
| GitOps flapping | two controllers, manual edits, bad desired state | freeze and establish one source of truth |
| Database drift | manual parameter, PITR, KMS, replication | DBRE-led recovery validation |
| Untrusted change ticket | actor/commit mismatch or stale exception | quarantine, independent review |
| Reconcile causes SLO regression | plan impact / missed dependency | halt, rollback and incident review |

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Architecture, ownership and trust boundaries | 15 |
| Three-way drift detection and native provider scope | 20 |
| Change intelligence, classification and evidence | 20 |
| Offline labs, negative tests and remediation safety | 20 |
| DBRE recovery, SLO and incident exercises | 15 |
| Audit retention, runbooks and handoff | 10 |
| **Total** | **100** |

**Pass >=85 with no critical failures.** Automatic fail: destructive auto-apply, false-green stale inventory, wrong account, unverifiable evidence, missed critical policy/identity drift, unapproved database change or failed RPO/RTO. Production acceptance requires native cloud/IaC/GitOps evidence and independent SRE/DBRE/security review.

**Next:** Chapter 093 — IaC Incident Correlation, Root Cause Analysis, Change Failure Detection and Reliability Engineering.
