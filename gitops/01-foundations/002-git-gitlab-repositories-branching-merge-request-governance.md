# Chapter 002 — Git, GitLab Repositories, Branching and Enterprise Merge Request Governance

**Part 01 — Foundations and Enterprise Architecture**  
**Platform:** GitLab source control + GitLab CI/CD; GitHub hosts this tutorial  
**Lab application:** `demo-app` (generic example)  
**Difficulty:** Foundation to production operations  
**Prerequisites:** Git, GitLab project access, Git CLI, optional `glab` CLI

> **Scope:** This chapter governs the **application source repository**. Production GitOps configuration is maintained separately, and deployments are reconciled by Argo CD rather than CI jobs directly changing Kubernetes resources.

## 1. Learning objectives

By the end of this chapter, you can:

1. Explain Git history, commits, branches, merge requests and protected branches.
2. Implement a trunk-based GitLab workflow with short-lived feature branches.
3. Protect `main`, require review and passing pipelines, and define CODEOWNERS.
4. Distinguish application source approvals from production GitOps promotion approvals.
5. Perform a safe local lab, validate branch protection, and recover from mistakes.
6. Identify governance gaps and operational troubleshooting steps.

## 2. Architecture and ownership boundaries

```text
Application GitLab repository                  GitOps GitLab repository
+---------------------------------+            +--------------------------------+
| main (protected)                |            | environment desired state      |
| feature/* -> Merge Request      |            | dev/test/staging/prod          |
| tests + scans + review          |            | CODEOWNERS + approval gates    |
+---------------+-----------------+            +---------------+----------------+
                |                                              |
                v                                              v
        GitLab CI/CD pipeline                            Argo CD reconciliation
        test -> build -> scan                            -> Kubernetes cluster
        -> sign -> publish image                             namespaces:
                |                                      demo-dev / demo-test /
                +-- image digest -> GitOps MR --------> demo-staging / demo-prod
```

**Separation of duties:** CI can propose a GitOps merge request, but production deployment configuration must not be silently rewritten without the required approval. Production Argo CD sync requires an explicitly chosen control policy.

**Shared cluster caveat:** Namespaces are logical boundaries; they do not protect against cluster-wide outages or misconfiguration. Apply namespace RBAC, quotas, policy, and appropriate node isolation, and evaluate separate production clusters for critical workloads.

## 3. Git fundamentals for platform engineers

| Term | Meaning | Operational relevance |
| --- | --- | --- |
| Repository | Versioned files and history | Auditability and recovery |
| Commit | Immutable history object identified by SHA | Trace releases to exact source |
| Branch | Movable reference to commits | Isolate proposed changes |
| Merge request (MR) | Reviewed proposal to integrate changes | Policy and human approval gate |
| Protected branch | Restricted branch updates and merges | Prevent bypass of required checks |
| CODEOWNERS | Path-based review ownership | Require platform/security review for sensitive files |
| Tag | Named revision, ideally protected for releases | Stable release references |
| Revert | New commit undoing an earlier change | Auditable rollback without rewriting history |

Prefer short-lived branches and frequent integration to `main`. Avoid using long-lived `dev`, `test`, `staging`, and `prod` branches to represent deployment environments. **Use GitOps environment directories and reviewed promotion commits instead.** Branches describe code development; environment paths describe deployment state.

## 4. Recommended GitLab project governance

### Application repository

- Protect `main`: disable direct pushes for developers; require merge requests.
- Require successful CI pipelines before merging.
- Require at least one independent reviewer; add security/platform owners for high-risk changes.
- Use CODEOWNERS for `.gitlab-ci.yml`, Dockerfiles, dependency manifests, and infrastructure code.
- Restrict force-push and deletion on protected branches and protected release tags.
- Prefer squash merge for short-lived feature branches when the team's audit policy permits it.
- Enforce signed commits/tags if required by organizational policy.
- Use least-privilege GitLab project/group membership; audit bot tokens and runner permissions.
- Configure approval settings so authors cannot approve their own changes where supported.
- Prevent approval bypass by pipeline configuration changes; validate the effective project settings.

