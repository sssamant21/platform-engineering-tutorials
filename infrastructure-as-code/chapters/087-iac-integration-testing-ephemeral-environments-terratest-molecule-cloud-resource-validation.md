# Chapter 087 — IaC Integration Testing, Ephemeral Environments, Terratest, Molecule and Cloud Resource Validation

**Part 18 — Testing and Compliance | Chapter 087/120 | Enterprise SRE/DevOps/DBRE**

## 1. Learning objectives and operating contract

Build a production-grade integration-testing system for Terraform/OpenTofu, Terratest, Ansible Molecule, Pulumi, CloudFormation, Bicep, Kubernetes, Helm, Argo CD/Flux and stateful databases. Learn isolation, disposable environments, cost and TTL controls, IAM, native resource assertions, idempotence, drift, failure injection, teardown and verifiable SRE/DBRE acceptance.

**Safety:** The companion executable Python 3 standard-library lab is entirely offline. It validates *declared synthetic evidence*, models lifecycle and checks budgets/cleanup. It neither provisions resources nor runs Terratest/Molecule or a real database restore. Native examples require approved isolated accounts and must not be run against production.

## 2. Architecture and trust boundaries

~~~text
Protected PR + immutable source revision
   -> static validation, secret scanning, OPA/Sentinel
   -> build/pin Terraform/OpenTofu/Pulumi/Ansible toolchains
   -> protected OIDC identity (test-only cloud account)
   -> environment lease: owner, run ID, TTL, budget, region
   -> Terraform apply / Pulumi up / CFN / Bicep
   -> Terratest and native API assertions
   -> Molecule converge / idempotence / verify
   -> K8s admission, GitOps reconciliation and network tests
   -> PostgreSQL/MongoDB/Redis/Kafka/OpenSearch recovery drills
   -> SLO + RPO/RTO + audit evidence
   -> destroy, independently verify zero owned resources
   -> revoke credentials, close lease, archive report
~~~

Keep CI pull-request testing unprivileged. Use a protected workflow with exact OIDC audience/subject for test-only accounts. Separate plan and apply identities where feasible, use account-level guardrails and constrain destructive permissions to tagged test resources. **Do not grant a test runner broad production permissions.**

## 3. Test layers and the isolation contract

| Layer | Tools | Observable assertion | Limitation |
|---|---|---|---|
| Static | terraform/tofu fmt, validate, ansible-lint, cfn-lint, bicep build | schema and syntax | no provider behavior |
| Unit/policy | terraform test, Pulumi mocks, OPA/Rego, Sentinel | configuration intent and denies | mocks are not live cloud |
| Provisioning | Terratest + native Terraform/OpenTofu; Pulumi integration | actual resource and API outputs | costs, credentials, side effects |
| Configuration | Molecule, Ansible check/idempotence | converge, repeatability, verify | driver/inventory differences |
| Kubernetes | kubectl, Helm, Kustomize, Kyverno/Gatekeeper | admission, RBAC, network, readiness | CNI/webhook-dependent |
| DBRE | PITR, snapshots, replication, failover, reconciliation | RPO/RTO, consistency, SLO | requires real isolated data |
| Teardown | destroy, cloud inventory, cost, lease reconciliation | zero owned resources and credentials | eventual consistency |

**Isolation invariant:** each run gets a unique run ID, distinct state key, account/project/subscription or bounded namespace, dedicated secrets, TTL and owner. Never use a production kubeconfig or shared database. The test harness must fail closed when environment identity cannot be independently verified.

## 4. Terratest with Terraform/OpenTofu

Terratest is a Go testing framework that can call Terraform/OpenTofu and query cloud APIs. Pin Go modules, provider versions and Terraform CLI. Use a temporary module copy or unique workspace/state key and enforce a maximum test duration. **Defer teardown immediately after successful environment selection** and verify cleanup separately.

