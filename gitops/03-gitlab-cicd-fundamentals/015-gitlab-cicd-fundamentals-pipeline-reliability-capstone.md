# Chapter 015 — GitLab CI/CD Fundamentals and Pipeline Reliability Capstone

**Part 03 — Final Capstone** | **Chapter 015 / 100**  
**Role:** SRE / Infrastructure / Platform Engineering  
**Scope:** GitLab CI configuration, pipeline reliability, runner operations, governance and safe failure recovery  
**Lab environment:** Disposable private GitLab project, unprivileged container runner, Python standard library  
**Reference deployment model:** GitLab CI → immutable artifact → approved GitOps promotion → Argo CD → Dev/Test/Staging/Prod namespaces in one Kubernetes cluster

> **Safety:** This is a nonproduction lab. No cloud keys, real secrets, production kubeconfigs, customer data, privileged runner sockets or actual deployments are needed.

## 1. Capstone objectives

This project integrates Chapters 011–014. By the end, you will demonstrate:

1. Correct `workflow: rules` for merge-request and default-branch pipelines.
2. Job-level rules, stage ordering, and explicit DAG `needs` dependencies.
3. Safe variable handling, including precedence and protected-ref considerations.
4. Genuine unit-test reporting through JUnit XML.
5. Artifact production, checksum verification, access and retention review.
6. Cache isolation and resilience to cache misses.
7. Negative testing for failing tests, policy violations, missing artifacts and runner unavailability.
8. Operational evidence, measurable reliability SLOs, incident response and rollback.

## 2. Architecture and trust boundaries

```text
Developer -> feature branch -> MR -> GitLab pipeline
                                       |
                          +------------+-----------+
                          |                        |
                     lint + policy              unit tests
                          |                        |
                          +----------+-------------+
                                     |
                                   package
                                     |
                                  verify
                                     |
                        approved merge to main
                                     |
                           trusted build/publish
                             (later chapters)
                                     |
                       immutable container digest
                                     |
                     reviewed GitOps promotion MRs
                      dev -> test -> staging -> prod
                                     |
                              Argo CD sync
                                     |
                     shared Kubernetes cluster
```

**Separation of duties:** Passing CI does not authorize production release. GitOps production changes need independent approval, Argo CD RBAC and Kubernetes permissions. Namespace separation is not equivalent to cluster isolation.

## 3. Enterprise acceptance targets

| Domain | Target |
| --- | --- |
| Pipeline creation | MR and default-branch events only, as configured |
| Quality gates | All required jobs must pass before packaging |
| Tests | Actual tests pass; failures surface in JUnit and job status |
| Policy | Synthetic forbidden marker blocks packaging |
| Artifacts | Explicit producer/consumer dependencies and checksum verification |
| Secrets | No real credentials in YAML, jobs, logs, artifacts or caches |
| Runner | Nonprivileged execution, documented capacity and trust tier |
| Reliability | Capture real baseline and define alert thresholds |
| Recovery | Failure injection, diagnosis, recovery and reviewed revert documented |

## 4. Repository layout

```text
demo-app/
├── .gitlab-ci.yml
├── README.md
├── src/
│   ├── __init__.py
│   └── service.py
├── tests/
│   └── test_service.py
├── scripts/
│   ├── policy.py
│   ├── run_tests.py
│   ├── package.py
│   └── verify.py
└── docs/
    └── RUNBOOK.md
```

Create an empty `src/__init__.py`.

## 5. Application and tests

`src/service.py`:

```python
def normalize_name(name: str) -> str:
    value = name.strip()
    if not value:
        raise ValueError("name cannot be blank")
    return value.lower()


def health() -> dict[str, str]:
    return {"status": "ok"}
```

`tests/test_service.py`:

```python
import unittest
from src.service import normalize_name, health


class ServiceTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_name("  DEMO  "), "demo")

    def test_blank_name(self):
        with self.assertRaises(ValueError):
            normalize_name("  ")

    def test_health(self):
        self.assertEqual(health(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
```

## 6. Policy check

`scripts/policy.py`:

```python
from pathlib import Path

required = [
    Path("README.md"),
    Path(".gitlab-ci.yml"),
    Path("src/service.py"),
    Path("tests/test_service.py"),
    Path("docs/RUNBOOK.md"),
]
missing = [str(path) for path in required if not path.is_file()]
if missing:
    raise SystemExit(f"FAIL: missing required files: {missing}")

for folder in ("src", "tests", "scripts"):
    for path in Path(folder).rglob("*.py"):
        if "DEMO_FORBIDDEN_MARKER_123" in path.read_text(encoding="utf-8"):
            raise SystemExit(f"FAIL: synthetic policy marker in {path}")

print("PASS: required files and synthetic policy")
```

