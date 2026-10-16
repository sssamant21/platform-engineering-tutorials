# Chapter 041 — Docker Fundamentals and Jenkins Container Build Pipelines

**Part 09 — Docker, Containers and Image Pipelines**  
**Audience:** Jenkins SRE, DevOps, platform engineering, security and release teams  
**Prerequisites:** Chapters 001–040, disposable Jenkins, isolated Linux build agent with approved Docker Engine/BuildKit, nonproduction container registry.

## 1. Learning objectives

Explain container image layers, Dockerfile stages, build contexts, tags and digests; build a minimal application image; implement Jenkins container CI with unit tests and image validation; control Docker daemon privileges and secrets; publish only from trusted branches; capture immutable provenance; troubleshoot build failures and recover safely.

## 2. Architecture and trust boundary

```text
Git protected revision → Jenkins isolated agent
   ├─ unit tests and quality checks
   ├─ Dockerfile validation
   ├─ docker build / BuildKit
   ├─ image smoke test
   ├─ local image ID + digest evidence
   └─ registry auth (trusted release only)
                 ↓
       private container registry
                 ↓
       deployment by immutable digest
```

**Security warning:** Access to a rootful Docker daemon socket is effectively host-root-equivalent. Never mount the host `/var/run/docker.sock` into an untrusted Jenkins build, or grant untrusted PRs Docker daemon or registry-publish credentials. Use dedicated ephemeral builders, rootless BuildKit where supported, or appropriately isolated managed build services. Docker-in-Docker requires deliberate isolation and often privileged configuration; it is not a default recommendation.

## 3. Docker concepts for SRE

| Concept | Operational meaning | SRE consideration |
|---|---|---|
| Image | Content-addressed filesystem/config | Pin digest for deployment |
| Tag | Mutable name referencing image | Never rely on `latest` |
| Digest | Immutable content identifier | Record from registry |
| Layer | Reusable build filesystem delta | Cache, storage, leakage |
| Build context | Files sent to builder | Use `.dockerignore` |
| Multi-stage build | Build in one stage, copy to runtime | Smaller attack surface |
| Registry | Stores manifests and blobs | Auth, retention, capacity |
| BuildKit | Modern build backend | Cache and secret mounts |
| Container runtime | Runs image | Rootless/nonroot controls |

Image ID from `docker image inspect` and registry manifest digest are not interchangeable; record the digest returned by the registry after push.

## 4. Minimal application fixture

`app.py`:
```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler).serve_forever()
```

`test_app.py`:
```python
import unittest
from app import Handler

class AppTests(unittest.TestCase):
    def test_handler_exists(self):
        self.assertTrue(callable(Handler))
```

`Dockerfile`:
```dockerfile
# Replace the tag with an organization-approved digest-pinned Python base image.
FROM python:3.12-slim
WORKDIR /app
COPY app.py /app/app.py
RUN useradd --system --uid 10001 appuser
USER 10001
EXPOSE 8080
CMD ["python", "/app/app.py"]
```

`.dockerignore`:
```text
.git
.venv
__pycache__
*.pyc
*.log
.env
reports
```

**Production hardening:** Pin the base image to a reviewed digest; rebuild on base image security updates; run as nonroot, keep the image minimal, avoid embedding secrets, and define runtime filesystem/network restrictions in the deployment platform. The fixture uses an unpinned tag only to simplify initial local lab setup.

## 5. Local build and smoke test

```sh
set -eu
python3 -m unittest discover -v -p 'test_*.py'
docker version
docker build --pull -t jenkins-ch041:lab .
docker image inspect jenkins-ch041:lab --format '{{.Id}}'
docker run -d --name jenkins-ch041-smoke -p 127.0.0.1:18080:8080 jenkins-ch041:lab
curl --fail --silent --show-error --retry 8 --retry-delay 1 http://127.0.0.1:18080/healthz
docker logs jenkins-ch041-smoke
docker rm -f jenkins-ch041-smoke
```

