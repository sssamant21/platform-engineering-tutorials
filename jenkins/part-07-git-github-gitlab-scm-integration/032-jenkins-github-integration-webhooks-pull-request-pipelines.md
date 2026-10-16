# Chapter 032 — Jenkins GitHub Integration, Webhooks and Pull Request Pipelines

**Part 07 — Git, GitHub, GitLab and SCM Integration**  
**Audience:** SRE, DevOps, platform engineers and Jenkins administrators  
**Prerequisites:** Chapter 031; a disposable Jenkins controller; isolated Linux build agent; GitHub test repository with administrator access for webhook configuration; least-privilege GitHub integration identity.

## Learning objectives

Connect Jenkins to GitHub securely; distinguish Git plugin, GitHub plugin and GitHub Branch Source plugin responsibilities; configure Multibranch Pipeline and pull request discovery; verify webhook delivery and build scheduling; publish commit status/check results with appropriately scoped credentials; defend against untrusted PR code; and execute incident, rollback and recovery runbooks.

## 1. Enterprise integration architecture

```text
GitHub organization / repository
  ├─ protected main branch, PRs, review policy
  ├─ GitHub App (preferred where supported) / scoped token
  └─ webhook event (push / pull_request)
       ↓ HTTPS, webhook signature / provider verification
Reverse proxy / ingress
       ↓ GitHub integration endpoint
Jenkins controller
  ├─ GitHub Branch Source plugin: branch / PR discovery
  ├─ SCM revision selection and Jenkinsfile retrieval
  ├─ credentials and job authorization
  └─ build queue / status reporting
       ↓ isolated build agent
Git checkout → lint → test → package
       ↓
GitHub checks/status and Jenkins audit evidence
```

Webhooks are event notifications, not authorization to execute arbitrary code. The Jenkins SCM trust policy and job permissions determine what runs and what secrets may be available.

## 2. Plugin responsibilities

| Component | Primary responsibility |
|---|---|
| Git plugin / Git Client | Fetch and checkout Git revisions |
| Pipeline: SCM Step | `checkout scm` in SCM-aware Pipeline jobs |
| GitHub plugin | General GitHub integration and webhook support |
| GitHub Branch Source | GitHub repository/branch/PR discovery for Multibranch and organization jobs |
| Credentials / Credentials Binding | Controlled authentication and secret use |
| Checks API and supported publisher plugins | Optional check run reporting, subject to plugin compatibility |

Install a reviewed, compatible plugin set. Plugin names, settings and available strategies can change between versions; validate against the actual Jenkins instance rather than assuming every option exists.

## 3. Authentication model

**Preferred for enterprise installations:** a GitHub App where supported by the configured GitHub Branch Source integration. Install only on the test repository, grant minimal repository metadata/content read permissions, and add checks/status write permissions only if reporting is required. GitHub App credentials use an app ID and private key stored in Jenkins' credential store; do not put the key in a Jenkinsfile.

**Alternative:** a narrowly scoped fine-grained personal access token or read-only deploy key, with rotation and ownership documented. Some plugin capabilities may require a different token type or scopes; verify against the plugin's requirements.

Avoid using a personal admin token or granting repository write access to a job that only needs to fetch code. Limit credential scope to the relevant folder and jobs.

## 4. Repository and PR policy

For the fixture GitHub repository:
1. Protect `main` with pull-request review and required status checks as supported by repository settings.
2. Require Jenkinsfile changes to receive explicit review.
3. Restrict direct pushes and release-tag modifications.
4. Configure test-only branch names, e.g. `feature/ci-check`.
5. Keep untrusted fork PRs isolated and without sensitive credentials.

Branch protection and check requirements must avoid deadlocks: ensure the required check name is actually emitted by the configured Jenkins integration.

## 5. Create a GitHub Multibranch Pipeline

1. Install GitHub Branch Source and its reviewed dependencies.
2. Create **New Item → Multibranch Pipeline** on the disposable controller.
3. Under Branch Sources, choose **GitHub** and configure the GitHub App or scoped credential.
4. Select repository owner and test repository.
5. Configure branch discovery, origin PR discovery and fork PR discovery only as appropriate for your threat model.
6. Select a safe trust strategy for forks: do not automatically trust a fork's Jenkinsfile for privileged operations.
7. Set the Jenkinsfile script path, e.g. `Jenkinsfile`.
8. Save, run **Scan Multibranch Pipeline Now**, and inspect discovered branches/PR jobs.

**Critical distinction:** a fork PR's code is untrusted even when the PR is opened against a trusted repository. Jenkins may use a trusted Jenkinsfile revision under some SCM trust strategies, but any checked-out fork code must still be treated as hostile. Do not expose write-capable GitHub credentials, signing keys, deployment secrets or privileged agents to untrusted PR builds.

## 6. Safe fixture Jenkinsfile

```groovy
pipeline {
    agent { label 'isolated-linux' }
    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh '''#!/bin/sh
                    set -eu
                    git rev-parse HEAD
                    test -f README.md
                '''
            }
        }
        stage('Validate') {
            steps {
                sh 'test -f Jenkinsfile'
            }
        }
        stage('Unit tests') {
            steps {
                sh 'echo "Run isolated fixture tests here"'
            }
        }
    }
    post {
        always {
            echo "Build: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
        }
    }
}
```

The example deliberately avoids credentials, deployment and publishing. Replace the placeholder unit-test command with a real test suite before using it as a required quality gate; an `echo` is not test evidence.

## 7. Webhook delivery and verification

