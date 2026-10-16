# Chapter 035 — SCM Integration Production Operations and Reliability Capstone

**Part 07 — Git, GitHub, GitLab and SCM Integration (final capstone)**  
**Audience:** Jenkins SREs, platform engineers, DevOps and SCM administrators  
**Prerequisites:** Chapters 031–034, disposable Jenkins controller and isolated agents, GitHub and GitLab test repositories, least-privilege integration credentials.

## 1. Mission

Build and operate a secure, reliable Jenkins SCM integration supporting both GitHub and GitLab. Demonstrate repository onboarding, branch and PR/MR discovery, authenticated webhooks, revision provenance, status reporting, safe failure handling and tested recovery.

**Scope:** All work is performed against disposable Jenkins and nonproduction SCM fixtures. No production secrets, customer data, deployment environments or privileged fork builds.

## 2. Objectives and architecture

```text
GitHub test repository       GitLab test project
  ├─ protected main            ├─ protected main
  ├─ PR + branch refs          ├─ MR + branch refs
  └─ webhook                  └─ webhook
            \                  /
             ↓ HTTPS + validation
        Jenkins reverse proxy
             ↓
       Jenkins controller
        ├─ Git / Git Client
        ├─ GitHub Branch Source
        ├─ GitLab Branch Source or GitLab plugin
        ├─ SCM credentials / trust policy
        ├─ branch indexing / job lifecycle
        └─ build queue
             ↓
      isolated build agents
       checkout exact SHA
       lint → unit test → package
             ↓
      JUnit + artifact + status
             ↓
       audit / SLO / incident
```

Trust boundaries matter: SCM providers can notify Jenkins, but webhook receipt alone does not authorize arbitrary Jenkinsfile execution. A fork PR/MR remains untrusted even if Jenkins retrieves a trusted Jenkinsfile. Keep sensitive credentials and privileged agents inaccessible to contributor-controlled code.

## 3. Implementation phases

### Phase A — Inventory and security baseline

Record Jenkins core and plugin versions, agent image/labels, Git client version, proxy hostname, GitHub App installation or scoped token, GitLab integration identity, repository ownership and credential rotation schedule. Verify TLS and SSH host identity. Protect `main`, review Jenkinsfile changes and enforce least privilege.

### Phase B — Repository onboarding

Create a GitHub Multibranch Pipeline with GitHub Branch Source. Create a GitLab Multibranch Pipeline with GitLab Branch Source **or** a Pipeline from SCM with GitLab plugin triggers; record the actual plugin model because their webhook endpoints and MR discovery differ. Configure branch and origin PR/MR discovery, test checkout, and document fork trust policies.

### Phase C — End-to-end event flow

For each provider: push a fixture commit; capture webhook delivery ID, HTTP response, indexing event, Jenkins build number, expected revision, `git rev-parse HEAD` and published status/check. Confirm that the status is attached to the revision actually tested.

### Phase D — Reliability, capacity and recovery

Run bounded failure injections (expired credential, missing branch, webhook route error, duplicate event, rate-limit symptom, agent outage), preserve evidence, correct safely and retest. Rehearse credential rotation and webhook outage recovery. Record a rollback to known-good job/plugin configuration in the disposable environment.

## 4. Reference Jenkinsfile

```groovy
pipeline {
    agent { label 'isolated-linux' }
    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 25, unit: 'MINUTES')
        disableConcurrentBuilds()
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh '''#!/bin/sh
                    set -eu
                    git rev-parse HEAD
                    git status --short
                '''
            }
        }
        stage('Test') {
            steps { sh './ci/test.sh' }
        }
        stage('Archive') {
            steps {
                archiveArtifacts artifacts: 'evidence/*.txt',
                                 allowEmptyArchive: false,
                                 fingerprint: true
            }
        }
    }
}
```

Fixture `ci/test.sh`:

```sh
#!/bin/sh
set -eu
test -f README.md
test -f Jenkinsfile
mkdir -p evidence
git rev-parse HEAD > evidence/scm-revision.txt
printf 'SCM integration fixture PASS\n'
```

