# Chapter 040 — AWS Stateful Data, Storage, Resilience and Production Operations Capstone

**Part 08 — AWS Infrastructure as Code · Chapter 040/120 (Part 08 capstone)**  
**Audience:** SRE, DBRE, Platform Engineering, Cloud Security, Incident Command  
**Prerequisites:** Chapters 036–039; Terraform >=1.7, Python >=3.9, Bash  
**Execution boundary:** The default lab uses only \`terraform_data\`, never AWS APIs. AWS templates are review-only, require a separate approved account and may incur charges. Publication and authored tests are **not** production acceptance.

## 1. Mission

Engineer a defensible, recoverable AWS stateful platform integrating RDS/Aurora PostgreSQL, S3, EBS, EFS, KMS, backup governance, cross-AZ availability, cross-region disaster recovery, workload monitoring and change control. Prove that infrastructure declaration, application data recovery and SRE/DBRE operational acceptance are distinct requirements.

**Outcomes:** design data tiers and failure domains; choose RPO/RTO targets; define backup/restore and encryption contracts; detect destructive Terraform changes; exercise fail-closed policy tests; document recovery, evidence and rollback; and complete a 100-point capstone.

## 2. Reference architecture

~~~text
Git + CI OIDC + protected environment + approved change
                  |
       Terraform AWS provider + S3 remote state
                  |
  +---------------+------------------+
  |                                  |
VPC private data subnets         Compute / EKS
  |                                  |
RDS/Aurora PostgreSQL <---------- workload IAM
  |  writer + multi-AZ / readers      |
  |  automated backups / PITR         +-- EBS CSI encrypted volumes
  |  manual snapshots                 +-- EFS CSI shared files
  |  KMS CMK / Secrets Manager        +-- S3 object storage
  |                                  |
  +------------ CloudWatch / RDS Performance Insights
  |              CloudTrail / AWS Backup / Config
  +------------ DR: copied backups, tested restore, DNS/fencing
                  |
           Incident command + RPO/RTO evidence
~~~

The platform must be deployed across independent AZ failure domains where supported. Region failover needs replicated/copyable data, IAM/KMS access, network paths, application cutover, writer fencing and tested restoration—not merely a second provider alias.

## 3. Storage selection and workload contracts

| Service | Strength | Operational hazard | Recovery evidence |
|---|---|---|---|
| RDS PostgreSQL | managed relational engine, PITR | failover, storage/engine changes, logical corruption | restored DB query + point-in-time validation |
| Aurora PostgreSQL | distributed storage, readers, failover | cluster/instance changes, parameter compatibility | cluster failover + cross-region restore |
| S3 | durable object storage, versioning | overwrite, lifecycle expiration, bucket/KMS policy | version restore and object checksum |
| EBS | block volume, AZ attachment | wrong AZ, snapshot gap, CSI binding | snapshot restore and filesystem/app validation |
| EFS | regional file system with mount targets | NFS access, throughput, access points | mount recovery and file-level restore |
| AWS Backup | centralized backup policies/vaults | insufficient coverage, retention and KMS | restore job and independent recovery verification |

RDS Multi-AZ improves availability but is **not** a substitute for backup, PITR or cross-region DR. A read replica is not an immutable backup. S3 versioning is not a universal backup strategy; consider immutable/locked backup copies with appropriate governance and retention.

## 4. RDS/Aurora DBRE architecture

Choose engine/version deliberately, review end-of-support and upgrade paths, DB subnet groups across AZs, security groups, parameter groups, storage type/IOPS, encryption and KMS. Production contracts should include backup retention, deletion protection, storage autoscaling limits, Multi-AZ or Aurora HA, log exports and observability.

RDS backup retention supports PITR only within the configured recovery window. RPO/RTO targets must be measured by executing restore, validating data and timing application cutover. A manual snapshot restore creates a separate DB instance/cluster; it does not overwrite the original automatically. Check endpoint changes, DNS TTL, connection pools and replica lag.

For PostgreSQL, test schema migration rollback, transaction consistency, logical backup compatibility, replication slots, long-running transactions and connection saturation. For Aurora, distinguish cluster-level from instance-level configuration and failover behavior.

## 5. S3, EBS and EFS lifecycle

**S3:** block public access, bucket ownership controls, encryption, versioning, access logging and scoped IAM/KMS. Lifecycle policies can irreversibly remove historical object versions; review with data owners and retention policy. For cross-region replication, account for IAM, KMS key availability and replication lag.

**EBS:** encrypt volumes and snapshots, choose gp3/io2 based on IOPS/throughput needs, align CSI volume AZ with pod scheduling, protect against unintended replacement, and test restore with filesystem consistency.

**EFS:** configure mount targets in workload AZs, NFS 2049 security group access, TLS, access points and throughput mode; validate failover, backups and data permissions. EFS sharing does not imply workload-level consistency.

## 6. KMS, IAM and secret recovery

Use scoped roles and short-lived OIDC credentials. Separate deployment, runtime, backup and restore roles. Verify both key policy and IAM authorization, encryption context and cross-region KMS strategy. If the key is disabled or inaccessible, encrypted backups may be unusable even when present. Secrets Manager rotation can invalidate database clients; test staged rotation and reconnect.

Never commit production secrets, Terraform state, plans or DB connection strings. \`sensitive = true\` affects display, not necessarily storage. Limit state access, enable versioning/encryption and maintain an independent recovery process.

## 7. Terraform state and safe change lifecycle

~~~text
PR -> fmt/validate -> Python policy tests -> terraform plan
   -> review resource changes, delete/replace, DB/storage impact
   -> DBRE + security + change approval -> protected apply
   -> observe service SLO -> verify backup/restore -> acceptance
~~~

Use isolated remote state by account/environment/workload and state locking. Protect critical data resources with \`deletion_protection\` where supported and selective \`prevent_destroy\`, but understand these are guardrails, not disaster recovery. Never blindly \`terraform state rm\`, \`force-unlock\` or \`destroy\` a production data resource.

Plan JSON review must inspect action arrays: \`["delete","create"]\` and \`["create","delete"]\` are both replacements. Also review \`after_unknown\`, output changes, resource address moves and drift. This capstone's offline policy checks declared manifest and a simplified plan fixture; it is **not** a complete policy engine for arbitrary AWS plans.

## 8. Executable capstone files

~~~text
labs/chapter-040/
  versions.tf, variables.tf, main.tf, outputs.tf
  environments/dev.tfvars, environments/prod.tfvars
  examples/aws-stateful-data.tf.example
  examples/aws-identity-preflight.sh.example
  stateful-policy.json
  fixtures/stateful-safe.json, stateful-unsafe.json
  fixtures/plan-safe.json, plan-destructive.json
  stateful_gate.py, test_stateful_gate.py
  run-preflight.sh, runbook.md, acceptance.md, .gitignore
~~~

## 9. Lab A — Offline Terraform data contracts

~~~bash
cd infrastructure-as-code/labs/chapter-040
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter040.tfplan
terraform apply chapter040.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected resources: \`terraform_data.database_contract\`, \`terraform_data.object_storage_contract\`, \`terraform_data.volume_contract\`, \`terraform_data.recovery_contract\`. A second unchanged plan should exit 0. Use separate state for prod; never apply production inputs to dev state.

## 10. Lab B — Positive and negative policy tests

~~~bash
python3 stateful_gate.py fixtures/stateful-safe.json fixtures/plan-safe.json stateful-policy.json
python3 stateful_gate.py fixtures/stateful-unsafe.json fixtures/plan-destructive.json stateful-policy.json
python3 -m unittest -v test_stateful_gate.py
bash run-preflight.sh
~~~

Safe must pass; unsafe must fail. Negative tests cover account/region mismatch, DB backups/PITR/Multi-AZ, deletion protection, S3 encryption/versioning/public access, EBS/EFS encryption, KMS decryptability, backup restore evidence, missing RPO/RTO, cross-region recovery, audit and destructive plan actions.

## 11. Lab C — Optional AWS plan-only integration

1. Obtain dedicated sandbox account, budget and approvals.
2. Verify STS identity, account allowlist, provider version and state backend.
3. Review \`examples/aws-stateful-data.tf.example\`; substitute reviewed VPC subnet groups, KMS and IAM values.
4. In a separate working root, run \`terraform init\`, \`terraform validate\` and \`terraform plan\`.
5. Examine RDS engine/version, backup retention, deletion protection, KMS, storage replacement, bucket lifecycle and endpoint access.
6. **Do not apply** the example automatically; real RDS and storage services incur charges and require full design review.

## 12. SRE/DBRE incident scenarios

| Incident | Detection | Immediate response | Recovery validation |
|---|---|---|---|
| RDS writer AZ outage | connection failures, RDS events | verify failover, pool reconnect | read/write and latency SLO |
| Accidental DB table deletion | audit/row count anomaly | stop writes, choose PITR | row counts, checksums, app correctness |
| RDS storage saturation | free storage, latency | halt risky writes, capacity review | headroom, query latency |
| KMS key disabled | decrypt failures | security incident, key/grant review | restored decrypt and backups |
| S3 lifecycle data loss | object missing/version gap | suspend harmful lifecycle | restored version and checksum |
| EBS volume AZ mismatch | pod Pending, CSI errors | inspect PV/PVC/zone | filesystem and app integrity |
| EFS NFS outage | mount timeout, I/O errors | check mount targets/SG/DNS | application read/write |
| Cross-region failover | regional outage | fence old writer, restore/cutover | measured RPO/RTO and consistency |

## 13. Troubleshooting

| Symptom | Cause | Diagnostic action |
|---|---|---|
| RDS \`InvalidDBSubnetGroup\` | missing AZ coverage | inspect subnet group and VPC |
| Snapshot cannot restore | KMS policy or incompatible engine | inspect grants, engine/version, backup |
| Terraform wants to replace DB | immutable property change | freeze, assess data migration and PITR |
| S3 \`AccessDenied\` | bucket/IAM/KMS policy | inspect identity and CloudTrail |
| EBS attachment error | wrong AZ or quota | inspect instance/volume AZ |
| EFS mount timeout | SG 2049, DNS or endpoint | inspect mount targets and NFS path |
| Backup reports success but restore fails | incomplete recovery dependencies | exercise full restore and decrypt |
| Terraform state locked | concurrent apply | wait; incident review before unlock |

## 14. Production runbooks

**Pre-change:** verify identity, state isolation, backups, KMS decrypt and data-owner approval → run gates → inspect full plan → schedule change → canary → validate SLO and restore posture.

**RDS failover:** declare incident, inspect RDS events and endpoints, prevent split-brain, validate writer and replication, refresh connection pools, check queries and application health.

**PITR after logical deletion:** stop damaging writes, select a timestamp before loss, restore to **new** instance, validate data, reconcile intervening writes, perform approved cutover and record data loss.

**KMS recovery:** freeze key changes, verify key state/policies/grants, restore access under dual control, test backup decryptability and audit the incident.

**Regional DR:** confirm writer fencing, network/IAM/KMS availability, backup/replication freshness, restore data, cut over DNS/clients, validate integrity, measure RPO/RTO and perform failback separately.

**Terraform state corruption:** preserve versioned state, stop concurrent writers, restore state metadata under change control, refresh/plan carefully; **state restore does not restore DB data**.

## 15. 100-point enterprise acceptance

| Domain | Points |
|---|---:|
| RDS/Aurora HA, backup and DBRE design | 25 |
| S3/EBS/EFS encryption and lifecycle | 20 |
| IAM/KMS/secrets and state protection | 15 |
| Automated positive/negative plan gates | 15 |
| DR game day, observed RPO/RTO and data integrity | 15 |
| Incident command, observability and evidence | 10 |

**Pass:** >=85 and zero critical failures. Hard stops: no restorable backup, missing production encryption/deletion protection, public data exposure, unapproved data deletion/replacement, wrong account, missing recovery key, or untested DR claims.

## 16. Cleanup and capstone review

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Destroy only disposable local contract resources.

Review: Why does Multi-AZ not replace PITR? What is the difference between a snapshot and a database-consistent restore? Why can KMS block recovery? Why do EBS volumes have AZ constraints? What is the effect of an S3 lifecycle policy on historical versions? How does a failover avoid two writers? Why must RPO/RTO be measured, not declared?

**Part 08 complete on publication of Chapters 036–040.**  
**Next: Chapter 041 — Azure Infrastructure as Code Foundations and Terraform AzureRM Provider.**
