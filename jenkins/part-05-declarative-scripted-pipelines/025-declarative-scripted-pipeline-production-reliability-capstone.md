# Chapter 025 — Declarative and Scripted Pipeline Production Reliability Capstone

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 05:** Declarative and Scripted Pipelines  
**Chapter:** 025 / 100 — **Part 05 final capstone**  
**Companion lab:** [Chapter 025 — Production Reliability Capstone Check](labs/025-declarative-scripted-pipeline-production-reliability-capstone-check.md)

> **Safety:** Use a disposable localhost Jenkins controller with **zero built-in executors**. The runnable examples use lightweight Pipeline steps, not shell/workspace steps. Deployment, agent-backed build, real credential bindings, notifications, JUnit and artifact publishing require separate approved staging validation.

## 1. Mission

Combine Chapters 021–024 into a production-oriented SRE acceptance for Declarative and Scripted Jenkins Pipelines: syntax and directives, typed inputs, conditional stages, environment scope, agents and trust boundaries, error classification, retries, timeouts, post/finally actions, Groovy/CPS durability, rollback and monitoring.

## 2. Prerequisite chapters

- [021 — Declarative Pipeline Syntax, Stages, Steps and Directives](021-declarative-pipeline-syntax-stages-steps-directives.md)
- [022 — Declarative Pipeline Agents, Environment, Parameters and Conditional Execution](022-declarative-pipeline-agents-environment-parameters-conditional-execution.md)
- [023 — Declarative Pipeline Post Conditions, Error Handling, Timeouts and Retries](023-declarative-pipeline-post-conditions-error-handling-timeouts-retries.md)
- [024 — Scripted Pipeline Groovy, Node, Stage and Flow Control](024-scripted-pipeline-groovy-node-stage-flow-control.md)

## 3. Reference architecture

```text
protected SCM / reviewed Jenkinsfile
              |
         typed parameters
              |
   Declarative or Scripted orchestration
              |
      when/if + release gates
              |
       stage-level agent
     (isolated trusted pool)
              |
       build/test/package
              |
       JUnit + digest + SBOM
              |
     immutable artifact store
              |
  approval -> controlled deployment
              |
  result/post/finally -> telemetry
              |
   incident recovery and rollback
```

Agent labels are not an authorization boundary. Use separate identities, credentials, agent pools and SCM trust for untrusted pull requests and privileged releases.

## 4. Capstone operational requirements

| Control | Production requirement | Acceptance evidence |
|---|---|---|
| Versioning | Protected Jenkinsfile and peer review | Commit, approval |
| Syntax | Valid Declarative/Scripted structure | Parse and smoke |
| Input | Typed parameters and allowlists | Negative test |
| Conditional | Expected branch/stage gates | Dev/staging runs |
| Agents | Controller executors zero; isolated pools | Node/queue review |
| Credentials | Folder-scoped least privilege | Access review |
| Recovery | Bounded retry, no duplicate side effects | Synthetic transient test |
| Timeout | Interruption preserved, orphans contained | Staging drill |
| Result | SUCCESS/FAILURE/UNSTABLE/ABORTED policy | Build evidence |
| CPS | Serializable state across suspension | Restart drill |
| Artifacts | Signed/checksummed immutable outputs | Provenance evidence |
| Observability | Queue, duration, failures, retries, cost | SLO dashboard |
| Rollback | Last-known-good commit and release | Recovery evidence |

## 5. Safe disposable controller

```bash
docker volume create jenkins-ch025-home
docker run -d --name jenkins-ch025 --restart=no \
  -p 127.0.0.1:8103:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch025-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker logs --tail 60 jenkins-ch025
docker port jenkins-ch025
```

Unlock privately at `http://127.0.0.1:8103`, create a named admin, and set **Manage Jenkins → Nodes → Built-In Node → executors = 0**. Pin reviewed image digests and plugins for production; mutable LTS tag is training-only.

## 6. Declarative implementation — runnable smoke

