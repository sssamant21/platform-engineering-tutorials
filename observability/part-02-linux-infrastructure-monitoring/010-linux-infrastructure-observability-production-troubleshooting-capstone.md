# Chapter 010 — Linux Infrastructure Observability and Production Troubleshooting Capstone

**Part 02 — Linux and Infrastructure Monitoring: final capstone**  
**Audience:** SRE/DBRE, Linux and cloud platform engineers, on-call incident commanders.  
**Prerequisites:** Chapters 006–009, Linux/WSL2, Python 3.10+; optional Prometheus/node_exporter.  
**Scope:** Offline synthetic acceptance and read-only host investigation. No production certification or deployment is implied.

## 1. Mission

Design and validate a Linux infrastructure observability system that distinguishes **CPU scheduling contention, memory reclaim/OOM, storage saturation, network degradation, application latency and telemetry blind spots**. Apply evidence-first triage to a fictional search API using Elasticsearch, PostgreSQL, Redis and Kafka. Complete 24 exercises, 20 incident scenarios, eight runbooks, a 14-test executable gate and a 100-point acceptance review.

## 2. Production reference architecture

```text
User / API latency, errors, saturation (service SLO)
                       |
           application / database processes
                       |
 Linux kernel (/proc, /sys, PSI, cgroup v2)
        |          |          |         |
     CPU/runq   memory/OOM  block I/O  NIC/TCP
        \          |          |        /
          node_exporter + process exporters
                       |
               Prometheus / OTEL
                 /          \
          recording rules  telemetry health
                 \          /
            Grafana / alert routing
                       |
              on-call / RCA / COA
```

Architecture decisions: host and pod ownership, tenancy, network segmentation, TLS and RBAC, metrics retention, scrape interval, missing-data alerting, high-cardinality budgets, label policy, time synchronization, alert routing and tested escalation. Host metrics explain mechanisms; user-facing SLOs establish impact. Telemetry pipeline health must be monitored independently.

## 3. Signals and differential diagnosis

| Layer | Read-only sources | Core question |
|---|---|---|
| CPU | `/proc/stat`, `vmstat`, `mpstat`, `pidstat`, CPU PSI | Busy, queued, throttled or stolen? |
| Memory | `/proc/meminfo`, `vmstat`, memory PSI, `memory.events` | Cache or reclaim/OOM pressure? |
| Storage | `df -hT`, `df -i`, `iostat -xz`, I/O PSI | Capacity, IOPS, throughput or latency? |
| Network | `ip -s link`, `ss -s`, `/proc/net/dev` | Errors, drops, connection pressure? |
| Workload | traces, DB metrics, logs, p95 and errors | Which dependency hurts users? |
| Telemetry | exporter `up`, scrape errors, freshness | Are measurements trustworthy? |

**Interpretation:** Load average is not CPU utilization. Low `MemFree` is not automatically memory pressure. Disk `%util` is not a universal NVMe saturation indicator. An allocated swap file does not imply active swap thrashing. Cumulative counters require deltas. Node health cannot substitute for application SLOs.

## 4. Read-only production investigation

```bash
date -u
uname -r
uptime
cat /proc/loadavg
vmstat 1 5
free -h
df -hT
df -i
lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,ROTA
ip -s link
ss -s
cat /proc/pressure/cpu 2>/dev/null || true
cat /proc/pressure/memory 2>/dev/null || true
cat /proc/pressure/io 2>/dev/null || true
command -v mpstat >/dev/null && mpstat -P ALL 1 3 || true
command -v pidstat >/dev/null && pidstat -u -d 1 3 || true
command -v iostat >/dev/null && iostat -xz 1 3 || true
cat /sys/fs/cgroup/cpu.stat 2>/dev/null || true
cat /sys/fs/cgroup/memory.events 2>/dev/null || true
```

Note which tools are unavailable, permissions, and whether the shell is inside a container. Kernel logs and process metadata can be sensitive; restrict evidence storage. Do not run stress tools, delete data, change quotas, clear caches or restart production services without approval.

## 5. Observability contracts and SLOs

Document metric name, unit, source, label set, owner, scrape interval, expected freshness, alert duration, dashboard, runbook and impact correlation.

