# Chapter 022 — Hands-On Lab: Declarative Agents, Environment, Parameters and Conditions

**Parent:** [Chapter 022](../022-declarative-pipeline-agents-environment-parameters-conditional-execution.md)

## Safety and prerequisites

Disposable localhost Jenkins controller only. No controller executors, external credentials or real deployments. Agent-backed shell and credential examples are approved-staging only; mark unexecuted exercises design-only.

## Exercise 01 — Check Docker prerequisites

```bash
docker version
docker ps
```

**Operator action:** Record observed or design-only evidence; do not claim external integrations were tested.

**Pass:** Docker ready. **Rollback:** revert lab-only configuration.

## Exercise 02 — Create dedicated volume

```bash
docker volume create jenkins-ch022-home
```

**Operator action:** Record observed or design-only evidence; do not claim external integrations were tested.

**Pass:** Volume created. **Rollback:** revert lab-only configuration.

## Exercise 03 — Start private controller

```bash
docker run -d --name jenkins-ch022 --restart=no -p 127.0.0.1:8100:8080 --memory 4g --cpus 2 --mount source=jenkins-ch022-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator action:** Record observed or design-only evidence; do not claim external integrations were tested.

**Pass:** Controller started. **Rollback:** revert lab-only configuration.

## Exercise 04 — Inspect startup logs

```bash
docker logs --tail 60 jenkins-ch022
```

**Operator action:** Record observed or design-only evidence; do not claim external integrations were tested.

**Pass:** No fatal errors. **Rollback:** revert lab-only configuration.

## Exercise 05 — Verify port isolation

```bash
docker port jenkins-ch022
```

**Operator action:** Record observed or design-only evidence; do not claim external integrations were tested.

**Pass:** Loopback binding. **Rollback:** revert lab-only configuration.

## Exercise 06 — Bootstrap named admin

```bash
docker exec jenkins-ch022 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator action:** Unlock privately at http://127.0.0.1:8100 and create named admin; do not capture unlock password.

**Pass:** Private unlock. **Rollback:** revert lab-only configuration.

## Exercise 07 — Set built-in executors zero

```bash
docker ps --filter name=jenkins-ch022
```

**Operator action:** Manage Jenkins → Nodes → Built-In Node → set executors = 0.

**Pass:** Controller executors zero. **Rollback:** revert lab-only configuration.

## Exercise 08 — Inspect runtime identity

```bash
docker inspect jenkins-ch022 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator action:** Record observed or design-only evidence; do not claim external integrations were tested.

**Pass:** Runtime recorded. **Rollback:** revert lab-only configuration.

## Exercise 09 — Inspect home mount

```bash
docker inspect jenkins-ch022 --format '{{json .Mounts}}'
```

**Operator action:** Record observed or design-only evidence; do not claim external integrations were tested.

**Pass:** Dedicated volume. **Rollback:** revert lab-only configuration.

## Exercise 10 — Inspect storage baseline

```bash
docker exec jenkins-ch022 sh -c 'df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Operator action:** Record observed or design-only evidence; do not claim external integrations were tested.

**Pass:** Capacity baseline. **Rollback:** revert lab-only configuration.

## Exercise 11 — Create parameterized Pipeline

```bash
docker logs --tail 15 jenkins-ch022
```

**Operator action:** Create Pipeline ch022-agents-parameters using the Jenkinsfile below.

**Pass:** Job created. **Rollback:** revert lab-only configuration.

## Exercise 12 — Run dev target

```bash
docker stats --no-stream jenkins-ch022
```

**Operator action:** Run TARGET=dev, RELEASE_TAG=v1.0.0 and confirm staging skipped.

**Pass:** Staging skipped. **Rollback:** revert lab-only configuration.

## Exercise 13 — Run staging target

```bash
docker logs --tail 25 jenkins-ch022
```

**Operator action:** Run TARGET=staging, RELEASE_TAG=v1.0.0 and confirm staging executes.

**Pass:** Staging executed. **Rollback:** revert lab-only configuration.

## Exercise 14 — Verify environment scope

```bash
docker inspect jenkins-ch022 --format '{{.State.Status}}'
```

**Operator action:** Check stage REGION=us-west-2 and final global REGION=us-east-1.

**Pass:** Stage override only. **Rollback:** revert lab-only configuration.

## Exercise 15 — Test invalid release tag

```bash
docker logs --tail 25 jenkins-ch022
```

**Operator action:** Run RELEASE_TAG=not-a-version and confirm validation FAILURE.

