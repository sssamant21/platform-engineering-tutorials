# Chapter 018 — GitLab CI/CD Reusable Pipelines, Includes, Templates and Child Pipelines

**Part 04 — Pipeline Design, Testing and Artifacts** | **Chapter 018 / 100**  
**Audience:** SRE, infrastructure, platform and DevSecOps engineers  
**Lab:** Disposable private GitLab project, nonprivileged runner, Python standard library  
**Enterprise workflow:** GitLab CI builds and validates; approved GitOps changes promote immutable image digests through Dev → Test → Staging → Prod namespaces in a shared Kubernetes cluster.

> **Safety:** All examples use generic training names. No real credentials, deployment permissions, internal project identifiers or production resources are required. Treat reusable CI configuration as executable code with the same review requirements as application code.

## 1. Learning objectives

After completing this chapter, you can:

1. Explain `include:local`, `include:project`, `include:remote`, and `include:template`.
2. Use `extends`, hidden jobs, YAML anchors and `!reference` appropriately.
3. Design reusable CI components without hiding mandatory quality gates.
4. Build a parent-child pipeline using `trigger: include`.
5. Distinguish parent-child pipelines from multi-project pipelines.
6. Understand include resolution, variable inheritance, artifact passing and downstream status propagation.
7. Troubleshoot missing includes, duplicate jobs, invalid DAG dependencies and child-pipeline failures.
8. Apply version pinning, CODEOWNERS, protected refs and governance to shared templates.

## 2. Architecture

```text
demo-app/.gitlab-ci.yml
       |
       +--> include:local ci/common.yml
       |       |
       |       +--> .python_base (hidden template)
       |       +--> .validation_rules (shared rules)
       |
       +--> include:local ci/validation.yml
       |       |
       |       +--> lint
       |       +--> policy
       |
       +--> parent pipeline
               |
               +--> unit_tests
               +--> trigger child pipeline
                        |
                        v
                  ci/child.yml
                        |
                        +--> child_contract
                        +--> child_package
                        +--> child_verify
```

**Key rule:** A child pipeline has its own jobs, status and configuration. The parent trigger job can mirror downstream status, but ordinary parent job artifacts are not automatically available inside child jobs.

## 3. Reuse mechanisms compared

| Mechanism | Best use | Risks |
| --- | --- | --- |
| `include:local` | Templates in same repository/ref | File path or branch drift |
| `include:project` | Central CI template repository | Cross-project permissions, ref mutability |
| `include:remote` | Externally hosted YAML | Supply-chain trust and availability |
| `include:template` | GitLab-provided templates | Version-dependent behavior |
| `extends` | Job inheritance and overrides | Merge behavior not always intuitive |
| YAML anchors | Reuse within a YAML file | Anchors do not cross file boundaries |
| `!reference` | Reuse selected GitLab config sections | Version/keyword limitations |
| Child pipeline | Split complex workflows into downstream pipeline | Status, variables, artifact transfer complexity |
| Multi-project pipeline | Orchestrate another GitLab project | Separate permissions and provenance |

### Includes are evaluated before execution

GitLab resolves included configuration when a pipeline is created. Changing an included template later does not retroactively rewrite an existing pipeline's configuration. A newly created pipeline may resolve a newer template if the include uses a mutable branch ref.

**Production recommendation:** Pin shared `include:project` content to a protected, reviewed tag or commit SHA where feasible. Govern changes to shared templates through CODEOWNERS and approvals.

## 4. Merge semantics and template inheritance

A hidden job begins with a dot:

```yaml
.python_base:
  image: python:3.12-slim
  before_script:
    - python --version

lint:
  extends: .python_base
  script:
    - python -m compileall -q src tests scripts
```

GitLab `extends` uses reverse deep merging for map keys; arrays such as `script` and `rules` are generally replaced rather than concatenated. Test the final merged YAML using CI Lint rather than assuming inheritance behavior.

### Shared rules with `!reference`

