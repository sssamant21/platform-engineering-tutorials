# Chapter 031 — Jenkins Git and SCM Integration Fundamentals

**Part 07 — Git, GitHub, GitLab and SCM Integration**  
**Audience:** Jenkins administrators, DevOps, SRE and platform engineers  
**Prerequisites:** Chapters 001–030, Git CLI, disposable Jenkins controller, isolated agent and a nonproduction Git repository.

## Learning objectives

Explain Jenkins SCM checkout architecture; configure Git plugins and scoped credentials; build reproducibly from immutable revisions; compare lightweight checkout and workspace checkout; handle branches, tags, pull requests and webhook events; diagnose Git failures; and apply enterprise source-control security and rollback controls.

## 1. Architecture and trust boundaries

```text
Git server (GitHub / GitLab / self-hosted Git)
   ├── repository, branches, tags and commit objects
   └── webhook / SCM polling trigger
           ↓ authenticated endpoint
Jenkins controller
   ├── job configuration and SCM metadata
   ├── Git / Git client / Pipeline SCM plugins
   ├── credential lookup and authorization
   └── queue and build scheduling
           ↓ agent allocation
Isolated build agent
   ├── git fetch / checkout
   ├── Jenkinsfile execution steps
   └── build, test, artifact publication
```

Jenkins controller may retrieve Jenkinsfiles or SCM metadata before agent allocation; build workspaces are normally checked out on agents. SCM webhooks trigger evaluation but are not proof that a particular commit is trusted. Protect both the repository and the pipeline definition.

## 2. Git concepts for Jenkins operations

| Concept | Meaning | Operational impact |
|---|---|---|
| Commit SHA | Content-addressed Git revision | Strong build provenance |
| Branch | Mutable ref | Good for discovery, not immutable release proof |
| Tag | Named ref | Protect release tags; they can be moved without controls |
| Remote | SCM endpoint | HTTPS/SSH reachability and credentials |
| Fetch | Download objects and refs | RefSpec controls what Jenkins sees |
| Checkout | Populate workspace at revision | Reproducible build when revision is recorded |
| Shallow clone | Limited commit history | Faster but can break changelog/merge-base operations |
| RefSpec | Mapping of remote refs | Missing PR/tag refs cause resolution failures |
| Submodule | Nested repository reference | Requires separate trust and credential review |
| Git LFS | Large-file extension | Needs client support and storage capacity |

A successful build from `main` is not sufficient evidence of exactly what was built. Capture `git rev-parse HEAD`, SCM URL and Jenkins build identifier.

## 3. Prerequisites and plugin checks

On the disposable Jenkins controller, verify compatible versions of Git, Git Client, Pipeline: SCM Step, Credentials and Pipeline plugins. For GitHub/GitLab organization discovery, provider-specific branch-source plugins are separate and covered later in Part 07. Install plugins from reviewed, pinned manifests and test upgrades before production adoption.

On an isolated Linux agent:

```bash
git --version
git config --global --get safe.directory || true
git ls-remote https://github.com/jenkinsci/jenkins.git HEAD
```

The public `ls-remote` check is a connectivity example, not a required production dependency. Do not broadly configure `safe.directory '*'` to bypass workspace ownership errors; correct ownership and trust settings instead.

## 4. Configure SCM access safely

Prefer a dedicated read-only deploy key or narrowly scoped repository token. For HTTPS, use Jenkins credentials of an appropriate type (often username/password with token as password for providers that support it); for SSH, use a scoped private key credential with verified server host keys. Never embed a token in a repository URL or Jenkinsfile.

**Example registration:**
1. Create a nonproduction Git repository and a Jenkins test job.
2. In Jenkins Credentials, store a read-only SCM credential in the narrowest suitable domain/folder.
3. Configure Git repository URL and credential ID in the job or multibranch source.
4. Validate SCM connectivity and inspect the resolved revision in the build log.
5. Confirm the credential cannot write to the repository or access unrelated repositories.

