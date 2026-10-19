# Chapter 075 — Pulumi Enterprise Multi-Cloud Runbooks

## R1 Preflight
Verify project/stack/backend, AWS/Azure/GCP targets, approvals, pinned artifacts and policy.

## R2 Identity
Verify federated token audience/subject, scopes, IAM/RBAC and expiry.

## R3 Supply chain
Check CLI/SDK/provider digests and component provenance.

## R4 Preview
Review creates, replacements, deletes, aliases, protection and policy findings.

## R5 Canary
Stop promotion on SLO regression, capture telemetry, decide recovery with owners.

## R6 Stateful recovery
Verify PITR, snapshots, replica lag/quorum, RPO/RTO and restore drills.

## R7 State outage
Preserve checkpoints, confirm lock owner, restore only under change control.

## R8 Cross-cloud incident
Freeze rollouts, assess consistency, network/identity, coordinate DBRE.

## R9 FinOps
Audit retained resources, orphaned storage, tags, budgets and owners.

## R10 Post-change
Verify backups, SLO, state protection, drift, audit and handover.
