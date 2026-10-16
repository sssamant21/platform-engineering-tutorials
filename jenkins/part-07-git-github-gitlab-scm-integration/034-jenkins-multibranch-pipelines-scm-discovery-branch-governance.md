# Chapter 034 — Jenkins Multibranch Pipelines, SCM Discovery and Branch Governance

**Part 07 — Git, GitHub, GitLab and SCM Integration**  
**Audience:** Jenkins administrators, SRE, DevOps and platform engineering teams  
**Prerequisites:** Chapters 031–033, disposable Jenkins controller, isolated build agents, GitHub or GitLab fixture repository and least-privilege SCM identity.

## Learning objectives

Design and administer Multibranch Pipeline jobs, understand branch-source discovery and indexing, distinguish branches/PRs/MRs and trusted/untrusted SCM revisions, apply branch governance and orphaned-item strategies, tune scans and webhooks for scale, and recover safely from indexing and security incidents.

## 1. Architecture

```text
GitHub / GitLab repository
  ├── main, release/*, feature/*, PR/MR refs
  └── provider API + webhook
           ↓
Jenkins controller / Multibranch Pipeline
  ├── SCMSource + discovery traits
  ├── branch indexing and job creation
  ├── Jenkinsfile retrieval and trust policy
  ├── orphaned item lifecycle
  └── scheduling / status reporting
           ↓
Isolated build agents
  ├── checkout selected SCM revision
  ├── validate → test → package
  └── reports and immutable revision evidence
```

Indexing discovers or updates child jobs. Indexing is not the same as building: an event can be accepted and indexed without a new build, depending on strategies and configuration.

## 2. Multibranch versus single Pipeline jobs

| Feature | Pipeline from SCM | Multibranch Pipeline |
|---|---|---|
| Branch discovery | Explicitly configured | Automatic based on source traits |
| PR/MR jobs | Custom/manual integration | Branch-source provider integration |
| Jenkinsfile | One configured SCM context | Per discovered head, subject to trust rules |
| Lifecycle | Admin-maintained job | Dynamic child job creation/removal |
| Scale risk | Per-job administration | API rate limits, indexing storms, job sprawl |

Use an Organization Folder only when repository-level discovery is needed and the installed provider plugin supports it; organization scanning multiplies API and controller load.

## 3. Discovery traits and trust

Common traits include branch discovery, origin PR/MR discovery, fork PR/MR discovery, head versus merge revision strategy, tag discovery and branch name filtering. Actual names and options depend on GitHub Branch Source or GitLab Branch Source versions.

**Security:** Forks and external contributors are untrusted. Do not expose trusted Shared Libraries, deployment credentials, privileged Kubernetes agents, signing keys or production network access to untrusted PR/MR builds. A trusted Jenkinsfile does not make arbitrary checked-out PR code safe. Review the source plugin's trust model and isolate execution.

## 4. Repository governance

| Ref class | Suggested controls | Build policy |
|---|---|---|
| `main` | Protected, reviewed merges, required checks | Full CI |
| `release/*` | Restricted writes, explicit approvals | Full regression + provenance |
| `feature/*` | Developer-owned, no deploy secrets | Lint/test |
| Origin PR/MR | Review Jenkinsfile changes, isolated agent | Tests + status |
| Fork PR/MR | Untrusted SCM, restricted agents/network | Read-only validation |
| Tags | Protected immutable release tags | Release verification only |

Avoid relying solely on branch name matching for security: branch names are mutable user input. Authorization must come from SCM permissions, job trust strategy and credential policy.

## 5. Create a Multibranch Pipeline

1. Create a disposable test repository with a `Jenkinsfile`, `README.md` and executable `ci/test.sh`.
2. Install reviewed Git, Pipeline and provider Branch Source plugins.
3. Create **New Item → Multibranch Pipeline**.
4. Configure Branch Source provider and a narrowly scoped credential.
5. Enable appropriate branch and origin PR/MR discovery; configure fork discovery only after trust review.
6. Set script path to `Jenkinsfile`.
7. Configure periodic scan as a recovery mechanism, not an aggressive default.
8. Set orphaned item strategy with retention aligned to audit requirements.
9. Save and run **Scan Multibranch Pipeline Now**.
10. Inspect indexing log, discovered child jobs and selected SCM revisions.

## 6. Reference Jenkinsfile

```groovy
pipeline {
    agent { label 'isolated-linux' }
    options {
        timestamps()
        skipDefaultCheckout(true)
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
    }
    post {
        always { echo "Completed ${env.JOB_NAME} #${env.BUILD_NUMBER}" }
    }
}
```

**Fixture `ci/test.sh`:**

```sh
#!/bin/sh
set -eu
test -f README.md
test -f Jenkinsfile
printf 'Multibranch fixture checks passed\n'
```

For a real application, replace fixture assertions with actual lint, unit and integration tests.

## 7. Branch-aware logic

Jenkins Multibranch commonly provides `BRANCH_NAME`, `CHANGE_ID`, `CHANGE_TARGET` and related environment variables; availability varies with job/provider.

