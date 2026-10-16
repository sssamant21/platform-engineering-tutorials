# Chapter 036 — Jenkins Build Automation with Maven, Gradle and npm

**Part 08 — Build Automation, Testing and Artifacts**  
**Audience:** Jenkins administrators, DevOps, SRE, platform engineers  
**Prerequisites:** Chapters 001–035; disposable Jenkins, isolated Linux agents, fixture Git repositories and approved JDK, Node.js, Maven/Gradle versions.

## Learning objectives

Design reproducible Java and JavaScript builds; select Maven, Gradle and npm commands correctly; manage toolchains, wrappers, dependency caches and lockfiles; collect test reports and artifacts; troubleshoot common failures; and apply production reliability, security, capacity and rollback controls.

## 1. Build architecture

```text
Git provider → Jenkins Multibranch Pipeline → isolated agent
                                                ├─ JDK + Maven → JAR / test XML
                                                ├─ JDK + Gradle → JAR / test XML
                                                └─ Node.js + npm → dist / test XML
                                                          ↓
                                              archived outputs + fingerprints
                                                          ↓
                                          artifact repository / release gate
```

**Security boundary:** `pom.xml`, Gradle scripts, `package.json` lifecycle scripts and build plugins are executable code. Treat third-party dependencies and untrusted PRs as potentially hostile. Build on isolated agents with minimal network and no deployment credentials. Never run untrusted build steps on the controller.

## 2. Tool comparison

| Dimension | Maven | Gradle | npm |
|---|---|---|---|
| Typical manifest | `pom.xml` | `build.gradle(.kts)` | `package.json` |
| Lock / repeatability | Dependency versions, dependency management and plugin pinning | Dependency locking and verification metadata | `package-lock.json` + `npm ci` |
| Recommended CI entry | `./mvnw -B -ntp verify` | `./gradlew --no-daemon clean build` | `npm ci && npm test` |
| Common report path | `target/surefire-reports/*.xml` | `build/test-results/test/*.xml` | Test-runner dependent |
| Typical artifact | `target/*.jar` | `build/libs/*.jar` | `dist/**` |
| Cache | `~/.m2/repository` | Gradle user home | npm cache |

Maven Wrapper is optional; if absent, use a pinned, approved Maven installation and `mvn -B -ntp verify`. Gradle Wrapper should be committed with reviewed distribution URL/checksum and executable permissions. npm scripts depend on the project; a `build` script and JUnit reporter must exist before invoking them.

## 3. Version and dependency governance

1. Pin JDK/Node runtime versions in reviewed agent images or Jenkins tool configuration.
2. Commit `mvnw` / `gradlew` wrappers when used and review their distribution sources and integrity settings.
3. Pin Maven plugin versions and avoid floating `SNAPSHOT` dependencies in release builds.
4. Enable Gradle dependency locking/verification for critical workloads; pin plugin versions.
5. Commit npm lockfile and use `npm ci` rather than `npm install` in CI.
6. Keep dependency repositories authenticated with narrowly scoped credentials; never log tokens.
7. Generate provenance: source SHA, tool versions, dependency lock hash, build ID and artifact digest.

## 4. Maven fixture and Pipeline

Fixture `pom.xml` must include a real test dependency and test class; for a minimal standalone smoke lab, use an existing reviewed Maven fixture from your organization. The following Jenkinsfile assumes `mvnw` exists, `target/surefire-reports` is produced, and a JDK is available on `isolated-jdk` agents.

```groovy
pipeline {
    agent { label 'isolated-jdk' }
    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Toolchain') {
            steps { sh 'java -version; ./mvnw -version' }
        }
        stage('Verify') {
            steps { sh './mvnw -B -ntp clean verify' }
        }
        stage('Digest') {
            steps { sh 'sha256sum target/*.jar > artifact-sha256.txt' }
        }
    }
    post {
        always {
            junit testResults: 'target/surefire-reports/*.xml',
                  allowEmptyResults: false
            archiveArtifacts artifacts: 'target/*.jar,artifact-sha256.txt',
                             allowEmptyArchive: false,
                             fingerprint: true
        }
    }
}
```

