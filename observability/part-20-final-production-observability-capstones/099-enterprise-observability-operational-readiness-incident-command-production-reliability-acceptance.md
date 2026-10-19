# Chapter 099 — Enterprise Observability Operational Readiness, Incident Command and Production Reliability Acceptance

**Part 20 — Final Production Observability Capstones (4/5)**

## Mission

Convert the architecture, staging integration tests and chaos/DR findings from Chapters 096–098 into a rigorous **operational readiness review (ORR)**. A deployment that passes smoke tests is not automatically supportable in production. This chapter requires named ownership, service-level objectives, independent alerting, security approval, rehearsed incident command, recovery evidence and an explicit go/no-go decision.

**Safety:** all exercises are synthetic, tabletop or in a separately approved staging environment. No live paging, production failover or destructive operations are authorized by this chapter.

## Learning outcomes

- Establish service ownership and an auditable on-call model.
- Define SLIs/SLOs, error-budget policy, alert quality and escalation.
- Lead an incident with clear roles, evidence preservation and stakeholder communications.
- Test detection, triage, rollback, recovery, security and cross-team handoff.
- Prove backup/DR, privacy and tenant-isolation controls using independently reviewed evidence.
- Issue a documented GO/NO-GO with unresolved risks and corrective actions.

## Operating model and accountability

| Function | Primary responsibility | Backup / escalation |
|---|---|---|
| Platform SRE | Collector, backend health, capacity, alert delivery | infrastructure on-call |
| DBRE | PostgreSQL, MongoDB, Kafka/streaming data source signals | database service owner |
| Application team | instrumentation, trace/log correctness, service SLO | application incident lead |
| Security/SOC | identity, tenant isolation, threat signals, breach triage | security incident commander |
| Privacy/governance | classification, retention, deletion/legal hold | legal/compliance owner |
| Incident commander (IC) | severity, decisions, coordination, timeline | designated deputy |
| Communications lead | customer/internal updates and cadence | incident commander |
| Scribe | timeline, evidence links, action items | incident delegate |
| Change authority | approve release, rollback and exception | CAB/delegated approver |

Assign actual people and coverage hours in a private operational roster. Do not publish personal phone numbers or privileged escalation secrets in public GitHub files.

## Operational architecture

```text
workload + DB + Kubernetes telemetry
                 |
         Collector / gateways
                 |
   Prometheus | Loki | Tempo
          |       |       |
        Grafana + SLO views
                 |
    independent synthetic probes
                 |
      Alertmanager / SOC feeds
                 |
      test paging / real paging*
                 |
      incident command + runbooks
                 |
  change / rollback / backup / DR
                 |
      evidence + ORR decision

* real paging only under separately approved operational change
```

Observability for the observability platform must be independent enough to detect its own outage. A dashboard backed solely by the failed monitoring system is insufficient as the only failure signal.

## SLI, SLO and error-budget policy

Define an SLI with numerator, denominator, aggregation interval, excluded events and data source. Example:

```text
SLI = successful synthetic queries / all valid synthetic queries
SLO = 99.9% over 30 days
Error budget = 0.1% of valid requests in that window
```

For a 30-day window, a 99.9% availability objective corresponds to 43.2 minutes of *equivalent full unavailability* if the SLI is time-based; request-based SLIs require request-weighted interpretation. Alert on multi-window burn rate rather than a single noisy threshold. Separate ingestion completeness, query availability, alert delivery and tenant-security SLIs. Security violations must not be traded against error budget.

### Example policy

- Normal budget: reviewed releases with canary and rollback.
- Elevated burn: suspend risky changes and initiate mitigation.
- Budget exhausted: freeze nonessential deployments pending SRE review.
- Security breach or cross-tenant leakage: immediate blocker regardless of availability score.

## Readiness evidence domains

