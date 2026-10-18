# Chapter 020 — PromQL Production Query Engineering, SLO Alerting and Performance Capstone

**Part 04 — PromQL and Advanced Metrics: FINAL CAPSTONE**  
**Audience:** Enterprise SRE/DBRE, observability engineers and incident commanders.  
**Prerequisites:** Chapters 016–019; Python 3.10+ for offline lab; optional approved staging Prometheus.  
**Outcome:** Design, review and assess a production PromQL rule pack with reliable SLO alerting, bounded query costs, secure labels, runbooks, and rollback.

## 1. Capstone architecture

```text
Application + PostgreSQL / MongoDB / Redis / Elasticsearch
                     |
           Exporters and instrumentation
                     |
          Prometheus HA scrape / TSDB
                     |
       Raw metrics / rate / histograms
                     |
           Recording rules (GitOps)
                     |
          SLO error ratio + latency
                     |
     Multi-window burn alerts / Alertmanager
                     |
          On-call response + runbooks
```

Use staging or synthetic data for drills. A passing offline policy gate does not prove a live deployment, accurate production SLIs, functioning paging, or disaster recovery.

## 2. Engineering contract

| Control | Production requirement | Evidence |
|---|---|---|
| Selector scope | bounded cluster/service/tenant | peer-reviewed expressions |
| Counter correctness | rate before aggregation | reset tests |
| Histograms | correct le aggregation and buckets | p95 fixture |
| Target completeness | explicit missing-target detection | inventory + absent alerts |
| Recording rules | versioned, reviewed, tested | promtool / GitOps |
| Query cost | cardinality and p95 limits | load test and metrics |
| SLO math | correct numerator/denominator | SLI contract |
| Alerting | multi-window policy and routing | page drill |
| HA/DR | independent failure domains, restore | acceptance records |
| Rollback | tested and owned | change evidence |

## 3. Production PromQL examples

```promql
sum by (cluster, service) (rate(http_requests_total[5m]))
```

```promql
sum by (cluster, service) (rate(http_requests_total{status=~"5.."}[5m]))
/
sum by (cluster, service) (rate(http_requests_total[5m]))
```

```promql
histogram_quantile(
  0.95,
  sum by (cluster, service, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)
```

```promql
absent_over_time(up{job="postgres",instance="pg-primary:9187"}[5m])
```

The metric names and labels are illustrative. `absent_over_time` for a specific expected instance does not replace an authoritative inventory of all expected targets. Keep recording-rule label sets compatible before dividing vectors.

## 4. Multi-window SLO alerting

A 99.9% availability target permits an error fraction of 0.001. Burn rate = observed error fraction / 0.001. A multi-window rule pages only when both a fast and slow window cross policy thresholds, helping reduce noise.

```yaml
groups:
  - name: service-slo
    interval: 30s
    rules:
      - record: service:http_requests:rate5m
        expr: sum by (cluster, service) (rate(http_requests_total[5m]))
      - record: service:http_errors:rate5m
        expr: sum by (cluster, service) (rate(http_requests_total{status=~"5.."}[5m]))
      - alert: ServiceHighErrorBurn
        expr: |
          (
            service:http_errors:rate5m
            /
            service:http_requests:rate5m
          ) > 0.0144
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High 5-minute error fraction for {{ $labels.service }}"
```

**Important:** The YAML above is a **single-window example**, not a complete multi-window burn-rate alert. A real multi-window alert requires separately computed fast and slow recording rules, their matching label sets, thresholds, `and` conditions, minimum-traffic policy, notification routing, and tests. The offline lab below demonstrates the *two-window gate* concept using precomputed fractions.

## 5. Query cost, correctness and security

- Limit high-cardinality label combinations and avoid raw SQL, patient identifiers, email addresses, user IDs or request IDs.
- Preserve cluster/tenant labels when aggregating and vector matching.
- Use `rate()` for counters, `avg_over_time()` for gauges and appropriate histogram functions for latency.
- Bound subquery ranges and steps; precompute frequent expensive queries with tested recording rules.
- Verify `prometheus_rule_group_last_duration_seconds`, missed iterations, query duration and head-series trends in the deployed version.
- Treat empty vectors, stale samples, low traffic and zero denominators explicitly.
- Use least-privilege query access and approved GitOps change control; never assume a local lab authorizes production reloads.

## 6. Safe validation commands

```bash
promtool check rules service-slo.rules.yml
promtool test rules service-slo.test.yml
curl -fsS 'http://127.0.0.1:9090/api/v1/rules'
curl -G 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=prometheus_rule_group_last_duration_seconds'
```

Run `promtool` only when installed with a compatible Prometheus version and the referenced YAML/test files have been created. These commands have **not** been executed against a live environment here.

## 7. Complete executable offline SLO acceptance lab

