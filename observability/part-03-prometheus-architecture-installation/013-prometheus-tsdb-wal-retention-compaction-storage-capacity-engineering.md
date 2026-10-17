# Chapter 013 — Prometheus TSDB, WAL, Retention, Compaction and Storage Capacity Engineering

**Part 03 — Prometheus Architecture and Installation**  
**Audience:** SRE/DBRE and platform operators. **Prerequisites:** Chapters 011–012, Prometheus basics, Python 3.10+.  
**Learning outcomes:** Explain the storage lifecycle, quantify ingestion/retention requirements, diagnose WAL and compaction failures, distinguish recoverability from HA, and demonstrate an executable capacity acceptance gate.

## 1. Storage architecture

```text
Service discovery -> scrape -> sample validation -> head block (memory)
                                              |          |
                                              |         WAL
                                              |          |
                                              +--> persisted TSDB blocks
                                                     |
                                               compaction/retention
                                                     |
                                             local persistent volume
PromQL query engine ---------------------------------+
remote_write queue -> optional external long-term storage
```

Prometheus stores recent samples in its mutable head and WAL for crash recovery, then writes immutable TSDB blocks with index, chunks and metadata. Compaction merges blocks and improves storage layout. Retention deletes old local blocks by configured time/size limits; deletion is not a substitute for backups or disaster recovery.

## 2. WAL, head and crash recovery

The WAL records recent ingest activity so the head can be reconstructed after an unclean restart. WAL replay duration depends on ingestion, head size, storage I/O and checkpoint state. A WAL is **not** a complete backup of the TSDB. Do not manually remove WAL or block directories to resolve an incident without a validated recovery procedure and approved risk assessment.

Key operational risks: storage full, slow WAL fsync, abrupt power loss, insufficient persistent volume performance, high cardinality, slow replay and data gaps after corruption. Always record version, mount, filesystem, retention settings, last known healthy scrape and affected time range.

## 3. TSDB compaction and retention

A TSDB block contains samples, an index and metadata. Blocks are compacted over time; excessive block churn or delayed compaction can affect CPU, memory, I/O and startup behavior. Monitor `prometheus_tsdb_compactions_failed_total`, `prometheus_tsdb_head_series`, `prometheus_tsdb_head_chunks`, WAL metrics and filesystem capacity, verifying exact names against the deployed Prometheus version.

Retention flags for a standalone deployment:

```bash
--storage.tsdb.path=/prometheus
--storage.tsdb.retention.time=15d
--storage.tsdb.retention.size=180GB
```

Time and size retention are independent constraints; whichever applies can result in block removal. Size retention is approximate and should leave room for WAL, head, compaction work and other filesystem usage. Prometheus cannot promise exact retention under disk pressure.

## 4. Capacity engineering

A first-pass **planning estimate**, not a storage guarantee:

```text
retained GiB =
  samples_per_second × 86,400 × retention_days
  × observed_bytes_per_sample × overhead_factor / 1024³
```

Example: 10,000 samples/sec, 15 days, 2 bytes/sample and 1.5 overhead factor gives approximately **36.21 GiB**. Real block compression, churn, label cardinality, WAL, index, metadata, queries, compaction temporary space and filesystem behavior vary. Calibrate against observed disk growth. The lab uses a configurable overhead factor rather than pretending bytes/sample is universal.

**Headroom policy:** define distinct warning and critical limits for disk, inode usage, WAL replay recovery budget, compaction backlog and query memory. Confirm limits at host, PVC, cloud volume and container level. Size for peak ingestion and realistic query concurrency, not only steady-state average.

## 5. Read-only inspection and operational metrics

```bash
date -u
df -hT /prometheus 2>/dev/null || true
df -i /prometheus 2>/dev/null || true
du -sh /prometheus 2>/dev/null || true
curl -fsS 'http://127.0.0.1:9090/api/v1/status/tsdb' || true
curl -fsS 'http://127.0.0.1:9090/api/v1/status/runtimeinfo' || true
curl -fsS 'http://127.0.0.1:9090/api/v1/query?query=prometheus_tsdb_head_series' || true
```

Restrict API access to an authorized environment; the status APIs may expose operational metadata. `du` can be expensive on large trees; use approved maintenance windows for heavy filesystem scans.

### PromQL diagnostic examples

```promql
prometheus_tsdb_head_series
```

```promql
rate(prometheus_tsdb_head_samples_appended_total[5m])
```

```promql
increase(prometheus_tsdb_compactions_failed_total[1h])
```

```promql
rate(prometheus_tsdb_wal_fsync_duration_seconds_count[5m])
```

```promql
100 * (1 - node_filesystem_avail_bytes{mountpoint="/prometheus"} / node_filesystem_size_bytes{mountpoint="/prometheus"})
```

Validate metric availability and filesystem mount labels in your environment. For WAL fsync latency, use histogram sum/count rates when exported, rather than count rate alone. For cardinality, inspect TSDB status and per-job sample ingestion as well as head series.

## 6. Complete offline executable capacity lab

Create:

```text
chapter013/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/capacity.py
  tests/test_capacity.py
```

