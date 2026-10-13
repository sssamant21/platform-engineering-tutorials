# Chapter 004 — GitLab CI/CD Variables, Secrets, Artifacts, Caching and Secure Pipeline Configuration

**Part 01 — Enterprise Foundations**  
**Reference architecture:** GitLab CI/CD → immutable artifacts → reviewed GitOps promotion → Argo CD → shared Kubernetes cluster with `demo-dev`, `demo-test`, `demo-staging`, `demo-prod` namespaces  
**Lab scope:** Disposable GitLab project; no production credentials required.

## 1. Learning objectives

By completing this chapter you will:
1. Distinguish predefined, project, group, instance, pipeline and job-level CI/CD variables.
2. Explain masking, protection, environment scoping and why they are not complete security boundaries.
3. Use nonsecret variables safely and understand file-type variables.
4. Configure short-lived authentication with OIDC ID tokens and a trusted secrets broker.
5. Publish job artifacts, use dependency-aware downloads, and distinguish caches from artifacts.
6. Implement safe pipeline rules, retention, permissions and incident-response controls.
7. Validate the pipeline with a practical lab and troubleshoot common failures.

## 2. Enterprise architecture

```text
GitLab merge request / protected main
       |
       v
GitLab pipeline (workflow rules)
       |
       +-- validate job (no secrets) -----------+
       |                                        |
       +-- test job (no secrets) ---------------+--> package artifact
       |                                              |
       +-- trusted release job (protected ref)         v
                  |                             OCI image + SBOM
                  v                             signed digest
        OIDC token -> cloud IAM / Vault                |
                  |                                    v
         short-lived scoped credentials          GitOps promotion MR
                                                       |
                                                 approvals + policy
                                                       |
                                                     Argo CD
                                                       |
                                          Kubernetes environment namespace
```

**Security boundary:** Untrusted merge request code must not receive production credentials. Never assume a masked variable is safe from malicious job scripts. Keep deployment authority in the GitOps approval and Argo CD reconciliation workflow.

## 3. CI/CD variable types and precedence

| Type | Typical purpose | Caution |
| --- | --- | --- |
| Predefined | Commit SHA, pipeline ID, branch, MR metadata | Availability varies by pipeline type |
| YAML global | Nonsecret defaults shared by jobs | Committed to source; public to readers |
| YAML job | Job-specific configuration | Can override global defaults |
| Project/group/instance | Centralized settings and secrets | Scope and access need auditing |
| Pipeline-supplied | Manual/API/trigger values | Restrict overrides; untrusted input |
| File-type variable | Certificates or config represented as temporary files | Protect contents and cleanup |
| External secret | Short-lived credential from Vault/cloud secret store | Preferred for high-value credentials |

Variable precedence is not simply “job overrides project.” GitLab has a documented multi-level precedence order that changes with variable source and pipeline policy; verify your GitLab version's current documentation before relying on an override. Avoid reusing a secret variable name across multiple scopes.

### Variable controls

- **Masked:** GitLab attempts to redact matching values from job logs; transformations, shell tracing and deliberate exfiltration can bypass this.
- **Protected:** Only exposed to eligible protected refs, subject to GitLab's MR and pipeline configuration. Verify effective behavior with your GitLab version.
- **Environment-scoped:** Restricts variables to matching environment names; scope matching and wildcard rules need review.
- **Hidden:** Where supported, limits display in the UI; it does not make a secret inaccessible to jobs that receive it.
- **File-type:** The environment variable contains a path to a temporary file, not the raw secret.

Do not place secrets in `.gitlab-ci.yml`, `values.yaml`, command arguments, artifacts, caches, test reports or container image layers.

## 4. Secure identity and secret retrieval

For cloud access, prefer GitLab **OIDC ID tokens** exchanged for short-lived credentials with audience and subject restrictions.

Example trusted job skeleton:

```yaml
release_metadata:
  stage: release
  id_tokens:
    CLOUD_ID_TOKEN:
      aud: https://secrets.example.com
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
      when: manual
    - when: never
  script:
    - test -n "$CLOUD_ID_TOKEN"
    - echo "Token obtained; do not print it"
    # Exchange the token with a configured trusted broker.
    # No broker call is made in this educational example.
```

**Do not deploy this skeleton as an authorization system.** The trust policy must validate issuer, audience, subject, project identity, ref protection and token expiry. Configure cloud-specific identity federation for EKS/AWS, AKS/Azure and GKE/Google Cloud; use distinct trust policies and least-privilege roles. A manual job alone is not an approval boundary.

