# Chapter 041 — Elasticsearch and OpenSearch Logging Architecture, Index Design and Ingestion Foundations

**Part 09 — Elasticsearch and OpenSearch Logging**  
**Audience:** SRE/DBRE, observability engineers, data platform operators.  
**Prerequisites:** Chapters 036–040, REST APIs, JSON, Elasticsearch/OpenSearch fundamentals, Python 3.10+.

## 1. Learning objectives

Design a production log pipeline; compare Elasticsearch and OpenSearch architecture; create explicit mappings and lifecycle policies; safely ingest JSON logs; size primary shards; diagnose indexing failures; enforce privacy and change controls.

## 2. Architecture

```text
Applications / PostgreSQL / Kubernetes / Linux
           |          |
      Fluent Bit / Vector / Elastic Agent / OpenTelemetry Collector
           |
      transform -> redact -> buffer / retry / dead-letter
           |
        load balancer / HTTPS
           |
 Elasticsearch or OpenSearch data nodes
     ingest pipeline -> data stream / write index
           |
      primary shards -> replicas -> searchable segments
           |
       Kibana / OpenSearch Dashboards
           |
       alerting / incident response
```

Elasticsearch and OpenSearch are related but **not API-identical**. Verify distribution/version before applying lifecycle, security, ingest, or data-stream examples. Elasticsearch uses Index Lifecycle Management (ILM); OpenSearch commonly uses Index State Management (ISM). Do not apply ILM policy endpoints to OpenSearch as if interchangeable.

## 3. Data modeling and shard strategy

| Field | Mapping | Rationale |
|---|---|---|
| `@timestamp` | `date` | UTC event time |
| `service.name` | `keyword` | filtering/aggregation |
| `log.level` | `keyword` | filtering |
| `message` | `match_only_text` (Elastic-compatible versions) | cost-conscious log search |
| `trace.id` | `keyword` | trace correlation |
| `event.duration` | `long` | numeric latency |

OpenSearch may not support every Elasticsearch field type identically; for a portable lab use `text` for `message` and verify target-version support. Do not map arbitrary JSON as unrestricted dynamic fields. Explicitly control fields and redact PII, PHI and secrets before indexing.

**Sizing:** Estimate primary-shard storage as daily ingest × index retention/rollover span × compression/index expansion ÷ primary count. The lab governance target is **10–50 GB per primary shard**, with 40 GB as an operational review threshold; workload-specific benchmarking overrides generic targets. Avoid both hundreds of tiny shards and >100 GB shards that make recovery and merges expensive.

## 4. Version-aware example: composable index template (Elasticsearch 8.x)

```http
PUT _index_template/logs-app-v1
Content-Type: application/json

{
  "index_patterns": ["logs-app-*"],
  "priority": 200,
  "template": {
    "settings": {"number_of_shards": 1, "number_of_replicas": 1, "refresh_interval": "30s"},
    "mappings": {
      "dynamic": false,
      "properties": {
        "@timestamp": {"type": "date"},
        "service": {"properties": {"name": {"type": "keyword"}}},
        "log": {"properties": {"level": {"type": "keyword"}}},
        "message": {"type": "match_only_text"},
        "trace": {"properties": {"id": {"type": "keyword"}}}
      }
    }
  }
}
```

Review existing templates for collisions. In Elasticsearch, use data streams for append-only time-series logs when compatible; write via the data-stream name. In OpenSearch, verify supported templates, data streams and mapping types first.

## 5. Ingest pipeline and simulation

```http
PUT _ingest/pipeline/logs-normalize-v1
Content-Type: application/json

{
  "description": "Lab-only normalized logs",
  "processors": [
    {"set": {"field": "event.ingested", "value": "{{_ingest.timestamp}}"}},
    {"lowercase": {"field": "log.level", "ignore_missing": true}}
  ]
}
```

```http
POST _ingest/pipeline/logs-normalize-v1/_simulate
Content-Type: application/json

{"docs":[{"_source":{"@timestamp":"2026-10-18T12:00:00Z","service":{"name":"orders-api"},"log":{"level":"ERROR"},"message":"synthetic timeout"}}]}
```

