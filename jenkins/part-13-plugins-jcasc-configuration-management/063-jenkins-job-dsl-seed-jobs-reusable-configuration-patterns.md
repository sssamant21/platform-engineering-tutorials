# Chapter 063 — Jenkins Job DSL, Seed Jobs and Reusable Configuration Patterns

**Part 13 — Plugins, JCasC and Configuration Management**  
**Audience:** Jenkins administrators, platform/SRE, DevOps and release engineering  
**Prerequisites:** Chapters 061–062, disposable Jenkins LTS, Job DSL plugin, Pipeline and Git plugins, reviewed JCasC baseline.

## Learning outcomes

Generate Jenkins jobs from version-controlled Job DSL; operate seed jobs safely; design reusable folders, multibranch jobs and pipeline templates; test changes before deployment; prevent accidental job deletion, privilege escalation and drift.

## 1. Architecture

```text
Git: jobs/*.groovy + Jenkinsfiles
         ↓ protected PR + tests
Seed Pipeline (trusted only)
         ↓ Job DSL plugin
Jenkins folders / pipeline jobs / multibranch jobs
         ↓ SCM Jenkinsfile
Build/test/deploy Pipelines
```

**Distinction:** JCasC configures controller and supported plugin settings. Job DSL generates and updates jobs. Jenkinsfiles define build logic. All three should be versioned, reviewed and validated.

## 2. Repository layout

```text
jenkins-as-code/
├── casc/
├── plugins.txt
├── jobs/
│   ├── folders.groovy
│   ├── applications.groovy
│   └── releases.groovy
├── Jenkinsfile.seed
├── Jenkinsfile.app
├── tests/
│   └── acceptance.md
└── README.md
```

Protect the seed job and its SCM repository as privileged configuration code. Untrusted contributors must not modify Job DSL that can create or reconfigure privileged jobs.

## 3. Folder DSL

```groovy
folder('engineering') {
    displayName('Engineering')
    description('Managed by Job DSL; do not edit manually')
}
folder('engineering/team-a') {
    displayName('Team A')
}
folder('releases') {
    displayName('Releases')
}
folder('releases/staging') {
    displayName('Staging Releases')
}
```

Run folder definitions before nested jobs if needed. Folder plugin is required. Names and paths should be deterministic and environment-independent where possible.

## 4. Pipeline job DSL

```groovy
pipelineJob('engineering/team-a/service-ci') {
    description('Generated from approved Job DSL')
    definition {
        cpsScm {
            scm {
                git {
                    remote {
                        url('https://github.com/example-org/example-service.git')
                    }
                    branch('*/main')
                }
            }
            scriptPath('Jenkinsfile')
            lightweight(true)
        }
    }
    logRotator {
        numToKeep(30)
    }
}
```

Replace the example SCM URL with an approved repository. Depending on Job DSL and plugin versions, DSL method availability and Git configuration differ; validate on the installed plugins and use the Job DSL API viewer.

## 5. Multibranch Pipeline pattern

```groovy
multibranchPipelineJob('engineering/team-a/service-multibranch') {
    branchSources {
        branchSource {
            source {
                git {
                    id('team-a-service-git')
                    remote('https://github.com/example-org/example-service.git')
                    credentialsId('')
                    includes('*')
                }
            }
        }
    }
    orphanedItemStrategy {
        discardOldItems {
            numToKeep(10)
        }
    }
}
```

**Version-sensitive example:** SCM source DSL is plugin-dependent; some versions require different nested structures or traits. Use the Job DSL API viewer for the installed Git/Branch API plugins. For GitHub/GitLab PRs, prefer the corresponding maintained branch-source plugin and explicit trust policies. Do not expose release secrets to untrusted PR branches.

## 6. Seed Pipeline

```groovy
pipeline {
    agent { label 'trusted-seed-agent' }
    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
    }
    stages {
        stage('Checkout approved DSL') {
            steps { checkout scm }
        }
        stage('Generate jobs') {
            steps {
                jobDsl(
                    targets: 'jobs/*.groovy',
                    removedJobAction: 'IGNORE',
                    removedViewAction: 'IGNORE',
                    lookupStrategy: 'JENKINS_ROOT',
                    sandbox: true
                )
            }
        }
    }
}
```

**Safety:** `removedJobAction: 'IGNORE'` prevents automatic deletion during early rollout; choose explicit retirement after inventory and approval. Sandbox restrictions may require script approvals. Do not broadly approve arbitrary methods or grant untrusted authors access to seed SCM.

## 7. Reusable patterns

Use data-driven DSL with a reviewed application catalog:

```groovy
def apps = [
    [name: 'service-a', repo: 'https://github.com/example-org/service-a.git'],
    [name: 'service-b', repo: 'https://github.com/example-org/service-b.git']
]
apps.each { app ->
    pipelineJob("engineering/team-a/${app.name}") {
        definition {
            cpsScm {
                scm {
                    git {
                        remote { url(app.repo) }
                        branch('*/main')
                    }
                }
                scriptPath('Jenkinsfile')
            }
        }
    }
}
```