For Kubernetes workloads, use External Secrets Operator or a comparable approved secret integration with cloud workload identity, rather than embedding application secrets in Git.

## 5. Artifacts versus caches

| Property | Artifact | Cache |
| --- | --- | --- |
| Primary purpose | Pass or retain build outputs | Accelerate repeated work |
| Trust expectation | Controlled job output, still validate | Treat as potentially stale/untrusted |
| Consumption | `needs: artifacts` / `dependencies` | `cache` keys and policy |
| Retention | `expire_in` and GitLab retention settings | Runner/backend eviction and lifecycle |
| Security | Never store credentials | Never store credentials |
| Example | Test report, packaged source, SBOM | Package download directory |

Avoid caching across untrusted/protected ref boundaries. GitLab may separate protected and nonprotected caches depending on settings, but verify configuration rather than assuming separation.

## 6. Hands-on lab — safe variables, artifacts and caching

### Prerequisites

- Disposable GitLab project `demo-app`.
- GitLab Runner supporting Docker/container executor.
- No cloud credentials, Kubernetes privileges or production variables.
- A feature branch and an MR pipeline.

### Step A — Create files

`src/calculator.py`:

```python
def add(a: int, b: int) -> int:
    return a + b
```

`tests/test_calculator.py`:

```python
import unittest
from src.calculator import add

class TestCalculator(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

if __name__ == "__main__":
    unittest.main()
```

`requirements.txt` (empty file; illustrates a cacheable dependency workflow without external packages):

```text
# No third-party dependencies in this lab.
```

### Step B — Configure the complete `.gitlab-ci.yml`

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
  APP_NAME: "demo-app"
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

lint:
  stage: validate
  script:
    - python -m compileall -q src tests

unit_tests:
  stage: test
  needs:
    - lint
  cache:
    key:
      files:
        - requirements.txt
    paths:
      - .cache/pip/
    policy: pull-push
  script:
    - python -m pip --version
    - python -m unittest discover -s tests -v
    - mkdir -p reports
    - python -m unittest discover -s tests -v > reports/tests.txt 2>&1
  artifacts:
    when: always
    paths:
      - reports/tests.txt
    expire_in: 3 days

package_source:
  stage: package
  needs:
    - job: unit_tests
      artifacts: false
  script:
    - mkdir -p dist
    - tar -czf dist/demo-app-source.tar.gz src/
    - sha256sum dist/demo-app-source.tar.gz > dist/SHA256SUMS
  artifacts:
    paths:
      - dist/demo-app-source.tar.gz
      - dist/SHA256SUMS
    expire_in: 7 days

verify_package:
  stage: verify
  needs:
    - job: package_source
      artifacts: true
  script:
    - cd dist
    - sha256sum -c SHA256SUMS
    - tar -tzf demo-app-source.tar.gz
```

**Notes:** The cache is illustrative and may be empty because no packages are installed. The package checksum detects accidental corruption, **not malicious substitution or supply-chain compromise**. Production artifact attestation and signing require additional controls.

### Step C — Create a nonsecret project variable

In GitLab **Settings → CI/CD → Variables**, add:

```text
Key: LAB_RELEASE_CHANNEL
Value: development
Type: Variable
Protected: No
Masked: No
```

Use this only for harmless metadata. To verify it is available, temporarily add `test "$LAB_RELEASE_CHANNEL" = "development"` to the `lint` script, then rerun the MR pipeline.

Do **not** use real credentials in this exercise.

### Step D — Commit and run

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/ch004-secure-ci
git add .gitlab-ci.yml src/calculator.py tests/test_calculator.py requirements.txt
git commit -m "ci: demonstrate variables artifacts and cache controls"
git push -u origin feature/ch004-secure-ci
```

Create an MR targeting `main`, confirm the pipeline is created, and inspect all four stages.

Expected results:

```text
lint             passed
unit_tests       passed
package_source   passed
verify_package   passed
SHA256SUMS       OK
```

### Step E — Validate artifacts and cache behavior

1. Open `unit_tests` and inspect its `reports/tests.txt` artifact.
2. Open `package_source` and inspect `dist/demo-app-source.tar.gz` and `dist/SHA256SUMS`.
3. Open `verify_package`; confirm checksum verification and archive listing.
4. Rerun the pipeline; compare cache restore/save messages. Cache hits are **not guaranteed** because runner cache backends and retention vary.
5. Inspect the artifact expiration configuration.

