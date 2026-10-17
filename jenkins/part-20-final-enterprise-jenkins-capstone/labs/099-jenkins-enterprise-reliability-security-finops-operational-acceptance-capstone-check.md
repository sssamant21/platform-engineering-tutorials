# Chapter 099 — Hands-on Lab: Jenkins Reliability, Security and FinOps Acceptance

**Safety:** Offline synthetic validation and read-only staging review. No production changes or destructive operations.

## 24 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Define service boundary | Catalog |
| 02 | Review RACI | Matrix |
| 03 | Review on-call route | Record |
| 04 | Define SLIs | Contract |
| 05 | Calculate budget | Worksheet |
| 06 | Review burn alerts | Rule |
| 07 | Run incident tabletop | Timeline |
| 08 | Review controller/agent metrics | Dashboard |
| 09 | Review backup encryption | Evidence |
| 10 | Review restore RTO/RPO | DR |
| 11 | Review single-writer fencing | Gate |
| 12 | Review SSO/MFA/RBAC | Matrix |
| 13 | Review PR secret isolation | Policy |
| 14 | Review plugin advisories | Inventory |
| 15 | Review artifact provenance | Evidence |
| 16 | Review change/rollback | Ticket |
| 17 | Review cost tags | Mapping |
| 18 | Reconcile billing | Worksheet |
| 19 | Review capacity forecast | Forecast |
| 20 | Review rightsizing guardrails | Decision |
| 21 | Create operations JSON | Fixture |
| 22 | Run validator/tests | Results |
| 23 | Run unsafe negative fixture | Denial |
| 24 | Score and sign off | Assessment |

## 12 failure drills

1. Missing service owner.
2. Missing burn alert.
3. Exhausted error budget.
4. Failed restore.
5. Dual controller writers.
6. SSO/MFA disabled.
7. Untrusted PR secret exposure.
8. Unsupported plugin.
9. Missing provenance.
10. Unapproved change.
11. Billing reconciliation failure.
12. Rightsizing SLO regression.

## Executable acceptance tests

Use `evidence/operations.json`, `scripts/operational_acceptance.py` and `tests/test_operations.py` from the chapter:

```bash
python3 scripts/operational_acceptance.py evidence/operations.json
python3 -m unittest discover -s tests -v
cp evidence/operations.json /tmp/jenkins-ops-unsafe.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-ops-unsafe.json"
with open(p) as f:
    d = json.load(f)
d["untrusted_pr_prod_secrets"] = True
d["restore_tested"] = False
d["billing_reconciled"] = False
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/operational_acceptance.py /tmp/jenkins-ops-unsafe.json; then
  echo "FAIL: unsafe acceptance allowed"; exit 1
else
  echo "PASS: unsafe acceptance denied"
fi
```

## Enterprise tabletop

Jenkins queue p95 breaches the critical release SLO, an agent autoscaler change increases cloud costs, and a plugin advisory is issued. Coordinate SRE, security, finance and change owners; decide freeze/rollback, incident escalation, evidence retention, cost reconciliation and follow-up remediation.

## Evidence worksheet

```text
UTC / lab owner:
Service tier/RACI:
SLO and error budget:
Incident and DR:
Security/provenance:
Billing and capacity:
Change/rollback:
Validator and tests:
12 drills:
Score / mandatory gates / RCA / COA / reviewer:
```

## Acceptance

- [ ] 24 exercises attempted with evidence.
- [ ] 12 failure drills completed or explicitly blocked.
- [ ] SLO/incident/DR evidence reviewed.
- [ ] Identity and PR trust controls reviewed.
- [ ] Core/plugin/provenance controls reviewed.
- [ ] Billing reconciliation and capacity reviewed.
- [ ] Local validator and unit tests executed.
- [ ] Unsafe fixture denied.
- [ ] Real operational gates independently verified.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 099 — Jenkins Enterprise Reliability, Security and FinOps Operational Acceptance Capstone](../099-jenkins-enterprise-reliability-security-finops-operational-acceptance-capstone.md).
