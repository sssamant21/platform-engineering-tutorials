# Chapter 060 — Jenkins Enterprise Security Hardening and Secrets Management Capstone

**Part 12 — Security, RBAC, SSO, Credentials and Secrets (final capstone)**  
**Audience:** Jenkins SRE, security engineering, IAM, compliance, incident response and release engineering  
**Prerequisites:** Chapters 056–059; disposable Jenkins LTS, compatible security plugins, synthetic IdP identities, trusted/untrusted agents, optional external secret store.

## Mission

Harden a Jenkins controller and its build/release trust boundaries; validate enterprise SSO and RBAC, secret lifecycle, agent and cloud identities, policy and audit; demonstrate safe response to credential compromise, unauthorized access and identity provider outage. Complete a **100-point security acceptance assessment** with independently verifiable evidence.

**Scope:** Perform attack simulations and destructive fault injection only on an isolated lab. Never disable production security or expose real credentials to prove a negative test.

## 1. Reference threat model

```text
Enterprise IdP → MFA / lifecycle → Jenkins security realm
                                      │
                           Authorization strategy
                          /          |          \
                  team folders  release jobs  administrators
                         |           |             |
                  untrusted CI   trusted agents   JCasC/config
                         |           |
                 no prod secrets  scoped credentials
                                      |
                           Vault / AWS / Azure IAM
                                      |
                          Kubernetes and cloud APIs
```

Trust is not transitive: Jenkins permissions, Git branch protection, Kubernetes RBAC and cloud IAM must all be validated independently. Anyone able to modify trusted Pipeline code may be able to exfiltrate credentials used by that job.

## 2. Deliverables and ownership

| Deliverable | Owner | Required evidence |
|---|---|---|
| Threat model and data flow | Security/platform | Diagram |
| Jenkins core/plugin inventory | Jenkins SRE | Version and advisory review |
| IdP and MFA integration | IAM | Login and revocation tests |
| RBAC/role matrix | Platform security | Allowed/denied tests |
| Folder/credential boundaries | Jenkins SRE | Negative access evidence |
| JCasC baseline | Platform | Git review and validated reload |
| Agent isolation | Kubernetes SRE | Pod/SA policy and RBAC |
| External secret lifecycle | Secrets team | Rotation/revocation |
| Logging/alerts | SOC/SRE | Redacted audit evidence |
| Incident and recovery runbooks | On-call | Measured drills |

## 3. Baseline hardening checklist

- Supported Jenkins LTS, Java runtime and plugin versions; review published security advisories.
- HTTPS ingress, correct Jenkins root URL and trusted reverse-proxy headers.
- CSRF protection retained; use supported API token workflows.
- No anonymous access to private controllers.
- SSO with IdP-managed MFA, tested group mapping and disabled-user behavior.
- Minimal Overall/Administer and Script Console access.
- Restricted Job/Configure, Run/Replay, trusted libraries and production Pipeline sources.
- Folder-scoped credentials and dedicated trusted release agents.
- No production secrets in fork PR builds or general-purpose agents.
- Short-lived workload identity instead of long-lived cloud keys where supported.
- Kubernetes Pod Security Standards, resource controls and service account restrictions.
- Audited JCasC, credential changes, role changes and privileged builds.
- Encrypted and access-controlled Jenkins backup including keys, with restore test.

## 4. JCasC security-as-code workflow

Store reviewed JCasC without embedded secret values. Use an approved secret store or protected environment injection. Validate against the **installed plugin versions** on an isolated controller.

```text
security-config/
  jenkins.yaml
  permissions-matrix.md
  approved-plugins.txt
  test-users.md
  validation-results/
```

Do not copy a sample JCasC security realm into production without verifying schema and administrator recovery. A broken authorization configuration can lock out all users.

## 5. Enterprise identity acceptance

| Test | Expected |
|---|---|
| Valid test user + MFA | Authenticated |
| Missing MFA under enforced policy | Denied |
| Disabled test user | Access revoked within documented session policy |
| Missing IdP group | No elevated permissions |
| Developer views own folder | Allowed |
| Developer configures production job | Denied |
| Developer accesses Script Console | Denied |
| Release operator runs approved job | Allowed |
| Anonymous views private controller | Denied |
| IdP unavailable | Documented fail-safe recovery |

Session revocation is not always instantaneous. Record IdP/Jenkins cache and session expiry behavior rather than claiming immediate invalidation without testing.

## 6. Authorization and privilege escalation

Review Jenkins Role Strategy or Matrix Authorization, inherited item permissions, role regex boundaries, Overall/Administer, Job/Configure, Run/Replay, Agent/Configure, credentials management and trusted shared-library SCM write access. Test with actual identities and a negative case for every privileged action.

**Separation of duties:** production release operators may trigger reviewed jobs but should not modify their Pipeline definitions, trusted library, parameters that execute arbitrary commands or deployment credentials.

## 7. Credential and external secret acceptance

```groovy
pipeline {
    agent { label 'trusted-security-lab-agent' }
    stages {
        stage('Synthetic secret binding') {
            steps {
                withCredentials([string(credentialsId: 'lab-readonly-token', variable: 'LAB_TOKEN')]) {
                    sh '''#!/bin/sh
                        set +x
                        test -n "$LAB_TOKEN"
                        echo "Synthetic credential bound without printing value"
                    '''
                }
            }
        }
    }
}
```

Use only synthetic credentials. Inspect build logs, artifacts, environment exposure, workspace and downstream provider audit events. Credential masking does **not** prevent malicious Pipeline exfiltration.

