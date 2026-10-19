# Chapter 097 — Shared platform chargeback architecture

**Source:** immutable AWS CUR/Data Exports, Azure Cost Management, GCP BigQuery Billing, IaC ownership.

**Normalize:** provider account, UTC usage period, amortized basis, USD, credits and adjustments; never mix bases.

**Meter:** EKS/AKS/GKE CPU/memory/GPU/PVC/egress and platform idle costs; PostgreSQL/MongoDB/Redis/Kafka/Elasticsearch/Snowflake tenancy.

**Allocate:** direct ownership, approved shared weights, explicit idle and unallocated residual; integer cents.

**Govern:** showback visibility, finance-approved chargeback, dispute resolution, tenant isolation.

**Reliability:** SLO, DBRE RPO/RTO, capacity, backup, and independent optimization approval.

**Boundary:** offline synthetic fixture only; no real invoice settlement.
