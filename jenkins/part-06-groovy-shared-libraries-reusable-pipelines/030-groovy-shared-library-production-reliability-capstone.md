# Chapter 030 — Groovy and Shared Library Production Reliability Capstone

**Part 06 — Groovy, Shared Libraries and Reusable Pipelines (final capstone)**  
**Audience:** Jenkins administrators, SREs, DevOps and platform engineers  
**Prerequisites:** Chapters 026–029; disposable Jenkins controller, isolated Linux agent, two application fixture repositories, protected Git tags and a tested rollback path.

## 1. Mission and acceptance scenario

Act as the platform team responsible for an enterprise Shared Library consumed by multiple CI pipelines. Deliver a reusable, versioned, tested, observable and secure build workflow that survives failures without compromising credentials or affecting unrelated consumers.

**Success means:** two consumer fixtures build and test through the same immutable library release; invalid inputs fail closed; Jenkins restart/agent loss scenarios are investigated; a bad release is detected by a canary; and a rollback restores a known-good version with complete evidence.

No production credentials, deployments, or customer repositories are required or permitted in the lab.

## 2. Learning objectives

- Apply Groovy and CPS-safe Pipeline design across `vars/`, `src/`, and `resources/`.
- Enforce validated configuration and fixed allowlists rather than arbitrary shell commands.
- Execute unit, mocked Pipeline, integration and consumer contract tests.
- Prove version pinning, SCM provenance, change approval, progressive release and rollback.
- Produce a 100-point reliability assessment, operational dashboards and incident runbooks.

## 3. Target architecture

```text
Protected shared-library Git repository
  ├─ vars/validateCiConfig.groovy
  ├─ vars/runBuild.groovy
  ├─ vars/runTests.groovy
  ├─ vars/publishArtifacts.groovy
  ├─ src/org/example/ci/CiConfig.groovy
  ├─ resources/org/example/ci/policy.json
  ├─ test/ (unit + Pipeline mock tests)
  └─ immutable version tags
       ↓ Jenkins Shared Library retriever
Disposable Jenkins controller (reviewed plugins / scoped credentials)
       ↓ Pipeline orchestration / CPS
Isolated build agents
       ├─ Maven consumer fixture
       └─ Gradle consumer fixture
       ↓ JUnit reports + archived artifacts + build metadata
Evidence → canary promotion → rollback → SRE acceptance
```

**Security boundary:** Shared Library Groovy is not inherently executed on an isolated agent; Pipeline orchestration executes in Jenkins runtime, whereas `sh`/build tools run on agents. Trusted libraries can bypass the Groovy sandbox. Treat SCM write permissions to trusted library sources as privileged access.

## 4. Reference repository layout

```text
enterprise-ci/
├── vars/
│   ├── validateCiConfig.groovy
│   ├── runBuild.groovy
│   ├── runTests.groovy
│   └── publishArtifacts.groovy
├── src/org/example/ci/CiConfig.groovy
├── resources/org/example/ci/policy.json
├── test/
│   ├── org/example/ci/CiConfigTest.groovy
│   └── RunBuildPipelineTest.groovy
├── Jenkinsfile
├── CHANGELOG.md
├── VERSIONING.md
└── docs/runbooks/
```

Use the implementation and examples from Chapters 027–029. Keep application-specific stage structure in the consumer Jenkinsfile; the library supplies small, reviewed operations.

## 5. Capstone application Jenkinsfile

```groovy
@Library('enterprise-ci@v1.2.0') _

pipeline {
    agent { label 'isolated-linux' }
    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 45, unit: 'MINUTES')
        skipDefaultCheckout(true)
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Validate') {
            steps {
                script {
                    validateCiConfig(
                        environment: 'staging',
                        buildTool: 'maven',
                        timeoutMinutes: 15
                    )
                }
            }
        }
        stage('Build') {
            steps {
                script { runBuild(buildTool: 'maven', timeoutMinutes: 15) }
            }
        }
        stage('Test') {
            steps {
                script { runTests(buildTool: 'maven', timeoutMinutes: 15) }
            }
        }
        stage('Archive') {
            steps {
                script { publishArtifacts(buildTool: 'maven') }
            }
        }
    }
    post {
        always { cleanWs(deleteDirs: true) }
    }
}
```

