# Chapter 071 — Service Level Indicators, Objectives and Error Budget Engineering

**Part 15 — SLIs, SLOs and Error Budgets**  
**Audience:** Enterprise SRE, DBRE, platform engineering, service owners and incident commanders.  
**Prerequisites:** Chapters 001–070; Prometheus, Grafana and RED metrics.

## Learning objectives

Define user-centric SLIs and achievable SLOs, calculate error budgets, detect fast and slow budget burn, govern releases with budget policy, and correlate application availability, latency and data freshness with database/platform health.

## Architecture

```text
Users -> API / service -> PostgreSQL / Redis / Kafka -> Snowflake
               |             |                |
       good/total events   dependency SLIs   freshness
               |             |                |
          Prometheus recording rules + OTel evidence
                              |
                  Grafana SLO dashboards
                              |
           multiwindow burn -> Alertmanager -> on-call
                              |
            release policy / incident / rollback
```

## Reliability concepts

- **SLI:** measured proportion or distribution representing a user-facing behavior. Example: good HTTP requests divided by eligible requests.
- **SLO:** target for an SLI over a stated rolling or calendar window, e.g. 99.9% good requests over 30 days.
- **SLA:** external agreement with commercial or contractual terms; do not treat an internal SLO as an SLA.
- **Error budget:** permitted failure within the window. For 99.9% request success, 0.1% of eligible events may fail.
- **Burn rate:** observed bad-event fraction divided by the allowed bad-event fraction. A burn rate of 10 spends budget 10 times faster than sustainable.

### Example budget

For 1,000,000 eligible requests and a 99.9% success SLO, allowed bad events are 1,000. If 500 are bad, budget consumption is 50%, leaving 500 allowed bad events. Request-based and time-based SLIs are not interchangeable: use an appropriate denominator and document exclusions.

## SLI design matrix

| User journey | Good event | Total event | Caveat |
|---|---|---|---|
| API availability | eligible successful response | all eligible requests | define expected 4xx and cancellations |
| API latency | request duration under threshold | all eligible requests | prefer histogram bucket count |
| Kafka processing | processed within freshness window | eligible records | offsets alone do not measure seconds |
| Snowflake freshness | target updated within lateness bound | scheduled/eligible deliveries | compare source and target watermarks |
| PostgreSQL read path | successful eligible DB-backed operation | eligible DB-backed operations | DB up does not guarantee user success |

## PromQL patterns

Request availability, subject to exporter labels:

```promql
1 -
sum(rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[5m]))
/
clamp_min(sum(rate(http_server_request_duration_seconds_count[5m])), 1e-9)
```

Latency good-event ratio for a 300 ms classic histogram:

```promql
sum(rate(http_server_request_duration_seconds_bucket{le="0.3"}[5m]))
/
clamp_min(sum(rate(http_server_request_duration_seconds_count[5m])), 1e-9)
```

The 0.3-second bucket must exist; otherwise configure one or use an appropriate histogram query. Inspect actual metric names and label conventions. Handle zero-traffic windows explicitly rather than declaring them 100% successful.

## Multiwindow burn-rate alerts

For a 99.9% SLO, allowed bad fraction is 0.001. Common burn-rate design uses fast and slow windows together, such as 5m/1h at 14.4x and 30m/6h at 6x, tuned for the 30-day objective and alert policy. Evaluate each pair against independent eligible-request counters and ensure low-traffic safeguards.

```promql
# Example instantaneous 5m burn rate (pair with a 1h expression)
(
 sum(rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[5m]))
 /
 clamp_min(sum(rate(http_server_request_duration_seconds_count[5m])), 1e-9)
) / 0.001
```

## Change and incident governance

A depleted error budget should trigger a **reviewed** reliability response: assess customer impact, pause nonessential risky changes when policy requires, prioritize remediation, and record exceptions. Do not automatically freeze emergency security fixes or necessary recovery work. SLOs are decision tools, not individual performance targets.

## Production incident simulation

An API's 5xx rate rises while PostgreSQL pool waits increase and Kafka-to-Snowflake freshness deteriorates. The 5-minute burn rate spikes, but 30-day availability still looks healthy. Determine whether the user-facing request SLO and data freshness SLO are separate; inspect the fast/slow burn pair, issue severity, halt risky rollout, recover service and document budget consumption.

## Executable offline error-budget gate

The following files evaluate a **synthetic** SLO manifest, not live Prometheus.

### healthy.json

```json
{
  "owner": "reliability-sre",
  "environment": "staging",
  "change_id": "OBS-071",
  "window_days": 30,
  "total_events": 1000000,
  "bad_events": 500,
  "slo_percent": 99.9,
  "latency_good_events": 997000,
  "latency_slo_percent": 99.5,
  "destructive_change": false,
  "checks": {
    "service_owner": true,
    "user_journey": true,
    "availability_sli": true,
    "latency_sli": true,
    "freshness_sli": true,
    "good_total_events": true,
    "window": true,
    "objective": true,
    "error_budget": true,
    "burn_rate": true,
    "alert_routing": true,
    "multiwindow": true,
    "dependency_sli": true,
    "dashboard": true,
    "change_policy": true,
    "privacy": true
  }
}
```

### slo_gate.py

