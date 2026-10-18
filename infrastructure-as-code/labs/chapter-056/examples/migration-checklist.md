# OpenTofu migration checklist — review-only
1. Inventory roots, Terraform/OpenTofu versions, providers, modules, state and backends.
2. Verify encrypted versioned backup and isolated restore.
3. Freeze all writers; confirm exclusive state lock and change ticket.
4. Compare pinned toolchain plans in an isolated workspace.
5. Reject unexpected delete/replace and secrets in state.
6. Obtain DBRE/Security approval and validate database/Kubernetes resource IDs.
7. Cut over one writer, measure SLO, record state lineage/serial and rollback path.
