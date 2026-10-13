# Chapter 021 — Secure Container Image Builds, Registries and Immutable Tags

**Part 05 — Container Builds and Software Supply-Chain Security** | **Chapter 021 / 100**  
**Audience:** SRE, platform, infrastructure, DevSecOps and release engineers  
**Lab:** Disposable GitLab project, rootless-compatible Docker/BuildKit workstation or isolated build runner, disposable container registry  
**Architecture:** GitLab CI validates and builds once; GitOps promotes the same immutable image digest across Dev → Test → Staging → Production namespaces. All four namespaces share one Kubernetes cluster in the reference architecture.

> **Safety:** Use generic training names only. Do not expose registry passwords, mount a host Docker socket into untrusted MR jobs, enable privileged Docker-in-Docker on a shared runner, or push to production repositories during this lab. No Kubernetes production changes are required.

## 1. Learning objectives

After this chapter, you can:

1. Explain OCI image layers, manifests, indexes, tags and digests.
2. Build a minimal, non-root application image using a multi-stage Dockerfile.
3. Separate MR validation from trusted publishing on protected refs.
4. Authenticate to a registry using scoped, short-lived credentials.
5. Publish and inspect a container image and record its registry digest.
6. Demonstrate why tags are mutable and why GitOps should pin digests.
7. Validate container runtime security, image metadata and provenance boundaries.
8. Diagnose build, authentication, push, architecture and pull failures.
9. Define operational acceptance criteria and a rollback procedure.

## 2. Reference architecture

