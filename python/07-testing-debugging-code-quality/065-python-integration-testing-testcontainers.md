# Chapter 065 — Python Integration Testing and Testcontainers

**Part 07 — Testing, Debugging and Code Quality | Python 3.11+ | 8–10 hours**

## Objectives
Build reproducible integration tests with pytest, disposable PostgreSQL and Redis containers, readiness checks, transactional isolation, teardown, safe CI, negative-path tests and production runbooks.

## 1. Integration tests versus unit tests
Unit tests validate pure logic and use in-memory fakes. Integration tests validate real drivers, SQL semantics, Redis TTL behavior, transaction boundaries and network connectivity. Integration tests should run against **disposable** resources only. Containerized testing does not prove compatibility with every production version, configuration or managed-service feature.

## 2. Architecture
\`\`\`text
pytest session
  |-- explicit CH065_RUN_CONTAINERS + CH065_ALLOW_DOCKER opt-in
  |-- Testcontainers PostgreSQL (isolated ephemeral container)
  |      |-- psycopg driver + telemetry_events table
  |      |-- truncate disposable table before each test
  |-- Testcontainers Redis (isolated ephemeral container)
  |      |-- redis-py + PING readiness
  |      |-- unique per-test key namespace + TTL + scoped cleanup
  |-- TelemetryService with Store and Cache protocols
         |-- PostgreSQL authoritative idempotent INSERT ... ON CONFLICT
         |-- Redis best-effort derived cache
         |-- strict synthetic input validation
\`\`\`

## 3. Testcontainers lifecycle
Testcontainers starts real containers using Docker and typically waits for startup readiness. Its fixtures use context managers and \`yield\` so containers are stopped during teardown. Containers require a functioning Docker daemon, available images, host networking and permissions. Image pulls may require internet access. Use approved pinned image digests and restricted registries in production CI. Do not run Docker socket mounts in untrusted pull-request jobs.

## 4. PostgreSQL readiness and transaction boundaries
The PostgreSQL fixture connects only after Testcontainers startup, creates a small table, and uses a fresh test fixture per test. The table is truncated **only inside the disposable container**. \`INSERT ... ON CONFLICT DO NOTHING RETURNING\` verifies idempotent persistence. \`commit()\` makes inserted rows visible for later queries. A real system must handle transaction failures with rollback and avoid reusing failed connections.

## 5. Redis readiness, isolation and cleanup
Redis \`PING\` verifies client connectivity. Every test uses a unique key prefix and deletes only keys it created. Never use \`FLUSHDB\` or \`FLUSHALL\` in a test harness that might accidentally connect to a shared service. The Redis cache uses TTL and is explicitly non-authoritative: cache failure does not invalidate a successful PostgreSQL write.

## 6. Safety and security
Require two explicit opt-in environment variables for container tests. Use synthetic data and local disposable resources. Never pass production credentials or hostnames into these fixtures. In CI, use isolated runners with limited Docker permissions, no production network route, reviewed dependencies and strict execution timeouts. Cleanup must be scoped; verify no containers or volumes remain after runs.

## 7. Environment and dependencies
Use Python 3.11+, pytest, testcontainers, psycopg and redis-py. Pin exact dependency versions and image digests in a reviewed lockfile for a real project. The lab includes example compatibility ranges rather than falsely claiming a validated lockfile.

## 8. CI integration
Recommended jobs: always-on offline unit tests, opt-in container integration tests on trusted branches, vulnerability scanning, logs/artifacts without secrets, and a manual production promotion gate. Do not run untrusted code with unrestricted Docker access.

## 9. Failure modes
| Symptom | Cause | Recovery |
|---|---|---|
| Docker unavailable | Daemon stopped or permissions | Start daemon; verify trusted runner |
| Image pull fails | Registry/network issue | Use approved cached/pinned images |
| PostgreSQL connect fails | Readiness or driver mismatch | Inspect container logs and DSN |
| Redis PING fails | Startup or port mapping | Inspect mapped port and readiness |
| Test contamination | Shared table or key prefix | Per-test cleanup and unique namespace |
| Leaked containers | Aborted teardown | Inspect owned resources and remove safely |
| Duplicate records | Missing unique key | Verify primary key and ON CONFLICT |
| False green test | Cache mock hides real driver failure | Maintain real Redis integration tests |
| Production data risk | Wrong DSN or cleanup scope | Block live credentials and destructive commands |

## 10. Production runbooks
**Integration suite failure:** capture sanitized container logs, verify image/driver versions, isolate failing test and block release.

**Docker runner outage:** verify daemon, registry and network, rerun only on trusted isolated infrastructure.

**PostgreSQL contamination:** stop suite, verify disposable DSN, reset only owned container and rerun.

**Redis leak:** inspect namespace and TTL, delete only owned keys, verify no shared keys were touched.

**Rollback:** restore prior adapter, fixtures and image pins; rerun unit/integration gates and document acceptance.

## 11. Lab
[Chapter 065 — Integration Testing with Testcontainers SRE/DBRE Lab](labs/065-integration-testing-testcontainers-sre-dbre-lab.md) contains complete application code, offline unit tests, real disposable PostgreSQL and Redis tests, CI workflow, failure simulations and a 100-point assessment.

**Next:** Chapter 066 — Python Debugging, Profiling and Diagnostics (provisional).