~~~go
// Illustration only: requires Terratest dependencies and an isolated AWS account.
package test

import (
  "testing"
  "github.com/gruntwork-io/terratest/modules/terraform"
)

func TestIsolatedModule(t *testing.T) {
  t.Parallel()
  opts := &terraform.Options{
    TerraformDir: "../fixtures/example-module",
    Vars: map[string]interface{}{"environment": "ephemeral"},
    NoColor: true,
  }
  defer terraform.Destroy(t, opts)
  terraform.InitAndApply(t, opts)
  id := terraform.Output(t, opts, "resource_id")
  if id == "" { t.Fatal("missing resource_id") }
}
~~~

This is a **teaching skeleton**, not an immediately runnable project: create the example module, install Terratest, configure isolated credentials, and add unique state and cloud assertions. Avoid `t.Parallel()` unless state, account quotas and resource names are isolated. A failed `Destroy` requires a separate inventory sweep and owner escalation.

## 5. Ansible Molecule and idempotence

Molecule can provision disposable instances/containers, converge roles, rerun for idempotence, verify outcomes and destroy. Driver behavior varies by version and plugin; pin compatible Molecule, Ansible and driver packages. Containerized scenarios are suitable for package/configuration tests, but systemd, kernel, networking and cloud IAM tests may need isolated VMs.

~~~yaml
# Illustrative molecule/default/molecule.yml; driver must be installed.
dependency:
  name: galaxy
driver:
  name: default
platforms:
  - name: instance
provisioner:
  name: ansible
verifier:
  name: ansible
scenario:
  test_sequence:
    - destroy
    - create
    - converge
    - idempotence
    - verify
    - destroy
~~~

Always inspect inventory, `become`, credentials and target hosts before converge. Treat check mode as advisory: not all Ansible modules accurately predict changes. Test privilege boundaries and that a second converge reports no unintended changes.

## 6. Ephemeral environment lifecycle and FinOps

Lifecycle: **requested -> leased -> provisioned -> tested -> cleanup_pending -> destroyed -> verified -> closed**. Failure moves to **quarantined**, never directly to success. An external sweeper should find expired leases, orphaned cloud resources, state keys, namespaces and disks. Tag every resource with run ID, owner, expiry and cost center. Measure provision, test and teardown time, not just test duration. Alert when spend, lease age or orphan count exceeds budget. Cleanup may be destructive; verify ownership before deleting anything.

## 7. Kubernetes, GitOps and admission integration

Test `kubectl auth can-i` using authorized impersonation; check Pod Security Admission, Gatekeeper/Kyverno, NetworkPolicy egress and DNS, readiness/liveness, PVC binding and CSI snapshots. Use Helm template and a staging `kubectl apply --dry-run=server` for representative webhook behavior. Verify Argo CD AppProject destination/repository constraints, Flux service account impersonation and source revision. Test rollback through Git, because controllers may undo imperative hotfixes.

## 8. Multi-cloud and IaC resource assertions

**AWS:** compare account ID, VPC, security groups, S3 encryption, RDS PITR, CloudTrail and KMS access. **Azure:** confirm tenant/subscription, resource group, Azure Policy, managed identity, Key Vault and AKS admission. **GCP:** verify project, org policy, WIF, GKE Workload Identity and Cloud KMS. **Pulumi/CloudFormation/Bicep:** inspect actual preview/change-set/what-if plus resulting resources, not just deployment exit code. Require deterministic output assertions and explicit negative tests for public ingress, wildcard IAM, unencrypted storage and destructive database replacement.

## 9. SRE/DBRE integration matrix

