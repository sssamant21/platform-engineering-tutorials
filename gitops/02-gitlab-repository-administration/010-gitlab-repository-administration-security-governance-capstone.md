# Chapter 010 — GitLab Repository Administration, Security and Governance Capstone

**Part 02 — Final Enterprise Capstone**  
**Chapter:** 010 / 100  
**Platform:** GitLab CI/CD + Helm + Argo CD + Kubernetes (EKS / AKS / GKE)  
**Lab:** Disposable GitLab group and repositories using generic `demo-app` names  
**Environment architecture:** Dev, Test, Staging and Production use separate namespaces in a shared Kubernetes cluster.

> **Scope:** This is a repository-governance acceptance project. It does not create a production cluster, deploy applications, provision cloud infrastructure or grant production credentials. Those workflows are implemented in later chapters.

## 1. Capstone goals

Demonstrate, with actual evidence, that an enterprise GitLab setup can:

1. Separate application, Helm, GitOps and platform automation repositories.
2. Enforce least-privilege group/project access and prevent unauthorized inherited permissions.
3. Protect default branches and release tags from direct changes.
4. Require successful MR validation and independent CODEOWNERS approval where supported.
5. Prevent untrusted CI jobs from receiving production secrets or privileged runner access.
6. Inventory tokens, runner trust boundaries and security scanning configuration.
7. Collect auditable evidence for changes and access.
8. Execute negative security tests and demonstrate a safe recovery workflow.

## 2. Reference architecture

```text
GitLab group: training-platform/
├── applications/
│   └── demo-app/                # Source, tests, untrusted MR CI
├── helm-charts/
│   └── demo-app-chart/          # Chart owners, lint and release
├── gitops/
│   └── platform-environments/   # Dev/Test/Staging/Prod desired state
└── platform-automation/
    └── release-orchestration/   # Restricted automation

Developer -> feature MR -> review + CI -> protected main
                                            |
                                       immutable image
                                      (later modules)
                                            |
                                     GitOps promotion MR
                                            |
                                     Argo CD sync
                                            |
                                shared Kubernetes cluster
                           demo-dev / demo-test /
                           demo-staging / demo-prod
```

**Production boundary:** A developer's permission to merge application code must not imply permission to approve production GitOps changes. GitLab repository permissions, Argo CD Projects/RBAC and Kubernetes RBAC are independently enforced.

## 3. Prerequisites and safety

- Authorized administrative access to a **disposable** GitLab group or training subgroup.
- Two distinct test identities: Developer and Reviewer/Owner.
- A GitLab Runner for nonprivileged validation jobs.
- Git CLI (Git Bash or PowerShell).
- A known GitLab version/tier, recorded in the evidence sheet.
- No production secrets, tokens, clusters, runners or actual organization-specific names.

If your tier does not support enforced CODEOWNERS approval or certain audit/security features, mark the relevant acceptance control **Not Verified / Unavailable**, never Pass.

## 4. Lab 1 — Create the repository governance structure

Create private GitLab subgroups/projects:

```text
training-platform/applications/demo-app
training-platform/helm-charts/demo-app-chart
training-platform/gitops/platform-environments
training-platform/platform-automation/release-orchestration
```

Record owners and purpose:

| Project | Responsible team | Trust level |
| --- | --- | --- |
| demo-app | Application team | Untrusted MRs; protected main |
| demo-app-chart | Platform team | Trusted chart maintenance |
| platform-environments | Release/platform owners | Restricted production desired state |
| release-orchestration | CI platform owners | Privileged automation, restricted refs |

### Membership tests

1. Grant Developer test identity access to `demo-app` only.
2. Grant Reviewer identity the appropriate review rights.
3. Confirm the Developer cannot read or write the private GitOps project unless intentionally granted.
4. Review direct, inherited and shared membership on all projects.
5. Restrict Owner/Maintainer assignments and inventory service identities.

**Expected:** Application development permission does not grant production GitOps write access.

## 5. Lab 2 — Protect branches, tags and sensitive paths

Configure `main` protection on the application, chart and GitOps repositories.

- Disallow ordinary direct pushes and force-pushes.
- Require merge requests and passing pipelines.
- Require independent review.
- Enable enforced code-owner approvals where supported.
- Protect release tag pattern `v*`.
- Review overlapping wildcard branch rules for permissive exceptions.

In the GitOps repository, create a generic layout:

```text
platform-environments/
├── CODEOWNERS
├── environments/
│   ├── dev/demo-app-values.yaml
│   ├── test/demo-app-values.yaml
│   ├── staging/demo-app-values.yaml
│   └── prod/demo-app-values.yaml
└── argocd/
    ├── applications/
    └── projects/
```

