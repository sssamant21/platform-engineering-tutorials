# Chapter 039 — Jenkins Artifact Management, Versioning and Repository Integration

**Part 08 — Build Automation, Testing and Artifacts**  
**Audience:** Jenkins SREs, DevOps engineers, platform teams and release engineers  
**Prerequisites:** Chapters 036–038; disposable Jenkins and Linux agent, fixture Maven/npm build, nonproduction artifact repository, read/write service identities.

## 1. Learning objectives

Understand Jenkins archived artifacts versus external artifact repositories; design immutable versioning and retention; publish Maven packages, generic files and npm packages to approved repositories; verify checksums and provenance; apply scoped credentials, audit and promotion controls; investigate repository incidents; and demonstrate rollback without mutating immutable releases.

## 2. Reference architecture

```text
Git protected commit → Jenkins isolated build agent
  ├─ compile/test + JUnit/quality gates
  ├─ package + version metadata
  ├─ SHA-256 manifest + provenance
  └─ short-lived publish credential
               ↓ HTTPS
        Artifact repository
       ├─ snapshots/dev
       ├─ immutable release
       └─ retention / access / audit
               ↓
    deployment consumes exact version + digest
```

**Jenkins `archiveArtifacts` is not a substitute for a dedicated enterprise package registry.** Jenkins archives are associated with build history and may be pruned; registries support controlled package coordinates, repository ACLs, immutable releases and distribution.

## 3. Artifact classes and repository options

| Artifact | Typical format | Common repository |
|---|---|---|
| Maven Java package | JAR, POM | Nexus, Artifactory, Maven-compatible repo |
| npm package | `.tgz` package | Private npm registry |
| Generic binary | ZIP, tar.gz, JSON | Generic artifact repository or object storage |
| Container image | OCI image + digest | Container registry (Part 09) |
| Helm chart | OCI chart / chart archive | OCI registry or chart repository |
| Test reports | JUnit XML, coverage | Jenkins build evidence storage |

Examples below use a Maven-compatible repository and generic HTTPS endpoint. Product-specific APIs, endpoints and permissions differ: confirm repository documentation before adapting.

## 4. Versioning and immutable release policy

- Use explicit semantic versions where appropriate, e.g. `1.4.2`; use a non-release suffix such as `1.4.3-SNAPSHOT` only in an approved snapshot repository.
- Do not overwrite an immutable release version or reuse its coordinates with different bytes.
- Record Git SHA, Jenkins build URL/number, build toolchain, dependency lock checksum and SHA-256.
- Use immutable digest for downstream deployment, not only `latest` or mutable tags.
- Promotion should **copy or reference existing validated bytes**, not rebuild with changed inputs.
- Retention must preserve artifacts required for rollback, audit and regulatory obligations.
- Sign release artifacts when supported and required; signing does not replace secure build provenance.

## 5. Maven publication: settings and Pipeline

In a trusted fixture Maven project, configure distribution repositories in `pom.xml`:

```xml
<distributionManagement>
  <snapshotRepository>
    <id>snapshots</id>
    <url>https://repo.example.test/repository/maven-snapshots/</url>
  </snapshotRepository>
  <repository>
    <id>releases</id>
    <url>https://repo.example.test/repository/maven-releases/</url>
  </repository>
</distributionManagement>
```

Use the actual nonproduction repository URL. Supply authentication via a Jenkins-managed Maven `settings.xml` or temporary settings file created with credential bindings and strict permissions; never commit tokens or echo secrets.

