# Chapter 095 — Enterprise Observability Security, Governance and Reliability Acceptance Capstone

**Part 19 — Enterprise Security, Governance and Reliability (5/5) · Final Part 19 capstone**

## Mission and learning outcomes

Build a defensible **staging acceptance decision** for a multi-tenant enterprise observability platform. Integrate the identity and authorization controls of Chapter 091, governance/privacy controls of Chapter 092, detection/response controls of Chapter 093, and resilience/DR controls of Chapter 094. This capstone is an assessment framework; publication of this chapter does not constitute a successful assessment.

By completion, an SRE/DBRE should be able to: describe trust boundaries; collect independent evidence; prove denied cross-tenant access; validate telemetry redaction and retention; test detection and paging; measure backup recoverability and RPO/RTO; demonstrate rollback; and prepare an auditable go/no-go decision.

## Reference enterprise architecture

```text
     applications / databases / Kubernetes / cloud audit feeds
                        |
            OTel agents and gateways
                        |
        mTLS, scoped identities, admission controls
                        |
       +----------------+----------------+
       |                |                |
   Prometheus          Loki             Tempo
       |                |                |
       +---------- Grafana --------------+
                  |           |
           tenant-aware   security audit trail
           query proxy          |
                  |        SIEM / SOC / IR
             SSO / RBAC          |
                  |        independent paging
        GitOps / policy gates    |
                  +-------------+
                        |
         encrypted, versioned, isolated backups
                        |
           tested DR and clean-room restore
```

Separate data plane and control plane identities. Apply least privilege at query APIs, object storage, cluster namespaces, dashboards and backup administration. A Grafana folder permission alone does not prove isolation in Prometheus/Loki/Tempo. Keep an out-of-band incident communication path.

## Acceptance workstreams and evidence

| Workstream | Mandatory evidence | Failure condition |
|---|---|---|
| 1. Identity and tenancy | SSO/MFA design, RBAC review, negative tenant A/B API tests | cross-tenant read or write succeeds |
| 2. Privacy and governance | classification, redaction tests, retention policy, deletion/legal-hold workflow | regulated fields leak or unapproved retention |
| 3. Detection and response | synthetic attack signals, alert routing, incident timeline, SOC acknowledgment | high-severity signal unpaged or untracked |
| 4. Backup and disaster recovery | backup manifest, checksums, clean restore, observed RPO/RTO | unrecoverable data or exceeded critical target |
| 5. Reliability | ingestion/query SLIs, burn-rate alert checks, capacity and failure-domain tests | critical SLO or alert routing gap |
| 6. Change management | pinned image/config versions, peer approval, rollback rehearsal | unapproved change or untested rollback |
| 7. Audit and assurance | signed evidence manifest, independent reviewer, exceptions register | missing chain of custody or unapproved exception |

## Threat model and security assumptions

**Assets:** telemetry with potential PII, security logs, traces, secrets, Grafana identities, backend storage, alert routes, GitOps configurations and recovery credentials.

**Threats:** stolen SSO tokens, service account overprivilege, insecure collector exporters, tenant-header spoofing, query API bypass, log injection, credential leakage in spans, malicious retention changes, backup deletion, compromised build artifacts, and adversarial alert silencing.

**Boundaries:** workload-to-collector, collector-to-backend, user-to-query, backend-to-object-store, SOC-to-alert, CI/CD-to-cluster and DR-to-production.

**Required controls:** verified authentication, server-side tenant identity enforcement, mTLS where appropriate, encryption/key rotation, restricted admin access, tamper-evident audit retention, vulnerability and image provenance review, scoped backup credentials and a documented break-glass process.

Do not use production credentials or real personal data in training fixtures.

## Acceptance scenarios

### S01 — Unauthorized tenant query

Use synthetic tenant A and B data. Attempt to read tenant B data with tenant A identity through **every** relevant backend and proxy path, not just the dashboard UI. Capture HTTP status, response body classification, request ID and audit record. Any data leakage is a **critical blocker**.

