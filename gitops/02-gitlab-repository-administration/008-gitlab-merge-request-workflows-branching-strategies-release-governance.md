# Chapter 008 — GitLab Merge Request Workflows, Branching Strategies and Release Governance

**Part 02 — GitLab Repository Administration**  
**Chapter:** 008 / 100  
**Stack:** GitLab CI/CD, Helm, Argo CD, Kubernetes  
**Lab:** Disposable GitLab project `demo-app`  
**Environment architecture:** Dev, Test, Staging, Prod in separate namespaces of one shared Kubernetes cluster.

> **Safety:** All write operations in this chapter target a disposable training project. No real internal organization names, credentials, customer identifiers or production resources are used.

## 1. Learning objectives

After completing this chapter, you will be able to:

1. Compare trunk-based development, GitFlow and release-branch models and select an appropriate enterprise strategy.
2. Implement a short-lived feature-branch and merge-request workflow in GitLab.
3. Configure MR descriptions, approval gates, pipelines, CODEOWNERS and merge controls.
4. Distinguish application code integration from environment promotion through GitOps.
5. Practice conflict resolution, safe rebase, revert and hotfix governance.
6. Trace an approved change from commit to release candidate and deployment decision.
7. Collect operational evidence and validate release governance.

## 2. Architecture: branches are not environments

```text
APPLICATION SOURCE REPOSITORY
feature/* -- MR --> protected main --> trusted build --> image@sha256:...
                   |                                   |
             review + CI                               |
                                                       v
GITOPS REPOSITORY                           promotion MRs / approvals
environments/dev/      <------------------------- digest update
environments/test/     <------------------------- same digest
environments/staging/  <------------------------- same digest
environments/prod/     <------------------------- same digest + production approval
                                                       |
                                                       v
                                                Argo CD sync
                                                       |
                                shared Kubernetes cluster (four namespaces)
```

**Policy:** Do not maintain long-lived `dev`, `test`, `staging`, `prod` source branches merely to represent deployment environments. Environment state belongs in reviewed GitOps configuration, and the same immutable image digest moves through promotion gates.

## 3. Branching strategy trade-offs

| Strategy | Advantages | Risks | Best fit |
| --- | --- | --- | --- |
| Trunk-based, short-lived feature branches | Fast integration, smaller changes, simpler promotion | Requires good automated tests and feature flags | Recommended default for continuously delivered services |
| GitFlow (`develop`, `release/*`, `hotfix/*`) | Explicit release stabilization | Long-lived divergence, merge complexity | Products with infrequent coordinated releases |
| Release branches from `main` | Supports patching supported versions | Backport overhead | Multi-version supported software |
| Direct commits to `main` | Minimal branching | Weak review/audit when unrestricted | Not recommended for enterprise protected source |

**Recommendation:** Protected `main` with short-lived `feature/*`, `fix/*` and time-limited `release/*` or `hotfix/*` only where needed. Use feature flags for incomplete features rather than long-running branches.

### Branch naming and commit conventions

```text
feature/add-health-endpoint
fix/handle-empty-response
hotfix/recover-timeout
release/v1.4-maintenance
```

Example commit subjects:

```text
feat: add health endpoint
fix: handle missing configuration
test: add regression coverage
ci: validate merge requests
docs: document rollback
```

These conventions improve traceability but do not replace required review.

## 4. Merge request lifecycle

```text
Issue/change request
      |
      v
Feature branch -> Draft MR -> CI validation -> Reviewer feedback
                                           -> Security / owner approval
                                           -> Merge gate verification
                                           -> Merge into protected main
                                           -> Release candidate metadata
                                           -> GitOps promotion MR
                                           -> Controlled Argo CD sync
```

### Required MR contents

Every significant MR should document:

- **Why:** change purpose and linked issue.
- **What:** affected services, configuration and dependencies.
- **How tested:** unit, integration, policy, security and manual checks.
- **Risk:** backward compatibility, data impact, deployment blast radius.
- **Rollback:** code revert, feature flag or approved release reversal.
- **Operational readiness:** observability, alerts, capacity and runbook changes.

### Sample `.gitlab/merge_request_templates/Standard.md`

