# Chapter 086 — Jenkins Infrastructure as Code with Terraform and Ansible

**Part 18 — Terraform, Ansible and Infrastructure Automation**  
**Audience:** Jenkins SRE/DBRE, DevOps, platform engineers, security and cloud infrastructure owners  
**Prerequisites:** Chapters 081–085; Terraform CLI, Ansible, disposable Linux VM or Kubernetes lab, Jenkins LTS, approved credentials and source control.

## Learning objectives

Build a reproducible Jenkins controller using Terraform for infrastructure and Ansible for operating-system/controller configuration. Enforce drift control, least privilege, state security, immutable version pinning, automated testing and safe rollback.

## 1. Architecture and separation of concerns

```text
 Git repository → PR checks / policy / approval
                          |
                 Terraform plan/apply
                          |
           network, VM, disk, IAM, DNS, firewall
                          |
                  Ansible inventory
                          |
             OS hardening + Jenkins runtime
                          |
              Jenkins LTS + JCasC + plugins
                          |
          ephemeral agents / SCM / artifacts
                          |
       observability, backup, drift and recovery
```

Terraform manages infrastructure resources and state. Ansible converges operating-system packages and configuration. Jenkins Configuration as Code (JCasC) manages Jenkins settings. Avoid having Terraform, Ansible and manual UI changes concurrently manage the same fields.

## 2. Repository layout

```text
jenkins-iac/
  terraform/
    versions.tf
    variables.tf
    main.tf
    outputs.tf
    backend.tf.example
  ansible/
    inventory.ini
    site.yml
    templates/jenkins.service.j2
  casc/
    jenkins.yaml
  plugins/
    plugins.txt
  tests/
    test_policy.py
  README.md
```

Keep credentials in an approved secret manager. Never commit `terraform.tfstate`, `*.tfvars` containing secrets, SSH private keys, Jenkins keys or API tokens.

## 3. Terraform reproducibility

```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

variable "environment" {
  type        = string
  description = "Disposable lab environment name"
  default     = "jenkins-lab"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.environment))
    error_message = "Use a lowercase environment identifier."
  }
}

resource "local_file" "ansible_inventory" {
  filename = "${path.module}/generated-inventory.ini"
  content  = "[jenkins]\nlocalhost ansible_connection=local\n"
}

output "inventory_path" {
  value = local_file.ansible_inventory.filename
}
```

This **local-only example** demonstrates deterministic Terraform → Ansible handoff without cloud spend. For AWS/Azure, replace the local provider with reviewed VPC/subnet/VM/IAM/security-group/storage resources, remote encrypted state and environment-scoped permissions.

## 4. Terraform validation workflow

```bash
cd terraform
terraform init
terraform fmt -check
terraform validate
terraform plan -out=tfplan
terraform show tfplan
terraform apply tfplan
```

Review plans before applying. For production use an approved remote backend with encryption, locking and least-privilege access. A saved plan can contain sensitive values: restrict and expire it.

## 5. Ansible convergence

Example `ansible/site.yml` for a **safe local lab**:

```yaml
---
- name: Validate Jenkins IaC lab prerequisites
  hosts: jenkins
  gather_facts: false
  tasks:
    - name: Confirm Jenkins home directory variable
      ansible.builtin.assert:
        that:
          - jenkins_home is defined
          - jenkins_home | length > 0
        fail_msg: "Set jenkins_home to a disposable path."

    - name: Ensure lab configuration directory exists
      ansible.builtin.file:
        path: "{{ jenkins_home }}/casc"
        state: directory
        mode: "0700"

    - name: Write lab configuration marker
      ansible.builtin.copy:
        dest: "{{ jenkins_home }}/casc/iac-managed.txt"
        content: "Managed by Ansible - do not edit manually\n"
        mode: "0600"
```

Run with:

```bash
ansible-playbook -i terraform/generated-inventory.ini ansible/site.yml \
  -e "jenkins_home=/tmp/jenkins-iac-lab"
ansible-playbook -i terraform/generated-inventory.ini ansible/site.yml \
  -e "jenkins_home=/tmp/jenkins-iac-lab" --check --diff
```

The playbook does **not** install or start Jenkins; it is a safe executable convergence baseline. Production roles must separately manage supported Java/Jenkins packages, pinned images, systemd service, file ownership, TLS and secret delivery.

## 6. Production controller configuration

Pin:
- Jenkins LTS and Java version **after** verifying current support matrix.
- Plugin versions and dependencies through a tested plugin manifest.
- JCasC Git commit and schema compatibility.
- Controller image digest, agent images and remoting versions.
- Terraform provider lock file and Ansible collection versions.

Use an immutable controller image and externalize secret values to a supported credential provider. Treat JCasC as configuration, not a secret store.

## 7. State and secrets security