| Platform | Test | Fault injection | Acceptance |
|---|---|---|---|
| PostgreSQL/RDS/Aurora | migrations, replica, PITR | KMS deny, failover, lock contention | measured restore RPO/RTO and query SLO |
| MongoDB | replica set, backup, TLS | primary loss, oplog window | quorum, consistent restore |
| Redis | ACL, persistence, failover | stale pool, lost master | recovery and integrity |
| Kafka/MSK | topic/group ACL, ISR | broker loss, consumer lag | no unapproved loss and lag recovery |
| Elasticsearch/OpenSearch | index, snapshot, query load | disk IOPS pressure, shard loss | restore, shard health, latency SLO |
| Snowflake | role, CDC pipeline, warehouse | stale checkpoint, role denial | reconciliation and pipeline recovery |
| EKS/AKS/GKE | admission, CNI, CSI, node drain | webhook or DNS failure | readiness, restore and SLO |

A backup object is not proof of restorability. Verify actual decryption and data consistency in an isolated target, include RPO/RTO measurements and independent DBRE sign-off.

## 10. Executable offline labs

### Lab A — Fail-closed environment readiness gate

~~~bash
cd infrastructure-as-code/labs/chapter-087
python3 integration_gate.py fixtures/safe.json policy.json
python3 integration_gate.py fixtures/unsafe.json policy.json  # expected nonzero
bash run-preflight.sh
~~~

The gate checks exact target, 32 control claims, immutable digest, unique lease, test counts, cleanup, cost, SLO and RPO/RTO. All input is synthetic.

### Lab B — Lease and cleanup state machine

`lifecycle.py` enforces environment transitions, prohibits unverified cleanup and quarantines failed tests. A closed lease requires verified zero owned resources.

### Lab C — Cost and TTL enforcement

`budget_gate.py` rejects expired leases, over-budget spend, orphaned resources, wrong ownership, or incomplete teardown. Negative fixtures test fail-closed behavior.

### Lab D — Integration evidence quality

`evidence_gate.py` requires declared native test layers, distinct test run IDs, zero skipped critical tests and signed-off cleanup. It does **not** independently query cloud APIs.

### Lab E — Real staging exercise (procedure only)

Request an isolated cloud account and approved budget. Provision a disposable PostgreSQL/RDS or MongoDB stack using Terraform/OpenTofu; execute Terratest, Molecule and Kubernetes admission assertions; run a real backup restore and measure RPO/RTO; perform tagged teardown, verify resource inventory and attach cloud billing/audit logs. Requires explicit authorization and is **not executed by the companion lab**.

## 11. Production SRE/DBRE incident simulation catalog

