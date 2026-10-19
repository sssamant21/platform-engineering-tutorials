# Chapter 093 — Enterprise Observability Security Monitoring, Threat Detection and Incident Response Automation

**Part 19 — Enterprise Security, Governance and Reliability (3/5)**

## Learning objectives

Design security telemetry for the observability control plane, detect abuse and tampering, correlate signals into actionable incidents, and automate *safe, authorized* response with immutable evidence and human approvals. Separate detection effectiveness from operational reliability and regulatory compliance claims.

## Enterprise architecture

```text
Kubernetes audit / cloud IAM / Grafana audit / reverse-proxy logs / OTel health
                | (TLS, workload identity, redaction)
       OpenTelemetry Collector / log forwarding
                | (validation, tenant boundaries)
         Loki / SIEM      Prometheus / Alertmanager
                \          /
              Detection rules + correlation
                       |
               Incident queue / SOAR
                 /            \
        Notify + enrich    approval gate
                               |
                    scoped, reversible action
                               |
                  audit + recovery verification
```

Security event pipelines must not share credentials with the protected systems' administrator accounts. Route high-value audit evidence to access-controlled, tamper-evident storage with independent retention. Threat detection is defense-in-depth, not a substitute for prevention.

## Threat model and telemetry inventory

| Surface | Threat | Detection signal | Response owner |
|---|---|---|---|
| Grafana | credential stuffing / privilege escalation | repeated failed logins, role changes, token creation | IAM / SOC |
| Prometheus | unauthorized scrape / configuration tampering | scrape target changes, config reload anomalies, API access logs | Platform SRE |
| Loki / Tempo | cross-tenant reads, data exfiltration | gateway 403s, unusual query volume and egress | Security / Observability |
| OTel Collector | pipeline bypass, export failures | config drift, exporter failures, drop rate, receiver changes | Platform SRE |
| Kubernetes | RBAC abuse / secret reads | audit events for role bindings, secrets, service accounts | Kubernetes security |
| Cloud storage | retention or encryption tampering | bucket policy changes, KMS denies, object delete attempts | Cloud security |

Treat telemetry as potentially sensitive. Never log credentials, tokens, raw request bodies, or unredacted customer identifiers. Capture timestamps in UTC, principal, tenant, source, action, outcome, request ID and change ticket where available. Audit fields depend on the product edition, gateway, and configured log sources; validate availability rather than assuming native support.

## Detection engineering

Start with a documented detection hypothesis, data source, baseline, exclusion logic, severity and owner. Distinguish benign SRE changes from suspicious access with approved change records. Establish coverage for:

1. Repeated authentication failures followed by success from an unusual source.
2. Unexpected Grafana organization or role grants.
3. New privileged Kubernetes RoleBinding/ClusterRoleBinding.
4. Unauthorized telemetry export endpoint or OTel processor change.
5. Loki or Tempo cross-tenant access attempts and high-volume query bursts.
6. Prometheus scrape target disappearance or unexpected remote-write change.
7. Audit pipeline silence or evidence store policy modification.
8. Sudden telemetry drop coincident with an infrastructure change.

Use allowlists only with explicit expiry and ownership. Avoid blocking or deleting resources automatically from a single weak indicator.

## Prometheus security pipeline health rules

Example PromQL; adapt job names and metric labels to the pinned deployment:

```promql
sum by (job) (rate(otelcol_exporter_send_failed_log_records[5m])) > 0
```

```promql
up{job="security-audit-forwarder"} == 0
```

```promql
changes(prometheus_config_last_reload_successful[15m]) > 0
```

The last expression detects a value change, **not** every configuration reload. A failed reload is better detected by `prometheus_config_last_reload_successful == 0`; confirm the metric exists in the installed version. Security detections require additional access/audit context.

## Example Loki investigation

Assuming structured JSON logs are ingested with low-cardinality stream labels:

```logql
{service_name="grafana-gateway"} | json | status="403"
```

```logql
sum by (service_name) (count_over_time({service_name="grafana-gateway"} | json | status="403" [5m]))
```

Do not label by user ID, request ID or token; extract those fields at query time under authorized access.

## Correlation and severity

Join audit, authentication, Kubernetes, GitOps and exporter events by bounded UTC windows, stable request IDs and verified principal mappings. A Grafana admin grant plus unapproved GitOps change plus unusual tenant query is higher-confidence than any one event. Record gaps, clock skew, missing telemetry and alternative explanations. Use severity based on scope, confidence, affected tenants, active compromise and recovery risk.

## Incident response automation: guardrails

**Automatic:** enrich alerts, deduplicate, page responders, preserve event hashes, create an incident record and attach read-only investigation queries.

**Human approval required:** token revocation, access changes, traffic blocks, deployment rollback, isolation, key rotation and any action that may affect availability or evidence. Use two-person review for high-blast-radius changes, least-privilege service identities, time-limited approvals and an explicit rollback plan.

**Never automatic:** destructive log deletion, evidence alteration, blanket account disablement, cross-tenant queries or unreviewed production isolation. Every playbook must fail closed if approval, owner, scope or evidence is missing.

## Executable offline response policy gate

Save `security_gate.py`:

