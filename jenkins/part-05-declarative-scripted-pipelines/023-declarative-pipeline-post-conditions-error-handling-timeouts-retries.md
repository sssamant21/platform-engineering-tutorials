# Chapter 023 — Declarative Pipeline Post Conditions, Error Handling, Timeouts and Retries

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 05:** Declarative and Scripted Pipelines  
**Chapter:** 023 / 100  
**Companion lab:** [023 — Post, Error, Timeout and Retry Check](labs/023-declarative-post-error-timeout-retry-check.md)

> **Safety:** The executable exercises use `agent none` and lightweight Pipeline steps. Never run untrusted shell commands on the controller. External notifications, test runners, deployments and agent work are staging-only.

## 1. Learning outcomes

Design `post` result conditions, differentiate SUCCESS/FAILURE/UNSTABLE/ABORTED, use `error`, `catchError`, `timeout`, `retry` and `warnError` responsibly, preserve interruption, avoid repeated side effects, prevent noisy notifications and implement SRE recovery.

## 2. Failure-handling architecture

```text
SCM Jenkinsfile -> validated Pipeline -> stage execution
                                         |
                                result / exception
                                         |
                           retry? transient + bounded
                                         |
                        SUCCESS / UNSTABLE / FAILURE
                               or ABORTED
                                         |
                          post: result-specific + always
                                         |
                      alert, evidence, cleanup, rollback
```

A post-action is not a replacement for a safe transactional deployment or independent incident-response workflow. Errors in cleanup/notifications can obscure the original incident.

## 3. Declarative post conditions

| Condition | Intended use | Note |
|---|---|---|
| `always` | Audit/cleanup attempt | Guard secondary errors |
| `success` | Successful result | Not a production acceptance guarantee |
| `failure` | Failed result | Alert with deduplication |
| `unstable` | Test/quality instability | Review JUnit or policy |
| `aborted` | Interrupted/canceled run | Do not blindly retry |
| `unsuccessful` | Any non-success result | Can overlap other conditions |
| `changed` | Result changed since previous run | Avoid alert storms |
| `fixed` | Recovery from prior unsuccessful result | Supported Declarative post condition |
| `regression` | Worsening from prior result | Check policy and plugin support |
| `cleanup` | Final post cleanup | Keep safe/idempotent |

## 4. Error handling semantics

`error('message')` fails the current execution. `catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE')` can mark a stage and build unstable while continuing. `warnError` is a convenience for marking instability. Never convert real deployment failures into SUCCESS merely to suppress alerts.

## 5. Runnable no-agent capstone Pipeline

```groovy
pipeline {
  agent none
  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '10'))
  }
  parameters {
    choice(name: 'MODE', choices: ['success', 'failure', 'unstable', 'retry', 'timeout'])
  }
  stages {
    stage('Validate') {
      steps {
        echo "Mode=${params.MODE}"
      }
    }
    stage('Simulate') {
      steps {
        script {
          switch (params.MODE) {
            case 'failure':
              error('Intentional failure')
              break
            case 'unstable':
              catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                error('Intentional unstable quality gate')
              }
              break
            case 'retry':
              int attempts = 0
              retry(2) {
                attempts++
                echo "Attempt ${attempts}"
                if (attempts == 1) {
                  error('Transient lab failure')
                }
              }
              break
            case 'timeout':
              timeout(time: 1, unit: 'SECONDS') {
                sleep(time: 3, unit: 'SECONDS')
              }
              break
            default:
              echo 'Success path'
          }
        }
      }
    }
  }
  post {
    success { echo 'POST success' }
    failure { echo 'POST failure' }
    unstable { echo 'POST unstable' }
    aborted { echo 'POST aborted' }
    always { echo 'POST always: collect redacted evidence' }
  }
}
```

The `timeout` mode intentionally triggers an interruption and normally produces **ABORTED**; verify actual result in the lab because plugin versions and surrounding exception handling can affect reporting. `retry` simulates one transient error followed by success, without side effects. The `sleep` step is a Pipeline timer, not an OS shell process.

## 6. Retry policy and idempotency

Retry only errors classified as transient (network timeouts, temporary 429/503, agent provisioning issues) and only when the operation is safe to repeat. Use bounded attempts, exponential backoff with jitter for external APIs, an idempotency key for mutating operations, and alerting after exhaustion. Do not retry irreversible production deployment blindly.

## 7. Timeout policy

Distinguish queue wait, agent acquisition, step execution and external service timeouts. A stage timeout may include agent provisioning depending on directive scope. Ensure cancellation terminates child processes and external jobs; monitor orphaned work. A timeout is an interruption, not always a normal FAILURE.

## 8. CatchError and interruption preservation

By default `catchError` is intended for recoverable failures; be careful not to swallow operator aborts or timeouts. When applicable use `catchInterruptions: false` so interruptions propagate. Scripted `try/catch` should rethrow interruption exceptions rather than treating them as retryable failures.

```groovy
catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE', catchInterruptions: false) {
  error('Recoverable quality gate failure')
}
```

## 9. Safe post actions

Use result-specific notifications, but do not print secrets or full unredacted environment dumps. In `post { always { ... } }`, collect logs and test reports only if the required workspace/agent exists. Avoid deleting evidence before publishing artifacts or completing compliance retention.

## 10. Testing and deployment gates

Test failures may mark a build UNSTABLE; production promotion should explicitly reject unacceptable quality results. Approval gates must have owners and timeouts. Prefer compensating actions and reviewed rollback plans over uncontrolled automated retry of deployment mutations.

## 11. Observability and SLOs

Track failure/unstable/aborted rates, timeout counts by stage, retry attempts and success after retry, duplicate side effects, post-action delivery, orphaned jobs, alert volume and mean time to recovery. Correlate by build number, SCM commit, stage and environment.

