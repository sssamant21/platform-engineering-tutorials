# Chapter 090 — Jenkins Infrastructure Automation, Drift and Compliance Acceptance Capstone

**Part 18 — Terraform, Ansible and Infrastructure Automation (final capstone)**  
**Audience:** Jenkins SRE/DBRE, DevOps, platform engineers, security, audit and change owners  
**Prerequisites:** Chapters 086–089; Terraform, Ansible, Python 3, Git, disposable Jenkins controller and an isolated test workspace.

## Mission

Prove that Jenkins infrastructure can be provisioned reproducibly, configured idempotently, changed through reviewed Git workflows, checked against security policies, monitored for drift and safely recovered from failures.

**Lab scope:** All executable examples are local and synthetic. A successful lab does not certify a live Jenkins controller, cloud account or regulatory compliance posture.

## 1. Architecture

```text
Git PR + CODEOWNERS + approval
        |
        v
Terraform fmt/validate/test → plan → policy-as-code → approved apply
        |
        v
Terraform modules + encrypted/locked remote state
        |
        v
Ansible inventory → roles → JCasC → Jenkins controller
        |
        v
RBAC + SCM + agents + synthetic Pipeline + artifact integrity
        |
        v
Drift check → severity classification → PR or incident
        |
        v
Evidence / RCA / COA / acceptance sign-off
```

Ownership boundaries: Terraform manages cloud resources; Ansible manages host configuration; JCasC manages Jenkins settings; GitOps controllers manage their declared Kubernetes workloads. Prevent overlapping resource ownership and preserve one active Jenkins controller writer per writable home.

## 2. Acceptance objectives

| Requirement | Mandatory evidence |
|---|---|
| Reproducibility | pinned Terraform modules/providers and role versions |
| State security | environment-isolated remote state, encryption, locking and access review |
| Change control | reviewed plan, PR approvals, separate apply identity |
| Idempotence | second Ansible convergence produces zero unintended changes |
| Configuration | JCasC schema, core/Java/plugin compatibility |
| Security | policy denies unsafe changes; no secrets in Git/logs |
| Drift | read-only plan classification and owner escalation |
| Recovery | rollback point and tested restore procedure |
| Reliability | synthetic CI, agents, RBAC and artifacts |
| Audit | timestamps, plan hash, state version, owner and sign-off |

Do not treat a Terraform plan difference as proof of unauthorized drift; correlate it with Git changes and provider/cloud audit records.

## 3. Reference repository

```text
jenkins-iac-capstone/
  terraform/
    main.tf
  ansible/
    inventory.yml
    site.yml
  policy/
    compliant.json
    unsafe.json
  scripts/
    policy_gate.py
    acceptance.py
  Jenkinsfile
  evidence/
    README.md
```

## 4. Executable local Terraform configuration

Save `terraform/main.tf`:

```hcl
terraform {
  required_version = ">= 1.6.0"
}

variable "environment" {
  type    = string
  default = "lab"
  validation {
    condition     = contains(["lab", "staging"], var.environment)
    error_message = "Only disposable lab or staging is allowed."
  }
}

locals {
  policy = {
    environment         = var.environment
    controller_replicas = 1
    storage_encrypted   = true
    backup_enabled      = true
    public_ingress      = false
  }
}

output "jenkins_policy" {
  value = local.policy
}
```

Run:

```bash
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
terraform -chdir=terraform plan
```

This local configuration does not create resources and therefore does not exercise real remote-state locking, IAM or encryption. Those must be validated separately in an approved cloud staging environment.

## 5. Executable Ansible convergence

Save `ansible/inventory.yml`:

```yaml
all:
  children:
    jenkins:
      hosts:
        localhost:
          ansible_connection: local
```

Save `ansible/site.yml`:

```yaml
---
- name: Converge disposable Jenkins IaC capstone
  hosts: jenkins
  gather_facts: false
  vars:
    lab_home: /tmp/jenkins-iac-capstone
  tasks:
    - name: Assert disposable target
      ansible.builtin.assert:
        that:
          - lab_home == '/tmp/jenkins-iac-capstone'

    - name: Create lab configuration directory
      ansible.builtin.file:
        path: "{{ lab_home }}/casc"
        state: directory
        mode: "0700"

    - name: Write managed configuration marker
      ansible.builtin.copy:
        dest: "{{ lab_home }}/casc/managed.txt"
        content: "Managed by Ansible - Jenkins IaC capstone\n"
        mode: "0600"
```

