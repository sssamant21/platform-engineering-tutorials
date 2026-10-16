# Chapter 058 — Jenkins Enterprise SSO, LDAP, SAML and OIDC Integration

**Part 12 — Security, RBAC, SSO, Credentials and Secrets**  
**Audience:** Jenkins administrators, IAM, SRE, security engineering and incident responders  
**Prerequisites:** Chapters 056–057; isolated Jenkins LTS, protected administrator recovery, a test identity provider and verified controller backup.

## Learning outcomes

Select and operate an enterprise identity architecture for Jenkins; integrate LDAP, SAML or OIDC through supported plugins; enforce IdP-managed MFA, map groups to least-privilege authorization, validate session and logout behavior, troubleshoot federation failures and recover from outages without disabling security.

## 1. Identity and authorization architecture

```text
User → browser → TLS ingress → Jenkins
                                │
                     Security realm plugin
                     ├─ LDAP directory
                     ├─ SAML IdP
                     └─ OIDC IdP
                                │
                     Authenticated principal
                                ↓
                     Jenkins authorization
                     (Role Strategy / Matrix)
                                ↓
                     Folder/job permissions
```

Configure **one Jenkins security realm** at a time. Authentication identifies a user; Jenkins authorization decides access. IdP MFA is not automatically provided by every Jenkins realm. Confirm MFA policy at the IdP, including break-glass exceptions.

## 2. Protocol comparison

| Method | Integration | Strength | Main risks |
|---|---|---|---|
| LDAP/LDAPS | Directory bind/search | Mature enterprise directory integration | Bind account exposure, group search complexity |
| SAML 2.0 | Browser assertions | Enterprise federation and IdP MFA | ACS/EntityID mismatch, certificates, clock skew |
| OIDC | OAuth 2.0-based identity tokens | Modern claims and IdP federation | Issuer/audience/redirect/claim mapping errors |

Use only maintained plugins compatible with the deployed Jenkins core. LDAP alone is not a browser SSO protocol; it typically authenticates against a directory and may not provide the same IdP session experience as SAML/OIDC.

## 3. Preflight checklist

- Current supported Jenkins LTS, Java runtime and security plugins.
- Verified backup of Jenkins home, secrets/master key material and JCasC.
- Restricted emergency administrator recovery path, documented and monitored.
- Accurate Jenkins root URL, HTTPS and reverse-proxy headers.
- NTP/time synchronization on controller and IdP.
- IdP test tenant, test users, test groups and negative-test user.
- Approved issuer/metadata URL, client identifier, callback/ACS URL and certificate rotation plan.
- Network/DNS/firewall path to IdP and directory.
- Least-privilege authorization matrix from Chapter 057.
- Change window, rollback plan, monitoring and audit ownership.

## 4. LDAP/LDAPS integration

Typical settings: server URI, root DN, user search base/filter, group search strategy, manager/bind DN and credential, TLS truststore, connection timeout and cache behavior. Prefer LDAPS or STARTTLS with certificate verification and dedicated read-only bind identity.

**Example directory layout (illustrative):**

```text
dc=example,dc=test
├── ou=people
│   ├── uid=jenkins-user
│   └── uid=jenkins-admin
└── ou=groups
    ├── cn=jenkins-developers
    └── cn=jenkins-release-operators
```

Do not commit LDAP bind passwords. Test disabled accounts, nested groups, group membership changes, referral handling and directory failover. Avoid overly broad searches and insecure anonymous bind.

## 5. SAML 2.0 integration

Typical Jenkins SAML plugin configuration includes IdP metadata, Service Provider Entity ID, Assertion Consumer Service (ACS) URL, signed assertions/responses, NameID/user attributes, group attribute and session lifetime. Use signed metadata or a verified trusted channel for certificate changes.

```text
Browser → Jenkins login
  → redirect to IdP
  → IdP authenticates user + MFA
  → signed SAML response to Jenkins ACS
  → signature, audience, recipient, timing validation
  → Jenkins principal and groups
  → authorization check
```

**Failure modes:** incorrect Entity ID, ACS URL, reverse-proxy host, signing certificate rollover, invalid audience, expired assertion, clock skew and missing group attribute. Never disable signature validation to troubleshoot production login.

## 6. OIDC integration

A supported OIDC plugin typically needs issuer/discovery URL, client ID, client secret or approved confidential-client mechanism, redirect URI, scopes (`openid`, often `profile`/`email`), username claim and group claim mapping.

```text
Browser → Jenkins
  → IdP authorization endpoint
  → authorization code returned to Jenkins redirect URI
  → back-channel token exchange
  → ID token issuer/audience/signature/nonce validation
  → Jenkins principal and groups
  → authorization check
```

Prefer Authorization Code flow with PKCE where the chosen plugin supports it. Do not use implicit flow or accept tokens without proper issuer, audience and signature validation. Token claim names and group overage handling vary by IdP.

## 7. Example OIDC claim mapping

Illustrative **decoded claims** for lab inspection only; never paste actual identity tokens into tickets or logs:

```json
{
  "iss": "https://idp.example.test/tenant",
  "aud": "jenkins-lab-client",
  "sub": "stable-user-id",
  "preferred_username": "jenkins.user@example.test",
  "groups": ["jenkins-developers"]
}
```

Use a stable unique user identifier for Jenkins account mapping; email/username can change or collide. Confirm the chosen plugin's user ID claim behavior before migration. Group claims may be absent or truncated; absence must not grant elevated privileges.

