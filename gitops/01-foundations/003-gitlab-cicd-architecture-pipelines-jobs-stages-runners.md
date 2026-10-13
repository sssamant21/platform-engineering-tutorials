# Chapter 003 — GitLab CI/CD Architecture, Pipelines, Jobs, Stages and Runners

**Part 01 — Enterprise Foundations**  
**Track:** GitLab CI/CD + Helm + Argo CD + Kubernetes (EKS / AKS / GKE)  
**Lab:** `demo-app` in a disposable GitLab project  
**Environments:** Dev, Test, Staging, Production in separate namespaces of a shared Kubernetes cluster

## Learning objectives

After this chapter, you should be able to:
1. Explain GitLab's control plane and the runner execution plane.
2. Distinguish pipelines, stages, jobs, runners, executors, artifacts and caches.
3. Design a secure merge-request pipeline with `workflow: rules` and job `rules`.
4. Run and validate a reproducible multi-stage CI pipeline.
5. Identify runner isolation, secret-handling, artifact provenance and approval controls.
6. Troubleshoot failed, stuck, skipped and duplicate pipelines.

## 1. Architecture

```text
Developer -> GitLab Merge Request
                  |
                  v
      GitLab CI/CD orchestration
       .gitlab-ci.yml + rules
                  |
        +---------+---------+
        |                   |
        v                   v
  Ephemeral runner A   Ephemeral runner B
  lint / unit tests    security checks
        |                   |
        +---------+---------+
                  v
             Build job
                  |
           OCI registry
        image@sha256:...
                  |
                  v
       GitOps promotion MR
                  |
        approved desired state
                  |
                  v
              Argo CD
                  |
       Shared Kubernetes cluster
      +-----+------+--------+------+
      | dev | test | staging| prod |
      +-----+------+--------+------+
```

GitLab schedules jobs; **runners execute them**. Argo CD is the deployment reconciler. CI must not silently mutate production Kubernetes resources or bypass protected GitOps paths.

### Components and responsibilities

| Component | Responsibility | Operational concern |
| --- | --- | --- |
| GitLab server | Source, MR, pipeline configuration, orchestration | Availability, permissions, audit |
| Pipeline | DAG of jobs created by event and rules | Duplicate or unexpected execution |
| Stage | Logical execution grouping | Stage barriers and latency |
| Job | Script in a defined execution environment | Exit codes, reproducibility |
| Runner | Polls GitLab for eligible jobs and executes them | Capacity, isolation, credentials |
| Executor | Shell, Docker, Kubernetes, etc. | Security boundary and cleanup |
| Artifact | Output passed between jobs or retained | Retention, integrity, secrets |
| Cache | Reusable performance optimization | Poisoning, staleness, isolation |
| Registry | Immutable image/package storage | Provenance, scanning, retention |
| GitOps repo | Reviewed environment desired state | Separation of duties |
| Argo CD | Syncs approved desired state | RBAC, sync windows, drift |

## 2. Pipeline creation and execution model

1. A push, merge request, tag, schedule, API trigger or parent pipeline event occurs.
2. GitLab evaluates `workflow: rules` to decide whether to create a pipeline.
3. GitLab evaluates each job's `rules` to decide inclusion and behavior.
4. Jobs become eligible according to `stages` or `needs` dependencies.
5. An eligible runner claims a job according to scope, tags and availability.
6. The executor prepares an isolated working environment, checks out the source, downloads dependencies, executes scripts, and uploads artifacts.
7. GitLab records status and surfaces results in the MR.

**Important:** `rules` are evaluated in order; the first matching rule determines behavior. A broad fallback can unintentionally create duplicate push and MR pipelines.

## 3. Enterprise pipeline design principles

- Prefer merge-request pipelines for proposed code changes and default-branch pipelines for approved integration.
- Avoid duplicate pipelines with `workflow: rules`.
- Use `needs` only when jobs can safely start before the preceding stage finishes.
- Pin container images by digest in production and manage upgrades deliberately.
- Keep runner images minimal; avoid privileged Docker-in-Docker unless a documented exception exists.
- Use short-lived workload identity/OIDC where supported; avoid long-lived cloud credentials.
- Scope CI/CD variables to the required environments, mask and protect secrets, and never echo tokens.
- Treat contributions from forks and untrusted branches as untrusted code.
- Use protected runners for privileged publishing and release tasks.
- Use immutable build outputs; publish image digest and provenance for promotion.
- Distinguish caches (untrusted optimization) from artifacts (job output); neither is a secrets store.
- Enforce security gates before publishing or promoting an artifact.

