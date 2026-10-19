# Chapter 076 — Enterprise Incident Response Architecture, Severity Models and On-Call Operations

**Part 16 — Incident Response and Troubleshooting (1/5)**

## Objectives and architecture

Build production incident command across Kubernetes, PostgreSQL, Redis, Kafka, Elasticsearch/OpenSearch, Snowflake and API services. Design on-call ownership, severity, escalation, customer communication, evidence collection, reversible mitigation and postmortem.

```text
Users / SLIs / RED / USE / logs / traces
                  |
       Grafana / Prometheus / Alertmanager
                  |
        primary -> secondary on-call
                  |
           incident commander
           /       |       \
       operations  comms   scribe
           \       |       /
          mitigation / rollback
                  |
       independent SLI recovery
                  |
             postmortem
```

## Severity and operational theory

| Severity | Customer impact | Response |
|---|---|---|
| SEV1 | critical user journey unavailable or major data integrity threat | immediate incident command and urgent updates |
| SEV2 | significant partial outage, sustained latency or freshness degradation | coordinated response |
| SEV3 | limited degradation and workaround | managed on-call investigation |

Severity is based on verified user impact, criticality and duration—not CPU alone. Assign incident commander, operations lead, communications lead and scribe. Keep UTC timeline, escalation routes, least-privilege access and audited decisions. Use independent SLO burn and RED metrics for impact, USE metrics for saturation, traces/logs for dependencies and release markers for correlation.

## Operational lifecycle

1. Detect and verify user impact and affected scope.
2. Declare severity, commander and incident ID.
3. Stabilize and pause nonessential risky changes.
4. Correlate API metrics with PostgreSQL pool/locks, Redis hot keys, Kafka lag, Elasticsearch rejections, Snowflake freshness and Kubernetes throttling.
5. Escalate to service owners and specialist DBRE/platform teams.
6. Apply reversible mitigation and document rollback criteria.
7. Communicate verified impact and next update time.
8. Confirm independent SLI recovery and complete blameless review.

## Communications template

```text
Incident / severity / UTC:
Verified customer impact:
Known evidence:
Mitigation / owner:
Next update UTC:
```

Never include credentials, PHI/PII or speculative causes.

## Executable synthetic readiness gate

Save `healthy.json`:

```json
{"owner":"enterprise-sre","environment":"staging","incident_id":"INC-076","severity":"SEV2","commander_assigned":true,"communications_owner_assigned":true,"user_impact_confirmed":true,"destructive_action":false,"checks":{"ownership":true,"severity":true,"oncall":true,"escalation":true,"incident_command":true,"communications":true,"timeline":true,"user_impact":true,"slo_evidence":true,"red_use":true,"tracing":true,"dependency_map":true,"security":true,"mitigation":true,"recovery":true,"postmortem":true}}
```

Save `incident_gate.py`:

```python
import json,sys
from pathlib import Path
CHECKS=("ownership","severity","oncall","escalation","incident_command","communications","timeline","user_impact","slo_evidence","red_use","tracing","dependency_map","security","mitigation","recovery","postmortem")
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","incident_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 if p.get("severity") not in ("SEV1","SEV2","SEV3"):e.append("invalid severity")
 for k in ("commander_assigned","communications_owner_assigned","user_impact_confirmed"):
  if p.get(k) is not True:e.append("missing "+k)
 c=p.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append("unverified "+k)
 if p.get("destructive_action") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 p=json.loads(Path(sys.argv[1]).read_text());e=validate(p)
 print(json.dumps({"status":"PASS" if not e else "FAIL","findings":e},indent=2));sys.exit(bool(e))
```

Save `test_incident_gate.py`:

```python
import copy,json,unittest
from pathlib import Path
from incident_gate import validate,CHECKS
class IncidentTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_missing_each_control(self):
  for k in CHECKS:
   with self.subTest(control=k):
    p=copy.deepcopy(self.p);p["checks"][k]=False
    self.assertTrue(validate(p))
 def test_unsafe(self):
  p=copy.deepcopy(self.p);p["environment"]="production";self.assertTrue(validate(p))
 def test_invalid_severity(self):
  p=copy.deepcopy(self.p);p["severity"]="SEV0";self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()
```

```bash
python3 incident_gate.py healthy.json
python3 -m unittest -v test_incident_gate.py
```

Four authored test methods plus 16 parameterized control subtests. Execution pending.

## 24 hands-on exercises

1. Define incident taxonomy.
2. Map service ownership.
3. Document primary rotation.
4. Document secondary escalation.
5. Assign incident commander.
6. Assign operations lead.
7. Assign communications lead.
8. Assign scribe.
9. Define SEV1 impact.
10. Define SEV2 impact.
11. Define SEV3 impact.
12. Map customer journeys.
13. Review SLO burn.
14. Create incident channel.
15. Capture UTC timeline.
16. Draft stakeholder update.
17. Correlate metrics/logs/traces.
18. Review dependency map.
19. Test nonproduction paging.
20. Run tabletop.
21. Exercise escalation.
22. Rehearse safe mitigation.
23. Verify recovery.
24. Conduct postmortem.

## 24 production failure scenarios

1. API outage.
2. Regional partial failure.
3. PostgreSQL pool exhaustion.
4. Redis hot key.
5. Kafka consumer lag.
6. Elasticsearch query timeouts.
7. Snowflake freshness breach.
8. Kubernetes CrashLoopBackOff.
9. Node disk pressure.
10. Collector telemetry loss.
11. Prometheus scrape outage.
12. False-positive page.
13. Missed page.
14. On-call handoff failure.
15. Unclear ownership.
16. Competing incident commanders.
17. Underestimated impact.
18. Error-budget burn spike.
19. Retry storm.
20. Rollback failure.
21. Unapproved change.
22. Sensitive logs exposed.
23. Delayed status update.
24. Recurring incident.

For each scenario, record customer impact, severity, evidence, mitigation owner, escalation and independent recovery checks.

## Eight production runbooks

1. Declare incident and record UTC, impact and severity.
2. Assign command roles and preserve timeline.
3. Correlate RED, USE, traces, logs, deployments and dependencies.
4. Escalate through primary/secondary and specialist teams.
5. Communicate verified impact, action owners and next update.
6. Mitigate with approved reversible changes and rollback.
7. Verify recovery via independent user-facing SLIs.
8. Review contributing factors and assign follow-up owners.

## 100-point assessment

| Area | Points |
|---|---:|
| Severity, ownership and on-call | 20 |
| Detection, triage and SLO evidence | 20 |
| Incident command and communications | 20 |
| Safe mitigation and validation | 20 |
| Recovery and postmortem | 20 |
| **Total** | **100** |

Recommended pass 85/100. Live paging and game-day execution remain pending.

**Companion:** [Chapter 076 lab](labs/076-enterprise-incident-response-architecture-severity-models-on-call-operations-lab.md).

**Next:** Chapter 077 — Enterprise Incident Triage, Signal Correlation and Root Cause Investigation.
