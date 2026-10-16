# Chapter 017 — Jenkins Build Triggers, Parameters and Scheduling

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 04:** Jenkins Jobs and Pipeline Fundamentals  
**Chapter:** 017 / 100  
**Companion lab:** [017 — Build Triggers, Parameters and Scheduling Check](labs/017-jenkins-build-triggers-parameters-scheduling-check.md)

> **Safety:** Use a disposable localhost Jenkins controller. Webhooks, SCM polling, scheduled production jobs and external integrations are **design or approved-staging exercises** unless explicitly configured. Never put credentials in build parameters, URLs, Jenkinsfiles or logs. Keep controller built-in executors at zero.

## 1. Learning objectives

Distinguish manual, scheduled, SCM polling, webhook and upstream triggers; implement safe parameters; explain Jenkins hashed cron syntax and timezone; prevent duplicate events, runaway schedules, concurrent state corruption and unauthorized deployments; investigate trigger incidents.

## 2. Trigger architecture

```text
manual / cron / SCM polling / signed webhook / upstream job
                           |
                    trigger evaluation
                           |
               validation + authorization
                           |
                     Jenkins queue
                           |
               eligible isolated agent
                           |
                    Pipeline stages
                           |
             artifacts, notifications, audit
```

A trigger starts or queues work; it does not guarantee an available executor. Separate the trigger delivery SLO from queue wait and build duration.

## 3. Trigger methods and tradeoffs

| Method | Use | Risk/control |
|---|---|---|
| Manual Build Now | Operator or incident action | Job/Build RBAC and audit |
| Build with Parameters | Controlled environment/branch selection | Allowlist and validation |
| Cron timer | Periodic maintenance/reporting | Timezone, overlap and missed runs |
| Poll SCM | Repositories lacking webhooks | API load and latency |
| SCM webhook | Event-driven builds | TLS, signature, deduplication |
| Upstream/downstream | Multi-job orchestration | Cycles, result propagation |
| Multibranch SCM events | Branch/PR discovery | Untrusted branch restrictions |

## 4. Jenkins cron and timezone

Jenkins cron has five fields: `MINUTE HOUR DAY_OF_MONTH MONTH DAY_OF_WEEK`. Jenkins supports `H` to spread scheduled load across jobs; `H` is a stable hash rather than a random minute on each run. Review timezone handling explicitly and test daylight-saving transitions for business-critical schedules.

```text
H/15 * * * *       # roughly every 15 minutes with hashed offset
H 2 * * *          # once daily during the 02:00 hour
H H * * 1-5        # once each weekday at hashed hour/minute
```

These examples are illustrative. `H/15` spreads start offsets and is not a strict wall-clock interval SLA.

## 5. Safe Pipeline parameters

```groovy
pipeline {
  agent none
  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '10'))
  }
  parameters {
    choice(name: 'TARGET', choices: ['dev', 'staging'], description: 'Approved target')
    booleanParam(name: 'DRY_RUN', defaultValue: true, description: 'Do not deploy')
  }
  stages {
    stage('Validate inputs') {
      steps {
        script {
          if (!(params.TARGET in ['dev', 'staging'])) {
            error('Invalid target')
          }
        }
        echo "Target=${params.TARGET}; dryRun=${params.DRY_RUN}"
      }
    }
    stage('Report') {
      steps { echo 'No deployment or agent execution in this smoke job.' }
    }
  }
}
```

This example uses only lightweight controller orchestration steps, not shell or workspace operations. Never substitute a free-text parameter for a Jenkins credential.

## 6. Timed trigger example

```groovy
pipeline {
  agent none
  triggers {
    cron('H 2 * * 1-5')
  }
  stages {
    stage('Scheduled smoke') {
      steps { echo 'Scheduled orchestration check.' }
    }
  }
}
```

Do not leave a lab cron enabled after testing. Scheduled jobs can overlap unless explicitly constrained; choose `disableConcurrentBuilds()` when appropriate.

## 7. SCM polling versus webhooks