Bind the test port to loopback and use a disposable host. The smoke test retries because the application may not yet be listening. If the script exits before cleanup, remove the named test container manually after capturing logs.

## 6. Jenkinsfile: build, test and smoke

```groovy
pipeline {
    agent { label 'isolated-docker-builder' }
    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }
    environment {
        IMAGE_LOCAL = 'jenkins-ch041:ci'
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Unit test') {
            steps { sh "python3 -m unittest discover -v -p 'test_*.py'" }
        }
        stage('Build') {
            steps {
                sh 'docker build --pull --tag "$IMAGE_LOCAL" .'
                sh 'docker image inspect "$IMAGE_LOCAL" --format "{{.Id}}" > image-id.txt'
            }
        }
        stage('Smoke') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    docker run -d --name "ch041-$BUILD_NUMBER" \
                      -p 127.0.0.1::8080 "$IMAGE_LOCAL"
                    port=$(docker port "ch041-$BUILD_NUMBER" 8080/tcp | sed 's/.*://')
                    curl --fail --silent --show-error \
                      --retry 10 --retry-delay 1 \
                      "http://127.0.0.1:$port/healthz"
                '''
            }
        }
    }
    post {
        always {
            sh '''#!/bin/sh
                docker rm -f "ch041-$BUILD_NUMBER" >/dev/null 2>&1 || true
            '''
            archiveArtifacts artifacts: 'image-id.txt',
                             allowEmptyArchive: true
        }
    }
}
```

The example assumes an exclusive ephemeral builder, Docker CLI/daemon access and Linux `sed`/curl. On shared builders, use collision-resistant container names and job isolation. This CI-only example deliberately does **not** publish images.

## 7. Trusted registry publication

For a separately authorized protected-branch release job, use a dedicated registry credential:

```groovy
stage('Publish') {
    when { branch 'main' }
    steps {
        withCredentials([usernamePassword(credentialsId: 'registry-publisher',
                         usernameVariable: 'REG_USER',
                         passwordVariable: 'REG_PASS')]) {
            sh '''#!/bin/sh
                set -eu
                export DOCKER_CONFIG="$(mktemp -d)"
                trap 'rm -rf "$DOCKER_CONFIG"' EXIT
                printf '%s' "$REG_PASS" | docker login registry.example.test \
                  --username "$REG_USER" --password-stdin
                docker tag jenkins-ch041:ci \
                  registry.example.test/training/jenkins-ch041:1.0.0
                docker push registry.example.test/training/jenkins-ch041:1.0.0
                docker image inspect \
                  registry.example.test/training/jenkins-ch041:1.0.0 \
                  --format '{{json .RepoDigests}}'
                docker logout registry.example.test
            '''
        }
    }
}
```

**Do not rely on the `when` branch condition for authorization.** Enforce SCM branch protection, trusted Pipeline definitions, isolated release agents, registry ACLs and approvals. Prefer a unique immutable release tag; inspect registry-side manifest digest after push and record it with source SHA. The example uses a username/password credential; adapt to short-lived workload identity when supported.

## 8. Image security and supply-chain policy

1. Pin base images to digests; track upstream patch releases.
2. Enforce `.dockerignore` and scan context for secrets.
3. Never put credentials in Dockerfile `ARG` or `ENV`; use BuildKit secret mounts for build-time secrets when necessary.
4. Generate SBOM and vulnerability scan evidence using approved tools.
5. Sign image digests and verify signatures where policy requires.
6. Apply least privilege and avoid privileged/rootful builders for untrusted workloads.
7. Record source SHA, Dockerfile hash, builder version, image ID, registry digest and scan result.
8. Use immutable digest deployment and maintain previous known-good digest for rollback.

## 9. Build performance and FinOps

