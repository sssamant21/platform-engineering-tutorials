# Chapter 102 — Python Identity, Authentication and Authorization for Production Systems

**Part 11 — Production Security and Performance | Chapter 102/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/102-identity-authentication-authorization-sre-dbre-lab.md) · [Executable offline project](labs/102/README.md)

## Objectives

Design production-grade authentication, authorization and identity federation for Python services. Explain OAuth 2.0, OpenID Connect (OIDC), JSON Web Tokens (JWT), role-based and attribute-based access control (RBAC/ABAC), Kubernetes service accounts, AWS IAM, Microsoft Entra ID/Azure managed identity and Google Cloud Workload Identity Federation. Build a **safe offline policy simulator** with denial-by-default, tenant isolation, expiry, replay detection and audit logs.

## Architecture

```text
Human / workload
      |
Identity Provider (OIDC / IAM federation)
      |
OAuth authorization / token issuance
      |
API gateway -> TLS -> JWT signature + iss/aud/exp/nbf verification
      |
Principal (subject, tenant, roles, scopes, auth context)
      |
RBAC + ABAC + resource ownership / environment
      |
Scoped service / database action
      |
Structured audit -> SIEM, SLO, incident investigation
```

The runnable lab models the **post-verification authorization decision**. It does not issue or cryptographically verify JWTs, contact an identity provider, mint cloud credentials, or access production resources.

## 1. Authentication versus authorization

Authentication establishes who a principal is; authorization determines what that principal may do on a specific object. Identity proof is not permission. Enforce authorization at every service boundary and every object access (including object-level and tenant-level checks); do not rely only on API gateway filtering or a UI role.

A production principal should carry a stable subject, trusted tenant identifier, role assignments, approved scopes, authentication strength, expiry and token identifier. Never trust user-controlled HTTP headers to establish tenant or roles.

## 2. OAuth 2.0

OAuth 2.0 delegates access to resources using scoped access tokens. For interactive browser/mobile applications, prefer authorization code flow with PKCE and a properly validated redirect URI. Confidential backend clients use appropriate client authentication. Machine-to-machine workflows can use client credentials where supported. Avoid implicit grant and resource owner password credentials. Distinguish authorization server, client, resource server and resource owner.

Use narrowly scoped tokens, least privilege, short lifetimes, refresh-token rotation/reuse detection where applicable, and TLS. OAuth access tokens are not necessarily JWTs: they can be opaque and require introspection.

## 3. OpenID Connect

OIDC adds an identity layer, including an ID token intended for the client. Verify issuer, audience, nonce when required, expiration and cryptographic signature. **Do not send ID tokens as API access tokens** unless an explicitly designed protocol requires it. Fetch issuer metadata and signing keys from trusted endpoints; pin the issuer and allowed algorithms.

## 4. JWT validation

Production JWT verification must use a maintained library and a trusted JWKS endpoint, never a home-grown cryptographic parser. Enforce signature verification with an allowlisted asymmetric algorithm, exact issuer, audience, `exp`, `nbf`, expected token type and `kid` key selection. Do not accept `alg=none`, algorithm confusion, untrusted `jku` URLs, unsigned payloads or tokens for another service. Handle clock skew narrowly, rotate keys and cache JWKS with bounded TTL. Validate revocation/session state where required; signature validity alone does not prove authorization.

**Offline exercise:** the simulator consumes a synthetic `VerifiedPrincipal` object that represents claims already verified by an upstream trusted verifier. It is **not** a JWT verification implementation.

## 5. RBAC and ABAC

RBAC maps roles to actions; ABAC adds trusted context such as tenant, environment, resource ownership, sensitivity and change-ticket state. Combine both for sensitive operations: role permission AND tenant match AND scope AND environmental policy. Separate operator from approver. Default deny on missing attributes. Keep permission checks centralized, versioned and tested against privilege escalation.

For DBRE, read-only observability can be broadly delegated while credential rotation, PostgreSQL failover, Elasticsearch index deletion and Kubernetes deployment changes require additional approvals and blast-radius constraints.

## 6. AWS, Azure, GCP and Kubernetes workload identity

**AWS:** IAM roles and STS temporary credentials, EKS Pod Identity or IAM Roles for Service Accounts. Validate trust policies, OIDC audience/subject constraints, cross-account roles and CloudTrail attribution. Avoid permanent access keys.

**Azure:** Microsoft Entra ID managed identities and federated workload credentials. Restrict federated subject/issuer/audience, subscription and Azure RBAC scope. Verify that a token is intended for the requested resource, not merely issued by a trusted tenant.

**GCP:** Workload Identity Federation / Workload Identity for GKE, service-account impersonation only where necessary, IAM Conditions and audit logs. Avoid service-account JSON keys.

**Kubernetes:** namespace-scoped service accounts, projected bounded-audience tokens, explicit RBAC, workload isolation and admission policy. Do not mount service-account tokens unnecessarily. A Kubernetes token is not a cloud token without a properly configured federation exchange.

## 7. Threat model

| Threat | Mitigation |
|---|---|
| JWT algorithm confusion | Trusted verification library, algorithm allowlist |
| Token replay | Short expiry, token ID tracking for sensitive actions, sender constraints where supported |
| Cross-tenant IDOR/BOLA | Object-level tenant/owner authorization |
| Privilege escalation | Deny-by-default RBAC/ABAC and independent approval |
| Cloud credential leak | Federation, short-lived credentials, secret redaction |
| Confused deputy | Audience, scope and resource-bound policy |
| JWKS/key rotation outage | Controlled cache, issuer validation, operational runbook |
| Stale permissions | Token TTL, revocation strategy and entitlement synchronization |
| Misconfigured Kubernetes RBAC | Least privilege and namespace restrictions |
| Token in logs | Redaction and incident rotation/revocation |

## 8. Audit, retries and incident response

Log decision, subject pseudonym, tenant, action, resource, policy version, trace ID and reason code; **never log bearer tokens, secrets or full sensitive claims**. Distinguish authentication failure (401) from authorization denial (403). Do not blindly retry 401/403. Monitor token verification latency, failed authorizations, denied privileged operations and identity-provider availability. Preserve forensic evidence under retention and privacy policy.

## 9. Production security runbooks

**Token verification failure:** inspect issuer, audience, allowed algorithm, JWKS rotation, clock skew and expected token type; do not disable signature validation.

**Cross-tenant access attempt:** deny, preserve audit evidence, assess scope and check all object-level access paths.

**Compromised workload identity:** contain, revoke sessions where supported, rotate trust/credentials, audit API actions and re-establish least privilege.

**Authorization outage:** validate policy deployment, attribute completeness, identity provider and entitlement sync; fail closed for privileged actions.

**DBRE break-glass:** use a time-limited, separately approved, audited process with post-incident review; never embed permanent admin credentials.

## 10. Hands-on lab

The [complete lab](labs/102-identity-authentication-authorization-sre-dbre-lab.md) and [Python project](labs/102/README.md) implement synthetic principal expiry, issuer/audience expectations, tenant isolation, RBAC/ABAC, scoped resources, sensitive-action approvals, replay checks and redacted audit decisions. The project includes automated tests, incident drills and a 100-point assessment.

**Validation boundary:** This is an offline policy simulator, **not** a JWT cryptographic verifier or cloud IAM integration. GitHub CI, live identity-provider tests and production security review remain pending.

**Next proposed:** Chapter 103 — Python Secrets Management, Encryption and Key Lifecycle Automation.
