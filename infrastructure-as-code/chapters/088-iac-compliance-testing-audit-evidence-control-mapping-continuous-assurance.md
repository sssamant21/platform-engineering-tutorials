# Chapter 088 — IaC Compliance Testing, Audit Evidence, Control Mapping and Continuous Assurance

**Part 18 — Testing and Compliance · Chapter 088/120 · Enterprise SRE/DevOps/DBRE**

## Outcomes

Design a reproducible compliance-as-code operating model for Terraform/OpenTofu, Pulumi, CloudFormation, Bicep, Ansible, Kubernetes, GitOps and stateful data infrastructure. Build control catalogs, traceability from policy to enforcement to independently verifiable evidence, exception workflows, immutable audit archives, continuous monitoring and risk-based acceptance. Implement offline automated negative tests and evidence chain checks. Distinguish **published training artifacts** from **executed control tests** and **formal audit/compliance attestation**.

The companion Python standard-library lab is **offline and synthetic**. It checks claims, digests and control mappings supplied as JSON. It does not authenticate cloud accounts, verify external signatures, execute OPA/Sentinel or certify NIST/CIS/SOC 2/HIPAA/PCI compliance.

## 1. Compliance architecture and shared responsibility

~~~text
Policy owner / regulatory scope / control register
      |
  framework mapping + risk and owner
      |
 source PR + approved change + threat model
      |
 IaC lint/SAST/secret scan/SBOM/provenance
      |
 Terraform/OpenTofu/Pulumi/CFN/Bicep/Ansible plan
      |
 OPA/Sentinel/Cloud Guard/Azure Policy/GCP Org Policy
      |
 protected OIDC + native IAM + K8s admission
      |
 deployment audit / GitOps reconciliation / DBRE restore
      |
 runtime CSPM + cloud audit + SLO + drift
      |
 immutable evidence manifest, hashes and retention
      |
 independent control test -> exception -> remediation
      |
 SRE/DBRE/security/audit acceptance and revalidation
~~~

**Three lines of assurance:** (1) engineering owns controls and remediations; (2) security/compliance independently sets standards and challenges evidence; (3) internal/external auditors test operating effectiveness. Separation of duties prevents an IaC author from self-approving their production exceptions or rewriting audit artifacts.

## 2. Control catalog and mapping methodology

Each control must include unique ID, objective, scoped resources, accountable owner, risk tier, framework references, policy implementation, evidence source, frequency, retention, exception procedure and failure response. Example mappings below are **illustrative**, not legal or certification conclusions:

| Internal control | Objective | Example framework alignment | Native evidence |
|---|---|---|---|
| IAC-001 | approved, immutable changes | NIST CM, SOC 2 change management | signed commit, review, ticket, artifact digest |
| IAC-002 | least-privilege identity | NIST AC, CIS IAM, SOC 2 logical access | cloud IAM policies, OIDC trust, access tests |
| IAC-003 | secrets and encryption | NIST SC, CIS encryption | KMS, secret manager, scan reports |
| IAC-004 | enforced policy gates | NIST CM/SI, CIS configuration | OPA/Sentinel deny tests and policy-set binding |
| IAC-005 | tamper-evident audit trail | NIST AU, SOC 2 monitoring | cloud logs, immutable retention, digest chain |
| IAC-006 | backup and recoverability | NIST CP, SOC 2 availability | actual restore, RPO/RTO, DBRE approval |
| IAC-007 | continuous drift and vulnerability management | NIST CA/SI, CIS | scanner freshness, CSPM, drift alerts |
| IAC-008 | controlled exceptions | NIST RA/PM, SOC 2 risk management | scope, expiry, compensating control, approvals |

Mapping a rule to a framework does not prove the control is effective. Evidence must show **design** and **operation** over the assessed period; external assessors decide applicability and sufficiency.

## 3. Evidence model, provenance and chain of custody

Every evidence record should carry control ID, source system, immutable source revision, policy bundle version, target cloud account/cluster, timestamp, collector identity, result, owner, change ticket, artifact SHA-256 and retention classification. Protect sensitive plans, state and logs with encryption, access restrictions and immutable/versioned retention. Hashes detect content changes **only if** the expected digest is independently trusted; a self-declared hash alone does not prove origin or authenticity.

Recommended evidence families: protected Git PR and CODEOWNERS review, CI scan output, OPA/Sentinel decision logs, signed supply-chain provenance, Terraform plan/change-set digest, AWS CloudTrail/Azure Activity Log/GCP Audit Logs, Kubernetes audit/admission, GitOps reconciliation, backup restore logs, SLO dashboards and incident/change tickets.

