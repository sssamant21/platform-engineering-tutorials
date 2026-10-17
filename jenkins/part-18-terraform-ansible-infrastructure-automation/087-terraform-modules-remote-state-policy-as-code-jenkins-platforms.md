# Chapter 087 — Terraform Modules, Remote State and Policy-as-Code for Jenkins Platforms

**Part 18 — Terraform, Ansible and Infrastructure Automation**  
**Audience:** SRE/DBRE, DevOps, platform security, cloud infrastructure and change owners  
**Prerequisites:** Chapter 086, Terraform CLI, Python 3, optional OPA CLI, an isolated Git repository and a disposable Terraform workspace.

## Outcomes

Design reusable Jenkins infrastructure modules, separate root configurations and remote state, protect state and secrets, enforce policy before apply, test module contracts, detect drift and safely promote changes.

## 1. Reference architecture

```text
Git PR → fmt/validate/test → policy check → reviewed plan
                         |
                   approved apply
                         |
              Terraform root per environment
                         |
          versioned modules: network, compute,
              storage, IAM, Jenkins platform
                         |
              remote encrypted locked state
                         |
             Ansible + JCasC + Jenkins smoke
                         |
              drift, cost, audit, rollback
```

A module is a reusable configuration interface, not an isolation boundary. A root module is an independently applied deployment unit. Keep production, staging and DR states separate and enforce their permissions independently.

## 2. Recommended repository structure

```text
jenkins-iac/
  modules/
    jenkins-platform/
      versions.tf
      variables.tf
      main.tf
      outputs.tf
      tests/contract.tftest.hcl
  environments/
    staging/main.tf
    prod/main.tf
    dr/main.tf
  policy/
    jenkins.rego
    plan-example.json
  scripts/
    check_plan.py
  docs/
    state-recovery.md
```

Use Git tags or commit SHAs for remote modules, reviewed provider constraints and committed `.terraform.lock.hcl` for each root. Avoid mutable module references.

## 3. Module interface design

A good Jenkins module exposes stable, validated inputs for environment, network boundaries, controller sizing, storage encryption, workload identity, backups and tags. Avoid inputs that allow arbitrary administrator credentials, public controller access or disabled backups.

The following lab module uses only built-in Terraform features, so it does not provision cloud resources or incur cost.

`modules/jenkins-platform/variables.tf`:

```hcl
variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "Unsupported environment."
  }
}

variable "controller_replicas" {
  type = number
  default = 1
  validation {
    condition     = var.controller_replicas == 1
    error_message = "A shared-home Jenkins controller must have exactly one active writer."
  }
}

variable "storage_encrypted" {
  type = bool
  default = true
}

variable "backup_enabled" {
  type = bool
  default = true
}

variable "public_ingress" {
  type = bool
  default = false
}
```

`modules/jenkins-platform/main.tf`:

```hcl
locals {
  policy = {
    environment         = var.environment
    controller_replicas = var.controller_replicas
    storage_encrypted   = var.storage_encrypted
    backup_enabled      = var.backup_enabled
    public_ingress      = var.public_ingress
  }
}

output "platform_policy" {
  value = local.policy
}
```

`environments/staging/main.tf`:

```hcl
terraform {
  required_version = ">= 1.6.0"
}

module "jenkins" {
  source              = "../../modules/jenkins-platform"
  environment         = "staging"
  controller_replicas = 1
  storage_encrypted   = true
  backup_enabled      = true
  public_ingress      = false
}

output "policy" {
  value = module.jenkins.platform_policy
}
```

## 4. Module contract tests

Terraform native tests exercise inputs and outputs. Save as `modules/jenkins-platform/tests/contract.tftest.hcl`:

```hcl
run "valid_staging" {
  command = plan

  variables {
    environment = "staging"
  }

  assert {
    condition     = output.platform_policy.controller_replicas == 1
    error_message = "Controller writer count must be one."
  }
}

run "reject_multiple_writers" {
  command = plan

  variables {
    environment         = "staging"
    controller_replicas = 2
  }

  expect_failures = [var.controller_replicas]
}
```

Execute:

```bash
cd modules/jenkins-platform
terraform init -backend=false
terraform fmt -check -recursive
terraform validate
terraform test
cd ../../environments/staging
terraform init -backend=false
terraform plan
```

## 5. Remote state architecture

