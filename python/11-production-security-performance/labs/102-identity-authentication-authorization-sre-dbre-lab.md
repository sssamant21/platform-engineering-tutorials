# Chapter 102 — Identity, Authentication and Authorization SRE/DBRE Lab

[Executable project](102/README.md) · [Python source](102/identity_lab.py) · [Automated tests](102/test_identity_lab.py)

## Mission

Build a safe, offline authorization boundary for a multi-tenant production platform managing Kubernetes deployments and PostgreSQL databases. Model OAuth/OIDC identity and JWT validation requirements, then implement deny-by-default RBAC/ABAC, least privilege, approval, replay detection and audit without issuing tokens or changing resources.

```text
Trusted upstream OIDC/JWT verifier (design only)
                |
      Synthetic VerifiedPrincipal
                |
       issuer/audience/time validation
                |
       tenant + RBAC + action scope
                |
        production approval gate
                |
     redacted audit + advisory decision
                |
           zero cloud writes
```

## Lab 1 — Run

```bash
cd python/11-production-security-performance/labs/102
python -m compileall -q identity_lab.py test_identity_lab.py
python -m unittest -v test_identity_lab.py
python identity_lab.py --dry-run
```

## Lab 2 — OAuth 2.0 and OIDC

Draw the authorization code + PKCE flow. Explain authorization server, resource server, client, access token, refresh token and ID token. Verify the difference between an OAuth access token and an OIDC ID token. Design a trusted JWT verification boundary with signature/JWKS/issuer/audience/expiry checks. **Do not treat the synthetic principal constructor as a real token verifier.**

## Lab 3 — RBAC and ABAC

Inspect the role matrix (viewer, operator, dbre, security). Test role permission, action scope and resource tenant independently. Deny cross-tenant object access even when role and scope match. Require a change ticket, separate approver, expiry and rollback evidence for production deployment and database failover.

## Lab 4 — AWS/Azure/GCP/Kubernetes identity

Design trust-policy and audience/subject checks for AWS STS and EKS Pod Identity/IRSA; Azure managed identity/Entra ID federation; GCP Workload Identity Federation; Kubernetes projected service-account tokens and RBAC. Identify where workload credentials are minted and how cloud principal attribution is audited.

## Lab 5 — Audit and replay

Hash the subject for sample audit output; never log bearer tokens. Exercise token-ID replay detection with an in-memory set. Explain why a real service needs atomic, distributed, expiring replay storage and authenticated approval provenance.

## Production incident simulations

| # | Scenario | Expected behavior | Mode |
|---|---|---|---|
| 1 | Valid synthetic principal | Accept identity fields | Automated |
| 2 | Expired token | Reject | Automated |
| 3 | Token not yet valid | Reject | Automated |
| 4 | Wrong issuer | Reject | Automated |
| 5 | Wrong audience | Reject | Automated |
| 6 | Malformed subject | Reject | Automated |
| 7 | Unknown role | Reject | Automated |
| 8 | Invalid scope | Reject | Automated |
| 9 | Invalid resource | Reject | Automated |
| 10 | Unsupported action | Reject | Automated |
| 11 | Cross-tenant object access | Deny | Automated |
| 12 | Viewer attempts deploy | Deny | Automated |
| 13 | Missing action scope | Deny | Automated |
| 14 | Production approval missing | Hold | Automated |
| 15 | Valid simulated independent approval | Advisory allow | Automated |
| 16 | Wrong approval fingerprint | Hold | Automated |
| 17 | Self-approval | Hold | Automated |
| 18 | Expired approval | Hold | Automated |
| 19 | Rollback not tested | Hold | Automated |
| 20 | Staging action | Role/scope allow | Automated |
| 21 | Read-only request | Allow | Automated |
| 22 | Repeated token ID | Reject replay | Automated |
| 23 | Raw subject in audit | Redact/hash | Automated |
| 24 | Unauthorized mutation | Zero writes | Automated |
| 25 | AWS OIDC trust mismatch | Review role trust and audience | Guided |
| 26 | Azure Entra ID 401/403 | Check token resource, tenant, RBAC | Guided |
| 27 | GCP Workload Identity denial | Check pool/provider/IAM binding | Guided |
| 28 | Kubernetes RBAC forbidden | Check service account/namespace | Guided |
| 29 | JWKS key rotation | Verify issuer/key cache and TTL | Guided |
| 30 | Cross-tenant BOLA exploit | Contain and audit object checks | Guided |
| 31 | PostgreSQL unauthorized failover | Enforce DBRE break-glass | Guided |
| 32 | Elasticsearch privileged token leak | Revoke scoped token and investigate | Guided |
| 33 | OAuth token replay | Revoke/contain and validate sender | Guided |
| 34 | IdP outage | Fail closed on privileged actions | Guided |

## Troubleshooting and operational runbooks

**JWT rejection:** inspect exact issuer, audience, signing algorithm, JWKS cache, token type and clock skew. Never disable signature verification to restore service.

**Cross-tenant authorization:** block access, inspect object-level policies, preserve audit evidence and test other endpoints for BOLA.

**Workload identity failure:** verify federation trust, projected token audience, IAM bindings and cloud principal identity. Avoid static key fallback.

**DBRE privileged change:** validate incident ticket, independent approver, expiration, resource scope, backups, rollback and post-change SLO.

**Token leak/replay:** contain credentials, revoke where supported, review logs, reduce token lifetime and restore verified access.

## Final 100-point assessment

| Competency | Points |
|---|---:|
| OAuth 2.0, OIDC and JWT verification design | 20 |
| RBAC/ABAC and tenant isolation | 20 |
| AWS/Azure/GCP/Kubernetes workload identity | 20 |
| Approval, replay and least privilege | 15 |
| Incident response, audit and runbooks | 15 |
| Automated tests and security acceptance | 10 |
| **Total** | **100** |

**Pass:** ≥90/100, offline test execution, zero-write evidence and independent security review of production integration design.

**Validation:** Offline tests are published. Real JWT verification, identity-provider integrations, CI and execution of the exact committed code are pending.
