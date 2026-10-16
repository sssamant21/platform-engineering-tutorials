# Chapter 043 — Jenkins Container Registry Integration, Image Tagging and Promotion

**Part 09 — Docker, Containers and Image Pipelines**  
**Audience:** Jenkins SRE/DevOps, platform engineering, release and security teams  
**Prerequisites:** Chapters 041–042, isolated container builder, nonproduction registry (Harbor, ECR, ACR, GAR or OCI-compatible), scoped publisher identity.

## Objectives

Integrate Jenkins with private container registries, use safe tag and digest strategies, separate untrusted CI from privileged publication, promote identical OCI image bytes between environments, implement registry authentication and cleanup policies, and troubleshoot push/pull, integrity and rollback incidents.

## 1. Reference architecture

```text
Git protected commit
       ↓
Jenkins CI (unprivileged isolated builder)
   ├─ unit tests / static gates
   ├─ Docker/BuildKit image build
   ├─ smoke + vulnerability/SBOM checks
   └─ source SHA + local image evidence
       ↓ reviewed release authorization
Jenkins trusted release job (scoped identity)
   ├─ push candidate to private registry
   ├─ record immutable manifest digest
   ├─ verify signature/policy
   └─ promote same manifest/layers to release namespace
       ↓
Deploy by registry/repository@sha256:digest
```

A **tag is a mutable pointer**; a registry manifest digest identifies immutable content. The digest is the preferred deployment identity. A local Docker image ID is not necessarily the registry manifest digest. When copying across registries, manifest serialization or format conversion may change digest even when layer content is equivalent; verify both source and destination manifest identity and record any intentional transformation.

## 2. Registry comparison

| Registry | Typical identity | Operational concerns |
|---|---|---|
| AWS ECR | IAM role/temporary login token | Cross-account permissions, region, lifecycle |
| Azure ACR | Managed identity/service principal | Role scope, network endpoints, retention |
| Google Artifact Registry | Workload identity/service account | Repository IAM, region, cleanup |
| Harbor | Robot account/OIDC | Projects, quotas, replication, signing |
| Nexus/Artifactory OCI | Scoped repository credentials | Path semantics, immutability, quotas |
| Generic OCI registry | Username/token | TLS, retention, manifest support |

Do not assume provider-specific commands work for another registry. Prefer short-lived workload identities over static passwords where available.

## 3. Tagging policy

Use unique tags such as `1.4.2`, `git-<shortsha>`, or `build-<runid>` for traceability, but **do not** assume uniqueness makes a tag immutable unless registry policy enforces it. For multi-architecture images, a tag may point to an OCI image index rather than a single-platform manifest. Record the index digest and the selected platform manifest digest as needed.

Recommended release record:

```yaml
repository: registry.example.test/training/service
source_sha: <full-git-sha>
candidate_tag: git-<shortsha>
release_tag: 1.4.2
manifest_digest: sha256:<registry-manifest-digest>
builder_identity: isolated-builder
test_result: passed
scan_result: passed
approval_ticket: <change-id>
rollback_digest: sha256:<previous-approved-digest>
```

## 4. Jenkins trusted publication Pipeline

The following stage assumes a **separate trusted release job**, an image already built and validated as `service:ci` on its isolated agent, and a registry that accepts Docker username/password credentials:

```groovy
stage('Publish candidate') {
    steps {
        withCredentials([usernamePassword(
            credentialsId: 'nonprod-registry-publisher',
            usernameVariable: 'REGISTRY_USER',
            passwordVariable: 'REGISTRY_PASSWORD'
        )]) {
            sh '''#!/bin/sh
                set -eu
                export DOCKER_CONFIG="$(mktemp -d)"
                trap 'rm -rf "$DOCKER_CONFIG"' EXIT
                registry="registry.example.test"
                repository="$registry/training/service"
                shortsha="$(git rev-parse --short=12 HEAD)"
                tag="git-$shortsha"
                printf '%s' "$REGISTRY_PASSWORD" | \
                    docker login "$registry" --username "$REGISTRY_USER" --password-stdin
                docker tag service:ci "$repository:$tag"
                docker push "$repository:$tag"
                docker image inspect "$repository:$tag" \
                    --format '{{json .RepoDigests}}'
                docker logout "$registry"
            '''
        }
    }
}
```

**Important:** `RepoDigests` after push is useful evidence but can be ambiguous for multi-platform images or when the same image is referenced by multiple repositories. For release automation, query the registry manifest digest using an approved tool (`docker buildx imagetools inspect`, `skopeo inspect --raw`, registry API, or provider CLI) and persist a machine-readable verified digest. Do not use `docker inspect .Id` as a registry digest. The example assumes a trusted checkout; a branch condition alone is not authorization.

## 5. AWS ECR example (isolated test account)

Prerequisites: AWS CLI v2, Docker, scoped IAM identity and precreated ECR repository. For commercial AWS partition:

```sh
set -eu
AWS_REGION=us-east-1
ACCOUNT_ID=123456789012 # placeholder, replace with test account
REPO=jenkins-ch043
aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin \
    "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
docker tag service:ci \
  "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO:git-test"
docker push "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO:git-test"
aws ecr describe-images --region "$AWS_REGION" \
  --repository-name "$REPO" --image-ids imageTag=git-test \
  --query 'imageDetails[0].imageDigest' --output text
```

**GovCloud note:** Registry DNS suffix, partition, account, region and IAM role configuration differ. Do not copy commercial AWS examples into GovCloud without verifying endpoints and identity. Prefer workload role credentials, not static AWS access keys.

## 6. Promotion without rebuilding

