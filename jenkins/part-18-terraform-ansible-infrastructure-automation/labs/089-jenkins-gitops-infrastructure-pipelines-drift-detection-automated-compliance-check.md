# Chapter 089 — Hands-on Lab: GitOps Infrastructure Pipelines, Drift and Compliance

**Scope:** Disposable Terraform/Ansible/Jenkins environment. No production apply.

## 20 hands-on exercises
1. Map Git source-of-truth boundaries.
2. Define protected PR approvals.
3. Create read-only Jenkinsfile.
4. Run Terraform fmt.
5. Run Terraform validate.
6. Run Ansible syntax check.
7. Create compliance JSON.
8. Implement Python policy gate.
9. Verify valid fixture allowed.
10. Verify unsafe fixture denied.
11. Review CI/state identity separation.
12. Run read-only Terraform drift plan.
13. Capture detailed exit code.
14. Classify proposed changes.
15. Simulate public ingress violation.
16. Simulate disabled backup violation.
17. Review unknown plan values/deletions.
18. Design evidence retention.
19. Review rollback and incident runbooks.
20. Complete 100-point scorecard and COA.

## 12 failure drills
1. Branch protection bypass.
2. Privileged PR runner.
3. Terraform backend denial.
4. State lock contention.
5. Plan artifact secret exposure.
6. Destructive replacement.
7. Missing policy mapping.
8. False policy denial.
9. Stale plan.
10. Wrong Ansible inventory.
11. Unreviewed auto-remediation.
12. Missing audit evidence.

## Executable compliance checker
Save `compliance.py`:
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
actual = json.loads(Path(sys.argv[1]).read_text())
bad = [key for key, value in EXPECTED.items() if actual.get(key) != value]
if bad:
    print("DENY:", ", ".join(bad))
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
python3 compliance.py valid.json
if python3 compliance.py invalid.json; then
  echo "FAIL: unsafe fixture allowed"; exit 1
else
  echo "PASS: unsafe fixture denied"
fi
```

## Read-only drift check
```bash
set +e
terraform -chdir=terraform plan -detailed-exitcode
rc=$?
set -e
case "$rc" in
  0) echo "No proposed changes" ;;
  2) echo "Proposed changes: review" ;;
  1) echo "Plan failed" >&2; exit 1 ;;
  *) exit 1 ;;
esac
```
Use a disposable Terraform root. Do not automatically apply.

## Evidence
```text
UTC/owner:
Git PR policy and approval:
CI identity/secret handling:
Terraform plan/state:
Ansible syntax/check:
Valid and invalid compliance:
Drift plan/classification:
Synthetic CI:
Evidence retention:
Score/RCA/COA/reviewer:
```

## Acceptance
- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Git ownership and approvals defined.
- [ ] Terraform/Ansible/JCasC validation designed.
- [ ] Valid fixture allowed; unsafe fixture denied.
- [ ] Drift exit codes classified correctly.
- [ ] No automatic destructive remediation.
- [ ] State and CI credentials protected.
- [ ] Audit evidence and rollback reviewed.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 089 — Jenkins GitOps Infrastructure Pipelines, Drift Detection and Automated Compliance](../089-jenkins-gitops-infrastructure-pipelines-drift-detection-automated-compliance.md).
