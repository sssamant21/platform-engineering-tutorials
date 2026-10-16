# Chapter 021 — Declarative Pipeline Syntax, Stages, Steps and Directives

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 05:** Declarative and Scripted Pipelines  
**Chapter:** 021 / 100  
**Companion lab:** [021 — Declarative Pipeline Syntax and Directives Check](labs/021-declarative-pipeline-syntax-stages-steps-directives-check.md)

> **Safety:** The executable smoke Pipeline uses `agent none` and lightweight Pipeline steps. Never enable built-in controller executors to make shell steps work. Shell builds require a separately provisioned, isolated and authorized agent.

## 1. Learning outcomes

Explain Declarative Pipeline grammar; use `pipeline`, `agent`, `stages`, `stage`, `steps`, `options`, `parameters`, `environment`, `when`, `post` and `tools`; understand `script`, `parallel` and `matrix`; distinguish Pipeline orchestration from agent-backed execution; debug syntax, scope, security and stage results.

## 2. Declarative Pipeline architecture

```text
protected Git branch -> Jenkinsfile -> Declarative parser
                                     |
                          pipeline / options / parameters
                                     |
                         stage -> when -> agent -> steps
                                     |
                          post conditions / build result
                                     |
                       logs, reports, artifacts, audit
```

A Declarative Jenkinsfile is versioned Pipeline-as-Code. The Jenkins controller interprets and orchestrates; workspace operations run on eligible agents. Use a protected branch and pull-request review before privileged changes.

## 3. Syntax and directive map

| Directive | Typical scope | Purpose | Caution |
|---|---|---|---|
| `pipeline` | Root | Declarative entry point | One top-level block |
| `agent` | Pipeline or stage | Allocates execution context | `none` does not provide workspace |
| `stages` | Pipeline/stage | Ordered stage container | Must contain valid stage definitions |
| `stage` | Inside stages | Named phase | Steps or nested supported structure |
| `steps` | Stage | Executable Pipeline steps | `sh` needs node/workspace |
| `options` | Pipeline or stage | Timeout, timestamps, discarder | Check directive scope |
| `parameters` | Pipeline | User-supplied typed inputs | Validate and allowlist |
| `environment` | Pipeline or stage | Scoped variables/credential bindings | Avoid exposing secrets |
| `when` | Stage | Conditional stage execution | Understand `beforeAgent` |
| `post` | Pipeline or stage | Result-specific cleanup/actions | Preserve original failure |
| `tools` | Pipeline or stage | Managed tool selection | Tool must be configured |
| `triggers` | Pipeline | Cron/SCM event triggers | Governance and deduplication |

## 4. Minimal runnable Jenkinsfile

```groovy
pipeline {
  agent none
  stages {
    stage('Validate') {
      steps { echo 'Declarative Pipeline parsed successfully' }
    }
    stage('Report') {
      steps { echo 'No agent or workspace required' }
    }
  }
}
```

Create a Pipeline job and run it on a disposable controller. This is an orchestration smoke test, not a real build.

## 5. Complete controller-only demonstration

```groovy
pipeline {
  agent none
  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '10'))
  }
  parameters {
    choice(name: 'TARGET', choices: ['dev', 'staging'])
    booleanParam(name: 'FAIL_DEMO', defaultValue: false)
  }
  environment {
    APP_NAME = 'declarative-demo'
  }
  stages {
    stage('Validate') {
      steps {
        script {
          if (!(params.TARGET in ['dev', 'staging'])) {
            error('Target is not approved')
          }
        }
        echo "App=${env.APP_NAME}; target=${params.TARGET}"
      }
    }
    stage('Conditional staging') {
      when { expression { params.TARGET == 'staging' } }
      steps { echo 'Staging gate selected' }
    }
    stage('Result') {
      steps {
        script {
          if (params.FAIL_DEMO) {
            error('Intentional lab failure')
          }
        }
        echo 'Successful smoke run'
      }
    }
  }
  post {
    success { echo 'Build SUCCESS' }
    failure { echo 'Build FAILURE' }
    always { echo 'Record redacted evidence' }
  }
}
```

Expected: dev skips conditional staging; staging executes it. `FAIL_DEMO=true` produces FAILURE. This example uses no `sh`, `checkout`, `archiveArtifacts` or `junit` steps.

