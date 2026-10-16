# Chapter 031 — Hands-on Lab: Jenkins Git and SCM Integration Fundamentals

**Environment:** Disposable Jenkins controller and isolated agent. Use only test repositories and least-privilege credentials.

## Preparation

Create a fixture Git repository containing a `README.md` and a `Jenkinsfile`. Prepare an isolated agent with Git installed. Record Jenkins version, Git/Git Client plugin versions, repository URL, credential ID (never secret) and baseline revision.

## 18 hands-on exercises

| # | Exercise | Procedure | Expected evidence |
|---|---|---|---|
| 01 | Verify Git | Run `git --version` on agent | Version captured |
| 02 | Network | `git ls-remote` against test repo | Remote HEAD observed |
| 03 | Repository setup | Commit fixture Jenkinsfile | SHA recorded |
| 04 | Read-only identity | Create narrowly scoped credential | Access scope reviewed |
| 05 | HTTPS checkout | Configure Pipeline from SCM | Checkout succeeds |
| 06 | Provenance | Run `git rev-parse HEAD` | SHA matches expected |
| 07 | Explicit Git step | Run `git branch: ..., url: ...` | Workspace populated |
| 08 | SCM context | Use `checkout scm` in SCM-backed job | Selected revision fetched |
| 09 | Inline job contrast | Test `checkout scm` without SCM context | Expected failure documented |
| 10 | Branch update | Push safe fixture commit | New SHA observed on next build |
| 11 | Tag | Create test tag and inspect ref | Tag target recorded |
| 12 | Revision replay | Build a known commit | Same source SHA |
| 13 | Invalid credential | Use incorrect test credential | Authentication fails safely |
| 14 | Invalid ref | Select nonexistent branch | Clear SCM resolution failure |
| 15 | Webhook | Configure provider-specific test webhook | Delivery and build correlation |
| 16 | Duplicate event | Trigger two safe events | Concurrency/idempotency reviewed |
| 17 | SCM interruption | Temporarily block test Git endpoint | Bounded failure and recovery |
| 18 | Runbook review | Simulate expired credential | Rotation and retest evidence |

## Executable fixture

`Jenkinsfile`:

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
                sh '''#!/bin/sh
                    set -eu
                    git rev-parse HEAD
                    git status --short
                    test -f README.md
                '''
            }
        }
    }
}
```

Create a **Pipeline from SCM** job to run this example; an inline Pipeline job may not supply `scm`.

## 12 troubleshooting drills

1. Incorrect HTTPS credential ID.
2. Expired read-only token.
3. Untrusted SSH host key (do not disable verification).
4. Typo in repository URL.
5. Nonexistent branch.
6. Missing tag refspec.
7. Agent missing Git CLI.
8. Workspace permission mismatch.
9. Git server temporarily unavailable.
10. Webhook event filtered out by job configuration.
11. Duplicate webhook and polling triggers.
12. Submodule requiring separate access.

For each, record symptom, logs, hypothesis, safe remediation and successful retest. Mark any unexecutable drill blocked rather than inventing outcomes.

## Evidence template

```text
UTC time:
Jenkins core and plugins:
SCM provider and test repository:
Agent label/image and Git version:
Credential ID (not value):
Expected revision:
Actual git rev-parse HEAD:
Webhook delivery identifier:
Failure injection and root cause:
Recovery steps and retest:
Reviewer:
```

## Acceptance criteria

- [ ] All 18 exercises attempted with results.
- [ ] All 12 troubleshooting drills completed or marked blocked.
- [ ] Git fetch and Jenkins checkout work with scoped credentials.
- [ ] Actual revision is recorded.
- [ ] Negative auth/refspec tests fail safely.
- [ ] Webhook or polling behavior is verified with evidence.
- [ ] No real secrets, production systems or unsafe host-key bypasses used.
- [ ] SCM outage and credential rotation runbooks reviewed.

**Related chapter:** [031 — Git and SCM Integration Fundamentals](../031-jenkins-git-scm-integration-fundamentals.md).