```markdown
## Purpose
Describe the problem and proposed change.

## Scope
- Components changed:
- Out-of-scope items:

## Validation
- [ ] Unit tests
- [ ] Integration tests where applicable
- [ ] CI pipeline passes
- [ ] Security and dependency checks where applicable

## Release and operational impact
- Risk level:
- Feature flag:
- Monitoring:
- Rollback plan:
- Database or API compatibility:

## Approvals
- [ ] Independent reviewer
- [ ] CODEOWNERS / platform / security reviewers when required
```

A template is documentation; enforce approvals and pipelines through GitLab project settings.

## 5. Enterprise merge policy

| Control | Recommended policy |
| --- | --- |
| Protected default branch | Ordinary developers cannot push directly |
| Review | Independent review before merge |
| CODEOWNERS | Required owner approval for sensitive paths, where supported |
| Pipeline | Required passing MR checks |
| Discussions | Resolve blocking discussions |
| Approval freshness | Re-evaluate after new commits according to policy |
| Merge method | Squash for short-lived feature branches when audit policy permits |
| Merge trains | Consider for high-concurrency repositories |
| Release tags | Restricted creation, verified provenance |
| Emergency changes | Time-limited exception, documented authorization, retrospective |

GitLab capabilities differ by tier and version. **Do not mark CODEOWNERS or approval enforcement as passing until verified with negative tests.** Overlapping protected branch rules and privileged tokens can create unexpected bypass paths.

## 6. Release governance: build once, promote the digest

A code merge is an integration event, not a production deployment approval.

1. The default-branch pipeline produces a single immutable container image and records its digest.
2. Trusted build jobs perform scanning, SBOM generation, signing and provenance controls (implemented in later chapters).
3. A GitOps change proposes the digest for `dev`.
4. The same digest progresses through `test` and `staging` after required validation.
5. A separate production GitOps MR receives authorized release approval.
6. Argo CD reconciles the approved production desired state under controlled sync policy.

**Rollback:** Restore a previously approved digest through a reviewed GitOps revert or rollback commit; do not rebuild an older version and assume it is byte-for-byte identical.

**Shared-cluster risk:** Namespace separation is not a full security or failure boundary. Enforce RBAC, resource quotas, network policies, Pod Security, admission policy and appropriate node isolation. For highly critical production systems, consider dedicated clusters.

## 7. Hands-on lab — complete MR workflow

### Prerequisites

- Git installed; Git Bash or PowerShell on Windows is supported.
- Disposable private GitLab project `https://gitlab.example.com/training/demo-app`.
- Developer and independent Reviewer test accounts.
- Nonprivileged GitLab runner.
- Protected `main`, pipeline merge gate and approvals configured as in Chapters 006–007.

### Step 1 — Create application files

`src/app.py`:

```python
def health():
    return {"status": "ok"}
```

`tests/test_app.py`:

```python
import unittest
from src.app import health


class HealthTests(unittest.TestCase):
    def test_health(self):
        self.assertEqual(health(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
```

Create empty `src/__init__.py`.

`.gitlab-ci.yml`:

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages:
  - validate
  - test

default:
  image: python:3.12-slim

validate:
  stage: validate
  script:
    - python -m compileall -q src tests

unit_tests:
  stage: test
  script:
    - python -m unittest discover -s tests -v
```

### Step 2 — Create feature branch

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/health-endpoint
# Add the files above using your editor
git add src/ .gitlab-ci.yml tests/
git commit -m "feat: add health endpoint"
git push -u origin feature/health-endpoint
```

If the project already contains a CI file, update it intentionally instead of blindly overwriting existing jobs.

### Step 3 — Open MR

Create a merge request from `feature/health-endpoint` to `main`.

- Use the Standard MR template.
- Link a training issue or change request.
- Assign an independent reviewer.
- Verify the MR pipeline passes.
- Confirm merge is blocked while required approvals are missing.

### Step 4 — Review iteration

The reviewer requests a test for a missing condition. Add a regression test or update the change as appropriate, then commit and push:

```bash
git add src/ tests/
git commit -m "test: strengthen health endpoint coverage"
git push
```

Verify the pipeline reruns and required approvals are re-evaluated according to configured policy.

### Step 5 — Simulate and resolve a conflict

In a **separate disposable training branch**, modify the same README line on `main` through an approved MR. Then update the feature branch:

```bash
git switch feature/health-endpoint
git fetch origin
git merge origin/main
```

