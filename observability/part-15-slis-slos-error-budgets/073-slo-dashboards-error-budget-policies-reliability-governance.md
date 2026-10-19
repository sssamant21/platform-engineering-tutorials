# Chapter 073 — SLO Dashboards, Error Budget Policies and Reliability Governance

**Part 15 — SLIs, SLOs and Error Budgets (3/5)**

## Goals and architecture

Connect user-facing SLI event counters to Prometheus recording rules, Grafana dashboards, multiwindow burn alerts, service-owner decisions, release controls and audit evidence. Cover API availability and latency, PostgreSQL/Redis dependency health and Kafka/Snowflake freshness.

```text
User journeys -> good/total counters -> Prometheus -> Grafana SLO dashboards
                                          |               |
                                    burn alerts      error budgets
                                          \               /
                                      service-owner review
                                              |
                                    change gate / rollback
```

## Detailed theory

A **request-based SLI** is the fraction of eligible events that meet a declared threshold. A 99.9% objective allows 0.1% bad events in its window. For 1,000,000 eligible requests, 1,000 may be bad; if 400 are bad, 600 remain. A 30-day rolling window differs from a calendar month. Error-budget policy should respond to *current burn* and *remaining budget*, not a green dashboard alone.

| Panel | Evidence | Decision |
|---|---|---|
| Availability | eligible successful / total events | user-facing reliability |
| Latency | under-threshold histogram bucket / total | latency objective |
| Freshness | within lateness bound / eligible deliveries | data pipeline SLO |
| Budget | allowed, consumed and remaining bad events | change risk |
| Burn | 5m/1h and 30m/6h windows | page or ticket |
| Telemetry | scrape gaps and absent series | unknown vs healthy |
| Release | deployment and incident annotations | rollback correlation |

**PromQL example** (adapt metric names and status labels):

```promql
100 * (1 -
  (sum(increase(http_requests_total{job="api",code=~"5.."}[30d]))
   / clamp_min(sum(increase(http_requests_total{job="api"}[30d])),1))
  / 0.001)
```

This represents *remaining budget percentage*, not availability. It can be negative after exhaustion. Treat absent metrics, low traffic, counter resets and dashboard permissions separately. Never put customer identifiers, raw URLs or patient data in metric labels.

## Governance and incident practice

Normal budget: approved releases. Rapid burn: review and pause risky rollout. Low budget: prioritize reliability work. Exhaustion: restrict nonessential risky changes under documented policy, while preserving emergency security and recovery exceptions with owner approval and expiry.

During an API error spike accompanied by PostgreSQL connection waits and Kafka-to-Snowflake freshness delay, validate live source counters before trusting Grafana. Review the burn alert, record the incident commander and service owner, execute a reversible mitigation, and confirm independent SLI recovery.

## Executable offline gate

Save `healthy.json`:

```json
{
  "owner": "slo-governance",
  "change_id": "OBS-073",
  "environment": "staging",
  "total_events": 1000000,
  "bad_events": 400,
  "objective_percent": 99.9,
  "policy": "normal",
  "destructive_change": false,
  "checks": {
    "sli_owner": true,
    "eligibility": true,
    "objective": true,
    "dashboard": true,
    "burn_panels": true,
    "missing_data": true,
    "deploy_annotations": true,
    "incident_annotations": true,
    "alert_routing": true,
    "budget_policy": true,
    "change_gate": true,
    "exception_approval": true,
    "privacy": true,
    "access_review": true,
    "rollback": true,
    "audit_evidence": true
  }
}
```

Save `governance_gate.py`:

```python
import json,sys
from pathlib import Path
REQUIRED=["sli_owner","eligibility","objective","dashboard","burn_panels","missing_data","deploy_annotations","incident_annotations","alert_routing","budget_policy","change_gate","exception_approval","privacy","access_review","rollback","audit_evidence"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 c=p.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in REQUIRED:
  if c.get(k) is not True:e.append("unverified "+k)
 n,b,o=p.get("total_events"),p.get("bad_events"),p.get("objective_percent")
 if type(n) is not int or n<=0:e.append("invalid total")
 if type(b) is not int or b<0:e.append("invalid bad")
 if type(n) is int and type(b) is int and b>n:e.append("bad exceeds total")
 if type(o) not in (int,float) or not 0<o<100:e.append("invalid objective")
 if type(n) is int and n>0 and type(b) is int and 0<=b<=n and type(o) in (int,float) and 0<o<100 and b>n*(1-o/100)+1e-9:e.append("budget exhausted")
 if p.get("policy") not in ("normal","restricted"):e.append("invalid policy")
 if p.get("destructive_change") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 p=json.loads(Path(sys.argv[1]).read_text());e=validate(p)
 print(json.dumps({"status":"PASS" if not e else "FAIL","findings":e},indent=2));sys.exit(bool(e))
```

