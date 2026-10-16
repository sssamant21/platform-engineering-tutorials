# Chapter 042 — Hands-on Lab: Multi-Stage Dockerfiles and Image Security

**Environment:** Disposable Jenkins and isolated Linux Docker/BuildKit builder. Synthetic Node.js HTTP fixture, approved scanner tools if available. Do not use production credentials.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record Docker/BuildKit, Node/npm | Versions |
| 02 | Fixture | Commit server, test and package manifest | Git SHA |
| 03 | Lockfile | Generate and commit `package-lock.json` | Lock hash |
| 04 | Baseline | Build single-stage image | Image ID/size |
| 05 | Ignore rules | Add `.dockerignore` | Context inspection |
| 06 | Multi-stage | Build test + runtime stages | Build logs |
| 07 | Stage isolation | Inspect runtime contents | No test tools/source extras |
| 08 | Nonroot | Inspect image `Config.User` | User |
| 09 | Image size | Compare baseline/optimized bytes | Table |
| 10 | Layer review | Run `docker history` | Layer evidence |
| 11 | Runtime smoke | Curl `/healthz` | HTTP 200 |
| 12 | Read-only FS | Run with `--read-only` | Healthy |
| 13 | Capabilities | Run `--cap-drop=ALL` | Healthy |
| 14 | Jenkins Pipeline | Execute test/build/smoke | Build URL |
| 15 | Cache experiment | Compare cold/warm build | Duration |
| 16 | Base digest | Inspect approved base manifest | Digest |
| 17 | Vulnerability scan | Run approved scanner | Findings |
| 18 | SBOM | Generate approved SBOM | Artifact |
| 19 | Fault injection | Break COPY or lockfile | Fail-closed |
| 20 | Recovery | Restore Dockerfile, retest | Pass |

## 12 troubleshooting drills

1. Lockfile missing or inconsistent.
2. Multi-stage COPY references wrong stage.
3. Runtime image lacks required source.
4. Nonroot process cannot write.
5. Read-only filesystem breaks app.
6. Container health endpoint unreachable.
7. Build context unexpectedly huge.
8. Cache produces unexpected stale output.
9. Base image pull fails.
10. Vulnerability scanner blocks build.
11. Scanner database update fails.
12. Secret accidentally included in image context.

Record logs, source SHA, image ID, root cause, correction and retest for each. Mark unsupported scanners/signing steps blocked, never invent evidence.

## Executable fixture

`package.json`:
```json
{"name":"ch042-fixture","version":"1.0.0","private":true,"scripts":{"test":"node --test","start":"node server.js"}}
```

`server.js`:
```js
require('node:http').createServer((req, res) => {
  res.writeHead(req.url === '/healthz' ? 200 : 404);
  res.end(req.url === '/healthz' ? 'ok' : 'not found');
}).listen(8080, '0.0.0.0');
```

`server.test.js`:
```js
const test = require('node:test');
const assert = require('node:assert/strict');
test('smoke contract', () => assert.equal(2 + 2, 4));
```

`Dockerfile`:
```dockerfile
# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS test
WORKDIR /src
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --ignore-scripts
COPY server.js server.test.js ./
RUN npm test

FROM node:22-bookworm-slim AS runtime
WORKDIR /app
COPY --from=test --chown=node:node /src/server.js ./server.js
USER node
EXPOSE 8080
CMD ["node", "server.js"]
```

Run:

```sh
set -eu
npm install --package-lock-only --ignore-scripts
npm ci && npm test
docker build --pull -t ch042:lab .
docker run -d --name ch042-test --read-only --cap-drop=ALL \
  -p 127.0.0.1:18082:8080 ch042:lab
curl --fail --retry 10 --retry-delay 1 http://127.0.0.1:18082/healthz
docker image inspect ch042:lab --format '{{.Id}} {{.Size}} {{.Config.User}}'
docker rm -f ch042-test
```

For production replace the tagged base with a reviewed digest. If an exercise exits early, clean up the disposable test container after preserving logs.

## Evidence template

```text
UTC timestamp:
Git SHA / Jenkins build:
Docker/BuildKit version:
Base tag and approved digest:
Lockfile hash:
Baseline image size:
Optimized image size:
Build duration and cache behavior:
Runtime user and security options:
Smoke result:
SBOM and scan evidence:
Injected failure:
Root cause / recovery:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Multi-stage image builds successfully.
- [ ] Runtime is nonroot and smoke passes with read-only FS.
- [ ] Size/performance measurements recorded.
- [ ] Secret exclusion and base pinning reviewed.
- [ ] Vulnerability scan and SBOM produced where tools available.
- [ ] Recovery and reviewer approval documented.

**Related:** [Chapter 042 — Dockerfile Optimization, Multi-Stage Builds and Image Security](../042-dockerfile-optimization-multi-stage-builds-image-security.md).