**Pass:** FAILURE from validation. **Rollback:** revert lab-only configuration.

## Exercise 16 — Review beforeAgent true

```bash
docker ps --filter name=jenkins-ch022
```

**Operator action:** Explain why beforeAgent true avoids agent allocation for skipped stage.

**Pass:** No unnecessary stage allocation. **Rollback:** revert lab-only configuration.

## Exercise 17 — Review isolated agent example

```bash
docker stats --no-stream jenkins-ch022
```

**Operator action:** Review approved lab-linux stage example; no shell on controller.

**Pass:** Trusted label and workspace policy. **Rollback:** revert lab-only configuration.

## Exercise 18 — Review credential binding

```bash
docker inspect jenkins-ch022 --format '{{.Config.Image}}'
```

**Operator action:** Review folder-scoped credential binding; do not create or print real token.

**Pass:** No token exposure. **Rollback:** revert lab-only configuration.

## Exercise 19 — Incident tabletop

```bash
docker logs --tail 40 jenkins-ch022
```

**Operator action:** Tabletop: missing agent, invalid environment gate and secret leak.

**Pass:** Three agent/gate/secret cases. **Rollback:** revert lab-only configuration.

## Exercise 20 — Cleanup and score

```bash
docker stop jenkins-ch022
docker rm jenkins-ch022
```

**Operator action:** Remove only lab-owned resources and verify volume ownership before deletion.

**Pass:** Controller removed. **Rollback:** revert lab-only configuration.

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
    choice(name: 'TARGET', choices: ['dev', 'staging'])
    booleanParam(name: 'DRY_RUN', defaultValue: true)
    string(name: 'RELEASE_TAG', defaultValue: 'v1.0.0')
  }
  environment {
    APP_NAME = 'pipeline-demo'
    REGION = 'us-east-1'
  }
  stages {
    stage('Validate') {
      steps {
        script {
          if (!(params.TARGET in ['dev', 'staging'])) {
            error('Invalid target')
          }
          if (!(params.RELEASE_TAG ==~ /^v[0-9]+\.[0-9]+\.[0-9]+$/)) {
            error('Invalid release tag')
          }
        }
        echo "App=${env.APP_NAME}; target=${params.TARGET}; dryRun=${params.DRY_RUN}"
      }
    }
    stage('Staging only') {
      when {
        beforeAgent true
        expression { params.TARGET == 'staging' }
      }
      environment { REGION = 'us-west-2' }
      steps { echo "Stage region=${env.REGION}" }
    }
    stage('Global scope') {
      steps { echo "Global region=${env.REGION}" }
    }
  }
  post {
    success { echo 'SUCCESS' }
    failure { echo 'FAILURE' }
    always { echo 'No deployment executed' }
  }
}
```

## Agent and environment matrix

| Test | Expected result |
|---|---|
| TARGET=dev | Staging stage skipped |
| TARGET=staging | Staging stage executes |
| RELEASE_TAG=v1.0.0 | Validation passes |
| RELEASE_TAG=bad | Validation fails |
| Stage REGION | us-west-2 |
| Final REGION | us-east-1 |
| No lab-linux agent | Agent-backed example queues if run |
| Credential binding | Staging-only, token never printed |

## Incident drills

| Symptom | Evidence | Recovery |
|---|---|---|
| Missing agent | Queue reason and labels | Restore approved pool |
| Wrong environment | Stage/global scope | Correct Jenkinsfile |
| Invalid release tag | Validation error | Reject input |
| Secret exposed | Redacted log and audit | Revoke/rotate |
| Skipped stage unexpected | when and beforeAgent | Fix gate |
| Untrusted PR privileged | SCM trust and RBAC | Quarantine and isolate |

## Assessment — 100 points

| Domain | Points |
|---|---:|
| Agent selection/isolation | 25 |
| Parameter validation | 20 |
| Environment/credentials | 20 |
| Conditional execution | 15 |
| Incident response | 10 |
| Evidence/cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ and all critical security gates.

## Evidence handoff

```text
Operator/date:
Controller URL:
Built-in executors:
JENKINS_HOME volume:
Dev build/skipped stage:
Staging build/executed stage:
Environment scope output:
Invalid tag failure:
beforeAgent explanation:
Agent trust policy:
Credential binding design:
Three incident diagnoses:
Cleanup proof:
Score/reviewer:
```

**Next:** Chapter 023 — Declarative Pipeline Post Conditions, Error Handling, Timeouts and Retries.
