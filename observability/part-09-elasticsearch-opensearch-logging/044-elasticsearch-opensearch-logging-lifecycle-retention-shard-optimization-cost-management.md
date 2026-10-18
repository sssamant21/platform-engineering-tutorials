# Chapter 044 — Elasticsearch and OpenSearch Logging Lifecycle, Retention, Shard Optimization and Cost Management

**Part 09 — Elasticsearch and OpenSearch Logging**  
**Audience:** SRE/DBRE, search and observability platform owners.  
**Prerequisites:** Chapters 041–043, storage and shard fundamentals, Python 3.10+.

## 1. Learning objectives

Operate logging lifecycle safely, compare Elasticsearch ILM and OpenSearch ISM, forecast retention and shard growth, diagnose merge/disk bottlenecks, estimate storage costs and execute change-controlled remediation.

## 2. Lifecycle architecture

```text
Fluent Bit / applications -> ingest pipeline -> write index or data stream
                                                   |
                                  rollover by age / size / docs
                                                   |
                            hot -> warm -> cold -> delete (if approved)
                                                   |
                           snapshots / governance / legal hold / audit
```

**Elasticsearch ILM and OpenSearch ISM are not interchangeable.** Endpoint names, policy schemas, data-stream support and lifecycle actions vary by distribution and version. Validate the selected deployment before applying examples.

## 3. Shard sizing and capacity

```text
primary GB per rollover ≈ daily primary GB × rollover days
GB per primary shard ≈ primary GB per rollover ÷ primary shards
logical indexed GB ≈ primary GB × (1 + replica count)
```

Example: 20 GB primary data per day, one-day rollover, one primary and one replica = ~20 GB per primary shard and ~40 GB logical shard storage before additional overhead. Forecast real compression, translogs, segment overhead, watermarks and recovery headroom separately.

For this curriculum, review shards at **40 GB** and treat **50 GB** as an operational escalation threshold; neither is a universal hard Elasticsearch/OpenSearch limit. Too many tiny shards can also harm heap and coordination. Benchmark against actual workload and recovery targets.

## 4. Elasticsearch ILM example (version-specific)

```http
PUT _ilm/policy/logs-14d-lab
Content-Type: application/json

{
  "policy": {
    "phases": {
      "hot": {"actions": {"rollover": {"max_primary_shard_size": "40gb", "max_age": "1d"}}},
      "delete": {"min_age": "14d", "actions": {"delete": {}}}
    }
  }
}
```

**Do not apply this example to production.** It deletes indices after policy-defined lifecycle conditions; rollover requires appropriate data stream or write alias setup. Snapshot, legal hold and data owner approvals are mandatory. Verify ILM availability and version syntax.

## 5. OpenSearch ISM design

An equivalent ISM policy uses states, transitions and actions, not ILM phases. Plan a hot state with rollover and a retention state with delete only after approval. Review the index template's policy attachment, rollover alias/data stream behavior, ISM explain output and version-specific API before deployment.

## 6. Operational diagnostics

```http
GET _cat/indices/logs-*?v&bytes=gb
GET _cat/shards/logs-*?v&bytes=gb
GET _cluster/health
GET _nodes/stats/indices,fs,thread_pool
GET logs-*/_stats/docs,store,merge,segments,refresh
```

Elasticsearch lifecycle inspection: `GET logs-*/_ilm/explain`. OpenSearch: inspect the ISM plugin explain API supported by your version. Track primary shard size, merge throttling, deleted-document ratio, disk latency, watermarks and indexing rejections. **Force merge is not routine maintenance for active write indices**; it may amplify I/O and impair service.

## 7. FinOps scenarios

Compare 7-, 14- and 30-day retention using measured GB/day, replica count, compression, storage tier pricing, snapshots and data-transfer charges. Include query latency and restore RTO in tiering decisions. A cheaper storage tier is not necessarily a cheaper operational outcome.

## 8. Executable offline lifecycle policy lab

This is **synthetic review metadata**, not ILM/ISM configuration. It performs no deletion and cannot prove a real cluster has enforced retention.

### healthy.json

