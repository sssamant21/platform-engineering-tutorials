# Chapter 043 — Azure Identity / Key Vault SRE/DBRE runbooks

## Security preflight
Verify tenant/subscription, federated OIDC issuer/audience/subject, principal, RBAC scope, Key Vault RBAC, private endpoint/DNS, purge protection, soft-delete, rotation policy, CMK service access and audit logs. Run policy tests, plan and security review before approval.

## Compromised credential
Freeze impacted deployments; revoke/rotate credential and dependent secrets; inspect Entra sign-in logs, Activity Log and Key Vault audit. Restore minimal access with short-lived identity. Preserve sanitized incident evidence.

## Federated CI outage
Compare actual token claims with Entra federated credential, branch/environment restrictions, audience and issuer. Fix exact trust; avoid long-lived secret fallback.

## Key Vault 403 or network outage
Inspect data-plane RBAC and token scope, vault firewall, private DNS and endpoint; restore scoped permissions/network, verify secret retrieval without logging values.

## Disabled/deleted CMK
Declare incident, freeze key operations, check key version state, soft-delete and purge protection, recover approved key or RBAC under dual control, verify database read/write and backup decrypt.

## Secret rotation incident
Pause rollout, identify approved current/previous secret versions, coordinate DBRE and app pool refresh, roll back under change control and verify application auth.

## Terraform state leak
Isolate backend, audit access, rotate exposed credentials, review plan artifacts and restore storage network/RBAC. State encryption alone does not erase exposure.
