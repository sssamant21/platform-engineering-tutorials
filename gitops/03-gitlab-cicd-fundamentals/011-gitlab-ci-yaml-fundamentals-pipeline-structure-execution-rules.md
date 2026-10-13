# Chapter 011 — GitLab CI/CD YAML Fundamentals, Pipeline Structure and Execution Rules

**Part 03 — GitLab CI/CD Fundamentals**  
**Chapter:** 011 of 100  
**Audience:** Platform Engineers, SREs, DevOps and GitLab Administrators  
**Hands-on:** A disposable GitLab project and nonprivileged runner  
**Reference architecture:** GitLab CI → immutable image → reviewed GitOps promotion → Argo CD → Kubernetes (Dev/Test/Staging/Prod namespaces on a shared cluster)

> This chapter focuses on how GitLab evaluates pipeline YAML and schedules jobs. It does **not** grant production deployment permissions or deploy Kubernetes workloads.

## 1. Learning objectives

After this chapter you can:

1. Explain the purpose and structure of `.gitlab-ci.yml`.
2. Use `workflow: rules`, `rules`, `stages`, `needs`, `default` and `variables`.
3. Distinguish merge-request pipelines from default-branch pipelines.
4. Avoid duplicate pipelines, accidentally skipped jobs and unintended release execution.
5. Understand YAML anchors, `extends`, `include`, `before_script` and `after_script`.
6. Validate pipeline configuration, simulate failures and troubleshoot scheduling.
7. Define production guardrails for runner isolation, identity and GitOps approval.

## 2. GitLab CI/CD execution architecture

```text
Git push / merge request / schedule / trigger
                  |
                  v
        GitLab evaluates workflow
           create pipeline?
                  |
                  v
           Evaluate job rules
                  |
                  v
           Pipeline job graph
       validate -> test -> package
                  |
                  v
       Runner claims eligible job
                  |
                  v
         Executor runs script
                  |
                  v
      Job status + artifacts/logs
                  |
                  v
       Protected main merge gate
                  |
                  v
   Trusted image build (later chapter)
                  |
                  v
   Approved GitOps MR + Argo CD sync
```

**Responsibility split:** GitLab controls pipeline creation and job scheduling; runners execute jobs. GitLab CI must not silently modify production desired state or perform unrestricted `kubectl apply` to the shared Kubernetes cluster.

## 3. Anatomy of `.gitlab-ci.yml`

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
  interruptible: true

variables:
  PYTHONDONTWRITEBYTECODE: "1"

syntax_check:
  stage: validate
  script:
    - python -m compileall -q src tests

unit_tests:
  stage: test
  script:
    - python -m unittest discover -s tests -v
```

| Keyword | Function | Operational concern |
| --- | --- | --- |
| `workflow` | Controls pipeline creation | Avoid duplicate/unintended pipelines |
| `stages` | Declares stage order | Barriers may delay work |
| `default` | Shares supported job defaults | Review executor image and privileges |
| `variables` | Defines nonsecret configuration | Do not store credentials in YAML |
| `job_name` | Defines a job | Use stable, descriptive names |
| `stage` | Assigns job to stage | Defaults to `test` if omitted |
| `script` | Runs commands | Exit status controls success |
| `rules` | Controls job inclusion/behavior | First matching rule wins |
| `needs` | Defines DAG dependencies | Can start jobs before earlier stages finish |
| `artifacts` | Stores job outputs | Retention and access matter |
| `cache` | Speeds up dependency reuse | Untrusted and potentially stale |

## 4. Pipeline creation with `workflow: rules`

GitLab evaluates `workflow: rules` before it creates jobs. A common enterprise pattern is to run merge-request pipelines for proposed changes and default-branch pipelines after approved merges:

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never
```

Expected behavior:

| Event | Pipeline |
| --- | --- |
| Push to a feature branch without MR | Not created |
| Feature branch with an open MR, MR pipeline event | Created |
| Push/merge to default branch | Created |
| Tag push | Not created |
| Schedule | Not created |
| API trigger | Not created |

These rules are intentional for the lab; production teams may need explicit scheduled, tag or security pipelines. Add only required sources, with appropriate authorization and tests.

### Job-level rules

```yaml
docs_check:
  stage: validate
  script:
    - test -f README.md
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
```

**Avoid this common error:** Using broad fallback `when: always` rules alongside MR rules without a matching workflow policy can create duplicate push and MR pipelines.

## 5. Stage sequencing versus DAG dependencies

### Stage-based ordering

```yaml
stages: [validate, test, package]

lint:
  stage: validate
  script: ["echo lint"]

test:
  stage: test
  script: ["echo test"]

package:
  stage: package
  script: ["echo package"]
```

