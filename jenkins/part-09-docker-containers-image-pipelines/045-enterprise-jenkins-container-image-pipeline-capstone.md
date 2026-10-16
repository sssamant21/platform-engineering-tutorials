# Chapter 045 — Enterprise Jenkins Container Image Pipeline Capstone

**Part 09 — Docker, Containers and Image Pipelines (final capstone)**  
**Audience:** Jenkins SRE/DevOps, platform engineering, application security and release teams  
**Prerequisites:** Chapters 041–044; disposable Jenkins and isolated builders; nonproduction OCI registry; approved scanner/SBOM/signer identities.

## Mission

Build an end-to-end, policy-controlled container supply chain from reviewed Git SHA to immutable OCI digest, including tests, optimized Dockerfile, nonroot smoke test, vulnerability scanning, SBOM, trusted registry publication, digest signing/verification, controlled promotion, retention and rollback. Do **not** use production credentials or deploy to production during labs.

## 1. Target architecture

```text
Protected Git SHA / reviewed Dockerfile
         ↓
Jenkins isolated CI builder (no publish credentials)
   ├─ dependency lock and unit tests
   ├─ multi-stage BuildKit image
   ├─ nonroot, read-only HTTP smoke
   ├─ vulnerability/secret checks
   ├─ SBOM (CycloneDX/SPDX)
   └─ provenance/evidence
         ↓ trusted release authorization
Jenkins release agent (scoped registry identity)
   ├─ publish unique candidate tag
   ├─ obtain authoritative registry digest
   ├─ sign digest and verify trusted issuer
   ├─ promote same manifest/layers
   └─ record release and rollback digest
         ↓
Deployment policy consumes repository@sha256:digest
```

A tag is a mutable reference; a local image ID is not the registry manifest digest. Promotion should copy validated bytes without rebuilding. If OCI media types or manifest serialization change during cross-registry copy, reconcile source/destination digests and provenance before approval.

## 2. Ownership and trust boundaries

| Boundary | Owner | Required control |
|---|---|---|
| Source repository | Application team | Branch protection, review |
| Jenkinsfile/shared libraries | Platform CI | Reviewed pipeline changes |
| CI builder | SRE/platform | Ephemeral isolation, no publish secrets |
| Registry publisher | Release engineering | Least-privilege short-lived identity |
| Scanner and policy | AppSec | Versioned blocking rules, exceptions |
| Signing identity | Security/platform | Trusted OIDC or managed KMS |
| Promotion | Release manager | Approval and immutable version |
| Rollback | On-call SRE | Prior signed digest and runbook |

Rootful Docker socket access is effectively host-root-equivalent. Do not expose it to untrusted pull requests or mount it into arbitrary Jenkins containers. Use approved isolated builders or rootless/managed build services.

## 3. Fixture and versioning

Use the synthetic Node HTTP fixture from Chapter 042 with committed `package-lock.json`, a multi-stage Dockerfile and `/healthz`. Record full Git SHA, Dockerfile hash, Node/npm versions, base image digest and build agent identity.

Candidate tag: `git-<short-sha>-<unique-run>`. Release tag: reviewed semantic version (e.g. `1.0.0`) protected by registry immutability policy. Production deployment uses `registry/repo@sha256:<digest>` rather than a tag.

## 4. Build and test commands

```sh
set -eu
npm ci
npm test
docker build --pull -f Dockerfile -t ch045:candidate .
docker image inspect ch045:candidate --format '{{.Id}} {{.Size}} {{.Config.User}}'
docker run -d --name ch045-smoke --read-only --cap-drop=ALL \
  --security-opt no-new-privileges \
  -p 127.0.0.1:18085:8080 ch045:candidate
curl --fail --silent --show-error --retry 10 --retry-delay 1 \
  http://127.0.0.1:18085/healthz
docker rm -f ch045-smoke
```

Use a free loopback port and dedicated disposable builder; clean up any container remaining after a failed command. Confirm the fixture does not require a writable root filesystem.

## 5. Security and evidence gates

```sh
set -eu
trivy image --scanners vuln --severity HIGH,CRITICAL \
  --format json --output trivy-vuln.json ch045:candidate
syft ch045:candidate -o cyclonedx-json=sbom.cdx.json
syft ch045:candidate -o spdx-json=sbom.spdx.json
test -s trivy-vuln.json
test -s sbom.cdx.json
test -s sbom.spdx.json
trivy image --scanners vuln --severity HIGH,CRITICAL \
  --exit-code 1 ch045:candidate
```

