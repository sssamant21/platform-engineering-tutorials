# Chapter 053 — Jenkins Integration with Argo CD and Flux GitOps

**Part 11 — Helm, Kubernetes Deployment and GitOps**  
**Audience:** Jenkins SRE, GitOps engineers, platform security, Kubernetes operations  
**Prerequisites:** Chapters 051–052, disposable Kubernetes cluster, Git repository for desired state, Jenkins, Argo CD or Flux installed in a lab.

## Learning outcomes

Separate CI from continuous reconciliation; use Jenkins to build, scan, sign and propose immutable image digests; use Argo CD or Flux to reconcile reviewed Git state; verify drift, promotion, rollback, access boundaries and audit evidence.

## 1. Architecture and ownership

```text
Application Git → Jenkins CI → tests/scans/SBOM/signing → OCI digest
                         ↓
                 PR to environment Git
                         ↓
                review + protected merge
                         ↓
           Argo CD OR Flux reconciles cluster
                         ↓
              health, SLO, audit feedback
```

**One authoritative deployment owner:** Do not have Jenkins run `helm upgrade` against objects managed by Argo CD or Flux. Jenkins should normally change desired state in Git, not mutate live Kubernetes workloads.

| Layer | Owner | Permissions |
|---|---|---|
| Source/build | Jenkins CI | Read source, publish scoped artifacts |
| Environment manifest | Protected Git workflow | PR creation only for automation |
| Deployment reconciliation | Argo CD or Flux | Namespaced Kubernetes permissions |
| Approval | Reviewers/change management | Merge/protected branch |
| Rollback | Git revert or reviewed new digest | Reconcile through GitOps |

## 2. Repository design

```text
app-repo/
  Jenkinsfile
  src/
  tests/
environment-repo/
  clusters/
    staging/
      sample-app/
        kustomization.yaml
        deployment.yaml
    production/
      sample-app/
        kustomization.yaml
        deployment.yaml
```

Separate staging and production write privileges. Jenkins CI should not hold a token able to bypass protected production branch reviews.

## 3. Immutable digest promotion

Example Kustomize Deployment fragment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  namespace: jenkins-staging
spec:
  replicas: 2
  selector:
    matchLabels: {app: sample-app}
  template:
    metadata:
      labels: {app: sample-app}
    spec:
      automountServiceAccountToken: false
      containers:
        - name: app
          image: registry.example.test/training/sample-app@sha256:REPLACE_WITH_REAL_DIGEST
          ports: [{containerPort: 8080}]
          resources:
            requests: {cpu: 100m, memory: 128Mi}
            limits: {cpu: 500m, memory: 512Mi}
```

Replace placeholder with a **real verified manifest digest**; use digest-pinned, signed images and enforce policy before merge. The example app must be compatible with declared probes and resources.

## 4. Jenkins CI creates a reviewed Git change

The following Pipeline validates a digest and prepares a proposed environment change; it does **not** push directly to protected production branches:

```groovy
pipeline {
    agent { label 'trusted-gitops-ci' }
    parameters {
        string(name: 'IMAGE_DIGEST', defaultValue: '', description: 'Approved sha256 digest')
    }
    options { timestamps(); timeout(time: 20, unit: 'MINUTES') }
    stages {
        stage('Validate digest') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    printf '%s' "$IMAGE_DIGEST" | grep -Eq '^sha256:[a-f0-9]{64}$'
                '''
            }
        }
        stage('Verify artifact') {
            steps {
                echo 'Run approved signature, SBOM and provenance verification here'
            }
        }
        stage('Prepare promotion') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    printf 'Proposed image digest: %s\\n' "$IMAGE_DIGEST" > promotion-request.txt
                '''
                archiveArtifacts artifacts: 'promotion-request.txt', fingerprint: true
            }
        }
    }
}
```

**Production implementation:** Add a scoped GitHub/GitLab app/token to create a branch and PR/MR in the environment repository, modify the exact YAML path using a YAML-aware tool, validate diff/policy, and require protected review before merge. The sample intentionally avoids fabricating provider-specific API commands or bypassing approval. Never store long-lived Git credentials in workspace artifacts.

## 5. Argo CD Application example

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: sample-app-staging
  namespace: argocd
spec:
  project: staging
  source:
    repoURL: https://github.com/EXAMPLE-ORG/environment-repo.git
    targetRevision: main
    path: clusters/staging/sample-app
  destination:
    server: https://kubernetes.default.svc
    namespace: jenkins-staging
  syncPolicy:
    automated:
      prune: false
      selfHeal: true
    syncOptions:
      - CreateNamespace=false
```

Prerequisites: Argo CD installed, `staging` AppProject configured with allowed repo/destination, target namespace precreated, and Argo CD repository credentials if private. In production, review pruning, self-heal, sync windows, hooks and cluster-scoped resources before enabling. This is not a Jenkins controller manifest.

## 6. Flux GitRepository and Kustomization example

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: sample-app-env
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/EXAMPLE-ORG/environment-repo.git
  ref:
    branch: main
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: sample-app-staging
  namespace: flux-system
spec:
  interval: 1m
  path: ./clusters/staging/sample-app
  prune: false
  sourceRef:
    kind: GitRepository
    name: sample-app-env
  targetNamespace: jenkins-staging
  timeout: 3m
