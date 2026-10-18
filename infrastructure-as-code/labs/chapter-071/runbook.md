# Chapter 071 — Pulumi SRE/DBRE Runbooks

## R1 Stack identity
Verify stack, backend URL, project, organization, environment and cloud account.

## R2 Secrets
Revoke leaks, check config encryption, restrict outputs and audit access.

## R3 Preview
Review replacements/deletions, protection, provider upgrades and approvals.

## R4 State lock/outage
Preserve logs, identify operation owner; avoid manual state surgery.

## R5 Drift
Review refresh impact, reconcile manual changes through source of truth.

## R6 DBRE change
Verify PITR, backup, replica/quorum, RPO/RTO and restore evidence.

## R7 Failed update
Inspect resource URNs, provider errors, checkpoint and recovery options.

## R8 Identity
Validate scoped credentials and target account before retry.

## R9 FinOps
Review orphaned resources, provider SKUs, tags and budgets.

## R10 Post-change
Validate SLO, backups, outputs, encryption, monitoring and handover.
