# Chapter 040 — AWS Stateful Data SRE/DBRE Runbooks

## Pre-change
Verify STS principal/account, backend isolation and lock; inventory RDS/Aurora, S3, EBS, EFS and KMS dependencies. Review latest successful **restore**, not just backup status. Confirm retention, PITR, RPO/RTO, change approval, plan digest and no delete/replace actions.

## RDS/Aurora failover
Declare incident, inspect events, replication and writer identity, prevent split-brain, verify endpoint/DNS and client pools, check read/write queries and error budget. Record actual recovery time.

## Logical deletion / PITR
Stop damaging writes, select safe restore point, restore into new DB, validate row counts and checksums, reconcile writes after the restore point, perform approved cutover, document observed data loss.

## S3 lifecycle error
Freeze offending lifecycle rule, locate versioned objects or protected backup copy, restore versions and validate checksums, inspect CloudTrail and owner approval.

## EBS/EFS outage
Verify AZ placement, CSI/PV bindings, mount targets, NFS SG 2049, KMS decrypt and snapshot/backup freshness; restore in isolation and validate application consistency.

## KMS access failure
Freeze key changes, inspect key policy/grants and encryption context, restore approved access under dual control, test DB/S3/EBS backup decrypt. Do not delete the key during recovery.

## Cross-region DR
Declare incident and fence primary writer, validate DR IAM/KMS/network, recover from replicated/copyable data, test integrity, cut over DNS/app clients, measure RPO/RTO, plan controlled failback.

## State recovery
Preserve state versions and change history, stop concurrent applies, restore Terraform metadata only under approval; separately restore data and validate services.
