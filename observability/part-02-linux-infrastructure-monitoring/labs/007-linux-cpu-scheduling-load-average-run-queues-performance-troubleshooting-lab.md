# Chapter 007 — Hands-on Lab: Linux CPU Scheduling, Load and Run Queues

**Scope:** Read-only host investigation plus synthetic CPU diagnosis; no production mutation. Requires Linux/WSL2 and Python 3.10+.

## 1. Read-only inspection

```bash
date -u
uname -r
nproc
uptime
cat /proc/loadavg
cat /proc/pressure/cpu 2>/dev/null || true
cat /proc/pressure/io 2>/dev/null || true
vmstat 1 5
command -v mpstat >/dev/null && mpstat -P ALL 1 3 || true
command -v pidstat >/dev/null && pidstat -u -t 1 3 || true
command -v iostat >/dev/null && iostat -xz 1 3 || true
ps -eo pid,ppid,stat,ni,psr,pcpu,comm --sort=-pcpu | head -n 20
cat /sys/fs/cgroup/cpu.max 2>/dev/null || true
cat /sys/fs/cgroup/cpu.stat 2>/dev/null || true
```

Interpret differences between host and cgroup namespaces. Record missing tools and permissions.

## 2. Reproduce executable synthetic checks

Copy the four complete source blocks from [Chapter 007](../007-linux-cpu-scheduling-load-average-run-queues-performance-troubleshooting.md) into:

```text
chapter007/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/cpu_diagnose.py
  tests/test_cpu_diagnose.py
```

```bash
cd chapter007
python3 scripts/cpu_diagnose.py fixtures/healthy.json
if python3 scripts/cpu_diagnose.py fixtures/degraded.json; then
  echo "FAIL: degraded CPU case accepted"; exit 1
else
  echo "PASS: degraded CPU case detected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy fixture passes, degraded fixture fails, ten tests pass.

## 3. Twelve failure-injection drills

1. Increase CPU busy to 95% and CPU PSI to 35%.
2. Increase load1 to 20 with blocked tasks and I/O PSI.
3. Increase throttled periods to 300 of 1,000.
4. Increase steal time to 20%.
5. Increase service p95 beyond budget.
6. Remove owner.
7. Set CPU busy to 110%.
8. Set logical CPU count to zero.
9. Set period delta to zero.
10. Set blocked tasks to a negative value.
11. Set CPU PSI to an invalid negative value.
12. Set throttled periods above total periods.

Capture findings, hypotheses, operational mitigation and rollback/approval requirements for each.

## 4. Incident tabletop

Synthetic Elasticsearch search service shows load 18 on eight logical CPUs, CPU busy 32%, blocked tasks 14, I/O PSI 38% and search p95 2.4 seconds. Explain why load alone is not evidence of CPU saturation, how storage IOPS/throughput and disk latency should be investigated, and which changes need approval.

## 5. Evidence template

```text
UTC / operator / kernel:
Host or container namespace:
Load / CPU busy / runnable / blocked:
CPU PSI / I/O PSI:
Throttling / steal:
Service latency:
Positive and negative fixtures:
Ten tests:
Twelve drills:
Incident hypothesis / evidence / mitigation:
RCA / COA / reviewer:
```

**Acceptance:** all ten tests pass, unsafe synthetic cases are detected, host evidence is read-only and no production deployment is claimed.