For the lab, each values file can contain non-deployable illustrative metadata:

```yaml
# Training-only placeholder; not a complete Helm values schema.
environmentName: dev
applicationName: demo-app
```

Replace `dev` with the corresponding environment in each file. No Kubernetes resources are created.

### CODEOWNERS

```text
# Replace with actual GitLab groups authorized in the training instance
/environments/       @platform-reviewers
/environments/prod/  @release-approvers
/argocd/             @platform-reviewers
/CODEOWNERS          @platform-reviewers
/.gitlab-ci.yml      @platform-reviewers
```

**Important:** Multiple matching CODEOWNERS entries do not necessarily accumulate approvals. If both platform and release approvals are required for production, configure appropriate supported CODEOWNERS sections and approval rules and validate the actual behavior. Do not assume the example alone enforces dual approval.

## 6. Lab 3 — Implement a security and repository CI gate

In the disposable `demo-app` project create:

```text
demo-app/
├── README.md
├── CODEOWNERS
├── .gitlab-ci.yml
├── security/
│   └── check.py
├── src/
│   ├── __init__.py
│   └── app.py
└── tests/
    └── test_app.py
```

### `src/app.py`

```python
def health() -> dict:
    return {"status": "ok"}
```

### `tests/test_app.py`

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

### `security/check.py`

```python
from pathlib import Path

required = [
    Path("README.md"),
    Path("CODEOWNERS"),
    Path(".gitlab-ci.yml"),
    Path("src/app.py"),
    Path("tests/test_app.py"),
]
missing = [str(p) for p in required if not p.is_file()]
if missing:
    raise SystemExit(f"FAIL: missing required files: {missing}")

# Synthetic lab marker only. This is NOT a production secret scanner.
for p in Path(".").rglob("*"):
    if not p.is_file() or ".git" in p.parts:
        continue
    if p.suffix not in {".py", ".md", ".yml", ".yaml", ".txt"}:
        continue
    if "DEMO_FORBIDDEN_MARKER_123" in p.read_text(
        encoding="utf-8", errors="replace"
    ):
        raise SystemExit(f"FAIL: synthetic forbidden marker in {p}")

print("PASS: training repository policy")
```

### `.gitlab-ci.yml`

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

repository_policy:
  stage: validate
  script:
    - python security/check.py

unit_tests:
  stage: test
  needs:
    - repository_policy
  script:
    - python -m unittest discover -s tests -v
