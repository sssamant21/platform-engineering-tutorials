# Chapter 099 — Twelve production runbooks

1. **AWS EC2/EKS:** CPU/memory/IOPS, Spot and node capacity, SLO and rollback.
2. **AWS RDS/Aurora:** replication, backups, storage IOPS, RPO/RTO and PITR.
3. **AWS commitments:** Savings Plans/RI eligibility, utilization and term approvals.
4. **Azure VM/AKS:** rightsizing, reservations, savings plans and regional capacity.
5. **GCP Compute/GKE:** CUD eligibility, utilization, fallback and discounts.
6. **Kubernetes:** requests, limits, VPA/HPA, Karpenter, PV and PDB constraints.
7. **GPU/Spot:** interruption risk, on-demand fallback and reservation.
8. **PostgreSQL/MongoDB/Redis:** data integrity, replication, memory and restore.
9. **Kafka/MSK/Elasticsearch/OpenSearch:** replicas, shards, retention and storage.
10. **Snowflake:** warehouses, auto-suspend, credits, CDC and query performance.
11. **Network/storage:** egress, NAT, snapshots, legal retention and telemetry.
12. **Acceptance:** FinOps/SRE/DBRE/Finance sign-off, measured savings, SLO and audit.

For every runbook: identify exact scope, baseline, change and owner; freeze unsafe optimization; preserve evidence and backups; diagnose capacity and cost basis; use separately approved rollback; verify SLO/RPO/RTO; reconcile realized billed savings.