```bash
ansible-playbook -i ansible/inventory.yml ansible/site.yml --syntax-check
ansible-playbook -i ansible/inventory.yml ansible/site.yml
ansible-playbook -i ansible/inventory.yml ansible/site.yml --check --diff
```

The second convergence should show no unintended changes. Do not run this lab against a production Jenkins home.

## 6. Executable policy-as-code gate

Save `scripts/policy_gate.py`:

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REQUIRED = {
    "controller_replicas": 1,
    "storage_encrypted": True,
    "backup_enabled": True,
    "public_ingress": False,
    "secrets_in_git": False,
    "change_approved": True,
}

def violations(actual):
    return [f"{key}: expected {value!r}, got {actual.get(key)!r}"
            for key, value in REQUIRED.items() if actual.get(key) != value]

if __name__ == "__main__":
    data = json.loads(Path(sys.argv[1]).read_text())
    errors = violations(data)
    if errors:
        print("DENY", *errors, sep="\n")
        sys.exit(1)
    print("ALLOW: synthetic contract")
```

Save `policy/compliant.json`:

```json
{"controller_replicas":1,"storage_encrypted":true,"backup_enabled":true,"public_ingress":false,"secrets_in_git":false,"change_approved":true}
```

Save `policy/unsafe.json`:

```json
{"controller_replicas":2,"storage_encrypted":false,"backup_enabled":false,"public_ingress":true,"secrets_in_git":true,"change_approved":false}
```

```bash
python3 scripts/policy_gate.py policy/compliant.json
if python3 scripts/policy_gate.py policy/unsafe.json; then
  echo "FAIL: unsafe policy allowed"; exit 1
else
  echo "PASS: unsafe policy denied"
fi
```

This checker validates a synthetic fixture, **not actual Terraform plan JSON**. Production gates must inspect real planned resource changes, unknown values, IAM permissions and destructive actions.

## 7. Jenkins read-only pipeline

```groovy
pipeline {
  agent { label 'iac-validation' }
  options {
    timestamps()
    disableConcurrentBuilds()
    timeout(time: 20, unit: 'MINUTES')
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Terraform validation') {
      steps {
        sh '''
          set -eu
          terraform -chdir=terraform init -backend=false
          terraform -chdir=terraform fmt -check
          terraform -chdir=terraform validate
        '''
      }
    }
    stage('Ansible syntax') {
      steps {
        sh 'ansible-playbook -i ansible/inventory.yml ansible/site.yml --syntax-check'
      }
    }
    stage('Policy allow and deny') {
      steps {
        sh '''
          set -eu
          python3 scripts/policy_gate.py policy/compliant.json
          if python3 scripts/policy_gate.py policy/unsafe.json; then
            exit 1
          fi
        '''
      }
    }
  }
}
```

Use a trusted, pinned toolchain agent. Do not expose remote state credentials to untrusted PR jobs.

## 8. Drift workflow

```bash
set +e
terraform -chdir=terraform plan -detailed-exitcode
rc=$?
set -e
case "$rc" in
  0) echo "No proposed changes" ;;
  2) echo "Proposed changes: classify against Git and audit" ;;
  1) echo "Plan error: investigate" >&2; exit 1 ;;
  *) exit 1 ;;
