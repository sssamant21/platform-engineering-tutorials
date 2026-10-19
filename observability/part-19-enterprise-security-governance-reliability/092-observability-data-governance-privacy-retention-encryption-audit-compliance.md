# Chapter 092 — Observability Data Governance, Privacy, Retention, Encryption and Audit Compliance

**Part 19 — Enterprise Security, Governance and Reliability (2/5)**

## Objectives

Build a production-ready governance model for telemetry data across Prometheus, Grafana, Loki, Tempo, OpenTelemetry and object storage: classification, minimization, privacy, residency, retention, encryption, audit and evidence.

## Governance reference architecture

```text
Applications / Kubernetes / DBRE services
                   |
          OTel policy and redaction
                   |
         tenant-aware secure gateway
             /      |       \
       Prometheus  Loki     Tempo
             \      |       /
        encrypted storage + retention
                   |
          Grafana scoped access
                   |
    audit evidence / security / legal
```

## Data inventory and classification

Inventory metrics labels, log attributes, trace spans, exemplars, alert payloads, dashboard annotations, object storage and backups. Classify as public/internal/confidential/restricted according to organizational policy. Treat IP addresses, user identifiers, SQL literals, Redis keys, Kafka payloads, Elasticsearch document content and Snowflake query text as potentially sensitive. Apply minimization at source before collection.

## Privacy-by-design pipeline

Use OpenTelemetry processor filtering, attribute deletion and transformations according to the pinned Collector distribution and version. Validate that redaction runs before export, including failure/retry paths. Use synthetic canary values and verify they never reach Loki, Tempo, metrics, alert payloads or downstream exports. Do not depend on Grafana dashboard masking to protect stored data.

## Retention governance

Specify signal-level and tenant-level retention with business owner, legal/compliance approval and documented exceptions. Prometheus local TSDB, Loki compactor and Tempo block retention use different mechanisms. A configuration value alone does not prove deletion; verify observed lifecycle and backup/object-store expiration. Legal holds can conflict with deletion and must be resolved by the appropriate authority. Avoid irreversible deletion in production without a reviewed change.

## Encryption and keys

Require TLS in transit and approved encryption at rest for TSDB, object stores and backups where supported. Use workload identity, scoped KMS permissions and audited key access. Plan key rotation, overlapping validity, certificate expiry alerts and restore verification. Disabling a key can make otherwise intact backups unreadable; rehearse only in isolated staging.

## Audit evidence and controls

Capture UTC changes, policy versions, CODEOWNERS approval, access reviews, tenant boundary tests, retention reports, encryption configuration, KMS key history, deletion evidence and incident timelines. Apply tamper-evident storage and least-privilege access. Do not claim GDPR, HIPAA, SOC 2 or other compliance solely from these technical controls; legal applicability and independent audit review are separate.

## Example policy inventory

```yaml
dataset: application-logs
classification: confidential
owner: platform-sre
purpose: incident-response
retention_days: 30
residency: approved-region
encryption_in_transit: required
encryption_at_rest: required
redaction: before-ingest
legal_hold: approval-required
```

This is a governance inventory example, not a native Loki configuration.

## Staging privacy acceptance

1. Inject synthetic sensitive fields into a log, span and metric label.
2. Verify redaction or rejection before backend storage.
3. Test tenant A cannot read tenant B data.
4. Verify TLS and encrypted object-store policies.
5. Confirm retention/backup expiration evidence without deleting production data.
6. Rotate a test key and restore a staging backup.
7. Audit access and export attempts, including denied actions.
8. Document approvals, findings, remediation and SLO impact.

## Offline executable governance evidence gate

Save `healthy.json`:

```json
{
  "owner": "observability-governance",
  "environment": "staging",
  "change_id": "OBS-092",
  "reviewed": true,
  "privacy_verified": true,
  "audit_verified": true,
  "destructive_action": false,
  "checks": {
    "classification": true,
    "ownership": true,
    "data_flow": true,
    "residency": true,
    "retention_policy": true,
    "log_redaction": true,
    "span_redaction": true,
    "label_privacy": true,
    "tls": true,
    "encryption_rest": true,
    "kms": true,
    "key_rotation": true,
    "loki_retention": true,
    "tempo_retention": true,
    "prometheus_retention": true,
    "legal_hold": true,
    "audit_logs": true,
    "deletion": true,
    "backup_expiry": true,
    "incident_response": true
  }
}
```

Save `governance_gate.py`:

```python
"""Synthetic governance evidence gate; does not access real telemetry."""
import json,sys
from pathlib import Path
CHECKS=["classification","ownership","data_flow","residency","retention_policy","log_redaction","span_redaction","label_privacy","tls","encryption_rest","kms","key_rotation","loki_retention","tempo_retention","prometheus_retention","legal_hold","audit_logs","deletion","backup_expiry","incident_response"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 for k in ("reviewed","privacy_verified","audit_verified"):
  if p.get(k) is not True:e.append("missing "+k)
 c=p.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append("unverified "+k)
 if p.get("destructive_action") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());e=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not e else "FAIL","findings":e},indent=2));sys.exit(bool(e))

```

Save `test_governance_gate.py`:

