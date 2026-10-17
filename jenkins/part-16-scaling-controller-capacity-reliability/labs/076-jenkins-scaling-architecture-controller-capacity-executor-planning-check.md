# Chapter 076 — Hands-on Lab: Jenkins Controller Capacity and Executor Planning

**Environment:** Disposable Jenkins LTS, Prometheus/Grafana, isolated synthetic jobs and optional Kubernetes agents. No load testing on production controllers.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory controller/Java/plugins | Baseline |
| 02 | Record controller CPU and heap | Dashboard |
| 03 | Record Jenkins home I/O and capacity | Metrics |
| 04 | Inventory agent labels and executors | Matrix |
| 05 | Create synthetic short job | Build |
| 06 | Create synthetic long job | Build |
| 07 | Measure arrival rate and duration | Worksheet |
| 08 | Calculate offered concurrency | Formula |
| 09 | Size slots at stated utilization | Calculation |
| 10 | Validate CPU/memory per build | Metrics |
| 11 | Measure baseline queue p95 | Graph |
| 12 | Generate bounded burst workload | Timeline |
| 13 | Observe queue saturation | Evidence |
| 14 | Inject lab label mismatch | Queue reason |
| 15 | Correct compatible labels | Recovery |
| 16 | Measure Kubernetes agent startup p95 | Graph |
| 17 | Simulate reduced compatible agent pool | Result |
| 18 | Restore pool and measure queue drain | Graph |
| 19 | Document capacity forecast and cost | Plan |
| 20 | Complete change/rollback acceptance | Sign-off |

## 12 failure drills

1. Queue backlog with idle executors.
2. Executor pool saturation.
3. Controller CPU throttling.
4. JVM GC pressure.
5. Jenkins home storage latency.
6. Agent pod Pending.
7. Cluster autoscaler delay.
8. Image pull bottleneck.
9. Cloud quota limit.
10. Retry storm.
11. Long-running job starvation.
12. Agent overcommit.

## Example sizing calculation

```python
import math

arrival_per_hour = 120
mean_minutes = 8
planning_utilization = 0.70

offered_concurrency = arrival_per_hour * mean_minutes / 60
planned_slots = math.ceil(offered_concurrency / planning_utilization)
print(f"Offered concurrency: {offered_concurrency:.1f}")
print(f"Illustrative compatible slots: {planned_slots}")
```

Expected: offered concurrency 16.0; planned slots 23. This is a starting estimate, not a p95 SLA guarantee.

## Evidence template

```text
UTC timestamp:
Controller core/Java/plugins:
Workload classes and labels:
Arrival rates / mean and p95 durations:
Per-build CPU/RSS/I/O:
Offered concurrency:
Utilization assumption:
Planned compatible executors:
Controller CPU/GC/storage:
Queue p95 before/after:
Agent provisioning p95:
Peak burst and abort threshold:
Cloud/node constraints and cost:
Rollback:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Capacity model assumptions documented.
- [ ] Queue and agent latency measured.
- [ ] Controller protected from builds.
- [ ] Workload burst recovered.
- [ ] Cost and cloud constraints assessed.
- [ ] No shared writable controller home.
- [ ] SLO and rollback approved.

**Related:** [Chapter 076 — Jenkins Scaling Architecture, Controller Capacity and Executor Planning](../076-jenkins-scaling-architecture-controller-capacity-executor-planning.md).
