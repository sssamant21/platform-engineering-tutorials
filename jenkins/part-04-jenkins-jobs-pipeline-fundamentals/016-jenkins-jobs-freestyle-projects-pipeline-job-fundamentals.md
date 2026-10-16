# Chapter 016 — Jenkins Jobs, Freestyle Projects and Pipeline Job Fundamentals

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 04:** Jenkins Jobs and Pipeline Fundamentals  
**Chapter:** 016 / 100  
**Companion lab:** [016 — Jobs, Freestyle and Pipeline Fundamentals Check](labs/016-jenkins-jobs-freestyle-pipeline-fundamentals-check.md)

> **Safety:** Use a disposable localhost Jenkins controller and an isolated agent for any shell commands. The controller built-in node must have **zero executors**. Never place real credentials in job scripts, parameters, logs or screenshots.

## 1. Learning objectives

Create and compare Freestyle and Pipeline jobs; understand job configuration, triggers, parameters, SCM, stages, build history, workspace, artifacts, test results, RBAC and migration patterns; diagnose production failures.

## 2. Job architecture and execution

```text
User / cron / signed SCM webhook
                 |
          Jenkins job definition
          |                    |
       Freestyle             Pipeline
    UI-defined steps     Jenkinsfile (in Git)
          |                    |
          +---- queue + labels +
                      |
             isolated build agent
                      |
             checkout / test / build
                      |
             reports / artifacts
                      |
            build result + retention
```

A job is the reusable definition; a build is one execution of that definition. Jenkins stores metadata on the controller; workspace-dependent commands execute on agents.

## 3. Freestyle versus Pipeline

| Dimension | Freestyle | Pipeline |
|---|---|---|
| Definition | Mostly UI configuration | Jenkinsfile in SCM preferred |
| Logic | Sequential build steps, plugin-specific | Declarative or Scripted stages/steps |
| Review and audit | Harder unless managed with Job DSL | Native Git review and history |
| Branch strategy | Separate jobs or plugin integrations | Multibranch Pipeline support |
| Recovery | UI/XML/Job DSL restoration | Revert reviewed Jenkinsfile |
| Recommended use | Simple legacy tasks, short transitions | Modern enterprise CI/CD |

Use Freestyle for learning and legacy maintenance; prefer Pipeline-as-Code for complex, versioned CI/CD.

## 4. Job types and permissions

Common types: Freestyle project, Pipeline, Multibranch Pipeline, Folder, and Organization Folder (plugin dependent). Separate `Job/Create`, `Job/Configure`, `Job/Build`, `Job/Read` and credential access. Do not grant anonymous build or administrative permissions.

## 5. Lab setup: disposable controller

```bash
docker volume create jenkins-ch016-home
docker run -d --name jenkins-ch016 --restart=no \
  -p 127.0.0.1:8094:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch016-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch016
docker logs --tail 60 jenkins-ch016
docker port jenkins-ch016
```

The mutable LTS tag is acceptable for a disposable lab; pin an approved digest for production. Unlock at `http://127.0.0.1:8094`, install Pipeline plugins if not already present, create a named administrator, and set **Manage Jenkins → Nodes → Built-In Node → executors = 0**.

## 6. Freestyle project: safe configuration

Create **New Item → Freestyle project → `ch016-freestyle-demo`**. Set description and owner. Do not add an Execute shell step unless an isolated Linux agent is configured and assigned through **Restrict where this project can be run**. A Freestyle job without a build agent will remain queued with zero controller executors; that is expected.

For an approved staging agent labeled `lab-linux`, add **Execute shell**:

```bash
set -eu
printf 'Job=%s Build=%s\n' "$JOB_NAME" "$BUILD_NUMBER"
mkdir -p output
printf 'hello from Freestyle\n' > output/result.txt
```

Archive `output/result.txt` using **Post-build Actions → Archive the artifacts**. Set retention to an approved policy.

## 7. Pipeline job: no-agent smoke

Create **New Item → Pipeline → `ch016-pipeline-smoke`** and use:

