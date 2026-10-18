# Chapter 053 — Kubernetes Workloads, Storage and Helm SRE/DBRE Runbooks

## Pre-change
Verify approved cluster/context, provider/chart pins, image digests, workload probes, PDB, HPA pool capacity, PVC topology/reclaim policy, database backup/restore, CI identity, ticket and DBRE/security sign-off. Deny unexpected delete/replace.

## Failed Deployment rollout
Inspect readiness/liveness/startup, endpoints, image and resources. Roll back compatible image and validate error rate, latency and downstream DB.

## StatefulSet or PVC incident
Preserve PV/PVC, inspect CSI, zone affinity, operator quorum, backup and WAL. Coordinate DBRE before migration, eviction or restore.

## Helm release stuck
Inspect helm history/status, hooks, CRDs and API events. Pause competing controller under approval; recover release without uninstalling stateful data.

## Database connection storm
Measure HPA replicas times per-pod pool; cap fan-out, apply backpressure, reduce retries and verify transaction success.

## Data corruption / DR
Freeze unsafe writes, restore isolated known-good backup with WAL, verify integrity, cut over under change control and measure actual RPO/RTO.
