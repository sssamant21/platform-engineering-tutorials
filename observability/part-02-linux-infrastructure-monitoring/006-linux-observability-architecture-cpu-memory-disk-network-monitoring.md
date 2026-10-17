# Chapter 006 — Linux Observability Architecture, CPU, Memory, Disk and Network Monitoring

**Part 02 — Linux and Infrastructure Monitoring**  
**Audience:** SRE/DBRE, Linux administrators, platform engineers, on-call responders.  
**Prerequisites:** Chapters 001–005; Linux VM, WSL2 or container host; Python 3.10+; shell utilities.

## 1. Learning objectives

Build a four-layer Linux monitoring model: **host → process → workload → user impact**. Understand CPU utilization versus pressure, memory reclaim and OOM, disk capacity versus I/O saturation, and network throughput versus packet errors. Collect read-only evidence, interpret kernel counters and validate synthetic incident thresholds with automated tests.

## 2. Reference architecture

```text
Linux kernel (/proc, /sys, cgroups, PSI)
         |                 |
   node_exporter       process/app exporters
         |                 |
         +------ Prometheus / OTEL Collector
                        |
              recording rules / alerts
                        |
                 Grafana / SLO
                        |
           incident response / RCA
```

For containers, inspect both host counters and cgroup limits. For virtual machines, correlate guest metrics with cloud storage/network metrics; the guest cannot always reveal provider-side throttling.

## 3. CPU: utilization, scheduling and pressure

- `/proc/stat`: cumulative CPU jiffies; calculate rates over an interval, not a single snapshot.
- `uptime` and `/proc/loadavg`: runnable plus uninterruptible tasks; load is **not** CPU utilization.
- `vmstat 1`: run queue, blocked tasks, swap activity, CPU idle and I/O wait.
- `pidstat -u 1`, `top -H`: process/thread CPU.
- `/proc/pressure/cpu`: CPU scheduling pressure stall information where supported.
- cgroup v2 `cpu.stat`: `nr_throttled`, `throttled_usec` and `usage_usec`; examine throttling **rate** and application latency.

A CPU-bound Redis command can saturate one execution thread while total multi-core host CPU looks low. A PostgreSQL workload can show high load due to I/O-blocked tasks rather than CPU saturation.

## 4. Memory: available, reclaim, OOM

- `/proc/meminfo`: `MemAvailable` is a better general headroom estimate than `MemFree`.
- `free -h`, `vmstat 1`: cache, swap and reclaim behavior.
- `/proc/pressure/memory`: memory stalls.
- `journalctl -k`: OOM-killer evidence (permissions permitting).
- cgroup v2 `memory.current`, `memory.max`, `memory.events`: container memory usage, limits and OOM events.

High page cache use alone is not an incident. Combine available memory, reclaim, OOM events, swap activity and workload latency.

## 5. Storage: capacity is not throughput

| Signal | Evidence | Failure hypothesis |
|---|---|---|
| Filesystem free | `df -hT` | disk full |
| Inodes | `df -i` | inode exhaustion |
| Device throughput | `iostat -xz 1` | throughput ceiling |
| IOPS / queue | `iostat -xz 1` | I/O saturation |
| Latency | `await` and cloud disk metrics | backend storage bottleneck |
| Process I/O | `pidstat -d 1` | heavy writer/reader |
| Filesystem errors | `dmesg`, `journalctl -k` | storage health |

`%util` is not a universal saturation indicator on parallel SSD/NVMe systems; correlate queue, latency, service limits and user-facing symptoms. Database shard/segment merge pressure can produce disk bottlenecks without high CPU.

## 6. Network: packets, errors and path

- `ip -s link`: RX/TX packets, drops and errors.
- `ss -s`, `ss -tanp`: socket state and connection pressure.
- `/proc/net/dev`: cumulative per-interface byte/packet counters.
- `ethtool -S IFACE`: driver counters (if supported).
- `sar -n DEV 1`: throughput rates (sysstat).
- `mtr`/`traceroute`: path clues; ICMP rate limits can mislead.
- `curl -w` and application tracing: distinguish DNS, connect, TLS and server latency.