Examples (verify exporter support and filter devices appropriately):

```promql
100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))
```

```promql
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
```

```promql
rate(node_disk_read_bytes_total[5m]) + rate(node_disk_written_bytes_total[5m])
```

```promql
rate(node_network_receive_errs_total[5m]) + rate(node_network_transmit_errs_total[5m])
```

```promql
up{job="node-exporter"} == 0
```

A missing time series may not satisfy `up == 0`; use an appropriate `absent_over_time` rule for missing expected targets, with service discovery/labels explicitly controlled. Alert routing should include severity, impact, ownership and remediation guidance.

## 6. Synthetic end-to-end acceptance gate

The following code is self-contained and uses only Python's standard library. Build:

```text
chapter010/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/infra_gate.py
  tests/test_infra_gate.py
```

### fixtures/healthy.json

```json
{
  "host": "staging-db-01",
  "owner": "platform-sre",
  "cpu_busy_pct": 44,
  "cpu_psi_pct": 2,
  "load_per_cpu": 0.7,
  "mem_available_pct": 34,
  "memory_psi_pct": 1,
  "oom_delta": 0,
  "fs_used_pct": 63,
  "inode_used_pct": 28,
  "disk_await_ms": 4,
  "disk_budget_ms": 20,
  "io_psi_pct": 1,
  "net_errors_delta": 0,
  "net_drops_delta": 0,
  "service_p95_ms": 130,
  "service_budget_ms": 300,
  "telemetry_age_seconds": 8,
  "max_telemetry_age_seconds": 30
}
```

### fixtures/degraded.json

```json
{
  "host": "staging-db-01",
  "owner": "platform-sre",
  "cpu_busy_pct": 95,
  "cpu_psi_pct": 35,
  "load_per_cpu": 3,
  "mem_available_pct": 4,
  "memory_psi_pct": 40,
  "oom_delta": 2,
  "fs_used_pct": 97,
  "inode_used_pct": 95,
  "disk_await_ms": 80,
  "disk_budget_ms": 20,
  "io_psi_pct": 38,
  "net_errors_delta": 25,
  "net_drops_delta": 500,
  "service_p95_ms": 2600,
  "service_budget_ms": 300,
  "telemetry_age_seconds": 150,
  "max_telemetry_age_seconds": 30
}
```

### scripts/infra_gate.py

```python
#!/usr/bin/env python3
"""Offline, synthetic Linux infrastructure acceptance gate."""
import json
import sys
from pathlib import Path

PERCENT = ("cpu_busy_pct", "cpu_psi_pct", "mem_available_pct",
           "memory_psi_pct", "fs_used_pct", "inode_used_pct", "io_psi_pct")
NONNEGATIVE = ("load_per_cpu", "disk_await_ms", "service_p95_ms",
               "telemetry_age_seconds")
POSITIVE = ("disk_budget_ms", "service_budget_ms",
            "max_telemetry_age_seconds")
COUNTERS = ("oom_delta", "net_errors_delta", "net_drops_delta")

def assess(data):
    findings = []
    for field in ("host", "owner"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            findings.append("missing " + field)
    for field in PERCENT:
        value = data.get(field)
        if type(value) not in (int, float) or not 0 <= value <= 100:
            findings.append("invalid " + field)
    for field in NONNEGATIVE + POSITIVE:
        value = data.get(field)
        if type(value) not in (int, float) or value < 0 or (field in POSITIVE and value == 0):
            findings.append("invalid " + field)
    for field in COUNTERS:
        if type(data.get(field)) is not int or data[field] < 0:
            findings.append("invalid " + field)
    if findings:
        return findings
    if data["cpu_busy_pct"] >= 90 and data["cpu_psi_pct"] >= 20:
        findings.append("CPU saturation with scheduler pressure")
    if data["load_per_cpu"] >= 2 and data["io_psi_pct"] >= 20:
        findings.append("high load with I/O stalls")
    if data["mem_available_pct"] < 10 or data["memory_psi_pct"] >= 20:
        findings.append("memory pressure")
    if data["oom_delta"] > 0:
        findings.append("OOM event")
    if data["fs_used_pct"] >= 90:
        findings.append("filesystem capacity")
    if data["inode_used_pct"] >= 90:
        findings.append("inode capacity")
    if data["disk_await_ms"] > data["disk_budget_ms"]:
        findings.append("disk latency budget")
    if data["net_errors_delta"] or data["net_drops_delta"]:
        findings.append("network errors/drops")
    if data["service_p95_ms"] > data["service_budget_ms"]:
        findings.append("service latency budget")
    if data["telemetry_age_seconds"] > data["max_telemetry_age_seconds"]:
        findings.append("stale telemetry")
    return findings

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 infra_gate.py fixture.json", file=sys.stderr)
        sys.exit(2)
    problems = assess(json.loads(Path(sys.argv[1]).read_text()))
    print("INFRA CAPSTONE PASS (synthetic)" if not problems else "INFRA CAPSTONE FAIL")
    for problem in problems:
        print("-", problem)
    sys.exit(bool(problems))
```

