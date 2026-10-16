# Chapter 042 — Dockerfile Optimization, Multi-Stage Builds and Image Security

**Part 09 — Docker, Containers and Image Pipelines**  
**Audience:** SRE, DevOps, platform engineers, security engineers  
**Prerequisites:** Chapter 041, disposable isolated Docker/BuildKit builder, Jenkins Pipeline, private test registry.

## Objectives

Optimize Dockerfiles for reproducible, minimal runtime images; use multi-stage builds, digest-pinned bases and BuildKit cache mounts; reduce build context and layer risk; run as nonroot; generate SBOM and vulnerability evidence; enforce image policy in Jenkins; and practice recovery from compromised or oversized images.

## 1. Architecture and tradeoffs

```text
SCM revision + Dockerfile + dependency lock
    ↓ isolated BuildKit builder
    ├─ stage: dependency resolution / compile / test
    ├─ stage: minimal runtime filesystem
    ├─ static checks and vulnerability/SBOM tools
    └─ digest + provenance
            ↓
    private registry / immutable manifest digest
            ↓
    admission policy + deployment by digest
```

A smaller image usually reduces pull time and exposure but **does not guarantee** fewer vulnerabilities or runtime safety. Treat base-image patch cadence, least privilege, dependencies and workload policy as separate controls.

## 2. Dockerfile optimization principles

| Technique | Benefit | Failure mode / control |
|---|---|---|
| Multi-stage build | Excludes compilers/dev packages | Ensure only required runtime files copied |
| Pinned base digest | Stable base bytes | Schedule digest refresh and CVE response |
| `.dockerignore` | Smaller context, fewer secrets | Verify secrets are not in build context |
| Lockfile | Reproducible dependencies | Pin/check integrity of dependency graph |
| Cache mount | Faster downloads | Isolate untrusted build caches |
| Nonroot `USER` | Reduces runtime privilege | Check filesystem ownership and ports |
| Read-only filesystem | Limits persistence | Provide writable tmpfs if needed |
| Minimal runtime | Lower attack surface | Include required CA/timezone dependencies |
| SBOM | Component inventory | Verify accuracy and retention |
| Image signature | Publisher provenance | Verify trusted identity and digest |

## 3. Lab fixture

`package.json`:
```json
{
  "name": "jenkins-ch042-fixture",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "test": "node --test",
    "start": "node server.js"
  }
}
```

`server.js`:
```js
const http = require('node:http');
const server = http.createServer((req, res) => {
  if (req.url === '/healthz') {
    res.writeHead(200, { 'content-type': 'text/plain' });
    res.end('ok');
  } else {
    res.writeHead(404);
    res.end('not found');
  }
});
server.listen(8080, '0.0.0.0');
```

`server.test.js`:
```js
const test = require('node:test');
const assert = require('node:assert/strict');
test('fixture smoke contract', () => assert.equal(2 + 2, 4));
```

Generate and commit a lockfile with an approved Node/npm version:

```sh
npm install --package-lock-only --ignore-scripts
npm ci
npm test
```

`npm ci` requires a matching committed `package-lock.json`; the lab intentionally has no external runtime packages.

## 4. Multi-stage Dockerfile

```dockerfile
# syntax=docker/dockerfile:1
# LAB ONLY: pin both FROM references to an approved registry digest in production.
FROM node:22-bookworm-slim AS test
WORKDIR /src
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --ignore-scripts
COPY server.js server.test.js ./
RUN npm test

FROM node:22-bookworm-slim AS runtime
ENV NODE_ENV=production
WORKDIR /app
COPY --from=test --chown=node:node /src/server.js ./server.js
USER node
EXPOSE 8080
CMD ["node", "server.js"]
```

The test stage runs first and the final runtime image contains only the server source plus Node runtime. The Node base is **tagged for lab accessibility**; production should use `FROM node:22-bookworm-slim@sha256:<approved-digest>` with a real digest obtained from the trusted registry. Do not insert a fabricated digest.

