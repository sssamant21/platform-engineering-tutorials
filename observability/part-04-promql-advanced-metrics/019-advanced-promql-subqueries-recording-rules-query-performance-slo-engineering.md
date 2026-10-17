# Chapter 019 — Advanced PromQL Subqueries, Recording Rules, Query Performance and SLO Engineering

**Part 04 — PromQL and Advanced Metrics**  
**Audience:** SRE/DBRE, observability platform and incident engineers.  
**Prerequisites:** Chapters 016–018, Python 3.10+, Prometheus fundamentals.  
**Goal:** Design scalable subqueries and recording rules, test SLO math, bound query cost and operate rule deployments safely.

## 1. Architecture and theory

```text
Scrape targets -> TSDB samples -> instant/range selectors
                                       |
                                 subquery grid
                                       |
                              aggregations / rate
                                       |
                         recording rule evaluation
                                       |
                       recorded time series in TSDB
                                       |
                   dashboards / SLOs / alert rules
```

A subquery evaluates an instant-vector expression repeatedly over a range and returns a range vector. A recording rule evaluates an expression on a schedule and stores the result as new time series. Subqueries increase query flexibility but may multiply computation. Recording rules can reduce repeated dashboard/query work while adding evaluation, storage and cardinality cost.

## 2. Advanced subquery syntax and semantics

```promql
max_over_time(
  rate(http_requests_total{job="api"}[5m])[1h:1m]
)
```

The inner `rate(...[5m])` is an instant-vector expression. `[1h:1m]` re-evaluates it over the trailing hour at one-minute resolution, creating a range vector consumed by `max_over_time`. The subquery's step and range are not the same as the counter's inner five-minute window.

```promql
avg_over_time(
  sum by (cluster, service) (rate(http_requests_total[5m]))[30m:1m]
)
```

Use explicit resolution where predictability matters. Subqueries can be nested, but expensive selectors, long windows and fine resolutions increase memory and CPU. The actual alignment and resolution semantics are governed by the Prometheus engine; do not assume an offline grid exactly reproduces the engine.

## 3. Recording rules and GitOps

```yaml
groups:
  - name: service-request-rates
    interval: 30s
    rules:
      - record: service:http_requests:rate5m
        expr: sum by (cluster, service) (rate(http_requests_total[5m]))
        labels:
          team: platform
      - record: service:http_errors:rate5m
        expr: sum by (cluster, service) (rate(http_requests_total{status=~"5.."}[5m]))
        labels:
          team: platform
```

Prometheus rule files are configured via `rule_files`; changing a file alone does not guarantee it is loaded. Use the deployment's approved configuration reload/restart mechanism. Validate with a compatible `promtool check rules` and `promtool test rules` before rollout.

Recording-rule names should be meaningful, stable and consistent with team conventions. Preserve cluster, service and tenant isolation labels. Rule labels can overwrite existing labels; review collision behavior and avoid sensitive identifiers.

## 4. Rule testing example

```yaml
rule_files:
  - service-rates.rules.yml
evaluation_interval: 1m
tests:
  - interval: 1m
    input_series:
      - series: 'http_requests_total{cluster="east",service="api",status="200"}'
        values: '0+60x10'
    promql_expr_test:
      - expr: 'service:http_requests:rate5m{cluster="east",service="api"}'
        eval_time: 10m
        exp_samples:
          - labels: 'service:http_requests:rate5m{cluster="east",service="api",team="platform"}'
            value: 1
```

This is a **teaching fixture**; validate expected labels, test file format and evaluation timing with the exact deployed `promtool` version. Do not claim it has been executed here. Real rule tests should cover resets, sparse scrapes, stale series, zero traffic and cluster isolation.

## 5. Query performance engineering

- **Bound scope:** metric names, jobs, cluster/tenant labels and regex patterns.
- **Bound time:** range and step; avoid retrieving unnecessary history.
- **Bound output:** enforce label budgets, query limits and tenant quotas.
- **Precompute selectively:** recording rules for frequently used expensive expressions, with ownership and retention policies.
- **Measure:** query duration, concurrency, TSDB churn, rule evaluation duration, missed evaluations and query failure rates.
- **Govern:** Git review, promtool validation, canary rules, safe rollback and periodic unused-rule cleanup.

Useful Prometheus metrics include `prometheus_rule_evaluation_duration_seconds`, `prometheus_rule_evaluation_failures_total`, `prometheus_rule_group_last_duration_seconds`, `prometheus_rule_group_iterations_missed_total`, and `prometheus_engine_query_duration_seconds` (check deployed metric availability and label schema).

