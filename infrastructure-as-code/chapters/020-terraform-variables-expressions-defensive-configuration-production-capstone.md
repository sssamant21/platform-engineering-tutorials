# Chapter 020 — Terraform Variables, Expressions and Defensive Configuration Production Capstone

**Part 04 — Variables and Expressions (final capstone)** · **Audience:** SRE, DBRE and Platform Engineering · **Cost:** $0 core lab · **Status:** Published materials; live lab acceptance pending

## 1. Mission and success criteria

Implement a production-oriented Terraform input-contract and transformation pipeline using typed variables, locals, comprehensions, conditional expressions, null handling and safe fallbacks. Build a stable service × availability-zone topology with no-cloud terraform_data resources, enforce mandatory production backup, encryption, deletion protection, capacity and ownership requirements, review plan JSON for destructive changes, and demonstrate recovery. A passing local exercise is **not** certification for cloud production.

The capstone integrates Chapters 016–019. Passing score is 85/100 with no critical safety violation; collect real execution evidence before marking lab acceptance complete.

## 2. Architecture and trust boundaries

~~~text
reviewed Git commit / pinned CLI / isolated backend
                       |
       typed environment-specific tfvars
                       |
     HCL validation + normalized locals
                       |
 service × zone matrix / stable for_each keys
                       |
 terraform_data resources + lifecycle preconditions
                       |
      saved plan -> plan JSON inspection
                       |
  Python plan policy + input policy + unit tests
                       |
 owner + DBRE approval -> apply -> verify -> audit
                       |
      drift check / recovery / destroy
~~~

**Trust boundaries:** A dev/prod label does not prove AWS account, Azure subscription, GCP project or backend identity. The offline input policy validates a JSON fixture; it does not parse HCL. The plan policy inspects Terraform plan JSON actions; it cannot prove that real backups exist or that an approval ticket is authentic. Real production CI must bind approved commit, backend, identity, plan artifact and signed authorization.

## 3. Theory synthesis: Chapters 016–019

**Typed variables:** string, number, bool, list, set, map, object and tuple provide contracts. Defaults are explicit policy decisions; nullable=false prevents unexpected null for required values. sensitive=true only redacts some displays and does not remove secrets from state or saved plans.

**Expressions and locals:** locals normalize reusable derived values. Conditional expressions must have compatible result types. for expressions transform/filter collections; grouping mode (...) preserves repeated group keys. flatten, merge, sort, distinct, keys and setproduct require careful deterministic ordering and size limits.

**Stable addresses:** for_each over maps with stable nonsensitive keys minimizes accidental replacement. Rename a key only with a reviewed address migration (moved blocks where applicable). Avoid count index churn and unknown apply-time keys.

**Defensive configuration:** null is absence, unknown is deferred evaluation. try handles dynamic evaluation errors; can tests evaluability; lookup and coalesce provide fallbacks. A fallback for an optional display label may be safe; a fallback disabling database backups is not. Lifecycle preconditions and hard CI gates protect critical invariants. Terraform check assertions can warn rather than fail.

**Change lifecycle:** fmt -> init -> validate -> tests -> plan -> policy -> owner/DBRE approval -> apply -> observe -> audit. plan -detailed-exitcode returns 0 for no changes, 1 for errors, 2 for differences. State is not a data backup; protect it and all plan files as potentially sensitive.

## 4. Repository layout and prerequisites

~~~text
labs/chapter-020/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  environments/dev.json
  environments/prod.json
  capstone-policy.json
  sample-plan.json
  capstone_policy.py
  test_capstone_policy.py
  run-preflight.sh
  .gitignore
~~~

Terraform >=1.5 or approved compatible OpenTofu; Python 3.9+; Bash, Git and WSL2 on Windows if needed. Built-in terraform_data requires no cloud provider or external plugin. Use a disposable directory and local state; never share state/plan files.

## 5. Lab A — Typed input and expression review

Review variables.tf and main.tf. Inputs include environment, owner, change ticket, zones, service map, database backup/encryption/deletion protection and replication settings. Locals expand enabled services into a deterministic service×zone map and attach mandatory tags last. Production resource lifecycle preconditions require database safety and at least three replicas for each enabled service.

~~~bash
cd infrastructure-as-code/labs/chapter-020
terraform fmt -check -recursive
terraform init -input=false
terraform validate
terraform console -var-file=environments/dev.tfvars
~~~

In console evaluate:

~~~hcl
sort(distinct(var.zones))
[for name, spec in var.services : name if spec.enabled]
{ for name, spec in var.services : spec.tier => name... }
coalesce(null, "safe-display")
try(var.services["missing"].replicas, 0)
setproduct(keys(var.services), var.zones)
~~~

Exit with exit. Explain why an optional display fallback is safe while production backup fallback is not.

## 6. Lab B — Plan, policy, apply and idempotence

~~~bash
python3 capstone_policy.py environments/dev.json sample-plan.json capstone-policy.json
python3 capstone_policy.py environments/prod.json sample-plan.json capstone-policy.json
python3 -m unittest -v test_capstone_policy.py
bash run-preflight.sh
terraform plan -var-file=environments/dev.tfvars -out=chapter020.tfplan
terraform show -json chapter020.tfplan > chapter020-plan.json
python3 capstone_policy.py environments/dev.json chapter020-plan.json capstone-policy.json
terraform apply chapter020.tfplan
terraform state list
terraform output -json
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected: four workload instances and one audit record, with a subsequent no-change exit 0. The plan gate denies delete/replace and malformed actions. The example JSON inputs and tfvars must be reviewed for parity; CI should generate both from a canonical source rather than trusting duplicated files.

## 7. Lab C — Production and negative drills