For the Gradle fixture, use `buildTool: 'gradle'` in the three shared steps and ensure its wrapper is reviewed and executable. This example assumes the JUnit and Workspace Cleanup plugins. The test-report globs must match the fixture's actual output. Never copy this directly to a production controller without review and compatibility testing.

## 6. Build and validation contract

| Gate | Verification | Pass condition |
|---|---|---|
| Source | Protected main branch, peer-reviewed PR | Reviewed changes only |
| Supply chain | Tag and commit SHA recorded; dependencies pinned | Traceable source and toolchain |
| Groovy | Unit tests for default, invalid and boundary inputs | All assertions pass |
| Pipeline mocks | `sh` only executes approved commands | No command on rejected input |
| Integration | Disposable Jenkins with required plugins | Maven and Gradle builds pass |
| Reports | JUnit XML and artifact fingerprint | Visible and retained |
| Security | No embedded secrets or production credentials | Least-privilege configuration |
| Reliability | Failure injection and rollback | Recovery demonstrated |
| Audit | Logs, timings, change record, reviewer | Evidence complete |

## 7. Production-grade reliability controls

1. **Isolation:** allocate dedicated labels, resource limits and ephemeral agents for untrusted code; keep executors off the controller.
2. **Timeouts:** bound overall pipeline duration and individual build/test operations. Account for time spent waiting for agents.
3. **Concurrency:** prevent overlapping jobs when sharing mutable state; prefer immutable artifacts and per-build workspaces.
4. **CPS safety:** retain only serializable state across suspending Pipeline steps; do not invoke Pipeline steps from `@NonCPS` methods.
5. **Dependency hygiene:** pin compatible Jenkins core/plugins and toolchain versions; test upgrades in staging.
6. **Credential scope:** inject secrets only for required operations, never print or interpolate them into Groovy-created shell commands.
7. **Release safety:** protect tags, pin consumer versions and use canary promotion. Do not rewrite release tags.
8. **Audit:** record resolved library SHA, consumer SHA, agent image, plugin versions and acceptance evidence.

## 8. SLOs, SLIs and observability

Define a test-environment reliability scorecard before running the capstone.

| SLI | Example target (lab, not production guarantee) | Measurement |
|---|---|---|
| Valid fixture success | 100% in controlled test suite | Successful valid runs / valid runs |
| Invalid input rejection | 100% | Rejected invalid cases / injected invalid cases |
| Report availability | 100% on successful test runs | Runs with JUnit report / successful runs |
| Artifact availability | 100% on successful package runs | Runs with expected archive / successful runs |
| Canary rollback | Within 15 minutes of decision | Rollback decision to verified successful build |
| Release traceability | 100% | Runs recording tag and resolved commit |

Track queue duration separately from execution duration. Collect controller/agent health, executor utilization, library SCM retrieval errors, build stage duration, test results, retries, timeout counts and unexpected cancellations. Choose production SLOs from observed baselines and business requirements rather than adopting lab targets unchanged.

## 9. Failure injection campaign

| Fault | Expected response | Evidence |
|---|---|---|
| Unknown config key | Fail before any shell step | Validation log |
| Shell injection in build tool | Reject allowlist violation | Mock assertion: zero `sh` calls |
| Missing library tag | Fail during SCM retrieval | Jenkins console and SCM revision |
| Agent offline | Queue or fail safely; cancel/recover | Queue and node logs |
| Missing Maven/Gradle | Fail with clear tool error | Agent PATH and console |
| Failing unit test | Pipeline fails, no success artifact | Test report and stage graph |
| Missing test XML | Strict JUnit gate fails | Report path diagnostics |
| Build exceeds timeout | Jenkins aborts running step | Timeout evidence |
| Nonserializable Groovy state | Detect in integration/restart test | Stack trace and code fix |
| Broken candidate library | Canary fails; unaffected consumers remain pinned | Side-by-side build results |
| Workspace disk pressure | Detect agent issue; clean safely | Disk metrics and cleanup log |
| Credential exposure simulation | Use fake marker only; stop and report | Redacted incident evidence |

Never deliberately leak a real secret or disrupt shared production agents. Some faults require separate disposable controller runs to avoid corrupting the lab baseline.

## 10. Release, canary and rollback runbooks