```

Prerequisites: Flux controllers and CRDs installed; Git repository access configured; namespace precreated. For stronger isolation use Flux service account impersonation and namespaced RBAC. Do not enable Argo CD and Flux reconciliation for the same resources.

## 7. Promotion workflow

1. Jenkins builds/tests/scans/signs OCI digest and records Git SHA.
2. Jenkins creates a **proposal** to update staging digest in environment Git.
3. Reviewer validates artifact provenance, manifest diff, policy and change ticket.
4. Protected merge updates desired state.
5. Argo CD/Flux reconciles staging and reports health.
6. Synthetic/SLO checks validate actual workload behavior.
7. Production promotion uses separate reviewed PR and credentials.
8. Rollback reverts desired state to prior verified digest and lets GitOps reconcile.

A green GitOps sync does not necessarily prove application health. Verify Deployment readiness, endpoints, SLOs and business synthetic transactions.

## 8. Drift and reconciliation

Argo CD can detect OutOfSync and self-heal based on policy; Flux continuously reconciles declared state. A manual `kubectl patch` is not a durable fix. Capture desired commit, live object, reconciliation status and actor; correct Git desired state or temporarily suspend reconciliation through approved incident change control.

Commands:

```sh
argocd app get sample-app-staging
argocd app diff sample-app-staging
flux get kustomizations -A
flux get sources git -A
kubectl get deployment sample-app -n jenkins-staging -o wide
kubectl get events -n jenkins-staging --sort-by=.lastTimestamp
```

Only run commands for the controller installed in the lab. `argocd` CLI requires authentication; `flux` CLI requires appropriate kubeconfig.

## 9. Security boundaries

- Jenkins CI: read source, write artifacts and PR branches; no production cluster-admin.
- GitOps controllers: least-privilege namespaces and approved cluster resources.
- Protected branches: mandatory review, CODEOWNERS and policy checks.
- Git credentials: short-lived app identities where supported.
- Supply chain: digest pinning, signatures, SBOM and provenance.
- Secrets: external secret stores or encrypted GitOps secret workflow; never plaintext secrets in Git.
- Multi-tenancy: Argo CD AppProjects or Flux service-account impersonation and namespace isolation.
- Audit: connect Jenkins build ID, digest, PR, merge commit, sync revision and Kubernetes rollout.

## 10. Observability and SLOs

Measure CI-to-PR time, PR approval lead time, GitOps reconciliation lag, sync success, drift count/duration, deployment readiness, rollback time, error budget burn, unauthorized sync attempts and controller availability. Alert when desired revision differs from observed revision beyond an approved window.

## 11. Troubleshooting matrix

| Failure | Evidence | Recovery |
|---|---|---|
| Jenkins PR creation denied | Git API 403 | Scope app permissions |
| Protected branch bypass | Audit log | Revoke/bind protection |
| Bad image digest | Registry verification | Fix proposal |
| Argo repo auth failure | Repository status | Repair scoped credentials |
| Argo AppProject deny | Application conditions | Correct project boundaries |
| Argo OutOfSync | App diff | Review desired/live state |
| Flux source not Ready | GitRepository status | Fix URL/auth/branch |
| Flux Kustomization not Ready | Reconcile conditions | Fix manifest/policy |
| Namespace absent | Events | Precreate via platform |
| ImagePullBackOff | Pod events | Fix registry access |
| Admission rejected | Policy webhook | Harden YAML |
| Two reconcilers fight | Repeated drift | Remove duplicate owner |
| Manual hotfix reverted | Reconcile history | Commit desired fix |
| Health degraded after sync | App/SLO metrics | Revert digest |
| Git revert not applied | Controller status | Repair reconciliation |
| Secrets committed | Git audit | Revoke/rotate/remove history as needed |

## 12. Production runbooks

### A. GitOps onboarding
1. Define environment repo, ownership and protected branches.
2. Scope Jenkins to artifact publishing and PR creation.
3. Configure one GitOps reconciler and namespace boundaries.
4. Deploy synthetic digest through reviewed merge.
5. Validate reconciliation, health, rollback and audit chain.

### B. Reconciliation outage
1. Capture desired Git commit and controller conditions.
2. Distinguish source auth, manifest, policy, namespace and API errors.
3. Fix cause in Git or controller configuration through approved change.
4. Reconcile and validate live digest/readiness.
5. Record lag, customer impact and follow-up.

### C. Bad release rollback
1. Freeze further promotions and identify known-good digest.
2. Revert environment Git change through protected process.
3. Confirm controller reconciles the intended revision.
4. Verify app readiness and SLO recovery.
5. Record incident evidence.

### D. Drift incident
1. Identify actual owner and drift source.
2. Capture diff and audit actor.
3. Stop competing direct mutations.
4. Restore single desired-state authority.
5. Confirm drift no longer recurs.

### E. Credential compromise
1. Revoke affected Git/Jenkins/GitOps credentials.
2. Audit PRs, commits and controller syncs.
3. Rotate secrets and validate artifact provenance.
4. Restore least privilege and branch protections.
5. Record security review.

## 13. Acceptance criteria

- [ ] Jenkins cannot mutate production workloads directly.
- [ ] Environment changes require reviewed PR/merge.
- [ ] One GitOps controller owns each resource.
- [ ] Immutable digest and signature verified before promotion.
- [ ] Staging sync and application health validated.
- [ ] Drift detection and correction demonstrated.
- [ ] Git revert rollback tested.
- [ ] Full audit chain preserved.

**Companion:** [Chapter 053 hands-on lab](labs/053-jenkins-argocd-flux-gitops-integration-check.md).  
**Next:** Chapter 054 — Jenkins GitOps Promotion, Drift Detection and Policy Enforcement.
