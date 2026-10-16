# Chapter 028 — Reusable Jenkins Pipeline Functions, Configuration and Design Patterns

**Part 06 — Groovy, Shared Libraries and Reusable Pipelines**  
**Audience:** Platform engineers, Jenkins administrators, DevOps and SRE  
**Prerequisites:** Chapters 026–027, disposable Jenkins controller, Git-backed Shared Library and isolated Linux agent.

## Learning outcomes

Build small reusable Pipeline functions; distinguish orchestration from policy and pure logic; design typed configuration validation; implement secure build, test and artifact steps; select appropriate Pipeline patterns; test failure paths; and execute canary rollout and rollback without changing application repositories unexpectedly.

## 1. Reference architecture

```text
application/Jenkinsfile
  ├── @Library('enterprise-ci@v1.1.0') _
  ├── explicit Declarative stages: Validate → Build → Test → Publish
  └── vars/validateCiConfig.groovy
      vars/runBuild.groovy
      vars/runTests.groovy
      vars/publishArtifacts.groovy
          └── src/org/example/ci/CiConfig.groovy  (pure validation)
              resources/org/example/ci/policy.json (nonsecret defaults)
  → Jenkins agent (shell and build tools)
  → artifact store (only with scoped credentials)
```

**Design principle:** Jenkinsfile owns stage structure and business-specific decisions. Shared steps own repeatable operations and guardrails. Groovy library code orchestrates Pipeline steps on the controller; shell commands run on agents. Never treat the Groovy sandbox as an isolation boundary for untrusted build scripts.

## 2. API design contract

| Concern | Pattern | Anti-pattern |
|---|---|---|
| Interface | `call(Map config = [:])` with documented keys | Positional arguments with implicit meaning |
| Validation | Reject unknown environments, tools and invalid timeouts | Trust user-controlled strings |
| Return | Small serializable result maps or strings | File handles, streams or Jenkins runtime objects |
| Errors | Fail explicitly and preserve meaningful logs | Swallow exceptions and report success |
| Stage graph | Keep stages in Jenkinsfile | Hide entire deployment graph in one opaque helper |
| Security | Allowlisted commands and trusted SCM refs | `sh "tool ${userInput}"` |
| Defaults | Version-controlled nonsecret configuration | Hardcoded secrets or implicit production target |
| Evolution | Versioned API, deprecation period and consumer tests | Break all consumers with a mutable default branch |

## 3. Repository structure

```enterprise-ci/
├── vars/
│   ├── validateCiConfig.groovy
│   ├── runBuild.groovy
│   ├── runTests.groovy
│   └── publishArtifacts.groovy
├── src/org/example/ci/CiConfig.groovy
├── resources/org/example/ci/policy.json
├── test/org/example/ci/CiConfigTest.groovy
└── README.md
```

### Pure validation in src/

`src/org/example/ci/CiConfig.groovy`:

```groovy
package org.example.ci

class CiConfig implements Serializable {
    static Map normalize(Map input) {
        Set allowedKeys = ['environment', 'buildTool', 'timeoutMinutes'] as Set
        Set unknown = input.keySet() - allowedKeys
        if (unknown) throw new IllegalArgumentException("Unknown keys: ${unknown}")
        String environment = (input.environment ?: 'dev').toString().trim()
        String tool = (input.buildTool ?: 'maven').toString().trim()
        if (!(environment in ['dev', 'staging', 'prod']))
            throw new IllegalArgumentException('Unsupported environment')
        if (!(tool in ['maven', 'gradle']))
            throw new IllegalArgumentException('Unsupported buildTool')
        int minutes
        try {
            minutes = (input.timeoutMinutes ?: 20).toString().toInteger()
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException('timeoutMinutes must be an integer')
        }
        if (minutes < 1 || minutes > 60)
            throw new IllegalArgumentException('timeoutMinutes must be 1..60')
        return [environment: environment, buildTool: tool, timeoutMinutes: minutes]
    }
}
```

### Pipeline-facing validation

`vars/validateCiConfig.groovy`:

```groovy
import org.example.ci.CiConfig

def call(Map input = [:]) {
    Map normalized = CiConfig.normalize(input)
    echo "Validated CI configuration: environment=${normalized.environment}, tool=${normalized.buildTool}"
    return normalized
}
```

The returned map contains only strings and an integer and is suitable for Pipeline CPS serialization. Validation does not authorize a production deployment; that requires separate access controls and approval.

### Build function

`vars/runBuild.groovy`:

```groovy
def call(Map config = [:]) {
    if (!(config.buildTool in ['maven', 'gradle']))
        error('Unsupported build tool')
    int limit = config.timeoutMinutes as int
    timeout(time: limit, unit: 'MINUTES') {
        if (config.buildTool == 'maven') {
            sh(label: 'Maven package', script: 'mvn -B -ntp -DskipTests package')
        } else {
            sh(label: 'Gradle assemble', script: './gradlew --no-daemon assemble')
        }
    }
}
```

The fixed command allowlist prevents injecting arbitrary shell fragments through `buildTool`. Run on a controlled, isolated agent with the relevant toolchain preinstalled. Use dependency lockfiles, checksum verification and artifact repository controls for reproducibility.

### Test function

`vars/runTests.groovy`:

```groovy
def call(Map config = [:]) {
    if (!(config.buildTool in ['maven', 'gradle']))
        error('Unsupported build tool')
    try {
        timeout(time: config.timeoutMinutes as int, unit: 'MINUTES') {
            if (config.buildTool == 'maven') {
                sh(label: 'Maven tests', script: 'mvn -B -ntp test')
            } else {
                sh(label: 'Gradle tests', script: './gradlew --no-daemon test')
            }
        }
    } finally {
        junit allowEmptyResults: false, testResults: '**/surefire-reports/*.xml,**/test-results/test/*.xml'
    }
}
```

**Operational caveat:** If tests fail before producing XML, `junit allowEmptyResults: false` also fails, which is intentional for a strict quality gate but can obscure the original error. During incident diagnosis inspect both test command output and report collection. Adjust report patterns for the actual build tool.

### Artifact function

`vars/publishArtifacts.groovy`:

```groovy
def call(Map config = [:]) {
    if (!(config.buildTool in ['maven', 'gradle']))
        error('Unsupported build tool')
    String pattern = config.buildTool == 'maven'
        ? 'target/*.jar' : 'build/libs/*.jar'
    archiveArtifacts artifacts: pattern, fingerprint: true, onlyIfSuccessful: true
}
```

`archiveArtifacts` stores artifacts with the Jenkins build, not a durable external artifact registry. Configure retention and external repository publication separately. Avoid archiving credentials, workspace dumps or untrusted paths.

## 4. Application Jenkinsfile: explicit stages

```groovy
@Library('enterprise-ci@v1.1.0') _

pipeline {
    agent { label 'isolated-linux' }
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
    }
    parameters {
        choice(name: 'TARGET_ENV', choices: ['dev', 'staging'], description: 'CI target')
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Validate') {
            steps {
                script {
                    ci = validateCiConfig(
                        environment: params.TARGET_ENV,
                        buildTool: 'maven',
                        timeoutMinutes: 20
                    )
                }
            }
        }
        stage('Build') {
            steps { script { runBuild(ci) } }
        }
        stage('Test') {
            steps { script { runTests(ci) } }
        }
        stage('Archive') {
            steps { script { publishArtifacts(ci) } }
        }
    }
    post {
        always { cleanWs(deleteDirs: true) }
    }
}
```

The sample assumes Workspace Cleanup and JUnit plugins are installed. `ci` is assigned in a `script` block for reuse; for a production implementation prefer a clearly scoped serializable variable initialized before the Declarative pipeline or use an explicit configuration map in each step. Validate on the installed Jenkins and plugin versions. Production deployments are intentionally excluded.

## 5. Configuration and policy layering

1. **Library defaults:** safe, nonsecret defaults in `resources/`; versioned with library release.
2. **Application config:** explicitly supplied tool, environment and timeout; validated by library.
3. **Controller policy:** credential scope, node labels, approvals, plugin configuration and global restrictions; not bypassable by application config.
4. **Deployment policy:** separate release authorization, environment protection, artifact provenance and change record.

Example `resources/org/example/ci/policy.json`:

```json
{
  "schemaVersion": 1,
  "allowedBuildTools": ["maven", "gradle"],
  "maxTimeoutMinutes": 60,
  "productionDeploymentEnabled": false
}
```

A Pipeline step can read this via `libraryResource('org/example/ci/policy.json')` and parse with `groovy.json.JsonSlurperClassic`. Keep the policy in sync with the `CiConfig` validator; otherwise a JSON file that is never consumed gives false assurance. Never place passwords or access tokens in resources.

## 6. Production design patterns

**Functional core / imperative shell:** pure Groovy validation in `src/`, Pipeline steps in `vars/`. This makes most policy logic testable without Jenkins.

**Template method:** keep Checkout/Build/Test/Archive stages visible; use small shared functions to standardize implementation.

**Strategy via allowlist:** choose Maven or Gradle through an explicit validated value, not a free-form command string.

**Fail fast:** validate inputs before agent-intensive work; stop on missing reports, invalid configurations or failed tests.

**Idempotency:** artifact publishing must use immutable build identifiers; retries must not silently overwrite previously approved releases.

