# Chapter 022 — Declarative Pipeline Agents, Environment, Parameters and Conditional Execution

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 05:** Declarative and Scripted Pipelines  
**Chapter:** 022 / 100  
**Companion lab:** [022 — Agents, Environment, Parameters and Conditions Check](labs/022-declarative-agents-environment-parameters-conditions-check.md)

> **Safety:** The runnable smoke uses `agent none` with no shell or workspace operations. Actual builds must run on separately provisioned isolated agents. Never enable controller executors to resolve queued jobs; never print secrets or accept unvalidated deployment targets.

## 1. Learning objectives

Choose pipeline- and stage-level agents; reason about `agent none`, labels, workspaces and container agents; use typed parameters, environment scope and Jenkins credentials safely; control execution with `when`, `beforeAgent`, branch and expression gates; diagnose queueing, secret leakage and conditional execution.

## 2. Execution architecture

```text
protected SCM -> Jenkinsfile
                   |
           pipeline agent none
                   |
          typed parameter validation
                   |
              when condition
                   |
         +---------+-----------+
         |                     |
      skip stage           allocate agent
                               |
                       isolated workspace
                               |
                       build/test/deploy
                               |
                         post + audit
```

Agent selection determines execution context, not authorization by itself. Keep privileged deployment jobs in trusted folders with separate identities, approved agents and branch protection.

## 3. Agent strategies

| Agent directive | Meaning | Operational guidance |
|---|---|---|
| `agent any` | Any eligible executor | Avoid for privileged production jobs |
| `agent none` | No global agent | Use for orchestration and stage-scoped allocation |
| `agent { label 'lab-linux' }` | Eligible matching agent | Restrict labels to approved pools |
| `agent { node { label 'lab-linux' } }` | Node with options such as custom workspace | Avoid shared paths |
| `agent { docker { image '...' } }` | Docker-based execution (supported setup) | Pin images, verify runtime and trust |
| Stage-level `agent` | Allocated for one stage | Useful for heterogeneous builds |

Labels are not a security boundary. Never run untrusted code on a privileged agent merely because the label matches.

## 4. Environment variable scope

```groovy
pipeline {
  agent none
  environment {
    APP_NAME = 'demo-service'
    REGION = 'us-east-1'
  }
  stages {
    stage('Scope') {
      environment {
        REGION = 'us-west-2'
      }
      steps {
        echo "App=${env.APP_NAME}; stageRegion=${env.REGION}"
      }
    }
    stage('Global') {
      steps { echo "globalRegion=${env.REGION}" }
    }
  }
}
```

Stage-level environment overrides apply only within the stage. Keep environment values non-sensitive unless bound through Jenkins Credentials.

## 5. Typed parameters and input validation

```groovy
parameters {
  choice(name: 'TARGET', choices: ['dev', 'staging'])
  booleanParam(name: 'DRY_RUN', defaultValue: true)
  string(name: 'RELEASE_TAG', defaultValue: 'v0.0.0')
}
```

Validate `TARGET` against an allowlist and `RELEASE_TAG` against a strict release-tag pattern before using either in SCM, artifact names or shell commands. Use `params.DRY_RUN` as a boolean rather than comparing to a string.