**Important:** A strict `post { always { junit ... } }` gate may also fail a build that aborts before tests run; this is intentionally fail-closed but can obscure the primary checkout/toolchain failure. For production, report primary failures clearly and use stage-aware reporting without silently accepting missing tests. Likewise, digest/archive steps require an actual JAR; package-only projects need a different artifact contract.

## 5. Gradle fixture and Pipeline

```groovy
pipeline {
    agent { label 'isolated-jdk' }
    options { skipDefaultCheckout(true); timeout(time: 30, unit: 'MINUTES') }
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Toolchain') { steps { sh 'java -version; ./gradlew --version' } }
        stage('Build') {
            steps { sh './gradlew --no-daemon clean build' }
        }
        stage('Digest') {
            steps { sh 'sha256sum build/libs/*.jar > artifact-sha256.txt' }
        }
    }
    post {
        always {
            junit testResults: 'build/test-results/test/*.xml',
                  allowEmptyResults: false
            archiveArtifacts artifacts: 'build/libs/*.jar,artifact-sha256.txt',
                             allowEmptyArchive: false, fingerprint: true
        }
    }
}
```

Use a dedicated Gradle user home per isolated agent or a controlled shared cache. Never assume build cache contents are trusted across privilege boundaries.

## 6. npm fixture and Pipeline

A JavaScript fixture must contain `package.json`, `package-lock.json`, and meaningful `test`/`build` scripts. Configure a JUnit-compatible test reporter if publishing XML.

```groovy
pipeline {
    agent { label 'isolated-node' }
    options { skipDefaultCheckout(true); timeout(time: 25, unit: 'MINUTES') }
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Toolchain') { steps { sh 'node --version; npm --version' } }
        stage('Dependencies') { steps { sh 'npm ci --no-audit --no-fund' } }
        stage('Test') { steps { sh 'npm test -- --ci' } }
        stage('Build') { steps { sh 'npm run build' } }
        stage('Digest') {
            steps { sh "find dist -type f -print0 | sort -z | xargs -0 -r sha256sum > artifact-sha256.txt" }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'dist/**,artifact-sha256.txt',
                             allowEmptyArchive: false, fingerprint: true
        }
    }
}
```

The `--ci` argument is **test-runner specific**; remove it if unsupported. `--no-audit` only disables npm's automatic audit during install; run a separately governed dependency vulnerability scan. If JUnit XML is configured, publish it with `junit` and `allowEmptyResults: false`. The digest command uses GNU tools available on the example Linux agent; adjust for other operating systems.

## 7. Multi-tool orchestration

For a monorepo, keep independent toolchains and stage-specific working directories:

```groovy
stage('Backend') {
    steps {
        dir('backend') { sh './mvnw -B -ntp verify' }
    }
}
stage('Frontend') {
    steps {
        dir('frontend') {
            sh 'npm ci --no-audit --no-fund'
            sh 'npm test'
            sh 'npm run build'
        }
    }
}
```

Use separate isolated agents or `parallel` stages when workload and resource limits justify it. Avoid sharing writable caches across concurrent untrusted builds. Build/test output paths must be unique and verified.

## 8. Dependency cache strategy

| Cache | Benefits | Failure modes | Controls |
|---|---|---|---|
| Maven local repo | Faster repeated downloads | Corrupt/inconsistent artifacts | Repository checksums, isolation, cache eviction |
| Gradle cache | Faster dependency resolution | Cache lock, poisoned content | Dependency verification, separate user homes |
| npm cache | Faster tarball retrieval | Stale/corrupt entries | Lockfile integrity, `npm cache verify` |
| Remote build cache | Cross-agent reuse | Cache poisoning and permission bleed | Authenticated cache, key partitioning |

Caches improve speed but are not release artifacts. Keep release outputs immutable, fingerprinted and retained per policy.

## 9. Build SLIs and capacity

| SLI | Measurement | Lab target |
|---|---|---|
| Valid build success | Passed valid fixtures / attempted | 100% in controlled lab |
| Test report coverage | Builds with expected test XML | 100% for Java fixtures |
| Artifact provenance | SHA and digest captured | 100% successful packages |
| Dependency restore latency | Download time per tool | Baseline and compare |
| Queue time | Scheduled → agent start | Recorded separately |
| Build duration | Checkout → archive | Record p50/p95 across repeated runs |