**Bulkhead and timeout:** dedicated agent labels and bounded timeouts prevent one slow workload from exhausting shared executors.

**Progressive rollout:** canary consumers pin a new immutable tag, validate metrics, then widen adoption; no unreviewed global default switch.

## 7. Testing pyramid

- **Unit:** test `CiConfig.normalize` against valid, missing, unknown and malicious inputs without Jenkins.
- **Pipeline step tests:** JenkinsPipelineUnit or equivalent mocks assert expected `sh`, `timeout`, `junit` and `archiveArtifacts` invocations.
- **Integration:** disposable Jenkins controller with pinned plugin set, registered library and isolated agent runs a real Maven or Gradle fixture.
- **Acceptance:** compare success/failure results, timing, test reports, artifacts, auditability and rollback.

Example Spock-independent Groovy assertions:

```groovy
import org.example.ci.CiConfig
assert CiConfig.normalize([buildTool:'maven']).environment == 'dev'
assert CiConfig.normalize([timeoutMinutes:60]).timeoutMinutes == 60
try {
    CiConfig.normalize([buildTool:'maven; curl attacker'])
    assert false : 'Expected validation failure'
} catch (IllegalArgumentException expected) {
    assert expected.message == 'Unsupported buildTool'
}
```

## 8. Troubleshooting matrix

| Symptom | Investigation | Remediation |
|---|---|---|
| `No such DSL method runBuild` | Confirm `vars/runBuild.groovy` and library tag | Fix name or pinned ref |
| Unknown key rejected | Inspect caller map and API version | Correct key; add explicit migration |
| `NotSerializableException` | Find retained nonserializable state across steps | Return primitives/maps; isolate pure logic |
| Missing JUnit reports | Verify actual workspace XML paths | Fix report glob and test command |
| Maven unavailable | Verify agent image, PATH and label | Use approved toolchain agent |
| Gradle wrapper denied | Check file mode and checkout | Commit executable wrapper; verify provenance |
| Build hangs | Inspect timeout and agent queue | Distinguish queue delay from running step |
| Library tag resolves unexpectedly | Inspect SCM revision and tag protection | Pin and protect immutable tag |
| Artifact missing | Inspect build outputs and archive glob | Correct path; do not weaken quality gate |
| Credential leak in log | Review masking and command invocation | Revoke/rotate secret, remove unsafe interpolation |
| Pipeline fails after Jenkins restart | Check CPS serialization and durable-task logs | Remove nonserializable objects, rerun safely |
| Controller CPU spike | Inspect Groovy loops and library initialization | Move heavy computation to agents |

## 9. SRE operational runbooks

### A. Release reusable functions
1. Record baseline build success, P95 duration, queue delay and test failure rate.
2. Run pure unit tests, mocked Pipeline tests and disposable Jenkins integration.
3. Review changes to `vars/`, `src/`, `resources/` and security-sensitive commands.
4. Create protected immutable release tag; record commit SHA and plugin compatibility.
5. Upgrade one canary Jenkinsfile, run both success and failure scenarios, then expand.
6. Record approval, affected consumers, release version and validation evidence.

### B. Roll back a broken shared function
1. Pause expansion and identify impacted jobs and most recent known-good tag.
2. Change consumers from `enterprise-ci@v1.1.0` to the known-good immutable tag.
3. Re-run a safe test build; verify report and artifact integrity.
4. Preserve failed build logs and SCM revisions; open corrective action.
5. Do not force-move an existing release tag.

### C. Suspected compromised library
1. Disable affected builds and restrict library repository writes.
2. Identify loaded revisions and jobs executed during exposure.
3. Revoke potentially exposed credentials and audit artifact destinations.
4. Restore from reviewed commit, rotate secrets, validate controller integrity and record incident timeline.

## 10. Acceptance criteria

- [ ] Four reusable steps and pure configuration validator are version controlled.
- [ ] Library is loaded from a protected immutable version.
- [ ] Positive and negative validation tests pass.
- [ ] Jenkinsfile exposes Checkout, Validate, Build, Test and Archive stages.
- [ ] Build commands run only on isolated agents with approved tools.
- [ ] JUnit XML and expected artifacts are collected, or failures are explicitly explained.
- [ ] No credentials or arbitrary shell command inputs appear in configuration.
- [ ] Canary and rollback drills produce evidence.
- [ ] Consumer compatibility and plugin dependencies are documented.

**Companion:** [Chapter 028 hands-on lab](labs/028-reusable-jenkins-pipeline-functions-configuration-design-patterns-check.md).  
**Next:** Chapter 029 — Jenkins Shared Library Testing, Versioning and Release Management.