```groovy
pipeline {
  agent none
  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '10'))
  }
  parameters {
    choice(name: 'ENVIRONMENT', choices: ['dev', 'staging'], description: 'Lab target')
  }
  stages {
    stage('Validate') {
      steps {
        echo "Selected environment: ${params.ENVIRONMENT}"
      }
    }
    stage('Report') {
      steps {
        echo 'Controller orchestrates; shell steps require an agent.'
      }
    }
  }
  post {
    always { echo 'Pipeline finished.' }
  }
}
```

This Pipeline deliberately uses only lightweight steps that do not require a workspace. It can complete while the controller has zero executors.

## 8. Pipeline with a real isolated agent

The following requires an already provisioned and approved Linux agent with label `lab-linux`:

```groovy
pipeline {
  agent { label 'lab-linux' }
  options { timeout(time: 10, unit: 'MINUTES') }
  stages {
    stage('Build') {
      steps {
        sh '''
          set -eu
          mkdir -p output
          printf "artifact\n" > output/build.txt
        '''
      }
    }
  }
  post {
    success { archiveArtifacts artifacts: 'output/*.txt', fingerprint: true }
  }
}
```

With no matching agent, the build queues. Do not enable controller executors as a workaround. Artifact archival requires an agent workspace and a successful file creation step.

## 9. SCM and Jenkinsfile governance

Prefer **Pipeline script from SCM**, a reviewed Jenkinsfile in Git, protected branches and explicit credentials scope. Pin library versions, review pull-request trust and avoid allowing untrusted contributors to alter privileged deployment logic. Configure webhook signatures and narrow token scopes.

## 10. Triggers and parameters

- Manual **Build Now** or **Build with Parameters**.
- Poll SCM or cron only where justified; prefer signed webhooks for prompt SCM events.
- Use parameter validation and allowlists for environment, branch and deployment target.
- Never use password parameters as a substitute for Jenkins Credentials.
- Disable concurrent builds for stateful jobs; use locks for shared resources when supported.

## 11. Artifacts, reports and retention

Archive only required outputs, not credentials or entire workspaces. Use external artifact repositories for large deliverables, publish JUnit XML via `junit` when the plugin is installed, and define build/artifact retention for cost and recovery. Distinguish build result (SUCCESS/UNSTABLE/FAILURE/ABORTED) from stage outcome.

## 12. Migration: Freestyle to Pipeline

Inventory source control, build commands, triggers, credentials, agent labels, artifact patterns and notifications. Reimplement in a Jenkinsfile; run both paths in staging and compare results. Cut over webhook/triggers only after acceptance and keep a rollback plan.

## 13. Twenty troubleshooting scenarios

| # | Symptom | Investigation | Safe recovery |
|---|---|---|---|
| 1 | Freestyle build stays queued | Agent labels, executor occupancy, offline state | Restore matching agent capacity |
| 2 | Pipeline syntax error | Console and Declarative parser message | Validate Jenkinsfile before rerun |
| 3 | Job cannot be created | Item/Job permissions and folder RBAC | Grant scoped permissions |
| 4 | Build cannot access workspace | Agent availability and remote root ACL | Use isolated writable workspace |
| 5 | SCM checkout authentication fails | Credential ID, scope and repository permissions | Repair least-privilege credential |
| 6 | SCM branch not found | Branch specifier and ref inventory | Correct branch configuration |
| 7 | Webhook does not trigger job | Endpoint, signature, trigger and logs | Repair signed webhook integration |
| 8 | Scheduled build not firing | Cron syntax, controller clock and job state | Correct schedule and monitor |
| 9 | Parameterized build receives wrong value | Parameter defaults, validation and downstream mapping | Validate input before execution |
| 10 | Secret appears in console | Job script and credentials handling | Revoke/rotate, restrict logs and fix pipeline |
| 11 | Freestyle shell fails | Interpreter, exit code, PATH and agent toolchain | Repair reproducible environment |
| 12 | Pipeline runs on controller | Built-in executors and agent selection | Set controller executors zero |
| 13 | Job builds concurrently unexpectedly | Concurrency setting and lock design | Disable concurrent builds when required |
| 14 | Build artifacts missing | Archive pattern, workspace and retention | Fix path and artifact policy |
| 15 | JUnit results missing | Test report path and XML generation | Publish valid test reports |
| 16 | Job hangs indefinitely | Timeout settings and blocked steps | Apply bounded timeout and diagnose |
| 17 | Untrusted PR reaches deployment | SCM trust and credential scope | Quarantine and isolate jobs |
| 18 | Workspace cleanup deletes shared data | Workspace ownership and cleanup pattern | Restore safe per-job cleanup |
| 19 | Plugin upgrade breaks job | Plugin/core/Java compatibility and change diff | Restore tested versions |
| 20 | Job configuration drift | Job XML, JCasC/Job DSL and Git review | Reconcile source-controlled definition |

