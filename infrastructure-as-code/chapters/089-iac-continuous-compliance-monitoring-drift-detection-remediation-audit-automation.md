# Chapter 089 — IaC Continuous Compliance Monitoring, Drift Detection, Remediation and Audit Automation

**Part 18 — Testing and Compliance · Chapter 089/120 · Enterprise SRE/DevOps/DBRE**

## 1. Learning outcomes

Build a continuous assurance program that detects divergence between desired IaC, provider state, deployed configuration and runtime policy; classifies risk; routes incidents; enforces human-approved remediation for high-impact changes; and creates reproducible, tamper-evident audit records. The chapter covers Terraform/OpenTofu, Pulumi, CloudFormation, Bicep, Ansible, Kubernetes, Argo CD/Flux, OPA/Sentinel, AWS/Azure/GCP, and PostgreSQL, MongoDB, Redis, Kafka, Elasticsearch/OpenSearch and Snowflake.

**Execution boundary:** Companion Python 3 standard-library labs are offline and use synthetic JSON. They do not access cloud APIs, run Terraform or Kubernetes, remediate resources, authenticate evidence or establish compliance certification. The native operational steps require isolated staging environments and independent approvals.

## 2. Reference architecture

~~~text
Protected Git / module registry / approved policy bundles
                |
           desired-state inventory
                |
 provider refresh + read-only cloud APIs + K8s API + DB telemetry
                |
     normalized observation + provenance + timestamp
                |
   drift classifier + policy/exception engine + risk scoring
                |
  low-risk notify / medium-risk PR / critical quarantine + incident
                |
     independent approval + immutable plan + bounded identity
                |
     controlled reconcile / GitOps / native remediation
                |
   post-change assertion + SLO + backup/restore health
                |
    signed audit event + retention + exception closure
~~~

Do not confuse **configuration drift** (live state differs from desired), **policy drift** (enforcement changes), **security drift** (identity/network exposure), **data-plane drift** (database health/capacity), and **evidence drift** (logs stale or unverifiable). Drift may also be intentional emergency repair. Classify and preserve evidence before reverting.

## 3. Detection strategies and limitations

| Layer | Native method | Evidence and caveat |
|---|---|---|
| Terraform/OpenTofu | scheduled read-only `plan -refresh-only` and reviewed normal plan | refresh-only shows remote-state changes; a normal plan is needed to evaluate desired changes; no apply in scanner |
| Pulumi | `pulumi refresh --preview-only` where supported, preview, stack history | validate pinned CLI/provider and stack |
| CloudFormation | `detect-stack-drift` / describe drift | resource-type/property coverage is incomplete |
| Azure Bicep | ARM what-if plus Azure Policy/resource graph | what-if is predictive, not proof of runtime enforcement |
| AWS | Config, CloudTrail, IAM Access Analyzer, inventory | recording scope and delivery lag matter |
| Azure | Azure Policy, Activity Logs, Defender, Resource Graph | exemptions and assignment scope matter |
| GCP | Org Policy, Cloud Asset Inventory, Audit Logs | feed latency and permission gaps matter |
| Kubernetes | server-side diff, audit, Gatekeeper/Kyverno, RBAC checks | controllers can revert manual changes |
| GitOps | Argo CD OutOfSync/Health; Flux reconciliation status | Git source may itself be compromised |
| DBRE | backup status, replication, PITR, ACL, KMS, SLO, snapshot/restore | green backups do not prove restorable data |

Schedule discovery according to risk (e.g., identity/network changes more frequently than low-impact tags). Measure **detection latency**, **mean time to acknowledge**, **time to remediate**, **false-positive rate**, **unmonitored scope**, **stale evidence**, **orphan resources**, **exception age** and **SLO impact**.

## 4. Drift classification, priority and safety

Normalize every finding to resource ID, account/tenant/project, region/cluster, desired and observed values, change source, timestamp, owner, environment, policy version and evidence hash. Critical examples: wildcard cloud IAM, public database endpoint, disabled audit, expired exception, missing backup, destructive DB replacement or KMS recovery failure.

**Never auto-remediate blindly:** resource delete/replace, stateful storage, database schema, network isolation, identity revocation, KMS changes and GitOps pruning require an approved plan, rollback, impact analysis, restore validation and DBRE/SRE sign-off. A low-risk tag repair can be automated only under explicit allowlist, ownership verification, least-privilege identity, idempotence and canary/SLO gates.