| # | Scenario | Initial action |
|---|---|---|
| 1 | Ephemeral AWS account misidentified as production | Freeze test lease; inspect ownership, isolation and cleanup |
| 2 | Terraform apply creates a public RDS instance | Stop destructive testing; DBRE verifies recovery |
| 3 | Terratest parallel suite collides on S3 bucket | Freeze test lease; inspect ownership, isolation and cleanup |
| 4 | Test cleanup fails due to finalizer | Freeze test lease; inspect ownership, isolation and cleanup |
| 5 | Cloud credentials leak through CI logs | Quarantine credentials/evidence and rotate |
| 6 | OIDC subject grants cross-environment role | Freeze test lease; inspect ownership, isolation and cleanup |
| 7 | Terratest destroy blocked by state lock | Quarantine credentials/evidence and rotate |
| 8 | Terraform state backend deleted before teardown | Quarantine credentials/evidence and rotate |
| 9 | Provider drift triggers resource replacement | Freeze test lease; inspect ownership, isolation and cleanup |
| 10 | Test runner killed before cleanup | Freeze test lease; inspect ownership, isolation and cleanup |
| 11 | Ephemeral cluster remains after TTL | Freeze test lease; inspect ownership, isolation and cleanup |
| 12 | Cloud budget threshold exceeded | Freeze test lease; inspect ownership, isolation and cleanup |
| 13 | Molecule converge mutates production inventory | Freeze test lease; inspect ownership, isolation and cleanup |
| 14 | Molecule idempotence test fails | Freeze test lease; inspect ownership, isolation and cleanup |
| 15 | Ansible become privilege escalation | Freeze test lease; inspect ownership, isolation and cleanup |
| 16 | Molecule delegated driver cannot clean EC2 | Freeze test lease; inspect ownership, isolation and cleanup |
| 17 | Container runtime unavailable | Freeze test lease; inspect ownership, isolation and cleanup |
| 18 | Testcontainers reuses contaminated volume | Freeze test lease; inspect ownership, isolation and cleanup |
| 19 | PostgreSQL migration deadlocks during test | Stop destructive testing; DBRE verifies recovery |
| 20 | PostgreSQL PITR restore missing WAL | Stop destructive testing; DBRE verifies recovery |
| 21 | Aurora failover exceeds RTO | Stop destructive testing; DBRE verifies recovery |
| 22 | RDS snapshot encrypted under inaccessible KMS | Stop destructive testing; DBRE verifies recovery |
| 23 | MongoDB replica set cannot elect primary | Stop destructive testing; DBRE verifies recovery |
| 24 | MongoDB backup restore lacks index | Stop destructive testing; DBRE verifies recovery |
| 25 | Redis ACL rotation disconnects clients | Stop destructive testing; DBRE verifies recovery |
| 26 | Redis failover loses writes | Stop destructive testing; DBRE verifies recovery |
| 27 | Kafka consumer lag exceeds threshold | Stop destructive testing; DBRE verifies recovery |
| 28 | MSK IAM authentication denied | Stop destructive testing; DBRE verifies recovery |
| 29 | Kafka ISR below minimum | Stop destructive testing; DBRE verifies recovery |
| 30 | OpenSearch shards remain unassigned | Stop destructive testing; DBRE verifies recovery |
| 31 | Elasticsearch query latency exceeds SLO | Stop destructive testing; DBRE verifies recovery |
| 32 | Snowflake role has excessive privilege | Stop destructive testing; DBRE verifies recovery |
| 33 | Snowflake CDC reconciliation mismatch | Stop destructive testing; DBRE verifies recovery |
| 34 | EKS node fails scheduling constraints | Freeze test lease; inspect ownership, isolation and cleanup |
| 35 | AKS workload identity federation fails | Freeze test lease; inspect ownership, isolation and cleanup |
| 36 | GKE CSI driver lacks storage permission | Freeze test lease; inspect ownership, isolation and cleanup |
| 37 | Kubernetes NetworkPolicy blocks DNS | Freeze test lease; inspect ownership, isolation and cleanup |
| 38 | Kubernetes admission webhook fails open | Freeze test lease; inspect ownership, isolation and cleanup |
| 39 | Argo CD sync overwrites test namespace | Freeze test lease; inspect ownership, isolation and cleanup |
| 40 | Flux source points to wrong branch | Freeze test lease; inspect ownership, isolation and cleanup |
| 41 | Helm chart deploys mutable image | Freeze test lease; inspect ownership, isolation and cleanup |
| 42 | CloudFormation stack rollback incomplete | Freeze test lease; inspect ownership, isolation and cleanup |
| 43 | Bicep what-if fails to detect replacement | Freeze test lease; inspect ownership, isolation and cleanup |
| 44 | Pulumi stack secrets unavailable | Quarantine credentials/evidence and rotate |
| 45 | OPA test policy is advisory | Freeze test lease; inspect ownership, isolation and cleanup |
| 46 | Kyverno test fixture bypasses admission | Freeze test lease; inspect ownership, isolation and cleanup |
| 47 | Test harness assumes all checks passed | Freeze test lease; inspect ownership, isolation and cleanup |
| 48 | Negative test case accidentally omitted | Freeze test lease; inspect ownership, isolation and cleanup |
| 49 | Artifact provenance unverified | Freeze test lease; inspect ownership, isolation and cleanup |
| 50 | SBOM missing dependency | Freeze test lease; inspect ownership, isolation and cleanup |
| 51 | Test result age exceeds SLA | Freeze test lease; inspect ownership, isolation and cleanup |
| 52 | Parallel runs share database schema | Freeze test lease; inspect ownership, isolation and cleanup |
| 53 | Synthetic data contains real PII | Quarantine credentials/evidence and rotate |
| 54 | Restore drill never measures RPO | Stop destructive testing; DBRE verifies recovery |
| 55 | RTO clock excludes provisioning delay | Stop destructive testing; DBRE verifies recovery |
| 56 | Cleanup removes unrelated resources | Freeze test lease; inspect ownership, isolation and cleanup |
| 57 | Cost tag missing from resources | Freeze test lease; inspect ownership, isolation and cleanup |
| 58 | Break-glass identity used by test suite | Freeze test lease; inspect ownership, isolation and cleanup |
| 59 | GitOps controller leaves resources after teardown | Freeze test lease; inspect ownership, isolation and cleanup |
| 60 | Cloud API throttling makes tests flaky | Freeze test lease; inspect ownership, isolation and cleanup |

