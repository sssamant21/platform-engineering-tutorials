# Chapter 039 — Hands-on Lab: Artifact Repositories, Versioning and Rollback

**Environment:** Disposable Jenkins, isolated Linux agent, fixture Maven/npm project, nonproduction Maven-compatible repository and private generic package endpoint. No production publishing credentials.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Registry inventory | Record product/version and endpoints | Baseline |
| 02 | Credential scope | Create limited write identity | Permission record |
| 03 | Version policy | Define snapshot/release coordinates | Policy |
| 04 | Maven fixture | Commit wrapper, POM and tests | Git SHA |
| 05 | Maven verify | Run `./mvnw -B -ntp verify` | Test result |
| 06 | Maven settings | Bind Jenkins-managed settings | No secret in logs |
| 07 | Snapshot publish | Deploy snapshot to test repo | Package coordinate |
| 08 | Maven download | Fetch published snapshot | Digest |
| 09 | Generic package | Build fixture tarball | Artifact |
| 10 | SHA-256 | Generate checksum manifest | Hash |
| 11 | Generic upload | Publish to approved test endpoint | HTTP response |
| 12 | Generic download | Retrieve package | Matching hash |
| 13 | npm fixture | Commit package and lockfile | Git SHA |
| 14 | npm pack | Run `npm ci`, tests and pack | Tarball |
| 15 | npm registry | Review private registry auth and dry run | Registry evidence |
| 16 | Jenkins archive | Fingerprint artifact and checksum | Build evidence |
| 17 | Immutable collision | Attempt same test release coordinate | Rejected/blocked |
| 18 | Auth failure | Revoke test token | 401/403 |
| 19 | Retention audit | Inspect lifecycle/rollback window | Retention record |
| 20 | Rollback | Select previous approved digest | Recovery evidence |

## 12 troubleshooting drills

1. Maven server ID mismatch.
2. Maven repository 401/403.
3. Immutable release 409 collision.
4. Snapshot/release repository mismatch.
5. npm wrong registry destination.
6. npm publish token lacks permission.
7. Generic upload endpoint returns 404.
8. Registry HTTP 429/503.
9. Artifact checksum mismatch.
10. Jenkins archive glob empty.
11. Registry storage quota exceeded.
12. Previous release missing during rollback.

For each drill capture symptom, artifact coordinate, HTTP response, expected/actual digest, root cause, remediation and retest. Mark unsupported operations blocked rather than inventing evidence.

## Minimal generic artifact fixture

```sh
set -eu
mkdir -p dist
printf 'jenkins-ch039-fixture\n' > dist/README.txt
tar -czf dist/app-1.0.0.tar.gz -C dist README.txt
sha256sum dist/app-1.0.0.tar.gz > dist/app-1.0.0.tar.gz.sha256
cat dist/app-1.0.0.tar.gz.sha256
```

After uploading and downloading the tarball to a separate directory:

```sh
sha256sum downloaded/app-1.0.0.tar.gz
# Compare the digest to the saved expected digest.
```

Do not use `sha256sum -c` against an untrusted manifest without reviewing paths.

## Evidence template

```text
UTC timestamp:
Git SHA and Jenkins build:
Artifact type / coordinate / version:
Registry product and endpoint:
Credential ID (never value):
Test results and toolchain:
SHA256 expected / downloaded:
HTTP publish and download responses:
Retention/immutability policy:
Failure injection:
Root cause and recovery:
Rollback digest:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 12 drills completed or explicitly blocked.
- [ ] At least one test artifact published and downloaded.
- [ ] SHA-256 integrity verified after retrieval.
- [ ] Immutable version collision blocked.
- [ ] Scoped credential rotation tested.
- [ ] Retention and rollback policy documented.
- [ ] No production registry or secrets used.

**Related:** [Chapter 039 — Artifact Management and Repository Integration](../039-jenkins-artifact-management-versioning-repository-integration.md).