### Runbook A — Pre-release
1. Record known-good tag, consumer inventory, Jenkins/plugin versions and baseline performance.
2. Review Groovy API changes and security-sensitive commands.
3. Run static checks, unit tests, Pipeline mocks and real Jenkins integration.
4. Run negative tests and verify quality gates fail closed.
5. Approve a protected immutable candidate tag and record its commit SHA.

### Runbook B — Canary promotion
1. Update **one** fixture Jenkinsfile to the candidate version.
2. Run success and failure-path builds; compare results with baseline.
3. Confirm reports, artifact checksums, stage durations and resolved library SHA.
4. Expand only after documented approval; leave other consumers pinned.
5. Stop promotion if any security or reliability gate fails.

### Runbook C — Emergency rollback
1. Declare the issue and pause candidate promotion.
2. Identify the last-known-good immutable tag and affected consumers.
3. Revert consumer pins; do not mutate the candidate or prior tags.
4. Re-run safe smoke tests, validate outputs and record recovery time.
5. Preserve evidence, publish incident analysis and release a new fixed version.

### Runbook D — Controller or agent incident
1. Determine whether the failure is controller, SCM, plugin, agent, toolchain or fixture-specific.
2. Collect logs, queue depth, executor state, disk/memory metrics and stage timestamps.
3. Quarantine unhealthy agent and stop new scheduling there; preserve diagnostics.
4. Restore service in the disposable environment and run a smoke test.
5. Do not use shared writable `JENKINS_HOME` for an active/active controller workaround.

## 11. Troubleshooting matrix

| Symptom | Primary check | Remediation |
|---|---|---|
| `No such DSL method` | `vars/` filename and `call` | Correct API and pinned tag |
| Class not found | `src/` package and compile-time load | Fix path/import |
| `NotSerializableException` | Retained CPS state | Use serializable primitives |
| Sandbox rejection | Trusted/untrusted library boundary | Refactor; avoid blanket approvals |
| Build stuck in queue | Agent label, offline nodes, executors | Restore matching capacity |
| Unexpected shell execution | Allowlist and mock assertions | Fail closed, review change |
| Missing JUnit XML | Fixture output and glob | Correct pattern |
| Artifact not archived | Build output, glob and stage status | Correct archive policy |
| Wrong release loaded | Tag protection and resolved SHA | Pin reviewed revision |
| Controller overloaded | Groovy loops, SCM fetch and agent usage | Shift compute to agents |
| Broken canary | Compare baseline and candidate SHA | Revert pin |
| Rollback fails | Previous tag/fixture compatibility | Restore tested known-good consumer |

## 12. 100-point enterprise acceptance rubric

| Category | Points | Required evidence |
|---|---:|---|
| Architecture and library separation | 15 | Repository tree, ownership, stage visibility |
| Secure config and command validation | 15 | Negative tests, allowlists, no secrets |
| Unit and Pipeline behavior testing | 15 | Test results, mocks, coverage of failure paths |
| Jenkins integration and consumers | 15 | Maven/Gradle runs and compatibility matrix |
| Observability and operational evidence | 10 | Logs, timings, resolved SHAs, report/artifacts |
| Fault injection and incident triage | 10 | Failure matrix and root-cause notes |
| Release governance and supply chain | 10 | Reviewed immutable tag, approval, changelog |
| Canary rollout and verified rollback | 10 | Before/after builds and recovery timing |
| **Total** | **100** | |

**Suggested pass threshold:** 85/100 **and** all critical gates pass: no real credential exposure, no arbitrary command execution, no uncontrolled production deployment, immutable release provenance and a successful rollback. A high score cannot override a critical security failure.

## 13. Final deliverables

- Library repository, reviewed release tag and immutable commit SHA.
- Maven and Gradle consumer fixtures with explicit version pins.
- Unit, mock and integration test results.
- Build and JUnit reports, archived artifact evidence and agent details.
- Fault injection log, rollback runbook and executed rollback record.
- Acceptance score, reviewer sign-off and corrective action backlog.

**Companion:** [Chapter 030 capstone lab](labs/030-groovy-shared-library-production-reliability-capstone-check.md).  
**Part 06 complete after publication:** Chapters 026–030.  
**Next:** Chapter 031 — Jenkins Git and SCM Integration Fundamentals, beginning Part 07.
