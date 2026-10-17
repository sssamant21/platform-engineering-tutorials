# Chapter 027 — Terraform Remote Backends, State Locking, Encryption and Access Control

**Part 06 — State and Remote Backends** · **Audience:** SRE/DBRE/Platform Engineering · **Core lab:** no-cloud backend security acceptance simulation · **Status:** published; live acceptance evidence pending

## 1. Learning objectives

Design production remote state for AWS S3, Azure Blob, Google Cloud Storage and HCP Terraform; explain backend initialization and credential handling; compare locking and concurrency models; enforce encryption, least privilege, versioning, isolation and recovery; detect unsafe backend configurations through executable Python policy; simulate lock contention and migration failures without provisioning cloud resources.

**Critical distinction:** A remote backend stores Terraform state; it is not a database backup, application recovery system, secret vault or automatic guarantee of exclusive access. Capabilities and syntax depend on the Terraform/OpenTofu release and backend version. Verify the exact pinned CLI and provider documentation before production adoption.

## 2. Reference architecture

~~~text
Approved Git revision / change ticket
                 |
      CI workload identity / SSO
                 |
  terraform init -backend-config=...
                 |
  Remote backend (state + lock mechanism)
   |          |            |
  ACL/IAM   Encryption    Versioning
   |          |            |
     backend-specific audit trail
                 |
       saved plan + policy gate
                 |
   change approval + exact-plan apply
                 |
      DBRE/SRE health and data checks
~~~

