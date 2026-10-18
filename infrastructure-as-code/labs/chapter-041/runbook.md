# Chapter 041 — Azure IaC SRE/DBRE runbooks

## Deployment
Verify Azure tenant, subscription, identity and RBAC; check AzureRM version and state backend authentication. Run fmt/validate/tests, policy gate and plan. Review Azure Policy, regions, resource provider registrations, quota and cost. Apply only after change approval, under state lock, then verify Activity Logs, alerts and service health.

## Wrong tenant or subscription
Stop pipeline immediately. Preserve STS/Entra principal, subscription and plan evidence; identify unintended changes; notify security and platform incident command. Do not use broad permissions to compensate.

## OIDC failure
Inspect issuer, subject, audience, federated identity credential, service principal/managed identity and role assignment scope. Repair exact trust, re-run gate, avoid static secret fallback.

## Azure state outage
Freeze concurrent writers. Inspect Storage RBAC, network, blob lease, versioning and encryption. Restore state metadata under approval. Do not blindly force-unlock or break blob leases.

## Azure Policy denial
Inspect assignment scope, definition, initiative, effect and exemption; correct deployment or request governed exception. Never disable guardrails in production to force apply.

## DBRE recovery
For Azure PostgreSQL/SQL, separately restore application data, private DNS, network paths, keys and credentials. Terraform state restoration does not recover databases. Record observed RPO/RTO and integrity.