| Domain | Evidence | Release blocker |
|---|---|---|
| Ownership | named primary/secondary, escalation and handoff | no accountable on-call |
| SLOs | SLIs, baselines, burn-rate tests, budget policy | undefined critical SLO |
| Alerting | synthetic independent paging and routing proof | critical alert not delivered |
| Incident command | tabletop timeline, severity and role assignment | no commander/escalation |
| Runbooks | executable, reviewed, timed recovery steps | unsafe or untested rollback |
| Change management | pinned revision, approvals, canary, rollback | unapproved production change |
| Security | SSO/RBAC, tenant negative tests, audit | unauthorized access |
| Privacy | synthetic canary redaction, retention approval | sensitive data leak |
| DR | backup integrity, clean restore, measured RPO/RTO | recovery target unmet |
| Capacity | ingest/query load, cardinality, quota and cost | unbounded failure risk |
| DBRE integration | source metrics, exporter security and escalation | missing critical datastore signal |
| Evidence/review | immutable references, independent approval | unverified claims |

## Incident command playbook

### Declare

Identify affected service, customer impact, severity, first observation UTC, independent detection signal and initial mitigation. Open incident record and assign IC, operations lead, communications lead and scribe.

### Stabilize

Prioritize safety and containment: stop unauthorized data access, halt unapproved changes, restore independent paging and protect backups. Capture evidence before changing systems when safe.

### Diagnose

Use a hypothesis-driven timeline: recent deployment, Collector receiver/exporter errors, queue saturation, backend ingestion/query failures, storage/KMS, Grafana authentication, Alertmanager routing and database exporter health.

### Mitigate and recover

Choose the lowest-risk approved action. Roll back pinned configuration, restore healthy collectors or backend dependencies, or activate DR only with designated authority. Confirm metrics, logs, traces, alerts, security isolation and audit continuity.

### Communicate

Set update cadence based on severity, document what is known/unknown, expected next checkpoint and responsible owner. Avoid unsupported recovery ETAs.

### Close and learn

Require objective recovery verification, impact assessment, RPO/RTO and data-loss measurements, post-incident review, action owners, due dates and regression tests.

## Twelve production-oriented incident simulations

| ID | Incident | Primary response | Acceptance evidence |
|---|---|---|---|
| ORR-01 | Collector outage | restore ingest and quantify loss | signal query and queue metrics |
| ORR-02 | Prometheus unavailable | independent detection and query recovery | probe and PromQL result |
| ORR-03 | Loki backlog | restore export and record log gap | log ID and exporter counters |
| ORR-04 | Tempo missing traces | validate sampling and backend | trace ID and span evidence |
| ORR-05 | Alert delivery failure | out-of-band paging | test receiver timestamp |
| ORR-06 | High-cardinality surge | stop load and enforce budgets | series and memory trend |
| ORR-07 | DB replication lag | DBRE escalation and correlation | approved DB metric |
| ORR-08 | Tenant data exposure | block access and notify security | negative API tests |
| ORR-09 | Secret canary leak | isolate pipeline and rotate if needed | redaction and audit proof |
| ORR-10 | Corrupt backup | clean-room restore | checksums and query evidence |
| ORR-11 | Regional outage | DR command and measured recovery | RPO/RTO, paging, rollback |
| ORR-12 | Failed GitOps rollout | change freeze and rollback | pinned revision and E2E probes |

## Executable offline ORR acceptance gate

This standard-library Python gate validates a **self-reported synthetic evidence manifest**. It does not inspect live infrastructure and cannot establish operational readiness without independent real-world evidence.

Save `orr_gate.py`:

```python
"""Fail-closed offline ORR evaluator. No network or infrastructure actions."""
import json
import sys
from pathlib import Path

DOMAINS = {
    "ownership": 8, "slo_policy": 8, "alerting": 12,
    "incident_command": 10, "runbooks": 8, "change_control": 8,
    "security_isolation": 12, "privacy_governance": 8,
    "disaster_recovery": 12, "capacity": 6,
    "dbre_integration": 4, "independent_review": 4,
}
CRITICAL = frozenset(("alerting", "security_isolation", "privacy_governance", "disaster_recovery"))
SCENARIOS = tuple(f"ORR-{i:02d}" for i in range(1, 13))
assert sum(DOMAINS.values()) == 100

def assess(doc):
    if not isinstance(doc, dict):
        return {"decision": "NO-GO", "score": 0, "findings": ["manifest must be object"]}
    findings = []
    for field in ("assessment_id", "change_id", "owner", "reviewer", "evidence_ref"):
        if not isinstance(doc.get(field), str) or not doc[field].strip():
            findings.append("missing " + field)
    if doc.get("owner") == doc.get("reviewer"):
        findings.append("independent reviewer required")
    if doc.get("environment") not in ("lab", "staging"):
        findings.append("unsafe environment")
    if doc.get("approved") is not True:
        findings.append("approval missing")
    if doc.get("destructive") is not False:
        findings.append("destructive actions prohibited")
    if doc.get("abort_triggered") is not False:
        findings.append("abort condition triggered or unverified")
    controls = doc.get("controls")
    if not isinstance(controls, dict):
        controls = {}
        findings.append("controls map missing")
    score = 0
    for name, weight in DOMAINS.items():
        item = controls.get(name)
        if (isinstance(item, dict) and item.get("passed") is True
                and isinstance(item.get("evidence"), str) and item["evidence"].strip()):
            score += weight
        else:
            findings.append("failed or unsupported " + name)
            if name in CRITICAL:
                findings.append("critical blocker: " + name)
    scenarios = doc.get("scenarios")
    if not isinstance(scenarios, dict):
        scenarios = {}
        findings.append("scenarios map missing")
    for name in SCENARIOS:
        item = scenarios.get(name)
        if not (isinstance(item, dict) and item.get("passed") is True
                and isinstance(item.get("evidence"), str) and item["evidence"].strip()):
            findings.append("scenario failed or unsupported " + name)
    if score < 90:
        findings.append("score below 90")
    return {"decision": "GO" if not findings else "NO-GO",
            "score": score, "findings": findings}

if __name__ == "__main__":
    try:
        record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        result = assess(record)
    except (IndexError, OSError, ValueError) as exc:
        sys.exit(str(exc))
    print(json.dumps(result, indent=2))
    sys.exit(result["decision"] != "GO")
```

Save `make_fixture.py`:

```python
import json
from pathlib import Path
from orr_gate import DOMAINS, SCENARIOS
doc = {
    "assessment_id": "OBS-099-SYNTHETIC",
    "change_id": "CHG-099-TRAINING",
    "owner": "sre", "reviewer": "security",
    "evidence_ref": "synthetic://orr",
    "environment": "staging", "approved": True,
    "destructive": False, "abort_triggered": False,
    "controls": {name: {"passed": True, "evidence": "synthetic://" + name}
                 for name in DOMAINS},
    "scenarios": {name: {"passed": True, "evidence": "synthetic://" + name}
                  for name in SCENARIOS},
}
Path("synthetic-orr.json").write_text(json.dumps(doc, indent=2))
```

Save `test_orr_gate.py`:

```python
import unittest
from orr_gate import DOMAINS, SCENARIOS, CRITICAL, assess

def good():
    return {
        "assessment_id": "test", "change_id": "CHG-099",
        "owner": "sre", "reviewer": "security", "evidence_ref": "synthetic://orr",
        "environment": "staging", "approved": True,
        "destructive": False, "abort_triggered": False,
        "controls": {n: {"passed": True, "evidence": "synthetic://" + n}
                     for n in DOMAINS},
        "scenarios": {n: {"passed": True, "evidence": "synthetic://" + n}
                      for n in SCENARIOS},
    }

class ORRTests(unittest.TestCase):
    def test_weights(self):
        self.assertEqual(sum(DOMAINS.values()), 100)
    def test_happy_path(self):
        self.assertEqual(assess(good())["decision"], "GO")
    def test_non_object(self):
        self.assertEqual(assess([])["decision"], "NO-GO")
    def test_production_denied(self):
        self.assertEqual(assess(dict(good(), environment="production"))["decision"], "NO-GO")
    def test_unapproved_denied(self):
        self.assertEqual(assess(dict(good(), approved=False))["decision"], "NO-GO")
    def test_destructive_denied(self):
        self.assertEqual(assess(dict(good(), destructive=True))["decision"], "NO-GO")
    def test_abort_denied(self):
        self.assertEqual(assess(dict(good(), abort_triggered=True))["decision"], "NO-GO")
    def test_reviewer_independence(self):
        self.assertEqual(assess(dict(good(), reviewer="sre"))["decision"], "NO-GO")
    def test_missing_metadata(self):
        self.assertEqual(assess(dict(good(), change_id=""))["decision"], "NO-GO")
    def test_missing_controls(self):
        self.assertEqual(assess(dict(good(), controls=None))["decision"], "NO-GO")
    def test_missing_scenarios(self):
        self.assertEqual(assess(dict(good(), scenarios=None))["decision"], "NO-GO")
    def test_each_failed_control(self):
        for name in DOMAINS:
            with self.subTest(name=name):
                doc = good()
                doc["controls"][name]["passed"] = False
                self.assertEqual(assess(doc)["decision"], "NO-GO")
    def test_each_missing_evidence(self):
        for name in DOMAINS:
            with self.subTest(name=name):
                doc = good()
                doc["controls"][name]["evidence"] = ""
                self.assertEqual(assess(doc)["decision"], "NO-GO")
    def test_critical_blockers(self):
        for name in CRITICAL:
            with self.subTest(name=name):
                doc = good()
                del doc["controls"][name]
                self.assertTrue(any("critical blocker" in f for f in assess(doc)["findings"]))
    def test_each_failed_scenario(self):
        for name in SCENARIOS:
            with self.subTest(name=name):
                doc = good()
                doc["scenarios"][name]["passed"] = False
                self.assertEqual(assess(doc)["decision"], "NO-GO")

if __name__ == "__main__":
    unittest.main()
```