All jobs in a stage normally wait for earlier stages to complete successfully.

### DAG ordering with `needs`

```yaml
test:
  stage: test
  needs: [lint]
  script: ["echo test"]

package:
  stage: package
  needs: [test]
  script: ["echo package"]
```

`needs` expresses direct dependencies. A job with `needs` may run before all jobs in preceding stages finish. Use `needs:optional` when referencing jobs that may be omitted by `rules`, otherwise pipeline creation can fail if a required job does not exist.

For artifact-consuming jobs, explicitly specify `needs:artifacts` in the supported YAML structure; do not assume a DAG job downloads every prior artifact.

## 6. Reuse and configuration composition

### `extends`

```yaml
.python_job:
  image: python:3.12-slim
  before_script:
    - python --version

lint:
  extends: .python_job
  script:
    - python -m compileall -q src
```

A job name beginning with a dot is a hidden template; it is not executed as a standalone job.

### YAML anchors

```yaml
.common_steps: &common_steps
  - python --version
  - python -m compileall -q src

validate:
  script: *common_steps
```

Anchors are YAML-level reuse within the same YAML file; they do not provide general cross-file inheritance.

### `include`

```yaml
include:
  - local: '/ci/quality.yml'
```

Use `include` for maintained templates and reusable jobs. In production, review trust and version pinning for external/project/remote includes. Changes to a shared CI template can affect many projects; apply CODEOWNERS and change governance.

### `before_script` and `after_script`

`before_script` runs setup commands before the job's main script. `after_script` runs separately after the main execution and is useful for cleanup/diagnostics, but it has distinct execution behavior and should not be relied on to make a failed job succeed or to guarantee cleanup under every failure mode.

## 7. Hands-on lab — rules, stages, dependencies and validation

### Prerequisites

- Disposable private GitLab project such as `https://gitlab.example.com/training/demo-app`.
- An authorized nonprivileged runner supporting a container executor.
- Git installed on Windows (Git Bash or PowerShell) or Linux/macOS.
- No cloud credentials or Kubernetes access.

### Step 1 — Create application files

```text
demo-app/
├── .gitlab-ci.yml
├── README.md
├── src/
│   ├── __init__.py
│   └── calculator.py
└── tests/
    └── test_calculator.py
```

Create empty `src/__init__.py`.

`src/calculator.py`:

```python
def add(a: int, b: int) -> int:
    return a + b


def multiply(a: int, b: int) -> int:
    return a * b
```

`tests/test_calculator.py`:

```python
import unittest
from src.calculator import add, multiply


class CalculatorTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_multiply(self):
        self.assertEqual(multiply(3, 4), 12)


if __name__ == "__main__":
    unittest.main()
```

`README.md`:

```markdown
# demo-app

Disposable GitLab CI/CD YAML fundamentals lab.
```

### Step 2 — Add complete pipeline

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

.python_job:
  before_script:
    - python --version

lint:
  extends: .python_job
  stage: validate
  script:
    - python -m compileall -q src tests
    - test -s README.md

unit_tests:
  extends: .python_job
  stage: test
  needs:
    - lint
  script:
    - python -m unittest discover -s tests -v

package:
  extends: .python_job
  stage: package
  needs:
    - unit_tests
  script:
    - mkdir -p dist
    - tar -czf dist/demo-app-source.tar.gz src
  artifacts:
    paths:
      - dist/demo-app-source.tar.gz
    expire_in: 7 days

verify:
  extends: .python_job
  stage: verify
  needs:
    - job: package
      artifacts: true
  script:
    - test -s dist/demo-app-source.tar.gz
    - tar -tzf dist/demo-app-source.tar.gz
```

**Expected:** Four jobs succeed. This source archive is a training artifact, not a production container image.

### Step 3 — Validate with GitLab CI Lint

Open GitLab's Pipeline Editor or CI Lint page and validate the file. Review:
- YAML syntax.
- Job names and stages.
- `needs` relationships.
- Rules for merge-request and default-branch events.
- Availability of a matching runner.

CI Lint syntax validity does not prove that permissions, runner isolation or production policies are correct.

### Step 4 — Commit and create MR

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch011-ci-yaml
# Create files shown in Steps 1 and 2 using your editor
git add .gitlab-ci.yml README.md src/ tests/
git commit -m "ci: add pipeline rules and DAG fundamentals lab"
git push -u origin feature/ch011-ci-yaml
```

Create an MR targeting `main`.

Expected pipeline:

```text
lint          passed
unit_tests    passed
package       passed
verify        passed
```

### Step 5 — Negative test: failed unit test

Temporarily change the test expectation from `5` to `6`, commit and push.

