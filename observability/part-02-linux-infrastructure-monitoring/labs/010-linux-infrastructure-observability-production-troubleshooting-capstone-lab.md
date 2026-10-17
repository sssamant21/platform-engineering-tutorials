# Chapter 010 — Linux Infrastructure Observability Production Capstone Lab

**Part 02 final assessment.** This lab is read-only on real Linux hosts and uses synthetic fixtures for failure simulation. Requires Python 3.10+.

## 1. Evidence collection

```bash
date -u
uname -r
uptime
vmstat 1 5
free -h
df -hT
df -i
ip -s link
ss -s
cat /proc/pressure/cpu 2>/dev/null || true
cat /proc/pressure/memory 2>/dev/null || true
cat /proc/pressure/io 2>/dev/null || true
command -v iostat >/dev/null && iostat -xz 1 3 || true
```

Do not infer zero pressure from unsupported or missing data. Capture timestamps, namespaces, host identity and service ownership.

## 2. Build runnable synthetic project

Copy the complete code and fixture blocks from [Chapter 010](../010-linux-infrastructure-observability-production-troubleshooting-capstone.md) into:

```text
chapter010/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/infra_gate.py
  tests/test_infra_gate.py
```

```bash
cd chapter010
python3 scripts/infra_gate.py fixtures/healthy.json
if python3 scripts/infra_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded infrastructure accepted"; exit 1
else
  echo "PASS: degraded infrastructure rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy accepted, degraded rejected, 14 automated tests pass.

## 3. Twelve targeted failure drills

1. CPU busy 95% and CPU PSI 35%.
2. Load per CPU 3 with I/O PSI 38%.
3. MemAvailable 4%.
4. Memory PSI 40%.
5. OOM delta 2.
6. Filesystem 97%.
7. Inodes 95%.
8. Disk await 80 ms.
9. NIC errors 25.
10. Network drops 500.
11. Service p95 2600 ms.
12. Telemetry age 150 seconds.

For each, record expected detection, diagnostic next step, escalation and safe mitigation.

## 4. Integrated incident simulation

Elasticsearch API latency increases during heavy indexing. Device await and I/O PSI increase; CPU remains below saturation. At the same time the node exporter disappears. Build a timeline with service traces, cloud disk metrics, database merge stats and independent exporter health. Explain what is known, what remains uncertain and how to verify recovery.

## 5. Evidence package

```text
UTC / operator / incident:
Host and workload ownership:
CPU / memory / storage / network observations:
Service p95 / errors / customer impact:
Telemetry freshness and missing-data behavior:
Healthy/degraded checks:
14 unit tests:
12 failure drills:
RCA / COA / approvals:
Score out of 100 / reviewer:
```

- [ ] Read-only commands only.
- [ ] Positive and negative synthetic checks executed.
- [ ] Fourteen tests pass.
- [ ] Twelve drills documented.
- [ ] Incident tabletop reviewed.
- [ ] No production certification claimed without actual staging/production evidence.
