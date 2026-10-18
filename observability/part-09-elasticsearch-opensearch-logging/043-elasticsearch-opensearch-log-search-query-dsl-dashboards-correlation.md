# Chapter 043 — Elasticsearch and OpenSearch Log Search, Query DSL, Dashboards and Correlation

**Part 09 — Elasticsearch and OpenSearch Logging**  
**Audience:** SRE/DBRE, platform observability engineers, incident responders.  
**Prerequisites:** Chapters 041–042, JSON, mappings, REST API, Python 3.10+.

## 1. Outcomes and query architecture

Build efficient, bounded log searches; distinguish term-level and full-text semantics; use safe pagination, aggregations, dashboards and cross-signal correlation; troubleshoot search latency and incorrect results.

```text
Grafana / Kibana / OpenSearch Dashboards
                |
      Query DSL / search API
                |
    coordinating node / search phases
                |
    primary or replica shard copies
                |
       Lucene segments + caches
                |
       fetch phase -> results
```

Search performance depends on index mapping, shard count, disk I/O, query selectivity, cache behavior and fetch volume. Elasticsearch and OpenSearch have diverging APIs and features; verify the target distribution and version.

## 2. Term-level, full-text and structured filters

```json
{
  "size": 100,
  "track_total_hits": false,
  "_source": ["@timestamp","service.name","log.level","message","trace.id"],
  "query": {
    "bool": {
      "filter": [
        {"term": {"service.name": "orders-api"}},
        {"terms": {"log.level": ["error","warn"]}},
        {"range": {"@timestamp": {"gte": "now-30m","lte": "now"}}}
      ],
      "must": [
        {"match_phrase": {"message": "database timeout"}}
      ],
      "must_not": [
        {"term": {"event.dataset": "healthcheck"}}
      ]
    }
  },
  "sort": [{"@timestamp": "desc"}, {"_id": "asc"}]
}
```

Use `term` on keyword fields for exact matches, `match` for analyzed text and `match_phrase` when ordering matters. Filter context avoids relevance scoring for predicates. A `_id` sort may be inefficient or unsupported for certain versions; for **production deep pagination**, prefer a point-in-time (PIT) search with a stable sortable keyword tie-breaker or PIT-provided `_shard_doc` where supported. Never rely on `_id` sorting as a universal recommendation. The offline gate later uses `_id` as a *teaching placeholder*, not a production pagination prescription.

## 3. Log search aggregation patterns

```json
{
  "size": 0,
  "query": {"bool": {"filter": [
    {"term": {"service.name": "orders-api"}},
    {"range": {"@timestamp": {"gte": "now-1h","lte": "now"}}}
  ]}},
  "aggs": {
    "errors_by_minute": {
      "date_histogram": {"field": "@timestamp","fixed_interval": "1m"},
      "aggs": {"by_level": {"terms": {"field": "log.level","size": 5}}}
    }
  }
}
```

Do not confuse log-event counts with request error rates. Collector drops, duplication, sampling and retention gaps can bias metrics. Compare with independently instrumented Prometheus request counters.

## 4. Pagination, performance and cost

- Bound time windows and source fields. Avoid `size: 10000` as a default.
- Prefer `search_after` with PIT for large result sets; ensure a deterministic tie-breaker.
- Use `_profile` in a controlled test, not indiscriminately on production traffic.
- Inspect `_nodes/stats/indices/search,fs,thread_pool`, shard sizes, cache evictions, merges and rejections.
- Treat slow fetch phases and large `_source` payloads as first-class bottlenecks.
- Limit expensive regex, leading wildcards, scripts and high-cardinality aggregations.

## 5. Dashboards and correlation

A practical incident dashboard combines error counts by service, error trends, recent events, top affected namespaces, ingestion lag and independent application SLOs. Include environment and time-range filters, owner, runbook and last validation date. Correlate logs with traces using `trace.id` as a **field** and metrics using service/environment/time. Do not expose patient data, SQL bind values or secrets in dashboards.

## 6. Executable offline query policy lab

The following manifest is **synthetic review metadata**, not Query DSL or proof that a query ran against a cluster.

### healthy.json

```json
{
  "owner": "platform-dbre",
  "environment": "staging",
  "index_pattern": "logs-app-*",
  "time_field": "@timestamp",
  "time_window_minutes": 30,
  "max_time_window_minutes": 60,
  "size": 100,
  "max_size": 500,
  "track_total_hits": false,
  "source_fields": [
    "@timestamp",
    "service.name",
    "log.level",
    "message",
    "trace.id"
  ],
  "allowed_fields": [
    "@timestamp",
    "service.name",
    "log.level",
    "message",
    "trace.id"
  ],
  "filter_fields": [
    "service.name",
    "log.level"
  ],
  "required_filters": [
    "service.name"
  ],
  "query_kind": "bool_filter",
  "uses_wildcard": false,
  "uses_script": false,
  "uses_leading_wildcard": false,
  "uses_search_after": true,
  "stable_sort": [
    "@timestamp",
    "_id"
  ],
  "rbac_reviewed": true,
  "pii_reviewed": true,
  "dashboard_owner_reviewed": true,
  "query_profile_reviewed": true,
  "rollback_tested": true
}
```

