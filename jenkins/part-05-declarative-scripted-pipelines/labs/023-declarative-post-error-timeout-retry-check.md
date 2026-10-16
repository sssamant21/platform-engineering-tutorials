# Chapter 023 — Hands-On Lab: Post Conditions, Error Handling, Timeouts and Retries

**Parent:** [Chapter 023](../023-declarative-pipeline-post-conditions-error-handling-timeouts-retries.md)

## Safety

Disposable localhost Jenkins controller only. All executable Pipeline steps are controller-only orchestration, with no shell, credentials or deployments. Built-in executors remain zero.

## Exercise 01 — Docker prerequisites

```bash
docker version
docker ps
```

**Operator action:** Record redacted evidence; distinguish observed from design-only checks.

**Pass:** Docker available. **Rollback:** revert lab-owned settings only.

## Exercise 02 — Create lab volume

```bash
docker volume create jenkins-ch023-home
```

**Operator action:** Record redacted evidence; distinguish observed from design-only checks.

**Pass:** Dedicated volume. **Rollback:** revert lab-owned settings only.

## Exercise 03 — Start private controller

```bash
docker run -d --name jenkins-ch023 --restart=no -p 127.0.0.1:8101:8080 --memory 4g --cpus 2 --mount source=jenkins-ch023-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator action:** Record redacted evidence; distinguish observed from design-only checks.

**Pass:** Controller running. **Rollback:** revert lab-owned settings only.

## Exercise 04 — Inspect startup

```bash
docker logs --tail 60 jenkins-ch023
```

**Operator action:** Record redacted evidence; distinguish observed from design-only checks.

**Pass:** No fatal startup errors. **Rollback:** revert lab-owned settings only.

## Exercise 05 — Verify loopback listener

```bash
docker port jenkins-ch023
```

**Operator action:** Record redacted evidence; distinguish observed from design-only checks.

**Pass:** Localhost only. **Rollback:** revert lab-owned settings only.

## Exercise 06 — Bootstrap admin privately

```bash
docker exec jenkins-ch023 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator action:** Unlock privately at http://127.0.0.1:8101; create named admin; never record unlock password.

**Pass:** Secret not captured. **Rollback:** revert lab-owned settings only.

## Exercise 07 — Set controller executors zero

```bash
docker ps --filter name=jenkins-ch023
```

**Operator action:** Manage Jenkins → Nodes → Built-In Node → executors = 0.

**Pass:** Built-in executors zero. **Rollback:** revert lab-owned settings only.

## Exercise 08 — Inspect runtime identity

```bash
docker inspect jenkins-ch023 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator action:** Record redacted evidence; distinguish observed from design-only checks.

**Pass:** Runtime recorded. **Rollback:** revert lab-owned settings only.

## Exercise 09 — Inspect home mount

```bash
docker inspect jenkins-ch023 --format '{{json .Mounts}}'
```

**Operator action:** Record redacted evidence; distinguish observed from design-only checks.

**Pass:** Dedicated state. **Rollback:** revert lab-owned settings only.

## Exercise 10 — Inspect disk/inodes

```bash
docker exec jenkins-ch023 sh -c 'df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Operator action:** Record redacted evidence; distinguish observed from design-only checks.

**Pass:** Storage baseline. **Rollback:** revert lab-owned settings only.

## Exercise 11 — Create Pipeline job

```bash
docker logs --tail 15 jenkins-ch023
```

**Operator action:** Create Pipeline ch023-post-retry with the Jenkinsfile below.

**Pass:** Job saved. **Rollback:** revert lab-owned settings only.

## Exercise 12 — Run success mode

```bash
docker stats --no-stream jenkins-ch023
```

**Operator action:** Run MODE=success; capture SUCCESS and POST success.

**Pass:** SUCCESS and post success. **Rollback:** revert lab-owned settings only.

## Exercise 13 — Run failure mode

```bash
docker logs --tail 25 jenkins-ch023
```

**Operator action:** Run MODE=failure; capture FAILURE and POST failure.

**Pass:** FAILURE and post failure. **Rollback:** revert lab-owned settings only.

