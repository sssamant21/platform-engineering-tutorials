# Chapter 004 — IaC Lifecycle, Version Control, Git Workflows and Change Management

**Part 01:** Fundamentals and Architecture | **Audience:** DevOps, SRE, DBRE, Cloud and Platform Engineering | **Level:** Intermediate | **Lab cost:** $0

## Learning objectives
Implement a controlled infrastructure delivery lifecycle from issue and Git branch to pull request, validation, plan, approval, apply, service verification, audit, and recovery. Explain plan immutability, change windows, protected branches, separation of duties, state protection, safe rollback, and emergency change processes. Execute local Terraform and Python change-policy labs with automated tests.

## 1. Theory: IaC is a controlled change system
Infrastructure as Code combines source-controlled intent, review, execution identity, state, provider APIs, and operational evidence. A valid configuration is not necessarily a safe configuration: changes can replace stateful resources, break networks, widen IAM, or cause outages. The change process must evaluate **risk and impact**, not only syntax.

### The production lifecycle
1. **Request:** change ticket, owner, business rationale, affected services, risk, rollback/restore plan.
2. **Develop:** short-lived feature branch; one scoped change; update tests and documentation.
3. **Review:** pull request, CODEOWNERS review, security/policy checks, blast-radius assessment.
4. **Validate:** format, syntax, unit/integration tests, secret scanning, static analysis.
5. **Plan:** create an immutable, reviewable plan against the correct workspace/backend and inputs.
6. **Approve:** authorized reviewers validate plan actions, destructive changes, service dependencies and maintenance window.
7. **Apply:** trusted runner, short-lived federated identity, concurrency guard and state lock; apply approved saved plan only if still valid.
8. **Verify:** resource status, connectivity, application SLOs, DB health, telemetry and alerts.
9. **Audit:** retain commit SHA, ticket, approvers, sanitized plan summary, pipeline/job ID and verification.
10. **Recover:** stop further applies, assess partial changes and state, replan a safe fix or execute independent backup/restore procedure.

```text
Ticket -> feature branch -> PR -> fmt/validate/tests/scan
                                  |
                         plan + policy review
                                  |
                       approval / change window
                                  |
                     apply using scoped CI identity
                                  |
                 post-change SLO / DB / network tests
                                  |
                     audit evidence / close ticket
                                  |
                        incident recovery if needed
```

### Git strategies
- **Trunk-based with short-lived branches:** small PRs and fast feedback; often preferable to long-lived environment branches.
- **Environment promotion:** promote a reviewed artifact/configuration through dev, staging, then production with environment-specific variables and independent state.
- **Protected main:** no direct push; require checks and reviews; restrict who can approve production deployments.
- **CODEOWNERS:** require review by infrastructure and service owners where applicable; CODEOWNERS is not itself an approval system without branch protection.
- **Secrets:** never commit credentials, state snapshots or binary plan artifacts. Saved plans may contain sensitive values.

### Plan/apply integrity
A saved Terraform plan is tied to the configuration, variables, provider selection and state snapshot used when created. The plan can become stale if state changes; it must not be treated as a universal rollback artifact. Keep plan and apply in the same trusted execution context where feasible. A production pipeline should check commit SHA, environment, plan age, policy decision and approval. Do not auto-apply unexpected deletions or replacements.

### Rollback vs recovery
Reverting a Git commit changes **desired configuration**; it does not restore deleted data or undo every provider-side effect. Re-plan and review actions. Stateful databases require backups, point-in-time recovery, schema migration strategy and service cutover procedures. Terraform has no general-purpose undo command.

## 2. Repository design
```text
infrastructure-as-code/
  chapters/
  labs/chapter-004/
    main.tf
    change_request.json
    change_policy.py
    test_change_policy.py
    .gitignore
  README.md
  STATUS.md
```
In a larger organization, separate reusable modules from live environment configuration. Keep production state, credentials and approval boundaries separate from development. Use module versions and provider lockfiles. Avoid making one giant state file the single failure domain for all environments.

