# Chapter 079 — Enterprise Incident Communications, Postmortems and Corrective Action Tracking

**Part 16 — Incident Response and Troubleshooting (4/5)**  
**Audience:** SRE, DBRE, incident commanders, service owners, customer communications and platform leads.  
**Prerequisites:** Chapters 076–078.

## Learning outcomes

Design incident communications that are timely, accurate, audience-aware and privacy-safe; lead blameless postmortems; convert contributing factors into measurable corrective actions; track action effectiveness and repeat incidents.

## Reference workflow

```text
User impact + SLO burn -> incident command
                              |
                       communications lead
                      /       |        \
                  on-call  leadership   customers
                      \       |        /
                      verified UTC updates
                              |
                  recovery + stable SLIs
                              |
                  blameless postmortem
                              |
                 actions / owner / due date
                              |
                   effectiveness checks
                              |
                    reliability review
```

## Incident communications theory

Incident communications are distinct from technical diagnosis. The communications lead translates verified impact and mitigation into updates with a consistent UTC timestamp and next update commitment. Maintain separate internal, executive, customer and security audiences. Acknowledging uncertainty is preferable to declaring an unverified root cause.

| Stage | Required content |
|---|---|
| Declared | incident ID, severity, known impact, owner and next update |
| Investigating | verified symptoms, scope, evidence and actions |
| Mitigating | action underway, remaining customer impact and next update |
| Monitoring | independent SLI recovery and stability window |
| Resolved | verified recovery time, residual risks and review commitment |

Do not expose patient information, credentials, internal endpoints or unapproved customer data. Use access-controlled incident channels and approved customer notification processes.

## Postmortem and causal analysis

Use a blameless approach that examines system conditions and decision context, not individual blame. Preserve an event timeline with alerts, customer reports, deploys, SLO burn, mitigations and recovery. Separate *trigger*, *contributing factors*, *detection gaps* and *root-cause confidence*. Counterfactual claims require evidence.

## Corrective action lifecycle

Each action requires an accountable owner, deadline, priority, measurable acceptance criteria, supporting evidence and follow-up verification. Prefer changes that reduce blast radius or improve detection over vague tasks like “monitor more.” Review repeat incidents, overdue actions and residual error-budget exposure monthly.

## Production scenario

A release introduces increased PostgreSQL connection demand, triggering API p99 degradation and Kafka-to-Snowflake freshness delay. The incident commander coordinates a safe rollback while communications sends verified updates. The postmortem distinguishes the deployment trigger from insufficient pool backpressure, missing alert ownership and stale runbooks. Assign independent corrective actions and verify them with staging tests.

## Communications examples

Initial update:

```text
INC-079 | SEV2 | 2026-10-19 20:00 UTC
We are investigating increased API latency affecting a subset of requests.
Mitigation is underway; impact and duration are being verified.
Next update: 20:30 UTC.
```

Recovery update:

```text
INC-079 | Monitoring
API error rate and latency have returned to the defined SLO range.
We are verifying sustained recovery and data freshness before closure.
Next update: [UTC].
```

The timestamps above are illustrative only.

## Executable offline governance gate

### healthy.json

```json
{
  "owner": "incident-comms-sre",
  "environment": "staging",
  "incident_id": "INC-079",
  "severity": "SEV2",
  "verified_customer_impact": true,
  "blameless_review": true,
  "corrective_action_assigned": true,
  "destructive_action": false,
  "controls": {
    "communications_owner": true,
    "stakeholder_map": true,
    "severity": true,
    "impact": true,
    "utc_timeline": true,
    "update_cadence": true,
    "internal_update": true,
    "external_update": true,
    "privacy": true,
    "evidence": true,
    "mitigation": true,
    "recovery": true,
    "postmortem": true,
    "action_owner": true,
    "action_deadline": true,
    "effectiveness": true,
    "review": true
  }
}
```

### comms_gate.py

```python
"""Synthetic communications and postmortem acceptance gate."""
import json,sys
from pathlib import Path
CONTROLS=["communications_owner","stakeholder_map","severity","impact","utc_timeline","update_cadence","internal_update","external_update","privacy","evidence","mitigation","recovery","postmortem","action_owner","action_deadline","effectiveness","review"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","incident_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 if p.get("severity") not in ("SEV1","SEV2","SEV3"):e.append("invalid severity")
 for k in ("verified_customer_impact","blameless_review","corrective_action_assigned"):
  if p.get(k) is not True:e.append("missing "+k)
 c=p.get("controls")
 if not isinstance(c,dict):e.append("invalid controls");c={}
 for k in CONTROLS:
  if c.get(k) is not True:e.append("unverified "+k)
 if p.get("destructive_action") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());e=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not e else "FAIL","findings":e},indent=2));sys.exit(bool(e))

```

