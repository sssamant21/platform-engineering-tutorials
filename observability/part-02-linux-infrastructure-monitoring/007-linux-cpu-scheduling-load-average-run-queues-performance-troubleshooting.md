# Chapter 007 — Linux CPU Scheduling, Load Average, Run Queues and Performance Troubleshooting

**Part 02 — Linux and Infrastructure Monitoring**  
**Audience:** SRE, DBRE, Linux and Kubernetes operators. **Prerequisites:** Chapters 001–006, Linux shell, Python 3.10+.  
**Outcome:** Distinguish CPU saturation, I/O-blocked load, cgroup throttling, scheduler contention and application latency using reproducible evidence.

## 1. Mental model

CPU utilization is time spent executing; load average counts tasks runnable or in uninterruptible sleep, averaged over 1, 5 and 15 minutes; run queue indicates runnable work waiting for CPU; CPU pressure stall information (PSI) measures time tasks are delayed for CPU; throttling measures cgroup CPU quota enforcement. These are **not interchangeable**.

```text
Incoming requests
      |
Application threads/processes
      |
Linux scheduler / run queue ----> CPU cores
      |                              |
      +-- cgroup quota/throttle      +-- user/system/irq/steal
      |
      +-- blocked I/O (D state) --> storage/network dependencies
      |
Application latency / errors / SLO burn
```

A high load average with low CPU utilization can indicate uninterruptible I/O wait. A single-threaded Redis command can saturate one core while overall host CPU looks modest. CPU quota throttling can degrade pod latency even when the node has idle cores.

## 2. Linux scheduler essentials

Linux uses scheduling classes and per-CPU run queues. CFS concepts remain important, but newer Linux kernels may use EEVDF scheduling behavior; do not assume identical scheduler internals across kernel versions. Scheduling priority, nice values, affinity, CPU quota, SMT topology and NUMA placement influence runnable latency. CPU time categories from `/proc/stat` include user, nice, system, idle, iowait, irq, softirq, steal, guest and guest_nice.

Use deltas between two `/proc/stat` samples to calculate CPU utilization; counters are cumulative. I/O wait is a CPU accounting state, not direct device latency. For disk latency, use `iostat`, cloud volume metrics and service tracing.

## 3. Read-only diagnostic workflow

```bash
date -u
uname -r
nproc
uptime
cat /proc/loadavg
cat /proc/stat | head -n 5
cat /proc/pressure/cpu 2>/dev/null || true
cat /proc/pressure/io 2>/dev/null || true
vmstat 1 5
command -v mpstat >/dev/null && mpstat -P ALL 1 3 || true
command -v pidstat >/dev/null && pidstat -u -t 1 3 || true
command -v iostat >/dev/null && iostat -xz 1 3 || true
ps -eo pid,ppid,stat,ni,psr,pcpu,comm --sort=-pcpu | head -n 20
```

For a cgroup v2 workload, inspect its own files (path varies by deployment):

```bash
cat /sys/fs/cgroup/cpu.max 2>/dev/null || true
cat /sys/fs/cgroup/cpu.stat 2>/dev/null || true
cat /sys/fs/cgroup/cpu.pressure 2>/dev/null || true
```

`cpu.max` is quota and period in microseconds or `max` for unlimited. `cpu.stat` counters include throttling data where supported. Compute **rates from deltas**; cumulative counters alone do not prove a current incident. `vmstat`'s first line may represent averages since boot; use subsequent intervals.

## 4. Diagnose by evidence, not a single threshold

| Symptom | Distinguishing evidence | First investigation |
|---|---|---|
| CPU saturated | high busy %, high runnable pressure | hot processes, threads, code paths |
| High load, low CPU busy | blocked tasks, elevated I/O PSI, device latency | storage/backend wait |
| Pod latency with idle host | cgroup `nr_throttled` rising, CPU PSI | quota/limits, burst |
| One core pegged | per-core and per-thread CPU | single-thread bottleneck |
| Steal time | `st` in `vmstat`/`mpstat` | hypervisor contention |
| High system/softirq | kernel/interrupt CPU, network drops | packet rate, driver |
| Load rising after deployment | rollout and traffic correlation | code/config regression |