### Step F — Failure simulation

Temporarily change the unit test expectation from `5` to `6`, commit and push.

Expected:
- Lint passes.
- Tests fail.
- Test report artifact is uploaded because `when: always`.
- Packaging and verification are not run.

Restore the expected value `5`, push and verify green.

### Step G — Cleanup and rollback

- Remove the disposable `LAB_RELEASE_CHANNEL` variable when finished.
- Close/merge the MR as appropriate and delete the lab branch.
- Do not delete project-wide caches or artifacts used by other teams.
- For merged mistakes, use a reviewed revert MR; never force-push protected `main`.

## 7. Production patterns

### Runner trust tiers

1. **Untrusted MR:** no privileged credentials, no signing keys, no production variables; isolated ephemeral runner.
2. **Trusted build:** protected refs, scoped registry publishing, SBOM and image scanning, provenance.
3. **Release automation:** protected identity allowed to create GitOps MRs, not silently merge production changes.
4. **Platform administration:** separate restricted runner pool and approval controls.

When CI runners share the same Kubernetes cluster as production, isolate runners using dedicated node pools, namespace quotas, network controls, Pod Security standards and capacity protections. For critical workloads, use separate CI clusters.

### Multi-environment release promotion

The release artifact is built once and identified by a digest. Promote the **same digest** through `demo-dev`, `demo-test`, `demo-staging`, and `demo-prod` by approved GitOps changes. Keep environment secrets in a managed secret store and use workload identity. Argo CD sync policy and production approvals remain separate from CI job execution.

### Production artifact controls

- Pin build images and dependencies.
- Generate SBOM and provenance attestation.
- Scan vulnerabilities and apply risk-based blocking policies.
- Sign container images and verify signatures at admission/deployment.
- Set retention policies that preserve incident/audit evidence.
- Prevent untrusted pipeline code from publishing to trusted registries.

## 8. Troubleshooting runbook

| Symptom | Checks | Corrective action |
| --- | --- | --- |
| Variable empty | Scope, protection, MR/ref type, precedence | Align variable scope and protected ref policy |
| Secret visible in logs | Debug tracing, script echo, masking limitations | Revoke/rotate secret; incident response |
| File variable fails | Path vs raw value, permissions | Pass the temporary file path correctly |
| Job can't authenticate | OIDC audience/subject/issuer, clock, trust policy | Fix federation policy; never hardcode credentials |
| Artifact missing | `needs`, paths, expiry, job result | Correct dependencies and retention |
| Cache miss | Key, runner backend, protected-ref isolation | Verify cache configuration; don't depend on hits |
| Cache contamination | Shared keys, untrusted pipelines | Partition or disable cross-trust caching |
| Pipeline skipped | `workflow: rules`, job `rules` | Use CI Lint and inspect event context |
| Runner stuck | Runner scope, tags, executor, capacity | Restore runner health or scale capacity |

## 9. Production acceptance checklist

- [ ] All secret sources and owners are inventoried.
- [ ] Untrusted MR pipelines cannot access protected production secrets.
- [ ] OIDC federation uses scoped trust claims and short-lived credentials.
- [ ] CI/CD variable precedence and environment scoping have been tested.
- [ ] Sensitive values are excluded from artifacts, logs and caches.
- [ ] Artifact retention, access and integrity controls are defined.
- [ ] Cache trust boundaries are isolated.
- [ ] Build images and dependencies are pinned and scanned.
- [ ] Release artifacts are immutable, signed and traceable.
- [ ] Production GitOps updates require review and explicit approval.
- [ ] Argo CD and Kubernetes identities follow least privilege.
- [ ] Secret leakage response and credential rotation are rehearsed.

## 10. Knowledge checks

1. Why does masking not guarantee a secret cannot be exfiltrated?
2. How do protected variables differ from environment-scoped variables?
3. Why are caches not suitable for passing release artifacts?
4. What does `needs: artifacts: true` do?
5. How does OIDC reduce long-lived cloud credential exposure?
6. Why should production promotion use the same image digest?

## 11. Completion criteria

**Pass:** The MR pipeline completes, test reports and package artifacts are available, checksum verification succeeds, a deliberate test failure blocks packaging, and you can explain the production secret/runner trust boundaries.

**Next:** Chapter 005 — Enterprise GitLab CI/CD Foundations Capstone: Secure Pipeline and Release Governance.
