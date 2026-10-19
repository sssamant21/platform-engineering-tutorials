# Chapter 085 — Enterprise IaC Security, Policy and Zero-Trust Production Readiness Capstone

**Part 17 — Security and Policy · Chapter 085/120 · Final capstone for Part 17**

## Purpose and learning outcomes

Integrate Chapters **081–084** into one auditable, production-oriented infrastructure security program. Design and verify threat modeling, workload identity, least-privilege cloud IAM, Kubernetes authorization, policy as code, secrets management, supply-chain integrity, continuous compliance, controlled promotion and DBRE disaster recovery. Deliver a **100-point acceptance decision** with independent evidence, rather than a checklist that merely asserts compliance.

**Scope:** Terraform/OpenTofu, Pulumi, CloudFormation, Bicep, Ansible, Helm/Kustomize, Kubernetes EKS/AKS/GKE, Argo CD/Flux, PostgreSQL/Aurora/RDS, MongoDB, Redis, Kafka/MSK, OpenSearch/Elasticsearch and Snowflake.

**Lab safety:** The companion Python standard-library lab runs **offline only** with synthetic evidence. Its passing fixture does not verify OIDC tokens, signatures, real policy engines, production access, actual restores or compliance certification.

## 1. Reference enterprise architecture

~~~text
Developer PR / signed source / CODEOWNERS
              |
       unprivileged CI
  IaC lint + SAST + secrets + SBOM
  provider locks + provenance + OPA
              |
    immutable plan and artifact
              |
  Security / SRE / DBRE approval
    exact commit + target + ticket
              |
       protected deployment
   exact OIDC federation + short TTL
   cloud IAM boundaries + org policy
              |
  native preview + plan policy gates
   Sentinel / OPA / CrossGuard / Guard
              |
   encrypted locked/versioned state
   KMS + secret manager + audit trail
              |
   cloud API + Kubernetes admission
     scoped RBAC + GitOps ownership
              |
    canary SLO + error budget gates
              |
  backups/PITR + restore + DR evidence
              |
  continuous compliance + drift/SIEM
              |
 signed acceptance and audit archive
~~~

### Security and reliability invariants

1. Untrusted pull requests cannot access protected deployment credentials.
2. A production release is bound to one immutable source commit, artifact digest, plan digest, target account/cluster and change ticket.
3. Cloud roles use exact OIDC issuer/audience/subject and minimum permissions; no wildcard administrative trust or persistent cloud keys.
4. State is encrypted, versioned, access-scoped, locked and auditable; KMS recovery is tested.
5. OPA/Sentinel and cloud-side guardrails fail closed; advisory-only results never masquerade as enforced policy.
6. Kubernetes RBAC is namespace-scoped; privileged admission and GitOps controllers have independent constraints.
7. Secret exposure triggers revoke/rotate and audit, not merely deletion of the latest Git commit.
8. Stateful production changes require DBRE approval, verified PITR, restore rehearsal, quorum/replication checks and RPO/RTO.
9. Canary SLO and error budget gates block promotion when unhealthy.
10. Exceptions are exact-scope, two-person approved, compensating, expiring and auditable.

## 2. Threat model and zero-trust boundaries

Use STRIDE across source repository, CI runner, artifact registry, OIDC issuer, cloud control plane, state backend, KMS, Kubernetes API, GitOps controllers, data stores and backup accounts. Rate likelihood and impact, assign an owner and control, and track residual risk. Focus on credential theft, privilege escalation, policy bypass, state exfiltration, malicious provider dependencies, admission failure and destructive database changes.

**Zero trust is continuous verification:** verify identity, source, target, authorization, runtime state and evidence at each boundary. A passing offline JSON flag is not proof. Real enforcement requires independent native APIs, signed attestations and logs.

## 3. Identity, IAM and policy controls

**AWS:** protected GitHub/GitLab OIDC with exact trust conditions; scoped roles, permissions boundaries, SCPs, KMS, CloudTrail and state backend access. **Azure:** Entra federation, narrowly scoped RBAC, Azure Policy, Key Vault and tenant/subscription verification. **GCP:** workload identity federation, IAM Conditions, org policies, Secret Manager and audit. **Kubernetes:** ServiceAccount isolation, Roles/RoleBindings, Pod Security Admission, NetworkPolicy, Gatekeeper/Kyverno/ValidatingAdmissionPolicy, audit and `kubectl auth can-i` tests. **GitOps:** Argo CD AppProjects and Flux impersonation with single-writer reconciliation.