GitHub repository → **Settings → Webhooks → Add webhook** (or use the integration's documented auto-registration flow if available). For GitHub Branch Source integrations, a commonly used Jenkins endpoint is:

```text
https://jenkins.example.org/github-webhook/
```

Use the externally reachable HTTPS URL for your Jenkins instance and the exact endpoint supported by your installed plugins. Configure GitHub event selection for push and PR events as required, and a webhook secret where supported. Do not publish the endpoint without reverse-proxy controls and provider-specific validation.

**Validate:** GitHub webhook Recent Deliveries should show successful HTTP delivery, while Jenkins logs should show event handling, branch indexing or scheduling. A 2xx delivery alone does **not** prove that the expected branch build ran.

## 8. PR build strategies

| Strategy | What is tested | Operational caveat |
|---|---|---|
| PR head | Contributor branch commit | May not include current target branch |
| PR merge | Synthetic merge with target branch | Better integration signal, can differ from final merge |
| Origin PR discovery | Same-repository PRs | Still review Jenkinsfile changes |
| Fork PR discovery | External contributor code | Must enforce strict trust and secret isolation |

Actual strategy labels depend on GitHub Branch Source plugin version. Record both PR head SHA and checkout SHA for auditability. For a merge test, these may differ.

## 9. Commit statuses and checks

Some GitHub integrations automatically publish build status or checks when authorized and configured; others require an explicit compatible plugin or publisher. Confirm the actual status/check context, target SHA, repository permissions and retry behavior. Never mark a required check successful based only on webhook delivery or a no-op stage.

A status report must correspond to the revision actually tested. If GitHub rejects publication, inspect permission scope and API rate limits before expanding privileges.

## 10. Webhook reliability patterns

- Expect duplicate, delayed and out-of-order events; use revision-aware scheduling and concurrency controls.
- Keep periodic indexing as a recovery mechanism when appropriate; avoid aggressive polling that overloads GitHub or Jenkins.
- Inspect webhook deliveries and Jenkins branch indexing logs to distinguish provider delivery from Jenkins job execution.
- Rotate webhook secrets using a documented maintenance window and test delivery after rotation.
- Monitor GitHub API rate-limit exhaustion, webhook 4xx/5xx responses, queue latency and build scheduling delay.

## 11. Troubleshooting matrix

| Symptom | Verify | Safe fix |
|---|---|---|
| Webhook 404 | External URL, reverse proxy path, plugin endpoint | Correct routing |
| Webhook 403 | Signature, proxy/WAF policy, Jenkins integration settings | Repair verification; do not disable security |
| Webhook 5xx | Controller/proxy health | Restore service and retry |
| Delivery 2xx, no build | Event filter, branch indexing, job configuration | Fix discovery/trigger rules |
| PR not discovered | Branch Source traits, repository access | Correct source/strategy |
| Fork PR rejected | Trust policy | Preserve isolation; review approved path |
| Checkout unauthorized | App installation/token scopes | Grant only necessary read access |
| Status check missing | Plugin/publisher, permission and context | Configure verified status reporting |
| Wrong SHA checked | Head vs merge revision | Record selected strategy and SHA |
| Duplicate jobs | Webhook plus polling or duplicate sources | Remove duplicate trigger paths |
| API rate limit | GitHub API headers/plugin logs | Reduce indexing, use App where suitable |
| Secret appears in log | Credential handling | Revoke/rotate and investigate |

## 12. Production runbooks

### A. Onboard a GitHub repository
1. Review repository trust level, branch protection and build workload.
2. Install least-privilege GitHub App or scoped token.
3. Create Multibranch Pipeline with appropriate PR discovery traits.
4. Validate branch indexing and a known-good test commit.
5. Configure webhook and correlate delivery with build and actual SHA.
6. Verify check reporting, required-check policy and credential isolation.

### B. Webhook incident
1. Record event delivery ID, HTTP status and timestamp from GitHub.
2. Check DNS/TLS/reverse proxy, webhook endpoint and Jenkins plugin logs.
3. Inspect branch indexing and queue for the target revision.
4. Restore connectivity or perform controlled rescan; avoid unbounded retries.
5. Confirm a build for the intended SHA and update incident timeline.

### C. Compromised GitHub credential
1. Revoke App installation token or PAT as applicable and pause affected jobs.
2. Audit repository access, SCM changes and Jenkins credential usage.
3. Rotate credential and verify minimal permissions.
4. Rebuild from approved immutable commit and inspect produced artifacts.
5. Document scope, containment and security sign-off.

### D. Untrusted PR containment
1. Stop the affected PR build and revoke any credentials it could have accessed.
2. Preserve redacted logs, commit SHAs and agent/container evidence.
3. Revalidate fork trust settings, agent isolation and credential exposure.
4. Re-run safe tests on a disposable unprivileged agent.
5. Require security review before resuming external PR builds.

## 13. Acceptance criteria

- [ ] GitHub integration uses a scoped identity and protected repository.
- [ ] Multibranch Pipeline discovers test branch and PR as intended.
- [ ] Webhook delivery is correlated with Jenkins build and checked-out SHA.
- [ ] Head/merge revision semantics are documented.
- [ ] Fork PRs cannot access privileged credentials or trusted agents.
- [ ] Status/check reporting is verified if configured.
- [ ] Negative webhook, credential and discovery scenarios documented.
- [ ] Runbooks, audit evidence and rollback path reviewed.

**Companion:** [Chapter 032 hands-on lab](labs/032-jenkins-github-integration-webhooks-pull-request-pipelines-check.md).  
**Next:** Chapter 033 — Jenkins GitLab Integration, Webhooks and Merge Request Pipelines.
