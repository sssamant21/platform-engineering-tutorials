# Chapter 029 — Alert Quality Engineering, Noise Reduction, SLO Burn-Rate Alerts and Incident Signal Design

**Part 06 — Alertmanager and Alert Engineering**  
**Audience:** Enterprise SRE/DBRE, service owners, observability and incident teams.  
**Prerequisites:** Chapters 016–020 and 026–028; PromQL, Python 3.10+.  
**Goal:** Build actionable, low-noise, user-impact-focused alerting using SLIs, SLO error budgets, multiwindow burn-rate alerts and defensible notification routes.

## 1. Alert quality engineering

A good page identifies a current, actionable threat to users, has an owner and runbook, routes to an available responder, and carries enough context to mitigate. A ticket tracks non-urgent work. A dashboard is for exploration, not a substitute for paging. Avoid paging on every CPU, memory, or disk metric without a service-impact connection.

**Signal contract:** SLI definition, SLO target/window, numerator and denominator, query, threshold, duration, missing-data policy, ownership, severity, receiver, runbook, maintenance handling, deduplication, review cadence and test evidence.

## 2. Error budgets and burn rate

For an availability SLO target \(S\), error-budget fraction \(B=1-S\). Observed error ratio \(E=\text{bad requests}/\text{eligible requests}\), and burn rate \(R=E/B\). A 99.9% SLO has a 0.1% error budget. At 14.4× burn for one hour, a 30-day budget loses approximately \(14.4/720=2\%\). At 6× for six hours, it loses \(6\times6/720=5\%\). These calculations assume a 30-day, 720-hour period and steady rates.

Multiwindow multi-burn-rate alerting requires **both** a long and a short window above the same threshold, limiting transient noise while retaining outage sensitivity. The thresholds below are illustrative engineering starting points and must be calibrated to the service and SLO policy.

## 3. Prometheus recording rules and alert rules

The following is **Prometheus-managed rule YAML**, evaluated by Prometheus and forwarded to Alertmanager. It is not Grafana-managed rule syntax.

```yaml
groups:
  - name: postgres-api-slo
    interval: 30s
    rules:
      - record: service:http_requests:rate5m
        expr: sum by (service) (rate(http_requests_total{service="postgres-api"}[5m]))
      - record: service:http_errors:rate5m
        expr: sum by (service) (rate(http_requests_total{service="postgres-api",status=~"5.."}[5m]))
      - alert: PostgresAPIFastErrorBudgetBurn
        expr: |
          (
            sum(rate(http_requests_total{service="postgres-api",status=~"5.."}[1h]))
            /
            clamp_min(sum(rate(http_requests_total{service="postgres-api"}[1h])), 1e-9)
          ) > (14.4 * 0.001)
          and
          (
            sum(rate(http_requests_total{service="postgres-api",status=~"5.."}[5m]))
            /
            clamp_min(sum(rate(http_requests_total{service="postgres-api"}[5m])), 1e-9)
          ) > (14.4 * 0.001)
        for: 2m
        labels:
          team: dbre
          severity: page
          service: postgres-api
          cluster: lab
        annotations:
          summary: "Postgres API error budget burning rapidly"
          runbook_url: "https://example.org/runbooks/postgres-api"
```

The example assumes `http_requests_total` and `status` labels exist. Adapt to your instrumented application. It uses `clamp_min` to avoid division by zero, **but that is not sufficient to make low-traffic ratios reliable**. Add a separate minimum-volume gate and synthetic availability checks. A missing target may produce no series rather than a page; add inventory-based missing-series alerts.

A more complete production ruleset should include 6h/30m at 6×, plus slow-burn ticketing; record ratios where appropriate and avoid expensive duplicated queries. Run `promtool check rules` before deployment.

## 4. Paging, tickets and noise reduction

- **Page:** high-confidence, time-sensitive user impact; clear responder action.
- **Ticket:** slow burn, trend, capacity and preventive work with no immediate user impact.
- **Suppress safely:** group related alerts, use narrowly scoped inhibition and time-bounded silences, and avoid per-request labels.
- **Tune:** use incident history, precision, recall, false pages per week, acknowledgement latency and missed incidents.
- **Protect telemetry:** alert on Prometheus scrape failure, rule evaluation failure, target inventory gaps and routing failures independently.

Do not silence the only symptom of an outage. Alertmanager grouping and inhibition operate on notifications, not on Prometheus rule evaluation.

## 5. SRE/DBRE application scenarios