**OPA/Rego and Sentinel:** use native plan/admission inputs and independently trusted policy bundles; enforce deny for destructive changes, insecure networks, unencrypted state, unrestricted IAM and missing DBRE recovery. Verify Sentinel policy-set attachment and enforcement level. Do not treat a sample Rego boolean or Sentinel placeholder as production-ready policy.

## 4. Supply chain, secrets and compliance

Pin and verify dependencies, provider checksums, build runners, action commits and container digests. Generate SBOMs and validate signed provenance against trusted builder identity. Use secret scanners (Gitleaks/TruffleHog), IaC scanners (Checkov/Trivy), vulnerability scanners and runtime CSPM/cloud policy; correlate their coverage and gaps. Protect plan/state artifacts as sensitive data.

Compliance is continuous: source baseline -> preflight -> deploy policy -> runtime inventory -> drift alerts -> remediation -> evidence. Retain scan version, rules, artifact digest, exception scope, owner, change ticket, approval and closure. Framework mappings (CIS/NIST/SOC 2/HIPAA where applicable) require organizational review; tools do not certify compliance.

## 5. Production SRE/DBRE safeguards

| Service | Guardrails | Recovery proof |
|---|---|---|
| PostgreSQL/RDS/Aurora | no unreviewed delete/replacement, encrypted disks, PITR, scoped DB roles | point-in-time restore, connection/replica health |
| MongoDB | no root automation, TLS, quorum and backup policy | replica-set recovery and restore |
| Redis | scoped ACL, TLS, persistence and failover controls | reconnect, failover and data integrity |
| Kafka/MSK | TLS/IAM/SASL, topic/group ACL and ISR limits | broker/consumer recovery and lag |
| OpenSearch/Elasticsearch | index permissions, snapshots, storage/IOPS budget | snapshot restore, shard health |
| Snowflake | restricted roles, key rotation and network controls | pipeline/query and access audit |
| EKS/AKS/GKE | admission, RBAC, CNI policy, PDB and CSI backup | restore, rollback and SLO |

Production gate must verify backup **restorability**, not backup existence alone. If KMS keys or identity permissions are missing, an encrypted backup can be unusable. Distinguish RPO (acceptable data loss) from RTO (acceptable restoration time), and record measured drill results.

## 6. Executable capstone labs

### Lab 1 — Fail-closed integrated security gate

~~~bash
cd infrastructure-as-code/labs/chapter-085
python3 readiness_gate.py fixtures/safe.json policy.json
python3 readiness_gate.py fixtures/unsafe.json policy.json  # expected rejection
bash run-preflight.sh
~~~

The offline gate checks 40 independent declared controls, exact targets, immutable digest, ticket, zero critical findings, no destructive changes, zero secret exposures and bounded RPO/RTO measurements. It intentionally does not provision infrastructure or authenticate to any cloud.

### Lab 2 — STRIDE risk register

`threat_model.py` rejects missing owners, invalid STRIDE categories, unmitigated high-risk threats and malformed risk scores. Add malicious-runner, state exposure and database destruction scenarios and assert fail-closed behavior.

### Lab 3 — Release promotion state machine

`promotion.py` enforces source -> scan -> attest -> policy -> approve -> backup -> restore -> canary -> SLO -> promote -> audit. Out-of-order or failed gates permanently halt that simulated promotion.

### Lab 4 — DR acceptance

`dr_gate.py` validates declared backup isolation, successful restore, KMS recovery and measured RPO/RTO. Negative cases simulate missing decryption rights and exceeded objectives. This is **not** a real database restore.

### Lab 5 — Production staging validation plan

On a separately approved staging environment, run real OIDC trust negative tests, IAM Access Analyzer/Azure/GCP permission checks, native OPA/Sentinel policy tests, secret scans, signed artifact verification, Kubernetes SubjectAccessReview and admission tests, actual PostgreSQL/MongoDB restore and a canary. Collect immutable CI logs and independent sign-off. **Do not execute against production from this tutorial.**

## 7. Production incident simulation catalog