The fixture validates checkout and evidence collection, **not** application correctness. Replace it with actual tests and JUnit reporting when promoting a CI pattern to production. The fixture Jenkinsfile assumes `archiveArtifacts` is available.

## 5. Provider-specific acceptance matrix

| Check | GitHub | GitLab |
|---|---|---|
| Scoped identity | GitHub App / narrowly scoped token | Project/group token / dedicated service identity |
| Branch discovery | GitHub Branch Source | GitLab Branch Source or configured job |
| PR/MR discovery | Origin PR + controlled fork policy | Origin MR + controlled fork policy |
| Webhook | Provider/plugin documented endpoint | Plugin-specific endpoint |
| Event verification | GitHub signature/secret as supported | GitLab secret token as supported |
| Status reporting | GitHub check/status on tested SHA | GitLab commit status on tested SHA |
| Audit | Delivery ID, job, SHA, agent, result | Delivery ID, job, SHA, agent, result |

Never assume the same webhook URL or event payload fields across plugins.

## 6. SCM provenance and supply-chain safeguards

For each build record repository URL, selected SCM head, actual checkout SHA, PR/MR ID, Jenkinsfile source, Shared Library version, agent image, Jenkins/plugin versions, test results and artifact fingerprint. Protect release tags and use immutable SHAs for reproduction. A SHA proves content identity, not reviewer approval or source authenticity; combine it with protected branches and reviewed commits.

Avoid arbitrary shell commands derived from branch names, commit messages or webhook payloads. Do not interpolate untrusted SCM metadata into shell strings.

## 7. Reliability SLIs and proposed lab targets

| SLI | Proposed lab target | Measurement |
|---|---|---|
| Correct revision checkout | 100% | Matching expected and actual SHA |
| Valid webhook-to-build correlation | 100% for controlled events | Delivery ID → build → SHA |
| Credential isolation | Zero privileged access in untrusted builds | Trust/agent/credential review |
| Valid fixture success | 100% | Passing test fixture runs |
| Status/check correctness | 100% when publisher enabled | Correct result and SHA |
| Recovery from injected outage | Within 15 minutes in lab | Detection → verified build |
| Orphan lifecycle compliance | 100% | Jobs retained/pruned per policy |

Targets are **exercise goals**, not claims about production SLOs. For production, set thresholds from measured baseline, error budgets and business requirements. Monitor provider API quota, webhook 4xx/5xx, indexing latency, branch count, queue delay, executor utilization and SCM checkout failures.

## 8. Failure injection campaign

| Scenario | Expected behavior | Recovery evidence |
|---|---|---|
| GitHub App access removed | Discovery/checkout fails closed | Scoped access restored, SHA verified |
| GitLab token expired | API/checkout rejects | Rotated token and successful retest |
| Wrong webhook endpoint | Provider records 404 | Corrected endpoint, event correlation |
| Secret mismatch | Event rejected/flagged | Verified secret rotation |
| Missing ref | No unintended fallback to main | Correct refspec/branch |
| Duplicate delivery | No unsafe duplicate publishing | Event/build correlation |
| Provider API throttling | Bounded retries/scans | Indexing stabilizes |
| Agent offline | Queue/timeout safely | Agent restored and fixture passes |
| Fork PR/MR | No secrets or privileged agents | Trust policy evidence |
| Wrong head/merge SHA | Mismatch detected | Strategy corrected, status aligned |
| Jenkinsfile missing | Clear indexing/build diagnostic | Fixture restored |
| Orphaned branch | Lifecycle policy followed | Retention audit |

## 9. Troubleshooting matrix