Monitor CPU/memory pressure, filesystem usage/inodes, network dependency failures, cache hit rate, executor utilization and toolchain drift. Lab targets are not production SLO promises.

## 10. Troubleshooting matrix

| Symptom | Root cause checks | Remediation |
|---|---|---|
| `mvnw: Permission denied` | Executable bit | Commit `chmod +x mvnw` |
| Maven dependency 401 | Registry token scope | Rotate scoped credential |
| Maven tests not found | Surefire config/glob | Correct test/report contract |
| Gradle wrapper download fails | Proxy/TLS/distribution URL | Fix trusted network path |
| Gradle daemon OOM | JVM heap/agent limits | Size memory; use no-daemon |
| Gradle cache lock | Concurrent shared cache | Isolate Gradle user homes |
| `npm ci` fails lock mismatch | Lockfile differs from manifest | Regenerate/review lockfile |
| npm install script fails | Native deps / toolchain | Pin image and dependencies |
| npm test hangs | Watch mode / runner flags | Use noninteractive CI mode |
| `dist` missing | No build script or wrong path | Fix artifact contract |
| JUnit empty | Test failure before report / wrong glob | Investigate; do not mark green |
| Artifact digest mismatch | Different toolchain/deps/input | Compare provenance |
| Agent disk full | Cache/workspace growth | Safe cleanup and quotas |
| Build unexpectedly slow | Registry latency, cache, queue | Baseline stage timings |
| Dependency compromise | Untrusted registry/script | Quarantine and review SBOM |
| Secret printed in logs | Unsafe interpolation/script | Revoke/rotate, investigate |

## 11. Production runbooks

### A. Onboard a build project
1. Inventory language, toolchain, wrapper, lockfiles and test/report contract.
2. Select a pinned isolated agent image; validate filesystem, memory and network.
3. Configure read-only SCM access and scoped dependency registry credentials.
4. Run a clean build, record SHA and tool versions, publish test reports and digests.
5. Exercise negative tests and validate fail-closed behavior.
6. Review cache isolation, retention and rollback.

### B. Dependency registry outage
1. Distinguish DNS/TLS, registry 401/403/429/5xx and agent network failures.
2. Preserve logs and failing dependency coordinates without exposing secrets.
3. Stop unbounded retries and avoid bypassing TLS/integrity validation.
4. Restore approved mirror/registry access; rebuild pinned revision.
5. Verify artifact digest and document incident.

### C. Agent resource pressure
1. Capture CPU/memory, `df -h`, `df -i`, executor and queue metrics.
2. Stop scheduling on unhealthy agent and preserve evidence.
3. Identify cache/workspace consumers; clean only disposable, approved paths.
4. Resize or replace isolated agent, rerun known-good fixture.
5. Record preventive quotas and alerts.

### D. Bad toolchain upgrade
1. Compare old/new JDK, Node, Maven/Gradle and agent image versions.
2. Freeze promotion; restore previously reviewed image/wrapper/lockfile.
3. Re-run tests from identical source SHA and verify reports/digests.
4. Document compatibility findings and release a reviewed correction.
5. Avoid overwriting previously published immutable artifacts.

## 12. Acceptance criteria

- [ ] Maven, Gradle and npm fixtures build with pinned toolchains.
- [ ] Correct test commands and report paths documented.
- [ ] npm lockfile and Gradle/Maven dependency policies reviewed.
- [ ] Source SHA, tool versions and artifact digests captured.
- [ ] Credential, cache and agent isolation verified.
- [ ] Negative failures and runbooks exercised.
- [ ] Build duration, queue delay and disk usage recorded.
- [ ] Evidence and reviewer approval preserved.

**Companion:** [Chapter 036 hands-on lab](labs/036-jenkins-build-automation-maven-gradle-npm-check.md).  
**Next:** Chapter 037 — Jenkins Automated Testing, JUnit Reporting and Quality Gates.
