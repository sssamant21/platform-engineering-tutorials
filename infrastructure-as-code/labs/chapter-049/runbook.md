# Chapter 049 — GCP Compute/GKE SRE and DBRE Runbooks

## Pre-change
Confirm project, API/quota, IAM/WIF, private VPC/GKE endpoint, node pools, MIG capacity, health checks, PDBs, DB connections, backups, SLOs, change ticket and security/DBRE approvals. Block unapproved cluster/node pool replacement.

## MIG unhealthy rollout
Inspect health checks, startup logs, instance template and load balancer. Pause rollout, revert to known-good template, validate latency/5xx.

## GKE node/pod failures
Inspect node conditions, events, CNI, Pod IP capacity, quota, PDBs, image pulls and disk zone affinity. Restore safe capacity and rollout.

## Workload identity 403
Verify GKE workload pool, Kubernetes service account mapping, OIDC audience, IAM and audit logs. Restore scoped trust; do not issue static keys.

## Cloud SQL connection saturation
Measure pool fan-out and max connections, coordinate DBRE, reduce application connection concurrency and validate transactions.

## GKE upgrade outage
Inspect release channel, maintenance window, surge, PDBs, Pod disruption and control plane version. Recover workloads, then resume only after review.

## Region failure
Restore private networking, IAM/KMS, compute/GKE and data in dependency order. Measure actual RPO/RTO, app SLO and DB integrity.
