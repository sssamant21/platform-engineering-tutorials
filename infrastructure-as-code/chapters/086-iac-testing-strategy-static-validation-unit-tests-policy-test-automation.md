# Chapter 086 — IaC Testing Strategy, Static Validation, Unit Tests and Policy Test Automation

**Part 18 — Testing and Compliance · Chapter 086/120 · Enterprise SRE/DevOps/DBRE**

## Objectives and scope

Build a defensible, repeatable testing strategy across Terraform/OpenTofu, Pulumi, AWS CloudFormation, Azure Bicep, Ansible, Helm/Kustomize, Kubernetes and GitOps. Implement static validation, unit tests, property-based and mutation-inspired negative tests, policy-as-code tests, ephemeral integration environments, drift checks, DBRE recovery verification and continuous audit evidence. Separate **syntax correctness**, **plan safety**, **runtime behavior**, **recovery** and **production acceptance**.

The accompanying offline Python standard-library lab validates **synthetic, self-declared evidence**. It is not an actual Terraform plan, OPA decision, cloud authorization, signature verification or database restore. Production tests require native tools, protected identities and independent evidence.

## 1. Test pyramid and architecture

~~~text
              Production SLO/DR drills
           Canary and staged integration
        Cloud/Kubernetes ephemeral integration
       Native plan/preview, policy and contracts
     Unit tests, property checks, mutation negatives
  fmt / lint / schema / static scan / secrets / SBOM
Source commit -> CI -> signed artifact -> protected CD
                         |
               immutable audit evidence
~~~

Run cheap deterministic tests first. Each layer proves a different property; no one layer substitutes for another. Protect CI runners from untrusted PRs, pin toolchain versions and test dependencies, enforce exact cloud targets and destroy ephemeral resources through a controlled cleanup mechanism.

| Layer | Typical tools | Pass condition | What it cannot prove |
|---|---|---|---|
| Format/syntax | terraform fmt/validate, tofu fmt/validate, pulumi preview, cfn-lint, bicep build, ansible-lint | valid configuration | safe real deployment |
| IaC static/security | Checkov, Trivy config, tfsec legacy, custom scanners | no unapproved critical findings | real IAM enforcement |
| Unit/module | terraform test, Terratest, pytest, Pulumi mocks, Pester where relevant | deterministic expected outputs | actual provider effects |
| Policy | OPA/Rego `opa test`, Sentinel test, CloudFormation Guard | deny negative fixtures | correct policy attachment/enforcement |
| Integration | ephemeral cloud/cluster, Molecule, Testcontainers | resource behavior and teardown | long-term reliability |
| Recovery | PITR, backup restore, failover, GitOps rollback | measured RPO/RTO and SLO | every future incident |
| Compliance | immutable logs, owner, controls, evidence | traceable signed acceptance | external certification |

## 2. Terraform/OpenTofu testing

Use `terraform fmt -check -recursive`, `terraform init -backend=false` (when appropriate), `terraform validate`, and the equivalent OpenTofu commands. Prefer isolated module tests and `terraform test` with mocks or provider-backed run blocks as appropriate to installed version. Inspect **plan JSON** for delete/replace actions, encryption, public access and backup retention. Plan files may contain secrets and should be treated as sensitive. A saved plan is tied to state and configuration; revalidate identity, target and state lock before apply.

~~~bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform test
# Requires configured providers and a safe test environment:
terraform plan -out=tfplan
terraform show -json tfplan > plan.json
~~~

Never run provider-backed tests against production or shared resources without explicit authorization and cleanup. Terratest may create real infrastructure and incur cost; use dedicated accounts and hard timeouts.

## 3. Pulumi, CloudFormation, Bicep and Ansible

**Pulumi:** unit-test resource properties with mocks, inspect `pulumi preview` and test policy packs; confirm stack identity and secret handling. **CloudFormation:** validate YAML/JSON with `cfn-lint`, use CloudFormation Guard and change-set review; do not equate template validity with stack safety. **Bicep:** `az bicep build`, lint, what-if and Azure Policy; unknown outputs require explicit review. **Ansible:** `ansible-lint`, `ansible-playbook --syntax-check`, check/diff mode and Molecule on disposable targets; check mode is not guaranteed side-effect free for all modules.

## 4. Kubernetes and GitOps testing

