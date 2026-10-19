# Chapter 073 — Pulumi Stack, Secrets and State Runbooks

## R1 Identity
Verify project, stack, backend, provider account and environment before preview/update.

## R2 Secret incident
Revoke/rotate, restrict state and logs, inspect encryption and access.

## R3 Backend outage
Freeze updates, check backend health, preserve evidence, avoid unsafe unlock.

## R4 Lock conflict
Identify active update owner; never force unlock blindly.

## R5 Checkpoint recovery
Verify encrypted backup, resource URNs, provider versions and isolated restore.

## R6 DBRE stateful change
Verify PITR, backup, replica quorum, RPO/RTO and restore drill.

## R7 Drift
Review refresh impact, reconcile manual changes through approved code.

## R8 Key rotation
Inventory stacks, secrets-provider dependencies and decrypt/re-encrypt plan.

## R9 FinOps
Review retained/orphaned resources, tags, budgets and owners.

## R10 Post-change
Validate outputs, state protection, monitoring, SLO and handover.