### S02 — Secret leakage through telemetry

Emit a synthetic canary such as `TRAINING_ONLY_TOKEN_DO_NOT_USE` in a staging application field. Confirm processor redaction at the Collector, storage, queries and exports. A test must assert absence of the canary from all accessible sinks. Never use real secrets.

### S03 — Retention and legal hold

Test synthetic old and new records under approved retention rules. Validate deletion behavior, exceptions and immutable audit evidence without deleting actual production data. Document the difference between logical query expiry and physical object deletion.

### S04 — Threat detection and paging

Generate controlled synthetic failed-authentication bursts and unauthorized query attempts. Verify SIEM/SOC detection, routing to a **test receiver**, deduplication, incident creation, acknowledgment and closure evidence. Never send simulated attacks to production paging.

### S05 — Security incident response

Tabletop a compromised Collector credential: revoke in staging, preserve evidence, rotate approved credentials, validate no alternate exporter remains active, and restore ingestion. Document timeline, commander, communications and postmortem.

### S06 — Backup corruption and clean restore

Corrupt a **disposable fixture** (not live storage). Validate that checksum verification rejects it; restore an intact versioned copy in an isolated namespace. Verify backend query, alert routing, permissions and encryption after restore.

### S07 — Regional disaster recovery

Simulate region loss in a tabletop or isolated DR environment. Measure last recoverable sample and elapsed restoration time, prove a secure restore and demonstrate documented rollback. Replication alone does not satisfy recoverability.

### S08 — Reliability regression and error budget

Inject a staging-only ingestion outage or synthetic query failure. Measure SLI impact, verify SLO burn-rate alert logic and demonstrate change freeze/escalation according to policy.

### S09 — GitOps drift and unauthorized change

Introduce drift only in a disposable namespace; confirm detection, review and reconciliation. Confirm admission/policy checks reject privileged identities and unapproved telemetry destinations.

### S10 — Independent acceptance review

Produce a signed decision record with traceable evidence links, reviewer identity, score, unresolved risks, compensating controls, exception expiry and explicit go/no-go.

## Acceptance evidence data contract

The following Python implementation is intentionally **offline** and uses only Python standard-library modules. It validates a *synthetic evidence manifest*, not real controls. Real acceptance requires independent evidence from staging exercises.

Save `acceptance_gate.py`:

```python
"""Offline acceptance evidence gate. No network, cloud or destructive actions."""
import json
import sys
from pathlib import Path

REQUIRED = (
    "identity_tenant_isolation",
    "privacy_redaction",
    "retention_governance",
    "threat_detection",
    "incident_paging",
    "backup_integrity",
    "clean_restore",
    "rpo_rto_met",
    "reliability_slo",
    "gitops_policy",
    "rollback_tested",
    "audit_chain_of_custody",
    "independent_review",
)
CRITICAL = frozenset((
    "identity_tenant_isolation", "privacy_redaction",
    "incident_paging", "backup_integrity",
    "clean_restore", "audit_chain_of_custody",
))
WEIGHTS = {
    "identity_tenant_isolation": 15,
    "privacy_redaction": 10,
    "retention_governance": 8,
    "threat_detection": 8,
    "incident_paging": 8,
    "backup_integrity": 8,
    "clean_restore": 10,
    "rpo_rto_met": 8,
    "reliability_slo": 8,
    "gitops_policy": 5,
    "rollback_tested": 5,
    "audit_chain_of_custody": 4,
    "independent_review": 3,
}
assert sum(WEIGHTS.values()) == 100

def assess(record):
    failures = []
    if not isinstance(record, dict):
        return {"decision": "NO-GO", "score": 0, "findings": ["manifest must be object"]}
    for key in ("assessment_id", "owner", "reviewer", "evidence_ref", "change_id"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            failures.append("missing " + key)
    if record.get("environment") not in ("lab", "staging"):
        failures.append("environment must be lab or staging")
    if record.get("approved") is not True:
        failures.append("approval missing")
    if record.get("destructive") is not False:
        failures.append("destructive actions prohibited")
    if record.get("reviewer") == record.get("owner"):
        failures.append("independent reviewer required")
    controls = record.get("controls")
    if not isinstance(controls, dict):
        controls = {}
        failures.append("controls object missing")
    score = 0
    for name in REQUIRED:
        item = controls.get(name)
        if not isinstance(item, dict):
            failures.append("missing evidence for " + name)
            continue
        status = item.get("passed")
        evidence = item.get("evidence")
        if status is True and isinstance(evidence, str) and evidence.strip():
            score += WEIGHTS[name]
        else:
            failures.append("failed or unsupported " + name)
    critical_failures = [x for x in CRITICAL if not (
        isinstance(controls.get(x), dict)
        and controls[x].get("passed") is True
        and isinstance(controls[x].get("evidence"), str)
        and controls[x]["evidence"].strip()
    )]
    if critical_failures:
        failures.append("critical blockers: " + ", ".join(sorted(critical_failures)))
    if score < 90:
        failures.append("score below 90")
    return {"decision": "GO" if not failures else "NO-GO",
            "score": score, "findings": failures}

if __name__ == "__main__":
    try:
        payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        result = assess(payload)
    except (IndexError, OSError, ValueError) as exc:
        sys.exit(str(exc))
    print(json.dumps(result, indent=2))
    sys.exit(result["decision"] != "GO")
```

Create a **synthetic** fixture without asserting real controls have been validated:

```python
# save as make_fixture.py
import json
from pathlib import Path
from acceptance_gate import REQUIRED
fixture = {
    "assessment_id": "OBS-095-SYNTHETIC",
    "owner": "sre-team",
    "reviewer": "independent-reviewer",
    "evidence_ref": "training-only-not-real-evidence",
    "change_id": "CHG-095-STAGING",
    "environment": "staging",
    "approved": True,
    "destructive": False,
    "controls": {
        name: {"passed": True, "evidence": "synthetic://" + name}
        for name in REQUIRED
    }
}
Path("synthetic-acceptance.json").write_text(json.dumps(fixture, indent=2))
```

Save `test_acceptance_gate.py`:

```python
import copy
import unittest
from acceptance_gate import assess, REQUIRED, WEIGHTS, CRITICAL

def good():
    return {
        "assessment_id": "OBS-095-TEST",
        "owner": "sre", "reviewer": "security",
        "evidence_ref": "synthetic-only", "change_id": "CHG-095",
        "environment": "staging", "approved": True, "destructive": False,
        "controls": {name: {"passed": True, "evidence": "synthetic://" + name}
                     for name in REQUIRED}
    }

class GateTests(unittest.TestCase):
    def test_weight_total(self):
        self.assertEqual(sum(WEIGHTS.values()), 100)
    def test_clean_synthetic_fixture(self):
        self.assertEqual(assess(good())["decision"], "GO")
    def test_non_object(self):
        self.assertEqual(assess([])["decision"], "NO-GO")
    def test_production_denied(self):
        self.assertEqual(assess(dict(good(), environment="production"))["decision"], "NO-GO")
    def test_approval_required(self):
        self.assertEqual(assess(dict(good(), approved=False))["decision"], "NO-GO")
    def test_destructive_denied(self):
        self.assertEqual(assess(dict(good(), destructive=True))["decision"], "NO-GO")
    def test_independent_reviewer(self):
        self.assertEqual(assess(dict(good(), reviewer="sre"))["decision"], "NO-GO")
    def test_missing_metadata(self):
        self.assertEqual(assess(dict(good(), change_id=""))["decision"], "NO-GO")
    def test_controls_required(self):
        self.assertEqual(assess(dict(good(), controls=None))["decision"], "NO-GO")
    def test_missing_evidence(self):
        for name in REQUIRED:
            with self.subTest(name=name):
                record = good()
                record["controls"][name]["evidence"] = ""
                self.assertEqual(assess(record)["decision"], "NO-GO")
    def test_failed_controls(self):
        for name in REQUIRED:
            with self.subTest(name=name):
                record = good()
                record["controls"][name]["passed"] = False
                self.assertEqual(assess(record)["decision"], "NO-GO")
    def test_critical_blockers(self):
        for name in CRITICAL:
            with self.subTest(name=name):
                record = good()
                del record["controls"][name]
                self.assertTrue(any("critical blockers" in f
                                    for f in assess(record)["findings"]))
    def test_score_deduction(self):
        record = good()
        record["controls"]["independent_review"]["passed"] = False
        self.assertEqual(assess(record)["score"], 97)
        self.assertEqual(assess(record)["decision"], "NO-GO")

if __name__ == "__main__":
    unittest.main()
```