### query_gate.py

```python
"""Offline query policy check, not a Query DSL parser or live cluster validation."""
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","index_pattern","time_field","query_kind"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("time_field")!="@timestamp":e.append("invalid time field")
 if p.get("query_kind")!="bool_filter":e.append("query must use bool filter")
 for a,b in (("time_window_minutes","max_time_window_minutes"),("size","max_size")):
  x=p.get(a);y=p.get(b)
  if type(x) is not int or type(y) is not int or not 0<x<=y<=1000:e.append("invalid query budget "+a)
 for k in ("uses_wildcard","uses_script","uses_leading_wildcard"):
  if p.get(k) is not False:e.append("unreviewed expensive query "+k)
 for k in ("rbac_reviewed","pii_reviewed","dashboard_owner_reviewed","query_profile_reviewed","rollback_tested","uses_search_after"):
  if p.get(k) is not True:e.append("missing review "+k)
 allowed=p.get("allowed_fields");source=p.get("source_fields")
 if not isinstance(allowed,list) or not isinstance(source,list) or not set(source).issubset(allowed):e.append("unsafe source fields")
 filters=p.get("filter_fields");required=p.get("required_filters")
 if not isinstance(filters,list) or not isinstance(required,list) or not required or not set(required).issubset(filters):e.append("missing selective filter")
 if p.get("stable_sort")!=["@timestamp","_id"]:e.append("review deterministic pagination sort")
 return e
if __name__=="__main__":
 result=validate(json.loads(Path(sys.argv[1]).read_text()))
 print(json.dumps({"status":"PASS" if not result else "FAIL","findings":result},indent=2))
 sys.exit(bool(result))

```

### test_query_gate.py