```python
import copy,json,unittest
from pathlib import Path
from governance_gate import validate
class GovernanceTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["classification"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["ownership"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["data_flow"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["residency"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["retention_policy"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["log_redaction"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["span_redaction"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["label_privacy"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["tls"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["encryption_rest"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["kms"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["key_rotation"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["loki_retention"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["tempo_retention"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["prometheus_retention"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["legal_hold"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["checks"]["audit_logs"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["checks"]["deletion"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["checks"]["backup_expiry"]=False
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["checks"]["incident_response"]=False
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["reviewed"]=false
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["privacy_verified"]=false
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["audit_verified"]=false
  self.assertTrue(validate(p))
 def test_negative_27(self):
  p=copy.deepcopy(self.p)
  p["destructive_action"]=true
  self.assertTrue(validate(p))
 def test_negative_28(self):
  p=copy.deepcopy(self.p)
  p["checks"]=null
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 governance_gate.py healthy.json
python3 -m unittest -v test_governance_gate.py
```

Expected PASS and **30 authored tests**. This offline gate checks synthetic attestations only; live execution and independent compliance audit remain pending.

## 24 hands-on exercises

1. Classify metric data: record owner, policy, evidence, risk and safe rollback.
2. Classify logs: record owner, policy, evidence, risk and safe rollback.
3. Classify traces: record owner, policy, evidence, risk and safe rollback.
4. Identify data owners: record owner, policy, evidence, risk and safe rollback.
5. Map data flows: record owner, policy, evidence, risk and safe rollback.
6. Inventory regional boundaries: record owner, policy, evidence, risk and safe rollback.
7. Define lawful retention: record owner, policy, evidence, risk and safe rollback.
8. Configure log redaction: record owner, policy, evidence, risk and safe rollback.
9. Configure span redaction: record owner, policy, evidence, risk and safe rollback.
10. Audit label privacy: record owner, policy, evidence, risk and safe rollback.
11. Validate TLS: record owner, policy, evidence, risk and safe rollback.
12. Review encryption at rest: record owner, policy, evidence, risk and safe rollback.
13. Review KMS policies: record owner, policy, evidence, risk and safe rollback.
14. Test key rotation: record owner, policy, evidence, risk and safe rollback.
15. Review Loki retention: record owner, policy, evidence, risk and safe rollback.
16. Review Tempo retention: record owner, policy, evidence, risk and safe rollback.
17. Review Prometheus retention: record owner, policy, evidence, risk and safe rollback.
18. Test legal hold exceptions: record owner, policy, evidence, risk and safe rollback.
19. Validate access logging: record owner, policy, evidence, risk and safe rollback.
20. Export audit evidence: record owner, policy, evidence, risk and safe rollback.
21. Test deletion workflow: record owner, policy, evidence, risk and safe rollback.
22. Test backup expiry: record owner, policy, evidence, risk and safe rollback.
23. Simulate privacy incident: record owner, policy, evidence, risk and safe rollback.
24. Complete compliance review: record owner, policy, evidence, risk and safe rollback.

## 24 production incident scenarios

1. **PII in metrics:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
2. **PII in logs:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
3. **PII in spans:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
4. **SQL literal disclosure:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
5. **Cross-border telemetry:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
6. **Unauthorized retention extension:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
7. **Premature retention deletion:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
8. **Legal hold conflict:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
9. **Loki compactor misconfig:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
10. **Tempo block leakage:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
11. **Prometheus snapshot leak:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
12. **KMS key disabled:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
13. **TLS downgrade:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
14. **Expired certificate:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
15. **Unencrypted object bucket:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
16. **Audit log gap:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
17. **Audit tampering:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
18. **Unauthorized export:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
19. **Excessive Grafana access:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
20. **Secret in telemetry:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
21. **Backup retention mismatch:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
22. **Failed deletion verification:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
23. **Data subject request backlog:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.
24. **Incident evidence missing:** assess exposure, contain, preserve audit evidence, recover and prevent recurrence.

## Eight production runbooks

1. **Telemetry data discovery and classification:** define trigger, accountable approver, containment, evidence and restoration.
2. **Sensitive log/trace/metric containment:** define trigger, accountable approver, containment, evidence and restoration.
3. **Retention change and deletion approval:** define trigger, accountable approver, containment, evidence and restoration.
4. **Encryption and KMS incident response:** define trigger, accountable approver, containment, evidence and restoration.
5. **Cross-region residency and transfer review:** define trigger, accountable approver, containment, evidence and restoration.
6. **Legal hold and backup lifecycle governance:** define trigger, accountable approver, containment, evidence and restoration.
7. **Audit evidence collection and access review:** define trigger, accountable approver, containment, evidence and restoration.
8. **Privacy incident escalation and postmortem:** define trigger, accountable approver, containment, evidence and restoration.

## 100-point assessment

| Domain | Points |
|---|---:|
| Data inventory, ownership and classification | 20 |
| Privacy, minimization and redaction | 20 |
| Retention, legal holds and backup lifecycle | 20 |
| Encryption, identity and residency | 20 |
| Audit evidence, incidents and compliance readiness | 20 |
| **Total** | **100** |

Recommended passing score 85/100 with no unresolved critical privacy exposures. Production acceptance requires security, legal/compliance and service-owner sign-off.

**Companion:** [Chapter 092 lab](labs/092-observability-data-governance-privacy-retention-encryption-audit-compliance-lab.md).

**Next:** Chapter 093 — Enterprise Observability Security Monitoring, Threat Detection and Incident Response Automation.
