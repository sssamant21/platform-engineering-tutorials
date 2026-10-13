# Chapter 005 — Enterprise GitLab CI/CD Foundations Capstone: Secure Pipeline and Release Governance

**Part 01 — Final Capstone**  
**Track:** GitLab CI/CD → Immutable Artifacts → Reviewed GitOps → Argo CD → Kubernetes  
**Lab:** `demo-app` in a disposable GitLab project  
**Reference environment model:** One Kubernetes cluster, separate `demo-dev`, `demo-test`, `demo-staging`, `demo-prod` namespaces  
**Scope:** CI and governance acceptance. Actual Kubernetes delivery, image signing, Helm packaging, Argo CD reconciliation and production promotion are implemented in later modules.

## 1. Learning objectives

On completion you can:

1. Design an auditable GitLab merge-request workflow with branch protection, review and CI checks.
2. Build a reproducible multi-stage pipeline that validates, tests, packages and verifies a release candidate.
3. Produce test reports, checksum manifests and a release metadata manifest linked to the Git commit.
4. Demonstrate failure gating, artifact retention, runner isolation and secret-safe configuration.
5. Explain the separate production GitOps approval boundary and release promotion lifecycle.
6. Collect objective evidence for an enterprise acceptance review.

## 2. Capstone architecture and trust boundaries

```text
Developer feature branch
       |
       v
GitLab Merge Request (CODEOWNERS, approvals, protected main)
       |
       v
GitLab MR pipeline (untrusted / least-privileged runner)
       |-- syntax checks
       |-- unit tests + JUnit report
       |-- package source
       |-- checksum + release manifest
       v
Approved merge to main
       |
       v
Trusted publishing pipeline [FUTURE MODULE]
       |-- build container image once
       |-- scan, SBOM, attest, sign
       |-- publish image@sha256:...
       v
Reviewed GitOps promotion MR [FUTURE MODULE]
       |-- dev -> test -> staging -> prod
       v
Argo CD sync [FUTURE MODULE]
       |
       v
Shared Kubernetes cluster
       |-- demo-dev
       |-- demo-test
       |-- demo-staging
       +-- demo-prod
```

**Do not treat a successful capstone CI pipeline as production deployment authorization.** A real production release requires additional security, identity, registry, GitOps, Argo CD and operational controls.

## 3. Capstone repository

```text
demo-app/
├── .gitlab-ci.yml
├── .gitignore
├── CODEOWNERS
├── README.md
├── src/
│   ├── __init__.py
│   └── calculator.py
├── tests/
│   └── test_calculator.py
└── scripts/
    ├── validate.py
    └── make_release.py
```

Use a new disposable GitLab project or a dedicated feature branch in the training project. Do not replace an existing production pipeline.

## 4. Build the application and tests

### `src/__init__.py`

Create an empty file.

### `src/calculator.py`

```python
def add(a: int, b: int) -> int:
    return a + b


def divide(a: int, b: int) -> float:
    if b == 0:
        raise ValueError("division by zero")
    return a / b
```

### `tests/test_calculator.py`

```python
import unittest
from src.calculator import add, divide


class CalculatorTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_divide(self):
        self.assertEqual(divide(9, 3), 3.0)

    def test_divide_by_zero(self):
        with self.assertRaises(ValueError):
            divide(9, 0)


if __name__ == "__main__":
    unittest.main()
```

### `scripts/validate.py`

```python
from pathlib import Path

required = [
    Path("src/calculator.py"),
    Path("tests/test_calculator.py"),
    Path("scripts/make_release.py"),
    Path(".gitlab-ci.yml"),
]
missing = [str(path) for path in required if not path.is_file()]
if missing:
    raise SystemExit("Missing required files: " + ", ".join(missing))
print("PASS: required project files present")
```

### `scripts/make_release.py`

```python
import hashlib
import json
import os
from pathlib import Path
import tarfile

dist = Path("dist")
dist.mkdir(exist_ok=True)
archive = dist / "demo-app-source.tar.gz"

with tarfile.open(archive, "w:gz") as tar:
    tar.add("src", arcname="src")

digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(dist / "SHA256SUMS").write_text(
    f"{digest}  {archive.name}\n", encoding="utf-8"
)
manifest = {
    "application": "demo-app",
    "source_commit": os.environ.get("CI_COMMIT_SHA", "local-lab"),
    "pipeline_id": os.environ.get("CI_PIPELINE_ID", "local-lab"),
    "artifact": archive.name,
    "sha256": digest,
    "artifact_type": "training-source-archive",
}
(dist / "release-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(manifest, indent=2))
```