**Safety:** Never modify nice levels, CPU quotas, affinities, kernel scheduler settings or production workloads merely to test a hypothesis. Use staging and approved change management.

## 5. CPU utilization from kernel counters

```python
def cpu_busy_percent(before, after):
    # Both lists contain aggregate /proc/stat counters in Linux field order.
    if len(before) < 5 or len(after) < 5:
        raise ValueError("at least five CPU counters required")
    delta = [b - a for a, b in zip(before, after)]
    if any(x < 0 for x in delta):
        raise ValueError("counter reset or invalid sample")
    total = sum(delta)
    if total <= 0:
        raise ValueError("zero sample interval")
    idle = delta[3] + delta[4]
    return 100.0 * (total - idle) / total
```

On Linux, guest and guest_nice are already included in user/nice; for exact accounting avoid double-counting them. The lab below uses the first eight CPU fields and excludes guest counters.

## 6. Prometheus metrics and PromQL

Common node_exporter series (verify version and enabled collectors):

```promql
100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))
```

```promql
sum by (instance) (rate(node_cpu_seconds_total{mode="steal"}[5m]))
```

```promql
rate(node_pressure_cpu_waiting_seconds_total[5m])
```

CPU PSI metric naming/availability depends on node_exporter version and configuration. Verify with the live `/metrics` endpoint before creating alerts. For Kubernetes, compare container CPU usage with CFS throttling metrics from kubelet/cAdvisor; align denominators and scrape intervals. Couple saturation alerts to latency/error SLOs and explicit runbooks.

## 7. Executable synthetic CPU diagnostic lab

Create the following files:

```text
chapter007/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/cpu_diagnose.py
  tests/test_cpu_diagnose.py
```

### fixtures/healthy.json

```json
{"host":"staging-linux-01","owner":"platform-sre","logical_cpus":8,"load1":2.0,"cpu_busy_pct":38,"cpu_psi_some_pct":2,"io_psi_some_pct":1,"runnable_tasks":2,"blocked_tasks":0,"throttled_periods_delta":0,"periods_delta":1000,"steal_pct":0,"service_p95_ms":120,"service_budget_ms":300}
```

### fixtures/degraded.json

```json
{"host":"staging-linux-01","owner":"platform-sre","logical_cpus":8,"load1":18,"cpu_busy_pct":32,"cpu_psi_some_pct":4,"io_psi_some_pct":38,"runnable_tasks":3,"blocked_tasks":14,"throttled_periods_delta":250,"periods_delta":1000,"steal_pct":1,"service_p95_ms":2400,"service_budget_ms":300}
```

### scripts/cpu_diagnose.py

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

PERCENT = ("cpu_busy_pct", "cpu_psi_some_pct", "io_psi_some_pct", "steal_pct")
COUNTS = ("logical_cpus", "runnable_tasks", "blocked_tasks", "throttled_periods_delta", "periods_delta")

