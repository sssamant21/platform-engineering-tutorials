# Chapter 055 — Enterprise Environment Promotion and Release Governance Capstone

**Track:** GitLab CI/CD, Helm, GitOps & Argo CD — Enterprise Tutorial Series  
**Part 11:** Environment Promotion and Release Governance  
**Chapter:** 055 / 100 — Part 11 Capstone  
**Audience:** Platform Engineers, SREs, DevSecOps, Release Managers, Security and Compliance Teams

> **Lab safety:** Use dedicated development, staging and production-*simulation* clusters or namespaces. No exercise authorizes modifying live production workloads, deleting customer data, bypassing approval policy or storing tokens in Git. The sample change windows and registry names are illustrative.

## 1. Capstone mission

Design and validate an auditable, recoverable enterprise release process from source commit to production-simulation deployment.

This capstone combines:

- **Chapter 051:** Environment promotion architecture, immutable digests and GitOps separation.
- **Chapter 052:** GitLab pipelines, merge-request approval gates and release automation.
- **Chapter 053:** Production change windows, release evidence and compliance controls.
- **Chapter 054:** Safe rollback, stateful compatibility and disaster recovery.

**Completion criterion:** Demonstrate that the same approved artifact is promoted through each environment, unauthorized deployments are denied, evidence proves what actually ran, and a failed release can be recovered within a measured objective.

## 2. Reference architecture

~~~text
Developer -> source MR -> CI tests / scan / SBOM / build / sign
                                         |
                                   OCI image digest
                                         |
                               GitOps promotion MR
                                         |
                       +-----------------+------------------+
                       |                 |                  |
                  dev overlay       staging overlay     prod-sim overlay
                       |                 |                  |
                    Argo CD           Argo CD            Argo CD
                       |                 |                  |
                   dev cluster       staging cluster     prod-sim cluster
                                         |                  |
                                   smoke/SLO checks    change approval
                                         |                  |
                                         +-------> audit evidence
                                                       |
                                            controlled archive
~~~

**Trust boundaries:** GitLab permissions govern proposed desired state, Argo CD governs reconciliation, Kubernetes RBAC/admission independently govern live writes, and the secret manager controls sensitive credentials. A GitLab deployment approval does not automatically block Argo CD auto-sync after a Git merge; enforce approvals at the **effective deployment boundary**.

## 3. Lab topology and prerequisites

| Component | Lab requirement |
| --- | --- |
| GitLab | Disposable source and GitOps projects |
| Registry | Approved test registry with immutable digest retrieval |
| Kubernetes | dev, staging and prod-sim contexts or isolated namespaces |
| Argo CD | Test installation with separate AppProjects |
| Identity | Developer, release approver, security reviewer and release bot test identities |
| CI runners | Isolated, pinned runner images and scoped credentials |
| Monitoring | Deployment health, logs, smoke tests and basic latency/error metrics |
| Audit | GitLab events, Argo CD operations, Kubernetes audit and redacted evidence store |
| Data | Stateless demo service plus stateful migration tabletop |

Before proceeding:

~~~bash
kubectl config get-contexts
kubectl config current-context
argocd version --client
argocd app list
argocd cluster list
kubectl -n argocd get appprojects,applications
~~~

Record environment ownership, Argo CD version, branch protection, image registry and recovery contacts. Never export Kubernetes Secrets or full credential-bearing kubeconfigs as evidence.

## 4. Suggested repository layout

~~~text
release-capstone/
├── source/
│   ├── .gitlab-ci.yml
│   ├── Dockerfile
│   ├── app/
│   └── tests/
├── gitops/
│   ├── CODEOWNERS
│   ├── apps/demo-web/
│   │   ├── base/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── kustomization.yaml
│   │   └── overlays/
│   │       ├── dev/kustomization.yaml
│   │       ├── staging/kustomization.yaml
│   │       └── prod-sim/kustomization.yaml
│   ├── argocd/
│   ├── changes/
│   └── policies/
├── ci/
│   ├── verify-release.sh
│   ├── propose-promotion.sh
│   └── validate-window.py
├── runbooks/
│   ├── failed-release.md
│   ├── emergency-change.md
│   └── gitops-recovery.md
└── evidence/
    └── acceptance-template.md