## 4. Continuous compliance and policy tests

Implement policy gates at commit, plan, admission and runtime. **OPA/Rego**: test both allow and deny fixtures, enforce a default-deny decision and verify the deployed policy bundle/version. **Sentinel**: distinguish advisory, soft-mandatory and hard-mandatory; test policy-set attachment and authorized overrides. **AWS**: IAM/SCP, AWS Config and CloudTrail. **Azure**: Policy assignments, exemptions, Defender/Activity Logs. **GCP**: Org Policy, Cloud Asset Inventory, audit logs. **Kubernetes**: Pod Security Admission, Kyverno/Gatekeeper/ValidatingAdmissionPolicy, RBAC and audit. Re-run after every policy, provider, identity, drift or topology change.

Scan tool coverage is not a compliance verdict. Document false positives, missed resources, unsupported providers and rule version. Deny unknown critical results rather than silently treating skipped checks as PASS.

## 5. Exception management and risk acceptance

Require: exact control and resource scope; incident/change ticket; reason; accountable owner; independent approver; compensating controls; expiry; renewal review and evidence. A break-glass action is time-limited, logged and reconciled. Reject wildcard scope, self-approval, missing compensating controls and expired exceptions. High-impact database delete/replace needs DBRE and security authorization plus a tested recovery path.

## 6. DBRE-specific continuous assurance

| Platform | Control | Independent operating evidence |
|---|---|---|
| PostgreSQL/RDS/Aurora | encryption, PITR, restricted roles, approved schema changes | restore logs, KMS decrypt, RPO/RTO and replication |
| MongoDB | TLS, RBAC, backup encryption, quorum | audit, replica-set failover, consistent restore |
| Redis | TLS, ACL, persistence | ACL review, reconnect and failover drill |
| Kafka/MSK | IAM/SASL/TLS, ACL, durability | consumer/producer tests, ISR and lag |
| OpenSearch/Elasticsearch | index permissions, snapshot, capacity | restore, shard health and query SLO |
| Snowflake | least privilege, lineage, retention, masking | grants, query history, reconciliation |
| EKS/AKS/GKE | RBAC, admission, network and storage | native admission, CNI, CSI restore and audit |

A backup status flag is insufficient. Execute isolated restore, validate decryption, data integrity and measured RPO/RTO. Protect clinical or regulated data: use synthetic fixtures and approved de-identified datasets for labs.

## 7. Hands-on labs — offline and executable

### Lab A: Control catalog and evidence gate

~~~bash
cd infrastructure-as-code/labs/chapter-088
python3 compliance_gate.py fixtures/safe.json policy.json
python3 compliance_gate.py fixtures/unsafe.json policy.json  # must reject
bash run-preflight.sh
~~~

Checks exact synthetic environment, immutable artifact, required control IDs, zero critical findings, all control statuses PASS, bounded evidence age, restore and SLO claims, and no expired exception. No cloud access.

### Lab B: Control mapping completeness

`mapping_gate.py` checks eight required internal controls, framework references, unique owners, implementation references, test frequency and evidence type. Missing, duplicated or unsupported mappings fail closed.

### Lab C: Audit evidence chain

`evidence_chain.py` recomputes SHA-256 of canonical JSON payloads and checks ordered `previous_digest` links. This detects accidental or malicious modification **against the supplied manifest**, but cannot independently authenticate who created the manifest.

### Lab D: Exception governance

`exception_gate.py` rejects expired, wildcard, self-approved, unowned and uncompensated exceptions. Time is passed explicitly in test fixtures for deterministic behavior.

### Lab E: Native integration procedure (not executed)

In an approved staging account, capture real IAM and OIDC negative tests, OPA/Sentinel policy results, provider plans, cloud audit logs, K8s admission and GitOps reconciliation, signed provenance, scanner reports, and actual database restore. Export read-only evidence with independent trusted timestamp and object-lock policy; verify hash and retention from a separate identity. Document sampling window and gaps. **Do not run production mutation from this chapter.**

## 8. Production SRE/DBRE incident simulations