If a conflict occurs, inspect the marked files, resolve them, run tests, then:

```bash
git add <resolved-file>
git commit
git push
```

Use the actual resolved filename. If no conflict occurs, the merge completes normally. Never fabricate a conflict or force-push protected history. Rebase is an alternative for private branches but may require a carefully authorized force-with-lease push; prefer merge when collaborating on the same feature branch.

### Step 6 — Merge and capture evidence

After all required approvals and a passing pipeline, merge through GitLab. Record:

```text
MR URL:
Source commit SHA:
Merge commit or squash commit SHA:
Pipeline ID:
Reviewer(s):
CODEOWNERS check:
Risk/rollback note:
Release candidate identifier:
```

Then verify locally:

```bash
git switch main
git pull --ff-only origin main
git log --oneline --decorate -8
```

### Step 7 — Practice safe revert

In the disposable project, create a revert MR using GitLab's revert action, or for a regular commit:

```bash
git switch main
git pull --ff-only origin main
git switch -c revert/health-endpoint
git revert <COMMIT_SHA>
git push -u origin revert/health-endpoint
```

For a merge commit, use the GitLab revert UI or explicitly determine the correct parent before `git revert -m 1`. Verify CI and obtain review before merging the revert.

### Step 8 — Cleanup

Delete disposable branches after merge/revert verification. Do not remove shared projects, protected tags or production environments.

## 8. Hotfix workflow and incident controls

For urgent production defects:

1. Declare incident/change severity and incident owner.
2. Branch from the approved source revision or supported release branch.
3. Implement the smallest safe fix with a regression test.
4. Run expedited but documented CI/security checks.
5. Obtain designated emergency approval.
6. Build and publish a new immutable artifact once.
7. Promote the artifact through the authorized emergency GitOps path.
8. Verify service health and SLOs; rollback if needed.
9. Reconcile the hotfix into the primary development line and document the incident.

**Do not bypass GitOps governance merely because the incident is urgent.** Use a pre-approved emergency procedure with auditability.

## 9. Troubleshooting

| Problem | Likely cause | Response |
| --- | --- | --- |
| MR not created | Wrong branch, permissions, missing push | Check remote, project and branch |
| Duplicate pipelines | Push and MR rules overlap | Tighten `workflow: rules` |
| MR cannot merge | CI, approvals, conflicts or discussions | Inspect merge widget and address gate |
| Approval unexpectedly retained | Project approval reset policy | Verify configured behavior |
| CODEOWNERS not enforced | Tier, syntax, membership or settings | Validate owner rules with negative test |
| Conflicts recur | Long-lived feature branch | Integrate frequently; reduce scope |
| Hotfix missing from main | Branch reconciliation omitted | Backport/merge through reviewed MR |
| Deployment differs by environment | Rebuilds or mutable tags | Promote same immutable image digest |
| Unauthorized production change | Overprivileged token or Argo CD access | Revoke access, investigate audit logs |

## 10. Acceptance checklist

- [ ] Default branch protected; ordinary direct pushes rejected.
- [ ] Short-lived feature branches and MR templates used.
- [ ] Independent approval and CI checks enforced.
- [ ] CODEOWNERS effective for sensitive paths.
- [ ] Approval behavior after new commits verified.
- [ ] Conflicts resolved without rewriting protected history.
- [ ] Release metadata links source, pipeline and artifact.
- [ ] Production approval distinct from code merge approval.
- [ ] GitOps environment paths represent Dev/Test/Staging/Prod, not source branches.
- [ ] Same immutable digest is promoted through environments.
- [ ] Emergency hotfix and rollback process documented.
- [ ] Actual MR/pipeline/approval evidence retained.

## 11. Knowledge checks

1. Why is trunk-based development a good default for continuously delivered services?
2. Why should environments be represented in GitOps directories rather than long-lived source branches?
3. What controls must be satisfied before merging an MR?
4. When should a release branch be used?
5. How does an emergency hotfix maintain release governance?
6. Why is a reviewed GitOps revert preferable to rebuilding an older image?

## 12. Completion criteria

**Pass:** You can create, review, validate and merge a feature MR, handle a conflict, practice a reviewed revert, and explain the distinction between application merge approval and production GitOps promotion approval.

**Next: Chapter 009 — GitLab Repository Security, Audit Events, Compliance and Secret Protection.**
