# Chapter 008 — Linux Memory Management, Page Cache, Swap, PSI and OOM Troubleshooting

**Part 02 — Linux and Infrastructure Monitoring**  
**Audience:** SRE/DBRE, Linux and Kubernetes operators. **Prerequisites:** Chapters 001–007, Python 3.10+, Linux shell.

## Learning objectives

Interpret Linux memory accounting, distinguish healthy page cache from reclaim distress, diagnose swap thrashing and OOM kills, inspect cgroup v2 controls, correlate memory PSI with application latency, and implement repeatable evidence-driven troubleshooting.

## 1. Architecture

```text
Database / app processes / page cache / kernel slabs
                 |
       virtual memory and page tables
                 |
       reclaim (kswapd / direct reclaim)
           /                  \
       free pages         swap / file-backed I/O
           \                  /
        memory PSI / major faults
                 |
       cgroup memory.high / memory.max
                 |
      workload latency / OOM / eviction
```

Linux uses spare RAM for cache. **High cache usage alone is not memory pressure.** Interpret `MemAvailable`, active reclaim, page faults, swap-in/out, PSI, cgroup events, OOM and customer latency together.

## 2. Linux memory accounting

| Metric/source | Meaning | Pitfall |
|---|---|---|
| `MemTotal`, `MemFree` | total and completely free RAM | low free can be healthy |
| `MemAvailable` | kernel estimate of allocatable RAM without heavy swapping | estimate, not guarantee |
| `Cached`, `Buffers` | file-backed cache and buffers | cache is reclaimable only under constraints |
| `Slab`, `SReclaimable` | kernel object caches | reclaimability varies |
| `AnonPages`, RSS | anonymous/process resident memory | shared mappings complicate totals |
| `Committed_AS` | committed virtual memory | not physical RAM use |
| `pgmajfault` | faults requiring I/O (typically) | use counter deltas and context |
| `pswpin`, `pswpout` | swapped pages | rates matter more than swap allocated |
| `oom_kill` / `memory.events` | kill and cgroup memory events | scope matters |

`free -h` displays used, free, buff/cache and available. Distinguish application heap, RSS, page cache, mapped files, kernel slab and cgroup-charged cache. For PostgreSQL, MongoDB and Elasticsearch, consider application-managed caches and filesystem cache separately.

## 3. Memory pressure and PSI

Linux `/proc/pressure/memory` provides `some` (at least one task stalled) and `full` (all non-idle tasks stalled) aggregates over rolling windows and cumulative totals. `avg10`, `avg60` and `avg300` are percentages. PSI availability depends on kernel configuration and permissions.

```bash
cat /proc/pressure/memory
grep -E '^(MemTotal|MemFree|MemAvailable|Cached|Buffers|SwapTotal|SwapFree|AnonPages|Slab|SReclaimable):' /proc/meminfo
vmstat 1 5
grep -E '^(pgmajfault|pswpin|pswpout|pgscan|pgsteal|oom_kill) ' /proc/vmstat
```

Collect at least two samples; absolute cumulative values are not rates. `vmstat` swap columns `si` and `so` show swap activity; nonzero allocated swap does not necessarily imply ongoing thrashing.

## 4. cgroup v2 and Kubernetes memory

```bash
cat /sys/fs/cgroup/memory.current 2>/dev/null || true
cat /sys/fs/cgroup/memory.max 2>/dev/null || true
cat /sys/fs/cgroup/memory.high 2>/dev/null || true
cat /sys/fs/cgroup/memory.events 2>/dev/null || true
cat /sys/fs/cgroup/memory.stat 2>/dev/null || true
cat /sys/fs/cgroup/memory.pressure 2>/dev/null || true
```

- `memory.current`: charged memory for the current cgroup.
- `memory.high`: throttling/reclaim boundary; exceeding it does not directly invoke the OOM killer.
- `memory.max`: hard limit; can lead to cgroup OOM if reclaim cannot satisfy allocations.
- `memory.events`: `high`, `max`, `oom`, `oom_kill` counters; capture deltas.
- `memory.stat`: anon, file, slab and related categories.
- `memory.pressure`: cgroup-local PSI when supported.