~~~

Separate application build privileges from production GitOps write privileges. All credentials must come from approved secret delivery; release metadata and CI artifacts must be non-sensitive.

## 5. Phase 1 — Establish artifact identity

Build once, test, scan, generate an SBOM and record the immutable registry digest.

~~~text
Release ID:
Source commit SHA:
CI pipeline URL:
Container registry:
Image digest: sha256:<64 lowercase hex characters>
SBOM reference:
Signature/provenance verification:
Security policy result:
Release owner:
~~~

A mutable tag is insufficient evidence. Use an immutable digest in each environment overlay. If image signing is enforced, verify the signature and identity against the approved trust policy before promotion.

### Artifact acceptance

- The digest resolves to the expected image.
- The source commit and pipeline are traceable.
- Security checks meet the organization's release policy.
- No production secret was included in the image, pipeline output or release record.

## 6. Phase 2 — Build environment overlays

Example staging Kustomize overlay:

~~~yaml
resources:
  - ../../base
namespace: demo-staging
replicas:
  - name: demo-web
    count: 2
images:
  - name: registry.example.internal/demo/web
    digest: sha256:REPLACE_WITH_REAL_64_HEX_DIGEST
~~~

Example production-simulation overlay:

~~~yaml
resources:
  - ../../base
namespace: demo-prod-sim
replicas:
  - name: demo-web
    count: 3
images:
  - name: registry.example.internal/demo/web
    digest: sha256:REPLACE_WITH_SAME_APPROVED_DIGEST
~~~

The base Deployment must use the same image name. Replace placeholders with a real digest before applying. Verify Kustomize syntax compatibility with the installed version.

~~~bash
kubectl kustomize gitops/apps/demo-web/overlays/staging
kubectl kustomize gitops/apps/demo-web/overlays/prod-sim
~~~

**Pass:** the rendered images reference the same digest, while environment-specific replica counts and namespaces remain explicitly reviewed.

## 7. Phase 3 — Configure release governance

Apply these controls to the disposable GitLab project:

1. Protect the GitOps default branch.
2. Configure CODEOWNERS for staging and prod-sim overlays.
3. Require independent approval for prod-sim changes.
4. Prevent the release bot from directly pushing or approving its own MR.
5. Require passing manifest render, policy, artifact and release-record checks.
6. Define an authorized production-simulation change window.
7. Establish an explicit emergency exception path.
8. Protect Argo CD Projects, Applications and cluster credentials.

Example CODEOWNERS:

~~~text
/gitops/apps/demo-web/overlays/dev/       @platform/dev-owners
/gitops/apps/demo-web/overlays/staging/   @platform/release-owners
/gitops/apps/demo-web/overlays/prod-sim/  @platform/prod-approvers @security/reviewers
/gitops/argocd/                           @platform/argocd-admins
/gitops/policies/                         @security/reviewers
~~~

**Important:** CODEOWNERS text alone does not enforce approval. Configure protected branches and applicable GitLab approval rules, then run negative tests. Exact enforcement features vary by GitLab edition and version.

## 8. Phase 4 — Change record and window policy

Example non-Kubernetes change record:

~~~yaml
apiVersion: platform.example/v1
kind: ChangeRecord
metadata:
  name: demo-web-capstone
spec:
  changeId: CHG-CAPSTONE-055
  classification: normal
  environment: prod-sim
  application: demo-web
  imageDigest: sha256:REPLACE_WITH_REAL_DIGEST
  sourceCommit: REPLACE_WITH_FULL_SHA
  approvedWindow:
    start: "2026-10-21T20:00:00Z"
    end: "2026-10-21T21:00:00Z"
  rollback:
    previousDigest: sha256:REPLACE_WITH_PREVIOUS_DIGEST
    runbook: runbooks/failed-release.md
