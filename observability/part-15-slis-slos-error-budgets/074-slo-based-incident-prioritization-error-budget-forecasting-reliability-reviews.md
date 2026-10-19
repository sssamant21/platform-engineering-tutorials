# Chapter 074 — SLO-Based Incident Prioritization, Error Budget Forecasting and Reliability Reviews

**Part 15 — SLIs, SLOs and Error Budgets (4/5)**  
**Audience:** Enterprise SRE, DBRE, incident commanders, service owners and platform leads.  
**Prerequisites:** Chapters 071–073.

## Learning objectives

Prioritize incidents by customer impact and error-budget burn, forecast budget exhaustion with explicit uncertainty, govern high-risk releases, and conduct actionable weekly/monthly reliability reviews.

## Architecture

```text
User journeys -> RED / availability / latency / freshness SLIs
                            |
                      Prometheus rules
                            |
               fast + slow burn / 30d budget
                            |
             Grafana + Alertmanager + on-call
                            |
              incident severity / forecast
                            |
           service-owner reliability review
                            |
            remediation / release gate / rollback
```

## Incident prioritization

Incident severity is grounded in **customer impact**, affected service criticality, duration and expected budget burn—not infrastructure CPU alone. A fast burn may warrant immediate paging; a persistent low burn may require an engineering ticket. Define policy for missing telemetry, low-traffic services, planned maintenance and dependency failures.

| Condition | Operational decision |
|---|---|
| Fast burn: 5m AND 1h above 14.4x | page and investigate immediately |
| Slow burn: 30m AND 6h above 6x | page or urgent ticket by service policy |
| Sustained lower burn | reliability backlog and owner review |
| Budget depleted | restrict nonessential risky releases under approved policy |
| Telemetry missing | classify unknown; validate independent checks |

Thresholds are illustrative for a 99.9% SLO over 30 days. Tune windows, alert routing and incident severity to the service and user journey.

## Error-budget forecasting

For a request-based 99.9% SLO and 1,000,000 eligible events, allowed bad events = 1,000. If 400 are bad, 600 remain. The **burn multiple** equals observed bad-event fraction divided by 0.001. At a recent bad-event fraction of 0.0005, burn multiple = 0.5.

Forecasting time to exhaustion requires a *future eligible request arrival rate* and projected bad fraction, not just a burn multiple. A simplistic constant-rate forecast is:

```text
remaining_bad_events = allowed_bad_events - observed_bad_events
bad_events_per_hour = predicted_requests_per_hour * predicted_bad_fraction
hours_to_exhaustion = remaining_bad_events / bad_events_per_hour
```

For rolling windows, both historical bad events and eligible requests age out, so the allowance changes. Treat the simple calculation as a short-horizon planning approximation, not a reliable exact date. Use scenario bands for traffic and error-rate uncertainty, exclude unrepresentative incident spikes, and show forecast confidence.

## Weekly reliability review

Review objective and ownership, current SLI, budget remaining, burn-rate history, significant incidents, repeat dependency bottlenecks, release correlation, corrective actions, risks, exceptions and next review date. Track accountable owners and evidence. Avoid using SLOs as individual performance ratings.

## Data-platform examples

- **PostgreSQL:** connection-pool saturation and lock waits increase API bad-event rate.
- **Redis:** hot-key latency creates p99 regressions despite healthy CPU averages.
- **Kafka/MSK:** consumer lag affects delivery timeliness; lag alone is not a freshness SLI.
- **Elasticsearch/OpenSearch:** search rejections and oversized queries degrade user-facing latency.
- **Snowflake:** warehouse queueing or CDC delay breaches freshness objectives even if API uptime is healthy.

## Production incident game day

A deployment raises 5xx errors and p95 latency while Kafka-to-Snowflake freshness also worsens. An initial five-minute burn spike lacks confirmation from the one-hour window. Separate user-facing and data freshness SLOs, verify independent counters, assign incident severity, estimate near-term budget exposure, pause risky rollout, roll back and review root causes.

