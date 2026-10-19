# Chapter 089 — Observability FinOps, Retention Optimization, Cardinality Governance and Cost Forecasting

**Part 18 — Scaling, High Availability and FinOps (4/5)**

## Objectives

Measure and govern Prometheus, Loki, Tempo, Grafana and OpenTelemetry spend without degrading SLO visibility, incident response or audit retention. Build owner-level chargeback/showback, forecast capacity and cost, and apply safe policy gates.

## FinOps architecture

```text
Prometheus samples/series -> metrics storage + remote-write cost
Loki logs/streams --------> ingest + object-store + query cost
Tempo spans --------------> ingestion + sampling + retention cost
Grafana queries ----------> compute + cache + egress cost
           |
       usage metrics
           |
 owner/team/tenant allocation
           |
 budgets -> policy -> reviewed change -> SLO acceptance
```

## Cost drivers and governance

Metric costs depend on active series, churn, samples/sec, scrape frequency, HA replication, remote-write egress, query concurrency and retention. Loki costs depend on bytes ingested, stream cardinality, compression, object storage, index/query load and retention. Tempo costs depend on spans/sec, average span size, sampling, object storage, compaction and queries. Allocate spend to bounded tenant/team labels, not per-request identifiers.

## Forecast model

```text
metric_daily_bytes = samples_per_sec * observed_bytes_per_sample * 86400
log_daily_bytes = log_bytes_per_sec * 86400
trace_daily_bytes = spans_per_sec * observed_bytes_per_span * 86400
monthly_cost = ingestion + compute + object_storage + operations + egress
forecast = measured_baseline * growth_factor * seasonal_peak_factor
```

Account for compression, replicas, metadata, object-store requests and failure headroom separately. Never treat a fixed bytes-per-sample assumption as a universal Prometheus storage figure.

## Cardinality governance

```promql
topk(10, count by (__name__) ({__name__!=""}))
sum(prometheus_tsdb_head_series)
sum(rate(prometheus_tsdb_head_samples_appended_total[5m]))
```

Validate these against actual versions and scrape topology. High-cardinality hazards include PostgreSQL query literals, Redis keys, Kafka message IDs, Elasticsearch document IDs and Snowflake query IDs. Keep bounded service/cluster/environment labels; move high-dimensional diagnostic data to secured logs or traces.

## Retention and sampling decisions

Set retention per signal and compliance requirement. Avoid irreversible deletion without approvals, backups where appropriate and documented rollback limitations. Sampling reduces Tempo storage but can conceal rare incidents; use representative, policy-driven sampling with error and latency coverage. Reduce noisy Loki logs by application-level controls and safe filtering before simply shrinking retention.

## Budget controls

Define warning and critical thresholds using cost growth and SLO impact. Investigate unexpected tenant spend before throttling ingestion. Enforce approved quotas, capacity forecasts and exception expiry. Test alert delivery and DBRE troubleshooting coverage after optimization.

## DBRE scenario

An Elasticsearch per-document label and PostgreSQL per-query label produce a sharp rise in Prometheus head series and remote-write backlog. Contain the instrumentation change, quantify cardinality and WAL recovery, restore SLO visibility, then update CI policy and the monthly forecast.

## Offline synthetic FinOps gate

### healthy.json

```json
{
  "owner": "observability-finops",
  "environment": "staging",
  "change_id": "OBS-089",
  "reviewed": true,
  "budget_verified": true,
  "slo_verified": true,
  "destructive_action": false,
  "controls": {
    "ownership": true,
    "metrics_rate": true,
    "series": true,
    "churn": true,
    "scrape": true,
    "remote_write": true,
    "loki_volume": true,
    "loki_retention": true,
    "tempo_volume": true,
    "sampling": true,
    "storage": true,
    "egress": true,
    "forecast": true,
    "budget": true,
    "cardinality_policy": true,
    "slo": true,
    "approval": true,
    "rollback": true
  }
}
```

### finops_gate.py