This is a deliberately narrow training check, **not** a real secret detector. Production secret detection and supply-chain scanning are separate controls.

## 7. Real JUnit report generator

`scripts/run_tests.py`:

```python
import sys
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


class Result(unittest.TextTestResult):
    def startTest(self, test):
        if not hasattr(self, "started"):
            self.started = {}
        self.started[test.id()] = time.monotonic()
        super().startTest(test)

    def stopTest(self, test):
        if not hasattr(self, "durations"):
            self.durations = {}
        self.durations[test.id()] = time.monotonic() - self.started[test.id()]
        super().stopTest(test)


suite = unittest.defaultTestLoader.discover("tests")
tests = []

def collect(s):
    for item in s:
        if isinstance(item, unittest.TestSuite):
            collect(item)
        else:
            tests.append(item)

collect(suite)
result = unittest.TextTestRunner(resultclass=Result, verbosity=2).run(suite)
root = ET.Element("testsuite", {
    "name": "demo-app",
    "tests": str(result.testsRun),
    "failures": str(len(result.failures)),
    "errors": str(len(result.errors)),
    "skipped": str(len(result.skipped)),
})
failures = {t.id(): message for t, message in result.failures}
errors = {t.id(): message for t, message in result.errors}
skipped = {t.id(): reason for t, reason in result.skipped}
for case in tests:
    name = case.id()
    node = ET.SubElement(root, "testcase", {
        "classname": case.__class__.__module__ + "." + case.__class__.__name__,
        "name": case._testMethodName,
        "time": f"{result.durations.get(name, 0):.4f}",
    })
    if name in failures:
        ET.SubElement(node, "failure", {"message": "assertion failure"}).text = failures[name]
    if name in errors:
        ET.SubElement(node, "error", {"message": "test error"}).text = errors[name]
    if name in skipped:
        ET.SubElement(node, "skipped", {"message": skipped[name]})
Path("reports").mkdir(exist_ok=True)
ET.ElementTree(root).write("reports/junit.xml", encoding="utf-8", xml_declaration=True)
sys.exit(0 if result.wasSuccessful() else 1)
```

This generator records genuine test results and returns nonzero on failure. For large production suites, use a maintained JUnit reporting library.

## 8. Package and verify

`scripts/package.py`:

```python
import hashlib
import json
import os
from pathlib import Path
import tarfile

out = Path("dist")
out.mkdir(exist_ok=True)
archive = out / "demo-app.tar.gz"
with tarfile.open(archive, "w:gz") as tar:
    tar.add("src", arcname="src")

digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(out / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
(out / "manifest.json").write_text(json.dumps({
    "application": "demo-app",
    "commit": os.getenv("CI_COMMIT_SHA", "local"),
    "pipeline": os.getenv("CI_PIPELINE_ID", "local"),
    "sha256": digest
}, indent=2) + "\n", encoding="utf-8")
print(f"PASS: packaged training archive SHA256={digest}")
```

`scripts/verify.py`:

```python
import hashlib
import json
from pathlib import Path

out = Path("dist")
archive = out / "demo-app.tar.gz"
manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
expected = manifest["sha256"]
actual = hashlib.sha256(archive.read_bytes()).hexdigest()
assert actual == expected, "archive digest differs from manifest"
assert (out / "SHA256SUMS").read_text(encoding="utf-8").strip() == (
    f"{expected}  {archive.name}"
), "SHA256SUMS differs from manifest"
assert manifest["application"] == "demo-app"
print("PASS: archive integrity and metadata")
```

This is an integrity demonstration, **not** a signature, attestation or production container image.

## 9. Complete GitLab CI pipeline

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
  - package
  - verify

default:
  image: python:3.12-slim
  interruptible: true

variables:
  PYTHONDONTWRITEBYTECODE: "1"
  APP_NAME: "demo-app"

lint:
  stage: validate
  script:
    - python -m compileall -q src tests scripts
    - test -s README.md

policy:
  stage: validate
  script:
    - python scripts/policy.py

unit_tests:
  stage: test
  needs:
    - job: lint
      artifacts: false
  script:
    - python scripts/run_tests.py
  artifacts:
    when: always
    reports:
      junit: reports/junit.xml
    paths:
      - reports/junit.xml
    expire_in: 7 days

package:
  stage: package
  needs:
    - job: lint
      artifacts: false
    - job: policy
      artifacts: false
    - job: unit_tests
      artifacts: false
  script:
    - python scripts/package.py
  artifacts:
    paths:
      - dist/demo-app.tar.gz
      - dist/SHA256SUMS
      - dist/manifest.json
    expire_in: 7 days

