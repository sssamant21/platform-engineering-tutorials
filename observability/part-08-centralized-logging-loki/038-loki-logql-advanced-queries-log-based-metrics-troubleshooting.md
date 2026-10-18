# Chapter 038 — Loki LogQL Advanced Queries, Log-Based Metrics and Troubleshooting

**Part 08 — Centralized Logging with Loki** · SRE/DBRE production operations · Prerequisites: Chapters 036–037, LogQL fundamentals, Python 3.10+

## Learning outcomes

Develop efficient LogQL queries, derive log-based metrics, distinguish logs from SLIs, diagnose ingestion/query failures, control cardinality and query cost, and execute incident runbooks.

## 1. Query execution architecture

```text
Alloy -> Loki ingestion -> TSDB index + chunks -> query frontend
                                              -> queriers -> LogQL
                                              -> Grafana / ruler / alerts
```

Loki indexes **stream labels**; line filters and parsers act on selected log streams. Always begin with narrow selectors and bounded time ranges. Labels such as service, environment, cluster and namespace should have controlled cardinality. Never index request IDs, trace IDs, SQL text or user identifiers as stream labels.

## 2. LogQL query patterns

```logql
{service="orders-api",environment="staging"} |= "timeout"
{service="orders-api"} != "healthcheck"
{service="orders-api"} | json | level="error"
{service="orders-api"} | json | status >= 500
{service="orders-api"} | json | __error__ = ""
{service="orders-api"} | json | line_format "{{.level}} {{.message}}"
```

A JSON parser extracts fields at query time; extraction does not make those fields index labels. Filter parser failures with `__error__ = ""` where appropriate. Use careful string/number comparison semantics and test on representative samples.

## 3. Log-based metrics and operational caveats

```logql
sum by (service) (rate({service="orders-api"} |= "error" [5m]))
sum by (service) (count_over_time({service="orders-api"} | json | level="error" [5m]))
sum(rate({service="orders-api"} | json | status >= 500 [5m]))
topk(5, sum by (namespace) (rate({cluster="lab"}[5m])))
```

These measure **observed log volume**, not necessarily HTTP request volume, user error rate or actual latency. Sampling, dropped logs, duplication and pipeline filtering bias derived values. Prefer direct Prometheus instrumentation for paging-grade request SLIs. Use log-based metrics as supporting diagnostics unless completeness and semantics are validated.

## 4. Query performance and FinOps

- Narrow stream selectors first, then use simple line filters before JSON/regexp parsing.
- Bound query range and step; avoid full-tenant scans.
- Use recording rules for repeatedly expensive aggregations when justified.
- Monitor query latency, bytes scanned, frontend queues, ingester load, cache hit ratio and object-storage performance.
- Review retention, daily ingest, high-churn labels and tenant limits; do not increase limits as a substitute for correcting a bad query.

## 5. Incident response walkthrough

**Scenario:** PostgreSQL-backed API is slow. Grafana shows few errors despite elevated 5xx from an independent metric. Verify Loki readiness and Alloy push, confirm time range and label selection, inspect `__error__` from JSON parsing, check log sampling/drops, and correlate with PostgreSQL lock waits, CPU, I/O and Prometheus request counters. If request IDs were added as Loki labels, roll back that schema change before raising cardinality limits.

## 6. Executable offline LogQL policy lab

The policy below checks a **restricted teaching subset** of LogQL and intentionally rejects broad/unbounded query shapes. It is **not a LogQL parser** or a substitute for executing queries against Loki.

Create `chapter038/query_gate.py`:

```python
import json,re,sys
from pathlib import Path

ALLOWED={"service","environment","cluster","namespace","team"}
UNSAFE={"request_id","trace_id","user_id","pod_uid","sql_text"}
def validate(p):
    errors=[]
    if not isinstance(p,dict):return ["manifest must be object"]
    queries=p.get("queries")
    if not isinstance(queries,list) or not queries:return ["queries required"]
    if p.get("reviewed") is not True:errors.append("review missing")
    if type(p.get("max_range_minutes")) is not int or not 0<p["max_range_minutes"]<=60:errors.append("invalid range budget")
    for i,q in enumerate(queries):
        if not isinstance(q,dict):errors.append("invalid query");continue
        text=q.get("expression");mins=q.get("range_minutes")
        if not isinstance(text,str) or not text.strip():errors.append("empty query");continue
        selector=re.search(r"\{([^{}]*)\}",text)
        if not selector:errors.append("missing selector");continue
        labels=set(re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=~|!~|=|!=)',selector.group(1)))
        if not labels or not labels.issubset(ALLOWED) or labels.intersection(UNSAFE):errors.append("unsafe selector")
        if not re.search(r'\b(service|namespace)\s*=',selector.group(1)):errors.append("selector too broad")
        if type(mins) is not int or mins<=0 or mins>p["max_range_minutes"]:errors.append("unbounded range")
        if "| regexp" in text and q.get("regexp_reviewed") is not True:errors.append("regexp review missing")
    return errors
if __name__=="__main__":
    result=validate(json.loads(Path(sys.argv[1]).read_text()))
    print(json.dumps({"status":"PASS" if not result else "FAIL","findings":result},indent=2))
    sys.exit(bool(result))
```

Create `chapter038/healthy.json`:

```json
{"reviewed":true,"max_range_minutes":30,"queries":[{"expression":"{service=\"orders-api\",environment=\"staging\"} |= \"timeout\"","range_minutes":15},{"expression":"sum(rate({service=\"orders-api\"} | json | level=\"error\" [5m]))","range_minutes":10}]}
```

