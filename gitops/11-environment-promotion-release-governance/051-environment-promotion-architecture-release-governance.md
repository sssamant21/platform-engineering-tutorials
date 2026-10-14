# Chapter 051 — Environment Promotion Architecture and Release Governance

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 11:** Environment Promotion and Release Governance  
**Chapter:** 051 / 100  
**Audience:** Platform Engineers, SREs, DevSecOps Engineers, Release Managers

> **Safety:** All examples target disposable development, test, staging and production-*simulation* namespaces. Do not deploy these sample resources to a live production cluster. Promotion is a controlled change to reviewed GitOps desired state; do not use CI runners to bypass Argo CD and write directly to production clusters.

## 1. Learning objectives

After this chapter you can:

1. Explain the distinction between continuous integration, artifact publication, promotion and GitOps reconciliation.
2. Design a promotion chain from development to production with immutable artifacts.
3. Separate environment configuration from application build artifacts.
4. Implement GitLab protected branches, merge-request approval gates and CODEOWNERS.
5. Promote the same image digest across environments with auditable Git commits.
6. Validate release readiness using tests, health checks and post-deployment evidence.
7. Roll back desired state safely while accounting for database/schema changes.
8. Troubleshoot failed promotions, drift, unauthorized releases and stalled reconciliation.

## 2. Reference architecture

```text
Developer -> GitLab source MR -> CI: test/scan/build/sign -> OCI registry
                                    |
                               image digest
                                    |
                         Promotion merge requests
                                    |
                  +-----------------+-----------------+
                  |                 |                 |
               dev Git          staging Git       prod Git
                  |                 |                 |
               Argo CD           Argo CD           Argo CD
                  |                 |                 |
             dev namespace     staging cluster    production cluster
                  |                 |                 |
             smoke tests       integration/SLO     approval + canary
```

**Key rule:** Build the application image once. Promote the **same verified digest**, not a rebuilt image with the same tag. Changes to Helm values, secrets references, feature flags or infrastructure must also be reviewed and tracked because identical images can behave differently under different configuration.

GitLab performs build, test, attest and review. Argo CD continuously reconciles approved GitOps state. Kubernetes admission controls provide an independent enforcement boundary.

## 3. Promotion models and tradeoffs

| Model | Advantages | Risks and controls |
| --- | --- | --- |
| Directory per environment in one repo | Simple diff, common history | Require CODEOWNERS and path-specific review |
| Branch per environment | Strong branch-level restrictions | Drift and complex merges |
| Separate environment repos | Strong ownership/access boundaries | More automation and cross-repo traceability |
| ApplicationSet generator | Consistent multi-cluster templating | Protect selectors and generator inputs |
| Tag-based promotion | Simple release identity | Immutable tag enforcement and provenance needed |

**Recommended training baseline:** one GitOps repository with explicit environment overlays and path-scoped approvals. For organizations requiring stronger production separation, use a dedicated production repository and/or cluster with separate credentials.

## 4. Repository layout

```text
application-source/
  .gitlab-ci.yml
  Dockerfile
  src/
  tests/

gitops-config/
  CODEOWNERS
  apps/demo-web/
    base/
      deployment.yaml
      service.yaml
      kustomization.yaml
    overlays/
      dev/
        kustomization.yaml
      staging/
        kustomization.yaml
      prod/
        kustomization.yaml
  argocd/
    dev-app.yaml
    staging-app.yaml
    prod-app.yaml
  policies/
  evidence/
```

Keep application source and deployment state logically separated. CI should create a promotion merge request to the GitOps repository; it should not have direct permission to mutate the production Kubernetes API.

## 5. Immutable artifact identity

A container digest identifies a particular manifest. A mutable tag such as `latest` or `release` is insufficient to prove that the same artifact was tested and deployed.

Example deployment using a **placeholder digest** (replace it with a real, validated SHA-256 digest from the approved registry):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo-web
  template:
    metadata:
      labels:
        app: demo-web
    spec:
      containers:
        - name: web
          image: registry.example.internal/demo/web@sha256:REPLACE_WITH_64_HEX_CHARACTERS
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
            periodSeconds: 5
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

The placeholder is deliberately not deployable. Use an image that actually serves `/healthz` on port 8080, or adjust the probe and port to the tested application's behavior.

Verify a published digest with the registry's supported tooling (for example `crane digest IMAGE:TAG`) and verify signatures/attestations with your approved policy. Record registry, digest, source commit, CI pipeline and SBOM/provenance references.

## 6. Environment overlays with Kustomize

Create `apps/demo-web/base/kustomization.yaml`:

```yaml
resources:
  - deployment.yaml
  - service.yaml
```

