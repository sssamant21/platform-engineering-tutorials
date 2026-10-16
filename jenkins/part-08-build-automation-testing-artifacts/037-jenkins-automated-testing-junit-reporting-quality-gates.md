# Chapter 037 — Jenkins Automated Testing, JUnit Reporting and Quality Gates

**Part 08 — Build Automation, Testing and Artifacts**  
**Audience:** SRE, DevOps, platform engineers, QA automation engineers and Jenkins administrators  
**Prerequisites:** Chapter 036, disposable Jenkins controller, isolated test agents, fixture project with deterministic tests and a compatible JUnit plugin.

## 1. Objectives

Design a production-oriented Jenkins test pipeline; execute unit, integration and smoke tests; publish JUnit XML and code coverage; define enforceable quality gates; handle flaky tests and missing reports safely; use parallel test stages with appropriate agent isolation; troubleshoot CI reliability failures; and recover from test infrastructure incidents.

## 2. Testing architecture

```text
Git checkout (immutable SHA)
  ├─ lint / static checks
  ├─ unit tests ───────────────┐
  ├─ integration tests ────────┼─ JUnit XML + coverage + logs
  └─ security checks ──────────┘
            ↓
Jenkins JUnit and artifact publishers
            ↓
Quality gate (tests, coverage, required checks)
            ↓
Release eligibility / blocked promotion
```

Tests should be deterministic, isolated and repeatable. A successful checkout or test command with zero discovered tests is **not** proof of quality.

## 3. Test pyramid and operational boundaries

| Level | Purpose | Typical duration | Common infrastructure |
|---|---|---|---|
| Lint/static | Syntax, formatting, static defects | Seconds | Isolated agent |
| Unit | Logic in small components | Seconds–minutes | No external service |
| Integration | API/DB/cache interaction | Minutes | Disposable dependencies |
| Contract | Consumer/provider compatibility | Minutes | Stub/provider fixture |
| Smoke | Critical end-to-end health | Minutes | Ephemeral staging |
| Performance | Load and latency regression | Longer | Dedicated controlled environment |

Keep PR gates fast and focused; run heavier suites on protected branches or schedules as appropriate. Separate code failures from infrastructure failures and flaky tests.

## 4. JUnit reporting fundamentals

Jenkins `junit` reads JUnit-compatible XML files produced by test runners. It does **not** execute tests itself. Use precise report globs, archive supporting logs and ensure test failures affect build quality.

```groovy
post {
    always {
        junit testResults: 'reports/junit/*.xml',
              allowEmptyResults: false
        archiveArtifacts artifacts: 'reports/logs/**',
                         allowEmptyArchive: true
    }
}
```

If a stage fails before report generation, strict publishing can add a secondary error. Keep the primary failure visible in logs and explicitly distinguish missing reports from zero tests.

## 5. Working fixture with Python unittest

Use a disposable repository with these files:

`app/calculator.py`:
```python
def add(a, b):
    return a + b
```

`tests/test_calculator.py`:
```python
import unittest
from app.calculator import add

class CalculatorTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
```

`requirements-test.txt`:
```text
pytest==8.3.5
pytest-cov==6.0.0
```

Pinning versions is a baseline; for stronger reproducibility use a fully resolved, hash-verified lockfile and reviewed package mirror. A real project should test more than this simple fixture.

## 6. Reference Jenkinsfile

```groovy
pipeline {
    agent { label 'isolated-python' }
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
                sh 'git rev-parse HEAD'
            }
        }
        stage('Test') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    python3 -m venv .venv
                    . .venv/bin/activate
                    python -m pip install -r requirements-test.txt
                    mkdir -p reports/junit reports/coverage
                    python -m pytest tests \
                        --junitxml=reports/junit/unit.xml \
                        --cov=app \
                        --cov-report=xml:reports/coverage/coverage.xml \
                        --cov-fail-under=80
                '''
            }
        }
    }
    post {
        always {
            junit testResults: 'reports/junit/*.xml',
                  allowEmptyResults: false
            archiveArtifacts artifacts: 'reports/coverage/*.xml',
                             allowEmptyArchive: true,
                             fingerprint: true
        }
    }
}
```

**Expected:** fixture test passes, `unit.xml` and `coverage.xml` exist, and Jenkins records a test result. The coverage threshold is a **lab example**, not a universal standard. Use a disposable agent with Python 3 and network access to an approved package repository.

## 7. Multi-stage test architecture

```groovy
stage('Verification') {
    parallel {
        stage('Unit') {
            agent { label 'isolated-python' }
            steps { sh './ci/unit-tests.sh' }
            post {
                always {
                    junit testResults: 'reports/unit/*.xml',
                          allowEmptyResults: false
                }
            }
        }
        stage('Integration') {
            agent { label 'isolated-integration' }
            steps { sh './ci/integration-tests.sh' }
            post {
                always {
                    junit testResults: 'reports/integration/*.xml',
                          allowEmptyResults: false
                }
            }
        }
    }
}
```

The snippet belongs inside a declarative Pipeline `stages` block and assumes executable scripts that generate reports in each agent's workspace. With separate agents, do not expect reports to be visible in a shared workspace. Use `stash/unstash` or per-stage publishing deliberately.

## 8. Quality gates