| # | Incident | First action |
|---|---|---|
| 1 | Compromised CI runner assumes prod role | Isolate identity or artifact, preserve logs, revoke/rotate |
| 2 | OIDC subject wildcard permits fork | Isolate identity or artifact, preserve logs, revoke/rotate |
| 3 | AWS PassRole escalation | Halt promotion; verify policy, scope, approval and audit |
| 4 | Azure subscription Owner overgrant | Halt promotion; verify policy, scope, approval and audit |
| 5 | GCP workload federation principal spoofing | Halt promotion; verify policy, scope, approval and audit |
| 6 | Kubernetes cluster-admin bound to workload | Halt promotion; verify policy, scope, approval and audit |
| 7 | Argo CD controller exceeds AppProject scope | Halt promotion; verify policy, scope, approval and audit |
| 8 | Flux controller crosses namespace | Halt promotion; verify policy, scope, approval and audit |
| 9 | Terraform state publicly accessible | Isolate identity or artifact, preserve logs, revoke/rotate |
| 10 | OpenTofu lock bypass causes concurrent apply | Halt promotion; verify policy, scope, approval and audit |
| 11 | Pulumi secret provider key unavailable | Isolate identity or artifact, preserve logs, revoke/rotate |
| 12 | CloudFormation execution role privilege escalation | Halt promotion; verify policy, scope, approval and audit |
| 13 | Bicep deployment identity cross-subscription | Halt promotion; verify policy, scope, approval and audit |
| 14 | Ansible Vault credential leaked | Isolate identity or artifact, preserve logs, revoke/rotate |
| 15 | Provider dependency checksum mismatch | Halt promotion; verify policy, scope, approval and audit |
| 16 | SBOM missing transitive library | Halt promotion; verify policy, scope, approval and audit |
| 17 | Artifact provenance signed by untrusted builder | Halt promotion; verify policy, scope, approval and audit |
| 18 | Scanner CVE database stale | Halt promotion; verify policy, scope, approval and audit |
| 19 | OPA policy bundle unexpectedly allows all | Halt promotion; verify policy, scope, approval and audit |
| 20 | Sentinel advisory misread as blocking | Halt promotion; verify policy, scope, approval and audit |
| 21 | Kyverno admission fail-open | Halt promotion; verify policy, scope, approval and audit |
| 22 | Gatekeeper webhook outage | Halt promotion; verify policy, scope, approval and audit |
| 23 | Cloud SCP missing in prod | Halt promotion; verify policy, scope, approval and audit |
| 24 | Azure Policy exemption never expires | Halt promotion; verify policy, scope, approval and audit |
| 25 | GCP org policy drift | Halt promotion; verify policy, scope, approval and audit |
| 26 | Emergency exception self-approved | Halt promotion; verify policy, scope, approval and audit |
| 27 | Policy exception scope wildcard | Halt promotion; verify policy, scope, approval and audit |
| 28 | Production approval bound to wrong commit | Halt promotion; verify policy, scope, approval and audit |
| 29 | Immutable digest changes between plan and apply | Halt promotion; verify policy, scope, approval and audit |
| 30 | Database replacement proposed without restore | Freeze destructive action; DBRE validates restore and SLO |
| 31 | RDS PITR retention shortened | Freeze destructive action; DBRE validates restore and SLO |
| 32 | Aurora KMS key revoked | Isolate identity or artifact, preserve logs, revoke/rotate |
| 33 | PostgreSQL replication lag spikes during rollout | Freeze destructive action; DBRE validates restore and SLO |
| 34 | MongoDB quorum lost during upgrade | Freeze destructive action; DBRE validates restore and SLO |
| 35 | Redis ACL rotation causes outage | Freeze destructive action; DBRE validates restore and SLO |
| 36 | Kafka MSK ISR drops | Freeze destructive action; DBRE validates restore and SLO |
| 37 | OpenSearch snapshot permission denied | Freeze destructive action; DBRE validates restore and SLO |
| 38 | Snowflake automation uses ACCOUNTADMIN | Halt promotion; verify policy, scope, approval and audit |
| 39 | Kubernetes default deny blocks DNS | Halt promotion; verify policy, scope, approval and audit |
| 40 | Pod Security admission blocks rollback | Halt promotion; verify policy, scope, approval and audit |
| 41 | GitOps reconciliation reverts emergency fix | Halt promotion; verify policy, scope, approval and audit |
| 42 | Secret leaked through Terraform plan logs | Isolate identity or artifact, preserve logs, revoke/rotate |
| 43 | Kubernetes Secret committed to Git | Isolate identity or artifact, preserve logs, revoke/rotate |
| 44 | Cross-account state read detected | Isolate identity or artifact, preserve logs, revoke/rotate |
| 45 | SRE break-glass session not recorded | Halt promotion; verify policy, scope, approval and audit |
| 46 | RPO objective exceeded in drill | Freeze destructive action; DBRE validates restore and SLO |
| 47 | RTO objective exceeded in drill | Freeze destructive action; DBRE validates restore and SLO |
| 48 | Canary SLO burns error budget | Halt promotion; verify policy, scope, approval and audit |
| 49 | Production deploy bypasses change ticket | Halt promotion; verify policy, scope, approval and audit |
| 50 | Backup exists but cannot decrypt | Halt promotion; verify policy, scope, approval and audit |
| 51 | Approval signer identity expired | Halt promotion; verify policy, scope, approval and audit |
| 52 | Release evidence overwritten | Halt promotion; verify policy, scope, approval and audit |
| 53 | Policy engine unavailable during emergency | Halt promotion; verify policy, scope, approval and audit |
| 54 | DBRE owner missing on critical change | Halt promotion; verify policy, scope, approval and audit |
| 55 | Disaster recovery region inaccessible | Halt promotion; verify policy, scope, approval and audit |
| 56 | IAM rollback locks out responders | Halt promotion; verify policy, scope, approval and audit |
| 57 | GitHub action mutable tag hijacked | Halt promotion; verify policy, scope, approval and audit |
| 58 | Service account token exfiltrated | Isolate identity or artifact, preserve logs, revoke/rotate |
| 59 | Kubernetes webhook cert expired | Halt promotion; verify policy, scope, approval and audit |
| 60 | CloudTrail/Azure/GCP audit logging disabled | Halt promotion; verify policy, scope, approval and audit |

