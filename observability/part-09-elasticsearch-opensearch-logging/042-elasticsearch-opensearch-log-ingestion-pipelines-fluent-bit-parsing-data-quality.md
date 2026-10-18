# Chapter 042 — Elasticsearch and OpenSearch Log Ingestion Pipelines, Fluent Bit, Parsing and Data Quality

**Part 09 — Elasticsearch and OpenSearch Logging**  
**Audience:** SRE, DBRE, Kubernetes/platform engineers.  
**Prerequisites:** Chapter 041, JSON, HTTP bulk API, Fluent Bit, Python 3.10+.

## 1. Learning outcomes

Build a resilient logging ingestion architecture; configure Fluent Bit inputs, filters and outputs; normalize structured logs; implement retries and dead-letter handling; diagnose partial bulk failures; and govern data quality, security and operational cost.

## 2. Reference architecture

```text
Kubernetes / Linux / PostgreSQL / applications
               |
          Fluent Bit agents
    tail / multiline / JSON / metadata
               |
        redact -> normalize
               |
       memory/disk buffer + retry
               |
       HTTPS + least privilege
               |
   Elasticsearch or OpenSearch ingest
               |
      template -> pipeline -> bulk
               |
   write index/data stream + replicas
               |
       Dashboards / alerting
               |
   reject counters / protected DLQ
```

Elasticsearch and OpenSearch share many APIs but have different supported plugin versions, security configuration and lifecycle policies. Pin versions and validate behavior against the chosen distribution.

## 3. Fluent Bit ingestion design

For Kubernetes, choose approved host file paths, service account permissions and DaemonSet resource requests. Persistent filesystem buffering reduces data loss during temporary downstream outages; it does not replace durable source retention or delivery testing. Bound retries, storage, memory and log volume.

### Example local Fluent Bit pipeline (synthetic JSON only)

```ini
[SERVICE]
    Flush        2
    Log_Level    info
    storage.path /tmp/fluent-bit-buffer

[INPUT]
    Name         tail
    Path         /var/log/demo/*.jsonl
    Tag          app.logs
    Parser       json
    DB           /tmp/fluent-bit-tail.db
    storage.type filesystem

[FILTER]
    Name         modify
    Match        app.logs
    Add          environment staging

[OUTPUT]
    Name         stdout
    Match        app.logs
```

The output deliberately uses stdout to avoid sending unreviewed logs to a live cluster. The sample is **not** a redaction pipeline. For production, use supported Elasticsearch/OpenSearch output plugins, authenticated TLS, approved index routing and verified redaction before transmission. Check the installed Fluent Bit version's parser configuration and output compatibility.

### Sample JSON lines

```json
{"@timestamp":"2026-10-18T12:00:00Z","service":{"name":"orders-api"},"log":{"level":"error"},"message":"synthetic timeout","trace":{"id":"demo-001"}}
{"@timestamp":"2026-10-18T12:00:01Z","service":{"name":"orders-api"},"log":{"level":"info"},"message":"synthetic recovered","trace":{"id":"demo-002"}}
```

## 4. Ingest pipeline simulation

```http
PUT _ingest/pipeline/logs-normalize-v2
Content-Type: application/json

{
  "description": "Normalize synthetic log levels",
  "processors": [
    {"lowercase": {"field": "log.level", "ignore_missing": true}},
    {"set": {"field": "event.ingested", "value": "{{_ingest.timestamp}}"}}
  ]
}
```

```http
POST _ingest/pipeline/logs-normalize-v2/_simulate
Content-Type: application/json

{"docs":[{"_source":{"@timestamp":"2026-10-18T12:00:00Z","log":{"level":"ERROR"},"message":"synthetic timeout"}}]}
```

Check version-specific support and mappings. Test actual redaction separately. Processor failures should be observable and either rejected safely or routed to a protected, reviewed failure path.

## 5. Bulk ingestion reliability

Bulk APIs use NDJSON action/source pairs and require a final newline. HTTP 200 does **not** imply every item succeeded: inspect `errors` and each item status. Retry 429/503 with exponential backoff and jitter, and quarantine mapping/validation failures without infinite retries. Preserve deterministic IDs where deduplication is required.

## 6. Data quality contract

| Control | Example check |
|---|---|
| Timestamp | UTC RFC3339, non-null |
| Service | stable keyword dimension |
| Severity | normalized enum |
| Message | bounded size and safe redaction |
| Correlation | trace ID field, not uncontrolled index field |
| Schema | explicit mapping and version |
| Failure handling | item-level errors, DLQ, replay |
| Retention | approved ILM/ISM lifecycle |
| Security | least privilege, TLS, no secrets in logs |

## 7. Executable offline pipeline-governance lab

The JSON below is **synthetic review metadata**, not Fluent Bit or Elasticsearch/OpenSearch configuration. The gate verifies declared controls; it does not prove actual redaction or ingestion behavior.

### healthy.json

