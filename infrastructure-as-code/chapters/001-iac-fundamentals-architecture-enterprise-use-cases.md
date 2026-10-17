# Chapter 001 — Infrastructure as Code Fundamentals, Architecture and Enterprise Use Cases

**Track:** Enterprise Infrastructure as Code | **Audience:** DevOps, SRE, DBRE, Platform Engineering | **Difficulty:** Beginner → operational | **Cloud cost:** $0

## Learning outcomes
Explain IaC, declarative vs imperative models, reconciliation, idempotence, desired vs actual state, drift, state, providers, modules, plan/apply lifecycle, approvals, and recovery. Run a safe local lab, test changes, investigate drift, and clean up.

## 1. Why Infrastructure as Code?
Manual console changes are difficult to review, reproduce and audit. IaC expresses infrastructure intent in version-controlled configuration. A reviewed change can be validated, planned, approved, applied, monitored, and rolled back or remediated. IaC is **not** inherently safe: poor state handling, overly broad IAM, concurrent applies, destructive plans, and secrets in state remain serious risks.

**Declarative:** describe desired outcome (Terraform/OpenTofu, CloudFormation, Bicep). **Imperative:** describe steps (shell scripts, procedural automation). Ansible is commonly task-oriented and can converge systems when modules are idempotent. Git is a source of intent; state records managed object bindings; provider APIs operate on real infrastructure.

**Idempotence:** repeated application of the same configuration should converge without unnecessary changes, assuming stable providers and no external changes. **Drift:** actual infrastructure changes outside the reviewed IaC workflow. **Immutable patterns:** replace instances or images rather than mutating long-lived hosts. **Reconciliation:** compare desired and observed conditions and take corrective actions.

## 2. Architecture and lifecycle

```text
Engineer -> Git branch -> Pull request -> CI checks
                                 | fmt / validate / tests / security
                                 v
                           terraform plan
                                 |
                         review + approval
                                 v
                     controlled terraform apply
                                 |
                     cloud/provider APIs
                                 |
               monitoring + drift detection + audit
                                 |
                  incident response / recovery
```

A production deployment separates **code repository**, **remote state backend**, **execution identity**, **policy gates**, and **runtime observability**. Use short-lived federated CI credentials, least privilege, state encryption and locking, environment separation, and human approval for destructive production changes. Do not apply an old saved plan after configuration or environment changes; regenerate and review it.

### Terraform primitives
- `terraform` block: CLI and provider requirements.
- `provider`: API integration (not needed for built-in `terraform_data`).
- `resource`: managed object.
- `data`: reads an existing object.
- `variable`: configurable input with type and validation.
- `locals`: reusable expressions.
- `output`: exposed result.
- **State:** records bindings between configuration and managed objects; treat it as sensitive operational data.
- **Module:** reusable collection of configuration files.

## 3. Prerequisites
Install Terraform CLI 1.5+ (or a compatible current version) and Git. Windows PowerShell, macOS and Linux shells are supported. Confirm `terraform version`. This lab uses only built-in `terraform_data`: no cloud account, provider download, or paid resources.

Create a clean directory `labs/chapter-001` and add the files below. Avoid running these commands in an existing Terraform state directory.

## 4. Executable lab: desired state and change planning

**main.tf**
```hcl
terraform {
  required_version = ">= 1.5.0"
}

variable "environment" {
  description = "Isolated lab environment"
  type        = string
  default     = "lab"
  validation {
    condition     = contains(["lab", "staging", "prod"], var.environment)
    error_message = "environment must be lab, staging, or prod."
  }
}

variable "team" {
  type    = string
  default = "platform-sre"
}

locals {
  metadata = {
    environment = var.environment
    team        = var.team
    managed_by  = "terraform"
  }
}

resource "terraform_data" "inventory" {
  input = local.metadata
}

output "inventory" {
  value = terraform_data.inventory.output
}
```

**terraform.tfvars.example**
```hcl
environment = "lab"
team        = "platform-sre"
```

**.gitignore**
```gitignore
.terraform/
*.tfstate
*.tfstate.*
*.tfplan
crash.log
crash.*.log
*.tfvars
!*.tfvars.example
override.tf
override.tf.json
*_override.tf
*_override.tf.json
```

Keep `.terraform.lock.hcl` under version control when provider dependencies are introduced. Never commit credentials, secret tfvars, saved plans, or state snapshots.

### Lab A — initialize and deploy
```bash
terraform init
terraform fmt -check
terraform validate
terraform plan -out=chapter001.tfplan
terraform show chapter001.tfplan
terraform apply chapter001.tfplan
terraform output -json
terraform state list
```
**Expected:** one `terraform_data.inventory` resource created; `inventory` output includes environment `lab`, team `platform-sre`, managed_by `terraform`. The exact formatting varies by CLI version.

### Lab B — idempotence
```bash
terraform plan -detailed-exitcode
```
Expected exit code **0** for no changes. Exit code **2** means changes are proposed; **1** means error. In PowerShell, inspect `$LASTEXITCODE`; in bash, `echo $?` immediately after the command.

### Lab C — controlled change
```bash
terraform plan -var='team=database-reliability' -out=team-change.tfplan
terraform show team-change.tfplan
terraform apply team-change.tfplan
terraform output
```
The input update may replace the internal `terraform_data` value in-place. Review actual plan output rather than assuming action type. Run `terraform plan -var='team=database-reliability'` again; expect no changes.

