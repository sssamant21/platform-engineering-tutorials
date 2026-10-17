# Chapter 080 — Hands-on Capstone: Jenkins Scaling, HA and Reliability Acceptance

**Environment:** Disposable Jenkins LTS, test SCM/artifact registry, isolated Kubernetes agent pools, Prometheus/Grafana, synthetic credentials and separate backup/restore volume. Do not run load tests or fault injection in production.

## 24 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory controller, plugins, Java and JCasC | Manifest |
| 02 | Verify single-writer Jenkins home | Architecture |
| 03 | Document trusted/untrusted zones | Trust matrix |
| 04 | Test synthetic credential isolation | Negative test |
| 05 | Create synthetic end-to-end CI Pipeline | Build |
| 06 | Record external availability and queue p95 | Dashboard |
| 07 | Measure agent startup p95 | Timeline |
| 08 | Record controller CPU, GC and storage | Metrics |
| 09 | Measure jobs/hour and duration distribution | Dataset |
| 10 | Calculate offered concurrency and slots | Worksheet |
| 11 | Validate per-build CPU/memory requests | Metrics |
| 12 | Run bounded steady-state load | Report |
| 13 | Run bounded burst and measure queue | Graph |
| 14 | Inject incompatible agent label | Failure |
| 15 | Restore label and measure queue drain | Recovery |
| 16 | Simulate pod Pending in test namespace | Events |
| 17 | Observe autoscaler node provisioning | Timeline |
| 18 | Simulate isolated agent node failure | Recovery |
| 19 | Stop and recover test controller | Timeline |
| 20 | Inject and roll back test JCasC regression | Git evidence |
| 21 | Restore backup into separate volume/namespace | Restore |
| 22 | Measure RTO/RPO and artifact integrity | Validation |
| 23 | Simulate SCM/registry outage with bounded retry | Logs |
| 24 | Complete scorecard, RCA/COA and handover | Sign-off |

## 16 failure drills

1. Controller CPU saturation.
2. JVM GC pressure.
3. Jenkins home I/O bottleneck.
4. Queue backlog.
5. Long-running job starvation.
6. Agent pod Pending.
7. Autoscaler delay.
8. Cloud quota.
9. ImagePullBackOff.
10. Agent remoting failure.
11. Agent node loss.
12. Network/DNS failure.
13. Plugin/JCasC regression.
14. Controller crash.
15. Backup restore integrity failure.
16. SCM/artifact registry outage.

## Executable capacity calculator

```python
import math

jobs_per_hour = 150
mean_minutes = 8
planning_utilization = 0.70
cpu_per_job = 1
memory_gib_per_job = 2

offered = jobs_per_hour * mean_minutes / 60
slots = math.ceil(offered / planning_utilization)
print(f"Offered concurrency: {offered:.1f}")
print(f"Illustrative compatible slots: {slots}")
print(f"Requested CPU: {slots * cpu_per_job} vCPU")
print(f"Requested memory: {slots * memory_gib_per_job} GiB")
```

Expected: 20 offered concurrent jobs, 29 compatible slots, 29 vCPU and 58 GiB requests, excluding node overhead. This is not an SLO guarantee or node count.

## Diagnostic commands

```sh
kubectl get pods -n jenkins -o wide
kubectl get events -n jenkins --sort-by=.lastTimestamp
kubectl get pods -n jenkins-build -o wide
kubectl get nodes -o wide
kubectl get pvc -n jenkins
```

## 100-point scorecard

| Category | Maximum |
|---|---:|
| Architecture, failure domains and isolation | 15 |
| Controller/executor capacity | 15 |
| Kubernetes autoscaling/queue recovery | 15 |
| Controller recovery | 15 |
| Backup restore/RTO/RPO | 15 |
| SLO/error-budget observability | 10 |
| FinOps/dependencies/rollback | 10 |
| RCA/COA and sign-off | 5 |
| **Total** | **100** |

Suggested pass 85 plus mandatory gates from Chapter 080.

## Evidence template

```text
UTC / owner / change approval:
Controller versions and Git SHA:
Single-writer verification:
Trusted/untrusted negative access tests:
Load profile and capacity model:
Queue/agent p95 baseline and recovery:
Fault injection / rollback:
Controller recovery and synthetic CI:
Isolated restore integrity / RTO / RPO:
SLO and error budget:
Cost and cloud quota:
Score / residual risks / COA:
Reviewer:
```

## Acceptance checklist

- [ ] 24 exercises attempted with evidence.
- [ ] 16 drills completed or explicitly blocked.
- [ ] Single active controller writer verified.
- [ ] Trust isolation positive and negative tests pass.
- [ ] Queue/autoscaling recovery measured.
- [ ] Controller and isolated backup restore validated.
- [ ] RTO/RPO, SLO and cost recorded.
- [ ] No secrets exposed or production disrupted.
- [ ] Scorecard and sign-off complete.

**Related:** [Chapter 080 — Jenkins Scaling, High Availability and Reliability Acceptance Capstone](../080-jenkins-scaling-high-availability-reliability-acceptance-capstone.md).
