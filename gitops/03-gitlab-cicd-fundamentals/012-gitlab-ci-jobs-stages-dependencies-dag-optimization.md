# Chapter 012 — GitLab CI/CD Jobs, Stages, Dependencies and DAG Optimization

**Part 03 — GitLab CI/CD Fundamentals** | **Chapter 012 / 100**  
**Audience:** SREs, infrastructure engineers, platform engineers, GitLab administrators  
**Hands-on:** Nonprivileged GitLab Runner, Python standard library, disposable private GitLab project  
**Architecture:** GitLab CI builds and validates; a separate approved GitOps workflow promotes immutable image digests to Dev, Test, Staging and Prod namespaces in a shared Kubernetes cluster.

## 1. Outcomes

You will be able to:

1. Explain the job lifecycle and how stages differ from a directed acyclic graph (DAG).
2. Configure `needs`, optional dependencies, artifacts and failure behavior correctly.
3. Reduce critical-path latency without bypassing security or quality gates.
4. Understand `parallel`, resource contention, `interruptible`, `resource_group` and runner capacity.
5. Diagnose blocked, pending, skipped and failed jobs.
6. Benchmark a sequential pipeline against a safe DAG and document acceptance evidence.

## 2. Execution model

```text
GitLab pipeline created
         |
         v
Job rules evaluated
         |
         v
Dependency graph constructed
         |
         +--> lint ----------+
         |                   |
         +--> security ------+--> package --> verify
         |                   |
         +--> unit tests ----+
         |
         +--> docs check (independent)
```

With stage barriers, all jobs in an earlier stage must finish before the next stage begins. With `needs`, jobs may begin as soon as **their own declared dependencies** succeed, even if unrelated earlier-stage jobs are still running.

**Security principle:** A DAG is an optimization, not an authorization mechanism. A packaging job must explicitly depend on every required quality/security gate; otherwise it may begin too early.

## 3. Jobs and runner lifecycle

A GitLab job has a name, optional `stage`, execution environment, commands, conditions and dependencies.

```yaml
unit_tests:
  stage: test
  image: python:3.12-slim
  script:
    - python -m unittest discover -s tests -v
  timeout: 10m
  retry:
    max: 1
    when:
      - runner_system_failure
```

Operational considerations:

- **Pending:** Runner unavailable, incompatible tags, runner protection, capacity or project scope.
- **Running:** Executor acquired; script executes in its job context.
- **Success/failure:** Shell exit status normally determines result.
- **Canceled/interrupted:** Can occur due to manual cancellation or newer pipelines.
- **Retry:** Restrict automatic retries to transient infrastructure failures. Do not hide deterministic test failures with blanket retries.
- **Timeout:** Bound runaway jobs and investigate consistently slow work.

Use pinned images and controlled dependencies in trusted production pipelines. The moving `python:3.12-slim` tag here is for training.

## 4. Stage barriers versus DAG

### Stage-based pipeline

```yaml
stages: [validate, test, package]

lint:
  stage: validate
  script: ["echo lint"]

docs:
  stage: validate
  script: ["echo docs"]

unit_tests:
  stage: test
  script: ["echo tests"]

package:
  stage: package
  script: ["echo package"]
```

Here `unit_tests` waits for both `lint` and `docs` because they share the previous stage.

### DAG optimization

```yaml
unit_tests:
  stage: test
  needs:
    - lint
  script: ["echo tests"]
```

Now `unit_tests` can begin after `lint`, without waiting for unrelated `docs`. This is appropriate only if `docs` is not a required gate for tests.

### Critical-path calculation

For a dependency chain, the theoretical minimum completion time is the longest path through the DAG, **before** runner queueing and overhead.

Example durations:

| Job | Duration | Dependency |
| --- | ---: | --- |
| lint | 1 min | none |
| security | 4 min | none |
| unit tests | 3 min | lint |
| docs | 6 min | none |
| package | 2 min | lint, security, unit tests |
| verify | 1 min | package |