def diagnose(d):
    findings = []
    for name in ("host", "owner"):
        if not isinstance(d.get(name), str) or not d[name].strip():
            findings.append(f"missing {name}")
    for name in PERCENT:
        value = d.get(name)
        if type(value) not in (int, float) or not 0 <= value <= 100:
            findings.append(f"invalid {name}")
    for name in COUNTS:
        value = d.get(name)
        if type(value) is not int or value < (1 if name in ("logical_cpus", "periods_delta") else 0):
            findings.append(f"invalid {name}")
    for name in ("load1", "service_p95_ms", "service_budget_ms"):
        value = d.get(name)
        if type(value) not in (int, float) or value < 0 or (name == "service_budget_ms" and value == 0):
            findings.append(f"invalid {name}")
    if findings:
        return findings
    if d["throttled_periods_delta"] > d["periods_delta"]:
        return ["invalid throttling counters"]
    if d["cpu_busy_pct"] >= 90 and d["cpu_psi_some_pct"] >= 20:
        findings.append("CPU saturation with scheduler pressure")
    if d["load1"] > d["logical_cpus"] and d["blocked_tasks"] > 0 and d["io_psi_some_pct"] >= 20:
        findings.append("high load consistent with I/O-blocked tasks")
    if d["throttled_periods_delta"] / d["periods_delta"] >= 0.2:
        findings.append("cgroup throttling investigation required")
    if d["steal_pct"] >= 10:
        findings.append("hypervisor steal time elevated")
    if d["service_p95_ms"] > d["service_budget_ms"]:
        findings.append("user-facing latency budget exceeded")
    return findings

if __name__ == "__main__":
    findings = diagnose(json.loads(Path(sys.argv[1]).read_text()))
    print("CPU DIAGNOSTIC PASS: synthetic" if not findings else "CPU DIAGNOSTIC FINDINGS")
    for finding in findings:
        print("-", finding)
    sys.exit(bool(findings))
```

The validator is an educational triage aid, **not** an automated production remediation engine. A throttled-period fraction is not a throttled-time fraction and does not by itself prove user impact.

### tests/test_cpu_diagnose.py

```python
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from cpu_diagnose import diagnose

class CpuTests(unittest.TestCase):
    def fixture(self, name):
        return json.loads((ROOT / "fixtures" / name).read_text())

    def test_healthy(self):
        self.assertEqual(diagnose(self.fixture("healthy.json")), [])

    def test_degraded(self):
        self.assertTrue(diagnose(self.fixture("degraded.json")))

    def test_cpu_pressure(self):
        d = self.fixture("healthy.json")
        d["cpu_busy_pct"] = 95
        d["cpu_psi_some_pct"] = 35
        self.assertTrue(diagnose(d))

    def test_io_blocked_load(self):
        d = self.fixture("healthy.json")
        d.update(load1=20, blocked_tasks=12, io_psi_some_pct=35)
        self.assertTrue(diagnose(d))

    def test_throttling(self):
        d = self.fixture("healthy.json")
        d["throttled_periods_delta"] = 300
        self.assertTrue(diagnose(d))

    def test_steal(self):
        d = self.fixture("healthy.json")
        d["steal_pct"] = 20
        self.assertTrue(diagnose(d))

    def test_bad_percent(self):
        d = self.fixture("healthy.json")
        d["cpu_busy_pct"] = 110
        self.assertTrue(diagnose(d))

    def test_bad_periods(self):
        d = self.fixture("healthy.json")
        d["periods_delta"] = 0
        self.assertTrue(diagnose(d))

    def test_latency(self):
        d = self.fixture("healthy.json")
        d["service_p95_ms"] = 900
        self.assertTrue(diagnose(d))

    def test_missing_owner(self):
        d = self.fixture("healthy.json")
        d["owner"] = ""
        self.assertTrue(diagnose(d))

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 scripts/cpu_diagnose.py fixtures/healthy.json
if python3 scripts/cpu_diagnose.py fixtures/degraded.json; then
  echo "FAIL: degraded case accepted"; exit 1
else
  echo "PASS: degraded case detected"