## 3. Prerequisites
Git, Terraform >=1.5 (or compatible OpenTofu), Python 3.9+, and a scratch directory. No cloud account or network credentials required. Windows PowerShell is supported for Terraform/Python; use Git Bash or PowerShell for Git examples. Check `git --version`, `terraform version`, and `python --version`. Never run this lab against existing production state.

## 4. Lab A — Local Git branch and PR simulation
Use a disposable clone or new local repository; do not change your repository's real main branch during this exercise.
```bash
mkdir iac-ch004-git-lab
cd iac-ch004-git-lab
git init -b main
git config user.name "IaC Lab"
git config user.email "iac-lab@example.invalid"
printf '# IaC change lab\n' > README.md
git add README.md
git commit -m "docs: initialize IaC lab"
git switch -c feat/CHG-004-lab-metadata
printf 'environment=staging\nowner=sre-platform\n' > metadata.txt
git add metadata.txt
git commit -m "feat(iac): add reviewed staging metadata"
git diff main...HEAD
git log --oneline --decorate -3
```
Expected: a feature branch with a scoped commit; `git diff main...HEAD` displays only the proposed metadata change. Open a real PR only in an approved remote test repository. Git alone cannot enforce production approvals; configure branch protection and required checks in the hosting service.

## 5. Lab B — Terraform plan, apply, change review and cleanup
Use the supplied `labs/chapter-004/main.tf`. Work from that directory:
```bash
terraform init
terraform fmt -check
terraform validate
terraform plan -out=change.tfplan
terraform show -no-color change.tfplan
terraform apply change.tfplan
terraform output -json
terraform plan -detailed-exitcode
```
Expected: one `terraform_data.change` resource created and second plan exits 0. `-detailed-exitcode` exit 0 means no changes, 2 means changes, 1 means error.

### Review a staged change
```bash
terraform plan -var='environment=staging' -out=staging.tfplan
terraform show -no-color staging.tfplan
terraform apply staging.tfplan
terraform plan -var='environment=staging' -detailed-exitcode
```
Expected: an update plan, then no changes when reusing the staging input. Capture a **sanitized** plan summary for audit, not full plan files with possible secrets. Plan artifacts should have restricted access and short retention.

### Reject unsafe input
```bash
terraform plan -var='environment=production'
```
Expected: validation failure (the lab permits only lab/staging). Do not apply.

### Cleanup
```bash
terraform destroy -var='environment=staging'
terraform state list
```
Expected: no managed resources. The state file may remain and must not be committed.

## 6. Lab C — Executable change-management policy gate
The included `change_policy.py` checks a JSON change request for ticket, environment, commit SHA, approvals, planned actions, rollback plan, and verification. It blocks production delete/replace actions unless an explicit destructive-change approval exists; this is a teaching example, not a substitute for policy-as-code integrated with real Terraform plan JSON.

```bash
python3 change_policy.py change_request.json
python3 -m unittest -v test_change_policy.py
```
Expected: the supplied staging change is approved and all tests pass. Try changing the environment to `prod` without approval, or adding a `delete` action; expect a nonzero exit and a clear denial. The validator fails closed for unknown actions.

## 7. Lab D — Pull-request quality and audit checklist
In an approved sandbox repository:
1. Create a short-lived branch from current main.
2. Commit Terraform code and tests; avoid `*.tfstate`, `*.tfplan`, `*.tfvars` with secrets.
3. Open PR referencing change ticket, owner, blast radius and verification.
4. Require formatting, validation, unit tests, secret scanning and plan summary checks.
5. Review actual plan actions and confirm no unintended `delete` or `replace`.
6. Approve and merge; production deployment uses environment-specific authorization.
7. Record commit SHA, plan summary, approvals, deployment run and post-change checks.

**Example PR body**
```markdown
## Change
Ticket: CHG-004
Environment: staging
Owner: platform-sre
Scope: update local IaC metadata
Impact: no cloud resources or service downtime
Plan: one managed local metadata resource update
Risk: low
Rollback: revert desired config, generate and review fresh plan
Verification: terraform validate; plan; output; no-change second plan
Approvals: platform reviewer
```

## 8. Production SRE / DBRE use cases
### Case A — RDS/Aurora instance class change
Require maintenance window, workload baseline, backups/PITR verification, failover expectations, connection pool monitoring, and service-owner approval. A plan that replaces the DB is a stop condition pending explicit migration/restore design.