Save `test_governance_gate.py`:

```python
import copy,json,unittest
from pathlib import Path
from governance_gate import validate
class GovernanceTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_missing_control_1(self):
  p=copy.deepcopy(self.p);p["checks"]["sli_owner"]=False
  self.assertTrue(validate(p))
 def test_missing_control_2(self):
  p=copy.deepcopy(self.p);p["checks"]["eligibility"]=False
  self.assertTrue(validate(p))
 def test_missing_control_3(self):
  p=copy.deepcopy(self.p);p["checks"]["objective"]=False
  self.assertTrue(validate(p))
 def test_missing_control_4(self):
  p=copy.deepcopy(self.p);p["checks"]["dashboard"]=False
  self.assertTrue(validate(p))
 def test_missing_control_5(self):
  p=copy.deepcopy(self.p);p["checks"]["burn_panels"]=False
  self.assertTrue(validate(p))
 def test_missing_control_6(self):
  p=copy.deepcopy(self.p);p["checks"]["missing_data"]=False
  self.assertTrue(validate(p))
 def test_missing_control_7(self):
  p=copy.deepcopy(self.p);p["checks"]["deploy_annotations"]=False
  self.assertTrue(validate(p))
 def test_missing_control_8(self):
  p=copy.deepcopy(self.p);p["checks"]["incident_annotations"]=False
  self.assertTrue(validate(p))
 def test_missing_control_9(self):
  p=copy.deepcopy(self.p);p["checks"]["alert_routing"]=False
  self.assertTrue(validate(p))
 def test_missing_control_10(self):
  p=copy.deepcopy(self.p);p["checks"]["budget_policy"]=False
  self.assertTrue(validate(p))
 def test_missing_control_11(self):
  p=copy.deepcopy(self.p);p["checks"]["change_gate"]=False
  self.assertTrue(validate(p))
 def test_missing_control_12(self):
  p=copy.deepcopy(self.p);p["checks"]["exception_approval"]=False
  self.assertTrue(validate(p))
 def test_missing_control_13(self):
  p=copy.deepcopy(self.p);p["checks"]["privacy"]=False
  self.assertTrue(validate(p))
 def test_missing_control_14(self):
  p=copy.deepcopy(self.p);p["checks"]["access_review"]=False
  self.assertTrue(validate(p))
 def test_missing_control_15(self):
  p=copy.deepcopy(self.p);p["checks"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_missing_control_16(self):
  p=copy.deepcopy(self.p);p["checks"]["audit_evidence"]=False
  self.assertTrue(validate(p))
 def test_exhausted(self):
  p=copy.deepcopy(self.p);p["bad_events"]=5000;self.assertTrue(validate(p))
 def test_unsafe(self):
  p=copy.deepcopy(self.p);p["environment"]="production";self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()
```

```bash
python3 governance_gate.py healthy.json
python3 -m unittest -v test_governance_gate.py
```

**20 authored tests**; live execution pending. This gate validates synthetic attestations, not actual dashboards or approval.

## 24 hands-on exercises