Promotion should preserve the tested bytes and provenance. Options include registry-native copy/retag or OCI-aware copy tools (e.g. `skopeo copy`, `crane cp`) with digest verification. Example using `crane` when installed and authenticated:

```sh
source_ref="registry.example.test/candidates/service@sha256:SOURCE_DIGEST"
dest_ref="registry.example.test/releases/service:1.4.2"
crane cp "$source_ref" "$dest_ref"
crane digest "$dest_ref"
```

`SOURCE_DIGEST` is a placeholder; replace with actual validated registry digest. The command may copy an OCI index and associated manifests depending on tool support. Compare source/destination digests and media types; if they differ, investigate before approving promotion. Enforce release tag immutability and prevent concurrent promotion races.

## 7. Security policy

- Require protected-branch or signed-tag authorization and explicit release approval.
- Restrict registry push rights to a separate trusted identity.
- Use private registries, TLS verification and scoped network policies.
- Do not mount rootful Docker sockets into untrusted PR agents.
- Avoid secrets in Dockerfile ARG/ENV and build context; use ephemeral credentials.
- Generate SBOM and vulnerability scan evidence and sign digest when required.
- Verify signatures/attestations at deployment or admission.
- Preserve prior approved digest for rollback.
- Use retention rules that do not delete deployed, referenced or rollback-critical manifests.
- Audit who published, promoted, deleted or retagged images.

## 8. Promotion and rollback state machine

```text
BUILT → TESTED → SCANNED → CANDIDATE_PUBLISHED
    → APPROVED → PROMOTED → DEPLOYED
                   ↘ FAILED → BLOCKED
DEPLOYED → ROLLBACK_REQUESTED → PREVIOUS_DIGEST_VERIFIED
         → PREVIOUS_DIGEST_DEPLOYED → VALIDATED
```

A failed scan or integrity mismatch must block promotion. Never “fix” an immutable release by silently overwriting its tag. Create a new version with a new digest and audit record.

## 9. Observability and FinOps

| Signal | SRE use |
|---|---|
| Push/pull latency p50/p95 | Network and registry performance |
| 401/403 | Identity/ACL drift |
| 404 | Missing repo/manifest/retention |
| 409 | Immutable tag collision |
| 429/5xx | Throttling/outage |
| Registry storage/quota | Capacity planning |
| Replication lag | Multi-region readiness |
| Digest verification failures | Supply-chain incident |
| Tag mutation events | Governance |
| Cleanup jobs | Retention and rollback impact |
| Registry egress and storage | Cost optimization |

## 10. Troubleshooting matrix

| Symptom | Diagnosis | Recovery |
|---|---|---|
| Docker login 401 | Token/username | Refresh scoped identity |
| Push 403 | Repo write ACL | Correct permission |
| Repo 404 | Wrong path or missing repo | Create/repair approved repo |
| Immutable tag conflict | Tag exists | Allocate new version |
| TLS unknown CA | Registry trust | Repair CA |
| DNS/proxy failure | Builder connectivity | Restore approved route |
| Push stalls | Layer size/network | Inspect metrics, bounded retry |
| ECR token expired | Session age | Refresh login |
| ACR unauthorized | Identity/RBAC | Verify role assignment |
| GAR permission denied | Repository IAM | Correct scoped role |
| Wrong digest recorded | Image ID vs manifest | Query registry manifest |
| Multi-arch digest differs | OCI index/platform | Inspect media types |
| Replication lag | Cross-region registry | Wait for verified manifest |
| Retention deleted rollback | Cleanup policy | Restore from backup |
| Scan result missing | Scanner/report path | Block promotion |
| Secret in logs | Jenkins credential exposure | Revoke and investigate |

## 11. Production runbooks

### A. Registry onboarding
1. Choose registry/region, ownership and data classification.
2. Configure scoped publisher/puller roles and private endpoints.
3. Define immutability, lifecycle and quotas.
4. Test login, push, digest lookup, pull and verification.
5. Validate scan/signature and promotion policy.
6. Document credential rotation and rollback.

### B. Push outage
1. Capture build SHA, target repo/tag, registry endpoint and HTTP error.
2. Separate auth, network, quota, throttling and manifest issues.
3. Preserve builder logs and stop unbounded retries.
4. Restore registry/identity, retry approved candidate.
5. Verify digest and record incident.

### C. Digest mismatch
1. Halt promotion and quarantine suspect reference.
2. Capture source/destination manifests and tool versions.
3. Check platform index, media types and unexpected conversion.
4. Reconcile provenance and verify approved bytes.
5. Resume only after security/release approval.

### D. Credential compromise
1. Revoke publishing identity and pause release jobs.
2. Audit registry push/retag/delete events and affected digests.
3. Rotate credentials, verify trusted agent isolation.
4. Rescan/revalidate suspect images and signatures.
5. Obtain security sign-off before resuming.

### E. Rollback and retention failure
1. Identify previous approved registry digest.
2. Verify manifest exists and signatures/policy match.
3. Deploy previous digest with change controls.
4. Validate health/SLOs and capture evidence.
5. Fix retention/replication gap if image was unavailable.

## 12. Acceptance checklist

- [ ] Registry identity is scoped and protected.
- [ ] Candidate image published with unique tag.
- [ ] Actual registry manifest digest recorded.
- [ ] Pull by digest succeeds.
- [ ] Promotion preserves validated image bytes.
- [ ] Immutable tag collision blocked.
- [ ] Scan/signature evidence and rollback retained.
- [ ] Incident runbooks exercised.

**Companion:** [Chapter 043 hands-on lab](labs/043-jenkins-container-registry-integration-image-tagging-promotion-check.md).  
**Next:** Chapter 044 — Container Image Vulnerability Scanning, SBOMs and Signing in Jenkins.