## 6. SLO recording-rule pattern

```promql
service:http_errors:rate5m
/
service:http_requests:rate5m
```

This ratio requires compatible cluster/service label sets and a positive denominator. For a 99.9% availability SLO, error budget fraction = 0.001; burn rate is the observed error fraction divided by 0.001. Multi-window burn-rate alerting combines fast and slow windows to balance detection speed and noise; choose thresholds and window pairs based on SLO policy, not universal constants.

A practical DBRE policy distinguishes database connectivity errors, replication unavailability, timeouts and application errors. Do not equate query errors with user-visible errors without validating the SLI.

## 7. Read-only investigation

```bash
curl -fsS 'http://127.0.0.1:9090/api/v1/rules'
curl -G 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=prometheus_rule_group_last_duration_seconds'
curl -G 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=prometheus_rule_group_iterations_missed_total'
```

Only use approved endpoints. Rule changes and reloads require a reviewed change ticket, canary validation and rollback plan.

## 8. Executable offline recording-rule governance lab

The Python gate below validates **policy metadata**: record names, review/testing signoff, owner, cluster scope, evaluation intervals, estimated series budgets and sensitive labels. It **does not parse PromQL, validate actual query correctness, calculate SLOs or replace promtool**.

Create:

```text
chapter019/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/rule_gate.py
  tests/test_rule_gate.py
```

### fixtures/healthy.json

```json
{
  "rules": [
    {
      "record": "service:http_requests:rate5m",
      "expr": "sum by (cluster, service) (rate(http_requests_total[5m]))",
      "owner": "sre-observability",
      "reviewed": true,
      "unit_tested": true,
      "preserves_cluster": true,
      "evaluation_interval_seconds": 30,
      "estimated_input_series": 12000,
      "range_window": "5m",
      "labels": {
        "team": "platform"
      }
    },
    {
      "record": "service:http_errors:rate5m",
      "expr": "sum by (cluster, service) (rate(http_requests_total{status=~\"5..\"}[5m]))",
      "owner": "sre-observability",
      "reviewed": true,
      "unit_tested": true,
      "preserves_cluster": true,
      "evaluation_interval_seconds": 30,
      "estimated_input_series": 12000,
      "range_window": "5m",
      "labels": {
        "team": "platform"
      }
    }
  ]
}
```

### fixtures/degraded.json

```json
{
  "rules": [
    {
      "record": "service:http_requests:rate5m",
      "expr": "sum by (cluster, service) (rate(http_requests_total[5m]))",
      "owner": "sre-observability",
      "reviewed": false,
      "unit_tested": false,
      "preserves_cluster": false,
      "evaluation_interval_seconds": 30,
      "estimated_input_series": 500000,
      "range_window": "5m",
      "labels": {
        "team": "platform",
        "patient_id": "unsafe"
      }
    },
    {
      "record": "service:http_requests:rate5m",
      "expr": "sum by (cluster, service) (rate(http_requests_total{status=~\"5..\"}[5m]))",
      "owner": "sre-observability",
      "reviewed": true,
      "unit_tested": true,
      "preserves_cluster": true,
      "evaluation_interval_seconds": 30,
      "estimated_input_series": 12000,
      "range_window": "5m",
      "labels": {
        "team": "platform"
      }
    }
  ]
}
```

### scripts/rule_gate.py