### Lab D — validation failure
```bash
terraform plan -var='environment=production'
```
Expected: input validation error. The accepted value is `prod`, not `production`. Do not apply.

### Lab E — inspect state safely
```bash
terraform state list
terraform state show terraform_data.inventory
```
Never edit `terraform.tfstate` manually. For a real incident, back up state securely and use documented state operations only after review. The state may contain secrets even if outputs are marked sensitive.

### Lab F — cleanup
```bash
terraform destroy -var='team=database-reliability'
terraform state list
```
Expected: resource destroyed and no managed resources listed. Review the destroy plan before approval. The local state file may remain and should be protected or removed according to lab retention policy.

## 5. Validation and acceptance tests

| Test | Command | Pass criteria |
|---|---|---|
| Formatting | `terraform fmt -check` | exit 0 |
| Configuration | `terraform validate` | success |
| Initial plan | `terraform plan` | one new resource |
| Applied inventory | `terraform output -json` | expected metadata |
| Idempotence | `terraform plan -detailed-exitcode` | exit 0 |
| Input guard | `terraform plan -var='environment=production'` | nonzero with validation message |
| Cleanup | `terraform state list` | no resources after destroy |

**Acceptance:** record CLI version, sanitized plan summary, test results, resource count, cleanup confirmation. Never paste secret-bearing state or plans into tickets.

## 6. SRE/DBRE production scenarios

**Scenario 1 — Console drift:** An engineer manually changes an RDS instance class. Freeze conflicting changes, inspect plan and cloud audit logs, determine whether desired code or runtime should win, review service impact, and reconcile via an approved PR. Do not blindly apply a plan that may resize or replace a database.

**Scenario 2 — Lost or locked state:** A pipeline exits mid-apply. Check whether a different run is active and confirm backend health. Never force-unlock without proving the original operation is gone; coordinate with incident commander. Restore from versioned backend backups only after checking actual infrastructure and state lineage.

**Scenario 3 — Destructive plan:** A networking module change proposes replacement of a production subnet. Stop the pipeline, inspect dependency graph, state address moves, provider schema and lifecycle, then redesign/migrate. Approval is not a substitute for safe design.

**Scenario 4 — Secret exposure:** A password appears in state or CI logs. Restrict access, revoke and rotate the credential, assess audit logs, and follow incident response. Marking a value `sensitive` hides some CLI output but does **not** remove it from state.

**Scenario 5 — CI identity failure:** Terraform receives 403/AccessDenied. Check workload identity federation trust, role scope, expiration, provider region/project/account, and policy denies. Do not solve by granting administrator access.

**Scenario 6 — Provider/API throttling:** Concurrent large applies trigger rate limits. Reduce concurrency, segment state, add retry/backoff where supported, inspect quotas and provider errors, and verify partial changes before re-running.

## 7. Troubleshooting quick reference

| Symptom | Investigation | Safe response |
|---|---|---|
| `terraform: command not found` | PATH and installation | Install supported CLI, reopen terminal |
| `terraform init` fails | Network/proxy, backend config | Verify connectivity and backend credentials |
| Invalid variable | Type/validation message | Use `lab`, `staging` or `prod` |
| Plan exit 2 | Proposed changes | Review diff; not a failure by itself |
| Unexpected replacement | Plan actions, dependency graph | Stop; evaluate migration/data loss |
| State lock | Backend lease and active jobs | Wait or coordinate recovery |
| Drift | Cloud audit events vs plan | Decide intent, approve reconciliation |
| Destroy blocked | Dependencies and policy | Review ownership; do not force-delete |

## 8. Operational runbooks

**Change runbook:** ticket → scope and risk → PR review → `fmt`/`validate`/security checks → immutable plan artifact → independent approval → apply same reviewed plan in controlled window → service smoke tests → audit evidence.

**Failure runbook:** halt concurrent applies → preserve sanitized logs and plan metadata → assess partial resources and state → recover backend access → generate fresh plan → approve repair → validate application SLOs → write incident follow-up.

**Drift runbook:** scheduled read-only plan → triage actionable changes → classify approved emergency vs unauthorized changes → update code or revert drift via reviewed workflow → retain audit trail.

**Rollback note:** Terraform has no universal `undo`. Revert the configuration in Git, generate and review a new plan, and apply only after understanding whether resources/data will be destroyed. Database rollback often requires independent backups and tested restore procedures.

## 9. Security and cost controls
Use remote state with encryption, versioning, least-privilege access and locking; isolate prod state and identities; avoid storing secrets in configuration; use a secret manager and assume state remains sensitive; add policy-as-code and static analysis; require approvals for delete/replace; use tagging and budget alerts; routinely detect orphan resources. The introductory `terraform_data` lab incurs no cloud charges.

## 10. Knowledge check
1. Why is Git not a replacement for Terraform state?
2. What does plan exit code 2 mean?
3. Why must a production database replacement be reviewed?
4. How can `sensitive = true` still leave a secret exposed?
5. Why is force-unlock dangerous?
6. What evidence should accompany an IaC production change?

## 11. Next chapter
**Chapter 002 — IaC Tooling Landscape: Terraform, OpenTofu, Ansible, Pulumi, CloudFormation and Bicep.** Compare selection criteria, licensing, workflows, and operational tradeoffs.
