# Chapter 061 — Ansible Foundations Runbooks

## R1 Preflight
Pin ansible-core/collections, inventory and --list-hosts; review --syntax-check, --check, --diff, change approval and backups.

## R2 Authentication
Stop rollout, inspect SSH/WinRM/identity and become permissions; restore least privilege.

## R3 Idempotence
Run twice in sandbox; inspect changed counts and replace non-idempotent shell tasks with modules.

## R4 Drift
Review Git desired config and host file, simulate change, check diff and reconcile.

## R5 DBRE rolling change
Verify replication, quorum, PITR/backup, connection budget and SLO; canary then serial rollout.

## R6 Secret exposure
Revoke leaked identity, rotate secret, restrict CI logs and vault access.

## R7 Rollback
Stop further hosts, restore last-known-good config, verify health and record partial completion.

## R8 Post-change
Verify service, checksums, SLO, backup, owner and incident notes.
