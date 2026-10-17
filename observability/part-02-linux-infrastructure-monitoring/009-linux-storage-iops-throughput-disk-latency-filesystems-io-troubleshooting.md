# Chapter 009 — Linux Storage IOPS, Throughput, Disk Latency, Filesystems and I/O Troubleshooting

**Part 02 — Linux and Infrastructure Monitoring**  
**Audience:** SRE/DBRE, Linux, Kubernetes and cloud platform engineers. **Prerequisites:** Chapters 001–008; Linux shell; Python 3.10+.

## Learning objectives

Diagnose filesystem capacity, inode exhaustion, device IOPS, throughput, queueing, latency, I/O PSI, filesystem errors and cloud block-storage throttling. Separate storage symptoms from database/query design and measure customer impact before remediation.

## 1. Linux storage architecture

```text
Application / PostgreSQL / Elasticsearch / MongoDB
           |
  buffered / direct I/O and page cache
           |
    VFS / filesystem (ext4, XFS)
           |
  block layer / scheduler / multipath
           |
    device driver / NVMe / virtual disk
           |
  EBS / Azure Managed Disk / GCP Persistent Disk
           |
  IOPS / throughput / latency / burst credits / provider limits
```

A filesystem can be healthy in capacity but saturated by I/O. A device can have ample provisioned IOPS yet hit throughput limits. An application may be slow due to locks, queries, CPU or networking even when disk metrics are healthy.

## 2. Key storage metrics

| Metric | Interpretation | Caveat |
|---|---|---|
| IOPS | completed read/write operations per second | operation size varies |
| Throughput | MiB/s read/write | distinguish MiB from MB |
| `r_await`/`w_await` | average read/write I/O completion time including queueing | average hides tails |
| `aqu-sz` | average device queue size | depends on sampling and parallelism |
| `%util` | fraction of time with I/O in progress | not universal SSD/NVMe saturation metric |
| `svctm` | obsolete legacy statistic | do not use for diagnosis |
| `df -h` | filesystem free space | excludes inode issues |
| `df -i` | inode availability | small-file workloads |
| `/proc/pressure/io` | task I/O stall pressure | workload context required |

Rates must be calculated from cumulative counters over an interval. `iostat` first report can be since boot; sample multiple intervals. Compare **device-level** metrics with cloud provisioned and instance-level limits, filesystem layout, RAID/multipath and database behavior.

## 3. Safe evidence collection

```bash
date -u
uname -r
lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,ROTA
findmnt -T /
df -hT
df -i
cat /proc/pressure/io 2>/dev/null || true
cat /proc/diskstats | head -n 20
command -v iostat >/dev/null && iostat -xz 1 5 || true
command -v pidstat >/dev/null && pidstat -d 1 5 || true
command -v vmstat >/dev/null && vmstat 1 5 || true
journalctl -k --since '-30 min' 2>/dev/null | grep -iE 'I/O error|nvme|ext4|xfs|reset' | tail -n 30 || true
```

These commands are read-only. Device and filesystem visibility can be restricted in containers; check host/cloud dashboards as needed. Kernel logs may include sensitive identifiers.

## 4. Filesystems and capacity

- **ext4/XFS:** verify mount options, error state, metadata and inode capacity; never assume identical behavior across filesystems.
- **Inode exhaustion:** `df -i` may reach 100% with free bytes remaining.
- **Deleted-open files:** space can remain consumed while processes hold descriptors; investigate with approved `lsof +L1` if installed.
- **Database durability:** WAL/journal and fsync semantics matter; never recommend unsafe mount or write-cache changes for speed.
- **Volume expansion:** requires approved storage, partition/filesystem steps, snapshot/backup and rollback plan.

## 5. Database and cloud scenarios

**Elasticsearch/OpenSearch:** shard merges, indexing bursts, translog/fsync, search and disk watermarks can drive I/O; correlate per-node disk latency with merge time and rejected requests.

**PostgreSQL:** checkpoints, WAL flush, autovacuum, temp files, sequential scans and replication can create distinct I/O patterns. Review `pg_stat_io` where supported and appropriate.

**MongoDB:** WiredTiger checkpoints, cache eviction and journal activity can raise read/write latency; correlate with storage utilization and workload.

**Redis:** persistence RDB/AOF can produce write bursts even for an in-memory workload.

**Cloud:** EBS, Azure and GCP disks have provisioned IOPS/throughput ceilings; instance/VM bandwidth and burst behavior may be additional limits. Validate current SKU limits in provider documentation.

## 6. Prometheus queries

Common node_exporter metrics (confirm exporter/version):

```promql
sum by (instance, device) (rate(node_disk_reads_completed_total[5m]) + rate(node_disk_writes_completed_total[5m]))
```

```promql
sum by (instance, device) (rate(node_disk_read_bytes_total[5m]) + rate(node_disk_written_bytes_total[5m]))
```

```promql
rate(node_disk_read_time_seconds_total[5m]) / clamp_min(rate(node_disk_reads_completed_total[5m]), 0.001)
```