## 12. Operational change control

Review error paths in pull requests, test synthetic failure/timeout in staging, record the last-known-good Jenkinsfile and define an explicit escalation owner. A successful retry should still emit a reliability signal if the first attempt failed.

## 13. Twenty troubleshooting scenarios

| # | Symptom | Investigation | Safe recovery |
|---|---|---|---|
| 1 | Post block not invoked | Declarative parse failure or wrong scope | Fix parser/scope; retest |
| 2 | Success notification on unstable | Result classification and post condition | Use correct unstable/unsuccessful gate |
| 3 | Failure notification duplicates | Pipeline and stage post overlap | Deduplicate event keys |
| 4 | Cleanup masks root failure | Post step throws secondary exception | Guard cleanup; preserve original error |
| 5 | Timeout before agent allocation | Stage timeout includes queue/provisioning | Set expected budget and monitor queue |
| 6 | Timeout never terminates external job | Child process detached from agent | Use process groups and bounded external operations |
| 7 | Retry repeats deployment | Non-idempotent side effect | Stop and add idempotency key |
| 8 | Retry exhausts quota | High attempt count and API throttling | Bound retries and add backoff |
| 9 | Retry hides persistent error | All errors treated as transient | Classify error and fail fast |
| 10 | CatchError turns failure green | buildResult/stageResult mismatch | Set explicit result policy |
| 11 | Unstable test suite blocks promotion | JUnit result and release gate | Fix tests or approved exception |
| 12 | Abort reported as failure | InterruptedException swallowed | Preserve interruption and ABORTED |
| 13 | Manual abort ignored | catch block handles interruption incorrectly | Rethrow interruption |
| 14 | Input approval waits forever | Missing timeout and owner | Bound approval wait |
| 15 | Parallel failure leaves tasks running | failFast and branch behavior | Cancel/contain sibling work |
| 16 | Notification credentials leaked | Groovy interpolation or logs | Rotate and scope secrets |
| 17 | Always post runs without workspace | agent none or agent teardown | Run workspace steps on agent |
| 18 | Agent disconnect during retry | Infrastructure failure and resume semantics | Reprovision isolated agent |
| 19 | Flaky test retries conceal instability | Retries on assertion failures | Report flake and fail gate |
| 20 | Rollback trigger loops | Automated recovery causes repeated changes | Require bounded/manual escalation |

## 14. Eight SRE runbooks

### RB-01 Failure classification

**Procedure:** Inspect build/stage result, Jenkinsfile revision, stack trace and test reports; distinguish application vs infrastructure.

**Exit criteria:** correct result classification, bounded recovery, no duplicated side effects, preserved interruption and redacted evidence.

### RB-02 Timeout response

**Procedure:** Check queue/provisioning versus runtime, external process cleanup and approved timeout budget; stop orphaned work.

**Exit criteria:** correct result classification, bounded recovery, no duplicated side effects, preserved interruption and redacted evidence.

### RB-03 Retry storm

**Procedure:** Identify attempt counts and non-idempotent operations, disable retry, reconcile side effects and restore bounded policy.

**Exit criteria:** correct result classification, bounded recovery, no duplicated side effects, preserved interruption and redacted evidence.

### RB-04 Post-action outage

**Procedure:** Inspect success/failure/always scopes, notification plugin, credentials and stage context; protect primary result.

**Exit criteria:** correct result classification, bounded recovery, no duplicated side effects, preserved interruption and redacted evidence.

### RB-05 Interrupted or aborted build

**Procedure:** Trace operator abort and interruption propagation; prevent accidental success or repeat side effects.

**Exit criteria:** correct result classification, bounded recovery, no duplicated side effects, preserved interruption and redacted evidence.

### RB-06 UNSTABLE acceptance

**Procedure:** Review JUnit failures, quality gate, exceptions and release policy; require approved disposition.

**Exit criteria:** correct result classification, bounded recovery, no duplicated side effects, preserved interruption and redacted evidence.

### RB-07 Secret in error log

**Procedure:** Contain console access, revoke/rotate secrets, remove unsafe interpolation and preserve redacted evidence.

**Exit criteria:** correct result classification, bounded recovery, no duplicated side effects, preserved interruption and redacted evidence.

### RB-08 Change and rollback

**Procedure:** Restore reviewed Jenkinsfile, validate failure/timeout paths in staging and record owner acceptance.

**Exit criteria:** correct result classification, bounded recovery, no duplicated side effects, preserved interruption and redacted evidence.

## 15. Acceptance gates

| Gate | Requirement |
|---|---|
| G1 | Controller built-in executors zero |
| G2 | Post condition semantics documented |
| G3 | SUCCESS/FAILURE/UNSTABLE results tested |
| G4 | Retry succeeds after one simulated transient error |
| G5 | Timeout interruption/ABORTED result investigated |
| G6 | catchError result and interruption policy explained |
| G7 | Retry idempotency and attempt budget documented |
| G8 | No secrets or unapproved external notifications |
| G9 | Three incident diagnoses and rollback |
| G10 | Redacted evidence and cleanup complete |

## 16. Assessment — 100 points

| Domain | Points |
|---|---:|
| Post conditions and result semantics | 25 |
| Error and catchError handling | 20 |
| Timeout and interruption | 20 |
| Retry and idempotency | 15 |
| SRE incidents and monitoring | 10 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ with all security-critical gates. Controller-only tests are not proof of production integration reliability.

## 17. Cleanup

```bash
docker stop jenkins-ch023
docker rm jenkins-ch023
# Destructive only if exclusively lab-owned:
docker volume rm jenkins-ch023-home
```

**Next:** Chapter 024 — Scripted Pipeline Groovy, Node, Stage and Flow Control.