Render Helm/Kustomize, validate schemas and namespace, run policy tests and Kubernetes **server-side dry-run** in a staging cluster with representative admission. Test RBAC via `kubectl auth can-i`, service account impersonation where authorized, Pod Security, NetworkPolicy DNS and egress, PVC/StorageClass constraints, PDB and node disruption. Test Argo CD/Flux reconciliation and single-writer ownership. Imperative rollback can be overwritten by GitOps reconciliation; rollback the Git source and verify convergence.

## 5. Policy-as-code automation

Test **both allow and deny** cases for OPA/Rego, Sentinel, Pulumi CrossGuard, CloudFormation Guard, Azure Policy, Gatekeeper and Kyverno. Deny cases should cover wildcard IAM, unsigned artifacts, unencrypted state, public ingress, wrong target, database destroy, missing backup and failed SLO. Mutation-inspired testing changes one security-critical field at a time; tests must fail when the control is removed. Verify native policy-set attachment, enforcement mode, bundle provenance and version, not just rule syntax.

## 6. Test environment, data and evidence governance

Use ephemeral isolated cloud accounts/projects, namespaces, resource prefixes, TTL tags and budget alarms. Seed only synthetic or properly anonymized data. Keep CI outputs, Terraform plans, state snapshots, Kubernetes Secrets and DB connection strings restricted. Pin image digests, dependencies and actions; record source SHA, artifact digest, target, test tool version, policy bundle, run ID, timestamps, approval and cleanup outcome. A test report without independently verified execution logs is **authored evidence**, not proof of execution.

## 7. DBRE testing and reliability acceptance

| System | Test | Failure to simulate | Acceptance |
|---|---|---|---|
| PostgreSQL/RDS/Aurora | migration, lock, PITR, replica lag | failed restore or KMS denial | measured RPO/RTO, no data corruption |
| MongoDB | role, TLS, replica failover, backup | quorum loss, oplog window | consistent restore and healthy election |
| Redis | ACL, persistence, failover | stale connection pool, memory pressure | SLO and integrity restored |
| Kafka/MSK | ACL, producer/consumer, ISR | partition leader loss, lag | no unintended loss, recovery |
| OpenSearch/Elasticsearch | snapshot, shard placement, query load | IOPS saturation, rejected requests | snapshot restore and latency SLO |
| Snowflake | role grants, pipeline integration | warehouse failure, stale CDC | reconciliation and pipeline health |
| EKS/AKS/GKE | PDB, CSI restore, node drain | admission and CNI outage | restored stateful service |

Define RPO/RTO and error budgets **before** the drill. Production change approval should require real backup restorability and monitored rollback, not just a `backup_exists=true` field.

## 8. Executable hands-on labs

### Lab A — Offline test-evidence gate

~~~bash
cd infrastructure-as-code/labs/chapter-086
python3 test_gate.py fixtures/safe.json policy.json
python3 test_gate.py fixtures/unsafe.json policy.json  # must reject
bash run-preflight.sh
~~~

The gate rejects wrong target, mutable artifact, missing policy tests, destructive actions, expired exceptions, absent DBRE restore evidence, failed SLO and incomplete cleanup. All evidence fields are **self-declared**.

### Lab B — Negative and mutation-inspired tests

Run `python3 -m unittest -v test_test_gate.py`. Each required control is independently flipped to false; exact target, test counts, RPO/RTO, ticket and digest are tested with negative cases.

### Lab C — Coverage and test-quality gate

`coverage_gate.py` evaluates a synthetic test matrix: required layers, negative-case counts, zero skipped critical tests and bounded test age. It is not a code-coverage collector.

### Lab D — Fail-closed test pipeline

`pipeline.py` enforces `source -> format -> static -> unit -> policy -> plan -> integration -> restore -> canary -> evidence -> approval`. Out-of-order and failed stages halt promotion. No real deployment is performed.

### Lab E — Staging integration blueprint

Create an isolated account/cluster, pin native tools, run policy and IaC tests, perform a real PostgreSQL restore, validate IAM and admission, measure canary SLO, destroy all ephemeral resources and attach logs. This is a **procedure**, not an executed lab.

## 9. Production SRE/DBRE incident simulations

