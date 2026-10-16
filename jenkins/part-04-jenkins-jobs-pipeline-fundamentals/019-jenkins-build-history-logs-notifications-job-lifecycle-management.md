# Chapter 019 — Jenkins Build History, Logs, Notifications and Job Lifecycle Management

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 04:** Jenkins Jobs and Pipeline Fundamentals  
**Chapter:** 019 / 100  
**Companion lab:** [019 — Build History, Logs, Notifications and Lifecycle Check](labs/019-jenkins-build-history-logs-notifications-lifecycle-check.md)

> **Safety:** Use a disposable localhost controller with zero built-in executors. Never print credentials or expose logs publicly. SMTP, Slack and external notifications are **design-only** unless an approved staging destination is available.

## 1. Objectives

Understand build history and result semantics, console logs and metadata, notification delivery and noise reduction, job lifecycle, retention, audit, backup, incident evidence and SRE handoff.

## 2. Lifecycle and observability architecture

```text
SCM / manual / schedule
          |
      Jenkins job
          |
  queue -> agent build
          |
  build result + stage events
       /      |       \
    logs    tests    artifacts
       \      |       /
       build history + audit
          |
    notifications/alerts
          |
   retention + archival
          |
  backup / compliance / DR
```

A job definition is distinct from its build records. Build history is useful operational evidence but should not be treated as an immutable compliance archive without dedicated controls.

## 3. Build result semantics

| Result | Meaning | Operator action |
|---|---|---|
| SUCCESS | Pipeline completed successfully | Check downstream artifacts/tests |
| UNSTABLE | Build completed with issues, often test failures | Review tests and policy |
| FAILURE | Pipeline/build step failed | Triage root cause |
| ABORTED | Build canceled/interrupted | Determine intentional vs incident |
| NOT_BUILT | Stage/build not executed | Review gating and upstream state |

Do not equate a green build with application production readiness.

## 4. Build history and metadata

Inspect build number, start time, duration, cause, queue wait, stage results, SCM revision, agent identity, parameters, artifact references and triggering principal. Retain enough metadata for incident correlation without persisting sensitive parameters.

## 5. Console logs and privacy

- Prefer timestamped, structured logs with correlation identifiers.
- Masking is defense in depth, not permission to print secrets.
- Never enable shell `set -x` around credential-bearing commands.
- Centralize audit and controller logs where retention and access are governed.
- Restrict console access by job/folder RBAC and classify build outputs.

## 6. Disposable controller

```bash
docker volume create jenkins-ch019-home
docker run -d --name jenkins-ch019 --restart=no \
  -p 127.0.0.1:8097:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch019-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch019
docker logs --tail 60 jenkins-ch019
docker port jenkins-ch019
```

Use mutable LTS only for a disposable lab; pin reviewed image digest in production. Unlock privately at `http://127.0.0.1:8097`, create a named administrator, and set built-in node executors to **0**.

## 7. No-agent Pipeline for build history

