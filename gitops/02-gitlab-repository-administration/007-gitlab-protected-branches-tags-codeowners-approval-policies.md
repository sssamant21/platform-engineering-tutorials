# Chapter 007 — GitLab Protected Branches, Tags, CODEOWNERS and Approval Policies

**Part 02 — GitLab Repository Administration**  
**Platform:** GitLab CI/CD + Helm + Argo CD + Kubernetes (EKS, AKS, GKE)  
**Lab environment:** Disposable GitLab group/project, generic `demo-app`  
**Reference deployment:** Dev, Test, Staging and Production are separate namespaces within the same Kubernetes cluster.

## 1. Learning objectives

By completing this chapter, you will be able to:

1. Explain protected branches and protected tags and distinguish push, merge, and release permissions.
2. Configure merge request approvals and path-based CODEOWNERS.
3. Identify bypass risks arising from inherited roles, overlapping branch rules, CI credentials and untrusted pipeline execution.
4. Apply distinct approval requirements to application source, Helm charts, and production GitOps configuration.
5. Validate branch, tag and code-owner protections using a safe, repeatable lab.
6. Diagnose and respond to governance failures without rewriting protected Git history.

## 2. Why repository protection matters

```text
Developer
   |
   v
feature/change --> Merge Request --> CI checks --> Code owner review
                                            |              |
                                            +------+-------+
                                                   |
                                          protected main
                                                   |
                                          trusted build
                                                   |
                                          image@sha256:...
                                                   |
                                      GitOps promotion MR
                                                   |
                                   production release approval
                                                   |
                                               Argo CD
                                                   |
                                       shared Kubernetes cluster
                                    dev | test | staging | prod
```

**Key distinction:** Approval to merge application source is not the same as authorization to deploy to production. Production changes must pass separate GitOps and Argo CD controls.

## 3. Protected branch governance

A protected branch controls which actors may push, merge and (where supported) force-push or delete a branch. Use the current GitLab UI and effective permissions to verify behavior, because role mappings, group-level rules and overlapping protections vary by version and tier.

### Recommended policy

| Branch / ref | Direct push | Merge | Review / checks |
| --- | --- | --- | --- |
| `main` in application repo | Deny ordinary developers | Authorized maintainers / eligible merge roles | Passing CI and independent review |
| `main` in Helm repo | Deny ordinary developers | Chart maintainers | Lint, rendering, policy and owner review |
| `main` in GitOps repo | Deny ordinary developers | Restricted release maintainers | Policy checks, path owners, approved promotion |
| `release/*` | Explicitly restricted | Approved release operators | Release verification |
| `feature/*` | Authorized contributors | Merge via MR to protected target | Standard CI and review |

Avoid assuming that a wildcard rule such as `*` plus a more specific `main` rule always yields the strictest outcome. GitLab can evaluate overlapping protected-branch rules using the most permissive applicable rule for certain settings. Inspect **all** matching rules and validate with test accounts.

### Minimum requirements

- No direct push to production-sensitive protected branches except documented emergency procedures.
- No force-push on protected release branches.
- Require successful pipelines and resolved discussions before merging where configured.
- Use short-lived feature branches rather than one branch per deployment environment.
- Audit users, groups, access tokens, deploy keys and automation with effective write permissions.

## 4. Protected tags and release provenance

Tags label Git revisions. Protect release tag patterns such as `v*` so unauthorized users cannot create or overwrite release references.

A protected tag does **not** by itself guarantee a signed, immutable release artifact. Combine it with:
- Authorized tag creation.
- Signed tags or other approved attestations where required.
- CI pipeline checks on release refs.
- Immutable image digest publication and provenance.
- Registry retention and artifact-signing controls.

Example read-only validation:

```bash
git fetch --tags
git tag --list 'v*'
git show --no-patch --format=fuller v1.0.0
```

Run the last command only after the tag exists. Never use `git push --force --tags` against shared release history.

## 5. CODEOWNERS and approval policies

`CODEOWNERS` maps repository paths to responsible reviewers. GitLab typically supports a root `CODEOWNERS` file or supported alternative locations such as `.gitlab/CODEOWNERS` or `docs/CODEOWNERS`; verify the applicable behavior in your version.

### Example for an application repository

```text
# Replace placeholder groups with actual authorized GitLab groups
/.gitlab-ci.yml         @platform-reviewers
/Dockerfile             @platform-reviewers
/scripts/               @platform-reviewers
/security/              @security-reviewers
```

### Example for a GitOps repository