## 4. Hands-on lab — first enterprise-style pipeline

### Prerequisites and safety

- A **disposable** GitLab project such as `https://gitlab.example.com/training/demo-app`.
- A GitLab Runner registered and able to run non-privileged container jobs.
- Git CLI installed; Docker is **not** required locally.
- Create a feature branch; do not modify production repositories.
- No Kubernetes access or production secrets are required for this chapter.

### Step A — Create lab files

```text
demo-app/
├── .gitlab-ci.yml
├── src/
│   └── calculator.py
└── tests/
    └── test_calculator.py
```

`src/calculator.py`:

```python
def add(a: int, b: int) -> int:
    return a + b
```

`tests/test_calculator.py`:

```python
import unittest
from src.calculator import add

class CalculatorTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

if __name__ == "__main__":
    unittest.main()
```

### Step B — Add `.gitlab-ci.yml`

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

default:
  image: python:3.12-slim
  interruptible: true

lint_python:
  stage: validate
  script:
    - python -m compileall -q src tests

unit_tests:
  stage: test
  needs:
    - lint_python
  script:
    - python -m unittest discover -s tests -v

package_source:
  stage: package
  needs:
    - unit_tests
  script:
    - mkdir -p dist
    - tar -czf dist/demo-app-source.tar.gz src/
    - test -s dist/demo-app-source.tar.gz
  artifacts:
    name: "demo-app-$CI_COMMIT_SHORT_SHA"
    paths:
      - dist/demo-app-source.tar.gz
    expire_in: 7 days
```

This intentionally uses only the Python standard library and packages source code as a **training artifact**. It is **not** a production container-image pipeline, does not scan/sign artifacts, and does not deploy to Kubernetes. Those capabilities are introduced in later chapters.

**Why `needs` matters:** The unit-test job explicitly depends on lint; the packaging job depends on tests. A failure prevents downstream work. More complex DAGs will be covered later.

### Step C — Commit and push

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/ch003-ci-pipeline
git add .gitlab-ci.yml src/calculator.py tests/test_calculator.py
git commit -m "ci: add validated three-stage demo pipeline"
git push -u origin feature/ch003-ci-pipeline
```

Create a merge request targeting `main`. If merge request pipelines are not enabled/configured for your project, verify project settings before assuming a pipeline will run.

### Step D — Validate the configuration

1. Open **Build → Pipeline editor → Validate** or the GitLab CI Lint page (menu varies by version).
2. Validate `.gitlab-ci.yml`.
3. Open the MR pipeline and confirm that `lint_python`, `unit_tests` and `package_source` appear.
4. Check job logs and the source artifact.
5. Confirm the MR pipeline passes before merge.

Expected result:

```text
lint_python      passed
unit_tests       passed (1 test)
package_source   passed
artifact         dist/demo-app-source.tar.gz
```

The exact UI, scheduling order, and job output vary by GitLab version and runner executor.

### Step E — Deliberate failure test

On the feature branch, temporarily change the expected result to `6`:

```python
self.assertEqual(add(2, 3), 6)
```

Commit and push. Verify:
- `lint_python` passes.
- `unit_tests` fails.
- `package_source` is not executed.

Restore the expected value `5`, push again, and verify that the MR pipeline returns to green.

### Step F — Check duplicate pipeline prevention

For a feature branch with an open MR, inspect **Build → Pipelines**. You should see the MR pipeline and not an additional branch push pipeline from the same change. The default branch gets a branch pipeline after merge.

### Step G — Cleanup and rollback

Do not delete a shared runner or production configuration. Remove the training branch after merging, or close the MR and delete the branch if this is only a lab. If the CI change is already merged and must be undone, open a reviewed revert MR rather than force-pushing `main`.

## 5. Runner design for enterprise environments