verify:
  stage: verify
  needs:
    - job: package
      artifacts: true
  script:
    - python scripts/verify.py
```

**Important:** `package` depends on all three required gates. `unit_tests` may begin after `lint` while `policy` runs, but `package` waits for `policy` and `unit_tests`. No job deploys anything.

## 10. Operational runbook

`docs/RUNBOOK.md`:

```markdown
# Demo CI Pipeline Reliability Runbook

## Symptoms
- Pipeline not created
- Job stuck pending
- Unit tests fail
- Policy gate fails
- Artifact missing or checksum mismatch

## Initial triage
1. Identify MR URL, pipeline ID, commit SHA and pipeline source.
2. Review workflow rules and CI Lint.
3. Check runner eligibility, tags, protection and concurrency.
4. Find the first failing job and its direct dependencies.
5. Inspect artifact paths, expiry and download settings.
6. Do not print CI credentials while debugging.

## Recovery
- Correct configuration through a reviewed MR.
- Retry only transient infrastructure failures.
- Restore required quality gates before merging.
- Revert a merged faulty change through an approved MR.

## Evidence
Record job status, queue duration, pipeline duration,
runner identity, root cause, mitigation and validation.
```

`README.md`:

```markdown
# demo-app

Disposable GitLab CI/CD fundamentals and pipeline reliability capstone.

No production credentials or deployments.
```

## 11. Lab execution

### Step A — Local validation

From the repository root:

```bash
python -m compileall -q src tests scripts
python scripts/policy.py
python scripts/run_tests.py
python scripts/package.py
python scripts/verify.py
```

Expected:

```text
PASS: required files and synthetic policy
Ran 3 tests
OK
PASS: packaged training archive ...
PASS: archive integrity and metadata
```

### Step B — Create feature MR

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch015-pipeline-capstone
# Add all files above using your editor
git add .gitlab-ci.yml README.md src/ tests/ scripts/ docs/
git commit -m "ci: complete pipeline reliability capstone"
git push -u origin feature/ch015-pipeline-capstone
```

Create an MR. Validate the configuration using GitLab CI Lint.

Expected five jobs:

```text
lint         passed
policy       passed
unit_tests   passed
package      passed
verify       passed
```

Record the MR URL, pipeline ID, job timings and runner identity.

### Step C — Failure injection 1: test regression

Temporarily change the expected normalized value in `test_normalize` from `"demo"` to `"incorrect"`, commit and push.

Expected: `unit_tests` fails and publishes a JUnit failure; `package` and `verify` are blocked. Restore the correct expectation and verify green.

### Step D — Failure injection 2: synthetic policy violation

Temporarily add a comment containing `DEMO_FORBIDDEN_MARKER_123` to `src/service.py`, commit and push.

Expected: `policy` fails, blocking `package` even if tests pass. Remove marker and rerun.

### Step E — Failure injection 3: missing artifact

In a separate disposable branch, temporarily set `verify.needs` to:

```yaml
needs:
  - job: package
    artifacts: false
```

Expected: `verify` fails because `dist/` is unavailable in the downstream job. Restore `artifacts: true` and verify recovery.

### Step F — Failure injection 4: runner unavailability

**Do not disable shared or production runners.** Use a disposable training runner, or in a separate branch add an intentionally unmatched tag to one harmless test job:

```yaml
tags:
  - training-runner-tag-that-does-not-exist
```

Expected: that job remains pending if no eligible runner has the tag. Record queue duration and diagnostic evidence; remove the tag and verify recovery. Stop the experiment promptly to avoid unnecessary CI resource consumption.

### Step G — Variable safety review

In the disposable project, add a synthetic project variable `LAB_OVERRIDE=project-level`. Add a temporary validation job or local script that checks equality without printing its value. Verify project-level precedence over a YAML default, then remove the variable.

Review:
- Protected-variable eligibility on MR vs protected refs.
- Runner trust tier and whether privileged tokens are accessible.
- Artifact, JUnit and job-log access.
- Cache settings (if enabled).
- Pipeline variable override permissions.

Do not add real secrets to the lab.

### Step H — Governance and recovery

After clean pipeline and required approvals, merge to protected `main`. Confirm a default-branch pipeline runs. If reversal is needed, create a reviewed revert MR; never rewrite protected branch history.

## 12. Reliability measurements and SLOs

Record a baseline from multiple real pipeline executions before setting operational thresholds.