## Executable offline incident and forecasting gate

The synthetic manifest checks review controls and computes a conservative budget summary; it does not query live systems or predict an exhaustion timestamp.

### healthy.json

```json
{
  "owner": "reliability-review-sre",
  "environment": "staging",
  "change_id": "OBS-074",
  "window_days": 30,
  "total_events": 1000000,
  "bad_events": 400,
  "objective_percent": 99.9,
  "recent_bad_fraction": 0.0005,
  "destructive_change": false,
  "checks": {
    "owner": true,
    "eligible_events": true,
    "rolling_window": true,
    "budget_math": true,
    "fast_burn": true,
    "slow_burn": true,
    "severity": true,
    "customer_impact": true,
    "dependency_traces": true,
    "forecast": true,
    "uncertainty": true,
    "dashboard": true,
    "alert_routing": true,
    "change_policy": true,
    "rollback": true,
    "review_evidence": true
  }
}
```

### incident_forecast_gate.py

```python
"""Offline SLO incident/forecast review; synthetic data only."""
import json,sys
from pathlib import Path
CHECKS=["owner","eligible_events","rolling_window","budget_math","fast_burn","slow_burn","severity","customer_impact","dependency_traces","forecast","uncertainty","dashboard","alert_routing","change_policy","rollback","review_evidence"]
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["expected object"]
 for k in ("owner","environment","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 c=p.get("checks")
 if not isinstance(c,dict):e.append("invalid checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append("unverified "+k)
 n,b,o=p.get("total_events"),p.get("bad_events"),p.get("objective_percent")
 if type(n) is not int or n<=0:e.append("invalid total")
 if type(b) is not int or b<0:e.append("invalid bad")
 if type(n) is int and type(b) is int and b>n:e.append("bad exceeds total")
 if type(o) not in (int,float) or not 0<o<100:e.append("invalid objective")
 w=p.get("window_days")
 if type(w) is not int or w<=0:e.append("invalid window")
 f=p.get("recent_bad_fraction")
 if type(f) not in (int,float) or not 0<=f<=1:e.append("invalid recent bad fraction")
 if type(n) is int and n>0 and type(b) is int and 0<=b<=n and type(o) in (int,float) and 0<o<100 and b>n*(1-o/100)+1e-9:e.append("budget exhausted")
 if p.get("destructive_change") is not False:e.append("unsafe action")
 return e
def forecast(p):
 n,b,o,f=p["total_events"],p["bad_events"],p["objective_percent"],p["recent_bad_fraction"]
 allowed=n*(1-o/100);remaining=allowed-b
 recent_burn=f/(1-o/100)
 return {"allowed_bad_events":round(allowed,2),"remaining_bad_events":round(remaining,2),"recent_burn_multiple":round(recent_burn,3),"forecast_note":"No time-to-exhaustion without measured future traffic rate and uncertainty bounds"}
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());findings=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 result={"status":"PASS" if not findings else "FAIL","findings":findings}
 if not findings:result["forecast"]=forecast(p)
 print(json.dumps(result,indent=2))
 sys.exit(bool(findings))

```

### test_incident_forecast_gate.py

```python
import copy,json,unittest
from pathlib import Path
from incident_forecast_gate import validate,forecast
class IncidentForecastTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_budget(self):self.assertAlmostEqual(forecast(self.p)["remaining_bad_events"],600)
 def test_burn(self):self.assertAlmostEqual(forecast(self.p)["recent_burn_multiple"],0.5)
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["owner"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["eligible_events"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rolling_window"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["budget_math"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["fast_burn"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["slow_burn"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["severity"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["customer_impact"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["dependency_traces"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["forecast"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["uncertainty"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["dashboard"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["alert_routing"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["change_policy"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["review_evidence"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["window_days"]=0
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["total_events"]=0
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["bad_events"]=2000000
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["objective_percent"]=101
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["bad_events"]=5000
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["recent_bad_fraction"]=-1
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["recent_bad_fraction"]=2
  self.assertTrue(validate(p))
 def test_negative_27(self):
  p=copy.deepcopy(self.p)
  p["destructive_change"]=True
  self.assertTrue(validate(p))
 def test_negative_28(self):
  p=copy.deepcopy(self.p)
  p["checks"]=None
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 incident_forecast_gate.py healthy.json
python3 -m unittest -v test_incident_forecast_gate.py
```

