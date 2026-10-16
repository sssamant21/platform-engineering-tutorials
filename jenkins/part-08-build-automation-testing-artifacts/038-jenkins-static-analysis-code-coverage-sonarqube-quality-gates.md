# Chapter 038 — Jenkins Static Analysis, Code Coverage and SonarQube Quality Gates

**Part 08 — Build Automation, Testing and Artifacts**  
**Audience:** Jenkins SRE/DevOps, platform engineering, security and application owners  
**Prerequisites:** Chapters 036–037, disposable Jenkins with approved SonarQube Scanner for Jenkins integration, isolated agent, nonproduction SonarQube instance, fixture project and project-scoped token.

## 1. Objectives

Implement static analysis and coverage in Jenkins; distinguish scanners, code quality, security rules and quality gates; integrate SonarQube safely; publish verifiable test and coverage evidence; enforce asynchronous quality gate results; diagnose failures; and rehearse rollback and production operations.

## 2. Architecture

```text
SCM immutable commit
       ↓
Jenkins isolated agent
  ├── build + unit tests → JUnit XML
  ├── coverage generator → coverage XML
  ├── lint/static analyzers → findings
  └── SonarScanner → SonarQube analysis task
                          ↓ asynchronous processing
                      SonarQube server
                          ↓ webhook (validated)
                    Jenkins quality gate
                          ↓
                pass / block promotion
```

A scanner's successful exit means the report was submitted, **not** that the quality gate passed. Quality gate status is determined after SonarQube background processing. Jenkins must wait for the actual gate decision before promotion.

## 3. Quality controls and ownership

| Control | Producer | Gate |
|---|---|---|
| Unit tests | Maven/Gradle/pytest/Jest | Required tests pass |
| Coverage | JaCoCo, coverage.py, LCOV-compatible runner | Reviewed project threshold |
| Lint | ESLint, Checkstyle, Ruff, etc. | No blocking findings |
| Static analysis | SonarQube scanner + server | Server-side Quality Gate |
| Dependency vulnerabilities | Dedicated SCA scanner | Approved security policy |
| Secrets | Secret-scanning tool | No exposed secrets |
| Provenance | Git/Jenkins | Tested SHA matches analysis SHA |

Do not equate SonarQube analysis with comprehensive SAST/SCA or supply-chain security. SonarQube capabilities and branch/PR analysis support depend on product edition and configuration; verify licensing and installed versions.

## 4. Prerequisites and credential model

1. Pin Jenkins core, SonarQube Scanner for Jenkins plugin and scanner versions using approved compatibility matrix.
2. Configure a SonarQube server in Jenkins global settings with HTTPS URL and a project-scoped analysis token stored as a Jenkins credential.
3. Configure an appropriate SonarScanner installation or a pinned scanner in the isolated agent image.
4. Configure a **SonarQube → Jenkins** webhook using the endpoint documented for the installed plugin (commonly `https://jenkins.example/sonarqube-webhook/` including trailing slash).
5. Restrict webhook ingress and configure webhook secret verification if supported.
6. Ensure agent-to-SonarQube network access and Jenkins-to-SonarQube API access for quality gate polling/status as required.

Never expose SonarQube tokens in `sonar-project.properties`, command-line echo, PR builds with untrusted code or Jenkins console output. Limit scan credentials to approved trusted branches/agents if scanning arbitrary contributed code could exfiltrate them.

## 5. Minimal Python fixture

Repository layout:

```text
.
├── app/__init__.py
├── app/calculator.py
├── tests/test_calculator.py
├── requirements-test.txt
├── sonar-project.properties
└── Jenkinsfile
```

`app/calculator.py`:
```python
def add(a, b):
    return a + b
```

`tests/test_calculator.py`:
```python
from app.calculator import add

def test_add():
    assert add(2, 3) == 5
```

`requirements-test.txt` (lab versions; update to approved supported versions):
```text
pytest==8.3.5
pytest-cov==6.0.0
```

