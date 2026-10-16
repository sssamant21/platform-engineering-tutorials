# Chapter 036 — Hands-on Lab: Maven, Gradle and npm Build Automation

**Scope:** Disposable Jenkins controller and isolated test agents; use fixture applications, not production credentials.

## Preparation

Create three small reviewed fixture repositories: Maven Java application with `mvnw`, Gradle Java application with `gradlew`, and npm application with `package-lock.json`, `test` and `build` scripts. Ensure Java fixtures contain actual unit tests and generate JUnit XML. Prepare agents labeled `isolated-jdk` and `isolated-node`. Record Git SHAs, tool versions, agent image IDs and plugin versions.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record Jenkins, plugins, agent images | Baseline |
| 02 | Maven toolchain | Run Java and Maven Wrapper version | Versions |
| 03 | Maven checkout | Checkout fixed fixture SHA | SHA |
| 04 | Maven verify | Run `./mvnw -B -ntp clean verify` | Successful build |
| 05 | Maven JUnit | Publish Surefire XML | Test counts |
| 06 | Maven archive | Archive JAR and SHA256 | Fingerprint |
| 07 | Gradle toolchain | Verify JDK and wrapper | Versions |
| 08 | Gradle locking | Review lock/verification configuration | Dependency policy |
| 09 | Gradle build | Run `./gradlew --no-daemon clean build` | Build logs |
| 10 | Gradle JUnit | Publish `build/test-results/test/*.xml` | Report |
| 11 | Gradle archive | Archive JAR and digest | Fingerprint |
| 12 | npm toolchain | Record Node and npm versions | Versions |
| 13 | npm reproducibility | Run `npm ci` from committed lockfile | Install log |
| 14 | npm test | Execute project-supported CI test script | Test result |
| 15 | npm build | Run `npm run build` | Dist output |
| 16 | npm archive | Archive dist and digest | Artifact record |
| 17 | Failure injection | Break one test in each fixture | Pipeline fails |
| 18 | Cache experiment | Compare cold and warm dependency restore | Timings |
| 19 | Resource experiment | Measure CPU/memory/disk during build | Metrics |
| 20 | Recovery | Restore pinned toolchain and rerun fixtures | Successful retest |

## 12 troubleshooting drills

1. Maven wrapper lacks execute permission.
2. Maven repository credential rejected.
3. Maven Surefire report missing.
4. Gradle distribution URL unavailable.
5. Gradle cache lock contention.
6. Gradle test fails under different JDK.
7. npm `package-lock.json` mismatch.
8. npm lifecycle script missing native dependency.
9. npm test runner stuck in watch mode.
10. Artifact glob matches no files.
11. Agent disk full or inode pressure.
12. Wrong runtime version causes build drift.

For each drill capture symptom, command, exit status, logs, root cause, correction and retest. Mark unsafe or unavailable drills blocked; never fabricate successful executions.

## Reusable evidence template

```text
UTC timestamp:
Fixture repository and source SHA:
Jenkins job/build:
Agent image and label:
Java/Node/Maven/Gradle/npm versions:
Dependency lock/checksum:
Build command and exit code:
Test report location and test count:
Artifact path and SHA256:
Queue/build durations:
Fault injection:
Root cause and recovery:
Reviewer:
```

## Acceptance checklist

- [ ] All 20 exercises attempted with evidence.
- [ ] All 12 troubleshooting drills completed or explicitly blocked.
- [ ] Maven and Gradle tests publish valid JUnit XML.
- [ ] npm uses lockfile and supported test/build scripts.
- [ ] Build outputs archived with digest and source SHA.
- [ ] Negative tests fail as expected.
- [ ] Cache, credentials and agent isolation reviewed.
- [ ] Toolchain rollback demonstrated on disposable agents.

**Related chapter:** [036 — Jenkins Build Automation with Maven, Gradle and npm](../036-jenkins-build-automation-maven-gradle-npm.md).