1. Define user journey; record owner, expected result, evidence and rollback.
2. Confirm SLI ownership; record owner, expected result, evidence and rollback.
3. Define eligible events; record owner, expected result, evidence and rollback.
4. Validate rolling window; record owner, expected result, evidence and rollback.
5. Compute availability; record owner, expected result, evidence and rollback.
6. Compute latency good-event ratio; record owner, expected result, evidence and rollback.
7. Compute freshness; record owner, expected result, evidence and rollback.
8. Compute allowed budget; record owner, expected result, evidence and rollback.
9. Compute remaining budget; record owner, expected result, evidence and rollback.
10. Build Grafana SLO panel; record owner, expected result, evidence and rollback.
11. Build burn panel; record owner, expected result, evidence and rollback.
12. Annotate deployments; record owner, expected result, evidence and rollback.
13. Annotate incidents; record owner, expected result, evidence and rollback.
14. Validate no-data state; record owner, expected result, evidence and rollback.
15. Validate dashboard permissions; record owner, expected result, evidence and rollback.
16. Review policy tiers; record owner, expected result, evidence and rollback.
17. Review exhausted budget; record owner, expected result, evidence and rollback.
18. Review emergency exceptions; record owner, expected result, evidence and rollback.
19. Test alert routing; record owner, expected result, evidence and rollback.
20. Review low-traffic case; record owner, expected result, evidence and rollback.
21. Simulate burn; record owner, expected result, evidence and rollback.
22. Review risky rollout; record owner, expected result, evidence and rollback.
23. Rehearse rollback; record owner, expected result, evidence and rollback.
24. Record audit evidence; record owner, expected result, evidence and rollback.

## 24 production failure scenarios

1. **Wrong denominator:** investigate user impact, metric correctness, change governance and recovery.
2. **Stale Grafana data:** investigate user impact, metric correctness, change governance and recovery.
3. **Silent scrape failure:** investigate user impact, metric correctness, change governance and recovery.
4. **Missing burn alert:** investigate user impact, metric correctness, change governance and recovery.
5. **Budget reset misunderstanding:** investigate user impact, metric correctness, change governance and recovery.
6. **Timezone mismatch:** investigate user impact, metric correctness, change governance and recovery.
7. **Calendar vs rolling confusion:** investigate user impact, metric correctness, change governance and recovery.
8. **Invalid latency histogram:** investigate user impact, metric correctness, change governance and recovery.
9. **Incorrect p95 aggregation:** investigate user impact, metric correctness, change governance and recovery.
10. **Freshness clock skew:** investigate user impact, metric correctness, change governance and recovery.
11. **Unowned SLO:** investigate user impact, metric correctness, change governance and recovery.
12. **Unapproved objective change:** investigate user impact, metric correctness, change governance and recovery.
13. **Release gate bypass:** investigate user impact, metric correctness, change governance and recovery.
14. **Emergency fix blocked:** investigate user impact, metric correctness, change governance and recovery.
15. **Exception undocumented:** investigate user impact, metric correctness, change governance and recovery.
16. **Dashboard permissions leak:** investigate user impact, metric correctness, change governance and recovery.
17. **High-cardinality labels:** investigate user impact, metric correctness, change governance and recovery.
18. **Duplicate SLI series:** investigate user impact, metric correctness, change governance and recovery.
19. **Counter reset:** investigate user impact, metric correctness, change governance and recovery.
20. **Low traffic false green:** investigate user impact, metric correctness, change governance and recovery.
21. **Dependency outage:** investigate user impact, metric correctness, change governance and recovery.
22. **SLO mismatch with SLA:** investigate user impact, metric correctness, change governance and recovery.
23. **Risky rollout during burn:** investigate user impact, metric correctness, change governance and recovery.
24. **Rollback verification missing:** investigate user impact, metric correctness, change governance and recovery.

## Eight production runbooks

1. Dashboard stale: compare Prometheus raw counters, scrape health and panel windows.
2. Budget review: compute allowed/consumed/remaining events on the same rolling window.
3. Release gate: document budget status, change risk and approver.
4. Fast burn: validate user impact and page routing.
5. Slow burn: prioritize systemic remediation and tickets.
6. SLO ownership: document eligibility, target, exclusions and review cadence.
7. Security: validate access isolation, redaction and audit records.
8. Recovery: approve rollback, verify SLI improvement and document postmortem.

## 100-point assessment

| Domain | Points |
|---|---:|
| SLO dashboards and SLI integrity | 20 |
| Error-budget mathematics | 20 |
| Change governance and exceptions | 20 |
| Security and offline tests | 20 |
| Incident recovery and audit | 20 |
| **Total** | **100** |

Suggested pass: 85/100. Production sign-off requires witnessed dashboard validation and service-owner approval.

**Companion:** [Chapter 073 lab](labs/073-slo-dashboards-error-budget-policies-reliability-governance-lab.md).

**Next:** Chapter 074 — SLO-Based Incident Prioritization, Error Budget Forecasting and Reliability Reviews.
