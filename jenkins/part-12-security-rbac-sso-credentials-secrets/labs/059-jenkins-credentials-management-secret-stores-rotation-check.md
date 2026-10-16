# Chapter 059 — Hands-on Lab: Jenkins Credentials, Secret Stores and Rotation

**Environment:** Disposable Jenkins LTS, Credentials Binding plugin, synthetic test tokens, isolated trusted/untrusted agents, optional Vault/AWS Secrets Manager/Azure Key Vault. Never use production secrets in drills.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | List credential IDs/types without values | Inventory |
| 02 | Threat model | Map controller/agent/provider boundaries | Diagram |
| 03 | Ownership | Assign owner/expiry/consumer | Register |
| 04 | Folder scope | Create synthetic team credential | Scope |
| 05 | Isolation | Deny unrelated folder access | Denied |
| 06 | Trusted binding | Use withCredentials safely | Build |
| 07 | No tracing | Verify secret not printed | Log |
| 08 | File binding | Test secret file outside workspace | Path |
| 09 | Artifact | Verify secret absent from artifacts | Scan |
| 10 | Untrusted PR | Deny secret access | Denied |
| 11 | Vault | Test dynamic secret if available | Lease |
| 12 | AWS | Test scoped Secrets Manager identity if available | IAM |
| 13 | Azure | Test Key Vault workload identity if available | RBAC |
| 14 | K8s RBAC | Deny ordinary build SA secret access | `can-i` |
| 15 | Rotation | Issue synthetic replacement token | Change |
| 16 | Cutover | Validate new credential consumer | Pass |
| 17 | Revocation | Verify old token rejected | Denied |
| 18 | Expiry | Test alert/expired credential behavior | Alert |
| 19 | Incident | Simulate synthetic token exposure | Runbook |
| 20 | Review | Complete access review and sign-off | Report |

## 12 troubleshooting drills

1. Wrong credential ID.
2. Folder scope mismatch.
3. Pipeline interpolation exposes token.
4. Secret file archived accidentally.
5. Untrusted PR attempts credential use.
6. Vault policy denies secret read.
7. Vault dynamic lease expires.
8. AWS IAM AccessDenied.
9. EKS Pod Identity/IRSA misconfigured.
10. Azure Key Vault 403.
11. Rotation breaks dependent job.
12. Revoked synthetic token remains usable due to downstream session.

Mark provider-specific drills blocked if the integration is not installed. Never deliberately leak real credentials.

## Commands

```sh
kubectl auth can-i get secrets -n jenkins-build \
  --as=system:serviceaccount:jenkins-build:jenkins-build
kubectl get sa -n jenkins-build jenkins-build -o yaml
```

Replace example namespace/SA. Ordinary build agents should not be authorized to read Kubernetes Secrets.

## Evidence template

```text
UTC timestamp:
Jenkins/plugin versions:
Credential IDs/types (no values):
Owner/environment/expiry:
Trusted job ID:
Folder scope negative test:
Pipeline log/artifact inspection:
External provider and identity:
Kubernetes SA RBAC:
Rotation old/new references (redacted):
Revocation denial:
Provider audit event:
Exposure drill:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted with evidence.
- [ ] 12 drills completed or marked blocked.
- [ ] Secrets not printed, archived or committed.
- [ ] Untrusted jobs denied production credentials.
- [ ] Rotation and revocation tested with synthetic secrets.
- [ ] Cloud workload identities least privilege.
- [ ] Kubernetes build SA cannot read Secrets.
- [ ] Audit and expiry monitoring demonstrated.
- [ ] Reviewer signs off.

**Related:** [Chapter 059 — Jenkins Credentials Management, Secret Stores and Rotation](../059-jenkins-credentials-management-secret-stores-rotation.md).
