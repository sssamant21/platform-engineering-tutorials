# Chapter 064 — Hands-on Lab: Jenkins Configuration Drift and GitOps Governance

**Environment:** Disposable Jenkins LTS, Git-managed JCasC/Job DSL, pinned plugins, test identities, CI runner, optional OPA/Conftest. No production mutation.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Baseline | Capture core/plugin/config revision | Inventory |
| 02 | Architecture | Diagram desired/observed state | Diagram |
| 03 | Ownership | Create CODEOWNERS example | Git |
| 04 | Protection | Define required review rules | Policy |
| 05 | Plugins | Compare approved vs installed | Diff |
| 06 | JCasC | Export safe supported metadata | Export |
| 07 | Normalize | Remove nonsemantic differences | Diff |
| 08 | Jobs | Compare generated inventory | Report |
| 09 | Secrets | Verify no values in evidence | Scan |
| 10 | OPA | Test controller executor policy | Result |
| 11 | Negative | Introduce insecure synthetic setting | Denied |
| 12 | CI | Run static policy gate | Logs |
| 13 | Staging | Build immutable controller image | Digest |
| 14 | Promotion | Record Git SHA/image digest | Record |
| 15 | Drift | Make benign UI change | Alert |
| 16 | Security | Simulate unauthorized role grant | Alert |
| 17 | Exception | Record time-bound approved exception | Ticket |
| 18 | Reconcile | Restore reviewed Git state | Result |
| 19 | Rollback | Restore prior controller image/config | RTO |
| 20 | Review | Complete governance sign-off | Report |

## 12 troubleshooting drills

1. Plugin inventory mismatch.
2. JCasC export default mismatch.
3. Job DSL overwrites manual edit.
4. False-positive policy rule.
5. Secret in audit export.
6. Unreviewed admin grant.
7. Missing CODEOWNERS enforcement.
8. Expired exception.
9. CI build dependency failure.
10. Staging/prod digest mismatch.
11. Unsupported JCasC live reload.
12. Rollback from bad configuration.

## Sample drift check

```sh
#!/usr/bin/env bash
set -euo pipefail
diff -u expected-plugins.txt observed-plugins.txt
```

Inventory files must be sorted, normalized and free of secrets. This checks only plugin version drift, not effective Jenkins permissions.

## Evidence template

```text
UTC timestamp:
Git desired-state revision:
Controller image digest:
Plugin inventory diff:
JCasC supported-field comparison:
Generated job inventory:
Policy/approval results:
Injected benign/security drift:
Exception owner/expiry:
Reconciliation result:
Rollback time:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Drift covers plugins, JCasC and generated jobs.
- [ ] Secret values absent from evidence.
- [ ] Security drift detected and remediated.
- [ ] Git approval and exception lifecycle validated.
- [ ] Rollback demonstrated.
- [ ] Reviewer signs off.

**Related:** [Chapter 064 — Jenkins Configuration Drift Detection, Policy Validation and GitOps Governance](../064-jenkins-configuration-drift-policy-validation-gitops-governance.md).