| Signal | Interpretation |
|---|---|
| Build duration p50/p95 | Cache and dependency performance |
| Build context size | Excessive context slows upload |
| Layer cache hit ratio | Rebuild efficiency |
| Image size | Pull latency, storage, attack surface |
| Builder CPU/memory | Agent saturation |
| Registry push/pull latency | Network/storage health |
| Image retention | Registry cost and rollback availability |
| Vulnerability age | Patch management effectiveness |

Use registry retention policies that preserve deployed and rollback-required digests. Do not prune blobs referenced by active deployments.

## 10. Troubleshooting matrix

| Symptom | Checks | Safe remediation |
|---|---|---|
| Docker daemon unavailable | Socket/daemon health | Restore builder, do not escalate blindly |
| Permission denied socket | Builder identity | Use approved isolated builder |
| Build context huge | `.dockerignore` | Exclude unnecessary files |
| Base image pull 429 | Registry rate limits | Authenticate/use approved mirror |
| Dockerfile syntax error | Build output | Correct and retest |
| `COPY` fails | Context path | Fix context layout |
| Container exits | Logs/entrypoint | Correct runtime command |
| Health endpoint fails | Port/listen/route | Inspect logs and binding |
| Port already allocated | Existing container | Use dynamic port |
| Image runs as root | Dockerfile `USER` | Use nonroot identity |
| Registry push 401/403 | Credentials/ACL | Rotate/fix scoped identity |
| Registry TLS error | Trust chain | Repair CA, no insecure mode |
| Tag points to wrong image | Manifest digest | Redeploy verified digest |
| Builder disk full | Layers/cache | Clean disposable cache safely |
| Scan blocks image | Vulnerability report | Patch or approved exception |
| Secret embedded in layer | History/context scan | Revoke/rotate, rebuild clean |

## 11. Production runbooks

### A. Onboard container build
1. Review Dockerfile, base digest, ownership and build context.
2. Allocate dedicated ephemeral builder with minimum privilege.
3. Configure tests, image build and smoke verification.
4. Enable scanning/SBOM and source-to-digest provenance.
5. Configure separate protected publication workflow.
6. Rehearse image rollback and retention.

### B. Docker builder outage
1. Capture build URL, agent identity, daemon logs and disk usage.
2. Distinguish agent offline, socket access, storage and registry failure.
3. Stop scheduling affected builder; preserve evidence.
4. Replace/restart isolated builder using approved procedure.
5. Rerun pinned source SHA; compare image evidence.

### C. Registry incident
1. Capture HTTP response, target repo/tag, manifest digest and source SHA.
2. Check DNS/TLS, auth, quota and registry availability.
3. Stop uncontrolled retries and avoid tag overwrites.
4. Restore service, republish only approved immutable coordinates.
5. Verify registry digest and record incident.

### D. Image compromise
1. Pause promotion and quarantine affected digest.
2. Revoke exposed credentials and audit registry writes.
3. Rebuild from reviewed base/dependencies on clean builder.
4. Scan, sign and publish a new immutable digest.
5. Notify security owners and document impacted deployments.

### E. Rollback
1. Identify previous approved image digest.
2. Verify registry manifest, signature and scan policy.
3. Redeploy previous digest via controlled deployment workflow.
4. Validate readiness, functional smoke and SLOs.
5. Preserve failed image for investigation.

## 12. Acceptance checklist

- [ ] Docker fixture builds on isolated agent.
- [ ] Unit tests and HTTP smoke test pass.
- [ ] Nonroot runtime and context exclusions validated.
- [ ] Image ID and source SHA recorded.
- [ ] Registry publication demonstrated only in authorized test workflow.
- [ ] Registry manifest digest captured and verified.
- [ ] Security scans and rollback policy reviewed.
- [ ] Troubleshooting and runbooks exercised.

**Companion:** [Chapter 041 hands-on lab](labs/041-docker-fundamentals-jenkins-container-build-pipelines-check.md).  
**Next:** Chapter 042 — Dockerfile Optimization, Multi-Stage Builds and Image Security.