```python
#!/usr/bin/env python3
"""Offline recording-rule policy validator; never executes PromQL."""
import json, math, re, sys
from pathlib import Path
NAME=re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
LABEL=re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
DURATION=re.compile(r"^[1-9][0-9]*(ms|s|m|h|d|w|y)$")
def check(doc):
    issues=[]
    if not isinstance(doc,dict) or not isinstance(doc.get("rules"),list):
        return ["invalid rules document"]
    seen=set()
    for i,r in enumerate(doc["rules"]):
        p=f"rule[{i}]"
        if not isinstance(r,dict):
            issues.append(p+" invalid object"); continue
        name=r.get("record")
        if not isinstance(name,str) or not NAME.fullmatch(name):
            issues.append(p+" invalid record name")
        elif name in seen: issues.append(p+" duplicate record name")
        else: seen.add(name)
        expr=r.get("expr")
        if not isinstance(expr,str) or not expr.strip():
            issues.append(p+" missing expression")
        elif len(expr)>1000: issues.append(p+" expression too long")
        if not isinstance(r.get("owner"),str) or not r["owner"].strip():
            issues.append(p+" missing owner")
        if not isinstance(r.get("reviewed"),bool) or not r["reviewed"]:
            issues.append(p+" not reviewed")
        if not isinstance(r.get("unit_tested"),bool) or not r["unit_tested"]:
            issues.append(p+" unit tests missing")
        if not isinstance(r.get("preserves_cluster"),bool) or not r["preserves_cluster"]:
            issues.append(p+" cluster scope not verified")
        interval=r.get("evaluation_interval_seconds")
        if type(interval) not in (int,float) or not math.isfinite(interval) or interval < 15:
            issues.append(p+" invalid evaluation interval")
        samples=r.get("estimated_input_series")
        if type(samples) is not int or samples < 0 or samples > 100000:
            issues.append(p+" input series budget exceeded")
        duration=r.get("range_window")
        if not isinstance(duration,str) or not DURATION.fullmatch(duration):
            issues.append(p+" invalid range window")
        labels=r.get("labels")
        if not isinstance(labels,dict): issues.append(p+" invalid labels")
        else:
            for k,v in labels.items():
                if not LABEL.fullmatch(k) or not isinstance(v,str):
                    issues.append(p+" invalid label")
                if k.lower() in ("user_id","patient_id","email","request_id","sql_text"):
                    issues.append(p+" sensitive or unbounded label")
    if not doc["rules"]: issues.append("no rules")
    return issues
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 rule_gate.py fixtures/healthy.json")
    try: findings=check(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as e: sys.exit(f"input error: {e}")
    print("RULE POLICY PASS" if not findings else "RULE POLICY FAIL")
    for finding in findings: print("-",finding)
    sys.exit(bool(findings))
```

### tests/test_rule_gate.py

```python
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from rule_gate import check
class RuleGateTests(unittest.TestCase):
    def doc(self,name="healthy.json"):
        return json.loads((ROOT/"fixtures"/name).read_text())
    def changed(self,**changes):
        d=self.doc()
        d["rules"][0].update(changes)
        return check(d)
    def test_healthy(self): self.assertEqual(check(self.doc()),[])
    def test_degraded(self): self.assertTrue(check(self.doc("degraded.json")))
    def test_missing_rules(self): self.assertTrue(check({}))
    def test_empty_rules(self): self.assertTrue(check({"rules":[]}))
    def test_bad_record(self): self.assertTrue(self.changed(record="bad name"))
    def test_missing_expr(self): self.assertTrue(self.changed(expr=""))
    def test_long_expr(self): self.assertTrue(self.changed(expr="a"*1001))
    def test_missing_owner(self): self.assertTrue(self.changed(owner=""))
    def test_not_reviewed(self): self.assertTrue(self.changed(reviewed=False))
    def test_not_tested(self): self.assertTrue(self.changed(unit_tested=False))
    def test_scope(self): self.assertTrue(self.changed(preserves_cluster=False))
    def test_interval(self): self.assertTrue(self.changed(evaluation_interval_seconds=5))
    def test_series(self): self.assertTrue(self.changed(estimated_input_series=100001))
    def test_window(self): self.assertTrue(self.changed(range_window="0m"))
    def test_labels(self): self.assertTrue(self.changed(labels={"bad-label":"x"}))
    def test_sensitive(self): self.assertTrue(self.changed(labels={"patient_id":"123"}))
    def test_duplicate(self):
        d=self.doc()
        d["rules"][1]["record"]=d["rules"][0]["record"]
        self.assertTrue(check(d))
    def test_negative_series(self): self.assertTrue(self.changed(estimated_input_series=-1))
    def test_invalid_boolean(self): self.assertTrue(self.changed(reviewed="yes"))
    def test_invalid_rule(self): self.assertTrue(check({"rules":[None]}))
if __name__=="__main__": unittest.main()
```

### Execute