~~~

This document is repository metadata, **not a Kubernetes CRD**. Dates are examples, not actual approval. A trusted controller must verify the real approved record, freeze state and current UTC time at the effective release action.

If Argo CD auto-syncs, hold the production GitOps merge until approval/window conditions pass. A separate GitLab manual deployment job cannot retroactively prevent auto-sync after merge.

## 9. Phase 5 — CI/CD promotion pipeline

The following is an integration skeleton; approved internal runner images and scripts must be implemented for your environment.

~~~yaml
stages: [test, build, verify, propose]

unit_tests:
  stage: test
  image: python:3.12-slim
  script:
    - python -m pip install -r requirements.txt
    - python -m pytest -q

build_image:
  stage: build
  image: registry.example.internal/ci/secure-builder:PINNED_VERSION
  script:
    - ./ci/build-image.sh
  artifacts:
    paths: [release.env]
    reports:
      dotenv: release.env
    expire_in: 7 days

verify_artifact:
  stage: verify
  image: registry.example.internal/ci/security-tools:PINNED_VERSION
  needs:
    - job: build_image
      artifacts: true
  script:
    - ./ci/verify-release.sh

propose_staging:
  stage: propose
  image: registry.example.internal/ci/gitlab-client:PINNED_VERSION
  resource_group: staging-promotion
  needs:
    - job: build_image
      artifacts: true
    - job: verify_artifact
  script:
    - ./ci/propose-promotion.sh staging
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
~~~

**Security:** the dotenv artifact may contain only non-secret metadata such as image digest and source commit. Do not store GitLab API tokens or registry passwords in artifacts. Use least-privilege credentials and never allow untrusted MR pipelines to access production credentials.

## 10. Phase 6 — Promote dev to staging

1. Merge the reviewed source change.
2. Run CI and verify the immutable digest.
3. Create a GitOps MR updating the dev overlay.
4. Validate dev deployment and smoke tests.
5. Propose the same digest in the staging overlay.
6. Obtain required staging approval.
7. Merge and reconcile the staging Argo CD Application.
8. Record the observed digest, Git revision and health.

~~~bash
argocd app get demo-staging --refresh
argocd app diff demo-staging
# Only after approved GitOps merge:
argocd app sync demo-staging
argocd app wait demo-staging --sync --health --timeout 300
kubectl --context STAGING_CONTEXT -n demo-staging rollout status deploy/demo-web
kubectl --context STAGING_CONTEXT -n demo-staging \
  get deploy demo-web -o jsonpath='{.spec.template.spec.containers[*].image}{"\n"}'
~~~

**Pass:** staging is Synced and Healthy at the approved revision, smoke tests pass, and the observed image digest equals the release record.

## 11. Phase 7 — Promote staging to production simulation

1. Verify staging integration, performance and security evidence.
2. Create a production-simulation promotion MR using the identical digest.
3. Require independent approvers and valid change window.
4. Confirm no active release freeze.
5. Merge through the protected branch only when the effective gate passes.
6. Reconcile through the approved Argo CD sync mechanism.
7. Validate rollout, application smoke tests and SLOs.
8. Archive redacted release evidence.

~~~bash
argocd app get demo-prod-sim --refresh
argocd app diff demo-prod-sim
# If manual sync is configured and approved:
argocd app sync demo-prod-sim
argocd app wait demo-prod-sim --sync --health --timeout 300
kubectl --context PROD_SIM_CONTEXT -n demo-prod-sim rollout status deploy/demo-web
kubectl --context PROD_SIM_CONTEXT -n demo-prod-sim \
  get deploy demo-web -o jsonpath='{.spec.template.spec.containers[*].image}{"\n"}'
~~~