\`\`\`text
GitLab merge request
      |
      +--> lint / unit tests / security checks
      |           (untrusted, no publish credentials)
      |
Approved merge to protected main
      |
      v
Trusted build runner / BuildKit
      |
      +--> deterministic source context
      +--> multi-stage Dockerfile
      +--> non-root runtime
      |
      v
Container registry
      |
      +--> human-readable tag (mutable pointer)
      +--> immutable manifest digest (sha256:...)
      |
      v
Reviewed GitOps MR updates image@sha256:...
      |
      v
Argo CD sync to Kubernetes namespaces
demo-dev -> demo-test -> demo-staging -> demo-prod
\`\`\`

**Core principle:** Build once and promote the exact same digest. Do not rebuild separately for each environment, because different builds can produce different artifacts even from the same source commit.

## 3. OCI image fundamentals

An OCI-compatible image is a content-addressed collection of configuration and filesystem layers referenced by a manifest. A multi-platform image index can point to architecture-specific manifests.

| Concept | Example | Operational meaning |
| --- | --- | --- |
| Repository | \`registry.example.com/training/demo-app\` | Image namespace |
| Tag | \`:main-abc1234\` | Human-readable reference, usually mutable |
| Manifest digest | \`@sha256:...\` | Content-addressed image reference |
| Layer | Compressed filesystem change | Shared/cached build content |
| Image config | Entrypoint, user, env, labels | Runtime defaults |
| Multi-platform index | linux/amd64 + linux/arm64 | Platform selection |
| Registry retention | Keep/delete artifacts | Affects rollback availability |

**Nuance:** A digest identifies the referenced manifest or index bytes. A multi-platform index digest is not interchangeable with an architecture-specific manifest digest. Record the exact digest intended for deployment and confirm the target cluster architecture is supported.

### Why tags are not enough

\`\`\`text
demo-app:main  -> sha256:AAAA  (Monday)
demo-app:main  -> sha256:BBBB  (Tuesday)
\`\`\`

A Kubernetes manifest referencing only \`demo-app:main\` may resolve differently over time. A GitOps manifest referencing \`demo-app@sha256:AAAA\` selects the same immutable content as long as the registry retains it and the platform supports it.

Do not confuse a source commit SHA, an image tag containing a commit SHA, and an OCI registry digest. They are different identifiers.

## 4. Build security controls

- Use a trusted, reviewed base image pinned by digest for production.
- Use a multi-stage build to exclude compilers and build tools from runtime.
- Use a non-root UID and a minimal runtime filesystem.
- Do not put secrets in \`ARG\`, \`ENV\`, image layers, build logs or committed files.
- Use BuildKit secret mounts for authorized build-time secrets when necessary.
- Pin dependency versions and verify dependency integrity.
- Limit build context with \`.dockerignore\`.
- Scan dependencies, source and built image with supported scanners.
- Keep the trusted publish runner isolated from untrusted MR code.
- Produce SBOM and provenance attestations in later chapters.
- Retain approved digests for rollback; registry garbage collection can make a digest unavailable.

**Build isolation:** Rootless BuildKit or a hardened dedicated build service is preferred where compatible. Docker-in-Docker in privileged mode and Docker socket mounting are high-risk patterns and are **not** required for this lab.

## 5. Hands-on lab — minimal container image

### Prerequisites

- Disposable repository \`demo-app\`.
- Docker Engine with BuildKit or a supported rootless builder.
- Python 3.12 for local tests.
- An authorized disposable registry repository, such as a GitLab Container Registry project.
- Permission to inspect the registry and create scoped tokens.
- Network access to fetch an approved Python base image.

### Step 1 — Create files

\`\`\`text
demo-app/
├── .dockerignore
├── Dockerfile
├── README.md
├── src/
│   ├── __init__.py
│   └── server.py
└── tests/
    └── test_server.py
\`\`\`

Create an empty \`src/__init__.py\`.

\`src/server.py\`:

\`\`\`python
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


def response(path: str) -> tuple[int, dict[str, str]]:
    if path == "/healthz":
        return 200, {"status": "ok"}
    return 404, {"error": "not found"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        code, payload = response(self.path)
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
\`\`\`

\`tests/test_server.py\`:

\`\`\`python
import unittest
from src.server import response


class ServerTests(unittest.TestCase):
    def test_health(self):
        self.assertEqual(response("/healthz"), (200, {"status": "ok"}))

    def test_unknown(self):
        self.assertEqual(response("/missing")[0], 404)


if __name__ == "__main__":
    unittest.main()
\`\`\`

\`README.md\`:

\`\`\`markdown
# demo-app

Disposable image build and registry digest lab.
\`\`\`

### Step 2 — Create \`.dockerignore\`

\`\`\`dockerignore
.git
.gitlab
.gitlab-ci.yml
.env
*.pem
*.key
__pycache__/
.pytest_cache/
tests/
dist/
reports/
*.log
\`\`\`

This reduces accidental inclusion of sensitive or irrelevant files. It does not replace secret scanning.

### Step 3 — Multi-stage Dockerfile

\`\`\`dockerfile
# syntax=docker/dockerfile:1
# Training base tag; production should pin a reviewed digest.
FROM python:3.12-slim AS build
WORKDIR /build
COPY src/ ./src/
RUN python -m compileall -q src

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=build /build/src/ /app/src/
USER 65532:65532
EXPOSE 8080
CMD ["python", "-m", "src.server"]
\`\`\`

This example has no third-party Python packages. A production build should replace the training base tag with an approved digest, verify that the base includes a compatible interpreter, and document rebuild cadence for security updates.

### Step 4 — Local unit tests

\`\`\`bash
python -m unittest discover -s tests -v
\`\`\`

Expected: 2 tests pass.

### Step 5 — Build the image

\`\`\`bash
docker build --pull -t demo-app:ch021 .
docker image inspect demo-app:ch021 \
  --format '{{.Config.User}} {{.Config.Entrypoint}} {{.Config.Cmd}}'
\`\`\`

Expected user: \`65532:65532\`. Confirm the image contains no secrets or development-only files.

### Step 6 — Run the container without extra privileges

\`\`\`bash
docker run --rm --name demo-app-ch021 \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  -p 127.0.0.1:8080:8080 \
  -d demo-app:ch021

curl --fail --silent http://127.0.0.1:8080/healthz
docker logs demo-app-ch021
docker stop demo-app-ch021
\`\`\`

Expected response:

\`\`\`json
{"status": "ok"}
\`\`\`

The read-only filesystem works for this simple app; more complex applications may require an explicitly mounted writable temporary directory. If the port is already occupied, choose another local host port.

### Step 7 — Tag for a disposable registry

Use the registry path provided by your authorized GitLab project. Replace the placeholder below; do not literally push to \`registry.example.com\`.

\`\`\`bash
export IMAGE_REPO="registry.example.com/training/demo-app"
export IMAGE_TAG="lab-$(git rev-parse --short=12 HEAD)"
docker tag demo-app:ch021 "$IMAGE_REPO:$IMAGE_TAG"
\`\`\`

If working outside a Git checkout, set a unique training tag manually.

### Step 8 — Authenticate securely

Use an approved, least-privilege registry token. A GitLab CI job should use the supported CI registry variables or a short-lived credential, not a personal password stored in YAML.

\`\`\`bash
read -r -s -p "Registry token: " REGISTRY_TOKEN
printf '\n'
printf '%s' "$REGISTRY_TOKEN" | docker login registry.example.com \
  --username "<REGISTRY_USERNAME>" --password-stdin
unset REGISTRY_TOKEN
\`\`\`

Replace the registry hostname and username with approved values. Docker may store credentials using its configured credential helper or local config; inspect and follow your organization's credential-storage policy. Never print the token.

### Step 9 — Push and inspect the digest

\`\`\`bash
docker push "$IMAGE_REPO:$IMAGE_TAG"
docker buildx imagetools inspect "$IMAGE_REPO:$IMAGE_TAG"
\`\`\`

Record the registry manifest or index digest shown by the inspection command. Some local Docker image IDs and RepoDigests are not the same as the intended multi-platform index digest; use the registry's reported reference.

If \`docker buildx imagetools\` is unavailable, use an approved OCI-aware registry inspection tool such as \`skopeo\` or \`crane\`.

### Step 10 — Pull by digest

Set \`IMAGE_DIGEST\` to the actual \`sha256:...\` value reported by the registry inspection:

\`\`\`bash
export IMAGE_DIGEST="sha256:<REPLACE_WITH_ACTUAL_DIGEST>"
docker pull "$IMAGE_REPO@$IMAGE_DIGEST"
docker image inspect "$IMAGE_REPO@$IMAGE_DIGEST" --format '{{.Config.User}}'
\`\`\`

Do not use a fabricated digest. Validate the actual digest resolves from the registry and the runtime user remains non-root.

## 6. GitLab CI architecture: validation vs publishing

A safe enterprise design uses two runner trust tiers:

| Runner pool | Pipeline source | Permissions |
| --- | --- | --- |
| \`mr-validation\` | Merge requests | Tests/scans only, no registry write |
| \`trusted-build\` | Protected default branch | Registry push with scoped credentials |
| \`release-automation\` | Approved promotion workflow | GitOps change proposal, no direct cluster-admin |

The following pipeline is a **validation-only executable example**. It does not require Docker-in-Docker, privileged runners or registry credentials:

\`\`\`yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages: [validate, test]

default:
  image: python:3.12-slim
  tags: [mr-validation]

syntax:
  stage: validate
  script:
    - python -m compileall -q src tests

unit_tests:
  stage: test
  needs:
    - job: syntax
      artifacts: false
  script:
    - python -m unittest discover -s tests -v
\`\`\`

A **separate, centrally governed trusted publish pipeline** should run only on protected refs and a dedicated build runner. Choose a supported nonprivileged BuildKit/build service and implement registry authentication via a secret manager or approved GitLab CI registry variables. Do not copy MR-supplied arbitrary Dockerfiles into a highly privileged build environment without threat-modeling the build process.

### Trusted publish pseudo-workflow

\`\`\`text
1. Verify protected ref and approvals.
2. Fetch reviewed commit.
3. Build with approved, pinned base images.
4. Run real security scanners and policy enforcement.
5. Publish once to scoped registry repository.
6. Query registry for immutable manifest/index digest.
7. Record commit, digest, builder identity, scan results and provenance.
8. Open reviewed GitOps MR updating image digest for demo-dev.
9. Promote same digest through demo-test, demo-staging, demo-prod.
\`\`\`

This sequence is a production architecture checklist, not a claim that the validation-only YAML publishes images.

## 7. Kubernetes deployment by digest

Illustrative GitOps Deployment excerpt:

\`\`\`yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-app
  namespace: demo-dev
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo-app
  template:
    metadata:
      labels:
        app: demo-app
    spec:
      containers:
        - name: demo-app
          image: registry.example.com/training/demo-app@sha256:<ACTUAL_DIGEST>
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8080
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            runAsUser: 65532
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 64Mi
            limits:
              cpu: 500m
              memory: 256Mi
\`\`\`

**Not directly applyable:** Replace \`<ACTUAL_DIGEST>\` with the verified digest, confirm image pull credentials and admission policies, and validate with \`kubectl apply --dry-run=server\` in an authorized training namespace. A Kubernetes cluster might also require \`seccompProfile: RuntimeDefault\` to satisfy Restricted Pod Security. This chapter does not deploy into the shared cluster.

For Helm, configure the chart to render an image reference by digest. Do not accidentally concatenate both a tag and digest incorrectly; test the rendered manifest.

## 8. Operational failure injections

Perform these only in the disposable environment.

### Test A — Mutable tag demonstration

Push a different harmless training image to the **same disposable tag** (only if registry policy allows). Observe that the tag's digest changes. Restore the original image if required.

**Expected:** Tag can move; previously recorded digest remains a reference to original content if retained.

### Test B — Wrong digest

Try to pull a clearly invalid digest in the disposable registry.

**Expected:** Manifest unknown/not found. Correct to the verified digest.

### Test C — Authentication denied

Attempt a push using a credential with read-only scope, or inspect permissions without issuing a push.

**Expected:** Registry denies push. Restore a properly scoped credential; do not widen permissions unnecessarily.

### Test D — Runtime privilege review

Inspect image user and container security settings. Attempt no privileged host operations.

**Expected:** Container runs as non-root with dropped capabilities and no-new-privileges.

### Test E — Missing architecture

Inspect image platforms and compare with your target Kubernetes node architecture.

**Expected:** Document any mismatch; do not promote unsupported platform images.

### Test F — Registry retention

Review whether an old approved digest remains available after tag changes. Do not delete shared registry content.

**Expected:** Retention policy preserves required rollback digests.

## 9. Observability and SRE indicators

| Signal | Why it matters | Response |
| --- | --- | --- |
| Build duration p95 | CI latency and cost | Inspect cache, network and builder capacity |
| Registry push failure rate | Publishing reliability | Check auth, storage, throttling |
| Digest resolution failures | Deployment and rollback risk | Inspect retention and replication |
| Image size | Pull latency and storage | Reduce layers/dependencies |
| Scanner coverage | Supply-chain risk | Fix gaps and policy enforcement |
| Base-image age | Exposure to known vulnerabilities | Rebuild with approved updates |
| Architecture mismatch | Pod startup failures | Publish supported platforms |
| Provenance completeness | Auditability | Record source, builder and digest |

## 10. Troubleshooting runbook

| Symptom | Likely cause | Investigation |
| --- | --- | --- |
| Build fails during COPY | Wrong context or .dockerignore | Inspect build context |
| Container exits | Entrypoint, missing files, permission | Check logs and user |
| Read-only filesystem failure | App writes at runtime | Add approved writable volume |
| Push unauthorized | Token scope or registry URL | Verify credential and repository |
| Digest differs from expectation | Different manifest/platform or rebuild | Inspect OCI index and platform |
| ImagePullBackOff | Registry auth, DNS, architecture or missing digest | Inspect pod events |
| Registry tag overwritten | Mutable tag policy | Deploy by digest, protect tags |
| Vulnerability scan fails | Known vulnerable dependency/base | Triage, remediate and rebuild |
| Rollback digest missing | Retention or garbage collection | Restore retained artifact/backup |
| Builder saturation | Concurrency/resource limits | Scale isolated builders |

## 11. Incident response and rollback

1. Identify affected commit, image repository, tag, registry digest and environment.
2. Determine whether failure is build, registry, security or runtime related.
3. Quarantine suspicious images and revoke exposed registry credentials.
4. Preserve nonsecret logs, scan reports and manifest evidence.
5. Stop promotion of the affected digest.
6. Select a previously approved and **still available** digest.
7. Update GitOps configuration through a reviewed revert/promotion MR.
8. Verify Argo CD sync, pod readiness and application SLOs.
9. Record timeline, root cause and preventive action.

A Git rollback changes desired configuration; it does not resurrect an image that registry retention has deleted.

## 12. Acceptance checklist

- [ ] OCI tag, digest, manifest and index distinctions explained.
- [ ] Multi-stage image builds successfully.
- [ ] Application unit tests pass.
- [ ] Non-root container responds to \`/healthz\`.
- [ ] Read-only filesystem and dropped capabilities validated.
- [ ] Registry authentication uses scoped credentials.
- [ ] Image pushed only to authorized disposable repository.
- [ ] Registry digest recorded and pull-by-digest validated.
- [ ] MR validation and trusted publish identities separated.
- [ ] Mutable tag and rollback retention risks documented.
- [ ] Production image base pinning and scanner policy identified.
- [ ] No production cluster changes or secrets exposed.

## 13. Evidence worksheet

\`\`\`text
CHAPTER 021 — SECURE IMAGE BUILD AND REGISTRY LAB
Date:
GitLab project:
Builder / Docker / BuildKit version:
Runner trust tier:
Source commit:
Base image and approved digest:
Image repository:
Published tag:
Published registry digest:
Platform(s):
Runtime UID:
Read-only filesystem test:
Health endpoint test:
Image size:
Registry auth scope:
Scanner/policy results:
Tag mutability test:
Pull-by-digest test:
Retention review:
Reviewer:
Open risks and owners:
\`\`\`

## 14. Knowledge checks

1. Why does a source commit SHA not uniquely identify a container image?
2. What is the difference between a tag and a registry digest?
3. Why can a multi-platform image have both an index digest and platform-specific digests?
4. Why should MR runners not receive registry write credentials?
5. What does a multi-stage build remove from the runtime image?
6. Why is a SHA-256 checksum not a signature or provenance attestation?
7. How does registry retention affect disaster recovery and GitOps rollback?

## 15. Completion

**Pass:** You build and run a non-root image, publish it to an authorized disposable registry, retrieve and pull by its real digest, demonstrate the operational risks of mutable tags, and document trusted publishing and GitOps promotion boundaries.

**Next: Chapter 022 — Container Image Vulnerability Scanning, SBOM Generation and Dependency Security.**