For SSH, configure the Git Client plugin's host-key verification strategy with a trusted known-hosts source or reviewed fingerprints. Disabling verification is not an acceptable fix.

## 5. Declarative Pipeline: standard checkout

A Multibranch Pipeline typically provides `scm` automatically:

```groovy
pipeline {
    agent { label 'isolated-linux' }
    options {
        timestamps()
        skipDefaultCheckout(true)
        timeout(time: 20, unit: 'MINUTES')
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh(label: 'Record revision', script: '''
                    set -eu
                    git rev-parse HEAD
                    git status --short
                ''')
            }
        }
        stage('Validate') {
            steps {
                sh 'test -f README.md'
            }
        }
    }
}
```

**Important:** `checkout scm` depends on the job having an SCM definition (e.g., Pipeline from SCM or Multibranch). For a standalone inline Pipeline, define the repository explicitly using the Git step or `checkout([$class: 'GitSCM', ...])`.

## 6. Explicit Git checkout for a fixed repository

```groovy
pipeline {
    agent { label 'isolated-linux' }
    options { skipDefaultCheckout(true) }
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    credentialsId: 'scm-readonly',
                    url: 'https://git.example.org/platform/fixture-app.git'
                sh 'git rev-parse HEAD'
            }
        }
    }
}
```

Replace the placeholder repository URL and credential ID with disposable test values. The `git` step supports common simple checkout use cases; use the full `checkout` SCM configuration for tags, nonstandard refspecs, shallow clones and extensions.

## 7. Pinning a revision for reproducibility

A branch can move between scheduling and checkout. In a Pipeline from SCM job, `checkout scm` generally uses the revision selected by the job's SCM context; record the returned checkout metadata and `git rev-parse HEAD`. To reproduce a build, use the exact commit SHA with an appropriate GitSCM configuration and ensure the commit remains fetchable.

```groovy
stage('SCM provenance') {
    steps {
        script {
            def revision = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
            echo "SCM revision: ${revision}"
            currentBuild.description = revision.take(12)
        }
    }
}
```

A commit hash alone does not establish authenticity or approval; combine it with branch protection, signed commits/tags where required, review status and artifact provenance.

## 8. Lightweight Jenkinsfile checkout vs workspace checkout

**Lightweight checkout** retrieves the Jenkinsfile without a full workspace checkout when the SCM and plugin support it. It may occur before agent allocation. **Workspace checkout** fetches repository content for builds/tests. If lightweight retrieval fails, Jenkins may fall back to a full checkout depending on job and plugin configuration. Inspect logs to distinguish them.

Avoid executing unreviewed Jenkinsfiles from forked PRs with powerful credentials or trusted libraries. Treat contributor-controlled SCM content as untrusted.

## 9. Triggering strategies

| Trigger | Advantage | Caveat |
|---|---|---|
| Webhook | Near-real-time notification | Delivery, auth, duplicates and outages |
| SCM polling | Works without inbound webhook | Adds load and latency |
| Scheduled scan | Discovers branch/ref changes | Not necessarily a build trigger |
| Manual | Controlled maintenance | Human-dependent |

Configure webhooks on the SCM provider to the appropriate Jenkins integration endpoint, not a generic URL guessed from examples. Validate signatures/secrets or provider-specific verification and restrict network access as appropriate. Duplicate events and delayed deliveries are normal possibilities: use idempotent builds and concurrency controls.

## 10. GitHub, GitLab and self-hosted SCM differences

GitHub and GitLab differ in webhook event names, token scopes, PR versus merge request refs and branch-source plugins. Jenkins Git plugin provides generic Git checkout; provider plugins add discovery, status reporting and event handling. Keep provider-specific access minimal and separate discovery credentials from build-time credentials where possible.

## 11. Enterprise production patterns

