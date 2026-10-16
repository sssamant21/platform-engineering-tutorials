# Chapter 054 — Jenkins GitOps Promotion, Drift Detection and Policy Enforcement

**Part 11 — Helm, Kubernetes Deployment and GitOps**  
**Audience:** Jenkins SRE, GitOps/platform engineering, security and release governance  
**Prerequisites:** Chapters 051–053; Jenkins, protected Git environment repository, disposable Kubernetes cluster, Argo CD or Flux and a policy engine or CI policy checker.

## Learning outcomes

Implement a secure staging-to-production GitOps promotion process, detect unauthorized drift, enforce policies before merge and at admission, verify signed immutable images, design fail-closed release gates, and respond to reconciliation and policy incidents.

## 1. Enterprise promotion architecture

```text
Application commit
  → Jenkins build/test/scan/SBOM/sign
  → immutable OCI digest
  → staging PR (policy + reviewers)
  → GitOps staging sync + SLO checks
  → production PR (separate approvers)
  → GitOps production sync + monitoring
  → rollback by reviewed Git revert
```

Jenkins proposes changes; **Argo CD or Flux owns deployment reconciliation**. Do not run `helm upgrade` from Jenkins against the same objects. Protected production branches must not be writable by an untrusted pull-request job.

## 2. Trust and separation of duties

| Actor | Allowed | Prohibited |
|---|---|---|
| CI Jenkins agent | Build/test, publish scoped artifact, propose PR | Direct production Kubernetes mutation |
| Release Jenkins agent | Verify provenance and request promotion | Bypass protected reviews |
| Git reviewer | Approve change with policy evidence | Approve own change where prohibited |
| Argo CD/Flux | Reconcile approved Git state | Read arbitrary unrelated namespaces |
| Policy controller | Validate admission constraints | Store long-lived registry secrets |
| On-call | Authorized incident rollback | Silent uncontrolled hotfix |

Use short-lived Git app credentials where available, CODEOWNERS, branch protection, signed commits where required and audit logs.

## 3. Environment repository

```text
environment-repo/
  apps/
    sample-app/
      base/
        deployment.yaml
        service.yaml
        kustomization.yaml
      overlays/
        staging/
          kustomization.yaml
        production/
          kustomization.yaml
  policies/
    image-digest.rego
  docs/
    release-evidence-template.md
```

A single Git commit identifies desired state. Production promotion should carry the **same verified digest** that passed staging acceptance, not rebuild an image from a mutable tag.

## 4. Kustomize image pinning

`apps/sample-app/overlays/staging/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: jenkins-staging
resources:
  - ../../base
images:
  - name: registry.example.test/training/sample-app
    newName: registry.example.test/training/sample-app
    digest: sha256:REPLACE_WITH_REAL_DIGEST
```

The base Deployment image must use the matching image name so Kustomize can rewrite it. Verify rendered output with `kubectl kustomize`; never assume an overlay changed the intended container.

```sh
kubectl kustomize apps/sample-app/overlays/staging > rendered-staging.yaml
grep -n 'image:' rendered-staging.yaml
```

Do not use the placeholder digest in a real deployment. Image digest is an integrity reference, not proof of signature or provenance.

## 5. CI policy: require digest-pinned images

Example Rego policy for `conftest` evaluating individual Kubernetes Deployment YAML documents:

```rego
package main

deny contains msg if {
  input.kind == "Deployment"
  some container in input.spec.template.spec.containers
  not regex.match("@sha256:[a-f0-9]{64}$", container.image)
  msg := sprintf("container %s must use immutable sha256 digest", [container.name])
}
```

This example uses **OPA Rego v1 syntax** and a Conftest/OPA version supporting it. The rule intentionally focuses on Deployments; extend coverage to StatefulSets, DaemonSets, Jobs, CronJobs and initContainers. A digest-only rule does not verify a signature or allowlist the registry. Test with policy unit tests and pin policy tool versions.

```sh
kubectl kustomize apps/sample-app/overlays/staging > rendered-staging.yaml
conftest test rendered-staging.yaml --policy policies/
```

Conftest evaluates YAML documents and reports policy failures. Confirm the installed version's YAML handling and `deny` conventions in your lab.

## 6. Additional policy gates

- Approved registry/repository allowlist.
- Signed image and provenance verification with approved signer identities.
- Nonroot, seccomp RuntimeDefault, no privilege escalation, dropped capabilities.
- CPU/memory requests and limits, probes, minimum replicas and PDBs where appropriate.
- No privileged Pods, hostPath, hostNetwork or hostPID unless explicitly approved.
- Namespaced RBAC and allowed ServiceAccount.
- No plaintext secrets in Git, Jenkins logs or artifacts.
- NetworkPolicy and external-secret integration.
- Change ticket, CODEOWNERS approval and environment freeze windows.
- Policy exceptions must be scoped, time-bound, reviewed and audited.

Use both **pre-merge checks** and admission controls (Kyverno, Gatekeeper or equivalent). CI checks can be bypassed outside Git; admission catches unauthorized cluster mutations, while admission alone does not ensure reviewed change provenance.

## 7. Jenkins promotion Pipeline

This example validates a candidate digest and prepares an auditable promotion request. PR creation requires a provider-specific integration and is intentionally a separate controlled step.

