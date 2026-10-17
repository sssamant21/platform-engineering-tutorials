# Chapter 095 — Jenkins Enterprise SRE Operations, Security and FinOps Acceptance Capstone

**Part 19 — Enterprise Jenkins SRE Operations and FinOps (final capstone)**  
**Audience:** Jenkins platform SRE/DBRE, service owners, security, finance, incident commanders and audit.  
**Prerequisites:** Chapters 091–094, Python 3, Git, optional Jenkins staging controller and read-only monitoring/billing evidence.

## Mission and boundaries

Demonstrate enterprise operational readiness across **service ownership, SLOs/error budgets, incident management, identity/security, capacity/FinOps, change governance, backup/DR and audit**. The offline checks below validate **synthetic evidence declarations**; real acceptance requires independent verification against Jenkins, identity provider, Prometheus, cloud billing, backup restore and change records.

## 1. Operating architecture

```text
Business owners / service tiers / RACI
              |
    Jenkins platform service catalog
              |
   SLIs / SLOs / error budget policy
              |
  incidents / changes / security controls
              |
    capacity / FinOps / DR readiness
              |
     evidence + acceptance scoring
              |
       sign-off / RCA / COA
```

The Jenkins platform team owns controller availability, agents, plugins, platform credentials and recovery. Pipeline owners own build definitions, application tests and downstream deployment logic. Infra/DBRE owns supporting infrastructure under agreed RACI. Escalation must work across these boundaries.

## 2. Enterprise readiness control matrix

| Control | Acceptance evidence | Owner |
|---|---|---|
| GOV-01 | service tier, business/platform owner, on-call | service owner |
| GOV-02 | approved RACI and change policy | platform lead |
| REL-01 | SLI contract, SLO target and error budget | SRE |
| REL-02 | actionable burn alerts and incident runbook | SRE |
| OPS-01 | restore-tested backup and RTO/RPO | platform/infra |
| OPS-02 | critical synthetic CI, agents and artifacts | platform |
| SEC-01 | SSO/MFA/RBAC and access review | security |
| SEC-02 | PR trust, secret isolation and agent hardening | security |
| SEC-03 | plugin/core/Java support and provenance | platform/security |
| FIN-01 | tagged cost allocation and invoice reconciliation | finance |
| FIN-02 | rightsizing SLO/DR guardrails | platform |
| AUD-01 | audit retention, exceptions, approvals and COAs | compliance |

## 3. SLO and error budget policy

Use user-centered signals: authenticated API probe success, critical-job queue wait, agent provisioning and infrastructure-attributable job failure. Document eligible events, classification, observation windows and exclusions.

For a 30-day time-based 99.9% availability target:

```text
43,200 total minutes × 0.001 = 43.2 minutes error budget
```

For event-based SLO:

```text
SLI = good / eligible
allowed_bad = floor(eligible × (1 - target))
remaining = max(0, allowed_bad - observed_bad)
```

Do not interchange time and event budgets when traffic varies. Escalate rapid burn and review change risk; urgent security and restoration changes may proceed through approved emergency controls.

## 4. Security and operational controls

- Enforce IdP SSO/MFA and least-privilege Jenkins RBAC.
- Keep production secrets away from untrusted PR builds and privileged agents.
- Pin Jenkins LTS, supported Java and plugin versions; maintain advisory review.
- Maintain encrypted backups and **tested** restore procedures.
- Preserve one active Jenkins writer per writable home.
- Require reviewed changes, rollback, emergency access logging and evidence retention.
- Validate supply-chain provenance, artifact digests and signing where applicable.
- Maintain exception owners, expiry and compensating controls.

## 5. FinOps and capacity gates

Track controller/agent compute, storage, artifacts, network egress, observability and shared overhead. Reconcile team allocations to billing; distinguish idle agent cost from useful build minutes. Forecast growth and bursts, not just daily averages. Reject savings proposals that violate critical queue SLOs, security isolation, RTO/RPO or audit retention.

## 6. Executable offline acceptance checker

Create `evidence/readiness.json`:

```json
{
  "service_id": "jenkins-staging",
  "tier": "T2",
  "platform_owner": "platform-sre",
  "business_owner": "devex",
  "oncall_route": "platform-sre-oncall",
  "slo_target": 0.999,
  "eligible_events": 100000,
  "good_events": 99950,
  "burn_alerts_defined": true,
  "restore_test_passed": true,
  "rto_minutes": 240,
  "rpo_minutes": 60,
  "synthetic_ci_passed": true,
  "sso_mfa_enforced": true,
  "rbac_reviewed": true,
  "untrusted_pr_prod_secrets": false,
  "plugin_review_current": true,
  "cost_center": "engineering",
  "billing_reconciled": true,
  "change_approval_required": true,
  "audit_retention_defined": true,
  "risk_owner": "platform-security"
}
```