For each environment, maintain a small overlay. Example `apps/demo-web/overlays/staging/kustomization.yaml`:

```yaml
resources:
  - ../../base
namespace: demo-staging
replicas:
  - name: demo-web
    count: 2
images:
  - name: registry.example.internal/demo/web
    digest: sha256:REPLACE_WITH_REAL_64_HEX_DIGEST
```

**Version compatibility:** Confirm the installed Kustomize supports the chosen `images.digest` syntax. The base Deployment image name should match the `images.name` entry. Alternatively use an explicit reviewed image field patch. Do not blindly substitute digests with shell string replacement.

Example `prod` overlay:

```yaml
resources:
  - ../../base
namespace: demo-prod
replicas:
  - name: demo-web
    count: 3
images:
  - name: registry.example.internal/demo/web
    digest: sha256:REPLACE_WITH_SAME_APPROVED_DIGEST
```

Render and inspect each environment before approval:

```bash
kubectl kustomize apps/demo-web/overlays/staging
kubectl kustomize apps/demo-web/overlays/prod
```

Use `kubectl apply --dry-run=server` only against the intended staging API after validating the context and namespace.

## 7. Argo CD Applications and promotion control

Example staging Application:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-staging
  namespace: argocd
spec:
  project: demo-staging
  source:
    repoURL: https://gitlab.example.internal/platform/gitops-config.git
    targetRevision: main
    path: apps/demo-web/overlays/staging
  destination:
    name: staging-cluster
    namespace: demo-staging
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
```

Use a separate production AppProject with approved source repository, destination cluster and namespace. Keep production sync manual where release governance requires explicit approval; if auto-sync is used, the **Git merge** becomes the effective deployment approval boundary. Argo CD RBAC is not a native two-person approval workflow.

For every environment, verify the Application's expected Git revision, image digest, sync state and health. A Healthy application can still be running an older revision if synchronization has not occurred.

## 8. GitLab CI/CD — build once, then propose promotion

Example conceptual CI pipeline; adapt tools, authentication and registry names to your actual runner images and security controls:

```yaml
stages: [test, build, verify, propose]

unit_tests:
  stage: test
  image: python:3.12-slim
  script:
    - python -m pip install -r requirements.txt
    - python -m pytest -q

build_image:
  stage: build
  image: registry.example.internal/ci/approved-builder:VERSION
  script:
    - ./ci/build-and-push.sh
    - ./ci/write-image-digest.sh > image-digest.txt
  artifacts:
    paths: [image-digest.txt]
    expire_in: 7 days

verify_artifact:
  stage: verify
  image: registry.example.internal/ci/approved-security-tools:VERSION
  needs:
    - job: build_image
      artifacts: true
  script:
    - ./ci/verify-signature-sbom-and-policy.sh image-digest.txt