```bash
cd chapter019
python3 scripts/rule_gate.py fixtures/healthy.json
if python3 scripts/rule_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded rule policy accepted"; exit 1
else
  echo "PASS: degraded rule policy rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy fixture passes, degraded fixture fails and **20 unit tests pass**. This is offline policy testing, not live Prometheus rule evaluation.

## 9. Twenty-four hands-on exercises

1. Inspect a subquery timestamp grid.
2. Compare `[5m]` range selectors and `[30m:1m]` subqueries.
3. Evaluate `rate(counter[5m])[1h:1m]` semantics.
4. Explain subquery nesting and cost.
5. Use `max_over_time` on a subquery.
6. Write a cluster-scoped request-rate recording rule.
7. Write a matching error-rate rule.
8. Choose an evaluation interval.
9. Document lookback and staleness implications.
10. Verify recording-rule names and labels.
11. Define unit tests for counter resets.
12. Test missing-series behavior.
13. Test denominator-zero behavior.
14. Review cardinality and series budgets.
15. Review tenant and cluster label retention.
16. Explain recording-rule deployment ordering.
17. Inspect `/api/v1/rules`.
18. Inspect rule evaluation duration.
19. Inspect rule evaluation failures.
20. Define query latency SLO.
21. Define a burn-rate expression.
22. Execute healthy fixture.
23. Reject degraded fixture and run 20 tests.
24. Complete peer review and rollback evidence.

## 10. Twenty production failure scenarios

| # | Scenario | First investigation |
|---|---|---|
| 01 | subquery step too small | source series, labels, rule timing and owner |
| 02 | subquery range too wide | source series, labels, rule timing and owner |
| 03 | nested subquery timeout | source series, labels, rule timing and owner |
| 04 | rule evaluation exceeds interval | source series, labels, rule timing and owner |
| 05 | rule group skipped evaluations | source series, labels, rule timing and owner |
| 06 | duplicate record name | source series, labels, rule timing and owner |
| 07 | missing cluster label | source series, labels, rule timing and owner |
| 08 | cross-tenant aggregation | source series, labels, rule timing and owner |
| 09 | recording rule creates cardinality explosion | source series, labels, rule timing and owner |
| 10 | missing source metric | source series, labels, rule timing and owner |
| 11 | counter reset handled incorrectly | source series, labels, rule timing and owner |
| 12 | stale input persists in dashboard | source series, labels, rule timing and owner |
| 13 | division by zero in SLO | source series, labels, rule timing and owner |
| 14 | alert references uncreated rule | source series, labels, rule timing and owner |
| 15 | recording-rule name collision | source series, labels, rule timing and owner |
| 16 | high TSDB write amplification | source series, labels, rule timing and owner |
| 17 | expensive regex selector | source series, labels, rule timing and owner |
| 18 | rule rollout lacks rollback | source series, labels, rule timing and owner |
| 19 | sensitive identifier added as label | source series, labels, rule timing and owner |
| 20 | remote-write lag causes stale SLO | source series, labels, rule timing and owner |

## 11. Eight production runbooks

**A. Query latency regression:** Inspect query log, step, range, subquery nesting, cardinality, cache and concurrency; narrow scope before retrying.

**B. Recording-rule failure:** Check `/api/v1/rules`, evaluation failures, source metrics, labels, syntax and service permissions; roll back incompatible rules.

**C. Rule scheduling delay:** Inspect rule evaluation duration against interval, missed iterations, CPU pressure and TSDB contention.

**D. SLO discrepancy:** Compare raw counter rates with recorded rates, timestamps, freshness, aggregation scope and denominator.

**E. Cardinality incident:** Identify new output label combinations, bound selectors, change instrumentation and estimate TSDB cost.

**F. Missing or stale data:** Check scrape discovery, lookback, stale markers, remote-write lag and rule group scheduling.

**G. Security review:** Review rule labels, tenancy, query API exposure, RBAC and secret handling; contain sensitive metrics.

**H. Safe rollout and rollback:** Validate rules with promtool in a pinned compatible environment, run tests, canary deployment, rollback and post-change checks.

## 12. 100-point acceptance assessment

| Domain | Points |
|---|---:|
| Subquery syntax and time-grid semantics | 20 |
| Recording-rule architecture and tests | 20 |
| Query performance and cardinality | 20 |
| Offline policy gate and 20 tests | 20 |
| SLOs, runbooks, incident response and evidence | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory gates: cluster/tenant isolation, query budget, review/test signoff, degraded-fixture rejection, change rollback and 20 passing tests.

## 13. Evidence worksheet

```text
UTC / owner / environment / Prometheus version:
Subquery expression / step / estimated evaluations:
Recording-rule file / record name / group interval:
Rule evaluation duration / failures / missed iterations:
Input/output series budget:
SLO numerator / denominator / missing-data policy:
promtool version and results (if separately run):
Offline healthy/degraded gate / 20 tests:
Canary / rollback / reviewer / assessment score:
```

**Companion:** [Chapter 019 executable lab](labs/019-advanced-promql-subqueries-recording-rules-query-performance-slo-engineering-lab.md).

**Next:** Chapter 020 — PromQL Production Query Engineering, SLO Alerting and Performance Capstone.