The data catalog must be trusted; validate job names, repository URLs, branch names and credential IDs before generation. Avoid dynamic evaluation of untrusted DSL.

## 8. JCasC and seed bootstrap

JCasC can configure a Job DSL seed mechanism through supported plugin integrations, but availability and YAML shape depend on installed plugins. Prefer a documented bootstrap sequence:
1. Install reviewed core/plugins.
2. Apply validated JCasC security and controller config.
3. Create trusted seed job through approved bootstrap.
4. Execute seed job from protected Git revision.
5. Validate generated jobs and permissions.
6. Record Git SHA, generated inventory and audit event.

Never bootstrap privileged jobs from an unreviewed branch.

## 9. Testing strategy

| Gate | Validation |
|---|---|
| Syntax | Groovy parse / Job DSL test harness |
| API compatibility | Installed Job DSL plugin reference |
| Generated inventory | Expected folders/jobs present |
| Idempotency | Second seed run produces no unintended changes |
| Deletion safety | Missing DSL does not delete jobs unexpectedly |
| SCM | Correct repository/branch/Jenkinsfile |
| Authorization | Team isolation and no untrusted Configure |
| Secrets | No production credential in PR jobs |
| Pipeline | Representative CI/release smoke tests |
| Rollback | Restore previous DSL revision safely |

## 10. Change management

Require PR review, CODEOWNERS, static checks, generated inventory diff, staging seed run, approval for production folder/job changes, change ticket and post-deployment audit. Use a single controlled seed job per scope to avoid competing writers. Prefer separate release configuration ownership for production.

## 11. Drift and reconciliation

Manual UI edits may be overwritten by the next seed run. Compare generated job configuration with approved DSL and audit changes. Do not blindly run seed jobs after an incident without verifying the desired Git revision and impact on job history.

## 12. Troubleshooting matrix

| Symptom | Likely cause | Recovery |
|---|---|---|
| DSL method missing | Plugin/API mismatch | Use installed API viewer |
| Folder not found | Creation order/plugin | Create folder first |
| Script approval required | Sandbox method | Review narrow approval |
| Seed job permission denied | Job/Configure/Create | Fix trusted seed role |
| Job points wrong branch | SCM config | Correct DSL |
| Jenkinsfile not found | scriptPath/repo | Validate SCM |
| Duplicate job names | Catalog collision | Enforce unique names |
| Unexpected job deletion | Removed job policy | Restore config/backups |
| Job not updated | Seed scope/ownership | Check generated items |
| Multibranch not indexing | SCM credentials/webhook | Fix source |
| PR accesses secrets | Trust policy | Isolate and revoke |
| Generated job inherits broad RBAC | Folder role | Tighten permissions |
| Seed fails after plugin upgrade | DSL API drift | Restore plugin baseline |
| Job DSL slow | Large catalog/API | Batch/measure |
| Concurrent seeds conflict | Multiple writers | Serialize |
| UI drift reappears | Manual changes | Reconcile Git |

## 13. Production runbooks

### A. New application onboarding
1. Validate owner, repository and branch protection.
2. Add catalog entry and Pipeline definition.
3. Review RBAC, agent and credential boundaries.
4. Run staging seed and smoke tests.
5. Deploy and record generated job inventory.

### B. Seed job change
1. Open protected PR with DSL diff.
2. Validate plugin compatibility and generated inventory.
3. Run staging seed with deletion disabled.
4. Approve production change and run controlled seed.
5. Verify idempotency and audit.

### C. Accidental job deletion
1. Stop seed execution and preserve logs.
2. Identify removed items and previous DSL revision.
3. Restore jobs/state from verified backup where needed.
4. Reapply reviewed DSL with safe removal policy.
5. Validate history, credentials and access.

### D. Unauthorized generated job
1. Disable affected job and preserve config.
2. Review seed SCM commit, author and approvals.
3. Revoke exposed credentials and check downstream actions.
4. Restore trusted DSL revision.
5. Correct permissions and complete RCA.

### E. Plugin/API compatibility incident
1. Capture Job DSL plugin/core versions.
2. Identify unsupported DSL method.
3. Test compatible syntax or plugin version in staging.
4. Restore last known-good seed/image if required.
5. Re-run generation and acceptance.

## 14. Acceptance criteria

- [ ] DSL and Jenkinsfiles stored in protected Git.
- [ ] Seed job restricted to trusted administrators.
- [ ] Folder/job generation deterministic.
- [ ] Second seed run idempotent.
- [ ] Removed job policy safe and reviewed.
- [ ] Multibranch PR trust and credentials isolation tested.
- [ ] Generated RBAC boundaries validated.
- [ ] Plugin API compatibility checked.
- [ ] Rollback and recovery tested.
- [ ] Generated inventory and audit evidence retained.

**Companion:** [Chapter 063 hands-on lab](labs/063-jenkins-job-dsl-seed-jobs-reusable-configuration-patterns-check.md).  
**Next:** Chapter 064 — Jenkins Configuration Drift Detection, Policy Validation and GitOps Governance.
