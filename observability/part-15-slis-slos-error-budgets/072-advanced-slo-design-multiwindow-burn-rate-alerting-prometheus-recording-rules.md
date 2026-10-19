# Chapter 072 — Advanced SLO Design, Multiwindow Burn-Rate Alerting and Prometheus Recording Rules

**Part 15 — SLIs, SLOs and Error Budgets (2/5)**  
**Audience:** SRE, DBRE, platform owners and on-call engineers.  
**Prerequisites:** Chapter 071; PromQL and Alertmanager.

## Objectives

Engineer production-grade user-facing SLOs, implement low-noise multiwindow burn-rate alerts, validate Prometheus recording rules and Alertmanager routing, and govern error-budget consumption.

## Architecture

```text
User requests -> API / PostgreSQL / Redis / Kafka
                       |
                eligible good/total counters
                       |
                 Prometheus rules
                 /     |       \
           5m/1h    30m/6h    1d/3d
                 \     |       /
                   burn rates
                       |
                Alertmanager
                 /          \
             page           ticket
                 \          /
              on-call + Grafana SLOs
                       |
               rollback / budget review
```

## SLO and burn-rate theory

An SLI needs an explicit population, numerator, denominator, time window and owner. For a 99.9% objective, the error-budget fraction is 0.001. Burn rate = bad-event fraction / 0.001. A burn rate of 14.4 sustained for one hour consumes approximately 2% of a 30-day budget; a 6x burn sustained six hours consumes approximately 5%. These values are design heuristics; tune to service traffic and alert-response needs.

For a 30-day window, useful alert pairs are **5m AND 1h at 14.4x**, **30m AND 6h at 6x**, and slower ticket-level pairs such as **1d AND 3d at 1x**. Both windows of a pair must exceed threshold. Do not rely on only one short window. Treat low traffic, missing metrics, counter resets and incomplete labels explicitly.

## Prometheus recording rules

Save `slo-rules.yaml` and adapt labels and metric names to your exporter.

```yaml
groups:
  - name: api-slo-recording
    interval: 30s
    rules:
      - record: job:slo_http_error_ratio:rate5m
        expr: |
          sum by (job) (rate(http_requests_total{code=~"5.."}[5m]))
          /
          clamp_min(sum by (job) (rate(http_requests_total[5m])), 1e-9)
      - record: job:slo_http_error_ratio:rate1h
        expr: |
          sum by (job) (rate(http_requests_total{code=~"5.."}[1h]))
          /
          clamp_min(sum by (job) (rate(http_requests_total[1h])), 1e-9)
      - record: job:slo_http_error_ratio:rate30m
        expr: |
          sum by (job) (rate(http_requests_total{code=~"5.."}[30m]))
          /
          clamp_min(sum by (job) (rate(http_requests_total[30m])), 1e-9)
      - record: job:slo_http_error_ratio:rate6h
        expr: |
          sum by (job) (rate(http_requests_total{code=~"5.."}[6h]))
          /
          clamp_min(sum by (job) (rate(http_requests_total[6h])), 1e-9)
  - name: api-slo-alerts
    rules:
      - alert: APIErrorBudgetFastBurn
        expr: |
          (job:slo_http_error_ratio:rate5m{job="api"} > 14.4 * 0.001)
          and on (job)
          (job:slo_http_error_ratio:rate1h{job="api"} > 14.4 * 0.001)
        for: 2m
        labels:
          severity: page
        annotations:
          summary: "API error budget burning rapidly"
      - alert: APIErrorBudgetSlowBurn
        expr: |
          (job:slo_http_error_ratio:rate30m{job="api"} > 6 * 0.001)
          and on (job)
          (job:slo_http_error_ratio:rate6h{job="api"} > 6 * 0.001)
        for: 5m
        labels:
          severity: ticket
        annotations:
          summary: "API error budget burning persistently"
```

```bash
promtool check rules slo-rules.yaml
```

The `job="api"` selector is illustrative; check real series. Validate routing and expression behavior with synthetic series using `promtool test rules` before rollout. `clamp_min` prevents divide-by-zero errors but does **not** distinguish no traffic; add a separate minimum-traffic or absent-metric guard for production.

## Example alert test fixture

