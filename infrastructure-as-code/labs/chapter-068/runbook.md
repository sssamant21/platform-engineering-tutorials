# Chapter 068 — Azure Bicep Operations Runbooks

## R1 Preflight
Verify tenant, subscription, resource group, caller, module pins, Azure Policy, locks, quotas and approvals.

## R2 What-if
Inspect additions, modifications, deletes, unresolved expressions and secure parameters.

## R3 RBAC
Inspect identity, token, role assignment and scope; do not grant broad Owner.

## R4 Policy/lock
Identify denying policy or lock, review remediation and owner-approved exception.

## R5 Partial deployment
Inspect ARM deployment operations, preserve evidence, reconcile resource graph.

## R6 DBRE stateful change
Validate PITR, backups, replicas, SLO and restore evidence before Azure SQL/PostgreSQL changes.

## R7 Secret incident
Revoke/rotate, restrict CI logs, audit Key Vault and federated identity.

## R8 Drift
Compare deployed resources to Bicep/Git, reconcile through reviewed what-if.

## R9 FinOps
Review storage, disks, SKUs, retention, tags and orphaned assets.

## R10 Post-change
Verify Azure Monitor, Activity Log, backups, security and handover.
