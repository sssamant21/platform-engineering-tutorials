# Chapter 097 — Enterprise GitOps Final Project: Infrastructure Provisioning, GitLab CI/CD and Argo CD Implementation

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 20:** Final Enterprise GitOps Capstone  
**Chapter:** 097 / 100  
**Audience:** SRE, Platform Engineering, Cloud Infrastructure, Security and Release Engineering

> **Safety:** This is a lab implementation reference. Never apply Terraform plans, change CI credentials, install controllers or synchronize Applications in production without an approved change and verified blast radius. Placeholder paths and domains require implementation in a disposable repository and cluster.

## 1. Learning objectives

Turn the Chapter 096 architecture into a reproducible implementation: pinned Terraform and cloud identities, Kubernetes prerequisites, GitLab CI/CD with protected runners, tested Helm charts, signed OCI images, Argo CD AppProjects/Applications, secret delivery, environment promotion, rollback and acceptance evidence.

## 2. Implementation architecture

```text
Application Git -> GitLab CI tests -> build/SBOM/sign -> OCI registry
                                               |
                                 GitOps config promotion PR
                                               |
                                     protected main branch
                                               |
                                       Argo CD controller
                                               |
                           AppProject -> Helm -> lab Kubernetes
                                               |
                                  synthetic API + SLO checks
Infrastructure Git -> Terraform plan -> approval -> cloud resources
```

**Separation of duties:** infrastructure provisioning, image building and desired-state reconciliation use separate identities. Production cluster write access must not be granted to generic build runners.

## 3. Prerequisites

A disposable Kubernetes cluster and cloud sandbox; protected GitLab project; isolated runner; OCI registry; Terraform, Helm, kubectl, Git and a suitable test runtime. Use pinned versions and least-privilege identities. This chapter does not provision a specific cloud account because provider IDs, regions, VPCs and billing must be supplied by the operator.

## 4. Repository layout

```text
enterprise-gitops/
  infrastructure/terraform/
    modules/{network,cluster,identity}/
    environments/lab/{main.tf,providers.tf,variables.tf,lab.tfvars}
  platform/
    namespaces/lab.yaml
    argocd/projects/team-a.yaml
    argocd/applications/lab.yaml
    external-secrets/
  applications/synthetic-api/
    chart/{Chart.yaml,values.yaml,templates/}
    tests/
  environments/{lab,staging,prod}/values.yaml
  scripts/{preflight.sh,verify.sh}
  .gitlab-ci.yml
  CODEOWNERS
```

## 5. Terraform foundation

Illustrative provider constraints (adapt to actual provider and cluster modules):

```hcl
terraform {
  required_version = ">= 1.6.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = "enterprise-gitops-lab", Environment = "lab" }
  }
}
variable "region" {
  type = string
}
```

Pin module revisions, validate provider compatibility and configure encrypted, access-controlled remote state with locking before shared use. `-backend=false` in the labs is for local validation only; it is not an acceptable shared production state strategy.

## 6. GitLab CI pipeline template

The sample assumes a protected runner image that contains Git, Python, Helm and kubectl. Pin it by a verified digest before use. Build/sign/push is intentionally a separate reviewed workflow because registry credentials and signing keys vary by organization.

```yaml
stages: [validate, test, package, promote]
variables:
  HELM_CHART: applications/synthetic-api/chart
validate:
  stage: validate
  image: registry.example.invalid/ci/toolchain@sha256:REPLACE_WITH_VERIFIED_DIGEST
  script:
    - git diff --check
    - helm lint "$HELM_CHART"
    - helm template synthetic-api "$HELM_CHART" -f environments/lab/values.yaml > rendered.yaml
  artifacts:
    paths: [rendered.yaml]
test:
  stage: test
  image: registry.example.invalid/ci/toolchain@sha256:REPLACE_WITH_VERIFIED_DIGEST
  script:
    - python -m pytest -q applications/synthetic-api/tests
promote:
  stage: promote
  image: registry.example.invalid/ci/toolchain@sha256:REPLACE_WITH_VERIFIED_DIGEST
  when: manual
  allow_failure: false
  script:
    - echo "Create a reviewed GitOps configuration PR for the signed image digest"
  rules:
    - if: '$CI_COMMIT_REF_PROTECTED == "true"'
```

