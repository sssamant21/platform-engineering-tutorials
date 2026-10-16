# Chapter 052 — Hands-on Lab: Rolling, Blue-Green and Canary Deployments

**Environment:** Disposable Kubernetes cluster, Jenkins trusted release agent, Helm, kubectl and a synthetic HTTP service. Optional approved canary routing controller.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record K8s/Helm/Jenkins versions | Baseline |
| 02 | Architecture | Map traffic and release ownership | Diagram |
| 03 | Digest | Verify immutable image digest | Digest |
| 04 | Rolling config | Set maxSurge/maxUnavailable | Manifest |
| 05 | Rolling deploy | Deploy known-good revision | Rollout |
| 06 | Readiness | Verify health probe behavior | Events |
| 07 | Rolling upgrade | Deploy candidate revision | History |
| 08 | Rolling rollback | Restore previous revision | Recovery |
| 09 | Blue deploy | Deploy stable track | Pods |
| 10 | Green deploy | Deploy candidate track | Pods |
| 11 | Preview | Test green through preview Service | HTTP |
| 12 | Cutover | Switch lab Service selector | EndpointSlices |
| 13 | Blue rollback | Restore selector to blue | HTTP |
| 14 | Capacity | Compare rolling/blue-green requests | Model |
| 15 | Canary design | Select supported routing controller | Decision |
| 16 | Canary weight | Test 5% if controller installed | Metrics |
| 17 | SLO gate | Simulate regression and halt | Decision |
| 18 | Metrics loss | Fail closed on missing data | Evidence |
| 19 | Schema safety | Document expand/contract plan | Review |
| 20 | Acceptance | Review strategy tradeoffs | Sign-off |

## 12 troubleshooting drills

1. Rolling Pod readiness failure.
2. maxSurge capacity shortage.
3. PodDisruptionBudget conflict.
4. Blue-green Service selector mismatch.
5. Green preview Service not reachable.
6. Existing connections remain on blue.
7. Canary controller absent.
8. Canary traffic weights ineffective.
9. Canary insufficient request sample.
10. SLO regression.
11. Metrics backend unavailable.
12. Helm/GitOps competing reconciliation.

For canary exercises without a supported routing controller, record **blocked**, not passed. Do not pretend Kubernetes Service selectors support weighted traffic.

## Commands

```sh
kubectl rollout status deployment/sample-app -n jenkins-staging --timeout=5m
kubectl rollout history deployment/sample-app -n jenkins-staging
kubectl get endpointslices -n jenkins-staging \
  -l kubernetes.io/service-name=sample-app
kubectl get events -n jenkins-staging --sort-by=.lastTimestamp
helm history sample-app -n jenkins-staging
```

Only use `kubectl rollout undo` for kubectl-managed Deployments; use `helm rollback` for Helm-managed releases and Git revert/reconcile for GitOps-managed releases.

## Evidence template

```text
UTC timestamp:
Kubernetes/Helm/Jenkins versions:
Image digests:
Release strategy and owner:
Rolling revision / readiness:
Blue and green Pod versions:
Preview test:
Cutover and rollback:
Canary controller/traffic weights:
SLO query and sample count:
Injected fault:
Recovery time and result:
Capacity and cost:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Rolling upgrade/rollback successful.
- [ ] Blue-green cutover/rollback successful.
- [ ] Canary validated with real controller or marked blocked.
- [ ] SLO gate halts on regression or missing metrics.
- [ ] No mutable tags or secret exposure.
- [ ] One release/routing owner documented.
- [ ] Reviewer signs off.

**Related:** [Chapter 052 — Jenkins Kubernetes Deployment Strategies](../052-jenkins-kubernetes-deployment-strategies-rolling-blue-green-canary.md).
