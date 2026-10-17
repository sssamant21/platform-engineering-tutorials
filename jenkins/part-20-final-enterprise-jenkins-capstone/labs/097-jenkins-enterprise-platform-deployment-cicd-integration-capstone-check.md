# Chapter 097 — Hands-on Lab: Enterprise Jenkins Deployment and CI/CD Integration

**Safety:** Offline Python release-contract tests plus staging design/tabletop. No production applies, secrets or destructive commands.

## 24 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Define deployment boundary | Diagram |
| 02 | Create CODEOWNERS/repo layout | Review |
| 03 | Pin Terraform versions | Lockfile |
| 04 | Review remote state | ADR |
| 05 | Review plan and approval | Ticket |
| 06 | Review Ansible idempotency | Check |
| 07 | Review Helm staging settings | Values |
| 08 | Review JCasC schema | Validation |
| 09 | Verify controller zero executors | Gate |
| 10 | Design isolated agents | Pod policy |
| 11 | Review service accounts | IAM |
| 12 | Verify webhook trust | Checklist |
| 13 | Review PR/release isolation | Matrix |
| 14 | Review build/test/scans | Pipeline |
| 15 | Define artifact digest/SBOM | Contract |
| 16 | Define staging smoke | Plan |
| 17 | Define SLO gates | Dashboard |
| 18 | Define release approvals | Policy |
| 19 | Define rollback | Runbook |
| 20 | Create release JSON | Fixture |
| 21 | Run validator and tests | Results |
| 22 | Run negative fixture | Denial |
| 23 | Execute release tabletop | Timeline |
| 24 | Score and sign off | Assessment |

## 12 failure drills

1. Terraform state lock conflict.
2. Wrong cloud account.
3. Unreviewed destructive plan.
4. JCasC incompatibility.
5. Controller executors enabled.
6. Kubernetes agent Pending.
7. Privileged agent.
8. Untrusted PR deployment token.
9. Missing SBOM.
10. Artifact digest mismatch.
11. Staging SLO regression.
12. Missing approval/rollback.

## Executable local tests

Use `policy/release.json`, `scripts/validate_release.py` and `tests/test_release.py` from the chapter:

```bash
python3 scripts/validate_release.py policy/release.json
python3 -m unittest discover -s tests -v
cp policy/release.json /tmp/jenkins-release-unsafe.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-release-unsafe.json"
with open(p) as f:
    d = json.load(f)
d["untrusted_pr_deploy_secrets"] = True
d["terraform_plan_reviewed"] = False
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/validate_release.py /tmp/jenkins-release-unsafe.json; then
  echo "FAIL: unsafe release accepted"; exit 1
else
  echo "PASS: unsafe release denied"
fi
```

## Deployment tabletop

A protected release branch triggers a Terraform plan that includes an unexpected IAM privilege expansion; meanwhile a Kubernetes agent pool has rising queue latency. Halt deployment, identify plan owner, review identity blast radius, validate SLO and rollback criteria, and document release decision.

## Evidence worksheet

```text
UTC / lab owner:
IaC state and plan review:
JCasC/plugin/agent validation:
SCM and credential isolation:
Artifact digest/SBOM:
Staging smoke and SLO:
Approval/rollback:
Validator and tests:
12 drills:
Score / mandatory gates / RCA / COA / reviewer:
```

## Acceptance

- [ ] 24 exercises attempted with evidence.
- [ ] 12 failure drills completed or explicitly blocked.
- [ ] IaC ownership and state locking documented.
- [ ] Controller/agent/JCasC security reviewed.
- [ ] PR and release identity isolation defined.
- [ ] Artifact provenance and staging smoke specified.
- [ ] Local validator and unit tests executed.
- [ ] Unsafe fixture denied.
- [ ] Rollback and approval gates reviewed.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 097 — Jenkins Enterprise Platform Deployment and CI/CD Integration Capstone](../097-jenkins-enterprise-platform-deployment-cicd-integration-capstone.md).
