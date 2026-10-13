# Chapter 019 — GitLab CI/CD Pipeline Testing, Quality Gates, Security Scanning and Failure Recovery

**Part 04 — Pipeline Design, Testing and Artifacts** | **Chapter 019 / 100**  
**Audience:** SRE, DevSecOps, platform and release engineers  
**Hands-on:** Disposable GitLab project, unprivileged container runner, Python standard library  
**Architecture:** GitLab CI checks source → trusted build publishes immutable image digest → approved GitOps promotion → Argo CD reconciles Dev, Test, Staging and Production namespaces in one Kubernetes cluster.

> **Security note:** This lab uses a synthetic policy check, not a substitute for real SAST, dependency, secret, container or IaC scanning. Do not put real credentials or production deployment access in MR pipelines.

## 1. Objectives

By completing this chapter you will:

1. Design a layered CI quality strategy: syntax, unit, integration, policy and security.
2. Build mandatory gates using explicit DAG dependencies and branch protection.
3. Generate real JUnit results and preserve failure evidence.
4. Distinguish scanning execution, findings, enforcement and approval policy.
5. Configure targeted retries, timeouts, failure handling and recovery.
6. Perform controlled failure injections and confirm release artifacts are blocked.
7. Troubleshoot flaky tests, runner failures, false positives and policy bypasses.
8. Produce a release-readiness evidence record.

## 2. Quality gate architecture

```text
Feature MR
   |
   +--> lint -------------+
   |                      |
   +--> policy -----------+--> package --> verify
   |                      |
   +--> unit tests -------+
   |                      |
   +--> security scan ----+
   |
   +--> nonblocking diagnostics (informational only)
   |
   v
Approved merge to protected main
   |
   v
Trusted build / publish (later chapters)
   |
   v
Reviewed GitOps change with immutable image digest
   |
   v
Argo CD reconciliation
```

A required gate must be both **executed** and **enforced**. A security job that produces a report but uses `allow_failure: true`, is omitted by `rules`, or is not a dependency of the package/release path may not block unsafe changes.

## 3. Testing layers and operational purpose

| Layer | What it catches | Example |
| --- | --- | --- |
| YAML and syntax | Invalid CI or application syntax | GitLab CI Lint, Python compilation |
| Unit | Logic regressions | Python `unittest` |
| Integration | Service and dependency behavior | Disposable test database/API |
| Contract | API/schema incompatibilities | Consumer/provider contract |
| Security | Vulnerabilities and exposed credentials | SAST, dependency, secret scanning |
| Policy | Organization-specific controls | Protected branch, signing, IaC policy |
| Package verification | Missing or corrupted build output | SHA-256, manifest checks |
| Deployment verification | Runtime behavior after release | Argo CD health, smoke tests, SLOs |

This chapter implements syntax, unit, a synthetic policy/security check, and artifact verification. Full integration environments, container scanning and Kubernetes release validation are developed in later chapters.

## 4. Gate semantics

```yaml
package:
  stage: package
  needs:
    - job: lint
      artifacts: false
    - job: unit_tests
      artifacts: false
    - job: policy_check
      artifacts: false
    - job: security_check
      artifacts: false
  script:
    - python scripts/package.py
```

This makes package creation depend on all four checks. The protected branch must also require a successful pipeline and approved merge request; `needs` alone is not governance.

### Failure behavior

- A failed required job blocks dependent jobs by default.
- `allow_failure: true` is suitable only for explicitly informational checks, never an enforcement gate.
- Use `retry` for transient runner/system failures, not deterministic test regressions.
- Use `timeout` to bound hangs.
- Use `artifacts: when: always` for nonsecret diagnostic/test reports.
- Avoid automatic deployment on a green MR; production promotion remains a reviewed GitOps operation.

## 5. Real security scanning integration

GitLab offers CI security templates and reports, with availability, supported analyzers and UI/approval features varying by GitLab edition, version and licensing. Examples include SAST, dependency scanning, secret detection and container scanning. A real enterprise implementation must:

1. Confirm that a supported scanner executes on the intended pipeline source.
2. Inspect its analyzer logs, exit status and produced report.
3. Decide how findings become blocking policy, including severity thresholds, exceptions and approvals.
4. Ensure protected branches cannot bypass enforcement by modifying YAML.
5. Validate with a safe, approved test finding in a disposable project.
6. Track scanner version, signature/database freshness, false positives and scan coverage.

**Critical distinction:** A scanner report displayed in GitLab is not necessarily a blocking gate. Some templates intentionally permit findings without failing the job. Enforcement may require security approval policies or explicit evaluated gates. Never assume a passing scan job means zero vulnerabilities.

