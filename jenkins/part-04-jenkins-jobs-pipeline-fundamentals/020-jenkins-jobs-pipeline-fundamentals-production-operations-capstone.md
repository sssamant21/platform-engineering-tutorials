# Chapter 020 — Jenkins Jobs and Pipeline Fundamentals Production Operations Capstone

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 04:** Jenkins Jobs and Pipeline Fundamentals  
**Chapter:** 020 / 100 — **Part 04 capstone**  
**Companion lab:** [020 — Jobs and Pipeline Fundamentals Capstone Check](labs/020-jenkins-jobs-pipeline-fundamentals-capstone-check.md)

> **Safety:** Run all executable examples on a disposable localhost Jenkins controller with **zero built-in executors**. External SCM webhooks, notifications, artifact publishing, JUnit and shell builds require approved staging integrations/isolated agents; the local capstone does not claim those are tested.

## 1. Mission

Integrate chapters 016–019 into a production-style CI operations acceptance: job taxonomy, Freestyle-to-Pipeline migration, validated parameters, trigger governance, agent/workspace boundaries, artifacts/test results, build history, logs, notifications, retention, incident response and rollback.

## 2. Prerequisite chapters

- [016 — Jobs, Freestyle and Pipeline Fundamentals](016-jenkins-jobs-freestyle-projects-pipeline-job-fundamentals.md)
- [017 — Triggers, Parameters and Scheduling](017-jenkins-build-triggers-parameters-scheduling.md)
- [018 — Workspaces, Artifacts and Test Reports](018-jenkins-build-workspaces-artifacts-test-reports.md)
- [019 — Build History, Logs, Notifications and Lifecycle](019-jenkins-build-history-logs-notifications-job-lifecycle-management.md)

## 3. Reference architecture

```text
 SCM provider (protected branch / signed webhook)
       |                  scheduled/manual trigger
       +---------------------------+
                                   |
                          validated job definition
                          (Pipeline in Git preferred)
                                   |
                        controller queue / audit
                        (built-in executors = 0)
                                   |
                   isolated Linux agent / pod
                         |         |        |
                       checkout   test    package
                         |         |        |
                         |      JUnit     artifact + SHA
                         +---------+--------+
                                   |
                    result / logs / notification
                                   |
                    retention / backup / DR
```

Labels are scheduling hints, not a security boundary. Untrusted PRs must not access privileged credentials, deployment agents or release approvals.

## 4. Enterprise job standards

| Domain | Requirement | Evidence |
|---|---|---|
| Definition | Versioned Jenkinsfile/Job DSL with owner | Git review |
| Access | Folder/job RBAC and credential scoping | Access audit |
| Triggers | Signed webhooks, bounded cron, manual authorization | Delivery records |
| Parameters | Allowlisted environment, branch and dry-run | Validation output |
| Concurrency | Explicit overlap/lock policy | Build overlap test |
| Agents | Controller executors zero; trusted pools isolated | Node config |
| Workspace | Job-owned path, safe cleanup and capacity | Agent metrics |
| Artifacts | Allowlisted outputs, checksum, immutable repository | Manifest and scan |
| Tests | Valid runner-generated JUnit, result gating | Report and build result |
| Logs | Timestamps, redaction and restricted access | Redacted evidence |
| Notifications | Owner, severity, deduplication, recovery | Delivery audit |
| Lifecycle | Retention, disable/archive/delete approvals | Change record |

## 5. Safe local deployment

```bash
docker volume create jenkins-ch020-home
docker run -d --name jenkins-ch020 --restart=no \
  -p 127.0.0.1:8098:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch020-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch020
docker logs --tail 60 jenkins-ch020
docker port jenkins-ch020
```

The mutable LTS tag is for disposable training only; production images must be reviewed and pinned by digest. Unlock privately at `http://127.0.0.1:8098`, create a named admin and configure **Manage Jenkins → Nodes → Built-In Node → executors = 0**.

## 6. Integrated no-agent capstone Pipeline

