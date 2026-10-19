# Chapter 098 — Twelve production FinOps runbooks

1. **Billing completeness:** missing days, export freshness, replay and source lineage.
2. **AWS:** CUR 2.0, Budgets, Cost Anomaly Detection, payer/linked scope.
3. **Azure:** Cost Management budgets, export schedule, actual/amortized basis.
4. **GCP:** Billing BigQuery, credits, budgets, project labels and alerts.
5. **Terraform/OpenTofu/Pulumi:** tag policy, change estimate and approval.
6. **CloudFormation/Bicep/Ansible:** inventory, tag propagation and governance.
7. **Kubernetes:** EKS/AKS/GKE nodes, GPU, PVC, idle capacity and seasonality.
8. **Shared network:** NAT, load balancers, egress and storage forecasts.
9. **PostgreSQL/Aurora/RDS/MongoDB:** capacity, backups, IOPS and RPO/RTO.
10. **Redis/Kafka/MSK/OpenSearch/Elasticsearch:** persistence, retention and replicas.
11. **Snowflake:** credits, warehouses, CDC, storage and resource monitors.
12. **Incident closure:** FinOps/Finance/SRE/DBRE, actual versus forecast, paging receipt, SLO and audit.

Each runbook: identify account and UTC billing window; freeze unsafe automation; preserve source; check basis, ownership and completeness; investigate anomaly and approved changes; escalate to owner; validate SLO, data integrity and RPO/RTO; obtain finance sign-off.
