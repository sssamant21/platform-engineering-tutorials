# Chapter 045 — Elasticsearch and OpenSearch Production Logging Reliability, Security and Troubleshooting Capstone

**Part 09 — Elasticsearch and OpenSearch Logging: FINAL CAPSTONE**  
**Audience:** SRE/DBRE, platform engineers, incident commanders, security and governance.  
**Prerequisites:** Chapters 041–044, index lifecycle, query DSL, bulk APIs and Python 3.10+.

## 1. Capstone mission

Build and assess a reliable enterprise logging platform with collection, parsing, bulk ingestion, search, dashboards, lifecycle, backups, security and incident response. Distinguish authored design checks from witnessed runtime validation.

## 2. Reference architecture

```text
Kubernetes / Linux / PostgreSQL / applications
                     |
              Fluent Bit / collectors
       normalize -> redact -> buffer -> retry/DLQ
                     |
                 HTTPS gateway
                     |
     Elasticsearch OR OpenSearch ingest pipeline
                     |
      template -> data stream / write index
                     |
        primaries -> replicas -> segments
                     |
        Kibana / OpenSearch Dashboards
                     |
       alerts + independent service SLIs
                     |
      ILM (Elastic) / ISM (OpenSearch)
                     |
         snapshots / restore / audit
```

Use version-pinned deployments. Elasticsearch and OpenSearch differ in lifecycle, plugins, security, mapping types and APIs; test each independently. This is an architecture, not a complete production manifest.

## 3. Reliability and SLO model

| Signal | Example review target | Evidence |
|---|---|---|
| Ingest success | under 1% rejected events (lab only) | per-item bulk response and DLQ |
| Query latency | p95 under 1000 ms (lab only) | search/query metrics |
| Shard sizing | review at 40 GB, escalate at 50 GB | shard stats |
| Retention | approved 14 days (lab only) | lifecycle explain and data age |
| Restore | witnessed disposable recovery | snapshot + RPO/RTO |
| Security | least privilege, TLS and redaction | negative tests |

These are **illustrative lab budgets**, not universal production SLOs. User-facing SLIs must come from independent application instrumentation: log loss and duplicates can make log-derived error rates misleading.

## 4. Security and governance

Use authenticated HTTPS and least-privilege roles; redact PII/PHI and credentials before indexing; restrict query and export permissions; version templates and pipelines; enforce retention with legal hold and owner approval; encrypt backups and test restore. Never delete indices, force merge hot indices or reindex production data without change approval.

## 5. DBRE incident game day

An API backed by PostgreSQL experiences latency while log volume spikes. Collector queues grow, bulk writes return 429 and mapping 400 errors, and five oversized primaries experience merge throttling and disk contention. Search dashboards are slow and retention policies stall.

**Incident sequence:** confirm impact with independent Prometheus/APM and DB metrics; triage collector and bulk item failures; identify mapping/schema regression; inspect shard sizing, disk latency, merge and fetch phases; verify lifecycle explain; stage a versioned template/rollover/reindex remediation; test DLQ replay, snapshots, alert delivery and rollback. Preserve owner approval and audit evidence.

## 6. Executable offline capstone gate

The following is **synthetic governance metadata**. Boolean review flags are attestations only; this code cannot prove that actual redaction, RBAC, restore or alert delivery occurred.

### healthy.json

```json
{
  "owner": "platform-dbre",
  "environment": "staging",
  "distribution": "elasticsearch",
  "change_id": "OBS-045",
  "index_pattern": "logs-app-*",
  "data_owner_approved": true,
  "pii_redaction_tested": true,
  "rbac_tested": true,
  "tls_tested": true,
  "retention_approved": true,
  "legal_hold_checked": true,
  "backup_restore_tested": true,
  "ingest_retries_tested": true,
  "dlq_replay_tested": true,
  "independent_slo_monitoring": true,
  "rollback_tested": true,
  "incident_drill_completed": true,
  "primary_shard_gb": 25,
  "shard_warning_gb": 40,
  "shard_critical_gb": 50,
  "ingest_error_percent": 0,
  "ingest_error_budget_percent": 1,
  "query_p95_ms": 500,
  "query_p95_budget_ms": 1000,
  "retention_days": 14,
  "replicas": 1,
  "production_delete": false
}
```

### capstone_gate.py