The checksum is an integrity check, **not a cryptographic signature or provenance attestation**. Those require a trusted signing and verification workflow.

## 5. Enterprise-style GitLab CI/CD pipeline

Create `.gitlab-ci.yml`:

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages:
  - validate
  - test
  - package
  - verify

default:
  image: python:3.12-slim
  interruptible: true

variables:
  PYTHONDONTWRITEBYTECODE: "1"
  PYTHONUNBUFFERED: "1"

validate:
  stage: validate
  script:
    - python -m compileall -q src tests scripts
    - python scripts/validate.py

unit_tests:
  stage: test
  needs:
    - validate
  script:
    - mkdir -p reports
    - python -m unittest discover -s tests -v
    - python -m unittest discover -s tests -v > reports/tests.txt 2>&1
  artifacts:
    when: always
    paths:
      - reports/tests.txt
    expire_in: 7 days

package:
  stage: package
  needs:
    - job: unit_tests
      artifacts: false
  script:
    - python scripts/make_release.py
  artifacts:
    paths:
      - dist/demo-app-source.tar.gz
      - dist/SHA256SUMS
      - dist/release-manifest.json
    expire_in: 14 days

verify:
  stage: verify
  needs:
    - job: package
      artifacts: true
  script:
    - cd dist
    - sha256sum -c SHA256SUMS
    - python -c 'import json; from pathlib import Path; m=json.loads(Path("release-manifest.json").read_text()); assert m["application"]=="demo-app"; assert len(m["sha256"])==64; print("PASS: manifest validated")'
```

**Portability note:** `sha256sum` is available in the Debian-based Python container used here. The pipeline deliberately avoids Docker-in-Docker and cloud credentials.

**Runner requirements:** An authorized, non-privileged runner with a container executor must be available. Production builds should use pinned images and controlled dependency versions; the educational `python:3.12-slim` tag is not an immutable production pin.

## 6. Governance and branch protection

### `CODEOWNERS`

```text
# Replace with existing authorized GitLab groups
/.gitlab-ci.yml       @platform-reviewers
/scripts/             @platform-reviewers
```

GitLab CODEOWNERS approval enforcement depends on GitLab version, tier and project configuration. **Verify** that the groups exist and that owner approvals are actually required.

In the disposable project, configure:

1. Protected `main`; disable ordinary developer direct pushes.
2. Required successful pipeline before merge.
3. Independent MR review.
4. CODEOWNERS approval for pipeline-sensitive files where supported.
5. Restricted force-push and release-tag creation.
6. Least-privilege project and runner permissions.

Keep production GitOps configuration in a separate protected repository or project with its own approval and authorization controls.

## 7. Execute the lab

### Step A — Create a branch

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/ch005-foundations-capstone
git add .
git commit -m "ci: complete foundations capstone"
git push -u origin feature/ch005-foundations-capstone
```

### Step B — Open and validate a merge request

Open a GitLab MR from the feature branch to `main`. Validate the CI configuration with GitLab CI Lint. Confirm the four jobs appear:

```text
validate       passed
unit_tests     passed
package        passed
verify         passed
```

Inspect the job trace and artifact download. The release manifest must contain the current `CI_COMMIT_SHA` and `CI_PIPELINE_ID`.

### Step C — Run the equivalent checks locally

From the project root:

```bash
python -m compileall -q src tests scripts
python scripts/validate.py
python -m unittest discover -s tests -v
python scripts/make_release.py
cd dist
sha256sum -c SHA256SUMS
```

On Windows PowerShell, replace the final checksum command with:

```powershell
$m = Get-Content .\release-manifest.json | ConvertFrom-Json
$actual = (Get-FileHash .\demo-app-source.tar.gz -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $m.sha256) { throw "Checksum mismatch" }
"PASS: artifact checksum verified"
```

### Step D — Prove failure gating

Temporarily change `self.assertEqual(add(2, 3), 5)` to expect `6`. Commit and push to the feature branch.

Expected:
- Validation passes.
- Unit tests fail.
- Packaging and verification do not run.
- Test output artifact remains available.

Restore the test to expect `5`, commit and push. Confirm the MR pipeline is green again.

### Step E — Validate approval enforcement

