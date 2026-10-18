# Chapter 055 — Production Kubernetes/Helm/GitOps SRE/DBRE Runbooks

## R1: Change and preflight
Verify approved cluster/context, state lock, identity, provider/chart pins, namespace policy, CNI/CSI, PDB, backups, rollout, RPO/RTO, ticket and Security/DBRE sign-off. Deny unexpected delete/replace.

## R2: Helm/Deployment incident
Freeze changes; inspect helm history, hooks, rollout, events and probes. Recover compatible chart/image; validate SLO and database schema compatibility.

## R3: GitOps ownership drift
Identify owner, pause competing reconciler under approval, reconcile Terraform/Git state, verify single ownership and audit.

## R4: DB connection exhaustion
Calculate HPA replicas times per-pod connection pools, reduce retry amplification, cap fan-out, apply backpressure, verify transactions.

## R5: CSI/PVC incident
Preserve PV/PVC, inspect topology, attachments, operator quorum, WAL/backup. Coordinate DBRE before eviction, migration or restore.

## R6: Security breach
Revoke/rotate leaked credentials, audit state/Helm metadata, verify RBAC and network egress, preserve incident evidence.

## R7: DR
Freeze unsafe writes, restore isolated consistent backup/WAL, verify data, cut over under DBRE approval and measure actual RPO/RTO.

## R8: Postmortem
Capture SLO impact, timeline, cost, evidence, root causes, action owners and acceptance sign-off.
