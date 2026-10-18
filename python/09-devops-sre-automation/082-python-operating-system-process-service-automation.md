# Chapter 082 — Python Operating System, Process and Service Automation

**Part 09 — DevOps, SRE and Automation | Python 3.11+ | SRE/DevOps/DBRE**

## Outcomes
Automate operating-system inventory and service health checks using \`pathlib\`, \`os\`, \`shutil\`, \`subprocess\` and \`psutil\`. Safely manage process lifecycle, monitor CPU/memory/disk, implement bounded timeouts and cleanup, and build portable SRE runbooks. The lab operates on a disposable local workspace and a child process it launches itself; it never controls arbitrary system services.

## Architecture
\`\`\`text
operator/CI -> Python CLI -> policy and workspace validation
  -> psutil inventory -> process lifecycle / health probe
  -> bounded subprocess -> JSON report -> alerts/runbook
  -> dry-run / explicit mutation approval
\`\`\`

## 1. Filesystem automation
\`pathlib.Path\` provides portable path operations, \`os\` exposes environment and process interfaces, and \`shutil\` handles high-level file operations. Treat paths as untrusted: normalize and constrain them to an approved workspace, reject symlink escapes and never recursively delete an arbitrary user-supplied path. \`Path.resolve()\` and preflight checks alone are not sufficient against concurrent symlink replacement; production security-sensitive operations need descriptor-relative APIs or dedicated sandboxing. Use \`tempfile\` for disposable data and \`os.replace\` for atomic same-filesystem replacement. For crash durability, flush and fsync data and consider directory fsync where supported.

## 2. Processes and subprocess
\`subprocess.Popen\` starts a child and exposes \`poll()\`, \`wait()\`, \`terminate()\` and \`kill()\`. Use argument arrays with \`shell=False\`, fixed allowlisted executables, and explicit timeouts. A process exit code of zero does not prove service health. Never send signals to an arbitrary PID supplied by a caller: PIDs can be reused and ownership may be unclear. Only terminate processes your automation created and retained a handle to. On timeout, terminate, wait a grace period, then kill if necessary. Descendant cleanup requires OS-specific process-group or job-object design.

## 3. psutil resource monitoring
\`psutil.Process(pid)\` can inspect RSS, CPU, status and create time; \`psutil.virtual_memory()\`, \`psutil.disk_usage()\`, and \`psutil.cpu_percent()\` provide host signals. CPU percent is sampling-dependent; a first nonblocking sample may be zero or unrepresentative. Container metrics and host metrics differ; for Kubernetes, consult cgroup and pod limits rather than assuming host memory equals allocatable memory. Catch \`NoSuchProcess\`, \`AccessDenied\`, and \`ZombieProcess\` as appropriate. Do not enumerate or log other tenants' command lines.

## 4. Service health
Separate liveness (process exists), readiness (can serve requests), and dependency health (database, Kafka, Elasticsearch, Redis, DNS). A running PID is not proof of readiness. Use synthetic probes with finite deadlines and clear failure classification. The lab checks a synthetic child process and its exit status; production readiness should probe an authenticated, approved service endpoint or native service manager.

## 5. Cross-platform service operations
Linux \`systemd\`, Windows Service Control Manager and Kubernetes controllers have different lifecycle semantics. Prefer official APIs and least-privilege roles. Do not assume \`systemctl\` exists in containers or Windows. For managed cloud services, use provider APIs and change windows. Restart loops can amplify outages; apply backoff and escalation thresholds.

## 6. Disk and capacity
\`shutil.disk_usage(path)\` reports filesystem totals and free bytes, not cloud storage IOPS or quota. Track growth rates, inode pressure on Linux, mount-specific metrics, temp files, open file descriptors and deleted-but-open files. Avoid cleaning directories without owner approval and retention validation. For DBRE, consider PostgreSQL WAL, MongoDB WiredTiger, Elasticsearch shard storage and Kafka log segments separately.

## 7. Operational security
Run with least privilege; never use root/admin by default. Avoid logging environment variables or raw process arguments because they may contain secrets. Use bounded file sizes, redaction, secure temporary paths and approval gates for mutations. Distinguish read-only inventory from service changes.

## 8. Incident simulations
1. Process exits unexpectedly.
2. Process ignores graceful shutdown.
3. Process times out during execution.
4. Nonzero exit code.
5. Executable missing.
6. PID reused after process exit.
7. Access denied to process metrics.
8. CPU spike.
9. Memory RSS growth.
10. Disk space below threshold.
11. Disk full during atomic write.
12. Symlink traversal attempt.
13. Readiness failure with PID alive.
14. Dependency failure despite healthy service.
15. Container memory limit lower than host memory.
16. Service restart storm.
17. Zombie process.
18. Orphan child/descendant process.
19. Secret leakage in command-line arguments.
20. Unapproved directory cleanup.

## 9. Troubleshooting matrix
| Symptom | Signal | Action |
|---|---|---|
| High CPU | psutil CPU trend | Profile workload and compare cgroup limits |
| High RSS | process.memory_info().rss | Inspect leaks, heap/cache, OOM events |
| Disk pressure | disk_usage, inodes, IOPS | Identify owner and approved retention action |
| Hung child | poll() is None after deadline | Graceful terminate then bounded kill |
| Readiness false | Probe timeout/response | Check dependency and application logs |
| PID disappeared | NoSuchProcess | Reconcile lifecycle; avoid PID-based signals |
| Permission denied | AccessDenied | Use approved identity, no privilege bypass |
| Restart loop | Frequent exit/restart | Stop automation loop and escalate |

## 10. Runbooks
**High CPU:** capture baseline, host/container limits and process ownership; identify expensive work and mitigate through approved throttling.

**Memory pressure:** measure RSS and cgroup pressure, inspect OOM events, reduce concurrency and validate recovery.

**Disk pressure:** locate affected mount and service data, preserve backups, coordinate retention cleanup with owners.

**Hung process:** verify ownership of child handle, send terminate, wait grace period, kill only that child if necessary and collect exit evidence.

**Failed service health:** distinguish liveness/readiness/dependency failure, validate configuration and rollback only through approved change.

## 11. Lab and assessment
[Chapter 082 — OS, Process and Service Automation SRE/DevOps/DBRE Lab](labs/082-os-process-service-automation-sre-devops-dbre-lab.md) includes complete executable source, psutil inventory, safe filesystem operations, child process lifecycle and timeout handling, automated tests, incident exercises, runbooks and a 100-point assessment.

**Next proposed:** Chapter 083 — Python Scheduling, Background Jobs and Reliable Task Automation.