### Case B — EKS node group change
Canary new capacity, verify PodDisruptionBudgets, storage and topology constraints, monitor pending pods and autoscaler behavior, and ensure rollback capacity. A green Terraform apply does not prove application health.

### Case C — Elasticsearch data-node disk upgrade
Assess IOPS, throughput, node evacuation, shard allocation, disk watermarks and search SLOs. Stage a change with observed storage metrics and explicit recovery triggers.

### Case D — IAM policy broadening
Require security review and least-privilege diff; do not merge wildcard actions/resources solely to unblock CI. Prefer OIDC federation and scoped deploy roles.

### Case E — Stale plan during concurrent changes
A second pipeline modifies state after plan generation. Stop applying old plan, regenerate against current state and request renewed approval if diff changes. Use concurrency controls and backend locking.

### Case F — Emergency production hotfix
Use break-glass access with ticket, incident commander, audit trail and time-bound permissions. After stabilization, reconcile emergency drift through a reviewed PR; do not let automated GitOps immediately revert the fix.

## 9. Troubleshooting
| Failure | Investigation | Safe response |
|---|---|---|
| Git push rejected | Protected branch | Open PR and satisfy checks |
| Plan stale | State changed since plan | Regenerate and reapprove |
| State locked | Active job/backend lease | Coordinate; never blindly force-unlock |
| Policy gate denies | Missing approval / destructive action | Update request or redesign; no bypass |
| CI AccessDenied | OIDC trust, role scope, token audience | Repair scoped identity, not admin access |
| Unexpected replace | Provider schema, immutable property, state address | Stop; migration review |
| Apply partially succeeds | Provider/API failure | Inspect actual resources and state; replan |
| Post-apply SLO regression | Application or dependency impact | Incident response; safe restore/cutover |

## 10. Operational runbooks
**Standard change:** record ticket → branch → PR → test/scan → plan → approval → controlled apply → health checks → audit closure.

**Failed deployment:** freeze concurrent applies; preserve sanitized logs; inspect state and real resources; identify partial changes; regenerate plan; choose remediation/restore with owner approval; verify SLOs; record RCA.

**Rollback:** Git revert → new plan → check data-loss/replacement risks → apply if safe; otherwise use tested backup/restore and application cutover.

**Emergency change:** declare incident → scoped temporary access → record manual changes → stabilize → monitor → reconcile code and state → remove break-glass permissions → postmortem.

## 11. Security, cost and compliance controls
Protect remote state with encryption, versioning, locking and least privilege. Use protected branches, CODEOWNERS, two-person approvals for destructive production changes, secret scanning, policy-as-code, cost estimates and tagging. Keep state and plans out of Git and avoid leaking them into CI logs. Use separate identities for plan and apply where feasible, with time-limited credentials.

## 12. Acceptance tests
| Check | Command | Expected |
|---|---|---|
| Git branch | `git branch --show-current` | feature branch |
| Git diff | `git diff main...HEAD` | only scoped change |
| Terraform syntax | `terraform validate` | success |
| Terraform idempotence | `terraform plan -detailed-exitcode` | exit 0 after apply with same inputs |
| Terraform input guard | plan with production | fails |
| Policy happy path | `python3 change_policy.py change_request.json` | approved |
| Policy negative cases | `python3 -m unittest -v test_change_policy.py` | all pass |
| Cleanup | `terraform state list` after destroy | empty |

## 13. Knowledge check
1. Why is `terraform validate` insufficient for production safety?
2. Why should an approved plan be tied to a commit and environment?
3. What is the difference between Git revert and infrastructure rollback?
4. When must an IaC change require a database restore plan?
5. How do CODEOWNERS and branch protection complement each other?
6. What happens if state changes after a saved plan was generated?
7. What evidence should be retained after production deployment?
8. How should emergency console drift be reconciled?

## 14. Completion and next
Publish all labs, tests, troubleshooting and runbooks. Record live execution evidence separately; committing code does not prove it has run. **Next: Chapter 005 — Enterprise IaC Architecture, Operating Models and Governance.**