Run:

```bash
python3 make_fixture.py
python3 acceptance_gate.py synthetic-acceptance.json
python3 -m unittest -v test_acceptance_gate.py
```

**Interpretation:** `GO` on the synthetic fixture proves only that the offline evaluator accepts a well-formed self-reported fixture. It is **not** permission to deploy or a statement of compliance. Actual evidence must be produced by controlled tests, independently reviewed, and bound to immutable artifact references.

## Production incident and assessment runbooks

### RB-095-01 — Cross-tenant access

Stop affected queries/exports, preserve request IDs and access logs, revoke compromised credentials through approved change, confirm scope, notify security/privacy owners, validate tenant boundary at each backend, and document breach-handling decisions.

### RB-095-02 — Sensitive telemetry leakage

Quarantine affected pipelines and access paths; preserve evidence without redistributing secrets; rotate impacted credentials; correct Collector redaction; validate storage/export sinks and retention actions with legal/security approval.

### RB-095-03 — Detection and alerting failure

Activate out-of-band paging, verify security signals independently, restore approved alert routes, perform a staging-only notification test, reconcile missed incidents and document detection gap.

### RB-095-04 — Failed backup or DR drill

Block promotion, preserve checksums and restore logs, select known-good clean recovery point, validate keys and identity, rerun end-to-end queries and paging, and record measured RPO/RTO and corrective actions.

### RB-095-05 — Release acceptance failure

Declare NO-GO, freeze promotion, assign findings with owners and due dates, remediate in staging, rerun failed and regression scenarios, and require independent re-approval.

## 100-point scorecard

The 13 controls in the Python gate carry 100 points in total. **All required controls must pass with evidence**, score must be at least 90, and there may be **zero critical blockers**. The strict all-controls requirement intentionally means a passing assessment scores 100; the 90-point threshold is retained for diagnostic prioritization and must not be used to waive a failed control. No exceptions are silently accepted; any exception requires a separate documented governance decision and a new approved assessment scope.

## Final acceptance checklist

- [ ] Security architecture, trust boundaries and identities reviewed
- [ ] Tenant A/B negative query tests at every backend
- [ ] Redaction, retention and privacy tests with synthetic fixtures
- [ ] Detection, SOC acknowledgment and test paging verified
- [ ] Backup checksum and clean-room restore verified
- [ ] RPO/RTO measured from actual staging evidence
- [ ] SLO/error budget alerts and rollback rehearsed
- [ ] GitOps and policy controls verified
- [ ] Incident timelines, evidence links and approvals preserved
- [ ] Independent security and SRE reviewers signed the decision

**Curriculum milestone:** Part 19 completes when Chapters 091–095 and companion labs are published. **Operational acceptance:** remains pending until the above tests and independent review are actually completed and documented.

**Next:** Chapter 096 — Enterprise Observability Production Capstone Architecture and Readiness Planning (Part 20).