```python
"""Synthetic observability FinOps evidence gate; no cloud API calls."""
import json,sys
from pathlib import Path
CONTROLS=["ownership","metrics_rate","series","churn","scrape","remote_write","loki_volume","loki_retention","tempo_volume","sampling","storage","egress","forecast","budget","cardinality_policy","slo","approval","rollback"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 for k in ("reviewed","budget_verified","slo_verified"):
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

### test_finops_gate.py

```python
import copy,json,unittest
from pathlib import Path
from finops_gate import validate
class FinOpsTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["controls"]["ownership"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["controls"]["metrics_rate"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["controls"]["series"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["controls"]["churn"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["controls"]["scrape"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["controls"]["remote_write"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["controls"]["loki_volume"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["controls"]["loki_retention"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["controls"]["tempo_volume"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["controls"]["sampling"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["controls"]["storage"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["controls"]["egress"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["controls"]["forecast"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["controls"]["budget"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["controls"]["cardinality_policy"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["controls"]["slo"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["controls"]["approval"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["controls"]["rollback"]=False
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
  p["reviewed"]=false
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["budget_verified"]=false
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["slo_verified"]=false
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
python3 finops_gate.py healthy.json
python3 -m unittest -v test_finops_gate.py
```

Expected PASS and **28 authored tests**. This gate checks synthetic attestations; live cost reconciliation and test execution remain pending.

## 24 hands-on exercises

1. Inventory observability spend: measure baseline, model cost, evaluate SLO impact and capture evidence.
2. Attribute tenant owners: measure baseline, model cost, evaluate SLO impact and capture evidence.
3. Measure active series: measure baseline, model cost, evaluate SLO impact and capture evidence.
4. Measure samples per second: measure baseline, model cost, evaluate SLO impact and capture evidence.
5. Identify top labels: measure baseline, model cost, evaluate SLO impact and capture evidence.
6. Analyze metric churn: measure baseline, model cost, evaluate SLO impact and capture evidence.
7. Review scrape intervals: measure baseline, model cost, evaluate SLO impact and capture evidence.
8. Review recording rules: measure baseline, model cost, evaluate SLO impact and capture evidence.
9. Audit Loki bytes per day: measure baseline, model cost, evaluate SLO impact and capture evidence.
10. Review log retention: measure baseline, model cost, evaluate SLO impact and capture evidence.
11. Measure Tempo span volume: measure baseline, model cost, evaluate SLO impact and capture evidence.
12. Audit sampling policies: measure baseline, model cost, evaluate SLO impact and capture evidence.
13. Measure object store bytes: measure baseline, model cost, evaluate SLO impact and capture evidence.
14. Analyze cross-region egress: measure baseline, model cost, evaluate SLO impact and capture evidence.
15. Estimate compactor costs: measure baseline, model cost, evaluate SLO impact and capture evidence.
16. Model storage growth: measure baseline, model cost, evaluate SLO impact and capture evidence.
17. Forecast 30-day costs: measure baseline, model cost, evaluate SLO impact and capture evidence.
18. Forecast 90-day costs: measure baseline, model cost, evaluate SLO impact and capture evidence.
19. Define budget thresholds: measure baseline, model cost, evaluate SLO impact and capture evidence.
20. Design cost alerts: measure baseline, model cost, evaluate SLO impact and capture evidence.
21. Review SLO impact: measure baseline, model cost, evaluate SLO impact and capture evidence.
22. Test cardinality policy: measure baseline, model cost, evaluate SLO impact and capture evidence.
23. Simulate budget breach: measure baseline, model cost, evaluate SLO impact and capture evidence.
24. Approve FinOps change: measure baseline, model cost, evaluate SLO impact and capture evidence.

## 24 production incident scenarios

1. **Cardinality surge:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
2. **Unbounded request labels:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
3. **Duplicate scrape targets:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
4. **Prometheus WAL growth:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
5. **Remote write egress spike:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
6. **Grafana query amplification:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
7. **Loki log storm:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
8. **Loki tenant rate limit:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
9. **Unexpected log retention:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
10. **Loki compactor backlog:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
11. **Tempo trace explosion:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
12. **Tempo sampling misconfig:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
13. **Trace storage growth:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
14. **Cross-region transfer spike:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
15. **Object-store API bill:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
16. **Unused dashboards:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
17. **Overprovisioned replicas:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
18. **Underprovisioned ingesters:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
19. **Missing cost owner:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
20. **Stale forecast:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
21. **Budget alert missing:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
22. **Policy bypass:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
23. **Retention deletion error:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.
24. **Cost fix breaks SLO:** quantify cost and customer impact, diagnose root cause, mitigate safely and verify recovery.

## Eight production runbooks

1. **Metric cardinality audit and remediation:** define triggers, owner, cost evidence, risk, rollback and acceptance checks.
2. **Prometheus scrape and retention tuning:** define triggers, owner, cost evidence, risk, rollback and acceptance checks.
3. **Loki ingestion and retention cost response:** define triggers, owner, cost evidence, risk, rollback and acceptance checks.
4. **Tempo sampling and trace storage optimization:** define triggers, owner, cost evidence, risk, rollback and acceptance checks.
5. **Tenant cost allocation and showback:** define triggers, owner, cost evidence, risk, rollback and acceptance checks.
6. **Budget threshold breach and safe mitigation:** define triggers, owner, cost evidence, risk, rollback and acceptance checks.
7. **Capacity forecast reconciliation and anomaly review:** define triggers, owner, cost evidence, risk, rollback and acceptance checks.
8. **Change approval, SLO validation and rollback:** define triggers, owner, cost evidence, risk, rollback and acceptance checks.

## 100-point assessment

| Domain | Points |
|---|---:|
| Cost attribution and baselines | 20 |
| Cardinality and ingestion governance | 20 |
| Retention, sampling and storage | 20 |
| Forecasting and budget controls | 20 |
| SLO-safe optimization and incident recovery | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production approval requires observed billing/usage reconciliation, privacy review, owner approval and witnessed SLO checks.

**Companion:** [Chapter 089 lab](labs/089-observability-finops-retention-optimization-cardinality-governance-cost-forecasting-lab.md).

**Next:** Chapter 090 — Enterprise Observability Scaling, High Availability and FinOps Reliability Acceptance Capstone.
