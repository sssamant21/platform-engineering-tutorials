# Chapter 056 — Jenkins Security Architecture, Authentication and Authorization

**Part 12 — Security, RBAC, SSO, Credentials and Secrets**  
**Audience:** Jenkins administrators, SRE, platform security, IAM and incident responders  
**Prerequisites:** Chapters 001–055, isolated Jenkins lab, administrator access, current supported Jenkins LTS and tested backup.

## Objectives

Build a defense-in-depth Jenkins security model, configure identity and authorization safely, separate controller and agent trust, enforce least privilege, verify access with positive/negative tests, and recover from authentication or privilege incidents without disabling security.

## 1. Threat model and trust boundaries

```text
Users / IdP / SSO
    │ TLS + MFA + group claims
    ▼
Reverse proxy / ingress → Jenkins controller
                           ├─ security realm: identity
                           ├─ authorization: permissions
                           ├─ credential store: scoped secrets
                           ├─ trusted admins / configuration
                           └─ Kubernetes / VM build agents
                                  ├─ untrusted PR builds
                                  ├─ internal CI builds
                                  └─ restricted release jobs
```

Treat Jenkins administrators, job authors, shared-library maintainers, agent administrators and release approvers as different trust levels. A user who can modify Pipeline code may be able to use credentials available to that Pipeline even without reading their plaintext values in the UI. Untrusted PRs must not run with deployment secrets.

## 2. Authentication versus authorization

**Authentication:** who the user is, via Jenkins local accounts, LDAP, SAML/OIDC through supported plugins or reverse-proxy integration. **Authorization:** what the authenticated principal can do, through Matrix Authorization, Role Strategy or another supported strategy. Authentication alone does not enforce least privilege.

| Persona | Typical permissions | Must not receive |
|---|---|---|
| Jenkins platform admin | Overall/Administer | Unreviewed shared credentials |
| Security auditor | Overall/Read and approved audit visibility | Configure/credentials write |
| Folder owner | Folder-scoped job management | Overall/Administer |
| Developer | Job/Read, Job/Build on approved folders | Credentials/View, Job/Configure if untrusted |
| Release operator | Approved release Job/Build | Production secret management |
| Anonymous | None or deliberately limited public access | Overall/Read on private controller |
| Agent identity | Connect to approved controller | Controller admin or broad cloud IAM |

Actual permission names and inheritance vary by plugin/version. Validate them on the installed system rather than assuming a generic table is executable configuration.

## 3. Identity provider architecture

For enterprise SSO, prefer a supported Jenkins security realm integrated with an organization-controlled IdP, enforcing MFA and lifecycle policies at the IdP. Validate issuer, audience, callback URLs, reverse-proxy headers, clock synchronization, group claim format and session behavior. Keep at least one documented, protected emergency recovery method consistent with organizational policy.

**Never** disable Jenkins security to fix SSO. Do not expose a recovery local account to general users or keep unmonitored shared passwords.

## 4. JCasC baseline

The following is an **isolated lab-only** example using Jenkins Configuration as Code and Matrix Authorization plugin syntax. Confirm syntax against installed plugin versions and the JCasC reference exported from that exact controller.

```yaml
jenkins:
  systemMessage: "Jenkins security lab — nonproduction"
  securityRealm:
    local:
      allowsSignup: false
      users:
        - id: "lab-admin"
          password: "${JENKINS_LAB_ADMIN_PASSWORD}"
  authorizationStrategy:
    globalMatrix:
      entries:
        - user:
            name: "lab-admin"
            permissions:
              - "Overall/Administer"
        - group:
            name: "authenticated"
            permissions:
              - "Overall/Read"
```

The environment variable must be injected from a protected secret store and must **not** be committed. This sample does not represent a recommended production SSO configuration. Avoid granting all authenticated users global read if your organization's confidentiality model forbids it. Matrix Authorization and JCasC plugin schemas can change; validate using a disposable controller and the installed plugin's documented schema.

## 5. Harden controller ingress

- Terminate TLS with valid certificates; enforce HTTPS end-to-end where applicable.
- Set correct Jenkins root URL and trusted reverse-proxy forwarding headers.
- Restrict ingress/network paths to approved clients and agents.
- Preserve CSRF protection; use supported API token authentication rather than disabling crumb issuer.
- Protect agent TCP/WebSocket connections; prefer outbound agents and approved transport.
- Apply security updates to Jenkins core, plugins, OS/container base images and Java runtime.
- Separate controller runtime from build tools; never run arbitrary build steps on built-in node.
- Back up Jenkins home and encryption keys with controlled access; test restore.

## 6. Authorization models

**Global Matrix:** straightforward global permission grants, suitable for smaller installations but potentially broad.

**Project-based Matrix:** permissions on items with inheritance rules; check parent permissions and discoverability.

**Role Strategy:** map global, item and agent roles to principals/groups; beware regex scope and inherited privileges.

Do not equate folder isolation with complete security if developers can change trusted shared libraries, use Script Console, configure agents or control credentials. The **Overall/Administer** and script-execution capabilities are high-trust.

## 7. Folder and credential boundaries

```text
Jenkins root
├── platform-admin/
├── engineering/
│   ├── build-only/
│   └── integration-test/
└── releases/
    ├── staging/
    └── production/   ← restricted job authors, approvers and credentials
```

Use folder-scoped credentials, credential domains and external secrets integrations where appropriate. Folder credential scope is not a sandbox against anyone who can edit a Pipeline that can consume those credentials. Restrict job configuration, SCM source trust, shared libraries and PR build contexts.

## 8. Jenkins Pipeline secret safety