```text
# All environment configuration reviewed by platform owners
/environments/          @platform-reviewers

# Additional production ownership
/environments/prod/     @release-approvers

# Platform-level Argo CD controls
/argocd/projects/       @platform-reviewers
/argocd/applications/   @platform-reviewers
```

**Important:** CODEOWNERS syntax and rule precedence can be subtle. A later matching entry may supersede an earlier entry within a section. If you need approvals from **multiple independent groups**, configure supported CODEOWNERS sections and approval rules, then test them; do not assume two plain matching lines automatically require two approvals.

### Approval policy requirements

- Independent review: do not count the author as the required approver.
- Re-evaluate approvals after new commits, according to organizational policy.
- Prevent users from overriding approval rules without authorization.
- Apply additional security review for CI configuration, identity, credentials and production desired state.
- Require passing validation before merge.
- Maintain a documented emergency change path with audit and retrospective review.

**GitLab tier note:** Required approvals, code-owner enforcement, approval-rule customization and approval reset behaviors vary by GitLab version, tier and settings. A CODEOWNERS file alone is **not proof** of enforced owner approval.

## 6. Example repository layout

```text
platform-environments/
├── CODEOWNERS
├── .gitlab-ci.yml
├── argocd/
│   ├── projects/
│   └── applications/
└── environments/
    ├── dev/
    │   └── demo-app-values.yaml
    ├── test/
    │   └── demo-app-values.yaml
    ├── staging/
    │   └── demo-app-values.yaml
    └── prod/
        └── demo-app-values.yaml
```

All four environments may share the same Kubernetes cluster, but have distinct namespaces and Argo CD Applications. Namespace separation is not equivalent to independent cluster isolation.

## 7. Hands-on lab — verify branch, tag and approval controls

### Prerequisites and safety

- Disposable private GitLab project `training-platform/demo-app`.
- Administrator or Maintainer authorized to configure project rules.
- Separate test Developer and Reviewer identities.
- Git CLI and a GitLab Runner for CI validation.
- No production secrets, projects or real release tags.

If your GitLab tier cannot enforce an approval policy, record it as **Not Verified** and do not represent the lab as a successful enforcement test.

### Step 1 — Initialize the project

In the disposable project, create `README.md`:

```markdown
# demo-app

Training repository for branch, tag and review governance.
```

Add `.gitlab-ci.yml`:

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages:
  - validate

validate_repository:
  stage: validate
  image: alpine:3.21
  script:
    - test -s README.md
    - test -s CODEOWNERS
```

Add `CODEOWNERS`:

```text
/.gitlab-ci.yml @platform-reviewers
/CODEOWNERS @platform-reviewers
```

Replace the placeholder group with an actual test group having appropriate access.

### Step 2 — Configure protected main

In GitLab, open the project branch-rule settings (menu location varies).

Set `main` to:
1. Deny direct push for ordinary Developer accounts.
2. Allow merging only for the roles/groups intended by the policy.
3. Disable force-push.
4. Require passing pipelines and any required independent approvals.
5. Require code-owner approval where supported.

Inspect other branch rules and wildcard patterns to ensure they do not accidentally broaden access.

### Step 3 — Configure protected release tags

Create a protected tag pattern `v*` and restrict tag creation to a release-maintainer test group or approved role.

Do not create a real production release tag for this exercise.

### Step 4 — Create a feature branch

```bash
git clone https://gitlab.example.com/training-platform/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch007-branch-protection
printf '\nReview and governance test.\n' >> README.md
git add README.md
git commit -m "docs: validate repository governance"
git push -u origin feature/ch007-branch-protection
```

**PowerShell alternative for appending text:**

```powershell
Add-Content README.md 'Review and governance test.'
```

Open an MR targeting `main`. Confirm CI passes, then verify the merge remains blocked until required approvals are provided.

### Step 5 — Test unauthorized direct push

Using the **Developer test identity** and a disposable clone:

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/direct-push-test
printf '\nTemporary direct-push test.\n' >> README.md
git add README.md
git commit -m "test: verify protected main"
git push origin HEAD:main
```

Expected: GitLab rejects the push to `main`. The commit remains on the local feature branch; no history is lost. **Do not run this test as a Maintainer/Owner or in a production project.**

### Step 6 — Test CODEOWNERS enforcement

Modify `.gitlab-ci.yml` in a second disposable feature branch and open an MR.

Verify:
- The correct owner group is requested.
- A non-owner's approval does not satisfy the code-owner requirement if enforcement is configured.
- The MR cannot merge until required code-owner approval and pipeline checks pass.

