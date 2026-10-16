# Chapter 019 — Hands-On Lab: Build History, Logs, Notifications and Lifecycle

**Parent:** [Chapter 019](../019-jenkins-build-history-logs-notifications-job-lifecycle-management.md)

## Safety

Disposable localhost controller only. Notification destinations are design-only unless explicitly approved. Never include secrets in console or evidence; keep built-in executors zero.

## Exercise 01 — Docker baseline

```bash
docker version
docker ps
```

**Operator action:** Record observed or design-only evidence and operational implications.

**Pass:** Engine ready. **Rollback:** revert lab-owned changes only.

## Exercise 02 — Create lab home

```bash
docker volume create jenkins-ch019-home
```

**Operator action:** Record observed or design-only evidence and operational implications.

**Pass:** Volume exists. **Rollback:** revert lab-owned changes only.

## Exercise 03 — Start localhost controller

```bash
docker run -d --name jenkins-ch019 --restart=no -p 127.0.0.1:8097:8080 --memory 4g --cpus 2 --mount source=jenkins-ch019-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator action:** Record observed or design-only evidence and operational implications.

**Pass:** Controller running. **Rollback:** revert lab-owned changes only.

## Exercise 04 — Inspect startup logs

```bash
docker logs --tail 60 jenkins-ch019
```

**Operator action:** Record observed or design-only evidence and operational implications.

**Pass:** Startup healthy. **Rollback:** revert lab-owned changes only.

## Exercise 05 — Check port exposure

```bash
docker port jenkins-ch019
```

**Operator action:** Record observed or design-only evidence and operational implications.

**Pass:** Loopback-only. **Rollback:** revert lab-owned changes only.

## Exercise 06 — Bootstrap named admin

```bash
docker exec jenkins-ch019 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator action:** Unlock privately at http://127.0.0.1:8097 and create a named admin; do not record the unlock password.

**Pass:** Secret used privately. **Rollback:** revert lab-owned changes only.

## Exercise 07 — Set controller executors zero

```bash
docker ps --filter name=jenkins-ch019
```

**Operator action:** Manage Jenkins → Nodes → Built-In Node → executors = 0.

**Pass:** Zero built-in executors. **Rollback:** revert lab-owned changes only.

## Exercise 08 — Inspect runtime image

```bash
docker inspect jenkins-ch019 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator action:** Record observed or design-only evidence and operational implications.

**Pass:** Runtime recorded. **Rollback:** revert lab-owned changes only.

## Exercise 09 — Inspect home mount

```bash
docker inspect jenkins-ch019 --format '{{json .Mounts}}'
```

**Operator action:** Record observed or design-only evidence and operational implications.

**Pass:** Persistent state verified. **Rollback:** revert lab-owned changes only.

## Exercise 10 — Inspect disk/inodes

```bash
docker exec jenkins-ch019 sh -c 'df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Operator action:** Record observed or design-only evidence and operational implications.

**Pass:** Storage baseline. **Rollback:** revert lab-owned changes only.

## Exercise 11 — Create Pipeline with results

```bash
docker logs --tail 15 jenkins-ch019
```

**Operator action:** Create Pipeline ch019-build-history with the Jenkinsfile below.

**Pass:** Job saved. **Rollback:** revert lab-owned changes only.

## Exercise 12 — Run successful build

```bash
docker stats --no-stream jenkins-ch019
```

**Operator action:** Run with FAIL_DEMO=false and capture build result.

**Pass:** SUCCESS recorded. **Rollback:** revert lab-owned changes only.

## Exercise 13 — Run intentional failure

```bash
docker logs --tail 25 jenkins-ch019
```

**Operator action:** Run with FAIL_DEMO=true and verify expected FAILURE.

**Pass:** FAILURE recorded. **Rollback:** revert lab-owned changes only.

## Exercise 14 — Review build history

```bash
docker inspect jenkins-ch019 --format '{{.State.Status}}'
```

**Operator action:** Compare build numbers, causes, timestamps and duration.

**Pass:** Results and timestamps visible. **Rollback:** revert lab-owned changes only.

## Exercise 15 — Review console logs

```bash
docker logs --tail 30 jenkins-ch019
```

**Operator action:** Inspect console output and verify no sensitive data.

**Pass:** No secrets and correct error context. **Rollback:** revert lab-owned changes only.

## Exercise 16 — Review notification policy

```bash
docker ps --filter name=jenkins-ch019
```

**Operator action:** Design failure/recovery notifications and rate limiting; do not send externally.

**Pass:** Destinations, severity and dedupe planned. **Rollback:** revert lab-owned changes only.

## Exercise 17 — Review build discarder

```bash
docker exec jenkins-ch019 sh -c 'df -h /var/jenkins_home'
```

**Operator action:** Review numToKeepStr=10 and legal-hold implications.

**Pass:** Retention policy documented. **Rollback:** revert lab-owned changes only.

## Exercise 18 — Review disable and restore

```bash
docker inspect jenkins-ch019 --format '{{.Config.Image}}'
```

**Operator action:** Document disable → archive → approved delete, without deleting shared jobs.

**Pass:** Job lifecycle safe sequence. **Rollback:** revert lab-owned changes only.

## Exercise 19 — Incident tabletop

```bash
docker logs --tail 40 jenkins-ch019
```

**Operator action:** Tabletop: lost history, leaked token and notification storm.

**Pass:** Three failures diagnosed. **Rollback:** revert lab-owned changes only.

## Exercise 20 — Cleanup and scoring

```bash
docker stop jenkins-ch019
docker rm jenkins-ch019
```

**Operator action:** Remove dedicated volume only after exclusive ownership check.

**Pass:** Controller removed. **Rollback:** revert lab-owned changes only.

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
    booleanParam(name: 'FAIL_DEMO', defaultValue: false)
  }
  stages {
    stage('Observe') {
      steps {
        echo "Build=${env.BUILD_NUMBER} FAIL_DEMO=${params.FAIL_DEMO}"
      }
    }
    stage('Result') {
      steps {
        script {
          if (params.FAIL_DEMO) {
            error('Intentional lab failure')
          }
        }
        echo 'Lab success'
      }
    }
  }
  post {
    success { echo 'SUCCESS recorded' }
    failure { echo 'FAILURE recorded' }
    always { echo 'Check build history' }
  }
}
```

## Incident decision matrix

| Failure | Evidence | Recovery |
|---|---|---|
| Build history missing | Discarder, backup and job migration | Restore supported records |
| Token in console | Restricted log and audit | Revoke/rotate, contain |
| Notification storm | Repeated result transitions | Dedupe/rate-limit |
| Disk pressure | Build/artifact count, df -h | Reviewed retention |
| Job disabled | Config history and RBAC | Restore approved state |
| Wrong result classification | Post conditions, test reports | Correct policy |

## Assessment — 100 points

| Domain | Points |
|---|---:|
| Build history/results | 25 |
| Logs/security | 20 |
| Notifications | 20 |
| Retention/lifecycle | 15 |
| Incident response | 10 |
| Evidence/cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ with no security-critical failure.

## Evidence template

```text
Operator/date:
Controller localhost URL:
Built-in executors:
JENKINS_HOME volume:
SUCCESS build number:
FAILURE build number:
Console logs redacted:
UNSTABLE/ABORTED interpretation:
Notification design and owner:
Build/artifact retention:
Job disable/archive/delete policy:
Three incident diagnoses:
Cleanup proof:
Score/reviewer:
```

**Next:** Chapter 020 — Jenkins Jobs and Pipeline Fundamentals Production Operations Capstone.
