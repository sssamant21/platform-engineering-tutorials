# Chapter 087 — Hands-on Lab: Terraform Modules, Remote State and Policy-as-Code

**Environment:** Disposable Terraform module, Python 3, optional OPA CLI. Use no real cloud credentials or production state.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Create reusable module layout | Tree |
| 02 | Define environment input | HCL |
| 03 | Validate controller writer count | Test |
| 04 | Validate encryption and backup inputs | Test |
| 05 | Export typed policy output | Output |
| 06 | Create staging root configuration | HCL |
| 07 | Run terraform fmt -check | Pass |
| 08 | Run terraform init -backend=false | Pass |
| 09 | Run terraform validate | Pass |
| 10 | Run terraform test | Pass |
| 11 | Generate local plan | Plan |
| 12 | Inspect remote state design for S3/Azure | Review |
| 13 | Document backend identity/locking | Matrix |
| 14 | Create valid/invalid policy fixtures | JSON |
| 15 | Run Python policy allow test | Result |
| 16 | Run Python policy deny test | Result |
| 17 | Evaluate OPA Rego if installed | Result |
| 18 | Simulate unauthorized ingress drift | Finding |
| 19 | Review state recovery/rollback runbook | Checklist |
| 20 | Complete 100-point acceptance and COA | Sign-off |

## 12 failure drills

1. Invalid module input.
2. Multiple active writers requested.
3. Module source unavailable.
4. Provider lock mismatch.
5. Backend access denied.
6. State lock contention.
7. State version corruption.
8. Unencrypted storage requested.
9. Backup disabled.
10. Public Jenkins ingress.
11. Policy input mismatch.
12. Unauthorized manual drift.

## Executable synthetic policy gate

Save `check_plan.py`:

```python
import json
import sys
from pathlib import Path

def violations(plan):
    errors = []
    if plan.get("controller_replicas") != 1:
        errors.append("one active controller required")
    if plan.get("storage_encrypted") is not True:
        errors.append("encrypted storage required")
    if plan.get("backup_enabled") is not True:
        errors.append("backup required")
    if plan.get("public_ingress") is not False:
        errors.append("public ingress forbidden")
    return errors

if __name__ == "__main__":
    errors = violations(json.loads(Path(sys.argv[1]).read_text()))
    if errors:
        print("DENY:", *errors, sep="\n")
        raise SystemExit(1)
    print("ALLOW")
```

Save `valid.json`:

```json
{"controller_replicas":1,"storage_encrypted":true,"backup_enabled":true,"public_ingress":false}
```

Save `invalid.json`:

```json
{"controller_replicas":2,"storage_encrypted":false,"backup_enabled":false,"public_ingress":true}
```

```bash
python3 check_plan.py valid.json
if python3 check_plan.py invalid.json; then
  echo "ERROR: unsafe policy accepted"; exit 1
else
  echo "PASS: unsafe policy denied"
fi
```

Expected: valid ALLOW, invalid DENY. These fixtures are **not Terraform plan JSON**; production policy must inspect real plan changes and unknowns.

## Terraform module contract test

Save `tests/contract.tftest.hcl` in a module with the matching variables/outputs from the chapter:

```hcl
run "valid" {
  command = plan
  variables {
    environment = "staging"
  }
  assert {
    condition     = output.platform_policy.controller_replicas == 1
    error_message = "Expected one active writer."
  }
}

run "invalid_replicas" {
  command = plan
  variables {
    environment         = "staging"
    controller_replicas = 2
  }
  expect_failures = [var.controller_replicas]
}
```

```bash
terraform init -backend=false
terraform fmt -check
terraform validate
terraform test
```

## Evidence worksheet

```text
UTC / lab owner:
Module source and version:
Terraform version and provider lock:
Module validation/test results:
Remote backend architecture and access:
Policy allow/deny evidence:
State recovery and drift drill:
Security/approval controls:
Score / RCA / COA / reviewer:
```

## Acceptance

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Terraform module contracts validated.
- [ ] Remote state encryption/locking design reviewed.
- [ ] Environment state isolation defined.
- [ ] Valid fixture allowed and unsafe fixture denied.
- [ ] Actual-plan policy integration design documented.
- [ ] Drift and rollback runbooks reviewed.
- [ ] No secrets or state committed.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 087 — Terraform Modules, Remote State and Policy-as-Code for Jenkins Platforms](../087-terraform-modules-remote-state-policy-as-code-jenkins-platforms.md).