The release candidate can finish after approximately **7 minutes** (lint 1 + tests 3 + package 2 + verify 1), assuming enough runners and no overhead; the unrelated docs check completes at 6 minutes. If docs is a mandatory release gate, packaging must also depend on it, increasing the release candidate's critical path to **9 minutes** (docs 6 + package 2 + verify 1).

**Do not claim performance improvements without measuring actual runner queue time, cache behavior and job durations.**

## 5. Correct dependency semantics

### Required dependencies

```yaml
package:
  stage: package
  needs:
    - job: lint
    - job: unit_tests
    - job: security_check
  script:
    - echo "All required gates passed"
```

If a required job fails, packaging does not run.

### Optional dependencies

```yaml
package:
  stage: package
  needs:
    - job: lint
    - job: optional_docs_check
      optional: true
  script:
    - echo "Packaging after mandatory checks"
```

Use `optional: true` **only** when the referenced job may be absent from the pipeline because of `rules` or `only/except`. It does not turn a mandatory security check into an optional one.

### Artifact dependencies

```yaml
package:
  stage: package
  artifacts:
    paths: [dist/demo-app.tar.gz]

verify:
  stage: verify
  needs:
    - job: package
      artifacts: true
  script:
    - test -s dist/demo-app.tar.gz
```

Jobs using `needs` should declare precisely which producer artifacts they need. Do not rely on implicit downloads of every earlier-stage artifact.

### Special `needs: []`

A job with `needs: []` is eligible to start immediately when the pipeline is created, independent of stage barriers. This is useful for standalone checks, but dangerous for release jobs if used accidentally.

## 6. Parallelism, concurrency and resource protection

### Parallel jobs

```yaml
smoke_test:
  stage: test
  parallel: 3
  script:
    - echo "Shard $CI_NODE_INDEX of $CI_NODE_TOTAL"
```

This creates three job instances. **It does not automatically split tests.** Implement deterministic sharding in the test runner, or all three jobs will execute the same tests.

### Resource groups

```yaml
staging_change:
  stage: deploy
  resource_group: training-staging
  script:
    - echo "Serialized non-production training change"
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
```

A resource group serializes jobs sharing the same resource name across pipelines. It is **not** an approval mechanism and does not replace GitOps change review. This sample performs no deployment.

### Interruptible work

`interruptible: true` is appropriate for disposable MR lint/test work, but avoid blindly applying it to publishing, migrations, signing or state-changing jobs. Understand project auto-cancel behavior before enabling interruption.

### Runner capacity

Monitor pending job count, queue age, CPU, memory, executor concurrency and per-project quotas. Parallelizing ten jobs on a two-runner fleet may **increase** queueing and total cost.

## 7. Hands-on lab — optimize a real pipeline

### Prerequisites

- Disposable private project `https://gitlab.example.com/training/demo-app`.
- GitLab Runner with a Docker/container executor, no privileged socket or cloud credentials.
- Git, Python 3.12 (local testing optional).
- Merge-request pipelines enabled and protected default branch.

### Step A — Create the files

```text
demo-app/
├── .gitlab-ci.yml
├── README.md
├── src/
│   ├── __init__.py
│   └── math_service.py
├── tests/
│   └── test_math_service.py
└── scripts/
    ├── check_security.py
    └── package.py
```

Create an empty `src/__init__.py`.

`src/math_service.py`:

```python
def total(values: list[int]) -> int:
    return sum(values)


def average(values: list[int]) -> float:
    if not values:
        raise ValueError("empty values")
    return sum(values) / len(values)
```

`tests/test_math_service.py`:

```python
import unittest
from src.math_service import total, average


class MathServiceTests(unittest.TestCase):
    def test_total(self):
        self.assertEqual(total([2, 3, 5]), 10)

    def test_average(self):
        self.assertEqual(average([2, 4]), 3.0)

    def test_empty_average(self):
        with self.assertRaises(ValueError):
            average([])


if __name__ == "__main__":
    unittest.main()
```