## 6. Stage-scoped isolated agent

The following requires a **pre-existing approved Linux agent** labeled `lab-linux`; do not run on the controller.

```groovy
pipeline {
  agent none
  stages {
    stage('Build') {
      agent { label 'lab-linux' }
      options { timeout(time: 10, unit: 'MINUTES') }
      steps {
        sh '''
          set -eu
          printf 'build on isolated agent\n'
          uname -s
        '''
      }
    }
  }
}
```

The controller queues until an eligible agent is available. A stage-level `agent` creates a workspace for that stage; later stages on different agents do not implicitly share files.

## 7. Declarative and Scripted comparison

Declarative imposes a structured DSL with `stages`/`steps` and declarative controls. Scripted Pipeline uses Groovy logic such as `node { stage('Build') { ... } }` for flexible orchestration. Use Declarative by default for standard enterprise delivery; use `script { }` sparingly for complex logic and keep shared logic in reviewed libraries.

## 8. Conditions, failures and post behavior

- `when { branch 'main' }` depends on appropriate multibranch/SCM branch context.
- `when { expression { ... } }` can gate on validated parameters.
- `post { always { ... } }` executes after runtime stage completion; it cannot fix a Jenkinsfile that fails parsing.
- `error('message')` fails the run intentionally; distinguish from agent infrastructure failure.
- `timeout` and `retry` should be bounded, with idempotency for side effects.

## 9. Environment and secrets

Plain `environment` values are suitable for non-sensitive configuration. Use Jenkins Credentials and narrowly scoped bindings for secrets, never free-text parameters or literal credentials. Avoid Groovy GString interpolation of secrets into shell commands; mask logs, restrict access and rotate after exposure.

## 10. Parallel and matrix overview

Declarative supports `parallel` stages and `matrix` axes for independent work, subject to syntax/plugin support. Each branch must have an appropriate agent for workspace operations. Limit concurrency and avoid shared mutable output paths. Detailed parallel and matrix labs appear in later Part 05 chapters.

## 11. Validation workflow

Review Jenkinsfile in Git; use Jenkins' Pipeline syntax/Declarative validation facilities where available; run controller-only parse/smoke; test agent-backed steps in staging; inspect build history, stage outcomes, logs and timeouts; promote only with change approval.

## 12. Monitoring and SRE controls

Track parse failures, skipped stages, build results, queue p95, timeout counts, agent availability, secret-scan incidents, retry storms, post-condition failures and Pipeline change failure rate. Establish an owner and rollback commit for every privileged Pipeline.

## 13. Twenty troubleshooting scenarios

| # | Symptom | Likely cause | Safe recovery |
|---|---|---|---|
| 1 | pipeline root missing | Declarative parser requires a top-level pipeline block | Add exactly one pipeline block |
| 2 | agent unspecified | Pipeline agent allocation and node selection | Declare agent none or an approved label |
| 3 | shell on agent none | sh requires node/workspace context | Allocate isolated agent for shell work |
| 4 | stage missing steps | Declarative stages require valid steps or nested stages/parallel/matrix | Correct stage grammar |
| 5 | duplicate stages directive | Only one stages section per scope | Consolidate stage declarations |
| 6 | invalid options placement | Options valid at pipeline/stage scope with supported directives | Move to supported scope |
| 7 | timeout unexpected | Top-level vs stage timeout and agent allocation | Define explicit timeout boundaries |
| 8 | when condition skipped | when expression, beforeAgent and parameter values | Inspect gating and expected skip |
| 9 | environment variable not found | Scope and interpolation context | Use env.NAME or approved environment block |
| 10 | Groovy interpolation leaks secret | GString expansion before shell masking | Use credentials binding and literal shell strings |
| 11 | post always does not run as expected | Parse failure vs runtime execution | Validate syntax and execution phase |
| 12 | post cleanup masks failure | Post step error and original build result | Preserve root cause and handle cleanup |
| 13 | parallel branch needs agent | Per-branch agent requirements | Allocate approved agent for workspace operations |
| 14 | matrix axis unsupported | Plugin/core syntax compatibility | Validate supported Declarative version |
| 15 | script block sandbox rejection | Groovy sandbox and script approvals | Use approved Pipeline APIs |
| 16 | stage skipped due to prior failure | Pipeline fail-fast behavior | Use explicit post/recovery strategy |
| 17 | input step blocks unattended | Approval owner and timeout | Define approver and bounded timeout |
| 18 | retry causes duplicate side effects | Non-idempotent deploy/build steps | Use idempotency and bounded retry |
| 19 | build remains queued | No matching agent label or capacity | Restore isolated agents; not controller executors |
| 20 | pipeline code drift | Inline UI script vs reviewed SCM Jenkinsfile | Move definition to protected Git |