Create `scripts/acceptance.py`:

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

TRUE_KEYS = (
    "burn_alerts_defined", "restore_test_passed", "synthetic_ci_passed",
    "sso_mfa_enforced", "rbac_reviewed", "plugin_review_current",
    "billing_reconciled", "change_approval_required", "audit_retention_defined",
)
TEXT_KEYS = (
    "service_id", "platform_owner", "business_owner", "oncall_route",
    "cost_center", "risk_owner",
)

def evaluate(data):
    failures = []
    for key in TEXT_KEYS:
        if not isinstance(data.get(key), str) or not data[key].strip():
            failures.append(f"{key}: missing")
    if data.get("tier") not in ("T0", "T1", "T2", "T3"):
        failures.append("tier: invalid")
    for key in TRUE_KEYS:
        if data.get(key) is not True:
            failures.append(f"{key}: must be true")
    if data.get("untrusted_pr_prod_secrets") is not False:
        failures.append("untrusted_pr_prod_secrets: must be false")
    for key in ("rto_minutes", "rpo_minutes"):
        v = data.get(key)
        if type(v) is not int or v <= 0:
            failures.append(f"{key}: must be positive integer")
    target = data.get("slo_target")
    total = data.get("eligible_events")
    good = data.get("good_events")
    if type(target) not in (float, int) or not 0 < target < 1:
        failures.append("slo_target: invalid")
    if type(total) is not int or total <= 0 or type(good) is not int or not 0 <= good <= total:
        failures.append("eligible/good events: invalid")
    if not failures:
        bad = total - good
        allowed = int(total * (1 - target) + 1e-9)
        if bad > allowed:
            failures.append(f"SLO exhausted: bad={bad} allowed={allowed}")
    return failures

if __name__ == "__main__":
    data = json.loads(Path(sys.argv[1]).read_text())
    failures = evaluate(data)
    if failures:
        print("ACCEPTANCE FAIL", *failures, sep="\n")
        sys.exit(1)
    print("ACCEPTANCE PASS: synthetic declaration only")
```

Run:

```bash
python3 scripts/acceptance.py evidence/readiness.json
```

This script does not prove that the named controls were implemented; it tests consistency of a **declared fixture**. Production sign-off must link each declaration to trusted evidence.

## 7. Negative control test

```bash
cp evidence/readiness.json /tmp/jenkins-readiness-fail.json
python3 - <<'PY'
import json
p = "/tmp/jenkins-readiness-fail.json"
with open(p) as f:
    d = json.load(f)
d["sso_mfa_enforced"] = False
d["untrusted_pr_prod_secrets"] = True
d["billing_reconciled"] = False
with open(p, "w") as f:
    json.dump(d, f)
PY
if python3 scripts/acceptance.py /tmp/jenkins-readiness-fail.json; then
  echo "FAIL: unsafe readiness fixture accepted"; exit 1
else
  echo "PASS: unsafe readiness fixture denied"
