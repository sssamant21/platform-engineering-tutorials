# Chapter 020 — Enterprise GitLab Pipeline Design, Testing and Runner Operations Capstone

**Part 04 — Final Capstone** | **Chapter 020 of 100**  
**Audience:** SRE, infrastructure, platform, DevSecOps and CI operations engineers  
**Prerequisites:** Chapters 016–019; GitLab CI Lint; a disposable GitLab project and isolated nonprivileged runner  
**Outcome:** Build, break, recover and assess an enterprise-style CI pipeline without deploying anything to production.

> **Safety:** All names and data are synthetic. This exercise requires no cloud credentials, cluster-admin access, Docker socket, production namespace access or privileged runner. Conduct disruption tests only on disposable jobs and runners.

## 1. Capstone mission

You are the on-call platform engineer responsible for a GitLab CI service used by multiple teams. Your task is to demonstrate a reliable pipeline that:

- Runs on an explicitly selected runner.
- Reuses centrally understandable CI configuration.
- Executes mandatory syntax, policy, security-sentinel and unit-test gates.
- Starts a downstream child pipeline **only after all required parent checks pass**.
- Creates and verifies an archive with SHA-256 integrity evidence.
- Produces a genuine JUnit report.
- Propagates downstream failures to the parent pipeline.
- Supports repeatable troubleshooting and safe recovery.
- Records operational evidence for an SRE readiness review.

A green pipeline alone is **not** the acceptance criterion: you must show that deliberate failures are detected, enforced and recovered.

## 2. Reference architecture

```text
Developer -> feature MR
                 |
                 v
       GitLab parent pipeline
          /      |       \
       lint    policy    security sentinel
          \      |       /
             unit tests (JUnit)
                 |
            child trigger
            strategy: mirror
                 |
                 v
        GitLab child pipeline
           contract test
                 |
           package archive
                 |
        checksum + manifest verify
                 |
          Approved MR merge
                 |
       Protected main pipeline
                 |
        Later: trusted image build
                 |
       Reviewed GitOps digest promotion
                 |
         Argo CD reconciliation
          dev/test/staging/prod
       (namespaces in one cluster)
```

**Trust model:** Merge request jobs are untrusted. No production secrets are exposed to them. Release authority remains separate from source validation. Shared Kubernetes namespaces do not provide the same isolation as dedicated clusters.

## 3. Operational controls and acceptance criteria

| Control | Expected behavior | Evidence |
| --- | --- | --- |
| Pipeline source | MR and default-branch pipelines only | Pipeline source and CI Lint |
| Runner eligibility | Training-tagged jobs use training runner | Job details, runner ID |
| Runner privilege | Nonprivileged, no host Docker socket | Runner configuration review |
| Mandatory gates | Failure blocks child trigger | Failed-job pipeline graph |
| Unit tests | Real JUnit output and nonzero failure exit | GitLab test report |
| Child pipeline | Correct source rules and mirrored status | Parent/child IDs |
| Artifact integrity | SHA-256 and manifest checked | Child verify job |
| Cache correctness | Build succeeds without cache | Runner/cache observation |
| Recovery | Revert/fix via reviewed commit and rerun | Before/after pipelines |
| Governance | Protected branch and approvals verified | Project settings review |
| Reliability | Baseline queue and execution times recorded | Job timestamps |
| Security | No sensitive output in logs/artifacts | Access and content review |

## 4. Lab repository layout

```text
demo-app/
├── .gitlab-ci.yml
├── README.md
├── ci/
│   ├── common.yml
│   ├── validation.yml
│   └── child.yml
├── src/
│   ├── __init__.py
│   └── service.py
├── tests/
│   └── test_service.py
├── scripts/
│   ├── policy.py
│   ├── security_sentinel.py
│   ├── run_tests.py
│   ├── package.py
│   └── verify.py
└── docs/
    └── RUNBOOK.md
```

Create an empty `src/__init__.py`.

### Application: `src/service.py`

```python
def normalize(value: str) -> str:
    result = value.strip().lower()
    if not result:
        raise ValueError("blank input")
    return result


def health() -> dict[str, str]:
    return {"status": "ok"}
```

### Tests: `tests/test_service.py`