The Python model validates synthetic error fractions, burn-rate thresholds, query/cardinality budgets, recording-rule timing, target completeness and mandatory change evidence. It **does not parse or execute PromQL** and is not a substitute for Prometheus/Alertmanager integration tests.

Create:

```text
chapter020/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/acceptance.py
  tests/test_acceptance.py
```

### fixtures/healthy.json

```json
{
  "service": "db-api",
  "environment": "staging",
  "owner": "sre-observability",
  "window_minutes": 60,
  "requests": 100000,
  "errors": 35,
  "slo_target": 0.999,
  "fast_window_error_fraction": 0.0012,
  "slow_window_error_fraction": 0.0007,
  "fast_burn_threshold": 14.4,
  "slow_burn_threshold": 6,
  "query_p95_ms": 240,
  "query_p95_budget_ms": 500,
  "estimated_series": 25000,
  "series_budget": 100000,
  "rule_eval_p99_seconds": 1.8,
  "rule_interval_seconds": 30,
  "missing_target_count": 0,
  "cluster_scope_preserved": true,
  "tenant_scope_preserved": true,
  "alert_route_tested": true,
  "rollback_tested": true,
  "restore_drill_tested": true
}
```

### fixtures/degraded.json

```json
{
  "service": "db-api",
  "environment": "staging",
  "owner": "sre-observability",
  "window_minutes": 60,
  "requests": 100000,
  "errors": 400,
  "slo_target": 0.999,
  "fast_window_error_fraction": 0.04,
  "slow_window_error_fraction": 0.012,
  "fast_burn_threshold": 14.4,
  "slow_burn_threshold": 6,
  "query_p95_ms": 1800,
  "query_p95_budget_ms": 500,
  "estimated_series": 300000,
  "series_budget": 100000,
  "rule_eval_p99_seconds": 45,
  "rule_interval_seconds": 30,
  "missing_target_count": 3,
  "cluster_scope_preserved": false,
  "tenant_scope_preserved": false,
  "alert_route_tested": false,
  "rollback_tested": false,
  "restore_drill_tested": false
}
```

### scripts/acceptance.py

```python
#!/usr/bin/env python3
"""Offline SLO and PromQL change acceptance gate; synthetic inputs only."""
import json, math, sys
from pathlib import Path
FIELDS=("window_minutes","requests","errors","slo_target","fast_window_error_fraction",
        "slow_window_error_fraction","fast_burn_threshold","slow_burn_threshold",
        "query_p95_ms","query_p95_budget_ms","estimated_series","series_budget",
        "rule_eval_p99_seconds","rule_interval_seconds","missing_target_count")
FLAGS=("cluster_scope_preserved","tenant_scope_preserved","alert_route_tested",
       "rollback_tested","restore_drill_tested")
def assess(d):
    errors=[]
    if not isinstance(d,dict): return ["input must be an object"]
    for k in ("service","environment","owner"):
        if not isinstance(d.get(k),str) or not d[k].strip():
            errors.append("missing "+k)
    for k in FIELDS:
        v=d.get(k)
        if type(v) not in (int,float) or not math.isfinite(v) or v<0:
            errors.append("invalid "+k)
    for k in FLAGS:
        if type(d.get(k)) is not bool: errors.append("invalid "+k)
    if errors: return errors
    for k in ("window_minutes","requests","query_p95_budget_ms","series_budget",
              "rule_interval_seconds","fast_burn_threshold","slow_burn_threshold"):
        if d[k]<=0: errors.append("must be positive: "+k)
    if not 0<d["slo_target"]<1: errors.append("invalid SLO target")
    if d["errors"]>d["requests"]: errors.append("errors exceed requests")
    if any(d[k]>1 for k in ("fast_window_error_fraction","slow_window_error_fraction")):
        errors.append("invalid error fraction")
    if errors: return errors
    budget=1-d["slo_target"]
    error_fraction=d["errors"]/d["requests"]
    fast_burn=d["fast_window_error_fraction"]/budget
    slow_burn=d["slow_window_error_fraction"]/budget
    if error_fraction>budget: errors.append("SLO error budget exceeded")
    if fast_burn>=d["fast_burn_threshold"] and slow_burn>=d["slow_burn_threshold"]:
        errors.append("multi-window burn alert triggered")
    if d["query_p95_ms"]>d["query_p95_budget_ms"]: errors.append("query latency budget exceeded")
    if d["estimated_series"]>d["series_budget"]: errors.append("cardinality budget exceeded")
    if d["rule_eval_p99_seconds"]>=d["rule_interval_seconds"]:
        errors.append("rule evaluation misses interval budget")
    if d["missing_target_count"]>0: errors.append("missing expected targets")
    for k in FLAGS:
        if not d[k]: errors.append("mandatory evidence missing: "+k)
    return errors
def report(d):
    findings=assess(d)
    if findings: return {"status":"FAIL","findings":findings}
    return {"status":"PASS","findings":[]}
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 acceptance.py fixtures/healthy.json")
    try: result=report(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as e: sys.exit(f"input error: {e}")
    print(json.dumps(result,indent=2))
    sys.exit(result["status"]!="PASS")
```

