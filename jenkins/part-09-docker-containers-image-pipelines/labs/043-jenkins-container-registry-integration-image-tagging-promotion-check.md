# Chapter 043 — Hands-on Lab: Container Registries, Image Tagging and Promotion

**Environment:** Disposable Jenkins, isolated Docker builder, nonproduction OCI registry, scoped publisher and read-only pull identities. Never publish to production.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Registry inventory | Record product/region/version | Baseline |
| 02 | Identity design | Define push/pull roles | Permission matrix |
| 03 | Private repo | Create nonproduction repository | Repo URL |
| 04 | Immutability | Enable release-tag protection | Policy |
| 05 | Fixture | Build Chapter 042 test image | Source SHA/image ID |
| 06 | Test | Execute container smoke | HTTP result |
| 07 | Local tag | Tag with source SHA | Tag |
| 08 | Registry login | Use scoped ephemeral credentials | Auth result |
| 09 | Push | Publish candidate image | Push logs |
| 10 | Digest | Query registry manifest digest | SHA256 |
| 11 | Pull | Pull by digest on clean builder | Verification |
| 12 | Source record | Link digest to Git SHA | Provenance |
| 13 | Promotion | Copy candidate to release namespace | Destination digest |
| 14 | Identity check | Compare source/destination manifests | Equality/explanation |
| 15 | Collision | Attempt duplicate release tag | Rejected |
| 16 | Unauthorized push | Use read-only identity | 403 |
| 17 | Token expiry | Revoke/expire test token | 401 |
| 18 | Retention | Validate protected rollback digest | Lifecycle evidence |
| 19 | Rollback | Pull previous approved digest | Recovery |
| 20 | Review | Approve evidence and runbooks | Sign-off |

## 12 troubleshooting drills

1. Registry DNS failure.
2. Registry TLS unknown CA.
3. Login 401.
4. Push 403.
5. Missing repository 404.
6. Immutable tag collision.
7. Expired ECR/ACR/GAR session.
8. Push throttling or 5xx.
9. Manifest digest mismatch.
10. OCI multi-architecture index confusion.
11. Replication delay.
12. Retention deletes required rollback manifest.

For each drill capture exact HTTP error, source SHA, tag/digest, root cause, remediation and retest. Mark provider-specific drills blocked when no relevant test environment is available.

## Example commands (generic registry)

Use real test registry, repository and credentials; placeholders below are **not executable without replacement**:

```sh
set -eu
REGISTRY=registry.example.test
REPO=training/service
SHA=$(git rev-parse --short=12 HEAD)
IMAGE="$REGISTRY/$REPO:git-$SHA"
docker tag service:ci "$IMAGE"
docker push "$IMAGE"
docker buildx imagetools inspect "$IMAGE"
```

Query the authoritative registry digest, then verify a pull by `repository@sha256:digest`. Never equate local image ID to registry digest.

## Evidence template

```text
UTC timestamp:
Git SHA / Jenkins build:
Registry provider/region:
Publisher credential ID (not secret):
Repository and candidate tag:
Registry manifest digest:
Promotion source/destination:
Manifest comparison:
Scan/signature evidence:
HTTP error and fault injection:
Root cause and recovery:
Rollback digest:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 12 drills completed or explicitly blocked.
- [ ] Private candidate image published.
- [ ] Manifest digest recorded from registry.
- [ ] Digest-pinned pull verified.
- [ ] Release tag immutability enforced.
- [ ] Credential boundaries and recovery validated.
- [ ] Retention protects rollback image.
- [ ] No production registry or privileged untrusted builds used.

**Related:** [Chapter 043 — Container Registry Integration and Promotion](../043-jenkins-container-registry-integration-image-tagging-promotion.md).