~~~bash
terraform plan -var-file=environments/prod.tfvars
terraform plan -var-file=environments/prod.tfvars -var='database_backup_enabled=false'
terraform plan -var-file=environments/prod.tfvars -var='database_encrypted=false'
terraform plan -var-file=environments/prod.tfvars -var='database_deletion_protection=false'
terraform plan -var-file=environments/prod.tfvars -var='database_replicas=1'
terraform plan -var='environment=production'
terraform plan -var='zones=[]'
~~~

The unsafe production and malformed inputs must fail validation or lifecycle preconditions. Do not apply a prod plan against the existing dev lab state; use a separate disposable directory/state for each environment. The offline prod fixture is fictional and requires no cloud access.

For Python policy negative tests, inject missing owner, ticket, null backups, low replicas, invalid zones, excessive service×zone expansion, delete/replace actions and malformed plan JSON. Restore valid inputs after drills.

## 8. Lab D — Address migration and incident simulation

In a separate disposable copy, rename the api key to api-v2 and inspect the plan for address churn. Restore the original input without applying. For a legitimate migration, use reviewed moved blocks to map each old address to its new address; verify the plan and provider identity before production rollout.

Simulate a stale saved plan by explaining what happens when state changes between plan and apply; do not manipulate a live remote backend. For drift, compare HCL, state and real resources in a separately authorized cloud lab; terraform_data does not demonstrate actual cloud drift.

## 9. Lab E — Cleanup and evidence

~~~bash
terraform plan -destroy
terraform destroy
terraform state list
git status --short
~~~

Expected: empty state. Record sanitized CLI versions, fmt/validate output, policy test results, resource addresses, plan exit codes, owner approval, rollback steps and cleanup. Do not commit state, saved plans, credentials, or raw plan JSON.

## 10. Production SRE/DBRE scenarios

**RDS/Aurora:** Generate instance/AZ topology with stable IDs. Require backups, encryption, deletion protection, PITR and restore drill evidence; inspect any replacement for data loss.

**PostgreSQL:** Derive HA replica and connection-pool settings with bounded inputs; validate WAL, synchronous commit, failover and storage growth.

**Elasticsearch/OpenSearch:** Normalize data-node pools and disk tiers. Prevent a missing IOPS input from silently selecting undersized storage; review shard placement, merge pressure and search latency.

**EKS:** Expand node pools across zones with stable for_each keys. Require PDB checks, surge headroom, max-node caps and workload identity verification.

**AKS:** Validate subscription, tenant, managed identity and remote state independently of environment labels; assess node-pool disruptions.

**Redis:** Enforce HA replica and memory headroom constraints, client retry behavior and failover test evidence.

**Snowflake:** Generate warehouse maps with owner/cost center, allowed size and auto-suspend policy; independently verify grants and spend.

**Kafka/MSK:** Build broker/AZ inventory deterministically; enforce replication factor, quorum, partition placement and maintenance sequencing.

## 11. Troubleshooting matrix

| Symptom | Likely cause | Safe response |
|---|---|---|
| Invalid variable | Type, range or enum mismatch | Fix reviewed inputs |
| Invalid index/attribute | Missing optional map/object key | Normalize with safe explicit fallback |
| Unknown for_each | Apply-time or sensitive keys | Use known stable input keys |
| Duplicate key | Canonicalization collision | Reject ambiguous mapping |
| Unexpected replacement | Key rename or immutable field | Stop and review migration |
| Prod safety precondition fails | Backup/HA/encryption disabled | Block release; restore required controls |
| Policy DENY | Delete, replace, missing ticket | Correct change and reapprove |
| Stale plan | State changed after planning | Replan and obtain fresh approval |
| State lock | Concurrent writer | Coordinate; never blind force-unlock |
| Drift/partial apply | Remote mutation or interrupted apply | Preserve data, inspect state and actual resources |

## 12. Operational runbooks

**Standard production change:** confirm environment, account/backend and Git SHA -> owner/DBRE ticket -> input and policy tests -> fmt/init/validate -> plan and JSON inspection -> destructive-action review -> backup/PITR/restore evidence -> approval -> apply exact reviewed plan -> verify SLOs, data and cost -> audit.

**Destructive DB change:** halt -> inspect addresses and replacement reason -> validate recovery objectives, snapshots and restore drill -> migrate/reject -> replan -> reapprove -> controlled window.

**Unexpected address churn:** freeze pipeline -> compare old/new keys -> add explicit moved blocks if semantically same resource -> rerun policy -> review state and plan -> controlled apply.

**Partial apply:** prevent concurrent writers -> identify actual remote objects and state entries -> recover service/data first -> reconcile under new approved plan -> RCA/COA.

**Secret or state exposure:** contain artifacts -> revoke/rotate credentials -> inspect logs/runner IAM -> remediate and record incident.

## 13. Acceptance rubric (100 points)

| Area | Points |
|---|---:|
| Typed inputs and defensive validation | 20 |
| Deterministic collections and resource addresses | 20 |
| Plan/apply/idempotence evidence | 15 |
| Python policy and negative tests | 20 |
| SRE/DBRE runbooks and approvals | 15 |
| Cleanup, evidence and artifact hygiene | 10 |

Pass 85+ with no critical failure. Automatic failure for production data deletion without approval, missing backup/restore strategy, bypassed state locks, or committed secrets/state. Tests are **authored**, not claimed to have run.

## 14. Final knowledge assessment

Explain object optional defaults, null vs unknown, try vs can, grouped for expressions, setproduct explosion, for_each key churn, sensitive plan handling, production hard gates, why state is not backup, and the DBRE decision sequence for a destructive RDS plan.

**Part 04 complete upon publication of Chapters 016–020; learner lab acceptance remains separate.**

**Next:** Chapter 021 — Terraform Provider Configuration, Aliases, Version Constraints and Authentication.
