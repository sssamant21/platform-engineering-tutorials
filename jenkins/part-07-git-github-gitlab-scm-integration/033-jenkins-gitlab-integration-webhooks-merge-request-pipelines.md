# Chapter 033 — Jenkins GitLab Integration, Webhooks and Merge Request Pipelines

**Part 07 — Git, GitHub, GitLab and SCM Integration**  
**Audience:** Jenkins administrators, DevOps engineers, SREs and platform teams  
**Prerequisites:** Chapters 031–032, disposable Jenkins controller and Linux agent, GitLab test project, scoped integration credential, HTTPS endpoint.

## Learning objectives

Configure Jenkins GitLab connectivity; distinguish GitLab plugin, GitLab Branch Source and generic Git checkout; discover branches and merge requests; securely process webhook events; report commit status; handle fork trust, credentials and protected branches; troubleshoot integration failures; and perform incident response and recovery.

## 1. Reference architecture

```text
GitLab SaaS / self-managed GitLab
  ├── project, protected branches, merge requests
  ├── project/group access token or service identity
  └── push / merge-request webhook
        ↓ HTTPS / token verification / reverse proxy
Jenkins controller
  ├── Git plugin: checkout
  ├── GitLab plugin: event integration and status features
  ├── GitLab Branch Source: multibranch discovery (if installed)
  └── queue, SCM revision selection, credential scope
        ↓ isolated unprivileged build agent
Checkout → lint → tests → artifact evidence
        ↓
GitLab commit status + MR policy
```

**Important:** GitLab plugin and GitLab Branch Source are different integrations. Their supported endpoints, authentication fields and job types differ. Confirm the plugin and version actually installed before following any UI steps.

## 2. GitLab authentication options

| Option | Use case | Controls |
|---|---|---|
| Project access token | Test project integration | Least privilege, expiry, rotation |
| Group access token | Multiple approved projects | Restrict group and token scopes |
| Service account PAT | When plugin requires PAT behavior | Dedicated identity, scoped access |
| SSH deploy key | Read-only checkout | Verified host key and repo scope |
| GitLab CI job token | Native GitLab jobs | Not a general replacement for Jenkins credentials |

For project discovery/API operations, plugins may require `read_api` or `api` scopes; verify the minimal permissions supported by your chosen plugin and GitLab version. Checkout typically needs `read_repository` or equivalent SSH access. Status reporting requires an API permission appropriate to the endpoint. Do not grant `api` automatically when a narrower supported permission works.

Never put tokens in Git URLs, Jenkinsfiles, console output or webhook query strings. Store credentials in Jenkins' credential store and restrict access to the relevant folder.

## 3. Configure GitLab plugin for a Pipeline job

A common configuration approach for the **GitLab plugin**:

1. Install a reviewed compatible version of GitLab plugin, Git plugin and required dependencies.
2. Configure GitLab server connection in Jenkins global settings, using HTTPS URL and a scoped API credential.
3. Create a test Pipeline job using **Pipeline script from SCM**, pointing at the GitLab test project.
4. Enable the plugin's GitLab event trigger for the job, as supported by the installed version.
5. Inspect the job's webhook URL supplied by the plugin configuration and configure GitLab **Settings → Webhooks** accordingly.
6. Send a test push or merge-request event and correlate delivery with Jenkins build.

For **GitLab Branch Source**, instead create a Multibranch Pipeline with GitLab as the branch source and configure branch/MR discovery traits. Do not assume GitLab plugin trigger settings apply to Branch Source jobs.

