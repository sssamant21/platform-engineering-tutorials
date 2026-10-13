# Chapter 014 — GitLab CI/CD Artifacts, Caching, Reports and Pipeline Data Flow

**Part 03 — GitLab CI/CD Fundamentals** | **Chapter 014 of 100**  
**Audience:** SREs, DevOps, platform engineers and CI/CD administrators  
**Lab:** Disposable private GitLab project, Python standard library, nonprivileged runner  
**Reference architecture:** GitLab CI validates and packages → trusted build publishes immutable image → approved GitOps promotion → Argo CD → Dev/Test/Staging/Prod namespaces on a shared Kubernetes cluster.

> **Safety:** Do not store passwords, tokens, kubeconfigs, signing keys or customer data in artifacts, caches, dotenv reports or job traces. Use synthetic training data only.

## 1. Learning objectives

You will learn to:

1. Distinguish artifacts, caches, job logs and GitLab reports.
2. Pass files safely between jobs using `needs: artifacts`.
3. Configure artifact paths, expiration, access and retention.
4. Cache nonsecret dependencies with appropriate keys and fallback strategies.
5. Publish test and coverage reports and understand their UI limitations.
6. Troubleshoot missing, stale, expired or unauthorized pipeline data.
7. Apply enterprise data-flow and supply-chain controls.

## 2. Pipeline data-flow architecture

```text
Commit / Merge Request
        |
        v
    validate job -----------+
        |                   |
        v                   v
    unit tests          dependency cache
        |               (performance only)
        v
    JUnit report --------------> GitLab MR / pipeline UI
        |
        v
    package job
        |
        +--> dist/demo-app.tar.gz
        +--> dist/SHA256SUMS
        +--> dist/manifest.json
        |
        v
    verify job -- explicit artifact download
        |
        v
    trusted build/release workflow (later chapters)
        |
        v
    immutable image digest + reviewed GitOps MR
```

**Key distinction:** Artifacts transfer or preserve outputs from a specific job/pipeline; caches accelerate reuse across jobs/pipelines and must be treated as untrusted performance hints.

## 3. Artifacts: scope and lifecycle

```yaml
package:
  stage: package
  script:
    - mkdir -p dist
    - echo "training-only" > dist/result.txt
  artifacts:
    name: "demo-app-$CI_COMMIT_SHORT_SHA"
    paths:
      - dist/result.txt
    expire_in: 7 days
    when: on_success
```

| Setting | Purpose | Operational consideration |
| --- | --- | --- |
| `paths` | Files uploaded from job workspace | Use narrow paths; avoid secret-bearing directories |
| `exclude` | Omit matching files | Pattern matching is not a substitute for data classification |
| `expire_in` | Retention period | Some artifacts may be kept longer by instance/project retention behavior |
| `when` | Upload on success/failure/always | Failure diagnostics may expose sensitive data |
| `name` | Human-readable artifact archive name | Include commit or pipeline identifier |
| `access` | Restrict download visibility where supported | Verify version-specific behavior and API access |
| `reports` | Structured GitLab report ingestion | Report formats and UI features differ |

Artifact retention and access settings are subject to GitLab instance configuration, project policy and feature availability. **Do not assume `expire_in` is an absolute deletion deadline** without checking keep-latest-successful-pipeline and retention policies.

## 4. Downloading artifacts with DAG dependencies

```yaml
package:
  stage: package
  script:
    - mkdir -p dist
    - printf 'hello\n' > dist/output.txt
  artifacts:
    paths:
      - dist/output.txt

verify:
  stage: verify
  needs:
    - job: package
      artifacts: true
  script:
    - test -s dist/output.txt
```

When a job uses `needs`, declare which upstream job's artifacts it requires. Avoid mixing `needs` and `dependencies` in the same job; use one consistent supported pattern.

If an upstream job may be omitted by `rules`, evaluate whether an optional dependency is appropriate. Never mark a required security or provenance producer optional simply to make pipeline creation succeed.

## 5. Caching: acceleration, not trust

```yaml
cache:
  key:
    files:
      - requirements.txt
  paths:
    - .cache/pip/
  policy: pull-push
```

