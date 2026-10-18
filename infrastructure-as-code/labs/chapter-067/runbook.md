# Chapter 067 — Nested Stack and StackSet Runbooks

## R1 Preflight
Verify caller, account, region, OU, StackSet target matrix, template digests, execution roles, quotas and approvals.

## R2 Nested stack failure
Inspect parent and child events, restore reviewed child template and reconcile resources without force deletion.

## R3 StackSet partial deployment
Enumerate failed instances by account/region, stop operations, diagnose roles/quotas, re-plan.

## R4 Export dependency
Identify import consumers, coordinate interface migration and avoid destructive renames.

## R5 Stateful change
Validate RDS backup/PITR, replica/quorum, connection budget, SLO and restore evidence.

## R6 Security incident
Revoke roles, audit CloudTrail, quarantine templates/macros and rotate exposed secrets.

## R7 Drift
Inspect resource/stack drift, establish ownership, reconcile via reviewed change set.

## R8 Rollback
Inspect failed resources and events, restore approved template, verify data and SLO.

## R9 FinOps
Audit retained/orphaned resources, tags and cost before cleanup.

## R10 Post-change
Verify all account/region instances, monitoring, backup, drift and handover.