## 8. Group-to-role mapping

| IdP group | Jenkins role | Scope |
|---|---|---|
| jenkins-platform-admins | Admin | Controller |
| jenkins-security-auditors | Read-only audit | Approved folders |
| jenkins-team-a | Developer/build | engineering/team-a |
| jenkins-staging-release | Release operator | releases/staging |
| jenkins-prod-release | Restricted operator | releases/production |

Validate both allowed and denied actions with real test users. Avoid defaulting all authenticated users to Job/Configure, Credentials/Manage or Overall/Administer.

## 9. Reverse proxy and callback validation

```sh
curl -sSIk https://jenkins.example.test/login
date -u
```

Check Jenkins root URL, trusted forwarded headers, cookie Secure/SameSite behavior, HTTPS redirects, external hostname, ingress authentication layering and time sync. Do not blindly trust client-supplied `X-Forwarded-User` or `X-Forwarded-Proto`; only trusted proxies should set security-relevant headers.

## 10. Session lifecycle and logout

Test IdP session timeout, Jenkins session timeout, browser logout, SSO logout expectations, disabled user behavior, password/credential rotation, group membership revocation and emergency access. SAML/OIDC single logout support depends on plugins and IdP; do not assume Jenkins logout terminates the IdP session. Document revocation latency and reauthentication behavior.

## 11. Safe rollout sequence

1. Capture backup and existing realm/authorization configuration.
2. Build isolated Jenkins clone with synthetic accounts and no production secrets.
3. Configure IdP test application and callback URL.
4. Validate successful login, group mapping and MFA.
5. Run negative tests: disabled user, missing group, wrong audience, expired assertion/token.
6. Validate administrator recovery and rollback to prior realm.
7. Deploy through approved change window, monitor login success and support tickets.
8. Retain audit evidence and follow-up access review.

## 12. Troubleshooting matrix

| Symptom | Investigation | Safe remediation |
|---|---|---|
| Redirect loop | Root URL, proxy, cookies | Fix trusted proxy/URL |
| SAML invalid audience | Entity ID/ACS | Correct IdP/SP settings |
| SAML signature error | Metadata/cert rollover | Update trusted signing cert |
| SAML assertion expired | NTP, IdP session | Restore time sync |
| OIDC invalid issuer | Discovery/tenant | Fix issuer |
| OIDC invalid audience | Client ID/token type | Correct client registration |
| OIDC nonce/state error | Session/cookies/redirect | Fix flow/proxy |
| OIDC groups missing | Scope/claim/overage | Fix claim mapping |
| LDAP bind fails | Bind DN/password/TLS | Rotate/fix bind identity |
| LDAP group lookup slow | Search scope/index | Optimize query |
| Disabled user still active | Session/cache | Revoke session and validate |
| Developer gets admin | Group-to-role inheritance | Revoke role/audit |
| IdP unavailable | Network/DNS/IdP health | Follow fail-safe recovery |
| JCasC realm invalid | Plugin schema | Restore validated config |
| MFA not enforced | IdP conditional access | Correct policy |
| SSO logout unexpected | Session semantics | Document/test logout |

## 13. Production runbooks

### A. New SSO integration
1. Approve protocol/plugin and threat model.
2. Prepare test tenant and Jenkins clone.
3. Validate callback, TLS, claims and group mapping.
4. Test MFA and negative authorization cases.
5. Deploy with rollback and monitor login metrics.

### B. SSO outage
1. Distinguish IdP, DNS/TLS, proxy and Jenkins plugin failure.
2. Preserve logs without exposing assertions/tokens.
3. Confirm clock/cert/issuer and endpoint reachability.
4. Use approved emergency recovery, **not** security disablement.
5. Restore login and complete RCA.

### C. Certificate/secret rotation
1. Identify IdP metadata/signing certificate or OIDC client secret expiry.
2. Stage new trust material and test overlap/rotation.
3. Update secret store and plugin configuration.
4. Verify positive/negative authentication.
5. Revoke old material and document audit.

### D. Unauthorized group elevation
1. Capture principal, group claim and role mapping.
2. Revoke inappropriate IdP group/Jenkins grant.
3. Review actions performed during access window.
4. Correct claim mapping and negative tests.
5. Record incident and preventive controls.

### E. Migration rollback
1. Halt further realm changes.
2. Restore known-good realm/JCasC from verified backup.
3. Verify admin and developer access separately.
4. Confirm secrets and authorization state remain intact.
5. Record recovery time and lessons learned.

## 14. Acceptance criteria

- [ ] Chosen protocol and supported plugin documented.
- [ ] HTTPS, proxy and callback/ACS settings verified.
- [ ] IdP MFA enforced for appropriate users.
- [ ] Stable unique user and group mapping tested.
- [ ] Disabled/missing-group users denied privileged access.
- [ ] Session/logout/revocation behavior documented.
- [ ] Credential/certificate rotation tested.
- [ ] IdP outage and recovery tested without disabling security.
- [ ] Least-privilege role matrix validated.
- [ ] Audit evidence and runbooks signed off.

**Companion:** [Chapter 058 hands-on lab](labs/058-jenkins-enterprise-sso-ldap-saml-oidc-integration-check.md).  
**Next:** Chapter 059 — Jenkins Credentials Management, Secret Stores and Rotation.
