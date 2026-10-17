# Chapter 029 — Terraform State Migration, Backup, Restore and Disaster Recovery

**Part 06 — State and Remote Backends** · **Audience:** SRE/DBRE/Platform Engineering · **Lab:** offline Terraform and Python · **Status:** published; live acceptance pending

## Objectives

Design and rehearse safe Terraform state backup, backend migration, restore and disaster recovery. Understand lineage, serial, encryption, state locking, source/destination identity, retention, versioned snapshots, recovery point and time objectives, stale-plan invalidation and post-recovery reconciliation. Create an executable no-cloud lab, a deterministic DR manifest policy, negative tests, incident simulations and production runbooks.

## 1. Production architecture

~~~text
Git revision + verified caller + change ticket
                   |
        Freeze concurrent state writers
                   |
      Verify source backend / lineage / serial
                   |
       Encrypted, versioned state snapshot
                   |
      Integrity check + access + retention
                   |
       Migration or DR recovery decision
                   |
     Destination backend + locking + IAM
                   |
    Restore / migrate under change control
                   |
  Fresh plan, real-resource identity, health
                   |
  SRE/DBRE acceptance + audit + rollback
~~~

**Key distinction:** Terraform state DR restores the infrastructure *mapping*, not database contents, Kafka offsets, Elasticsearch shards, Redis keys or Kubernetes workload data. Application and data DR require separate backups, PITR, replicas, restore drills and validated RPO/RTO.

## 2. State backup design

State may contain secrets, private endpoint information, provider attributes and resource IDs. Encrypt snapshots in transit and at rest, restrict IAM, version objects, protect against accidental deletion and set retention according to policy. Avoid placing raw state in Git, tickets, CI logs or general artifact storage. The local lab's \`terraform state pull\` output is sensitive and must be stored in a private restricted location, not committed.

Capture a backup manifest with: environment, backend source/destination, owner, change ticket, snapshot ID, lineage, serial, SHA-256 checksum, encryption, versioning, retention, lock/freeze evidence, recovery drill status and independent object-health verification. A checksum detects accidental snapshot changes; it does **not** prove the snapshot is authorized, confidential or free of malicious alteration. In production, sign/attest manifests and verify cloud audit logs.

## 3. Backend migration fundamentals

