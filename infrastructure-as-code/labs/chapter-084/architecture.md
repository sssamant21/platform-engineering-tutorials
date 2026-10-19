# Chapter 084 — Zero-trust architecture

**Source:** protected PR, signed commits and independent reviewers.

**CI:** untrusted code runs without production secrets; pinned toolchain and isolated runner.

**CD:** exact-subject short-lived OIDC identity; distinct AWS/Azure/GCP environment roles; scoped IAM/RBAC, org policies, KMS and state access.

**Kubernetes:** dedicated ServiceAccounts, namespace Roles, admission, NetworkPolicy, Pod Security and GitOps controller isolation.

**DBRE:** separate application/migration/admin roles; credential overlap and connection-pool verification; encrypted backups, PITR, restore rehearsal, RPO/RTO.

**Audit:** CloudTrail, Azure Activity Logs, GCP Cloud Audit Logs, Kubernetes audit and immutable change approvals.
