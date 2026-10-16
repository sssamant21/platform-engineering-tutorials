# Chapter 020 — Hands-On Lab: Jobs and Pipeline Fundamentals Operations Capstone

**Parent:** [Chapter 020](../020-jenkins-jobs-pipeline-fundamentals-production-operations-capstone.md)

## Goal and safety

Validate integrated job governance, Pipeline results, parameter controls and operations on a disposable localhost controller. SCM webhooks, agents, artifacts, JUnit and external notifications remain design/staging-only unless independently executed and approved. Never enable built-in controller executors.

## Exercise 01 — Check Docker host

```bash
docker version
docker ps
```

**Operator action:** Capture redacted evidence and distinguish executed from design-only acceptance.

**Pass:** Docker available. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 02 — Create lab volume

```bash
docker volume create jenkins-ch020-home
```

**Operator action:** Capture redacted evidence and distinguish executed from design-only acceptance.

**Pass:** Volume exists. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 03 — Start controller privately

```bash
docker run -d --name jenkins-ch020 --restart=no -p 127.0.0.1:8098:8080 --memory 4g --cpus 2 --mount source=jenkins-ch020-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator action:** Capture redacted evidence and distinguish executed from design-only acceptance.

**Pass:** Controller starts. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 04 — Inspect startup logs

```bash
docker logs --tail 60 jenkins-ch020
```

**Operator action:** Capture redacted evidence and distinguish executed from design-only acceptance.

**Pass:** No fatal startup errors. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 05 — Check listener

```bash
docker port jenkins-ch020
```

**Operator action:** Capture redacted evidence and distinguish executed from design-only acceptance.

**Pass:** Loopback-only. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 06 — Bootstrap named admin

```bash
docker exec jenkins-ch020 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator action:** Unlock at http://127.0.0.1:8098 privately; create named admin and do not record password.

**Pass:** Private unlock; no token captured. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 07 — Set controller executors zero

```bash
docker ps --filter name=jenkins-ch020
```

**Operator action:** Set Manage Jenkins → Nodes → Built-In Node → executors = 0.

**Pass:** Zero built-in executors. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 08 — Inspect image/user

```bash
docker inspect jenkins-ch020 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator action:** Capture redacted evidence and distinguish executed from design-only acceptance.

**Pass:** Runtime recorded. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 09 — Inspect home persistence

```bash
docker inspect jenkins-ch020 --format '{{json .Mounts}}'
```

**Operator action:** Capture redacted evidence and distinguish executed from design-only acceptance.

**Pass:** Volume correct. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 10 — Inspect disk/inodes

```bash
docker exec jenkins-ch020 sh -c 'df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Operator action:** Capture redacted evidence and distinguish executed from design-only acceptance.

**Pass:** Storage baseline. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 11 — Create integrated Pipeline

```bash
docker logs --tail 15 jenkins-ch020
```

**Operator action:** Create Pipeline ch020-operations-capstone using the Jenkinsfile below.

**Pass:** Pipeline definition saved. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 12 — Run approved dry-run

```bash
docker stats --no-stream jenkins-ch020
```

**Operator action:** Run TARGET=dev, DRY_RUN=true, FAIL_DEMO=false; capture SUCCESS.

**Pass:** SUCCESS with safe parameters. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 13 — Run intentional failure

```bash
docker logs --tail 25 jenkins-ch020
```

**Operator action:** Run FAIL_DEMO=true; capture expected FAILURE.

**Pass:** FAILURE and post result recorded. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 14 — Review build history

```bash
docker inspect jenkins-ch020 --format '{{.State.Status}}'
```

**Operator action:** Compare build number, result, timestamps and redacted logs.

**Pass:** Two result states. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 15 — Review Freestyle migration

```bash
docker logs --tail 15 jenkins-ch020
```

**Operator action:** Inventory Freestyle-to-Pipeline migration: scripts, SCM, triggers, credentials, agents, outputs.

**Pass:** Migration matrix completed. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 16 — Review triggers and approval

```bash
docker port jenkins-ch020
```

**Operator action:** Document signed webhook, hashed cron, timezone, manual approvals and dedupe; no live triggers.

