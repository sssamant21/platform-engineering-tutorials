# Chapter 054 — Helm, GitOps and Policy SRE/DBRE Runbooks

## Pre-change
Verify approved cluster context, chart/provider version, provenance, RBAC, hooks, CRDs, PDB, image digest, policy, release owner, DB backup, plan, ticket and Security/DBRE sign-off. Block delete/replace and unapproved uninstall.

## Helm pending-upgrade
Inspect helm history/status, hooks, Job events and Kubernetes API. Freeze competing reconcilers; recover a compatible release without uninstalling stateful data.

## CRD or operator failure
Stop dependent applies, check CRD served/storage versions and operator compatibility. Coordinate DBRE for database safety and backups.

## Terraform/GitOps ownership conflict
Pause one controller under approval, identify owner of release and fields, reconcile Terraform state, document handoff and resume single reconciler.

## Secret leak
Revoke/rotate affected credentials, audit Helm values and Terraform state access, migrate to approved secret delivery and verify consumers.

## Stateful DR
Preserve PVC/PV, restore isolated database from consistent backup/WAL, verify data integrity, cut over under DBRE approval, measure RPO/RTO.