### GitOps repository

- Restrict changes to `environments/prod/**` and Argo CD Projects/ApplicationSets.
- Require production platform or release-owner approval for production paths.
- Block image tags such as `latest`; promote pinned image digests.
- Verify Helm chart version, image provenance, policy validation, and deployment plan before merging.
- Do not let an untrusted CI job push directly to protected production branches.
- Use Argo CD Project restrictions for repositories, clusters, namespaces, and resource types.

**GitLab licensing note:** Specific approval-rule and CODEOWNERS enforcement capabilities vary by GitLab tier and configuration. Verify the actual plan and effective project settings; a CODEOWNERS file alone is not proof that owner approval is enforced.

## 5. Reference repository layout

```text
demo-app/
├── .gitlab-ci.yml
├── .gitignore
├── CODEOWNERS
├── README.md
├── Dockerfile
├── src/
│   └── app.py
├── tests/
│   └── test_app.py
└── docs/
    └── operations.md
```

`CODEOWNERS` example:

```text
# Replace example groups with actual GitLab groups before use
/.gitlab-ci.yml    @platform-reviewers
/Dockerfile        @platform-reviewers
/docs/operations.md @platform-reviewers
```

The group references are placeholders. Check that groups exist, have project access, and are configured as required approvers.

## 6. Hands-on lab — branch, merge request, review and recovery

### Lab safety and prerequisites

Use a **disposable GitLab project**, not an existing production repository. GitLab hostname and group are placeholders. Run commands in Git Bash, PowerShell, or a terminal with Git installed.

**Lab project URL:** `https://gitlab.example.com/training/demo-app`

### Step 1 — Clone and inspect

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git remote -v
git status
git branch -a
git log --oneline -5
```

Expected: the remote points to the training project, the working tree is clean, and `main` exists.

If the remote project is empty, initialize it with a README in GitLab before cloning.

### Step 2 — Create a short-lived feature branch

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/add-health-documentation
mkdir -p docs
printf '# Health checks\n\nDocument readiness and liveness probes here.\n' > docs/health-checks.md
git add docs/health-checks.md
git commit -m "docs: add health check guidance"
git push -u origin feature/add-health-documentation
```

**Windows PowerShell alternative** for the file creation step:

```powershell
New-Item -ItemType Directory -Force docs | Out-Null
@'
# Health checks

Document readiness and liveness probes here.
'@ | Set-Content docs/health-checks.md
```

### Step 3 — Open a merge request

In GitLab: **Code → Merge requests → New merge request**.

- Source: `feature/add-health-documentation`
- Target: `main`
- Title: `docs: add health check guidance`
- Description: purpose, validation, impact, rollback.
- Assign a reviewer who did not author the change.

Do not merge until the pipeline passes and the required approvals are recorded.

### Step 4 — Add a minimal CI check

Create `.gitlab-ci.yml` on a separate branch or include it in the same lab MR **only if you have permission to edit CI configuration**:

```yaml
stages:
  - validate

validate_docs:
  stage: validate
  image: alpine:3.21
  script:
    - test -s docs/health-checks.md
    - grep -q "Health checks" docs/health-checks.md
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
```

**Expected result:** The `validate_docs` job succeeds if the documentation exists and contains the required heading. A runner capable of executing the container image must be available.

For a first-time project, create a protected `main` branch and validate CI configuration using GitLab CI Lint before enforcing the pipeline gate.

### Step 5 — Configure and verify protection

In the disposable project, use GitLab's repository/branch rules UI (menu names vary by version) to configure:

1. Protected `main`.
2. No direct developer pushes.
3. Merge requests required.
4. Passing pipelines required.
5. Required reviewers and CODEOWNERS where supported.
6. Restricted force pushes and protected release tags.

**Validation:** Try a direct push using a non-privileged test account. It should be rejected. Do not test by attempting to bypass protections in a production repository.

Record evidence: protected branch settings, pipeline status, reviewer approvals, MR merge commit SHA, and project audit events if available.

