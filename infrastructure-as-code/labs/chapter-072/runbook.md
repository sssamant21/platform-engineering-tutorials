# Chapter 072 — Pulumi Resource Models Operations Runbooks

## R1 Provider identity
Verify stack, account, region, subscription, project, provider version and workload identity.

## R2 Component refactor
Compare old/new URNs, aliases, parents, providers and resource options.

## R3 Dependency failure
Inspect inferred and explicit edges, cycles and eventual consistency.

## R4 Replacement
Block unexpected stateful replacement; check protect/retain/aliases and DBRE approval.

## R5 Secret incident
Revoke/rotate credentials; inspect output handling and provider configuration.

## R6 DBRE recovery
Verify backup, PITR, replica quorum, RPO/RTO and restore evidence.

## R7 State recovery
Preserve checkpoints and active operations; use approved state backup.

## R8 Provider upgrade
Pin versions, test compatibility and canary rollout.

## R9 FinOps
Review retained resources, orphaned identities, tags and owners.

## R10 Post-change
Validate SLO, backup, state encryption, outputs, drift and handover.