| Gate | Example policy | Failure behavior |
|---|---|---|
| Test execution | At least one test discovered | Fail |
| Unit tests | All required tests pass | Fail |
| Coverage | At least 80% for fixture | Fail |
| Integration | Required service contracts pass | Fail |
| Static checks | Zero blocking findings | Fail |
| Security | No unapproved critical findings | Fail / explicit exception |
| Reports | JUnit XML present and parseable | Fail |
| Provenance | Tested SHA matches status SHA | Fail |

Quality thresholds should be agreed by code owners, security and SRE teams. Do not blindly copy coverage thresholds across repositories. An exception requires explicit approval, expiry and audit evidence.

## 9. Test failure classification

| Type | Example | Response |
|---|---|---|
| Product defect | Assertion failure | Fix code/test |
| Test defect | Wrong assertion or fixture | Repair test with review |
| Infrastructure | Agent lost, registry timeout | Restore infra; rerun pinned SHA |
| Environment | Database unavailable | Restore disposable service |
| Flaky/non-deterministic | Timing/race condition | Quarantine with ticket and expiry |
| Reporting | XML missing/malformed | Repair reporter; do not report green |
| Security | Secret exposed in test logs | Revoke/rotate and investigate |

Retries can mask flaky tests. Record initial failure, retry count and outcome; do not automatically mark a flaky required gate healthy.

## 10. Test report and coverage governance

- Use a stable JUnit-compatible XML path per suite.
- Preserve stdout/stderr and relevant service logs with redaction.
- Publish coverage in a compatible format and enforce thresholds using the test tool or a verified quality-gate integration.
- Ensure generated reports do not include tokens, private data or customer identifiers.
- Track test count, failure rate, duration and flaky-test trend by branch and commit.
- Retain reports for incident reconstruction and prune according to policy.

## 11. Reliability SLIs

| SLI | Measurement | Suggested lab goal |
|---|---|---|
| Test report availability | Runs with expected JUnit XML / runs | 100% |
| Deterministic fixture result | Identical revision yields same result | 100% |
| Quality-gate enforcement | Injected failures block pipeline | 100% |
| Missing-report detection | No-report runs fail closed | 100% |
| Test duration | Per-suite p50/p95 | Record baseline |
| Flake rate | Retry-success after initial failure | Zero in fixture |

These are lab acceptance goals, not established production SLOs.

## 12. Troubleshooting matrix

| Symptom | Check | Remediation |
|---|---|---|
| No JUnit results | Glob and workspace path | Correct report path |
| JUnit XML malformed | Test runner output | Fix reporter |
| Tests pass but pipeline fails | Coverage or publish gate | Review failing gate |
| Pipeline green with zero tests | Test discovery and flags | Require nonzero tests |
| Test timeout | Deadlock, service, agent limits | Capture thread/log evidence |
| Intermittent failures | Race, clock, external dependency | Isolate and fix flake |
| Integration tests fail | Service readiness and DNS | Restore disposable service |
| Coverage unexpectedly drops | Instrumentation, exclusions | Review source/test changes |
| Agent OOM | Memory requests/limits | Right-size isolated agent |
| Workspace collision | Concurrent jobs share path | Separate workspaces |
| Reports missing in parallel | Different agent workspace | Publish per stage/stash |
| Tests leak credentials | Log masking/fixtures | Revoke and rotate |
| Test retries hide defects | Retry policy | Track original failure |
| Required status missing | Publisher and SHA | Fix status integration |
| Package install fails | Registry auth/TLS | Repair scoped access |

## 13. Production runbooks

### A. Onboard a new test suite
1. Review test framework, expected JUnit XML and dependencies.
2. Run locally in disposable environment and validate nonzero test count.
3. Pin toolchain and package versions; use isolated agent.
4. Configure JUnit, coverage and artifact publishing.
5. Inject a failing assertion and missing-report condition.
6. Review required check and approval policy.

### B. Test infrastructure outage
1. Identify whether failure is agent, dependency registry or test service.
2. Preserve failing build SHA, logs, queue time and service health.
3. Stop uncontrolled retries and restore isolated dependency service.
4. Rerun identical revision and compare results.
5. Record incident impact, recovery time and follow-up.

### C. Flaky test response
1. Preserve first failure and full reproduction details.
2. Reproduce under controlled conditions.
3. Open tracked defect with owner, expiry and impact.
4. Apply approved quarantine only if required; do not silently remove gates.
5. Re-enable and validate after fix.

### D. Coverage regression
1. Verify toolchain, report generator and source revision.
2. Compare changed files, exclusions and instrumentation.
3. Confirm whether reduction reflects real untested code.
4. Restore threshold only via reviewed policy change.
5. Re-run full suite and attach evidence.

## 14. Acceptance checklist

- [ ] Real fixture test executes and generates JUnit XML.
- [ ] Coverage XML is produced and threshold enforced.
- [ ] Missing or malformed reports fail closed.
- [ ] Injected failing assertion blocks success.
- [ ] Parallel suites publish results from correct workspaces.
- [ ] Test provenance, runtime and logs captured.
- [ ] Flaky-test handling and incident runbooks reviewed.
- [ ] Security, artifact retention and rollback documented.

**Companion:** [Chapter 037 hands-on lab](labs/037-jenkins-automated-testing-junit-reporting-quality-gates-check.md).  
**Next:** Chapter 038 — Jenkins Static Analysis, Code Coverage and SonarQube Quality Gates.
