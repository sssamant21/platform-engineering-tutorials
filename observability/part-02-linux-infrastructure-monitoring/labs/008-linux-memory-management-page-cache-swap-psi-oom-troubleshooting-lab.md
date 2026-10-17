# Chapter 008 — Hands-on Lab: Linux Memory, Cache, Swap, PSI and OOM

**Safety:** Read-only commands and synthetic Python data; no production changes or credentials. Requires Linux/WSL2 and Python 3.10+.

## 1. Collect host evidence

```bash
date -u
uname -r
free -h
grep -E '^(MemTotal|MemFree|MemAvailable|Cached|Buffers|SwapTotal|SwapFree|AnonPages|Slab):' /proc/meminfo
cat /proc/pressure/memory 2>/dev/null || true
vmstat 1 5
grep -E '^(pgmajfault|pswpin|pswpout|pgscan|pgsteal|oom_kill) ' /proc/vmstat
ps -eo pid,ppid,rss,vsz,stat,comm --sort=-rss | head -n 20
cat /sys/fs/cgroup/memory.current 2>/dev/null || true
cat /sys/fs/cgroup/memory.max 2>/dev/null || true
cat /sys/fs/cgroup/memory.high 2>/dev/null || true
cat /sys/fs/cgroup/memory.events 2>/dev/null || true
```

Capture UTC and whether you are inside a container. Missing metrics are not equivalent to healthy readings.

## 2. Build offline synthetic lab

Copy the four complete source blocks from [Chapter 008](../008-linux-memory-management-page-cache-swap-psi-oom-troubleshooting.md) into:

```text
chapter008/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/memory_gate.py
  tests/test_memory_gate.py
```

## 3. Execute checks

```bash
cd chapter008
python3 scripts/memory_gate.py fixtures/healthy.json
if python3 scripts/memory_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded memory accepted"; exit 1
else
  echo "PASS: degraded memory detected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy passes, degraded fails, 12 tests pass.

## 4. Twelve negative drills

1. Lower MemAvailable to 4%.
2. Increase memory PSI some to 35%.
3. Increase memory PSI full to 12%.
4. Increment OOM kills.
5. Increment memory.high events.
6. Increase swap-in activity.
7. Increase swap-out activity.
8. Increase major faults.
9. Increase service p95 beyond budget.
10. Remove owner.
11. Set page-cache percentage above 100.
12. Set OOM counter negative.

For each record the validator finding, likely real-world signal, containment and escalation owner.

## 5. DBRE tabletop

A MongoDB node reports high WiredTiger cache use, a Linux host has 4% MemAvailable, PSI some 38%, frequent major faults and disk latency spikes. Explain how to separate DB cache configuration, Linux reclaim, storage pressure and application impact. Do not force cache drops or restart without approval.

## 6. Evidence and acceptance

```text
UTC / operator / host:
Kernel / cgroup version:
MemAvailable / cache / RSS:
Swap activity / faults:
Memory PSI some/full:
memory.high/max/events:
OOM and service latency:
Healthy and degraded checks:
12 unit tests / 12 negative drills:
RCA / COA / reviewer:
```

- [ ] Host evidence collected read-only.
- [ ] Healthy fixture passes.
- [ ] Degraded fixture rejected.
- [ ] Twelve tests pass.
- [ ] DBRE cache/reclaim scenario documented.
- [ ] No claim of production validation based solely on synthetic tests.
