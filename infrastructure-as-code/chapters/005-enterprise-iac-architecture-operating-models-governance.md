# Chapter 005 — Enterprise IaC Architecture, Operating Models and Governance

**Part 01 capstone:** IaC Fundamentals and Architecture | **Audience:** SRE, DBRE, DevOps, Security and Platform Engineering | **Level:** Intermediate–Advanced | **Lab cost:** $0

## Objectives
Design an enterprise IaC operating model; establish resource and state ownership, environment boundaries, identities, controls and approvals; evaluate centralized, federated and platform-as-product teams; create a reusable environment inventory; enforce policy in CI; test isolation, blast radius and production governance; and run incident-response drills.

## 1. Enterprise IaC is a socio-technical system
Infrastructure as Code requires more than Terraform modules. The complete system combines architecture, identity, state, Git workflows, review, security policy, CI/CD, operations, audit, ownership and disaster recovery. Success is measured by repeatability, lead time, safe change rate, recoverability and visibility—not number of Terraform files.

### Operating models
| Model | Structure | Benefits | Risks | Good fit |
|---|---|---|---|---|
| Central platform | Platform team owns templates, execution and guardrails | Standardization, shared expertise | Bottleneck and ticket queues | Regulated or early-stage platform |
| Federated | Product teams own stacks within central policies | Autonomy, faster delivery | Inconsistent practices and ownership drift | Mature multi-team organization |
| Hybrid platform-as-product | Platform owns golden paths, backends, identity and policies; service teams own scoped resources | Guardrails with self-service | Needs clear contracts and SLOs | Most growing enterprises |

**Recommended hybrid responsibility contract:** platform team owns backend configuration, CI runners, base networking and security policies; application teams own service-specific stacks within approved boundaries; DBRE owns database availability, backup, recovery and data-impact approval; security owns policy and exception review; incident command owns emergency overrides. Ownership must be explicit per resource.

## 2. Reference architecture
```text
                   Organization Git + change tickets
                  /            |               \
              Modules       Live stacks        Policy code
                  \            |               /
                    PR / CODEOWNERS / CI checks
                         |  plan / scan / tests
                    central policy gate
                         |  approval / risk
               trusted CI identity (OIDC)
                         |
          +--------------+----------------+
          |              |                |
      AWS account    Azure subscription  GCP project
       prod/stage       prod/stage        prod/stage
          |              |                |
     per-stack state / lock / encryption / versioning
                         |
              metrics / audit / drift alerts
                         |
                 SRE on-call / DBRE / DR
```
State and provider access must be separated by account, subscription/project, environment and stack where appropriate. Avoid a single global state containing every environment. Do not reuse prod credentials in staging. Prefer short-lived identity federation, least privilege, policy-as-code, encryption, audit logging and protected state backups.

### Layer boundaries
- **Organization/bootstrap:** identities, backend storage, key management and policy foundations; often separately bootstrapped with special recovery procedures.
- **Landing zone:** accounts/subscriptions/projects, networks, IAM and baseline logging.
- **Shared platform:** Kubernetes clusters, observability, DNS, secrets integrations.
- **Application/service:** load balancers, queues, service databases and scoped permissions.
- **Data plane:** DB provisioning is distinct from schema/data migration and restore; never conflate resource replacement with safe data recovery.

## 3. Governance controls
| Control | Requirement | Evidence |
|---|---|---|
| Ownership | Named team, service, environment, cost center | Inventory and tags |
| Identity | CI OIDC, least privilege, separate prod role | IAM policy and audit |
| State | Encrypted, versioned, locked, backed up | Backend settings and restore drill |
| Git | Protected main, CODEOWNERS, mandatory checks | PR and branch rules |
| Plan | Environment-scoped plan, no unreviewed replacement | Sanitized plan summary |
| Approval | Service owner + DBRE for stateful changes | Change ticket and reviewer record |
| Secrets | Secret manager; no plaintext in Git/state outputs | Scan results and access logs |
| Cost | Tags, budget alerts, lifecycle | Cost allocation reports |
| Reliability | SLO checks, tested rollback/restore, RPO/RTO | Smoke tests and DR evidence |
| Drift | Scheduled read-only scans, triage ownership | Drift incident log |