## 14. Eight SRE runbooks

### RB-01 Declarative parse failure

**Procedure:** Capture Jenkinsfile revision and parser output; validate braces, directive order, step names and plugin support; revert last change.

**Exit criteria:** Jenkinsfile parses, agent trust boundary holds, expected stages/results are observed, and redacted evidence is recorded.

### RB-02 Agent and queue failure

**Procedure:** Inspect queue reason, labels, executors, pod provisioning and trust zones; restore authorized agents only.

**Exit criteria:** Jenkinsfile parses, agent trust boundary holds, expected stages/results are observed, and redacted evidence is recorded.

### RB-03 Stage failure

**Procedure:** Correlate stage, error, parameters and recent commits; reproduce in staging and apply bounded rollback.

**Exit criteria:** Jenkinsfile parses, agent trust boundary holds, expected stages/results are observed, and redacted evidence is recorded.

### RB-04 Conditional execution issue

**Procedure:** Inspect when conditions, beforeAgent, branch/parameter values and skipped-stage evidence.

**Exit criteria:** Jenkinsfile parses, agent trust boundary holds, expected stages/results are observed, and redacted evidence is recorded.

### RB-05 Credential or log exposure

**Procedure:** Stop affected runs, restrict logs, revoke/rotate, preserve redacted evidence and remove unsafe interpolation.

**Exit criteria:** Jenkinsfile parses, agent trust boundary holds, expected stages/results are observed, and redacted evidence is recorded.

### RB-06 Parallel or retry incident

**Procedure:** Check branch isolation, resource locks, fail-fast and idempotency; disable unsafe retries.

**Exit criteria:** Jenkinsfile parses, agent trust boundary holds, expected stages/results are observed, and redacted evidence is recorded.

### RB-07 Post-action and notification failure

**Procedure:** Inspect post condition, plugin availability and delivery route; keep primary build failure visible.

**Exit criteria:** Jenkinsfile parses, agent trust boundary holds, expected stages/results are observed, and redacted evidence is recorded.

### RB-08 Production release readiness

**Procedure:** Verify reviewed Jenkinsfile, isolated agents, test evidence, approvals, timeout, artifact provenance and rollback.

**Exit criteria:** Jenkinsfile parses, agent trust boundary holds, expected stages/results are observed, and redacted evidence is recorded.

## 15. Acceptance gates

| Gate | Requirement |
|---|---|
| G1 | Controller built-in executors zero |
| G2 | Root/stage/directive structure explained |
| G3 | Minimal no-agent smoke succeeds |
| G4 | Parameters and environment scope validated |
| G5 | Conditional staging gate tested |
| G6 | SUCCESS and intentional FAILURE captured |
| G7 | Agent-backed shell execution isolated or marked design-only |
| G8 | Secrets and SCM trust model reviewed |
| G9 | Three incident tabletop diagnoses |
| G10 | Redacted evidence, cleanup and owner sign-off |

## 16. Assessment — 100 points

| Domain | Points |
|---|---:|
| Declarative grammar and directives | 25 |
| Parameters, conditions and environment | 20 |
| Agent and workspace isolation | 20 |
| Results, post and error handling | 15 |
| Security, troubleshooting and rollback | 10 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ with all critical security gates. A controller-only smoke does not certify real build, test or deployment execution.

## 17. Cleanup

```bash
docker stop jenkins-ch021
docker rm jenkins-ch021
# Only if exclusively lab-owned:
docker volume rm jenkins-ch021-home
```

**Next:** Chapter 022 — Declarative Pipeline Agents, Environment, Parameters and Conditional Execution.