Polling periodically queries source control, increasing API and controller load. Webhooks are lower-latency and should be authenticated/signed at the provider and handled through a trusted HTTPS endpoint. Avoid generic unauthenticated build tokens; restrict permissions and implement idempotency for repeated deliveries.

## 8. Upstream and downstream orchestration

```groovy
pipeline {
  agent none
  stages {
    stage('Parent') {
      steps {
        echo 'Validate upstream completion before downstream work.'
      }
    }
  }
}
```

For real downstream jobs, the Pipeline `build` step can schedule another job, but it requires authorization and an existing target job. Avoid trigger cycles and propagate build failures according to an explicit contract.

## 9. Trigger security and change control

- Require signed provider webhooks over trusted TLS.
- Restrict who can edit Jenkinsfiles, triggers and deployment parameters.
- Isolate untrusted PRs from production credentials and privileged agent pools.
- Prefer allowlisted environment choices and protected deployment approvals.
- Track webhook delivery IDs, schedule owners, trigger volume and job-to-environment mapping.
- Design retries to be idempotent and bounded.

## 10. Disposable controller setup

```bash
docker volume create jenkins-ch017-home
docker run -d --name jenkins-ch017 --restart=no \
  -p 127.0.0.1:8095:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch017-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch017
docker logs --tail 60 jenkins-ch017
docker port jenkins-ch017
```

Use the mutable LTS tag for disposable learning only; production should pin an approved digest. Unlock privately at `http://127.0.0.1:8095`, create a named admin and set **built-in node executors to 0**.

## 11. Hands-on safe validation

Create a Pipeline job `ch017-trigger-parameters` using the safe parameter example. Run with both allowed target values and both DRY_RUN settings; inspect build history and confirm no shell command or deployment runs. Review (do not activate) a cron expression and signed webhook design.

## 12. Observability and SLOs

Monitor trigger deliveries and errors, webhook signature failures, duplicate delivery rate, scheduled-job last success, SCM polling cost, queue wait, executor saturation, unexpected manual invocations and deployment approval bypass. Separate false positives from actual missed schedules.

## 13. Twenty trigger and scheduling failure scenarios

| # | Symptom | Investigation | Safe response |
|---|---|---|---|
| 1 | Webhook never arrives | Provider delivery, DNS, TLS, ingress, signature | Restore signed webhook route |
| 2 | Webhook rejected 403 | CSRF, auth, token and plugin endpoint | Fix approved authentication |
| 3 | Webhook duplicated | Delivery IDs, retries, trigger configuration | Deduplicate/idempotent builds |
| 4 | SCM polling floods controller | Poll interval, repository size, plugin behavior | Prefer webhooks or tune polling |
| 5 | Cron schedule unexpected | Timezone, H hash and job config | Document timezone and adjust schedule |
| 6 | Cron fires during maintenance | Quiet period, maintenance window and triggers | Disable/reconcile safely |
| 7 | Parameter value invalid | Choice/regex validation and allowlists | Reject unsafe input |
| 8 | Password passed as string parameter | Build logs, job history and environment | Revoke/rotate and use Credentials |
| 9 | Untrusted branch triggers deploy | Branch filters and SCM trust | Restrict deploy permissions |
| 10 | Concurrent builds corrupt shared state | Concurrency, locks and workspace ownership | Serialize critical jobs |
| 11 | Quiet period causes apparent delay | Job trigger settings and queue reason | Tune intentional delay |
| 12 | Trigger disabled after config change | Job enabled state and change history | Restore reviewed trigger |
| 13 | Upstream build loops | Dependency graph and trigger recursion | Break cycle and add guard |
| 14 | Parameterized branch injection | SCM branch validation and shell interpolation | Use allowlists and safe quoting |
| 15 | Build aborted by timeout | Queue vs stage timeout scope | Right-size timeout and investigate |
| 16 | Schedule missed after restart | Controller availability and scheduling logs | Reconcile missed work explicitly |
| 17 | Webhook secret rotated | Provider/Jenkins secret synchronization | Update both ends safely |
| 18 | Trigger causes burst queue | Event volume, executors and provisioning | Throttle/scale eligible pools |
| 19 | Wrong environment selected | Parameter defaults and approval controls | Require explicit validated choice |
| 20 | Job runs without expected approval | Input gate and authorization policy | Restore human gate and audit |