Expected:
- `lint` passes.
- `unit_tests` fails.
- `package` and `verify` do not run.

Restore `5`, push again and confirm green.

### Step 6 — Negative test: job rule omission

Add a temporary job to the pipeline:

```yaml
never_run_on_mr:
  stage: validate
  script:
    - echo "This job is intentionally absent from MR pipelines"
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
```

Expected:
- On an MR pipeline, the job is omitted.
- After approved merge to `main`, the default-branch pipeline includes it.

Remove the temporary job after observing the behavior.

### Step 7 — Verify pipeline source and artifacts

In GitLab inspect:
- Pipeline source: merge request versus push/default branch.
- Commit SHA and MR association.
- Runner assigned to each job.
- Package artifact presence and expiry.
- Job dependencies and total duration.

Do not print protected variables or authentication tokens into logs.

### Step 8 — Cleanup

After approval, merge the MR or close it and delete the training branch. Remove only disposable lab resources. For merged changes requiring rollback, create a reviewed revert MR rather than force-pushing protected `main`.

## 8. Production design guidance

### Runner trust boundaries

Use distinct runner pools for:
- Untrusted MR validation.
- Trusted default-branch builds.
- Restricted release automation.

Avoid giving untrusted MR jobs cloud credentials, signing keys, privileged Docker sockets or production kubeconfigs. Use short-lived OIDC identity for trusted automation where available.

### GitOps deployment separation

A production-ready pipeline should eventually:
1. Validate and test source.
2. Build a container image **once**.
3. Scan, generate SBOM/provenance, and sign the image.
4. Publish a digest.
5. Open reviewed GitOps promotion MRs for Dev → Test → Staging → Prod.
6. Let Argo CD reconcile approved configuration.

Do not build a different image per environment. Namespaces within one cluster do not fully isolate production; apply node isolation, RBAC, quotas, network policy and admission controls, or separate clusters when necessary.

### Pipeline reliability and performance

- Monitor runner saturation, pending-job age, job failure rates and pipeline duration.
- Use `needs` to reduce safe critical paths.
- Cache dependencies only across appropriate trust boundaries.
- Set artifact retention and pipeline timeout policies.
- Avoid unbounded job fan-out and resource-heavy CI workloads on production nodes.

## 9. Troubleshooting runbook

| Symptom | Likely cause | Investigation / action |
| --- | --- | --- |
| Pipeline not created | `workflow: rules` excluded event | Inspect pipeline source and CI Lint |
| Job omitted | Job-level `rules` | Verify first matching rule |
| Duplicate pipelines | Overlapping push and MR creation | Tighten `workflow: rules` |
| Job stuck pending | Runner offline, tags, scope, concurrency | Check runner availability and capacity |
| Invalid `needs` | Required job omitted by rules | Align rules or use supported optional dependency |
| Unexpected early job | DAG scheduling | Inspect `needs` rather than only stage order |
| Artifact unavailable | `needs: artifacts`, paths, expiry | Check dependency and artifact configuration |
| Included YAML changes unexpectedly | Unpinned shared template | Pin/review include and audit upstream change |
| CI job exposes secret | Untrusted execution or unsafe logging | Revoke/rotate and investigate immediately |

## 10. Enterprise acceptance checklist

- [ ] CI YAML validated with GitLab CI Lint.
- [ ] MR and default-branch pipeline behavior verified.
- [ ] Duplicate pipelines prevented for intended events.
- [ ] Job rules and stage/DAG dependencies documented.
- [ ] Failed unit tests block packaging and verification.
- [ ] Artifacts are accessible only as intended and expire appropriately.
- [ ] Untrusted MR jobs cannot access privileged credentials.
- [ ] Shared CI templates are reviewed and version-controlled.
- [ ] Runner scope, isolation and capacity are documented.
- [ ] Production deployment authority remains separate from CI execution.
- [ ] Evidence includes actual MR URL, pipeline ID and job results.

## 11. Knowledge checks

1. What is the difference between `workflow: rules` and job-level `rules`?
2. Why can `needs` allow a job to start before earlier stages finish?
3. What happens if a job `needs` another job omitted by `rules`?
4. Why should production CI includes be pinned and reviewed?
5. Why does a valid YAML file not prove a secure pipeline?
6. How does GitOps approval differ from successful CI completion?

## 12. Completion criteria

**Pass:** A disposable GitLab MR pipeline successfully executes the four jobs, a failing unit test blocks downstream jobs, a default-branch-only job is omitted from MR pipelines, and you can explain the pipeline creation and runner execution lifecycle.

**Next: Chapter 012 — GitLab CI/CD Jobs, Stages, Dependencies and DAG Optimization.**