Avoid packet captures with payloads unless approved; they can expose credentials or patient data.

## 7. Read-only investigation commands

```bash
date -u
uname -a
uptime
cat /proc/loadavg
grep -E '^(MemTotal|MemAvailable|SwapTotal|SwapFree):' /proc/meminfo
df -hT
df -i
ip -s link
ss -s
cat /proc/pressure/cpu 2>/dev/null || true
cat /proc/pressure/memory 2>/dev/null || true
cat /proc/pressure/io 2>/dev/null || true
command -v iostat >/dev/null && iostat -xz 1 3 || true
command -v vmstat >/dev/null && vmstat 1 3 || true
```

Capture timestamps and workload impact. Do not treat missing optional utilities as a healthy signal. In containers, `/proc` and namespace visibility may differ from host scope.

## 8. Prometheus and alert design

Useful node_exporter metrics (verify installed collector/version): `node_cpu_seconds_total`, `node_memory_MemAvailable_bytes`, `node_memory_MemTotal_bytes`, `node_filesystem_avail_bytes`, `node_filesystem_size_bytes`, `node_disk_read_bytes_total`, `node_disk_written_bytes_total`, `node_network_receive_errs_total`, `node_network_transmit_errs_total`.

Illustrative PromQL:

```promql
100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))
```

```promql
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
```

```promql
100 * (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{fstype!~"tmpfs|overlay"})
```

```promql
rate(node_network_receive_errs_total[5m]) + rate(node_network_transmit_errs_total[5m])
```

Filesystem filtering must be customized for your environment, including ephemeral mounts, read-only devices and Kubernetes volume labels. Alerts should include a duration, owner, service impact and runbook link; do not alert solely on CPU percentages.

## 9. Executable synthetic Linux health gate

Create:

```text
chapter006/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/linux_health.py
  tests/test_linux_health.py
```

### fixtures/healthy.json

```json
{
  "host": "staging-linux-01",
  "owner": "platform-sre",
  "cpu_utilization_pct": 55,
  "cpu_pressure_some_pct": 3,
  "memory_available_pct": 32,
  "memory_pressure_some_pct": 1,
  "oom_kills_delta": 0,
  "filesystem_used_pct": 65,
  "inode_used_pct": 35,
  "disk_await_ms": 4,
  "disk_latency_budget_ms": 20,
  "network_errors_delta": 0,
  "network_drops_delta": 0,
  "service_p95_ms": 140,
  "service_latency_budget_ms": 300
}
```

### fixtures/degraded.json

```json
{
  "host": "staging-linux-01",
  "owner": "",
  "cpu_utilization_pct": 96,
  "cpu_pressure_some_pct": 35,
  "memory_available_pct": 3,
  "memory_pressure_some_pct": 40,
  "oom_kills_delta": 2,
  "filesystem_used_pct": 97,
  "inode_used_pct": 99,
  "disk_await_ms": 65,
  "disk_latency_budget_ms": 20,
  "network_errors_delta": 100,
  "network_drops_delta": 500,
  "service_p95_ms": 2200,
  "service_latency_budget_ms": 300
}
```

### scripts/linux_health.py

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

PERCENT_FIELDS = (
    "cpu_utilization_pct", "cpu_pressure_some_pct", "memory_available_pct",
    "memory_pressure_some_pct", "filesystem_used_pct", "inode_used_pct"
)
COUNTERS = ("oom_kills_delta", "network_errors_delta", "network_drops_delta")
LATENCIES = ("disk_await_ms", "disk_latency_budget_ms", "service_p95_ms", "service_latency_budget_ms")

