# Chapter 013 — GitLab CI/CD Variables, Environments, Secrets and Configuration Precedence

**Part 03 — GitLab CI/CD Fundamentals** | **Chapter 013 / 100**  
**Audience:** SRE, infrastructure, DevSecOps and platform engineers  
**Lab:** Disposable private GitLab project, nonprivileged runner, synthetic configuration only  
**Architecture:** GitLab CI validates/builds → reviewed GitOps changes → Argo CD reconciles Dev, Test, Staging and Prod namespaces on a shared Kubernetes cluster.

> **Safety:** Never put real credentials in YAML, test files, job logs, artifacts or Git history. Use a disposable project and synthetic values throughout this lab. A masked variable is not safe from malicious code running in the same job.

## 1. Learning objectives

After completing this chapter, you will be able to:

1. Distinguish predefined, YAML-defined, project, group, instance, pipeline and policy variables.
2. Understand variable precedence, expansion and environment scope without relying on assumed defaults.
3. Configure protected, masked, hidden and file-type variables appropriately.
4. Explain the differences between GitLab environments, Kubernetes namespaces and GitOps desired state.
5. Design short-lived cloud authentication with OIDC and external secrets rather than long-lived static keys.
6. Validate variable behavior safely with synthetic values, without printing secrets.
7. Troubleshoot missing variables, unexpected overrides and unsafe MR exposure.

## 2. Enterprise configuration architecture

```text
GitLab group/project settings
  |-- nonsecret variables
  |-- protected/masked secrets (only where unavoidable)
  |-- CI identity / OIDC configuration
  |
  v
GitLab pipeline
  |-- MR jobs: untrusted, no production credentials
  |-- protected main jobs: trusted build identity
  |-- release automation: restricted, approved identity
  |
  v
Immutable image digest
  |
  v
Reviewed GitOps environment change
  |-- environments/dev/
  |-- environments/test/
  |-- environments/staging/
  +-- environments/prod/
  |
  v
Argo CD Applications and AppProjects
  |
  v
Shared Kubernetes cluster
  |-- demo-dev
  |-- demo-test
  |-- demo-staging
  +-- demo-prod
```

**Do not confuse:** GitLab's `environment:` keyword records deployment environments in GitLab; it does not create Kubernetes namespaces, enforce cluster RBAC or make an Argo CD deployment happen.

## 3. Variable sources and scope

| Source | Example | Guidance |
| --- | --- | --- |
| Predefined | `CI_COMMIT_SHA`, `CI_PIPELINE_ID` | Read-only pipeline context; avoid overriding |
| YAML global | `variables: APP_NAME: demo-app` | Nonsecret defaults |
| YAML job | Job-level `variables:` | Nonsecret job-specific settings |
| Project | GitLab project CI/CD settings | Scoped project configuration |
| Group / subgroup | Group CI/CD settings | Inherited; review scope and overrides |
| Instance | Administrator configuration | Centrally governed |
| Pipeline / trigger inputs | Manual/API/trigger values | Restrict who can override |
| Policy variables | Security/execution policies | Higher-precedence governed values where applicable |
| Dotenv artifact | Produced during CI | Nonsecret cross-job metadata only |

### Precedence matters

GitLab variable precedence is **not** simply “job beats project.” In current GitLab documentation, pipeline execution policy and scan execution policy variables can outrank pipeline variables; pipeline variables can outrank project/group/instance variables; job YAML variables override top-level YAML defaults; dotenv variables have their own precedence position.

**Operational rule:** Consult the variable-precedence reference for your deployed GitLab version and record the effective result with a harmless synthetic test. Be especially cautious with manual pipeline variables and downstream trigger forwarding, which can override expected values. GitLab supports controls on who may use pipeline variables; consider typed pipeline inputs where appropriate.

## 4. Protected, masked, hidden and file-type variables

### Protected