esac
```

**Response:** classify informational, expected pending change, unauthorized drift or critical incident. Do not auto-apply destructive changes. Use approved owner reconciliation and retain evidence.

## 9. Twenty-four capstone exercises

1. Map Git, Terraform, Ansible, JCasC and Kubernetes ownership.
2. Define environment isolation and change approval.
3. Create repository and source protection policy.
4. Pin Terraform and provider/module versions.
5. Define a reusable Jenkins module interface.
6. Validate Terraform inputs and outputs.
7. Review remote state encryption and locking.
8. Document state backup/recovery and IAM.
9. Create Ansible inventory with explicit target limits.
10. Build idempotent role or playbook.
11. Run syntax and check mode.
12. Run first and second convergence.
13. Review Java/core/plugin/JCasC compatibility.
14. Validate secret manager and logging controls.
15. Build policy allow and deny fixtures.
16. Run automated policy checker.
17. Integrate validation into Jenkins Pipeline.
18. Review plan/apply identity separation.
19. Simulate drift with manual lab marker change.
20. Detect drift and restore intended configuration.
21. Test rollback and failure escalation.
22. Run synthetic CI and RBAC/agent checks in optional Jenkins lab.
23. Collect plan hashes, audit and recovery evidence.
24. Complete 100-point scorecard, RCA/COA and sign-off.

## 10. Twenty-four failure scenarios

| # | Scenario | Gate or response |
|---|---|---|
| 01 | Unreviewed PR | branch protection |
| 02 | Untrusted PR gets write credentials | identity isolation |
| 03 | Provider version drift | lock file |
| 04 | Module source changes unexpectedly | pinned ref |
| 05 | Terraform validation fails | block |
| 06 | Backend state unavailable | incident |
| 07 | State lock contention | identify active writer |
| 08 | State corruption | verified recovery |
| 09 | KMS key inaccessible | key custody |
| 10 | State/plan secret exposure | security response |
| 11 | Destructive plan replacement | manual approval |
| 12 | Wrong environment inventory | scope validation |
| 13 | Ansible task not idempotent | repair role |
| 14 | Become permission denied | least privilege |
| 15 | JCasC schema invalid | config gate |
| 16 | Plugin/Java mismatch | compatibility |
| 17 | Multiple Jenkins writers | hard stop |
| 18 | Public ingress allowed | policy denial |
| 19 | Backup disabled | policy denial |
| 20 | Policy input misses resource | coverage test |
| 21 | Terraform plan error treated as no drift | exit-code gate |
| 22 | Expected Git change mistaken for drift | correlation |
| 23 | Auto-remediation deletes stateful resource | approval block |
| 24 | Evidence missing at sign-off | fail acceptance |

## 11. Eight operational runbooks

### A. Terraform state lock or backend failure
Stop competing applies, identify lock owner, preserve state and restore only through approved recovery procedure.

### B. Terraform module or provider regression
Pin known-good versions, review state schema, replan and execute approved rollback if compatible.

### C. Ansible inventory or idempotence failure
Stop rollout, verify targets, correct role logic and retest check mode and convergence.

### D. Jenkins JCasC/plugin regression
Pause changes, preserve logs, restore compatible configuration and validate critical CI.

### E. Secrets/state exposure
Revoke and rotate, preserve audit, restrict CI artifacts and involve security.

### F. Unauthorized drift
Correlate cloud audit and Git history, classify impact, open change/incident and reconcile with owner approval.

### G. Dangerous automated remediation
Disable automated apply, preserve state and logs, evaluate blast radius and recover from tested backup.

### H. Acceptance or audit failure
Record failed mandatory gate, assign COA and repeat the failed drill before service-owner sign-off.

## 12. 100-point enterprise acceptance

| Domain | Points |
|---|---:|
| Architecture, ownership and environment isolation | 10 |
| Terraform modules, remote state and recovery | 20 |
| Ansible idempotence and Jenkins/JCasC compatibility | 20 |
| Git controls, plan review and CI policy | 15 |
| Drift detection, classification and safe remediation | 15 |
| Secrets, IAM and security evidence | 10 |
| Runbooks, rollback, synthetic CI and sign-off | 10 |
| **Total** | **100** |

Suggested pass **85/100**, plus mandatory gates: protected state, reviewed change, least-privilege identity, no leaked secrets, policy denial for unsafe configurations, single-writer safety, idempotent convergence and verified synthetic CI in the target test environment. Blocked or unexecuted checks must not be marked passed.

## 13. Evidence template

```text
UTC / owner / change ID:
Git SHA / approvals:
Terraform version/module/provider locks:
State isolation/encryption/locking/backup:
Plan hash and policy decision:
Ansible inventory and two-run idempotence:
JCasC/core/Java/plugins:
Secrets and IAM review:
Drift injection/classification/remediation:
Synthetic CI / RBAC / agents / artifact:
Rollback and incident runbooks:
24 exercises / 24 scenarios:
Score / mandatory gates / RCA / COA / reviewer:
```

**Companion:** [Chapter 090 acceptance lab](labs/090-jenkins-infrastructure-automation-drift-compliance-acceptance-capstone-check.md).  
**Part 18 complete:** Chapters 086–090.  
**Next:** Chapter 091 — Jenkins Enterprise SRE Operating Model, Governance and Service Ownership.