Manual jobs alone do not provide sufficient authorization. Enforce protected environments, approvers, runner isolation, secret scoping and audit retention. A CI pipeline should not bypass GitOps with a direct production `kubectl apply`.

## 7. Helm chart and deployment

```yaml
# applications/synthetic-api/chart/Chart.yaml
apiVersion: v2
name: synthetic-api
description: Synthetic GitOps capstone API
type: application
version: 0.1.0
appVersion: "1.0.0"
```

```yaml
# applications/synthetic-api/chart/values.yaml
replicaCount: 2
image:
  repository: registry.example.invalid/lab/synthetic-api
  digest: sha256:REPLACE_WITH_VERIFIED_DIGEST
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    memory: 256Mi
```

For a real chart, include templated Deployment/Service, immutable digest image reference, readiness/liveness probes, securityContext, ServiceAccount, topology spread and a PodDisruptionBudget where suitable. Lint, render and validate against a disposable cluster before any sync.

## 8. Argo CD project and application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: capstone-lab
  namespace: argocd
spec:
  sourceRepos:
    - https://git.example.invalid/platform/enterprise-gitops.git
  destinations:
    - server: https://kubernetes.default.svc
      namespace: enterprise-gitops-lab
  clusterResourceWhitelist: []
---
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: capstone-lab
  namespace: argocd
spec:
  project: capstone-lab
  source:
    repoURL: https://git.example.invalid/platform/enterprise-gitops.git
    targetRevision: main
    path: applications/synthetic-api/chart
    helm:
      valueFiles: [values.yaml]
  destination:
    server: https://kubernetes.default.svc
    namespace: enterprise-gitops-lab
  syncPolicy:
    syncOptions: [CreateNamespace=false]