### tests/test_acceptance.py

```python
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from acceptance import assess,report
class AcceptanceTests(unittest.TestCase):
    def data(self,name="healthy.json"):
        return json.loads((ROOT/"fixtures"/name).read_text())
    def changed(self,**changes):
        d=self.data()
        d.update(changes)
        return assess(d)
    def test_healthy(self): self.assertEqual(report(self.data())["status"],"PASS")
    def test_degraded(self): self.assertEqual(report(self.data("degraded.json"))["status"],"FAIL")
    def test_missing_owner(self): self.assertTrue(self.changed(owner=""))
    def test_invalid_requests(self): self.assertTrue(self.changed(requests=0))
    def test_errors_exceed(self): self.assertTrue(self.changed(errors=100001))
    def test_budget(self): self.assertTrue(self.changed(errors=150))
    def test_fast_slow_burn(self): self.assertTrue(self.changed(fast_window_error_fraction=.03,slow_window_error_fraction=.01))
    def test_only_fast_not_multiwindow(self): self.assertEqual(self.changed(fast_window_error_fraction=.03,slow_window_error_fraction=.0001),[])
    def test_only_slow_not_multiwindow(self): self.assertEqual(self.changed(fast_window_error_fraction=.0001,slow_window_error_fraction=.01),[])
    def test_query_latency(self): self.assertTrue(self.changed(query_p95_ms=1000))
    def test_series_budget(self): self.assertTrue(self.changed(estimated_series=100001))
    def test_rule_interval(self): self.assertTrue(self.changed(rule_eval_p99_seconds=30))
    def test_missing_targets(self): self.assertTrue(self.changed(missing_target_count=1))
    def test_cluster(self): self.assertTrue(self.changed(cluster_scope_preserved=False))
    def test_tenant(self): self.assertTrue(self.changed(tenant_scope_preserved=False))
    def test_alert_route(self): self.assertTrue(self.changed(alert_route_tested=False))
    def test_rollback(self): self.assertTrue(self.changed(rollback_tested=False))
    def test_restore(self): self.assertTrue(self.changed(restore_drill_tested=False))
    def test_invalid_slo(self): self.assertTrue(self.changed(slo_target=1))
    def test_invalid_bool(self): self.assertTrue(self.changed(rollback_tested="yes"))
    def test_invalid_fraction(self): self.assertTrue(self.changed(fast_window_error_fraction=2))
    def test_nan(self): self.assertTrue(self.changed(query_p95_ms=float("nan")))
    def test_missing_field(self):
        d=self.data()
        del d["errors"]
        self.assertTrue(assess(d))
    def test_not_object(self): self.assertTrue(assess(None))
if __name__=="__main__": unittest.main()
```

### Run