Run:

```bash
python3 make_fixture.py
python3 orr_gate.py synthetic-orr.json
python3 -m unittest -v test_orr_gate.py
```

The synthetic fixture should yield 100 points and GO, but that proves **only the evaluator's happy path**. No incident drill or production control has been verified by this fixture.

## Incident runbooks

### RB-099-01 — Major incident declaration

Create incident record, severity, UTC start, impact statement, IC/backup, scribe and communication channel. Trigger independent alerting and establish decision cadence.

### RB-099-02 — Missing telemetry

Correlate workload, Collector, exporter, backend and query signals. Check queues, dropped data, auth and storage. Recover safely and document the exact unobservable interval.

### RB-099-03 — Alert delivery failure

Activate independent paging, investigate route, silence, receiver and network, restore test receiver, then reconcile missed incidents.

### RB-099-04 — Security or privacy incident

Block affected tenant/export path, preserve access logs and evidence, involve SOC/privacy owners, remediate identity/redaction, and require independent sign-off.

### RB-099-05 — Database telemetry incident

DBRE validates exporter health and database impact separately. Avoid interpreting missing exporter metrics as healthy database behavior. Escalate to service owner.

### RB-099-06 — Disaster recovery command

Confirm authority and scope, select clean backup, validate keys and identity, restore into approved environment, measure RPO/RTO and verify queries, alerts and isolation.

### RB-099-07 — Change freeze and rollback

Stop rollout, pin last-known-good revision, assess schema compatibility, roll back with change authority, rerun integration tests and record the decision.

### RB-099-08 — Post-incident and readiness closure

Publish timeline, impact, root/contributing factors, action owners, verification and ORR scorecard. Keep GO blocked until critical findings are independently closed.

## 100-point operational readiness rubric

The 12 domains in `orr_gate.py` total 100 points. **Every domain and every ORR-01–12 scenario requires traceable passing evidence**. There must be zero critical blockers and no triggered safety abort. The 90-point threshold is diagnostic; because all domains are mandatory, an actual GO currently requires 100/100. Exceptions require a separate formally approved change to the assessment scope, never a silent waiver.

## Handoff and acceptance artifacts

1. Service catalogue and named operational owners.
2. On-call rota, escalation matrix and severity policy.
3. SLI/SLO definitions and error-budget policy.
4. Synthetic independent paging and alert routing evidence.
5. Incident command tabletop timelines and communication templates.
6. Reviewed runbooks, rollback and GitOps revision references.
7. Security/privacy negative-test evidence.
8. Clean restore, measured RPO/RTO and capacity tests.
9. DBRE exporter ownership and database signal validation.
10. Independent ORR decision record and corrective-action register.

**Status:** This chapter documents the required tests and operating model; live deployment, incident drill execution, independent approval and compliance validation remain pending until actual evidence is supplied.

**Next:** Chapter 100 — Enterprise Observability Final Production Reliability and SRE/DBRE Certification Capstone.
