# Chapter 092 — Drift detection SRE/DBRE runbooks

1. **Drift scope:** exact account/cluster, change, owner, ticket, time and blast radius.
2. **State:** preserve Terraform/OpenTofu backend snapshot, lock and serial; review refresh-only and normal plans.
3. **Cloud:** AWS Config/CloudTrail, Azure Resource Graph/Policy, GCP Asset Inventory/Audit Logs; validate pagination and freshness.
4. **Identity:** quarantine IAM/OIDC and privilege expansion; independent security review.
5. **Kubernetes/GitOps:** admission, RBAC, Argo CD/Flux ownership and approved revision.
6. **PostgreSQL/Aurora:** PITR, WAL, KMS, backup age, replication and measured RPO/RTO.
7. **MongoDB/Redis/Kafka:** quorum, ACL, ISR, snapshot, failover and recovery.
8. **Elasticsearch/OpenSearch/Snowflake:** snapshots, shard/warehouse configuration, grants and CDC correctness.
9. **Change intelligence:** correlate actor, approved commit, ticket, policy version and exception.
10. **Remediation:** circuit breaker, independent approval, non-destructive canary and rollback.
11. **Evidence:** native source, trusted timestamps, chain, retention and gap closure.
12. **Acceptance:** SLO, zero orphans, recovery evidence, SRE/DBRE/security sign-off.