### fixtures/healthy.json

```json
{
  "cluster": "prom-staging",
  "owner": "platform-sre",
  "active_series": 200000,
  "samples_per_second": 10000,
  "retention_days": 15,
  "bytes_per_sample": 2,
  "head_wal_overhead_factor": 1.5,
  "disk_capacity_gib": 200,
  "current_disk_used_gib": 45,
  "query_peak_memory_gib": 2,
  "memory_limit_gib": 16,
  "compaction_backlog_blocks": 0,
  "wal_replay_seconds": 35,
  "recovery_budget_seconds": 180
}
```

### fixtures/degraded.json

```json
{
  "cluster": "prom-staging",
  "owner": "platform-sre",
  "active_series": 3500000,
  "samples_per_second": 90000,
  "retention_days": 30,
  "bytes_per_sample": 2.5,
  "head_wal_overhead_factor": 1.8,
  "disk_capacity_gib": 200,
  "current_disk_used_gib": 190,
  "query_peak_memory_gib": 14,
  "memory_limit_gib": 16,
  "compaction_backlog_blocks": 8,
  "wal_replay_seconds": 900,
  "recovery_budget_seconds": 180
}
```

### scripts/capacity.py

```python
#!/usr/bin/env python3
"""Synthetic Prometheus TSDB sizing and risk gate; Python standard library."""
import json
import math
import sys
from pathlib import Path

FIELDS = ("active_series", "samples_per_second", "retention_days", "bytes_per_sample",
          "head_wal_overhead_factor", "disk_capacity_gib", "current_disk_used_gib",
          "query_peak_memory_gib", "memory_limit_gib", "compaction_backlog_blocks",
          "wal_replay_seconds", "recovery_budget_seconds")

def assess(data):
    issues = []
    for key in ("cluster", "owner"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            issues.append(f"missing {key}")
    for key in FIELDS:
        v = data.get(key)
        if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
            issues.append(f"invalid {key}")
    for key in ("active_series", "compaction_backlog_blocks"):
        if key in data and (type(data[key]) is not int or data[key] < 0):
            issues.append(f"invalid integer {key}")
    if issues:
        return {"findings": sorted(set(issues)), "estimated_retained_gib": None}
    for key in ("retention_days", "bytes_per_sample", "head_wal_overhead_factor",
                "disk_capacity_gib", "memory_limit_gib", "recovery_budget_seconds"):
        if data[key] <= 0:
            issues.append(f"invalid positive {key}")
    if issues:
        return {"findings": issues, "estimated_retained_gib": None}
    estimated = (data["samples_per_second"] * 86400 * data["retention_days"] *
                 data["bytes_per_sample"] * data["head_wal_overhead_factor"] / (1024**3))
    if estimated > 0.8 * data["disk_capacity_gib"]:
        issues.append("estimated retention exceeds 80% disk budget")
    if data["current_disk_used_gib"] > 0.85 * data["disk_capacity_gib"]:
        issues.append("current TSDB disk pressure")
    if data["query_peak_memory_gib"] > 0.8 * data["memory_limit_gib"]:
        issues.append("query memory headroom low")
    if data["compaction_backlog_blocks"] > 3:
        issues.append("compaction backlog")
    if data["wal_replay_seconds"] > data["recovery_budget_seconds"]:
        issues.append("WAL replay exceeds recovery budget")
    if data["active_series"] > 2_000_000:
        issues.append("high series count requires cardinality review")
    return {"findings": issues, "estimated_retained_gib": round(estimated, 3)}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 capacity.py fixtures/healthy.json")
    try:
        result = assess(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError, ValueError) as exc:
        sys.exit(f"input error: {exc}")
    print(json.dumps(result, indent=2))
    sys.exit(bool(result["findings"]))
```

### tests/test_capacity.py

```python
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from capacity import assess

class CapacityTests(unittest.TestCase):
    def fixture(self, name="healthy.json"):
        return json.loads((ROOT / "fixtures" / name).read_text())
    def changed(self, **changes):
        d = self.fixture()
        d.update(changes)
        return assess(d)["findings"]
    def test_healthy(self): self.assertEqual(assess(self.fixture())["findings"], [])
    def test_degraded(self): self.assertTrue(assess(self.fixture("degraded.json"))["findings"])
    def test_retention(self): self.assertTrue(self.changed(retention_days=300))
    def test_disk_pressure(self): self.assertTrue(self.changed(current_disk_used_gib=190))
    def test_memory(self): self.assertTrue(self.changed(query_peak_memory_gib=15))
    def test_compaction(self): self.assertTrue(self.changed(compaction_backlog_blocks=9))
    def test_wal_recovery(self): self.assertTrue(self.changed(wal_replay_seconds=500))
    def test_cardinality(self): self.assertTrue(self.changed(active_series=3000000))
    def test_zero_disk(self): self.assertTrue(self.changed(disk_capacity_gib=0))
    def test_missing_owner(self): self.assertTrue(self.changed(owner=""))
    def test_negative_samples(self): self.assertTrue(self.changed(samples_per_second=-1))
    def test_nan(self): self.assertTrue(self.changed(bytes_per_sample=float("nan")))
    def test_bad_integer(self): self.assertTrue(self.changed(active_series=2.5))
    def test_estimate(self): self.assertGreater(assess(self.fixture())["estimated_retained_gib"], 0)

if __name__ == "__main__":
    unittest.main()
```

