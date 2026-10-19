# Chapter 075 — Enterprise SLI/SLO and Error Budget Reliability Acceptance Capstone

**Part 15 — SLIs, SLOs and Error Budgets: Final Capstone (5/5)**  
**Audience:** Enterprise SRE, DBRE, platform engineering, service owners and incident commanders.  
**Prerequisites:** Chapters 071–074.

## Mission and acceptance criteria

Demonstrate a defensible user-facing SLO program: SLI contracts, Prometheus recording rules, Grafana dashboards, multiwindow burn alerts, error-budget policy, forecasting caveats, incident severity, audited change governance and independently verified recovery.

## Reference architecture

```text
Users -> API -> PostgreSQL / Redis / Elasticsearch
              |          |
              +-> Kafka -> Snowflake freshness
              |
         good / total events + latency histograms
              |
        Prometheus recording rules
              |
       5m/1h + 30m/6h burn alerts
              |
       Grafana + Alertmanager -> on-call
              |
       SLO review / change approval / rollback
```

## SLO design theory

An SLI contract defines the user journey, eligibility, numerator, denominator, exclusions, owner and time window. Request-based availability differs from time-based availability. A latency SLI measures the fraction of eligible requests below a declared threshold; do not average per-instance p95. Kafka lag and PostgreSQL CPU are diagnostic signals, not substitutes for user-visible freshness and availability.

For a 99.9% SLO over 1,000,000 eligible requests, 1,000 bad events are allowed. With 450 bad events, 45% of budget is consumed and 550 events remain. Error-budget calculations must use the same population and window as the SLO. Rolling-window expiration makes simple exhaustion forecasts approximate.

## Multiwindow alerting

For a 30-day 99.9% objective, a common fast-burn alert requires **both 5m and 1h** bad-event ratios to exceed 14.4 × 0.001; a slower alert uses **both 30m and 6h** at 6 × 0.001. Validate rule labels, missing-data behavior, low traffic, counter resets and Alertmanager routing before release. Tune severity to real customer impact.

```promql
# Illustrative API error ratio; verify actual metric labels.
sum(rate(http_requests_total{job="api",code=~"5.."}[5m]))
/
clamp_min(sum(rate(http_requests_total{job="api"}[5m])), 1e-9)
```

Pair with an independent 1h expression and a minimum-traffic/absent-series guard. Do not interpret no traffic as 100% availability.

## Incident acceptance game day

After a rollout, API 5xx and p99 latency rise while PostgreSQL pool waits and Redis hot-key latency increase. Kafka-to-Snowflake freshness also breaches its separate SLO. Verify independent user impact, check paired burn windows, distinguish service failures from telemetry gaps, classify incident severity, stop risky rollout, perform approved rollback and document budget consumed.

## Change governance

| Budget state | Acceptance decision |
|---|---|
| Healthy | approved normal release process |
| Fast burn | investigate and pause nonessential risky rollout |
| Low remaining | owner review and additional validation |
| Exhausted | restrict nonessential changes under documented policy |
| Emergency recovery/security | documented time-bound exception |

SLO policy must not prevent urgent recovery or security fixes. Store service-owner sign-off, exception approvals and evidence with appropriate access controls.

## Executable offline acceptance gate

The following is a **synthetic manifest check**, not a live observability validation.

### healthy.json

```json
{
  "owner": "enterprise-sre",
  "environment": "staging",
  "change_id": "OBS-075",
  "window_days": 30,
  "total_events": 1000000,
  "bad_events": 450,
  "objective_percent": 99.9,
  "latency_good_events": 997000,
  "latency_objective_percent": 99.5,
  "destructive_change": false,
  "controls": {
    "owner": true,
    "user_journey": true,
    "eligibility": true,
    "availability": true,
    "latency": true,
    "freshness": true,
    "objective": true,
    "budget": true,
    "burn_alerts": true,
    "recording_rules": true,
    "promtool": true,
    "alert_routing": true,
    "dashboard": true,
    "missing_data": true,
    "privacy": true,
    "rollback": true,
    "review": true,
    "evidence": true
  }
}
```

### slo_acceptance_gate.py

```python
"""Offline synthetic SLO acceptance gate; does not access production."""
import json,sys
from pathlib import Path
CONTROLS=["owner","user_journey","eligibility","availability","latency","freshness","objective","budget","burn_alerts","recording_rules","promtool","alert_routing","dashboard","missing_data","privacy","rollback","review","evidence"]
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["expected object"]
 for k in ("owner","environment","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 c=p.get("controls")
 if not isinstance(c,dict):e.append("invalid controls");c={}
 for k in CONTROLS:
  if c.get(k) is not True:e.append("unverified "+k)
 n,b,g=p.get("total_events"),p.get("bad_events"),p.get("latency_good_events")
 if type(n) is not int or n<=0:e.append("invalid total")
 if type(b) is not int or b<0:e.append("invalid bad")
 if type(g) is not int or g<0:e.append("invalid latency good")
 if type(n) is int and type(b) is int and b>n:e.append("bad exceeds total")
 if type(n) is int and type(g) is int and g>n:e.append("good exceeds total")
 if type(p.get("window_days")) is not int or p["window_days"]<=0:e.append("invalid window")
 for k in ("objective_percent","latency_objective_percent"):
  x=p.get(k)
  if type(x) not in (int,float) or not 0<x<100:e.append("invalid "+k)
 for a,threshold,good in (("bad_events","objective_percent",False),("latency_good_events","latency_objective_percent",True)):
  x,o=p.get(a),p.get(threshold)
  if type(n) is int and n>0 and type(x) is int and 0<=x<=n and type(o) in (int,float) and 0<o<100:
   ratio=(x/n*100 if good else (n-x)/n*100)
   if ratio<o-1e-10:e.append("SLO breach "+a)
 if p.get("destructive_change") is not False:e.append("unsafe action")
 return e
def budget(p):
 allowed=p["total_events"]*(1-p["objective_percent"]/100)
 return {"allowed_bad_events":round(allowed,2),"remaining_bad_events":round(allowed-p["bad_events"],2),"consumed_percent":round(p["bad_events"]/allowed*100,2)}
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());findings=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 result={"status":"PASS" if not findings else "FAIL","findings":findings}
 if not findings:result["budget"]=budget(p)
 print(json.dumps(result,indent=2));sys.exit(bool(findings))

```