Create `ch020-operations-capstone`:

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
            error('Unauthorized target')
          }
        }
        echo "Target=${params.TARGET} DryRun=${params.DRY_RUN}"
      }
    }
    stage('Review') {
      steps {
        echo 'This controller-only smoke never deploys.'
      }
    }
    stage('Result') {
      steps {
        script {
          if (params.FAIL_DEMO) {
            error('Intentional capstone failure')
          }
        }
        echo 'Accepted orchestration smoke'
      }
    }
  }
  post {
    success { echo 'Success recorded' }
    failure { echo 'Failure recorded' }
    always { echo 'Capture redacted build evidence' }
  }
}
```

Run once with `TARGET=dev`, `DRY_RUN=true`, `FAIL_DEMO=false` and once with `FAIL_DEMO=true`. Observe SUCCESS and FAILURE, build history and `post` behavior. `DRY_RUN=false` still does **not** deploy; it is only a parameter demonstration.

## 7. Freestyle migration acceptance

Inventory existing Freestyle jobs, shell commands, plugins, triggers, SCM credentials, agent labels, artifacts and post-build notifications. Implement reviewed Pipeline equivalents; run side-by-side in staging; compare checksums, test results, duration and downstream effects. Migrate triggers after approval, retain rollback and disable the old job only after evidence.

## 8. Trigger and schedule acceptance

Review webhook TLS/signature, delivery ID deduplication, protected branch trust, cron H hashing, timezone/DST, missed-run reconciliation, manual RBAC and approvals. Never configure an untrusted PR to trigger privileged deployment.

## 9. Agent-backed build and report acceptance

On an **approved isolated Linux agent only**, verify checkout, workspace ownership, valid test-runner JUnit XML, allowlisted artifact archive, SHA-256, immutable external repository and retention. The local controller-only smoke does not validate these integrations.

## 10. Observability, SLO and FinOps

Measure queue wait p95, build duration p95, failure/unstable rates, webhook delivery failures, last successful schedule, agent online ratio, workspace disk/inodes, artifact growth, notification delivery and idle executor cost. Set owners, alert thresholds, escalation and cost budgets.

## 11. Operational change and rollback

Before changes, record approved Jenkinsfile/Job DSL commit, trigger config, plugin versions, home snapshot and credentials inventory (never copy secrets into reports). During change, protect active jobs, validate staging and watch SLOs. Roll back the reviewed job definition or restore a compatible full snapshot if plugin/data migration prevents safe downgrade.

## 12. Twenty production failure scenarios

| # | Symptom | Investigation | Safe recovery |
|---|---|---|---|
| 1 | Untrusted job scheduled on privileged pool | Agent labels, trust boundaries, credential access | Quarantine and isolate |
| 2 | Freestyle configuration drift | UI changes, config history and Job DSL | Reconcile reviewed definition |
| 3 | Pipeline syntax regression | Jenkinsfile parser, SCM diff and plugins | Revert reviewed commit |
| 4 | Webhook event rejected | Signature, TLS and endpoint | Restore trusted delivery |
| 5 | Webhook delivery duplicated | Delivery IDs and idempotency | Deduplicate and bound retries |
| 6 | Cron missed maintenance window | Timezone, DST, controller uptime | Reconcile missed run |
| 7 | Unvalidated environment parameter | Input allowlist and approvals | Reject input and audit |
| 8 | Concurrent builds collide | Workspace ownership and locks | Serialize stateful work |
| 9 | Queue waits grow | Labels, executors, agent provisioning | Restore eligible capacity |
| 10 | Artifact missing after build | Workspace, archive glob and teardown | Fix publish ordering |
| 11 | Artifact leaks credentials | Archive paths and secret scanner | Quarantine and rotate |
| 12 | JUnit report missing | Runner output, plugin and glob | Repair report generation |
| 13 | UNSTABLE incorrectly green | Result handling and test policy | Enforce gate |
| 14 | Logs expose tokens | Console, tracing and plugin output | Restrict, revoke and rotate |
| 15 | Notification storm | Repeated failure events and rate limit | Deduplicate and group |
| 16 | Notification silently fails | Transport, credentials and provider delivery | Repair approved channel |
| 17 | Build history deleted too early | Discarder, legal hold and backup | Recover and correct retention |
| 18 | Job disabled without approval | Audit and change management | Restore authorized state |
| 19 | Controller disk pressure | Build records, artifacts and inode usage | Approved cleanup/capacity |
| 20 | Rollback incompatible with plugin change | Version matrix and state migration | Restore compatible full snapshot |

## 13. Eight SRE runbooks

### RB-01 CI job outage

**Procedure:** Identify job owner, trigger, queue, agent and last-good build; restore service and verify result.

**Exit criteria:** authorized job, correct trigger and agent isolation, protected outputs, observable result, retention and handoff evidence.

### RB-02 Webhook and schedule failure

**Procedure:** Review provider delivery, TLS, signature, cron timezone and missed-work reconciliation.

**Exit criteria:** authorized job, correct trigger and agent isolation, protected outputs, observable result, retention and handoff evidence.

### RB-03 Parameter or credential incident

**Procedure:** Stop risky job, revoke exposed tokens, validate input and re-establish trust boundaries.

**Exit criteria:** authorized job, correct trigger and agent isolation, protected outputs, observable result, retention and handoff evidence.

### RB-04 Workspace/artifact failure

**Procedure:** Check agent filesystem, permissions, archive paths, JUnit reports and teardown ordering.

**Exit criteria:** authorized job, correct trigger and agent isolation, protected outputs, observable result, retention and handoff evidence.

### RB-05 Notification and logging incident

**Procedure:** Validate destinations, delivery, masking, deduplication, redaction and escalation.

**Exit criteria:** authorized job, correct trigger and agent isolation, protected outputs, observable result, retention and handoff evidence.

### RB-06 Retention and storage incident

**Procedure:** Review disk/inodes, build discarder, external repository and legal-hold constraints.

**Exit criteria:** authorized job, correct trigger and agent isolation, protected outputs, observable result, retention and handoff evidence.

### RB-07 Change rollback

**Procedure:** Revert reviewed Jenkinsfile/Job DSL and tested plugins; verify build and trigger behavior.

**Exit criteria:** authorized job, correct trigger and agent isolation, protected outputs, observable result, retention and handoff evidence.

### RB-08 Operational acceptance

**Procedure:** Collect gate evidence, owner approvals, SLO baselines, residual risks and handoff.

**Exit criteria:** authorized job, correct trigger and agent isolation, protected outputs, observable result, retention and handoff evidence.

## 14. Production readiness gates

| Gate | Requirement | Lab evidence |
|---|---|---|
| G1 | Controller built-in executors zero | Node configuration |
| G2 | Versioned Pipeline/owner and RBAC | Job and governance review |
| G3 | Parameter allowlist and dry-run | Local smoke |
| G4 | SUCCESS/FAILURE result handling | Two local builds |
| G5 | Signed webhook/cron/DST design | Staging plan |
| G6 | Isolated agent and workspace | Staging-only test |
| G7 | JUnit/artifact integrity and retention | Staging-only test |
| G8 | Notifications/log redaction | Design or staging delivery |
| G9 | Incident drills and rollback | Tabletop record |
| G10 | SLO, evidence, cleanup and approvals | Reviewer sign-off |

**Important:** Educational pass is not production certification; gates G5–G8 require separate live staging evidence for a go-live decision.

## 15. Assessment — 100 points

| Domain | Points |
|---|---:|
| Job design, migration and governance | 20 |
| Triggers, parameters and security | 20 |
| Agent/workspace/artifact/test architecture | 20 |
| Logs, results, notifications and retention | 15 |
| SRE incident response and rollback | 15 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Educational pass:** 90+ with no security-critical failures. Production acceptance requires independent controls verification and named approval.

## 16. Cleanup

```bash
docker stop jenkins-ch020
docker rm jenkins-ch020
# Destructive only after verifying exclusive lab ownership:
docker volume rm jenkins-ch020-home
```

**Part 04 complete:** Jenkins Jobs and Pipeline Fundamentals — Chapters 016–020.

**Next:** Chapter 021 — Declarative Pipeline Syntax, Stages, Steps and Directives, beginning Part 05 — Declarative and Scripted Pipelines.
