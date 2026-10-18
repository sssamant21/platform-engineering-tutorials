# Chapter 066 — Python Debugging, Profiling and Diagnostics

**Part 07 — Testing, Debugging and Code Quality | Python 3.11+ | 7–9 hours**

## Learning objectives
Diagnose SRE/DBRE Python incidents with \`pdb\`, \`breakpoint()\`, \`traceback\`, \`faulthandler\`, \`cProfile\`, \`pstats\` and \`tracemalloc\`; distinguish CPU from I/O bottlenecks; capture safe evidence; test diagnostic paths; and build incident runbooks.

## 1. Debugging discipline
Start with a reproducible symptom, expected behavior, a synthetic fixture and an incident timeline. Record interpreter version, resource limits, process model and configuration *without collecting credentials*. Form a hypothesis, collect the smallest useful evidence, make one change and rerun regression tests. Avoid live production debugging when it can pause critical services.

## 2. pdb and breakpoint()
\`python -m pdb script.py\` starts interactive debugging. Commands: \`l\` list, \`n\` next, \`s\` step, \`c\` continue, \`p expression\` print, \`bt\` stack and \`q\` quit. \`breakpoint()\` invokes the configured debugger (normally pdb). It is safe in a disposable local lab but can block a production worker or reveal secrets; never leave unconditional breakpoints in deployed code. Set \`PYTHONBREAKPOINT=0\` to disable built-in breakpoint calls in controlled environments.

## 3. traceback and exception diagnostics
\`traceback.format_exception\` captures exception type, message and frames. Frames and exception messages can expose file paths, SQL, query parameters, tokens or customer data. Capture raw traces only in restricted local debugging or approved incident storage. User-facing reports should emit sanitized error categories and correlation IDs instead.

## 4. faulthandler
\`faulthandler.enable()\` enables traceback dumps for fatal Python faults. \`faulthandler.dump_traceback(file=...)\` captures thread stacks, and \`dump_traceback_later(timeout, repeat=False)\` can help diagnose hangs. Keep the target file open for the entire scheduled dump lifetime; call \`cancel_dump_traceback_later()\` in cleanup. Faulthandler output is low-level and may reveal paths, so store it in a protected location. It is not a substitute for OS crash dumps or native profilers.

## 5. cProfile and pstats
\`cProfile.Profile\` captures function-call statistics. Use \`pstats.Stats(profile).sort_stats("cumulative")\` for call chains or \`sort_stats("tottime")\` for time spent in each function itself. Profiling has overhead and can distort small workloads; measure a representative baseline and compare multiple runs. Call counts and profile paths may be sensitive.

## 6. tracemalloc and memory diagnostics
\`tracemalloc.start()\` tracks Python allocations; \`get_traced_memory()\` returns current and peak traced bytes. Snapshot diffs can identify allocation growth. \`tracemalloc\` does not represent total RSS, native extension allocations, mmap usage or all allocator fragmentation. Compare with OS/cgroup RSS metrics, GC activity and workload size. Ensure tracing is stopped only if your code started it.

## 7. Diagnostic architecture
\`\`\`text
synthetic PostgreSQL / Elasticsearch / Kafka telemetry
  -> strict input validation
  -> deterministic classifier
  -> exception classification + sanitized JSON
  -> cProfile / pstats function timings
  -> tracemalloc Python allocation measurements
  -> optional local pdb / traceback / faulthandler
  -> incident runbooks and regression tests
\`\`\`

| Engine | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag seconds | 30 | 120 |
| Elasticsearch | search_latency milliseconds | 200 | 500 |
| Kafka | consumer_lag messages | 1,000 | 10,000 |

All telemetry and thresholds are synthetic, not production SLO recommendations.

## 8. Performance and production safety
Do not enable verbose tracing on all production requests by default. Prefer bounded sampling, short profiling windows, restricted artifacts and explicit incident approval. Profile CPU, wall time, I/O wait and memory separately. If a process is unresponsive, inspect event-loop stalls, thread stacks, deadlocks and downstream service latency before increasing capacity. Use noninteractive tools on production hosts whenever possible.

## 9. Troubleshooting
| Symptom | Likely cause | Remedy |
|---|---|---|
| pdb blocks worker | Interactive breakpoint | Remove breakpoint, restart safely |
| Traceback leaks secrets | Unredacted exception | Sanitize logs and rotate exposed secrets |
| Profile results unstable | Small sample / warmup | Repeat representative workloads |
| cProfile shows high cumulative time | Downstream call chain | Inspect callees and I/O |
| tracemalloc flat but RSS rising | Native memory / fragmentation | Inspect OS/cgroup and native allocators |
| faulthandler dump missing | File closed or timer canceled | Keep descriptor open; verify schedule |
| Intermittent hang | Lock, queue, I/O timeout | Capture stacks and add bounded deadlines |
| Profiling slows service | Instrumentation overhead | Sample and reduce collection window |

## 10. Production runbooks
**CPU saturation:** capture short CPU profile, compare cumulative vs total time, inspect hot paths, revert regressions and validate latency.

**Memory growth:** compare tracemalloc snapshots with RSS/cgroup metrics, isolate leak, cap workload and roll back.

**Hung process:** collect protected faulthandler stacks, inspect deadlocks and external I/O, recover using approved restart procedure.

**Sensitive trace exposure:** restrict access, remove leaked artifacts, rotate affected credentials and document incident.

**Rollback:** restore known-good implementation, rerun automated tests, compare baselines and close incident with evidence.

## 11. Lab
[Chapter 066 — Python Debugging and Profiling SRE/DBRE Lab](labs/066-debugging-profiling-diagnostics-sre-dbre-lab.md) provides complete executable source, automated tests, incident simulations, diagnostic commands, runbooks and a 100-point assessment.

**Next:** Chapter 067 — Python Logging, Structured Diagnostics and Observability Testing (provisional).