```groovy
stage('Branch policy') {
    when {
        allOf {
            branch 'main'
            not { changeRequest() }
        }
    }
    steps {
        echo 'Protected-branch validation path'
    }
}
```

Use `when { changeRequest() }` for PR/MR-specific stages. Do **not** treat `BRANCH_NAME == 'main'` as authorization for production deployment. Enforce separate approvals, identity and environment controls.

## 8. Indexing and webhook behavior

Webhook → provider event handling → SCM source indexing or event evaluation → child job update → optional build. A successful webhook HTTP response is not proof of job creation or successful build.

Monitor:
- Last successful scan and duration.
- Discovered branch/PR/MR counts.
- GitHub/GitLab API quota, 401/403/429 errors.
- Queue delay, executor saturation and controller CPU/heap.
- Builds by branch type, failed SCM retrieval and missing Jenkinsfiles.

Keep a bounded periodic scan to recover from missed events, with cadence chosen for repository size and provider API limits. Avoid enabling redundant polling plus frequent full scans without measuring load.

## 9. Orphaned item lifecycle

When branches are deleted or no longer discovered, Jenkins can remove or retain their child jobs and build history according to orphaned-item strategy. Choose retention to satisfy audit and cost needs; avoid immediate deletion if build evidence must be retained. Archive necessary reports externally according to policy before pruning.

## 10. Scale and capacity design

A repository with 300 feature branches and 50 PRs can create hundreds of child jobs if discovery is unrestricted. Limit discovery to relevant refs; apply retention policies, tune indexing, stagger organization scans, and use ephemeral agents. Avoid indiscriminate `.*` branch filters or aggressive scan intervals.

Do not put heavy Git/Groovy build work on controller executors. Prefer lightweight Jenkinsfile retrieval where supported and verified.

## 11. Troubleshooting matrix

| Symptom | Verification | Remediation |
|---|---|---|
| Branch missing | Discovery trait, name filter, indexing log | Adjust approved trait/filter |
| PR/MR missing | Provider plugin, token scopes, trust settings | Fix source configuration |
| Wrong revision built | Head vs merge strategy and checkout SHA | Select/test correct strategy |
| No Jenkinsfile | Script path, branch content | Fix file path |
| Webhook 2xx, no build | Event routing, indexing and suppression | Trace end to end |
| API rate limit | Provider quota and scan frequency | Reduce indexing and improve credentials |
| Orphaned job deleted | Retention settings | Restore evidence from archive |
| Unexpected job sprawl | Discovery scope and orphan policy | Restrict refs |
| Fork executes privileged step | Trust policy and credentials | Stop, revoke, isolate |
| Indexing slow | Controller CPU/heap, API latency | Tune scans and scale agents separately |
| Duplicate builds | Event/polling overlap | Remove redundant triggers |
| Status on wrong SHA | Head/merge revision mismatch | Align tested and reported revision |

## 12. Operational runbooks

### A. New repository onboarding
1. Review ownership, branch protection, PR/MR trust and credential scope.
2. Configure provider source with minimum required traits.
3. Run a manual scan; record indexing duration and discovered heads.
4. Build main and a test PR/MR on isolated agents; capture SHAs.
5. Validate webhook and status correlation.
6. Document scan cadence, orphan retention, on-call owner and rollback.

### B. Branch missing after push
1. Capture webhook delivery, branch name and expected SHA.
2. Inspect provider API access and source indexing log.
3. Check discovery filters and Jenkinsfile path.
4. Perform one controlled rescan after correction.
5. Verify child job creation and checkout revision.

### C. Indexing storm
1. Record controller CPU/heap, API quota and scan backlog.
2. Temporarily pause redundant scheduled scans or duplicate event sources.
3. Narrow discovery scope; do not delete jobs without retention review.
4. Resume controlled indexing and monitor rate-limit recovery.
5. Document corrective action and capacity thresholds.

### D. Compromised fork PR
1. Stop untrusted builds and revoke any potentially exposed credentials.
2. Preserve redacted logs and identify checked-out commit.
3. Audit trust traits, agent privileges and Shared Library access.
4. Reconfigure isolated validation and retest with harmless fixture.
5. Require security sign-off before reopening fork builds.

## 13. Acceptance checklist

- [ ] Branches and PR/MRs discovered with documented source traits.
- [ ] Jenkinsfile and checkout revision verified.
- [ ] Branch-aware stages work without granting deployment privileges.
- [ ] Webhook delivery correlated with indexing and actual build.
- [ ] Fork trust and credential isolation reviewed.
- [ ] Orphan retention and scan frequency documented.
- [ ] Indexing storm and missing-branch recovery rehearsed.
- [ ] Build logs and audit evidence retained.

**Companion:** [Chapter 034 hands-on lab](labs/034-jenkins-multibranch-pipelines-scm-discovery-branch-governance-check.md).  
**Next:** Chapter 035 — SCM Integration Production Operations and Reliability Capstone.