- **Multibranch:** discover branches and PR/MR refs with appropriate branch-source plugin; enforce trust strategy.
- **Monorepo:** use path-aware change detection carefully; do not skip required security checks.
- **Immutable releases:** build and promote artifacts by digest/SHA rather than rebuilding mutable branch heads.
- **Network resilience:** use bounded SCM timeouts and retries with backoff, not infinite loops.
- **Workspace hygiene:** use clean checkout when justified; avoid destructive cleanup on shared workspaces.
- **Audit:** record repository, revision, Jenkinsfile source, credential ID (not secret), agent and artifact digest.
- **Capacity:** limit concurrent fetches, use caching/mirrors when supported and monitor Git server throttling.

## 12. Troubleshooting matrix

| Symptom | Verification | Safe remediation |
|---|---|---|
| `Authentication failed` | Token expiry/scope, credential ID | Rotate scoped token; update credential |
| `Host key verification failed` | Known hosts and server key | Validate fingerprint; update trusted known hosts |
| `Repository not found` | URL and access rights | Correct URL/permissions |
| `Couldn't find any revision` | Branch/refspec and fetched refs | Fix branch or refspec |
| `git: not found` | Agent image/PATH | Use approved agent toolchain |
| `checkout scm` unavailable | Job type and SCM context | Configure Pipeline from SCM or explicit checkout |
| Checkout too slow | Network, history depth, LFS, submodules | Measure; optimize safely |
| Wrong commit built | Selected revision vs actual HEAD | Record SHA; review job configuration |
| Webhook received but no build | Event filter, branch scan, queue | Inspect provider delivery and Jenkins logs |
| Duplicate builds | Duplicate hooks/polling | Deduplicate and control concurrency |
| Submodule auth fails | Nested repo access | Separate scoped credentials |
| Unsafe workspace ownership | Filesystem UID/GID mismatch | Correct ownership; avoid global trust bypass |

## 13. Operational runbooks

### Runbook A — Onboard a repository
1. Identify SCM provider, repository owner, branch policy and trust level.
2. Create scoped read-only credential; verify host identity.
3. Configure test job and repository URL; test checkout on isolated agent.
4. Record selected and actual SHA, run baseline build and archive evidence.
5. Configure webhook/polling with security review; test a safe commit.
6. Document credential rotation, incident owner and expected recovery procedure.

### Runbook B — SCM outage
1. Distinguish DNS/TLS, Git host availability, credentials, rate limits and agent failures.
2. Preserve failed build logs and provider delivery history.
3. Pause noncritical retry storms; avoid weakening TLS/host-key checks.
4. Restore access, retry a pinned revision and verify artifact provenance.
5. Report impact, timeline and corrective actions.

### Runbook C — Credential compromise
1. Revoke affected token/key at the SCM provider.
2. Disable impacted Jenkins jobs and investigate SCM access logs.
3. Rotate scoped credentials and review repo branch protection.
4. Verify checkout against approved SHA; audit artifacts and builds during exposure.
5. Document incident response and security approval before reopening jobs.

### Runbook D — Reproduce or roll back a build
1. Capture last known-good commit SHA and Jenkinsfile/library versions.
2. Verify the commit remains fetchable and authorized.
3. Run a disposable test build pinned to that revision.
4. Compare tests and artifact digests with baseline.
5. Restore the approved ref only through normal SCM change controls.

## 14. Acceptance checklist

- [ ] Generic Git checkout and `checkout scm` differences explained.
- [ ] Isolated agent can fetch a nonproduction repository.
- [ ] Credentials are scoped and never printed.
- [ ] SCM revision is captured and verified.
- [ ] Branch movement and immutable revision behavior demonstrated.
- [ ] Webhook or polling path tested without assuming event delivery guarantees.
- [ ] Negative authentication, refspec and host-key scenarios documented.
- [ ] Recovery runbooks and reviewer evidence retained.

**Companion:** [Chapter 031 hands-on lab](labs/031-jenkins-git-scm-integration-fundamentals-check.md).  
**Next:** Chapter 032 — Jenkins GitHub Integration, Webhooks and Pull Request Pipelines.
