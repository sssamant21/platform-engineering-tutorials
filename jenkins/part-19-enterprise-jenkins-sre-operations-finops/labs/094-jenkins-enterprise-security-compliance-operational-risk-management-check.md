# Chapter 094 — Hands-on Lab: Jenkins Enterprise Security, Compliance and Risk

**Safety:** Offline policy-fixture lab; optional read-only Jenkins staging security review. Do not expose secrets or modify production RBAC.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Draw Jenkins threat boundaries | Diagram |
| 02 | Inventory controller and plugins | Matrix |
| 03 | Review SSO/MFA policy | Checklist |
| 04 | Review Jenkins RBAC | Matrix |
| 05 | Inventory service accounts | Register |
| 06 | Review controller executors | Setting |
| 07 | Review agent privilege | Pod policy |
| 08 | Check controller TLS design | Review |
| 09 | Review external secret ownership | Matrix |
| 10 | Review untrusted PR separation | Design |
| 11 | Review SBOM/provenance controls | Checklist |
| 12 | Review backup encryption | Evidence |
| 13 | Review audit retention | Policy |
| 14 | Define vulnerability risk scoring | Matrix |
| 15 | Define exception expiry workflow | Register |
| 16 | Create security policy JSON | Fixture |
| 17 | Run Python security gate | Result |
| 18 | Run unsafe fixture negative test | Denial |
| 19 | Execute credential incident tabletop | Runbook |
| 20 | Score 100-point acceptance and COA | Sign-off |

## 12 failure drills

1. Anonymous administrator access.
2. MFA disabled.
3. Unreviewed service account.
4. Controller build executors enabled.
5. Production secrets exposed to PR.
6. Privileged agents default.
7. Artifact provenance missing.
8. Unsupported plugin.
9. Unencrypted backup.
10. Expired risk exception.
11. Audit retention undefined.
12. CI credential compromise.

## Executable offline policy tests

Use `policy/jenkins-security.json` and `scripts/security_gate.py` from the main chapter.

```bash
python3 scripts/security_gate.py policy/jenkins-security.json
cp policy/jenkins-security.json /tmp/jenkins-security-unsafe.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-security-unsafe.json"
with open(p) as f:
    d = json.load(f)
d["controller"]["anonymous_admin"] = True
d["pipeline"]["untrusted_pr_has_prod_secrets"] = True
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/security_gate.py /tmp/jenkins-security-unsafe.json; then
  echo "FAIL: unsafe fixture allowed"; exit 1
else
  echo "PASS: unsafe fixture denied"
fi
```

## Incident tabletop

An untrusted PR job prints a production cloud token. Record containment, affected jobs and artifacts, rotation/revocation, cloud audit review, incident communications, policy fix and follow-up tests. Do not print real tokens in the exercise.

## Evidence worksheet

```text
UTC / lab owner:
SSO/MFA and RBAC review:
Jenkins core/plugins/agents:
Secret-manager and credential scopes:
PR trust and provenance:
Backup and audit retention:
Valid/invalid fixture results:
12 drills and tabletop:
Score / RCA / COA / reviewer:
```

## Acceptance

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Threat boundaries and owners documented.
- [ ] Identity, agent and plugin controls reviewed.
- [ ] Secret isolation and artifact provenance evaluated.
- [ ] Policy validator accepts safe fixture.
- [ ] Policy validator rejects unsafe fixture.
- [ ] Risk exception and audit controls reviewed.
- [ ] Incident tabletop completed.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 094 — Jenkins Enterprise Security, Compliance and Operational Risk Management](../094-jenkins-enterprise-security-compliance-operational-risk-management.md).