```python
"""Offline SLI/SLO and error-budget calculator; synthetic manifest only."""
import json,sys
from pathlib import Path
CHECKS=["service_owner","user_journey","availability_sli","latency_sli","freshness_sli","good_total_events","window","objective","error_budget","burn_rate","alert_routing","multiwindow","dependency_sli","dashboard","change_policy","privacy"]
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
 n,b,g=p.get("total_events"),p.get("bad_events"),p.get("latency_good_events")
 if type(n) is not int or n<=0:e.append("invalid total_events")
 if type(b) is not int or b<0:e.append("invalid bad_events")
 if type(g) is not int or g<0:e.append("invalid latency_good_events")
 if type(n) is int and type(b) is int and b>n:e.append("bad exceeds total")
 if type(n) is int and type(g) is int and g>n:e.append("good exceeds total")
 w=p.get("window_days")
 if type(w) is not int or w<=0:e.append("invalid window")
 for k in ("slo_percent","latency_slo_percent"):
  x=p.get(k)
  if type(x) not in (int,float) or not 0<x<100:e.append("invalid "+k)
 if type(n) is int and n>0 and type(b) is int and 0<=b<=n and type(p.get("slo_percent")) in (int,float):
  if (n-b)/n*100<p["slo_percent"]-1e-10:e.append("availability SLO breach")
 if type(n) is int and n>0 and type(g) is int and 0<=g<=n and type(p.get("latency_slo_percent")) in (int,float):
  if g/n*100<p["latency_slo_percent"]-1e-10:e.append("latency SLO breach")
 if p.get("destructive_change") is not False:e.append("unsafe action")
 return e
def budget(p):
 n,b=p["total_events"],p["bad_events"]
 allowed=n*(100-p["slo_percent"])/100
 return {"allowed_bad_events":round(allowed,2),"consumed_percent":round(b/allowed*100,2) if allowed else None,"remaining_bad_events":round(allowed-b,2)}
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());findings=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 result={"status":"PASS" if not findings else "FAIL","findings":findings}
 if not findings:result["budget"]=budget(p)
 print(json.dumps(result,indent=2))
 sys.exit(bool(findings))

```

### test_slo_gate.py

```python
import copy,json,unittest
from pathlib import Path
from slo_gate import validate,budget
class SLOTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_budget(self):self.assertAlmostEqual(budget(self.p)["allowed_bad_events"],1000)
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["service_owner"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["user_journey"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["availability_sli"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["latency_sli"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["freshness_sli"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["good_total_events"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["window"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["objective"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["error_budget"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["burn_rate"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["alert_routing"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["multiwindow"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["dependency_sli"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["dashboard"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["change_policy"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["privacy"]=False
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
  p["slo_percent"]=101
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["bad_events"]=5000
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["latency_good_events"]=10
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["destructive_change"]=True
  self.assertTrue(validate(p))
 def test_negative_27(self):
  p=copy.deepcopy(self.p)
  p["checks"]=None
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 slo_gate.py healthy.json
python3 -m unittest -v test_slo_gate.py
```

Expected PASS and **30 authored tests**. Execution not yet verified.

## 24 hands-on exercises

1. Identify critical user journey.
2. Define service boundary.
3. Assign SLO owner.
4. Choose request-based SLI.
5. Define good events.
6. Define total events.
7. Choose rolling window.
8. Calculate availability SLI.
9. Calculate latency SLI.
10. Define data freshness SLI.
11. Calculate allowed bad events.
12. Calculate budget consumed.
13. Calculate remaining budget.
14. Measure short-window burn.
15. Measure long-window burn.
16. Design multiwindow alert.
17. Route SLO page.
18. Review Prometheus recording rule.
19. Review Grafana SLO dashboard.
20. Review dependency SLIs.
21. Simulate bad-event spike.
22. Evaluate change freeze policy.
23. Review low-traffic caveats.
24. Document post-incident budget.

## 24 production failure scenarios

1. **API error surge:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
2. **p99 latency cliff:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
3. **Low traffic denominator:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
4. **Counter reset:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
5. **Missing metrics:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
6. **Scrape gap:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
7. **High-cardinality labels:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
8. **Wrong SLI numerator:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
9. **Wrong SLI denominator:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
10. **Averaged percentile:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
11. **Stale data pipeline:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
12. **Dependency SLO breach:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
13. **Alert storm:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
14. **Silent SLO burn:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
15. **Bad routing:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
16. **Time-window mismatch:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
17. **Release during budget exhaustion:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
18. **Seasonal traffic spike:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
19. **Maintenance exclusion dispute:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
20. **Synthetic check false positive:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
21. **Request retries mask errors:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
22. **Queueing delays:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
23. **Burn-rate false negative:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.
24. **Rollback fails:** identify SLI numerator/denominator, impact, burn rate, mitigation and recovery evidence.

## Eight production runbooks

1. **Define SLI: identify user journey, good/total events, service boundary and exclusions.**
2. **Calculate budget: derive allowed bad events and remaining/consumed events for rolling window.**
3. **Burn-rate triage: inspect fast/slow windows, current impact and remaining budget.**
4. **Metric quality: check counter resets, scrape gaps, low traffic and cardinality.**
5. **Latency SLO: use request-level histogram threshold counts, not average p95.**
6. **Data freshness: compare source and target timestamps and agreed lateness threshold.**
7. **Governance: apply reviewed release/change policy when budget is exhausted.**
8. **Incident recovery: verify independent SLIs, communication, rollback and postmortem.**

## 100-point assessment

| Area | Points |
|---|---:|
| SLI architecture and event semantics | 20 |
| SLO targets and error-budget math | 20 |
| PromQL and multiwindow burn alerts | 20 |
| Offline tests and governance | 20 |
| Incident response and recovery | 20 |
| **Total** | **100** |

Suggested pass 85/100. Production sign-off requires live metric validation, alert tests and a documented service-owner policy.

**Companion:** [Chapter 071 lab](labs/071-service-level-indicators-objectives-error-budget-engineering-lab.md).

**Next:** Chapter 072 — Advanced SLO Design, Multiwindow Burn-Rate Alerting and Prometheus Recording Rules.
