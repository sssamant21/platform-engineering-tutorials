# Chapter 040 — Build, Testing and Artifact Reliability Acceptance Capstone

**Part 08 — Build Automation, Testing and Artifacts (final capstone)**  
**Audience:** Jenkins SRE, DevOps, platform engineering, release engineering and application owners  
**Prerequisites:** Chapters 036–039, disposable Jenkins controller, isolated build agents, nonproduction artifact repository, optional nonproduction SonarQube.

## Mission and success criteria

Build a reliable CI supply chain from immutable Git revision to tested and verified artifact. Demonstrate reproducibility, explicit test evidence, fail-closed quality gates, controlled publication, traceability, recovery and safe rollback. **All exercises must use disposable systems and synthetic data.**

### Reference architecture

```text
Protected Git branch / PR
        ↓ immutable checkout SHA
 Jenkins Multibranch Pipeline
        ├─ Maven / Gradle / npm build
        ├─ JUnit unit + integration tests
        ├─ coverage + static analysis
        ├─ SonarQube asynchronous gate (optional)
        ├─ package + SHA256 manifest
        └─ policy / approval
                 ↓
     Nonproduction artifact repository
        ├─ candidate / snapshot
        ├─ immutable release
        └─ retention + audit
                 ↓
      download → verify digest
                 ↓
      promotion or rollback decision
```

A passing CI build is not equivalent to a secure release. Jenkins archives are build evidence; the registry is the system of record for distributed packages.

## 1. Architecture and trust boundaries

- SCM source, Jenkinsfile and dependency manifests can execute arbitrary code. Run contributor-controlled work only on isolated, unprivileged agents.
- Do not grant registry write tokens, SonarQube credentials or deployment privileges to untrusted pull requests.
- Require reviewed protected-branch changes and release approvals in addition to branch-name conditions.
- Pin JDK/Node/tool wrappers and dependencies, record agent image identity, and prevent mutable release coordinates.
- Never assume two Jenkins controllers can safely share one writable `JENKINS_HOME`.
- Keep Jenkins, SonarQube and registry tokens in credential stores, never repository source or build logs.

## 2. Capstone fixture design

Use three independent synthetic fixtures:

| Fixture | Toolchain | Required evidence |
|---|---|---|
| Java Maven | JDK + Maven Wrapper | `target/surefire-reports/*.xml`, JAR, SHA256 |
| Java Gradle | JDK + Gradle Wrapper | `build/test-results/test/*.xml`, JAR, SHA256 |
| Python or Node | Python pytest-cov or npm test | JUnit XML, coverage/report, package |

Each fixture must include actual passing and failing tests, an immutable source SHA and a deterministic package contract. For Node, configure a JUnit reporter if required by policy. Use Python fixture for the SonarQube example in Chapter 038.

## 3. End-to-end pipeline design

A practical implementation uses independent stage scripts to avoid hidden tool assumptions. The following **Maven fixture** is a template, not a production deployment pipeline:

```groovy
pipeline {
    agent { label 'isolated-jdk' }
    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 40, unit: 'MINUTES')
        disableConcurrentBuilds()
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git rev-parse HEAD > source-sha.txt'
            }
        }
        stage('Toolchain') {
            steps {
                sh 'java -version'
                sh './mvnw -version'
            }
        }
        stage('Verify') {
            steps {
                sh './mvnw -B -ntp clean verify'
            }
        }
        stage('Artifact integrity') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    mkdir -p evidence
                    sha256sum target/*.jar > evidence/artifacts.sha256
                    cp source-sha.txt evidence/source-sha.txt
                '''
            }
        }
        stage('Candidate approval') {
            when { branch 'main' }
            steps {
                echo 'Review test results, digest and release authorization'
            }
        }
    }
    post {
        always {
            junit testResults: 'target/surefire-reports/*.xml',
                  allowEmptyResults: false
            archiveArtifacts artifacts: 'evidence/**,target/*.jar',
                             allowEmptyArchive: false,
                             fingerprint: true
        }
    }
}
```