### test_comms_gate.py

```python
import copy,json,unittest
from pathlib import Path
from comms_gate import validate
class CommunicationsTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["controls"]["communications_owner"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["controls"]["stakeholder_map"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["controls"]["severity"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["controls"]["impact"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["controls"]["utc_timeline"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["controls"]["update_cadence"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["controls"]["internal_update"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["controls"]["external_update"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["controls"]["privacy"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["controls"]["evidence"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["controls"]["mitigation"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["controls"]["recovery"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["controls"]["postmortem"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["controls"]["action_owner"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["controls"]["action_deadline"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["controls"]["effectiveness"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["controls"]["review"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["incident_id"]=""
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["severity"]="SEV0"
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["verified_customer_impact"]=false
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["blameless_review"]=false
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["corrective_action_assigned"]=false
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["destructive_action"]=true
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["controls"]=null
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 comms_gate.py healthy.json
python3 -m unittest -v test_comms_gate.py
```

Expected PASS and **28 authored tests**. Execution pending; synthetic attestations do not demonstrate real incident communication.

## 24 hands-on exercises

1. Declare incident.
2. Assign communications lead.
3. Identify stakeholder groups.
4. Set update cadence.
5. Draft initial notice.
6. Verify affected scope.
7. Confirm SLO evidence.
8. Build UTC timeline.
9. Record change markers.
10. Document mitigation owners.
11. Publish internal update.
12. Publish external update.
13. Redact sensitive data.
14. Capture customer questions.
15. Record recovery criteria.
16. Publish recovery update.
17. Preserve evidence links.
18. Facilitate blameless review.
19. Build causal graph.
20. Separate triggers and factors.
21. Create corrective actions.
22. Set accountable owners.
23. Validate action effectiveness.
24. Hold reliability review.

## 24 production incident scenarios

1. **SEV1 API outage:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
2. **Partial customer impact:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
3. **Incorrect initial severity:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
4. **Status update delay:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
5. **Conflicting team messages:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
6. **Unverified root cause claim:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
7. **PHI leaked in update:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
8. **Credential in log excerpt:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
9. **Regional outage:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
10. **PostgreSQL failover:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
11. **Redis saturation:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
12. **Kafka processing backlog:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
13. **Elasticsearch query failures:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
14. **Snowflake freshness breach:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
15. **Kubernetes deployment regression:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
16. **Telemetry missing:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
17. **Incident timeline gap:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
18. **Customer report conflicts:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
19. **Premature resolved status:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
20. **Repeated incidents:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
21. **Unowned corrective action:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
22. **Overdue remediation:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
23. **Weak postmortem evidence:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.
24. **Failed effectiveness check:** draft verified communication, capture evidence, assign corrective owner and define effectiveness check.

## Eight production runbooks

1. **Incident communications: declare audience, lead, verified impact and next UTC update.**
2. **Stakeholder routing: separate internal technical, leadership, customer and security channels.**
3. **Evidence handling: redact sensitive content, preserve immutable UTC timeline and access controls.**
4. **Recovery update: independently verify user-facing SLIs, freshness and stable observation.**
5. **Postmortem facilitation: build blameless timeline and test causal hypotheses.**
6. **Corrective action creation: assign owner, deadline, risk and measurable acceptance criterion.**
7. **Action verification: test in staging, verify production signals and close with evidence.**
8. **Reliability review: aggregate repeat incidents, action aging and SLO/error-budget trends.**

## 100-point assessment

| Domain | Points |
|---|---:|
| Stakeholder communications and updates | 20 |
| Privacy and evidence handling | 20 |
| Causal analysis and postmortem | 20 |
| Corrective action ownership and tests | 20 |
| Effectiveness verification and reliability review | 20 |
| **Total** | **100** |

Suggested pass: 85/100. Production sign-off requires reviewed communications, witnessed tabletop, action-owner approval and effectiveness evidence.

**Companion:** [Chapter 079 lab](labs/079-enterprise-incident-communications-postmortems-corrective-action-tracking-lab.md).

**Next:** Chapter 080 — Enterprise Incident Response, Troubleshooting and Reliability Acceptance Capstone.