PostgreSQL: API availability SLO plus replication lag and connection saturation as diagnostic/ticket signals. MongoDB: user-facing query success/latency and replica-set health. Redis: cache-backed service errors and latency with evictions/replication as diagnostic context. Elasticsearch/OpenSearch: search request errors and tail latency, with shard size, disk pressure and thread-pool rejections as contributing signals. Kubernetes: application availability SLI with pod restarts and resource pressure as diagnostics. Ensure labels never contain PHI/PII or unbounded IDs.

## 6. Executable offline alert-quality governance lab

This JSON is **policy metadata for training**, not Prometheus or Alertmanager native configuration. The Python gate checks SLO bounds, routing, missing-data policy, low-traffic handling, labels, windows, burn thresholds and review evidence. It does not evaluate real telemetry or send pages.

Create:

```text
chapter029/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/slo_gate.py
  tests/test_slo_gate.py
```

### fixtures/healthy.json

```json
{
  "service": "postgres-api",
  "team": "dbre",
  "slo": 0.999,
  "window_days": 30,
  "request_rate_per_minute": 1200,
  "minimum_traffic_per_minute": 100,
  "labels": [
    "service",
    "team",
    "severity",
    "cluster"
  ],
  "runbook": "https://example.org/runbooks/postgres-api",
  "receiver": "dbre-test",
  "fallback_receiver": "sre-test",
  "reviewed": true,
  "route_tested": true,
  "no_data_policy": "alert",
  "low_traffic_policy": "ticket",
  "rules": [
    {
      "name": "FastBurn",
      "severity": "page",
      "long_window_minutes": 60,
      "short_window_minutes": 5,
      "burn_rate": 14.4,
      "for_minutes": 2
    },
    {
      "name": "MediumBurn",
      "severity": "page",
      "long_window_minutes": 360,
      "short_window_minutes": 30,
      "burn_rate": 6,
      "for_minutes": 5
    },
    {
      "name": "SlowBurn",
      "severity": "ticket",
      "long_window_minutes": 4320,
      "short_window_minutes": 360,
      "burn_rate": 1,
      "for_minutes": 30
    }
  ]
}
```

### fixtures/degraded.json

```json
{
  "service": "postgres-api",
  "team": "dbre",
  "slo": 1,
  "window_days": 30,
  "request_rate_per_minute": 1200,
  "minimum_traffic_per_minute": 100,
  "labels": [
    "service",
    "team",
    "severity",
    "cluster",
    "request_id"
  ],
  "runbook": "https://example.org/runbooks/postgres-api",
  "receiver": "dbre-test",
  "fallback_receiver": "sre-test",
  "reviewed": true,
  "route_tested": false,
  "no_data_policy": "ignore",
  "low_traffic_policy": "ticket",
  "rules": [
    {
      "name": "FastBurn",
      "severity": "page",
      "long_window_minutes": 60,
      "short_window_minutes": 90,
      "burn_rate": 14.4,
      "for_minutes": 2
    },
    {
      "name": "MediumBurn",
      "severity": "page",
      "long_window_minutes": 360,
      "short_window_minutes": 30,
      "burn_rate": 0,
      "for_minutes": 5
    },
    {
      "name": "SlowBurn",
      "severity": "ticket",
      "long_window_minutes": 4320,
      "short_window_minutes": 360,
      "burn_rate": 1,
      "for_minutes": 30
    }
  ]
}
```

### scripts/slo_gate.py

```python
#!/usr/bin/env python3
"""Offline SLO alert policy validation. Does not run PromQL or deliver notifications."""
import json,sys
from pathlib import Path
ALLOWED={"service","team","severity","cluster","environment","region"}
def validate(p):
    e=[]
    if not isinstance(p,dict): return ["policy not object"]
    for k in ("service","team","runbook","receiver","fallback_receiver"):
        if not isinstance(p.get(k),str) or not p[k]: e.append("missing "+k)
    for k in ("reviewed","route_tested"):
        if p.get(k) is not True: e.append("unverified "+k)
    if p.get("receiver")==p.get("fallback_receiver"): e.append("missing distinct fallback")
    slo=p.get("slo")
    if type(slo) not in (float,int) or not 0<slo<1: e.append("invalid slo")
    days=p.get("window_days")
    if type(days) is not int or not 1<=days<=90: e.append("invalid window")
    for k in ("request_rate_per_minute","minimum_traffic_per_minute"):
        v=p.get(k)
        if type(v) not in (int,float) or v<0: e.append("invalid "+k)
    if p.get("no_data_policy") not in ("alert","ticket"): e.append("unsafe no-data policy")
    if p.get("low_traffic_policy") not in ("ticket","synthetic-check"): e.append("unsafe low-traffic policy")
    labels=p.get("labels")
    if not isinstance(labels,list) or not {"service","team","severity","cluster"}.issubset(labels) or not set(labels).issubset(ALLOWED):
        e.append("unsafe labels")
    rules=p.get("rules")
    if not isinstance(rules,list) or not rules: e.append("missing rules");rules=[]
    seen=set()
    for i,r in enumerate(rules):
        name="rule "+str(i)
        if not isinstance(r,dict): e.append(name+" invalid");continue
        if not isinstance(r.get("name"),str) or not r["name"] or r["name"] in seen: e.append(name+" duplicate/missing")
        else: seen.add(r["name"])
        if r.get("severity") not in ("page","ticket"): e.append(name+" severity")
        a=r.get("long_window_minutes");b=r.get("short_window_minutes")
        if type(a) is not int or type(b) is not int or not 0<b<a: e.append(name+" windows")
        burn=r.get("burn_rate")
        if type(burn) not in (int,float) or burn<=0: e.append(name+" burn")
        duration=r.get("for_minutes")
        if type(duration) is not int or duration<0: e.append(name+" duration")
    return e
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 slo_gate.py fixtures/healthy.json")
    try: issues=validate(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as exc: sys.exit("input error: "+str(exc))
    print(json.dumps({"status":"FAIL" if issues else "PASS","issues":issues},indent=2))
    sys.exit(bool(issues))
```

