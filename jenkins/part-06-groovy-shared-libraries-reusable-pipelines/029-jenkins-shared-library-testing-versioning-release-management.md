# Chapter 029 — Jenkins Shared Library Testing, Versioning and Release Management

**Part 06 — Groovy, Shared Libraries and Reusable Pipelines**  
**Audience:** Jenkins administrators, SRE, DevOps and platform engineers  
**Prerequisites:** Chapters 026–028; isolated Jenkins test controller; Git; Java and a compatible Groovy toolchain.

## Learning objectives

Create a test pyramid for `src/` and `vars/` code, simulate Jenkins Pipeline steps, validate real builds on a disposable controller, version shared library APIs, control release provenance, run compatibility tests, safely promote a new release and recover from regressions.

## 1. Enterprise release architecture

```text
Pull request
  → static review and secret scanning
  → pure Groovy unit tests (src/)
  → JenkinsPipelineUnit behavior tests (vars/)
  → ephemeral Jenkins controller integration
  → consumer contract matrix
  → signed/protected release tag (where supported)
  → canary application Jenkinsfiles
  → staged consumer promotion
  → SLO monitoring / rollback
```

A shared library is executable CI infrastructure. A regression can affect many repositories simultaneously; a compromised trusted library can access sensitive Jenkins controller APIs. The test controller and agent must not contain production credentials.

## 2. Testing layers and responsibility

| Layer | Scope | Fast feedback | Acceptance |
|---|---|---|---|
| Static | Groovy syntax, dependency hygiene, secret scanning | Every PR | No critical findings |
| Unit | Pure `src/` validation and transformation | Every PR | Positive/negative cases pass |
| Pipeline mock | `vars/` calls to `sh`, `error`, `timeout`, `junit` | Every PR | Exact approved behavior |
| Integration | Real Jenkins plugin, CPS and agent behavior | PR/release candidate | Build/test/archive verified |
| Consumer contract | Existing application Jenkinsfiles with new tag | Release candidate | No breaking behavior |
| Resilience | Agent loss, SCM errors, timeout, restart | Before major release | Safe failure/recovery |

Mock tests **do not** prove Jenkins sandbox, CPS serialization, plugin integration, SCM resolution or durable-task behavior. Those require integration tests.

## 3. Recommended repository layout

```text
enterprise-ci/
├── vars/
│   ├── validateCiConfig.groovy
│   ├── runBuild.groovy
│   └── runTests.groovy
├── src/org/example/ci/CiConfig.groovy
├── resources/org/example/ci/policy.json
├── test/
│   ├── org/example/ci/CiConfigTest.groovy
│   └── RunBuildPipelineTest.groovy
├── Jenkinsfile
├── CHANGELOG.md
├── VERSIONING.md
└── README.md
```

Pin Java, Groovy, JUnit and JenkinsPipelineUnit versions in your build system and test the versions compatible with your target Jenkins core/plugins. Avoid downloading arbitrary build tools on a production controller.

## 4. Pure unit tests for src/

Use the `CiConfig` class from Chapter 028. Example JUnit 4 test at `test/org/example/ci/CiConfigTest.groovy`:

```groovy
package org.example.ci

import org.junit.Test
import static org.junit.Assert.*

class CiConfigTest {
    @Test void defaultsAreStable() {
        assertEquals(
            [environment:'dev', buildTool:'maven', timeoutMinutes:20],
            CiConfig.normalize([:])
        )
    }

    @Test void acceptsExplicitValues() {
        def c = CiConfig.normalize([
            environment:'staging', buildTool:'gradle', timeoutMinutes:45
        ])
        assertEquals('gradle', c.buildTool)
        assertEquals(45, c.timeoutMinutes)
    }

    @Test void rejectsShellInjection() {
        try {
            CiConfig.normalize([buildTool:'maven; curl example.invalid'])
            fail('Expected rejection')
        } catch (IllegalArgumentException expected) {
            assertEquals('Unsupported buildTool', expected.message)
        }
    }

    @Test void rejectsUnknownConfiguration() {
        try {
            CiConfig.normalize([rawShell:'echo unsafe'])
            fail('Expected rejection')
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.message.contains('Unknown keys'))
        }
    }
}
```

