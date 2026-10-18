# Chapter 062 — Ansible Reusable Roles Runbooks

## R1 Preflight
Pin ansible-core/collections, review inventory and --list-hosts, syntax, check mode, change approval and backups.

## R2 Variable precedence
Inspect role defaults, inventory and overrides; repair unexpected configuration without printing secrets.

## R3 Role failure
Check roles_path, fully qualified modules, handlers, role metadata and dependencies.

## R4 Idempotence/drift
Run twice, compare changed counts, simulate drift, reconcile and verify hash.

## R5 DBRE change
Require quorum, PITR, replica lag, connection budget, SLO and canary serial rollout.

## R6 Secret incident
Revoke identity, rotate secrets, restrict logs and audit vault.

## R7 Partial rollout
Stop further batches, restore last-good config, verify health, record affected hosts.

## R8 Post-change
Verify SLO, config checksums, backups, cost and handover.
