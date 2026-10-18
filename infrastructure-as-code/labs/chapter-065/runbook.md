# Chapter 065 — Ansible Enterprise SRE/DBRE Capstone Runbooks

## R1 Preflight
Verify pinned toolchain, inventory, list-hosts, change ticket, backup, SLO and approvals.

## R2 Security incident
Revoke identities, rotate Vault keys/secrets, quarantine CI artifacts and audit provenance.

## R3 Canary failure
Stop later batches, record changed hosts, diagnose, require reviewed recovery.

## R4 Partial rollout
Reconcile desired/current state, preserve evidence and re-plan serial rollout.

## R5 Database recovery
Verify quorum, replication, PITR, connection budget, RPO/RTO and SLO.

## R6 Drift
Detect unauthorized change, review diff, reconcile Git source and verify idempotence.

## R7 Backup/restore
Isolate target, verify checksum, restore, measure RPO/RTO and approve cutover.

## R8 Secrets
Use approved vault identities, no_log, restricted logs, rotation and audit.

## R9 Post-change
Verify SLO, backups, drift, monitoring, cost and ownership handover.

## R10 Game-day escalation
Declare incident, establish commander, freeze automation, communicate and record RCA/COA.