A compliance exception should have an approver, justification, expiry and compensating controls. An emergency break-glass path must be logged and reconciled after stabilization.

## 4. Repo and state design
```text
iac/
  modules/
    network/
    kubernetes/
    database/
  live/
    aws/dev/network/
    aws/prod/network/
    aws/prod/database/
    azure/staging/platform/
    azure/prod/platform/
  policies/
  pipelines/
  docs/
```
Treat this as a conceptual layout; different organizations may use separate repositories for modules and live stacks. Backend key naming example: `iac/aws/prod/network/terraform.tfstate`. State backend encryption, versioning and locking are cloud/provider-specific; validate implementation and recovery rather than assuming defaults. Do not commit `terraform.tfstate`, `*.tfplan` or secrets.

## 5. Prerequisites
Python 3.9+, Terraform >=1.5 (or compatible OpenTofu), Git. No cloud credentials. Work only inside `labs/chapter-005`. The sample governance policy is intentionally simple and must not be mistaken for a production-grade OPA/Sentinel policy engine.

## 6. Lab A — Terraform environment identity and governance metadata
Use supplied `main.tf`. Commands:
```bash
terraform init
terraform fmt -check
terraform validate
terraform plan -out=lab.tfplan
terraform show -no-color lab.tfplan
terraform apply lab.tfplan
terraform output -json
terraform plan -detailed-exitcode
```
Expected: one local `terraform_data.governance` resource with `environment=lab`, `owner=platform-sre`, `cost_center=training`. The second plan exits 0. For a simulated promotion:
```bash
terraform plan -var='environment=staging' -out=staging.tfplan
terraform show staging.tfplan
terraform apply staging.tfplan
terraform plan -var='environment=staging' -detailed-exitcode
```
Expect an update then no changes. Production input is intentionally blocked:
```bash
terraform plan -var='environment=prod'
```
Expected validation error. Cleanup: `terraform destroy -var='environment=staging'`, then `terraform state list` (empty). Never mix this lab with production state.

## 7. Lab B — Governance inventory policy
The included `environments.json` is a fictional inventory with AWS and Azure stacks. Run:
```bash
python3 governance.py environments.json
python3 -m unittest -v test_governance.py
```
Expected: `PASS` and all tests pass. The policy checks required fields, allowed environments, owner, cost center, non-overlapping backend keys, production approval, state encryption/locking/versioning and prohibited auto-apply. It fails closed on missing controls.

**Negative drill:** copy the JSON inventory, change the production stack's `state.encrypted` to `false`, run the validator on the copy; expected nonzero exit and a denial. Repeat with a duplicate state key and with `auto_apply=true` in prod. Restore the original file.

## 8. Lab C — Architecture and responsibility review
Create a written decision record for an EKS + RDS application spanning staging/prod:
1. List cloud account, environment, network, cluster, DB and IAM resource owners.
2. Draw state boundaries; do not put prod DB and staging Kubernetes in one state.
3. Identify who may approve a DB replacement, and which evidence is required.
4. Specify workload identity, state backup and restore test frequency.
5. Specify SLO smoke tests, rollback vs restore, change windows and incident escalation.
6. Confirm how emergency console changes are reconciled back into Git.

**Acceptance:** each resource has one authoritative IaC controller, one owning team and one operational escalation path.

## 9. Production SRE / DBRE scenarios
**A — Shared RDS module change:** A module update affects 20 database stacks. Pin versions, stage rollout, generate per-stack plans, detect replacement risks and require DBRE approval. Use canaries; a successful module test does not guarantee safe prod migration.

**B — Elasticsearch disk throughput incident:** A platform-owned storage policy conflicts with a DBRE emergency IOPS upgrade. Preserve incident changes, classify drift, review cost and performance, update desired code and avoid auto-revert during the incident.

**C — Cross-account EKS provisioning:** CI identity can deploy to staging but not prod. Diagnose OIDC trust, role assumption, permissions boundaries and account mapping; never copy prod credentials into a pipeline secret.

