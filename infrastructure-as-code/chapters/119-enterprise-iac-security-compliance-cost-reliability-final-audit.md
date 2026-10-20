# Chapter 119 — Enterprise IaC Security, Compliance, Cost and Reliability Final Audit

**Part 24 — Final Enterprise Capstone · Chapter 119/120 · Enterprise SRE/DBRE**

> **Verification boundary:** This chapter publishes an audit methodology and offline synthetic gate. It does not prove compliance, execute security scans, measure real cloud costs or validate disaster recovery. Native evidence and independent security/SRE/DBRE acceptance remain mandatory.

## 1. Learning objectives
Perform an integrated enterprise audit across security, compliance, FinOps, SLOs, Terraform/OpenTofu, CI/CD, Kubernetes/GitOps and database reliability. Identify control gaps, assign owners, verify evidence provenance, manage time-bound exceptions and issue an evidence-based GO/NO-GO decision.

Prerequisites: Chapters 001–118, cloud IAM, policy-as-code, observability, change management, cost management, backup/PITR and recovery testing.

## 2. Audit reference architecture
```text
Cloud IAM + audit logs + Terraform/OpenTofu state
                      |
CI/CD provenance + module SBOM + policy results
                      |
Kubernetes/GitOps + SLOs + capacity + cost tags
                      |
Database backup/PITR + restore + retention evidence
                      |
       Evidence collection and provenance checks
                      |
    Control mapping -> findings -> remediation owner
                      |
      Independent security/SRE/DBRE assessment
                      |
              GO / NO-GO / exception
```

Never equate a passed automated gate with regulatory certification. Map controls to the organization's actual contractual and regulatory obligations; do not claim SOC 2, ISO 27001, PCI DSS or HIPAA compliance solely from a training exercise.

## 3. Security audit domains

| Control | Evidence | Failure action |
|---|---|---|
| Tenant isolation | native deny tests, IAM scopes | NO-GO |
| Least privilege | role policy, OIDC claims, expiry | revoke/restrict |
| State security | encryption, locks, snapshots, access logs | halt state writes |
| Secrets | secret scans, key rotation, workload identity | rotate/quarantine |
| Supply chain | signed provenance, pinned modules/images | block promotion |
| Policy-as-code | CI and cloud admission deny tests | fail closed |
| Change governance | signed plans, approval binding, separation | invalidate change |
| Audit integrity | immutable logs, retention and timestamps | preserve evidence |

## 4. Compliance and evidence governance
Maintain an audit evidence register with control ID, scope, tenant, system owner, source, timestamp, retention, collector identity, immutable digest, reviewer and expiry. Record policy version, change ID and linked incident. Validate evidence provenance and freshness independently. Treat missing or unverifiable evidence as a control failure.

**Exceptions:** every accepted high finding requires a named owner, risk rationale, compensating control, approval, expiry and remediation deadline. Critical findings cannot be accepted by the offline gate.

## 5. FinOps and capacity audit
Audit tags/labels, resource ownership, chargeback/showback, cloud budgets, idle infrastructure, egress, Kubernetes requests/limits, storage growth, reservation commitments and disaster-recovery duplication. Validate that cost optimization does not weaken HA, RPO/RTO, backup retention, SLOs or security controls.

Measure utilization trends, peak headroom, quota exposure and unit costs per environment or service. Forecasts must be calibrated against actual demand, not assumed accurate.

## 6. Reliability and DBRE audit
Verify SLO definitions, alert coverage, error budgets, incident response, deployment rollback, multi-zone resilience and real restore evidence. For PostgreSQL/MongoDB/Redis/Kafka/Elasticsearch, assess replication durability, data integrity, recovery ordering, backup/PITR coverage, retention, encryption, RPO/RTO and ownership. A successful backup job is not proof of recoverability.

## 7. Cross-cloud and platform coverage
- **AWS:** Organizations/SCPs, IAM Access Analyzer, CloudTrail, AWS Config, cost allocation tags and CloudWatch.
- **Azure:** Entra ID/RBAC, Azure Policy, Activity Logs, Cost Management and Azure Monitor.
- **GCP:** organization policies, IAM, Cloud Audit Logs, Cloud Asset Inventory, Cloud Billing and Monitoring.
- **Terraform/OpenTofu:** encrypted locked state, pinned providers, immutable plan digests, drift detection and recovery snapshots.
- **Kubernetes/GitOps:** RBAC, admission, network policy, image provenance, Git reconciliation and workload SLOs.

## 8. Lab A — Offline final audit gate

Create `infrastructure-as-code/labs/chapter-119/audit_gate.py`:

```python
"""Offline enterprise IaC audit gate. Synthetic evidence; no cloud access."""
from dataclasses import dataclass

WEIGHTS={
    "identity_and_tenant_isolation":15,
    "state_and_secrets_protection":10,
    "supply_chain_and_policy":10,
    "audit_and_compliance_evidence":15,
    "cost_allocation_and_budget":10,
    "capacity_and_slo":10,
    "recovery_drill":10,
    "change_governance":10,
    "dbre_integrity":10,
}
assert sum(WEIGHTS.values()) == 100
MANDATORY=(
    "identity_and_tenant_isolation","state_and_secrets_protection",
    "supply_chain_and_policy","audit_and_compliance_evidence",
    "recovery_drill","change_governance",
)

@dataclass(frozen=True)
class AuditEvidence:
    audit_id: str
    environment: str
    tenant: str
    authorized_tenant: str
    evidence_current: bool
    evidence_provenance_verified: bool
    identity_and_tenant_isolation: bool
    state_and_secrets_protection: bool
    supply_chain_and_policy: bool
    audit_and_compliance_evidence: bool
    cost_allocation_and_budget: bool
    capacity_and_slo: bool
    recovery_drill: bool
    change_governance: bool
    dbre_integrity: bool
    databases_in_scope: bool
    dbre_signoff: bool
    security_signoff: bool
    sre_signoff: bool
    critical_findings_open: int
    high_findings_open: int
    approved_high_exceptions: int

def assess(e: AuditEvidence):
    if not e.audit_id.strip() or not e.tenant.strip():
        raise ValueError("audit ID and tenant required")
    if e.environment not in ("dev", "stage", "prod"):
        raise ValueError("invalid environment")
    if min(e.critical_findings_open,e.high_findings_open,e.approved_high_exceptions)<0:
        raise ValueError("negative finding count")
    if e.approved_high_exceptions>e.high_findings_open:
        raise ValueError("exceptions exceed high findings")
    score=sum(weight for key,weight in WEIGHTS.items() if getattr(e,key))
    failed=[key for key in MANDATORY if not getattr(e,key)]
    if e.databases_in_scope and not e.dbre_integrity: failed.append("dbre_integrity")
    if e.tenant!=e.authorized_tenant: failed.append("tenant_scope")
    if not e.evidence_current: failed.append("evidence_freshness")
    if not e.evidence_provenance_verified: failed.append("evidence_provenance")
    if not e.security_signoff: failed.append("security_signoff")
    if not e.sre_signoff: failed.append("sre_signoff")
    if e.databases_in_scope and not e.dbre_signoff: failed.append("dbre_signoff")
    if e.critical_findings_open: failed.append("critical_findings")
    if e.high_findings_open>e.approved_high_exceptions:
        failed.append("unapproved_high_findings")
    return {"decision":"REVIEW_READY" if score>=90 and not failed else "NO_GO",
            "score":score,"failed_controls":failed}
```

The gate uses synthetic evidence flags and exception counts. It cannot verify evidence signatures or independently establish regulatory compliance. `REVIEW_READY` means eligible for human review, not production authorization.

## 9. Lab B — Negative unit tests

Create `infrastructure-as-code/labs/chapter-119/test_audit_gate.py`:

```python
import unittest
from dataclasses import replace
from audit_gate import AuditEvidence, assess

class AuditGateTests(unittest.TestCase):
    def setUp(self):
        self.e=AuditEvidence("AUD-119","prod","team-a","team-a",
            True,True,True,True,True,True,True,True,True,True,True,
            True,True,True,True,0,0,0)
    def test_baseline(self):
        self.assertEqual(assess(self.e),{"decision":"REVIEW_READY","score":100,"failed_controls":[]})
    def test_mandatory_controls(self):
        for field in ("identity_and_tenant_isolation","state_and_secrets_protection",
                      "supply_chain_and_policy","audit_and_compliance_evidence",
                      "recovery_drill","change_governance","dbre_integrity"):
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_stale_or_unverified_evidence(self):
        for field in ("evidence_current","evidence_provenance_verified"):
            self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_cross_tenant(self):
        self.assertIn("tenant_scope",assess(replace(self.e,authorized_tenant="team-b"))["failed_controls"])
    def test_critical_finding(self):
        self.assertIn("critical_findings",assess(replace(self.e,critical_findings_open=1))["failed_controls"])
    def test_unapproved_high(self):
        self.assertIn("unapproved_high_findings",assess(replace(self.e,high_findings_open=1))["failed_controls"])
    def test_approved_high_exception(self):
        self.assertEqual(assess(replace(self.e,high_findings_open=1,approved_high_exceptions=1))["decision"],"REVIEW_READY")
    def test_approvals(self):
        for field in ("dbre_signoff","security_signoff","sre_signoff"):
            self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_low_score(self):
        self.assertEqual(assess(replace(self.e,cost_allocation_and_budget=False,
                                        capacity_and_slo=False))["decision"],"NO_GO")
    def test_invalid_exception_count(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,approved_high_exceptions=2))
    def test_no_db_scope(self):
        e=replace(self.e,databases_in_scope=False,dbre_integrity=False,dbre_signoff=False)
        self.assertEqual(assess(e)["decision"],"REVIEW_READY")
if __name__=="__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-119 -p 'test_*.py' -v
```

