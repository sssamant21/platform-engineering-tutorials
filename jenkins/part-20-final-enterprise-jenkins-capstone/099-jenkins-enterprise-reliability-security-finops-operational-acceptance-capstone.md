# Chapter 099 — Jenkins Enterprise Reliability, Security and FinOps Operational Acceptance Capstone

**Part 20 — Final Enterprise Jenkins Capstone**  
**Audience:** Jenkins SRE/DBRE, platform owners, security, FinOps, audit and release managers.  
**Prerequisites:** Chapters 091–098; Python 3; optional read-only staging dashboards and billing evidence.

## Mission

Run a unified **enterprise operational acceptance review** of Jenkins: ownership, SLOs, incidents, disaster recovery, security, compliance, capacity, cost governance and continuous improvement. Produce measurable, auditable go/no-go evidence and remediation plans.

**Safety:** The included executable tests validate synthetic evidence. They do not contact production Jenkins, IdP, cloud billing or backup systems. Real sign-off requires independent evidence and authorized reviewers.

## 1. Operational acceptance architecture

```text
Service catalog + RACI + on-call
                |
       SLO/error-budget policy
                |
 Controller/agent observability + incidents
                |
 Security posture + vulnerability register
                |
 Capacity forecasts + invoice reconciliation
                |
 Restore tests + rollback/change records
                |
 Evidence store + reviewer attestations
                |
 GO / CONDITIONAL NO-GO / NO-GO + COA
```

Do not grant a conditional GO for a failed mandatory safety control; exceptions require formally approved, time-bound risk treatment and cannot bypass critical secret isolation or data-integrity safeguards.

## 2. Control matrix

| Control | Acceptance evidence | Reviewer |
|---|---|---|
| GOV-01 | owner, tier, RACI, on-call route | service owner |
| REL-01 | SLO definition, eligible events, burn alerts | SRE |
| REL-02 | incident response and escalation drill | SRE |
| DR-01 | encrypted backup, restore and RTO/RPO | infra |
| SEC-01 | SSO/MFA/RBAC access review | security |
| SEC-02 | untrusted PR secret boundary and agent isolation | security |
| SEC-03 | Jenkins core/Java/plugins advisory inventory | platform |
| SUP-01 | SBOM/provenance and artifact digest | DevSecOps |
| FIN-01 | controller/agent/storage/egress cost allocation | FinOps |
| FIN-02 | demand forecast, queue SLO and optimization rollback | SRE |
| CHG-01 | protected deployment, change approval and rollback | change owner |
| AUD-01 | evidence retention and exception expiry | audit |

## 3. Reliability and error-budget policy

Define business-facing SLI events and distinguish platform-attributable CI failures from application-test failures. For a 99.9% event-based SLO over 100,000 eligible events, allowed bad events = 100. Review short/long burn-rate alerts with a low-traffic data-quality guard; do not treat missing telemetry as health.

## 4. Security and supply-chain gates

- SSO/MFA, least-privilege RBAC, periodic access review and audited break-glass.
- Untrusted PR jobs never receive production credentials.
- Controller executors zero; agent trust tiers and network policies.
- Supported Jenkins LTS/Java/plugins with advisories and upgrade plan.
- Secrets rotation, audit log retention, encrypted backup and isolated restore.
- Artifact digest, SBOM/provenance and promotion approval.
- Time-bound exceptions with owners, compensating controls and expiration.

## 5. Capacity and FinOps gates

Capture controller/agent compute, persistent storage, artifacts, network egress, monitoring and shared overhead. Reconcile allocations to invoice; compare cost per successful comparable build, queue p95, agent provisioning p95, utilization and burst forecasts. Approve rightsizing only with SLO, DR and security rollback gates.

## 6. Executable offline acceptance scorecard

Save `evidence/operations.json`:

```json
{
  "service": "jenkins-staging",
  "environment": "staging",
  "service_owner": "platform-sre",
  "security_owner": "platform-security",
  "finops_owner": "cloud-finops",
  "oncall_route": "platform-oncall",
  "slo_target": 0.999,
  "eligible_events": 100000,
  "bad_events": 50,
  "burn_alerts_reviewed": true,
  "incident_drill_reviewed": true,
  "restore_tested": true,
  "single_writer_verified": true,
  "sso_mfa_enforced": true,
  "rbac_reviewed": true,
  "untrusted_pr_prod_secrets": false,
  "plugin_advisories_reviewed": true,
  "artifact_provenance_verified": true,
  "billing_reconciled": true,
  "capacity_forecast_reviewed": true,
  "change_approved": true,
  "rollback_tested": true,
  "audit_retention_defined": true
}
```

Save `scripts/operational_acceptance.py`:

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

TRUE_KEYS = (
    "burn_alerts_reviewed", "incident_drill_reviewed", "restore_tested",
    "single_writer_verified", "sso_mfa_enforced", "rbac_reviewed",
    "plugin_advisories_reviewed", "artifact_provenance_verified",
    "billing_reconciled", "capacity_forecast_reviewed",
    "change_approved", "rollback_tested", "audit_retention_defined",
)
TEXT_KEYS = ("service", "service_owner", "security_owner", "finops_owner", "oncall_route")

def evaluate(data):
    errors = []
    if data.get("environment") != "staging":
        errors.append("environment must be staging")
    for key in TEXT_KEYS:
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"{key} missing")
    for key in TRUE_KEYS:
        if data.get(key) is not True:
            errors.append(f"{key} must be true")
    if data.get("untrusted_pr_prod_secrets") is not False:
        errors.append("untrusted_pr_prod_secrets must be false")
    target = data.get("slo_target")
    eligible = data.get("eligible_events")
    bad = data.get("bad_events")
    if type(target) not in (float, int) or not 0 < target < 1:
        errors.append("invalid slo_target")
    if type(eligible) is not int or eligible <= 0:
        errors.append("eligible_events must be positive integer")
    if type(bad) is not int or bad < 0:
        errors.append("bad_events must be nonnegative integer")
    if not errors:
        allowed = int(eligible * (1 - target) + 1e-9)
        if bad > eligible or bad > allowed:
            errors.append(f"SLO error budget exhausted: bad={bad} allowed={allowed}")
    return errors

if __name__ == "__main__":
    data = json.loads(Path(sys.argv[1]).read_text())
    errors = evaluate(data)
    if errors:
        print("OPERATIONAL NO-GO", *errors, sep="\n")
        sys.exit(1)
    print("OPERATIONAL FIXTURE PASS: real evidence still required")
```

```bash
python3 scripts/operational_acceptance.py evidence/operations.json
```

## 7. Automated unit tests

Save `tests/test_operations.py`:

```python
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from operational_acceptance import evaluate

class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "evidence/operations.json").read_text())

    def test_valid(self):
        self.assertEqual(evaluate(self.data), [])

    def test_budget_exhaustion(self):
        self.data["bad_events"] = 200
        self.assertTrue(evaluate(self.data))

    def test_pr_secrets(self):
        self.data["untrusted_pr_prod_secrets"] = True
        self.assertTrue(evaluate(self.data))

    def test_missing_billing(self):
        self.data["billing_reconciled"] = False
        self.assertTrue(evaluate(self.data))

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest discover -s tests -v
```

## 8. Negative test

```bash
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

## 9. Twenty-four operational acceptance labs

1. Define service boundary, tier and business owner.
2. Review RACI and escalation.
3. Verify on-call route.
4. Define SLIs and eligible events.
5. Calculate 30-day error budget.
6. Review burn alerts and missing-data policy.
7. Conduct incident tabletop.
8. Review controller/agent observability.
9. Review backup and encryption.
10. Review isolated restore RTO/RPO evidence.
11. Verify single-writer fencing.
12. Review SSO/MFA and RBAC.
13. Review PR secret isolation.
14. Review plugin/Java/core advisories.
15. Review artifact provenance and SBOM.
16. Review change approval and rollback.
17. Review cost center tagging.
18. Reconcile cloud billing and shared costs.
19. Review queue/agent capacity forecast.
20. Review SLO-aware rightsizing decision.
21. Create synthetic operations fixture.
22. Run acceptance validator and unit tests.
23. Execute unsafe negative test.
24. Complete reviewer scorecard, RCA and COA.