**Pass:** approvals and window enforcement are demonstrably effective; the deployed digest matches staging, and post-release health meets the acceptance threshold.

## 12. Lab A — Unauthorized release denial

Use a normal developer identity, not an administrator.

- Attempt direct push to the protected production-simulation branch.
- Attempt to merge a prod-sim MR without required approvals.
- Attempt to deploy outside the approved window.
- Attempt to sync a prod-sim Application outside the actor's Argo CD Project.
- Attempt to use an unapproved artifact digest.

**Pass:** each unauthorized action is denied at its enforcement boundary and logged. A failed CI job alone is not proof if the actor can still merge or sync through another route.

## 13. Lab B — Promotion race and stale release protection

1. Create release A and release B from the same GitOps branch revision.
2. Open separate staging promotion MRs.
3. Merge B first.
4. Attempt to merge A without revalidation.
5. Confirm the stale release cannot silently overwrite the newer approved digest.
6. Require a deliberate release-order decision before proceeding.

**Pass:** the system detects stale base revisions, conflicting updates or disallowed release ordering. A GitLab resource group serializes jobs in its scope but does not prevent cross-project races by itself.

## 14. Lab C — Failed release and GitOps rollback

Use a deliberately unhealthy image in a disposable prod-sim namespace.

1. Record the last known-good digest and GitOps commit.
2. Promote the failing digest through the test governance path.
3. Observe readiness failure and degraded application health.
4. Freeze subsequent promotions.
5. Revert the GitOps change through a reviewed MR.
6. Reconcile and verify actual running digest, readiness and smoke tests.

~~~bash
argocd app get demo-prod-sim
argocd app history demo-prod-sim
kubectl --context PROD_SIM_CONTEXT -n demo-prod-sim get deploy,pods
# After approved revert:
argocd app sync demo-prod-sim
argocd app wait demo-prod-sim --sync --health --timeout 300
~~~

**Pass:** the approved previous digest is restored and service recovery time is measured. A Git revert does not undo data changes, so use a stateless workload for this exercise.

## 15. Lab D — Database migration compatibility tabletop

**Scenario:** release B writes data in a format incompatible with release A.

1. Identify when the first incompatible write occurred.
2. Determine whether rolling back the application would fail or corrupt data.
3. Review backup/PITR availability and RPO/RTO.
4. Design an expand-and-contract migration or compatible roll-forward.
5. Evaluate CDC, replication and downstream data consistency.
6. Produce an incident decision record signed by the application owner and DBRE.

**Pass:** the team does not perform an unsafe application-only rollback. The recovery plan specifies validation, data ownership and write handling.

## 16. Lab E — Release evidence integrity and recovery

Create a redacted JSON evidence record with release ID, approvals, digest, revisions, observed image and health.

~~~bash
jq -S . evidence/release.json > evidence/release.canonical.json
sha256sum evidence/release.canonical.json > evidence/release.sha256
sha256sum -c evidence/release.sha256
~~~

1. Preserve the reference checksum in a separate trusted location.
2. Modify the local evidence file.
3. Confirm integrity verification fails.
4. Restore the original from the controlled archive.
5. Confirm integrity and access controls.

**Pass:** evidence tampering is detectable and the original can be recovered. A local checksum alone is not proof of authenticity.

## 17. Lab F — GitOps dependency outage tabletop

Simulate loss of one dependency at a time: GitLab, registry, Argo CD, Kubernetes API or secret manager.

For each:
1. Identify affected deployment/reconciliation actions.
2. Determine whether existing healthy workloads remain serving.
3. Check the approved recovery source and ownership.
4. Define the minimum safe recovery sequence.
5. Validate a canary before resuming fleet-wide releases.

**Pass:** the team can distinguish control-plane outages from workload/data outages and avoid unsafe bulk sync or pruning.

## 18. Lab G — Emergency change during release freeze

