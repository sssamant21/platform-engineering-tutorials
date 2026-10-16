# Chapter 069 — Hands-on Lab: Jenkins Controller, JVM, Queue and Agent Performance

**Environment:** Disposable Jenkins LTS, Prometheus/Grafana, JDK diagnostic tools, synthetic Pipelines and optional Kubernetes agents. No production load testing.

## 20 exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Record core/Java/plugin/agent baseline | Inventory |
| 02 | Diagram controller and agent performance flow | Diagram |
| 03 | Capture controller CPU | Graph |
| 04 | Measure heap and post-GC trend | Graph |
| 05 | Measure GC pause rate/distribution | Report |
| 06 | Capture protected thread dump | Diagnostic |
| 07 | Measure Jenkins home latency and capacity | Report |
| 08 | Generate bounded synthetic queue | Graph |
| 09 | Calculate queue wait p95 | Result |
| 10 | Compare executor utilization by label | Table |
| 11 | Inject lab label mismatch | Queue reason |
| 12 | Test controlled lock/concurrency bottleneck | Result |
| 13 | Measure agent provisioning p95 | Graph |
| 14 | Inspect Kubernetes pod events/limits | Evidence |
| 15 | Reduce lab agent capacity | Impact |
| 16 | Increase bounded arrival rate | Throughput curve |
| 17 | Isolate dominant latency component | RCA |
| 18 | Restore capacity/constraints | Change |
| 19 | Compare before/after queue and throughput | Recovery |
| 20 | Complete acceptance and reviewer sign-off | Report |

## 12 failure drills

1. Controller CPU saturation.
2. JVM heap pressure.
3. Long GC pauses.
4. Blocked threads.
5. Jenkins home I/O latency.
6. Disk capacity exhaustion.
7. Queue starvation.
8. Idle executors with queued jobs.
9. Label mismatch.
10. Kubernetes pod Pending.
11. Agent OOMKilled or remoting disconnect.
12. Plugin upgrade performance regression.

## Diagnostic commands

```sh
jcmd <PID> GC.heap_info
jcmd <PID> Thread.print -l > thread-dump.txt
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
```

Use actual PID, namespace and lab pod. Restrict diagnostic output.

## Evidence worksheet

```text
UTC timestamp:
Jenkins/Java/plugins:
CPU/heap/GC:
Thread sample findings:
Jenkins home I/O:
Queue p50/p95/p99:
Executor utilization by label:
Agent provisioning p95:
Synthetic load and stop condition:
Injected failure:
Root cause:
Before/after metrics:
Recovery duration:
Reviewer:
```

## Acceptance

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Baseline and peak conditions measured.
- [ ] Controller versus agent bottleneck distinguished.
- [ ] Load test isolated and bounded.
- [ ] Recovery verified.
- [ ] No secrets in diagnostics.
- [ ] Reviewer signed off.

**Related:** [Chapter 069 — Jenkins Controller, JVM, Queue and Agent Performance Analysis](../069-jenkins-controller-jvm-queue-agent-performance-analysis.md).