```python
import unittest
from src.service import health, normalize


class ServiceTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize("  DEMO  "), "demo")

    def test_empty(self):
        with self.assertRaises(ValueError):
            normalize(" ")

    def test_health(self):
        self.assertEqual(health(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
```

### Policy: `scripts/policy.py`

```python
from pathlib import Path

required = [
    ".gitlab-ci.yml", "README.md", "ci/common.yml",
    "ci/validation.yml", "ci/child.yml",
    "src/service.py", "tests/test_service.py", "docs/RUNBOOK.md",
]
missing = [p for p in required if not Path(p).is_file()]
if missing:
    raise SystemExit(f"FAIL: missing files: {missing}")
print("PASS: repository structure policy")
```

### Synthetic security sentinel: `scripts/security_sentinel.py`

```python
from pathlib import Path

# Training-only sentinel, NOT a real security scanner.
marker = "DEMO_FORBIDDEN_MARKER_123"
for folder in ("src", "tests"):
    for file in Path(folder).rglob("*.py"):
        if marker in file.read_text(encoding="utf-8"):
            raise SystemExit(f"FAIL: synthetic violation: {file}")
print("PASS: synthetic security sentinel")
```

**Production requirement:** Replace the sentinel with actual supported SAST, dependency, secret, container and IaC scanners plus enforceable approval policies. A scanner report by itself may be informational rather than blocking.

## 5. Genuine JUnit reporting

`scripts/run_tests.py`:

```python
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

suite = unittest.defaultTestLoader.discover("tests")
cases = []


def walk(item):
    if isinstance(item, unittest.TestSuite):
        for child in item:
            walk(child)
    else:
        cases.append(item)


walk(suite)
result = unittest.TextTestRunner(verbosity=2).run(suite)
failures = {case.id(): text for case, text in result.failures}
errors = {case.id(): text for case, text in result.errors}
skips = {case.id(): reason for case, reason in result.skipped}

root = ET.Element("testsuite", {
    "name": "demo-app",
    "tests": str(result.testsRun),
    "failures": str(len(result.failures)),
    "errors": str(len(result.errors)),
    "skipped": str(len(result.skipped)),
})
for case in cases:
    node = ET.SubElement(root, "testcase", {
        "classname": case.__class__.__module__ + "." + case.__class__.__name__,
        "name": case._testMethodName,
    })
    if case.id() in failures:
        ET.SubElement(node, "failure", message="assertion failed").text = failures[case.id()]
    if case.id() in errors:
        ET.SubElement(node, "error", message="test error").text = errors[case.id()]
    if case.id() in skips:
        ET.SubElement(node, "skipped", message=skips[case.id()])

Path("reports").mkdir(exist_ok=True)
ET.ElementTree(root).write(
    "reports/junit.xml", encoding="utf-8", xml_declaration=True
)
sys.exit(0 if result.wasSuccessful() else 1)
```

The test runner emits real results and fails when tests fail. In production use a maintained JUnit reporter for larger suites.

## 6. Artifact packaging and verification

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
(out / "SHA256SUMS").write_text(
    f"{digest}  {archive.name}\n", encoding="utf-8"
)
(out / "manifest.json").write_text(
    json.dumps({
        "application": "demo-app",
        "commit": os.getenv("CI_COMMIT_SHA", "local"),
        "pipeline": os.getenv("CI_PIPELINE_ID", "local"),
        "sha256": digest,
    }, indent=2) + "\n",
    encoding="utf-8",
)
print(f"PASS: packaged archive SHA256={digest}")
```

`scripts/verify.py`:

```python
import hashlib
import json
from pathlib import Path

out = Path("dist")
archive = out / "demo-app.tar.gz"
manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
actual = hashlib.sha256(archive.read_bytes()).hexdigest()
assert actual == manifest["sha256"], "archive digest mismatch"
assert (out / "SHA256SUMS").read_text(encoding="utf-8").strip() == (
    f"{actual}  {archive.name}"
), "SHA256SUMS mismatch"
assert manifest["application"] == "demo-app"
print("PASS: archive and manifest verified")
```

A checksum detects changes relative to a trusted reference; it is **not** a digital signature or provenance attestation.

## 7. Reusable pipeline configuration

### `ci/common.yml`

```yaml
.python_base:
  image: python:3.12-slim
  tags:
    - ci-training
  variables:
    PYTHONDONTWRITEBYTECODE: "1"
  before_script:
    - python --version
