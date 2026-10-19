# Chapter 100 — Enterprise Observability Final Production Reliability and SRE/DBRE Certification Capstone

**Part 20 — Final Production Observability Capstones (5/5)**

## Mission and learning outcomes

This is the final integrated, production-oriented **training** capstone for the 100-chapter Enterprise Observability Engineering curriculum. It is not an accredited certification or authorization to deploy. The candidate must design, deploy in approved staging, instrument, monitor, secure, troubleshoot, recover and hand off an observability platform with traceable evidence.

Competencies: Kubernetes and GitOps; OpenTelemetry; Prometheus, Loki, Tempo, Grafana and Alertmanager; PostgreSQL, MongoDB and Kafka telemetry; SLIs/SLOs and error budgets; capacity and FinOps; IAM and tenant isolation; incident command; disaster recovery; and independent reliability acceptance.

## Enterprise architecture

```text
Kubernetes / HTTP application / PostgreSQL / MongoDB / Kafka
            | OTLP / scrape / logs / exporters
            v
    regional OTel gateways and collectors
       |             |            |
   Prometheus       Loki         Tempo
       |             |            |
       +--------- Grafana --------+
       |                            |
  SLO rules / Alertmanager    tenant-scoped queries
       |                            |
 independent paging          SOC/audit/privacy
       +------------+---------------+
                    |
      SRE / DBRE incident command
                    |
   GitOps + policy + backup + DR + evidence
```

All manifests must pin approved compatible component versions and images. Identity, network, backend endpoints, storage and retention are environment-specific; diagrams are not deployable systems.

## Final implementation phases

| Phase | Activities | Required evidence |
|---|---|---|
| 1 Architecture | requirements, ADRs, data classification, owners | diagrams, threat model, RACI |
| 2 Foundation | staging IAM, TLS, network policies, storage, GitOps | pinned manifests, policy reports |
| 3 Signals | instrument workloads, DB exporters, metrics/logs/traces | synthetic IDs and backend queries |
| 4 SLOs | independent probes, burn-rate rules, test paging | delivered test alert, SLO dashboard |
| 5 Security | least privilege, tenant negative tests, redaction | denied direct API queries, audit |
| 6 Capacity | load, cardinality, ingestion and query budgets | measured baseline and cost forecast |
| 7 Incident | IC, DBRE escalation, rollback, stakeholder updates | UTC timeline and runbooks |
| 8 Recovery | clean backup restore, isolated DR, RPO/RTO | checksums and measured recovery |
| 9 Acceptance | independent review and release decision | evidence index, risk register, GO/NO-GO |

## Twelve final scenarios

| ID | Scenario | Pass evidence |
|---|---|---|
| FIN-01 | Architecture and ownership | approved ADRs, owners and topology |
| FIN-02 | Kubernetes staging deploy and rollback | Git revision, manifests, rollout proof |
| FIN-03 | Metrics ingestion and query | timestamped PromQL result |
| FIN-04 | Log ingestion and correlation | Loki query with synthetic ID |
| FIN-05 | Trace ingestion and correlation | Tempo trace with same ID |
| FIN-06 | SLO alert and independent paging | burn-rate query and test receipt |
| FIN-07 | Tenant isolation and privacy | denied tenant A/B queries, absent canary |
| FIN-08 | Capacity, cardinality and FinOps | staging load and budget |
| FIN-09 | Collector/backend outage | incident timeline and telemetry gap |
| FIN-10 | DBRE incident escalation | datastore signal and handoff |
| FIN-11 | Backup and DR | clean restore, checksum, RPO/RTO |
| FIN-12 | Operational handoff and ORR | independent signed review |

## 100-point assessment

| Domain | Points |
|---|---:|
| Architecture and ownership | 10 |
| Deployment, GitOps and rollback | 10 |
| Metrics, logs and traces | 15 |
| SLOs, alerting and independent detection | 15 |
| Security, privacy and tenant isolation | 15 |
| Capacity, cardinality and FinOps | 5 |
| Incident command and DBRE | 10 |
| Backup, DR and measured recovery | 15 |
| Evidence integrity and independent review | 5 |
| **Total** | **100** |

All nine domains and twelve scenarios are mandatory. A target score of at least 90 is diagnostic; under the strict all-controls rule a GO requires 100/100, no critical blockers and independent review. Synthetic fixtures do not demonstrate operational competence.

## Offline executable assessment gate

Save as `final_gate.py`:

```python
"""Fail-closed offline final capstone manifest evaluator."""
import json
import sys
from pathlib import Path

DOMAINS = {
    "architecture": 10, "deployment_gitops": 10, "signals": 15,
    "slo_alerting": 15, "security_privacy": 15, "capacity_finops": 5,
    "incident_dbre": 10, "backup_dr": 15, "independent_review": 5,
}
SCENARIOS = tuple(f"FIN-{i:02d}" for i in range(1, 13))
CRITICAL = {"signals", "slo_alerting", "security_privacy", "backup_dr"}
assert sum(DOMAINS.values()) == 100

def assess(doc):
    if not isinstance(doc, dict):
        return {"decision": "NO-GO", "score": 0, "findings": ["manifest not object"]}
    findings = []
    for key in ("candidate", "assessment_id", "change_id", "git_sha",
                "owner", "reviewer", "evidence_index"):
        if not isinstance(doc.get(key), str) or not doc[key].strip():
            findings.append("missing " + key)
    if doc.get("owner") == doc.get("reviewer"):
        findings.append("independent reviewer required")
    if doc.get("environment") not in ("lab", "staging"):
        findings.append("unsafe environment")
    if doc.get("approved") is not True:
        findings.append("approval missing")
    if doc.get("destructive") is not False:
        findings.append("destructive actions prohibited")
    if doc.get("abort_triggered") is not False:
        findings.append("abort triggered or unverified")
    domains = doc.get("domains")
    if not isinstance(domains, dict):
        domains = {}
        findings.append("domains missing")
    score = 0
    for key, points in DOMAINS.items():
        item = domains.get(key)
        if (isinstance(item, dict) and item.get("passed") is True
                and isinstance(item.get("evidence"), str) and item["evidence"].strip()):
            score += points
        else:
            findings.append("failed or unsupported " + key)
            if key in CRITICAL:
                findings.append("critical blocker: " + key)
    scenarios = doc.get("scenarios")
    if not isinstance(scenarios, dict):
        scenarios = {}
        findings.append("scenarios missing")
    for key in SCENARIOS:
        item = scenarios.get(key)
        if not (isinstance(item, dict) and item.get("passed") is True
                and isinstance(item.get("evidence"), str) and item["evidence"].strip()):
            findings.append("scenario failed or unsupported " + key)
    if score < 90:
        findings.append("score below 90")
    return {"decision": "GO" if not findings else "NO-GO",
            "score": score, "findings": findings}

if __name__ == "__main__":
    try:
        result = assess(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    except (IndexError, OSError, ValueError) as exc:
        sys.exit(str(exc))
    print(json.dumps(result, indent=2))
    sys.exit(result["decision"] != "GO")
```

Save as `make_fixture.py`:

```python
import json
from pathlib import Path
from final_gate import DOMAINS, SCENARIOS
record = {
    "candidate": "synthetic-trainee", "assessment_id": "OBS-100-SYNTHETIC",
    "change_id": "CHG-100-TRAINING", "git_sha": "synthetic-not-a-real-sha",
    "owner": "sre", "reviewer": "independent-reviewer",
    "evidence_index": "synthetic://index",
    "environment": "staging", "approved": True,
    "destructive": False, "abort_triggered": False,
    "domains": {k: {"passed": True, "evidence": "synthetic://" + k}
                for k in DOMAINS},
    "scenarios": {k: {"passed": True, "evidence": "synthetic://" + k}
                  for k in SCENARIOS},
}
Path("synthetic-final.json").write_text(json.dumps(record, indent=2))
```

Save as `test_final_gate.py`:

```python
import unittest
from final_gate import assess, DOMAINS, SCENARIOS, CRITICAL

def fixture():
    return {
        "candidate": "test", "assessment_id": "OBS-100",
        "change_id": "CHG-100", "git_sha": "synthetic",
        "owner": "sre", "reviewer": "security",
        "evidence_index": "synthetic://index", "environment": "staging",
        "approved": True, "destructive": False, "abort_triggered": False,
        "domains": {k: {"passed": True, "evidence": "synthetic://" + k}
                    for k in DOMAINS},
        "scenarios": {k: {"passed": True, "evidence": "synthetic://" + k}
                      for k in SCENARIOS},
    }

class FinalTests(unittest.TestCase):
    def test_weights(self):
        self.assertEqual(sum(DOMAINS.values()), 100)
    def test_scenarios(self):
        self.assertEqual(len(SCENARIOS), 12)
    def test_happy_path(self):
        self.assertEqual(assess(fixture())["decision"], "GO")
    def test_invalid_type(self):
        self.assertEqual(assess([])["decision"], "NO-GO")
    def test_production_denied(self):
        self.assertEqual(assess(dict(fixture(), environment="production"))["decision"], "NO-GO")
    def test_unapproved(self):
        self.assertEqual(assess(dict(fixture(), approved=False))["decision"], "NO-GO")
    def test_destructive(self):
        self.assertEqual(assess(dict(fixture(), destructive=True))["decision"], "NO-GO")
    def test_abort(self):
        self.assertEqual(assess(dict(fixture(), abort_triggered=True))["decision"], "NO-GO")
    def test_reviewer_conflict(self):
        self.assertEqual(assess(dict(fixture(), reviewer="sre"))["decision"], "NO-GO")
    def test_missing_git(self):
        self.assertEqual(assess(dict(fixture(), git_sha=""))["decision"], "NO-GO")
    def test_missing_domains(self):
        self.assertEqual(assess(dict(fixture(), domains=None))["decision"], "NO-GO")
    def test_missing_scenarios(self):
        self.assertEqual(assess(dict(fixture(), scenarios=None))["decision"], "NO-GO")
    def test_domain_failures(self):
        for key in DOMAINS:
            with self.subTest(key=key):
                record = fixture()
                record["domains"][key]["passed"] = False
                self.assertEqual(assess(record)["decision"], "NO-GO")
    def test_domain_evidence(self):
        for key in DOMAINS:
            with self.subTest(key=key):
                record = fixture()
                record["domains"][key]["evidence"] = ""
                self.assertEqual(assess(record)["decision"], "NO-GO")
    def test_critical_blockers(self):
        for key in CRITICAL:
            with self.subTest(key=key):
                record = fixture()
                del record["domains"][key]
                self.assertTrue(any("critical blocker" in x for x in assess(record)["findings"]))
    def test_scenario_failures(self):
        for key in SCENARIOS:
            with self.subTest(key=key):
                record = fixture()
                record["scenarios"][key]["passed"] = False
                self.assertEqual(assess(record)["decision"], "NO-GO")
    def test_scenario_evidence(self):
        for key in SCENARIOS:
            with self.subTest(key=key):
                record = fixture()
                record["scenarios"][key]["evidence"] = ""
                self.assertEqual(assess(record)["decision"], "NO-GO")

if __name__ == "__main__":
    unittest.main()
```

Run:

```bash
python3 make_fixture.py
python3 final_gate.py synthetic-final.json
python3 -m unittest -v test_final_gate.py
```

The fixture returns GO with 100 points by construction. It proves only that the offline gate accepts a synthetic complete manifest; it does **not** prove real infrastructure, certification or recovery.

## Final incident simulations and runbooks

1. **Collector failure:** compare receiver/exporter metrics, queue saturation, backend ingest and synthetic trace/log/metric arrival; recover and document gaps.
2. **Alerting outage:** activate independent paging, inspect routes/silences, test delivery, reconcile missed alerts and error-budget impact.
3. **DBRE incident:** validate PostgreSQL lag/locks, MongoDB cache or Kafka consumer lag independently of exporters; coordinate escalation without unsafe DB mutations.
4. **Tenant/privacy breach:** block affected path, preserve audit, involve SOC/privacy, retest direct APIs and redaction; never waive the security blocker.
5. **Capacity runaway:** halt synthetic load, control labels/quotas, inspect storage and costs, confirm critical signals are retained.
6. **GitOps failure:** freeze promotion, verify CRD/schema compatibility, roll back pinned revision and rerun integration tests.
7. **DR restore:** verify immutable backup checksum and KMS, restore in isolation, query metrics/logs/traces, test paging and tenant isolation, measure RPO/RTO.
8. **NO-GO closure:** record failed controls, action owners, deadlines, evidence and independent retest; do not promote.

## Required graduate portfolio

Architecture and ADRs; pinned deployment/rollback; end-to-end telemetry queries; SLOs and paging; negative tenant tests and redaction; capacity and cost model; SRE/DBRE incident timeline; clean restore and measured RPO/RTO; runbooks; independent review; final risk register and decision.

## Publication milestone

**100/100 chapters and 20/20 parts published.** Practical lab execution, independent technical/security review, compliance assessment and any actual production rollout remain separate, pending activities. No accredited credential is awarded by this tutorial.

**Curriculum complete.**