Create Pipeline `ch019-build-history`:

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
    stage('Validate') {
      steps {
        echo "Build number=${env.BUILD_NUMBER}"
        echo "Failure demonstration=${params.FAIL_DEMO}"
      }
    }
    stage('Result') {
      steps {
        script {
          if (params.FAIL_DEMO) {
            error('Intentional lab failure; no infrastructure fault')
          }
        }
        echo 'Successful lab result'
      }
    }
  }
  post {
    success { echo 'Result: success' }
    failure { echo 'Result: failure' }
    always { echo 'Result recorded in build history' }
  }
}
```

Run once with `FAIL_DEMO=false` and once with `FAIL_DEMO=true`. Inspect both build records and their redacted console logs. These steps require no agent workspace.

## 8. Notification design

Use approved plugins/integrations for email, Slack or incident systems. Configure per-result routing (failure, unstable, recovery), ownership and escalation; rate-limit repeated failures and avoid leaking job parameters or console content.

```groovy
post {
  failure {
    echo 'In production: send a scoped failure notification.'
  }
  fixed {
    echo 'In production: send recovery notification if supported.'
  }
}
```

This is an illustrative `post` block for a Declarative Pipeline, not a standalone runnable Jenkinsfile. Actual delivery requires approved plugin, credentials and destination.

## 9. Build discarder and retention

```groovy
options {
  buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '10'))
}
```

Retention must reflect operational needs, artifact repository lifecycle, compliance/legal hold and disk budgets. A build discarder may remove records and artifacts; do not configure deletion before reviewing obligations.

## 10. Job lifecycle governance

**Create → review → enable → monitor → disable → archive/export → delete (approved)**. Inventory upstream/downstream triggers, credential references, webhooks, SCM and dashboards before removal. Disable and observe before deletion, and preserve required audit and recovery evidence.

## 11. Alerting and SLOs

Track build failure and unstable rates, queue p95, build duration, last successful scheduled run, notification delivery failures, controller disk, artifact retention growth and log redaction incidents. Alerts should have clear owners and action thresholds.

## 12. Incident evidence and rollback

Capture job path, build number, SCM commit, timestamps in UTC, result, queue reason, agent, stage, recent changes and redacted error excerpts. For regression, revert reviewed Jenkinsfile/Job DSL and compatible plugin changes; do not delete evidence to hide failures.

## 13. Twenty failure scenarios

| # | Symptom | Investigation | Safe response |
|---|---|---|---|
| 1 | Build history missing | Build discarder, backup and job migration | Recover supported records from backup |
| 2 | Console output truncated | Log storage, rotation and plugin behavior | Preserve central logs and reproduce |
| 3 | Sensitive token printed | Console masking and script arguments | Contain, revoke/rotate and audit |
| 4 | Email notification not delivered | SMTP, credentials, DNS and provider limits | Repair authenticated transport |
| 5 | Slack notification missing | Webhook/token scope and egress | Restore scoped integration |
| 6 | Notification storm | Repeated failures and retry policy | Deduplicate and rate-limit |
| 7 | UNSTABLE incorrectly treated as success | JUnit result and post conditions | Fix result policy |
| 8 | ABORTED build retries endlessly | Trigger loops and retry guard | Stop recursive retry |
| 9 | Job deletion removes evidence | Retention, audit and backup | Restore approved record |
| 10 | Old builds consume disk | Build discarder and artifact storage | Apply reviewed retention |
| 11 | Build record references missing artifacts | Artifact manager and lifecycle | Reconcile retention policy |
| 12 | Wrong build timestamp | Controller timezone and log timestamps | Normalize to UTC |
| 13 | Queue wait hidden in metrics | Queue and executor instrumentation | Publish queue p95 |
| 14 | Failed stage not visible | Stage metadata and plugin compatibility | Repair Pipeline visualization |
| 15 | Post cleanup hides root cause | post step exception and result | Preserve original error and handle cleanup |
| 16 | Build cannot be replayed | RBAC, Pipeline definition and trust | Use reviewed SCM change |
| 17 | Job disabled unexpectedly | Job config history and admin audit | Restore approved state |
| 18 | Orphaned workspace after job removal | Agent inventory and owner tags | Delete only verified job-owned data |
| 19 | Webhook duplicates build history | Delivery IDs and trigger retry | Implement idempotency |
| 20 | Log retention violates compliance | Legal hold and data classification | Align policy with governance |

## 14. Eight SRE runbooks

### RB-01 Missing build evidence

**Procedure:** Check build record, discarder, controller home, artifact store and backup; recover only supported state.

**Exit criteria:** correct result classification, protected logs, notification ownership, retention policy and incident evidence.

### RB-02 Sensitive data in logs

**Procedure:** Stop affected jobs, restrict log access, revoke/rotate secrets, preserve redacted incident evidence.

**Exit criteria:** correct result classification, protected logs, notification ownership, retention policy and incident evidence.

### RB-03 Notification outage

**Procedure:** Inspect destination, credentials, DNS, TLS, plugin and provider delivery; test approved staging route.

**Exit criteria:** correct result classification, protected logs, notification ownership, retention policy and incident evidence.

### RB-04 Build result regression

**Procedure:** Compare SUCCESS/UNSTABLE/FAILURE/ABORTED semantics, JUnit reports and post conditions.

**Exit criteria:** correct result classification, protected logs, notification ownership, retention policy and incident evidence.

### RB-05 Storage and retention pressure

**Procedure:** Review build/artifact counts, home disk and retention policies; avoid deleting legal-hold records.

**Exit criteria:** correct result classification, protected logs, notification ownership, retention policy and incident evidence.

### RB-06 Job disable/archive/delete

**Procedure:** Inventory dependencies and ownership, preserve backups and audit, disable before reviewed deletion.

**Exit criteria:** correct result classification, protected logs, notification ownership, retention policy and incident evidence.

### RB-07 Alert fatigue

**Procedure:** Deduplicate repeated failures, group by owner and severity, add bounded retries and suppression.

**Exit criteria:** correct result classification, protected logs, notification ownership, retention policy and incident evidence.

### RB-08 SRE handoff

**Procedure:** Document log source, dashboard, notification owner, retention, escalation and rollback.

**Exit criteria:** correct result classification, protected logs, notification ownership, retention policy and incident evidence.

## 15. Acceptance gates

| Gate | Requirement |
|---|---|
| G1 | Built-in controller executors zero |
| G2 | SUCCESS and FAILURE demo builds recorded |
| G3 | Build history and console evidence inspected |
| G4 | UNSTABLE/ABORTED semantics understood |
| G5 | Notification destinations and dedupe designed |
| G6 | No secrets in logs or alerts |
| G7 | Retention and legal-hold implications reviewed |
| G8 | Job disable/archive/delete sequence documented |
| G9 | Three incident diagnoses and rollback |
| G10 | Lab cleanup and redacted evidence complete |

## 16. Assessment — 100 points

| Domain | Points |
|---|---:|
| Build history and result semantics | 25 |
| Console logs and security | 20 |
| Notifications and alerting | 20 |
| Lifecycle and retention | 15 |
| Incident response | 10 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ and all security-critical gates.

## 17. Cleanup

```bash
docker stop jenkins-ch019
docker rm jenkins-ch019
# Destructive only if exclusively lab-owned:
docker volume rm jenkins-ch019-home
```

**Next:** Chapter 020 — Jenkins Jobs and Pipeline Fundamentals Production Operations Capstone.
