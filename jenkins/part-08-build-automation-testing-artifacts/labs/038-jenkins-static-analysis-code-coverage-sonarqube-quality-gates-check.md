# Chapter 038 — Hands-on Lab: Static Analysis, Coverage and SonarQube Quality Gates

**Environment:** Disposable Jenkins, isolated Python agent, nonproduction SonarQube server, fixture project and project-scoped analysis token.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record Jenkins, scanner plugin, SonarQube version | Baseline |
| 02 | Fixture setup | Commit Python calculator and tests | SHA |
| 03 | Sonar project | Create fixture project/key | Project ID |
| 04 | Token | Provision scoped analysis token | Credential ID only |
| 05 | Jenkins server | Configure SonarQube global connection | Connectivity |
| 06 | Scanner tool | Configure approved scanner | Version |
| 07 | Unit tests | Run pytest fixture | Pass |
| 08 | JUnit XML | Generate and publish report | Test count |
| 09 | Coverage XML | Run pytest-cov | Coverage % |
| 10 | Properties | Configure source/test/report paths | Config evidence |
| 11 | Analysis | Execute scanner | Analysis task ID |
| 12 | Webhook | Configure SonarQube → Jenkins webhook | Delivery evidence |
| 13 | Quality Gate | Run `waitForQualityGate` | Final status |
| 14 | Coverage failure | Raise fixture threshold above coverage | Pipeline blocks |
| 15 | Static finding | Introduce approved test code smell | Finding |
| 16 | Credential failure | Revoke test token | 401/403 |
| 17 | Webhook failure | Temporarily disable test webhook | Timeout detected |
| 18 | Background queue | Observe task processing time | Latency |
| 19 | Recovery | Restore token/webhook and rerun | Gate passes |
| 20 | Acceptance | Correlate SHA, task, gate and build | Reviewer record |

## 12 troubleshooting drills

1. Scanner token expired.
2. Project analyze permission denied.
3. Scanner-to-SonarQube DNS/TLS failure.
4. Missing coverage XML.
5. Wrong Sonar source directory.
6. Invalid Sonar project key.
7. Scanner submits but webhook not delivered.
8. Webhook secret mismatch.
9. Quality gate returns ERROR.
10. SonarQube background task fails.
11. Wrong SCM SHA in analysis.
12. Scanner/Server plugin incompatibility.

For each drill capture failure, task ID, logs, root cause, remediation and retest. Mark unsupported edition features blocked rather than assuming they work.

## Fixture source

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

`requirements-test.txt`:
```text
pytest==8.3.5
pytest-cov==6.0.0
```

`sonar-project.properties`:
```properties
sonar.projectKey=jenkins-ch038-fixture
sonar.sources=app
sonar.tests=tests
sonar.python.coverage.reportPaths=reports/coverage.xml
sonar.python.version=3
```

Run tests before scanner:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-test.txt
mkdir -p reports
python -m pytest tests --junitxml=reports/junit.xml \
  --cov=app --cov-report=xml:reports/coverage.xml \
  --cov-fail-under=80
```

## Evidence template

```text
UTC timestamp:
Git SHA and Jenkins build:
Jenkins/SonarQube/plugin/scanner versions:
Sonar project key:
Credential ID (not value):
Test count and JUnit path:
Coverage percentage and XML path:
Analysis task ID:
Webhook delivery and HTTP status:
Quality Gate result:
Injected fault:
Root cause:
Recovery:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or explicitly blocked.
- [ ] JUnit and coverage XML generated.
- [ ] Scanner and SonarQube task correlated to source SHA.
- [ ] Quality Gate awaited before promotion.
- [ ] Quality failure blocks pipeline.
- [ ] Webhook and credential recovery rehearsed.
- [ ] No production tokens or privileged untrusted builds used.

**Related:** [Chapter 038 — Static Analysis and SonarQube](../038-jenkins-static-analysis-code-coverage-sonarqube-quality-gates.md).
