# Chapter 060 — OpenTofu and Terragrunt Enterprise Platform Engineering, Reliability and Migration Capstone

**Part 12 capstone (056–060) · Chapter 060/120 · SRE/DBRE production engineering**  
**Prerequisites:** Chapters 056–059; Python 3.9+, OpenTofu >=1.7, version-pinned Terragrunt, sandbox identity.  
**Safety:** This chapter publishes executable offline contracts and policy tests. It does **not** authorize production migration, cloud apply, state push, force-unlock or database deletion. Live infrastructure and restore acceptance require independent evidence and approval.

## 1. Capstone mission and outcomes

Design, test and defend an enterprise IaC platform that transitions reviewed Terraform roots to OpenTofu, orchestrates them through Terragrunt, maintains exclusive remote-state ownership and delivers reliable network, Kubernetes and stateful data services. Prove provider/module compatibility, dependency graph safety, secure CI/CD, drift governance, SLO-based change controls, backup and disaster recovery, incident handling and audited acceptance.

Deliverables: architecture decision record (ADR), ownership matrix, compatibility matrix, state inventory, pinned toolchain/module lockfile, DAG, plan evidence, security policy, automated tests, game-day records, DBRE runbooks and scored assessment.

## 2. Reference architecture

~~~text
Protected Git + signed PR + CI OIDC identity
              |
    static lint / security / unit tests
              |
  Terraform -> OpenTofu compatibility gate
              |
   Terragrunt effective-config + DAG gate
              |
    native plan adapter / policy review
              |
    SRE + DBRE + security approvals
              |
      one writer per remote state key
              |
    network -> IAM -> Kubernetes
         \         \         |
          \---------> data -> apps
                     |
         PostgreSQL / MongoDB / Redis
                     |
    SLO, backup/PITR, restore, drift, cost
~~~

**Root boundaries:** network, identity, cluster, platform add-ons, tenant controls, stateful databases and applications must have independently reviewed ownership, backend keys and CI promotion. GitOps controllers own application manifests; OpenTofu/Terragrunt own agreed infrastructure and platform boundaries. Prevent double writers for Kubernetes/Helm resources.

## 3. Terraform-to-OpenTofu migration

**Discovery:** inventory every root, workspace, backend, lineage, serial, provider source/version/checksums, module source/revision, outputs, import/moved blocks, secrets in state, CI runner and current lock owner.

**Compatibility:** pin tested CLI releases. Validate HCL language constructs, provider registry and schemas, module contracts, backend locking, state serialization and tool-specific features. Terraform and OpenTofu releases can diverge; never assume state is safely round-trippable.

**Cutover:** freeze competing writers, snapshot encrypted state and prove isolated restore; duplicate a disposable root; initialize OpenTofu against a **separate** test backend; compare planned actions and resource identities; perform controlled cutover only with approved rollback/forward-repair strategy. Keep the previous executor disabled after handover. Never let Terraform and OpenTofu concurrently write the same state.

**Rollback:** tool rollback does not necessarily reverse state format or remote resources. Preserve baseline, lockfile, state versions and provider schemas. Reconcile actual infrastructure before choosing isolated restore or forward repair.

## 4. Terragrunt enterprise orchestration

