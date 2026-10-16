# Chapter 053 — Hands-on Lab: Jenkins, Argo CD and Flux GitOps Integration

**Environment:** Disposable Kubernetes cluster; Jenkins; either Argo CD or Flux; two test Git repositories; protected staging branch or simulated review gate. Do not run both reconcilers against the same objects.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record Jenkins/K8s/GitOps versions | Baseline |
| 02 | Architecture | Diagram CI versus reconciliation | Diagram |
| 03 | Environment Git | Create staging desired-state path | Commit |
| 04 | Digest | Pin approved image digest | Manifest |
| 05 | Jenkins CI | Build/test/scan synthetic artifact | Build |
| 06 | Provenance | Record image/SBOM/signature evidence | Evidence |
| 07 | Git identity | Scope Jenkins to PR creation | Permission |
| 08 | PR proposal | Open staging digest update | PR |
| 09 | Review | Validate manifest diff/policy | Approval |
| 10 | Merge | Update protected desired state | Commit |
| 11 | Argo CD | Configure test Application if installed | Status |
| 12 | Flux | Configure test Kustomization if installed | Status |
| 13 | Reconcile | Verify live digest matches Git | Deployment |
| 14 | Health | Check readiness and synthetic HTTP | Metrics |
| 15 | Drift | Mutate disposable object and observe | Diff |
| 16 | Self-heal | Confirm approved reconciliation | Evidence |
| 17 | Bad digest | Simulate failed rollout | Failure |
| 18 | Rollback | Revert Git to verified digest | Recovery |
| 19 | Audit | Correlate Jenkins/PR/GitOps/K8s | Chain |
| 20 | Review | Document owner and SLOs | Sign-off |

## 12 troubleshooting drills

1. Jenkins cannot create PR.
2. Protected branch bypass attempt.
3. Invalid digest in proposal.
4. Argo CD repo authentication failure.
5. Argo CD AppProject destination denied.
6. Argo CD OutOfSync.
7. Flux GitRepository source failure.
8. Flux Kustomization reconciliation failure.
9. Namespace missing.
10. ImagePullBackOff after merge.
11. Competing reconciler or manual mutation.
12. Git revert not reflected in live Deployment.

Mark controller-specific drills blocked if the relevant controller is not installed; do not claim unexecuted evidence.

## Commands

```sh
kubectl get deployment sample-app -n jenkins-staging -o wide
kubectl get events -n jenkins-staging --sort-by=.lastTimestamp
# Argo CD, if installed and authenticated:
argocd app get sample-app-staging
argocd app diff sample-app-staging
# Flux, if installed:
flux get sources git -A
flux get kustomizations -A
```

## Evidence template

```text
UTC timestamp:
Jenkins build ID and Git SHA:
OCI digest and provenance:
Environment repo PR and approval:
Desired Git commit:
GitOps controller/version:
Application or Kustomization status:
Live Deployment digest:
Readiness/SLO check:
Drift injection and reconciliation:
Rollback Git commit and recovery:
Unauthorized access test:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Jenkins proposes Git change rather than mutating live cluster.
- [ ] Protected review/approval applied.
- [ ] Only one GitOps controller owns each resource.
- [ ] Desired and live digests match after sync.
- [ ] Drift detected and reconciled.
- [ ] Git revert rollback tested.
- [ ] No plaintext secrets committed.
- [ ] Reviewer signs off.

**Related:** [Chapter 053 — Jenkins Integration with Argo CD and Flux GitOps](../053-jenkins-argocd-flux-gitops-integration.md).
