# Chapter 021 — Hands-On Lab: Declarative Pipeline Syntax, Stages, Steps and Directives

**Parent:** [Chapter 021](../021-declarative-pipeline-syntax-stages-steps-directives.md)

## Goal and safety

Learn and validate Declarative Pipeline structure on a disposable localhost Jenkins controller. Controller built-in executors must be zero. No external secrets, real deployments or controller shell execution.

## Exercise 01 — Docker prerequisites

```bash
docker version
docker ps
```

**Operator action:** Capture redacted evidence; distinguish observed results from design-only checks.

**Pass:** Docker available. **Rollback:** revert lab-owned changes only.

## Exercise 02 — Create dedicated home

```bash
docker volume create jenkins-ch021-home
```

**Operator action:** Capture redacted evidence; distinguish observed results from design-only checks.

**Pass:** Volume exists. **Rollback:** revert lab-owned changes only.

## Exercise 03 — Start localhost controller

```bash
docker run -d --name jenkins-ch021 --restart=no -p 127.0.0.1:8099:8080 --memory 4g --cpus 2 --mount source=jenkins-ch021-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator action:** Capture redacted evidence; distinguish observed results from design-only checks.

**Pass:** Controller starts. **Rollback:** revert lab-owned changes only.

## Exercise 04 — Inspect startup

```bash
docker logs --tail 60 jenkins-ch021
```

**Operator action:** Capture redacted evidence; distinguish observed results from design-only checks.

**Pass:** No fatal errors. **Rollback:** revert lab-owned changes only.

## Exercise 05 — Verify loopback listener

```bash
docker port jenkins-ch021
```

**Operator action:** Capture redacted evidence; distinguish observed results from design-only checks.

**Pass:** 127.0.0.1 only. **Rollback:** revert lab-owned changes only.

## Exercise 06 — Bootstrap named admin

```bash
docker exec jenkins-ch021 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator action:** Unlock privately at http://127.0.0.1:8099 and create a named admin; never record the password.

**Pass:** Private unlock only. **Rollback:** revert lab-owned changes only.

## Exercise 07 — Disable controller executors

```bash
docker ps --filter name=jenkins-ch021
```

**Operator action:** Manage Jenkins → Nodes → Built-In Node → set executors = 0.

**Pass:** Built-in executors zero. **Rollback:** revert lab-owned changes only.

## Exercise 08 — Inspect runtime image

```bash
docker inspect jenkins-ch021 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator action:** Capture redacted evidence; distinguish observed results from design-only checks.

**Pass:** Runtime recorded. **Rollback:** revert lab-owned changes only.

## Exercise 09 — Inspect home mount

```bash
docker inspect jenkins-ch021 --format '{{json .Mounts}}'
```

**Operator action:** Capture redacted evidence; distinguish observed results from design-only checks.

**Pass:** Dedicated home attached. **Rollback:** revert lab-owned changes only.

## Exercise 10 — Inspect disk and inodes

```bash
docker exec jenkins-ch021 sh -c 'df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Operator action:** Capture redacted evidence; distinguish observed results from design-only checks.

**Pass:** Storage baseline. **Rollback:** revert lab-owned changes only.

## Exercise 11 — Create Declarative job

```bash
docker logs --tail 15 jenkins-ch021
```

**Operator action:** New Item → Pipeline → ch021-declarative-smoke; paste the Jenkinsfile below.

**Pass:** Job saved. **Rollback:** revert lab-owned changes only.

## Exercise 12 — Run dev success

```bash
docker stats --no-stream jenkins-ch021
```

**Operator action:** Run TARGET=dev, FAIL_DEMO=false; confirm Conditional staging skipped.

**Pass:** SUCCESS, conditional stage skipped. **Rollback:** revert lab-owned changes only.

## Exercise 13 — Run staging success

```bash
docker logs --tail 25 jenkins-ch021
```

**Operator action:** Run TARGET=staging, FAIL_DEMO=false; confirm conditional stage executes.

**Pass:** SUCCESS, conditional stage executed. **Rollback:** revert lab-owned changes only.

## Exercise 14 — Run intentional failure

```bash
docker logs --tail 25 jenkins-ch021
```