`scripts/check_security.py`:

```python
from pathlib import Path

# Harmless lab sentinel, not a production secrets scanner.
for path in list(Path("src").rglob("*.py")) + list(Path("tests").rglob("*.py")):
    if "DEMO_FORBIDDEN_MARKER_123" in path.read_text(encoding="utf-8"):
        raise SystemExit(f"FAIL: synthetic forbidden marker in {path}")
print("PASS: synthetic security policy")
```

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
(out / "manifest.json").write_text(
    json.dumps({
        "application": "demo-app",
        "commit": os.environ.get("CI_COMMIT_SHA", "local"),
        "pipeline": os.environ.get("CI_PIPELINE_ID", "local"),
        "sha256": sha
    }, indent=2) + "\n", encoding="utf-8"
)
print(f"Packaged {archive} with SHA256 {sha}")
```

### Step B — Create the DAG pipeline

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

security_check:
  stage: validate
  script:
    - python scripts/check_security.py

docs_check:
  stage: validate
  script:
    - test -s README.md

unit_tests:
  stage: test
  needs:
    - job: lint
      artifacts: false
  script:
    - python -m unittest discover -s tests -v

package:
  stage: package
  needs:
    - job: lint
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
    - cd dist
    - sha256sum -c SHA256SUMS
    - python -c 'import json; from pathlib import Path; m=json.loads(Path("manifest.json").read_text()); assert m["application"]=="demo-app"; print("PASS: release manifest")'
```

**Gate policy:** `lint`, `security_check`, and `unit_tests` must pass before `package`. `docs_check` is intentionally an independent nonrelease job. If documentation review is mandatory for your release, add it to `package.needs`.

### Step C — Run locally

```bash
python -m compileall -q src tests scripts
python scripts/check_security.py
python -m unittest discover -s tests -v
python scripts/package.py
cd dist
sha256sum -c SHA256SUMS
```

PowerShell checksum equivalent from the `dist` directory:

```powershell
$m = Get-Content .\manifest.json | ConvertFrom-Json
$actual = (Get-FileHash .\demo-app.tar.gz -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $m.sha256) { throw "Checksum mismatch" }
"PASS: checksum verified"
```

The checksum demonstrates integrity within this lab; it is not a signature or trusted provenance.

