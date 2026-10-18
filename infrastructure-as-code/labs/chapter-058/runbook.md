# Chapter 058 — Terragrunt SRE/DBRE Runbooks

## Preflight
Review toolchain and module pins, include hierarchy, account/region, backend keys, locks, encrypted backups, restore evidence and DBRE/Security approval.

## Graph failure
Stop downstream applies, identify missing output or cycle, repair upstream contracts and re-plan.

## Backend collision
Freeze all writers, capture state lineage/serial and CI audit, reconcile authoritative state before any migration.

## Partial graph apply
Inventory successful units and actual resources, isolate failed unit, resume only after approved plan.

## Database incident
Deny unapproved replacement; validate PITR and snapshots, control connection storms and coordinate DBRE.

## Secret incident
Revoke identities, rotate leaked secrets, audit generated files, backend and CI logs.

## Region DR
Restore encrypted state to isolated backend, validate resource IDs and RPO/RTO, authorize cutover.

## Post-change
Verify drift, SLO, database connectivity, backup success, cost and sign-off.
