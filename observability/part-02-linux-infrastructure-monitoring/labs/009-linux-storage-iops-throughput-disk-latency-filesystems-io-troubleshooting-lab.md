# Chapter 009 — Hands-on Lab: Linux Storage IOPS, Throughput, Latency and Filesystems

**Safety:** Read-only Linux inspection and synthetic Python tests. Never delete data, change mount options or resize volumes as part of this lab.

## 1. Read-only evidence

```bash
date -u
lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,ROTA
findmnt -T /
df -hT
df -i
cat /proc/pressure/io 2>/dev/null || true
command -v iostat >/dev/null && iostat -xz 1 5 || true
command -v pidstat >/dev/null && pidstat -d 1 5 || true
command -v vmstat >/dev/null && vmstat 1 5 || true
```

Capture host/device mapping and note unavailable utilities or container limitations.

## 2. Reproduce the synthetic gate

Copy the four complete source blocks from [Chapter 009](../009-linux-storage-iops-throughput-disk-latency-filesystems-io-troubleshooting.md) into:

```text
chapter009/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/storage_gate.py
  tests/test_storage_gate.py
```

```bash
cd chapter009
python3 scripts/storage_gate.py fixtures/healthy.json
if python3 scripts/storage_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded storage accepted"; exit 1
else
  echo "PASS: degraded storage rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy fixture passes, degraded fixture fails, twelve tests pass.

## 3. Twelve failure drills

1. Set filesystem usage to 97%.
2. Set inode usage to 95%.
3. Exceed provisioned IOPS.
4. Exceed throughput limit.
5. Increase read await.
6. Increase write await.
7. Increase I/O PSI.
8. Increment I/O errors.
9. Exceed service p95.
10. Remove owner.
11. Set invalid IOPS limit.
12. Set filesystem utilization above 100%.

For each, record finding, customer impact, root-cause hypothesis and safe response.

## 4. DBRE tabletop

Elasticsearch indexing latency rises while disk throughput hits the cloud volume limit, I/O PSI increases and merge pressure rises. Contrast this with a PostgreSQL checkpoint/WAL write burst and identify workload, filesystem and provider evidence needed before a change.

## 5. Evidence

```text
UTC / operator / host:
Mount and device:
Filesystem/inode utilization:
Read/write IOPS and MiB/s:
Read/write await and queue:
I/O PSI / errors:
Provisioned storage limits:
Positive and negative fixtures:
Twelve unit tests:
Twelve drills:
RCA / COA / reviewer:
```

**Acceptance:** read-only evidence, positive and negative synthetic checks, 12 tests and approved remediation plan. No production validation is claimed.