```groovy
pipeline {
    agent { label 'trusted-internal-agent' }
    stages {
        stage('Read-only identity check') {
            steps {
                withCredentials([string(credentialsId: 'lab-readonly-token', variable: 'API_TOKEN')]) {
                    sh '''#!/bin/sh
                        set +x
                        test -n "$API_TOKEN"
                        echo "Token available to trusted job; value not printed"
                    '''
                }
            }
        }
    }
}
```

The credential must exist and be accessible to the trusted job. Do not interpolate secrets into Groovy double-quoted shell strings; use shell environment expansion and avoid verbose tracing. Jenkins masking is **not** a complete data-loss-prevention control: malicious Pipeline code can exfiltrate secrets. Isolate trust domains.

## 9. Agent and cloud identity separation

| Component | Identity | Boundaries |
|---|---|---|
| Controller | Kubernetes/host runtime | No unnecessary cloud deployment permissions |
| Kubernetes provisioner | Scoped SA | Pod lifecycle in agent namespace |
| Ordinary build agent | Restricted SA | No Kubernetes API token by default |
| EKS trusted release agent | IRSA or EKS Pod Identity | Scoped AWS IAM role |
| AKS trusted release agent | Entra Workload Identity | Scoped Azure RBAC |
| Jenkins release job | Folder/job authorization | Approved source and promotion |

Never conflate Jenkins user permissions, Kubernetes RBAC and cloud IAM: all three must be evaluated independently.

## 10. Security verification commands

```sh
# Kubernetes agent identity: should not list secrets or create pods
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl auth can-i create pods -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build

# Verify HTTPS response headers in a lab without exposing credentials
curl -sSIk https://jenkins.example.test/login
```

The example hostname is a placeholder. Kubernetes checks must use the actual namespace/SA from Chapter 050. Both negative permissions should normally return `no` for a regular build SA.

## 11. SSO and authorization validation matrix

| Test | Expected |
|---|---|
| Anonymous private-controller access | Denied |
| Developer login | IdP-authenticated |
| Developer builds allowed job | Allowed |
| Developer configures production release | Denied |
| Developer accesses Script Console | Denied |
| Release operator triggers approved job | Allowed |
| Former employee login after IdP disable | Denied |
| Missing group claim | No privilege escalation |
| IdP outage | Documented fail-safe behavior |
| Admin recovery | Tested controlled procedure |
| Untrusted PR requests secret | Denied |
| Agent requests cluster secret list | Denied |

## 12. Troubleshooting scenarios

| Symptom | Investigate | Safe remediation |
|---|---|---|
| Login redirect loop | Root URL, proxy headers, cookie settings | Fix URL/proxy |
| OIDC/SAML validation fails | Issuer/audience/certs/clock | Correct IdP integration |
| LDAP groups missing | Search base/filter/group mapping | Fix directory mapping |
| User unexpectedly admin | Role/group inheritance | Revoke excessive grant |
| Developer cannot see job | Item role and Overall/Read | Correct scoped permission |
| Script Console exposed | Overall/Administer assignment | Revoke and audit |
| CSRF 403 | API token/crumb/session | Use supported authentication |
| Credentials visible in log | Pipeline quoting/tracing | Revoke/rotate and fix |
| Agent cannot connect | Remoting/TLS/network | Fix scoped connectivity |
| Build SA has Kubernetes access | RBAC/token mount | Remove privilege |
| Former user still active | IdP lifecycle/session | Revoke and audit |
| Plugin security advisory | Installed version/impact | Patch/test/rollback |
| SSO provider outage | IdP availability | Follow documented recovery |
| JCasC reload rejected | Plugin schema/logs | Roll back config |
| Emergency account misuse | Audit/session | Revoke and investigate |

## 13. Production runbooks

### A. SSO onboarding
1. Inventory supported Jenkins core/plugins and IdP requirements.
2. Test IdP realm on isolated controller with protected recovery access.
3. Map groups to least-privilege roles.
4. Validate positive/negative authorization tests.
5. Document IdP outage behavior, monitoring and change rollback.

### B. Unauthorized privilege incident
1. Preserve security/audit logs and identify affected principal.
2. Revoke session/token/role as appropriate.
3. Inspect job configuration, credential access and downstream actions.
4. Restore reviewed least-privilege mapping.
5. Complete security RCA and alert improvements.

### C. Credential exposure
1. Revoke and rotate affected secret immediately.
2. Inspect Jenkins logs, artifacts, environment and downstream use.
3. Remove secret from untrusted job contexts.
4. Verify rotation and deny unauthorized access.
5. Preserve incident evidence.

### D. Authentication outage
1. Determine IdP versus Jenkins versus reverse-proxy failure.
2. Validate TLS, DNS, callback, issuer and group claims.
3. Use approved emergency recovery without disabling security.
4. Restore IdP and validate access matrix.
5. Record outage and corrective actions.

### E. Plugin/JCasC security change
1. Capture compatible core/plugin inventory and backup.
2. Test change in isolated controller.
3. Validate JCasC reload and permission matrix.
4. Roll out with monitored maintenance window.
5. Restore known-good configuration if authorization regresses.

## 14. Acceptance checklist

- [ ] Documented trust boundaries and identity provider.
- [ ] MFA and IdP lifecycle enforced where supported.
- [ ] Anonymous and untrusted PR access restricted.
- [ ] Authorization matrix tested with real test accounts.
- [ ] Folder/job permissions do not expose production secrets.
- [ ] Agent and cloud identities are least privilege.
- [ ] CSRF/TLS/ingress protections verified.
- [ ] Security audit and recovery runbooks tested.
- [ ] JCasC changes versioned and validated.
- [ ] No production security bypasses used.

**Companion:** [Chapter 056 hands-on lab](labs/056-jenkins-security-architecture-authentication-authorization-check.md).  
**Next:** Chapter 057 — Jenkins Role-Based Access Control, Folder Security and Least Privilege.