```promql
100 * (1 - node_filesystem_avail_bytes / node_filesystem_size_bytes)
```

Exclude loop, ephemeral and irrelevant devices according to your environment. The read-time expression is an average per completed read and must not be interpreted as a latency percentile. Alert on sustained user-impacting latency, capacity growth and error signals, not raw `%util` alone.

## 7. Executable synthetic storage gate

Create:

```text
chapter009/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/storage_gate.py
  tests/test_storage_gate.py
```

### fixtures/healthy.json

```json
{
  "host": "staging-db-01",
  "owner": "dbre",
  "filesystem_used_pct": 61,
  "inode_used_pct": 30,
  "read_iops": 600,
  "write_iops": 300,
  "iops_limit": 5000,
  "read_mib_s": 28,
  "write_mib_s": 12,
  "throughput_limit_mib_s": 250,
  "read_await_ms": 3,
  "write_await_ms": 5,
  "latency_budget_ms": 20,
  "io_psi_some_pct": 1,
  "io_errors_delta": 0,
  "service_p95_ms": 140,
  "service_budget_ms": 300
}
```

### fixtures/degraded.json

```json
{
  "host": "staging-db-01",
  "owner": "dbre",
  "filesystem_used_pct": 96,
  "inode_used_pct": 94,
  "read_iops": 4000,
  "write_iops": 3000,
  "iops_limit": 5000,
  "read_mib_s": 160,
  "write_mib_s": 120,
  "throughput_limit_mib_s": 250,
  "read_await_ms": 65,
  "write_await_ms": 92,
  "latency_budget_ms": 20,
  "io_psi_some_pct": 38,
  "io_errors_delta": 3,
  "service_p95_ms": 2400,
  "service_budget_ms": 300
}
```

### scripts/storage_gate.py

```python
#!/usr/bin/env python3
"""Read-only synthetic storage risk gate. No production mutations."""
import json
import sys
from pathlib import Path

PCTS = ("filesystem_used_pct", "inode_used_pct", "io_psi_some_pct")
RATES = ("read_iops", "write_iops", "read_mib_s", "write_mib_s",
         "read_await_ms", "write_await_ms", "service_p95_ms")
LIMITS = ("iops_limit", "throughput_limit_mib_s", "latency_budget_ms", "service_budget_ms")

def assess(d):
    findings = []
    for key in ("host", "owner"):
        if not isinstance(d.get(key), str) or not d[key].strip():
            findings.append(f"missing {key}")
    for key in PCTS:
        val = d.get(key)
        if type(val) not in (int, float) or not 0 <= val <= 100:
            findings.append(f"invalid {key}")
    for key in RATES + LIMITS:
        val = d.get(key)
        if type(val) not in (int, float) or val < 0 or (key in LIMITS and val == 0):
            findings.append(f"invalid {key}")
    if type(d.get("io_errors_delta")) is not int or d["io_errors_delta"] < 0:
        findings.append("invalid io_errors_delta")
    if findings:
        return findings
    if d["filesystem_used_pct"] >= 90:
        findings.append("filesystem capacity critical")
    if d["inode_used_pct"] >= 90:
        findings.append("inode capacity critical")
    if d["read_iops"] + d["write_iops"] > d["iops_limit"]:
        findings.append("IOPS provisioned limit exceeded")
    if d["read_mib_s"] + d["write_mib_s"] > d["throughput_limit_mib_s"]:
        findings.append("throughput provisioned limit exceeded")
    if max(d["read_await_ms"], d["write_await_ms"]) > d["latency_budget_ms"]:
        findings.append("disk latency budget exceeded")
    if d["io_psi_some_pct"] >= 20:
        findings.append("I/O stall pressure")
    if d["io_errors_delta"] > 0:
        findings.append("device I/O errors")
    if d["service_p95_ms"] > d["service_budget_ms"]:
        findings.append("service latency budget exceeded")
    return findings

if __name__ == "__main__":
    problems = assess(json.loads(Path(sys.argv[1]).read_text()))
    print("STORAGE GATE PASS (synthetic)" if not problems else "STORAGE GATE FAIL")
    for problem in problems:
        print("-", problem)
    sys.exit(bool(problems))
```

### tests/test_storage_gate.py

```python
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from storage_gate import assess

class StorageTests(unittest.TestCase):
    def fixture(self, name="healthy.json"):
        return json.loads((ROOT / "fixtures" / name).read_text())

    def change(self, key, value):
        d = self.fixture()
        d[key] = value
        return assess(d)

    def test_healthy(self): self.assertEqual(assess(self.fixture()), [])
    def test_degraded(self): self.assertTrue(assess(self.fixture("degraded.json")))
    def test_filesystem(self): self.assertTrue(self.change("filesystem_used_pct", 97))
    def test_inode(self): self.assertTrue(self.change("inode_used_pct", 95))
    def test_iops(self): self.assertTrue(self.change("read_iops", 6000))
    def test_throughput(self): self.assertTrue(self.change("write_mib_s", 300))
    def test_latency(self): self.assertTrue(self.change("read_await_ms", 70))
    def test_psi(self): self.assertTrue(self.change("io_psi_some_pct", 40))
    def test_errors(self): self.assertTrue(self.change("io_errors_delta", 2))
    def test_service(self): self.assertTrue(self.change("service_p95_ms", 1000))
    def test_invalid_limit(self): self.assertTrue(self.change("iops_limit", 0))
    def test_missing_owner(self): self.assertTrue(self.change("owner", ""))

if __name__ == "__main__":
    unittest.main()
```