| # | Scenario | Containment |
|---|---|---|
| 1 | Terraform fmt passes but plan destroys RDS | Freeze change; DBRE verifies recovery and SLO |
| 2 | OpenTofu validate succeeds with wrong provider | Fail closed; verify target, test coverage, policy and provenance |
| 3 | Pulumi preview misses provider-side replacement | Fail closed; verify target, test coverage, policy and provenance |
| 4 | CloudFormation lint ignores runtime IAM denial | Fail closed; verify target, test coverage, policy and provenance |
| 5 | Bicep build succeeds but Azure Policy denies | Fail closed; verify target, test coverage, policy and provenance |
| 6 | Ansible syntax-check passes destructive task | Fail closed; verify target, test coverage, policy and provenance |
| 7 | Kustomize overlay selects prod namespace | Fail closed; verify target, test coverage, policy and provenance |
| 8 | Helm template omits required Secret | Quarantine evidence, revoke/rotate and audit |
| 9 | OPA Rego default allow regression | Fail closed; verify target, test coverage, policy and provenance |
| 10 | Sentinel policy set advisory not mandatory | Fail closed; verify target, test coverage, policy and provenance |
| 11 | Kyverno policy audit rather than enforce | Fail closed; verify target, test coverage, policy and provenance |
| 12 | Gatekeeper webhook unreachable | Fail closed; verify target, test coverage, policy and provenance |
| 13 | GitOps sync reverts emergency hotfix | Fail closed; verify target, test coverage, policy and provenance |
| 14 | CI test runner gains prod OIDC identity | Fail closed; verify target, test coverage, policy and provenance |
| 15 | Test fixture contains real credential | Quarantine evidence, revoke/rotate and audit |
| 16 | State lock race during integration test | Quarantine evidence, revoke/rotate and audit |
| 17 | Testcontainers cleanup deletes wrong volume | Fail closed; verify target, test coverage, policy and provenance |
| 18 | Molecule test touches prod inventory | Fail closed; verify target, test coverage, policy and provenance |
| 19 | Terratest test uses shared AWS account | Fail closed; verify target, test coverage, policy and provenance |
| 20 | Ephemeral environment not destroyed | Fail closed; verify target, test coverage, policy and provenance |
| 21 | Snapshot test hides schema drift | Fail closed; verify target, test coverage, policy and provenance |
| 22 | Golden file updated without review | Fail closed; verify target, test coverage, policy and provenance |
| 23 | Mocked IAM test misses explicit deny | Fail closed; verify target, test coverage, policy and provenance |
| 24 | RBAC test lacks cluster scope negative | Fail closed; verify target, test coverage, policy and provenance |
| 25 | Provider lockfile altered after test | Fail closed; verify target, test coverage, policy and provenance |
| 26 | Dependency registry compromise | Fail closed; verify target, test coverage, policy and provenance |
| 27 | Artifact digest changes after approval | Fail closed; verify target, test coverage, policy and provenance |
| 28 | Signed provenance issuer mismatch | Fail closed; verify target, test coverage, policy and provenance |
| 29 | Policy bundle version drift | Fail closed; verify target, test coverage, policy and provenance |
| 30 | OPA test input omits planned deletes | Fail closed; verify target, test coverage, policy and provenance |
| 31 | CloudFormation change set differs from tested plan | Fail closed; verify target, test coverage, policy and provenance |
| 32 | Azure what-if reports unknown values | Fail closed; verify target, test coverage, policy and provenance |
| 33 | Kubernetes server dry-run bypasses webhook | Fail closed; verify target, test coverage, policy and provenance |
| 34 | API admission timeout fail-open | Fail closed; verify target, test coverage, policy and provenance |
| 35 | PostgreSQL migration unit tests skip locks | Freeze change; DBRE verifies recovery and SLO |
| 36 | Aurora PITR test cannot decrypt backup | Freeze change; DBRE verifies recovery and SLO |
| 37 | MongoDB replica set loses quorum | Freeze change; DBRE verifies recovery and SLO |
| 38 | Redis ACL test breaks application connection | Freeze change; DBRE verifies recovery and SLO |
| 39 | Kafka MSK IAM test breaks consumer | Freeze change; DBRE verifies recovery and SLO |
| 40 | OpenSearch snapshot test exceeds IOPS | Freeze change; DBRE verifies recovery and SLO |
| 41 | Snowflake role test uses ACCOUNTADMIN | Fail closed; verify target, test coverage, policy and provenance |
| 42 | EKS network policy blocks DNS | Fail closed; verify target, test coverage, policy and provenance |
| 43 | AKS workload identity audience mismatch | Fail closed; verify target, test coverage, policy and provenance |
| 44 | GKE service account overgrant | Fail closed; verify target, test coverage, policy and provenance |
| 45 | Canary SLO burn after rollout | Fail closed; verify target, test coverage, policy and provenance |
| 46 | Load test overwhelms staging database | Fail closed; verify target, test coverage, policy and provenance |
| 47 | Synthetic secret scanning false negative | Quarantine evidence, revoke/rotate and audit |
| 48 | Scanner DB too stale for critical CVE | Fail closed; verify target, test coverage, policy and provenance |
| 49 | Security exception expires unnoticed | Fail closed; verify target, test coverage, policy and provenance |
| 50 | Compliance evidence missing change ticket | Fail closed; verify target, test coverage, policy and provenance |
| 51 | Test report fabricated from self-declared flags | Fail closed; verify target, test coverage, policy and provenance |
| 52 | Backup restore not actually executed | Freeze change; DBRE verifies recovery and SLO |
| 53 | RPO exceeds accepted objective | Freeze change; DBRE verifies recovery and SLO |
| 54 | RTO exceeds accepted objective | Freeze change; DBRE verifies recovery and SLO |
| 55 | Cross-region DR test leaves resources running | Fail closed; verify target, test coverage, policy and provenance |
| 56 | Emergency rollback fails due to GitOps | Fail closed; verify target, test coverage, policy and provenance |
| 57 | Wrong workspace targeted by plan | Fail closed; verify target, test coverage, policy and provenance |
| 58 | Test runner logs sensitive Terraform outputs | Fail closed; verify target, test coverage, policy and provenance |
| 59 | Provider schema upgrade changes behavior | Fail closed; verify target, test coverage, policy and provenance |
| 60 | Concurrency causes duplicate production applies | Fail closed; verify target, test coverage, policy and provenance |

