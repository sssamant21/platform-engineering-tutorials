# Chapter 090 — Enterprise IaC Testing, Compliance, Drift and Audit Reliability Capstone

**Part 18 — Testing and Compliance · Chapter 090/120 · SRE / DevOps / DBRE**

> **Publication is not certification.** This capstone integrates Chapters 086–089. Its Python standard-library labs run entirely offline against synthetic fixtures. They do not execute Terraform/OpenTofu, Terratest, Molecule, OPA/Sentinel, cloud APIs, Kubernetes, database restores, or cryptographic signature verification. Live production readiness requires separately approved native validation and independent SRE/DBRE/security acceptance.

## 1. Objectives and acceptance contract

At completion, design and demonstrate: (1) layered IaC test coverage; (2) isolated, bounded integration environments; (3) independently enforced policy controls; (4) continuous drift detection with safe, non-destructive reconciliation; (5) audit evidence provenance and retention; (6) measured data-plane RPO/RTO and SLO; (7) incident response, exception governance and operational handover.

**Acceptance requires:** exact target and immutable source, protected CI identities, no skipped critical tests, reproducible policy deny tests, reviewed native plans, isolated Terratest/Molecule runs, live Kubernetes admission tests, real database restore and measured RPO/RTO, cloud inventory verification after cleanup, tamper-evident evidence independently sourced, and written approvals. A simulated PASS does not satisfy these conditions.

## 2. Enterprise reference architecture

~~~text
PR + CODEOWNERS + ticket + immutable commit
        |
 static tests: fmt/validate, SAST, secrets, SBOM, provenance
        |
 unit/policy: terraform test, OPA/Rego, Sentinel, mocks
        |
 protected OIDC -> isolated cloud account + unique lease/state
        |
 Terratest / Molecule / Pulumi / CloudFormation / Bicep
        |
 Kubernetes admission + GitOps + cloud IAM + native inventory
        |
 DBRE: PostgreSQL/MongoDB/Redis/Kafka/OpenSearch/Snowflake
        |              |
     backup restore    SLO/error budget and failover
        |
 drift discovery: desired vs actual vs policy vs telemetry
        |
 risk classifier -> notify / protected PR / quarantine
        |
 independent approvals -> safe reconciliation -> verify
        |
 signed evidence + object-lock retention + exception expiry
        |
 SRE/DBRE/Security/Audit 100-point production acceptance
~~~

**Trust boundaries:** pull-request runners have read-only permissions; cloud integration identities are limited to disposable test accounts/projects/subscriptions; production apply is a separate protected process; drift discovery is read-only; stateful destructive changes require DBRE and security approval; evidence writers cannot rewrite retained archives.

## 3. Detailed theory — four layers of assurance

### 3.1 Test correctness (Chapter 086)

Static lint, syntax and schema validation catch malformed configuration but not real cloud behavior. Unit tests and policy tests validate intended properties and negative paths. Plan assertions detect replace/delete and privilege expansion. Integration tests verify actual resource attributes. SLO and recovery tests demonstrate operating behavior. Each layer has an explicit owner, versioned tools, negative tests, pass/fail threshold and evidence retention.

### 3.2 Integration isolation (Chapter 087)

Each test run must use a unique ID, separate state key, dedicated identity, tagged cloud resources, cost cap, TTL, approved region and teardown owner. Terratest exercises provider outputs and APIs; Molecule verifies converge, idempotence and role behavior. Testcontainers or disposable VMs may validate local services but cannot substitute for managed-cloud identity, KMS, replication or provider behavior. On test failure, preserve evidence and quarantine the lease; never delete unowned resources.

### 3.3 Compliance and evidence (Chapter 088)

Map each internal control to risk, framework, native enforcement, owner, observation frequency, exception rules and evidence. NIST/CIS/SOC 2 examples are **illustrative mappings**, not regulatory determinations. A control is effective only when independently tested in the assessed scope and period. Protect artifact hashes, signatures, trusted timestamps, native cloud audit logs, K8s admission decisions, policy bundle versions, approvals and retention. Self-declared JSON cannot authenticate itself.

### 3.4 Drift and remediation (Chapter 089)

Distinguish configuration drift, policy drift, identity drift, data-plane drift and evidence drift. Terraform/OpenTofu refresh-only and normal plans answer different questions. CloudFormation drift and Azure what-if have resource/property limitations. GitOps controllers may overwrite emergency hotfixes. Classify exposure, data sensitivity, production impact and destructive actions; use low-risk automation only with an explicit allowlist. Never automatically delete databases, PVCs, state or keys.

## 4. Cross-platform validation matrix