`sonar-project.properties`:
```properties
sonar.projectKey=jenkins-ch038-fixture
sonar.projectName=Jenkins Chapter 038 Fixture
sonar.sources=app
sonar.tests=tests
sonar.python.coverage.reportPaths=reports/coverage.xml
sonar.python.version=3
```

The project key must exist or be creatable by the configured SonarQube identity. SonarQube's configured gate must be appropriate for the fixture and verified independently.

## 6. Jenkins Pipeline example

The following is a **trusted-branch fixture**; it assumes a configured Jenkins SonarQube server named `sonarqube-lab`, a scanner installation named `SonarScanner`, and a valid webhook:

```groovy
pipeline {
    agent { label 'isolated-python' }
    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Unit tests and coverage') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    python3 -m venv .venv
                    . .venv/bin/activate
                    python -m pip install -r requirements-test.txt
                    mkdir -p reports
                    python -m pytest tests --junitxml=reports/junit.xml \
                      --cov=app --cov-report=xml:reports/coverage.xml \
                      --cov-fail-under=80
                '''
            }
        }
        stage('SonarQube analysis') {
            steps {
                script {
                    def scannerHome = tool 'SonarScanner'
                    withSonarQubeEnv('sonarqube-lab') {
                        sh "${scannerHome}/bin/sonar-scanner"
                    }
                }
            }
        }
        stage('Quality Gate') {
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }
    }
    post {
        always {
            junit testResults: 'reports/junit.xml', allowEmptyResults: false
            archiveArtifacts artifacts: 'reports/coverage.xml',
                             allowEmptyArchive: true, fingerprint: true
        }
    }
}
```

**Pipeline configuration note:** The empty `tools` directive is not needed and should be removed when copying this example; scanner resolution occurs through `tool 'SonarScanner'`. The quality gate wait normally does not require an executor; placing the wait in a separate `agent none` stage or separate pipeline structure can conserve agent capacity for long background tasks. Validate syntax against the installed Jenkins Declarative Pipeline version before production use.

The scan and `waitForQualityGate` must run within the same Pipeline flow with the analysis task metadata available. For multiple analyses in one Pipeline, associate each gate wait with its corresponding analysis task.

## 7. Coverage and static-analysis policy

| Policy | Example | Caveat |
|---|---|---|
| New-code coverage | At least 80% | Team-specific, not universal |
| Overall coverage | Trend monitored | Legacy debt may require staged goals |
| New bugs | Zero high-priority new issues | Depends on quality profile |
| New vulnerabilities | Zero unapproved findings | Requires security triage |
| Duplications | Below agreed threshold | Language/project-specific |
| Quality gate | SonarQube status OK | Must wait for server decision |
| Missing reports | Fail closed | Prevent false green |

SonarQube Quality Gate rules and names vary by edition/version. Prefer governing **new code** without hiding serious existing defects. A passing gate does not prove the software is secure.

## 8. Pull request and branch analysis

PR analysis requires provider integration and SonarQube edition/features supporting it. Use provider-generated PR metadata only after validating branch source and trust policy. Never place analysis tokens in untrusted fork workspaces; use a trusted analysis workflow or isolate token-bearing analysis from contributor-controlled build scripts.

Status reporting must refer to the analyzed revision. If GitHub/GitLab and SonarQube both publish checks, avoid conflicting required contexts.

## 9. Observability and SLOs

| Signal | Measurement |
|---|---|
| Analysis submission success | Scanner exit and task ID |
| Quality gate completion latency | Submission → decision |
| Webhook delivery errors | 4xx/5xx and secret failures |
| Analysis backlog | SonarQube background task queue |
| Coverage report availability | XML present and parsed |
| Gate correctness | Injected failure blocks promotion |
| Scanner duration | Per-project p50/p95 |
| Token rotation age | Credential expiry and ownership |

