# Chapter 057 — OpenTofu State, Provider and Module SRE/DBRE Runbooks

## Preflight
Record pinned OpenTofu/provider/module versions, state backend key, lineage/serial, exclusive lock, encrypted backup, restore test, ticket and DBRE/Security sign-off.

## Provider upgrade
Freeze changes; compare schema/lockfile and sandbox plan. Deny unapproved replace/delete; verify DB/KMS/PV identity.

## Module refactor
Review address changes, moved blocks and output contracts; plan and verify resource IDs remain stable.

## Lock conflict
Stop competing writers, identify active jobs and lock owner. Never force-unlock an active writer.

## State disaster
Recover encrypted backup in isolated backend, validate checksum/lineage/serial and actual resource IDs; authorize cutover only after reconciliation.

## Database incident
Preserve backups/PITR, block stateful replacement, coordinate DBRE for maintenance and recovery.

## Secret incident
Revoke and rotate leaked credentials; audit backend and CI logs; validate access controls.

## Post-change
Verify drift, application SLO, database connectivity, FinOps and signed change record.