### tests/test_infra_gate.py

```python
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from infra_gate import assess

class InfraCapstoneTests(unittest.TestCase):
    def fixture(self, name="healthy.json"):
        return json.loads((ROOT / "fixtures" / name).read_text())

    def changed(self, **changes):
        d = self.fixture()
        d.update(changes)
        return assess(d)

    def test_healthy(self): self.assertEqual(assess(self.fixture()), [])
    def test_degraded(self): self.assertTrue(assess(self.fixture("degraded.json")))
    def test_cpu(self): self.assertIn("CPU saturation with scheduler pressure", self.changed(cpu_busy_pct=95, cpu_psi_pct=30))
    def test_blocked_io(self): self.assertIn("high load with I/O stalls", self.changed(load_per_cpu=3, io_psi_pct=40))
    def test_memory(self): self.assertIn("memory pressure", self.changed(mem_available_pct=4))
    def test_oom(self): self.assertIn("OOM event", self.changed(oom_delta=1))
    def test_disk(self): self.assertIn("disk latency budget", self.changed(disk_await_ms=80))
    def test_inode(self): self.assertIn("inode capacity", self.changed(inode_used_pct=95))
    def test_network(self): self.assertIn("network errors/drops", self.changed(net_drops_delta=5))
    def test_service(self): self.assertIn("service latency budget", self.changed(service_p95_ms=900))
    def test_stale(self): self.assertIn("stale telemetry", self.changed(telemetry_age_seconds=120))
    def test_missing_owner(self): self.assertIn("missing owner", self.changed(owner=""))
    def test_invalid_pct(self): self.assertIn("invalid cpu_busy_pct", self.changed(cpu_busy_pct=101))
    def test_invalid_counter(self): self.assertIn("invalid oom_delta", self.changed(oom_delta=-1))

if __name__ == "__main__":
    unittest.main()
```

### Run

