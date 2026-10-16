# Chapter 054 — Hands-on Lab: GitOps Promotion, Drift and Policy

**Environment:** Disposable Kubernetes cluster, Jenkins, Argo CD or Flux, protected environment Git repository, Conftest/OPA and optional Kyverno/Gatekeeper. Use synthetic applications and test identities.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record tool versions | Baseline |
| 02 | Trust map | Define CI/Git/GitOps ownership | Diagram |
| 03 | Environment repo | Create staging/production overlays | Tree |
| 04 | Digest | Pin verified staging image | YAML |
| 05 | Jenkins CI | Build/test/scan artifact | Build |
| 06 | Signature | Verify approved signer | Evidence |
| 07 | Rego policy | Require digest-pinned images | Policy |
| 08 | Negative policy | Reject mutable tag | Failure |
| 09 | Security policy | Reject privileged Pod | Failure |
| 10 | Render | Validate staging overlay | YAML |
| 11 | Staging PR | Propose digest update | PR |
| 12 | Approval | Enforce reviewer requirement | Audit |
| 13 | Staging sync | Observe GitOps reconciliation | Status |
| 14 | Health gate | Verify readiness and SLOs | Metrics |
| 15 | Production PR | Promote same digest | Diff |
| 16 | Prod gate | Validate independent approval | Evidence |
| 17 | Drift | Patch disposable object | Diff |
| 18 | Reconcile | Restore Git desired state | Recovery |
| 19 | Rollback | Revert Git promotion | Revision |
| 20 | Review | Sign off evidence and controls | Report |

## 12 troubleshooting drills

1. Rego compilation error.
2. Mutable image tag policy denial.
3. Unapproved registry rejection.
4. Signature/provenance mismatch.
5. Jenkins Git token cannot create PR.
6. Protected branch bypass attempt.
7. Argo CD OutOfSync.
8. Flux Kustomization NotReady.
9. Admission policy rejects Deployment.
10. Competing writer causes drift.
11. SLO metrics unavailable during promotion.
12. Git rollback incompatible with schema.

Mark unavailable controller-specific drills as blocked, not passed. Never bypass policy or weaken production RBAC to complete an exercise.

## Commands

```sh
kubectl kustomize apps/sample-app/overlays/staging > rendered-staging.yaml
conftest test rendered-staging.yaml --policy policies/
kubectl get deployment sample-app -n jenkins-staging -o wide
kubectl get events -n jenkins-staging --sort-by=.lastTimestamp
# Argo CD, if installed:
argocd app diff sample-app-staging
# Flux, if installed:
flux get kustomizations -A
```

## Evidence template

```text
UTC timestamp:
Jenkins build/Git SHA:
OCI digest/signature/provenance:
Staging PR/merge:
Staging sync and health:
Production PR/approver:
Policy version and pass/fail:
Admission negative test:
Drift desired/live diff:
Reconciliation recovery:
SLO gate and sample count:
Rollback Git commit and live digest:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Immutable digest promoted without rebuilding.
- [ ] Protected PR approval enforced.
- [ ] CI policy and admission deny unsafe changes.
- [ ] Drift detected and reconciled.
- [ ] Production SLO gate fails closed.
- [ ] Git rollback demonstrated.
- [ ] No plaintext secrets committed.
- [ ] Reviewer signs off.

**Related:** [Chapter 054 — Jenkins GitOps Promotion, Drift Detection and Policy Enforcement](../054-jenkins-gitops-promotion-drift-detection-policy-enforcement.md).