**D — Remote state compromise:** State backend access is unexpectedly broadened. Restrict access, preserve audit logs, rotate exposed credentials, restore access boundaries and verify state version integrity. Assume state may contain sensitive data.

**E — Terraform controller conflict:** Helm and Terraform both manage the same Kubernetes resource. Freeze conflicting writers, define ownership, migrate resource state carefully and test reconciliation.

**F — Disaster recovery:** Region outage affects IaC backend and app workloads. Validate independent access to versioned state backups, encryption keys, provider credentials and recovery runbooks. DR success requires data consistency and application tests, not only recreated infrastructure.

**G — FinOps:** Orphaned staging resources are expensive. Reconcile ownership tags and state inventories, validate retention, and decommission through reviewed plans rather than manual deletion.

## 10. Runbooks
### Standard platform onboarding
1. Assign service owner, platform contact and DBRE contact.
2. Allocate environment and account boundaries.
3. Provision isolated backend, keys, access policies and locking.
4. Register approved module versions and mandatory CI checks.
5. Validate plan/approval/deploy workflow in nonprod.
6. Test SLO checks, state restore and incident escalation.
7. Record inventory, cost tags and audit evidence.

### Governance violation
1. Stop unsafe apply and preserve sanitized plan evidence.
2. Determine affected stacks, owners and blast radius.
3. Classify policy failure, exception eligibility and security exposure.
4. Correct code or control; require documented exception with expiry if necessary.
5. Re-run checks, obtain approvals and validate runtime health.

### State/backend recovery
1. Halt writers and confirm no active applies.
2. Validate backend identity, lock and access/audit history.
3. Inspect versioned backups and state lineage; do not manually edit state.
4. Restore only under controlled runbook with independent approval.
5. Refresh/replan against actual resources; confirm no accidental deletes.
6. Verify application health and retain incident evidence.

### Emergency change
Declare incident, use time-limited break-glass access, document manual changes, stabilize and monitor, reconcile through reviewed Git changes, revoke elevated access, and complete RCA/COA.

## 11. Troubleshooting
| Symptom | Cause | Safe response |
|---|---|---|
| Duplicate backend key | Two stacks share state | Block deployment; isolate state before apply |
| Prod auto-apply enabled | Unsafe pipeline setting | Disable; require production approvals |
| Policy validator fails | Missing owner/control | Correct inventory; do not bypass |
| Terraform plan proposes DB replace | Immutable change or state mismatch | Stop; DBRE review, migration/restore design |
| State locked | Active writer or stale lease | Coordinate; no blind force-unlock |
| Cross-account AccessDenied | Trust/role/scope mismatch | Repair least privilege and federation |
| Unexpected drift | Console change/controller conflict | Identify authority, approve remediation |
| SLO regression after apply | Runtime impact | Incident response and safe recovery |

## 12. Tests and acceptance
| Test | Command | Pass condition |
|---|---|---|
| Terraform formatting | `terraform fmt -check` | exit 0 |
| Terraform syntax | `terraform validate` | success |
| Idempotence | `terraform plan -detailed-exitcode` after apply | exit 0 |
| Prod guard | `terraform plan -var='environment=prod'` | fails |
| Governance inventory | `python3 governance.py environments.json` | PASS |
| Governance unit tests | `python3 -m unittest -v test_governance.py` | all pass |
| Cleanup | `terraform state list` after destroy | empty |

## 13. Final Part 01 assessment
1. Explain how state differs from desired state.
2. Draw an architecture separating code, CI, identity, backend, providers and monitoring.
3. Choose an operating model and document ownership boundaries.
4. Describe safe drift remediation during a production incident.
5. Explain why Git revert cannot recover deleted DB data.
6. Specify controls for prod database replacement.
7. Show how state recovery is tested.
8. Explain who approves exceptions and how they expire.

**Completion:** Chapter 005 is the Part 01 capstone. The chapter and labs can be published now; execution evidence remains a separate learner activity.

**Next: Chapter 006 — IaC Workstation Setup, CLI Installation and Toolchain Validation.**
