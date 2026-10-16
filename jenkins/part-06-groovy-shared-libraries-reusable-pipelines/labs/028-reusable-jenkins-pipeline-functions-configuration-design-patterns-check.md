# Chapter 028 — Hands-on Lab: Reusable Pipeline Functions and Configuration Patterns

**Scope:** Disposable Jenkins controller and isolated Linux agent only. Never run these exercises against production credentials, deployment targets or customer repositories.

## Prerequisites and setup

Use a test SCM repository for `enterprise-ci` and a separate fixture application repository with a minimal Maven or Gradle project and at least one passing test. Ensure Pipeline, Git, JUnit and Workspace Cleanup plugins are available, an agent labeled `isolated-linux` exists, and library version tags are protected. Record Jenkins version, relevant plugin versions, Git commit SHA, agent image and test timestamp.

## Exercises (18)

| # | Exercise | Procedure | Expected evidence |
|---|---|---|---|
| 01 | Baseline | Run fixture's existing Jenkinsfile | Build URL, status and duration |
| 02 | Library tree | Create `vars/`, `src/`, `resources/`, `test/` | SCM tree screenshot or commit |
| 03 | Pure validator | Implement `CiConfig.normalize` from chapter | Groovy class compiles |
| 04 | Defaults | Validate omitted optional keys | `dev/maven/20` returned |
| 05 | Reject unknown key | Pass `command:'rm -rf /'` | Explicit validation failure, no command execution |
| 06 | Reject tool injection | Pass `buildTool:'maven; echo unsafe'` | Fail before shell invocation |
| 07 | Timeout boundaries | Test 0, 1, 60 and 61 minutes | 1/60 pass; 0/61 fail |
| 08 | Global step | Add `vars/validateCiConfig.groovy` | Pipeline can invoke helper |
| 09 | Maven build | Add `vars/runBuild.groovy` | Package created on agent |
| 10 | Gradle branch | Run approved Gradle fixture | Assemble executes only approved command |
| 11 | Tests | Add `vars/runTests.groovy` | JUnit reports appear |
| 12 | Failure path | Introduce failing fixture test | Job fails and retains diagnostic logs |
| 13 | Artifact path | Add `vars/publishArtifacts.groovy` | JAR archived and fingerprinted |
| 14 | Explicit stages | Refactor Jenkinsfile as chapter shows | Five stages visible in UI |
| 15 | Version pin | Tag library `v1.1.0` and reference it | Build log resolves expected commit |
| 16 | Canary rollout | Switch only one fixture consumer to new tag | Baseline and canary compared |
| 17 | Fault injection | Break one helper in a new test tag | Canary fails; other consumers unaffected |
| 18 | Rollback | Restore last-good tag in canary Jenkinsfile | Successful recovery with evidence |

## Executable pure-logic test matrix

Create `test/org/example/ci/CiConfigTest.groovy` with an available Groovy test runner:

```groovy
import org.example.ci.CiConfig

assert CiConfig.normalize([:]) == [
    environment:'dev', buildTool:'maven', timeoutMinutes:20
]
assert CiConfig.normalize([environment:'staging', buildTool:'gradle', timeoutMinutes:60]).buildTool == 'gradle'

[
    [environment:'production'],
    [buildTool:'maven; echo unsafe'],
    [timeoutMinutes:0],
    [timeoutMinutes:61],
    [timeoutMinutes:'abc'],
    [unexpected:'value']
].each { invalid ->
    boolean rejected = false
    try { CiConfig.normalize(invalid) }
    catch (IllegalArgumentException expected) { rejected = true }
    assert rejected : "Expected rejection for ${invalid.keySet()}"
}
println 'PASS: validator positive and negative tests'
```

Compile with `groovyc` or run with `groovy -cp src test/org/example/ci/CiConfigTest.groovy` on a machine with compatible Groovy installed. The Jenkins controller is not required for this pure logic test.

## Jenkins integration verification

1. Register `enterprise-ci` under Jenkins global libraries with least-privilege SCM read access and reviewed trust settings.
2. Create a protected tag for the new library version. Record `git rev-parse HEAD` and `git rev-parse v1.1.0^{commit}`; verify they match.
3. Update only the fixture Jenkinsfile to reference `@Library('enterprise-ci@v1.1.0') _`.
4. Execute Maven and Gradle fixture builds separately. Capture the stage graph, console output, JUnit results and archived artifacts.
5. Introduce one failing unit test and verify `Test` fails, `Archive` is skipped, and the console contains a useful root cause.
6. Revert the failing fixture, rerun and verify recovery.
7. For rollback, pin the fixture to the previous known-good protected tag and repeat the smoke test.

## Troubleshooting drills (12)

1. Misspell the global step and identify `No such DSL method`.
2. Change the `src/` package declaration and locate the class-resolution error.
3. Reference a nonexistent resource and identify the failing lookup.
4. Use a nonexistent library tag and inspect SCM retrieval failure.
5. Remove Maven from the agent image and diagnose toolchain absence.
6. Remove executable permission from `gradlew` and inspect the permission error.
7. Change the JUnit glob and confirm the missing report failure.
8. Pass a disallowed tool value and verify no shell command executes.
9. Set timeout to 61 and verify validation prevents execution.
10. Inject a failing unit test and verify that the pipeline does not archive successful artifacts.
11. Try to run the build on an agent without the required label and identify queue blockage; cancel safely.
12. Reproduce a breaking library change in a canary and perform tag-based rollback.

## Evidence record

```text
Date/time (UTC):
Jenkins core/plugins:
Library repository and immutable tag:
Library commit SHA:
Application fixture commit SHA:
Agent label/image:
Unit tests: PASS/FAIL
Maven fixture: PASS/FAIL
Gradle fixture: PASS/FAIL
Negative validation: PASS/FAIL
JUnit report paths:
Archived artifact names:
Canary failure and recovery:
Rollback version and elapsed time:
Open risks and reviewer:
```

## Acceptance gate

- [ ] All 18 exercises attempted with outcomes recorded.
- [ ] All 12 drills completed or marked blocked with rationale.
- [ ] Pure validation positive/negative tests pass.
- [ ] Maven and Gradle fixtures build on isolated agents.
- [ ] Tests and artifact handling fail closed.
- [ ] SCM tag and commit SHA match expected library revision.
- [ ] Canary rollback succeeds without modifying global defaults.
- [ ] Logs contain no secrets and no production deployments occur.

**Related chapter:** [Chapter 028](../028-reusable-jenkins-pipeline-functions-configuration-design-patterns.md).
