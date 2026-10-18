# Chapter 060 — OpenTofu/Terragrunt Capstone SRE/DBRE Runbooks

## R1 Preflight
Record toolchain/provider/module pins, backend key, lock owner, lineage/serial, encrypted backup, isolated restore evidence, change ticket and approvals.

## R2 Compatibility
Freeze migration, compare provider schemas/state format and module addresses, reproduce in isolated root, revise rollback ADR.

## R3 Lock/serial
Stop all writers, preserve audit, reconcile authoritative state. Never force-unlock active process.

## R4 Partial DAG apply
Inventory successful units, compare actual IDs, isolate failed unit and approve re-plan.

## R5 Database incident
Block stateful replacement, verify PITR, backups, replication, connections, maintenance window and DBRE approval.

## R6 GitOps conflict
Pause reconciliation, establish one writer per object, resolve drift through reviewed source.

## R7 DR
Restore encrypted state in isolated backend, validate checksum/lineage/IDs and measure RPO/RTO before cutover.

## R8 Security
Revoke identities, rotate secrets, restrict plan artifacts, audit CI/backend access.

## R9 Post-cutover
Verify SLO, drift, DB health, backups, cost and signed handover.