## 14. Eight SRE runbooks

### RB-01 Job creation and permissions

**Procedure:** Check folder RBAC, item naming, audit trail and approved ownership; correct narrowly scoped access.

**Exit criteria:** authorized job configuration, correct agent routing, reproducible build, protected secrets, validated artifacts and owner handoff.

### RB-02 Queued job

**Procedure:** Check queue reason, label expression, online agents, executors and provisioning; restore eligible capacity.

**Exit criteria:** authorized job configuration, correct agent routing, reproducible build, protected secrets, validated artifacts and owner handoff.

### RB-03 SCM and webhook failure

**Procedure:** Inspect credential scope, branch/ref, webhook signature and provider delivery; repair integration.

**Exit criteria:** authorized job configuration, correct agent routing, reproducible build, protected secrets, validated artifacts and owner handoff.

### RB-04 Pipeline execution failure

**Procedure:** Review stage result, console, environment/toolchain, timeout and recent changes; reproduce in staging.

**Exit criteria:** authorized job configuration, correct agent routing, reproducible build, protected secrets, validated artifacts and owner handoff.

### RB-05 Secret exposure

**Procedure:** Stop affected jobs, revoke/rotate, preserve redacted evidence and review credential access.

**Exit criteria:** authorized job configuration, correct agent routing, reproducible build, protected secrets, validated artifacts and owner handoff.

### RB-06 Build artifact/test regression

**Procedure:** Validate workspace, archive patterns, JUnit XML, retention and external artifact store.

**Exit criteria:** authorized job configuration, correct agent routing, reproducible build, protected secrets, validated artifacts and owner handoff.

### RB-07 Job configuration rollback

**Procedure:** Restore reviewed Jenkinsfile/Job DSL and compatible plugins; verify a representative build.

**Exit criteria:** authorized job configuration, correct agent routing, reproducible build, protected secrets, validated artifacts and owner handoff.

### RB-08 Production job handoff

**Procedure:** Document owner, labels, triggers, SLO, retention, alerting, change controls and rollback.

**Exit criteria:** authorized job configuration, correct agent routing, reproducible build, protected secrets, validated artifacts and owner handoff.

## 15. Acceptance gates

| Gate | Requirement |
|---|---|
| G1 | Built-in node executors zero |
| G2 | Freestyle and Pipeline differences explained |
| G3 | Freestyle job created without unsafe controller execution |
| G4 | No-agent Pipeline completes successfully |
| G5 | Parameters and concurrency controls verified |
| G6 | Agent-backed job queue behavior explained |
| G7 | SCM/webhook and credentials trust model documented |
| G8 | Artifacts, reports and retention policy specified |
| G9 | Three incidents and rollback rehearsed |
| G10 | Evidence redacted and lab cleanup complete |

## 16. Assessment — 100 points

| Domain | Points |
|---|---:|
| Job types and architecture | 20 |
| Freestyle configuration | 15 |
| Pipeline and parameters | 25 |
| SCM, security and agent isolation | 15 |
| Troubleshooting, artifacts and operations | 15 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ with mandatory security gates. A localhost smoke test is not production go-live evidence.

## 17. Cleanup

```bash
docker stop jenkins-ch016
docker rm jenkins-ch016
# Destructive only if exclusively lab-owned:
docker volume rm jenkins-ch016-home
```

**Next:** Chapter 017 — Jenkins Build Triggers, Parameters and Scheduling.
