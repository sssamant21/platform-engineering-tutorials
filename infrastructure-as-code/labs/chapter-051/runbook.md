# Chapter 051 — Kubernetes Terraform SRE/DBRE Runbooks

## Pre-change
Verify cluster/context, provider version, CI identity, state, RBAC, namespace, quotas, network policy, PDBs, backups, change ticket and DBRE/Security approval. Deny namespace or stateful workload deletion.

## Wrong cluster context
Freeze Terraform writers; inspect provider settings and audit logs. Contain changes and restore affected objects under incident command.

## RBAC 403
Use kubectl auth can-i and impersonation; inspect roles/bindings and cloud identity. Restore scoped access, not cluster-admin.

## NetworkPolicy outage
Inspect CNI enforcement, default-deny, DNS egress and database access. Restore minimal rules and validate actual traffic.

## Stateful workload outage
Inspect PVC/PV topology, CSI, quorum and backup status; coordinate DBRE for safe data recovery and application cutover.

## GitOps conflict
Pause one controller with approval, determine resource/field ownership, reconcile Terraform state and resume one source of truth.

## Upgrade/DR
Validate PDB, node capacity, backups, cluster identity and monitoring. Recover platform dependencies then applications and data; measure RPO/RTO.