Protected variables are intended for pipelines on eligible protected branches/tags. Availability to merge-request and merged-results pipelines depends on project configuration, ref protection and GitLab behavior. Never assume all MRs are safe consumers.

### Masked

Masking attempts to redact matching variable values in job logs. It does **not** prevent scripts from reading or transmitting those values, and transformations may evade redaction.

### Hidden

Where supported, hidden variables prevent later display of their values in the GitLab UI. Hiding is not runtime isolation: an authorized job can still access the value.

### File-type

File-type variables expose a temporary file path to a job rather than embedding a multi-line credential directly into the environment variable. Restrict file permissions and lifecycle; the job still has access to the file content.

### Environment scope

GitLab CI/CD variables can be limited to environments such as `staging` or `production` where supported. Environment scope is not an independent authentication boundary. A job must be authorized and correctly mapped to the environment; use separate trusted identities and GitOps approvals for production.

## 5. Recommended enterprise variable policy

- Put nonsecret application names, feature toggles and test parameters in versioned YAML where appropriate.
- Put actual secrets in a supported secret manager, not Git.
- Use OIDC federated workload identity for cloud access where supported, with short-lived credentials and narrowly constrained trust conditions.
- Scope GitLab variables to the smallest eligible project/ref/environment.
- Limit privileged runners and restrict token creation, trigger variables and pipeline override permissions.
- Never expose production credentials to untrusted MR or fork pipelines.
- Do not forward secrets in dotenv artifacts, caches, logs or job artifacts.
- Audit configuration changes and rotate compromised credentials promptly.

## 6. OIDC and external secret patterns

A trusted job may request an OIDC ID token from GitLab and exchange it for narrowly scoped, short-lived cloud credentials through an identity provider. This requires explicit trust configuration in AWS, Azure or Google Cloud; **declaring `id_tokens` alone grants no cloud access**.

Illustrative configuration only:

```yaml
trusted_identity_example:
  stage: validate
  id_tokens:
    CLOUD_ID_TOKEN:
      aud: https://identity.example.com
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
  script:
    - test -n "$CLOUD_ID_TOKEN"
    - echo "ID token issued; do not print token contents"
```

Use this only with a trusted runner and approved identity configuration. Production implementations must validate issuer, audience, subject/ref/project claims, expiry and least-privilege roles; never print or persist the token. This example validates token presence but does not perform an exchange.

For Kubernetes applications, use supported external secret controllers and workload identities to fetch runtime secrets; GitOps should hold **references**, not plaintext production secret values.

## 7. Hands-on lab — safe precedence and environment scope

### Prerequisites

- Disposable GitLab project `https://gitlab.example.com/training/demo-app`.
- Authorized access to project CI/CD variable settings.
- Nonprivileged runner with Python 3.12 image support.
- No real secret values.
- GitLab version and edition recorded.

### Step A — Configure synthetic project variables

In the GitLab project CI/CD variable settings, add:

| Key | Synthetic value | Type | Protected |
| --- | --- | --- | --- |
| `LAB_REGION` | `project-region` | Variable | No |
| `LAB_OVERRIDE` | `project-level` | Variable | No |
| `LAB_PRIVATE_MARKER` | `synthetic-value-only-12345` | Variable | No |

Mark `LAB_PRIVATE_MARKER` masked only if your GitLab version accepts the value and requirements; **do not print it**. Do not mark these variables protected for the initial MR lab, because the feature branch may not be protected.

### Step B — Create files

```text
demo-app/
├── .gitlab-ci.yml
├── README.md
└── scripts/
    └── inspect_config.py
```

`README.md`:

```markdown
# demo-app

Synthetic GitLab variable precedence and environment-scope lab.
```

`scripts/inspect_config.py`:

```python
import os
from pathlib import Path

required = ["CI_COMMIT_SHA", "CI_PIPELINE_ID", "LAB_REGION", "LAB_OVERRIDE"]
missing = [key for key in required if not os.environ.get(key)]
if missing:
    raise SystemExit(f"FAIL: missing variables: {missing}")

expected = os.environ["LAB_EXPECTED_OVERRIDE"]
actual = os.environ["LAB_OVERRIDE"]
if actual != expected:
    raise SystemExit("FAIL: override value does not match expected precedence")

if not os.environ.get("LAB_PRIVATE_MARKER"):
    raise SystemExit("FAIL: synthetic private marker missing")

print("PASS: required variables available")
print("PASS: LAB_OVERRIDE precedence matches expectation")
print("PASS: private marker exists (value intentionally not printed)")
print("PASS: pipeline context present")
Path("reports").mkdir(exist_ok=True)
Path("reports/summary.txt").write_text(
    "Synthetic configuration checks passed\n", encoding="utf-8"
)
```

### Step C — Create pipeline

`.gitlab-ci.yml`:

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages:
  - validate
  - report

default:
  image: python:3.12-slim

variables:
  LAB_REGION: "yaml-region"
  LAB_OVERRIDE: "yaml-global"
  LAB_EXPECTED_OVERRIDE: "project-level"

check_precedence:
  stage: validate
  script:
    - python scripts/inspect_config.py
  artifacts:
    when: always
    paths:
      - reports/summary.txt
    expire_in: 1 day

check_job_scope:
  stage: validate
  variables:
    LAB_JOB_ONLY: "job-specific"
  script:
    - python -c 'import os; assert os.environ["LAB_JOB_ONLY"]=="job-specific"; print("PASS: job variable")'

check_metadata:
  stage: report
  script:
    - python -c 'import os; print("Pipeline metadata present:", bool(os.environ.get("CI_PIPELINE_ID")))'
```

**Expected precedence:** The project-level `LAB_OVERRIDE=project-level` overrides the YAML global value `yaml-global` in this lab, unless another higher-precedence value has been set. The same applies to `LAB_REGION`. This demonstrates why YAML job variables are not necessarily the final value.

### Step D — Run merge-request pipeline

```bash
git clone https://gitlab.example.com/training/demo-app.git
cd demo-app
git switch main
git pull --ff-only origin main
git switch -c feature/ch013-variables
# Add the files above using your editor
git add .gitlab-ci.yml README.md scripts/
git commit -m "ci: validate variable precedence safely"
git push -u origin feature/ch013-variables
```

Open an MR. Validate CI YAML with GitLab CI Lint.

Expected:

```text
check_precedence   passed
check_job_scope    passed
check_metadata     passed
```

Inspect `reports/summary.txt`: it contains only a success summary, not the synthetic private value.

### Step E — Negative test: override conflict

In the disposable project settings, temporarily change `LAB_OVERRIDE` to `unexpected-value` and rerun the MR pipeline.

Expected: `check_precedence` fails. Restore `project-level`, rerun and verify success.

Do not use this procedure on shared or production project variables.

### Step F — Negative test: missing variable

Temporarily remove the disposable `LAB_PRIVATE_MARKER` variable and rerun.

Expected: the check fails without printing the value. Restore the synthetic marker and verify recovery.

### Step G — Protected-variable isolation test

Create a separate synthetic variable `LAB_PROTECTED_ONLY` with **Protected** enabled. In a feature-branch MR pipeline, add a test that reports only presence:

```yaml
check_protected_scope:
  stage: validate
  script:
    - python -c 'import os; print("Protected marker present:", "LAB_PROTECTED_ONLY" in os.environ)'
```

Verify whether the variable is absent or available based on your actual GitLab configuration, ref protections and MR pipeline settings. The desired security outcome for an untrusted feature MR is **absent**. If present unexpectedly, stop and investigate before using any real protected secrets.

On a trusted protected default-branch pipeline, verify eligible availability without printing its value. Remove the temporary check afterward.

### Step H — Environment scope concept test

If environment-scoped project variables are supported, create a synthetic variable `LAB_ENV_LABEL` with environment scope `staging` and value `staging-only`. Add a job:

```yaml
check_staging_scope:
  stage: validate
  environment:
    name: staging
    action: prepare
  script:
    - python -c 'import os; assert os.environ.get("LAB_ENV_LABEL")=="staging-only"; print("PASS: staging-scoped value")'