```bash
cd chapter010
python3 scripts/infra_gate.py fixtures/healthy.json
if python3 scripts/infra_gate.py fixtures/degraded.json; then
  echo "FAIL: unsafe synthetic case was accepted"
  exit 1
else
  echo "PASS: unsafe synthetic case was rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy exit 0, degraded exit nonzero, 14 passing tests. All values are synthetic and thresholds must be tuned to actual workloads. A finding is a triage indicator, not proof of a root cause.

## 7. Twenty-four hands-on exercises

1. Draw host-to-service topology.
2. Assign Linux host and workload owners.
3. Define service p95 SLO and impact.
4. Capture UTC and kernel version.
5. Inspect load average and run queue.
6. Inspect per-core and per-thread CPU.
7. Read CPU PSI.
8. Read cgroup CPU throttling deltas.
9. Inspect MemAvailable and cache.
10. Inspect memory PSI.
11. Read OOM and cgroup events.
12. Inspect swap-in/out deltas.
13. Inspect filesystem byte capacity.
14. Inspect inode capacity.
15. Capture IOPS and throughput.
16. Capture disk latency and I/O PSI.
17. Inspect NIC errors/drops.
18. Inspect TCP socket states.
19. Verify node_exporter presence.
20. Design missing-data alert.
21. Construct healthy fixture.
22. Construct degraded fixture.
23. Run positive/negative gate and 14 tests.
24. Produce RCA, COA, evidence and acceptance score.

## 8. Twenty production failure scenarios

| # | Scenario | Triage |
|---|---|---|
| 01 | CPU-bound Redis thread | per-thread CPU, latency |
| 02 | High load with low CPU busy | D-state, I/O PSI |
| 03 | Cgroup CPU throttling | quota and counter deltas |
| 04 | Hypervisor steal | steal trend/provider |
| 05 | Memory cache mistaken for leak | MemAvailable and PSI |
| 06 | PostgreSQL memory pressure | process/cgroup |
| 07 | Elasticsearch heap OOM | JVM and pod events |
| 08 | MongoDB cache eviction | WiredTiger/reclaim |
| 09 | Swap thrashing | pswpin/out, faults |
| 10 | Container OOMKilled | memory.events |
| 11 | Filesystem full | df, growth |
| 12 | Inode exhaustion | df -i |
| 13 | Disk IOPS ceiling | provisioned limit |
| 14 | Disk throughput ceiling | MiB/s |
| 15 | High disk await | queue and cloud metrics |
| 16 | Elasticsearch merge storm | merge/IO |
| 17 | Network packet drops | NIC/driver |
| 18 | TCP connection backlog | ss/application |
| 19 | Missing node_exporter | scrape/absent |
| 20 | Stale telemetry during outage | independent freshness |

## 9. Eight production runbooks

**A. CPU contention:** Establish customer impact; inspect per-core CPU, runnable queue, CPU PSI and cgroup throttling; mitigate workload safely.

**B. Memory/OOM:** Review MemAvailable, PSI, swap, process RSS and memory.events; preserve logs; stage heap/limit changes.

**C. Storage latency:** Correlate device await, queue, IOPS, throughput, cloud caps and database workload; avoid unsafe cache/mount changes.

**D. Filesystem/inode exhaustion:** Identify owner and growth source; verify backup/retention; obtain approval before cleanup.

**E. Network degradation:** Inspect interface drops/errors, sockets, cloud networking and application traces; differentiate packet loss from downstream latency.

**F. Database performance:** For Elasticsearch, PostgreSQL, MongoDB or Redis, connect kernel evidence with internal DB telemetry and query/command mix.

**G. Telemetry blind spot:** Verify exporter process, scrape configuration, Collector health, missing-data alerts and evidence freshness.

**H. Incident command and recovery:** Assign incident commander, timeline, impact, containment, rollback, verification, RCA/COA and follow-up owners.

## 10. 100-point capstone assessment

| Domain | Points |
|---|---:|
| Architecture, ownership and SLO mapping | 20 |
| CPU/memory differential diagnosis | 20 |
| Storage/network differential diagnosis | 20 |
| Executable gate and 14 tests | 20 |
| Runbooks, evidence, incident tabletop | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory: safe read-only evidence, correct CPU/load and cache/memory distinctions, detection of synthetic failure, 14 tests, missing-telemetry plan and owner-reviewed remediation.

## 11. Incident tabletop and acceptance evidence

**Scenario:** An Elasticsearch-backed API p95 jumps from 130 ms to 2.6 s. Linux load increases; CPU is moderately busy; I/O PSI and disk await spike; the node exporter stops reporting for 2 minutes. Determine whether storage saturation, database merge load or telemetry loss explains each symptom. Document uncertainties, independent signals, containment, rollback and post-mitigation SLO verification.

```text
UTC / incident ID / host / owner:
Application SLO and impact:
CPU busy / load / CPU PSI:
Memory available / PSI / OOM:
Filesystem/inodes / disk await / IOPS / throughput:
Network drops/errors / sockets:
Telemetry freshness and gaps:
Healthy/degraded fixture checks:
Fourteen unit tests:
Twenty scenario reviews / eight runbooks:
RCA / COA / approver / acceptance score:
```

**Companion:** [Chapter 010 executable capstone lab](labs/010-linux-infrastructure-observability-production-troubleshooting-capstone-lab.md).

**Next:** Chapter 011 — Prometheus Architecture, Data Model, Scraping and Production Deployment Fundamentals (Part 03).
