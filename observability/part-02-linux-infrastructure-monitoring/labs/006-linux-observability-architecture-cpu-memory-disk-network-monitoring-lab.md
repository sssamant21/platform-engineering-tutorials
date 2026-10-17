# Chapter 006 — Hands-on Lab: Linux CPU, Memory, Disk and Network Observability

**Safety:** Read-only Linux commands and offline synthetic Python checks. No production mutation. Commands may expose host metadata; store evidence securely.

## Environment

Linux VM, WSL2 or a Linux container with Python 3.10+. Some utilities are optional and container namespaces may hide host counters.

## Step 1 — Collect read-only evidence

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
command -v vmstat >/dev/null && vmstat 1 3 || true
command -v iostat >/dev/null && iostat -xz 1 3 || true
```

Record whether each command is supported. Do not interpret absent output as zero pressure.

## Step 2 — Prepare synthetic validator

Copy all four complete source blocks from [Chapter 006](../006-linux-observability-architecture-cpu-memory-disk-network-monitoring.md) into:

```text
chapter006/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/linux_health.py
  tests/test_linux_health.py
```

## Step 3 — Execute

```bash
cd chapter006
python3 scripts/linux_health.py fixtures/healthy.json
if python3 scripts/linux_health.py fixtures/degraded.json; then
  echo "FAIL: degraded host accepted"; exit 1
else
  echo "PASS: degraded host rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy exits zero, degraded nonzero, eight unit tests pass.

## Step 4 — Twelve failure drills

1. Set CPU utilization 95% and CPU PSI 30%.
2. Set memory available 2%.
3. Set memory PSI 35%.
4. Increase OOM kill delta.
5. Set filesystem utilization 96%.
6. Set inode utilization 98%.
7. Set disk await above latency budget.
8. Increase NIC errors.
9. Increase NIC drops.
10. Raise service p95 beyond budget.
11. Remove owner.
12. Set an impossible CPU utilization of 110%.

For each drill capture output, hypothesis, user impact and recommended runbook.

## Step 5 — Production tabletop

Synthetic incident: Elasticsearch search p95 rises above 3 seconds, disk await exceeds 50 ms, queue depth rises, and CPU remains moderate. Explain why storage saturation is plausible, which cloud metrics are needed, and why blindly increasing CPU may not resolve the problem.

## Evidence

```text
UTC / operator / host:
Read-only command output:
CPU load/utilization/PSI:
Memory/OOM:
Filesystem/inodes:
Device latency:
Network errors:
Synthetic positive/negative checks:
Eight unit tests:
12 failure drills:
Incident tabletop:
RCA / COA / reviewer:
```

- [ ] Read-only commands reviewed.
- [ ] Healthy fixture accepted.
- [ ] Degraded fixture rejected.
- [ ] Eight tests pass.
- [ ] CPU/load/PSI distinctions explained.
- [ ] Storage latency correlated with workload impact.
- [ ] No live production validation claimed from synthetic checks.