```json
{
  "owner": "platform-dbre",
  "environment": "staging",
  "pipeline_version": "v1",
  "source": "kubernetes-application-logs",
  "destination": "logs-app-staging",
  "timestamp_field": "@timestamp",
  "dead_letter_queue": "encrypted-staging-dlq",
  "runbook": "https://example.org/runbooks/log-ingestion",
  "redaction_verified": true,
  "tls_verified": true,
  "least_privilege_reviewed": true,
  "retry_policy_reviewed": true,
  "dlq_replay_tested": true,
  "schema_reviewed": true,
  "rollback_tested": true,
  "bulk_item_errors_checked": true,
  "max_event_kb": 256,
  "estimated_event_kb": 12,
  "queue_capacity_mb": 512,
  "estimated_queue_mb": 128,
  "parse_failure_percent": 0,
  "parse_failure_budget_percent": 1,
  "fields": [
    "@timestamp",
    "service.name",
    "log.level",
    "message",
    "trace.id"
  ]
}
```

### pipeline_gate.py

```python
"""Offline synthetic pipeline contract validator. Does not inspect actual log content."""
import json,sys
from pathlib import Path
REQUIRED={"@timestamp","service.name","log.level","message"}
ALLOWED=REQUIRED|{"trace.id","event.duration","host.name","kubernetes.namespace"}
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be an object"]
 for k in ["owner","environment","pipeline_version","source","destination","timestamp_field","dead_letter_queue","runbook"]:
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 for k in ["redaction_verified","tls_verified","least_privilege_reviewed","retry_policy_reviewed","dlq_replay_tested","schema_reviewed","rollback_tested","bulk_item_errors_checked"]:
  if p.get(k) is not True:e.append("unverified "+k)
 fields=p.get("fields")
 if not isinstance(fields,list) or not REQUIRED.issubset(fields) or not set(fields).issubset(ALLOWED):e.append("unsafe fields")
 for estimate,limit in (("estimated_event_kb","max_event_kb"),("estimated_queue_mb","queue_capacity_mb"),("parse_failure_percent","parse_failure_budget_percent")):
  a=p.get(estimate);b=p.get(limit)
  if type(a) not in (int,float) or type(b) not in (int,float) or a<0 or b<=0 or a>b:e.append("invalid budget "+estimate)
 if p.get("timestamp_field")!="@timestamp":e.append("noncanonical timestamp")
 return e
if __name__=="__main__":
 try: findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_pipeline_gate.py

```python
import copy,json,unittest
from pathlib import Path
from pipeline_gate import validate
class PipelineTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_invalid_object(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_pipeline_version(self):
  p=copy.deepcopy(self.p);p["pipeline_version"]="";self.assertTrue(validate(p))
 def test_04_source(self):
  p=copy.deepcopy(self.p);p["source"]="";self.assertTrue(validate(p))
 def test_05_destination(self):
  p=copy.deepcopy(self.p);p["destination"]="";self.assertTrue(validate(p))
 def test_06_timestamp_field(self):
  p=copy.deepcopy(self.p);p["timestamp_field"]="";self.assertTrue(validate(p))
 def test_07_dead_letter_queue(self):
  p=copy.deepcopy(self.p);p["dead_letter_queue"]="";self.assertTrue(validate(p))
 def test_08_runbook(self):
  p=copy.deepcopy(self.p);p["runbook"]="";self.assertTrue(validate(p))
 def test_09_redaction_verified(self):
  p=copy.deepcopy(self.p);p["redaction_verified"]=False;self.assertTrue(validate(p))
 def test_10_tls_verified(self):
  p=copy.deepcopy(self.p);p["tls_verified"]=False;self.assertTrue(validate(p))
 def test_11_least_privilege_reviewed(self):
  p=copy.deepcopy(self.p);p["least_privilege_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_retry_policy_reviewed(self):
  p=copy.deepcopy(self.p);p["retry_policy_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_dlq_replay_tested(self):
  p=copy.deepcopy(self.p);p["dlq_replay_tested"]=False;self.assertTrue(validate(p))
 def test_14_schema_reviewed(self):
  p=copy.deepcopy(self.p);p["schema_reviewed"]=False;self.assertTrue(validate(p))
 def test_15_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_16_bulk_item_errors_checked(self):
  p=copy.deepcopy(self.p);p["bulk_item_errors_checked"]=False;self.assertTrue(validate(p))
 def test_17_max_event_kb(self):
  p=copy.deepcopy(self.p);p["max_event_kb"]=0;self.assertTrue(validate(p))
 def test_18_estimated_event_kb(self):
  p=copy.deepcopy(self.p);p["estimated_event_kb"]=500;self.assertTrue(validate(p))
 def test_19_queue_capacity_mb(self):
  p=copy.deepcopy(self.p);p["queue_capacity_mb"]=0;self.assertTrue(validate(p))
 def test_20_estimated_queue_mb(self):
  p=copy.deepcopy(self.p);p["estimated_queue_mb"]=900;self.assertTrue(validate(p))
 def test_21_parse_failure_budget_percent(self):
  p=copy.deepcopy(self.p);p["parse_failure_budget_percent"]=0;self.assertTrue(validate(p))
 def test_22_parse_failure_percent(self):
  p=copy.deepcopy(self.p);p["parse_failure_percent"]=5;self.assertTrue(validate(p))
 def test_23_fields(self):
  p=copy.deepcopy(self.p);p["fields"]=["message"];self.assertTrue(validate(p))
 def test_24_fields(self):
  p=copy.deepcopy(self.p);p["fields"]=["@timestamp","service.name","log.level","message","trace.id","password"];self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

### Run

```bash
mkdir -p chapter042 && cd chapter042
# Save the three blocks as healthy.json, pipeline_gate.py, test_pipeline_gate.py
python3 pipeline_gate.py healthy.json
python3 -m unittest -v test_pipeline_gate.py
```

Expected: PASS and **26 authored Python tests**.

## 8. Twenty-four hands-on exercises

1. Draw source-to-index data flow.
2. Inventory log producers.
3. Define JSON event contract.
4. Normalize UTC timestamps.
5. Normalize log severity.
6. Validate required service field.
7. Reject malformed JSON.
8. Review multiline stack traces.
9. Design Fluent Bit inputs.
10. Design Fluent Bit filters.
11. Design buffering.
12. Configure output authentication.
13. Verify TLS certificates.
14. Apply ingest pipeline.
15. Simulate ingest processors.
16. Inspect bulk item errors.
17. Classify retryable failures.
18. Design protected DLQ.
19. Test DLQ replay.
20. Check mapping compatibility.
21. Review secret redaction.
22. Measure parser failure rate.
23. Run offline gate and tests.
24. Execute staged rollback.

## 9. Twenty-four production failure scenarios

1. **Fluent Bit cannot read source:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
2. **Collector restart loses offsets:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
3. **Invalid JSON payload:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
4. **Multiline event split:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
5. **Missing timestamp:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
6. **Timezone skew:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
7. **Unknown severity:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
8. **Dynamic mapping explosion:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
9. **Mapping type conflict:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
10. **Bulk 429 rejection:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
11. **Bulk 400 rejection:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
12. **Partial bulk failure ignored:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
13. **TLS certificate error:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
14. **403 insufficient permissions:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
15. **Credentials exposed:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
16. **PII enters message:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
17. **Retry storm:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
18. **Queue disk full:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
19. **DLQ unavailable:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
20. **DLQ replay duplicates:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
21. **Ingest processor exception:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
22. **Excessive pipeline CPU:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
23. **Search data delayed:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.
24. **Rollback fails:** inspect collector offsets, parsing, output response, ingest pipeline, queue and cluster health.

## 10. Eight operational runbooks

1. **Missing logs:** inspect Fluent Bit inputs, file permissions, offsets, queues and output responses.
2. **Parsing errors:** capture synthetic samples, validate JSON/multiline rules and inspect reject counters.
3. **Bulk rejections:** inspect per-item status, classify 429/503 versus mapping 400, and apply bounded backoff.
4. **Mapping conflict:** compare templates and actual field types; version the target index and reindex safely.
5. **Sensitive data:** stop unsafe ingestion, restrict access, rotate exposed credentials and follow approved retention policy.
6. **Queue/DLQ pressure:** inspect queue usage, encryption, permissions, replay idempotency and age.
7. **Pipeline slowness:** profile ingest processor latency, bulk sizing, shard merges and storage I/O.
8. **Rollback:** revert versioned pipeline/config, validate new writes and reconcile queued events.

## 11. Production DBRE incident game day

A PostgreSQL-backed API produces a burst of JSON error logs during an I/O bottleneck. Fluent Bit queues fill; bulk requests return mixed 429 and mapping 400 failures. Investigate source completeness, parsing, per-item responses, retry pressure, shard size and disk latency. Repair mapping in a versioned index/template, replay protected DLQ records idempotently and validate recovery without deleting source logs.

## 12. 100-point acceptance assessment

| Domain | Points |
|---|---:|
| Fluent Bit architecture and collection | 20 |
| Parsing, mapping and data quality | 20 |
| Bulk reliability and DLQ | 20 |
| Offline governance and automated tests | 20 |
| Incident troubleshooting and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Live acceptance requires version-pinned Fluent Bit and Elasticsearch/OpenSearch, observed bulk item results, tested redaction, DLQ replay and rollback.

## 13. Evidence worksheet

```text
UTC / owner / change ID / environment:
Fluent Bit version / Elasticsearch or OpenSearch version:
Sources / parsers / mapping / ingest pipeline:
Bulk item errors / retry policy / DLQ:
Data quality / redaction / access controls:
Offline gate / 26 tests:
Incident drill / replay / rollback / reviewer:
```

**Companion:** [Chapter 042 hands-on lab](labs/042-elasticsearch-opensearch-log-ingestion-pipelines-fluent-bit-parsing-data-quality-lab.md).

**Next:** Chapter 043 — Elasticsearch and OpenSearch Log Search, Query DSL, Dashboards and Correlation.