| Technology | Native tests | Critical negative scenario | Production acceptance |
|---|---|---|---|
| Terraform/OpenTofu | fmt, validate, test, reviewed plan, isolated apply | database replace / state mismatch | immutable plan, target and state audit |
| Terratest | Go integration, cloud API, cleanup inventory | wrong account, orphan | scoped credentials and zero owned orphans |
| Ansible/Molecule | syntax, lint, converge, idempotence, verify | prod inventory, privilege escalation | isolated driver and no unauthorized change |
| Pulumi/CFN/Bicep | preview/change set/what-if + native resource check | IAM expansion | provider-native assertion |
| OPA/Sentinel | allow/deny unit tests, enforced binding | advisory or bypass | verified deployed policy mode |
| EKS/AKS/GKE | RBAC, PSA/admission, CNI, CSI, audit | cluster-admin, fail-open webhook | native admission and SLO |
| Argo CD/Flux | source, scope, drift, reconciliation | wrong repo/cluster | approved Git revision |
| PostgreSQL/Aurora/RDS | PITR, KMS, replica and failover | missing WAL, destructive replace | measured RPO/RTO and consistency |
| MongoDB | quorum, TLS, snapshot/restore | primary loss, stale backup | consistent restored data |
| Redis | ACL, persistence, failover | stale client ACL | reconnect and integrity |
| Kafka/MSK | IAM/ACL, ISR, lag, broker failover | ISR shortfall | durability and lag SLO |
| Elasticsearch/OpenSearch | shard health, snapshots, IOPS and query latency | snapshot failure | verified restore and query SLO |
| Snowflake | grants, masking, CDC reconciliation | privilege drift / missing rows | data correctness and least privilege |

## 5. Hands-on capstone labs

### Lab 1 — Fail-closed integrated assurance gate

~~~bash
cd infrastructure-as-code/labs/chapter-090
python3 capstone_gate.py fixtures/safe.json policy.json
python3 capstone_gate.py fixtures/unsafe.json policy.json # expected nonzero
bash run-preflight.sh
~~~

Checks an exact synthetic target, immutable digest, 40 declared controls, zero critical failures, test counts, evidence age, lease/cost, zero orphans and DBRE RPO/RTO. **It checks claims, not native operations.**

### Lab 2 — Coverage matrix and negative tests

`coverage_gate.py` checks required test layers, distinct test IDs, non-skipped critical tests, policy negative cases and explicit DBRE restore evidence claims. Missing layers or duplicate IDs fail closed.

### Lab 3 — Risk-based drift decision

`drift_decision.py` categorizes synthetic findings as `notify`, `review` or `quarantine`; destructive, critical, unknown and production database findings cannot auto-remediate.

### Lab 4 — Approval and rollback state machine

`reconciliation.py` models `detected -> classified -> approved -> reconciled -> verified -> closed`, enforcing independent approval and verified post-change SLO. No infrastructure mutation.

### Lab 5 — Evidence integrity

`audit_chain.py` verifies canonical JSON SHA-256 digests and linked records. A hash chain is tamper-evident only against an independently trusted anchor; this lab does not verify a signer or trusted timestamp.

### Lab 6 — Real staging game day (manual, not executed)

1. Obtain approved isolated AWS/Azure/GCP account and budget, protected workload identity and TTL lease.
2. Deploy a disposable module using Terraform/OpenTofu, then run native plan, Terratest and Molecule.
3. Deliberately introduce a low-risk tagged drift; confirm detection, exception check, approval and protected PR reconciliation.
4. Test deny rules for wildcard IAM, public ingress, disabled logging and destructive database replacement using native OPA/Sentinel/cloud/K8s controls.
5. Restore PostgreSQL or MongoDB from a real encrypted backup into an isolated target; measure data consistency, RPO and RTO; perform failover and SLO checks.
6. Exercise one negative security incident, preserve signed native evidence, validate object-lock retention, and independently verify cleanup.
7. Have SRE, DBRE, security and audit owners review the acceptance score and sign off. **Do not run on production.**

## 6. Production incident simulation catalog