The example does **not** redact sensitive data. Redaction must occur upstream or in a separately tested ingest processor before production data is indexed.

## 6. Bulk indexing and failure handling

Bulk requests use NDJSON action/source pairs with a final newline. Always inspect the top-level `errors` flag **and each item response**, even when HTTP status is 200. Retry transient 429/503 with exponential backoff and jitter; isolate nonretryable mapping/pipeline failures into a protected dead-letter workflow. Use deterministic document IDs when idempotent retries matter.

```text
{"index":{"_index":"logs-app-000001"}}
{"@timestamp":"2026-10-18T12:00:00Z","service":{"name":"orders-api"},"log":{"level":"error"},"message":"synthetic timeout"}
```

## 7. Production observability and troubleshooting

```http
GET _cluster/health
GET _cat/shards/logs-app-*?v&bytes=gb
GET _nodes/stats/indices,indexing_pressure,thread_pool,fs
GET _cat/indices/logs-app-*?v
GET _ingest/pipeline/logs-normalize-v1
```

Monitor rejected writes, ingest latency, merges, refresh costs, heap pressure, IOPS/latency, disk watermarks, shard allocation and lifecycle transitions. Never resolve disk pressure by deleting unapproved log indices.

## 8. Executable offline index-governance lab

The JSON is **synthetic governance metadata**, not an Elasticsearch/OpenSearch configuration file. It checks design rules but cannot validate a running cluster.

### healthy.json

```json
{
  "environment": "staging",
  "owner": "platform-dbre",
  "index_prefix": "logs-app",
  "template_priority": 200,
  "shards": 1,
  "replicas": 1,
  "refresh_interval": "30s",
  "retention_days": 14,
  "estimated_daily_gb": 15,
  "estimated_primary_shard_gb": 15,
  "shard_target_min_gb": 10,
  "shard_target_max_gb": 50,
  "ingest_pipeline": "logs-normalize-v1",
  "timestamp_field": "@timestamp",
  "fields": {
    "@timestamp": "date",
    "service.name": "keyword",
    "log.level": "keyword",
    "message": "match_only_text",
    "trace.id": "keyword",
    "event.duration": "long"
  },
  "dynamic_mapping": false,
  "pii_redaction_reviewed": true,
  "secret_redaction_reviewed": true,
  "ilm_ism_reviewed": true,
  "rbac_reviewed": true,
  "tls_reviewed": true,
  "rollback_tested": true,
  "dlq_reviewed": true
}
```

### index_gate.py

