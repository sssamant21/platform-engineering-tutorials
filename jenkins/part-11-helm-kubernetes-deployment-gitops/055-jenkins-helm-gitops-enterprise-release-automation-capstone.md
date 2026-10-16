# Chapter 055 — Jenkins Helm and GitOps Enterprise Release Automation Capstone

**Part 11 — Helm, Kubernetes Deployment and GitOps (final capstone)**  
**Audience:** Jenkins SRE, Kubernetes platform, release engineering, DevSecOps and incident commanders  
**Prerequisites:** Chapters 051–054; disposable Kubernetes cluster, Jenkins, Helm 3, kubectl, environment Git repository, Argo CD or Flux, policy checker and synthetic HTTP application.

## Mission

Demonstrate a reproducible, policy-controlled, observable and recoverable release process from a protected application commit through CI, signed immutable artifact, Helm packaging, GitOps promotion, progressive delivery, drift recovery and Git-based rollback. Collect objective evidence and complete a 100-point enterprise acceptance review. **Destructive drills must run only in a disposable lab.**

## 1. End-to-end architecture

```text
Protected application Git commit
          ↓
Jenkins CI: test → scan → SBOM → sign → OCI sha256 digest
          ↓
Helm chart validation + policy gates
          ↓
Staging desired-state PR → protected review
          ↓
Argo CD OR Flux reconciles staging
          ↓
Readiness + synthetic transactions + SLO evaluation
          ↓
Production desired-state PR (same digest, separate approval)
          ↓
GitOps reconciles production
          ↓
Traffic strategy → observe → accept or revert Git
```

**Ownership:** Jenkins produces and proposes. Git is the source of truth. Argo CD or Flux reconciles. A traffic controller (if used) owns weighted routing. Do not run Jenkins `helm upgrade` on objects managed by GitOps.

## 2. Deliverables and RACI

| Deliverable | Owner | Evidence |
|---|---|---|
| Architecture/trust boundaries | Platform | Diagram |
| Jenkins CI pipeline | CI team | Build log |
| Helm chart/locked dependencies | App/platform | Lint/template output |
| Artifact provenance | Supply chain | Digest/SBOM/signature |
| Staging/production overlays | GitOps team | Reviewed Git commits |
| Policies and admission | Security | Negative tests |
| Reconciliation health | GitOps SRE | Sync status |
| Progressive delivery | Release team | Traffic and SLO metrics |
| Rollback and incident runbooks | On-call | Measured recovery |
| Capacity/FinOps | Platform | Cost baseline |

## 3. Reference repository layout

```text
application-repo/
  Jenkinsfile
  charts/sample-app/
    Chart.yaml
    values.yaml
    templates/deployment.yaml
    templates/service.yaml
  tests/
environment-repo/
  clusters/
    staging/sample-app/
    production/sample-app/
  policies/
    image-digest.rego
  evidence/
    acceptance-template.md
```

Production environment repository writes require protected review. Use a scoped automation identity to create a branch/PR, not a token with direct production branch push rights.

## 4. Helm validation gates

```sh
set -eu
helm lint charts/sample-app -f environments/staging-values.yaml
helm template sample-app charts/sample-app \
  -n jenkins-staging \
  -f environments/staging-values.yaml > rendered.yaml
kubectl apply --dry-run=client -f rendered.yaml
conftest test rendered.yaml --policy policies/
```

Assumes Helm chart and values files from Chapter 051 and an OPA/Conftest policy set from Chapter 054. Client dry-run cannot guarantee admission acceptance; test server-side admission in a disposable namespace using appropriately scoped credentials. Pin tool versions.

## 5. Artifact provenance and immutable promotion

Every release must record source Git SHA, CI build ID, OCI digest, signing identity, SBOM reference, vulnerability policy result and chart revision. Promotion to production must use the **same digest** accepted in staging. Image digest alone is not signature verification; integrate an approved verification tool and fail closed if provenance cannot be verified.

```text
Release record:
  source_sha: <commit>
  jenkins_build: <url>
  chart_version: <version>
  image_digest: sha256:<64-hex>
  signature_verified: true/false
  sbom_ref: <artifact>
  staging_commit: <commit>
  production_commit: <commit>
```

These are placeholders; never mark a control passed without evidence.

## 6. Jenkins capstone Pipeline

