# Chapter 096 — FinOps production runbooks

1. **Billing freshness:** validate export source, usage day, ingestion lag, gaps and replay.
2. **AWS:** CUR 2.0, payer/linked account, tag activation and savings plan allocation.
3. **Azure:** Cost Management scope, export schedule, actual/amortized basis and reservation.
4. **GCP:** BigQuery billing export, project labels, credits and source completeness.
5. **IaC tags:** Terraform/OpenTofu/Pulumi ownership, module propagation and drift.
6. **CloudFormation/Bicep/Ansible:** tag propagation, resource owner and inventory.
7. **Kubernetes:** EKS/AKS/GKE shared node, PV, NAT, LB and namespace allocation.
8. **Network/storage:** egress, lifecycle, orphaned volumes, snapshots and NAT charges.
9. **PostgreSQL/Aurora/MongoDB:** IOPS, backup, retention, data integrity and RPO/RTO.
10. **Redis/Kafka/Elasticsearch/OpenSearch:** capacity, tiering, replication and durability.
11. **Snowflake:** credits, warehouse auto-suspend, queue, CDC and retention.
12. **Closure:** finance reconciliation, owner, savings verification, SLO and audit evidence.
