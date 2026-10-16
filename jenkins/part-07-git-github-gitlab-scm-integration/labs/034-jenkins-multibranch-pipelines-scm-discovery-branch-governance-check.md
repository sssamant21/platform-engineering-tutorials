# Chapter 034 — Hands-on Lab: Multibranch Discovery, Branch Governance and Recovery

**Environment:** Disposable Jenkins controller, isolated Linux agent and nonproduction GitHub/GitLab repository.

## Preparation

Prepare a repository with `main`, `feature/demo`, `release/test`, a PR/MR, `README.md`, `Jenkinsfile` and executable `ci/test.sh`. Record Jenkins core/plugin versions, provider credentials ID, expected refs and commit SHAs.

## 20 hands-on exercises

| # | Exercise | Procedure | Expected evidence |
|---|---|---|---|
| 01 | Baseline inventory | Record SCM source and plugin versions | Configuration record |
| 02 | Protected branch | Review main protection settings | Governance evidence |
| 03 | Create Multibranch job | Configure provider source | Job created |
| 04 | Branch discovery | Enable appropriate branch trait | Main/feature found |
| 05 | Initial scan | Run indexing | Scan log captured |
| 06 | Main build | Run fixture on main | Correct SHA |
| 07 | Feature build | Run fixture on feature | Correct SHA |
| 08 | Release branch | Discover `release/test` | Branch job |
| 09 | Origin PR/MR | Open same-repo change request | Change job discovered |
| 10 | Head/merge strategy | Compare revision selection | SHA differences recorded |
| 11 | Branch environment | Inspect `BRANCH_NAME` and `CHANGE_ID` | Context documented |
| 12 | Branch-aware stage | Add safe `when` condition | Expected stage selection |
| 13 | Webhook | Push fixture change | Event → scan/build correlation |
| 14 | Missing Jenkinsfile | Create branch without Jenkinsfile | Diagnostic observed |
| 15 | Filter behavior | Narrow branch name discovery | Only intended heads |
| 16 | Orphan lifecycle | Delete disposable feature branch | Retention policy observed |
| 17 | Scan tuning | Change test scan cadence | API/load evidence |
| 18 | Invalid credentials | Rotate/disable test token briefly | Fail and recover |
| 19 | Indexing storm simulation | Trigger limited repeated test scans | Backlog and controls observed |
| 20 | Recovery review | Restore baseline traits and run scan | Known-good state |

## 12 troubleshooting drills

1. Branch source credential expired.
2. Branch filter excludes expected ref.
3. Origin PR discovery disabled.
4. Fork PR blocked by trust strategy.
5. Jenkinsfile path incorrect.
6. Git fetch fails due to missing refspec.
7. Webhook delivery accepted but no indexing.
8. Head/merge SHA mismatch.
9. Provider API rate-limit response.
10. Orphaned job removed unexpectedly.
11. Excessive child-job discovery.
12. Duplicate webhook and periodic scan builds.

For each drill capture **symptom → source log → hypothesis → fix → retest**. If a scenario is unavailable or unsafe, record it as blocked.

## Fixture Jenkinsfile

```groovy
pipeline {
    agent { label 'isolated-linux' }
    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git rev-parse HEAD'
            }
        }
        stage('Fixture tests') {
            steps { sh './ci/test.sh' }
        }
        stage('Main-only validation') {
            when {
                allOf {
                    branch 'main'
                    not { changeRequest() }
                }
            }
            steps { echo 'Main branch checks executed' }
        }
    }
}
```

## Evidence template

```text
UTC timestamp:
Jenkins version/plugins:
SCM provider/repository:
Discovery traits:
Branch/PR/MR:
Expected SHA / checkout SHA:
Indexing duration:
Webhook delivery:
Job count before/after:
Orphan retention:
Failure injection:
Recovery and retest:
Reviewer:
```

## Acceptance criteria

- [ ] All 20 exercises attempted with evidence.
- [ ] All 12 drills completed or marked blocked.
- [ ] Branch and PR/MR jobs discovered as expected.
- [ ] Correct checkout revision recorded.
- [ ] Fork trust and credentials reviewed.
- [ ] Webhook and indexing correlation verified.
- [ ] Orphaned item strategy and scan limits documented.
- [ ] Recovery runbooks validated on disposable resources.

**Related:** [Chapter 034 — Multibranch Pipelines](../034-jenkins-multibranch-pipelines-scm-discovery-branch-governance.md).