- **DRY configuration:** root include, account/region metadata, explicit environment inputs, generated provider/backend settings. Review include merge precedence and locals scope.
- **DAG:** use \`dependency\` for output contracts, \`dependencies\` for ordering; detect cycles and stale outputs. Do not use mock outputs for production apply.
- **State:** unique \`org/account/env/region/unit\` key, encryption, versioning, backend-supported locking, scoped IAM and audited restore.
- **Concurrency:** serialize state writers and bound cross-unit parallelism to cloud quotas and DB capacity.
- **Partial failures:** Terragrunt is not transactional. Record successful units and state serials; stop downstream, reconcile resources, re-plan and resume by approval.
- **GitOps:** define a single authoritative writer for each Kubernetes/Helm object and use drift review before reconciliation.

## 5. Security, policy and CI/CD

Use short-lived workload identity/OIDC, protected environments, immutable module/provider/tool versions, pinned CI executors, encrypted plan artifacts and least privilege. Prevent untrusted PR workflows from accessing production credentials. Review native \`tofu show -json\` plans with a tested adapter: deny unexpected \`delete\`, \`delete/create\`, replacement paths, public ingress, unencrypted storage and unapproved stateful operations. The offline fixture gate below is intentionally **not** that native adapter.

CI stages: discovery → formatting → dependency graph/backend uniqueness → contract tests → sandbox plan → native plan policy → SRE/DBRE/Security approval → serialized apply → SLO/DB health/backup verification → audit evidence. Re-plan when approved artifacts become stale.

## 6. Reliability and DBRE requirements

| Workload | Change safety | Health / SLO | Recovery evidence |
|---|---|---|---|
| PostgreSQL/RDS/Aurora | block unapproved replace, preserve PITR | connections, replication lag, locks, query latency | snapshot/PITR restore drill |
| MongoDB | preserve replica majority and oplog window | replication lag, election stability, cache | restore and rejoin proof |
| Redis | cap client connection bursts, preserve persistence | p99, evictions, replication | failover/rebuild evidence |
| Kafka/MSK | preserve broker quorum and partitions | under-replicated partitions, lag | broker/AZ recovery |
| Elasticsearch/OpenSearch | avoid shard/volume disruption | rejection, IOPS, disk watermark | snapshot and shard recovery |
| Kubernetes | PDB, topology spread, probe and rollout gates | API errors, 5xx, latency | node/AZ outage simulation |

Define availability, latency, durability and change-failure SLIs; require burn-rate alerting, error-budget review, capacity forecasts and rollback triggers. Never claim RPO/RTO compliance without measured restore timing and data-loss assessment.

## 7. Executable Lab A — Offline OpenTofu contracts

~~~bash
cd infrastructure-as-code/labs/chapter-060
tofu version
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
tofu plan -var-file=environments/dev.tfvars -out=dev.tfplan
tofu apply dev.tfplan
tofu output -json
tofu state list
tofu destroy -var-file=environments/dev.tfvars
~~~

Five \`terraform_data\` resources assert migration, state, graph, delivery and DBRE recovery controls. Production tfvars require all safeguards to be declared, but do not configure a live backend or validate actual backups. Use only disposable local state.

## 8. Executable Lab B — Policy and automated negative tests

~~~bash
python3 capstone_gate.py fixtures/capstone-safe.json fixtures/plan-safe.json capstone-policy.json
python3 capstone_gate.py fixtures/capstone-unsafe.json fixtures/plan-destructive.json capstone-policy.json
python3 -m unittest -v test_capstone_gate.py
bash run-preflight.sh
~~~

Safe must exit 0; unsafe and destructive must exit nonzero. Tests mutate every required control, policy fail-open attempts, identity/label mismatches, backend-key isolation and destructive actions. This validates a **simplified declared-evidence fixture**, not live controls or native Terraform/OpenTofu plan JSON.

## 9. Lab C — Controlled migration rehearsal

1. Choose a disposable, isolated Terraform state root; inventory its lineage, serial and resource IDs.
2. Pin provider/module/CLI versions and verify remote-state lock and encrypted backup.
3. Restore state to an **isolated** backend and compare resource identity; never attach a second writer to live state.
4. Run Terraform baseline and OpenTofu compatibility plans against appropriately isolated test roots; record differences.
5. Inspect module address changes, provider schema and destructive actions. Reject unexplained replacement.
6. Render Terragrunt config, inventory backend keys, validate DAG and output contracts.
7. Simulate a failed downstream database unit after a successful upstream network unit; reconcile before retry.
8. Obtain SRE/DBRE/security approval; verify database health, SLO, PITR and recovery evidence.
9. Produce a cutover/rollback ADR with owner, maintenance window, stop conditions and audit trail.

## 10. Production incident game days

| Failure | Detection | Safe containment | Recovery |
|---|---|---|---|
| Concurrent Terraform/OpenTofu writers | state lock/serial conflict | freeze both executors | elect single writer, reconcile |
| Wrong backend key | unexpected creates | stop apply | isolate key and compare IDs |
| State corruption | unreadable state | preserve versions | isolated verified restore |
| Provider schema drift | replacement plan | deny apply | revert pin or controlled migration |
| Module address refactor | destroy/create | freeze rollout | reviewed moved/import blocks |
| Terragrunt dependency cycle | graph failure | stop downstream | redesign DAG |
| Missing upstream output | dependency failure | reject mocks | repair contract |
| Partial graph apply | inconsistent services | pause pipeline | inventory, re-plan |
| OIDC expiry | CI 403 | stop job | restore scoped identity |
| Secret leak | log/state exposure | revoke credentials | rotate and audit |
| PostgreSQL replacement | delete/create RDS/PG | DBRE veto | non-destructive plan/PITR |
| MongoDB quorum loss | election/lag | pause orchestration | restore majority |
| Redis connection storm | p99/CPU spike | throttle clients | pool tuning |
| Kafka ISR degradation | URP/lag | freeze broker changes | rebalance after health |
| Elasticsearch disk saturation | queue/latency | stop heavy rollout | storage/capacity remediation |
| Kubernetes AZ loss | pod unavailability | halt changes | reschedule and verify PDB |
| GitOps double ownership | repeated drift | freeze controllers | assign single writer |
| Failed DR restore | RTO breach | no cutover | repair backup chain |
| Untrusted PR privilege | anomalous API calls | revoke runner access | audit and isolate |
| Cost spike | spend anomaly | pause scale-up | review capacity/FinOps |

## 11. Troubleshooting and runbooks

Read-only diagnostics: \`tofu version\`, \`tofu providers\`, \`tofu validate\`, \`terragrunt --version\`, approved config/graph inspection, state-key inventory, CI audit and SLO dashboards. Avoid printing raw state, plan secrets or tokens.

**R1 Change preflight:** pin toolchain, provider/module, backend identity, state backup/lock, owner and approvals.

**R2 Compatibility mismatch:** halt cutover, compare schemas/state formats, reproduce in isolated root, revise migration ADR.

**R3 Lock/serial incident:** freeze writers, preserve evidence, identify authoritative state, never force-unlock an active process.

**R4 Partial DAG apply:** inventory completed units and actual IDs, stop downstream, reconcile and re-plan.

**R5 DBRE high-risk change:** veto unapproved replace/delete; verify PITR, replication, connection budget, maintenance window.

**R6 GitOps conflict:** pause reconciliation, define owner per resource, resolve drift through reviewed source of truth.

**R7 State/region DR:** restore encrypted backup to isolated backend, verify IDs, measure RPO/RTO, authorize cutover.

**R8 Security incident:** revoke OIDC/credentials, restrict artifacts, rotate secrets, audit state and pipeline.

**R9 Post-cutover:** verify SLO, drift, DB health, backup success, cost, alerting and handover.

## 12. 100-point Part 12 final assessment

| Domain | Max |
|---|---:|
| Migration architecture and compatibility evidence | 20 |
| State isolation, locking, backup and verified restore | 20 |
| Terragrunt DAG, outputs, concurrency and failure handling | 15 |
| Secure CI/CD, native plan policy and approvals | 15 |
| SRE/DBRE incidents, SLO and DR simulation | 20 |
| Governance, FinOps and operational handover | 10 |
| **Total** | **100** |

**Pass:** >=85/100 and **zero critical findings**. Critical findings include concurrent writers, unapproved stateful replacement, secrets exposure, untested restore, prod mocks, wrong backend key or missing DBRE approval. Scores remain pending until real execution evidence is reviewed.

## 13. Exit criteria and handoff

Attach architecture ADR, migration/compatibility matrix, pinned versions, state inventory and restore test, DAG, native-plan policy logs, CI run, incident timelines, RPO/RTO measurement, SLO and DBRE/Security approvals. **Publication completes Part 12 content (5/5); operational validation remains pending.**

**Next:** Chapter 061 — confirm the exact Part 13 roadmap title before publication.