Execute:

```bash
python3 scripts/storage_gate.py fixtures/healthy.json
if python3 scripts/storage_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded storage accepted"; exit 1
else
  echo "PASS: degraded storage rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy exits 0, degraded exits nonzero, 12 unit tests pass. Synthetic thresholds illustrate failure classification, not universal storage SLOs.

## 8. Twenty-four hands-on exercises

1. Map application to filesystem and block device.
2. Identify cloud volume and instance limits.
3. Capture `lsblk` and `findmnt`.
4. Capture filesystem byte capacity.
5. Capture inode utilization.
6. Inspect mount type and options.
7. Capture diskstats.
8. Capture read IOPS.
9. Capture write IOPS.
10. Capture read throughput.
11. Capture write throughput.
12. Capture `r_await` and `w_await`.
13. Explain queue depth and parallelism.
14. Interpret `%util` on NVMe.
15. Capture I/O PSI.
16. Inspect per-process I/O.
17. Correlate Elasticsearch merges.
18. Correlate PostgreSQL WAL/checkpoints.
19. Define filesystem alert.
20. Define latency and errors alert.
21. Create healthy fixture.
22. Create degraded fixture.
23. Run positive/negative gates and 12 tests.
24. Document RCA/COA and capacity decision.

## 9. Twenty production failure scenarios

| # | Failure | Investigation |
|---|---|---|
| 01 | filesystem full | df |
| 02 | inode exhaustion | df -i |
| 03 | deleted-open file | lsof |
| 04 | IOPS limit reached | provisioned IOPS |
| 05 | throughput limit reached | MiB/s ceiling |
| 06 | instance EBS cap | instance limits |
| 07 | burst credit exhaustion | provider metrics |
| 08 | disk await spike | queue/latency |
| 09 | high I/O PSI | blocked tasks |
| 10 | NVMe %util misread | parallelism |
| 11 | Elasticsearch merge storm | merge/shard |
| 12 | PostgreSQL checkpoint burst | WAL/checkpoint |
| 13 | MongoDB cache eviction | WiredTiger |
| 14 | Redis AOF write burst | persistence |
| 15 | Kubernetes volume saturation | PV/CSI |
| 16 | filesystem error | kernel logs |
| 17 | device reset | dmesg/provider |
| 18 | wrong device labels | exporter |
| 19 | latency without disk pressure | app/locks/network |
| 20 | unsafe cleanup proposal | owner review |

## 10. Eight production runbooks

**A. Disk latency:** Confirm user impact, sample device await, queue, IOPS, throughput and cloud caps; correlate application operations.

**B. IOPS saturation:** Inspect workload operation sizes, provisioned ceilings, instance limits and rate trends; plan controlled changes.

**C. Throughput saturation:** Compare MiB/s, I/O sizes, instance bandwidth and storage class; distinguish from IOPS.

**D. Filesystem full:** Identify mount, growth source, reserved capacity and retention; require data-owner approval before deletion.

**E. Inode exhaustion:** Locate small-file growth without indiscriminate deletion; plan retention/cleanup approval.

**F. Database I/O storm:** Correlate Elasticsearch merges, PostgreSQL checkpoints or MongoDB cache/eviction with service SLOs.

**G. Storage error:** Preserve kernel/device evidence, verify redundancy and backups, escalate to storage provider.

**H. Storage production readiness:** Baseline under realistic load, confirm limits, alerts, snapshots, rollback and capacity headroom.

## 11. 100-point acceptance

| Area | Points |
|---|---:|
| Linux storage architecture and filesystems | 20 |
| IOPS, throughput, latency and PSI interpretation | 20 |
| DBRE/cloud failure diagnosis | 20 |
| Synthetic lab and 12 tests | 20 |
| Runbooks, safe operations and evidence | 20 |
| **Total** | **100** |

Recommended pass 85/100; mandatory gates include safe read-only evidence, separation of IOPS/throughput, filesystem/inode checks, negative fixture rejection and 12 tests.

## 12. Evidence worksheet

```text
UTC / host / device / mount / owner:
Filesystem bytes/inodes:
IOPS / MiB/s / queue / await:
IO PSI / errors:
Cloud volume and instance limits:
Database workload / customer SLO:
Healthy/degraded fixtures:
Twelve unit tests:
RCA / COA / reviewer:
```

**Companion:** [Chapter 009 executable lab](labs/009-linux-storage-iops-throughput-disk-latency-filesystems-io-troubleshooting-lab.md).

**Next:** Chapter 010 — Linux Infrastructure Observability and Production Troubleshooting Capstone.
