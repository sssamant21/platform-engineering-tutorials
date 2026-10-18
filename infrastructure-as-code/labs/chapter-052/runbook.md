# Chapter 052 — Kubernetes Multitenancy SRE/DBRE Runbooks

## Pre-change
Confirm approved context, namespace owner, tenant labels, RBAC/ServiceAccount, PSA, quota, LimitRange, CNI, DNS/DB egress, backup and Security/DBRE approval. Block unexpected delete/replace.

## RBAC exposure
Freeze changes, capture audit logs, inspect effective roles and subjects, remove excessive bindings, revoke exposed credentials, validate tenant boundaries.

## NetworkPolicy outage
Verify CNI support, namespace selectors, CoreDNS UDP/TCP 53, private DB egress and service NAT. Restore narrowly scoped traffic and validate SLOs.

## Quota exhaustion
Inspect requests/limits, pending pods and cluster capacity; adjust with owner approval and recheck workloads.

## Stateful tenant incident
Check PVC/PV, CSI, PDB, database quorum and restore point. Do not delete namespace or PVC without DBRE sign-off.

## Terraform/GitOps drift
Freeze one controller, determine ownership, reconcile state, test approved changes and resume monitoring.