The following Pipeline demonstrates **safe orchestration gates and evidence creation**. It does not claim to implement artifact signing or provider-specific PR creation.

```groovy
pipeline {
    agent { label 'trusted-gitops-release' }
    parameters {
        string(name: 'IMAGE_DIGEST', defaultValue: '', description: 'Approved staging-verified sha256 digest')
        choice(name: 'TARGET', choices: ['staging', 'production'])
    }
    options {
        timestamps()
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
    }
    stages {
        stage('Validate digest') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    printf '%s' "$IMAGE_DIGEST" | grep -Eq '^sha256:[a-f0-9]{64}$'
                '''
            }
        }
        stage('Verify provenance') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    test -f provenance-verified.marker || {
                      echo "Missing verified provenance evidence" >&2
                      exit 1
                    }
                '''
            }
        }
        stage('Validate Helm chart') {
            steps {
                sh 'helm lint charts/sample-app -f environments/staging-values.yaml'
            }
        }
        stage('Policy check') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    kubectl kustomize clusters/"$TARGET"/sample-app > rendered.yaml
                    conftest test rendered.yaml --policy policies/
                '''
                archiveArtifacts artifacts: 'rendered.yaml', fingerprint: true
            }
        }
        stage('Production approval') {
            when { expression { params.TARGET == 'production' } }
            steps {
                input message: 'Approve production promotion request?', ok: 'Approve'
            }
        }
        stage('Prepare promotion evidence') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    printf 'target=%s\\ndigest=%s\\n' "$TARGET" "$IMAGE_DIGEST" > promotion-request.txt
                '''
                archiveArtifacts artifacts: 'promotion-request.txt', fingerprint: true
            }
        }
    }
}
```

**Production completion requirements:** The `provenance-verified.marker` must be generated by a trusted verification stage that cryptographically checks the intended digest, not by an untrusted workspace file. The Pipeline must also update the exact overlay to the approved digest **before** rendering and checking it, then create a reviewed PR using a scoped Git app. This example deliberately fails without evidence and does not deploy directly. A manual Jenkins `input` gate is not a substitute for protected branch review.

## 7. Staging acceptance

1. Merge reviewed staging overlay PR.
2. Confirm GitOps observed revision matches Git commit.
3. Confirm live Deployment digest equals verified OCI digest.
4. Check readiness, EndpointSlices, synthetic HTTP and application SLOs.
5. Record rollout duration, error rate, p95 latency and minimum request count.
6. Hold production promotion if metrics are missing, stale or below minimum sample.

A successful GitOps sync is not proof of healthy application behavior.

## 8. Production promotion and strategy

Promote the same digest via a separate production PR. For rolling, configure maxSurge/maxUnavailable and readiness. For blue-green, maintain stable/candidate Deployments and preview routing. For canary, require a supported traffic controller and measured percentage routing. **Kubernetes Services do not implement exact weighted canary traffic.**

If progressive routing is unavailable, mark canary acceptance **blocked** rather than claiming success.

## 9. Drift and policy enforcement

Inject a benign test-only change to a GitOps-owned resource and capture desired/live diff. Confirm the reconciler restores the approved Git state. Validate policy negative cases: mutable tag, privileged container, disallowed registry, missing resources, plaintext secret and unauthorized namespace. Admission must reject unsafe direct mutations as well as CI pre-merge policy checks.

## 10. Fault-injection matrix

| # | Fault | Expected gate/recovery |
|---|---|---|
| 01 | Invalid Helm template | Lint/render fails |
| 02 | Missing chart dependency | Validation blocks |
| 03 | Mutable image tag | Policy rejects |
| 04 | Unsigned/unverified artifact | Provenance gate fails |
| 05 | Jenkins Git PR token denied | Promotion halts |
| 06 | Protected branch bypass attempt | Git blocks |
| 07 | Argo CD repo auth failure | Sync NotReady |
| 08 | Flux GitRepository failure | Reconciliation NotReady |
| 09 | GitOps AppProject/RBAC deny | Sync blocked |
| 10 | Admission rejects privileged Pod | Release blocked |
| 11 | ImagePullBackOff | Readiness gate fails |
| 12 | Readiness probe failure | Rollout halted |
| 13 | ResourceQuota exceeded | Pod admission fails |
| 14 | Blue-green selector mismatch | Preview/cutover fails |
| 15 | Canary weight ineffective | Routing verification fails |
| 16 | SLO regression | Promotion halts/rollback |
| 17 | SLO backend unavailable | Fail closed |
| 18 | Manual kubectl drift | Reconciler restores Git |
| 19 | Helm/GitOps competing ownership | Remove competing writer |
| 20 | Bad production digest | Git revert and reconcile |