## 5. Reconciliation state machine and incident ownership

States: `detected -> classified -> approved -> remediating -> verified -> closed`. A policy failure, stale observation, target mismatch, critical impact or missing approval transitions to `quarantined`. Require independent security/DBRE approval for destructive stateful changes; break-glass needs ticket, expiry, alert and after-action reconciliation. Avoid force-unlocking state or running `terraform apply` merely to suppress an alert.

## 6. Continuous compliance and audit evidence

Attach each decision to a control catalog (NIST/CIS/SOC 2 mappings are illustrative), rule bundle version, immutable source revision, deployment target, observed native telemetry, change ticket, exception ID, approver, timestamp, artifact digest and remediation outcome. Store encrypted, access-controlled, versioned/object-locked evidence with explicit retention. **SHA-256 detects modifications only relative to an independently trusted expected digest; it does not authenticate a collector.** Validate signing identity and timestamps in a real system.

An exception must be resource-scoped, owner-assigned, independently approved, justified, compensated and time-limited. Expiry automatically reopens risk; it does not authorize destructive remediation.

## 7. SRE/DBRE operating playbook

- **PostgreSQL/Aurora/RDS:** compare encryption, backup retention, replication lag, PITR/WAL and actual restore RPO/RTO; stop unsafe plan replacement.
- **MongoDB:** inspect replica quorum, backup/restore, TLS and role drift; validate consistent recovery.
- **Redis:** verify ACL, persistence, failover and client reconnection.
- **Kafka/MSK:** verify ACL, ISR, replication, lag and broker identity.
- **OpenSearch/Elasticsearch:** verify snapshots, shard placement, storage IOPS, index lifecycle and latency SLO.
- **Snowflake:** inspect grants, masking, retention, warehouse and CDC reconciliation.
- **EKS/AKS/GKE:** check workload identity, RBAC, admission, network policies, CSI and audit sinks.

Use read-only discovery first; measure RPO/RTO with isolated recovery tests, not metadata claims. For regulated workloads, use approved synthetic or de-identified data.

## 8. Executable hands-on labs

### Lab A — Detect and classify drift

~~~bash
cd infrastructure-as-code/labs/chapter-089
python3 drift_gate.py fixtures/safe.json policy.json
python3 drift_gate.py fixtures/unsafe.json policy.json  # expected rejection
bash run-preflight.sh
~~~

`drift_gate.py` validates exact synthetic target, immutable artifact, observation freshness, 30 claimed controls, zero critical findings and DBRE recovery/SLO evidence.

### Lab B — Deterministic risk scoring

`risk_engine.py` scores synthetic findings using environment, exposure, data impact, destructive actions and missing approvals. Critical or unknown fields fail closed. Scores do not replace native risk assessment.

### Lab C — Safe remediation state machine

`remediation.py` models approval, quarantine, post-remediation verification and closure. No infrastructure mutation occurs.

### Lab D — Audit-chain validation

`audit_chain.py` checks canonical JSON SHA-256 hashes and linked audit events, detecting tampering against a supplied manifest; it does not validate external signatures.

### Lab E — Native staging exercise (procedure, not executed)

In a separately authorized test account, deliberately modify a tagged low-risk resource and observe scheduled native refresh/plan, cloud inventory, policy violation, PR-based remediation, GitOps reconciliation, post-change SLO, resource inventory and audit retention. In a second isolated database test, deliberately change a backup setting, **do not auto-apply a fix**, obtain DBRE approval, verify restore and capture RPO/RTO. Prohibit production mutations.

## 9. Production incident simulations