1. Declare a simulated security incident.
2. Record emergency change ID and authorized approver.
3. Limit exception scope to the affected application and environment.
4. Verify the emergency artifact digest and rollback/forward-fix plan.
5. Promote through the protected GitOps path.
6. Verify health and capture audit evidence.
7. Expire the override and perform retrospective review.

**Pass:** emergency access is narrow, time-bound and audited; no permanent bypass remains.

## 19. Release monitoring and SLO gates

| Signal | Baseline / decision |
| --- | --- |
| Argo CD sync/health | Expected revision is Synced and Healthy |
| Kubernetes rollout | Desired replicas Ready and progress within deadline |
| Running image | Exact approved digest |
| Application smoke tests | Critical endpoints and business paths pass |
| HTTP errors | No sustained regression against agreed baseline |
| Latency | P95/P99 within release-specific limits |
| Database health | Connection errors, replication lag and schema compatibility |
| Audit trail | Actor, MR, revision and deployment operation recorded |

Do not claim release success solely because pods are Running or Argo CD reports Healthy. Confirm customer-facing behavior and the actual revision.

## 20. Ten failure and troubleshooting scenarios

| # | Symptom | Investigation | Recovery |
| --- | --- | --- | --- |
| 1 | Production sync before approval | Auto-sync and Git merge boundary | Protect effective deployment gate |
| 2 | Wrong digest deployed | Mutable tag or overlay mismatch | Reconcile approved immutable digest |
| 3 | Staging healthy, prod-sim fails | Environment drift and dependencies | Compare config, policy and resource limits |
| 4 | MR approvals bypassed | GitLab tier/settings/token scope | Restore protection and audit |
| 5 | Release blocked during valid window | UTC, freeze or change lookup | Verify trusted policy and timestamps |
| 6 | Stale release overwrites newer | Promotion race | Enforce revision/order checks |
| 7 | Git revert does not recover app | Stateful migration or external side effect | DBRE-led roll-forward/recovery |
| 8 | Argo CD Synced but errors rise | Probes insufficient, dependency failure | Use SLO-based rollback decision |
| 9 | Evidence missing or altered | Artifact expiry or archive control | Recover trusted audit record |
| 10 | Emergency override persists | Missing expiry/revocation | Revoke, audit and remediate |

## 21. Production runbook — governed release

**Preflight:** verify approved change ID, time window, artifact digest, test evidence, staging SLOs, approvers, on-call ownership, rollback plan and no active freeze.

**Execution:** merge the reviewed GitOps MR or perform the explicitly authorized manual sync at the effective deployment boundary.

**Validation:** confirm Argo CD revision, observed Kubernetes image digest, rollout readiness, smoke tests, error rate, latency and database compatibility.

**Closure:** archive redacted evidence with integrity/retention controls, record actual timing and impact, and obtain release-owner sign-off.

## 22. Production runbook — failed or unauthorized release

1. Declare incident and identify target cluster, Application, Git revision and digest.
2. Pause subsequent promotions; preserve evidence.
3. Determine customer impact and whether stateful changes occurred.
4. Choose GitOps revert, roll-forward or data recovery based on compatibility.
5. Apply the approved recovery change.
6. Verify actual running digest, service behavior and SLO recovery.
7. Revoke unauthorized access or expired emergency exceptions.
8. Document root cause, missing gate, owner and follow-up deadline.

Never blindly restore a database to an earlier point without considering valid writes and downstream effects.

## 23. Production runbook — GitOps disaster recovery

1. Inventory the failed dependency and blast radius.
2. Preserve logs, change IDs and known-good Git revisions.
3. Restore Git, registry, cloud identity and secret manager dependencies as needed.
4. Recover Kubernetes cluster and persistent data using approved DR plans.
5. Bootstrap Argo CD from versioned configuration independent of the failed instance.
6. Restore scoped cluster registrations, AppProjects and application definitions.
7. Reconcile canary applications before broader fleet sync.
8. Validate revision, digest, health, audit forwarding and data consistency.

