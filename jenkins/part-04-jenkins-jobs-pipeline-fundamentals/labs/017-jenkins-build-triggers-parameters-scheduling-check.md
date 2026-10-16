# Chapter 017 — Hands-On Lab: Build Triggers, Parameters and Scheduling

**Parent:** [Chapter 017](../017-jenkins-build-triggers-parameters-scheduling.md)

## Safety

Disposable localhost Jenkins controller only. Live webhooks, cron automation and deployments are design-only unless approved staging exists. Do not print credentials or enable controller build executors.

## Exercise 01 — Docker prerequisites

```bash
docker version
docker ps
```

**Operator action:** Record observed or design-only evidence and the operational implications.

**Pass:** Engine ready. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 02 — Create dedicated volume

```bash
docker volume create jenkins-ch017-home
```

**Operator action:** Record observed or design-only evidence and the operational implications.

**Pass:** Volume exists. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 03 — Start private controller

```bash
docker run -d --name jenkins-ch017 --restart=no -p 127.0.0.1:8095:8080 --memory 4g --cpus 2 --mount source=jenkins-ch017-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator action:** Record observed or design-only evidence and the operational implications.

**Pass:** Controller running. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 04 — Inspect logs

```bash
docker logs --tail 60 jenkins-ch017
```

**Operator action:** Record observed or design-only evidence and the operational implications.

**Pass:** No fatal startup errors. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 05 — Check listener

```bash
docker port jenkins-ch017
```

**Operator action:** Record observed or design-only evidence and the operational implications.

**Pass:** Loopback-only binding. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 06 — Bootstrap privately

```bash
docker exec jenkins-ch017 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator action:** Unlock at http://127.0.0.1:8095 privately; never include unlock password in evidence.

**Pass:** Named admin; secret not recorded. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 07 — Disable built-in executors

```bash
docker ps --filter name=jenkins-ch017
```

**Operator action:** Manage Jenkins → Nodes → Built-In Node → set executors to zero.

**Pass:** Zero controller executors. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 08 — Inspect runtime identity

```bash
docker inspect jenkins-ch017 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator action:** Record observed or design-only evidence and the operational implications.

**Pass:** Runtime documented. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 09 — Inspect home mount

```bash
docker inspect jenkins-ch017 --format '{{json .Mounts}}'
```

**Operator action:** Record observed or design-only evidence and the operational implications.

**Pass:** Persistent home identified. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 10 — Create parameterized Pipeline

```bash
docker logs --tail 15 jenkins-ch017
```

**Operator action:** New Item → Pipeline → ch017-trigger-parameters; paste the Jenkinsfile below.

**Pass:** Job definition saved. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 11 — Run dev dry-run

```bash
docker stats --no-stream jenkins-ch017
```

**Operator action:** Build with Parameters using TARGET=dev, DRY_RUN=true; inspect console.

**Pass:** SUCCESS and dev/true values. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 12 — Run staging dry-run

```bash
docker logs --tail 20 jenkins-ch017
```

**Operator action:** Run TARGET=staging, DRY_RUN=true; record result.

**Pass:** SUCCESS and staging/true values. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 13 — Review dry-run false behavior

```bash
docker inspect jenkins-ch017 --format '{{.State.Status}}'
```

**Operator action:** Set DRY_RUN=false in the smoke job and verify it still performs no deployment.

**Pass:** No deployment even with false. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 14 — Review parameter allowlist

```bash
docker ps --filter name=jenkins-ch017
```

**Operator action:** Record observed or design-only evidence and the operational implications.

**Pass:** Only approved choices accepted. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 15 — Review cron H syntax

```bash
docker logs --tail 15 jenkins-ch017
```

**Operator action:** Compare H/15, H 2 and weekday cron expressions; do not enable live schedule.

**Pass:** Hashed schedule and timezone explained. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 16 — Design signed webhook

```bash
docker port jenkins-ch017
```

**Operator action:** Document TLS, provider signature, deduplication and replay strategy.

**Pass:** TLS/signature/delivery ID plan. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 17 — Compare polling and webhook

```bash
docker stats --no-stream jenkins-ch017
```

**Operator action:** Record observed or design-only evidence and the operational implications.

**Pass:** API and latency tradeoffs. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 18 — Review concurrency policy

```bash
docker logs --tail 20 jenkins-ch017
```

**Operator action:** Record observed or design-only evidence and the operational implications.

**Pass:** DisableConcurrentBuilds rationale. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 19 — Incident tabletop

```bash
docker logs --tail 30 jenkins-ch017
```

**Operator action:** Tabletop: webhook 403, duplicate delivery and missed cron; record rollback.

**Pass:** Three trigger failures diagnosed. **Rollback:** revert lab-only settings and remove disposable resources.

## Exercise 20 — Cleanup and score

```bash
docker stop jenkins-ch017
docker rm jenkins-ch017
```

**Operator action:** Verify ownership before optional removal of dedicated volume.

**Pass:** Lab controller removed. **Rollback:** revert lab-only settings and remove disposable resources.

## Runnable no-agent Pipeline

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
  }
  stages {
    stage('Validate') {
      steps {
        script {
          if (!(params.TARGET in ['dev', 'staging'])) {
            error('Target not allowed')
          }
        }
        echo "TARGET=${params.TARGET} DRY_RUN=${params.DRY_RUN}"
      }
    }
    stage('Report') {
      steps { echo 'No deployment executed.' }
    }
  }
}
```

## Cron worksheet

| Expression | Meaning | Notes |
|---|---|---|
| `H/15 * * * *` | Hashed 15-minute cadence | Not a strict interval SLA |
| `H 2 * * *` | Daily during 02:00 | Timezone/DST review |
| `H H * * 1-5` | Weekday hashed schedule | Record job owner |
| `H 4 * * 0` | Sunday during 04:00 | Maintenance overlap |

## Trigger incident decision matrix

| Failure | Evidence | Recovery |
|---|---|---|
| Webhook 403 | Provider delivery/auth logs | Repair signed integration |
| Duplicate webhook | Delivery ID and retry history | Idempotency and dedupe |
| Missed cron | Controller availability/timezone | Reconcile missed work |
| Invalid target | Parameter allowlist | Reject unsafe input |
| Overlapping builds | Job concurrency and locks | Serialize shared state |
| PR deploy risk | SCM branch trust and credentials | Quarantine and restrict |

## Assessment — 100 points

| Domain | Points |
|---|---:|
| Trigger and scheduling concepts | 25 |
| Parameter validation | 20 |
| Webhook/SCM security | 20 |
| Concurrency and authorization | 15 |
| Troubleshooting/monitoring | 10 |
| Cleanup/evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with all security-critical gates.

## Evidence template

```text
Operator/date:
Controller localhost URL and port:
Built-in executors:
Parameterized Pipeline name:
dev/staging build results:
DRY_RUN behavior:
Cron timezone and H syntax:
Webhook signature/replay design:
SCM polling tradeoffs:
Concurrency/approval policy:
Three trigger incidents:
Cleanup proof:
Score/reviewer:
```

**Next:** Chapter 018 — Jenkins Build Workspaces, Artifacts and Test Reports.