## 6. Runnable controller-only Pipeline

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
      environment {
        REGION = 'us-west-2'
      }
      steps { echo "Staging region=${env.REGION}" }
    }
    stage('Global scope') {
      steps { echo "Global region=${env.REGION}" }
    }
  }
  post {
    success { echo 'Validation successful' }
    failure { echo 'Validation failed' }
    always { echo 'No deployment executed' }
  }
}
```

Expected: dev skips the staging stage; staging executes it; `REGION` reverts to global scope in the final stage. Invalid release tags fail before any deployment. All steps are lightweight and require no workspace.

## 7. Stage-level isolated agent example

Only run on a pre-provisioned approved Linux agent labeled `lab-linux`:

```groovy
pipeline {
  agent none
  stages {
    stage('Build') {
      agent { label 'lab-linux' }
      when {
        beforeAgent true
        expression { true }
      }
      options { timeout(time: 10, unit: 'MINUTES') }
      steps {
        sh '''
          set -eu
          printf 'Agent workspace: %s\n' "$WORKSPACE"
        '''
      }
    }
  }
}
```

With no matching agent the stage queues; do not enable controller executors. Keep workspace paths job-owned.

## 8. Secure credential binding

For approved staging only, with a folder-scoped Jenkins Secret Text credential ID `staging-api-token`:

```groovy
pipeline {
  agent { label 'lab-linux' }
  stages {
    stage('Scoped credentials') {
      steps {
        withCredentials([string(credentialsId: 'staging-api-token', variable: 'API_TOKEN')]) {
          sh '''
            set +x
            test -n "$API_TOKEN"
            echo "Credential available; value not printed."
          '''
        }
      }
    }
  }
}
```

This validates presence only; do not print token values, pass them in process arguments, or persist them in artifacts. Scope credentials by folder, identity and trust boundary. The example requires Credentials Binding support.

## 9. Conditional execution

Use `when { expression { ... } }` for validated parameters; `branch` for multibranch context; `beforeAgent true` to avoid allocating a stage agent for a skipped stage. Be aware that SCM metadata such as `changeset` may not exist without checkout/changelog collection.

## 10. Stage ordering and timeout semantics

A top-level agent may allocate before stages; stage-level agents allow targeted allocation. Timeouts may include agent provisioning depending on scope. Define separate queue and runtime SLOs and monitor resource acquisition.

## 11. Environment promotion and policy

Use protected branches, reviewed environment mapping, dry-run defaults, explicit approvals and least-privilege credentials. Avoid letting a user-supplied string directly determine a deployment namespace, account or credential ID.

## 12. SRE observability

Measure agent queue p95, allocation failures, skipped-stage rate, invalid-parameter attempts, secret masking incidents, conditional gate errors, environment drift and promotion approval outcomes.

## 13. Twenty troubleshooting scenarios

| # | Symptom | Investigation | Safe recovery |
|---|---|---|---|
| 1 | No matching agent | Agent label and queue reason | Restore eligible isolated agent |
| 2 | Controller executes untrusted shell | Built-in executors and job label | Set controller executors zero and quarantine |
| 3 | Agent pod cannot start | Provisioning logs, image pull, quota | Repair staging pool |
| 4 | Stage uses wrong node | Top-level/stage agent precedence | Set explicit trusted label |
| 5 | Workspace unavailable | agent none and workspace step | Allocate isolated agent |
| 6 | Docker agent lacks daemon | Docker agent requirements and runtime | Use approved container runtime |
| 7 | Environment value unexpectedly empty | Pipeline vs stage scope and interpolation | Correct scope and reference |
| 8 | Credential variable leaks | Groovy interpolation, console and RBAC | Rotate and use safe binding |
| 9 | Credentials ID not found | Folder scope and credential type | Correct least-privilege credential |
| 10 | Choice parameter not respected | Default, build parameters and validation | Enforce allowlist |
| 11 | String parameter injection | Shell interpolation and untrusted input | Validate and avoid GStrings |
| 12 | Boolean parameter interpreted as string | Typed params vs env representation | Use params.FLAG as boolean |
| 13 | when branch never matches | Multibranch metadata and branch context | Use correct SCM context |
| 14 | when changeset unexpectedly false | SCM changelog availability | Validate checkout/changelog |
| 15 | beforeAgent not applied | Directive placement and plugin support | Move when option into stage |
| 16 | Skipped stage still requests agent | when evaluation order | Use beforeAgent true when appropriate |
| 17 | Stage-level timeout includes allocation | Timeout scope and agent acquisition | Define expected budget |
| 18 | Parallel branches share state | Agent/workspace/lock configuration | Isolate and serialize |
| 19 | Untrusted PR gets prod credentials | SCM trust and folder RBAC | Separate trusted pipelines |
| 20 | Environment drift across promotion | Hardcoded vars and configuration | Use reviewed environment mapping |

## 14. Eight SRE runbooks

### RB-01 Agent queue starvation

**Procedure:** Inspect label, node status, executors, Kubernetes pod events and provisioning; restore trusted capacity.

**Exit criteria:** agent trust boundaries preserved, validated inputs, correct environment scope, expected conditional execution and redacted evidence.

### RB-02 Agent trust violation

**Procedure:** Stop affected job, revoke privileged tokens, verify controller executors zero and reestablish isolation.

**Exit criteria:** agent trust boundaries preserved, validated inputs, correct environment scope, expected conditional execution and redacted evidence.

### RB-03 Parameter validation incident

**Procedure:** Inspect typed parameters, defaults, input allowlist and approval; reject unsafe targets.

**Exit criteria:** agent trust boundaries preserved, validated inputs, correct environment scope, expected conditional execution and redacted evidence.

### RB-04 Credential leak

**Procedure:** Restrict console, rotate secrets, inspect Groovy interpolation and switch to scoped binding.

**Exit criteria:** agent trust boundaries preserved, validated inputs, correct environment scope, expected conditional execution and redacted evidence.

### RB-05 Conditional stage skipped

**Procedure:** Review branch/parameter context, when expression, beforeAgent and SCM metadata.

**Exit criteria:** agent trust boundaries preserved, validated inputs, correct environment scope, expected conditional execution and redacted evidence.

### RB-06 Environment drift

**Procedure:** Compare pipeline/stage scopes, config revision and target mapping; revert reviewed change.

**Exit criteria:** agent trust boundaries preserved, validated inputs, correct environment scope, expected conditional execution and redacted evidence.

### RB-07 Timeout/provisioning regression

**Procedure:** Separate queue wait, agent acquisition and stage runtime; adjust bounds and capacity.

**Exit criteria:** agent trust boundaries preserved, validated inputs, correct environment scope, expected conditional execution and redacted evidence.

### RB-08 Release handoff

**Procedure:** Record trusted agent pool, credentials scope, parameter gates, environment promotion and rollback.

**Exit criteria:** agent trust boundaries preserved, validated inputs, correct environment scope, expected conditional execution and redacted evidence.

## 15. Acceptance gates

| Gate | Requirement |
|---|---|
| G1 | Controller built-in executors zero |
| G2 | Agent types and trust boundaries explained |
| G3 | Typed parameters validated |
| G4 | Dev/staging condition verified |
| G5 | Global versus stage environment scope verified |
| G6 | Invalid release tag rejected |
| G7 | beforeAgent behavior understood |
| G8 | Secret binding reviewed without exposing token |
| G9 | Three incident diagnoses and rollback |
| G10 | Redacted evidence and cleanup complete |

## 16. Assessment — 100 points

| Domain | Points |
|---|---:|
| Agent selection and isolation | 25 |
| Parameters and validation | 20 |
| Environment scope and credentials | 20 |
| Conditional execution | 15 |
| Troubleshooting and monitoring | 10 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ with all critical security gates. Controller-only smoke does not prove agent-backed credential or build execution.

## 17. Cleanup

```bash
docker stop jenkins-ch022
docker rm jenkins-ch022
# Destructive only if exclusively lab-owned:
docker volume rm jenkins-ch022-home
```

**Next:** Chapter 023 — Declarative Pipeline Post Conditions, Error Handling, Timeouts and Retries.