**Operator action:** Run FAIL_DEMO=true; confirm expected FAILURE and post failure output.

**Pass:** FAILURE and post failure. **Rollback:** revert lab-owned changes only.

## Exercise 15 — Review stage outcomes

```bash
docker inspect jenkins-ch021 --format '{{.State.Status}}'
```

**Operator action:** Inspect build numbers, timestamps, stage outcomes and redacted logs.

**Pass:** Stages classified. **Rollback:** revert lab-owned changes only.

## Exercise 16 — Review environment scope

```bash
docker logs --tail 20 jenkins-ch021
```

**Operator action:** Confirm APP_NAME is visible and contains no secret.

**Pass:** APP_NAME non-secret output. **Rollback:** revert lab-owned changes only.

## Exercise 17 — Review agent-backed design

```bash
docker stats --no-stream jenkins-ch021
```

**Operator action:** Review the agent-backed example in the parent chapter; do not execute without approved lab-linux agent.

**Pass:** Isolated label required. **Rollback:** revert lab-owned changes only.

## Exercise 18 — Review secrets and SCM

```bash
docker inspect jenkins-ch021 --format '{{.Config.Image}}'
```

**Operator action:** Document protected SCM Jenkinsfile and least-privilege credentials.

**Pass:** Protected Git and credential policy. **Rollback:** revert lab-owned changes only.

## Exercise 19 — Incident tabletop

```bash
docker logs --tail 40 jenkins-ch021
```

**Operator action:** Tabletop: syntax parse failure, no matching agent and skipped staging gate.

**Pass:** Three parse/queue/gate diagnoses. **Rollback:** revert lab-owned changes only.

## Exercise 20 — Cleanup and score

```bash
docker stop jenkins-ch021
docker rm jenkins-ch021
```

**Operator action:** Remove the dedicated volume only after confirming exclusive lab ownership.

**Pass:** Lab controller removed. **Rollback:** revert lab-owned changes only.

## Runnable no-agent Declarative Pipeline

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
            error('Invalid target')
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
            error('Intentional failure for lab')
          }
        }
        echo 'Success path'
      }
    }
  }
  post {
    success { echo 'SUCCESS' }
    failure { echo 'FAILURE' }
    always { echo 'Capture redacted evidence' }
  }
}
```

## Declarative syntax worksheet

| Construct | Expected use | Validation |
|---|---|---|
| pipeline | Single root | Parses |
| agent none | Controller-only orchestration | No workspace steps |
| options | Timestamp/retention/concurrency | Visible behavior |
| parameters | Choice and boolean | Valid inputs |
| environment | Non-secret scope | APP_NAME output |
| stages/stage/steps | Ordered phases | Stage visualization |
| when | Conditional staging | Skip/execute |
| script | Limited Groovy logic | Validation branch |
| post | Result-specific actions | SUCCESS/FAILURE |

## Incident drills

| Failure | Investigation | Safe recovery |
|---|---|---|
| Missing closing brace | Parser location | Revert/fix Jenkinsfile |
| Shell under agent none | Missing node/workspace | Use isolated stage agent |
| Unexpected skipped stage | when expression/params | Validate gate |
| Secret in console | GString and logs | Revoke/rotate and fix |
| Build queue blocked | Label and agent state | Restore approved agent |
| Post action fails | Post logs and plugin | Preserve root cause |

## Assessment — 100 points

| Domain | Points |
|---|---:|
| Syntax/directives | 25 |
| Parameters/conditions/environment | 20 |
| Agent isolation | 20 |
| Post/results/errors | 15 |
| Security/troubleshooting | 10 |
| Evidence/cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ with all critical security gates.

## Evidence handoff

```text
Operator/date:
Controller localhost URL:
Built-in executors:
JENKINS_HOME:
Job name:
Dev SUCCESS build and skipped stage:
Staging SUCCESS build and executed stage:
Intentional FAILURE build:
Post-condition output:
Agent-backed design review:
SCM/credentials policy:
Three incident analyses:
Cleanup proof:
Score/reviewer:
```

**Next:** Chapter 022 — Declarative Pipeline Agents, Environment, Parameters and Conditional Execution.
