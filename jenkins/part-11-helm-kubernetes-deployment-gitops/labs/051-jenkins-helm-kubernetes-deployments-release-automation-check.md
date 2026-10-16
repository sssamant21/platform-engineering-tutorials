# Chapter 051 — Hands-on Lab: Jenkins Helm-Based Kubernetes Deployments

**Environment:** Disposable Kubernetes cluster, Jenkins trusted release agent, Helm 3, kubectl, synthetic HTTP app and approved OCI image digest. Do not deploy to production.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record Helm/Kubernetes/Jenkins versions | Baseline |
| 02 | Architecture | Diagram CI/release/cluster trust | Diagram |
| 03 | Namespace | Create `jenkins-staging` | Namespace |
| 04 | RBAC | Scope release SA to namespace | Role/Binding |
| 05 | Chart | Create Chart.yaml | Chart |
| 06 | Values | Define image repo/digest/resources | Values |
| 07 | Deployment | Template secure Deployment | Manifest |
| 08 | Service | Template ClusterIP Service | Manifest |
| 09 | Lint | Run `helm lint` | Pass |
| 10 | Render | Run `helm template` | YAML |
| 11 | Dry-run | Validate manifests | Evidence |
| 12 | Digest | Verify approved registry manifest | Digest |
| 13 | Approval | Review deployment request | Record |
| 14 | Install | Deploy with `helm upgrade --install` | Revision |
| 15 | Rollout | Check readiness/health | Status |
| 16 | Audit | Record Helm history and digest | Report |
| 17 | Failure | Inject invalid image digest | Failed rollout |
| 18 | Rollback | Restore known-good revision | Recovery |
| 19 | GitOps boundary | Document single ownership | Decision |
| 20 | Review | Complete acceptance checklist | Sign-off |

## 12 troubleshooting drills

1. Invalid Chart.yaml.
2. YAML template indentation error.
3. Release service account forbidden.
4. Missing namespace.
5. ImagePullBackOff.
6. Pod Security admission rejection.
7. Readiness probe failure.
8. Insufficient node capacity.
9. Helm upgrade timeout.
10. Failed atomic rollback.
11. Secret inadvertently added to values.
12. GitOps reconciler reverts Helm changes.

## Commands

```sh
set -eu
helm lint charts/sample-app -f environments/staging-values.yaml
helm template sample-app charts/sample-app \
  -n jenkins-staging -f environments/staging-values.yaml > rendered.yaml
kubectl apply --dry-run=client -f rendered.yaml
helm upgrade --install sample-app charts/sample-app \
  -n jenkins-staging -f environments/staging-values.yaml \
  --set-string image.digest="$IMAGE_DIGEST" \
  --atomic --wait --timeout 10m
kubectl rollout status deployment/sample-app \
  -n jenkins-staging --timeout=5m
helm history sample-app -n jenkins-staging
```

Create namespace in advance; set `IMAGE_DIGEST` to a real `sha256:` registry digest and use the fixture from the main chapter. Rollback only to a verified prior revision.

## Evidence template

```text
UTC timestamp:
Jenkins build / Git SHA:
Helm and Kubernetes versions:
Namespace / release identity:
Chart version / values hash:
Image registry digest and signature verification:
Lint/template/admission results:
Approval/change ticket:
Helm release revision:
Rollout readiness and SLO checks:
Injected fault / root cause:
Rollback revision and recovery time:
GitOps ownership decision:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Chart renders without errors.
- [ ] Release identity is namespace-scoped.
- [ ] Immutable approved digest deployed.
- [ ] Rollout health and release history verified.
- [ ] Rollback completed on disposable cluster.
- [ ] No secrets in rendered YAML or Jenkins logs.
- [ ] Helm/GitOps ownership documented.
- [ ] Reviewer signs off.

**Related:** [Chapter 051 — Jenkins Helm-Based Kubernetes Deployments and Release Automation](../051-jenkins-helm-kubernetes-deployments-release-automation.md).