```bash
cd chapter020
python3 scripts/acceptance.py fixtures/healthy.json
if python3 scripts/acceptance.py fixtures/degraded.json; then
  echo "FAIL: degraded SLO policy accepted"; exit 1
else
  echo "PASS: degraded SLO policy rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and **24 unit tests pass**. The healthy fixture's 35 errors per 100,000 requests are below its 0.1% budget. The degraded fixture fails multiple mandatory gates.

## 8. Twenty-four hands-on exercises

1. Define service SLI and SLO.
2. Identify target inventory.
3. Map scrape and recording-rule topology.
4. Write request rate query.
5. Write error rate query.
6. Review label/tenant scope.
7. Review counter reset semantics.
8. Review absent-target detection.
9. Review histogram p95 query.
10. Choose query step and lookback.
11. Review subquery performance.
12. Write recording-rule YAML.
13. Design promtool unit tests.
14. Set cardinality budgets.
15. Measure query latency budget.
16. Set rule evaluation interval.
17. Calculate SLO error budget.
18. Calculate fast-window burn.
19. Calculate slow-window burn.
20. Review multi-window paging criteria.
21. Exercise query failure tabletop.
22. Run healthy and degraded fixtures.
23. Execute 24 automated tests.
24. Document go/no-go, owner and rollback.

## 9. Twenty-four production failure scenarios

| # | Scenario | First diagnostic |
|---|---|---|
| 01 | scrape target missing | Validate metric contract, label scope, query results and incident owner |
| 02 | scrape target down | Validate metric contract, label scope, query results and incident owner |
| 03 | PromQL returns empty vector | Validate metric contract, label scope, query results and incident owner |
| 04 | counter reset | Validate metric contract, label scope, query results and incident owner |
| 05 | query step too fine | Validate metric contract, label scope, query results and incident owner |
| 06 | subquery range too long | Validate metric contract, label scope, query results and incident owner |
| 07 | many-to-many vector match | Validate metric contract, label scope, query results and incident owner |
| 08 | cluster scope dropped | Validate metric contract, label scope, query results and incident owner |
| 09 | tenant labels dropped | Validate metric contract, label scope, query results and incident owner |
| 10 | histogram le removed | Validate metric contract, label scope, query results and incident owner |
| 11 | wrong p95 averaging | Validate metric contract, label scope, query results and incident owner |
| 12 | query p95 regression | Validate metric contract, label scope, query results and incident owner |
| 13 | rule evaluation overrun | Validate metric contract, label scope, query results and incident owner |
| 14 | rule file invalid | Validate metric contract, label scope, query results and incident owner |
| 15 | recording rule duplicates | Validate metric contract, label scope, query results and incident owner |
| 16 | high-cardinality label explosion | Validate metric contract, label scope, query results and incident owner |
| 17 | remote-write stale results | Validate metric contract, label scope, query results and incident owner |
| 18 | fast burn alert without slow burn | Validate metric contract, label scope, query results and incident owner |
| 19 | error budget exhausted | Validate metric contract, label scope, query results and incident owner |
| 20 | alert route unavailable | Validate metric contract, label scope, query results and incident owner |
| 21 | rollback untested | Validate metric contract, label scope, query results and incident owner |
| 22 | restore drill overdue | Validate metric contract, label scope, query results and incident owner |
| 23 | exporter metric renamed | Validate metric contract, label scope, query results and incident owner |
| 24 | SLO denominator zero | Validate metric contract, label scope, query results and incident owner |

## 10. Eight production runbooks

**A. Missing telemetry:** Compare expected target inventory, up and absent_over_time; validate discovery, scrape failures and staleness.

**B. PromQL query regression:** Check selector scope, query duration, step, subqueries, cardinality and vector-match uniqueness.

**C. Counter/histogram correctness:** Validate resets, rate-before-sum, le buckets, units, p95 estimation and sample density.

**D. SLO burn incident:** Verify numerator, denominator, window alignment, traffic minimum, burn policy and alert routing.

**E. Recording rule failure:** Use promtool and /api/v1/rules in staging; inspect evaluation errors, ownership and rollback.

**F. Cardinality/capacity emergency:** Identify high-cardinality labels, sample rate, head series, disk/WAL and ingestion limits.

**G. Alert delivery failure:** Check Alertmanager peers, receivers, route ownership, paging test and incident escalation.

**H. Production change rollback:** Freeze promotion, preserve evidence, revert approved rule changes, revalidate SLO and complete handover.

## 11. Production go/no-go runbook

1. Confirm approved change, named service owner and SLO contract.
2. Verify exporter/target inventory, HA, alert routing and DR evidence.
3. Peer-review all PromQL expressions and cluster/tenant isolation.
4. Validate recording-rule YAML and tests with a compatible promtool.
5. Run offline acceptance and document all 24 unit tests.
6. Canary deploy to authorized staging and compare raw vs recorded series.
7. Run controlled alert-routing, query-failure and rollback drills.
8. Review p95 query cost, cardinality, rule evaluation duration and remote-write freshness.
9. Record incident commander/on-call acceptance and production decision.
10. Roll back immediately if critical gates fail; capture evidence and lessons learned.

## 12. 100-point capstone assessment

| Domain | Points |
|---|---:|
| PromQL query correctness and selector safety | 20 |
| Recording rules, histograms and query performance | 20 |
| SLO/error-budget and multi-window alert design | 20 |
| Offline acceptance lab and 24 tests | 20 |
| Failure drills, runbooks, security and rollback | 20 |
| **Total** | **100** |

Suggested pass: 85/100, **with mandatory gates** for tenant isolation, target coverage, alert routing, rollback/restore evidence and test success. A synthetic pass is not production approval.

## 13. Evidence worksheet

```text
UTC / service / owner / change ticket:
Prometheus version / cluster / tenant:
SLI definition / SLO target / error budget:
Fast/slow windows / burn thresholds:
Query p95 / cardinality / rule duration:
Recording-rule review / promtool results:
Target inventory / missing-data policy:
Alertmanager route / end-to-end paging:
DR restore / rollback rehearsal:
Offline healthy/degraded / 24 tests:
Go-no-go reviewer / score / follow-up:
```

**Companion:** [Chapter 020 executable SLO capstone lab](labs/020-promql-production-query-engineering-slo-alerting-performance-capstone-lab.md).

**Part 04 complete. Next:** Chapter 021 — Grafana Architecture, Installation, Data Sources and Enterprise Dashboard Foundations (Part 05).