def assess(d):
    errors = []
    for key in ("host", "owner"):
        if not isinstance(d.get(key), str) or not d[key].strip():
            errors.append(f"missing {key}")
    for key in PERCENT_FIELDS:
        value = d.get(key)
        if type(value) not in (int, float) or not 0 <= value <= 100:
            errors.append(f"invalid {key}")
    for key in COUNTERS:
        if type(d.get(key)) is not int or d[key] < 0:
            errors.append(f"invalid {key}")
    for key in LATENCIES:
        value = d.get(key)
        if type(value) not in (int, float) or value < 0 or (key.endswith("budget_ms") and value == 0):
            errors.append(f"invalid {key}")
    if any(e.startswith("invalid ") for e in errors):
        return errors
    if d["cpu_utilization_pct"] >= 90 and d["cpu_pressure_some_pct"] >= 20:
        errors.append("CPU saturation and scheduling pressure")
    if d["memory_available_pct"] < 10 or d["memory_pressure_some_pct"] >= 20:
        errors.append("memory pressure")
    if d["oom_kills_delta"] > 0:
        errors.append("OOM kills detected")
    if d["filesystem_used_pct"] >= 90:
        errors.append("filesystem capacity critical")
    if d["inode_used_pct"] >= 90:
        errors.append("inode exhaustion risk")
    if d["disk_await_ms"] > d["disk_latency_budget_ms"]:
        errors.append("disk latency budget exceeded")
    if d["network_errors_delta"] > 0 or d["network_drops_delta"] > 0:
        errors.append("network errors or drops detected")
    if d["service_p95_ms"] > d["service_latency_budget_ms"]:
        errors.append("service latency SLO diagnostic breached")
    return errors

if __name__ == "__main__":
    problems = assess(json.loads(Path(sys.argv[1]).read_text()))
    print("LINUX HEALTH PASS: synthetic" if not problems else "LINUX HEALTH FAIL")
    for problem in problems:
        print("-", problem)
    sys.exit(bool(problems))
```

Run:

```bash
python3 scripts/linux_health.py fixtures/healthy.json
if python3 scripts/linux_health.py fixtures/degraded.json; then
  echo "FAIL: degraded host accepted"; exit 1
else
  echo "PASS: degraded host rejected"
fi
```

### tests/test_linux_health.py

```python
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from linux_health import assess