\`terraform init -migrate-state\` attempts to move existing state into a newly configured backend. \`terraform init -reconfigure\` accepts new backend configuration **without migrating existing state**. Before migration: pin Terraform version; verify source/destination account and key; ensure target bucket/container exists, is encrypted and versioned, and supports locking; backup source; freeze all writers; test migration on disposable state. After migration: verify state lineage/serial, resource addresses, actual remote identities, permissions, lock behavior and no unexpected plan changes.

Never treat \`terraform state push\` as routine recovery. It can overwrite authoritative state; use only with documented emergency procedure, verified backups, exclusive ownership and the CLI's safety checks. Do not bypass lineage/serial protections or force state push to make a mismatch disappear.

## 4. RPO, RTO and recovery dependencies

- **State RPO:** maximum acceptable loss of recent state mappings; determined by snapshot/version cadence and backend history.
- **State RTO:** time to restore backend availability, authoritative state, locks and a verified plan.
- **Application RPO/RTO:** separate measures of data loss and service restoration; state recovery alone cannot satisfy them.
- **Recovery order:** restore control-plane identity, backend and locks; identify authoritative state; reconcile real resources; then validate application/database recovery.
- **Failure domain:** state and backup copies must not share an unmitigated account, region, credential or deletion failure domain.

## 5. Lab files

~~~text
labs/chapter-029/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  dr-policy.json
  sample-dr-safe.json
  sample-dr-unsafe.json
  sample-state.json
  state_dr_policy.py
  test_state_dr_policy.py
  snapshot_manifest.py
  run-preflight.sh
  examples/backend-migration.sh.example
  examples/s3-backend.tf.example
  .gitignore
~~~

The executable Terraform lab uses only \`terraform_data\` and local state. Backend migration snippets are **illustrative**; no cloud credentials or cloud infrastructure are needed. The Python validator checks declared controls and synthetic state metadata, not actual cloud IAM, object versioning or lock acquisition.

## 6. Lab A — Establish an isolated state baseline

~~~bash
cd infrastructure-as-code/labs/chapter-029
terraform version
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter029.tfplan
terraform apply chapter029.tfplan
terraform state list
terraform output -json
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected: \`terraform_data.network\`, \`terraform_data.database\`, \`terraform_data.application\`; second plan exits 0. **Never apply production tfvars against the same dev state.** Production examples are configuration-only until a separately isolated state is prepared.

## 7. Lab B — Private snapshot and integrity check

~~~bash
umask 077
mkdir -p private-evidence
terraform state pull > private-evidence/state.snapshot.json
python3 snapshot_manifest.py private-evidence/state.snapshot.json > private-evidence/snapshot-metadata.json
sha256sum private-evidence/state.snapshot.json
~~~

The manifest generator emits only **lineage, serial, Terraform version, SHA-256, size and resource count**; it never prints resource attributes or outputs. It intentionally does not claim encryption, backup retention or restore success. \`private-evidence\` is Git-ignored, but that does not provide encryption. Protect it using OS/storage controls; remove it according to the security retention policy.

## 8. Lab C — Validate DR policy

~~~bash
python3 state_dr_policy.py sample-dr-safe.json sample-state.json dr-policy.json
python3 state_dr_policy.py sample-dr-unsafe.json sample-state.json dr-policy.json
python3 -m unittest -v test_state_dr_policy.py
bash run-preflight.sh
~~~

Safe fixture must pass; unsafe fixture must fail. The DR policy checks environment and ticket, source/destination separation, backup encryption, versioning, lock/freeze, restore test, snapshot identity, lineage/serial consistency, retention and RPO/RTO. **A passing JSON fixture is not evidence of a real backup or restore drill.**

## 9. Lab D — Simulated backend migration

1. Clone the lab into **two disposable work directories** and create a baseline local state in the source.
2. Back up the source state and record lineage, serial and resource addresses.
3. Review \`examples/backend-migration.sh.example\` as a checklist. Do not execute its placeholder remote backend commands without an approved sandbox.
4. In an approved cloud sandbox, prepare destination backend with encryption, versioning, IAM and locking. Reconfigure the Terraform backend block and run \`terraform init -migrate-state\` under an exclusive maintenance window.
5. Compare state lineage, serial, addresses and remote objects; run a fresh plan. No unintended creation/deletion should be present.
6. Record audit evidence and rollback decision. Never delete source state until target acceptance and retention requirements are met.

## 10. Lab E — Recovery and failure injection

- Change lineage or serial in a **copy** of sample-state.json; validator must deny a mismatch.
- Set snapshot SHA-256 to malformed value; deny.
- Disable encryption, versioning, locking, freeze or restore test; deny.
- Set RPO/RTO to zero or negative; deny.
- Reuse source as destination backend; deny.
- Change retention below policy minimum; deny.
- Simulate expired IAM identity and backend 403; follow identity runbook.
- Simulate partial migration with two divergent state versions; freeze and determine authoritative state.
- Simulate stale saved plan after recovery; discard and regenerate.
- Simulate a DB outage with healthy Terraform state; follow separate DB recovery, not state restore.

## 11. Production SRE/DBRE scenarios

| Platform | State DR boundary | Independent validation |
|---|---|---|
| RDS/Aurora | cluster/instance/subnet/KMS mappings | PITR, snapshot restore, replica health |
| PostgreSQL | instance/parameter/role resources | WAL, recovery timeline, data consistency |
| Elasticsearch/OpenSearch | domain/index infrastructure mapping | snapshots, shard allocation, search SLO |
| EKS/AKS | cluster/node/IAM/network state | control plane, workloads, PDBs, storage |
| Redis | cache topology and settings | RDB/AOF, replication, client behavior |
| Snowflake | warehouse/grant/integration mapping | privileges, query outcomes, cost |
| Kafka/MSK | broker/network/configuration mapping | ISR, partitions, offsets, consumer lag |

## 12. Troubleshooting matrix

| Symptom | Likely cause | Safe response |
|---|---|---|
| State key missing | wrong backend/workspace | stop; verify identity and key |
| Lineage mismatch | wrong state history | freeze; compare trusted versions |
| Serial regression | stale snapshot | reconcile actual objects before restore |
| Lock held | active writer | verify owner; do not force-unlock blindly |
| Backend 403 | IAM or identity expiry | verify caller and scoped permissions |
| Migration incomplete | network/credential failure | preserve both copies, select authority |
| Plan wants to recreate everything | empty/wrong state | stop; do not apply |
| Raw state exposed | unsafe artifact handling | contain, rotate, audit |
| State restored, app unhealthy | data/infra mismatch | run DBRE/service recovery |
| DR drill exceeds RTO | slow identity/backend restore | improve automation and rehearse |

## 13. Production runbooks

**Scheduled state backup:** verify backend/identity → lock/freeze or consistent versioned snapshot → encrypted copy → checksum and lineage/serial → retention → protected access → restore test → audit.

**Backend migration:** change approval → source/destination verification → freeze → backup → staging rehearsal → migrate-state → lineage/address comparison → fresh plan → application health → retire source after rollback period.

**State corruption:** stop all writers → preserve forensic evidence → find authoritative version → verify cloud resources → restore with exclusive lock and CLI safeguards → fresh plan → owner approval → verify SLO/data → RCA.

**Backend outage:** isolate pipeline → restore backend/identity/permissions → verify locks and versions → resume only after clean plan.

**Database DR:** independently recover data, WAL/PITR/snapshots, replicas and application connections; then reconcile Terraform state.

## 14. Acceptance (100 points)

| Control | Points |
|---|---:|
| State backup architecture, encryption and retention | 20 |
| Backend migration and lock safety | 20 |
| Snapshot metadata and policy/tests | 20 |
| DR drills, RPO/RTO and recovery | 25 |
| SRE/DBRE runbooks and evidence | 15 |

Pass 85+ with no critical failure. Critical: leaked raw state, unverified source/destination, no recoverable backup, unsafe state push, no locking, cross-environment state reuse or conflating state DR with database PITR. Record sanitized CLI versions, state address summary, checksum metadata, policy/test evidence and approved cleanup.

## 15. Cleanup

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Only destroy the isolated local lab. Preserve sensitive evidence according to retention policy; do not upload state or plans to GitHub.

## 16. Knowledge check

How do lineage and serial differ? What is the purpose of state versioning? Why is SHA-256 not proof of backup authorization? How does \`init -migrate-state\` differ from \`init -reconfigure\`? What makes a state snapshot recoverable? Why is force-push dangerous? How do state RPO/RTO differ from database RPO/RTO? How do you handle divergent state versions? What must be validated after migration? Why must a stale plan be discarded?

**Next:** Chapter 030 — Terraform State and Remote Backend Production Operations Capstone.