| # | Scenario | First response |
|---|---|---|
| 1 | OIDC trust grants production account access | Quarantine unsafe promotion and verify identity, source and policy |
| 2 | Terraform plan replaces PostgreSQL cluster | Freeze unsafe changes; DBRE verifies recovery |
| 3 | OpenTofu remote state backend loses encryption | Quarantine unsafe promotion and verify identity, source and policy |
| 4 | Pulumi stack drifts after manual cloud change | Quarantine unsafe promotion and verify identity, source and policy |
| 5 | CloudFormation stack drift skips unsupported property | Quarantine unsafe promotion and verify identity, source and policy |
| 6 | Bicep what-if underreports RBAC impact | Quarantine unsafe promotion and verify identity, source and policy |
| 7 | Ansible inventory points to production | Quarantine unsafe promotion and verify identity, source and policy |
| 8 | Terratest destroys shared VPC | Quarantine unsafe promotion and verify identity, source and policy |
| 9 | Molecule converge changes privileged host | Quarantine unsafe promotion and verify identity, source and policy |
| 10 | Kubernetes admission policy set to audit | Preserve source, validate chain of custody |
| 11 | Gatekeeper webhook fails open | Quarantine unsafe promotion and verify identity, source and policy |
| 12 | Kyverno exception wildcard expands | Quarantine unsafe promotion and verify identity, source and policy |
| 13 | Argo CD Application targets wrong cluster | Quarantine unsafe promotion and verify identity, source and policy |
| 14 | Flux controller reconciles stale source | Quarantine unsafe promotion and verify identity, source and policy |
| 15 | AWS Config recorder disabled | Quarantine unsafe promotion and verify identity, source and policy |
| 16 | Azure Policy exemption expires | Quarantine unsafe promotion and verify identity, source and policy |
| 17 | GCP org policy inheritance changes | Quarantine unsafe promotion and verify identity, source and policy |
| 18 | CloudTrail evidence delivery fails | Preserve source, validate chain of custody |
| 19 | Azure Activity Log sink permissions revoked | Preserve source, validate chain of custody |
| 20 | GCP audit log retention reduced | Preserve source, validate chain of custody |
| 21 | IAM permission boundary removed | Quarantine unsafe promotion and verify identity, source and policy |
| 22 | Workload identity audience wildcard | Quarantine unsafe promotion and verify identity, source and policy |
| 23 | Secrets appear in Terraform state | Quarantine unsafe promotion and verify identity, source and policy |
| 24 | CI logs leak ephemeral credentials | Preserve source, validate chain of custody |
| 25 | Unsigned artifact promoted to production | Quarantine unsafe promotion and verify identity, source and policy |
| 26 | SBOM excludes vulnerable provider | Quarantine unsafe promotion and verify identity, source and policy |
| 27 | Policy bundle digest changes after approval | Quarantine unsafe promotion and verify identity, source and policy |
| 28 | OPA negative test is skipped | Quarantine unsafe promotion and verify identity, source and policy |
| 29 | Sentinel policy advisory rather than enforced | Quarantine unsafe promotion and verify identity, source and policy |
| 30 | Drift scanner observes stale inventory | Quarantine unsafe promotion and verify identity, source and policy |
| 31 | Alert suppression hides critical drift | Quarantine unsafe promotion and verify identity, source and policy |
| 32 | Auto-remediation deletes persistent volume | Quarantine unsafe promotion and verify identity, source and policy |
| 33 | Break-glass role remains enabled | Quarantine unsafe promotion and verify identity, source and policy |
| 34 | Evidence hash chain mismatch | Preserve source, validate chain of custody |
| 35 | Evidence timestamp outside audit period | Preserve source, validate chain of custody |
| 36 | Audit archive becomes publicly accessible | Preserve source, validate chain of custody |
| 37 | Exception approved by same owner | Quarantine unsafe promotion and verify identity, source and policy |
| 38 | Expired exception stays marked accepted | Quarantine unsafe promotion and verify identity, source and policy |
| 39 | SLO regression after network reconciliation | Quarantine unsafe promotion and verify identity, source and policy |
| 40 | Kubernetes DNS denied by NetworkPolicy | Quarantine unsafe promotion and verify identity, source and policy |
| 41 | PVC snapshot exists but cannot restore | Freeze unsafe changes; DBRE verifies recovery |
| 42 | RDS PITR misses required WAL | Freeze unsafe changes; DBRE verifies recovery |
| 43 | Aurora failover exceeds RTO | Freeze unsafe changes; DBRE verifies recovery |
| 44 | PostgreSQL migration lock exceeds SLO | Freeze unsafe changes; DBRE verifies recovery |
| 45 | MongoDB replica set loses quorum | Freeze unsafe changes; DBRE verifies recovery |
| 46 | MongoDB backup lacks consistent snapshot | Freeze unsafe changes; DBRE verifies recovery |
| 47 | Redis ACL rotation disconnects workers | Freeze unsafe changes; DBRE verifies recovery |
| 48 | Redis persistence disabled by drift | Freeze unsafe changes; DBRE verifies recovery |
| 49 | Kafka ISR below required minimum | Freeze unsafe changes; DBRE verifies recovery |
| 50 | MSK IAM ACL mismatch | Freeze unsafe changes; DBRE verifies recovery |
| 51 | OpenSearch snapshot repository unavailable | Freeze unsafe changes; DBRE verifies recovery |
| 52 | Elasticsearch shard count exceeds capacity | Freeze unsafe changes; DBRE verifies recovery |
| 53 | Snowflake role becomes ACCOUNTADMIN | Freeze unsafe changes; DBRE verifies recovery |
| 54 | Snowflake CDC pipeline misses rows | Freeze unsafe changes; DBRE verifies recovery |
| 55 | Multi-region failover creates split brain | Quarantine unsafe promotion and verify identity, source and policy |
| 56 | KMS key revoked before restore | Freeze unsafe changes; DBRE verifies recovery |
| 57 | Cloud API throttling hides drift | Quarantine unsafe promotion and verify identity, source and policy |
| 58 | Ephemeral test account exceeds cost budget | Quarantine unsafe promotion and verify identity, source and policy |
| 59 | Cleanup removes resources outside lease | Quarantine unsafe promotion and verify identity, source and policy |
| 60 | Recovery acceptance signed without live restore | Quarantine unsafe promotion and verify identity, source and policy |