### Step 6 — Merge and verify

After approval and a passing pipeline, merge the MR using the GitLab UI.

```bash
git switch main
git pull --ff-only origin main
git log --oneline -5
git show --stat --oneline HEAD
```

Expected: the approved change is visible on `main`, with a traceable commit and MR.

### Step 7 — Safe recovery with revert

If a merged change must be undone, use a **new revert MR**. For a regular non-merge commit:

```bash
git switch main
git pull --ff-only origin main
git switch -c revert/health-documentation
git revert <COMMIT_SHA>
git push -u origin revert/health-documentation
```

Replace `<COMMIT_SHA>` with the actual commit ID. If the original change was a merge commit, use GitLab's revert UI or a carefully reviewed `git revert -m 1 <MERGE_COMMIT_SHA>` after confirming parentage. Do not rewrite shared history or force-push `main`.

### Step 8 — Cleanup

After merge and verification, remove the feature branch in GitLab. Locally:

```bash
git branch -d feature/add-health-documentation
```

Delete the disposable training project only when no longer needed and when you are authorized to do so.

## 7. Production release and environment policy

| Change | Approval | Deployment behavior |
| --- | --- | --- |
| Feature MR | Code owner + passing CI | Build artifact; no direct production deploy |
| Dev GitOps update | Automated after policy checks | Argo CD automated sync |
| Test GitOps update | Integration test gate | Argo CD automated/controlled sync |
| Staging GitOps update | Release gate | Controlled sync |
| Prod GitOps update | Authorized production approval | Controlled Argo CD sync with health monitoring |

Use **one immutable image digest** throughout promotion. Only configuration explicitly intended to vary by environment should differ. Treat secret values as external secret references rather than plaintext committed to Git.

## 8. Operational troubleshooting

| Problem | Diagnosis | Resolution |
| --- | --- | --- |
| Push rejected | Protected branch policy | Push a feature branch and open an MR |
| MR cannot merge | Failed pipeline, missing approval or conflicts | Inspect MR checks; address failures |
| CODEOWNERS ignored | File location, group permissions or tier | Verify path patterns and enforced rules |
| Pipeline missing | `rules`, workflow, runner availability | Validate CI YAML and MR pipeline settings |
| Diverged local branch | Remote changes | Fetch and rebase/merge carefully; avoid force-push |
| GitOps update not deployed | Argo CD sync/health and policy gates | Check desired revision, project restrictions, app events |
| Secret leaked into Git | Credential exposure | Revoke/rotate immediately; follow incident process |

Useful read-only commands:

```bash
git status
git remote -v
git fetch --all --prune
git log --oneline --decorate --graph -15
git diff origin/main...HEAD
```

## 9. Enterprise acceptance criteria

- [ ] `main` is protected; direct push and force-push are restricted.
- [ ] MRs require passing pipelines and appropriate independent review.
- [ ] CODEOWNERS rules are effective for CI and deployment-sensitive paths.
- [ ] Build artifacts can be traced to a source commit and pipeline.
- [ ] GitOps production paths require release authorization.
- [ ] GitLab CI cannot silently deploy or alter production desired state.
- [ ] Argo CD deployment permissions are constrained by Project and Kubernetes RBAC.
- [ ] A revert MR has been tested in a disposable environment.
- [ ] Audit evidence is retained according to policy.

## 10. Knowledge checks

1. Why do we use short-lived feature branches instead of a branch per environment?
2. How is a merge request approval different from Argo CD synchronization?
3. Why must CODEOWNERS enforcement be verified rather than assumed?
4. How can an organization prevent CI jobs from bypassing production release approval?
5. Why is `git revert` generally safer than rewriting shared branch history?

## 11. Chapter completion

**Pass:** You can create a feature branch, open an MR, enforce review and CI gates, verify protection, and safely revert a change without rewriting shared history.

**Next:** Chapter 003 — GitLab CI/CD Architecture, Pipelines, Jobs, Stages and Runners.
