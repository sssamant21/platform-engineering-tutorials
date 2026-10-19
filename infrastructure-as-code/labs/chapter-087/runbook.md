# Chapter 087 — Ephemeral integration SRE/DBRE runbooks

1. **Wrong account:** halt, revoke identity, inspect cloud audit and scope.
2. **Terratest failure:** preserve state and provider logs, verify target, isolate cleanup.
3. **Molecule failure:** inspect inventory, become, driver and idempotence.
4. **Kubernetes outage:** admission, CNI/DNS, PVC, RBAC and readiness.
5. **State lock:** identify competing runs; never force-unlock without review.
6. **Orphan cleanup:** verify run ID and ownership before delete, audit cost.
7. **Budget/TTL:** quarantine expired lease, notify owner, controlled teardown.
8. **PostgreSQL/RDS:** verify PITR, KMS, WAL, lag, RPO and RTO.
9. **MongoDB/Redis:** quorum, persistence, ACL, backup and failover.
10. **Kafka/OpenSearch:** ISR, lag, shard allocation and snapshot restore.
11. **GitOps:** resolve one writer and approved source rollback.
12. **Final acceptance:** attach native logs, resource inventory, SLO, cost and signatures.
