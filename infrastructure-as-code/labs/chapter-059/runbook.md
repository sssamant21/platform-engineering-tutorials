# Chapter 059 — Terragrunt DAG, State and CI/CD Runbooks

## Preflight
Inventory DAG, output contracts, pinned versions, account/region, backend keys, locks, encrypted backups, restore evidence, OIDC and DBRE/Security approval.

## Dependency failure
Stop downstream, identify cycle/missing output, repair upstream and re-plan.

## Backend collision
Freeze writers, preserve audit and lineage/serial, reconcile authoritative state.

## Partial graph apply
Inventory successful units, compare actual resources, isolate failure and resume with approved plan.

## Database incident
Deny unapproved replace/delete, verify PITR/backup, connections and replication, engage DBRE.

## CI security
Revoke compromised identity, rotate secrets, restrict plan artifacts and audit untrusted PR access.

## State DR
Restore encrypted backup to isolated backend, validate checksum/lineage/IDs and RPO/RTO.

## Post-change
Verify drift, SLO, DB connectivity, backup, cost and sign-off.
