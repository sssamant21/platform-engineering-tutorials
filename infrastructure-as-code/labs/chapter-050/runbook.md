# Chapter 050 — GCP Stateful Data SRE/DBRE Runbooks

## Change preflight
Confirm service owner, RPO/RTO, backups/PITR, last verified restore, network, CMEK, quota, billing, plan, state version, rollback and Security/DBRE approval. Deny database or bucket deletion/replacement.

## Cloud SQL slow queries and IOPS
Correlate Query Insights, CPU, disk queue, locks, connections and slow SQL. Throttle offenders, tune query/index and validate p95 recovery.

## Connection pool storm
Measure application replicas × per-pod pool, database max connections and failover retries. Apply backpressure and pool limits, confirm read/write transactions.

## Corruption / PITR
Freeze writes as appropriate, identify last-known-good recovery point, restore to isolated instance, validate schema and checksums, cut over under approval, record RPO/RTO.

## CMEK outage
Freeze key changes, check key-version state and service-agent IAM, restore authorized access, validate decrypt and data integrity.

## GCS accidental deletion
Review lifecycle/audit, object versions, soft delete and retention; restore isolated copy and verify checksums.

## GKE PV zone incident
Inspect PV topology, CSI events, snapshots and reclaim policy. Coordinate transaction-consistent database restore.

## Regional disaster recovery
Recover IAM/KMS, network/DNS, database, cache, app and monitoring in dependency order. Record observed RPO/RTO, failback and incident evidence.