Cache guidance:

- Cache dependency downloads, not secrets, source-of-truth deployment manifests or signed release evidence.
- Use lockfiles and stable keys to reduce stale dependency reuse.
- Understand runner storage: local cache may not be shared across runner hosts; distributed cache requires compatible object storage configuration.
- Restrict sharing between protected and unprotected branches and between trusted/untrusted runners.
- Treat cache content as untrusted; package integrity and dependency lock validation still apply.
- Use `policy: pull` for jobs that should consume but not mutate a shared cache, where appropriate.
- Do not rely on caches for required cross-job output transfer.

**Security risk:** Cache poisoning is possible when untrusted code can write cache data later consumed by trusted jobs. Separate trust domains and prefer immutable, verified dependencies.

## 6. GitLab report artifacts

### JUnit test report

```yaml
unit_tests:
  stage: test
  script:
    - python -m unittest discover -s tests -v
    - python scripts/create_junit.py
  artifacts:
    when: always
    reports:
      junit: reports/junit.xml
    paths:
      - reports/junit.xml
```

JUnit reports enable test visibility in the GitLab UI. The report file must conform to supported XML structure. A job's exit status still determines whether tests passed; **never generate a fake success report after a failed test**.

### Coverage

GitLab supports coverage extraction from job output and structured coverage report formats, subject to GitLab version and features. A percentage shown in a pipeline is not evidence that all important behaviors are tested. For production, use a real coverage tool and publish its genuine output.

### Dotenv

```yaml
build_metadata:
  stage: package
  script:
    - mkdir -p dist
    - echo "BUILD_CHANNEL=training" > dist/build.env
  artifacts:
    reports:
      dotenv: dist/build.env
```

Dotenv reports are intended for small, nonsecret runtime metadata. They have format, size and variable-count limits and can be downloaded or propagated depending on job permissions. **Never store credentials in dotenv artifacts.**

### Other reports

Depending on supported GitLab features, pipelines can ingest code quality, security, dependency, container, SAST and other report formats. Verify template compatibility, licensing and actual UI behavior. A report file existing on disk does not guarantee GitLab parsed or surfaced it.

## 7. Hands-on lab — artifact transfer, cache and JUnit report

### Prerequisites

- Disposable private GitLab project `https://gitlab.example.com/training/demo-app`.
- Nonprivileged runner with Python 3.12 container image support.
- Git CLI, optional local Python 3.12.
- No production credentials.

### Step A — Repository structure

```text
demo-app/
├── .gitlab-ci.yml
├── README.md
├── src/
│   ├── __init__.py
│   └── calculator.py
├── tests/
│   └── test_calculator.py
└── scripts/
    ├── run_tests.py
    └── package.py
```

Create empty `src/__init__.py`.

`src/calculator.py`:

```python
def add(a: int, b: int) -> int:
    return a + b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b
```

`tests/test_calculator.py`:

```python
import unittest
from src.calculator import add, divide


class CalculatorTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_divide(self):
        self.assertEqual(divide(8, 2), 4.0)

    def test_zero_division(self):
        with self.assertRaises(ZeroDivisionError):
            divide(1, 0)


if __name__ == "__main__":
    unittest.main()
```

`README.md`:

```markdown
# demo-app

Disposable GitLab artifacts, caching and reports lab.
```

### Step B — Test runner that writes genuine JUnit XML

`scripts/run_tests.py`:

```python
import sys
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


class RecordingResult(unittest.TextTestResult):
    def startTest(self, test):
        self._start = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        elapsed = time.perf_counter() - self._start
        if not hasattr(self, "durations"):
            self.durations = {}
        self.durations[test.id()] = elapsed
        super().stopTest(test)


suite = unittest.defaultTestLoader.discover("tests")
runner = unittest.TextTestRunner(resultclass=RecordingResult, verbosity=2)
result = runner.run(suite)

root = ET.Element(
    "testsuite",
    name="demo-app",
    tests=str(result.testsRun),
    failures=str(len(result.failures)),
    errors=str(len(result.errors)),
    skipped=str(len(result.skipped)),
)
failures = {case.id(): details for case, details in result.failures}
errors = {case.id(): details for case, details in result.errors}
skipped = {case.id(): reason for case, reason in result.skipped}

for test in list(suite):
    # This lab uses a single-level discovered suite; recurse for nested suites.
    def visit(item):
        if isinstance(item, unittest.TestSuite):
            for child in item:
                yield from visit(child)
        else:
            yield item

    for case in visit(test):
        case_id = case.id()
        item = ET.SubElement(
            root, "testcase",
            classname=case.__class__.__module__ + "." + case.__class__.__name__,
            name=case._testMethodName,
            time=f"{getattr(result, 'durations', {}).get(case_id, 0.0):.4f}",
        )
        if case_id in failures:
            ET.SubElement(item, "failure", message="assertion failure").text = failures[case_id]
        if case_id in errors:
            ET.SubElement(item, "error", message="test error").text = errors[case_id]
        if case_id in skipped:
            ET.SubElement(item, "skipped", message=skipped[case_id])

Path("reports").mkdir(exist_ok=True)
ET.ElementTree(root).write("reports/junit.xml", encoding="utf-8", xml_declaration=True)
sys.exit(0 if result.wasSuccessful() else 1)
```

**Validation note:** This script writes results from real `unittest` execution. For larger production suites, use a maintained JUnit-reporting test runner rather than custom XML generation.

### Step C — Packaging and manifest

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
(out / "manifest.json").write_text(
    json.dumps({
        "name": "demo-app",
        "commit": os.environ.get("CI_COMMIT_SHA", "local"),
        "pipeline": os.environ.get("CI_PIPELINE_ID", "local"),
        "sha256": digest
    }, indent=2) + "\n",
    encoding="utf-8"
)
print(f"Created training archive sha256={digest}")
```

### Step D — Complete pipeline

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
    - cd dist
    - sha256sum -c SHA256SUMS
    - python -c 'import json; from pathlib import Path; m=json.loads(Path("manifest.json").read_text()); assert m["name"]=="demo-app"; print("PASS: manifest")'
```

This pipeline uses only standard-library Python, so it deliberately does **not** require dependency caching. In Step H, you will add a safe cache experiment separately; a cache with no reusable inputs is not a useful optimization.

### Step E — Run locally

```bash
python -m compileall -q src tests scripts
python scripts/run_tests.py
python scripts/package.py
cd dist
sha256sum -c SHA256SUMS
```

On Windows PowerShell, validate the archive digest without `sha256sum`:

```powershell
$m = Get-Content .\manifest.json | ConvertFrom-Json
$actual = (Get-FileHash .\demo-app.tar.gz -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $m.sha256) { throw "Checksum mismatch" }
"PASS: checksum verified"
```

### Step F — Create MR and inspect reports

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch014-artifacts
# Create the files above using your editor
git add .gitlab-ci.yml README.md src/ tests/ scripts/
git commit -m "ci: add artifact transfer and JUnit reporting lab"
git push -u origin feature/ch014-artifacts
```

Open an MR and validate YAML with GitLab CI Lint.

Expected:

```text
lint         passed
unit_tests   passed (3 tests)
package      passed
verify       passed
```

Inspect the test report and download `dist/demo-app.tar.gz`, `dist/SHA256SUMS`, `dist/manifest.json` and `reports/junit.xml`. Confirm the report reflects actual executed tests.

### Step G — Negative test: genuine failing test

Change the expected `test_add` value from `5` to `6`, commit and push.

Expected:
- `unit_tests` fails.
- The JUnit artifact still uploads because `when: always` is set.
- The report includes a failure, not a fabricated success.
- `package` and `verify` do not run.

Restore `5`, push and confirm green.

### Step H — Safe cache experiment

Add a standalone job that caches **only synthetic, reproducible data**:

```yaml
cache_demo:
  stage: validate
  cache:
    key: "demo-cache-v1"
    paths:
      - .cache/demo/
    policy: pull-push
  script:
    - mkdir -p .cache/demo
    - python -c 'from pathlib import Path; p=Path(".cache/demo/marker.txt"); print("Cache present before write:", p.exists()); p.write_text("synthetic-cache-data\n")'