class LinuxHealthTests(unittest.TestCase):
    def fixture(self, name):
        return json.loads((ROOT / "fixtures" / name).read_text())

    def test_healthy(self):
        self.assertEqual(assess(self.fixture("healthy.json")), [])

    def test_degraded(self):
        self.assertTrue(assess(self.fixture("degraded.json")))

    def test_disk(self):
        d = self.fixture("healthy.json")
        d["disk_await_ms"] = 50
        self.assertTrue(assess(d))

    def test_inode(self):
        d = self.fixture("healthy.json")
        d["inode_used_pct"] = 95
        self.assertTrue(assess(d))

    def test_oom(self):
        d = self.fixture("healthy.json")
        d["oom_kills_delta"] = 1
        self.assertTrue(assess(d))

    def test_network(self):
        d = self.fixture("healthy.json")
        d["network_errors_delta"] = 2
        self.assertTrue(assess(d))

    def test_cpu_pressure(self):
        d = self.fixture("healthy.json")
        d["cpu_utilization_pct"] = 95
        d["cpu_pressure_some_pct"] = 30
        self.assertTrue(assess(d))

    def test_invalid_percent(self):
        d = self.fixture("healthy.json")
        d["filesystem_used_pct"] = 110
        self.assertTrue(assess(d))

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest discover -s tests -v
```

## 10. Twenty-four hands-on exercises

1. Identify host, process, workload and service layers.
2. Capture timestamped Linux inventory.
3. Read `/proc/stat` and explain delta-based CPU utilization.
4. Compare load average and CPU utilization.
5. Inspect CPU PSI.
6. Inspect cgroup CPU throttling.
7. Inspect `MemAvailable`.
8. Inspect swap and reclaim.
9. Inspect memory PSI.
10. Inspect cgroup OOM events.
11. Check filesystem capacity.
12. Check inode consumption.
13. Capture device latency with `iostat`.
14. Explain IOPS, throughput, queue and await.
15. Check NIC errors and drops.
16. Inspect TCP socket summary.
17. Design node_exporter labels.
18. Write PromQL CPU expression.
19. Write PromQL memory expression.
20. Define storage latency alert.
21. Create healthy fixture.
22. Create degraded fixture.
23. Run positive, negative and eight unit tests.
24. Write incident investigation summary.

## 11. Twenty production failure scenarios

| # | Failure | Investigation |
|---|---|---|
| 01 | CPU saturated | run queue and per-thread CPU |
| 02 | High load but idle CPU | I/O-blocked tasks |
| 03 | cgroup throttling | CPU quota |
| 04 | memory reclaim storm | PSI and swap |
| 05 | OOMKilled container | memory.events |
| 06 | page cache misunderstood | MemAvailable |
| 07 | disk capacity full | df |
| 08 | inode exhaustion | df -i |
| 09 | high IOPS | device limits |
| 10 | high throughput | cloud disk caps |
| 11 | disk latency spike | await/queue |
| 12 | SSD %util misread | device parallelism |
| 13 | network packet drops | NIC counters |
| 14 | TCP connection pressure | ss |
| 15 | DNS resolution slowness | resolver |
| 16 | cloud throttling invisible | provider metrics |
| 17 | missing node exporter | scrape |
| 18 | duplicate exporter target | discovery |
| 19 | high host CPU, healthy service | impact check |
| 20 | healthy host, slow service | app/dependency trace |

## 12. Eight production runbooks

**A. CPU pressure:** Compare utilization, run queue, PSI, throttling and service latency; identify hot threads and safely reduce workload.

**B. Memory/OOM:** Inspect available memory, reclaim, cgroup events, kernel logs and application memory; mitigate without blindly raising limits.

**C. Disk I/O saturation:** Check IOPS, throughput, queue, await, cloud limits, filesystem and database merges; preserve workload metrics.

**D. Disk full/inodes:** Identify filesystem, inode and growth sources; avoid deleting unknown data or open files without ownership review.

**E. Network errors/drops:** Correlate NIC counters, sockets, application latency and cloud network telemetry; validate path.

**F. Exporter missing:** Verify process, scrape, permissions, host namespace, service discovery and absent-metric alerts.

**G. Container versus host mismatch:** Check cgroup limits, namespace boundaries, node pressure and pod QoS; document attribution.

**H. Linux production readiness:** Baseline, alert ownership, dashboard, SLO mapping, capacity and rollback review.

## 13. 100-point acceptance

| Domain | Points |
|---|---:|
| Linux architecture and evidence collection | 20 |
| CPU and memory interpretation | 20 |
| Disk and network investigation | 20 |
| Prometheus alert/SLO design | 20 |
| Lab tests, runbooks and evidence | 20 |
| **Total** | **100** |

Suggested pass 85/100, with mandatory gates for read-only evidence collection, host/workload distinction, disk latency interpretation, positive/negative fixtures and eight unit tests.

## 14. Evidence worksheet

```text
UTC / host / workload / owner:
CPU utilization/load/PSI:
Memory available/reclaim/OOM:
Filesystem/inodes:
Disk IOPS/throughput/await:
NIC errors/drops:
Service SLI/latency:
Exporter/PromQL:
Healthy fixture:
Degraded fixture:
Eight tests:
RCA / COA / reviewer:
```

**Companion:** [Chapter 006 Linux observability lab](labs/006-linux-observability-architecture-cpu-memory-disk-network-monitoring-lab.md).

**Next:** Chapter 007 — Linux CPU Scheduling, Load Average, Run Queues and Performance Troubleshooting.
