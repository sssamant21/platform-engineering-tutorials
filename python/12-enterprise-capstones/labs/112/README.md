# Chapter 112 — Enterprise Python API Services and Data Access Lab

[Offline API simulator](api_lab.py) · [Automated unit tests](test_api_lab.py) · [Full SRE/DBRE lab](../112-enterprise-python-api-contracts-data-access-sre-dbre-lab.md)

## Run

Python 3.11+ standard library only. No packages, listening sockets, cloud credentials, databases, network calls or production writes.

```bash
cd python/12-enterprise-capstones/labs/112
python -m compileall -q api_lab.py test_api_lab.py
python -m unittest -v test_api_lab.py
python api_lab.py --dry-run
```

PowerShell: `py -3 -m unittest -v test_api_lab.py`.

## Implemented

- Simulated REST handlers for `POST /v1/records`, `GET /v1/records/{id}`, `GET /v1/search`.
- Exact-field request validation, type/length checks and stable HTTP-style error envelopes.
- Simplified reader/writer role gate (**not real authentication**).
- POST idempotency key and request fingerprint conflict handling.
- `MemoryPostgres`: bounded connection pool, revision-based optimistic concurrency and in-memory storage.
- `MemorySearch`: bounded search projection and query.
- `MemoryMongo`: constrained JSON document storage.
- `MemoryRedis`: deterministic TTL and defensive copies.
- Timeout budget validator, request/error counters and sample p99.
- Zero live connections, mutations, OTel exporters or deployed infrastructure.

## Labs

1. Create, read and search a record.
2. Verify unauthorized writes fail.
3. Reject malformed IDs, unexpected fields and invalid revisions.
4. Exercise idempotency replay and key-reuse conflicts.
5. Verify optimistic revision conflicts and pool release after errors.
6. Simulate connection exhaustion.
7. Validate bounded search query limits.
8. Store and validate MongoDB-style documents.
9. Test Redis TTL expiry and cache isolation.
10. Verify nested timeouts fit total deadlines.
11. Inspect synthetic request metrics and 5xx counts.
12. Design live integration contracts, OTel spans, rollback and database runbooks.

## CI template (not enabled)

```yaml
name: chapter-112-api-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/12-enterprise-capstones/labs/112
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q api_lab.py test_api_lab.py
      - run: python -m unittest -v test_api_lab.py
```

Pin reviewed GitHub Action SHAs before enabling. The CI workflow is an example only.

**Production extension:** Add a reviewed API framework, OpenAPI schemas, OIDC/JWT verification, tenant isolation, real drivers, TLS, migrations, transactional outbox, distributed cache invalidation, OTel and integration/load/security tests in an approved staging environment.

**Validation:** Tests published; exact committed execution, CI, live integrations and production acceptance pending.