```yaml
.validation_rules:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

lint:
  rules:
    - !reference [.validation_rules, rules]
  script:
    - echo "lint"
```

`!reference` is a GitLab CI configuration feature, not standard YAML. For broad portability, prefer a simple `extends` hierarchy or directly declared rules when the abstraction is not justified.

## 5. Parent-child and multi-project pipelines

A parent-child pipeline runs in the **same project**, usually against the same commit SHA, but has a separate pipeline identity. A multi-project downstream pipeline runs in another project and may use a different ref, permissions and source code.

```yaml
child_pipeline:
  stage: downstream
  trigger:
    include:
      - local: ci/child.yml
    strategy: mirror
```

`strategy: mirror` makes the trigger job reflect the downstream pipeline's status on supported GitLab versions. Older versions may use `strategy: depend` with different status behavior; check your deployed version.

**Important:** A child pipeline must not be accidentally excluded by workflow rules that only allow merge request or push sources. Child jobs run with `CI_PIPELINE_SOURCE=parent_pipeline`; account for that in child `workflow: rules`.

## 6. Hands-on lab — modular parent and child pipelines

### Prerequisites

- Disposable private project: `https://gitlab.example.com/training/demo-app`.
- GitLab Runner with `python:3.12-slim` support.
- Permission to create MRs and run downstream pipelines.
- No production variables or deployment credentials.
- GitLab version supporting parent-child pipelines and the chosen trigger strategy.

### Step A — Repository layout

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
│   └── calculator.py
├── tests/
│   └── test_calculator.py
└── scripts/
    ├── policy.py
    ├── package.py
    └── verify.py
```

Create an empty `src/__init__.py`.

`src/calculator.py`:

```python
def add(a: int, b: int) -> int:
    return a + b


def divide(a: int, b: int) -> float:
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

Disposable GitLab CI reusable templates and child pipeline lab.
```

### Step B — Reusable configuration

`ci/common.yml`:

```yaml
.python_base:
  image: python:3.12-slim
  variables:
    PYTHONDONTWRITEBYTECODE: "1"
  before_script:
    - python --version
```

`ci/validation.yml`:

```yaml
lint:
  extends: .python_base
  stage: validate
  script:
    - python -m compileall -q src tests scripts

policy:
  extends: .python_base
  stage: validate
  script:
    - python scripts/policy.py
```

`scripts/policy.py`:

```python
from pathlib import Path

required = [
    Path("README.md"),
    Path("ci/common.yml"),
    Path("ci/validation.yml"),
    Path("ci/child.yml"),
]
for path in required:
    if not path.is_file():
        raise SystemExit(f"FAIL: missing {path}")

for folder in ("src", "tests", "scripts"):
    for path in Path(folder).rglob("*.py"):
        if "DEMO_FORBIDDEN_MARKER_123" in path.read_text(encoding="utf-8"):
            raise SystemExit(f"FAIL: synthetic policy violation in {path}")
print("PASS: required files and synthetic policy")
```

### Step C — Packaging and verification scripts

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
    "commit": os.environ.get("CI_COMMIT_SHA", "local"),
    "sha256": digest,
}, indent=2) + "\n", encoding="utf-8")
print("PASS: package created")
```

`scripts/verify.py`:

```python
import hashlib
import json
from pathlib import Path

out = Path("dist")
manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
archive = out / "demo-app.tar.gz"
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest == manifest["sha256"], "archive checksum mismatch"
assert (out / "SHA256SUMS").read_text(encoding="utf-8").strip() == (
    f"{digest}  {archive.name}"
)
assert manifest["application"] == "demo-app"
print("PASS: artifact integrity verified")
```

### Step D — Parent pipeline

`.gitlab-ci.yml`:

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
    - python -m unittest discover -s tests -v

child_pipeline:
  stage: downstream
  needs:
    - job: lint
      artifacts: false
    - job: policy
      artifacts: false
    - job: unit_tests
      artifacts: false
  trigger:
    include:
      - local: ci/child.yml
    strategy: mirror
