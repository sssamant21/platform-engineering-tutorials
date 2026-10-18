# Chapter 070 — Multi-Cloud CloudFormation/Bicep SRE/DBRE Runbooks

## R1 Preflight
Verify AWS caller/account/region and Azure tenant/subscription/resource group, policy, approvals and backup.

## R2 Supply chain
Verify CloudFormation child artifact digests, Bicep module provenance, runner identity and pins.

## R3 Change previews
Review AWS change sets and Azure what-if, replacement/deletion and unknown impacts.

## R4 Canary failure
Stop remaining targets, preserve telemetry, inspect changes and escalate.

## R5 Stateful recovery
Verify PITR, backups, replication, RPO/RTO and service SLO before recovery.

## R6 Cloud control-plane failure
Inspect CloudFormation events and ARM operations; avoid force deletion.

## R7 Security incident
Revoke roles/tokens, rotate credentials, audit CloudTrail and Activity Log.

## R8 Drift
Reconcile ownership and source of truth; do not silently overwrite hotfixes.

## R9 FinOps
Audit retained/orphaned resources, tags, budgets and cleanup owners.

## R10 Post-change
Verify SLO, cloud health, backup, drift, monitoring and handover.