### Illustrative template inclusion

```yaml
# Check compatibility, tier and current GitLab documentation before use.
include:
  - template: Jobs/SAST.gitlab-ci.yml
```

Do not add this illustrative include to the executable standard-library lab unless you have confirmed the analyzer support and runner capacity. Do not use a homegrown text search as a replacement for an actual scanner.

## 6. Hands-on lab — gated pipeline with failure evidence

### Prerequisites

- Disposable private project `https://gitlab.example.com/training/demo-app`.
- Nonprivileged runner supporting `python:3.12-slim`.
- GitLab CI Lint access and merge request permissions.
- No real credentials or privileged cluster access.

### Step A — Repository structure

```text
demo-app/
├── .gitlab-ci.yml
├── README.md
├── src/
│   ├── __init__.py
│   └── service.py
├── tests/
│   └── test_service.py
└── scripts/
    ├── run_tests.py
    ├── policy_check.py
    ├── security_check.py
    ├── package.py
    └── verify.py
```

Create empty `src/__init__.py`.

`README.md`:

```markdown
# demo-app

Disposable CI quality gates and failure recovery lab.
```

`src/service.py`:

```python
def normalize(value: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned:
        raise ValueError("value must not be empty")
    return cleaned


def status() -> dict[str, str]:
    return {"status": "ok"}
```

`tests/test_service.py`:

```python
import unittest
from src.service import normalize, status


class ServiceTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize("  DEMO  "), "demo")

    def test_empty(self):
        with self.assertRaises(ValueError):
            normalize("  ")

    def test_status(self):
        self.assertEqual(status(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
```

### Step B — Generate genuine JUnit results

`scripts/run_tests.py`:

```python
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


class RecordingResult(unittest.TextTestResult):
    pass


suite = unittest.defaultTestLoader.discover("tests")
cases = []


def collect(item):
    if isinstance(item, unittest.TestSuite):
        for child in item:
            collect(child)
    else:
        cases.append(item)


collect(suite)
result = unittest.TextTestRunner(resultclass=RecordingResult, verbosity=2).run(suite)
failures = {case.id(): details for case, details in result.failures}
errors = {case.id(): details for case, details in result.errors}
skips = {case.id(): reason for case, reason in result.skipped}

root = ET.Element("testsuite", {
    "name": "demo-app",
    "tests": str(result.testsRun),
    "failures": str(len(result.failures)),
    "errors": str(len(result.errors)),
    "skipped": str(len(result.skipped)),
})
for case in cases:
    name = case.id()
    node = ET.SubElement(root, "testcase", {
        "classname": case.__class__.__module__ + "." + case.__class__.__name__,
        "name": case._testMethodName,
    })
    if name in failures:
        ET.SubElement(node, "failure", message="assertion failed").text = failures[name]
    if name in errors:
        ET.SubElement(node, "error", message="test error").text = errors[name]
    if name in skips:
        ET.SubElement(node, "skipped", message=skips[name])

Path("reports").mkdir(exist_ok=True)
ET.ElementTree(root).write("reports/junit.xml", encoding="utf-8", xml_declaration=True)
sys.exit(0 if result.wasSuccessful() else 1)
```

The report reflects actual test results; the script exits nonzero when tests fail. Use a maintained JUnit reporter for large production test suites.

### Step C — Policy and synthetic security checks

`scripts/policy_check.py`:

```python
from pathlib import Path

required = [
    Path("README.md"),
    Path(".gitlab-ci.yml"),
    Path("src/service.py"),
    Path("tests/test_service.py"),
]
missing = [str(path) for path in required if not path.is_file()]
if missing:
    raise SystemExit(f"FAIL: required files missing: {missing}")
print("PASS: repository policy")
```

`scripts/security_check.py`:

```python
from pathlib import Path

# Synthetic training sentinel only: not a real secret scanner.
marker = "DEMO_FORBIDDEN_MARKER_123"
for folder in ("src", "tests"):
    for path in Path(folder).rglob("*.py"):
        if marker in path.read_text(encoding="utf-8"):
            raise SystemExit(f"FAIL: synthetic marker in {path}")
print("PASS: synthetic security policy")
```

### Step D — Package and verify

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

sha = hashlib.sha256(archive.read_bytes()).hexdigest()
(out / "SHA256SUMS").write_text(f"{sha}  {archive.name}\n", encoding="utf-8")
(out / "manifest.json").write_text(json.dumps({
    "application": "demo-app",
    "commit": os.getenv("CI_COMMIT_SHA", "local"),
    "pipeline": os.getenv("CI_PIPELINE_ID", "local"),
    "sha256": sha,
}, indent=2) + "\n", encoding="utf-8")
print("PASS: package created")
```

`scripts/verify.py`:

```python
import hashlib
import json
from pathlib import Path

