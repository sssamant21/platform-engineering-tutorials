# Chapter 052 — GitLab Promotion Pipelines, Approval Gates and Release Automation

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 11:** Environment Promotion and Release Governance  
**Chapter:** 052 / 100  
**Audience:** Platform Engineers, DevSecOps, SREs and Release Managers

> **Safety:** Use a disposable GitLab project, registry and staging Kubernetes cluster for labs. Example tokens, URLs and image digests are placeholders. Never give a CI runner direct production cluster-admin credentials or allow an automated job to bypass protected production branch approvals.

## 1. Learning objectives

By the end of this chapter, you can:
1. Design a pipeline that builds an artifact once and promotes its immutable digest.
2. Separate application-source pipelines from GitOps configuration changes.
3. Create promotion merge requests using scoped GitLab API credentials.
4. Enforce protected environments, branches, CODEOWNERS and approval rules.
5. Validate deployment state after Argo CD reconciliation.
6. Implement idempotency, concurrency controls and safe retries.
7. Troubleshoot common CI, approval, Git and Argo CD failures.
8. Demonstrate rollback and audit evidence in a staging release exercise.

## 2. Enterprise release workflow

```text
Source MR -> tests -> build -> SBOM/sign/scan -> registry digest
                                               |
                                        release metadata
                                               |
                           GitLab API creates GitOps promotion MR
                                               |
                         CI render/policy tests + CODEOWNERS review
                                               |
                             protected branch merge/approval
                                               |
                                 Argo CD observes Git revision
                                               |
                          sync -> readiness -> smoke test -> evidence
                                               |
                              next environment promotion MR
```

The CI system proposes changes; GitOps defines desired state; Argo CD reconciles it. **Do not equate a successful pipeline with a successful Kubernetes rollout.** Promotion success requires verifying the intended revision and actual running digest.

## 3. Prerequisites and version-sensitive controls

- GitLab repository with protected default branch and merge-request approvals.
- Separate GitOps repository or protected environment paths.
- A container registry with immutable digest access.
- Argo CD staging Application and restrictive AppProject.
- Approved runner images with pinned versions and no privileged Docker socket by default.
- Scoped GitLab API credential or supported job-token access to create merge requests.
- Optional GitLab protected environments and deployment approvals, depending on edition/tier.
- `kubectl`, `argocd`, `jq`, `git`, `curl`, `sha256sum` for local validation.

GitLab features and API permissions vary by version, tier and token type. Confirm supported protected-environment deployment approvals and API access in your installation before relying on them.

## 4. Recommended repositories

```text
demo-web-source/
  .gitlab-ci.yml
  Dockerfile
  ci/
    build.sh
    verify.sh
    create-promotion-mr.sh
    validate-release.sh
  tests/

gitops-config/
  CODEOWNERS
  apps/demo-web/overlays/
    dev/kustomization.yaml
    staging/kustomization.yaml
    prod/kustomization.yaml
  argocd/
    dev.yaml
    staging.yaml
    prod.yaml
  release-metadata/
    release-2026-001.yaml
```

Use immutable image digests in overlays, and store non-sensitive release metadata such as source commit, registry digest, CI pipeline URL and change ticket.

## 5. Promotion state machine

| State | Entry condition | Next step | Failure handling |
| --- | --- | --- | --- |
| Built | CI published immutable image | Verify artifact | Stop on build error |
| Verified | Tests, scan, signature/provenance pass | Create staging MR | Block on policy failure |
| Proposed | GitOps MR opened | Review and approve | Leave MR open for correction |
| Approved | Required checks and reviewers passed | Merge protected branch | Block unauthorized merge |
| Reconciled | Argo CD synced expected Git revision | Check health and digest | Diagnose sync failure |
| Validated | Smoke/SLO checks pass | Propose next environment | Hold on regression |
| Released | Production approval and validation pass | Archive evidence | Monitor and close |
| Reverted | Reviewed GitOps revert merged | Validate restored revision | Escalate if rollback fails |

Never automatically promote to the next environment solely because an earlier CI job completed. The previous environment must have verifiable deployment and health evidence.

## 6. Example GitLab CI pipeline

This is an **integration skeleton**: internal runner images and the `ci/*.sh` scripts must be implemented, reviewed and pinned before use.

