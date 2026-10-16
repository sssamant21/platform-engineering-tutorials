# Chapter 055 — Hands-on Capstone: Jenkins Helm and GitOps Enterprise Release Automation

**Environment:** Disposable Kubernetes cluster, Jenkins, Helm, protected environment Git, Argo CD or Flux, Conftest/OPA, optional admission and progressive routing controllers. Do not run destructive tests in production.

## 20 capstone exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Architecture | Diagram CI/GitOps trust | Diagram |
| 02 | Ownership | Document RACI and one reconciler | Matrix |
| 03 | Jenkins | Run synthetic build/tests | Build |
| 04 | Artifact | Pin OCI sha256 digest | Digest |
| 05 | Provenance | Verify signature/SBOM | Evidence |
| 06 | Helm | Lint and template chart | Output |
| 07 | Policy | Run Conftest positive case | Pass |
| 08 | Negative policy | Reject mutable tag | Denied |
| 09 | Git | Create staging digest PR | PR |
| 10 | Approval | Verify protected review | Audit |
| 11 | Staging sync | Confirm GitOps revision | Status |
| 12 | Staging health | Validate readiness/SLOs | Metrics |
| 13 | Production PR | Promote same digest | Diff |
| 14 | Approval | Verify separate production review | Audit |
| 15 | Progressive release | Demonstrate rolling or routing | Events |
| 16 | Drift | Inject benign live change | Diff |
| 17 | Reconcile | Confirm desired state restored | Recovery |
| 18 | Failure | Inject bad digest/readiness | Incident |
| 19 | Rollback | Revert Git and verify health | RTO |
| 20 | Score | Complete acceptance and handover | Report |

## 20 troubleshooting drills

1. Helm lint error.
2. Helm template invalid YAML.
3. Chart dependency unavailable.
4. Mutable image tag policy failure.
5. Signature/provenance verification failure.
6. Jenkins Git token denied.
7. Protected branch bypass.
8. Argo CD repository authentication error.
9. Flux GitRepository NotReady.
10. GitOps namespace/RBAC denial.
11. Admission rejects privileged Pod.
12. ImagePullBackOff.
13. Readiness probe failure.
14. ResourceQuota exceeded.
15. Blue-green selector mismatch.
16. Canary routing controller missing.
17. SLO regression.
18. Metrics backend unavailable.
19. Competing Helm/GitOps owner.
20. Bad release reverted through Git.

Mark feature-specific exercises blocked when unavailable. Never invent evidence or claim canary weights without a real supported routing controller.

## Commands

```sh
set -eu
helm lint charts/sample-app -f environments/staging-values.yaml
helm template sample-app charts/sample-app \
  -n jenkins-staging -f environments/staging-values.yaml > rendered.yaml
conftest test rendered.yaml --policy policies/
kubectl get deployment sample-app -n jenkins-staging -o wide
kubectl get events -n jenkins-staging --sort-by=.lastTimestamp
```

## Evidence template

```text
UTC timestamp:
Cluster and tool versions:
Jenkins build / Git SHA:
Chart version / digest:
Image digest / SBOM / signer:
Policy positive/negative tests:
Staging PR and sync revision:
Staging SLO and health:
Production PR/approver:
Production sync revision:
Progressive strategy/traffic evidence:
Drift injection and recovery:
Failure injection and rollback RTO:
Cost baseline:
Score / risks / reviewer:
```

## 100-point scorecard

| Category | Max |
|---|---:|
| Architecture/ownership | 10 |
| CI/provenance | 15 |
| Helm validation | 10 |
| GitOps promotion | 15 |
| Progressive delivery/SLO | 10 |
| Security/policy | 15 |
| Drift recovery | 10 |
| Incidents/rollback | 10 |
| Observability/FinOps | 5 |
| **Total** | **100** |

Suggested pass: 85 plus mandatory integrity, access, health and rollback gates. Unavailable features are **not tested**, not passed.

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 20 drills completed or explicitly blocked.
- [ ] Same verified image digest promoted to production.
- [ ] Protected Git review and policy enforcement demonstrated.
- [ ] Only one reconciler owns workload.
- [ ] Drift detection and recovery validated.
- [ ] Missing SLO data blocks promotion.
- [ ] Git rollback restores verified digest.
- [ ] No secrets leaked to Git/logs/artifacts.
- [ ] Reviewer signs off.

**Related:** [Chapter 055 — Jenkins Helm and GitOps Enterprise Release Automation Capstone](../055-jenkins-helm-gitops-enterprise-release-automation-capstone.md).