- Remote Terraform state with locking, encryption, access auditing and backup.
- Separate IAM/managed identities for plan, apply, Jenkins runtime and backup/restore.
- Short-lived CI credentials via workload identity/OIDC where supported.
- No secrets in Terraform outputs, Jenkins console logs or Ansible `--diff`.
- `no_log: true` for sensitive Ansible tasks, while remembering that it does not remove secret values from state files.
- Require approval for resource deletion, state migration and key changes.

## 8. GitLab CI/CD reference gates

```yaml
stages: [validate, plan]

terraform_validate:
  stage: validate
  image: hashicorp/terraform:1.9
  script:
    - cd terraform
    - terraform init -backend=false
    - terraform fmt -check
    - terraform validate

ansible_syntax:
  stage: validate
  image: python:3.12-slim
  before_script:
    - pip install --no-cache-dir ansible-core
  script:
    - ansible-playbook -i 'localhost,' -c local ansible/site.yml --syntax-check
```

Illustrative CI images/versions require pinning and security review. A full production pipeline needs protected state access, plan artifact retention controls, policy checks, change approvals and a separate gated apply stage.

## 9. Operational workflow

1. Open PR for infrastructure/JCasC/Ansible change.
2. Run formatting, validation, lint, policy and secret scans.
3. Generate reviewed Terraform plan and blast-radius report.
4. Verify consistent Jenkins backup and rollback point.
5. Apply infrastructure changes with approved identity.
6. Run Ansible in check mode then converge configuration.
7. Start/restart controller only under approved change window.
8. Validate RBAC, SCM, agents, synthetic CI and artifacts.
9. Monitor queue, availability, storage and cost.
10. Record drift and incident evidence; close change after sign-off.

## 10. Twenty troubleshooting scenarios

| # | Symptom | Investigation |
|---|---|---|
| 01 | Terraform provider unavailable | registry/network |
| 02 | Backend state lock held | active apply |
| 03 | State drift | out-of-band changes |
| 04 | Plan contains secret | sensitive inputs/state |
| 05 | Apply access denied | IAM |
| 06 | Resource already exists | import/state mapping |
| 07 | Resource deletion planned | lifecycle/approval |
| 08 | Ansible inventory empty | output path |
| 09 | SSH/auth failure | host key/identity |
| 10 | Ansible privilege escalation denied | sudo |
| 11 | Playbook not idempotent | changed result |
| 12 | Package repository unavailable | network/proxy |
| 13 | Unsupported Java runtime | Jenkins matrix |
| 14 | Plugin dependency mismatch | pinned manifest |
| 15 | JCasC schema invalid | configuration validation |
| 16 | Credential source unavailable | secret manager |
| 17 | Jenkins home ownership wrong | filesystem permissions |
| 18 | Controller starts twice | single-writer fencing |
| 19 | Agent cannot register | TLS/network/remoting |
| 20 | Rollback fails | state/backup compatibility |

## 11. Six production runbooks

### A. Terraform plan drift
Stop apply, identify authoritative desired state, import or reconcile only after owner approval, rerun plan.

### B. Terraform state lock
Identify running operation and lock owner. Never force-unlock without verifying no active writer and obtaining approval.

### C. Ansible convergence failure
Inspect first failed task, inventory and privilege boundaries; retry idempotently and validate system state.

### D. Jenkins configuration regression
Preserve logs and manifests, fence controller if required, restore compatible JCasC/plugins or verified backup.

### E. Secrets or state exposure
Revoke access, rotate affected credentials per incident policy, preserve audit evidence and fix policy before retry.

### F. Infrastructure rollback
Review Terraform reversibility and state, restore compatible controller state if needed, apply approved recovery plan and run synthetic CI.

## 12. Acceptance scorecard

| Category | Points |
|---|---:|
| Architecture and ownership boundaries | 15 |
| Terraform reproducibility and state controls | 20 |
| Ansible idempotence and configuration security | 20 |
| Jenkins/JCasC/plugin compatibility | 15 |
| CI gates, drift and policy validation | 15 |
| Rollback, runbooks and evidence | 15 |
| **Total** | **100** |

Suggested pass 85/100 plus mandatory gates: no committed secrets, reviewed plan, locked/encrypted production state, idempotent configuration, one controller writer and synthetic CI success.

## 13. Evidence template

```text
UTC / change owner:
Terraform/provider versions and lock file:
State backend/locking/access review:
Plan hash and reviewer:
Ansible inventory/check/diff/idempotence:
Jenkins core/Java/plugins/JCasC:
Secret scanning and workload identity:
Backup and rollback checkpoint:
Synthetic CI / RBAC / agents / artifacts:
Drift and cost baseline:
Score / COA / approval:
```

**Companion:** [Chapter 086 hands-on lab](labs/086-jenkins-infrastructure-as-code-terraform-ansible-check.md).  
**Next:** Chapter 087 — Terraform Modules, Remote State and Policy-as-Code for Jenkins Platforms.