## 10. Twenty-four failure scenarios

| # | Scenario | Gate |
|---|---|---|
| 01 | Missing owner | governance |
| 02 | Broken on-call route | incident |
| 03 | Invalid SLI definition | reliability |
| 04 | Missing telemetry | data quality |
| 05 | Error budget exhausted | release |
| 06 | Burn alert not routed | monitoring |
| 07 | Incident response untested | readiness |
| 08 | Controller queue regression | capacity |
| 09 | Agent provisioning failure | operations |
| 10 | Backup unencrypted | security |
| 11 | Restore not tested | DR |
| 12 | Dual active writers | data integrity |
| 13 | SSO/MFA disabled | identity |
| 14 | RBAC overprivileged | identity |
| 15 | Untrusted PR sees secrets | security |
| 16 | Unsupported plugin | vulnerability |
| 17 | Artifact provenance missing | supply chain |
| 18 | Unapproved change | governance |
| 19 | Rollback fails | recovery |
| 20 | Missing cost tags | FinOps |
| 21 | Billing reconciliation gap | finance |
| 22 | Forecast misses burst | capacity |
| 23 | Rightsizing breaks SLO | reliability |
| 24 | Audit evidence expired | compliance |

## 11. Eight production runbooks

### A. SLO and queue incident
Validate data quality, classify failures, page owner, mitigate controller/agent bottleneck and preserve budget evidence.

### B. Controller/agent outage
Confirm blast radius, protect single writer, recover capacity and run critical synthetic CI.

### C. DR acceptance failure
Stop cutover, inspect backup and key custody, repeat isolated restore, measure real RTO/RPO.

### D. Security/credential incident
Isolate jobs, revoke/rotate credentials, review IdP/cloud audit, invoke security response.

### E. Plugin or artifact compromise
Block promotion, review advisories, quarantine artifacts, restore trusted toolchain.

### F. Cost anomaly
Reconcile invoice, tags, idle agents, artifacts, egress and shared overhead; assign COA.

### G. Change/rollback failure
Stop deployment, invoke incident command, revert approved change and verify SLO/DR gates.

### H. Operational acceptance no-go
Document failed mandatory gate, assign owner/due date, preserve evidence and retest before sign-off.

## 12. 100-point scorecard

| Domain | Points |
|---|---:|
| Service ownership, RACI and incident response | 15 |
| SLOs, error budgets and observability | 20 |
| Backup, DR and operational change | 15 |
| Identity, secrets, plugins and supply-chain security | 20 |
| Capacity, cost allocation and FinOps | 20 |
| Evidence, tests and reviewer sign-off | 10 |
| **Total** | **100** |

Suggested pass **85/100** plus mandatory gates: named owners/on-call, approved SLO, tested restore, single-writer integrity, SSO/MFA, PR secret isolation, critical advisory review, billing reconciliation, change/rollback and audit evidence. A synthetic fixture alone is not enough.

## 13. Evidence template

```text
UTC / service tier / environment:
Owners/RACI/on-call:
SLI/SLO/error-budget:
Alert/incident drill:
Controller/agent telemetry:
Backup/restore/RTO/RPO/fencing:
SSO/MFA/RBAC/secret isolation:
Core/Java/plugins/SBOM/provenance:
Cost allocation/invoice reconciliation:
Capacity/rightsizing/SLO:
Change/rollback/audit retention:
24 labs / 24 failures:
Score / mandatory gates / RCA / COA / reviewer:
```

**Companion:** [Chapter 099 hands-on lab](labs/099-jenkins-enterprise-reliability-security-finops-operational-acceptance-capstone-check.md).  
**Next:** Chapter 100 — Jenkins Enterprise SRE/DevOps Final Assessment and Production Readiness Certification.
