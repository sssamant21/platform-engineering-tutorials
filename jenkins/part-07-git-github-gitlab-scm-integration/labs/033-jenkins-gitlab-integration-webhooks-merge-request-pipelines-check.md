# Chapter 033 — Hands-on Lab: Jenkins GitLab Integration and Merge Request Pipelines

**Environment:** Disposable Jenkins controller, isolated agent and nonproduction GitLab project. Use test credentials only.

## Setup

Create a GitLab project with `README.md`, `Jenkinsfile` and executable `ci/test.sh`. Record Jenkins core/plugins, GitLab instance version/edition, project URL, credential ID and baseline commit SHA. Choose either GitLab plugin Pipeline or GitLab Branch Source Multibranch integration; note which one is used.

## 20 hands-on exercises

| # | Exercise | Procedure | Expected result |
|---|---|---|---|
| 01 | Plugin inventory | Record GitLab/Git plugins | Version list |
| 02 | Credential scope | Create test project token | Minimal permissions |
| 03 | Jenkins credential | Store scoped identity | No secret in log |
| 04 | Repository fixture | Commit README, Jenkinsfile, test script | SHA captured |
| 05 | SCM checkout | Configure GitLab repo in Jenkins | Fetch succeeds |
| 06 | Revision provenance | Run `git rev-parse HEAD` | Expected SHA |
| 07 | Test execution | Run fixture test script | Exit 0 |
| 08 | Branch protection | Protect main in test project | Policy verified |
| 09 | Feature branch | Push safe change | New SHA |
| 10 | Merge request | Open MR into main | MR visible |
| 11 | MR discovery | Scan or trigger appropriate job | MR build appears |
| 12 | Head vs merge | Compare checkout strategy | Selected SHA documented |
| 13 | Webhook endpoint | Configure plugin-specific URL | Delivery visible |
| 14 | Event correlation | Push change; inspect queue/build | Delivery → SHA |
| 15 | Status publishing | Use supported GitLab status integration | Correct context/SHA |
| 16 | Negative test | Break fixture script | Failed status |
| 17 | Fork trust | Review MR trust/agent policy | Secrets isolated |
| 18 | Token rotation | Revoke/replace test credential | Recovered checkout |
| 19 | Webhook outage | Temporarily disable test webhook | Failure detected |
| 20 | Recovery runbook | Restore webhook, controlled scan/build | End-to-end success |

## Fixture test script

```sh
#!/bin/sh
set -eu
test -f README.md
test -f Jenkinsfile
printf 'GitLab integration fixture passed\n'
```

Make executable with `chmod +x ci/test.sh`. The fixture verifies SCM integration, not production application quality.

## 12 troubleshooting drills

1. GitLab API token expired.
2. Credential missing `read_repository` access.
3. Plugin-specific webhook URL incorrect.
4. Test webhook secret mismatch.
5. Reverse proxy returns 404 or 403.
6. MR discovery disabled.
7. Merge result ref unavailable.
8. SCM checkout of wrong revision.
9. Status publisher cannot write GitLab status.
10. Duplicate trigger from webhook and polling.
11. Fork MR trust restriction.
12. GitLab server TLS chain not trusted.

Record **symptom → evidence → root cause → correction → retest** for each. If a drill is unavailable with the installed plugin, mark blocked and explain rather than guessing.

## Evidence template

```text
UTC timestamp:
Jenkins version and GitLab plugin versions:
GitLab instance / project:
Credential ID (not value):
Branch / MR IID:
Webhook delivery and HTTP response:
Source SHA / target SHA / checkout SHA:
Jenkins build URL and result:
GitLab status context and SHA:
Failure drill:
Root cause:
Recovery and retest:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] GitLab checkout and test fixture work.
- [ ] Webhook event correlated to actual build SHA.
- [ ] MR discovery and fork trust validated.
- [ ] Status correctly reports failure and success if enabled.
- [ ] Credential rotation and outage recovery tested.
- [ ] No production secrets or untrusted privileged agents used.

**Chapter:** [033 — GitLab Integration](../033-jenkins-gitlab-integration-webhooks-merge-request-pipelines.md).