```

**Runner setup:** Create or select an authorized nonprivileged training runner with tag `ci-training`. If your lab uses a different tag, update the template and child jobs consistently. Do not enable untagged execution on privileged release runners.

### `ci/validation.yml`

```yaml
lint:
  extends: .python_base
  stage: validate
  script:
    - python -m compileall -q src tests scripts
    - test -s README.md

policy:
  extends: .python_base
  stage: validate
  script:
    - python scripts/policy.py

security_sentinel:
  extends: .python_base
  stage: validate
  script:
    - python scripts/security_sentinel.py
```

### Parent: `.gitlab-ci.yml`

```yaml
include:
  - local: ci/common.yml
  - local: ci/validation.yml

workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages:
  - validate
  - test
  - downstream

unit_tests:
  extends: .python_base
  stage: test
  needs:
    - job: lint
      artifacts: false
  script:
    - python scripts/run_tests.py
  retry:
    max: 1
    when:
      - runner_system_failure
  timeout: 10m
  artifacts:
    when: always
    reports:
      junit: reports/junit.xml
    paths:
      - reports/junit.xml
    expire_in: 7 days

child_pipeline:
  stage: downstream
  needs:
    - job: lint
      artifacts: false
    - job: policy
      artifacts: false
    - job: security_sentinel
      artifacts: false
    - job: unit_tests
      artifacts: false
  trigger:
    include:
      - local: ci/child.yml
    strategy: mirror
```

`strategy: mirror` requires a GitLab version that supports it. On older supported instances, review `strategy: depend` semantics and document the behavioral differences rather than silently removing downstream status enforcement.

### Child: `ci/child.yml`

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "parent_pipeline"'
    - when: never

stages: [contract, package, verify]

child_contract:
  image: python:3.12-slim
  tags: [ci-training]
  stage: contract
  script:
    - python -c 'from src.service import normalize; assert normalize(" DEMO ") == "demo"; print("PASS: contract")'

child_package:
  image: python:3.12-slim
  tags: [ci-training]
  stage: package
  needs:
    - job: child_contract
      artifacts: false
  script:
    - python scripts/package.py
  artifacts:
    paths:
      - dist/demo-app.tar.gz
      - dist/SHA256SUMS
      - dist/manifest.json
    expire_in: 7 days

child_verify:
  image: python:3.12-slim
  tags: [ci-training]
  stage: verify
  needs:
    - job: child_package
      artifacts: true
  script:
    - python scripts/verify.py
```

The child pipeline creates and consumes its own artifacts. Parent artifacts are **not** automatically available to child jobs.

## 8. Runbook and README

`docs/RUNBOOK.md`:

```markdown
# CI Operations Runbook

## Triage
1. Record project, MR, commit, parent/child pipeline IDs and runner.
2. Determine whether failure is syntax, policy, test, runner or artifact related.
3. Inspect the first failed job and its required dependencies.
4. Check runner tags, protected status, concurrency and queue duration.
5. Verify child pipeline source rules and trigger status.
6. Preserve authorized nonsecret evidence.

## Recovery
- Fix deterministic code/policy failures in a reviewed MR.
- Retry only documented transient infrastructure failures.
- Re-enable required quality gates before merging.
- Quarantine compromised runners and rotate exposed credentials.
- Revert protected-branch changes using an approved MR.
- Validate both parent and child pipelines after recovery.

## Escalation
Escalate suspected secret exposure, runner compromise, missing security
gates, repeated runner outages and unauthorized deployment access.
```

`README.md`:

```markdown
# demo-app

Disposable GitLab CI runner and pipeline reliability capstone.
No production deployment or credentials.
```

## 9. Local validation

From the repository root:

```bash
python -m compileall -q src tests scripts
python scripts/policy.py
python scripts/security_sentinel.py
python scripts/run_tests.py
python scripts/package.py
python scripts/verify.py
```

Expected:

```text
PASS: repository structure policy
PASS: synthetic security sentinel
Ran 3 tests
OK
PASS: packaged archive SHA256=...
PASS: archive and manifest verified
```

For Windows PowerShell, the same Python commands work with `py` replacing `python` if configured. CI itself runs in a Linux container.