## Exercise 14 — Run unstable mode

```bash
docker inspect jenkins-ch023 --format '{{.State.Status}}'
```

**Operator action:** Run MODE=unstable; capture UNSTABLE and POST unstable.

**Pass:** UNSTABLE and post unstable. **Rollback:** revert lab-owned settings only.

## Exercise 15 — Run retry mode

```bash
docker logs --tail 25 jenkins-ch023
```

**Operator action:** Run MODE=retry; capture first failure, second attempt and SUCCESS.

**Pass:** Two attempts and SUCCESS. **Rollback:** revert lab-owned settings only.

## Exercise 16 — Run timeout mode

```bash
docker stats --no-stream jenkins-ch023
```

**Operator action:** Run MODE=timeout; inspect timeout interruption and actual build result (normally ABORTED).

**Pass:** Interruption and result captured. **Rollback:** revert lab-owned settings only.

## Exercise 17 — Review catchError policy

```bash
docker logs --tail 20 jenkins-ch023
```

**Operator action:** Explain catchInterruptions: false and when to rethrow interruption.

**Pass:** Interruption not swallowed. **Rollback:** revert lab-owned settings only.

## Exercise 18 — Review alert/retry safety

```bash
docker inspect jenkins-ch023 --format '{{.Config.Image}}'
```

**Operator action:** Document bounded retry, idempotency, alert dedupe and approval policy.

**Pass:** Idempotency and alert owner. **Rollback:** revert lab-owned settings only.

## Exercise 19 — Incident tabletop

```bash
docker logs --tail 40 jenkins-ch023
```

**Operator action:** Tabletop: retry storm, masked root failure and leaked notification token.

**Pass:** Three failure diagnoses. **Rollback:** revert lab-owned settings only.

## Exercise 20 — Cleanup and scoring

```bash
docker stop jenkins-ch023
docker rm jenkins-ch023
```

**Operator action:** Delete volume only after verifying exclusive lab ownership.

**Pass:** Controller removed. **Rollback:** revert lab-owned settings only.

## Runnable no-agent Jenkinsfile

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
    stage('Simulate') {
      steps {
        script {
          switch (params.MODE) {
            case 'failure':
              error('Intentional failure')
              break
            case 'unstable':
              catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                error('Intentional unstable gate')
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
    always { echo 'POST always' }
  }
}
```

## Expected results matrix

| MODE | Expected | Evidence |
|---|---|---|
| success | SUCCESS | post success + always |
| failure | FAILURE | post failure + always |
| unstable | UNSTABLE | catchError + post unstable |
| retry | SUCCESS | two attempts + post success |
| timeout | Usually ABORTED | timeout interruption + post aborted |

Do not assume timeouts always map to FAILURE. Preserve interruption in error handling.

## Incident tabletop

| Incident | Evidence | Recovery |
|---|---|---|
| Duplicate deployment after retry | Side-effect audit | Stop and add idempotency |
| Cleanup hides original failure | Post logs | Guard cleanup and preserve root |
| Timeout orphaned external process | Process/service logs | Terminate and reconcile |
| Notification storm | Delivery history | Deduplicate and rate-limit |
| Aborted build retried | Interrupt stack | Rethrow interruption |
| UNSTABLE promoted | Test reports and gate | Enforce release policy |

## Assessment — 100 points

| Area | Points |
|---|---:|
| Post and results | 25 |
| Error/catchError | 20 |
| Timeout/interruption | 20 |
| Retry/idempotency | 15 |
| SRE troubleshooting | 10 |
| Evidence/cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ with all security-critical gates.

## Evidence handoff

```text
Operator/date:
Controller localhost URL:
Built-in executors:
SUCCESS build:
FAILURE build:
UNSTABLE build:
Retry attempts/build:
Timeout result:
Post outputs:
Interruption policy:
Idempotency and alerting policy:
Three incident diagnoses:
Cleanup proof:
Score/reviewer:
```

**Next:** Chapter 024 — Scripted Pipeline Groovy, Node, Stage and Flow Control.