## 8. Production runbooks

**R1 — Security incident command and change freeze:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

**R2 — CI runner and OIDC credential compromise:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

**R3 — IAM trust and cloud organization policy rollback:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

**R4 — OPA/Sentinel policy outage and signed bundle restore:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

**R5 — Secret exposure and staged rotation:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

**R6 — Supply-chain tampering and trusted rebuild:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

**R7 — Kubernetes RBAC/admission isolation:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

**R8 — GitOps controller drift and emergency reconciliation:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

**R9 — Terraform/OpenTofu/Pulumi state recovery:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

**R10 — RDS/PostgreSQL/Aurora PITR and KMS restore:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

**R11 — MongoDB/Redis/Kafka/OpenSearch recovery:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

**R12 — Break-glass, SLO validation and final audit:** Establish incident command, owner and change freeze; preserve immutable evidence; identify affected target, identity and blast radius; execute independently approved containment; validate cloud policy, GitOps and database recovery; measure SLO/RPO/RTO; close with signed security/SRE/DBRE acceptance and preventive follow-up.

## 9. Troubleshooting and rollback

| Failure | Diagnostic | Safe response |
|---|---|---|
| OIDC AssumeRole denied | issuer/audience/subject and role trust | fix exact condition, not wildcard |
| OPA/Sentinel inconsistent | bundle version, enforcement level, input schema | halt, replay negative tests |
| Scanner unavailable | rules DB, runner and network | fail closed; recover scanning |
| Artifact signature invalid | signer identity and digest | quarantine and trusted rebuild |
| K8s admission blocks rollback | webhook health, policy, API audit | incident-approved scoped rollback |
| GitOps keeps reverting fix | resource owner and sync policy | coordinate one writer |
| State lock conflict | backend, leases, concurrent runs | preserve state; investigate, do not force-unlock casually |
| DB restore fails | KMS, backup metadata, IAM, storage | invoke DR, verify alternate restore |
| Canary burns error budget | SLO signals, dependencies, saturation | halt and roll back safely |
| Break-glass role expires mid-recovery | TTL, emergency session audit | renew via independent approval |

## 10. Final 100-point enterprise assessment

| Acceptance domain | Points |
|---|---:|
| Architecture, threat model and zero-trust boundaries | 15 |
| Cloud IAM, Kubernetes RBAC and GitOps security | 20 |
| OPA/Sentinel, scanning and supply-chain provenance | 20 |
| Offline labs, negative tests and evidence quality | 15 |
| Stateful DBRE restore, RPO/RTO and incident drills | 20 |
| Audit, exceptions, approvals and operational handover | 10 |
| **Total** | **100** |

**Pass >=85** and **zero critical failures**. Critical: wildcard production identity, unsigned artifact, policy bypass, exposed production secret, destructive DB change without tested restore, exceeded RPO/RTO, or failed canary SLO. Require actual native security evidence and signed security/SRE/DBRE approval. **Published training content is not a production-readiness certification.**

## 11. Part 17 closure and next chapter

Part 17 chapters 081–085 are **published**, but operational and production acceptance remain pending until native controls and restore drills are executed and reviewed. Continue to **Part 18 — Testing and Compliance**, starting **Chapter 086 — IaC Testing Strategy, Static Validation, Unit Tests and Policy Test Automation**.