fi
```

## 8. Jenkins read-only validation Pipeline

```groovy
pipeline {
  agent { label 'governance-validation' }
  options {
    timestamps()
    timeout(time: 10, unit: 'MINUTES')
  }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Readiness contract') {
      steps { sh 'python3 scripts/acceptance.py evidence/readiness.json' }
    }
  }
}
```

Run on pinned, trusted agents; do not grant cloud write credentials or production secrets to untrusted PR builds.

## 9. Twenty-four capstone exercises

1. Define Jenkins service boundary and dependency map.
2. Assign service tier and business impact.
3. Record business, platform and pipeline owners.
4. Approve RACI and on-call escalation.
5. Define critical user journeys and SLIs.
6. Define 30-day SLO targets and eligibility.
7. Calculate time and event error budgets.
8. Validate burn-rate alerts and routes.
9. Simulate critical queue SLO degradation.
10. Execute incident command tabletop.
11. Review change approval and emergency policy.
12. Verify backup encryption and restore evidence.
13. Verify RTO/RPO and DR owner.
14. Review SSO/MFA and administrator access.
15. Review untrusted PR/secret boundary.
16. Review agent privilege and plugin versions.
17. Review artifact provenance and audit retention.
18. Define cost centers and resource tagging.
19. Reconcile controller/agent/storage spend.
20. Forecast +25% and +50% demand.
21. Evaluate rightsizing against SLO/DR gates.
22. Execute offline readiness validator and negative test.
23. Collect evidence, risk exceptions and COAs.
24. Complete enterprise scorecard and reviewer sign-off.

## 10. Twenty-four failure scenarios

| # | Failure | Primary response |
|---|---|---|
| 01 | Missing service owner | governance block |
| 02 | On-call route broken | escalation |
| 03 | RACI ambiguous | owner review |
| 04 | SLI excludes critical failures | contract revision |
| 05 | Zero traffic reported healthy | data-quality gate |
| 06 | Error budget exhausted | change governance |
| 07 | Queue SLO breach | capacity incident |
| 08 | Agent provisioning fails | infra escalation |
| 09 | Incident has no commander | response policy |
| 10 | Backup exists but restore fails | DR incident |
| 11 | RPO/RTO unmet | recovery plan |
| 12 | Dual Jenkins writers | immediate stop |
| 13 | SSO/MFA disabled | security incident |
| 14 | Excess admin grants | RBAC review |
| 15 | Untrusted PR sees production secret | revoke/rotate |
| 16 | Privileged agent compromise | isolate |
| 17 | Unsupported plugin | vulnerability review |
| 18 | Artifact provenance missing | release block |
| 19 | Audit retention absent | compliance gap |
| 20 | Unapproved production change | audit/rollback |
| 21 | Cost-center tags missing | FinOps remediation |
| 22 | Idle agents overspend | capacity review |
| 23 | Rightsizing breaks SLO | rollback |
| 24 | Acceptance evidence incomplete | fail sign-off |

## 11. Eight production runbooks

### A. Ownership and on-call failure
Identify impacted service tier, invoke fallback paging, assign accountable owner and test route.

### B. SLO burn or queue degradation
Validate telemetry, declare incident, identify controller/agent bottleneck, mitigate and preserve error-budget evidence.

### C. Controller outage and DR
Preserve single-writer safety, verify storage and backups, restore compatible controller and run synthetic CI acceptance.

### D. Credential or PR trust breach
Isolate builds, revoke and rotate secrets, preserve logs/artifacts and coordinate security incident response.

### E. Plugin or supply-chain compromise
Block promotions, assess advisories and provenance, stage compatible fixes and verify build integrity.

### F. FinOps cost anomaly
Reconcile invoice, tags, agent idle time, artifacts and egress; remediate without SLO/DR regression.

### G. Change governance failure
Freeze high-risk work, preserve approvals/logs, review blast radius and run controlled rollback.

### H. Enterprise acceptance failure
Record failed mandatory gate, assign COA and owner, collect new evidence and repeat failed tests before sign-off.

## 12. 100-point acceptance scorecard

| Domain | Points |
|---|---:|
| Ownership, RACI, on-call and service tier | 15 |
| SLIs, SLOs, error budgets and incident response | 20 |
| Backup, recovery and operational change control | 15 |
| Identity, secrets, agents and supply-chain security | 20 |
| Capacity, cost allocation and FinOps governance | 15 |
| Audit evidence, runbooks and acceptance sign-off | 15 |
| **Total** | **100** |

Suggested pass **85/100**, plus mandatory gates: named owner and working escalation, validated SLO, tested restore, SSO/MFA, no production secrets in untrusted PRs, reviewed privileged access, billing reconciliation and approved change policy. **A passing synthetic fixture does not satisfy these gates by itself.**

## 13. Evidence template

```text
UTC / service tier / environment:
Business/platform/pipeline owners:
RACI and on-call route test:
SLI/SLO and error-budget calculations:
Burn alert and incident tabletop:
Backup restore and RTO/RPO:
SSO/MFA/RBAC/PR secret boundaries:
Plugin/Java/core/provenance:
Controller/agent/storage/network cost:
Capacity forecast and SLO guardrails:
Change approvals/audit retention:
24 exercises / 24 failure scenarios:
Score / mandatory gates / RCA / COA / reviewer:
```

**Companion:** [Chapter 095 acceptance lab](labs/095-jenkins-enterprise-sre-operations-security-finops-acceptance-capstone-check.md).  
**Part 19 complete:** Chapters 091–095.  
**Next:** Chapter 096 — Jenkins Final Enterprise Capstone Architecture and Production Readiness Planning.