```python
"""Offline index governance; does not connect to Elasticsearch or OpenSearch."""
import json,sys
from pathlib import Path
REQUIRED={"@timestamp":"date","service.name":"keyword","log.level":"keyword","message":"match_only_text"}
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("environment","owner","index_prefix","ingest_pipeline","timestamp_field"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 for k in ("pii_redaction_reviewed","secret_redaction_reviewed","ilm_ism_reviewed","rbac_reviewed","tls_reviewed","rollback_tested","dlq_reviewed"):
  if p.get(k) is not True:e.append("missing review "+k)
 for k in ("shards","replicas","retention_days","template_priority","estimated_daily_gb","estimated_primary_shard_gb","shard_target_min_gb","shard_target_max_gb"):
  if type(p.get(k)) is not int or p[k]<0:e.append("invalid "+k)
 if type(p.get("shards")) is int and p["shards"]<1:e.append("no primaries")
 if type(p.get("retention_days")) is int and not 1<=p["retention_days"]<=90:e.append("retention out of lab range")
 if p.get("dynamic_mapping") is not False:e.append("uncontrolled dynamic mapping")
 if p.get("refresh_interval") not in ("30s","60s"):e.append("unreviewed refresh")
 fields=p.get("fields")
 if not isinstance(fields,dict) or any(fields.get(k)!=v for k,v in REQUIRED.items()):e.append("missing canonical mapping")
 if isinstance(fields,dict) and any(k in fields for k in ("password","patient_name","raw_token")):e.append("sensitive fields")
 if p.get("timestamp_field")!="@timestamp":e.append("invalid timestamp")
 size=p.get("estimated_primary_shard_gb");lo=p.get("shard_target_min_gb");hi=p.get("shard_target_max_gb")
 if all(type(x) is int for x in (size,lo,hi)) and not 0<lo<=size<=hi<=50:e.append("shard size outside policy")
 return e
if __name__=="__main__":
 findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_index_gate.py

```python
import copy,json,unittest
from pathlib import Path
from index_gate import validate
class GateTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_index_prefix(self):
  p=copy.deepcopy(self.p);p["index_prefix"]="";self.assertTrue(validate(p))
 def test_03_ingest_pipeline(self):
  p=copy.deepcopy(self.p);p["ingest_pipeline"]="";self.assertTrue(validate(p))
 def test_04_shards(self):
  p=copy.deepcopy(self.p);p["shards"]=0;self.assertTrue(validate(p))
 def test_05_replicas(self):
  p=copy.deepcopy(self.p);p["replicas"]=-1;self.assertTrue(validate(p))
 def test_06_retention_days(self):
  p=copy.deepcopy(self.p);p["retention_days"]=0;self.assertTrue(validate(p))
 def test_07_retention_days(self):
  p=copy.deepcopy(self.p);p["retention_days"]=365;self.assertTrue(validate(p))
 def test_08_template_priority(self):
  p=copy.deepcopy(self.p);p["template_priority"]=-1;self.assertTrue(validate(p))
 def test_09_estimated_daily_gb(self):
  p=copy.deepcopy(self.p);p["estimated_daily_gb"]=-1;self.assertTrue(validate(p))
 def test_10_estimated_primary_shard_gb(self):
  p=copy.deepcopy(self.p);p["estimated_primary_shard_gb"]=80;self.assertTrue(validate(p))
 def test_11_shard_target_min_gb(self):
  p=copy.deepcopy(self.p);p["shard_target_min_gb"]=0;self.assertTrue(validate(p))
 def test_12_shard_target_max_gb(self):
  p=copy.deepcopy(self.p);p["shard_target_max_gb"]=100;self.assertTrue(validate(p))
 def test_13_dynamic_mapping(self):
  p=copy.deepcopy(self.p);p["dynamic_mapping"]=True;self.assertTrue(validate(p))
 def test_14_refresh_interval(self):
  p=copy.deepcopy(self.p);p["refresh_interval"]="1s";self.assertTrue(validate(p))
 def test_15_timestamp_field(self):
  p=copy.deepcopy(self.p);p["timestamp_field"]="timestamp";self.assertTrue(validate(p))
 def test_16_pii_redaction_reviewed(self):
  p=copy.deepcopy(self.p);p["pii_redaction_reviewed"]=False;self.assertTrue(validate(p))
 def test_17_secret_redaction_reviewed(self):
  p=copy.deepcopy(self.p);p["secret_redaction_reviewed"]=False;self.assertTrue(validate(p))
 def test_18_ilm_ism_reviewed(self):
  p=copy.deepcopy(self.p);p["ilm_ism_reviewed"]=False;self.assertTrue(validate(p))
 def test_19_rbac_reviewed(self):
  p=copy.deepcopy(self.p);p["rbac_reviewed"]=False;self.assertTrue(validate(p))
 def test_20_tls_reviewed(self):
  p=copy.deepcopy(self.p);p["tls_reviewed"]=False;self.assertTrue(validate(p))
 def test_21_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_22_dlq_reviewed(self):
  p=copy.deepcopy(self.p);p["dlq_reviewed"]=False;self.assertTrue(validate(p))
 def test_23_fields(self):
  p=copy.deepcopy(self.p);p["fields"]={"message":"text"};self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

### Execute

```bash
mkdir -p chapter041 && cd chapter041
# Save the three blocks as healthy.json, index_gate.py and test_index_gate.py
python3 index_gate.py healthy.json
python3 -m unittest -v test_index_gate.py
```