## 7. Production runbooks

**R1 — Incident command, blast radius and containment:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

**R2 — Source integrity, provenance and OIDC:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

**R3 — Terraform/OpenTofu state and plan recovery:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

**R4 — Pulumi, CloudFormation and Bicep reconciliation:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

**R5 — Terratest and Molecule test isolation:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

**R6 — Kubernetes admission, RBAC and GitOps:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

**R7 — Cloud IAM and policy enforcement drift:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

**R8 — Audit evidence, chain of custody and retention:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

**R9 — PostgreSQL/RDS/Aurora PITR and RTO:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

**R10 — MongoDB, Redis, Kafka and OpenSearch recovery:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

**R11 — FinOps, TTL and orphan cleanup:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

**R12 — Final acceptance, exception closure and handoff:** Declare incident, identify owner and blast radius; halt unsafe automation; preserve source, native logs and immutable evidence; validate exact cloud account, policy, state, GitOps and data-plane impact; revoke compromised identity where applicable; obtain independent approvals; execute bounded rollback/recovery in an authorized environment; verify native tests, DBRE RPO/RTO and SLO; audit cleanup and exceptions; document corrective actions and closure.

## 8. Troubleshooting

| Failure | Investigation | Recovery |
|---|---|---|
| Tests green but production insecure | scanner scope, policy mode, native resource attributes | block promotion; verify real deny path |
| Terratest/Molecule flakiness | isolation, driver, eventual consistency, quotas | unique lease, bounded retries, evidence |
| Terraform replacement unexpected | state/provider/plan diff | halt, review backup and DBRE impact |
| Drift scan empty | read-only identity, inventory coverage, stale observation | restore recorder, scope and freshness |
| GitOps rollback reverted | controller source-of-truth | reconcile protected Git commit |
| Audit hash mismatch | canonicalization, tampering, trust anchor | quarantine, recollect independently |
| DB backup cannot restore | KMS, WAL/oplog, chain, permissions | DR runbook and measured retest |
| Cleanup incomplete | owner tags, finalizers, state locks | controlled, ownership-verified cleanup |

## 9. Final 100-point reliability assessment

| Domain | Points | Required evidence |
|---|---:|---|
| Architecture, trust boundaries and threat model | 15 | approved design, exact target |
| Multi-tool testing and isolated integration | 20 | native Terratest/Molecule/cloud logs |
| Policy, compliance and negative controls | 20 | enforced OPA/Sentinel/cloud/K8s evidence |
| Drift classification and safe remediation | 15 | incident/PR/rollback/SLO |
| DBRE restore, data integrity and RPO/RTO | 20 | real recovery drill |
| Audit chain, retention, cleanup and handoff | 10 | independently verified archive and signatures |
| **Total** | **100** | **Production acceptance pending** |

**Pass >=85 and zero critical failures.** Automatic failure for wrong production target, secret exposure, fail-open critical policy, unapproved destructive reconciliation, tampered evidence, unverified database restore, exceeded RPO/RTO or SLO regression. A synthetic fixture cannot earn native operational credit.

## 10. Part 18 completion and next chapter

This publication completes the **five-chapter Part 18 sequence (086–090)**, not live-lab or security certification. Update curriculum index and STATUS; keep native cloud integration, automated test execution, real DBRE restore and independent acceptance explicitly pending.

**Next:** Chapter 091 — IaC Observability Architecture, Telemetry, SLOs and Operational Dashboards (Part 19 — Observability and Drift).