```

**Gate logic:** The child pipeline is not created until `lint`, `policy` and `unit_tests` all succeed. If any mandatory check fails, the trigger job cannot proceed.

### Step E — Child pipeline

`ci/child.yml`:

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "parent_pipeline"'
    - when: never

stages:
  - contract
  - package
  - verify

child_contract:
  image: python:3.12-slim
  stage: contract
  script:
    - python -c 'from src.calculator import add; assert add(2, 3) == 5; print("PASS: child contract")'

child_package:
  image: python:3.12-slim
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
  stage: verify
  needs:
    - job: child_package
      artifacts: true
  script:
    - python scripts/verify.py
```

**Data flow:** The child creates and consumes **its own** package artifacts. This avoids assuming parent artifacts automatically transfer across pipeline boundaries.

### Step F — Local validation

```bash
python -m compileall -q src tests scripts
python scripts/policy.py
python -m unittest discover -s tests -v
python scripts/package.py
python scripts/verify.py
```

Expected:

```text
PASS: required files and synthetic policy
Ran 3 tests
OK
PASS: package created
PASS: artifact integrity verified
```

### Step G — GitLab MR validation

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch018-reusable-pipelines
# Add files above using your editor
git add .gitlab-ci.yml README.md ci/ src/ tests/ scripts/
git commit -m "ci: modularize validation and child pipeline"
git push -u origin feature/ch018-reusable-pipelines
```

Open an MR and run GitLab CI Lint with the merged configuration view.

Expected parent jobs:

```text
lint             passed
policy           passed
unit_tests       passed
child_pipeline   passed
```

Expected child jobs:

```text
child_contract   passed
child_package    passed
child_verify     passed
```

Record parent and child pipeline IDs separately. Confirm that the trigger job reflects the downstream result.

## 7. Negative tests and recovery

### Test 1 — Missing local include

Temporarily change `ci/validation.yml` to `ci/missing.yml` in the parent `include`. Run CI Lint.

Expected: pipeline configuration fails to resolve the missing file. Restore the correct path.

### Test 2 — Parent policy failure

Insert a harmless `DEMO_FORBIDDEN_MARKER_123` comment into `src/calculator.py`, commit and push.

Expected: `policy` fails; `child_pipeline` is not triggered. Remove marker and confirm recovery.

### Test 3 — Child failure propagation

Temporarily change the child contract assertion to `assert add(2, 3) == 6`, commit and push.

Expected: `child_contract` fails, child package/verify do not execute, and the parent `child_pipeline` trigger job reflects failure when `strategy: mirror` is supported. Restore the assertion.

### Test 4 — Missing child artifact

Temporarily change `child_verify.needs` to `artifacts: false`.

Expected: child verification fails because the package files were not downloaded. Restore `artifacts: true`.

### Test 5 — Child workflow exclusion

Temporarily remove the `parent_pipeline` source rule from child `workflow` and replace it with a rule allowing only `merge_request_event`.

Expected: the downstream child cannot be created as intended. Restore the parent-pipeline rule. Validate against the installed GitLab version; exact error wording varies.

## 8. Shared templates in a central repository

For an approved, protected central CI library:

```yaml
include:
  - project: 'training/platform-ci-templates'
    ref: 'v1.2.0'
    file: '/python/validation.yml'