Expected PASS and **32 authored tests**. Execution remains pending.

## 24 hands-on exercises

1. Identify SLO owner.
2. Select rolling window.
3. Define eligible events.
4. Calculate allowed failures.
5. Calculate remaining budget.
6. Calculate consumption fraction.
7. Calculate 5m burn.
8. Calculate 1h burn.
9. Calculate 30m burn.
10. Calculate 6h burn.
11. Review severity matrix.
12. Classify customer impact.
13. Review dependency evidence.
14. Review incident timeline.
15. Compute historical burn trend.
16. Forecast exhaustion horizon.
17. Build forecast confidence bands.
18. Annotate release changes.
19. Review missing data.
20. Inspect Alertmanager route.
21. Simulate fast-burn incident.
22. Simulate slow-burn incident.
23. Rehearse rollback.
24. Hold reliability review.

## 24 production failure scenarios

1. **Fast burn after release:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
2. **Slow chronic degradation:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
3. **SLO denominator drift:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
4. **Counter reset:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
5. **Missing telemetry:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
6. **No traffic:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
7. **Latency SLO breach:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
8. **Freshness SLO breach:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
9. **DB pool saturation:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
10. **Redis latency surge:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
11. **Kafka backlog:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
12. **Elasticsearch rejection spike:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
13. **Snowflake freshness delay:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
14. **Wrong incident severity:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
15. **Alert route failure:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
16. **Budget forecast instability:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
17. **Burst skewed forecast:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
18. **Seasonality ignored:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
19. **Change freeze bypass:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
20. **Emergency fix blocked:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
21. **Unapproved exception:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
22. **SLO owner missing:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
23. **Recovery metric stale:** establish customer impact, SLI evidence, burn windows, mitigation and review action.
24. **Rollback incomplete:** establish customer impact, SLI evidence, burn windows, mitigation and review action.

## Eight production runbooks

1. **Incident classification: determine user impact, affected journeys, burn-rate pairs and severity.**
2. **Forecast budget: compute current burn, rolling allowance and time-to-exhaustion with caveats.**
3. **Fast-burn response: page owner, freeze risky rollout, isolate dependency and mitigate.**
4. **Slow-burn response: file reliability work, investigate persistent saturation and review SLO.**
5. **Telemetry quality: verify counters, absent data, sparse traffic and resets.**
6. **Change review: evaluate remaining budget, exception approvals and rollback readiness.**
7. **Reliability review: summarize trends, top incidents, action owners and deadlines.**
8. **Recovery: execute approved rollback, verify independent SLIs and capture postmortem.**

## 100-point assessment

| Area | Points |
|---|---:|
| User impact and incident severity | 20 |
| Error-budget and burn-rate calculations | 20 |
| Forecast uncertainty and trend review | 20 |
| Governance and synthetic validation | 20 |
| Incident recovery and reliability review | 20 |
| **Total** | **100** |

Suggested pass: 85/100. Production acceptance requires witnessed incident simulation, measured traffic forecasts, verified alerts and service-owner approval.

**Companion:** [Chapter 074 lab](labs/074-slo-based-incident-prioritization-error-budget-forecasting-reliability-reviews-lab.md).

**Next:** Chapter 075 — Enterprise SLI/SLO and Error Budget Reliability Acceptance Capstone.
