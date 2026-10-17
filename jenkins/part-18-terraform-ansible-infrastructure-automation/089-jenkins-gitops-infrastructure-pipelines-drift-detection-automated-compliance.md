# Chapter 089 — Jenkins GitOps Infrastructure Pipelines, Drift Detection and Automated Compliance

**Part 18 — Terraform, Ansible and Infrastructure Automation**

## Learning outcomes
Implement Git-governed infrastructure delivery, approved Terraform plans, Ansible and JCasC validation, policy-as-code, read-only drift detection, audit evidence, rollback and production runbooks.

## Architecture
```text
Git PR → lint/test/secret scan → Terraform plan → policy evaluation
  → approval → Terraform apply → Ansible/JCasC convergence
  → Jenkins synthetic CI → audit evidence
                          ↘ scheduled drift plan → triage/PR
```

**Ownership:** Terraform owns infrastructure; Ansible owns host configuration; JCasC owns Jenkins configuration; Argo CD/Flux may own Kubernetes workloads. Assign exactly one reconciliation owner to each resource. Jenkins should not be the only recovery mechanism for its own underlying infrastructure.

## Security and safety
- Use protected branches, CODEOWNERS, reviewed module/provider versions and restricted CI identities.
- Run untrusted PR validation without cloud write credentials or privileged Jenkins secrets.
- Use remote encrypted, locked Terraform state. Saved plan files and JSON may contain secrets.
- Require explicit approval before apply, resource deletion, state migration or production restarts.
- Keep one active Jenkins writer to a writable JENKINS_HOME.
- Never automatically apply all drift corrections: a plan difference may represent a pending approved change, computed provider value or unauthorized edit.
- Capture immutable or access-controlled audit evidence, not secret-bearing raw state in Git.

## Git repository layout
```text
jenkins-gitops/
  Jenkinsfile
  terraform/
  ansible/
  casc/
  policy/compliance.json
  scripts/compliance.py
  evidence/README.md
```