```yaml
rule_files:
  - slo-rules.yaml
evaluation_interval: 1m
tests:
  - interval: 1m
    input_series:
      - series: 'http_requests_total{job="api",code="200"}'
        values: '0+100x120'
      - series: 'http_requests_total{job="api",code="500"}'
        values: '0+3x120'
    alert_rule_test:
      - eval_time: 90m
        alertname: APIErrorBudgetFastBurn
        exp_alerts:
          - exp_labels:
              alertname: APIErrorBudgetFastBurn
              job: api
              severity: page
            exp_annotations:
              summary: "API error budget burning rapidly"
```

This fixture is illustrative; confirm parser syntax, labels and timing with `promtool test rules` in the target Prometheus version before relying on it. Alert labels may vary by evaluation configuration.

## Production operational design

Record rules in version control, review change windows, use CI `promtool check rules`, test Alertmanager receivers and escalation, and restrict dashboard visibility. Avoid user IDs, raw URLs and patient data as metric labels. Alert from user-facing eligibility, not database health alone. Define a safe fallback when telemetry is missing.

## Incident simulation

A deployment raises API 5xx while PostgreSQL connection waits and Redis hot-key contention increase. Five-minute burn rises immediately, while the one-hour window initially stays below threshold. Compare both windows, avoid premature false page, then verify sustained burn and the incident timeline. After rollback, confirm independent SLI recovery and document remaining budget.

## Offline acceptance gate

The following synthetic manifest checks SLO design review; it does not query Prometheus.

### healthy.json

```json
{
  "owner": "slo-sre",
  "environment": "staging",
  "change_id": "OBS-072",
  "objective_percent": 99.9,
  "total_requests": 1000000,
  "bad_requests": 500,
  "short_window_bad_ratio": 0.002,
  "long_window_bad_ratio": 0.001,
  "fast_burn_threshold": 14.4,
  "slow_burn_threshold": 6,
  "destructive_change": false,
  "checks": {
    "sli_contract": true,
    "eligible_requests": true,
    "status_policy": true,
    "five_min": true,
    "one_hour": true,
    "thirty_min": true,
    "six_hour": true,
    "one_day": true,
    "three_day": true,
    "fast_burn": true,
    "slow_burn": true,
    "recording_rules": true,
    "promtool": true,
    "alertmanager": true,
    "privacy": true,
    "rollback": true
  }
}
```

### burn_gate.py

```python
"""Offline multiwindow SLO review gate; no live metrics are fetched."""
import json,sys
from pathlib import Path
CHECKS=["sli_contract","eligible_requests","status_policy","five_min","one_hour","thirty_min","six_hour","one_day","three_day","fast_burn","slow_burn","recording_rules","promtool","alertmanager","privacy","rollback"]
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
 o=p.get("objective_percent")
 if type(o) not in (int,float) or not 0<o<100:e.append("invalid objective")
 n,b=p.get("total_requests"),p.get("bad_requests")
 if type(n) is not int or n<=0:e.append("invalid total")
 if type(b) is not int or b<0:e.append("invalid bad")
 if type(n) is int and type(b) is int and b>n:e.append("bad exceeds total")
 if type(n) is int and n>0 and type(b) is int and 0<=b<=n and type(o) in (int,float) and 0<o<100:
  if (n-b)/n*100<o-1e-10:e.append("SLO breach")
 for k in ("short_window_bad_ratio","long_window_bad_ratio"):
  v=p.get(k)
  if type(v) not in (int,float) or not 0<=v<=1:e.append("invalid "+k)
 for k in ("fast_burn_threshold","slow_burn_threshold"):
  v=p.get(k)
  if type(v) not in (int,float) or v<=0:e.append("invalid "+k)
 if p.get("destructive_change") is not False:e.append("unsafe action")
 return e
def burn(p):
 allowance=1-p["objective_percent"]/100
 return {"short_burn":round(p["short_window_bad_ratio"]/allowance,3),"long_burn":round(p["long_window_bad_ratio"]/allowance,3),"allowed_bad_events":round(p["total_requests"]*allowance,2)}
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());findings=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 result={"status":"PASS" if not findings else "FAIL","findings":findings}
 if not findings:result["burn"]=burn(p)
 print(json.dumps(result,indent=2))
 sys.exit(bool(findings))

```

### test_burn_gate.py