Create `ch025-declarative` as a Pipeline job with this Jenkinsfile:

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
    booleanParam(name: 'RETRY_DEMO', defaultValue: false)
  }
  stages {
    stage('Validate') {
      steps {
        script {
          if (!(params.TARGET in ['dev', 'staging'])) {
            error('Unapproved target')
          }
        }
        echo "Target=${params.TARGET}"
      }
    }
    stage('Staging gate') {
      when {
        beforeAgent true
        expression { params.TARGET == 'staging' }
      }
      steps { echo 'Staging-only path (no deployment)' }
    }
    stage('Resilience') {
      steps {
        script {
          int attempt = 0
          retry(2) {
            attempt++
            echo "Attempt ${attempt}"
            if (params.RETRY_DEMO && attempt == 1) {
              error('Simulated transient failure')
            }
          }
          if (params.FAIL_DEMO) {
            error('Intentional terminal failure')
          }
        }
      }
    }
  }
  post {
    success { echo 'POST SUCCESS' }
    failure { echo 'POST FAILURE' }
    always { echo 'POST ALWAYS: redacted evidence' }
  }
}
```

The staging gate logs only; it does not deploy. `RETRY_DEMO` fails the first of at most two attempts; `FAIL_DEMO` produces terminal FAILURE. Do not use real secrets or endpoints.

## 7. Scripted implementation — runnable equivalent

Create `ch025-scripted` with Pipeline parameters `TARGET` choice dev/staging, `FAIL_DEMO` boolean and `RETRY_DEMO` boolean. Then paste:

```groovy
def selected = params.TARGET ?: 'dev'
def attempt = 0
try {
  stage('Validate') {
    if (!(selected in ['dev', 'staging'])) {
      error('Unapproved target')
    }
    echo "Target=${selected}"
  }
  if (selected == 'staging') {
    stage('Staging gate') {
      echo 'Staging-only path (no deployment)'
    }
  }
  stage('Resilience') {
    retry(2) {
      attempt++
      echo "Attempt ${attempt}"
      if (params.RETRY_DEMO && attempt == 1) {
        error('Simulated transient failure')
      }
    }
    if (params.FAIL_DEMO) {
      error('Intentional terminal failure')
    }
  }
  echo 'SCRIPTED SUCCESS'
} catch (org.jenkinsci.plugins.workflow.steps.FlowInterruptedException interrupted) {
  throw interrupted
} catch (Exception ex) {
  echo "SCRIPTED FAILURE: ${ex.getClass().getSimpleName()}"
  throw ex
} finally {
  echo 'SCRIPTED FINALLY: redacted evidence'
}
```

Compare outcome, retry attempts, branch selection and finally output. Scripted does not automatically inherit Declarative `post` or `options`; configure concurrency, retention and timeouts explicitly at job/step level.

## 8. Five acceptance runs

| Run | Parameters | Expected |
|---|---|---|
| A | dev, fail=false, retry=false | SUCCESS; staging skipped |
| B | staging, fail=false, retry=false | SUCCESS; staging path |
| C | dev, fail=false, retry=true | First attempt fails, second succeeds |
| D | dev, fail=true, retry=false | FAILURE and post/finally evidence |
| E | invalid target (negative test) | Validation rejects before side effects |

The choice parameter normally prevents arbitrary target selection via UI. For negative testing, use a disposable modified allowlist/input or approved job API test; do not bypass RBAC on production.

## 9. Agent-backed production gates (staging only)

On an approved isolated Linux agent, validate checkout from protected SCM, shell build, JUnit test report, artifact checksum, provenance/SBOM, immutable registry publication, safe workspace cleanup and agent loss recovery. Do not claim these are covered by the no-agent smoke.

## 10. Reliability and interruption policy

Classify errors as transient, deterministic, security or interruption. Retry transient idempotent steps only, with bounded attempts/backoff. Propagate `FlowInterruptedException` on abort/timeout. Record orphaned external processes and reconcile side effects. Keep a tested rollback commit and immutable artifact digest.

## 11. CPS and controller recovery

Groovy state across suspension must remain serializable. Avoid holding Java streams, live client connections or large mutable objects. Validate a separate controlled restart while a safe suspended Pipeline is running, and distinguish resumable versus nonresumable steps. Never assume a backup is consistent without restore testing.

## 12. Observability, SLO and cost

Measure queue wait p95, stage duration p95, success/unstable/failure/aborted rates, retry success, agent provision failures, controller heap/CPU, script approvals, secret incidents, notification delivery, artifact retention and idle agent cost. Define owner, error budget and escalation for each release workflow.

## 13. Twenty production troubleshooting scenarios

| # | Symptom | Investigation | Safe recovery |
|---|---|---|---|
| 1 | Jenkinsfile parse failure | Parser output and reviewed commit | Revert Jenkinsfile |
| 2 | Unexpected controller shell execution | Executor count and node labels | Quarantine; disable controller executors |
| 3 | No eligible build agent | Queue reason and provisioner logs | Restore isolated pool |
| 4 | Privilege escalation through agent labels | Job RBAC, agent identity and folder trust | Separate trust zones |
| 5 | Unvalidated production target | Typed params and allowlist | Reject and require approval |
| 6 | Stage skipped during release | when branch/parameter context | Repair conditional gate |
| 7 | Wrong environment scope | Stage versus global env | Correct scoped config |
| 8 | Secret in console output | GString interpolation and credential binding | Contain and rotate |
| 9 | Secret archived as artifact | Archive allowlist and scanning | Quarantine artifact and rotate |
| 10 | Retry duplicates deployment | Attempt count and idempotency key | Stop and reconcile |
| 11 | Timeout leaves external process | Cancellation and process group | Terminate and reconcile |
| 12 | Operator abort swallowed | FlowInterruptedException handling | Rethrow interruption |
| 13 | UNSTABLE treated as success | Result policy and JUnit | Enforce quality gate |
| 14 | Post notification masks failure | post/finally secondary exception | Preserve primary result |
| 15 | CPS NotSerializableException | Objects retained across steps | Refactor durable state |
| 16 | Groovy loop saturates controller | Unbounded loop and CPU | Bound loops and offload |
| 17 | Parallel branch races | Shared workspace and mutable state | Isolate and lock |
| 18 | SCM definition drift | Inline script vs protected Git | Restore reviewed version |
| 19 | Restart loses nonresumable step | Step resumability and restart history | Recover safely from checkpoint |
| 20 | Release rollback unavailable | Artifact provenance and last-good commit | Restore approved immutable release |

## 14. Eight SRE runbooks

### RB-01 Pipeline outage triage

**Procedure:** Identify owner, commit, job result, parser errors, agent queue and last-good run; mitigate then verify.

**Exit criteria:** correct build result, protected release controls, verified recovery and redacted evidence.

### RB-02 Security containment

**Procedure:** Stop unsafe jobs, revoke exposed credentials, verify RBAC, protected branches and isolated agents.

**Exit criteria:** correct build result, protected release controls, verified recovery and redacted evidence.

### RB-03 Parameter/gate failure

**Procedure:** Audit typed inputs, allowlists, when conditions, approvals and environment scope; correct reviewed Jenkinsfile.

**Exit criteria:** correct build result, protected release controls, verified recovery and redacted evidence.

### RB-04 Timeout and retry incident

**Procedure:** Classify interruption, reconcile external effects, cap retries, terminate orphans and test idempotency.

**Exit criteria:** correct build result, protected release controls, verified recovery and redacted evidence.

### RB-05 Test and artifact incident

**Procedure:** Inspect JUnit result, immutable artifact digest, archive allowlist and release gate; block unsafe promotion.

**Exit criteria:** correct build result, protected release controls, verified recovery and redacted evidence.

### RB-06 CPS and restart failure

**Procedure:** Inspect serialization and suspension logs, preserve state, revert incompatible changes and test recovery.

**Exit criteria:** correct build result, protected release controls, verified recovery and redacted evidence.

### RB-07 Notifications and evidence

**Procedure:** Protect primary failure, deduplicate alerts, redact logs, retain audit artifacts and escalate.

**Exit criteria:** correct build result, protected release controls, verified recovery and redacted evidence.

### RB-08 Release rollback and acceptance

**Procedure:** Restore approved Jenkinsfile/release artifact, validate smoke and record gate evidence, SLO and owner signoff.

**Exit criteria:** correct build result, protected release controls, verified recovery and redacted evidence.

## 15. Ten acceptance gates

| Gate | Pass criteria |
|---|---|
| G1 | Zero controller executors |
| G2 | Versioned and reviewed Declarative/Scripted definitions |
| G3 | Typed/validated parameters and environment gates |
| G4 | Dev and staging execution paths verified |
| G5 | Bounded retry and terminal failure demonstrated |
| G6 | Correct post/finally and interruption policy |
| G7 | Isolated agent and credential trust design |
| G8 | Artifact/test/rollback provenance staged or marked not tested |
| G9 | Three incident tabletops, SLO and owner handoff |
| G10 | Evidence, cleanup and signoff |

## 16. Final Part 05 assessment — 100 points

| Domain | Points |
|---|---:|
| Declarative and Scripted implementation | 25 |
| Inputs, stages, agents and security | 20 |
| Retry, timeout and result handling | 20 |
| CPS, recovery and rollback | 15 |
| SRE scenarios and runbooks | 10 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Educational pass:** 90+ with no security-critical failures. Production go-live requires separate agent-backed, integration, security and recovery evidence plus owner approval.

## 17. Cleanup

```bash
docker stop jenkins-ch025
docker rm jenkins-ch025
# Destructive: only after confirming the volume is exclusively lab-owned
docker volume rm jenkins-ch025-home
```

**Part 05 complete:** Declarative and Scripted Pipelines — Chapters 021–025.

**Next:** Chapter 026 — Groovy Fundamentals for Jenkins Pipelines and Shared Libraries, beginning Part 06 — Groovy, Shared Libraries and Reusable Pipelines.