## 12. Production runbooks

**R1 — Ephemeral account and namespace quarantine:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

**R2 — Terraform/OpenTofu and Terratest failure:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

**R3 — Molecule/Ansible inventory isolation:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

**R4 — Kubernetes cluster admission and CNI:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

**R5 — State lock and orphan cleanup:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

**R6 — Cloud spend and TTL breach:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

**R7 — PostgreSQL/RDS/Aurora PITR drill:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

**R8 — MongoDB/Redis stateful integration recovery:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

**R9 — Kafka/MSK and OpenSearch reliability:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

**R10 — GitOps drift and controller reconciliation:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

**R11 — Credential leakage and IAM response:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

**R12 — Evidence, SLO and independent acceptance:** Identify run ID, environment and owner; halt unsafe actions; preserve CI/cloud/cluster evidence; isolate affected credentials or workloads; validate IAM, state, policy and data-plane health; perform authorized remediation; re-run native assertions and DBRE recovery; independently verify resource cleanup, cost and SLO; document approvals and preventive action.

## 13. Troubleshooting

| Symptom | Diagnostic | Safe recovery |
|---|---|---|
| Terratest fails after apply | state, API rate limit, provider version | preserve state; controlled destroy and inventory |
| Molecule idempotence fails | role tasks, handlers, changed_when | fix in disposable driver; rerun |
| Test hits wrong account | STS/tenant/project identity | stop and revoke session; incident review |
| Namespace stuck terminating | finalizers, PVC, controllers | verify ownership before cleanup |
| Test environment cost spikes | tags, TTL, idle load balancer/storage | quarantine and approved sweep |
| Restore fails | KMS grants, backup chain, identity | DR owner investigates; no prod mutation |
| GitOps reverts test fix | source ownership, sync mode | reconcile source and controller |
| Flaky integration test | shared resources, eventual consistency | isolate, bounded retry, deterministic assertions |

## 14. 100-point acceptance

| Domain | Points |
|---|---:|
| Architecture, isolation and security boundaries | 15 |
| Terraform/OpenTofu/Terratest and multi-cloud tests | 20 |
| Molecule, Kubernetes and GitOps validation | 20 |
| Offline labs, negative tests and lifecycle evidence | 20 |
| Stateful DBRE recovery and SLO | 15 |
| Cost, teardown, audit and runbooks | 10 |
| **Total** | **100** |

Pass >=85 and zero critical failures. Critical: test targeting production, unbounded identity, leaked secret, orphaned resource, unapproved destructive action, missing restore, exceeded RPO/RTO or failed SLO. Native test outputs, verified teardown and security/SRE/DBRE sign-off are required for production acceptance. **Offline synthetic evidence cannot certify readiness.**

**Next:** Chapter 088 — IaC Compliance Testing, Audit Evidence, Control Mapping and Continuous Assurance.