```python
import json
import sys
from pathlib import Path

REQUIRED = ("incident_id", "owner", "change_id", "evidence_ref")
SENSITIVE = {"revoke_token", "block_traffic", "rotate_key", "rollback", "isolate"}

def validate(event):
    errors = []
    if not isinstance(event, dict):
        return ["event must be an object"]
    for key in REQUIRED:
        if not isinstance(event.get(key), str) or not event[key].strip():
            errors.append(f"missing {key}")
    if event.get("environment") not in {"lab", "staging"}:
        errors.append("production execution prohibited")
    if event.get("tenant_scoped") is not True:
        errors.append("tenant boundary not verified")
    if event.get("audit_preserved") is not True:
        errors.append("audit evidence not preserved")
    action = event.get("action")
    if action not in SENSITIVE | {"notify", "enrich"}:
        errors.append("unknown action")
    if action in SENSITIVE:
        if event.get("approved") is not True:
            errors.append("approval required")
        if not event.get("approver") or not event.get("rollback_plan"):
            errors.append("approver and rollback plan required")
    if event.get("destructive") is not False:
        errors.append("destructive action prohibited")
    return errors

if __name__ == "__main__":
    try:
        event = json.loads(Path(sys.argv[1]).read_text())
        findings = validate(event)
    except (IndexError, OSError, ValueError) as exc:
        sys.exit(str(exc))
    print(json.dumps({"status": "PASS" if not findings else "FAIL",
                      "findings": findings}, indent=2))
    sys.exit(bool(findings))
```

Save `safe-event.json`:

```json
{
  "incident_id": "OBS-093-001",
  "owner": "security-oncall",
  "change_id": "CHG-093",
  "evidence_ref": "synthetic-evidence-001",
  "environment": "staging",
  "tenant_scoped": true,
  "audit_preserved": true,
  "action": "notify",
  "destructive": false
}
```

Save `test_security_gate.py`:

```python
import copy
import json
import unittest
from pathlib import Path
from security_gate import validate

BASE = json.loads(Path(__file__).with_name("safe-event.json").read_text())

class SecurityGateTests(unittest.TestCase):
    def test_safe_notification(self):
        self.assertEqual(validate(BASE), [])
    def test_no_production(self):
        event = dict(BASE, environment="production")
        self.assertIn("production execution prohibited", validate(event))
    def test_no_cross_tenant(self):
        self.assertTrue(validate(dict(BASE, tenant_scoped=False)))
    def test_no_evidence_loss(self):
        self.assertTrue(validate(dict(BASE, audit_preserved=False)))
    def test_no_destructive(self):
        self.assertTrue(validate(dict(BASE, destructive=True)))
    def test_no_unapproved_revocation(self):
        self.assertIn("approval required", validate(dict(BASE, action="revoke_token")))
    def test_approved_sensitive_action(self):
        event = dict(BASE, action="revoke_token", approved=True,
                     approver="security-reviewer", rollback_plan="restore test credential")
        self.assertEqual(validate(event), [])
    def test_unknown_action(self):
        self.assertTrue(validate(dict(BASE, action="delete_logs")))
    def test_missing_incident(self):
        event = copy.deepcopy(BASE)
        del event["incident_id"]
        self.assertTrue(validate(event))

if __name__ == "__main__":
    unittest.main()
```

Run:

```bash
python3 security_gate.py safe-event.json
python3 -m unittest -v test_security_gate.py
```

This gate validates **synthetic decision metadata only**. It does not perform response actions, authenticate approvals, verify evidence integrity or connect to production. In a real system use signed approval records, an immutable incident store, identity checks, policy-as-code enforcement, dry-run and explicit execution separation.

## Production incident scenarios and runbooks

| Scenario | Investigation | Containment and recovery |
|---|---|---|
| Privilege escalation | correlate role grants, IAM and change tickets | preserve audit trail; seek IAM approval before revocation |
| Tenant boundary probing | query gateway denies and tenant mappings | isolate suspect client only after scoped authorization |
| Telemetry exfiltration | inspect egress, remote-write and collector configs | halt unauthorized route under approved change |
| Audit silence | validate forwarder, ingestion lag and storage | restore pipeline; mark blind interval |
| Collector tampering | compare signed desired config and live state | review GitOps rollback and credentials |
| Alert flood | group alerts and verify real activity | rate-limit notifications without suppressing critical incidents |
| Compromised service account | correlate Kubernetes audit and cloud IAM | rotate staging credential with rollback and owner approval |
| Evidence deletion attempt | review object-store policy and audit access | preserve snapshots and escalate to forensics |

For each incident, record detection timestamp, evidence provenance, confidence, severity, affected tenants, on-call ownership, decision approvals, containment time, rollback, restoration checks, and postmortem actions.

## Staging game day and acceptance

Run synthetic auth failures, forbidden tenant queries, config drift, exporter outage and an unauthorized role-grant simulation in a disposable environment. Verify detection latency, alert routing, incident correlation, safe denial of unapproved automation, recovery, evidence integrity and no sensitive-data leakage. Never simulate credential attacks against live endpoints.

**100-point rubric:** threat coverage (20), telemetry completeness (15), detection precision (15), correlation and triage (15), automation safeguards (15), recovery verification (10), audit evidence and review (10). Require at least 85 points and zero critical safety failures for staging acceptance; this is a curriculum criterion, not a compliance certification.

## Operational exit criteria

Document false-positive rates, missed detections, data gaps, alert SLOs, rollback testing, SOC handoff, control ownership and independent security review. Live governance testing, production game days and external compliance verification remain pending until evidenced.
