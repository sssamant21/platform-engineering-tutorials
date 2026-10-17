# Chapter 090 — Hands-on Acceptance Lab: Jenkins Infrastructure Automation, Drift and Compliance

**Scope:** Disposable Terraform, Ansible and optional Jenkins test controller. Do not apply production changes or publish secrets.

## 24 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Map ownership boundaries | Diagram |
| 02 | Define environment isolation | Matrix |
| 03 | Review Git protection and approvals | Checklist |
| 04 | Pin Terraform and modules | Manifest |
| 05 | Validate Terraform module interface | Test |
| 06 | Run fmt/validate | Output |
| 07 | Review state encryption/locking | Report |
| 08 | Document state restore | Runbook |
| 09 | Validate Ansible inventory scope | Graph |
| 10 | Execute syntax check | Pass |
| 11 | Execute first convergence | Recap |
| 12 | Execute second convergence | Idempotence |
| 13 | Review Jenkins compatibility | Matrix |
| 14 | Audit secrets/logging controls | Checklist |
| 15 | Create allow/deny fixtures | JSON |
| 16 | Execute Python policy gate | Results |
| 17 | Review Jenkins read-only pipeline | Jenkinsfile |
| 18 | Separate plan and apply identities | RACI |
| 19 | Inject lab marker drift | Evidence |
| 20 | Detect and repair drift | Recap |
| 21 | Simulate rollback decision | Runbook |
| 22 | Run optional synthetic Jenkins CI | Build |
| 23 | Collect audit evidence | Package |
| 24 | Score and sign off | Assessment |

## 24 failure drills

1. Unreviewed PR.
2. Untrusted PR write credentials.
3. Provider version drift.
4. Mutable module source.
5. Terraform validation failure.
6. Backend unavailable.
7. State lock contention.
8. Corrupted state.
9. KMS key denial.
10. Secret in plan.
11. Destructive replacement.
12. Wrong inventory environment.
13. Non-idempotent role.
14. Privilege escalation denied.
15. Invalid JCasC.
16. Plugin/Java mismatch.
17. Multiple controller writers.
18. Public ingress.
19. Disabled backup.
20. Missing policy resource coverage.
21. Plan error misclassified as no drift.
22. Expected Git change misclassified.
23. Unsafe automatic remediation.
24. Missing acceptance evidence.

## Executable policy gate

Save `policy_gate.py`:

```python
import json
import sys
from pathlib import Path

required = {
    "controller_replicas": 1,
    "storage_encrypted": True,
    "backup_enabled": True,
    "public_ingress": False,
    "secrets_in_git": False,
    "change_approved": True,
}
data = json.loads(Path(sys.argv[1]).read_text())
failed = [k for k, v in required.items() if data.get(k) != v]
if failed:
    print("DENY:", ", ".join(failed))
    raise SystemExit(1)
print("ALLOW: synthetic fixture")
```

Save `valid.json`:

```json
{"controller_replicas":1,"storage_encrypted":true,"backup_enabled":true,"public_ingress":false,"secrets_in_git":false,"change_approved":true}
```

Save `invalid.json`:

```json
{"controller_replicas":2,"storage_encrypted":false,"backup_enabled":false,"public_ingress":true,"secrets_in_git":true,"change_approved":false}
```

```bash
python3 policy_gate.py valid.json
if python3 policy_gate.py invalid.json; then
  echo "FAIL: unsafe fixture allowed"; exit 1
else
  echo "PASS: unsafe fixture denied"
fi
```

## Ansible drift lab

Use the chapter's disposable `ansible/inventory.yml` and `ansible/site.yml`:

```bash
ansible-playbook -i ansible/inventory.yml ansible/site.yml --syntax-check
ansible-playbook -i ansible/inventory.yml ansible/site.yml
ansible-playbook -i ansible/inventory.yml ansible/site.yml --check --diff
printf 'manual drift\n' > /tmp/jenkins-iac-capstone/casc/managed.txt
ansible-playbook -i ansible/inventory.yml ansible/site.yml --check --diff
ansible-playbook -i ansible/inventory.yml ansible/site.yml
```

Expected: manual marker drift is detected and repaired; second converged run makes no unintended changes.

## 100-point scorecard

| Domain | Maximum |
|---|---:|
| Architecture, ownership and isolation | 10 |
| Terraform modules, state and recovery | 20 |
| Ansible idempotence and Jenkins compatibility | 20 |
| Git controls, CI and policy | 15 |
| Drift detection and safe remediation | 15 |
| Secrets/IAM and security evidence | 10 |
| Runbooks, rollback, synthetic CI and sign-off | 10 |
| **Total** | **100** |

Suggested pass 85 plus all mandatory gates in the chapter. A synthetic fixture is not proof of real infrastructure compliance.

## Evidence worksheet

```text
UTC / owner:
Git approval and commit:
Terraform validation and state controls:
Ansible first/second runs:
Policy allow/deny:
Drift injection and correction:
Jenkins compatibility and optional synthetic CI:
Security/secret review:
Rollback/runbook evidence:
24 exercises/24 drills:
Score / mandatory gates / RCA / COA / reviewer:
```

## Acceptance checklist

- [ ] 24 exercises attempted with evidence.
- [ ] 24 failure drills executed or explicitly blocked.
- [ ] Terraform validation completed.
- [ ] State controls reviewed.
- [ ] Ansible second run idempotent.
- [ ] Policy accepts safe fixture and rejects unsafe fixture.
- [ ] Drift detection and repair demonstrated.
- [ ] No secrets or privileged production operations used.
- [ ] Rollback and runbooks reviewed.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 090 — Jenkins Infrastructure Automation, Drift and Compliance Acceptance Capstone](../090-jenkins-infrastructure-automation-drift-compliance-acceptance-capstone.md).