```python
import copy,json,unittest
from pathlib import Path
from burn_gate import validate,burn
class BurnTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_budget(self):self.assertAlmostEqual(burn(self.p)["allowed_bad_events"],1000)
 def test_short_burn(self):self.assertAlmostEqual(burn(self.p)["short_burn"],2)
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["checks"]["sli_contract"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["checks"]["eligible_requests"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["checks"]["status_policy"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["checks"]["five_min"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["checks"]["one_hour"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["checks"]["thirty_min"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["checks"]["six_hour"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["checks"]["one_day"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["checks"]["three_day"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["checks"]["fast_burn"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["checks"]["slow_burn"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["checks"]["recording_rules"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["checks"]["promtool"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["checks"]["alertmanager"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["checks"]["privacy"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["checks"]["rollback"]=False
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
  p["objective_percent"]=101
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["total_requests"]=0
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["bad_requests"]=2000000
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["bad_requests"]=5000
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["short_window_bad_ratio"]=2
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["long_window_bad_ratio"]=-1
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["fast_burn_threshold"]=0
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
python3 burn_gate.py healthy.json
python3 -m unittest -v test_burn_gate.py
```

Expected PASS and **32 authored tests**. Execution not yet verified.

## 24 hands-on exercises

1. Define user journey and eligibility.
2. Select rolling 30-day SLO.
3. Define success numerator.
4. Define request denominator.
5. Validate status-code policy.
6. Create 5m error ratio.
7. Create 1h error ratio.
8. Create 30m error ratio.
9. Create 6h error ratio.
10. Create 3d error ratio.
11. Create 1d error ratio.
12. Build 14.4x burn alert.
13. Build 6x burn alert.
14. Build 1x ticket alert.
15. Create recording rule group.
16. Validate promtool rules.
17. Build Grafana SLO dashboard.
18. Test Alertmanager routing.
19. Simulate high-error burst.
20. Simulate sustained degradation.
21. Test missing metrics.
22. Test low traffic.
23. Evaluate budget and release gate.
24. Record rollback evidence.

## 24 production failure scenarios

1. **Counter reset:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
2. **Scrape outage:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
3. **Zero denominator:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
4. **Sparse traffic:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
5. **Unexpected 4xx:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
6. **Missing HTTP route label:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
7. **Label explosion:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
8. **Duplicate metric series:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
9. **Incorrect le bucket:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
10. **Averaged percentile:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
11. **Short window false positive:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
12. **Long window blind spot:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
13. **Burn alert noise:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
14. **Burn alert silent:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
15. **Recording rule delay:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
16. **Prometheus restart:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
17. **Remote write lag:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
18. **Alertmanager routing failure:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
19. **Pager suppression:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
20. **Timezone window confusion:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
21. **Latency objective breach:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
22. **Error budget exhausted:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
23. **Multi-tenant data leak:** inspect eligible events, alert windows, user impact, routing and rollback evidence.
24. **Rollback does not recover:** inspect eligible events, alert windows, user impact, routing and rollback evidence.

## Eight production runbooks

1. **Fast-burn page: confirm independent user impact, compare 5m/1h burn and declare severity.**
2. **Slow-burn ticket: compare 30m/6h and 1d/3d windows; prioritize sustained regression.**
3. **Recording-rule failure: check promtool, scrape coverage, label alignment and evaluation errors.**
4. **No traffic: classify absent and zero-denominator separately; avoid false green.**
5. **High cardinality: inspect metric labels and preserve low-cardinality service/route aggregation.**
6. **Alert routing: verify Alertmanager receiver, inhibition, grouping and on-call escalation.**
7. **Budget policy: compute rolling budget, review deployment risk and document exceptions.**
8. **Recovery: apply approved rollback, verify SLI improvement and capture incident evidence.**

## 100-point assessment

| Domain | Points |
|---|---:|
| SLO and SLI contracts | 20 |
| Error-budget and burn-rate mathematics | 20 |
| Prometheus rules and Alertmanager tests | 20 |
| Synthetic validation and security | 20 |
| Incident response and recovery | 20 |
| **Total** | **100** |

Suggested pass: 85/100. Production sign-off requires live rule testing, on-call routing validation and documented service-owner review.

**Companion:** [Chapter 072 lab](labs/072-advanced-slo-design-multiwindow-burn-rate-alerting-prometheus-recording-rules-lab.md).

**Next:** Chapter 073 — SLO Dashboards, Error Budget Policies and Reliability Governance.