```groovy
pipeline {
    agent { label 'trusted-gitops-release' }
    parameters {
        string(name: 'IMAGE_DIGEST', defaultValue: '', description: 'Staging-verified sha256 digest')
        choice(name: 'TARGET', choices: ['staging', 'production'])
    }
    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
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
                echo 'Integrate approved cosign/SBOM/provenance verification; fail if unavailable'
            }
        }
        stage('Render and policy test') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    kubectl kustomize apps/sample-app/overlays/"$TARGET" > rendered.yaml
                    conftest test rendered.yaml --policy policies/
                '''
                archiveArtifacts artifacts: 'rendered.yaml', fingerprint: true
            }
        }
        stage('Approval') {
            when { expression { params.TARGET == 'production' } }
            steps {
                input message: 'Approve production promotion request?', ok: 'Approve'
            }
        }
        stage('Prepare PR evidence') {
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

**This is a scaffold, not a complete production promotion pipeline.** The supplied `IMAGE_DIGEST` is not written into the overlay by this example; production must add a reviewed YAML-aware update step and re-render **after** that update. The provenance stage is a placeholder and must be replaced by real fail-closed verification. Jenkins `input` does not replace Git branch protection or required approvers.

## 8. Drift detection

**Argo CD:**

```sh
argocd app get sample-app-staging
argocd app diff sample-app-staging
argocd app history sample-app-staging
```

**Flux:**

```sh
flux get sources git -A
flux get kustomizations -A
kubectl get kustomization -n flux-system sample-app-staging -o yaml
```

Capture Git desired revision, observed live object, diff, sync/reconciliation status, actor and duration. Ignore expected controller-managed fields through narrowly scoped diff customizations, not broad ignore-all rules. A manual patch can be reverted by reconciliation and should not become the incident's permanent fix.

## 9. Promotion verification

Before production merge, require: staging sync at exact digest, healthy rollout, minimum sample count, acceptable error rate/p95 latency, security checks, approved change window and reviewed rollback plan. If telemetry is stale or unavailable, **hold promotion**. Production post-sync monitoring should include error-budget burn and automated alerts, with a human decision for irreversible operations.

## 10. Rollback

A Git revert (or reviewed commit restoring a known-good digest) is the normal GitOps rollback:

```sh
git log --oneline -- apps/sample-app/overlays/production
git revert <PROMOTION_COMMIT_SHA>
git push origin <REVIEW_BRANCH>
```

Open a protected PR and merge after required checks; do not push directly to production. The example commands assume a suitable local branch and permissions. Confirm the GitOps controller observes the revert and the live Deployment runs the restored digest. Schema and data changes may require forward-fix rather than rollback.

## 11. Troubleshooting matrix

| Failure | Evidence | Recovery |
|---|---|---|
| Conftest rejects digest | Policy output | Pin correct digest |
| OPA syntax error | Compiler/version | Fix policy/version |
| Signature verification fails | Signer/provenance | Quarantine artifact |
| PR rejected | Git API/branch policy | Correct scoped access |
| Reviewer missing | CODEOWNERS | Route approval |
| Staging sync delayed | GitOps status | Repair reconciliation |
| Argo CD OutOfSync | Diff | Review desired/live |
| Flux Kustomization failed | Conditions/events | Fix source/manifest |
| Drift repeatedly returns | Audit logs | Remove competing writer |
| Admission webhook denies | Policy events | Harden manifest |
| SLO data missing | Monitoring | Fail closed |
| Wrong digest in production | Live image/commit | Revert through Git |
| Secret leaked in Git | Audit/history | Revoke/rotate |
| Emergency hotfix reverted | Controller logs | Update Git desired state |
| Policy exception expired | Exception inventory | Reapprove or remediate |
| Rollback breaks schema | DB compatibility | Forward-fix/restore plan |

## 12. Production runbooks

### A. Staging-to-production promotion
1. Verify artifact digest, signature and provenance.
2. Confirm staging sync and SLO acceptance.
3. Prepare production overlay PR using exact tested digest.
4. Run policy, manifest and security checks.
5. Obtain protected review/change approval.
6. Merge, observe reconciliation and monitor SLOs.
7. Archive evidence and rollback reference.

### B. Drift incident
1. Capture desired Git commit and live object.
2. Identify writer through audit logs.
3. Check controller sync and diff customization.
4. Remove competing mutations and reconcile approved Git.
5. Verify drift clears and record RCA.

### C. Policy bypass attempt
1. Block promotion and preserve audit evidence.
2. Identify bypassed CI/admission/branch protection.
3. Revoke inappropriate access and restore controls.
4. Validate policy tests and admission enforcement.
5. Perform security review before resuming.

### D. Failed production promotion
1. Halt further changes and capture GitOps/controller conditions.
2. Diagnose image, policy, scheduling, health or identity.
3. Revert to known-good digest through approved Git workflow.
4. Confirm live image, readiness and SLO recovery.
5. Record customer impact and corrective actions.

### E. Emergency change
1. Declare incident and assign incident commander.
2. Identify minimal scoped change and owner.
3. Record emergency approval and desired Git commit.
4. Apply via GitOps where feasible; if direct patch is unavoidable, reconcile Git promptly.
5. Validate and document post-incident review.

## 13. Acceptance criteria

- [ ] Jenkins cannot directly mutate production workloads.
- [ ] Staging-to-production promotion uses same verified digest.
- [ ] Protected PR and required approvers enforced.
- [ ] Policy tests reject mutable/unsigned or disallowed artifacts.
- [ ] Admission controls block unsafe direct changes.
- [ ] Drift detected, attributed and reconciled.
- [ ] Missing SLO data blocks promotion.
- [ ] Git-based rollback and audit chain demonstrated.

**Companion:** [Chapter 054 hands-on lab](labs/054-jenkins-gitops-promotion-drift-detection-policy-enforcement-check.md).  
**Next:** Chapter 055 — Jenkins Helm and GitOps Enterprise Release Automation Capstone.
