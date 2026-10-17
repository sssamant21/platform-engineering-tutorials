# Chapter 086 — Hands-on Lab: Terraform and Ansible Jenkins IaC

**Safety:** Use the local-only Terraform provider and a disposable directory. No production infrastructure, real secrets or destructive operations.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Create Jenkins IaC repository layout | Tree |
| 02 | Install/check Terraform CLI | Version |
| 03 | Install/check Ansible | Version |
| 04 | Create versions.tf with provider constraints | HCL |
| 05 | Create validated environment variable | HCL |
| 06 | Generate local inventory via Terraform | Output |
| 07 | Run terraform fmt -check | Pass |
| 08 | Run terraform validate | Pass |
| 09 | Review terraform plan | Plan |
| 10 | Apply disposable local inventory | File |
| 11 | Create idempotent Ansible playbook | YAML |
| 12 | Run Ansible syntax check | Pass |
| 13 | Execute Ansible convergence | Result |
| 14 | Rerun and inspect idempotence | Changed count |
| 15 | Run Ansible --check --diff | Diff |
| 16 | Review state and secret hygiene | Checklist |
| 17 | Simulate manual inventory drift | Diff |
| 18 | Reapply desired state safely | Recovery |
| 19 | Review rollback and cleanup | Evidence |
| 20 | Score 100-point acceptance and COA | Report |

## 12 failure drills

1. Provider download unavailable.
2. Invalid Terraform variable.
3. Terraform syntax error.
4. State lock contention.
5. Unreviewed resource deletion.
6. Sensitive value in plan.
7. Missing inventory.
8. Ansible syntax error.
9. Non-idempotent task.
10. Permission denial.
11. JCasC incompatibility (discussion/simulation).
12. Jenkins single-writer violation (discussion/simulation).

## Executable Terraform example

Save as `terraform/main.tf`:

```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    local = {
      source = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

variable "environment" {
  type = string
  default = "jenkins-lab"
}

resource "local_file" "inventory" {
  filename = "${path.module}/generated-inventory.ini"
  content  = "[jenkins]\nlocalhost ansible_connection=local\n"
}

output "inventory_path" {
  value = local_file.inventory.filename
}
```

```bash
cd terraform
terraform init
terraform fmt -check
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
cd ..
```

## Executable Ansible example

Save as `ansible/site.yml`:

```yaml
---
- name: Converge disposable Jenkins IaC lab
  hosts: jenkins
  gather_facts: false
  tasks:
    - name: Require disposable Jenkins path
      ansible.builtin.assert:
        that:
          - jenkins_home is defined
          - jenkins_home is match('^/tmp/jenkins-iac-lab$')

    - name: Create configuration directory
      ansible.builtin.file:
        path: "{{ jenkins_home }}/casc"
        state: directory
        mode: "0700"

    - name: Write managed marker
      ansible.builtin.copy:
        dest: "{{ jenkins_home }}/casc/managed.txt"
        content: "Ansible managed\n"
        mode: "0600"
```

```bash
ansible-playbook -i terraform/generated-inventory.ini ansible/site.yml \
  -e jenkins_home=/tmp/jenkins-iac-lab
ansible-playbook -i terraform/generated-inventory.ini ansible/site.yml \
  -e jenkins_home=/tmp/jenkins-iac-lab --check --diff
```

## Idempotence and drift test

```bash
printf 'manual drift\n' > /tmp/jenkins-iac-lab/casc/managed.txt
ansible-playbook -i terraform/generated-inventory.ini ansible/site.yml \
  -e jenkins_home=/tmp/jenkins-iac-lab --check --diff
ansible-playbook -i terraform/generated-inventory.ini ansible/site.yml \
  -e jenkins_home=/tmp/jenkins-iac-lab
```

Verify the marker returns to `Ansible managed`. Clean up only the disposable lab directory after evidence collection.

## Evidence template

```text
UTC / owner:
Terraform/Ansible versions:
Provider lock and init:
Plan review:
Generated inventory:
First/second Ansible run:
Check-mode drift detection:
Security/state review:
Rollback/cleanup:
Score / COA / reviewer:
```

## Acceptance

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Terraform fmt/validate/plan pass.
- [ ] Inventory generation verified.
- [ ] Ansible syntax and convergence pass.
- [ ] Second run idempotent.
- [ ] Drift detection and correction demonstrated.
- [ ] No real credentials committed.
- [ ] Production controls identified separately.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 086 — Jenkins Infrastructure as Code with Terraform and Ansible](../086-jenkins-infrastructure-as-code-terraform-ansible.md).