```

### `CODEOWNERS` in the application repository

```text
/.gitlab-ci.yml @platform-reviewers
/security/      @security-reviewers
/CODEOWNERS     @platform-reviewers
```

Replace the groups with real training groups and verify approval enforcement.

### Commit and run

```bash
git clone https://gitlab.example.com/training-platform/applications/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch010-governance-capstone
# Create the files shown above using your editor
git add README.md CODEOWNERS .gitlab-ci.yml security/ src/ tests/
git commit -m "security: add repository governance capstone"
git push -u origin feature/ch010-governance-capstone
```

Open a GitLab MR targeting `main`. Expected jobs:

```text
repository_policy  passed
unit_tests         passed
```

The pipeline is deliberately nonprivileged and uses no cloud or production secrets.

## 7. Lab 4 — Negative security and access tests

### Test A — Synthetic marker rejection

Create `security/lab-marker.txt` containing:

```text
DEMO_FORBIDDEN_MARKER_123
```

Commit and push. Expected: `repository_policy` fails and `unit_tests` does not run. Remove the marker and push again; expect green.

### Test B — Direct protected-branch push denied

Using a separate nonprivileged Developer identity and disposable clone, make a harmless commit on a local test branch and attempt:

```bash
git push origin HEAD:main
```

Expected: GitLab rejects the direct push. Do not perform this test using privileged admin credentials.

### Test C — Protected tag creation denied

As an unauthorized Developer:

```bash
git tag v0.0.0-training
git push origin v0.0.0-training
```

Expected: remote tag creation is rejected. Remove the local test tag:

```bash
git tag -d v0.0.0-training
```

If a remote tag was unexpectedly created, treat the control as failed and coordinate authorized cleanup.

### Test D — CODEOWNERS enforcement

Modify `.gitlab-ci.yml` in a disposable MR. Verify the correct owner group is requested and that a non-owner cannot satisfy a mandatory owner approval. If enforcement is unavailable, record the limitation and compensating control.

### Test E — Production GitOps access denied

With the Developer test identity, attempt to open the private `platform-environments` project. Expected: access denied unless a separately authorized membership grants access.

### Test F — Audit visibility

Inspect available audit events for membership, branch-rule or token changes. Record actual event coverage, time range and retention. Do not claim event availability without observing it.

## 8. Lab 5 — Token, runner and secret governance review

Use the GitLab UI to inspect:

| Control | Validation |
| --- | --- |
| Personal/project/group tokens | Owner, scope, expiration, last use |
| Deploy keys and deploy tokens | Write permissions, project scope |
| CI variables | Protection, masking, environment scope |
| Runner assignments | Trust tier, tags, protected status |
| Project visibility | Private |
| Secret detection | Enabled / Disabled / Unavailable / Not Verified |
| Push protection | Enabled / Disabled / Unavailable / Not Verified |
| Audit events | Available categories and retention |
| MR approval settings | Independent review and owner enforcement |

Never copy credential values into the evidence sheet. Prefer short-lived OIDC-based credentials for later trusted build and cloud operations.

## 9. Evidence template

Complete with actual GitLab results:

```text
CAPSTONE: CHAPTER 010
Date:
GitLab version/tier:
Training group:
Application MR URL:
Application pipeline ID:
Protected main direct-push test: PASS / FAIL / NOT VERIFIED
Protected tag test: PASS / FAIL / NOT VERIFIED
CODEOWNERS enforcement: PASS / FAIL / UNAVAILABLE
Independent approval gate: PASS / FAIL / NOT VERIFIED
Synthetic marker rejection: PASS / FAIL
Unprivileged runner isolation: PASS / FAIL / NOT VERIFIED
Developer GitOps access denial: PASS / FAIL / NOT VERIFIED
Token inventory: COMPLETE / INCOMPLETE
Audit event inventory: COMPLETE / INCOMPLETE
Secret detection/push protection status:
Reviewer:
Open risks:
Follow-up owner/date:
```

## 10. Recovery and rollback exercise

For a merged training change, practice a reviewed revert MR. For a regular commit:

```bash
git switch main
git pull --ff-only origin main
git switch -c revert/ch010-governance
git revert <COMMIT_SHA>
git push -u origin revert/ch010-governance
```

Use the actual commit SHA. For a merge commit, use GitLab's revert UI or verify parent selection before a manual revert. Require CI and review for the revert. Never force-push protected `main`.

For a suspected real secret exposure, **revoke and rotate immediately**; deleting a Git commit does not erase clones, mirrors, caches or logs.

## 11. Troubleshooting runbook

| Failure | Likely reason | Action |
| --- | --- | --- |
| Developer can access GitOps repo | Inherited/shared group membership | Inspect all effective access paths |
| Direct main push succeeds | Misconfigured or overlapping branch rules | Correct rules and rerun negative test |
| Tag creation succeeds | Missing/incorrect protected tag rule | Restrict pattern and retest |
| CODEOWNERS not mandatory | Tier or approval configuration | Record limitation; enforce supported compensating control |
| MR pipeline missing | Workflow rules, MR pipeline settings | Validate YAML and pipeline source |
| Runner job pending | Runner unavailable, tags, scope | Restore safe runner capacity |
| Synthetic marker not detected | File type/path not covered | Review test scanner scope |
| Audit events unavailable | Tier, permission or retention | Document and centralize supported logs |
| Privileged token exposed | Incorrect CI scope or untrusted runner | Revoke/rotate, investigate, tighten identity |

## 12. Enterprise acceptance scorecard

| Domain | Required outcome |
| --- | --- |
| Group architecture | Application, charts, GitOps and automation ownership separated |
| Access | Least privilege, inherited membership reviewed |
| Branch/tag protection | Unauthorized direct push and release-tag creation rejected |
| MR governance | Independent review and passing pipeline |
| CODEOWNERS | Enforced where supported; otherwise explicitly unresolved |
| CI security | Untrusted jobs have no production secrets or privileged runners |
| Policy testing | Synthetic forbidden marker blocks MR |
| Audit | Evidence coverage and retention documented |
| Recovery | Safe revert procedure verified |
| Deployment separation | CI source merge does not itself authorize production sync |

**Acceptance rule:** Do not mark the capstone fully accepted if a required security control fails or cannot be verified. Document limitations and remediation owners rather than substituting assumptions.

## 13. Part 02 completion

**Deliverable:** A governed training GitLab hierarchy with validated branch/tag protection, review and pipeline controls, least-privilege membership, security/audit inventory, negative test evidence and a documented recovery process.

**Next: Chapter 011 — GitLab CI/CD YAML Fundamentals, Pipeline Structure and Execution Rules**, beginning Part 03 — GitLab CI/CD Fundamentals.