out = Path("dist")
archive = out / "demo-app.tar.gz"
manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest == manifest["sha256"], "archive digest mismatch"
assert (out / "SHA256SUMS").read_text(encoding="utf-8").strip() == (
    f"{digest}  {archive.name}"
), "checksum manifest mismatch"
assert manifest["application"] == "demo-app"
print("PASS: package integrity")
```

### Step E — GitLab CI configuration

`.gitlab-ci.yml`:

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages: [validate, test, package, verify]

default:
  image: python:3.12-slim
  interruptible: true

variables:
  PYTHONDONTWRITEBYTECODE: "1"

lint:
  stage: validate
  script:
    - python -m compileall -q src tests scripts
    - test -s README.md
  timeout: 5m

policy_check:
  stage: validate
  script:
    - python scripts/policy_check.py

security_check:
  stage: validate
  script:
    - python scripts/security_check.py

unit_tests:
  stage: test
  needs:
    - job: lint
      artifacts: false
  script:
    - python scripts/run_tests.py
  timeout: 10m
  retry:
    max: 1
    when:
      - runner_system_failure
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
    - job: policy_check
      artifacts: false
    - job: security_check
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

**Enforcement:** `package` cannot run until all four mandatory checks pass. No job has `allow_failure: true`; no job deploys or publishes to production.

### Step F — Local validation

```bash
python -m compileall -q src tests scripts
python scripts/policy_check.py
python scripts/security_check.py
python scripts/run_tests.py
python scripts/package.py
python scripts/verify.py
```

Expected:

```text
PASS: repository policy
PASS: synthetic security policy
Ran 3 tests
OK
PASS: package created
PASS: package integrity
```

### Step G — MR pipeline

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch019-quality-gates
# Add lab files above
git add .gitlab-ci.yml README.md src/ tests/ scripts/
git commit -m "ci: implement mandatory quality gates and recovery tests"
git push -u origin feature/ch019-quality-gates
```

Open an MR and validate with GitLab CI Lint.

Expected:

```text
lint             passed
policy_check     passed
security_check   passed
unit_tests       passed
package          passed
verify           passed
```

Inspect the DAG graph and the JUnit report. Record pipeline ID, job durations, artifact checksum and runner identity.

## 7. Failure-injection experiments

### Experiment 1 — Unit-test regression

Change the expected normalized result in `test_normalize` from `"demo"` to `"wrong"`. Commit and push.

Expected: `unit_tests` fails and produces a JUnit failure; `package` and `verify` do not run. Restore and rerun.

### Experiment 2 — Security gate violation

Add the harmless marker `DEMO_FORBIDDEN_MARKER_123` to a comment in `src/service.py`. Commit and push.

Expected: `security_check` fails and blocks packaging. Remove marker and rerun.

### Experiment 3 — Missing artifact

In a separate disposable branch, temporarily set `verify.needs[0].artifacts` to `false`.

Expected: verification fails due to missing `dist` files. Restore `true` and confirm recovery.

### Experiment 4 — Runner outage

Use a deliberately unmatched runner tag on a harmless job in the disposable project, or pause **only a disposable runner**. Expected: job pending. Diagnose eligibility and restore. Do not disable production/shared runners.

### Experiment 5 — Gate bypass attempt

In a disposable feature branch, remove `security_check` from `package.needs`. Observe that packaging may run before the security check completes; this demonstrates why CI configuration review is critical. Restore the edge.

**Important:** A contributor able to edit `.gitlab-ci.yml` can alter MR checks. Protected branch rules, required approvals, centrally governed security policies and trusted release validation must defend against such modifications.

## 8. Failure classification and retry policy

| Failure | Retry? | Response |
| --- | --- | --- |
| Assertion failure | No automatic retry | Fix code or test |
| Deterministic policy violation | No | Fix violation |
| Runner system failure | Limited retry | Inspect runner health |
| Registry transient 5xx | Limited, bounded retry | Check registry status |
| Authentication denied | No blind retry | Fix identity/permissions |
| Resource quota exceeded | Usually no | Review requests and capacity |
| Timeout | Investigate first | Identify slow/hung work |
| Flaky integration test | Quarantine with owner and expiry, not silent bypass | Remove flakiness |

Use retries sparingly; repeated retries can hide infrastructure degradation and increase CI costs.

## 9. Observability and quality SLOs

Track these independently:

- **CI infrastructure availability:** Ability to create and execute jobs, excluding code failures.
- **Quality gate coverage:** Percentage of required MRs with all mandated checks present and enforced.
- **Security scanner coverage:** Repositories, languages, dependencies and artifact types actually scanned.
- **Pipeline duration p95:** Time from pipeline creation to terminal state.
- **Runner queue time p95:** Time waiting for eligible runner.
- **Flaky-test rate:** Tests that fail then pass without source changes.
- **Artifact integrity failures:** Missing/corrupt output incidents.
- **Mean time to restore CI:** Time from infrastructure fault detection to validated recovery.

Set numeric thresholds from observed baselines. Do not interpret a passing pipeline as proof of zero security risk.

## 10. Troubleshooting runbook

| Symptom | Likely cause | Safe action |
| --- | --- | --- |
| Scan job succeeds despite findings | Informational template/report-only behavior | Verify enforcement/approval policy |
| Package starts too early | Missing `needs` edge | Restore dependency and review changes |
| Unit tests fail intermittently | Flaky test or nondeterministic environment | Reproduce and isolate root cause |
| JUnit report missing | Wrong path/XML or early failure | Inspect artifact upload and test runner |
| Pipeline not created | `workflow: rules` mismatch | CI Lint and source verification |
| Job pending | Runner tags, protection or capacity | Inspect runner eligibility |
| Artifact checksum mismatch | Corruption or wrong artifact | Stop release, rebuild and investigate |
| Security job skipped | `rules`, unsupported analyzer or policy issue | Fix coverage and block release |
| Secrets in logs | Unsafe debugging or untrusted code | Revoke/rotate, contain and investigate |
| Retry storm | Broad retry configuration | Limit retries and diagnose root cause |

## 11. Incident response and rollback

1. Identify affected MR, commit, pipeline, first failed job and runner.
2. Determine whether failure is code, infrastructure, security or policy related.
3. Preserve authorized nonsecret logs and test reports.
4. For suspected credential exposure, quarantine runner and revoke/rotate identities.
5. Correct the issue through a reviewed MR.
6. Rerun required gates and verify artifacts.
7. If an unsafe change reached protected main, use an approved revert MR.
8. If an image has already been promoted, restore the last known-good **immutable digest** via approved GitOps rollback, and verify Argo CD/application health.

Do not rely on CI reruns alone to undo changes already reconciled into Kubernetes.

## 12. Acceptance checklist

- [ ] CI YAML validates in GitLab CI Lint.
- [ ] All six jobs pass on a clean MR.
- [ ] Unit regression fails with genuine JUnit evidence.
- [ ] Security synthetic marker blocks packaging.
- [ ] Missing artifact causes verification failure.
- [ ] Runner unavailability diagnosed without disrupting shared infrastructure.
- [ ] Removing a required gate is recognized as a governance vulnerability.
- [ ] Retry policy distinguishes transient and deterministic failures.
- [ ] Security scanning and enforcement are understood as separate controls.
- [ ] Protected branch approvals and centrally governed policies reviewed.
- [ ] No production credentials or deployment access in MR jobs.
- [ ] Actual job timings, runner details and checksums recorded.
- [ ] Recovery and reviewed rollback documented.

## 13. Evidence template

```text
CHAPTER 019 — QUALITY GATES AND FAILURE RECOVERY
GitLab version/tier:
Project / MR:
Commit SHA:
Pipeline ID:
Runner:
CI Lint:
Lint:
Policy:
Security:
Unit tests / JUnit:
Package:
Verify / SHA256:
Test regression negative test:
Security marker negative test:
Missing artifact negative test:
Runner outage negative test:
Gate bypass review:
Scanner execution vs enforcement review:
Observed queue p95:
Observed pipeline duration p95:
Recovery MR:
Reviewer:
Open risks and owners:
```

## 14. Knowledge checks

1. Why is a successful security scanning job not necessarily a blocking security policy?
2. How can `allow_failure` undermine a mandatory quality gate?
3. Why must packaging explicitly depend on all required checks?
4. When is automatic retry appropriate?
5. Why should real test failures be reflected in both job status and JUnit?
6. What prevents contributors from removing security checks from their own CI YAML?
7. How is CI recovery different from rolling back an Argo CD deployment?

## 15. Completion

**Pass:** You validate a six-job pipeline, demonstrate mandatory quality gates with controlled failures, verify artifacts, distinguish scanning from enforcement, and document an actionable recovery procedure.

**Next: Chapter 020 — Enterprise GitLab Pipeline Design, Testing and Runner Operations Capstone**, completing Part 04.
