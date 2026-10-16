# Chapter 045 — Enterprise Jenkins Container Image Pipeline Capstone Lab

**Environment:** Disposable Jenkins, isolated Docker/BuildKit agent, synthetic Node fixture from Chapter 042, private nonproduction registry, approved Trivy/Syft/Cosign. Do not use production credentials.

## 20 capstone exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Architecture | Diagram SCM → CI → registry → release | Diagram |
| 02 | Trust boundaries | Separate CI and release identities | RACI |
| 03 | Source provenance | Pin full Git SHA | SHA |
| 04 | Dependency lock | Verify `npm ci` | Lockfile hash |
| 05 | Unit tests | Run `npm test` | Result |
| 06 | Multi-stage image | Build optimized Dockerfile | Image ID |
| 07 | Base image | Record approved digest | Base digest |
| 08 | Nonroot | Inspect runtime user | UID |
| 09 | Secure smoke | Run read-only, cap-drop and health | HTTP 200 |
| 10 | Vulnerability scan | Generate Trivy report | JSON |
| 11 | Enforce policy | Reject unapproved findings | Exit code |
| 12 | SBOM | Generate CycloneDX and SPDX | JSON |
| 13 | Registry publish | Push candidate with scoped identity | Tag |
| 14 | Manifest digest | Query authoritative registry | SHA256 |
| 15 | Signing | Sign pinned digest with trusted identity | Signature |
| 16 | Verification | Enforce issuer and identity | Verification |
| 17 | Promotion | Copy exact validated manifest | Digest comparison |
| 18 | Immutability | Attempt duplicate release tag | Rejected |
| 19 | Rollback | Verify previous signed digest | Recovery |
| 20 | Acceptance | Score and sign off | Report |

## 15 troubleshooting drills

1. Missing/mismatched npm lockfile.
2. Dockerfile COPY failure.
3. Untrusted job requests Docker daemon.
4. Container process exits.
5. Nonroot runtime cannot write.
6. Smoke health endpoint fails.
7. HIGH/CRITICAL scan finding blocks.
8. Scanner DB unavailable.
9. SBOM missing or malformed.
10. Registry publish 401/403.
11. Registry throttling 429/503.
12. Immutable release collision.
13. Registry manifest digest mismatch.
14. Signature issuer/identity mismatch.
15. Rollback image or signature missing.

Record UTC time, build, Git SHA, error, logs, root cause, remediation and verified recovery for each. Mark blocked exercises explicitly when test identity/registry capability is unavailable; never invent signing or deployment evidence.

## Reusable test fixture

Use the Chapter 042 Node.js HTTP fixture and Dockerfile. Verify:

```sh
set -eu
npm ci
npm test
docker build --pull -t ch045:candidate .
docker run -d --name ch045-test --read-only --cap-drop=ALL \
  -p 127.0.0.1:18085:8080 ch045:candidate
curl --fail --retry 10 --retry-delay 1 http://127.0.0.1:18085/healthz
docker rm -f ch045-test
trivy image --scanners vuln --severity HIGH,CRITICAL \
  --format json --output trivy-vuln.json ch045:candidate
syft ch045:candidate -o cyclonedx-json=sbom.cdx.json
syft ch045:candidate -o spdx-json=sbom.spdx.json
trivy image --scanners vuln --severity HIGH,CRITICAL \
  --exit-code 1 ch045:candidate
```

Trivy and Syft must be installed and approved. The final command deliberately fails on blocking findings. Registry publishing, digest signing and promotion require separate trusted credentials and verified identity.

## Evidence template

```text
UTC timestamp:
Jenkins build / agent:
Full Git SHA:
Dockerfile and base digest:
Node/npm/Docker/BuildKit versions:
Unit test and smoke result:
Runtime user/security flags:
Trivy version/DB timestamp/report:
Syft version/SBOM schemas:
Candidate registry tag:
Authoritative manifest digest:
Cosign signer issuer/identity:
Promotion source/destination digest:
Immutable collision result:
Failure injection and recovery:
Previous signed rollback digest:
Score / reviewer / outstanding risks:
```

## 100-point scorecard

| Category | Max |
|---|---:|
| Architecture/trust | 10 |
| Reproducible build/tests | 15 |
| Runtime security/smoke | 10 |
| Scanning/SBOM | 15 |
| Registry/digest/immutability | 15 |
| Signing/provenance | 15 |
| Observability | 5 |
| Failure injection | 10 |
| Rollback/handover | 5 |
| **Total** | **100** |

## Acceptance checklist

- [ ] All 20 exercises attempted and documented.
- [ ] All 15 drills completed or explicitly blocked.
- [ ] Tests and secure runtime smoke passed.
- [ ] Vulnerability gate and SBOM validated.
- [ ] Registry manifest digest captured and verified.
- [ ] Trusted signature identity enforced for release.
- [ ] Promotion did not rebuild the image.
- [ ] Rollback digest and retention verified.
- [ ] Score at least 85/100 and mandatory gates passed.
- [ ] Reviewer signs off on residual risks.

**Related:** [Chapter 045 — Enterprise Jenkins Container Image Pipeline Capstone](../045-enterprise-jenkins-container-image-pipeline-capstone.md).
