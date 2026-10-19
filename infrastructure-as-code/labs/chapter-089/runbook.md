# Chapter 089 — Continuous compliance SRE/DBRE runbooks

1. **Drift triage:** verify resource, target, desired state, owner and freshness.
2. **Unsafe automation:** quarantine, preserve plan, require independent approval.
3. **Cloud drift:** AWS Config/CloudTrail, Azure Policy/Activity Logs, GCP Org Policy/Audit Logs.
4. **IaC state:** inspect lock, backend, provider, refresh-only and normal plan.
5. **Kubernetes:** verify RBAC, admission, CNI and audit scope.
6. **GitOps:** verify source revision, Argo CD/Flux ownership and reconciliation.
7. **Identity:** revoke wildcard OIDC, investigate IAM and rotate secrets.
8. **PostgreSQL/Aurora:** verify PITR, KMS, WAL, RPO/RTO and rollback.
9. **MongoDB/Redis/Kafka/OpenSearch:** verify quorum, ACL, ISR, snapshots and recovery.
10. **Exception:** independent approver, compensating control, expiry and remediation.
11. **Audit:** preserve native source, trusted signature, chain and retention.
12. **Closure:** verify SLO, no orphan, native control enforcement and signed handoff.