## 14. Eight SRE runbooks

### RB-01 Webhook outage

**Procedure:** Check provider delivery status, TLS, endpoint, signature and Jenkins trigger logs; replay only idempotently.

**Exit criteria:** trigger delivery understood, authorized inputs, correct queue routing, no duplicate or unauthorized deployment, owner and evidence recorded.

### RB-02 Cron/schedule incident

**Procedure:** Verify controller timezone, H expression, disabled state and maintenance windows; reconcile missed runs.

**Exit criteria:** trigger delivery understood, authorized inputs, correct queue routing, no duplicate or unauthorized deployment, owner and evidence recorded.

### RB-03 Parameter abuse

**Procedure:** Quarantine job, inspect allowed values, revoke exposed secrets and enforce input validation.

**Exit criteria:** trigger delivery understood, authorized inputs, correct queue routing, no duplicate or unauthorized deployment, owner and evidence recorded.

### RB-04 Duplicate/retry storm

**Procedure:** Identify delivery IDs and retry policy, stop recursive triggers and deduplicate safely.

**Exit criteria:** trigger delivery understood, authorized inputs, correct queue routing, no duplicate or unauthorized deployment, owner and evidence recorded.

### RB-05 Queue burst

**Procedure:** Correlate trigger rate, label availability, executors and provisioning; apply bounded concurrency.

**Exit criteria:** trigger delivery understood, authorized inputs, correct queue routing, no duplicate or unauthorized deployment, owner and evidence recorded.

### RB-06 Deployment approval failure

**Procedure:** Freeze deployment, review RBAC, input gate and branch trust; restore approved control.

**Exit criteria:** trigger delivery understood, authorized inputs, correct queue routing, no duplicate or unauthorized deployment, owner and evidence recorded.

### RB-07 Trigger config rollback

**Procedure:** Restore reviewed Jenkinsfile/Job DSL, re-test in staging and validate provider webhook.

**Exit criteria:** trigger delivery understood, authorized inputs, correct queue routing, no duplicate or unauthorized deployment, owner and evidence recorded.

### RB-08 Operations handoff

**Procedure:** Record trigger owners, expected cadence, SLA, alerting, suppression, rollback and audit evidence.

**Exit criteria:** trigger delivery understood, authorized inputs, correct queue routing, no duplicate or unauthorized deployment, owner and evidence recorded.

## 15. Acceptance gates

| Gate | Requirement |
|---|---|
| G1 | Built-in controller executors zero |
| G2 | Trigger methods compared with risks |
| G3 | Parameter allowlist and defaults validated |
| G4 | No-agent Pipeline succeeds |
| G5 | Cron H/timezone and DST implications explained |
| G6 | Webhook signature and deduplication designed |
| G7 | Concurrency and retry policy documented |
| G8 | Branch trust and deployment approvals reviewed |
| G9 | Three incidents and rollback rehearsed |
| G10 | Lab cleanup and redacted evidence complete |

## 16. Assessment — 100 points

| Domain | Points |
|---|---:|
| Trigger methods and scheduling | 25 |
| Parameters and validation | 20 |
| SCM/webhook security | 20 |
| Concurrency and authorization | 15 |
| Incident response and monitoring | 10 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with mandatory security gates. A localhost smoke test does not certify live webhooks or cron reliability.

## 17. Cleanup

```bash
docker stop jenkins-ch017
docker rm jenkins-ch017
# Destructive only after verifying exclusive lab ownership:
docker volume rm jenkins-ch017-home
```

**Next:** Chapter 018 — Jenkins Build Workspaces, Artifacts and Test Reports.