For Kubernetes, correlate pod `OOMKilled`, container memory usage/working set, cgroup events, node pressure, QoS and eviction decisions. Do not equate a container working-set metric with exact unreclaimable application memory.

## 5. Read-only incident workflow

```bash
date -u
uname -r
free -h
cat /proc/pressure/memory 2>/dev/null || true
vmstat 1 5
ps -eo pid,ppid,rss,vsz,stat,comm --sort=-rss | head -n 20
dmesg --ctime 2>/dev/null | grep -iE 'out of memory|oom-kill|killed process' | tail -n 20 || true
journalctl -k --since '-30 min' 2>/dev/null | grep -iE 'oom|memory' | tail -n 30 || true
```

Kernel logs can be permission-restricted and may contain sensitive process metadata. Never kill a database process, drop caches, disable swap or increase limits without workload-owner review and approved change controls.

## 6. Differential diagnosis

| Symptom | Supporting evidence | Next action |
|---|---|---|
| Low `MemFree`, healthy `MemAvailable` | stable PSI, no swap-in/out | baseline, do not panic |
| Memory leak | steadily rising anon/RSS and GC pressure | profile and compare releases |
| Reclaim storm | PSI, pgscan, latency increase | identify pressure source |
| Swap thrashing | sustained pswpin/out, faults and stalls | inspect working set and capacity |
| cgroup OOM | `memory.events` oom_kill delta | inspect limit and application heap |
| Node eviction | kubelet events and node memory pressure | isolate node/workload |
| Cache eviction | cache shrink, major faults and storage reads | review workload and IO |
| Misleading dashboard | scope/units/scrape mismatch | validate raw counters |

## 7. Prometheus queries (verify exporter support)

```promql
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
```

```promql
rate(node_vmstat_pswpin[5m]) + rate(node_vmstat_pswpout[5m])
```

```promql
rate(node_vmstat_pgmajfault[5m])
```

```promql
increase(node_vmstat_oom_kill[5m])
```

Metric availability depends on kernel, node_exporter version and collectors. Use PromQL with labels for instance/cluster and explicit `for` durations; couple with user-facing SLOs. For cgroups use compatible kubelet/cAdvisor or dedicated exporter metrics and confirm semantics before alerting.

## 8. Executable synthetic acceptance lab

Create:

```text
chapter008/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/memory_gate.py
  tests/test_memory_gate.py
```

### fixtures/healthy.json

```json
{
  "host": "staging-db-01",
  "owner": "dbre",
  "mem_available_pct": 38,
  "page_cache_pct": 41,
  "swap_used_pct": 5,
  "memory_psi_some_pct": 1,
  "memory_psi_full_pct": 0,
  "major_faults_delta": 8,
  "swap_in_pages_delta": 0,
  "swap_out_pages_delta": 0,
  "oom_kills_delta": 0,
  "memory_high_events_delta": 0,
  "service_p95_ms": 110,
  "service_budget_ms": 300
}
```

### fixtures/degraded.json

```json
{
  "host": "staging-db-01",
  "owner": "dbre",
  "mem_available_pct": 4,
  "page_cache_pct": 41,
  "swap_used_pct": 5,
  "memory_psi_some_pct": 38,
  "memory_psi_full_pct": 12,
  "major_faults_delta": 900,
  "swap_in_pages_delta": 4500,
  "swap_out_pages_delta": 6000,
  "oom_kills_delta": 2,
  "memory_high_events_delta": 15,
  "service_p95_ms": 1900,
  "service_budget_ms": 300
}
```

### scripts/memory_gate.py