| Metric | Measurement method | Initial policy |
| --- | --- | --- |
| Pipeline success rate | Successful required pipelines / total required pipelines | Define baseline and target |
| Queue wait p95 | Job creation to runner start | Alert on sustained growth |
| Pipeline duration p95 | Creation to terminal state | Compare against baseline |
| Runner saturation | Active jobs / effective capacity | Scale or rebalance responsibly |
| Infrastructure retry rate | Retries due to runner/system failures | Investigate rising trend |
| Artifact failure rate | Missing/corrupt artifact failures | Target near zero |
| MR gate bypasses | Unauthorized merges or missing checks | Zero tolerated |
| Time to recover CI | Detection to verified pipeline recovery | Set team-specific objective |

**Illustrative targets, not measured results:** Some teams begin with 99% required-pipeline infrastructure availability and a 15-minute p95 queue-time alert, then refine based on their runner fleet and business requirements. Test failures from bad code should not be misclassified as CI infrastructure outages.

## 13. Troubleshooting and incident response

| Symptom | Likely cause | Response |
| --- | --- | --- |
| Pipeline absent | Workflow excluded event | Verify `CI_PIPELINE_SOURCE`, CI Lint and MR settings |
| Pending job | Runner unavailable or tag mismatch | Check runner scope, tags, concurrency and health |
| Tests fail | Code regression or flaky test | Reproduce; do not mask with broad retries |
| Policy bypass | Missing `needs` edge or misconfigured approvals | Block merge and restore required gate |
| Missing artifact | Wrong `needs: artifacts` or expiry | Verify producer, paths and retention |
| JUnit report missing | XML/path/report parsing issue | Inspect report artifact and test runner exit |
| Variable missing | Protection, scope or precedence | Inspect settings without logging values |
| Runner compromise suspected | Untrusted code on privileged executor | Quarantine runner, revoke credentials, investigate |
| Repeated long pipelines | Queue saturation or slow critical path | Measure first, optimize DAG and capacity |
| Production sync unexpectedly triggered | CI has excessive deployment authority | Disable/revoke, investigate GitOps/Argo CD access |

### Incident triage sequence

1. Identify affected pipelines, users, repositories and time window.
2. Check GitLab availability and runner fleet health.
3. Distinguish code/test failure from infrastructure or policy failure.
4. Preserve nonsecret logs, pipeline IDs, MR approvals and relevant audit events.
5. Contain privileged exposure if suspected.
6. Apply the smallest safe fix through a reviewed MR.
7. Rerun validation, monitor recovery and document preventive action.

## 14. Evidence and assessment worksheet

```text
CHAPTER 015 — PIPELINE RELIABILITY CAPSTONE
GitLab version/tier:
Training project:
MR URL:
Merge SHA:
MR pipeline ID:
Default-branch pipeline ID:
Runner identity/trust tier:
Lint result:
Policy result:
Unit tests + JUnit result:
Package artifact checksum:
Verify result:
Test failure blocked package: PASS / FAIL
Policy failure blocked package: PASS / FAIL
Missing artifact test: PASS / FAIL
Runner pending/recovery test: PASS / FAIL
Protected variable review:
Artifact retention/access:
Observed queue p95:
Observed pipeline duration p95:
Reviewer:
Open risks / remediation owners:
```

## 15. Final acceptance checklist

- [ ] Pipeline YAML validates and clean MR jobs pass.
- [ ] MR and protected-main pipeline sources behave as intended.
- [ ] Required gates cannot be bypassed by DAG scheduling.
- [ ] Real failing tests generate failing JUnit reports and block packaging.
- [ ] Synthetic policy failure blocks packaging.
- [ ] Artifact checksum verified through explicit dependency.
- [ ] Runner pending scenario diagnosed without impacting shared services.
- [ ] Variable and secret boundaries reviewed.
- [ ] No production credentials or deployment operations in MR jobs.
- [ ] Actual reliability measurements captured and SLO proposals documented.
- [ ] Recovery and reviewed revert process validated.
- [ ] MR, pipeline and audit evidence retained according to policy.

**Capstone pass condition:** All mandatory controls are observed and documented. Any failed or unavailable control must be recorded as a gap with an owner; do not claim enterprise readiness based solely on a green pipeline.

## 16. Part 03 completion and next chapter

You now have a reusable, testable, observable and governance-aware GitLab CI pipeline baseline. Later modules extend it with runner infrastructure, secure container builds, Helm, Argo CD and multi-cloud platform operations.

**Next: Chapter 016 — GitLab Runner Architecture, Executors, Registration and Lifecycle**, beginning Part 04 — Pipeline Design, Testing and Artifacts / Runner Infrastructure.