## 10. Lab C — Multi-cloud security, compliance and FinOps audit (manual)
1. Define disposable staging audit scope, owner, tenant and evidence retention.
2. Collect IAM policy, OIDC, cloud audit, network and encryption configuration from AWS/Azure/GCP.
3. Execute cross-tenant negative access tests with isolated staging identities.
4. Inspect Terraform/OpenTofu state access, locks, encryption, module pins and approved plan hashes.
5. Validate CI security checks, provenance, secret scanning and policy deny behavior.
6. Collect Kubernetes RBAC, admission, GitOps drift and SLO evidence.
7. Export staging cost allocation, budgets, idle resource findings and capacity headroom.
8. Create an evidence register with hashes, timestamps, provenance and reviewers.
9. Open findings with owners, severity, due dates and explicit exception expiry.
10. Produce a GO/NO-GO recommendation; clean up disposable resources.

## 11. Lab D — DBRE reliability and recovery audit (manual)
1. Inventory synthetic database workloads and classify business/data criticality.
2. Review backup retention, encryption, PITR windows, restore permissions and replication topology.
3. Run an isolated, separately approved staging restore and measure actual RPO/RTO.
4. Validate transaction/data integrity and single-writer fencing after recovery.
5. Audit database storage/IOPS forecasts and costs without weakening durability.
6. Verify change approvals, audit trails, retention requirements and incident runbooks.
7. Require independent DBRE and security review of data-impacting exceptions.
8. Record unresolved critical gaps as NO-GO and preserve sanitized evidence.

## 12. Twenty troubleshooting scenarios

| # | Failure | Safe response |
|---|---|---|
| 1 | IAM role privilege expansion | revoke and review blast radius |
| 2 | Cross-tenant state exposure | isolate backend and rotate credentials |
| 3 | Unencrypted state snapshot | quarantine and restore protected backup |
| 4 | Secrets in Terraform plan | restrict artifacts and rotate secrets |
| 5 | Unsigned module release | block dependency promotion |
| 6 | Policy engine outage | fail closed and restore policy |
| 7 | Stale compliance evidence | regenerate authoritative artifacts |
| 8 | Tampered audit log | preserve forensic copy and escalate |
| 9 | Missing owner tags | repair cost allocation |
| 10 | Budget threshold breached | freeze optional spend and investigate |
| 11 | Cloud egress cost spike | trace data paths and adjust architecture |
| 12 | Capacity forecast misses peak | rebaseline and preserve headroom |
| 13 | SLO error-budget exhaustion | pause changes and incident review |
| 14 | GitOps drift ignored | reconcile controller ownership |
| 15 | Unapproved production change | rollback safely and investigate |
| 16 | Backup job succeeds but restore fails | NO-GO and fix restore chain |
| 17 | Database PITR gap | DBRE assess recoverability |
| 18 | Retention policy violates requirement | halt deletion and review |
| 19 | High finding without exception | NO-GO until remediated |
| 20 | Critical finding falsely waived | deny acceptance and escalate |

## 13. Ten production runbooks

**RB-01 — Security finding triage:** classify severity, isolate affected scope and preserve evidence.

**RB-02 — Identity and state exposure:** revoke credentials, rotate secrets and assess cross-tenant impact.

**RB-03 — Supply-chain compromise:** quarantine module, runner and unsigned artifacts.

**RB-04 — Compliance evidence outage:** fail closed for affected controls and restore collection.

**RB-05 — Cost anomaly response:** validate tags, budgets, egress and runaway capacity.

**RB-06 — SLO and capacity breach:** freeze unsafe changes and recover headroom.

**RB-07 — Terraform/OpenTofu drift:** inspect locked state and reconcile through reviewed plan.

**RB-08 — GitOps governance failure:** restore authoritative Git and admission policies.

**RB-09 — DBRE audit and recovery:** validate backup, PITR, retention and integrity.

**RB-10 — Final audit disposition:** record finding owners, exceptions, expiry and GO/NO-GO.

## 14. Enterprise 100-point final audit

| Domain | Points |
|---|---:|
| Identity and tenant isolation | 15 |
| State and secrets protection | 10 |
| Supply chain and policy | 10 |
| Audit and compliance evidence | 15 |
| Cost allocation and budgets | 10 |
| Capacity and SLOs | 10 |
| Recovery drill | 10 |
| Change governance | 10 |
| DBRE integrity | 10 |
| **Total** | **100** |

**Acceptance:** at least 90/100; all mandatory controls, verified fresh evidence, tenant isolation, zero open critical findings, zero unapproved high findings, independent security/SRE sign-off and DBRE sign-off when databases are in scope. Any critical exception or missing mandatory evidence yields **NO-GO**.

## 15. Closure and next chapter
Preserve the audit register, signed findings, exception approvals, cost baselines, SLO evidence, restore results and owner acknowledgments. Do not mark live controls as verified until they have been exercised.

**Next:** Chapter 120 — Enterprise Infrastructure as Code SRE/DBRE Final Certification and Production Readiness Assessment.