### Execute and verify

```bash
cd chapter013
python3 scripts/capacity.py fixtures/healthy.json
if python3 scripts/capacity.py fixtures/degraded.json; then
  echo "FAIL: degraded storage accepted"
  exit 1
else
  echo "PASS: degraded storage rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy gate passes with estimated retained storage ~36.21 GiB; degraded gate fails with ~977.665 GiB estimated and multiple risk findings; 14 tests pass. These tests execute offline and do not prove a production Prometheus deployment.

## 7. Twenty-four hands-on exercises

1. Diagram head/WAL/block lifecycle.
2. Explain WAL recovery versus backup.
3. Inventory TSDB flags and version.
4. Inspect TSDB API safely.
5. Capture head series.
6. Capture sample append rate.
7. Inspect scrape samples.
8. Inspect disk and inode usage.
9. Calculate samples per day.
10. Estimate compressed retention.
11. Apply observed overhead factor.
12. Model 2x ingestion peak.
13. Model 30-day retention.
14. Calculate storage headroom.
15. Inspect compaction failures.
16. Define WAL replay RTO.
17. Explain remote-write isolation.
18. Define HA replica labeling.
19. Define cardinality governance.
20. Create healthy fixture.
21. Create degraded fixture.
22. Execute positive and negative gates.
23. Execute 14 unit tests.
24. Present capacity, recovery and rollback review.

## 8. Twenty production failure scenarios

| # | Failure | Investigation |
|---|---|---|
| 01 | WAL replay exceeds RTO | WAL size, I/O |
| 02 | TSDB filesystem full | retention/capacity |
| 03 | PVC reaches inode limit | inode counts |
| 04 | High head series | label churn |
| 05 | Sudden ingestion spike | scrape samples |
| 06 | Compaction backlog | CPU/I/O |
| 07 | Compaction failure | logs/metrics |
| 08 | WAL fsync latency | device await |
| 09 | Retention too short | settings |
| 10 | Retention too long | disk model |
| 11 | Unbounded request ID labels | instrumentation |
| 12 | Counter churn from ephemeral targets | lifecycle |
| 13 | Query OOM | query concurrency |
| 14 | Remote-write queue growth | backend/network |
| 15 | Remote backend outage | local retention |
| 16 | Corrupted block | integrity/recovery |
| 17 | Unsafe WAL deletion proposed | change control |
| 18 | Duplicate HA samples | replica labels |
| 19 | Backup not restorable | restore drill |
| 20 | Missing TSDB metrics | exporter/version |

## 9. Eight production runbooks

**A. Disk capacity pressure:** Confirm mount and retention, measure ingestion growth and free space, review alert/backup coverage; stage capacity expansion or retention change.

**B. WAL replay delay:** Preserve logs and version, inspect storage I/O, replay progress, recovery objective and safe rollback.

**C. Compaction failure:** Correlate compaction metrics, filesystem capacity, permissions, CPU/memory and TSDB logs; do not delete blocks blindly.

**D. High cardinality:** Identify high-churn labels and affected exporters, fix instrumentation, estimate TSDB cost and review privacy.

**E. Query memory exhaustion:** Inspect query concurrency and range, recording rules, cardinality and memory limits; test optimized queries.

**F. Remote-write backlog:** Inspect queue retries, destination health, network and local retention; document potential loss window.

**G. Restore and disaster recovery:** Define snapshot/backup consistency, restore in isolation, validate query results and RPO/RTO.

**H. Production readiness:** Validate retention, disk headroom, HA replicas, alert routing, RBAC, encryption, upgrade and rollback plans.

## 10. 100-point assessment

| Domain | Points |
|---|---:|
| TSDB, WAL, compaction and retention theory | 20 |
| Capacity estimation and headroom | 20 |
| Observability and failure diagnosis | 20 |
| Executable lab and 14 tests | 20 |
| Runbooks, recovery and evidence | 20 |
| **Total** | **100** |

Suggested pass: 85/100. Mandatory gates: correct WAL-versus-backup distinction, explicit disk headroom, degraded fixture rejection, all 14 tests and reviewed recovery plan.

## 11. Evidence worksheet

```text
UTC / operator / cluster / version:
Head series / samples per second:
Retention time / size:
Observed bytes per sample:
WAL replay duration / RTO:
Compaction health / disk / inode:
Estimated retained GiB / capacity headroom:
Positive/negative gate and 14 tests:
RCA / COA / reviewer:
```

**Companion:** [Chapter 013 executable capacity lab](labs/013-prometheus-tsdb-wal-retention-compaction-storage-capacity-engineering-lab.md).

**Next:** Chapter 014 — Prometheus High Availability, Federation, Remote Write and Long-Term Storage.