### Step D — Open a merge request

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch012-dag-optimization
# Create the files above using your editor
git add .gitlab-ci.yml README.md src/ tests/ scripts/
git commit -m "ci: implement gated DAG pipeline"
git push -u origin feature/ch012-dag-optimization
```

Open an MR and validate the YAML with GitLab CI Lint.

Expected:

```text
lint            passed
security_check  passed
docs_check     passed
unit_tests     passed
package        passed
verify         passed
```

Inspect the pipeline graph. `unit_tests` can begin after `lint`, while `security_check` and `docs_check` may still be running. Packaging waits for all three mandatory gates.

### Step E — Failure injection: unit test

Temporarily change the expected total in `test_total` from `10` to `11`. Commit and push.

Expected: `unit_tests` fails; `package` and `verify` do not run. Restore `10` and push again.

### Step F — Failure injection: security gate

Add the harmless string `DEMO_FORBIDDEN_MARKER_123` to a temporary comment in `src/math_service.py`, commit and push.

Expected: `security_check` fails; packaging is blocked even if unit tests pass. Remove the marker and confirm recovery.

### Step G — Benchmark stage barrier vs DAG

In the same disposable project, capture the current DAG pipeline job start/end times and total duration.

Create a separate feature branch from the clean baseline and remove the `needs` declarations from `unit_tests` and `package`, retaining the explicit artifact download for `verify` as needed. Run the equivalent stage-barrier pipeline. Compare:

| Metric | Stage barrier | DAG |
| --- | --- | --- |
| Pipeline ID | Record | Record |
| Runner queue time | Record | Record |
| Total pipeline duration | Record | Record |
| Unit-test start relative to lint completion | Record | Record |
| Packaging gate outcome | Record | Record |
| Runner count and concurrency | Record | Record |

Run more than once if practical and compare similar runner load. **Do not invent a speedup**: a small pipeline may show little improvement, and runner contention can erase the benefit.

### Step H — Cleanup

Remove temporary failure-injection changes and disposable branches. Merge only after approvals and a passing pipeline. If a merged training change needs reversal, use a reviewed revert MR, never a force-push to protected `main`.

## 8. Operational troubleshooting

| Symptom | Cause to investigate | Safe response |
| --- | --- | --- |
| Pipeline creation fails | `needs` references a job excluded by rules | Align rules or use `optional: true` only when truly optional |
| Package starts before security completes | Missing security dependency | Add required `needs` edge |
| Artifact missing in verify | `needs: artifacts` omitted, path/expiry issue | Declare producer artifacts explicitly |
| Pipeline slower after DAG | Runner saturation, queueing, cache misses | Inspect metrics and tune concurrency |
| Job never starts | Runner tags, protection, offline status | Validate runner eligibility and capacity |
| Retries hide flaky tests | Blanket retry policy | Fix flaky tests; retry only transient infra failures |
| Duplicate work across parallel jobs | No sharding implementation | Implement deterministic shard assignment |
| Interrupted publishing job | Unsafe `interruptible` default | Make state-changing jobs noninterruptible and idempotent |
| Resource-group bottleneck | Serialized job contention | Inspect queue, reduce lock scope safely |
| Production change bypasses approval | Privileged CI credentials | Revoke access, enforce reviewed GitOps and Argo CD policy |

## 9. Enterprise production practices

- Pin runner images and dependencies; patch and isolate runners.
- Treat merge-request code as untrusted.
- Use `needs` only for genuine dependencies; do not bypass required security checks.
- Protect artifacts, caches and logs by trust boundary.
- Separate test execution from image signing/publishing and production release authority.
- Measure critical path and runner queueing before increasing parallelism.
- Use resource groups only for operations requiring serialization, not as access control.
- Publish an immutable image once, then promote its digest via reviewed GitOps MRs.
- Enforce Kubernetes RBAC, quotas, NetworkPolicies, Pod Security and appropriate node isolation across shared-cluster namespaces.

## 10. Acceptance checklist

- [ ] Stage-barrier and DAG semantics understood and demonstrated.
- [ ] CI YAML validated with GitLab CI Lint.
- [ ] All six lab jobs succeed on a clean MR.
- [ ] Unit-test failure blocks packaging.
- [ ] Security-gate failure blocks packaging.
- [ ] Artifact verification succeeds with declared dependency.
- [ ] Pipeline duration and queueing compared using real observations.
- [ ] Runner privileges, job retries and interruption behavior reviewed.
- [ ] No production credentials or cluster write access in MR jobs.
- [ ] GitOps promotion approval remains separate from CI completion.

## 11. Knowledge checks

1. When does `needs` improve latency compared with stage barriers?
2. Why is `needs: []` inappropriate for an unguarded release job?
3. What does `optional: true` mean when a dependency is omitted?
4. Why does `parallel: 3` not automatically split tests?
5. What is the difference between a resource group and an approval gate?
6. Which metrics distinguish DAG gains from runner contention?
7. Why must security checks be explicit dependencies of packaging?

## 12. Completion

**Pass:** The clean DAG pipeline succeeds, deliberate unit/security failures block packaging, artifacts are verified, and actual pipeline timing evidence is recorded.

**Next: Chapter 013 — GitLab CI/CD Variables, Environments, Secrets and Configuration Precedence.**