Rotation procedure: inventory consumers, create replacement, validate cutover, revoke old token, verify old token denied, audit access and update expiry records. If leaked, revoke immediately rather than waiting for overlap.

## 8. Agent and cloud identity checks

```sh
# Ordinary build identity should be denied:
kubectl auth can-i list secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl auth can-i create deployments -n production \
  --as=system:serviceaccount:jenkins-build:jenkins-build
```

Check Pod `automountServiceAccountToken`, security context, host mounts, privileged mode, network egress and node isolation. For EKS verify IRSA/EKS Pod Identity and AWS IAM; for AKS verify Entra Workload Identity and Azure RBAC. Kubernetes RBAC does not prove cloud IAM least privilege.

## 9. Supply chain and plugin security

Pin compatible Jenkins core/plugins; scan advisories; restrict plugin installation and Script Console; validate signed/approved artifacts where supported. Protect shared-library repositories and build definitions. Prefer ephemeral agents and separate untrusted fork builds from privileged release jobs.

## 10. Monitoring and audit

Track successful/failed logins, authorization denials, role/JCasC changes, credential creation/rotation, privileged job changes, unusual Script Console activity, plugin changes, IdP availability, expired tokens and agent policy violations. Redact secrets, assertions and tokens before exporting logs.

## 11. Fault-injection and incident matrix

| # | Scenario | Expected control |
|---|---|---|
| 01 | Anonymous accesses private job | Deny |
| 02 | Developer requests Overall/Administer | Deny |
| 03 | Developer configures production job | Deny |
| 04 | Developer replays privileged Pipeline | Deny |
| 05 | Role regex overlaps another folder | Detect |
| 06 | IdP group claim missing | Fail least-privilege |
| 07 | Disabled user attempts login | Deny/revoke per session policy |
| 08 | IdP unavailable | Safe recovery |
| 09 | SAML/OIDC issuer/audience mismatch | Deny |
| 10 | TLS/certificate rollover error | Alert and recover |
| 11 | Jenkins API CSRF failure | Use supported token/crumb |
| 12 | Secret in Pipeline trace | Revoke/rotate |
| 13 | Secret archived in artifact | Contain and revoke |
| 14 | Fork PR requests release secret | Deny |
| 15 | Vault policy denies access | Fail closed |
| 16 | AWS/Azure workload identity overprivileged | Detect/restrict |
| 17 | Kubernetes build SA lists Secrets | Deny |
| 18 | JCasC authorization invalid | Rollback config |
| 19 | Plugin security advisory | Patch/test |
| 20 | Backup restore missing encryption keys | Restore test fails safely |

## 12. Five production runbooks

### A. Security onboarding
1. Approve threat model, plugin inventory and access matrix.
2. Configure IdP and authorization on isolated controller.
3. Protect trusted Pipelines, folders and credentials.
4. Verify negative tests and agent/cloud identity.
5. Deploy through reviewed change and record evidence.

### B. Unauthorized access incident
1. Preserve audit logs and affected identities.
2. Revoke sessions/tokens/roles and freeze sensitive jobs.
3. Review Pipeline changes, credential use and downstream cloud actions.
4. Restore approved RBAC/JCasC and validate negative tests.
5. Complete incident RCA and improve detections.

### C. Credential compromise
1. Revoke/rotate synthetic or real compromised credential immediately.
2. Investigate logs/artifacts/Git history and provider audit events.
3. Remove secret from untrusted contexts and remediate exposure.
4. Verify old credential denied and replacement works.
5. Record blast radius, notification and corrective action.

### D. SSO outage and lockout
1. Distinguish IdP, TLS, reverse proxy and Jenkins realm failure.
2. Preserve logs without raw tokens/assertions.
3. Use approved protected emergency access; **do not disable Jenkins security**.
4. Restore known-good realm/config and validate access matrix.
5. Document outage, revocation latency and recovery time.

### E. Plugin/JCasC hardening maintenance
1. Back up Jenkins home, secrets and config with restricted access.
2. Test plugin/core compatibility and JCasC schema in staging.
3. Apply change during approved window.
4. Run positive/negative authorization and credential tests.
5. Roll back safely if security regression appears.

## 13. 100-point security acceptance scorecard

| Domain | Points |
|---|---:|
| Threat model and architecture | 10 |
| Controller/ingress/plugin hardening | 10 |
| SSO/MFA and identity lifecycle | 15 |
| RBAC, folders and separation of duties | 15 |
| Credential isolation and rotation | 15 |
| Agent, Kubernetes and cloud identity | 10 |
| Audit, monitoring and detection | 10 |
| Incident response and recovery | 10 |
| Documentation and handover | 5 |
| **Total** | **100** |

Suggested passing score **85/100**, with mandatory gates: no unauthorized admin/production configuration, no secrets in untrusted jobs, least-privilege agent identity, protected SSO recovery, tested rotation/revocation and security audit evidence. Unavailable features are **not tested**, not passed.

## 14. Final handover

Include approved architecture, JCasC revision, plugin inventory, IdP integration, role matrix, credential inventory **without values**, agent/cloud identity permissions, negative test results, rotation evidence, incident drill records, backup/restore results, unresolved risks and reviewer sign-off.

**Companion:** [Chapter 060 security capstone lab](labs/060-jenkins-enterprise-security-hardening-secrets-management-capstone-check.md).  
**Part 12 complete:** Chapters 056–060.  
**Next:** Chapter 061 — Jenkins Plugin Architecture, Lifecycle and Dependency Management (Part 13).
