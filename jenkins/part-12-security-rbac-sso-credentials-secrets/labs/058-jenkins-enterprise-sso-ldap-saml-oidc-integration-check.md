# Chapter 058 — Hands-on Lab: Jenkins Enterprise SSO, LDAP, SAML and OIDC

**Environment:** Isolated Jenkins LTS, test IdP or directory, HTTPS ingress, compatible authentication plugin, Role Strategy/Matrix Authorization and synthetic identities. Do not log real tokens or weaken production authentication.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record Jenkins/plugin versions | Baseline |
| 02 | Threat model | Diagram IdP/Jenkins/proxy boundaries | Diagram |
| 03 | Protocol | Compare LDAP/SAML/OIDC | Decision |
| 04 | TLS | Verify HTTPS and certificate | Check |
| 05 | Root URL | Verify public callback hostname | Config |
| 06 | Time | Verify NTP/time synchronization | UTC |
| 07 | Test IdP | Create synthetic app/client | Config |
| 08 | Test users | Create admin/developer/disabled identities | Mapping |
| 09 | MFA | Validate test conditional access | Evidence |
| 10 | LDAP | Validate LDAPS bind/group search if available | Result |
| 11 | SAML | Validate signed assertion/ACS if available | Result |
| 12 | OIDC | Validate issuer/audience/redirect if available | Result |
| 13 | User claim | Verify stable unique Jenkins principal | Identity |
| 14 | Groups | Map test group to scoped role | Role |
| 15 | Positive | Developer can build allowed job | Allowed |
| 16 | Negative | Developer cannot configure prod job | Denied |
| 17 | Disabled user | Verify access revocation behavior | Denied |
| 18 | Outage | Simulate IdP failure in isolated lab | Runbook |
| 19 | Recovery | Restore known-good realm without disabling security | Recovery |
| 20 | Review | Document audit and handover | Sign-off |

## 12 troubleshooting drills

1. Wrong Jenkins root URL.
2. Proxy redirect loop.
3. SAML Entity ID mismatch.
4. SAML signing certificate rollover.
5. SAML assertion clock skew.
6. OIDC issuer mismatch.
7. OIDC audience mismatch.
8. OIDC group claim missing.
9. LDAP bind account expired.
10. LDAP nested group lookup failure.
11. Disabled user retains session.
12. IdP outage and controlled recovery.

Mark protocol-specific drills blocked when the relevant plugin/IdP is not installed. Never bypass signature checks or disable Jenkins security for a passing result.

## Commands

```sh
curl -sSIk https://jenkins.example.test/login
date -u
```

Use the actual lab hostname. Inspect redacted Jenkins security realm logs and IdP audit events; do not paste raw assertions, tokens, cookies or client secrets into evidence.

## Evidence template

```text
UTC timestamp:
Jenkins core/plugin versions:
Chosen protocol/IdP:
Jenkins root URL and TLS:
Issuer/Entity ID (nonsecret):
Redirect/ACS URL:
MFA policy:
User/group claim mapping:
Positive login test:
Negative authorization test:
Disabled user revocation:
Cert/client secret rotation:
IdP outage/recovery:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Supported plugin/protocol selected and documented.
- [ ] MFA and callback validation confirmed.
- [ ] Group-to-role least privilege tested.
- [ ] Disabled user and missing-group behavior tested.
- [ ] No tokens/assertions/client secrets in logs or evidence.
- [ ] IdP outage recovery tested without disabling security.
- [ ] Reviewer signs off.

**Related:** [Chapter 058 — Jenkins Enterprise SSO, LDAP, SAML and OIDC Integration](../058-jenkins-enterprise-sso-ldap-saml-oidc-integration.md).