`.dockerignore`:
```text
.git
node_modules
.env
.env.*
*.pem
*.key
reports
coverage
Dockerfile*
!Dockerfile
```

Do not assume ignore rules replace secret scanning. Keep secret files outside the checkout entirely.

## 5. Compare baseline and optimized image

Build a simple single-stage baseline:

`Dockerfile.baseline`:
```dockerfile
FROM node:22-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY server.js server.test.js ./
EXPOSE 8080
CMD ["node", "server.js"]
```

Compare:

```sh
set -eu
docker build --pull -f Dockerfile.baseline -t ch042:baseline .
docker build --pull -f Dockerfile -t ch042:optimized .
docker image inspect ch042:baseline --format '{{.Size}}'
docker image inspect ch042:optimized --format '{{.Size}}'
docker history --no-trunc ch042:optimized
docker image inspect ch042:optimized --format '{{.Config.User}}'
```

The optimized image may be only modestly smaller for this minimal fixture because the Node runtime dominates. Report observed sizes rather than claiming a predetermined reduction.

## 6. Smoke test and runtime security

```sh
set -eu
docker run -d --name ch042-smoke --read-only \
  --cap-drop=ALL --security-opt no-new-privileges \
  -p 127.0.0.1:18082:8080 ch042:optimized
curl --fail --show-error --silent --retry 10 --retry-delay 1 \
  http://127.0.0.1:18082/healthz
docker rm -f ch042-smoke
```

The app does not write files; real applications may need explicit `--tmpfs /tmp` or writable mounts. On some hosts Docker security options vary; document unsupported controls instead of silently disabling them.

## 7. Jenkinsfile with fail-closed build and smoke

```groovy
pipeline {
    agent { label 'isolated-docker-builder' }
    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Unit test') { steps { sh 'npm ci && npm test' } }
        stage('Build optimized image') {
            steps {
                sh 'docker build --pull -f Dockerfile -t ch042:ci .'
                sh "docker image inspect ch042:ci --format '{{.Id}} {{.Size}} {{.Config.User}}' > image-evidence.txt"
            }
        }
        stage('Smoke') {
            steps {
                sh '''#!/bin/sh
                    set -eu
                    name="ch042-$BUILD_NUMBER"
                    docker run -d --name "$name" --read-only --cap-drop=ALL \
                      --security-opt no-new-privileges \
                      -p 127.0.0.1::8080 ch042:ci
                    port=$(docker port "$name" 8080/tcp | sed 's/.*://')
                    curl --fail --retry 10 --retry-delay 1 \
                      "http://127.0.0.1:$port/healthz"
                '''
            }
        }
    }
    post {
        always {
            sh 'docker rm -f "ch042-$BUILD_NUMBER" >/dev/null 2>&1 || true'
            archiveArtifacts artifacts: 'image-evidence.txt',
                             allowEmptyArchive: true
        }
    }
}
```

This assumes Node/npm on the agent, Docker CLI/daemon and a dedicated disposable builder. `npm ci` runs in the checkout before building; the Dockerfile separately tests the code in the build stage. In production, use a controlled agent image and preserve both test reports and digest evidence.

## 8. Supply-chain and image scanning

Use organization-approved scanners (for example Trivy, Grype or an enterprise registry scanner) with pinned versions and vulnerability database update policy. A scanner command might be:

```sh
trivy image --exit-code 1 --severity CRITICAL,HIGH ch042:optimized
```

This command is only executable when Trivy is installed and its vulnerability database is accessible. Scanner exit 0 does not guarantee absence of vulnerabilities. Keep scan results, tool/database versions and exception approvals.

Generate an SBOM using an approved tool (e.g. Syft) and archive it with image digest, source SHA and scanner evidence. For release signing, use a reviewed signing identity and verify signature against the **registry digest**; do not sign a mutable tag and assume equivalence.

## 9. Secret handling with BuildKit

