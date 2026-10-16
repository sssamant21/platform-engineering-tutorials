# Chapter 029 — Hands-on Lab: Shared Library Testing, Versioning and Release Management

**Environment:** Disposable Jenkins controller, isolated Linux agent, test Git repository and Maven/Gradle fixtures. **Never use production credentials or production deployments.**

## Preparation

Clone the Chapter 028 shared library; create a test branch and pin Java/Groovy/JUnit/JenkinsPipelineUnit dependencies compatible with your target Jenkins version. Prepare at least two fixture Jenkinsfiles: one Maven and one Gradle. Record the starting library tag and commit SHA.

## 20 hands-on exercises

| # | Exercise | Procedure | Expected result |
|---|---|---|---|
| 01 | Baseline | Run both fixture consumers on last-good tag | Baseline status and duration recorded |
| 02 | Test directories | Create `test/` and runner config | Test discovery works |
| 03 | Default contract | Assert normalized defaults | Unit test passes |
| 04 | Valid parameters | Test staging/Gradle/45 minutes | Exact normalized map |
| 05 | Shell injection rejection | Supply disallowed buildTool | Validation fails before shell |
| 06 | Unknown config rejection | Supply unexpected key | Explicit exception |
| 07 | Timeout boundaries | Test 0, 1, 60, 61 | Only 1 and 60 pass |
| 08 | Mock Pipeline steps | Register `sh`, `timeout`, `error` | Test helper runs |
| 09 | Maven command | Call `runBuild` in mock | Approved Maven command observed |
| 10 | Gradle command | Call `runBuild` in mock | Approved Gradle command observed |
| 11 | Negative shell path | Pass injected tool | No `sh` calls |
| 12 | Real Jenkins setup | Configure disposable controller and agent | SCM and library retrieval succeed |
| 13 | Maven integration | Run fixture against candidate tag | Build and test evidence |
| 14 | Gradle integration | Run fixture against candidate tag | Build and test evidence |
| 15 | Failure injection | Introduce failing fixture test | Job fails safely; logs preserved |
| 16 | Compatibility matrix | Test existing consumer API contracts | Pass/fail documented |
| 17 | Candidate tag | Create protected `v1.2.0-rc.1` | Resolved commit matches expected |
| 18 | Canary promotion | Upgrade one fixture only | Other consumer stays on baseline |
| 19 | Breaking change drill | Remove a `vars/` step on a new test ref | Canary detects regression |
| 20 | Rollback | Restore known-good pin | Recovery verified with logs |

## Test execution reference

```bash
# Use your repository's pinned build tool and dependencies.
./gradlew clean test
git status --short
git rev-parse HEAD
git tag -a v1.2.0-rc.1 -m "Shared library release candidate"
git rev-parse 'v1.2.0-rc.1^{commit}'
# Push only after tests and code review.
git push origin v1.2.0-rc.1
```

If your project uses Maven, replace the Gradle command with its equivalent Maven test lifecycle. A test runner must be configured before the command will work.

## 12 troubleshooting drills

1. Rename a `vars/` entry point; verify consumer failure.
2. Introduce a Groovy compilation error; identify the failing test stage.
3. Remove a Pipeline step mock; distinguish test harness failure from product failure.
4. Introduce an unapproved shell value; verify zero shell calls.
5. Point Jenkins to a nonexistent tag; diagnose SCM retrieval.
6. Alter resource path; diagnose missing library resource.
7. Remove a required Jenkins plugin from the disposable controller; document the dependency failure.
8. Break a test fixture intentionally; ensure CI fails rather than publishing artifacts.
9. Force a short timeout on a long-running fixture; confirm cancellation.
10. Disable the isolated agent temporarily; inspect queue and recover.
11. Introduce a backward-incompatible function signature on a candidate ref; catch it with contract tests.
12. Switch canary back to last-good tag and verify recovery.

## Evidence template

```text
Date (UTC):
Jenkins core and plugins:
Library repo / branch / release tag:
Resolved commit SHA:
Test toolchain versions:
Unit tests PASS/FAIL:
Pipeline mock tests PASS/FAIL:
Maven integration PASS/FAIL:
Gradle integration PASS/FAIL:
Consumer contract matrix:
Candidate promotion result:
Injected failure and root cause:
Rollback tag and verification:
Security review:
Approver / open issues:
```

## Acceptance criteria

- [ ] All 20 exercises attempted with recorded outcomes.
- [ ] All 12 drills completed or marked blocked with explanation.
- [ ] Positive and negative unit tests pass.
- [ ] Pipeline mocks verify approved commands and rejected input.
- [ ] Real Jenkins integration confirms both consumer fixtures.
- [ ] Release tag resolves to reviewed commit SHA.
- [ ] Canary and rollback do not affect other consumers.
- [ ] No secrets or production systems were used.
- [ ] Logs, results, screenshots and reviewer sign-off retained.

**Chapter:** [029 — Shared Library Testing, Versioning and Release Management](../029-jenkins-shared-library-testing-versioning-release-management.md).
