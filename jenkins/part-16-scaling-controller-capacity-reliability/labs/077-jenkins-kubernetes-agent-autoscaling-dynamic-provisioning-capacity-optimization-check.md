# Chapter 077 — Hands-on Lab: Kubernetes Agent Autoscaling and Capacity Optimization

**Environment:** Disposable Jenkins LTS and isolated Kubernetes test namespace/node pool, approved registry, test workload identity. No production load or disruptive node experiments.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Inventory Jenkins Kubernetes plugin/version | Baseline |
| 02 | Document pod and node scaling stages | Diagram |
| 03 | Inspect namespace ResourceQuota/LimitRange | Output |
| 04 | Create least-privilege synthetic agent identity | Manifest |
| 05 | Configure pinned agent image digest | Manifest |
| 06 | Run known-good ephemeral agent | Build |
| 07 | Measure pod creation and ready latency | Timeline |
| 08 | Record cold-start and warm-start p95 | Graph |
| 09 | Measure per-build CPU/RSS | Metrics |
| 10 | Calculate offered concurrency and slots | Worksheet |
| 11 | Generate bounded burst jobs | Timeline |
| 12 | Observe Pending/scheduling events | Events |
| 13 | Simulate incompatible node selector | Failure |
| 14 | Restore compatible node constraints | Recovery |
| 15 | Simulate lab image pull error | Failure |
| 16 | Restore valid pinned image | Recovery |
| 17 | Observe autoscaler/node provision events | Logs |
| 18 | Compare spot/on-demand risk and cost | Report |
| 19 | Verify queue drain and pod cleanup | Result |
| 20 | Sign off SLO/cost/rollback acceptance | Review |

## 12 failure drills

1. Kubernetes API RBAC denied.
2. Namespace quota exceeded.
3. Node affinity mismatch.
4. Missing toleration.
5. Autoscaler cloud quota.
6. ImagePullBackOff.
7. Slow image pull.
8. Agent remoting timeout.
9. Agent OOMKilled.
10. Node IP exhaustion.
11. Spot interruption simulation.
12. Orphaned agents/idle nodes.

## Example sizing calculator

```python
import math
jobs_per_hour = 90
mean_minutes = 10
planning_utilization = 0.70
cpu_per_job = 2
memory_gib_per_job = 3
offered = jobs_per_hour * mean_minutes / 60
slots = math.ceil(offered / planning_utilization)
print({"offered_concurrency": offered, "slots": slots,
       "cpu_requests": slots * cpu_per_job,
       "memory_gib_requests": slots * memory_gib_per_job})
```

Expected: 15 concurrent offered jobs, 22 slots, 44 requested vCPU and 66 GiB memory before cluster overhead. Not a node count or p95 guarantee.

## Commands

```sh
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl get resourcequota,limitrange -n jenkins-build
kubectl get nodes -o wide
```

## Evidence template

```text
UTC timestamp:
Jenkins Kubernetes plugin:
Pod template image digest:
Service account and workload identity:
Requests/limits/quota:
Queue p95 before/after:
Pod request-to-ready p95:
Node provisioning p95:
Autoscaler/cluster constraints:
Cost assumptions:
Fault injection and mitigation:
Recovery build and cleanup:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Least-privilege agent template verified.
- [ ] Cold and warm starts measured.
- [ ] Autoscaler limits understood.
- [ ] Queue SLO and capacity model validated.
- [ ] Cost and disruption risks documented.
- [ ] No secrets disclosed.
- [ ] Cleanup and rollback signed off.

**Related:** [Chapter 077 — Jenkins Kubernetes Agent Autoscaling, Dynamic Provisioning and Capacity Optimization](../077-jenkins-kubernetes-agent-autoscaling-dynamic-provisioning-capacity-optimization.md).