These commands require approved pinned Trivy and Syft versions and an available vulnerability database. A scan exit code of zero is not proof of zero vulnerabilities. Scan policy must define severity, exploitability, fixes, database freshness and scoped time-limited exceptions. Missing scan results or SBOMs block release.

## 6. Jenkins CI Pipeline

```groovy
pipeline {
    agent { label 'isolated-docker-builder' }
    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git rev-parse HEAD > source-sha.txt'
            }
        }
        stage('Unit tests') {
            steps { sh 'npm ci && npm test' }
        }
        stage('Build') {
            steps {
                sh 'docker build --pull -f Dockerfile -t ch045:candidate .'
                sh "docker image inspect ch045:candidate --format '{{.Id}} {{.Size}} {{.Config.User}}' > image-evidence.txt"
            }
        }
        stage('Smoke') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    name="ch045-$BUILD_NUMBER"
                    docker run -d --name "$name" --read-only --cap-drop=ALL \
                      --security-opt no-new-privileges \
                      -p 127.0.0.1::8080 ch045:candidate
                    port=$(docker port "$name" 8080/tcp | sed 's/.*://')
                    curl --fail --retry 10 --retry-delay 1 \
                      "http://127.0.0.1:$port/healthz"
                '''
            }
        }
        stage('Security evidence') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    trivy image --scanners vuln --severity HIGH,CRITICAL \
                      --format json --output trivy-vuln.json ch045:candidate
                    syft ch045:candidate -o cyclonedx-json=sbom.cdx.json
                    syft ch045:candidate -o spdx-json=sbom.spdx.json
                    test -s sbom.cdx.json
                    test -s sbom.spdx.json
                    trivy image --scanners vuln --severity HIGH,CRITICAL \
                      --exit-code 1 ch045:candidate
                '''
            }
        }
    }
    post {
        always {
            sh 'docker rm -f "ch045-$BUILD_NUMBER" >/dev/null 2>&1 || true'
            archiveArtifacts artifacts: 'source-sha.txt,image-evidence.txt,trivy-vuln.json,sbom.*.json',
                             allowEmptyArchive: true,
                             fingerprint: true
        }
    }
}
```

This **CI-only** example does not publish or sign. It assumes a controlled Node/Docker/Trivy/Syft agent and Jenkins workspace isolation. A production implementation must add JUnit-format test reporting, schema validation, tool/database version evidence, policy-as-code and a secure handoff to a separate trusted release workflow. A branch-name condition is not authorization.

## 7. Trusted release and digest signing

1. Verify source SHA, tests, scanner result, SBOM and approval.
2. Use a **separate trusted release job** with scoped registry publisher identity.
3. Publish to a unique candidate tag in the private registry.
4. Query the authoritative registry manifest digest using a provider CLI or `docker buildx imagetools inspect`.
5. Sign `repository@sha256:<digest>` using approved Cosign identity (OIDC or KMS).
6. Verify signature against **expected certificate issuer and identity**; do not accept any signer.
7. Promote same bytes to immutable release namespace/tag; verify source/destination manifest equivalence.
8. Record deployment digest and previous known-good rollback digest.
9. Deploy only through approved release/change workflow.

Example (requires real digest, registry authentication and configured signing identity):

```sh
IMAGE="registry.example.test/training/ch045@sha256:REPLACE_WITH_REAL_DIGEST"
cosign sign --yes "$IMAGE"
cosign verify \
  --certificate-identity 'https://ci.example.test/trusted-release' \
  --certificate-oidc-issuer 'https://issuer.example.test' \
  "$IMAGE"
```

Never invent digest, identity or issuer. Some Cosign versions and registries have different attestation/referrer behavior; validate the exact supported workflow.

## 8. Reliability and operational SLOs

| SLI | Measurement | Capstone expectation |
|---|---|---|
| Git provenance | Image linked to reviewed SHA | 100% |
| Test gate | Failing test blocks promotion | 100% |
| Vulnerability gate | Unapproved blocking CVEs rejected | 100% |
| SBOM completeness | Valid nonempty evidence | 100% |
| Image integrity | Registry digest recorded/verified | 100% |
| Signing policy | Trusted issuer/identity verified | 100% |
| Tag immutability | Release collision rejected | 100% |
| Rollback readiness | Prior approved digest available | 100% |
| Queue/build duration | p50/p95 over multiple runs | Establish baseline |
| Registry availability | Push/pull success and latency | Establish baseline |
| Recovery time | Fault detection to verified recovery | Record measured time |

These are **lab acceptance targets**, not claimed production measurements.

## 9. Failure injection campaign