| # | Scenario | First response |
|---|---|---|
| 1 | IaC change lacks approved ticket | Block unsafe promotion, inspect control enforcement and ownership |
| 2 | Evidence archive bucket accidentally public | Preserve source, verify chain of custody and independent audit |
| 3 | CloudTrail logging disabled during rollout | Preserve source, verify chain of custody and independent audit |
| 4 | Azure Activity Log retention shortened | Preserve source, verify chain of custody and independent audit |
| 5 | GCP audit log sink permission revoked | Preserve source, verify chain of custody and independent audit |
| 6 | OPA rule changed without policy approval | Block unsafe promotion, inspect control enforcement and ownership |
| 7 | Sentinel policy set moved to advisory | Block unsafe promotion, inspect control enforcement and ownership |
| 8 | CIS benchmark mapping references obsolete rule | Block unsafe promotion, inspect control enforcement and ownership |
| 9 | NIST control mapped without technical proof | Block unsafe promotion, inspect control enforcement and ownership |
| 10 | SOC 2 evidence collected from wrong period | Preserve source, verify chain of custody and independent audit |
| 11 | HIPAA safeguard claimed without risk assessment | Block unsafe promotion, inspect control enforcement and ownership |
| 12 | PCI scope includes undocumented subnet | Block unsafe promotion, inspect control enforcement and ownership |
| 13 | Exception approval expires without remediation | Block unsafe promotion, inspect control enforcement and ownership |
| 14 | Exception owner leaves organization | Block unsafe promotion, inspect control enforcement and ownership |
| 15 | Exception compensating control absent | Block unsafe promotion, inspect control enforcement and ownership |
| 16 | Control test reports PASS from stale fixture | Block unsafe promotion, inspect control enforcement and ownership |
| 17 | Scanner signature database outdated | Block unsafe promotion, inspect control enforcement and ownership |
| 18 | Checkov scan skips critical module | Block unsafe promotion, inspect control enforcement and ownership |
| 19 | Trivy policy gate bypassed | Block unsafe promotion, inspect control enforcement and ownership |
| 20 | Terraform plan artifact overwritten | Block unsafe promotion, inspect control enforcement and ownership |
| 21 | State backend KMS key inaccessible | Block unsafe promotion, inspect control enforcement and ownership |
| 22 | Terraform state versioning disabled | Block unsafe promotion, inspect control enforcement and ownership |
| 23 | OpenTofu plan has unreviewed delete | Block unsafe promotion, inspect control enforcement and ownership |
| 24 | Pulumi stack audit misses secret rotation | Block unsafe promotion, inspect control enforcement and ownership |
| 25 | CloudFormation change set unsigned | Block unsafe promotion, inspect control enforcement and ownership |
| 26 | Bicep deployment missing Azure Policy exemption | Block unsafe promotion, inspect control enforcement and ownership |
| 27 | Ansible playbook runs with privileged identity | Block unsafe promotion, inspect control enforcement and ownership |
| 28 | GitHub Actions runner exposes OIDC token | Block unsafe promotion, inspect control enforcement and ownership |
| 29 | GitLab artifact retained without access controls | Block unsafe promotion, inspect control enforcement and ownership |
| 30 | SBOM missing provider dependency | Block unsafe promotion, inspect control enforcement and ownership |
| 31 | Provenance attestation signed by unknown identity | Preserve source, verify chain of custody and independent audit |
| 32 | Supply chain build uses mutable action tag | Block unsafe promotion, inspect control enforcement and ownership |
| 33 | Kubernetes admission webhook fail-open | Block unsafe promotion, inspect control enforcement and ownership |
| 34 | Gatekeeper constraint not deployed to production | Block unsafe promotion, inspect control enforcement and ownership |
| 35 | Kyverno policy set to Audit | Block unsafe promotion, inspect control enforcement and ownership |
| 36 | Kubernetes RBAC grants cluster-admin | Block unsafe promotion, inspect control enforcement and ownership |
| 37 | Argo CD AppProject allows all destinations | Block unsafe promotion, inspect control enforcement and ownership |
| 38 | Flux reconciliation ignores protected branch | Block unsafe promotion, inspect control enforcement and ownership |
| 39 | EKS cluster audit logs absent | Preserve source, verify chain of custody and independent audit |
| 40 | AKS Key Vault access policy overbroad | Block unsafe promotion, inspect control enforcement and ownership |
| 41 | GKE WIF subject wildcard | Block unsafe promotion, inspect control enforcement and ownership |
| 42 | PostgreSQL backup retention below RPO | Freeze destructive changes; DBRE validates recovery |
| 43 | Aurora PITR restore untested | Freeze destructive changes; DBRE validates recovery |
| 44 | MongoDB audit logs missing | Preserve source, verify chain of custody and independent audit |
| 45 | MongoDB backup encryption key revoked | Freeze destructive changes; DBRE validates recovery |
| 46 | Redis ACL audit shows admin role | Freeze destructive changes; DBRE validates recovery |
| 47 | Kafka/MSK topic ACL drift | Freeze destructive changes; DBRE validates recovery |
| 48 | OpenSearch snapshot repository unavailable | Freeze destructive changes; DBRE validates recovery |
| 49 | Elasticsearch data retention exception overdue | Freeze destructive changes; DBRE validates recovery |
| 50 | Snowflake ACCOUNTADMIN used by automation | Freeze destructive changes; DBRE validates recovery |
| 51 | Snowflake query history evidence incomplete | Preserve source, verify chain of custody and independent audit |
| 52 | Database schema change has no DBRE approval | Block unsafe promotion, inspect control enforcement and ownership |
| 53 | DR test exceeds RTO | Freeze destructive changes; DBRE validates recovery |
| 54 | Recovery evidence omits KMS decrypt | Preserve source, verify chain of custody and independent audit |
| 55 | Canary SLO regression ignored | Block unsafe promotion, inspect control enforcement and ownership |
| 56 | Change freeze bypassed for emergency | Block unsafe promotion, inspect control enforcement and ownership |
| 57 | Compliance evidence includes plaintext secrets | Preserve source, verify chain of custody and independent audit |
| 58 | Evidence hash mismatches original artifact | Preserve source, verify chain of custody and independent audit |
| 59 | Auditor cannot reproduce control result | Block unsafe promotion, inspect control enforcement and ownership |
| 60 | Continuous monitoring stops after deployment | Block unsafe promotion, inspect control enforcement and ownership |

