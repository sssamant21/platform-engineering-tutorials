# Chapter 056 — OpenTofu Adoption SRE/DBRE Runbooks

## Preflight
Inventory pinned toolchain, providers/modules, backend key, state lineage/serial, lock owner, encrypted backup and isolated restore; secure DBRE/Security approval.

## Migration dry run
Copy to isolated backend, compare planned actions, verify provider schemas, deny unapproved delete/replace and database downtime.

## Lock contention
Freeze writers; identify active Terraform/OpenTofu jobs; never force-unlock an active writer.

## State incompatibility
Stop migration, preserve backups and evidence, compare version/state format, restore only in isolated environment, reconcile actual infrastructure.

## DBRE high-risk replacement
Block apply, inspect drift and resource addresses, preserve backups and design non-destructive migration.

## Credential or state leak
Restrict backend, rotate credentials, review audit logs and CI output.

## Post-cutover
Verify drift, SLOs, database connectivity, state owner, backup, alerts and rollback record.