### tests/test_slo_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from slo_gate import validate
class SLOTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def mutate(self,f):
        p=copy.deepcopy(self.p);f(p);return validate(p)
    def test_healthy(self): self.assertEqual(validate(self.p),[])
    def test_degraded(self): self.assertTrue(validate(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_non_object(self): self.assertTrue(validate(None))
    def test_service(self): self.assertTrue(self.mutate(lambda p:p.update(service="")))
    def test_team(self): self.assertTrue(self.mutate(lambda p:p.update(team="")))
    def test_runbook(self): self.assertTrue(self.mutate(lambda p:p.update(runbook="")))
    def test_receiver(self): self.assertTrue(self.mutate(lambda p:p.update(receiver="")))
    def test_fallback(self): self.assertTrue(self.mutate(lambda p:p.update(fallback_receiver="dbre-test")))
    def test_review(self): self.assertTrue(self.mutate(lambda p:p.update(reviewed=False)))
    def test_route(self): self.assertTrue(self.mutate(lambda p:p.update(route_tested=False)))
    def test_slo_one(self): self.assertTrue(self.mutate(lambda p:p.update(slo=1)))
    def test_slo_zero(self): self.assertTrue(self.mutate(lambda p:p.update(slo=0)))
    def test_window(self): self.assertTrue(self.mutate(lambda p:p.update(window_days=0)))
    def test_traffic(self): self.assertTrue(self.mutate(lambda p:p.update(request_rate_per_minute=-1)))
    def test_min_traffic(self): self.assertTrue(self.mutate(lambda p:p.update(minimum_traffic_per_minute=-1)))
    def test_no_data(self): self.assertTrue(self.mutate(lambda p:p.update(no_data_policy="ignore")))
    def test_low_traffic(self): self.assertTrue(self.mutate(lambda p:p.update(low_traffic_policy="ignore")))
    def test_labels(self): self.assertTrue(self.mutate(lambda p:p["labels"].append("request_id")))
    def test_missing_labels(self): self.assertTrue(self.mutate(lambda p:p.update(labels=["team"])))
    def test_no_rules(self): self.assertTrue(self.mutate(lambda p:p.update(rules=[])))
    def test_duplicate_rule(self): self.assertTrue(self.mutate(lambda p:p["rules"][1].update(name="FastBurn")))
    def test_severity(self): self.assertTrue(self.mutate(lambda p:p["rules"][0].update(severity="debug")))
    def test_short_long(self): self.assertTrue(self.mutate(lambda p:p["rules"][0].update(short_window_minutes=61)))
    def test_zero_window(self): self.assertTrue(self.mutate(lambda p:p["rules"][0].update(short_window_minutes=0)))
    def test_burn(self): self.assertTrue(self.mutate(lambda p:p["rules"][0].update(burn_rate=0)))
    def test_duration(self): self.assertTrue(self.mutate(lambda p:p["rules"][0].update(for_minutes=-1)))
if __name__=="__main__": unittest.main()
```

### Execute

```bash
cd chapter029
python3 scripts/slo_gate.py fixtures/healthy.json
if python3 scripts/slo_gate.py fixtures/degraded.json; then
  echo "FAIL: unsafe alert policy accepted"; exit 1
else
  echo "PASS: unsafe policy rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL, **26 automated unit tests pass**.

## 7. Optional staging Prometheus and Alertmanager integration

1. Configure synthetic counters and representative request rates in an isolated environment.
2. Validate rule syntax with `promtool check rules`.
3. Compare fast and medium burn expressions against controlled error ratios.
4. Exercise low traffic, no traffic, absent series and counter resets.
5. Verify page versus ticket routing using Chapter 026's test-only receivers.
6. Verify silences/inhibition do not hide unrelated clusters.
7. Revert the rule revision and capture recovery evidence.

Do not send synthetic alerts to production paging integrations.

## 8. Twenty-four hands-on exercises

1. Define a user-facing SLI.
2. Choose a 30-day SLO.
3. Compute error budget fraction.
4. Compute burn rate.
5. Calculate 14.4x one-hour budget consumption.
6. Compare 5m and 1h windows.
7. Compare 30m and 6h windows.
8. Choose slow-burn ticket thresholds.
9. Implement recording rule.
10. Implement fast-burn alert.
11. Implement medium-burn alert.
12. Implement slow-burn ticket.
13. Validate missing series.
14. Design low-traffic fallback.
15. Bound labels and cardinality.
16. Review minimum request volume.
17. Set for and keep-firing-for.
18. Test Alertmanager grouping.
19. Design escalation and fallback.
20. Audit silences and inhibition.
21. Simulate paging noise.
22. Run healthy gate.
23. Reject degraded gate.
24. Run 26 tests and score review.

## 9. Twenty-four production failure scenarios

| # | Failure | Initial diagnostic |
|---|---|---|
| 01 | SLO threshold wrong | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 02 | SLI numerator/denominator mismatch | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 03 | Counter reset misread | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 04 | Low request volume | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 05 | No data interpreted as zero | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 06 | Scrape target vanished | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 07 | High-cardinality label | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 08 | Burn rate window reversed | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 09 | Short window too noisy | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 10 | Long window hides outage | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 11 | Incorrect 30-day budget math | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 12 | Missing route owner | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 13 | Duplicate alerts | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 14 | Flapping condition | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 15 | Alert stuck pending | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 16 | Slow burn pages overnight | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 17 | Fast burn sent as ticket | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 18 | SLO burn alert silenced broadly | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 19 | Inhibition hides critical page | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 20 | Dashboard stale data | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 21 | Metrics backend outage | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 22 | Traffic surge | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 23 | Prometheus rule load failure | Check SLI math, query window, traffic, missing series, routing and incident impact |
| 24 | Fallback receiver unavailable | Check SLI math, query window, traffic, missing series, routing and incident impact |

## 10. Eight production runbooks

**A. Burn-rate page:** Confirm user-facing SLI, request volume, short and long window, error budget and impact.

**B. Missing data:** Inspect target inventory, scrape status, absent series and dedicated telemetry-health alert.

**C. Alert storm:** Review grouping, labels, short-window noise, duplicate rules, routing and silences.

**D. Low-traffic service:** Check denominator reliability; use synthetic checks or ticket-level fallback instead of unreliable ratios.

**E. False positive:** Verify recording rule math, counter resets, latency/error classification and pending period.

**F. SLO budget exhaustion:** Estimate remaining budget, freeze risky releases where policy requires, and coordinate incident response.

**G. Misrouted page:** Inspect team/service/severity labels, Alertmanager routing and backup receiver.

**H. Rollback:** Revert approved PromQL rules, validate with promtool, reload and verify alert delivery in staging.

## 11. Incident simulation

A PostgreSQL-backed API experiences 3% 5xx errors for 12 minutes, then traffic drops sharply. A fast-burn page fires but the short-window ratio becomes unstable and a broad silence suppresses DBRE notifications. Calculate burn rate against the 99.9% SLO, verify denominator and target inventory, restore test-only routing and document a corrected minimum-volume rule.

## 12. 100-point assessment

| Domain | Points |
|---|---:|
| SLI/SLO and error-budget math | 20 |
| Multiwindow PromQL and recording rules | 20 |
| Noise reduction and incident signal quality | 20 |
| Offline governance and 26 tests | 20 |
| Troubleshooting, runbooks and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory: validated SLI definition, low-traffic/no-data strategy, service ownership, safe fallback route, test evidence and rollback plan.

## 13. Evidence worksheet

```text
UTC / owner / SLO target and window:
Numerator / denominator / excluded requests:
Fast and medium burn thresholds:
Minimum volume and missing-series policy:
Alert labels / route / test receiver:
Noise baseline / false pages / incident history:
Healthy/degraded gate / 26 tests:
Rule validation / rollback / reviewer / score:
```

**Companion:** [Chapter 029 executable alert-quality lab](labs/029-alert-quality-engineering-noise-reduction-slo-burn-rate-alerts-incident-signal-design-lab.md).

**Next:** Chapter 030 — Enterprise Alert Engineering, SLOs, On-Call and Incident Response Production Capstone.
