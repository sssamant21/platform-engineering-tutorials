# Chapter 101 — Production Security and Secure Coding Executable Project

[Python implementation](secure_ops.py) · [Automated regression tests](test_secure_ops.py) · [Full lab](../101-production-security-secure-coding-sre-dbre-lab.md)

## Run offline

Python 3.11+ standard library only. No cloud credentials, network calls, secret retrieval or production changes.

```bash
cd python/11-production-security-performance/labs/101
python -m compileall -q secure_ops.py test_secure_ops.py
python -m unittest -v test_secure_ops.py
python secure_ops.py --dry-run
```

Windows PowerShell: `py -3 -m unittest -v test_secure_ops.py`.

## What the lab implements

- Strict allowlisted request schema, service/environment identifiers and integer bounds.
- Small deny-by-default authorization matrix over a **synthetic already-authenticated principal**.
- Lexical path guards and public IP literal checks as teaching aids. Neither is a complete filesystem race/SSRF mitigation.
- Recursive key-based secret redaction; does not detect secrets embedded in arbitrary text.
- SHA-256 integrity comparison against a trusted expected digest; no package authenticity claim.
- Pinned dependency metadata validation, without a vulnerability scan or real package installation.
- Structured allow/deny audit event generation.
- Canonical advisory plan fingerprint and simulated separate approver, expiry and rollback checks.
- Zero network calls, zero secret reads and zero writes, even with simulated approval.

## Exercises

1. Attempt unknown fields and boolean `limit=True`; verify fail-closed validation.
2. Test missing service, malformed IDs and oversized limit.
3. Compare viewer and auditor permissions and production vs staging scope.
4. Reject path traversal and link-local cloud metadata IP.
5. Verify nested redaction and explain why key-based redaction is insufficient by itself.
6. Compare correct vs incorrect package digest.
7. Reject unpinned dependency metadata.
8. Generate audit events without sensitive data.
9. Attempt `delete` plan, expired approval, self-approval, bad digest and missing rollback.
10. Verify no mutation or secret retrieval code exists.
11. Design a secure PostgreSQL administrative API and its object-level access controls.
12. Draft an incident response plan for compromised CI credentials.

## Production extension acceptance gates

Add real OIDC/JWT verification through a maintained library; tenant-scoped authorization; parameterized database access; directory-descriptor filesystem protection; egress proxy/network policy with DNS and redirect handling; vault integrations; dependency scanning, SBOM/provenance and signed artifacts; structured audit sink; integration tests and threat-model sign-off. None is implemented by this offline simulator.

## Example CI workflow (not enabled)

```yaml
name: chapter-101-secure-coding-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/11-production-security-performance/labs/101
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q secure_ops.py test_secure_ops.py
      - run: python -m unittest -v test_secure_ops.py
```

Pin reviewed GitHub Actions SHAs before enabling. **Validation:** Source and tests committed; CI and execution of the exact committed files are pending.