| Symptom | Check | Safe action |
|---|---|---|
| 2xx webhook, no build | Indexing log, filters, trigger | Trace event to job |
| PR/MR not discovered | Source traits and token scopes | Correct discovery |
| Wrong revision built | Selected head/merge strategy | Pin/verify intended SHA |
| Missing check status | Publisher, permission, API response | Fix least-privilege integration |
| Jenkins controller busy | Indexing frequency, heap, API calls | Reduce scans and job sprawl |
| Duplicate builds | Multiple webhook/polling sources | Remove redundancy |
| Untrusted code sees credentials | Job trust and agent placement | Stop, revoke, investigate |
| SCM fetch timeout | Network, server, repo size | Bounded retry and measured optimization |
| Host key error | Trusted host key database | Verify and repair; never bypass |
| Orphaned job unexpectedly removed | Retention strategy | Restore audit from archive |
| GitLab plugin mismatch | Branch Source vs GitLab plugin config | Use correct job/endpoint |
| GitHub rate-limit exhaustion | API logs and scan cadence | Stagger scans, narrow discovery |

## 10. Enterprise runbooks

### Runbook A — Repository onboarding
1. Review SCM owner, threat model, branch protection, Jenkinsfile approval and plugin support.
2. Provision minimal credentials and configure a disposable job.
3. Run initial scan, verify branch and PR/MR discovery.
4. Trigger test event, capture delivery ID and actual SHA.
5. Validate status/check reporting and archive evidence.
6. Obtain reviewer approval before any production adaptation.

### Runbook B — Webhook delivery incident
1. Record provider delivery status, timestamp and request ID.
2. Inspect DNS/TLS, reverse proxy, plugin endpoint and Jenkins logs.
3. Trace indexing, queue, checkout and status publisher independently.
4. Correct the failed component; avoid disabling authentication.
5. Verify a fresh event on the intended revision; document incident timeline.

### Runbook C — Credential compromise
1. Revoke the token/key and pause affected jobs.
2. Audit Jenkins credential scope, SCM provider logs and source changes.
3. Rotate to a least-privilege identity and verify provider access.
4. Review affected builds and artifact integrity.
5. Obtain security sign-off before reopening jobs.

### Runbook D — Indexing overload
1. Capture controller CPU/heap, provider quota, scan frequency and job counts.
2. Stop redundant scans and narrow discovery traits.
3. Review orphaned item retention before pruning anything.
4. Resume controlled scans; monitor backlog and API errors.
5. Document capacity limits and prevention measures.

### Runbook E — Rollback integration configuration
1. Preserve current Jenkins job/SCM settings and plugin manifest.
2. Restore reviewed known-good configuration in disposable Jenkins.
3. Verify webhook, branch scan, checkout SHA and status publisher.
4. Preserve failure evidence and record recovery duration.
5. Avoid untested production plugin downgrades; follow the organization's upgrade/restore procedure.

## 11. 100-point reliability acceptance rubric

| Category | Points |
|---|---:|
| Architecture, SCM plugin choice and source governance | 15 |
| Credentials, trust policies and secret isolation | 15 |
| GitHub end-to-end integration | 15 |
| GitLab end-to-end integration | 15 |
| Revision provenance, status and audit | 10 |
| Webhook/indexing observability and SLOs | 10 |
| Fault injection and troubleshooting | 10 |
| Recovery, rollback and operational handover | 10 |
| **Total** | **100** |

Suggested passing score: **85/100**, with mandatory critical gates: no real secret exposure, no privileged untrusted PR/MR builds, no arbitrary command execution from SCM metadata, correct revision provenance and successful recovery.

## 12. Deliverables and sign-off

- Architecture diagram and SCM plugin inventory.
- GitHub and GitLab test repository/job configuration.
- Scoped credential ownership and rotation record (never secret values).
- Branch/MR discovery, webhook delivery and checkout SHA evidence.
- Test fixture logs, archived artifact fingerprints and status/check evidence.
- Failure injection matrix, root-cause notes and executed recovery runbooks.
- 100-point score, reviewer approval and open risks.

**Companion:** [Chapter 035 hands-on capstone lab](labs/035-scm-integration-production-operations-reliability-capstone-check.md).  
**Part 07 complete after publication:** Chapters 031–035.  
**Next:** Chapter 036 — Jenkins Build Automation with Maven, Gradle and npm, beginning Part 08.