```python
"""Offline synthetic logging capstone policy gate. No network or deletion."""
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","change_id","index_pattern"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("distribution") not in ("elasticsearch","opensearch"):e.append("invalid distribution")
 for k in ["data_owner_approved","pii_redaction_tested","rbac_tested","tls_tested","retention_approved","legal_hold_checked","backup_restore_tested","ingest_retries_tested","dlq_replay_tested","independent_slo_monitoring","rollback_tested","incident_drill_completed"]:
  if p.get(k) is not True:e.append("missing evidence "+k)
 if p.get("production_delete") is not False:e.append("unsafe deletion")
 for k in ("primary_shard_gb","shard_warning_gb","shard_critical_gb","retention_days","replicas","ingest_error_percent","ingest_error_budget_percent","query_p95_ms","query_p95_budget_ms"):
  if type(p.get(k)) is not int or p[k]<0:e.append("invalid "+k)
 if p.get("shard_warning_gb")!=40 or p.get("shard_critical_gb")!=50:e.append("shard thresholds changed")
 for a,b in (("primary_shard_gb","shard_critical_gb"),("ingest_error_percent","ingest_error_budget_percent"),("query_p95_ms","query_p95_budget_ms")):
  x=p.get(a);y=p.get(b)
  if type(x) is int and type(y) is int and (y<=0 or x>y):e.append("budget exceeded "+a)
 if type(p.get("retention_days")) is int and not 1<=p["retention_days"]<=90:e.append("invalid retention")
 return e
if __name__=="__main__":
 findings=validate(json.loads(Path(sys.argv[1]).read_text()))
 print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
 sys.exit(bool(findings))

```

### test_capstone_gate.py