Illustrative Pipeline using Jenkins Config File Provider (only if installed and configured):

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
        stage('Verify') { steps { sh './mvnw -B -ntp clean verify' } }
        stage('Publish') {
            when { branch 'main' }
            steps {
                configFileProvider([configFile(fileId: 'maven-publish-settings',
                                               variable: 'MAVEN_SETTINGS')]) {
                    sh './mvnw -B -ntp -s "$MAVEN_SETTINGS" deploy -DskipTests'
                }
            }
        }
    }
}
```

**Caveat:** This example reruns Maven lifecycle phases during `deploy` and uses `-DskipTests` only because `verify` has already run on the same checked-out revision. In stricter production pipelines, bind the exact verified artifact and promote that immutable package rather than allowing a second independent build. Protect the `main` job with SCM authorization and a trusted agent; `when { branch 'main' }` alone is not a security boundary. Use snapshot version for this exercise unless release approval has been implemented.

## 6. Generic artifact publication with checksums

For a nonproduction generic HTTP endpoint supporting authenticated PUT, use a Jenkins secret-text credential. **Do not copy this example into an untrusted PR job.**

```groovy
stage('Publish generic artifact') {
    when { branch 'main' }
    steps {
        withCredentials([string(credentialsId: 'artifact-write-token',
                                variable: 'REPO_TOKEN')]) {
            sh '''#!/bin/sh
                set -eu
                test -f dist/app.tar.gz
                sha256sum dist/app.tar.gz > dist/app.tar.gz.sha256
                curl --fail-with-body --show-error --silent \
                     --retry 2 --retry-delay 2 \
                     --header "Authorization: Bearer $REPO_TOKEN" \
                     --upload-file dist/app.tar.gz \
                     "https://repo.example.test/generic/app/1.0.0/app.tar.gz"
            '''
        }
    }
}
```

`--fail-with-body` requires a sufficiently recent curl. Use TLS verification, least privilege and redacted logs; some repositories require different API methods/authentication. Avoid unsafe redirects and never embed credentials in URL query parameters.

## 7. npm package publication

Use `npm ci` with committed lockfile, `npm test`, `npm pack --dry-run`, and publish only a reviewed package/version to a private registry. Configure `.npmrc` via ephemeral agent credential injection, not repository source. Verify package scope and registry destination before publish. npm publish behavior, provenance and OTP/MFA requirements depend on registry and account configuration; use supported noninteractive service credentials and do not weaken organization policy.

```sh
npm ci
npm test
npm pack --dry-run
npm pack
```

The `npm pack` command creates a tarball; use `sha256sum` to record digest. For actual publication, configure an approved registry and run `npm publish --registry <approved-url>` under a controlled release job with explicit approval. Do not use public npm for disposable exercises.

## 8. Jenkins archive and external registry evidence

```groovy
post {
    success {
        archiveArtifacts artifacts: 'dist/*.tar.gz,dist/*.sha256',
                         fingerprint: true,
                         allowEmptyArchive: false
    }
}
```

Jenkins fingerprinting aids traceability, but cryptographic integrity verification still requires independently computed digests/signatures. A release record should include repository coordinate, digest, source SHA, tests, approvals and publisher identity.

## 9. Promotion, retention and rollback

| Lifecycle | Operation | Control |
|---|---|---|
| Build | Produce candidate bytes | Deterministic inputs |
| Verify | Test and scan candidate | Required gates |
| Stage | Publish to nonproduction repo | Scoped write |
| Promote | Copy same bytes to release repo | Approval and digest comparison |
| Consume | Download pinned version | Digest/signature verification |
| Retain | Enforce lifecycle policy | Audit and rollback windows |
| Rollback | Redeploy previous known-good digest | No overwrite |

A failed release should be rolled back by selecting a previous immutable artifact. Do not delete or rewrite release history to conceal failure.

## 10. Observability and capacity

| Signal | Why it matters |
|---|---|
| Publish HTTP status and latency | Registry availability |
| Checksum mismatch | Integrity incident |
| 401/403 publish failures | Credential/permission drift |
| 409 conflicts | Immutable version collision |
| Repository disk/inode usage | Capacity exhaustion |
| Download 404 | Missing version or retention error |
| Retention/prune activity | Rollback eligibility |
| Storage growth and egress | FinOps |
| Publish retries | Potential duplicate uploads |
| Artifact-to-commit traceability | Audit and incident reconstruction |

Monitor registry quotas and object storage costs. Calculate retention from business RPO/RTO and audit obligations rather than a blanket short TTL.

## 11. Troubleshooting matrix

| Symptom | Diagnostic | Recovery |
|---|---|---|
| Maven 401 | Settings server ID/credential | Correct scoped identity |
| Maven 403 | Repository write ACL | Grant approved permission |
| Maven 409 | Existing immutable version | Increment version; do not overwrite |
| Snapshot published as release | POM version and repo mapping | Fix coordinates |
| npm publish 403 | Registry, scope, token | Correct private registry access |
| npm package already exists | Version conflict | Publish new version |
| Generic upload 404 | Endpoint/API mismatch | Use documented endpoint |
| HTTP 429/503 | Registry rate/availability | Bounded retry and alert |
| Digest mismatch | Download/upload integrity | Quarantine and investigate |
| Artifact missing in Jenkins | Archive glob | Fix path |
| Registry disk full | Capacity/retention | Expand safely, review cleanup |
| Credentials leaked | Console, process, config | Revoke/rotate, investigate |
| Wrong artifact deployed | Mutable tag/version | Pin verified digest |
| Rollback artifact pruned | Retention gap | Restore backup, revise policy |
| TLS failure | CA/trust chain | Repair CA; never disable TLS |

## 12. Production runbooks

### A. Repository onboarding
1. Classify artifact, coordinate, owners, retention and compliance requirements.
2. Configure snapshot and immutable release repositories with scoped identities.
3. Build and test fixture; generate checksum and provenance.
4. Publish to nonproduction endpoint; download and verify checksum.
5. Exercise collision, 401 and rollback scenarios.
6. Approve production promotion workflow.

### B. Publish outage
1. Record repository endpoint, HTTP response, source SHA and version.
2. Check DNS/TLS, registry health, storage quota and permissions.
3. Stop uncontrolled retries and prevent duplicate versions.
4. Restore service and publish approved version.
5. Verify downloaded bytes and digest; close incident with timeline.

### C. Integrity mismatch
1. Stop promotion and quarantine suspect package.
2. Capture expected digest, actual digest, source SHA and build evidence.
3. Audit repository writes, cache, storage and credentials.
4. Rebuild only through approved recovery procedure; assign new immutable coordinate if bytes differ.
5. Notify owners and document impact.

### D. Credential compromise
1. Revoke publish token and pause release jobs.
2. Audit package uploads and repository access.
3. Rotate to a narrower identity; verify no logs/artifacts contain secret.
4. Validate artifact integrity and provenance.
5. Resume after security approval.

### E. Rollback release
1. Identify previous approved version and digest.
2. Verify package is available and integrity matches.
3. Deploy pinned previous version using normal change controls.
4. Confirm health, SLOs and rollback evidence.
5. Preserve failed release for audit and RCA.

## 13. Acceptance criteria

- [ ] Artifact coordinates and immutability policy documented.
- [ ] Maven/npm/generic publication flows demonstrated where supported.
- [ ] Test results, source SHA and artifact SHA-256 captured.
- [ ] Registry download verifies expected digest.
- [ ] Publishing restricted to trusted identities/agents.
- [ ] 401/403, collision and integrity failure handled safely.
- [ ] Retention and rollback rehearsed.
- [ ] Runbooks and reviewer evidence complete.

**Companion:** [Chapter 039 hands-on lab](labs/039-jenkins-artifact-management-versioning-repository-integration-check.md).  
**Next:** Chapter 040 — Build, Testing and Artifact Reliability Acceptance Capstone.