**Pass:** Signed webhook/cron policy documented. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 17 — Review agent and artifact design

```bash
docker stats --no-stream jenkins-ch020
```

**Operator action:** Review agent-only build, JUnit, SHA-256 and artifact policy; mark design-only unless staged.

**Pass:** Agent workspace and artifact gates documented. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 18 — Review notifications/retention

```bash
docker exec jenkins-ch020 sh -c 'df -h /var/jenkins_home'
```

**Operator action:** Document notification ownership, build discarder and legal-hold checks.

**Pass:** Owners, discarder and legal hold. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 19 — Three incident tabletops

```bash
docker logs --tail 40 jenkins-ch020
```

**Operator action:** Tabletop queue starvation, leaked artifact secret and missed cron; record safe rollback.

**Pass:** Queue, leak, missed cron analyzed. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Exercise 20 — Cleanup and score

```bash
docker stop jenkins-ch020
docker rm jenkins-ch020
```

**Operator action:** Remove only lab-owned resources and verify exclusive volume ownership.

**Pass:** Controller removed. **Rollback:** revert lab-owned settings or stop/remove disposable resources only.

## Runnable integrated Jenkinsfile

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
    booleanParam(name: 'FAIL_DEMO', defaultValue: false)
  }
  stages {
    stage('Validate') {
      steps {
        script {
          if (!(params.TARGET in ['dev', 'staging'])) {
            error('Target not allowed')
          }
        }
        echo "Target=${params.TARGET} DryRun=${params.DRY_RUN}"
      }
    }
    stage('Review') {
      steps { echo 'No deployment or shell execution.' }
    }
    stage('Result') {
      steps {
        script {
          if (params.FAIL_DEMO) {
            error('Intentional lab failure')
          }
        }
        echo 'Lab smoke successful'
      }
    }
  }
  post {
    success { echo 'SUCCESS recorded' }
    failure { echo 'FAILURE recorded' }
    always { echo 'Collect redacted evidence' }
  }
}
```

## Production readiness matrix

| Gate | Status (Pass/Fail/Design only) | Evidence |
|---|---|---|
| G1 Zero controller executors | | |
| G2 Versioned job and RBAC | | |
| G3 Validated parameters | | |
| G4 SUCCESS and FAILURE build history | | |
| G5 Signed webhook/cron design | | |
| G6 Isolated agent/workspace | | |
| G7 JUnit/artifact integrity | | |
| G8 Notification/log retention | | |
| G9 Incident/rollback tabletop | | |
| G10 SLO, cleanup and approvals | | |

## Incident drills

| Incident | First checks | Safe recovery |
|---|---|---|
| Queue starvation | Agent labels, offline nodes, executors | Restore eligible agent capacity |
| Secret in archived artifact | Archive allowlist and credential scope | Quarantine and rotate |
| Missed cron | Timezone, controller availability, job state | Reconcile missed work |
| Duplicate webhook | Delivery ID, retry history | Idempotent deduplication |
| JUnit UNSTABLE | XML test failures, result policy | Repair tests/gates |
| Retention disk pressure | df -h, build/artifact counts | Approved cleanup |

## Assessment — 100 points

| Area | Points |
|---|---:|
| Job governance and migration | 20 |
| Triggers and security | 20 |
| Agents/workspaces/artifacts/tests | 20 |
| Results/logs/notifications | 15 |
| Incidents and rollback | 15 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ with no security-critical failure. Production readiness requires verified staging gates and approval.

## Evidence handoff

```text
Operator/date:
Controller localhost URL and port:
Built-in executor count:
Persistent home:
Pipeline success build:
Pipeline failure build:
Parameter allowlist:
Freestyle migration matrix:
Webhook/cron/approval design:
Agent/workspace security:
JUnit/artifact integrity:
Logs/notification/retention policy:
SLO and alert owners:
Three incident analyses:
Cleanup proof:
Score/reviewer:
Residual risks/approval:
```

**Part 04 complete. Next:** Chapter 021 — Declarative Pipeline Syntax, Stages, Steps and Directives.