With a nonprivileged test account, confirm that direct pushes to protected `main` are rejected. Verify that the MR cannot merge until required reviewers approve and the pipeline succeeds. Avoid performing bypass tests against production projects.

### Step F — Merge and verify traceability

After the required approvals, merge through GitLab. Record the MR URL, merged commit SHA, pipeline ID, artifact checksum and release manifest. Confirm the default-branch pipeline passes.

### Step G — Cleanup and recovery

Remove only disposable feature branches and lab resources. If the merged change needs to be undone, create a reviewed revert MR. Never force-push protected `main` or delete shared CI artifacts as a cleanup shortcut.

## 8. Evidence collection

| Evidence | Acceptance criterion |
| --- | --- |
| GitLab MR URL | Reviewed and approved change |
| Protected branch settings | Direct push restrictions effective |
| CI pipeline URL and ID | Four stages pass |
| Test logs | Three tests pass |
| Artifact checksum | `SHA256SUMS` verification passes |
| Release manifest | Source commit and pipeline ID match |
| Failure injection | Failed test blocks package and verify |
| Runner inventory | Runner trust tier and permissions documented |
| Secret audit | No privileged secrets available to MR jobs |
| Revert plan | Safe rollback procedure documented |

**Do not fabricate evidence.** Capture actual job output, links and settings from the disposable project.

## 9. Operational troubleshooting

| Symptom | Investigation | Recovery |
| --- | --- | --- |
| MR pipeline absent | `workflow: rules`, MR pipeline settings | Validate YAML and project configuration |
| Job stuck | Runner online, tags, scope, concurrency | Restore runner capacity or configuration |
| Test failure | Unit-test job log, expected results | Correct code/test and rerun |
| Artifact unavailable | `artifacts.paths`, retention, job status | Fix paths/expiry and rerun |
| Checksum mismatch | Artifact download, unexpected mutation | Rebuild from trusted source; investigate |
| MR merge blocked | Pipeline, approvals, conflicts | Address policy checks; do not bypass |
| Protected push succeeds unexpectedly | Branch rules, role privileges | Correct protection and audit activity |
| Credential leaked | Logs, variables, runner permissions | Revoke and rotate; follow incident process |

## 10. Production readiness gaps intentionally deferred

The foundations capstone is **not a production release pipeline** until these later-module controls are implemented:

- Immutable container image build and registry publishing.
- Software composition analysis, image scanning, SBOM and provenance attestation.
- Image signing and admission verification.
- Versioned Helm charts and tested values per environment.
- Protected GitOps repository with separate promotion approvals.
- Argo CD AppProjects, Applications/ApplicationSets, RBAC and sync policies.
- Kubernetes workload identity, external secrets, NetworkPolicies, ResourceQuotas and Pod Security.
- Progressive rollout, SLO monitoring, rollback drills and disaster recovery.

For a shared cluster, additionally assess dedicated production node pools and cluster-wide failure risks; separate production clusters may be required for stronger isolation.

## 11. Acceptance scorecard

| Control | Pass condition |
| --- | --- |
| Git governance | Protected branch, independent review, auditable merge |
| CI correctness | Lint/validation, unit tests, packaging and verification all pass |
| Negative testing | Intentional unit-test failure blocks downstream jobs |
| Artifact integrity | Downloaded archive matches recorded SHA-256 |
| Traceability | Manifest records actual source commit and pipeline ID |
| Runner security | No production secrets or privileged deployment access |
| Change recovery | Reviewed revert process available |
| Deployment separation | CI does not directly mutate production Kubernetes resources |

**Completion rule:** All eight controls must pass to close Part 01. If a control cannot be tested because of GitLab tier or permissions, mark it **Not Verified**, not Pass.

## 12. Knowledge assessment

1. Why should CI build once instead of rebuilding per environment?
2. How do merge request approval and production deployment approval differ?
3. Why is SHA-256 not a substitute for artifact signing?
4. What prevents untrusted MR code from accessing production credentials?
5. What does Argo CD add that a CI job running `kubectl apply` does not?
6. Which risks remain when Dev, Test, Staging and Production share a cluster?

## 13. Part 01 completion

You have an auditable GitLab workflow, an executable multi-stage CI pipeline, test and artifact evidence, negative-path verification, and a documented separation between build and production deployment authority.

**Next: Chapter 006 — Enterprise GitLab Repository Administration, Groups, Projects and Access Control.**
