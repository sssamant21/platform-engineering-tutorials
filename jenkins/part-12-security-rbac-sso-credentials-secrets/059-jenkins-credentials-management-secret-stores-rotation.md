# Chapter 059 — Jenkins Credentials Management, Secret Stores and Rotation

**Part 12 — Security, RBAC, SSO, Credentials and Secrets**  
**Audience:** Jenkins SRE, platform security, IAM, DevSecOps, release engineering  
**Prerequisites:** Chapters 056–058; disposable Jenkins LTS, Credentials Binding plugin, trusted lab agents, optional Vault/AWS Secrets Manager/Azure Key Vault integration.

## Learning outcomes

Design Jenkins credential trust boundaries; scope credentials to folders/jobs; integrate external secret managers; prefer short-lived cloud workload identities; implement rotation and revocation; prevent leakage from Pipelines, logs, artifacts and agents; audit secret access and respond to compromise.

## 1. Threat model

```text
IdP and RBAC → Jenkins controller → credential store / provider
                      │
                 Pipeline job
                      │
           trusted agent environment
                      │
          downstream registry / cloud API
```

**Important:** Jenkins credential masking is not a security boundary against malicious Pipeline authors. Anyone who can edit a Pipeline that can use a credential can often exfiltrate it. Limit Job/Configure, Run/Replay, shared-library write access, untrusted SCM branches and agent sharing.

## 2. Credential types and ownership

| Credential | Typical use | Risk / recommendation |
|---|---|---|
| Username/password | Legacy service integration | Rotate, prefer token |
| Secret text | API tokens | Restrict scope and lifetime |
| Secret file | Client config/cert | Protect workspace and agent |
| SSH private key | SCM/deploy | Prefer deploy keys/app tokens with read-only scope |
| Certificate | Mutual TLS/signing | Manage expiry/rotation |
| Cloud workload identity | EKS/AKS cloud APIs | Prefer short-lived federation |
| External secret reference | Vault/Secrets Manager/Key Vault | Central lifecycle and audit |

Credential types and availability depend on installed plugins. Use an inventory with owner, environment, access path, expiry, rotation procedure and revocation contact.

## 3. Scope hierarchy

```text
Jenkins root (avoid broad global secrets)
├── engineering/
│   ├── team-a/  → team-a read-only test token
│   └── team-b/  → separate token
└── releases/
    ├── staging/ → staging deployment identity
    └── production/ → restricted production identity
```

System-scoped credentials serve Jenkins internals and are not intended for general job use. Folder-scoped credentials limit accidental access, but do not protect against malicious job configuration within the folder. Credential domains are organizational selectors, **not** a complete authorization boundary.

## 4. Safe Pipeline bindings

Use Credentials Binding with single-quoted Groovy shell scripts so expansion happens in the shell, not Groovy:

```groovy
pipeline {
    agent { label 'trusted-internal-agent' }
    options { timestamps() }
    stages {
        stage('Read-only API check') {
            steps {
                withCredentials([string(credentialsId: 'lab-readonly-api-token', variable: 'API_TOKEN')]) {
                    sh '''#!/bin/sh
                        set +x
                        test -n "$API_TOKEN"
                        echo "Credential bound to trusted job; value not printed"
                    '''
                }
            }
        }
    }
}
```

Do not print tokens, enable `set -x`, use shell tracing, echo environment variables, archive secret files or pass secrets as process command-line arguments where avoidable. Environment variables can be observable to processes sharing the same agent/user; isolate secret-using jobs onto dedicated agents.

## 5. Secret file handling

Secret file bindings can be exposed under workspace-related temporary directories. Prefer binding **outside** `dir('subdir')` and avoid browsing or archiving secret-containing workspaces:

```groovy
withCredentials([file(credentialsId: 'lab-client-config', variable: 'CLIENT_CONFIG')]) {
    dir('build') {
        sh '''#!/bin/sh
            set +x
            test -f "$CLIENT_CONFIG"
            echo "Client configuration available to trusted build"
        '''
    }
}
```

Do not copy the file into the repository, `stash` it or include it in artifacts. Ensure agent cleanup and ephemeral workspaces.

## 6. External secret manager patterns

| Provider | Typical integration | Operational controls |
|---|---|---|
| HashiCorp Vault | Jenkins Vault plugin/API | Vault policies, short-lived tokens, lease renewal |
| AWS Secrets Manager | Jenkins provider or SDK | IAM least privilege, rotation Lambda, CloudTrail |
| Azure Key Vault | Jenkins plugin/SDK | Entra Workload Identity, Azure RBAC, audit logs |
| Kubernetes Secrets | Mounted/env secrets for trusted agents | Encryption at rest, RBAC, no unnecessary token mount |

Plugin capability varies by version; validate whether retrieval happens on controller or agent and how values are cached. Prefer provider-native short-lived authentication rather than storing a permanent cloud key in Jenkins to fetch other secrets.

## 7. EKS and AKS workload identity

**EKS:** use IRSA or EKS Pod Identity for trusted agent Pods with narrow AWS IAM permissions. Check trust policy, service account annotations/association, namespace and token audience.

**AKS:** use Microsoft Entra Workload Identity with federated identity credential, approved service account labels/annotations and narrow Azure RBAC/Key Vault permissions.