```python
#!/usr/bin/env python3
"""Synthetic memory pressure acceptance gate; Python 3.10+."""
import json
import sys
from pathlib import Path

def assess(d):
    problems = []
    for k in ("host", "owner"):
        if not isinstance(d.get(k), str) or not d[k].strip():
            problems.append("missing " + k)
    for k in ("mem_available_pct", "swap_used_pct", "memory_psi_some_pct",
              "memory_psi_full_pct", "page_cache_pct"):
        v = d.get(k)
        if type(v) not in (int, float) or not 0 <= v <= 100:
            problems.append("invalid " + k)
    for k in ("major_faults_delta", "swap_in_pages_delta", "swap_out_pages_delta",
              "oom_kills_delta", "memory_high_events_delta"):
        v = d.get(k)
        if type(v) is not int or v < 0:
            problems.append("invalid " + k)
    for k in ("service_p95_ms", "service_budget_ms"):
        v = d.get(k)
        if type(v) not in (int, float) or v < 0 or (k == "service_budget_ms" and v == 0):
            problems.append("invalid " + k)
    if problems:
        return problems
    if d["mem_available_pct"] < 10:
        problems.append("low available memory")
    if d["memory_psi_some_pct"] >= 20 or d["memory_psi_full_pct"] >= 5:
        problems.append("memory stall pressure")
    if d["oom_kills_delta"]:
        problems.append("OOM kill event")
    if d["memory_high_events_delta"]:
        problems.append("cgroup memory.high events")
    if d["swap_in_pages_delta"] > 1000 or d["swap_out_pages_delta"] > 1000:
        problems.append("elevated swap activity")
    if d["major_faults_delta"] > 500:
        problems.append("elevated major page faults")
    if d["service_p95_ms"] > d["service_budget_ms"]:
        problems.append("service latency budget exceeded")
    return problems

if __name__ == "__main__":
    issues = assess(json.loads(Path(sys.argv[1]).read_text()))
    print("MEMORY GATE PASS (synthetic)" if not issues else "MEMORY GATE FAIL")
    for issue in issues:
        print("-", issue)
    sys.exit(bool(issues))
```

### tests/test_memory_gate.py

```python
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from memory_gate import assess

class MemoryGateTests(unittest.TestCase):
    def fixture(self, name="healthy.json"):
        return json.loads((ROOT / "fixtures" / name).read_text())

    def mutate(self, key, value):
        d = self.fixture()
        d[key] = value
        return assess(d)

    def test_healthy(self): self.assertEqual(assess(self.fixture()), [])
    def test_degraded(self): self.assertTrue(assess(self.fixture("degraded.json")))
    def test_available(self): self.assertTrue(self.mutate("mem_available_pct", 4))
    def test_memory_psi(self): self.assertTrue(self.mutate("memory_psi_some_pct", 35))
    def test_oom(self): self.assertTrue(self.mutate("oom_kills_delta", 1))
    def test_swap(self): self.assertTrue(self.mutate("swap_in_pages_delta", 2000))
    def test_major_faults(self): self.assertTrue(self.mutate("major_faults_delta", 1000))
    def test_memory_high(self): self.assertTrue(self.mutate("memory_high_events_delta", 3))
    def test_latency(self): self.assertTrue(self.mutate("service_p95_ms", 800))
    def test_bad_percent(self): self.assertTrue(self.mutate("page_cache_pct", 150))
    def test_missing_owner(self): self.assertTrue(self.mutate("owner", ""))
    def test_bad_count(self): self.assertTrue(self.mutate("oom_kills_delta", -1))

if __name__ == "__main__":
    unittest.main()
```

Execute:

```bash
python3 scripts/memory_gate.py fixtures/healthy.json
if python3 scripts/memory_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded memory accepted"; exit 1
else
  echo "PASS: degraded memory rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy exits 0, degraded exits nonzero, 12 unit tests pass. Thresholds are educational defaults, not universal production SLOs.

## 9. Twenty-four hands-on exercises

1. Capture kernel and cgroup version.
2. Inspect `free -h`.
3. Compare MemFree versus MemAvailable.
4. Inspect cache and reclaimable slab.
5. Inspect anon and RSS.
6. Inspect page faults.
7. Read swap-in/out counters.
8. Calculate swap rates.
9. Read memory PSI some/full.
10. Compare PSI avg10/avg60/avg300.
11. Read `memory.current`.
12. Read `memory.max`.
13. Read `memory.high`.
14. Inspect `memory.events` deltas.
15. Review Kubernetes OOMKilled.
16. Distinguish node eviction and cgroup OOM.
17. Design memory dashboard.
18. Design missing-data alert.
19. Write service-impact hypothesis.
20. Create healthy fixture.
21. Create degraded fixture.
22. Run positive/negative gates.
23. Run twelve unit tests.
24. Write RCA/COA and capacity recommendation.

## 10. Twenty production failure scenarios

| # | Failure | Investigation |
|---|---|---|
| 01 | High cache mistaken for leak | MemAvailable/PSI |
| 02 | Java heap exhaustion | heap/GC |
| 03 | MongoDB WiredTiger pressure | cache/reclaim |
| 04 | PostgreSQL process RSS growth | process/cgroup |
| 05 | Elasticsearch heap OOM | JVM and shard load |
| 06 | Redis memory eviction | maxmemory/policy |
| 07 | Node memory pressure | kubelet |
| 08 | Container OOMKilled | memory.events |
| 09 | cgroup memory.high throttling | high events |
| 10 | Swap thrashing | pswpin/out |
| 11 | Direct reclaim latency | PSI |
| 12 | Major fault surge | pgmajfault |
| 13 | Memory leak after deploy | growth slope |
| 14 | Page cache collapse | storage reads |
| 15 | NUMA locality pressure | per-node memory |
| 16 | Huge page allocation failure | hugepage counters |
| 17 | Kernel slab growth | slabtop |
| 18 | OOM logs unavailable | permissions |
| 19 | Missing exporter metrics | collector |
| 20 | Working-set metric misunderstood | semantics |

## 11. Eight production runbooks

**A. Host memory pressure:** Confirm service impact, MemAvailable, PSI, reclaim, swap and top processes; preserve time-aligned evidence.

**B. Container OOM:** Inspect pod events, memory.events, memory.max, heap/cache and recent releases; stage resource adjustments.

**C. Swap/reclaim storm:** Correlate pswpin/out, major faults, PSI and storage latency; reduce load safely and plan capacity.

**D. Database cache pressure:** Correlate DB internal cache, filesystem cache, query latency, IOPS and workload concurrency.

**E. Suspected leak:** Compare RSS/heap slopes and deployments; use approved profiling, canary rollback and controlled restarts.

**F. Node eviction:** Inspect kubelet thresholds, node allocatable, QoS and pod usage; coordinate rescheduling.

**G. Missing memory telemetry:** Validate exporter, permissions, collector, cgroup scope and missing-data alerting.

**H. Production readiness:** Define workload-specific thresholds, baselines, ownership, evidence retention, capacity headroom and rollback.

## 12. 100-point acceptance

| Area | Points |
|---|---:|
| Linux memory architecture and accounting | 20 |
| PSI, reclaim, swap and OOM diagnosis | 20 |
| cgroup/Kubernetes and DBRE scenarios | 20 |
| Synthetic lab and twelve tests | 20 |
| Runbooks, security and evidence | 20 |
| **Total** | **100** |

Suggested pass 85/100. Mandatory gates: read-only investigation, MemAvailable versus MemFree distinction, cgroup scope awareness, safe negative test rejection, 12 tests and evidence review.

## 13. Evidence worksheet

```text
UTC / host / workload / owner:
MemAvailable / cache / RSS / slab:
PSI some/full / swap-in/out / faults:
cgroup memory.current/high/max/events:
OOM / Kubernetes events:
Service p95 / customer impact:
Healthy fixture / degraded fixture:
Twelve unit tests:
RCA / COA / reviewer:
```

**Companion:** [Chapter 008 executable lab](labs/008-linux-memory-management-page-cache-swap-psi-oom-troubleshooting-lab.md).

**Next:** Chapter 009 — Linux Storage IOPS, Throughput, Disk Latency, Filesystems and I/O Troubleshooting.