fi
python3 -m unittest discover -s tests -v
```

## 8. Twenty-four hands-on exercises

1. Inventory kernel and CPU topology.
2. Explain scheduler classes and EEVDF/CFS version differences.
3. Capture load averages and runnable tasks.
4. Compare load average to logical CPU count.
5. Capture CPU utilization using counter deltas.
6. Inspect per-core CPU distribution.
7. Inspect per-thread CPU consumption.
8. Identify runnable versus blocked tasks.
9. Read CPU PSI `some`.
10. Read I/O PSI `some`.
11. Interpret `vmstat` run queue and blocked counts.
12. Identify CPU steal time.
13. Read cgroup `cpu.max`.
14. Read cgroup throttling counters.
15. Calculate throttled-period fraction from deltas.
16. Compare host and pod CPU signals.
17. Correlate disk latency and D-state tasks.
18. Define CPU pressure alert policy.
19. Define missing-data alert policy.
20. Create healthy synthetic fixture.
21. Create degraded synthetic fixture.
22. Run positive and negative checks.
23. Run ten automated tests.
24. Write incident RCA and mitigation decision.

## 9. Twenty production failure scenarios

| # | Failure | Investigation |
|---|---|---|
| 01 | Single hot Redis thread | per-thread CPU |
| 02 | High load, idle CPU | blocked I/O |
| 03 | High CPU and run queue | saturation |
| 04 | CPU quota throttling | cgroup counters |
| 05 | High steal time | hypervisor |
| 06 | High softirq | NIC packet load |
| 07 | High system CPU | kernel path |
| 08 | High user CPU | hot code |
| 09 | CPU PSI spike | scheduling |
| 10 | I/O PSI spike | storage |
| 11 | Thread affinity bottleneck | taskset/NUMA |
| 12 | CPU frequency throttling | thermal/power |
| 13 | Container CPU versus node mismatch | cgroups |
| 14 | Wrong `/proc/stat` delta | counter reset |
| 15 | Misread load average | semantics |
| 16 | Oversized CPU limits | cost/capacity |
| 17 | CPU alert without impact | SLO correlation |
| 18 | Missing PSI collector | scrape config |
| 19 | Sampling gap | monitoring health |
| 20 | Deployment CPU regression | release correlation |

## 10. Eight production runbooks

**A. CPU saturation:** Establish customer impact, sample per-core/per-thread CPU, runnable pressure, recent changes and safe traffic reduction.

**B. I/O-blocked high load:** Correlate blocked tasks, I/O PSI, device await/queue and cloud storage limits; avoid scaling CPU as first response.

**C. Cgroup throttling:** Verify quota, throttled-period/time deltas, burstiness and service latency; stage limit changes.

**D. Hypervisor steal:** Check steal trend, host type, cloud provider telemetry and workload placement.

**E. Single-thread hotspot:** Identify critical thread and command/query mix; reduce work per request and parallelize only when safe.

**F. Softirq/network pressure:** Correlate packet rate, interrupts, drops, socket backlog and driver behavior.

**G. Missing CPU telemetry:** Check exporter collectors, permissions, scraping, labels and missing-data alerts.

**H. Production CPU readiness:** Baseline under realistic load, define owners, SLO coupling, capacity headroom, rollback and evidence.

## 11. 100-point acceptance

| Domain | Points |
|---|---:|
| Scheduler theory and load interpretation | 20 |
| CPU/PSI/cgroup instrumentation | 20 |
| I/O and hypervisor differential diagnosis | 20 |
| Ten executable tests and negative cases | 20 |
| Runbooks, incident evidence and RCA | 20 |
| **Total** | **100** |

Recommended pass 85/100. Mandatory gates: explain load versus CPU utilization, collect read-only evidence, detect synthetic blocked-I/O and throttling scenarios, run ten tests and avoid unapproved production changes.

## 12. Evidence worksheet

```text
UTC / host / workload / owner:
Kernel / logical CPUs / cgroup mode:
Load / runnable / blocked:
CPU busy / per-core / PSI:
I/O PSI / disk await:
Throttling counters / period delta:
Steal / softirq:
Service p95 / error SLO:
Healthy and degraded fixtures:
Ten tests / negative drills:
RCA / COA / reviewer:
```

**Companion:** [Chapter 007 executable lab](labs/007-linux-cpu-scheduling-load-average-run-queues-performance-troubleshooting-lab.md).

**Next:** Chapter 008 — Linux Memory Management, Page Cache, Swap, PSI and OOM Troubleshooting.