Expected: PASS and **25 authored tests** pass. The sample shard target is a review policy, not a capacity guarantee.

## 9. Twenty-four hands-on exercises

1. Design collection path.
2. Select Elastic versus OpenSearch APIs.
3. Define JSON event schema.
4. Normalize UTC timestamp.
5. Review message mapping.
6. Use keyword for dimensions.
7. Prevent dynamic field explosion.
8. Estimate ingest GB/day.
9. Estimate primary shard size.
10. Set replica policy.
11. Choose rollover condition.
12. Review ILM versus ISM.
13. Create composable template.
14. Create ingest pipeline.
15. Simulate pipeline.
16. Create write alias or data stream.
17. Send bulk NDJSON.
18. Inspect item-level bulk failures.
19. Query sample events.
20. Check shard allocation.
21. Check disk watermark.
22. Review redaction.
23. Run policy gate.
24. Run tests and rollback.

## 10. Twenty-four production failure scenarios

1. **Mapping explosion:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
2. **Timestamp parsing failure:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
3. **Bulk partial rejection:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
4. **429 write thread pool rejection:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
5. **Pipeline script failure:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
6. **Bad index template priority:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
7. **Shard overgrowth:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
8. **Too many tiny shards:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
9. **Disk watermark exceeded:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
10. **Hot node saturation:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
11. **Merge throttling:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
12. **Refresh overhead:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
13. **Replica unassigned:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
14. **Cluster red status:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
15. **ILM rollover stuck:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
16. **ISM transition stuck:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
17. **Retention deletes wrong data:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
18. **Dynamic mapping field conflict:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
19. **High-cardinality terms aggregation:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
20. **PII ingested into logs:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
21. **Secrets in message:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
22. **TLS handshake failure:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
23. **RBAC 403:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.
24. **DLQ not configured:** inspect ingest response, mapping, shards, disk, lifecycle state, credentials and rollback.

## 11. Eight production runbooks

1. Ingest rejection: inspect bulk item errors, pipeline failures, 429s and backoff with jitter.
2. Mapping conflict: inspect index template priority, field types and source payload; reindex rather than mutate immutable mappings.
3. Disk watermark: inspect allocation, shard sizes and storage I/O; expand capacity or retention safely.
4. Shard explosion: review rollover, template shard count, daily volume and target shard size.
5. Retention failure: inspect ILM/ISM state, policy attachment, index age and deletion approvals.
6. Sensitive log exposure: stop source, restrict access, rotate secrets and coordinate compliant deletion.
7. Search slowness: review query filters, shard fan-out, merges, cache and disk latency.
8. Rollback: revert template/pipeline via versioned change, validate new writes and preserve old data.

## 12. SRE/DBRE incident simulation

A Kubernetes application increases log volume after PostgreSQL timeouts. Dynamic mapping creates thousands of new fields, bulk writes return partial 429 errors, and disk latency slows searches. Use independent service metrics to establish user impact, inspect bulk item failures and mappings, reduce unsafe labels, control shard growth, and stage a new template/pipeline. Preserve evidence and obtain owner approval before any retention or deletion change.

## 13. 100-point acceptance

| Domain | Points |
|---|---:|
| Architecture and schema | 20 |
| Ingestion, lifecycle and shard sizing | 20 |
| Security and operational safety | 20 |
| Offline policy gate and tests | 20 |
| Incident recovery and runbooks | 20 |
| **Total** | **100** |

Recommended pass 85/100. Live validation requires a version-pinned Elasticsearch or OpenSearch test cluster, actual bulk ingestion, mapping inspection, lifecycle checks and rollback evidence.

**Companion:** [Chapter 041 logging architecture lab](labs/041-elasticsearch-opensearch-logging-architecture-index-design-ingestion-foundations-lab.md).

**Next:** Chapter 042 — Elasticsearch and OpenSearch Log Ingestion Pipelines, Fluent Bit, Parsing and Data Quality.