If the GitLab tier does not support mandatory owner approval, record the missing control and propose a compensating policy.

### Step 7 — Test tag creation restriction

As an unauthorized Developer, attempt to create a disposable protected-pattern tag:

```bash
git tag v0.0.0-training
git push origin v0.0.0-training
```

Expected: GitLab rejects the remote tag creation. The local tag may still exist; remove it locally:

```bash
git tag -d v0.0.0-training
```

If the push succeeds unexpectedly, treat this as a **failed security control**. Review effective protected-tag permissions and overlapping policies, then remove the remote training tag only with authorization.

### Step 8 — Validate approval reset behavior

After receiving initial approval, push another change to the MR branch. Verify whether approvals are reset or retained in accordance with the configured project policy. Do not assume the default behavior.

### Step 9 — Collect evidence

| Test | Expected evidence |
| --- | --- |
| Branch protection | Screenshot/export of effective rule |
| Direct push denied | Rejected push output |
| MR CI gate | Successful pipeline linked to MR |
| Owner approval | Required approval not satisfied by non-owner |
| Protected tag | Unauthorized tag push rejected |
| Approval reset | Behavior matches documented project policy |
| Audit | MR approval history and relevant settings |

### Step 10 — Cleanup

Delete only disposable feature branches and local test tags. Keep evidence according to the training policy. Remove the training project only when authorized and no shared users depend on it.

## 8. GitOps production change governance

A production promotion should update a pinned image digest in the **GitOps repository**, not run an unreviewed `kubectl set image` from CI.

Example promotion:

```text
Image built once -> digest sha256:...
     |
     +--> dev values update + checks
     +--> test promotion MR + integration tests
     +--> staging promotion MR + validation
     +--> prod promotion MR + release-owner approval
                                  |
                                  v
                          Argo CD controlled sync
```

Use protected paths, appropriate reviewer separation, automated policy validation, Argo CD Project restrictions, sync controls and operational rollback plans.

## 9. Troubleshooting runbook

| Symptom | Likely cause | Response |
| --- | --- | --- |
| Developer can push to main | Allowed-to-push rule or overlapping protection | Inspect all matching branch rules |
| Required owner approval absent | Tier, syntax, owner group membership, settings | Validate CODEOWNERS and enforced approval policy |
| MR approved without expected reviewers | Rule override or ineffective settings | Audit effective approval configuration |
| Tag push unexpectedly succeeds | Protected-tag pattern or role issue | Correct rule and audit tag creation |
| Legitimate MR blocked | CI failure, stale approvals, conflict, rule mismatch | Resolve underlying gate, do not bypass |
| Automation can rewrite production GitOps | Over-scoped token or role | Revoke/rotate and restrict identity |
| CI bypasses protected branch | Privileged job/token or workflow flaw | Audit CI trust boundaries and credentials |
| Production drift despite approval | Argo CD permissions or manual cluster change | Review Argo CD and Kubernetes audit events |

## 10. Production acceptance checklist

- [ ] Protected branch rules deny ordinary direct pushes and force-pushes.
- [ ] Overlapping wildcard rules have been reviewed for permissive outcomes.
- [ ] Protected release tags restrict unauthorized creation.
- [ ] CODEOWNERS paths and groups resolve correctly.
- [ ] Required owner approvals are **enforced**, not merely requested.
- [ ] Independent review and pipeline gates are effective.
- [ ] New commits trigger the intended approval re-evaluation policy.
- [ ] Service accounts and CI tokens cannot bypass production GitOps approval.
- [ ] Production promotion uses immutable image digests and approved GitOps changes.
- [ ] Argo CD and Kubernetes permissions provide independent enforcement.
- [ ] Negative access tests and audit evidence are recorded.
- [ ] Emergency override procedures are limited, auditable and reviewed.

## 11. Knowledge checks

1. Why might a wildcard branch rule undermine a more restrictive rule?
2. Why does CODEOWNERS not automatically guarantee mandatory owner approval?
3. How do protected tags differ from signed release artifacts?
4. Why must production GitOps approval be separate from application MR approval?
5. How can CI tokens bypass an otherwise well-designed repository policy?
6. What negative test proves a branch-protection rule is working?

## 12. Chapter completion

**Pass:** You have verified protected branches, protected tags, effective CODEOWNERS approvals, pipeline gating, independent review and documented negative access tests in a disposable GitLab project.

**Next: Chapter 008 — GitLab Merge Request Workflows, Branching Strategies and Release Governance.**