```yaml
stages:
  - test
  - build
  - verify
  - propose

default:
  interruptible: true

variables:
  GIT_STRATEGY: fetch

unit_test:
  stage: test
  image: python:3.12-slim
  script:
    - python -m pip install -r requirements.txt
    - python -m pytest -q

build_image:
  stage: build
  image: registry.example.internal/ci/secure-builder:PINNED_VERSION
  script:
    - ./ci/build.sh
  artifacts:
    paths:
      - release.env
    reports:
      dotenv: release.env
    expire_in: 7 days

verify_image:
  stage: verify
  image: registry.example.internal/ci/security-tools:PINNED_VERSION
  needs:
    - job: build_image
      artifacts: true
  script:
    - ./ci/verify.sh

propose_staging:
  stage: propose
  image: registry.example.internal/ci/gitlab-client:PINNED_VERSION
  needs:
    - job: build_image
      artifacts: true
    - job: verify_image
  resource_group: staging-promotion
  script:
    - ./ci/create-promotion-mr.sh staging
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
```

The `release.env` artifact must contain **only non-secret values**, e.g. `IMAGE_DIGEST=sha256:...` and `SOURCE_SHA=...`. Never place API tokens in dotenv artifacts: artifacts can be downloaded by users with appropriate project access.

### CI security requirements

- Pin runner images and dependencies; use approved build tooling.
- Separate protected production credentials from untrusted merge-request pipelines.
- Use protected/masked variables or short-lived credentials where supported.
- Avoid exposing secrets to fork pipelines and unreviewed CI definitions.
- Restrict who can edit `.gitlab-ci.yml`, release scripts and runner configuration.
- Set runner egress restrictions and isolate untrusted builds.
- Enforce signature, provenance and vulnerability policy before proposal.

## 7. Release metadata contract

A promotion job should receive structured, validated inputs:

```yaml
apiVersion: platform.example/v1
kind: ReleaseRecord
metadata:
  name: demo-web-2026-001
spec:
  application: demo-web
  sourceCommit: REPLACE_WITH_GIT_SHA
  image: registry.example.internal/demo/web
  digest: sha256:REPLACE_WITH_64_HEX_CHARACTERS
  buildPipeline: https://gitlab.example.internal/platform/demo-web/-/pipelines/123
  targetEnvironment: staging
  changeTicket: CHANGE-1234
```

The example is a repository document, **not** a Kubernetes custom resource to apply. Validate the digest with `^sha256:[a-f0-9]{64}$`, the source commit format and allowed environment values. Use a stable release identifier to avoid duplicate merge requests on retry.

## 8. Create a promotion merge request via GitLab API

The following shell illustrates a **staging-only** workflow. Use a GitLab API credential with only the required project permissions; `GITLAB_TOKEN` must be injected securely by the runner. Never print it.

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${GITLAB_URL:?required}"
: "${GITOPS_PROJECT_ID:?required}"
: "${GITLAB_TOKEN:?required}"
: "${RELEASE_ID:?required}"

TARGET_BRANCH="main"
SOURCE_BRANCH="promote/staging/${RELEASE_ID}"

# 1. Fetch the protected GitOps repository using approved Git credentials.
# 2. Create SOURCE_BRANCH from the latest TARGET_BRANCH.
# 3. Change only the staging overlay to the verified image digest.
# 4. Commit with release ID, source SHA and digest.
# 5. Push the branch with a scoped identity.

# 6. Propose the MR; URL-encode user-controlled values with jq.
payload="$(jq -n \
  --arg source "$SOURCE_BRANCH" \
  --arg target "$TARGET_BRANCH" \
  --arg title "Promote demo-web to staging: $RELEASE_ID" \
  '{source_branch:$source,target_branch:$target,title:$title,remove_source_branch:true}')"

curl --fail-with-body --silent --show-error \
  --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  --header "Content-Type: application/json" \
  --data "$payload" \
  "$GITLAB_URL/api/v4/projects/$GITOPS_PROJECT_ID/merge_requests"
