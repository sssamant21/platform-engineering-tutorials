# Chapter 059 — Terragrunt Dependency Graphs, Remote State, CI/CD and Enterprise Orchestration

**Part 12 — OpenTofu and Terragrunt | Chapter 059 of 120**  
**Audience:** Platform SRE, DBRE, DevOps, cloud security and change owners.  
**Prerequisites:** Chapters 056–058, pinned Terragrunt/OpenTofu, Python 3.9+, disposable sandbox.

> **Safety:** The executable lab is local \`terraform_data\` only. Declared-evidence fixtures do not prove remote state locks, live dependency readiness, CI identity or database recoverability. Production requires independent verification, approved plans, backups and DBRE sign-off.

## 1. Outcomes and architecture

Design an acyclic Terragrunt dependency graph, unique remote state per unit, secure CI/CD promotion, bounded parallelism, policy gates and failure recovery. Terragrunt orchestrates independently applied OpenTofu/Terraform units, **not an atomic transaction**.

~~~text
PR -> lint/validate -> dependency graph -> backend-key inventory
    -> per-unit plan -> policy -> SRE/DBRE approval
    -> one authorized writer per state key
network -> identity -> cluster -> database -> application
   |         |          |         |           |
  isolated encrypted remote state + locks + audit
                     |
          SLO, backups, drift and recovery
~~~

## 2. Dependency graph design

Use \`dependency\` when a downstream unit consumes upstream outputs; use \`dependencies\` for ordering alone. Outputs form versioned API contracts; test names, types, region/account identity and readiness separately. Detect cycles, missing outputs, stale state and accidental mock outputs. Production applies must not consume validation-only mocks. Keep database and storage operations separate from high-churn application releases. Limit parallelism to avoid cloud API throttling, backend lock contention and database connection storms. CLI syntax varies by pinned Terragrunt version; recent versions use \`terragrunt run --all\` while older releases use \`run-all\`.

## 3. Remote state and security

Use a deterministic unique backend key such as \`org/account/environment/region/unit/tofu.tfstate\` for each root. Confirm backend-supported encryption, versioning, IAM, audit logging and distributed locking. One state lineage must have one writer. State and plan artifacts may contain secrets; encrypt, restrict and retain them according to policy. Record lineage, serial, lock owner, last successful apply and tested isolated restore. A backend object version is not proof of recoverability. Do not force-unlock active writers or blindly push old state.

## 4. Enterprise CI/CD

1. Pin Terragrunt/OpenTofu, providers and module immutable revisions.
2. Run formatting, static security scans, configuration rendering, graph checks and state-key collision tests.
3. Obtain short-lived OIDC identity with environment-scoped permissions; never expose production credentials to untrusted pull requests.
4. Create per-unit reviewed plans and inspect native plan JSON through a tested adapter.
5. Deny unapproved delete/replace, insecure networking, unencrypted storage and risky database modifications.
6. Require protected environment, code owner, SRE/DBRE and security approval for high-risk changes.
7. Serialize writers per backend key; apply the approved plan and verify SLO, DB health, backup, drift and state serial.
8. On partial failure, stop downstream execution, inventory already-applied units, reconcile real infrastructure and replan. A graph apply cannot be rolled back atomically.

## 5. Executable Lab A — Offline OpenTofu contracts

~~~bash
cd infrastructure-as-code/labs/chapter-059
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

Four \`terraform_data\` resources represent DAG, state, CI/CD and operations controls. Dev/prod tfvars demonstrate separate declared state keys, not actual backend configuration. Production preconditions enforce supplied boolean controls; they do not attest external systems.

## 6. Executable Lab B — Policy and automated tests

~~~bash
python3 orchestration_gate.py fixtures/orchestration-safe.json fixtures/plan-safe.json orchestration-policy.json
python3 orchestration_gate.py fixtures/orchestration-unsafe.json fixtures/plan-destructive.json orchestration-policy.json
python3 -m unittest -v test_orchestration_gate.py
bash run-preflight.sh
~~~

Safe fixture must pass; unsafe/destructive fixtures must fail. Tests cover individual controls, policy fail-open attempts, environment/backend identity, labels, missing DAG evidence and replacement actions. The fixture is **not native \`tofu show -json\`**; production requires a separate validated adapter.

## 7. Lab C — Terragrunt sandbox graph and partial failure

Review \`examples/root.hcl.example\`, network and database unit configurations and CI example. Replace all placeholder backends, module URLs, versions and identities before sandbox execution. Inspect effective config and dependency graph with commands supported by the pinned Terragrunt release. Verify unique state keys and network output contracts. Simulate upstream failure, verify downstream blocks, then simulate a successful network unit and failed database unit. Preserve per-unit plans and state evidence, reconcile actual resources and resume only after approval. Do not use broad production applies.

## 8. SRE/DBRE incident scenarios

| Failure | Signal | Triage | Safe response |
|---|---|---|---|
| Graph cycle | dependency evaluation error | graph edges | redesign boundary |
| Missing output | downstream evaluation fails | upstream state/output | repair contract |
| Backend key collision | unexpected creates | root/key/account | freeze writers |
| Concurrent applies | lock timeout | CI jobs, lock owner | serialize |
| Backend outage | init/state errors | object store/KMS | fail closed |
| Partial apply | only some units changed | per-unit state/real IDs | reconcile and resume |
| Provider throttling | 429, retries | concurrency/quotas | reduce parallelism |
| PostgreSQL/RDS replacement | delete/create plan | provider schema, DB lifecycle | deny, DBRE approval |
| MongoDB replication lag | stale secondaries | oplog, disk, network | pause rollout |
| DB connection storm | pool exhaustion | replicas × pool size | throttle/backpressure |
| Kubernetes rollout stall | pods not ready | events, probes, PDB | halt downstream |
| KMS denied | state access failure | OIDC/key policy | restore least privilege |
| Secret exposure | CI artifact alert | logs, state ACL | revoke/rotate |
| Stale approved plan | apply mismatch | commit, drift, serial | replan |
| State divergence | wrong lineage | backup and real IDs | isolated restore/forward repair |

## 9. Troubleshooting

~~~bash
terragrunt --version
tofu version
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
tofu providers
python3 -m unittest -v test_orchestration_gate.py
~~~

Never publish raw state, sensitive plans, generated credentials or cloud tokens.

## 10. Operational runbooks

**R1 Preflight:** record pinned versions, unit/account/region, unique key, exclusive lock, encrypted backup, restore proof, ticket and DBRE/security approval.

**R2 DAG failure:** freeze downstream, identify missing output/cycle, repair upstream, replan.

**R3 Backend collision:** stop writers, preserve lineage/serial and audit, identify authoritative state before migration.

**R4 Partial graph apply:** inventory successful units, compare actual resources, isolate failed unit, approve safe continuation.

**R5 Database incident:** block unapproved replacement; validate PITR, backup, connections, replication and maintenance approval.

**R6 CI security:** revoke compromised identity, restrict artifacts, rotate secrets, audit OIDC trust.

**R7 Disaster recovery:** restore encrypted state in isolated backend, validate checksum/lineage/IDs and RPO/RTO, approve cutover.

**R8 Post-apply:** validate SLO, DB connectivity, drift, backups, FinOps and signed handover.

## 11. 100-point acceptance

| Domain | Points |
|---|---:|
| Dependency DAG and output contracts | 20 |
| State isolation, encryption and locking | 20 |
| Secure CI/CD, reviewed plans and approvals | 20 |
| Policy automation and negative testing | 15 |
| SRE/DBRE incidents, partial failure and DR | 15 |
| Governance, FinOps and handover | 10 |
| **Total** | **100** |

Pass **>=85/100** with zero critical findings. Critical: state collision, concurrent writers, unapproved database deletion, leaked production secrets, missing tested restore or untrusted PR cloud access.

## 12. Exit criteria

Submit graph/effective-config evidence, state-key inventory, isolated restore results, reviewed native plans, CI policy logs, incident timeline, DB health/SLO proof and sign-offs. Publication is not live acceptance.

**Next proposed:** Chapter 060 — OpenTofu and Terragrunt Enterprise Platform Engineering, Reliability and Migration Capstone.