Avoid `ARG SECRET` and `ENV TOKEN` in Dockerfiles; they may leak through metadata/history or layers. When a build needs private dependency credentials, use a BuildKit secret mount and trusted isolated builder:

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm ci
```

Invoke from a controlled release job with `docker build --secret id=npmrc,src=/path/to/ephemeral/npmrc`; delete the temporary file and rotate credentials on exposure. Secret mounts do not prevent malicious build scripts from exfiltrating the secret: trust the Dockerfile and dependencies.

## 10. Troubleshooting matrix

| Symptom | Diagnosis | Recovery |
|---|---|---|
| `npm ci` fails | Missing/mismatched lockfile | Regenerate/review lockfile |
| Multi-stage COPY fails | Stage path/name | Correct path |
| Runtime missing binary | Excluded dependency | Copy required runtime assets |
| Permission denied | Nonroot ownership | Use `--chown` or adjust paths |
| Read-only filesystem error | App writes to rootfs | Add controlled writable mount |
| Health probe fails | Port/listener | Inspect logs and binding |
| Image unexpectedly large | Base image/layers | Inspect `docker history` |
| Cache unexpectedly stale | Inputs/cache scope | Rebuild with reviewed cache policy |
| Base digest unavailable | Registry/manifest | Select approved replacement |
| Vulnerability scan fails | Real CVE or stale DB | Patch, review exception |
| Scanner cannot update DB | Proxy/TLS/network | Restore trusted access |
| SBOM incomplete | Scanner support/config | Validate coverage |
| Registry signature invalid | Wrong digest/identity | Quarantine image |
| Secret in image history | ARG/ENV misuse | Revoke, rebuild clean |
| Docker daemon denied | Privilege boundary | Use approved builder |
| BuildKit mount unsupported | Builder version | Upgrade compatible builder |

## 11. Operational runbooks

### A. Image optimization review
1. Record baseline image size, build time and layer history.
2. Review build context, lockfile, Dockerfile and base image.
3. Introduce multi-stage runtime and nonroot execution.
4. Rebuild on isolated builder; verify smoke and security options.
5. Compare actual metrics, scan results and SBOM.
6. Approve only after regression testing.

### B. Vulnerable base image
1. Capture affected registry digest and deployed workloads.
2. Review CVE severity, exploitability and fixed base availability.
3. Update to reviewed digest; rebuild from pinned source.
4. Rerun tests, smoke, scan and signature checks.
5. Promote new immutable digest and preserve rollback artifact.

### C. Image size regression
1. Compare Dockerfile, base digest, layers and build context.
2. Identify accidental dependency/artifact inclusion.
3. Restore ignore rules or stage boundaries.
4. Measure size and startup/pull time after correction.
5. Record regression threshold and prevention.

### D. Secret exposure
1. Quarantine image and pause release.
2. Revoke/rotate leaked secret immediately.
3. Audit image history, build logs, registry and cache.
4. Rebuild on clean isolated builder using secret mounts.
5. Verify no secret remains in published image or evidence.

### E. Rollback
1. Identify previous signed/approved image digest.
2. Verify registry availability, signature and policy.
3. Deploy previous digest through controlled rollout.
4. Confirm health/SLOs and preserve failed image evidence.
5. Open follow-up for root cause.

## 12. Acceptance criteria

- [ ] Dockerfile uses multi-stage build and nonroot runtime.
- [ ] Build context excludes sensitive files.
- [ ] Tests execute and image smoke passes.
- [ ] Read-only root filesystem and capability drop tested.
- [ ] Base digest pinning policy documented.
- [ ] Image sizes and build times measured.
- [ ] SBOM, scanner and signature policy reviewed.
- [ ] Fault injection and rollback evidenced.

**Companion:** [Chapter 042 hands-on lab](labs/042-dockerfile-optimization-multi-stage-builds-image-security-check.md).  
**Next:** Chapter 043 — Jenkins Container Registry Integration, Image Tagging and Promotion.