```python
import copy,json,unittest
from pathlib import Path
from capstone_gate import validate
class CapstoneTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_invalid_object(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_change_id(self):
  p=copy.deepcopy(self.p);p["change_id"]="";self.assertTrue(validate(p))
 def test_04_index_pattern(self):
  p=copy.deepcopy(self.p);p["index_pattern"]="";self.assertTrue(validate(p))
 def test_05_distribution(self):
  p=copy.deepcopy(self.p);p["distribution"]="unknown";self.assertTrue(validate(p))
 def test_06_data_owner_approved(self):
  p=copy.deepcopy(self.p);p["data_owner_approved"]=False;self.assertTrue(validate(p))
 def test_07_pii_redaction_tested(self):
  p=copy.deepcopy(self.p);p["pii_redaction_tested"]=False;self.assertTrue(validate(p))
 def test_08_rbac_tested(self):
  p=copy.deepcopy(self.p);p["rbac_tested"]=False;self.assertTrue(validate(p))
 def test_09_tls_tested(self):
  p=copy.deepcopy(self.p);p["tls_tested"]=False;self.assertTrue(validate(p))
 def test_10_retention_approved(self):
  p=copy.deepcopy(self.p);p["retention_approved"]=False;self.assertTrue(validate(p))
 def test_11_legal_hold_checked(self):
  p=copy.deepcopy(self.p);p["legal_hold_checked"]=False;self.assertTrue(validate(p))
 def test_12_backup_restore_tested(self):
  p=copy.deepcopy(self.p);p["backup_restore_tested"]=False;self.assertTrue(validate(p))
 def test_13_ingest_retries_tested(self):
  p=copy.deepcopy(self.p);p["ingest_retries_tested"]=False;self.assertTrue(validate(p))
 def test_14_dlq_replay_tested(self):
  p=copy.deepcopy(self.p);p["dlq_replay_tested"]=False;self.assertTrue(validate(p))
 def test_15_independent_slo_monitoring(self):
  p=copy.deepcopy(self.p);p["independent_slo_monitoring"]=False;self.assertTrue(validate(p))
 def test_16_rollback_tested(self):
  p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
 def test_17_incident_drill_completed(self):
  p=copy.deepcopy(self.p);p["incident_drill_completed"]=False;self.assertTrue(validate(p))
 def test_18_production_delete(self):
  p=copy.deepcopy(self.p);p["production_delete"]=True;self.assertTrue(validate(p))
 def test_19_primary_shard_gb(self):
  p=copy.deepcopy(self.p);p["primary_shard_gb"]=120;self.assertTrue(validate(p))
 def test_20_shard_warning_gb(self):
  p=copy.deepcopy(self.p);p["shard_warning_gb"]=20;self.assertTrue(validate(p))
 def test_21_shard_critical_gb(self):
  p=copy.deepcopy(self.p);p["shard_critical_gb"]=100;self.assertTrue(validate(p))
 def test_22_retention_days(self):
  p=copy.deepcopy(self.p);p["retention_days"]=0;self.assertTrue(validate(p))
 def test_23_retention_days(self):
  p=copy.deepcopy(self.p);p["retention_days"]=120;self.assertTrue(validate(p))
 def test_24_ingest_error_percent(self):
  p=copy.deepcopy(self.p);p["ingest_error_percent"]=20;self.assertTrue(validate(p))
 def test_25_ingest_error_budget_percent(self):
  p=copy.deepcopy(self.p);p["ingest_error_budget_percent"]=0;self.assertTrue(validate(p))
 def test_26_query_p95_ms(self):
  p=copy.deepcopy(self.p);p["query_p95_ms"]=9000;self.assertTrue(validate(p))
 def test_27_query_p95_budget_ms(self):
  p=copy.deepcopy(self.p);p["query_p95_budget_ms"]=0;self.assertTrue(validate(p))
 def test_28_replicas(self):
  p=copy.deepcopy(self.p);p["replicas"]=-1;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

### Run

```bash
mkdir -p chapter045 && cd chapter045
# Save blocks above as healthy.json, capstone_gate.py, test_capstone_gate.py
python3 capstone_gate.py healthy.json
python3 -m unittest -v test_capstone_gate.py
```

Expected PASS and **30 authored Python tests**.

## 7. Twenty-four exercises

1. Inventory logging sources.
2. Review collector backpressure.
3. Review ingest pipeline version.
4. Validate structured log contract.
5. Check PII redaction.
6. Check TLS authentication.
7. Review least privilege.
8. Validate bulk item errors.
9. Test bounded retry.
10. Test protected DLQ.
11. Verify mapping compatibility.
12. Inspect shard sizes.
13. Inspect replica allocation.
14. Review disk IOPS and latency.
15. Review merge throttling.
16. Check ILM or ISM state.
17. Review retention and legal hold.
18. Test disposable snapshot restore.
19. Measure query p95.
20. Review independent SLO metrics.
21. Simulate ingestion outage.
22. Simulate search degradation.
23. Run offline acceptance.
24. Record rollback and assessment.

## 8. Twenty-four production failures

1. **Collector loses file access:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
2. **Offsets reset:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
3. **Malformed JSON:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
4. **Multiline corruption:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
5. **PII leak:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
6. **Expired TLS certificate:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
7. **403 RBAC denial:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
8. **Bulk 429:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
9. **Bulk mapping 400:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
10. **Retry storm:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
11. **DLQ loss:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
12. **Duplicate replay:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
13. **Index template collision:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
14. **Shard size >50GB:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
15. **Too many small shards:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
16. **Disk watermark:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
17. **Merge throttling:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
18. **Search thread pool rejections:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
19. **Slow fetch phase:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
20. **Replica unassigned:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
21. **ILM stuck:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
22. **ISM stuck:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
23. **Snapshot restore fails:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.
24. **Rollback fails:** inspect collector, ingest, shards, search, lifecycle, backups and independent SLOs.

## 9. Eight operational runbooks

1. **Ingestion failure:** inspect source, collector offsets, parsing, bulk item errors and bounded retries.
2. **Sensitive log incident:** stop unsafe source, restrict access, rotate secrets and follow governance-approved deletion.
3. **Disk/merge pressure:** inspect IOPS, queue, shards, merges and disk watermarks; stage capacity remediation.
4. **Slow search:** bound filters and fetch size; inspect query/fetch latency, shard fan-out and caches.
5. **Lifecycle stuck:** inspect distribution-specific ILM/ISM state, owner approval, retention and legal holds.
6. **DLQ/replay incident:** quarantine failed events, verify schema, replay idempotently and compare counts.
7. **Restore/DR:** validate snapshots, test disposable restore, document RPO/RTO and access controls.
8. **Rollback:** restore reviewed templates/pipelines/policies, validate writes/queries and preserve evidence.

## 10. 100-point final assessment

| Domain | Points |
|---|---:|
| Architecture, ingestion and data quality | 20 |
| Search, performance and shard management | 20 |
| Security, lifecycle and backups | 20 |
| Offline gate and automated tests | 20 |
| Incident response, restore and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Mandatory production acceptance: verified access controls, real redaction tests, independent SLOs, per-item bulk inspection, lifecycle approval, snapshot restore and rollback.

## 11. Evidence worksheet

```text
UTC / owner / change ID / environment:
Elasticsearch or OpenSearch version:
Collector / pipeline / schema / DLQ:
Ingest errors / query p95 / shard sizes:
Disk / merges / replicas / lifecycle:
TLS / RBAC / redaction / data owner:
Snapshot restore / RPO / RTO:
Offline gate / 30 tests:
Game day / rollback / reviewer / score:
```

**Companion:** [Chapter 045 production logging capstone lab](labs/045-elasticsearch-opensearch-production-logging-reliability-security-troubleshooting-capstone-lab.md).

**Part 09 complete. Next:** Chapter 046 — OpenTelemetry Architecture, Signals, SDKs and Collector Fundamentals (Part 10).