```python
import copy,json,unittest
from pathlib import Path
from query_gate import validate
class QueryGateTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_invalid_object(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_index_pattern(self):
  p=copy.deepcopy(self.p);p["index_pattern"]="";self.assertTrue(validate(p))
 def test_04_time_field(self):
  p=copy.deepcopy(self.p);p["time_field"]="timestamp";self.assertTrue(validate(p))
 def test_05_query_kind(self):
  p=copy.deepcopy(self.p);p["query_kind"]="query_string";self.assertTrue(validate(p))
 def test_06_time_window_minutes(self):
  p=copy.deepcopy(self.p);p["time_window_minutes"]=0;self.assertTrue(validate(p))
 def test_07_time_window_minutes(self):
  p=copy.deepcopy(self.p);p["time_window_minutes"]=100;self.assertTrue(validate(p))
 def test_08_max_time_window_minutes(self):
  p=copy.deepcopy(self.p);p["max_time_window_minutes"]=0;self.assertTrue(validate(p))
 def test_09_size(self):
  p=copy.deepcopy(self.p);p["size"]=0;self.assertTrue(validate(p))
 def test_10_size(self):
  p=copy.deepcopy(self.p);p["size"]=900;self.assertTrue(validate(p))
 def test_11_max_size(self):
  p=copy.deepcopy(self.p);p["max_size"]=0;self.assertTrue(validate(p))
 def test_12_uses_wildcard(self):
  p=copy.deepcopy(self.p);p["uses_wildcard"]=True;self.assertTrue(validate(p))
 def test_13_uses_script(self):
  p=copy.deepcopy(self.p);p["uses_script"]=True;self.assertTrue(validate(p))
 def test_14_uses_leading_wildcard(self):
  p=copy.deepcopy(self.p);p["uses_leading_wildcard"]=True;self.assertTrue(validate(p))
 def test_15_rbac_reviewed(self):
  p=copy.deepcopy(self.p);p["rbac_reviewed"]=False;self.assertTrue(validate(p))
 def test_16_pii_reviewed(self):
  p=copy.deepcopy(self.p);p["pii_reviewed"]=False;self.assertTrue(validate(p))
 def test_17_dashboard_owner_reviewed(self):
  p=copy.deepcopy(self.p);p["dashboard_owner_reviewed"]=False;self.assertTrue(validate(p))
 def test_18_query_profile_reviewed(self):
  p=copy.deepcopy(self.p);p["query_profile_reviewed"]=False;self.assertTrue(validate(p))
 def test_19_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_20_uses_search_after(self):
  p=copy.deepcopy(self.p);p["uses_search_after"]=False;self.assertTrue(validate(p))
 def test_21_source_fields(self):
  p=copy.deepcopy(self.p);p["source_fields"]=["password"];self.assertTrue(validate(p))
 def test_22_filter_fields(self):
  p=copy.deepcopy(self.p);p["filter_fields"]=[];self.assertTrue(validate(p))
 def test_23_required_filters(self):
  p=copy.deepcopy(self.p);p["required_filters"]=[];self.assertTrue(validate(p))
 def test_24_stable_sort(self):
  p=copy.deepcopy(self.p);p["stable_sort"]=["@timestamp"];self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

### Run

```bash
mkdir -p chapter043 && cd chapter043
# Save the blocks as healthy.json, query_gate.py, test_query_gate.py
python3 query_gate.py healthy.json
python3 -m unittest -v test_query_gate.py
```

Expected PASS and **26 authored tests**. The gate is intentionally conservative; it does not parse or execute Query DSL.

## 7. Twenty-four practical exercises

1. Inspect index mapping.
2. Inspect field capabilities.
3. Set UTC time filter.
4. Filter by service.
5. Filter by severity.
6. Use bool filter.
7. Use term query on keyword.
8. Use match on text.
9. Compare match_phrase.
10. Use range on timestamp.
11. Exclude noisy health checks.
12. Restrict _source fields.
13. Sort chronologically.
14. Create search_after pagination.
15. Test point-in-time search.
16. Run terms aggregation.
17. Run date histogram.
18. Correlate trace IDs.
19. Correlate PostgreSQL errors.
20. Create saved search.
21. Create error trend dashboard.
22. Profile slow query.
23. Run governance tests.
24. Revert dashboard and query.

## 8. Twenty-four production failure scenarios

1. **Wrong time zone:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
2. **No timestamp filter:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
3. **Missing service selector:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
4. **Term query on analyzed text:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
5. **Match query on keyword confusion:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
6. **Query_string expensive:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
7. **Leading wildcard:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
8. **Regex explosion:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
9. **Too many shards:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
10. **Excessive size:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
11. **Deep from/size pagination:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
12. **search_after unstable:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
13. **PIT expired:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
14. **PIT not closed:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
15. **Source leaks PII:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
16. **RBAC 403:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
17. **Mapping mismatch:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
18. **Fielddata disabled:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
19. **High-cardinality aggregation:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
20. **Date histogram timezone confusion:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
21. **Empty result from delayed ingestion:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
22. **Slow storage I/O:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
23. **Merge pressure:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.
24. **Dashboard owner absent:** inspect query scope, mapping, shard/search metrics, ingestion completeness and security.

## 9. Eight production runbooks

1. **No results:** validate UTC time, index pattern, mapping, ingestion delay and exact keyword values.
2. **Slow searches:** bound time and shards, profile query, inspect IOPS/merges, avoid deep pagination.
3. **Query failures:** inspect mapping, field capabilities, syntax and cluster/search thread-pool rejections.
4. **Pagination anomalies:** use PIT with search_after and a stable tie-breaker; close PIT when done.
5. **Incorrect dashboard:** compare raw hits and aggregations, sampling, timezone and time buckets.
6. **Sensitive result:** restrict _source and access, rotate exposed secrets and follow privacy response.
7. **Cross-platform mismatch:** verify Elasticsearch versus OpenSearch version, query/aggregation compatibility.
8. **Rollback:** restore saved query/dashboard and validate independent service metrics.

## 10. Production incident simulation

An API backed by PostgreSQL and Elasticsearch exhibits 20-second log searches. The dashboard requests 10,000 hits over seven days, uses an expensive text query, and searches many oversized shards on high-latency disks. Correlate with application metrics, reduce time window, use selective filters and source projection, inspect query/fetch latency, shard allocation, storage I/O and cache. Test PIT-based pagination and document the safe rollback.

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Query DSL correctness and mapping | 20 |
| Pagination, search performance and cost | 20 |
| Dashboards, correlation and privacy | 20 |
| Offline gate and automated tests | 20 |
| Incident troubleshooting and runbooks | 20 |
| **Total** | **100** |

Recommended pass 85/100. Live acceptance requires distribution-specific query results, pagination consistency, performance baselines, dashboard validation and rollback evidence.

**Companion:** [Chapter 043 hands-on lab](labs/043-elasticsearch-opensearch-log-search-query-dsl-dashboards-correlation-lab.md).

**Next:** Chapter 044 — Elasticsearch and OpenSearch Logging Lifecycle, Retention, Shard Optimization and Cost Management.