| Failure | Expected behavior | Recovery |
|---|---|---|
| npm lockfile mismatch | Test/build blocked | Review and restore lock |
| Broken Dockerfile COPY | Build fails | Fix path and retest |
| Untrusted Docker socket access | Access denied | Correct isolation |
| Container exits | Smoke fails | Inspect logs/entrypoint |
| Nonroot write failure | Runtime fails safely | Provide explicit writable mount |
| Vulnerability scan HIGH/CRITICAL | Release blocked | Patch or approved exception |
| Scanner database outage | Release blocked | Restore trusted DB |
| SBOM missing | Release blocked | Repair generator |
| Registry 401/403 | Publish denied | Repair scoped identity |
| Registry 429/503 | Publish delayed/fails | Bounded retry, alert |
| Tag overwrite attempted | Rejected | New immutable version |
| Registry digest mismatch | Promotion quarantined | Investigate manifests |
| Cosign issuer mismatch | Verification rejected | Repair trusted identity |
| Signature/referrer pruned | Release blocked | Restore evidence and retention |
| Previous digest missing | Rollback readiness fails | Restore backup, fix lifecycle |

## 10. Troubleshooting decision tree

```text
Release blocked?
 ├─ No agent → capacity/labels/isolation
 ├─ Checkout/test → SHA, lockfile, test reports
 ├─ Build → Dockerfile, BuildKit, disk, base registry
 ├─ Smoke → process, port, read-only FS, nonroot
 ├─ Scan/SBOM → tool, DB, policy, evidence
 ├─ Publish → credentials, registry, quota, TLS
 ├─ Digest → OCI index/manifest, tag mutation
 ├─ Signature → issuer, identity, registry referrers
 └─ Rollback → retention, replication, previous digest
```

Do not bypass TLS, scanner gates, or signer identity verification to restore a green pipeline.

## 11. Production runbooks

### A. Pipeline onboarding
1. Review source, Dockerfile, dependencies and trust boundaries.
2. Configure isolated CI and separate trusted release agents.
3. Build/test fixture, verify nonroot smoke and security gates.
4. Publish to nonproduction registry and verify digest.
5. Sign/verify with trusted identity, then promote.
6. Exercise rollback and capture owner approval.

### B. Builder or registry outage
1. Record Jenkins build, source SHA, agent, registry endpoint and error.
2. Identify builder, network, quota, auth or upstream outage.
3. Stop uncontrolled retries; preserve logs and evidence.
4. Restore service and rerun pinned revision.
5. Verify scan, digest and signature before release.

### C. Critical vulnerability
1. Identify affected deployed digests from SBOM/registry inventory.
2. Triage exposure and exploitability with AppSec.
3. Block new promotion, patch dependency/base image.
4. Rebuild on trusted builder, rescan and re-sign new digest.
5. Deploy approved update and document response.

### D. Signature/provenance failure
1. Halt release and quarantine suspect digest.
2. Capture verifier output, issuer/identity, manifest and provenance.
3. Audit registry writes, CI workflow and signing credentials.
4. Reissue only after validated source/build review.
5. Retest trusted verification and document incident.

### E. Rollback
1. Identify prior approved signed digest and its manifest.
2. Verify registry availability, signature and policy.
3. Deploy previous digest through approved rollout.
4. Validate application health and SLOs.
5. Preserve failed image, open RCA and review retention.

## 12. 100-point acceptance assessment

| Category | Points |
|---|---:|
| Architecture, ownership and trust boundaries | 10 |
| Reproducible multi-stage build and testing | 15 |
| Nonroot runtime and smoke security | 10 |
| Scanning and SBOM quality | 15 |
| Registry tagging, digest and immutability | 15 |
| Signing, identity and provenance | 15 |
| Observability and capacity | 5 |
| Failure injection and incident response | 10 |
| Rollback and evidence handover | 5 |
| **Total** | **100** |

Suggested pass: **85/100**, plus mandatory gates: no secret exposure, tests pass, scan/SBOM policy enforced, digest verified, trusted signing identity verified for release, and rollback image available.

## 13. Final evidence package

Architecture/RACI; Git SHA and Dockerfile/base digest; Jenkins build and test logs; smoke result; Trivy/Syft versions and reports; registry manifest digest; Cosign signer identity/verification; promotion manifest comparison; rollback digest; 15 failure drills; 100-point score and reviewer approval.

**Companion:** [Chapter 045 capstone lab](labs/045-enterprise-jenkins-container-image-pipeline-capstone-check.md).  
**Part 09 complete:** Chapters 041–045.  
**Next:** Chapter 046 — Jenkins on Kubernetes: Architecture, Controllers and Dynamic Agents, beginning Part 10.
