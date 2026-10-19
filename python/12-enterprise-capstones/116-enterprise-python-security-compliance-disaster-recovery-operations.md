# Chapter 116 — Enterprise Python Security, Compliance and Disaster Recovery Operations

**Part 12 — Enterprise Capstone Projects | Chapter 116/120 | Python 3.11+**

[Complete SRE/DBRE lab](labs/116-enterprise-security-compliance-disaster-recovery-sre-dbre-lab.md) · [Executable offline project](labs/116/README.md)

## Learning objectives

Build secure, auditable Python platform services with workload identity, IAM/RBAC, secrets management, encryption, software supply-chain assurance, compliance evidence, backup/restore and tested RPO/RTO disaster recovery. Integrate PostgreSQL, Elasticsearch/OpenSearch, MongoDB, Redis, Kafka, Snowflake and Kubernetes into an enterprise resilience model. Practice policy decisions offline before designing authorized staging drills.

## Enterprise reference architecture

```text
                 OIDC / Cloud IAM / Kubernetes workload identity
                                    |
          API gateway -> Python APIs / workers / schedulers
                            |                |
                    RBAC/ABAC/tenant       secrets manager
                            |                |
        PostgreSQL -- MongoDB -- Kafka -- Elasticsearch -- Redis
                            |                         |
                  CDC/outbox pipelines             Snowflake
                            |
            encrypted snapshots / PITR / WAL / oplog
                            |
       immutable offsite backup -> isolated recovery account/region
                            |
       policy-as-code + audit logs + OTel/Prometheus + SIEM
                            |
       incident command -> restore drill -> reconciliation -> sign-off
```

## 1. Threat modeling and infrastructure boundaries

Inventory identities, workloads, databases, network paths, secrets, artifacts, backups and sensitive data. Model spoofing, privilege escalation, credential theft, lateral movement, supply-chain tampering, ransomware, data exfiltration, region loss and accidental deletion. Define control-plane/data-plane boundaries, zero-trust verification, egress allowlists, Kubernetes NetworkPolicies and segmentation. Treat workload compromise and backup compromise as separate failure domains.

## 2. Workload identity, IAM, RBAC and tenancy

Prefer short-lived, audience-bound federated workload identities over long-lived static keys. On EKS use reviewed IRSA or EKS Pod Identity integration; on AKS use Microsoft Entra Workload ID; on GKE use Workload Identity Federation for GKE. Verify trust policy, service-account binding, audience, token expiration, least-privilege resource ARNs and cloud audit events. Distinguish Kubernetes RBAC (API access) from application RBAC and datastore permissions. Enforce tenant boundaries at every data adapter, not only the ingress.

A sample permissions matrix:

| Role | Read inventory | Plan backup | Review audit | Propose restore |
|---|---|---|---|---|
| reader | Yes | No | No | No |
| operator | Yes | Yes | No | No |
| security | Yes | No | Yes | No |
| dr_admin | Yes | Yes | No | Yes |

A restore proposal is not execution authorization. Require separation of duties and a reviewed change ticket for destructive or production restore actions. The offline simulator uses illustrative role flags, **not token validation or real authorization**.

## 3. Secrets and cryptographic controls

Use a managed secrets service and KMS/HSM-backed keys, encrypted transport (TLS/mTLS where justified), envelope encryption at rest and automated rotation. Do not log tokens, database passwords, private keys or patient data. Establish key ownership, rotation interval, revocation, dual-key transition and break-glass audit. Prefer identity-based database authentication where supported; avoid embedding credentials in GitHub Actions, container images or Terraform state. Python application encryption should use a reviewed library and vetted modes, not custom cryptography. The lab checks **metadata only**, never generates/stores real key material.

## 4. Software supply chain and CI/CD security

Pin dependencies and container images to reviewed immutable versions/digests, generate SBOMs, scan SAST/dependencies/secrets/IaC, verify artifact signatures and provenance, enforce protected branches and least-privilege CI tokens. Use policy-as-code admission checks and signed release manifests. Document exceptions with expiration, owner and compensating controls. A 64-character SHA-256-looking string is not proof of artifact integrity: real verification must hash the actual artifact and validate trusted signatures/attestations. The offline supply-chain gate only evaluates supplied evidence flags.

## 5. Compliance and evidence

Map organizational requirements (SOC 2, HIPAA where applicable, ISO 27001, internal policies) to technical controls and accountable owners. Capture access reviews, encryption settings, vulnerability triage, change approvals, backup job evidence, restore drill results, incident timelines and data retention/deletion records. Preserve audit immutability and restrict access to evidence. A green control checklist is not a compliance certification or legal conclusion.

## 6. Backup and recovery design