## Jenkins read-only validation pipeline
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
          cd terraform
          terraform init -backend=false
          terraform fmt -check
          terraform validate
        '''
      }
    }
    stage('Ansible syntax') {
      steps {
        sh 'ansible-playbook -i ansible/inventory.yml ansible/site.yml --syntax-check'
      }
    }
    stage('Compliance contract') {
      steps {
        sh 'python3 scripts/compliance.py policy/compliance.json'
      }
    }
  }
}
```

This pipeline intentionally does not apply infrastructure. Pin tool versions and runner images for production.

## Executable synthetic compliance gate
Save `policy/compliance.json`:
```json
{"controller_replicas":1,"storage_encrypted":true,"backup_enabled":true,"public_ingress":false,"secrets_in_git":false,"change_approved":true}
```

Save `scripts/compliance.py`:
```python
import json
import sys
from pathlib import Path

EXPECTED = {
    "controller_replicas": 1,
    "storage_encrypted": True,
    "backup_enabled": True,
    "public_ingress": False,
    "secrets_in_git": False,
    "change_approved": True,
}
data = json.loads(Path(sys.argv[1]).read_text())
violations = [k for k, v in EXPECTED.items() if data.get(k) != v]
if violations:
    print("DENY:", ", ".join(violations))
    sys.exit(1)
print("ALLOW: synthetic compliance contract")
```
This checks a synthetic contract, **not** a real Terraform plan or live compliance posture. Production policy must inspect the actual plan JSON, unknown values, resource changes and deletion/replacement semantics.

## Terraform drift detection
Terraform `plan -detailed-exitcode` returns 0 (no changes), 1 (error), 2 (changes). A proposed change does not alone prove unauthorized drift.

```bash
set +e
terraform -chdir=terraform plan -detailed-exitcode
rc=$?
set -e
case "$rc" in
  0) echo "No proposed changes" ;;
  2) echo "Changes proposed: correlate with Git and cloud audit" ;;
  1) echo "Plan failed" >&2; exit 1 ;;
  *) exit 1 ;;
esac
```

Do not publish secret-bearing plan artifacts to open build logs. Restrict CI permissions and store signed or tamper-evident evidence as required.

## Production promotion gates
1. Protected PR and code-owner approval.
2. Terraform format, validate and native tests.
3. Ansible syntax/lint/check mode and JCasC validation.
4. Secret and misconfiguration scanning.
5. Saved reviewed plan with state version and plan hash.
6. OPA/Conftest policy decision over real plan changes.
7. Explicit production approval and time-bound apply role.
8. Apply the reviewed plan; reconcile any stale-plan rejection.
9. Run Ansible/JCasC under maintenance controls.
10. Verify RBAC, SCM, agent provisioning, synthetic Pipeline and artifact integrity.
11. Capture evidence and monitor SLO/queue/agent changes.
12. Detect future drift and open a PR or incident instead of blind apply.

## Drift severity
| Severity | Example | Response |
|---|---|---|
| Informational | provider-computed field | document |
| Medium | approved Git change not applied | schedule |
| High | public ingress, excessive IAM, disabled backups | security review |
| Critical | shared-home dual writer, compromised keys | stop and escalate |

## Twenty troubleshooting scenarios
| # | Symptom | Investigation |
|---|---|---|
| 01 | PR policy bypass | branch protection |
| 02 | CI identity overprivileged | OIDC/IAM |
| 03 | Terraform init fails | backend/provider |
| 04 | State lock contention | active writer |
| 05 | Plan leaks secret | artifact controls |
| 06 | Destructive replace | blast radius |
| 07 | Policy misses resource | schema mapping |
| 08 | Policy false positive | unknown values |
| 09 | Approval expired | change window |
| 10 | Stale plan | state mismatch |
| 11 | Wrong Ansible inventory | environment filter |
| 12 | Check mode inaccurate | module behavior |
| 13 | JCasC invalid | schema |
| 14 | Plugin/core mismatch | compatibility |
| 15 | Two controllers start | fencing |
| 16 | Expected change classified as drift | Git history |
| 17 | Drift detection fails | API identity |
| 18 | Audit evidence missing | pipeline retention |
| 19 | Synthetic CI fails | SCM/agents/artifacts |
| 20 | Remediation damages service | approval and rollback |

## Six operational runbooks
**Policy failure:** Inspect rule and authoritative plan, correct IaC or seek documented exception.

**Drift alert:** Correlate Git commit, Terraform plan and cloud audit; classify severity and assign owner.

**Apply/state failure:** Stop competing writers, preserve state, investigate partial resources and replan.

**Secret exposure:** Revoke and rotate, preserve audit trail, restrict artifacts and notify security.

**Jenkins regression:** Stop rollout, capture JCasC/plugin differences, restore compatible known-good state and validate CI.

**Evidence gap:** Identify missing source, regenerate trustworthy evidence, document audit impact.

## 100-point acceptance scorecard
| Domain | Points |
|---|---:|
| Git ownership and approvals | 15 |
| Terraform/Ansible/JCasC validation | 20 |
| Policy coverage and secrets | 20 |
| Drift detection/classification | 15 |
| Safe apply, rollback and single writer | 15 |
| Evidence, monitoring and runbooks | 15 |
| **Total** | **100** |

Pass guideline: 85/100 **and** mandatory gates: no privileged untrusted PR execution, protected state, reviewed plan, unsafe-change policy denial, no automatic destructive remediation and critical synthetic CI pass. Unexecuted checks remain blocked.

## Evidence template
```text
UTC/change owner:
Git SHA and PR approval:
Terraform plan hash and state version:
Policy revision and allow/deny:
Ansible inventory/check/apply:
JCasC/core/plugins:
Secrets and IAM review:
Drift classification and cloud audit:
Synthetic CI and artifact digest:
Rollback checkpoint:
Score/RCA/COA/reviewer:
```

**Companion:** [Chapter 089 hands-on lab](labs/089-jenkins-gitops-infrastructure-pipelines-drift-detection-automated-compliance-check.md).  
**Next:** Chapter 090 — Jenkins Infrastructure Automation, Drift and Compliance Acceptance Capstone.