```

**Idempotency:** Before creating a branch/MR, query for an existing open MR with the same release ID and target environment. If it exists, update or reuse it rather than creating duplicates. Handle HTTP 409 conflicts, protected branch failures, rate limits and retries with bounded exponential backoff. For production, never auto-merge an MR without required independent approvals.

## 9. Protected branches, CODEOWNERS and approvals

Example `CODEOWNERS`:

```text
/apps/demo-web/overlays/dev/       @platform/dev-owners
/apps/demo-web/overlays/staging/   @platform/release-owners
/apps/demo-web/overlays/prod/      @platform/prod-approvers @security/reviewers
/argocd/                           @platform/argocd-admins
/.gitlab-ci.yml                    @platform/ci-admins
/ci/                               @platform/ci-admins
```

Configure GitLab protected branches and merge request approval rules. Verify the installed tier supports required approval enforcement, and test that the release bot cannot approve its own MR or bypass protected branch restrictions.

**Two distinct gates:**
1. **GitOps MR approval** controls desired state entering a protected branch.
2. **Deployment approval** (if enabled and supported) controls a GitLab deployment job.

An Argo CD auto-sync Application will deploy after the Git merge without waiting for a GitLab deployment job. Therefore, GitLab deployment approvals do not automatically gate Argo CD auto-sync. Design the effective release boundary explicitly: protected Git merge, manual Argo CD sync with controlled RBAC, or an integrated approval controller.

## 10. Promotion concurrency and retry design

Use GitLab `resource_group` for promotion proposal jobs that target the same environment. This serializes those jobs within the relevant project; it does **not** serialize independent Argo CD reconciliations or jobs in other projects.

Additional safeguards:
- Compare-and-swap against the latest GitOps branch HEAD before committing.
- Ensure a candidate release is still the intended next release.
- Prevent an older retry from overwriting a newer approved digest.
- Avoid mixing infrastructure and application promotions in one unreviewable MR.
- Add a release lock or policy check at the GitOps merge boundary if multiple pipelines target the same environment.

## 11. Hands-on lab A — Build and verify an immutable release

**Goal:** produce a traceable release record without exposing secrets.

1. Run unit and integration tests.
2. Build and publish an image using the approved builder.
3. Resolve its registry digest.
4. Generate an SBOM and perform vulnerability/signature checks.
5. Produce `release.env` containing only the digest and source commit.
6. Confirm digest syntax and source-to-artifact traceability.

```bash
grep '^IMAGE_DIGEST=' release.env
grep '^SOURCE_SHA=' release.env
# Never cat the complete CI environment or masked variables.
```

**Pass:** artifact exists, digest is immutable and security gates pass; the release record contains no credentials.

## 12. Hands-on lab B — Staging promotion MR

1. Use the verified digest from Lab A.
2. Create a new GitOps branch from the protected default branch.
3. Change only the staging overlay.
4. Render the staging manifests and run policy checks.
5. Open an MR with evidence and required reviewers.
6. Merge after approvals.
7. Refresh and reconcile the staging Application.

```bash
kubectl kustomize apps/demo-web/overlays/staging
argocd app get demo-staging --refresh
argocd app diff demo-staging
# If the Application uses manual sync, and after approval:
argocd app sync demo-staging
argocd app wait demo-staging --sync --health --timeout 300
argocd app history demo-staging
```

**Pass:** expected Git revision and image digest are deployed; smoke tests pass; GitLab MR and Argo CD history identify the release.

## 13. Hands-on lab C — Production approval denial test

Use a production-*simulation* GitLab environment and cluster.

1. Attempt direct push to the protected production branch with a developer identity.
2. Attempt to merge a production promotion MR without required approvals.
3. Attempt to approve a bot-authored MR with the same identity if self-approval is prohibited.
4. Attempt to trigger a protected deployment job without authorization (where supported).
5. Confirm every unauthorized operation is denied and logged.

**Pass:** no production-simulation desired state changes and audit evidence identifies each denied action. Do not test using an administrator identity.

## 14. Hands-on lab D — Retry and race-condition exercise

Simulate two staging promotions, release A and release B, both based on the same GitOps HEAD.

1. Open A's promotion MR.
2. Open B's promotion MR.
3. Merge B first after review.
4. Attempt to complete A with stale assumptions.
5. Verify the system detects a conflict or rejects an outdated release.
6. Rebase/revalidate A only if business release ordering requires it.

**Pass:** an old retry cannot silently overwrite a newer approved digest.

## 15. Hands-on lab E — Rollback and release evidence

In production simulation, promote a deliberately unhealthy test image and observe failed readiness. Revert the GitOps overlay to a known-good digest through a reviewed MR. Reconcile and validate actual running image digest, readiness and application health.

```bash
argocd app get demo-prod
argocd app history demo-prod
kubectl --context PROD_SIM_CONTEXT -n demo-prod get deployment,pods
# After reviewed revert:
argocd app sync demo-prod
argocd app wait demo-prod --sync --health --timeout 300
```

**Pass:** recovery meets the measured objective and records the exact restored digest. Note that Git revert does not reverse database schema migrations or external state changes.

## 16. Release evidence and post-deployment verification

Record:

```text
Release ID:
Source commit:
CI pipeline ID:
Image registry and digest:
SBOM / signature / scan outcome:
Promotion MR URL and reviewers:
GitOps merge commit:
Argo CD Application and deployed revision:
Observed running image digest:
Smoke test / SLO outcome:
Deployment time and recovery objective:
Rollback commit:
Change ticket:
Evidence links (redacted):
```

A successful `argocd app wait --health` is necessary but insufficient by itself. Compare expected and actual revision, verify workload image digests and run application-level tests.

## 17. Troubleshooting matrix — ten failures

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Promotion API returns 401/403 | Token scope or protected resource | Verify identity and project permissions |
| 2 | MR creation returns 409 | Duplicate branch/MR | Reuse or update existing release MR |
| 3 | MR cannot merge | Approval or pipeline policy | Resolve required gates; do not bypass |
| 4 | CODEOWNERS not enforced | Approval settings/tier misconfigured | Configure and test enforcement |
| 5 | Old digest overwrites new | Stale branch/race condition | Add HEAD check and release ordering |
| 6 | Argo CD remains OutOfSync | Manual sync or render error | Inspect Application and sync policy |
| 7 | Deployment is Synced but unhealthy | Readiness, image, admission, resource failure | Investigate Kubernetes events/logs |
| 8 | Artifact digest unavailable | Registry publish/retention issue | Restore verified artifact, block promotion |
| 9 | CI job passes but production never deploys | Approval boundary or Argo CD issue | Trace Git revision and reconciliation |
| 10 | Rollback restores image but not service | Stateful/schema incompatibility | Follow data migration recovery plan |

## 18. Production runbook — approved promotion

**Preflight:** confirm immutable digest, verified signature/SBOM, staging tests, change window, production approvers, expected Git revision and rollback plan.

**Execute:** create the promotion MR, pass render/policy checks, obtain approvals, merge the protected branch and allow the approved Argo CD sync path to reconcile.

**Validate:** verify target revision, observed digest, Kubernetes rollout, smoke tests, latency/errors and audit records. Record release completion only after deployment validation.

## 19. Production runbook — failed release automation

```bash
argocd app get APP_NAME --refresh
argocd app diff APP_NAME
argocd app history APP_NAME
kubectl --context TARGET_CONTEXT -n TARGET_NAMESPACE get deploy,pods,events
```

1. Identify whether failure occurred in build, registry, GitLab API, MR policy, Git merge, Argo CD reconciliation or Kubernetes rollout.
2. Pause additional promotions to the affected environment.
3. Preserve pipeline, MR, Git commit and Argo CD operation evidence.
4. Fix the specific dependency or revert desired state through reviewed Git.
5. Validate the restored revision, running digest and service-level health.
6. Document detection gap, root cause and prevention owner.

Never temporarily grant cluster-admin to the CI runner as a workaround.

## 20. Rollback and cleanup

Use a reviewed Git revert to restore a previously verified digest. Re-check database and API compatibility before reverting stateful changes. If an emergency manual change is required, record the exception and reconcile Git to the final desired state.

Delete only lab-created promotion branches, disposable Applications and temporary CI identities after confirming no other team depends on them. Preserve redacted release evidence under the approved retention policy.

## 21. Acceptance criteria

- [ ] Build-once/promote-by-digest workflow implemented.
- [ ] Pipeline does not expose credentials in artifacts or logs.
- [ ] Promotion job creates a reviewed GitOps MR, not a direct Kubernetes deployment.
- [ ] Protected branch and CODEOWNERS approvals are tested.
- [ ] Production approval cannot be bypassed by release automation.
- [ ] Environment concurrency and stale-release handling are tested.
- [ ] Staging and production simulation deploy identical approved digests.
- [ ] Argo CD revision, workload digest and health are validated.
- [ ] Unauthorized promotion tests are denied and audited.
- [ ] Failed deployment rollback is measured and documented.
- [ ] Stateful rollback limitations and release owners are recorded.
- [ ] End-to-end audit evidence is retained without secrets.

## 22. Knowledge check

1. Why is a GitLab pipeline success not sufficient to declare a release complete?
2. How can auto-sync bypass an intended GitLab deployment approval gate?
3. What prevents a retry from overwriting a newer release?
4. Why should promotion metadata exclude secrets?
5. How do protected branches and CODEOWNERS work together?
6. Which GitLab API errors are safe to retry?
7. How do you verify the deployed image is the approved artifact?
8. What does Git revert fail to recover for stateful applications?

## 23. References

- [GitLab CI/CD YAML](https://docs.gitlab.com/ci/yaml/)
- [GitLab CI/CD Resource Groups](https://docs.gitlab.com/ci/resource_groups/)
- [GitLab Merge Requests API](https://docs.gitlab.com/api/merge_requests/)
- [GitLab Protected Branches](https://docs.gitlab.com/user/project/repository/branches/protected/)
- [GitLab Code Owners](https://docs.gitlab.com/user/project/codeowners/)
- [GitLab Merge Request Approvals](https://docs.gitlab.com/user/project/merge_requests/approvals/)
- [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Argo CD Sync Status](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)

---

**Chapter 052 complete.** Next: **Chapter 053 — Production Change Windows, Release Evidence and Compliance Automation**.