Define recovery scope by workload, dependency, data classification and region. RPO = maximum tolerable data loss; RTO = maximum tolerable service recovery time. Design retention, encryption, immutability, offsite/isolated copies, independent identity/key access and restoration sequencing. Validate **restorability**, not merely backup job success.

- **PostgreSQL:** physical base backups plus WAL/PITR, logical backups for selected use cases, replication slots, roles/extensions and transaction consistency.
- **MongoDB:** operator/Ops Manager snapshots or reviewed backup tools, replica consistency, oplog coverage, sharded-cluster considerations and point-in-time recovery.
- **Elasticsearch/OpenSearch:** repository snapshots, index templates, aliases, cluster metadata, version compatibility; do not copy live data directories as backups.
- **Redis:** persistence RDB/AOF and tested recovery where Redis is authoritative; if purely cache, rebuild safely without overloading origin.
- **Kafka:** replicated durable topics, configuration/ACL/schema backup, offsets, connector checkpoints and a disaster recovery replication strategy; broker replication alone is not a complete DR plan.
- **Snowflake:** Time Travel/Fail-safe within supported retention, replication/failover groups where configured, stages/integration definitions and region/account recovery; validate edition/features and retention.

## 7. DR orchestration and fencing

Establish declared recovery dependencies: identity/KMS/network -> stateful stores -> Kafka/CDC -> API/workers -> derived search/cache -> analytics -> validation. Stop or fence old writers before promoting a new primary to prevent split-brain. Require isolated restoration, backup checksum and decryptability checks, restore rehearsal, source-to-target reconciliation, approved DNS/traffic cutover, rollback and an audit record. Cross-region failover needs explicit RPO/RTO measurements and data consistency sign-off.

## 8. Observability and DR SLOs

Measure last verified recoverable point, backup age, failed jobs, immutable-copy coverage, restore duration, PITR verification, replication lag, WAL/oplog retention, Kafka lag, KMS availability, secrets expiry, unauthorized access attempts and recovery drill pass rate. Alert on breached backup age/RPO, stale evidence, failed restore drills and unexpected IAM grants. During a telemetry outage, status is unknown, not pass.

## 9. Threat and incident response

**Compromised workload identity:** revoke/disable credentials, isolate pods, preserve evidence, rotate secrets, audit access and re-establish least privilege.

**Ransomware/backup tampering:** isolate accounts, protect immutable copies, validate clean recovery point and coordinate Security/Legal before restoration.

**PostgreSQL accidental deletion:** freeze writes where necessary, identify PITR timestamp, restore into isolated environment, reconcile and approve cutover.

**MongoDB replica/region loss:** validate backups, oplog window, cluster metadata and restore ordering.

**Elasticsearch snapshot corruption:** verify repository integrity and compatibility, restore to isolated cluster and validate aliases/mappings.

**Kafka split-brain/replay:** fence producers, reconcile offsets, deduplicate downstream effects and audit recovery.

**Snowflake account/region incident:** verify replication configuration, roles, external integrations, recovery points and application cutover.

**Kubernetes control-plane compromise:** rotate credentials, rebuild trusted workloads from signed artifacts, audit admission and verify data-plane integrity.

## 10. Production runbooks

**Identity emergency:** contain, audit, revoke, rotate, validate workload reauthentication and monitor for recurrence.

**Secrets rotation:** prepare dual credential/key transition, stage rollout, validate clients, revoke old version and record evidence.

**Supply-chain block:** quarantine unsigned/vulnerable artifact, verify provenance, fix and rerun gates; never bypass silently.

**Backup verification:** inspect backup freshness, checksums, encryption, immutable retention, offsite copy and isolated restore test.

**DR invocation:** declare severity/commander, select verified recovery point, fence old writers, approve plan, restore dependencies, reconcile, test SLOs, cut over and monitor.

**DR rollback:** stop conflicting writers, assess data divergence, restore safe traffic path and preserve forensic timeline.

## 11. Lab and assessment

The [complete lab](labs/116-enterprise-security-compliance-disaster-recovery-sre-dbre-lab.md) and [offline Python project](labs/116/README.md) provide role/tenant policy decisions, secret rotation metadata, backup freshness/integrity/encryption checks, RPO/RTO recovery gates, supply-chain evidence checks, compliance checklist, redacted sample logs and automated tests.

**Validation boundary:** No actual IAM tokens, cryptographic operations, secrets, cloud resources, backup/restore, network access or production mutations. The simulator is an advisory teaching aid, not a security enforcement engine. Exact committed tests, CI, live recovery drills, penetration testing and production acceptance remain pending.

**Next:** Chapter 117 — Enterprise Python Capacity Planning, Performance Engineering and FinOps Capstone.
