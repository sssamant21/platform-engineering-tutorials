# Chapter 096 — FinOps architecture

**IaC:** protected Git, Terraform/OpenTofu/Pulumi/CloudFormation/Bicep/Ansible with owner tags.

**Cloud source:** AWS CUR 2.0/Data Exports, Azure Cost Management exports, GCP Billing BigQuery exports.

**Normalization:** raw immutable source, billing account, usage date, ingestion time, currency, credits, amortized/unblended basis, deduplication and freshness.

**Allocation:** tags, Kubernetes shared costs, resource inventory, unallocated residual and unit economics.

**Governance:** budgets, anomaly owner routing, policy-as-code, monthly finance reconciliation.

**Reliability:** SLO, storage IOPS, DBRE backups, RPO/RTO, capacity and approved rollback.

**Lab boundary:** synthetic offline USD data; no native provider or database action.