### test_slo_acceptance_gate.py

```python
import copy,json,unittest
from pathlib import Path
from slo_acceptance_gate import validate,budget
class AcceptanceTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_budget(self):self.assertAlmostEqual(budget(self.p)["remaining_bad_events"],550)
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["controls"]["owner"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["controls"]["user_journey"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["controls"]["eligibility"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["controls"]["availability"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["controls"]["latency"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["controls"]["freshness"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["controls"]["objective"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["controls"]["budget"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["controls"]["burn_alerts"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["controls"]["recording_rules"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["controls"]["promtool"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["controls"]["alert_routing"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["controls"]["dashboard"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["controls"]["missing_data"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["controls"]["privacy"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["controls"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["controls"]["review"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["controls"]["evidence"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["window_days"]=0
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["total_events"]=0
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["bad_events"]=2000000
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["bad_events"]=5000
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["objective_percent"]=100
  self.assertTrue(validate(p))
 def test_negative_27(self):
  p=copy.deepcopy(self.p)
  p["latency_good_events"]=1
  self.assertTrue(validate(p))
 def test_negative_28(self):
  p=copy.deepcopy(self.p)
  p["latency_objective_percent"]=-1
  self.assertTrue(validate(p))
 def test_negative_29(self):
  p=copy.deepcopy(self.p)
  p["destructive_change"]=true
  self.assertTrue(validate(p))
 def test_negative_30(self):
  p=copy.deepcopy(self.p)
  p["controls"]=None
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 slo_acceptance_gate.py healthy.json
python3 -m unittest -v test_slo_acceptance_gate.py
```

Expected PASS and **33 authored tests**. Runtime execution is not claimed.

## 24 hands-on exercises

1. Define critical user journey.
2. Set service ownership.
3. Define eligible request population.
4. Define good-event semantics.
5. Define latency threshold.
6. Define data freshness SLI.
7. Validate counter labels.
8. Review histogram buckets.
9. Set 30-day objective.
10. Calculate allowed failures.
11. Calculate consumed budget.
12. Calculate remaining budget.
13. Build 5m and 1h burn.
14. Build 30m and 6h burn.
15. Validate rule syntax.
16. Test alert routing.
17. Build Grafana SLO board.
18. Test no-data handling.
19. Review forecast assumptions.
20. Simulate dependency incident.
21. Classify customer severity.
22. Apply change-risk policy.
23. Rehearse rollback.
24. Present acceptance review.

## 24 production incident scenarios

1. **5xx spike:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
2. **p99 latency regression:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
3. **PostgreSQL pool exhaustion:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
4. **Redis hot-key contention:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
5. **Kafka consumer lag:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
6. **Snowflake CDC delay:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
7. **Elasticsearch search rejection:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
8. **Counter reset:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
9. **Zero traffic:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
10. **Missing scrape:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
11. **Missing recording rule:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
12. **Incorrect metric label:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
13. **Invalid histogram bucket:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
14. **Duplicate series:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
15. **Unbounded cardinality:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
16. **Fast burn page missing:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
17. **Slow burn false positive:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
18. **Budget forecast error:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
19. **Emergency exception missing:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
20. **Change gate bypass:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
21. **Sensitive metric label:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
22. **Grafana access leak:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
23. **Rollback failure:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.
24. **Stale recovery signal:** determine eligible user impact, SLO burn, diagnostic evidence, safe mitigation and recovery criteria.

## Eight production runbooks

1. **SLI contract validation: owner, eligible events, good/total definition, exclusions and window.**
2. **Error-budget accounting: compare current and historical bad events, allowance and rollover.**
3. **Burn-rate incident: validate fast/slow paired windows and page/ticket routing.**
4. **Dependency triage: correlate API, PostgreSQL, Redis, Kafka, search and Snowflake freshness.**
5. **Telemetry failure: distinguish no traffic, missing scrapes, counter resets and absent data.**
6. **Forecast review: validate traffic-rate assumptions, rolling expiration and uncertainty.**
7. **Change governance: document budget status, approver, emergency exception and rollback.**
8. **Reliability acceptance: collect independent SLI recovery, reviewer sign-off and follow-up actions.**

## 100-point final assessment

| Domain | Points |
|---|---:|
| SLI contracts and SLO mathematics | 20 |
| Prometheus rules and alert routing | 20 |
| Dashboards, forecasts and data integrity | 20 |
| Security, policy and offline tests | 20 |
| Incident game day and verified recovery | 20 |
| **Total** | **100** |

Recommended passing score 85/100. Production sign-off requires actual metric validation, alert delivery, staging incident evidence, reviewer approval and tested rollback.

**Companion:** [Chapter 075 capstone lab](labs/075-enterprise-sli-slo-error-budget-reliability-acceptance-capstone-lab.md).

**Part 15 complete. Next:** Chapter 076 — Enterprise Incident Response Architecture, Severity Models and On-Call Operations (Part 16).