propose_staging:
  stage: propose
  image: registry.example.internal/ci/approved-gitlab-client:VERSION
  needs:
    - job: build_image
      artifacts: true
    - job: verify_artifact
  script:
    - ./ci/create-staging-promotion-mr.sh image-digest.txt
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
```

**Important:** The `./ci/` scripts and internal runner images above are interfaces to implement, not built-in GitLab commands. Production CI must use approved isolated runners, least-privilege GitLab API credentials or job-token-based access where supported, protected variables and reviewed merge requests. The proposal job must **not auto-merge production**.

### Promotion MR requirements

Include source commit, image digest, build pipeline, vulnerability/SBOM results, test evidence, target environment, release notes, deployment window, rollback commit and approvers.

## 9. GitLab governance controls

Use protected branches, CODEOWNERS and required approval rules appropriate to your GitLab tier and deployment model.

Example `CODEOWNERS`:

```text
/apps/demo-web/overlays/dev/       @platform/dev-owners
/apps/demo-web/overlays/staging/   @platform/release-owners
/apps/demo-web/overlays/prod/      @platform/prod-approvers @security/reviewers
/argocd/                           @platform/argocd-admins
/policies/                         @security/reviewers
```

A CODEOWNERS file alone does not enforce approvals. Configure the corresponding protected branch and approval settings, prevent self-approval where required, and test that unauthorized actors cannot bypass the rules. Ensure CI identities cannot push directly to protected production paths.

## 10. Hands-on lab A — Promote a verified digest from dev to staging

**Prerequisites:** a disposable staging cluster, working demo application, a real image digest, Argo CD AppProject and GitLab test repository.

1. Build and test the application once.
2. Publish the image to the approved registry.
3. Capture its digest, provenance and test results.
4. Open a GitLab MR changing only the staging overlay's digest.
5. Run render, policy and security checks.
6. Obtain required staging approvals.
7. Merge the MR and refresh the staging Argo CD Application.
8. Sync through the approved policy and validate health.

```bash
kubectl kustomize apps/demo-web/overlays/staging
argocd app get demo-staging --refresh
argocd app diff demo-staging
# Only after the approved merge and if manual sync is required:
argocd app sync demo-staging
argocd app wait demo-staging --sync --health --timeout 300
argocd app history demo-staging
```

**Pass:** the expected digest is deployed, both readiness and application health checks pass, and the release can be traced to the GitLab MR and source pipeline.

## 11. Hands-on lab B — Staging-to-production approval gate

Use `demo-prod` as a **production simulation**, not a real production cluster.

1. Verify the staging Application is Synced and Healthy at the candidate digest.
2. Attach integration test, smoke test, performance and security evidence to a production promotion MR.
3. Update only the production overlay digest to the **same** staging-tested digest.
4. Require independent production approvers and protected branch checks.
5. Confirm the production AppProject restricts sources and destinations.
6. Merge in the approved change window.
7. Reconcile and verify production-simulation health, digest and audit history.

**Pass:** unauthorized direct writes or unapproved merges are rejected, and the deployed digest matches the staging-tested digest exactly.

## 12. Hands-on lab C — Rollback a failed promotion

In the production-simulation environment, deliberately deploy a known-bad **test** image that fails readiness. Never inject this into customer-serving infrastructure.

1. Record the last known-good digest and Git commit.
2. Promote the failing digest through the staging test workflow.
3. Observe Kubernetes readiness failures and Argo CD Degraded/Progressing state.
4. Revert the GitOps overlay to the previously approved digest using a reviewed Git revert MR.
5. Reconcile and verify the original healthy digest is restored.
6. Record detection, mitigation and recovery time.

```bash
argocd app get demo-prod
argocd app history demo-prod
kubectl --context PROD_SIM_CONTEXT -n demo-prod get deploy,pods
kubectl --context PROD_SIM_CONTEXT -n demo-prod describe deploy demo-web
# After approved Git revert:
argocd app sync demo-prod
argocd app wait demo-prod --sync --health --timeout 300
```

**Caution:** Git rollback of a container digest does not reverse destructive database migrations, external side effects, feature-flag changes or secret rotations. Design forward-compatible schema changes and separate rollback procedures for stateful systems.

## 13. Hands-on lab D — Detect and block unauthorized production changes

Attempt, using a low-privilege staging test identity, to:

- Push directly to the protected production branch.
- Merge a production promotion without required approvals.
- Change the production Application source repository.
- Sync a production Application outside the user's authorized Project.
- Change a Kubernetes Deployment directly and observe audit/drift.

Expected: GitLab and Argo CD reject unauthorized actions; Kubernetes audit logs identify any direct API write; drift is detected or reconciled. Do not use a privileged administrator account to represent an unprivileged test.

## 14. Promotion evidence and audit trail

Record the complete chain:

```text
Source commit SHA:
CI pipeline ID:
Image registry and SHA-256 digest:
Signature/provenance/SBOM reference:
Staging promotion MR:
Staging deployed Git revision:
Staging tests and SLO evidence:
Production promotion MR:
Required approvers:
Approved deployment window:
Production deployed Git revision:
Observed running image digest:
Argo CD sync/health outcome:
Rollback commit and runbook:
Incident/change ticket:
```

Do not store sensitive tokens, unredacted Kubernetes Secrets or raw credential-bearing logs in evidence repositories.

## 15. Release readiness gates

| Gate | Required evidence | Failure response |
| --- | --- | --- |
| Unit/integration tests | CI results | Block promotion |
| Vulnerability and provenance policy | Approved scan/signature outcome | Block or document approved exception |
| Manifest rendering | Helm/Kustomize render and schema checks | Fix before merge |
| Policy/admission | Namespace, privilege and image rules | Block promotion |
| Staging health | Ready workloads, smoke tests | Stop promotion |
| Staging SLO/performance | Latency, errors, resource use | Investigate regression |
| Approval governance | Protected MR and approver evidence | Reject unauthorized change |
| Production post-deploy | Expected digest, health, monitoring | Initiate rollback/mitigation |

## 16. Production runbook — release promotion

**Preflight:** validate approved change ticket, target cluster/context, image digest, dependency compatibility, migration plan, monitoring, rollback owner and freeze windows.

**Execution:** merge reviewed GitOps promotion MR, monitor Argo CD reconciliation, verify deployment health and observed digest, then run application smoke tests.

**Post-release:** record actual deployment revision, service-level metrics, customer impact and closure evidence. Avoid running direct `kubectl apply` from CI as an undocumented fallback.

## 17. Production runbook — failed or stalled promotion

```bash
argocd app get APP_NAME --refresh
argocd app diff APP_NAME
argocd app history APP_NAME
kubectl --context TARGET_CONTEXT -n TARGET_NAMESPACE get deploy,pods,events
kubectl --context TARGET_CONTEXT -n TARGET_NAMESPACE describe deploy DEPLOYMENT_NAME
```

1. Determine whether the failure is Git/registry access, manifest generation, admission rejection, Kubernetes scheduling, readiness, image pull or Argo CD authorization.
2. Pause subsequent promotions to the affected environment.
3. Assess customer impact and determine rollback versus forward fix.
4. Revert the GitOps desired state through the approved workflow when safe.
5. Verify the previous digest and health; inspect database compatibility before rolling back stateful components.
6. Record incident timeline, corrective action and updated release gate.

## 18. Troubleshooting — ten common promotion failures

| # | Symptom | Likely cause | Recovery |
| --- | --- | --- | --- |
| 1 | Dev passes, staging fails | Environment configuration drift | Diff overlays, secrets and dependencies |
| 2 | Same tag, different behavior | Mutable image tag/rebuild | Pin and verify immutable digest |
| 3 | Argo CD remains OutOfSync | Manual sync, failed render, stale revision | Check app status and sync policy |
| 4 | Production MR bypassed approval | Branch/approval misconfiguration | Restore protection, audit changes |
| 5 | ImagePullBackOff | Registry auth, missing digest, policy | Verify digest and image pull access |
| 6 | Deployment unhealthy | Readiness/startup/resource issue | Inspect pod events and app logs |
| 7 | AppProject rejects deployment | Source/destination not approved | Correct authorized Project configuration |
| 8 | Rollback fails | Schema or external state incompatibility | Follow stateful recovery/forward fix |
| 9 | CI can modify production directly | Overprivileged runner/token | Revoke scope, enforce GitOps boundary |
| 10 | Audit cannot link release to MR | Missing digest/revision evidence | Repair release metadata collection |

## 19. Rollback, recovery and cleanup

Prefer a reviewed Git revert of the promotion commit. Avoid manually changing live resources when Argo CD will immediately reconcile them back. If emergency manual intervention is unavoidable, record the change and promptly reconcile the source of truth afterward.

Cleanup only capstone-owned staging resources and CI credentials. Preserve release evidence and audit records per organizational retention requirements. Never delete shared Argo CD Projects, cluster registrations or production namespaces to finish a lab.

## 20. Acceptance checklist

- [ ] Application image is built once and promoted by immutable digest.
- [ ] Dev, staging and production overlays are version controlled.
- [ ] GitLab protected branches and CODEOWNERS approvals are enforced.
- [ ] CI cannot directly deploy to the production Kubernetes API.
- [ ] Argo CD Projects restrict source repositories and destinations.
- [ ] Promotion MR records tests, digest, approvers and rollback reference.
- [ ] Staging and production-simulation deployments use the identical digest.
- [ ] Post-deployment health and observed digest are verified.
- [ ] Unauthorized production promotion tests are denied.
- [ ] Failed release rollback exercise succeeds within a measured objective.
- [ ] Database/schema compatibility is included in rollback planning.
- [ ] Audit evidence correlates GitLab, registry, Argo CD and Kubernetes.
- [ ] Runbooks, change windows and release ownership are documented.

## 21. Knowledge check

1. Why must promotion use an immutable digest rather than a mutable tag?
2. What is the difference between CI artifact publication and GitOps deployment?
3. Why does an Argo CD Healthy state alone not prove the latest approved revision is running?
4. Which GitLab controls enforce two-person production review?
5. How should a production release be rolled back when a database migration is not reversible?
6. Why is direct Kubernetes access from a CI runner a governance risk?
7. What evidence links source commit, image digest, promotion MR and live deployment?
8. When does an auto-sync Git merge become the effective production deployment gate?

## 22. References

- [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Argo CD Applications](https://argo-cd.readthedocs.io/en/stable/user-guide/application-specification/)
- [Argo CD Projects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)
- [GitLab Protected Branches](https://docs.gitlab.com/user/project/repository/branches/protected/)
- [GitLab Code Owners](https://docs.gitlab.com/user/project/codeowners/)
- [GitLab Merge Request Approvals](https://docs.gitlab.com/user/project/merge_requests/approvals/)
- [Kubernetes Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)

---

**Chapter 051 complete.** Next: **Chapter 052 — GitLab Promotion Pipelines, Approval Gates and Release Automation**.
