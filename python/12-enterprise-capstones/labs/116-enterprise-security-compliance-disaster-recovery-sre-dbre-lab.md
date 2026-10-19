# Chapter 116 — Enterprise Security, Compliance and Disaster Recovery SRE/DBRE Lab

[Offline simulator](116/security_dr_lab.py) · [Tests](116/test_security_dr_lab.py) · [Project guide](116/README.md)

## Scenario

A Kubernetes-based Python data platform serves PostgreSQL, MongoDB, Elasticsearch, Redis, Kafka and Snowflake. A workload identity compromise coincides with a failed backup verification and regional outage. Establish least privilege, contain risk, assess backup readiness and plan an isolated, auditable recovery without touching production.

## Execute

```bash
cd python/12-enterprise-capstones/labs/116
python -m compileall -q security_dr_lab.py test_security_dr_lab.py
python -m unittest -v test_security_dr_lab.py
python security_dr_lab.py --dry-run
python security_dr_lab.py --failure
```

## Hands-on labs

**Lab 1 — Identity:** Validate expiry, roles and tenant boundaries. Deny cross-tenant reads and unauthorized restore proposals. Design actual OIDC/cloud workload identity and Kubernetes RBAC trust policies.

**Lab 2 — Secrets and encryption:** Check rotation age/encryption flags. Define KMS/HSM ownership, TLS, revocation, dual-key rollout and audit. Do not store secret values in labs.

**Lab 3 — Supply chain:** Validate immutable digest format and policy evidence for signatures, SBOM, critical vulnerabilities and approval. Real integrity requires hashing artifact bytes and verifying trusted signatures.

**Lab 4 — Backup/DR:** Assess backup freshness against RPO, estimated restore duration against RTO, checksum, encryption, immutability, tested restore and human approval. Simulate failure holds.

**Lab 5 — Compliance and incident response:** Map controls to evidence, redact sample logs, write an incident timeline, plan writer fencing, isolated restore, reconciliation and controlled cutover.

## Production incident simulations

| # | Incident | Response |
|---|---|---|
| 1 | Expired workload token | Renew safely |
| 2 | Invalid service identity | Deny |
| 3 | Excessive IAM permissions | Reduce |
| 4 | Cross-tenant access | Block/audit |
| 5 | Unauthorized restore | Deny |
| 6 | Compromised cloud role | Contain/revoke |
| 7 | Kubernetes RBAC escalation | Audit/fix |
| 8 | Secrets leaked to logs | Contain/rotate |
| 9 | Secret rotation overdue | Rotate |
| 10 | Unencrypted secret store | Remediate |
| 11 | TLS certificate expiry | Renew |
| 12 | KMS access failure | Restore trust |
| 13 | KMS key deletion risk | Stop/escalate |
| 14 | Unsigned artifact | Block |
| 15 | Missing SBOM | Block |
| 16 | Critical dependency finding | Triage/block |
| 17 | Unverified digest | Block |
| 18 | CI token overprivilege | Reduce scope |
| 19 | Compliance evidence missing | Hold |
| 20 | Audit log retention failure | Preserve |
| 21 | Backup age exceeds RPO | Hold recovery |
| 22 | Restore exceeds RTO | Escalate |
| 23 | Backup checksum failure | Quarantine |
| 24 | Backup not encrypted | Block |
| 25 | Mutable backup only | Improve isolation |
| 26 | Restore drill missing | Test first |
| 27 | DR approval missing | Hold |
| 28 | PostgreSQL PITR failure | Inspect WAL |
| 29 | MongoDB oplog gap | Snapshot/reconcile |
| 30 | Elasticsearch snapshot mismatch | Validate repository |
| 31 | Redis persistence missing | Plan rebuild |
| 32 | Kafka offset gap | Reconcile replay |
| 33 | Snowflake replication gap | Verify failover |
| 34 | Kubernetes region loss | Restore dependencies |
| 35 | Split-brain primary | Fence old writer |
| 36 | Backup ransomware | Use isolated immutable copy |
| 37 | Cross-region key unavailable | Recover KMS dependency |
| 38 | Telemetry outage during DR | Unknown evidence |
| 39 | Recovery validation fails | Do not cut over |
| 40 | DR rollback needed | Preserve state/audit |

## Production runbooks

**Identity compromise:** isolate workloads, revoke credentials, preserve audit logs, rotate and validate least privilege.

**Secrets:** stage dual-key rollout, verify clients, revoke old versions and record change evidence.

**Supply chain:** quarantine untrusted release, verify provenance, rerun security gates and document exception ownership.

**PostgreSQL:** select tested base backup/WAL PITR point, restore in isolation and reconcile before cutover.

**MongoDB:** validate backup/oplog, restore replica set/shards with compatible metadata and verify writes.

**Elasticsearch:** validate snapshot repository and versions, restore isolated cluster and verify aliases.

**Redis:** validate RDB/AOF or controlled cache rebuild without overloading origin.

**Kafka:** restore broker/topic/ACL/schema and connector/consumer offsets; prevent duplicate side effects.

**Snowflake:** verify replication/failover readiness, roles, integrations, data freshness and RPO.

**DR commander:** declare incident, fence old writers, approve recovery point, restore identity/network/data, validate consistency, cut over, monitor and preserve timeline.

## Final assessment — 100 points

| Domain | Points |
|---|---:|
| Identity, IAM/RBAC and tenant boundaries | 20 |
| Secrets, encryption and supply-chain integrity | 20 |
| Compliance controls and audit evidence | 15 |
| Backup/restore, RPO/RTO and DR architecture | 25 |
| Incident simulations and operational runbooks | 10 |
| Automated tests and reproducibility | 10 |
| **Total** | **100** |

Pass at 90+ with executed offline tests, reviewed threat model, recovery dependency map, approved restore drill and documented rollback.

**Validation:** Offline source and tests published; exact committed execution, CI, real security controls, restore drills and production acceptance pending.