```

This job records/prepares a **GitLab environment**; it does not deploy anything. Depending on GitLab version and project environment protection settings, permission checks may apply. Test in the disposable project and record actual behavior.

### Step I — Cleanup

Remove all synthetic project variables, temporary test jobs, feature branches and disposable environment records when no longer needed. Keep nonsecret acceptance evidence. Do not modify production CI settings.

## 8. Environment naming and GitOps separation

| GitLab concept | Example | Kubernetes/GitOps counterpart |
| --- | --- | --- |
| CI environment | `staging` | May correspond to GitOps `environments/staging/` |
| CI environment URL | App URL | Operational link, not deployment proof |
| Environment-scoped variable | `LAB_ENV_LABEL` | Not a Kubernetes Secret |
| Protected environment | Approved deployment access | Does not replace GitOps or Argo CD RBAC |
| GitOps directory | `environments/prod/` | Desired state for production |
| Kubernetes namespace | `demo-prod` | Workload isolation boundary inside shared cluster |

Do not assume creating a GitLab environment creates a namespace, cluster role or Argo CD Application.

## 9. Troubleshooting runbook

| Symptom | Likely cause | Safe action |
| --- | --- | --- |
| Variable unexpectedly overridden | Higher-precedence project/pipeline/policy variable | Inventory all scopes and pipeline inputs |
| Protected variable missing | Ref not eligible or pipeline-source restrictions | Check branch protection and settings |
| Protected variable visible in MR | Unexpected eligibility or misconfiguration | Stop privileged execution; audit settings |
| Masking not applied | Unsupported value format or transformed output | Remove logging; revoke if exposed |
| File variable missing | Wrong type, scope or job permissions | Verify variable configuration |
| Environment-scoped variable absent | Job environment mismatch or feature support | Validate exact environment name |
| OIDC exchange denied | Audience, subject, issuer or trust policy mismatch | Inspect identity claims securely |
| Duplicate/conflicting configuration | Group inheritance or manual overrides | Document effective source and restrict overrides |
| Secret found in artifact/log | Unsafe script or artifact paths | Revoke/rotate, investigate, restrict access |

## 10. Enterprise acceptance checklist

- [ ] Variable sources and precedence documented for the deployed GitLab version.
- [ ] Project variable overrides YAML default in the synthetic lab.
- [ ] Missing/incorrect synthetic values fail without disclosing their contents.
- [ ] Protected variable eligibility verified on untrusted and trusted refs.
- [ ] CI job logs and artifacts contain no secret values.
- [ ] Environment scope behavior verified without deploying anything.
- [ ] Privileged identity uses short-lived federation or managed secrets where supported.
- [ ] Production credentials are not available to MR jobs.
- [ ] Production release approval remains in protected GitOps and Argo CD controls.
- [ ] Actual pipeline IDs, settings and observed results recorded.

## 11. Knowledge checks

1. Why can a project variable override a job YAML variable?
2. Why is masking not a sufficient defense against a malicious script?
3. What makes a protected variable eligible for a particular pipeline?
4. How do GitLab environments differ from Kubernetes namespaces?
5. Why is OIDC preferable to long-lived static cloud credentials?
6. Why should dotenv artifacts never carry production secrets?
7. How can pipeline-variable overrides create release governance risks?

## 12. Completion criteria

**Pass:** You demonstrate synthetic variable precedence, safe failure on missing values, observed protected-variable isolation and environment-scoped behavior, and can explain how production identity is separated from untrusted MR execution.

**Next: Chapter 014 — GitLab CI/CD Artifacts, Caching, Reports and Pipeline Data Flow.**
