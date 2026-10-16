# Chapter 050 — Hands-on Capstone: Jenkins on Kubernetes, EKS and AKS

**Environment:** Disposable Kubernetes controller/agents; optional separate nonproduction EKS and AKS clusters with narrowly scoped cloud identities. Destructive exercises must never target shared production.

## 20 capstone exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Architecture | Diagram controller/agent/cloud trust | Diagram |
| 02 | Ownership | Define RACI and runbooks | Matrix |
| 03 | Controller | Record chart/core/plugin versions | Inventory |
| 04 | Persistence | Validate JENKINS_HOME PVC | PVC |
| 05 | Provisioner | Verify namespaced Pod RBAC | `can-i` |
| 06 | Build SA | Verify no Secret/Pod rights | Denied |
| 07 | Agent template | Define nonroot secure tool container | YAML |
| 08 | Effective Pod | Inspect injected inbound-agent spec | Evidence |
| 09 | Smoke | Execute dynamic Jenkins Pipeline | Build |
| 10 | Artifacts | Archive test evidence before cleanup | Artifact |
| 11 | Cleanup | Confirm ephemeral Pod removal | Event |
| 12 | EKS identity | Verify IRSA/Pod Identity in test Pod | STS role |
| 13 | EKS negative | Confirm denied unauthorized AWS action | Denied |
| 14 | AKS identity | Verify federated workload ID in Pod | Azure identity |
| 15 | AKS negative | Confirm denied unauthorized Azure action | Denied |
| 16 | Autoscaling | Run bounded agent burst | Queue/node metrics |
| 17 | Failure injection | Exercise selected safe faults | Logs |
| 18 | Restore | Restore isolated test controller | RTO/RPO |
| 19 | FinOps | Estimate cost per build and pool waste | Baseline |
| 20 | Acceptance | Score 100-point review and sign off | Report |

If EKS/AKS is unavailable, record cloud-specific items as blocked rather than inventing evidence or weakening requirements.

## 20 troubleshooting drills

1. Controller Pod not Ready.
2. JENKINS_HOME PVC Pending.
3. Kubernetes provisioner Role denied.
4. Build SA unexpectedly can list Secrets.
5. Pod Security admission rejects agent.
6. ImagePullBackOff.
7. Agent remoting connection timeout.
8. Pod Pending due to quota.
9. Node affinity mismatch.
10. OOMKilled.
11. Evicted by node pressure.
12. EKS IRSA trust mismatch.
13. EKS Pod Identity Agent unavailable.
14. ECR permission denied.
15. AKS workload identity label missing.
16. AKS federated subject mismatch.
17. ACR permission denied.
18. Autoscaler capacity limit reached.
19. Controller backup consistency failure.
20. Plugin upgrade incompatibility.

## Lab baseline

```sh
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl get resourcequota,limitrange -n jenkins-build
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl auth can-i create pods -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
```

Both build-SA `can-i` checks should return `no` in the standard lab. Confirm the separate provisioner identity has only required Pod lifecycle rights.

## Evidence template

```text
UTC timestamp:
Cluster / provider / version:
Jenkins core / chart / plugin versions:
Controller PVC and backup ID:
Provisioner and build SA:
Effective agent Pod YAML:
Agent build and artifact URL:
Queue p95 / Pod startup p95:
EKS identity positive/negative:
AKS identity positive/negative:
Node pool/autoscaler:
Fault drill / symptoms / root cause:
Restore RTO/RPO:
Estimated cost per build:
Score / residual risks / reviewer:
```

## 100-point scorecard

| Category | Max |
|---|---:|
| Architecture/trust | 10 |
| Controller backup/restore | 15 |
| Kubernetes RBAC/agent security | 15 |
| EKS identity | 10 |
| AKS identity | 10 |
| Autoscaling/capacity | 10 |
| Observability/SLOs | 10 |
| Failure injection | 15 |
| FinOps/handover | 5 |
| **Total** | **100** |

Suggested pass: 85 points plus mandatory security and recovery gates. Missing cloud exercises are **not tested**, not passed.

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 20 troubleshooting drills completed or explicitly blocked.
- [ ] Controller state and backup restored in isolation.
- [ ] Dynamic agent test and cleanup successful.
- [ ] Kubernetes build SA has no excess rights.
- [ ] AWS and Azure identities independently verified if available.
- [ ] Unauthorized cloud actions denied.
- [ ] Autoscaling and cost baselines captured.
- [ ] SLO dashboard and incident runbooks reviewed.
- [ ] Reviewer approves residual risks and score.

**Related:** [Chapter 050 — Jenkins on Kubernetes, EKS and AKS Production Operations Capstone](../050-jenkins-kubernetes-eks-aks-production-operations-capstone.md).