| # | Scenario | First action |
|---|---|---|
| 1 | AWS security group opens database port to internet | Stop destructive changes; DBRE validates recovery |
| 2 | Azure NSG rule permits unrestricted inbound traffic | Quarantine automatic remediation; verify source, target and policy |
| 3 | GCP firewall allows SSH from all sources | Quarantine automatic remediation; verify source, target and policy |
| 4 | AWS RDS encryption disabled by replacement | Quarantine automatic remediation; verify source, target and policy |
| 5 | Aurora backup retention reduced | Stop destructive changes; DBRE validates recovery |
| 6 | PostgreSQL PITR gap exceeds RPO | Stop destructive changes; DBRE validates recovery |
| 7 | MongoDB backup policy removed | Stop destructive changes; DBRE validates recovery |
| 8 | Redis ACL widened to all commands | Stop destructive changes; DBRE validates recovery |
| 9 | MSK topic ACL allows anonymous read | Stop destructive changes; DBRE validates recovery |
| 10 | Kafka min.insync.replicas lowered | Stop destructive changes; DBRE validates recovery |
| 11 | OpenSearch snapshot policy disabled | Stop destructive changes; DBRE validates recovery |
| 12 | Elasticsearch shard allocation disabled | Stop destructive changes; DBRE validates recovery |
| 13 | Snowflake role granted ACCOUNTADMIN | Stop destructive changes; DBRE validates recovery |
| 14 | EKS audit logs disabled | Preserve chain of custody and restore telemetry |
| 15 | AKS workload identity binding widened | Quarantine automatic remediation; verify source, target and policy |
| 16 | GKE node service account elevated | Quarantine automatic remediation; verify source, target and policy |
| 17 | Kubernetes ClusterRoleBinding adds cluster-admin | Quarantine automatic remediation; verify source, target and policy |
| 18 | Kyverno enforcement changed to Audit | Preserve chain of custody and restore telemetry |
| 19 | Gatekeeper webhook failure policy Ignore | Quarantine automatic remediation; verify source, target and policy |
| 20 | Argo CD Application source branch changed | Quarantine automatic remediation; verify source, target and policy |
| 21 | Flux Kustomization pruning enabled unexpectedly | Quarantine automatic remediation; verify source, target and policy |
| 22 | Terraform remote state lock lost | Quarantine automatic remediation; verify source, target and policy |
| 23 | OpenTofu provider lockfile changed | Quarantine automatic remediation; verify source, target and policy |
| 24 | Pulumi stack drift ignored | Quarantine automatic remediation; verify source, target and policy |
| 25 | CloudFormation stack drift reported | Quarantine automatic remediation; verify source, target and policy |
| 26 | Bicep deployment overwritten outside Git | Quarantine automatic remediation; verify source, target and policy |
| 27 | Ansible host inventory changed to production | Quarantine automatic remediation; verify source, target and policy |
| 28 | GitHub OIDC trust subject wildcard | Quarantine automatic remediation; verify source, target and policy |
| 29 | GitLab protected environment removed | Quarantine automatic remediation; verify source, target and policy |
| 30 | S3 audit evidence bucket public | Preserve chain of custody and restore telemetry |
| 31 | CloudTrail delivery delayed | Quarantine automatic remediation; verify source, target and policy |
| 32 | Azure Activity Log export fails | Preserve chain of custody and restore telemetry |
| 33 | GCP log sink writer loses permission | Preserve chain of custody and restore telemetry |
| 34 | Scanner misses newly created resources | Quarantine automatic remediation; verify source, target and policy |
| 35 | CSPM findings backlog exceeds SLA | Preserve chain of custody and restore telemetry |
| 36 | Exception expires before remediation | Quarantine automatic remediation; verify source, target and policy |
| 37 | Emergency break-glass role persists | Quarantine automatic remediation; verify source, target and policy |
| 38 | Drift auto-remediation destroys persistent volume | Quarantine automatic remediation; verify source, target and policy |
| 39 | Controller reconciles against stale plan | Quarantine automatic remediation; verify source, target and policy |
| 40 | Cloud API rate limit creates false-negative | Quarantine automatic remediation; verify source, target and policy |
| 41 | KMS key rotation blocks backup restore | Stop destructive changes; DBRE validates recovery |
| 42 | Certificate rotation causes admission failure | Quarantine automatic remediation; verify source, target and policy |
| 43 | FinOps tag removed from RDS | Quarantine automatic remediation; verify source, target and policy |
| 44 | Object lock retention shortened | Preserve chain of custody and restore telemetry |
| 45 | Unapproved region introduced | Quarantine automatic remediation; verify source, target and policy |
| 46 | Immutable artifact digest mismatches deployment | Quarantine automatic remediation; verify source, target and policy |
| 47 | SLO breaches after automated rollback | Quarantine automatic remediation; verify source, target and policy |
| 48 | NetworkPolicy blocks monitoring agents | Quarantine automatic remediation; verify source, target and policy |
| 49 | Prometheus alert silence remains active | Quarantine automatic remediation; verify source, target and policy |
| 50 | Cost budget exceeds limit after drift | Quarantine automatic remediation; verify source, target and policy |
| 51 | Ephemeral resource TTL sweep targets prod | Quarantine automatic remediation; verify source, target and policy |
| 52 | StatefulSet volume expansion pending | Quarantine automatic remediation; verify source, target and policy |
| 53 | GitOps controller loses repository access | Quarantine automatic remediation; verify source, target and policy |
| 54 | Audit record timestamps out of order | Preserve chain of custody and restore telemetry |
| 55 | Evidence manifest hash mismatch | Preserve chain of custody and restore telemetry |
| 56 | Control owner no longer active | Quarantine automatic remediation; verify source, target and policy |
| 57 | Policy exception lacks independent approver | Quarantine automatic remediation; verify source, target and policy |
| 58 | RPO metric based on stale backup | Stop destructive changes; DBRE validates recovery |
| 59 | RTO excludes restore validation | Stop destructive changes; DBRE validates recovery |
| 60 | Cross-region replication lag unobserved | Quarantine automatic remediation; verify source, target and policy |