```json
{
  "owner": "platform-dbre",
  "environment": "staging",
  "distribution": "elasticsearch",
  "policy_name": "logs-staging-14d",
  "retention_days": 14,
  "retention_approved": true,
  "legal_hold_checked": true,
  "index_owner_approved": true,
  "rollback_reviewed": true,
  "backup_reviewed": true,
  "storage_budget_gb": 2000,
  "estimated_storage_gb": 500,
  "daily_primary_gb": 20,
  "rollover_days": 1,
  "primary_shards": 1,
  "replicas": 1,
  "shard_warning_gb": 40,
  "shard_critical_gb": 50,
  "forecast_primary_shard_gb": 20,
  "estimated_deleted_docs_percent": 12,
  "merge_pressure_reviewed": true,
  "disk_watermark_reviewed": true,
  "ilm_ism_version_reviewed": true,
  "delete_production": false
}
```

### lifecycle_gate.py

```python
"""Offline lifecycle review; no cluster calls and no index deletion."""
import json,sys
from pathlib import Path
def validate(p):
 e=[]
 if not isinstance(p,dict):return ["manifest must be object"]
 for k in ("owner","environment","policy_name"):
  if not isinstance(p.get(k),str) or not p[k]:e.append("missing "+k)
 if p.get("distribution") not in ("elasticsearch","opensearch"):e.append("unknown distribution")
 for k in ("retention_approved","legal_hold_checked","index_owner_approved","rollback_reviewed","backup_reviewed","merge_pressure_reviewed","disk_watermark_reviewed","ilm_ism_version_reviewed"):
  if p.get(k) is not True:e.append("missing review "+k)
 if p.get("delete_production") is not False:e.append("destructive production action")
 for k in ("retention_days","storage_budget_gb","estimated_storage_gb","daily_primary_gb","rollover_days","primary_shards","replicas","shard_warning_gb","shard_critical_gb","forecast_primary_shard_gb","estimated_deleted_docs_percent"):
  if type(p.get(k)) is not int or p[k]<0:e.append("invalid "+k)
 for estimate,limit in (("estimated_storage_gb","storage_budget_gb"),("forecast_primary_shard_gb","shard_critical_gb")):
  a=p.get(estimate);b=p.get(limit)
  if type(a) is int and type(b) is int and (b<=0 or a>b):e.append("budget exceeded "+estimate)
 if type(p.get("retention_days")) is int and not 1<=p["retention_days"]<=90:e.append("invalid retention")
 if type(p.get("primary_shards")) is int and p["primary_shards"]<1:e.append("no primary shards")
 if type(p.get("rollover_days")) is int and p["rollover_days"]<1:e.append("invalid rollover")
 if p.get("shard_warning_gb")!=40 or p.get("shard_critical_gb")!=50:e.append("unreviewed shard thresholds")
 if type(p.get("estimated_deleted_docs_percent")) is int and p["estimated_deleted_docs_percent"]>80:e.append("deleted docs ratio needs investigation")
 if all(type(p.get(k)) is int for k in ("daily_primary_gb","rollover_days","primary_shards","forecast_primary_shard_gb")):
  expected=p["daily_primary_gb"]*p["rollover_days"]/max(1,p["primary_shards"])
  if abs(expected-p["forecast_primary_shard_gb"])>5:e.append("forecast mismatch")
 return e
if __name__=="__main__":
 errors=validate(json.loads(Path(sys.argv[1]).read_text()))
 print(json.dumps({"status":"PASS" if not errors else "FAIL","findings":errors},indent=2))
 sys.exit(bool(errors))

```

### test_lifecycle_gate.py