Use an approved remote backend rather than local state for team-managed production. Requirements:

| Control | Implementation principle |
|---|---|
| Isolation | separate state per environment and ownership domain |
| Encryption | at rest and in transit; customer-managed keys if policy requires |
| Locking | backend-supported locking, never concurrent writers |
| Least privilege | CI plan/read and approved apply/write roles |
| Versioning | recoverable state object versions and retention |
| Audit | state reads/writes, key use and changes logged |
| Recovery | documented, tested state restore and import procedure |
| Sensitive values | state is confidential even if outputs are marked sensitive |

Terraform's `sensitive = true` affects display but does **not** guarantee that values are absent from state. Do not put secrets into resource arguments unless necessary and understood.

### Example AWS S3 backend

```hcl
terraform {
  backend "s3" {
    bucket       = "REPLACE-APPROVED-STATE-BUCKET"
    key          = "jenkins/staging/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
```

This is illustrative; `use_lockfile` depends on the Terraform version and backend support. Configure state bucket versioning, KMS policy, access controls and audit independently. Do not run `terraform init -migrate-state` without a backup and approved migration plan.

### Example Azure Blob backend

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "REPLACE-STATE-RG"
    storage_account_name = "replacestatestorage"
    container_name       = "tfstate"
    key                  = "jenkins/staging.tfstate"
  }
}
```

Prefer workload identity or managed identity over long-lived secrets. Validate lease-based locking, RBAC, encryption, storage account network restrictions and recovery procedures.

## 6. Policy-as-code design

Policy gates should deny high-risk plans **before** apply: public Jenkins ingress, unencrypted volumes, absent backups, broad IAM, missing ownership tags, destructive storage changes and uncontrolled multi-writer controller topology.

Policy evaluation must inspect the **actual plan** and use reliable resource-type-specific fields. A generic string search is not a production policy engine.

Example OPA/Rego for a deliberately small synthetic input contract:

```rego
package jenkins.guardrails

import rego.v1

deny contains msg if {
  input.controller_replicas != 1
  msg := "Jenkins shared-home controller requires one active writer"
}

deny contains msg if {
  not input.storage_encrypted
  msg := "Controller storage must be encrypted"
}

deny contains msg if {
  not input.backup_enabled
  msg := "Backup must be enabled"
}

deny contains msg if {
  input.public_ingress
  msg := "Public Jenkins ingress is prohibited by this lab policy"
}
```

Evaluate with an installed compatible OPA version:

```bash
opa eval --fail-defined -d policy/jenkins.rego -i policy/invalid.json \
  'data.jenkins.guardrails.deny'
```

For valid input, use `opa eval -f json` and verify the denial set is empty. `--fail-defined` is suitable for asserting an invalid fixture produces denials, **not** as a blanket success test for valid inputs.

## 7. Executable Python policy gate

Save as `scripts/check_plan.py`:

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def violations(plan):
    issues = []
    if plan.get("controller_replicas") != 1:
        issues.append("controller_replicas must equal 1")
    if plan.get("storage_encrypted") is not True:
        issues.append("storage_encrypted must be true")
    if plan.get("backup_enabled") is not True:
        issues.append("backup_enabled must be true")
    if plan.get("public_ingress") is not False:
        issues.append("public_ingress must be false")
    return issues

if __name__ == "__main__":
    data = json.loads(Path(sys.argv[1]).read_text())
    errors = violations(data)
    if errors:
        print("DENY:", *errors, sep="\n")
        sys.exit(1)
    print("ALLOW: synthetic Jenkins policy contract")
```

Example `policy/valid.json`:

```json
{"controller_replicas":1,"storage_encrypted":true,"backup_enabled":true,"public_ingress":false}
```

Example `policy/invalid.json`:

```json
{"controller_replicas":2,"storage_encrypted":false,"backup_enabled":false,"public_ingress":true}
```

```bash
python3 scripts/check_plan.py policy/valid.json
! python3 scripts/check_plan.py policy/invalid.json
```

This validates a **synthetic policy contract**, not arbitrary `terraform show -json` output. A production gate must translate plan JSON into policy input and verify all relevant resources, unknown values and deletions.

## 8. CI/CD gates and promotion