| Runner class | Workloads | Guardrails |
| --- | --- | --- |
| Untrusted MR runners | Lint, unit tests, static checks | No privileged tokens, ephemeral isolated executors |
| Trusted build runners | Container build, SBOM, scanning, signing | Restricted registration, short-lived credentials, provenance |
| Release automation runners | Create GitOps MRs, publish metadata | Protected refs, narrowly scoped GitLab token |
| Platform maintenance runners | Controlled administrative tasks | Separate pool, approval, audit, no general MR access |

For Kubernetes executors, prefer ephemeral job pods, dedicated namespaces, resource limits, network policies, and non-privileged security contexts. Avoid sharing sensitive caches across trust boundaries. Configure runner concurrency and autoscaling to protect the cluster from CI-induced resource contention.

**Production risk:** When runner pods and production workloads share the same Kubernetes cluster, CI spikes can affect production. Use dedicated node pools, quotas, priority and admission policies—or separate CI infrastructure for high-criticality production clusters.

## 6. CI/CD and environment promotion

```text
Commit -> MR pipeline -> Merge -> Build once -> Scan/Sign -> Publish digest
                                                         |
                                                         v
                                           Dev GitOps change + sync
                                                         |
                                                         v
                                           Test GitOps promotion
                                                         |
                                                         v
                                           Staging validation
                                                         |
                                                         v
                                           Approved Prod GitOps MR
                                                         |
                                                         v
                                           Controlled Argo CD sync
```

The application image digest remains constant through promotion. Helm values and external secret references may differ by environment. GitLab CI is not granted broad direct production deployment permissions.

## 7. Operational troubleshooting

| Symptom | Investigation | Resolution |
| --- | --- | --- |
| Pipeline not created | `workflow: rules`, source event, project settings | Fix workflow and test CI Lint |
| Job missing | Job `rules`, branch/MR context | Inspect evaluated rules |
| Job stuck/pending | Runner online status, tags, scope, capacity | Correct runner assignment or scale |
| Job fails before script | Image pull, executor, network, auth | Check runner/executor logs |
| Test failure | Job logs, code change, dependencies | Reproduce and correct code |
| Artifact missing | `artifacts.paths`, expiration, job success | Validate path and retention |
| Duplicate pipelines | Push and MR workflows | Tighten `workflow: rules` |
| Secret exposure | Job logs, variable scopes, runner trust | Revoke/rotate and follow incident process |

Useful diagnostics:
- GitLab project **Build → Pipelines**, then inspect the job trace.
- GitLab project **Settings → CI/CD → Runners** (or current equivalent).
- For self-managed runner administrators: `gitlab-runner verify` and runner service logs, subject to runner version and host permissions.
- Compare pipeline source, ref, commit SHA and job variables; do not print secret values.

## 8. Security and compliance acceptance

- [ ] Merge requests run only on runners with an appropriate trust level.
- [ ] No production secrets are exposed to untrusted pipeline code.
- [ ] Runner permissions, concurrency and capacity are documented.
- [ ] CI configuration is protected by CODEOWNERS and review.
- [ ] Pipeline rules prevent unintended or duplicate execution.
- [ ] Failed tests block artifact promotion.
- [ ] Artifacts have appropriate retention and access controls.
- [ ] Build provenance links artifacts to a specific commit and pipeline.
- [ ] Production deployment authority remains with reviewed GitOps + Argo CD controls.
- [ ] CI and runner telemetry is monitored and alertable.

## 9. Knowledge checks

1. What is the difference between a GitLab pipeline and a runner?
2. What do `workflow: rules` and job-level `rules` each control?
3. When should `needs` be used instead of stage-only ordering?
4. Why must untrusted MR jobs not receive production credentials?
5. Why is an immutable image digest promoted instead of rebuilding for each environment?
6. What risks arise when CI runners share a Kubernetes cluster with production?

## 10. Chapter completion

**Pass criteria:** You can create and validate a multi-stage MR pipeline, explain execution and runner placement, prove a failed test blocks packaging, inspect an artifact, and identify production security and resource-isolation requirements.

**Next:** Chapter 004 — GitLab CI/CD Variables, Secrets, Artifacts, Caching and Secure Pipeline Configuration.