```

This is illustrative: the project must exist and be accessible to the pipeline's identity. In higher-assurance workflows, pin to a reviewed immutable commit SHA. Protect tags against reassignment and require CODEOWNERS approvals on shared template changes.

### Governance requirements

- Review shared templates as privileged infrastructure code.
- Define version compatibility and deprecation policies.
- Pin refs and maintain release notes.
- Test templates in disposable projects before broad rollout.
- Restrict who can modify included repositories.
- Inspect merged pipeline YAML to detect overridden gates.
- Avoid unaudited remote includes or mutable external endpoints.

## 9. Advanced pipeline design considerations

### Variable inheritance

Parent and child pipelines have different variable contexts. GitLab forwards certain predefined and YAML variables by default depending on trigger settings, while pipeline variables and other sources may require explicit forwarding. Review `trigger: forward`, `inherit: variables`, and project policy before relying on inherited values. **Never forward privileged secrets to untrusted downstream jobs.**

### Artifact passing across pipeline boundaries

Passing artifacts from parent to child requires supported cross-pipeline mechanisms, appropriate job identifiers and access permissions; it is not the same as same-pipeline `needs: artifacts`. Prefer producing artifacts within the child when possible, as in this lab.

### Dynamic child pipelines

GitLab supports generating child configuration as an artifact in supported versions. This is powerful but high-risk: untrusted code that generates CI configuration can introduce new jobs or permissions. Restrict generation inputs and review trust boundaries.

### Pipeline complexity

Too many child pipelines create debugging and observability overhead. Split by meaningful ownership, trust or lifecycle boundaries—not merely to reduce YAML line count.

## 10. Troubleshooting runbook

| Symptom | Likely cause | Safe response |
| --- | --- | --- |
| Include not found | Wrong path/ref/permissions | Validate path and protected ref |
| Unexpected merged job | Deep-merge or override behavior | Inspect merged CI configuration |
| Parent passes but child fails | Trigger strategy or child rules | Review downstream graph/status |
| Child not created | `workflow` excludes `parent_pipeline` | Correct source rules |
| Artifact missing in child | Assumed implicit parent transfer | Use explicit supported transfer or rebuild |
| Job skipped unexpectedly | Rules differ across include files | Trace effective rules |
| Template changes break many projects | Mutable ref or unreviewed shared change | Pin/ref rollback and govern releases |
| Secret leaked downstream | Unsafe variable forwarding | Revoke, rotate and restrict forwarding |
| Child job pending | Runner tags/protection/capacity | Inspect runner eligibility and queue |
| Excessive pipeline duration | Unnecessary stage barriers or child overhead | Measure critical path and optimize |

## 11. Production acceptance checklist

- [ ] Parent and child pipeline sources and statuses understood.
- [ ] Shared templates are reviewed and version-pinned.
- [ ] CI Lint validates merged configuration.
- [ ] Parent mandatory gates block child creation on failure.
- [ ] Child failure propagates to parent trigger status.
- [ ] Child artifact transfer is explicit and verified.
- [ ] Variables are not forwarded across trust boundaries without approval.
- [ ] Runner permissions remain minimal and isolated.
- [ ] No production deployment occurs automatically from an MR pipeline.
- [ ] GitOps promotion remains reviewed and digest-based.
- [ ] Actual pipeline IDs, test evidence and failure recovery recorded.

## 12. Evidence template

```text
CHAPTER 018 — REUSABLE PIPELINES LAB
GitLab version/tier:
Project:
MR URL:
Parent pipeline ID:
Child pipeline ID:
Runner identity:
Merged CI Lint:
Parent mandatory gates:
Child contract:
Child package:
Child verify:
Missing include negative test:
Parent policy failure negative test:
Child failure propagation:
Missing artifact negative test:
Child workflow exclusion:
Shared template pinning review:
Secret forwarding review:
Reviewer:
Open issues and owners:
```

## 13. Knowledge checks

1. Why should shared includes be pinned to protected refs?
2. What is the difference between `extends` and YAML anchors?
3. Why does a child pipeline need to allow the `parent_pipeline` source?
4. What does `strategy: mirror` change?
5. Why are parent artifacts not automatically available in child jobs?
6. What are the security risks of dynamic child configuration?
7. How can a template override accidentally bypass mandatory security gates?

## 14. Completion criteria

**Pass:** A reusable, modular parent pipeline runs all mandatory gates, triggers a child pipeline, verifies child-produced artifacts and correctly reports downstream failures. Negative tests and security reviews are documented.

**Next: Chapter 019 — GitLab CI/CD Pipeline Testing, Quality Gates, Security Scanning and Failure Recovery.**