```sh
kubectl auth can-i get secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl get sa -n jenkins-build jenkins-build -o yaml
```

Ordinary build agents should not have broad Kubernetes Secret access. Cloud IAM is independent from Kubernetes RBAC and Jenkins folder permissions.

## 8. Rotation lifecycle

1. Inventory credential ID, owner, consumers, scopes, expiry and downstream systems.
2. Create replacement credential at provider, with overlapping validity where supported.
3. Store replacement securely and update trusted consumer references.
4. Validate synthetic job with new credential.
5. Revoke old credential and verify it can no longer authenticate.
6. Review audit logs for unexpected use and document change.
7. Schedule next rotation based on risk and policy.

Do not rotate production secrets without knowing all consumers and rollback/recovery implications. For leaked credentials, prioritize immediate revocation over planned overlap.

## 9. Dynamic secrets and TTL

Vault dynamic credentials or cloud STS sessions reduce long-lived exposure. Ensure leases last long enough for job duration, handle expiry/retry safely and revoke after use. Do not log lease IDs or tokens if they enable credential access. Avoid automatic retries that repeatedly expose sensitive requests.

## 10. Pipeline source trust

- Never expose release credentials to untrusted fork PRs.
- Restrict trusted shared-library repositories and branch writes.
- Review `Job/Configure`, `Run/Replay`, and parameterized shell commands.
- Separate trusted and untrusted agents, workspaces and service accounts.
- Pin SCM sources and use branch protection.
- Treat secrets in Docker build args/layers, Kubernetes Pod specs and test reports as potential leaks.

## 11. Auditing and detection

Track credential creation/update/deletion, identity/provider access, secret retrieval failures, job identity, environment, unusual access times, rotation age, secret expiry and privileged Pipeline edits. Use Jenkins audit plugins or supported log forwarding and provider audit trails. Avoid logging actual secret values.

## 12. Troubleshooting matrix

| Symptom | Evidence | Recovery |
|---|---|---|
| Credentials ID not found | Folder scope/plugin | Correct ID/scope |
| Secret binding denied | Job context | Fix approved access |
| API returns 401 | Token expiry/revocation | Rotate |
| Vault permission denied | Policy/role | Fix narrow policy |
| Vault lease expires mid-build | TTL/renewal | Shorten job/renew |
| AWS AccessDenied | IAM role/trust | Fix least privilege |
| EKS identity unavailable | SA/Pod identity config | Fix association |
| Azure Key Vault 403 | Azure RBAC/federation | Fix role/issuer |
| Secret file in artifact | Artifact manifest | Revoke and purge |
| Secret in console log | Log review | Revoke/rotate |
| Fork PR accessed secret | SCM trust | Isolate and investigate |
| Credential stored in Git | Git history | Revoke and remove exposure |
| Rotation breaks dependent job | Consumer inventory | Roll forward safely |
| Stale secret cached | Plugin/provider behavior | Refresh/restart if needed |
| Agent environment exposed | Process isolation | Move to isolated agent |
| Revoked token still works | Downstream sessions | Invalidate and audit |

## 13. Production runbooks

### A. New credential onboarding
1. Define owner, purpose, environment and least-privilege permissions.
2. Choose workload identity/dynamic secret where feasible.
3. Store in approved provider or scoped Jenkins folder.
4. Test with trusted job and negative access case.
5. Record expiry, rotation and revocation procedure.

### B. Scheduled rotation
1. Discover all consumers and service dependencies.
2. Create new credential with approved overlap.
3. Update consumers and validate.
4. Revoke old credential and test denial.
5. Audit and close change ticket.

### C. Secret exposure incident
1. Preserve evidence without copying the secret into tickets.
2. Revoke/rotate immediately; assess blast radius.
3. Remove secret from logs/artifacts/history according to retention and incident policy.
4. Check downstream activity and compromised identities.
5. Harden Pipeline and agent trust; complete RCA.

### D. External provider outage
1. Distinguish network, IAM, provider availability and plugin errors.
2. Check cached credential/lease expiry.
3. Fail closed for new privileged operations.
4. Restore provider connectivity/identity without disabling checks.
5. Validate job recovery and alerting.

### E. Credential access review
1. Export credential inventory without values.
2. Review owners, scope, consumer jobs and expiry.
3. Remove orphaned and overprivileged secrets.
4. Test untrusted job negative access.
5. Obtain security sign-off.

## 14. Acceptance criteria

- [ ] No secrets committed to Git, artifacts or console logs.
- [ ] Production secrets unavailable to untrusted PRs.
- [ ] Folder/job credential boundaries verified.
- [ ] Cloud identities short-lived and least privilege where supported.
- [ ] Rotation and revocation tested.
- [ ] Secret file workspace handling verified.
- [ ] Provider audit logs and expiry alerts enabled.
- [ ] Exposure incident runbook rehearsed.
- [ ] Credential inventory has owners and review dates.
- [ ] No broad Kubernetes Secrets access for ordinary agents.

**Companion:** [Chapter 059 hands-on lab](labs/059-jenkins-credentials-management-secret-stores-rotation-check.md).  
**Next:** Chapter 060 — Jenkins Enterprise Security Hardening and Secrets Management Capstone.