For a Gradle-based library, configure `sourceSets.main.groovy.srcDirs = ['src', 'vars']` and `sourceSets.test.groovy.srcDirs = ['test']` where appropriate, and pin `org.codehaus.groovy:groovy`, JUnit and the pipeline testing library versions explicitly. For a Maven build, use a Groovy compiler plugin configured for the same source directories. Exact dependency versions are intentionally environment-specific: validate against your controller's Jenkins and Groovy compatibility.

## 5. Pipeline step behavior tests

A mocked Pipeline test should verify that approved commands execute, disallowed input fails **before** `sh`, and timeout behavior is bounded.

Example using JenkinsPipelineUnit (adapt the test helper API to the pinned library version):

```groovy
import com.lesfurets.jenkins.unit.BasePipelineTest
import org.junit.Before
import org.junit.Test
import static org.junit.Assert.*

class RunBuildPipelineTest extends BasePipelineTest {
    List<String> commands

    @Before
    void setUp() {
        super.setUp()
        commands = []
        helper.registerAllowedMethod('sh', [Map]) { Map args ->
            commands << args.script.toString()
            return 0
        }
        helper.registerAllowedMethod('timeout', [Map, Closure]) {
            Map args, Closure body -> body.call()
        }
        helper.registerAllowedMethod('error', [String]) {
            String message -> throw new IllegalArgumentException(message)
        }
    }

    @Test
    void executesApprovedMavenCommand() {
        def step = loadScript('vars/runBuild.groovy')
        step.call([buildTool:'maven', timeoutMinutes:20])
        assertEquals(['mvn -B -ntp -DskipTests package'], commands)
    }

    @Test
    void rejectsUnapprovedToolWithoutShell() {
        def step = loadScript('vars/runBuild.groovy')
        try {
            step.call([buildTool:'maven; echo unsafe', timeoutMinutes:20])
            fail('Expected rejection')
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.message.contains('Unsupported'))
        }
        assertTrue(commands.isEmpty())
    }
}
```

Configure JenkinsPipelineUnit's script roots to include the library's `vars/` directory and register other mocked Pipeline steps used by your implementation. The example is a behavioral pattern, not evidence that tests have been run.

## 6. Real Jenkins integration tests

Use a disposable controller with a pinned Jenkins core/plugin manifest and an isolated agent. A typical acceptance Jenkinsfile:

```groovy
@Library('enterprise-ci@v1.2.0-rc.1') _

pipeline {
    agent { label 'isolated-linux' }
    options { timestamps(); timeout(time: 30, unit: 'MINUTES') }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Validate') {
            steps {
                script {
                    def c = validateCiConfig(
                        environment:'staging',
                        buildTool:'maven',
                        timeoutMinutes:15
                    )
                    echo "Validated ${c.environment}"
                }
            }
        }
        stage('Build') {
            steps {
                script {
                    runBuild(buildTool:'maven', timeoutMinutes:15)
                }
            }
        }
    }
}
```

Capture: Jenkins core/plugin versions, SCM revision, library resolved commit, agent image, stage timing, logs, test XML, artifact checksums and failure details. Confirm restart behavior separately: Jenkins Pipeline steps can suspend and resume, and mocking cannot verify that property.

## 7. Semantic versioning and compatibility

| Change | Suggested release | Example |
|---|---|---|
| Fix without changing public behavior | PATCH | 1.1.0 → 1.1.1 |
| Backward-compatible optional config | MINOR | 1.1.0 → 1.2.0 |
| Rename/remove `vars/` step or required key | MAJOR | 1.x → 2.0.0 |
| Candidate under test | Prerelease | v1.2.0-rc.1 |

Public API includes `vars/` names, `call` signatures, accepted config keys, return types, failure behavior and any documented resource schema. A change that silently changes default deployment environment may be breaking even if the Groovy signature stays the same.

Publish a migration note for every breaking change. Maintain old and new entry points during an agreed deprecation window, test both, and enumerate affected consumers.

## 8. Immutable release workflow

```bash
git status --short
git fetch --tags origin
git checkout main
git pull --ff-only
# Only after CI and review approval:
git tag -a v1.2.0 -m "Enterprise CI shared library v1.2.0"
git rev-parse v1.2.0^{commit}
git push origin v1.2.0
```

Require protected tags/branch rules and release approval where supported. Annotated tags alone do not guarantee authenticity; use signing and verification if supported by the organization's tooling. Never force-move a released tag. Record the immutable commit SHA and build/test provenance.

## 9. Version selection in Jenkins

```groovy
@Library('enterprise-ci@v1.2.0') _
```

