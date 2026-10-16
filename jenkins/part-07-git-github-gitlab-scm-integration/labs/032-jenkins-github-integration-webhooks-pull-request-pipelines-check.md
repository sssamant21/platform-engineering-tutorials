# Chapter 032 — Hands-on Lab: GitHub Webhooks and Pull Request Pipelines

**Scope:** Disposable Jenkins controller, isolated Linux agent and GitHub test repository. Never use production secrets or privileged fork PR builds.

## Setup

Create a GitHub test repository with a `README.md`, fixture `Jenkinsfile`, protected main branch and test branch. Configure a narrowly scoped GitHub App or repository token appropriate for GitHub Branch Source. Record Jenkins core, plugin versions, GitHub repository, credential ID and initial commit SHA.

## 20 hands-on exercises

| # | Exercise | Procedure | Expected evidence |
|---|---|---|---|
| 01 | Baseline | Run fixture checkout via Jenkins | Revision recorded |
| 02 | Plugin audit | Record GitHub Branch Source/Git versions | Compatibility list |
| 03 | GitHub App scope | Review installation repository access | Minimal permissions |
| 04 | Credential storage | Configure Jenkins credential | No secret in logs |
| 05 | Branch protection | Require review on test main | Policy screenshot |
| 06 | Multibranch job | Create GitHub Branch Source job | Source configured |
| 07 | Branch discovery | Scan test repository | Branch job appears |
| 08 | Safe Jenkinsfile | Run checkout/validation | Successful fixture build |
| 09 | Feature branch | Push safe change | New SHA recorded |
| 10 | Origin PR | Open test PR from same repo | PR discovered |
| 11 | PR head vs merge | Compare configured checkout strategies | Revision evidence |
| 12 | Webhook registration | Configure documented endpoint | GitHub delivery visible |
| 13 | Delivery correlation | Push commit and inspect Jenkins | Event → build → SHA |
| 14 | Check reporting | Configure supported publisher if available | Status on correct SHA |
| 15 | Required check | Apply a verified test check context | PR policy validated |
| 16 | Fork trust review | Inspect available fork PR strategy | No privileged secrets |
| 17 | Duplicate event | Repeat safe webhook delivery | No unsafe duplicate side effects |
| 18 | Invalid webhook | Use incorrect test secret | Rejected or flagged appropriately |
| 19 | Credential rotation | Rotate test credential | Access restored and verified |
| 20 | Incident recovery | Disable webhook temporarily, restore and rescan | Recovery record |

## Minimal fixture Jenkinsfile

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
        stage('Fixture validation') {
            steps {
                sh 'test -f README.md && test -f Jenkinsfile'
            }
        }
    }
}
```

A passing fixture validation is not a substitute for real application tests or production required checks.

## 12 troubleshooting drills

1. Incorrect GitHub webhook endpoint.
2. Reverse proxy returns 404 for webhook.
3. Test webhook secret mismatch.
4. GitHub App not installed on fixture repository.
5. Missing repository contents permission.
6. PR discovery trait disabled.
7. Fork PR blocked by trust strategy.
8. GitHub API rate limit encountered (simulate/inspect safely).
9. Delivery succeeds but branch indexing not triggered.
10. Build tests unexpected SHA (head versus merge).
11. Status/check publisher lacks write permission.
12. Duplicate webhook and SCM polling schedule same revision.

For each drill, capture GitHub delivery ID/status, Jenkins indexing/build logs, selected SHA, root cause, remediation and retest. If a drill cannot safely be reproduced, mark it blocked with explanation.

## Evidence template

```text
UTC timestamp:
Jenkins core/plugins:
GitHub fixture repository:
GitHub App / credential ID (no secrets):
Branch and PR number:
Webhook delivery ID and HTTP status:
Expected head/merge SHA:
Actual checked-out SHA:
Jenkins build URL/status:
GitHub check context and target SHA:
Fault injected / symptom:
Root cause / recovery:
Reviewer:
```

## Acceptance checklist

- [ ] All 20 exercises attempted and documented.
- [ ] All 12 troubleshooting drills completed or explicitly blocked.
- [ ] Multibranch job discovers intended branches and origin PR.
- [ ] Webhook delivery maps to the intended Jenkins revision.
- [ ] Fork PR trust and credential isolation reviewed.
- [ ] Status/check is correctly attached to tested SHA if enabled.
- [ ] Rotation, webhook outage and rescan runbooks verified.
- [ ] No production systems or real secrets used.

**Related:** [Chapter 032 — GitHub Integration](../032-jenkins-github-integration-webhooks-pull-request-pipelines.md).