State locking protects against concurrent state writes only when the backend and clients honor the same lock protocol. A stale lock is an incident requiring ownership verification, not an invitation to use \`-lock=false\` or force-unlock blindly. Backend storage encryption does not prevent a highly privileged reader from retrieving sensitive plaintext state.

## 3. Backend architecture and configuration

Terraform initializes a backend before planning. A backend block selects the storage mechanism; backend configuration values are provided at init time. Backend blocks do not accept ordinary Terraform input variable references. \`terraform init -reconfigure\` accepts changed backend settings without automatically migrating existing state; \`terraform init -migrate-state\` performs a state migration and requires explicit verification and rollback planning.

Never hardcode access keys, tokens or passwords in \`.tf\`, \`.tfbackend\`, command history or CI logs. Backend settings may be cached in \`.terraform\` and plan files; use approved environment-based identity and short-lived credentials. Isolate production state per workload, environment, account/subscription/project and privilege boundary.

## 4. Backend comparison

| Backend | Storage | Locking / concurrency | Security and recovery |
|---|---|---|---|
| AWS S3 | versioned bucket/object key | S3 lockfile support in current Terraform versions; legacy DynamoDB locking exists in older configurations but is deprecated in newer Terraform | S3 IAM, TLS, SSE-KMS or SSE-S3, versioning, CloudTrail/data-event strategy, recovery |
| Azure Blob | Azure Storage blob | Azure blob lease-based locking | Entra ID/RBAC, TLS, encryption, versioning/soft delete, diagnostic logs |
| Google Cloud Storage | GCS bucket/object prefix | GCS backend supports state locking | IAM, TLS, Google-managed or CMEK encryption, object versioning and audit |
| HCP Terraform | managed remote state and runs | platform-managed concurrency and workspace controls | organization/workspace access, variables, run history, state versions |

**AWS note:** S3 \`use_lockfile = true\` is supported in newer Terraform versions; do not assume Terraform >=1.5 supports it. The optional S3 example requires Terraform >=1.10 for this locking configuration; verify current compatibility before use. DynamoDB locking is deprecated in modern Terraform, and a new design should prefer supported native S3 locking where available. Bucket versioning and separate encryption policies remain essential.

**Azure note:** Use the \`azurerm\` backend with supported Microsoft Entra ID authentication rather than account keys where practical. Authentication flags and identity options vary by CLI release.

**GCS note:** Verify required object permissions for both state and locking operations. Object versioning and IAM must be configured explicitly.

## 5. Lock and state security controls

Required production controls: approved storage identity; narrowly scoped read/write/list/delete permissions needed for state and lock operations; distinct production state key; encryption at rest/in transit; state versioning or equivalent rollback; access audit; non-public storage; lock enforcement; no static plaintext credentials; backup and restore drill; documented RPO/RTO and incident ownership. Evaluate break-glass identity separately.

State snapshots can include passwords, tokens, private data and provider attributes even when Terraform marks values \`sensitive\`. Do not post \`terraform state pull\`, \`terraform show -json\`, saved plans or state snapshots to tickets or GitHub.

## 6. Lab design

~~~text
labs/chapter-027/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  backend-policy.json
  backend-inventory.json
  backend-inventory-unsafe.json
  backend_security.py
  test_backend_security.py
  examples/s3.backend.tf.example
  examples/azure.backend.tf.example
  examples/gcs.backend.tf.example
  examples/hcp-terraform.tf.example
  run-preflight.sh
  .gitignore
~~~

The **executable core** uses only built-in \`terraform_data\` and local state; it models backend inventory and checks controls with Python. Cloud backend snippets are \`.example\` files, deliberately excluded from Terraform configuration, and require approved infrastructure and credentials before use. Python tests are not proof of actual S3/Azure/GCS permissions or lock enforcement.

## 7. Lab A — Local baseline and graph

~~~bash
cd infrastructure-as-code/labs/chapter-027
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter027.tfplan
terraform apply chapter027.tfplan
terraform state list
terraform output -json
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected local resources: \`terraform_data.state_boundary\`, \`terraform_data.audit_contract\`. A second plan should exit 0. Do not use the same state for dev and prod; use a separate disposable working directory for production simulation.

## 8. Lab B — Policy and negative fixtures

~~~bash
python3 backend_security.py backend-inventory.json backend-policy.json
python3 backend_security.py backend-inventory-unsafe.json backend-policy.json
python3 -m unittest -v test_backend_security.py
bash run-preflight.sh
~~~

The first inventory must pass; the unsafe inventory must be denied. The validator checks unique state keys, environment segregation, supported backend types, encryption, versioning, lock capability, least-privilege identity references, public access, TLS, audit, restore testing and secret-like fields. **The inventory is a declared-control fixture, not verified cloud configuration.** Tests include missing controls, unsafe lock settings, duplicate keys, wildcard permissions, plaintext credentials, and invalid policy.

## 9. Lab C — Lock contention tabletop

Two operators attempt to plan/apply against the same remote backend. Describe expected lock behavior, how to identify the lock owner and operation ID, and how to verify no operation remains active. Do not execute concurrent applies against production. In an isolated test backend, run one long operation and attempt a second operation with normal locking; confirm the second waits or fails according to backend behavior. Never use \`-lock=false\` to make the exercise succeed.

## 10. Lab D — Backend migration rehearsal

1. Verify source and destination backend identity, permissions, versioning, lock behavior and object keys.
2. Freeze writers and capture an encrypted, access-controlled, versioned state backup.
3. Test migration with **disposable** source/destination backends.
4. Use \`terraform init -migrate-state\` only after approved migration plan; inspect resulting lineage, serial and resource addresses.
5. Run a fresh plan; ensure no unintended create/delete/replacement.
6. Verify application/data health, then retire old access after a rollback period.
7. If migration fails, stop writers, preserve both copies, determine authoritative state and recover under change control.

Never run \`init -reconfigure\` and assume that it copied state.

## 11. Lab E — Failure injection

- Disable encryption, versioning, lock support, TLS, audit or restore-test flag in a disposable JSON fixture; expect denial.
- Duplicate a production state key across environments; expect denial.
- Add an access_key or client_secret field; expect denial.
- Change an identity reference to a static token; expect denial.
- Change permissions to \`*\` or make state public; expect denial.
- Set production backend to local; expect denial.
- Simulate an expired workload identity or storage 403; follow the identity runbook.
- Simulate a stale lock and an interrupted apply; document evidence needed before authorized unlock.
- Simulate object version restore with lineage/serial mismatch; freeze and reconcile rather than blindly overwrite.

## 12. Production SRE/DBRE scenarios

**RDS/Aurora:** isolate Terraform state from database snapshots/PITR; test both restore workflows and IAM boundaries.

**PostgreSQL:** protect endpoint/parameter and possibly credential metadata; state rollback cannot undo SQL data changes.

**Elasticsearch/OpenSearch:** state restores do not reconstruct deleted indices or shards; retain separate snapshot/restore runbooks.

**EKS/AKS:** separate cluster foundation state from application namespaces; avoid cyclic Kubernetes provider bootstrap.

**Redis:** state does not preserve RDB/AOF data; validate replica and persistence recovery separately.

**Snowflake:** state can contain roles, grants, warehouses and sensitive connection settings; enforce RBAC and audit.

**Kafka/MSK:** broker configuration state is distinct from topic data, ISR, offsets and consumer recovery.

## 13. Troubleshooting matrix

| Symptom | Likely cause | Safe action |
|---|---|---|
| Backend 403/AccessDenied | expired identity or wrong scope | verify caller, resource, permissions |
| Lock acquisition timeout | concurrent writer or stale lock | identify owner and active job |
| State key not found | wrong environment/key | stop, verify backend identity |
| Unexpected resource creation | empty/wrong state | stop, reconcile, never apply blindly |
| State serial conflict | concurrent update or stale copy | compare versions and lineage |
| S3 lockfile error | unsupported CLI or permissions | verify version and lock-object rights |
| Azure lease conflict | active lease/operation | investigate owner before recovery |
| GCS access error | bucket/object IAM | verify scoped permissions |
| State contains secret | provider attributes/output | restrict, rotate if exposed |
| Backend migration mismatch | incomplete migration | freeze, restore verified authoritative copy |
| Partial apply | API failure | reconcile actual resources and state |
| CI plan stale | another apply occurred | regenerate plan and approval |

## 14. Production runbooks

**Backend onboarding:** identify account/project/subscription → configure private encrypted versioned storage → configure workload identity and scoped permissions → verify locking → test audit and restore → approve state key naming → stage rollout.

**Lock incident:** freeze competing pipelines → identify active lock owner and backend operation → confirm no writer remains → backup state → use authorized unlock only with recorded lock ID and approval → replan and validate.

**Backend outage:** stop applies → protect latest verified state version → restore backend availability → validate lineage/serial/resources → replan, approve and resume.

**Credential exposure:** revoke/rotate, restrict state access, audit read events, remove leaked artifacts, improve identity and secrets handling.

**State version recovery:** freeze → compare trusted versions and remote resources → restore only with change approval → run read-only validation and plan → verify application/data health.

## 15. Acceptance rubric (100 points)

| Control | Points |
|---|---:|
| Backend selection and architecture | 20 |
| Identity, encryption, isolation and audit | 25 |
| Locking and concurrent-writer recovery | 20 |
| Executable lab, policy and negative tests | 20 |
| Migration, restore and SRE/DBRE runbooks | 15 |

Pass 85+ with no critical failures. Critical: public state, static plaintext credentials, production local backend, disabled locking, no recoverable state version, or unauthorized force-unlock. Record sanitized CLI version, state keys, policy/test output, lock test evidence and restore drill. **Authored tests have not been executed by GitHub publication.**

## 16. Cleanup

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Only the isolated local lab is destroyed. Do not delete production state objects as a cleanup step. Preserve approved redacted evidence and protect plan/state artifacts.

## 17. Knowledge check

How does a backend differ from a provider? Why are backend variables unavailable in a backend block? What does a lock protect? Why is encryption not equivalent to access control? Why is state versioning essential? How do S3 lockfiles differ from legacy DynamoDB locking? What does an Azure lease do? How should stale locks be handled? Why is a remote-state restore not a PostgreSQL PITR restore? What distinguishes \`init -migrate-state\` from \`init -reconfigure\`?

**Next:** Chapter 028 — Terraform State Operations, Import, Move, Remove and Drift Reconciliation.
