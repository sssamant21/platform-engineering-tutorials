# Chapter 095 — Hands-on Acceptance Lab: Enterprise Jenkins SRE, Security and FinOps

**Scope:** Offline Python evidence validation and operational tabletop. Optional read-only Jenkins staging review. No production changes.

## 24 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Define service boundary | Diagram |
| 02 | Assign tier and business impact | Catalog |
| 03 | Assign platform/business/pipeline owners | RACI |
| 04 | Test on-call route in approved environment | Record |
| 05 | Define critical user journeys | SLI contract |
| 06 | Define SLO targets/window | Policy |
| 07 | Calculate time/event budgets | Math |
| 08 | Review burn-rate alert | Rule |
| 09 | Simulate queue degradation | Incident |
| 10 | Run incident tabletop | Timeline |
| 11 | Review change approval | Ticket |
| 12 | Review restore-test evidence | DR |
| 13 | Verify RTO/RPO plan | Contract |
| 14 | Review SSO/MFA | Evidence |
| 15 | Review PR/secret isolation | Matrix |
| 16 | Review agent/plugin controls | Inventory |
| 17 | Review provenance and retention | Checklist |
| 18 | Map cost centers | Tags |
| 19 | Reconcile shared costs | Worksheet |
| 20 | Forecast growth scenarios | Capacity |
| 21 | Evaluate SLO-aware rightsizing | Decision |
| 22 | Run acceptance validator | Result |
| 23 | Run unsafe fixture negative test | Denial |
| 24 | Score and sign off | Acceptance |

## 24 failure drills

1. Missing owner.
2. Broken on-call route.
3. Ambiguous RACI.
4. Incomplete SLI eligibility.
5. Zero traffic marked healthy.
6. Error budget exhausted.
7. Queue SLO breach.
8. Agent provisioning failure.
9. Missing incident commander.
10. Failed restore.
11. RTO/RPO miss.
12. Dual controller writer.
13. SSO/MFA disabled.
14. Admin permission creep.
15. PR secret exposure.
16. Privileged agent compromise.
17. Unsupported plugin.
18. Missing artifact provenance.
19. Missing audit retention.
20. Unapproved change.
21. Missing cost center.
22. Idle agent cost spike.
23. Rightsizing SLO regression.
24. Missing sign-off evidence.

## Executable acceptance validation

Use `evidence/readiness.json` and `scripts/acceptance.py` from the chapter:

```bash
python3 scripts/acceptance.py evidence/readiness.json
cp evidence/readiness.json /tmp/jenkins-readiness-unsafe.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-readiness-unsafe.json"
with open(p) as f:
    d = json.load(f)
d["sso_mfa_enforced"] = False
d["untrusted_pr_prod_secrets"] = True
d["billing_reconciled"] = False
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/acceptance.py /tmp/jenkins-readiness-unsafe.json; then
  echo "FAIL: unsafe declaration allowed"; exit 1
else
  echo "PASS: unsafe declaration denied"
fi
```

The test checks fixture consistency only. Real controls require authoritative external evidence.

## Error budget exercise

```python
total = 100000
good = 99950
target = 0.999
allowed = int(total * (1 - target) + 1e-9)
bad = total - good
print({"bad": bad, "allowed": allowed, "remaining": max(0, allowed - bad)})
```

Expected: 50 bad, 100 allowed, 50 remaining.

## Incident and FinOps tabletop

A production release pipeline is delayed by 40 minutes, agent provisioning fails intermittently and spot costs rise during emergency scaling. Identify incident command, SLO impact, escalation, safe mitigation, cost attribution, rollback, communications and follow-up COAs.

## 100-point scorecard

| Domain | Maximum |
|---|---:|
| Ownership/RACI/on-call | 15 |
| SLOs/error budgets/incident response | 20 |
| DR/change governance | 15 |
| Security/supply chain | 20 |
| Capacity/FinOps | 15 |
| Evidence/runbooks/sign-off | 15 |
| **Total** | **100** |

## Evidence worksheet

```text
UTC / lab owner:
Service tier and RACI:
On-call test:
SLO/burn calculations:
Incident tabletop:
Restore/RTO/RPO:
SSO/MFA/RBAC/secrets:
Plugins/agents/provenance:
Billing allocation/capacity:
Validator allow/deny:
24 drills:
Score / mandatory gates / RCA / COA / reviewer:
```

## Acceptance

- [ ] 24 exercises attempted with evidence.
- [ ] 24 failure drills completed or explicitly blocked.
- [ ] Named owners and on-call route documented.
- [ ] SLO and budget calculations verified.
- [ ] Incident tabletop and DR review completed.
- [ ] Identity, secrets and supply-chain controls reviewed.
- [ ] Billing reconciliation and capacity forecast reviewed.
- [ ] Synthetic validator allows safe fixture and denies unsafe fixture.
- [ ] Mandatory production gates independently evidenced.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 095 — Jenkins Enterprise SRE Operations, Security and FinOps Acceptance Capstone](../095-jenkins-enterprise-sre-operations-security-finops-acceptance-capstone.md).