Create `chapter038/degraded.json`:

```json
{"reviewed":false,"max_range_minutes":30,"queries":[{"expression":"{request_id=\"req-123\"} | regexp \".*\"","range_minutes":120}]}
```

Create `chapter038/test_query_gate.py`:

```python
import copy,json,unittest
from pathlib import Path
from query_gate import validate
ROOT=Path(__file__).parent
class GateTests(unittest.TestCase):
    def setUp(self):self.p=json.loads((ROOT/"healthy.json").read_text())
    def reject(self,fn):
        p=copy.deepcopy(self.p);fn(p);self.assertTrue(validate(p))
    def test_healthy(self):self.assertEqual(validate(self.p),[])
    def test_degraded(self):self.assertTrue(validate(json.loads((ROOT/"degraded.json").read_text())))
    def test_nonobject(self):self.assertTrue(validate(None))
    def test_review(self):self.reject(lambda p:p.update(reviewed=False))
    def test_range_budget(self):self.reject(lambda p:p.update(max_range_minutes=0))
    def test_no_queries(self):self.reject(lambda p:p.update(queries=[]))
    def test_no_expression(self):self.reject(lambda p:p["queries"][0].update(expression=""))
    def test_no_selector(self):self.reject(lambda p:p["queries"][0].update(expression="timeout"))
    def test_request_id(self):self.reject(lambda p:p["queries"][0].update(expression='{request_id="x"}'))
    def test_cluster_only(self):self.reject(lambda p:p["queries"][0].update(expression='{cluster="lab"}'))
    def test_long_range(self):self.reject(lambda p:p["queries"][0].update(range_minutes=999))
    def test_zero_range(self):self.reject(lambda p:p["queries"][0].update(range_minutes=0))
    def test_regex_review(self):self.reject(lambda p:p["queries"][0].update(expression='{service="api"} | regexp ".*"'))
    def test_empty_labels(self):self.reject(lambda p:p["queries"][0].update(expression='{} |= "timeout"'))
if __name__=="__main__":unittest.main()
```

Execute:

```bash
cd chapter038
python3 query_gate.py healthy.json
if python3 query_gate.py degraded.json; then exit 1; fi
python3 -m unittest -v test_query_gate.py
```

Expected: healthy PASS, degraded FAIL and 14 authored unit tests. The offline validator is deliberately conservative and may reject legitimate LogQL; use actual Loki for syntax and result validation.

## 7. Twenty-four exercises

1. Compare exact and regex stream selectors.
2. Narrow by service.
3. Narrow by namespace.
4. Apply line contains filter.
5. Apply line excludes filter.
6. Parse JSON.
7. Filter errors.
8. Inspect parser errors.
9. Format output lines.
10. Count log events.
11. Calculate per-second log rate.
12. Aggregate by service.
13. Aggregate by namespace.
14. Rank noisy services.
15. Review metric completeness.
16. Compare against request counter.
17. Investigate missing logs.
18. Investigate duplicate logs.
19. Investigate time skew.
20. Profile expensive queries.
21. Review tenant limits.
22. Review cardinality budget.
23. Run offline gate.
24. Run unit tests and rollback.

## 8. Twenty-four failure scenarios

1. **Missing stream selector:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
2. **Overly broad selector:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
3. **Wrong namespace:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
4. **Wrong time range:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
5. **Invalid JSON:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
6. **Parser error ignored:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
7. **High regex CPU:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
8. **Slow query frontend:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
9. **Querier saturation:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
10. **Index lookup slow:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
11. **Object storage latency:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
12. **Loki 429:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
13. **Loki 500:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
14. **Alloy drops logs:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
15. **Duplicate ingestion:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
16. **Clock skew:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
17. **Cardinality spike:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
18. **Missing labels:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
19. **Schema change:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
20. **Incorrect log rate:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
21. **Misleading SLI:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
22. **Alert false positive:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
23. **Retention expired:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.
24. **Rollback unsuccessful:** inspect query scope, Loki components, collection pipeline, labels and independent service metrics.

## 9. Eight runbooks

1. **No query results:** verify range, labels, source health and ingestion timestamps.
2. **Query timeout:** narrow selector, bound range and inspect querier/frontend metrics.
3. **Parsing failure:** inspect sample lines and `__error__` before aggregation.
4. **Log-rate anomaly:** compare logs against independent request counters and collector drops.
5. **Cardinality spike:** remove volatile labels and restore approved stream budgets.
6. **Loki throttling:** review tenant limits, ingestion rate and queue/backoff behavior.
7. **Privacy event:** restrict exposure, rotate compromised secrets and follow retention policy.
8. **Rollback:** restore known-good query/rule and pipeline config; verify dashboards and alerts.

## 10. 100-point assessment

| Area | Points |
|---|---:|
| LogQL semantics and selectors | 20 |
| Log-based metrics and SLI interpretation | 20 |
| Performance, cardinality and security | 20 |
| Offline lab and tests | 20 |
| Incident simulation and runbooks | 20 |
| **Total** | **100** |

Recommended pass 85/100. Require verified query output, safe labels, reviewed cost, incident recovery and rollback.

**Companion:** [Chapter 038 hands-on lab](labs/038-loki-logql-advanced-queries-log-based-metrics-troubleshooting-lab.md).

**Next:** Chapter 039 — Loki Alerting, Recording Rules, Retention and Enterprise Operations.