Do not enable blanket prune or fleet-wide automated sync during uncertain recovery.

## 24. Evidence template

~~~text
Capstone ID:
Change ID and classification:
Environment:
Source commit:
CI pipeline:
Registry and image digest:
SBOM/signature evidence:
GitOps promotion MR:
Approvers:
Approved change window:
Effective deployment action/time:
Argo CD Application and revision:
Observed workload image:
Smoke/SLO result:
Failure-injection ID:
Rollback/forward-fix decision:
Recovery time and objective:
Data compatibility decision:
Audit archive and integrity reference:
Pass/Fail/Waiver:
Reviewer:
Follow-up owner and due date:
~~~

## 25. Scoring and sign-off

| Domain | Points | Minimum evidence |
| --- | ---: | --- |
| Immutable build and promotion | 20 | Identical verified digest across environments |
| Approval, window and freeze enforcement | 25 | Negative authorization and time-window tests |
| Release automation and concurrency | 15 | Protected MR and stale-release tests |
| Rollback and stateful safety | 20 | Recovery drill and DB migration decision |
| Observability and evidence | 15 | Actual digest, health/SLO and trusted audit archive |
| Operational runbooks | 5 | Reviewed release, incident and DR procedures |
| **Total** | **100** | |

**Pass:** at least **85/100** and **all critical controls** pass. Critical failures include unauthorized production-simulation deployment, missing artifact integrity, unsafe stateful rollback, or inability to recover an approved known-good release. A high numerical score cannot override these failures.

## 26. Final acceptance checklist

- [ ] Build-once, promote-by-digest workflow verified.
- [ ] Environment overlays render correctly.
- [ ] GitLab branch protection and required approvals enforced.
- [ ] Production change window and freeze enforced at effective deployment action.
- [ ] Release bot cannot bypass approval or use production cluster-admin.
- [ ] Stale promotions and duplicate retries handled safely.
- [ ] Approved Git revision and actual workload digest match.
- [ ] Smoke tests and application SLOs pass.
- [ ] GitOps rollback exercise recovers a known-good release.
- [ ] Stateful migration risks, backups and RPO/RTO documented.
- [ ] Emergency change exception is narrow and expires.
- [ ] Audit evidence is redacted, traceable and integrity-protected.
- [ ] Dependency outage/DR tabletop completed.
- [ ] Platform, security and release owners sign off.

## 27. Knowledge check

1. What is the true deployment approval boundary for an auto-sync Argo CD Application?
2. Why must a promotion pipeline verify the same digest across environments?
3. How can a stale GitOps MR undo a newer release?
4. Which controls prevent a release bot from bypassing production governance?
5. Why does a Git revert not guarantee recovery after an incompatible database migration?
6. What evidence proves that an approved artifact actually ran in Kubernetes?
7. How should emergency release authorization differ from a normal release?
8. Why is an independently stored audit checksum stronger than a local checksum alone?
9. What does Argo CD Healthy fail to prove about customer experience?
10. What must be validated before broad reconciliation after disaster recovery?

## 28. References

- [GitLab Protected Branches](https://docs.gitlab.com/user/project/repository/branches/protected/)
- [GitLab Merge Request Approvals](https://docs.gitlab.com/user/project/merge_requests/approvals/)
- [GitLab Code Owners](https://docs.gitlab.com/user/project/codeowners/)
- [GitLab Deployment Approvals](https://docs.gitlab.com/ci/environments/deployment_approvals/)
- [GitLab Resource Groups](https://docs.gitlab.com/ci/resource_groups/)
- [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Argo CD Projects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes Auditing](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)

---

**Chapter 055 complete — Part 11 complete (Chapters 051–055).**

**Next:** Chapter 056 — Progressive Delivery Fundamentals: Canary, Blue-Green and Release Risk, beginning Part 12: Progressive Delivery and Advanced Deployment Strategies.