## 9. Production runbooks

**R1 — Compliance incident command and scope:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

**R2 — Evidence tampering and immutable archive recovery:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

**R3 — OPA/Sentinel policy enforcement drift:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

**R4 — IAM least-privilege and OIDC investigation:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

**R5 — Secrets exposure and evidence sanitization:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

**R6 — Kubernetes/GitOps admission compliance:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

**R7 — Terraform/OpenTofu/Pulumi state governance:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

**R8 — Multi-cloud audit logging recovery:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

**R9 — DBRE backup/PITR/RPO/RTO evidence:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

**R10 — Exception expiry and compensating control:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

**R11 — Supply-chain provenance and scanner freshness:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

**R12 — Auditor handoff, SLO and closure:** Declare incident and accountable owner; preserve immutable logs and evidence; identify control, target and assessed period; contain policy/identity or DBRE exposure; validate native enforcement and restore where relevant; document exceptions and remediation; repeat negative tests and SLO checks; obtain independent SRE/DBRE/security acceptance and auditor handoff.

## 10. Troubleshooting and false assurance

| Symptom | Investigation | Corrective action |
|---|---|---|
| Policy scan PASS but resource insecure | deployed policy assignment and runtime inventory | fail closed, reconcile native controls |
| Evidence hash mismatch | canonicalization, source, chain links | quarantine and recollect independently |
| Exception expired | expiry, scope, owner and approver | revoke or independently reapprove |
| Audit logs missing | cloud audit sink, IAM, retention | restore logging and document evidence gap |
| Terraform plan differs from approved commit | artifact and state digest | stop deployment and regenerate approval |
| K8s admission differs by cluster | webhook mode, namespace labels | validate each environment natively |
| DB backup exists but restore fails | KMS, permissions, backup chain | invoke DR, retest RPO/RTO |
| Scanner reports stale | signature DB, version, scope | rerun fresh and block critical changes |

## 11. 100-point enterprise assessment

| Domain | Points |
|---|---:|
| Architecture, governance and framework mapping | 20 |
| Evidence integrity, provenance and chain of custody | 20 |
| Multi-cloud/Kubernetes policy and compliance testing | 20 |
| Offline labs, negative tests and exception governance | 15 |
| DBRE restore, SLO and continuous assurance | 15 |
| Audit handover, runbooks and independent sign-off | 10 |
| **Total** | **100** |

**Pass >=85** with no critical failure. Critical: fabricated or tampered evidence, disabled audit, unapproved wildcard exception, fail-open production policy, exposed secrets, destructive database action without verified restore, or exceeded RPO/RTO. Require independent native cloud/Kubernetes evidence and signed security/SRE/DBRE acceptance. **Publication and synthetic fixtures are not compliance certification.**

**Next:** Chapter 089 — IaC Continuous Compliance Monitoring, Drift Detection, Remediation and Audit Automation.