Prefer explicit, reviewed versions in consuming Jenkinsfiles. An SCM tag can be retargeted unless protected; a commit SHA provides stronger revision specificity where the configured retriever supports it. Verify actual resolved SCM revision in build logs. A global default version or automatic branch tracking can unexpectedly change many consumers.

Runtime `library()` loading differs from compile-time `@Library`; classes from runtime-loaded libraries cannot be statically imported the same way. Test the actual consumption mode.

## 10. Consumer compatibility matrix

| Consumer | Pinned version | Candidate | Validation |
|---|---|---|---|
| Java/Maven CI | v1.1.0 | v1.2.0-rc.1 | Package, tests, artifact |
| Gradle CI | v1.1.0 | v1.2.0-rc.1 | Assemble, tests, artifact |
| Kubernetes delivery | v1.1.0 | v1.2.0-rc.1 | Dry-run only; no production apply |
| Scheduled maintenance | v1.1.0 | v1.2.0-rc.1 | Timeout, retry, cancellation |

Record the pass/fail result for each **actual** consumer fixture; the matrix is a template, not a claim of successful testing.

## 11. Troubleshooting and failure injection

| Failure | Verification | Corrective action |
|---|---|---|
| Unit test fails after new default | Compare API contract and expected map | Version and document changed behavior |
| Pipeline mock passes, Jenkins fails | Check CPS, sandbox, plugin APIs | Add real controller integration |
| Missing `vars/` step | Inspect tag tree and global step name | Correct release contents |
| Wrong library revision | Inspect resolved SCM SHA | Pin and protect release ref |
| `NotSerializableException` | Inspect retained objects across steps | Use primitives/serializable state |
| Groovy dependency mismatch | Compare runtime and test compiler versions | Align supported toolchain |
| Plugin missing | Compare pinned plugin manifest | Install/test compatible plugin |
| Resource lookup fails | Check `resources/` path and library mode | Correct path and retriever |
| Test hangs | Inspect queue and timeout | Cancel, investigate agent availability |
| Flaky tests | Compare agent image, cache and external dependencies | Isolate deterministic fixtures |
| Trusted library security issue | Audit SCM write permissions | Restrict authorship; rotate secrets if exposed |
| Canary regression | Compare baseline and candidate logs | Revert consumer to last good tag |

## 12. Operational runbooks

### Runbook A — Release candidate
1. Freeze intended API contract; collect consumer inventory and baseline SLOs.
2. Execute static scans, pure unit tests, Pipeline mock tests and real Jenkins integration.
3. Verify negative paths: invalid inputs, failed tests, timeout and agent unavailability.
4. Review changelog, permissions, release notes, dependency and plugin compatibility.
5. Create immutable prerelease tag; validate canary consumers and capture evidence.
6. Promote the reviewed commit to final release tag without rewriting existing tags.

### Runbook B — Staged promotion
1. Select one noncritical consumer and pin its Jenkinsfile to the release tag.
2. Compare build success rate, P95 runtime, queue duration and test report quality.
3. Expand to a second cohort only after acceptance and stakeholder approval.
4. Preserve rollback mapping of consumer → previous tag.
5. Pause immediately if security, data integrity or reliability gates fail.

### Runbook C — Rollback and incident response
1. Halt promotion and identify impacted consumers and release SHA.
2. Change Jenkinsfile pins back to the last known-good immutable tag.
3. Re-run safe validation, preserving failed logs and test artifacts.
4. Investigate credential exposure, unauthorized changes and artifact integrity.
5. Publish corrective action and a new fixed release; never overwrite a released tag.

## 13. Enterprise acceptance checklist

- [ ] Pure `src/` logic tested with positive and negative inputs.
- [ ] `vars/` behavior tested with approved and rejected command paths.
- [ ] Real disposable Jenkins integration validates plugins, CPS and agent behavior.
- [ ] At least two representative consumer fixtures tested.
- [ ] Release API and semantic version changes documented.
- [ ] Tag protection and SCM revision evidence captured.
- [ ] Canary promotion and rollback performed without production impact.
- [ ] Secrets and controller access reviewed.
- [ ] Build logs, JUnit reports, timing and artifacts preserved for audit.

**Companion:** [Chapter 029 hands-on lab](labs/029-jenkins-shared-library-testing-versioning-release-management-check.md).  
**Next:** Chapter 030 — Groovy and Shared Library Production Reliability Capstone.