## 11. Recovery and rollback

```sh
# Identify desired and live state
kubectl get deployment sample-app -n jenkins-staging -o yaml
kubectl get events -n jenkins-staging --sort-by=.lastTimestamp
# Argo CD if installed
argocd app get sample-app-staging
# Flux if installed
flux get kustomizations -A
```

For GitOps-owned resources, revert the environment Git commit through approved branch protection, confirm the reconciler applies it, and verify the restored digest and SLO recovery. For Helm-owned **non-GitOps** resources, use `helm rollback` to a verified revision. Do not use both paths for the same resources.

Database schema/data changes require an explicit compatibility or forward-fix plan; manifest rollback cannot undo irreversible data writes.

## 12. Observability and cost

Measure CI build duration, policy gate latency, PR approval time, GitOps sync lag, release lead time, deployment success rate, rollback frequency, p95 latency/error budget, drift duration, image pull cost, spare capacity for progressive rollout and logging cost. Include controller/agent, cluster, registry, storage and network costs. Set a documented baseline, not invented production numbers.

## 13. Production runbooks

### A. Release onboarding
1. Approve ownership and trust boundaries.
2. Pin chart/image dependencies and configure protected environment Git.
3. Implement CI verification and policy/admission checks.
4. Configure exactly one GitOps reconciler per resource.
5. Run staging and production synthetic promotions.
6. Test rollback and capture acceptance evidence.

### B. Failed promotion
1. Halt further merges/promotions.
2. Capture Jenkins build, PR, Git commit, digest and controller conditions.
3. Diagnose policy, identity, registry, readiness, capacity or SLO.
4. Restore known-good Git desired state through approved review.
5. Confirm live digest, app health and incident record.

### C. Drift incident
1. Capture desired/live diff and Kubernetes audit actor.
2. Identify direct writer or competing controller.
3. Remove conflicting mutation source.
4. Reconcile authoritative Git.
5. Confirm drift cleared and add preventive control.

### D. Security/policy incident
1. Freeze affected promotion.
2. Revoke exposed Git/cloud credentials or compromised artifact.
3. Inspect signing/provenance and admission/audit logs.
4. Restore least privilege and policy.
5. Review blast radius before reopening pipeline.

### E. Release reliability regression
1. Compare rollout, readiness and SLO metrics with baseline.
2. Identify candidate cohort and traffic weight.
3. Halt promotion or shift traffic to stable via owner.
4. Revert Git if required and validate recovery.
5. Record change and corrective actions.

## 14. 100-point enterprise acceptance scorecard

| Domain | Points |
|---|---:|
| Architecture, ownership and trust boundaries | 10 |
| Jenkins CI, artifact integrity and provenance | 15 |
| Helm chart validation and secure deployment | 10 |
| GitOps staging/production promotion | 15 |
| Progressive deployment and SLO gates | 10 |
| Policy enforcement and access control | 15 |
| Drift detection and recovery | 10 |
| Incident drills and rollback | 10 |
| Observability, FinOps and handover | 5 |
| **Total** | **100** |

Suggested pass: **85/100** plus mandatory gates: verified immutable artifact, protected production review, one deployment owner, denied unsafe admission, healthy staged rollout, fail-closed SLO gate and tested Git rollback. If a controller/feature is unavailable, mark it **not tested**, not passed.

## 15. Final handover

Include architecture/RACI, Jenkinsfile and approved plugin versions, Helm chart/lockfile, environment Git revisions, artifact provenance, policy tests, GitOps sync history, traffic/SLO evidence, 20 fault drills, rollback timing, cost baseline, residual risks and reviewer sign-off.

**Companion:** [Chapter 055 capstone lab](labs/055-jenkins-helm-gitops-enterprise-release-automation-capstone-check.md).  
**Part 11 complete:** Chapters 051–055.  
**Next:** Chapter 056 — Jenkins Security Architecture, Authentication and Authorization (Part 12).