## 10. Production runbooks

**R1 — Triage and classify drift:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

**R2 — Quarantine unsafe automatic remediation:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

**R3 — AWS/Azure/GCP policy drift:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

**R4 — Terraform/OpenTofu state reconciliation:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

**R5 — Kubernetes admission and RBAC drift:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

**R6 — GitOps Argo CD/Flux source-of-truth recovery:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

**R7 — Secrets/IAM and OIDC incident:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

**R8 — PostgreSQL/Aurora PITR and KMS:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

**R9 — MongoDB/Redis/Kafka/OpenSearch recovery:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

**R10 — Compliance exception and risk review:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

**R11 — Audit evidence chain and retention:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

**R12 — SLO, rollback and independent closure:** Establish resource, account, owner and incident severity; stop unsafe automation; preserve read-only observation and logs; validate Git/source, provider drift and enforcement; identify approved exceptions; obtain independent approvals; prepare rollback and DBRE recovery where relevant; reconcile through protected workflows; verify SLO and resource inventory; archive native evidence and close with corrective action.

## 11. Troubleshooting

| Symptom | Likely cause | Recovery |
|---|---|---|
| No drift findings despite cloud changes | missing permissions, recorder disabled, wrong scope | validate read-only identity, recorder coverage and timestamps |
| Terraform plan unexpectedly replaces DB | provider/schema drift, state mismatch | halt; inspect diff and backups; DBRE approval |
| GitOps keeps reverting hotfix | desired Git revision unchanged | reconcile approved source; preserve emergency record |
| OPA/Sentinel passes but unsafe change deploys | advisory mode, wrong policy set | inspect deployed enforcement and negative test |
| False-positive drift | computed values, eventual consistency | bounded retry, documented suppression and native verification |
| Audit evidence hash fails | changed payload or canonicalization | quarantine; recollect from trusted source |
| Remediation causes SLO breach | unintended network/identity impact | halt and rollback with canary/SLO |
| Exception never closes | missing expiry/owner | assign accountable owner, time-bound approval |

## 12. 100-point acceptance

| Domain | Points |
|---|---:|
| Detection architecture and trust boundaries | 15 |
| Multi-cloud, Terraform/OpenTofu and GitOps drift coverage | 20 |
| Classification, approval and safe remediation | 20 |
| Offline labs, negative tests and evidence chain | 20 |
| DBRE restore, RPO/RTO and SLO assurance | 15 |
| Audit retention, incident runbooks and sign-off | 10 |
| **Total** | **100** |

**Pass >=85 and zero critical failures.** Critical includes production target confusion, unapproved destructive automation, fail-open policy, tampered audit, missing DB restore, exceeded RPO/RTO or SLO regression. Publication and synthetic tests do not establish operational or regulatory acceptance.

**Next:** Chapter 090 — Enterprise IaC Testing, Compliance, Drift and Audit Reliability Capstone.