```

Run twice and inspect job logs for cache restoration/upload. Cache availability depends on runner storage, branch protection partitioning and configuration; the second run may miss. **Never make a required build result depend on a cache hit.**

For a production dependency cache, use dependency lockfile keys, separate protected/unprotected cache scopes and verify downloaded packages independently.

### Step I — Negative test: missing producer artifact

In a separate disposable MR, temporarily change `verify.needs` to `artifacts: false` while keeping its checksum command.

Expected: `verify` cannot find the required `dist` files and fails. Restore `artifacts: true` and confirm recovery.

### Step J — Cleanup

Remove the temporary cache demo job if not needed, remove failure-injection edits, and merge or close the training MR. Delete disposable branches. Do not delete audit evidence under retention or modify shared runners.

## 8. Enterprise data governance

| Data type | Appropriate destination | Avoid |
| --- | --- | --- |
| Unit test results | JUnit report artifacts | Secrets or customer records |
| Source package for lab | Short-lived artifact | Treating archive as signed release |
| Production container image | Controlled registry with digest | Mutable tag-only promotion |
| SBOM/provenance | Governed artifact/registry system | Unreviewed, editable evidence |
| Dependency downloads | Isolated cache | Sharing across untrusted/trusted runners |
| Runtime credentials | Secret manager/workload identity | Artifacts, caches, dotenv and logs |
| Environment desired state | Reviewed GitOps repository | CI-local files as source of truth |

For enterprise use, classify artifacts, enforce access, review retention, and audit downloads where supported. Pipeline artifacts alone do not establish tamper-proof supply-chain provenance.

## 9. Troubleshooting runbook

| Symptom | Likely cause | Safe action |
| --- | --- | --- |
| Artifact missing | Wrong path, `needs` config or expiry | Inspect producer logs, paths and download rules |
| JUnit UI empty | Malformed XML, incorrect path, unsupported report | Validate actual XML and GitLab parser |
| Failed tests appear successful | Test runner swallowed nonzero exit | Propagate genuine test result |
| Cache always misses | Runner storage, key changes or branch partition | Inspect cache backend and key |
| Cache contaminated | Untrusted writers share trusted cache | Separate trust domains and invalidate |
| Artifacts kept too long | Retention/keep-latest policy | Review instance/project settings |
| Download forbidden | Permissions or artifact access policy | Check authorized identity and project |
| Dotenv unexpectedly overrides value | Variable precedence | Remove secret data and inspect effective sources |
| Report includes sensitive data | Unsafe test output | Contain, revoke/rotate if necessary, investigate |

## 10. Production acceptance checklist

- [ ] Artifact producer/consumer dependencies explicitly configured.
- [ ] Job artifacts contain only classified nonsecret outputs.
- [ ] Artifact expiry and actual retention behavior verified.
- [ ] JUnit report reflects real passing and failing tests.
- [ ] Failed tests block packaging.
- [ ] Cache used only as an optimization, not a correctness dependency.
- [ ] Protected and unprotected cache trust boundaries reviewed.
- [ ] Dotenv artifacts do not contain credentials.
- [ ] Runner, artifact and report permissions documented.
- [ ] Release image digests and GitOps approvals remain separate from training archives.
- [ ] Actual MR/pipeline IDs, report status and artifact checksums recorded.

## 11. Knowledge checks

1. Why are artifacts appropriate for passing a package between jobs, but caches are not?
2. Why should JUnit reports use `when: always`?
3. What does `needs: artifacts: true` accomplish?
4. Why can an artifact survive longer than its configured `expire_in`?
5. How can cache poisoning cross CI trust boundaries?
6. Why should dotenv reports never contain secrets?
7. Why is a checksum not the same as a cryptographic signature?

## 12. Completion criteria

**Pass:** You run a four-job MR pipeline, produce a genuine JUnit report, verify an archive via explicit artifact transfer, observe a failed test correctly reported, and demonstrate that caching is optional.

**Next: Chapter 015 — GitLab CI/CD Fundamentals and Pipeline Reliability Capstone**, completing Part 03.
