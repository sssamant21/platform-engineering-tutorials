# Chapter 097 — Twelve shared-cost production runbooks

1. **Billing ledger:** completeness, late records, source digest and replay.
2. **Basis/credits:** actual vs amortized, refunds, taxes and FX policy.
3. **AWS:** CUR payer/linked accounts, savings plan and direct/shared split.
4. **Azure:** subscription, reservation and resource-group mapping.
5. **GCP:** BigQuery billing export, labels, CUD and project ownership.
6. **Kubernetes:** CPU/memory/GPU/PVC, idle/system node and namespace allocation.
7. **Shared platform:** NAT, ingress, load balancers, observability and security.
8. **PostgreSQL/Aurora/RDS:** instance, IOPS, storage, backup and RPO/RTO.
9. **MongoDB/Redis:** replica overhead, memory, persistence and tenant usage.
10. **Kafka/MSK/OpenSearch/Elasticsearch:** brokers, retention, shards and storage.
11. **Snowflake:** warehouse credits, CDC, query attribution and shared compute.
12. **Finance acceptance:** zero-cent reconciliation, dispute, tenant privacy, sign-off.

For each: identify owner/scope; freeze chargeback publication; preserve immutable raw source; reconcile weights and residual; correct with approved effective-dated policy; verify SLO and data integrity; close with Finance/SRE/DBRE signatures.
