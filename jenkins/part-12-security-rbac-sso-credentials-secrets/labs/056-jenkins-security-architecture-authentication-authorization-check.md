# Chapter 056 — Hands-on Lab: Jenkins Security, Authentication and Authorization

**Environment:** Isolated Jenkins lab with supported Jenkins LTS, JCasC and authorization plugin, test identities, disposable Kubernetes agents. Do not weaken production security.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record Jenkins/core/plugin versions | Baseline |
| 02 | Threat model | Map user/controller/agent trust | Diagram |
| 03 | TLS | Inspect trusted HTTPS endpoint | Headers |
| 04 | Root URL | Verify reverse proxy configuration | Config |
| 05 | Authentication | Identify configured security realm | Evidence |
| 06 | IdP | Validate test user login if available | Login |
| 07 | MFA | Verify organization IdP enforcement | Evidence |
| 08 | JCasC | Export and review security config | YAML |
| 09 | Admin | Confirm controlled administrator role | Matrix |
| 10 | Developer | Grant scoped Job/Build | Matrix |
| 11 | Negative role | Deny Script Console to developer | Denied |
| 12 | Folder | Isolate staging/production jobs | Permissions |
| 13 | Anonymous | Deny private-controller access | Denied |
| 14 | Secrets | Scope lab credential to trusted job | Scope |
| 15 | Pipeline | Verify secret masking and no tracing | Build |
| 16 | PR trust | Deny untrusted job credential access | Denied |
| 17 | Kubernetes SA | Deny secret listing | `can-i` |
| 18 | SSO failure | Simulate safe IdP failure in lab | Runbook |
| 19 | Audit | Correlate user/job/credential changes | Logs |
| 20 | Acceptance | Review least-privilege matrix | Sign-off |

## 12 troubleshooting drills

1. Reverse proxy redirect loop.
2. OIDC issuer mismatch.
3. Missing LDAP group claim.
4. Developer unexpectedly granted admin.
5. Folder permission inheritance surprise.
6. Anonymous can read private job.
7. Jenkins Script Console exposed.
8. CSRF 403 on API request.
9. Pipeline secret leaked in trace.
10. Kubernetes build SA can list Secrets.
11. JCasC reload invalid authorization schema.
12. IdP outage with emergency access.

If an IdP or plugin is unavailable, mark its drill blocked, not passed. Use test accounts and disposable Jenkins controller for failure injection.

## Lab commands

```sh
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl auth can-i create pods -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
curl -sSIk https://jenkins.example.test/login
```

Replace the example hostname and SA with your actual lab values. The Kubernetes negative tests should normally return `no` for ordinary build agents.

## Evidence template

```text
UTC timestamp:
Jenkins core and plugin versions:
Authentication realm and IdP:
MFA policy:
Authorization plugin/version:
Role matrix:
Anonymous test:
Developer negative test:
Folder permission test:
Credential scope test:
Agent/Kubernetes SA test:
JCasC validation:
SSO failure/recovery:
Audit logs and reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Authentication and authorization clearly separated.
- [ ] No unauthorized administrator or Script Console access.
- [ ] Untrusted PRs cannot access production credentials.
- [ ] Build agents cannot list Kubernetes Secrets.
- [ ] SSO recovery does not disable security.
- [ ] TLS/CSRF and audit controls validated.
- [ ] Reviewer signs off.

**Related:** [Chapter 056 — Jenkins Security Architecture, Authentication and Authorization](../056-jenkins-security-architecture-authentication-authorization.md).
