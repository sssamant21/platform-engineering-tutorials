# Chapter 102 — Identity, Authentication and Authorization Executable Lab

[Python policy engine](identity_lab.py) · [Automated tests](test_identity_lab.py) · [Full lab](../102-identity-authentication-authorization-sre-dbre-lab.md)

## Run locally

Python 3.11+ standard library only; no network, credentials, cloud SDKs or JWT libraries.

```bash
cd python/11-production-security-performance/labs/102
python -m compileall -q identity_lab.py test_identity_lab.py
python -m unittest -v test_identity_lab.py
python identity_lab.py --dry-run
```

PowerShell: `py -3 -m unittest -v test_identity_lab.py`.

## Implemented

- Synthetic `VerifiedPrincipal` representing **already verified** OIDC/OAuth claims; no cryptographic token verification.
- Issuer, audience, expiry, not-before, role and scope checks on synthetic trusted data.
- Tenant-isolated RBAC and ABAC for production versus staging.
- Production deploy/failover approval bound to canonical SHA-256 request fingerprint, independent approver, expiry, ticket and rollback.
- Optional in-memory token-ID replay check for sensitive actions; **not durable or distributed**.
- Redacted audit output, no token material, zero cloud calls and zero mutations.

## Exercises

1. Reject expired, future, wrong-issuer and wrong-audience principals.
2. Compare OAuth access token vs OIDC ID token and why the lab cannot verify either.
3. Reject cross-tenant resource access and unrecognized roles.
4. Enforce action scopes independently of RBAC.
5. Require production approval and test staging behavior.
6. Reject self-approval, bad digest, expired approval and missing rollback evidence.
7. Demonstrate in-memory token-ID replay rejection.
8. Verify audit events omit raw subjects and bearer tokens.
9. Map AWS IAM, Azure Entra ID, GCP IAM and Kubernetes RBAC trust boundaries.
10. Write a PostgreSQL failover break-glass policy and incident runbook.

## Production extensions — NOT implemented

- Use a maintained OIDC/JWT library to verify signed JWTs with trusted JWKS, exact issuer/audience, allowed algorithms, `exp`, `nbf` and token type. Validate opaque access tokens through authorized introspection where appropriate.
- Support OIDC discovery and key rotation with issuer allowlists, bounded caches and network hardening.
- Use persistent, atomic, tenant-scoped replay storage for sensitive operations.
- Integrate AWS STS/EKS Pod Identity, Azure managed identities/Entra ID, GCP Workload Identity Federation and Kubernetes projected service-account tokens.
- Add authenticated approval services, policy versions, revocation/session strategy, rate limits, threat modeling and production audit retention.
- Perform independent security review and staging identity-provider integration tests.

## CI example (not enabled)

```yaml
name: chapter-102-identity-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/11-production-security-performance/labs/102
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q identity_lab.py test_identity_lab.py
      - run: python -m unittest -v test_identity_lab.py
```

Pin reviewed GitHub Actions SHAs before enabling. **Validation:** Test code is published, but execution of the exact committed revision, CI and live IdP/cloud integration are pending.