## 4. Safe fixture Jenkinsfile

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
        stage('Tests') {
            steps {
                sh './ci/test.sh'
            }
        }
    }
}
```

Commit an executable `ci/test.sh` into the test repository, for example:

```sh
#!/bin/sh
set -eu
test -f README.md
test -f Jenkinsfile
printf 'fixture validation passed\n'
```

These fixture checks validate the integration path; replace them with actual application tests before making the status a production merge gate.

## 5. Webhook events and trust model

GitLab project → **Settings → Webhooks**. Configure the URL from the installed Jenkins integration, select push and merge request events as required, and use a webhook secret/token when supported. Restrict ingress, use TLS, and verify provider-specific token/header validation in the plugin and reverse proxy.

Some GitLab plugin configurations use a job-specific endpoint such as `/project/<job-name>`; other integrations use different endpoints. Never assume one endpoint works for all Jenkins GitLab plugins.

A 2xx webhook delivery proves only HTTP acceptance. Validate **event → Jenkins indexing/trigger → build → checked-out SHA → status report**.

## 6. Merge request discovery and checkout strategies

| Strategy | Behavior | Risk |
|---|---|---|
| Source branch head | Test MR contributor revision | Target branch may have advanced |
| Merge result | Test candidate merge with target | Requires supported discovery/merge ref |
| Same-project MR | Branch belongs to trusted project | Jenkinsfile edits still need review |
| Fork MR | External project code | Strictly untrusted; no privileged credentials |

For GitLab Branch Source, select supported origin/fork MR discovery and trust traits according to the installed version. For a plain GitLab-plugin Pipeline, job triggers may provide environment variables, but these are plugin/version-specific; verify them in your disposable environment.

Capture source SHA, target branch, selected checkout SHA and build status. A synthetic merge SHA may differ from source SHA.

## 7. GitLab commit status reporting

The GitLab plugin may expose `gitlabCommitStatus` and `updateGitlabCommitStatus` steps depending on installed plugins and configuration. Example **only when these steps are installed and supported**:

```groovy
pipeline {
    agent { label 'isolated-linux' }
    stages {
        stage('Tests') {
            steps {
                gitlabCommitStatus(name: 'jenkins-tests') {
                    sh './ci/test.sh'
                }
            }
        }
    }
}
```

Confirm the status is posted to the **actual tested commit** and that failure is reported as failure. For GitLab Branch Source, status publication may use different APIs or integration behavior. Avoid duplicate or contradictory contexts from multiple publishers.

## 8. GitLab branch protection and merge gates

Configure protected `main`, mandatory reviews and required status checks where supported by your GitLab edition/settings. Ensure required status names are stable and actually emitted by Jenkins. Do not allow an `echo`-only Pipeline to count as an application test gate.

A Jenkins integration must not be able to bypass code review or merge restrictions unless explicitly required and separately approved.

## 9. Enterprise reliability and security controls

- Separate SCM read identity from status-write identity where supported.
- Use short-lived credentials or documented rotation.
- Keep untrusted MR agents ephemeral, unprivileged and network restricted.
- Do not expose deployment/signing secrets to fork MRs.
- Bound build concurrency and GitLab API calls.
- Monitor webhook delivery errors, Jenkins queue delay, MR discovery lag, API rate limits and status publication failures.
- Use immutable revisions and archive provenance, not mutable branch names alone.
- Test plugin updates and GitLab API changes on a disposable controller.

## 10. Troubleshooting matrix

| Symptom | Verification | Remediation |
|---|---|---|
| Webhook 404 | Plugin-specific endpoint, proxy routing | Correct URL |
| Webhook 403 | Secret/token, WAF, access rules | Repair validation without disabling checks |
| HTTP 2xx but no job | Trigger configuration, event type, branch indexing | Correct discovery/filter |
| MR missing | Branch Source traits, project API access | Enable approved MR strategy |
| `checkout scm` fails | SCM job context, refspec, credentials | Correct job and ref |
| GitLab API 401 | Token expiry or wrong credential | Rotate test token |
| GitLab API 403 | Missing scope or project access | Grant minimal required permission |
| Status not posted | Publisher, API permissions, target SHA | Fix integration and verify |
| Wrong MR revision | Head vs merge ref | Record and select intended strategy |
| Duplicate builds | Multiple triggers/integrations | Deduplicate |
| Fork MR accesses secrets | Trust/agent/credential configuration | Stop jobs, revoke secrets, harden |
| TLS verification fails | CA chain, GitLab host cert | Repair trust store; never disable TLS |

## 11. Production runbooks

### A. Onboard a GitLab project
1. Identify GitLab instance/edition, project owner, MR policy and integration plugin.
2. Create least-privilege credential; record owner and rotation date.
3. Configure Pipeline from SCM or Multibranch source.
4. Verify Git fetch, checkout SHA, MR discovery and fixture test execution.
5. Configure plugin-specific webhook endpoint and validate delivery-to-build correlation.
6. Confirm status reporting, merge gates, fork trust and incident ownership.

### B. Webhook outage
1. Record GitLab webhook delivery time, response and request ID.
2. Check proxy, TLS, controller logs, plugin endpoints and job triggers.
3. Inspect queue/indexing and selected revision.
4. Repair route or credential; use controlled rescan if needed.
5. Confirm build and status on the intended SHA, then close incident.

### C. Credential compromise
1. Revoke affected token/key at GitLab and pause affected jobs.
2. Review project activity, GitLab audit logs (where available) and Jenkins logs.
3. Rotate to a narrower identity and verify checkout/status operations.
4. Audit produced artifacts and unauthorized source changes.
5. Document containment, remediation and security approval.

### D. Failed merge request pipeline
1. Identify MR source/target SHA and checkout strategy.
2. Distinguish SCM retrieval, test failure, agent outage and status API failure.
3. Preserve test reports and Jenkins console logs.
4. Retry only on approved immutable revision after remediation.
5. Require the correct GitLab status before merge.

## 12. Acceptance criteria

- [ ] Scoped GitLab credential configured without leaking token.
- [ ] Pipeline checkout records actual SHA.
- [ ] GitLab webhook delivery correlates with Jenkins execution.
- [ ] MR discovery and checkout strategy documented.
- [ ] Fork MRs cannot access privileged Jenkins secrets.
- [ ] Status reporting validated where configured.
- [ ] Negative credential/webhook/API tests and runbooks documented.
- [ ] Reviewer evidence preserved.

**Companion:** [Chapter 033 hands-on lab](labs/033-jenkins-gitlab-integration-webhooks-merge-request-pipelines-check.md).  
**Next:** Chapter 034 — Jenkins Multibranch Pipelines, SCM Discovery and Branch Governance.