1. Run `terraform fmt`, `validate` and `test` for module contracts.
2. Scan IaC for secrets, known misconfigurations and vulnerable providers.
3. Generate `terraform plan -out=tfplan` with restricted credentials.
4. Convert saved plan to JSON in a restricted runner: `terraform show -json tfplan`.
5. Evaluate OPA/Sentinel/Conftest policies against the **full** reviewed plan.
6. Require human approval for destructive or production changes.
7. Apply the exact reviewed plan artifact with approved identity.
8. Validate Jenkins single-writer, RBAC, JCasC, agents and synthetic CI.
9. Record plan hash, state version, audit trail and rollback checkpoint.

Saved plan artifacts and JSON may contain sensitive data. Encrypt, restrict and expire them.

## 9. Drift and state incident management

Detect drift using scheduled read-only plans and classify:
- **Expected**: approved cloud-provider computed values.
- **Unauthorized**: manual edits to controller ingress/IAM/storage.
- **Critical**: backup disabled, storage exposed, deleted state or multiple writers.
- **Unclear**: provider schema or import mismatch requiring investigation.

Never automatically apply every drift correction; destructive reconciliation requires approval. Do not use `terraform state rm` or `force-unlock` as routine fixes.

## 10. Twenty troubleshooting scenarios

| # | Symptom | Investigation |
|---|---|---|
| 01 | Module source unavailable | Git tag/network/auth |
| 02 | Module version drift | immutable reference |
| 03 | Provider checksum mismatch | lock file/cache |
| 04 | Module input invalid | validation |
| 05 | Circular dependency | module graph |
| 06 | Output exposes secret | sensitivity/state |
| 07 | Remote backend denied | identity |
| 08 | State lock contention | active writer |
| 09 | Stale state after crash | version history |
| 10 | State bucket deletion | retention/recovery |
| 11 | KMS decrypt denied | key policy |
| 12 | Environment state collision | backend key |
| 13 | Policy misses unknown value | plan JSON handling |
| 14 | Policy falsely blocks change | input mapping |
| 15 | Unreviewed delete in plan | resource changes |
| 16 | Drift from console edit | audit trail |
| 17 | Import changes resource ownership | mapping |
| 18 | Jenkins ingress public | guardrail |
| 19 | Backup disabled | mandatory policy |
| 20 | Two active controllers planned | single-writer guardrail |

## 11. Six production runbooks

### A. Remote state lock contention
Identify active apply and lock owner; preserve state, obtain approval and never force-unlock an active operation.

### B. State corruption or loss
Freeze applies, select verified backend object version, restore under change control and reconcile real resources with refreshed plan.

### C. Module upgrade regression
Pin prior tested module version, inspect provider/state schema and plan; roll back infrastructure only when compatible and approved.

### D. Policy gate failure
Review exact denial and source plan; fix IaC rather than bypassing guardrails, or use a documented time-bound exception.

### E. Unauthorized drift
Preserve audit events, assess blast radius, identify owner and choose import/reconcile/rollback with security review.

### F. High-risk deletion
Stop apply, review replacement/destroy graph and backup/DR readiness, seek owner approval and rerun plan.

## 12. 100-point acceptance

| Domain | Points |
|---|---:|
| Module interface, versioning and tests | 20 |
| Remote state security, locking and recovery | 20 |
| Policy coverage and deny-by-default checks | 20 |
| CI review, plan/apply separation and approvals | 15 |
| Drift, rollback and incident runbooks | 15 |
| Evidence, security review and sign-off | 10 |
| **Total** | **100** |

Suggested pass 85/100 **plus mandatory gates**: isolated encrypted/locked state, least privilege, pinned modules/providers, no secret leakage, policy blocking unsafe changes, reviewed production plan and single-writer safety.

## 13. Evidence template

```text
UTC / change owner:
Module version and source:
Provider lock file and Terraform version:
Module tests and validation:
Backend environment key, locking, encryption:
State recovery and identity policy:
OPA/Conftest policy revision:
Valid/invalid fixtures and actual plan coverage:
Reviewed plan hash and approver:
Drift, rollback and synthetic CI:
Score / RCA / COA / reviewer:
```

**Companion:** [Chapter 087 hands-on lab](labs/087-terraform-modules-remote-state-policy-as-code-jenkins-platforms-check.md).  
**Next:** Chapter 088 — Ansible Roles, Dynamic Inventory and Jenkins Configuration Automation.
