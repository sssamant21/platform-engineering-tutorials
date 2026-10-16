# Chapter 060 — Hands-on Capstone: Jenkins Enterprise Security Hardening and Secrets Management

**Environment:** Disposable Jenkins LTS controller, test IdP, JCasC, RBAC plugin, synthetic credentials, isolated build/release agents, optional Vault/AWS/Azure integration. Do not use production credentials or disable production security.

## 20 capstone exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Capture Jenkins/core/plugin versions | Baseline |
| 02 | Threat model | Diagram trust and identity boundaries | Diagram |
| 03 | TLS | Verify ingress/root URL/headers | Check |
| 04 | JCasC | Export and review security config | Git diff |
| 05 | SSO | Validate test login | Auth |
| 06 | MFA | Verify IdP policy | Evidence |
| 07 | Disabled user | Test revocation/session behavior | Denied |
| 08 | Admin | Restrict Overall/Administer | Matrix |
| 09 | Folder | Verify team isolation | Denied |
| 10 | Production | Deny Job/Configure and Replay | Denied |
| 11 | Credentials | Create synthetic folder-scoped secret | Inventory |
| 12 | Binding | Verify safe withCredentials use | Build |
| 13 | PR trust | Deny untrusted Pipeline secret use | Denied |
| 14 | External store | Test scoped provider access if available | Audit |
| 15 | Rotation | Replace synthetic credential | Change |
| 16 | Revocation | Verify old token denied | Denied |
| 17 | Agent | Deny Kubernetes Secrets read | RBAC |
| 18 | Incident | Simulate credential leak and contain | Runbook |
| 19 | Recovery | Test SSO/JCasC rollback in lab | RTO |
| 20 | Acceptance | Complete scorecard and sign-off | Report |

## 20 troubleshooting drills

1. Anonymous job visibility.
2. Unauthorized Overall/Administer.
3. Production Job/Configure granted to developer.
4. Privileged Pipeline Replay.
5. Folder regex overlap.
6. Missing IdP group claim.
7. Disabled user active session.
8. IdP outage.
9. OIDC/SAML issuer or audience mismatch.
10. TLS certificate rollover.
11. CSRF 403.
12. Pipeline shell tracing leaks synthetic token.
13. Synthetic secret in archived artifact.
14. Fork PR requests release secret.
15. Vault policy deny.
16. AWS/Azure workload identity excess permission.
17. Build SA lists Kubernetes Secrets.
18. JCasC authorization schema error.
19. Vulnerable plugin version.
20. Restore without Jenkins encryption keys.

All fault injection must be isolated and use synthetic identities. Mark unsupported integrations **blocked**.

## Commands

```sh
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl auth can-i create deployments -n production \
  --as=system:serviceaccount:jenkins-build:jenkins-build
curl -sSIk https://jenkins.example.test/login
```

Replace placeholders with lab values. Ordinary build SA checks should return `no`.

## Evidence template

```text
UTC timestamp:
Jenkins core/plugin versions:
JCasC Git revision:
IdP/realm/MFA policy:
Admin and folder role matrix:
Positive/negative access results:
Synthetic credential ID/scope:
Log/artifact leak checks:
External provider audit:
Rotation and revocation:
Agent/Kubernetes/cloud IAM:
Incident drill and recovery time:
Backup/restore test:
Score / mandatory gates:
Reviewer:
```

## 100-point scorecard

| Category | Max |
|---|---:|
| Threat model | 10 |
| Controller/ingress/plugin hardening | 10 |
| SSO/MFA/lifecycle | 15 |
| RBAC/folder isolation | 15 |
| Credential isolation/rotation | 15 |
| Agent/cloud identity | 10 |
| Audit/monitoring | 10 |
| Incident/recovery | 10 |
| Documentation/handover | 5 |
| **Total** | **100** |

Suggested pass: 85 and all mandatory controls. Do not score untested controls as passed.

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 20 drills completed or explicitly blocked.
- [ ] Unauthorized admin and production job modification denied.
- [ ] SSO/MFA and disabled-user behavior verified.
- [ ] Untrusted PRs cannot use release secrets.
- [ ] Synthetic credential rotation/revocation proven.
- [ ] Ordinary build SA cannot read Kubernetes Secrets.
- [ ] Audit logs and security alerts captured.
- [ ] IdP/JCasC recovery tested without disabling security.
- [ ] Reviewer signs off and residual risks documented.

**Related:** [Chapter 060 — Jenkins Enterprise Security Hardening and Secrets Management Capstone](../060-jenkins-enterprise-security-hardening-secrets-management-capstone.md).
