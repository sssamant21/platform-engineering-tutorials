# Chapter 041 — Hands-on Lab: Docker Fundamentals and Jenkins Image Pipelines

**Environment:** Disposable Jenkins controller, isolated Docker-capable Linux agent, nonproduction container registry, synthetic Python HTTP service.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Builder inventory | Record Docker client/server/BuildKit | Versions |
| 02 | Trust boundary | Diagram daemon and agent access | Security review |
| 03 | Fixture | Commit Python app/test | Source SHA |
| 04 | Dockerfile | Create nonroot Python image | Dockerfile |
| 05 | Ignore rules | Create `.dockerignore` | Context review |
| 06 | Unit tests | Run unittest | Test result |
| 07 | Build | Run `docker build --pull` | Build logs |
| 08 | Image ID | Inspect local image | Image ID |
| 09 | Layer review | Run `docker history` | Layer summary |
| 10 | Image size | Run `docker image inspect` | Bytes |
| 11 | Nonroot | Inspect image `Config.User` | UID |
| 12 | Smoke | Start container on loopback | HTTP 200 |
| 13 | Logs | Capture container logs | Log evidence |
| 14 | Jenkinsfile | Run test/build/smoke stages | Build URL |
| 15 | Failure injection | Break Dockerfile COPY | Pipeline fails |
| 16 | Registry auth | Configure scoped test credential | Credential ID |
| 17 | Test push | Publish unique version in private registry | Registry digest |
| 18 | Pull verify | Pull digest into clean builder | Matching manifest |
| 19 | Rollback | Retrieve previous known-good digest | Recovery |
| 20 | Review | Audit secret exposure, retention and access | Acceptance |

## 12 troubleshooting drills

1. Docker daemon unavailable.
2. Agent socket permission denied.
3. Oversized build context.
4. Dockerfile `COPY` path mismatch.
5. Base image pull throttled.
6. Build fails due to missing dependencies.
7. Runtime process exits unexpectedly.
8. Smoke test connection refused.
9. Port collision.
10. Registry push unauthorized.
11. Registry certificate failure.
12. Builder disk full.

For each drill record symptom, Docker/Jenkins logs, root cause, remediation and retest. Use controlled fault injection only on disposable infrastructure.

## Executable fixture

`app.py`:
```python
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200 if self.path == "/healthz" else 404)
        self.end_headers()
        if self.path == "/healthz":
            self.wfile.write(b"ok")

HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
```

`Dockerfile`:
```dockerfile
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
.env
.venv
__pycache__
*.pyc
```

Run:

```sh
set -eu
docker build -t jenkins-ch041:lab .
docker run -d --name ch041-test -p 127.0.0.1:18080:8080 jenkins-ch041:lab
curl --fail --retry 8 --retry-delay 1 http://127.0.0.1:18080/healthz
docker image inspect jenkins-ch041:lab --format '{{.Id}} {{.Config.User}}'
docker rm -f ch041-test
```

If the port is occupied, choose a free loopback port. Record the image digest **after registry push**, not merely the local image ID.

## Evidence template

```text
UTC timestamp:
Git SHA and Jenkins build:
Docker Engine/BuildKit versions:
Builder host and agent label:
Base image tag and approved digest:
Dockerfile hash:
Local image ID:
Registry tag and manifest digest:
Smoke HTTP response:
Nonroot runtime identity:
Vulnerability/SBOM evidence:
Injected failure:
Root cause and recovery:
Rollback digest:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Fixture builds and responds on `/healthz`.
- [ ] Runtime user is nonroot.
- [ ] Build context excludes secrets.
- [ ] Jenkins test/build/smoke pipeline succeeds.
- [ ] Registry publish uses trusted scoped identity.
- [ ] Digest and rollback evidence preserved.
- [ ] No production secrets or privileged untrusted builds used.

**Related:** [Chapter 041 — Docker Fundamentals and Jenkins Container Build Pipelines](../041-docker-fundamentals-jenkins-container-build-pipelines.md).