## 10. GitLab execution procedure

1. Create the disposable project and eligible `ci-training` runner.
2. Create a feature branch and add the files above.
3. Run GitLab CI Lint and inspect the merged configuration.
4. Open an MR and wait for the parent and child pipelines.
5. Confirm the parent includes `lint`, `policy`, `security_sentinel`, `unit_tests`, `child_pipeline`.
6. Confirm the child includes `child_contract`, `child_package`, `child_verify`.
7. Inspect the JUnit test report and downloadable child package artifacts.
8. Record runner ID, job durations and artifact SHA-256.

Example Git commands:

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch020-enterprise-capstone
# Create the files above using your editor
git add .gitlab-ci.yml README.md ci/ src/ tests/ scripts/ docs/
git commit -m "ci: complete enterprise runner and pipeline capstone"
git push -u origin feature/ch020-enterprise-capstone
```

**Expected clean result:** 5 parent jobs and 3 child jobs pass, with a real JUnit report and verified archive.

## 11. Failure-injection acceptance matrix

Run each experiment in a disposable feature branch. Restore the original configuration after each test.

| Test | Injection | Expected result | Recovery |
| --- | --- | --- | --- |
| A — Unit regression | Expect `normalize(" DEMO ")` to equal `"wrong"` | Unit job fails, JUnit failure, child not triggered | Restore assertion |
| B — Policy gate | Temporarily remove `docs/RUNBOOK.md` | Policy fails, child blocked | Restore file |
| C — Security sentinel | Add marker comment to `src/service.py` | Sentinel fails, child blocked | Remove marker |
| D — Child contract | Change child assertion to `"wrong"` | Child fails, parent trigger mirrors failure | Restore assertion |
| E — Artifact dependency | Set child verify `artifacts: false` | Verify fails with missing files | Restore `true` |
| F — Runner mismatch | Change one job tag to nonexistent training tag | Job pending | Restore tag |
| G — Include error | Point local include to missing file | CI Lint rejects config | Restore path |
| H — Gate bypass | Remove sentinel from child trigger `needs` | Child may start before sentinel finishes | Restore dependency; review governance |

**Important nuance for Test H:** The test demonstrates that the trigger no longer waits for the sentinel. It does not guarantee that the parent pipeline overall reports success after a required job fails. A centrally enforced, protected security policy is still needed to prevent contributor-authored YAML from bypassing release controls.

For Test F, do not pause shared runners or alter production tags. For all tests, retain only sanitized logs and artifacts.

## 12. Runner security and Kubernetes operations review

For a Docker runner, confirm `privileged = false`, no host Docker socket, bounded concurrency, restricted scope and no production credentials.

For a Kubernetes executor, confirm:

- Dedicated CI namespace and preferably dedicated node pool.
- Namespaced least-privilege manager RBAC.
- Separate manager and job pod service-account permissions.
- ResourceQuota and LimitRange, pod requests/limits and appropriate Pod Security admission.
- NetworkPolicy with tested CNI enforcement and explicit required egress.
- No access to production namespace Secrets or Deployments.
- Cloud workload identity narrowly scoped on EKS, AKS or GKE.
- Runner capacity and node autoscaling are independently monitored.

Do not claim a cluster is isolated solely because jobs run in a different namespace.

## 13. Runner capacity and reliability exercise

Capture at least five **actual** disposable pipeline runs if resources permit. Record each run's parent and child durations and runner queue times.

| Indicator | Formula or observation | SRE action |
| --- | --- | --- |
| Queue p95 | 95th percentile of job pending time | Investigate eligible runner capacity |
| Pipeline p95 | 95th percentile of end-to-end duration | Inspect DAG critical path |
| Runner utilization | Running jobs / configured effective capacity | Right-size and scale |
| Infrastructure failure rate | Runner/system failures / total jobs | Review runner health |
| Gate coverage | Required checks executed / expected checks | Investigate skipped checks |
| Artifact verification success | Verified archives / attempted verifications | Investigate integrity failures |
| CI recovery time | Detection to successful rerun | Improve runbook |

A sample of five runs is a **lab exercise**, not a statistically reliable production SLO baseline. Use a longer observation window and distinguish code failures from infrastructure availability before setting production objectives.

## 14. Incident scenario — runner saturation and downstream failures

**Scenario:** Multiple MRs queue, a runner is unavailable, and an unrelated child verification job fails.

Triage sequence:

1. Record the affected pipeline IDs and timestamps.
2. Check GitLab runner online state, tags, protection and project eligibility.
3. Inspect runner `concurrent`, per-runner `limit` and host/Kubernetes capacity.
4. Separate queue delay from execution failure.
5. Inspect child pipeline failure independently; do not retry deterministic checksum errors.
6. Restore runner capacity safely without granting new privileges.
7. Fix the child artifact issue via reviewed MR.
8. Verify the complete parent-child pipeline and record recovery time.

**Escalation:** If a runner may be compromised, pause/quarantine it, revoke credentials, preserve approved evidence and rebuild from a trusted image. Never debug by exposing masked variables.

## 15. Governance review

A production-ready CI service needs controls **outside** contributor-editable YAML:

- Protected default branch and required merge request approvals.
- CODEOWNERS for CI configuration and reusable templates.
- Trusted, version-pinned shared CI components.
- Mandatory security policies enforced independently where supported.
- Restricted runner scopes, protected refs and workload identities.
- Separation between MR validation and trusted release/promotion jobs.
- Approved GitOps promotion of immutable image digests.
- Audit logs, artifact access restrictions and retention policies.

**No automatic production deployment** is part of this capstone.

## 16. Operational troubleshooting reference

| Symptom | Probable cause | Investigation |
| --- | --- | --- |
| No pipeline | `workflow: rules` mismatch | Check source and CI Lint |
| Job pending | Runner tag/protection/capacity | Inspect eligible runners |
| Runner manager healthy, jobs fail | Executor, image, RBAC or network issue | Inspect runner and job events |
| Child not created | Missing include or child source rule | Validate child `parent_pipeline` workflow |
| Parent green while child red | Trigger status strategy | Verify supported `mirror` behavior |
| JUnit empty | XML/path/early script exit | Inspect generated report |
| Archive missing | `needs: artifacts` disabled or expiry | Inspect producer and consumer |
| Security job skipped | Rules or YAML bypass | Restore gate and enforce policy |
| Unexpected variable access | Protected/scoped variable mismatch | Review identity and variable sources |
| Slow pipelines | Runner queue, serial dependencies or capacity | Measure queue and critical path |

## 17. Evidence worksheet

```text
CHAPTER 020 — ENTERPRISE CI / RUNNER OPERATIONS CAPSTONE
Date:
GitLab version/tier:
Training project:
MR URL:
Commit SHA:
Parent pipeline ID:
Child pipeline ID:
Runner ID / executor / trust tier:
CI Lint result:
Parent required jobs:
Child required jobs:
JUnit report:
Archive SHA-256:
Runner privilege review:
Variable/secret review:
Protected branch / CODEOWNERS review:
Failure A unit regression:
Failure B policy:
Failure C security sentinel:
Failure D child contract:
Failure E artifact:
Failure F runner tag:
Failure G include:
Failure H gate bypass review:
Observed queue p95:
Observed pipeline p95:
Incident scenario outcome:
Recovery commit / pipeline:
Reviewer:
Unresolved risks, owners and due dates:
```

## 18. Final scoring and acceptance

| Category | Points |
| --- | ---: |
| Parent pipeline and reusable templates | 15 |
| Runner security and eligibility | 15 |
| Mandatory quality gates and JUnit | 15 |
| Child pipeline and status propagation | 15 |
| Artifact integrity | 10 |
| Failure injection and recovery | 15 |
| Observability and SRE runbook | 10 |
| Governance and evidence | 5 |
| **Total** | **100** |

**Pass:** At least 85/100 **and** all critical controls pass: required gates block downstream execution, JUnit reflects real failures, child failures propagate, artifact verification works, and no privileged production credentials are exposed. A critical-control failure is an automatic **Not Ready**, regardless of score.

## 19. Part 04 completion

You have completed the runner, pipeline composition, quality gate and failure recovery foundation required for enterprise CI/CD operations.

**Next: Chapter 021 — Secure Container Image Builds, Registries and Immutable Tags**, beginning Part 05 — Container Builds and Software Supply-Chain Security.