A reasonable lab objective is 100% correlation among commit SHA, analysis task, gate result and Jenkins build. Production targets require observed baselines.

## 10. Troubleshooting matrix

| Symptom | Diagnosis | Recovery |
|---|---|---|
| Scanner 401 | Expired/wrong token | Rotate scoped token |
| Scanner 403 | Project permission | Grant minimal analyze rights |
| Scanner TLS failure | CA trust | Repair CA; do not disable TLS |
| Scanner cannot reach server | DNS/proxy/network | Restore approved route |
| Coverage 0% | Wrong report path | Align report config |
| Scanner succeeds, gate hangs | Missing webhook/task linkage | Fix webhook and metadata |
| Webhook 404 | Wrong endpoint/trailing slash | Correct plugin-specific URL |
| Webhook 403 | Secret mismatch | Rotate/verify secret |
| Background task failed | SonarQube compute engine logs | Resolve server issue |
| Wrong project key | Project config | Correct key and permissions |
| PR not analyzed | Edition/provider integration | Verify supported feature |
| Status on wrong SHA | SCM checkout mismatch | Reconcile analysis revision |
| Missing JUnit XML | Test failed before report | Diagnose primary failure |
| Gate returns ERROR | Quality profile/threshold | Fix issue or approved exception |
| Agent disk full | Workspace/cache growth | Safe cleanup and quota |
| Scanner version mismatch | Plugin/server compatibility | Pin supported versions |

## 11. Production runbooks

### A. Onboard a project
1. Review project owner, language, branch protection, quality profile and SonarQube edition.
2. Create scoped analysis identity; store credential securely.
3. Configure scanner, report paths and webhook secret.
4. Run known-good fixture and verify task ID, SHA, coverage and gate.
5. Inject quality gate failure and confirm promotion is blocked.
6. Document owner, token rotation and incident response.

### B. Quality gate outage
1. Preserve Jenkins build URL, commit SHA and SonarQube task ID.
2. Inspect scanner submission, background task and webhook delivery separately.
3. Check SonarQube health and Jenkins endpoint validation.
4. Repair configuration; rerun analysis on the same immutable revision.
5. Confirm final gate result; do not override fail-closed controls without approved exception.

### C. False coverage regression
1. Verify test runner, XML path, source roots and exclusions.
2. Compare tool versions, checkout SHA and coverage generator output.
3. Correct mapping or test configuration, not the threshold by default.
4. Rerun and confirm SonarQube ingests expected report.
5. Record change and review.

### D. Token compromise
1. Revoke token, pause affected analysis jobs.
2. Audit Jenkins and SonarQube logs; preserve redacted evidence.
3. Rotate credential with least privilege.
4. Verify no secret exposure in PR logs/artifacts.
5. Obtain security sign-off before resuming.

### E. Scanner/plugin rollback
1. Preserve plugin/tool manifests, configuration and analysis task IDs.
2. Restore previously reviewed compatible scanner/plugin versions in a disposable environment.
3. Re-run fixture and verify webhook/gate behavior.
4. Plan controlled production change only after test acceptance.
5. Avoid unreviewed plugin downgrade on a live controller.

## 12. Acceptance checklist

- [ ] Real test suite produces JUnit XML and coverage XML.
- [ ] Scanner submits analysis for expected project/SHA.
- [ ] Quality gate decision is awaited and enforced.
- [ ] Injected coverage/quality failure blocks promotion.
- [ ] Missing webhook and invalid token failures detected.
- [ ] Secrets isolated from untrusted PR code.
- [ ] SonarQube task and Jenkins build correlated.
- [ ] Recovery and rollback documented.

**Companion:** [Chapter 038 hands-on lab](labs/038-jenkins-static-analysis-code-coverage-sonarqube-quality-gates-check.md).  
**Next:** Chapter 039 — Jenkins Artifact Management, Versioning and Repository Integration.
