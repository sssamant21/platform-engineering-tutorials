# Chapter 045 — Azure Stateful Data SRE/DBRE Runbooks

## Change preflight
Verify subscription, change ticket, DBRE and Security sign-off, backup age, latest restore test, PITR retention, private DNS, TLS, CMK permissions, storage access, monitoring and cost. Run tests and plan. Block destructive production actions.

## PostgreSQL accidental delete
Stop writes; preserve evidence; identify last good point. Restore to isolated target, verify row counts, schema, extensions, roles and application queries; approve cutover and measure RPO/RTO.

## PostgreSQL failover
Inspect HA status, client retries and connection pools. Validate DNS, TLS, read/write, WAL and latency; do not treat failover as backup recovery.

## Azure SQL corruption
Identify clean restore point; restore separately; validate DB integrity and app credentials; cut over only with business/DBRE approval.

## Storage loss
Inspect soft delete, versioning, replication, snapshots and immutable retention. Restore to isolated target, compare checksums and access controls.

## CMK or Key Vault outage
Freeze key changes; inspect key versions, identity/RBAC, private DNS and purge protection. Restore access under dual control; validate decrypt and database writes.

## Region outage
Invoke DR, identify acceptable data loss, restore identities, keys, network and DNS before data cutover. Measure observed RPO/RTO.

## Terraform state backend outage
Preserve state versions and blob leases. Repair Azure AD/RBAC, private endpoint and DNS. Never force-unlock without confirming writer ownership.
