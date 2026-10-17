# Chapter 096 — Hands-on Lab: Jenkins Enterprise Architecture and Readiness

**Safety:** Offline Python and architecture review; optional read-only staging. No production deployment or secrets.

## 24 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Define service and impact | Catalog |
| 02 | Assign tier and owners | RACI |
| 03 | Draw trust boundaries | Diagram |
| 04 | Enforce single-writer design | ADR |
| 05 | Design agent pools | Diagram |
| 06 | Design SCM ingress | ADR |
| 07 | Design SSO/MFA/RBAC | Matrix |
| 08 | Design secret isolation | Policy |
| 09 | Define JCasC/plugin compatibility | Matrix |
| 10 | Define artifact provenance | Contract |
| 11 | Define IaC ownership | Matrix |
| 12 | Define remote-state safety | ADR |
| 13 | Define SLIs | Contract |
| 14 | Calculate SLO budget | Worksheet |
| 15 | Estimate queue capacity | Forecast |
| 16 | Estimate costs | FinOps |
| 17 | Define backup scope | Inventory |
| 18 | Define RTO/RPO | DR |
| 19 | Define rollback | Runbook |
| 20 | Define observability/on-call | Map |
| 21 | Write ADRs and threat model | Review |
| 22 | Run readiness gate | Result |
| 23 | Run negative test | Denial |
| 24 | Score go/no-go | Sign-off |

## 12 failure drills

1. Dual controller writer.
2. Controller executes untrusted jobs.
3. Anonymous admin.
4. MFA disabled.
5. Production secrets in PR.
6. Privileged agent.
7. Unsupported plugin.
8. Missing state locking.
9. Queue SLO breach.
10. Failed restore.
11. Unattributed cost.
12. Missing architecture sign-off.

## Executable acceptance test

Use `architecture/readiness.json` and `scripts/readiness_gate.py` from the main chapter:

```bash
python3 scripts/readiness_gate.py architecture/readiness.json
cp architecture/readiness.json /tmp/jenkins-architecture-unsafe.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-architecture-unsafe.json"
with open(p) as f:
    d = json.load(f)
d["controller_writers"] = 2
d["untrusted_pr_prod_secrets"] = True
d["restore_tested"] = False
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/readiness_gate.py /tmp/jenkins-architecture-unsafe.json; then
  echo "FAIL: unsafe architecture accepted"; exit 1
else
  echo "PASS: unsafe architecture denied"
fi
```

## Architecture tabletop

An enterprise Jenkins migration proposes two active controllers using the same persistent volume to avoid downtime. Reject shared writable home, propose isolated controllers or a tested failover design, specify DNS/routing and recovery, and record ADR and mandatory no-go gate.

## 100-point scorecard

| Domain | Maximum |
|---|---:|
| Architecture/ADRs/ownership | 20 |
| Controller/agents/IaC | 20 |
| Security/supply chain | 20 |
| SLOs/capacity/FinOps | 15 |
| Backup/DR/rollback | 15 |
| Evidence/review | 10 |
| **Total** | **100** |

## Evidence worksheet

```text
UTC / lab owner:
Architecture and ADRs:
Service tier/RACI:
Controller/agent isolation:
Security/secret trust boundaries:
SLOs and capacity:
Cost forecast:
DR and rollback:
Positive/negative policy tests:
12 failure drills:
Score / mandatory gates / RCA / COA / reviewer:
```

## Acceptance

- [ ] 24 exercises attempted with evidence.
- [ ] 12 failure drills completed or explicitly blocked.
- [ ] Architecture diagram and ADRs reviewed.
- [ ] Single-writer and secret isolation demonstrated in design.
- [ ] SLO/capacity/cost documented.
- [ ] Backup/restore and rollback reviewed.
- [ ] Readiness fixture passes positive test.
- [ ] Unsafe fixture denied.
- [ ] Mandatory gates independently evidenced.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 096 — Jenkins Final Enterprise Capstone Architecture and Production Readiness Planning](../096-jenkins-final-enterprise-capstone-architecture-production-readiness-planning.md).