## 10. SRE/DBRE runbooks

**R1 — Test pipeline triage and failure classification:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

**R2 — Terraform/OpenTofu plan regression:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

**R3 — Pulumi/CloudFormation/Bicep native test failure:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

**R4 — Ansible Molecule and inventory isolation:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

**R5 — OPA/Sentinel policy regression:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

**R6 — Kubernetes admission/RBAC test failure:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

**R7 — GitOps drift and reconciliation rollback:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

**R8 — Ephemeral environment teardown and cost:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

**R9 — Secrets and test evidence exposure:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

**R10 — Database PITR/restore test failure:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

**R11 — Canary SLO and performance regression:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

**R12 — Audit acceptance and test quality review:** Classify failure and owner; freeze unsafe promotion; preserve test, plan and audit artifacts; reproduce in isolated staging; verify target, policy, identity and dependency versions; coordinate approved remediation and DBRE restore; rerun negative tests, SLO and cleanup; record acceptance and follow-up.

## 11. Troubleshooting matrix

| Symptom | Investigation | Safe action |
|---|---|---|
| Unit tests green, apply fails | provider APIs, IAM, runtime state | isolate in staging, add integration test |
| OPA tests green, production bypasses | policy set, mode, webhook | block release, verify enforcement |
| Plan proposes database replace | dependency graph, provider schema | stop, require DBRE restore and approval |
| Ephemeral resources remain | teardown logs, finalizers, locks | owner-approved cleanup, cost audit |
| Native dry-run differs from apply | admission, defaults, controllers | staging integration and diff |
| Test runner leaks credentials | logs, artifacts, access scopes | quarantine and rotate |
| Flaky integration tests | shared state, timeouts, data races | isolate resources and pin versions |
| Restore drill exceeds RTO | KMS, storage, network, operator | DR remediation and repeat drill |

## 12. 100-point assessment

| Domain | Points |
|---|---:|
| Test architecture and trust boundaries | 15 |
| Terraform/OpenTofu, Pulumi, CloudFormation, Bicep and Ansible testing | 20 |
| Kubernetes/GitOps and policy-as-code tests | 20 |
| Executable negative tests and CI evidence | 20 |
| DBRE recovery, RPO/RTO and SLO acceptance | 15 |
| Audit, cleanup and runbook handover | 10 |
| **Total** | **100** |

**Pass >=85** with zero critical failures, real native test logs, independent security/SRE/DBRE approval, verified restore and resource cleanup. Critical failures include a destructive production change, policy fail-open, exposed secret, untrusted artifact, missing recovery or failed SLO. **Publication and offline fixtures do not certify production readiness.**

**Next:** Chapter 087 — IaC Integration Testing, Ephemeral Environments, Terratest, Molecule and Cloud Resource Validation.