```

**Implementation note:** for production, pin promotion to reviewed immutable revisions, separate environment values appropriately, and ensure AppProject resource restrictions match actual chart resources. This sample intentionally leaves automated sync and pruning disabled until validation.

## 9. Safe implementation preflight

```bash
export LAB_NS=enterprise-gitops-lab
export APPROVED_CONTEXT=replace-with-disposable-context
test "$(kubectl config current-context)" = "$APPROVED_CONTEXT"
kubectl get namespace "$LAB_NS"
terraform version
helm version
kubectl -n argocd get pods
```

## 10. Hands-on labs — 18 implementation exercises

All labs require a change ID, environment allowlist, expected result, evidence and rollback plan. Paths assume you created the repository structure above; some labs validate templates rather than deploying a full system.

### Lab 01 — Bootstrap local toolchain

**Procedure:** Verify Git, Terraform, Helm, kubectl and optional argocd CLI versions.

```bash
git --version
terraform version
helm version
kubectl version --client
```

**Acceptance:** Pinned tool versions recorded. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 02 — Validate cloud identity

**Procedure:** Inspect current lab account, context and namespace; confirm no production access.

```bash
kubectl config current-context
kubectl auth can-i create deployments -n "$LAB_NS"
```

**Acceptance:** Least-privilege lab identity. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 03 — Terraform initialize

**Procedure:** Initialize reviewed lab IaC with pinned providers and remote state settings.

```bash
terraform -chdir=infrastructure/terraform/environments/lab init -backend=false
```

**Acceptance:** Providers lockfile and init success. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 04 — Terraform validate

**Procedure:** Format and validate lab IaC without applying.

```bash
terraform -chdir=infrastructure/terraform/environments/lab fmt -check -recursive
terraform -chdir=infrastructure/terraform/environments/lab validate
```

**Acceptance:** No validation errors. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 05 — Review infrastructure plan

**Procedure:** Generate non-mutating Terraform plan with approved lab variables.

```bash
terraform -chdir=infrastructure/terraform/environments/lab plan -var-file=lab.tfvars -out=lab.tfplan
```

**Acceptance:** Peer-reviewed plan, no unexpected deletion. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 06 — Kubernetes prerequisite check

**Procedure:** Inspect cluster nodes, storage classes, CoreDNS and ingress controllers.

```bash
kubectl get nodes -o wide
kubectl get storageclass
kubectl -n kube-system get pods
```

**Acceptance:** Platform prerequisites healthy. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 07 — Namespace and quota manifests

**Procedure:** Use server-side dry run for scoped namespace, quotas and resource limits.

```bash
kubectl apply --dry-run=server -f platform/namespaces/lab.yaml
```

**Acceptance:** Manifest accepted by API. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 08 — GitLab runner isolation

**Procedure:** Review dedicated runner tags, workload identity, protected variables and build isolation.

```bash
git status --short
git diff --check
```

**Acceptance:** Runner security review signed. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 09 — Pipeline syntax and tests

**Procedure:** Validate YAML and run app unit tests in local or protected CI.

```bash
git diff --check
python -m pytest -q applications/synthetic-api/tests
```

**Acceptance:** Tests and pipeline lint pass. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 10 — Container provenance

**Procedure:** Build an immutable test artifact in protected CI; verify digest and signature before deploy.

```bash
kubectl -n "$LAB_NS" get deploy -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.template.spec.containers[*].image}{"\n"}{end}'
```

**Acceptance:** Signed digest captured. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 11 — Helm chart lint

**Procedure:** Lint app chart with staging values and render manifests for review.

```bash
helm lint applications/synthetic-api/chart
helm template synthetic-api applications/synthetic-api/chart -f environments/lab/values.yaml > /tmp/lab-rendered.yaml
```

**Acceptance:** Rendered manifests reviewed. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 12 — Helm manifest dry-run

**Procedure:** Check rendered resources against cluster schema and RBAC.

```bash
kubectl apply --dry-run=server -n "$LAB_NS" -f /tmp/lab-rendered.yaml
```

**Acceptance:** No unexpected cluster-scoped resources. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 13 — Argo CD install verification

**Procedure:** Inspect Argo CD control plane and CRD versions before bootstrap.

```bash
kubectl -n argocd get deploy,sts,pods
kubectl get crd | grep argoproj
```

**Acceptance:** Compatible components healthy. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 14 — AppProject boundary

**Procedure:** Validate source repository, namespace destination and cluster-resource restrictions.

```bash
kubectl -n argocd get appprojects -o yaml
```

**Acceptance:** No wildcard prod privileges. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 15 — Application deployment

**Procedure:** Apply approved lab Application definition only after manual review and confirm sync/health.

```bash
kubectl apply --dry-run=server -n argocd -f platform/argocd/applications/lab.yaml
kubectl -n argocd get applications -o wide
```

**Acceptance:** Desired revision and health observed. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 16 — Secrets and identity

**Procedure:** Verify External Secrets or SOPS integration without exposing secret values.

```bash
kubectl -n "$LAB_NS" get serviceaccounts
kubectl -n "$LAB_NS" get externalsecrets
```

**Acceptance:** Secrets ready and scoped. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 17 — Promotion and rollback

**Procedure:** Review protected promotion PR, deploy canary in lab and rehearse rollback to prior digest.

```bash
git log -3 --oneline
kubectl -n "$LAB_NS" rollout status deployment/synthetic-api --timeout=120s
```

**Acceptance:** Audit trail and safe rollback. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

### Lab 18 — Integration acceptance

**Procedure:** Check ingress, API health, Argo CD revision, pipeline evidence and cleanup ownership.

```bash
kubectl -n "$LAB_NS" get deploy,pods,svc,ingress -o wide
kubectl -n argocd get applications -o wide
```

**Acceptance:** Signed implementation evidence packet. **Rollback:** revert only reviewed lab resources; preserve Terraform state and recovery evidence.

## 11. Troubleshooting — 20 implementation failures

| # | Scenario | First check | Safe remediation |
|---|---|---|---|
| 1 | Terraform provider version mismatch | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 2 | Terraform state lock | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 3 | Cloud IAM access denied | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 4 | Cloud quota exhausted | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 5 | Node group not ready | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 6 | CNI initialization failure | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 7 | CSI driver missing | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 8 | Namespace quota exceeded | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 9 | GitLab runner offline | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 10 | Protected variable unavailable | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 11 | Pipeline unit test failure | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 12 | OCI image signing failure | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 13 | ImagePullBackOff | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 14 | Helm render invalid | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 15 | Kubernetes admission denied | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 16 | Argo CD repo authentication failure | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 17 | AppProject destination rejected | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 18 | ExternalSecret sync failure | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 19 | Argo CD drift loop | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |
| 20 | Rollback incompatible with DB migration | Check CI job, events, RBAC, manifests and dependency health | Contain scope; correct configuration; rerun dry-run and synthetic validation |

## 12. Eight implementation runbooks

### RB-01 Infrastructure plan and change

**Trigger and procedure:** Verify account, remote state, provider lock, change ID, peer review and blast radius. Execute only an approved plan; capture state and rollback.

**Exit criteria:** approved operator, timestamped commands, observed cluster/Git state, synthetic test, rollback status and audit evidence.

### RB-02 Terraform recovery

**Trigger and procedure:** On partial apply or lock, inspect state ownership and provider errors; never force-unlock without verifying abandoned lock and approval.

**Exit criteria:** approved operator, timestamped commands, observed cluster/Git state, synthetic test, rollback status and audit evidence.

### RB-03 GitLab CI failure

**Trigger and procedure:** Inspect runner, protected variables, test reports, artifacts and identity; rerun only idempotent jobs after fixing root cause.

**Exit criteria:** approved operator, timestamped commands, observed cluster/Git state, synthetic test, rollback status and audit evidence.

### RB-04 Supply-chain rejection

**Trigger and procedure:** Quarantine unsigned or unexpected digest, verify build provenance and signing trust root; promote only approved immutable artifacts.

**Exit criteria:** approved operator, timestamped commands, observed cluster/Git state, synthetic test, rollback status and audit evidence.

### RB-05 Helm deployment failure

**Trigger and procedure:** Inspect rendered manifests, values, hooks, CRDs and rollout status; revert only after compatibility and database migration checks.

**Exit criteria:** approved operator, timestamped commands, observed cluster/Git state, synthetic test, rollback status and audit evidence.

### RB-06 Argo CD reconciliation failure

**Trigger and procedure:** Inspect repo credentials, AppProject, sync policies, manifest generation and controller logs; prevent uncontrolled prune or sync loops.

**Exit criteria:** approved operator, timestamped commands, observed cluster/Git state, synthetic test, rollback status and audit evidence.

### RB-07 Identity and secrets outage

**Trigger and procedure:** Validate workload identity, KMS grants and External Secrets conditions; rotate via approved vault without printing plaintext.

**Exit criteria:** approved operator, timestamped commands, observed cluster/Git state, synthetic test, rollback status and audit evidence.

### RB-08 Production readiness handoff

**Trigger and procedure:** Review source revision, signed artifacts, SLO probes, rollback, DR dependencies, runbooks and owner signoffs before promotion.

**Exit criteria:** approved operator, timestamped commands, observed cluster/Git state, synthetic test, rollback status and audit evidence.

## 13. Acceptance scorecard (100 points)

| Domain | Points |
|---|---:|
| Terraform and cloud identity | 15 |
| Kubernetes prerequisites and isolation | 10 |
| GitLab pipeline and protected runner | 15 |
| OCI/Helm supply-chain verification | 15 |
| Argo CD project and reconciliation | 15 |
| Secrets and policy enforcement | 10 |
| Promotion, rollback and observability | 10 |
| Operational evidence and handoff | 10 |
| **Total** | **100** |

**Pass:** at least 90/100 and mandatory gates: correct lab context, reviewed Terraform plan, protected CI identity, signed immutable artifact, AppProject destination restrictions, no plaintext secrets, working synthetic transaction and documented rollback.

## 14. Evidence and handoff template

```text
Change ID / lab account / cluster context:
Terraform provider and module lock:
Terraform plan reviewer:
Runner identity and protected CI settings:
Unit test and Helm lint results:
Image digest / signature / SBOM reference:
Argo CD AppProject / Application revision:
Secrets and policy evidence:
Deployment health / synthetic transaction:
Rollback and DR prerequisites:
Final score / exceptions / owners:
Approver / next implementation milestone:
```

## 15. Definition of done

The team has a version-pinned and peer-reviewed IaC plan, an auditable CI pipeline, a tested Helm chart, restricted Argo CD reconciliation, verified identity/secrets integration and an evidence-backed synthetic deployment in a disposable cluster. No production readiness is claimed until later operational tests pass.

**Next:** Chapter 098 — Enterprise GitOps Final Project: Production Deployment, Security, Observability and Release Operations.