```python
import copy,json,unittest
from pathlib import Path
from lifecycle_gate import validate
class LifecycleTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_invalid_object(self):self.assertTrue(validate(None))
 def test_01_owner(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_02_environment(self):
  p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
 def test_03_policy_name(self):
  p=copy.deepcopy(self.p);p["policy_name"]="";self.assertTrue(validate(p))
 def test_04_distribution(self):
  p=copy.deepcopy(self.p);p["distribution"]="unknown";self.assertTrue(validate(p))
 def test_05_retention_approved(self):
  p=copy.deepcopy(self.p);p["retention_approved"]=False;self.assertTrue(validate(p))
 def test_06_legal_hold_checked(self):
  p=copy.deepcopy(self.p);p["legal_hold_checked"]=False;self.assertTrue(validate(p))
 def test_07_index_owner_approved(self):
  p=copy.deepcopy(self.p);p["index_owner_approved"]=False;self.assertTrue(validate(p))
 def test_08_rollback_reviewed(self):
  p=copy.deepcopy(self.p);p["rollback_reviewed"]=False;self.assertTrue(validate(p))
 def test_09_backup_reviewed(self):
  p=copy.deepcopy(self.p);p["backup_reviewed"]=False;self.assertTrue(validate(p))
 def test_10_merge_pressure_reviewed(self):
  p=copy.deepcopy(self.p);p["merge_pressure_reviewed"]=False;self.assertTrue(validate(p))
 def test_11_disk_watermark_reviewed(self):
  p=copy.deepcopy(self.p);p["disk_watermark_reviewed"]=False;self.assertTrue(validate(p))
 def test_12_ilm_ism_version_reviewed(self):
  p=copy.deepcopy(self.p);p["ilm_ism_version_reviewed"]=False;self.assertTrue(validate(p))
 def test_13_delete_production(self):
  p=copy.deepcopy(self.p);p["delete_production"]=True;self.assertTrue(validate(p))
 def test_14_retention_days(self):
  p=copy.deepcopy(self.p);p["retention_days"]=0;self.assertTrue(validate(p))
 def test_15_retention_days(self):
  p=copy.deepcopy(self.p);p["retention_days"]=100;self.assertTrue(validate(p))
 def test_16_storage_budget_gb(self):
  p=copy.deepcopy(self.p);p["storage_budget_gb"]=0;self.assertTrue(validate(p))
 def test_17_estimated_storage_gb(self):
  p=copy.deepcopy(self.p);p["estimated_storage_gb"]=9000;self.assertTrue(validate(p))
 def test_18_primary_shards(self):
  p=copy.deepcopy(self.p);p["primary_shards"]=0;self.assertTrue(validate(p))
 def test_19_rollover_days(self):
  p=copy.deepcopy(self.p);p["rollover_days"]=0;self.assertTrue(validate(p))
 def test_20_forecast_primary_shard_gb(self):
  p=copy.deepcopy(self.p);p["forecast_primary_shard_gb"]=100;self.assertTrue(validate(p))
 def test_21_shard_warning_gb(self):
  p=copy.deepcopy(self.p);p["shard_warning_gb"]=10;self.assertTrue(validate(p))
 def test_22_shard_critical_gb(self):
  p=copy.deepcopy(self.p);p["shard_critical_gb"]=120;self.assertTrue(validate(p))
 def test_23_estimated_deleted_docs_percent(self):
  p=copy.deepcopy(self.p);p["estimated_deleted_docs_percent"]=90;self.assertTrue(validate(p))
 def test_24_daily_primary_gb(self):
  p=copy.deepcopy(self.p);p["daily_primary_gb"]=200;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

### Run

```bash
mkdir -p chapter044 && cd chapter044
# Save the three blocks as healthy.json, lifecycle_gate.py, test_lifecycle_gate.py
python3 lifecycle_gate.py healthy.json
python3 -m unittest -v test_lifecycle_gate.py
```

Expected PASS and **26 authored tests**.

## 9. Twenty-four practical exercises

1. Inventory log indices.
2. Identify index owners.
3. Classify hot and warm data.
4. Measure daily primary GB.
5. Calculate replica multiplier.
6. Review rollover conditions.
7. Inspect ILM policy.
8. Inspect ISM policy.
9. Verify policy attachment.
10. Check lifecycle explain output.
11. Forecast primary shard size.
12. Review 40 GB warning threshold.
13. Review 50 GB critical threshold.
14. Inspect deleted document ratios.
15. Inspect merge throttling.
16. Inspect disk queue and latency.
17. Check cluster watermarks.
18. Review snapshot coverage.
19. Review legal holds.
20. Estimate storage budget.
21. Model retention scenarios.
22. Test staging rollover.
23. Run offline policy tests.
24. Document rollback.

## 10. Twenty-four production failure scenarios

1. **Rollover alias missing:** inspect policy state, shard metrics, data owner approval, storage and rollback.
2. **ILM step stuck:** inspect policy state, shard metrics, data owner approval, storage and rollback.
3. **ISM transition stuck:** inspect policy state, shard metrics, data owner approval, storage and rollback.
4. **Template policy mismatch:** inspect policy state, shard metrics, data owner approval, storage and rollback.
5. **Unexpected index deletion:** inspect policy state, shard metrics, data owner approval, storage and rollback.
6. **Retention not enforced:** inspect policy state, shard metrics, data owner approval, storage and rollback.
7. **Legal hold overlooked:** inspect policy state, shard metrics, data owner approval, storage and rollback.
8. **Snapshot unavailable:** inspect policy state, shard metrics, data owner approval, storage and rollback.
9. **Shards above 50 GB:** inspect policy state, shard metrics, data owner approval, storage and rollback.
10. **Thousands of tiny shards:** inspect policy state, shard metrics, data owner approval, storage and rollback.
11. **Deleted documents accumulate:** inspect policy state, shard metrics, data owner approval, storage and rollback.
12. **Force merge saturates I/O:** inspect policy state, shard metrics, data owner approval, storage and rollback.
13. **Merge throttling high:** inspect policy state, shard metrics, data owner approval, storage and rollback.
14. **Disk watermark exceeded:** inspect policy state, shard metrics, data owner approval, storage and rollback.
15. **Shard allocation blocked:** inspect policy state, shard metrics, data owner approval, storage and rollback.
16. **Replica unassigned:** inspect policy state, shard metrics, data owner approval, storage and rollback.
17. **Indexing thread pool rejected:** inspect policy state, shard metrics, data owner approval, storage and rollback.
18. **Search fetch slow:** inspect policy state, shard metrics, data owner approval, storage and rollback.
19. **Heap pressure:** inspect policy state, shard metrics, data owner approval, storage and rollback.
20. **Query cache evictions:** inspect policy state, shard metrics, data owner approval, storage and rollback.
21. **Object storage cost spike:** inspect policy state, shard metrics, data owner approval, storage and rollback.
22. **Retention forecast wrong:** inspect policy state, shard metrics, data owner approval, storage and rollback.
23. **Index owner approval absent:** inspect policy state, shard metrics, data owner approval, storage and rollback.
24. **Rollback fails:** inspect policy state, shard metrics, data owner approval, storage and rollback.

## 11. Eight production runbooks

1. **Lifecycle stuck:** inspect ILM explain or ISM explain, policy attachment, write alias, step errors and cluster health.
2. **Disk pressure:** inspect disk latency, watermarks, shard placement, primary growth and replica overhead before approving changes.
3. **Oversized shards:** estimate reindex/rollover, staged template updates, I/O cost and rollback; avoid splitting without workload review.
4. **Too many shards:** consolidate future rollover, template counts and retention while preserving search correctness.
5. **Merge pressure:** measure throttling, deleted documents, CPU and I/O; avoid aggressive force merge on hot write indices.
6. **Retention incident:** stop destructive operations, preserve evidence, verify legal hold and owner approval, restore from snapshots if required.
7. **FinOps surge:** analyze primary bytes, replicas, ingest growth, tiers, retention and query impact.
8. **Rollback:** restore versioned lifecycle policies/templates, validate index transitions and confirm data safety.

## 12. Production DBRE incident simulation

A 1.2 TB log index has five primaries with shard sizes above 100 GB. Merge throttling rises, fetch latency exceeds query latency and disk watermarks approach critical. Identify owner and retention constraints, estimate safe rollover/reindex target shard counts, monitor storage I/O and query baselines, and stage a remediation. Do not force merge or delete logs without approved impact analysis and rollback.

## 13. 100-point assessment

| Domain | Points |
|---|---:|
| ILM/ISM lifecycle architecture | 20 |
| Shard sizing and capacity planning | 20 |
| Retention, compliance and FinOps | 20 |
| Offline governance and tests | 20 |
| Incident troubleshooting and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Live acceptance requires a version-pinned test cluster, verified rollover/retention, shard metrics, owner approvals and recovery evidence.

**Companion:** [Chapter 044 lifecycle and FinOps lab](labs/044-elasticsearch-opensearch-logging-lifecycle-retention-shard-optimization-cost-management-lab.md).

**Next:** Chapter 045 — Elasticsearch and OpenSearch Production Logging Reliability, Security and Troubleshooting Capstone.