**Important:** The example's approval stage is informational only. A real release must enforce authorization using a reviewed approval mechanism and a separate trusted publication job. `when { branch 'main' }` is not authorization. Strict `post` report/archive gates may produce secondary errors if checkout or build fails early; capture the primary failure before diagnosing publisher errors.

## 4. Test and quality gate policy

| Gate | Acceptance | Failure behavior |
|---|---|---|
| Toolchain | Approved pinned version | Block |
| Tests | Required tests executed and passed | Block |
| JUnit | XML exists and parses; nonzero test count | Block |
| Coverage | Meets agreed project threshold | Block |
| Static analysis | No blocking findings | Block |
| SonarQube | Actual server-side gate returns OK | Block |
| Provenance | Checkout SHA recorded | Block |
| Artifact integrity | SHA256 recorded and verified after download | Block |
| Release authorization | Protected branch and approved identity | Block |
| Retention | Previous approved artifact remains recoverable | Block release if rollback unavailable |

Do not interpret a successful SonarScanner invocation as an approved quality gate. SonarQube gate status is asynchronous and must be awaited using the supported Jenkins integration.

## 5. Artifact versioning and promotion

Use a snapshot/candidate repository for ordinary CI. After test, quality and approval checks, promote **the same bytes** to an immutable release coordinate; do not rebuild from an unpinned branch head. Record repository URL, coordinate, digest, source SHA, test evidence, reviewer and release ticket. To rollback, redeploy the previously verified digest, not a mutable `latest` tag.

## 6. Reliability targets and observability

| SLI | Measurement | Suggested capstone target |
|---|---|---|
| Source provenance | Build SHA = expected SHA | 100% |
| JUnit report availability | Valid reports for completed test stages | 100% |
| Quality gate correctness | Injected failures block promotion | 100% |
| Artifact integrity | Downloaded digest = expected digest | 100% |
| Release immutability | Conflicting overwrite rejected | 100% |
| Recovery success | Verified rebuild after controlled fault | 100% |
| Queue time | Scheduled → agent start | Baseline p50/p95 |
| Build duration | Checkout → archive | Baseline p50/p95 |
| Registry availability | Successful test requests | Baseline |
| Recovery time | Detection → validated restore | Record and compare |

These are **lab targets**, not measured production SLOs. Track controller CPU/heap, queue/executor utilization, agent disk/inodes, dependency registry latency, SonarQube task backlog, publish errors and artifact storage growth.

## 7. Failure injection campaign

| Failure | Expected safe outcome | Recovery |
|---|---|---|
| Maven/Gradle wrapper missing | Build fails before publish | Restore reviewed wrapper |
| npm lock mismatch | `npm ci` fails | Regenerate/review lockfile |
| Unit test assertion fails | Required gate blocks | Fix and rerun same SHA |
| JUnit XML missing | Reporting gate fails closed | Repair reporter |
| Coverage below threshold | Pipeline blocks | Improve tests or approved policy change |
| SonarQube webhook lost | Gate wait times out | Restore webhook and reanalyze |
| SonarQube token revoked | Analysis denied | Rotate scoped credential |
| Agent offline | Queue/timeout; no publish | Restore agent |
| Dependency registry 503 | Build fails with bounded retries | Restore registry |
| Artifact registry 401/403 | Publish denied | Restore scoped permissions |
| Immutable version collision | Overwrite refused | New version coordinate |
| Download digest mismatch | Promotion quarantined | Investigate integrity |
| Registry storage full | Publish fails safely | Expand/clean per retention |
| Wrong SCM SHA | Provenance gate blocks | Correct checkout |
| Prior release missing | Rollback readiness fails | Restore backup and fix retention |

## 8. Troubleshooting decision tree

