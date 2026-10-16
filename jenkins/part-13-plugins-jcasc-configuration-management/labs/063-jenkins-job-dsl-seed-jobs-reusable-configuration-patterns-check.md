# Chapter 063 — Hands-on Lab: Jenkins Job DSL, Seed Jobs and Reusable Configuration

**Environment:** Disposable Jenkins LTS, Job DSL, Pipeline, Folders and Git plugins; protected synthetic SCM repo and trusted seed agent. Do not run deletion experiments on production.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record Job DSL/core/plugin versions | Baseline |
| 02 | Architecture | Diagram JCasC/seed/jobs | Diagram |
| 03 | Repository | Create jobs/ and Jenkinsfile.seed | Git |
| 04 | Folder | Generate engineering/team-a | Job |
| 05 | Pipeline | Generate service-ci Pipeline job | Job |
| 06 | SCM | Configure protected test repository | Config |
| 07 | Jenkinsfile | Verify scriptPath | Build |
| 08 | Seed | Execute trusted seed Pipeline | Logs |
| 09 | Idempotency | Run seed twice | Diff |
| 10 | Catalog | Generate two data-driven jobs | Inventory |
| 11 | Multibranch | Generate test multibranch job | Index |
| 12 | PR trust | Deny untrusted secret access | Denied |
| 13 | RBAC | Verify folder isolation | Denied |
| 14 | Sandbox | Test script approval boundary | Result |
| 15 | Deletion | Test removedJobAction IGNORE | Preserved |
| 16 | Drift | Manually edit synthetic job | Diff |
| 17 | Reconcile | Restore generated configuration | Result |
| 18 | Failure | Inject unsupported DSL method | Error |
| 19 | Recovery | Restore prior approved DSL | RTO |
| 20 | Review | Complete acceptance and sign-off | Report |

## 12 troubleshooting drills

1. Missing Job DSL plugin.
2. Unsupported DSL method.
3. Missing folder creation.
4. Seed permission denied.
5. Script approval rejection.
6. Wrong SCM branch.
7. Missing Jenkinsfile.
8. Duplicate job name.
9. Multibranch indexing failure.
10. Accidental removal policy.
11. Untrusted PR secret access.
12. Plugin upgrade breaks DSL.

## Example seed invocation

```groovy
jobDsl(
    targets: 'jobs/*.groovy',
    removedJobAction: 'IGNORE',
    removedViewAction: 'IGNORE',
    lookupStrategy: 'JENKINS_ROOT',
    sandbox: true
)
```

Use this only in a trusted seed Pipeline with the Job DSL plugin installed. Confirm syntax against the installed plugin.

## Evidence template

```text
UTC timestamp:
Jenkins/plugin versions:
Seed SCM revision:
Generated folders/jobs:
Second-run idempotency:
SCM/Jenkinsfile validation:
Multibranch trust policy:
RBAC negative tests:
Deletion safety:
Injected failure:
Recovery duration:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Seed SCM protected and access restricted.
- [ ] Generated jobs match approved catalog.
- [ ] Second seed run idempotent.
- [ ] No accidental job deletion.
- [ ] PR secrets isolation validated.
- [ ] Recovery and reviewer sign-off complete.

**Related:** [Chapter 063 — Jenkins Job DSL, Seed Jobs and Reusable Configuration Patterns](../063-jenkins-job-dsl-seed-jobs-reusable-configuration-patterns.md).