```text
Pipeline failed?
  ├─ No agent → queue, label, capacity
  ├─ Checkout failed → SCM identity/ref/network
  ├─ Build failed → toolchain, lockfile, dependency registry
  ├─ Tests failed → product defect vs flaky test vs environment
  ├─ Reports missing → glob, workspace, reporter
  ├─ Gate timed out → SonarQube task/webhook
  ├─ Package failed → build config, disk/inodes
  ├─ Publish failed → endpoint, auth, quota, version conflict
  └─ Digest mismatch → quarantine, audit, do not promote
```

Never bypass TLS or disable a required gate merely to make a build green.

## 9. Production runbooks

### Runbook A — Build pipeline onboarding
1. Record owners, toolchains, lockfiles, test/report contracts and agent requirements.
2. Review trust boundaries and repository credential scope.
3. Build fixture on isolated agent, record source SHA and versions.
4. Publish JUnit, coverage and quality gate evidence.
5. Publish candidate package and verify downloaded SHA256.
6. Exercise negative test and rollback before approval.

### Runbook B — CI outage triage
1. Determine affected repos/branches and first failing build.
2. Separate controller, agent, SCM, dependency registry and test failures.
3. Preserve build logs, timestamps, source SHAs and external service errors.
4. Apply bounded recovery, rerun pinned revisions.
5. Confirm test gates, artifact integrity and status checks.
6. Document incident timeline and corrective actions.

### Runbook C — Compromised dependency or artifact
1. Pause promotion and quarantine affected coordinates.
2. Revoke exposed credentials, preserve logs and provenance.
3. Audit registry writes, dependency source and impacted builds.
4. Rebuild under approved clean environment and publish a new immutable version if needed.
5. Notify security/release owners and record containment.

### Runbook D — SonarQube quality gate outage
1. Capture analysis task ID, source SHA and webhook status.
2. Inspect scanner, SonarQube compute engine and Jenkins gate wait.
3. Repair connection or task processing; do not silently skip gate.
4. Re-run analysis for same revision and await server result.
5. Confirm required status and document duration.

### Runbook E — Release rollback
1. Locate previous approved version and digest.
2. Verify artifact exists and checksum matches.
3. Use approved deployment workflow to restore previous version.
4. Validate health, functional smoke and SLOs.
5. Preserve failed release and rollback evidence.

### Runbook F — Storage and retention emergency
1. Inspect agent disk/inodes, Jenkins archive retention and registry quotas.
2. Preserve active and rollback-critical artifacts.
3. Clean only disposable caches/workspaces using reviewed policy.
4. Expand registry capacity or adjust retention with owner approval.
5. Verify previously approved artifacts remain retrievable.

## 10. 100-point enterprise acceptance rubric

| Category | Points |
|---|---:|
| Architecture, ownership and toolchain governance | 10 |
| Maven/Gradle/npm build correctness | 15 |
| Test execution and JUnit evidence | 15 |
| Coverage/static analysis and quality gates | 15 |
| Artifact versioning, immutability and provenance | 15 |
| Registry security and access controls | 10 |
| Observability and capacity | 5 |
| Failure injection and troubleshooting | 10 |
| Recovery, rollback and handover | 5 |
| **Total** | **100** |

Suggested pass: **85/100**, plus all mandatory gates: no secret exposure, required tests execute, quality gates cannot be bypassed, artifact digest verified, and rollback artifact available.

## 11. Final evidence package

- Architecture diagram and ownership matrix.
- Source SHA, toolchain manifest and dependency lockfiles.
- Jenkins build URLs, JUnit/coverage reports and SonarQube task/gate where used.
- Artifact repository coordinate, SHA256 and download verification.
- Failure-injection results with RCA and recovery times.
- Credential review, retention policy and rollback evidence.
- Scored rubric and reviewer sign-off.

**Companion:** [Chapter 040 capstone lab](labs/040-build-testing-artifact-reliability-acceptance-capstone-check.md).  
**Part 08 complete:** Chapters 036–040.  
**Next:** Chapter 041 — Docker Fundamentals and Jenkins Container Build Pipelines, beginning Part 09.
