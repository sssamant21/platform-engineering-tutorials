# Chapter 081 — Infrastructure as Code Security Foundations, Threat Modeling, Identity and Secrets Management

**Part 17 — Security and Policy · Chapter 081/120 · SRE/DevOps/DBRE**

## Outcomes and prerequisites

Build a production-focused threat model for Terraform/OpenTofu, Pulumi, CloudFormation, Bicep, Ansible, Kubernetes and GitOps. Design identity federation, state protection, secret lifecycle, software supply-chain controls, risk scoring, incident response and DBRE recovery safeguards. Prerequisites: Chapters 001–080; Python 3.10+ and Bash for the offline lab. **The companion lab makes no cloud, Kubernetes or database changes.**

## 1. Security architecture and trust boundaries

~~~text
Developers / signed PR / CODEOWNERS
               |
     untrusted source boundary
               |
 CI lint / unit tests / IaC scanners / SBOM
               |
    signed immutable build artifacts
               |
     protected deployment boundary
               |
    OIDC workload identity + RBAC
               |
       preview / policy evaluation
               |
      independent change approval
               |
 secrets broker / KMS / encrypted state
               |
       bounded production apply
               |
  cloud audit / detection / SLO / DBRE DR
~~~

Treat the CI runner, source repository, package registry, state backend, secret manager, identity provider, cloud control plane, Kubernetes API and database as **distinct security domains**. No PR-controlled script should receive a production credential. Do not trust an unverified preview or self-reported compliance JSON as a cryptographic attestation.

## 2. Threat modeling: STRIDE and attack trees

| STRIDE | IaC example | Defensive control |
|---|---|---|
| Spoofing | forged OIDC workload subject | exact audience/subject and protected environment |
| Tampering | modified plan/provider binary | immutable digest, verified provenance |
| Repudiation | unaudited emergency apply | signed approval and immutable logs |
| Information disclosure | secrets in state/plan/CI logs | encryption, least privilege, redaction, retention |
| Denial of service | unauthorized delete or lock abuse | change gates, backups, rate limits |
| Elevation of privilege | IAM PassRole or cluster-admin | permission boundaries, RBAC, separation of duties |

**Threat-model exercise:** enumerate sensitive assets (production credentials, state, database backups, encryption keys), attackers (malicious PR author, compromised runner, stolen workload identity), entry points, trust boundaries and security objectives. Score threats with likelihood and impact (1–5 each), assign owner and mitigation, then retest after architectural changes. A numerical risk score is prioritization, not proof of safety.

### Attack tree: production database deletion

~~~text
Goal: unauthorized DB deletion
├── obtain privileged identity
│   ├── steal static CI key
│   ├── abuse wildcard OIDC trust
│   └── compromise privileged runner
├── bypass change controls
│   ├── tamper plan artifact
│   ├── skip independent approval
│   └── exploit overbroad policy exception
└── prevent recovery
    ├── delete/disable backups
    ├── compromise KMS key
    └── suppress monitoring/audit
~~~

Defense-in-depth must independently prevent deletion and protect recoverability. Use cloud-side deny guardrails and deletion protection where appropriate; a CI-only check can be bypassed by a direct cloud API call.

## 3. Workload identity and authorization

Prefer short-lived federated credentials to stored access keys. For **AWS**, scope GitHub/GitLab OIDC role trust to exact issuer, audience and subject, then use narrowly scoped IAM permissions, permission boundaries and SCPs. For **Azure**, scope Entra workload identity federation to tenant, app/service principal and exact subject; use Azure RBAC and policy. For **GCP**, use Workload Identity Federation with constrained principal attributes and IAM bindings. Bind deploy identity to repository, protected branch/environment, runner and target account. Review token lifetime, revocation, session logging and emergency access.

For **Kubernetes**, use dedicated ServiceAccounts, namespace-scoped Roles/RoleBindings, admission and workload identity; avoid cluster-admin. For **Ansible**, scope SSH/sudo `become`, inventory access and Vault keys. For **GitOps**, limit Argo CD AppProjects and Flux controller permissions to assigned namespaces/resources.

## 4. Secrets and state security

**Terraform/OpenTofu:** `sensitive = true` redacts some CLI display but does **not** make state or plan files secret-free. Restrict backend access, enable encryption, versioning, audit and key recovery; avoid placing secrets in outputs. **Pulumi:** configure an approved secrets provider and backend, restrict stack exports, protect provider keys and test recovery. **CloudFormation:** use Secrets Manager/SSM dynamic references carefully; stack events and downstream applications may still expose values. **Bicep:** use secure parameters and Key Vault references; inspect deployment histories and logs. **Ansible:** Vault encrypts content at rest but tasks can still leak decrypted values; use `no_log` and privilege controls. **Kubernetes:** base64 is encoding, not encryption; use etcd encryption at rest, RBAC, external secret operators and rotation. **GitOps:** use approved encryption/external-secret patterns and tightly scoped decryption identities.

### Secret lifecycle

Create using managed randomness → store in dedicated secret manager → grant least-privilege read → deliver through short-lived identity → rotate with overlap/verification → revoke old credentials → audit access → test disaster recovery. Never write real secrets into lab fixtures, source control or CI logs. Do not assume secret masking removes values from every artifact.

## 5. Supply-chain security and policy enforcement

Pin CLI versions, provider/plugin versions, modules, Ansible collections, Helm charts, CI actions and container images to immutable, verified sources. Use lockfiles, SBOMs, vulnerability scanning, provenance verification and controlled registries. Run static IaC scanning and policy-as-code at PR and deploy boundaries. Independently enforce destructive-action protections through cloud IAM/SCP/Policy/organization policies. Require time-bound, reviewed exceptions with audit and expiry.

## 6. Production SRE/DBRE threat considerations

| Service | High-value asset | Key protection |
|---|---|---|
| PostgreSQL/RDS/Aurora | credentials, PITR and backups | IAM/DB roles, backup isolation, restore test |
| MongoDB | admin user, keyfile, replica-set data | role separation, TLS, quorum, oplog/backup |
| Redis | AUTH/ACL credentials, persistence | TLS/ACL, rotation, recovery |
| Kafka/MSK | broker credentials, topic ACLs | IAM/SASL, encrypted traffic, ISR monitoring |
| Elasticsearch/OpenSearch | API keys, index snapshots | scoped roles, snapshots, audit, storage safeguards |
| Snowflake | service users/keys, stages | key-pair/OAuth, role least privilege, audit |
| EKS/AKS/GKE | cluster admin, etcd, CSI secrets | workload identity, RBAC, KMS and admission |

A security fix can itself cause availability impact: credential rotation may break connection pools; KMS changes can prevent restore; overly broad policy enforcement may block recovery. Always test both security and operational readiness.

## 7. Executable labs

### Lab A — Offline threat model and identity policy gate

~~~bash
cd infrastructure-as-code/labs/chapter-081
python3 security_gate.py fixtures/safe.json policy.json
python3 security_gate.py fixtures/unsafe.json policy.json  # must fail
python3 -m unittest -v test_security_gate.py test_threat_model.py test_rotation.py
bash run-preflight.sh
~~~

The gate validates **declared evidence** for exact target, short-lived identity, OIDC claims, secret and state controls, approval and DBRE restore safeguards. It does not verify actual AWS IAM, Azure RBAC, GCP federation, KMS or signed attestations.

### Lab B — STRIDE risk register

Use `threat_model.py` to score threats by likelihood × impact. Inject high-risk threats without owner/mitigation and require rejection. Document an attack tree and map controls to trust boundaries.

### Lab C — Secret rotation simulator

Use `rotation.py` to enforce `prepare -> distribute -> verify -> revoke -> audit`. Reject early revocation, skipped verification, failed service health and replay after halt. This does not rotate any real credential.

### Lab D — Security incident game day

Simulate a compromised GitHub runner that can read Terraform state and a PostgreSQL connection secret. Quarantine runner, revoke OIDC sessions where possible, rotate credentials with overlap, inspect state access logs, verify PITR and test service SLO. Rebuild from pinned dependencies and record audit evidence.

### Lab E — Production integration design (not executed)

Design a protected pipeline using exact-subject OIDC federation, backend KMS, secret-manager references, provider pinning, policy-as-code and independent DBRE approval. Do not enable real apply until security, SRE and DBRE reviewers approve target, blast radius and recovery.

## 8. Production incident scenarios

| # | Scenario | Initial containment |
|---|---|---|
| 1 | CI runner credential exfiltration | Quarantine exposure, revoke access, preserve evidence |
| 2 | OIDC audience mismatch | Freeze change, validate identity, scope and recovery readiness |
| 3 | OIDC subject wildcard trust | Freeze change, validate identity, scope and recovery readiness |
| 4 | GitHub Actions pull_request_target abuse | Isolate supply chain, pin trusted digest and investigate |
| 5 | GitLab unprotected variable leak | Freeze change, validate identity, scope and recovery readiness |
| 6 | Jenkins shared-library injection | Freeze change, validate identity, scope and recovery readiness |
| 7 | Terraform state exposes database password | Quarantine exposure, revoke access, preserve evidence |
| 8 | OpenTofu plan artifact exposes secrets | Quarantine exposure, revoke access, preserve evidence |
| 9 | Pulumi secret provider key loss | Quarantine exposure, revoke access, preserve evidence |
| 10 | CloudFormation dynamic reference misuse | Freeze change, validate identity, scope and recovery readiness |
| 11 | Bicep secure parameter logged | Freeze change, validate identity, scope and recovery readiness |
| 12 | Ansible Vault password in shell history | Quarantine exposure, revoke access, preserve evidence |
| 13 | Kubernetes Secret committed to Git | Quarantine exposure, revoke access, preserve evidence |
| 14 | External Secrets operator overprivileged | Quarantine exposure, revoke access, preserve evidence |
| 15 | Argo CD repo credential compromise | Quarantine exposure, revoke access, preserve evidence |
| 16 | Flux deploy key leaked | Quarantine exposure, revoke access, preserve evidence |
| 17 | IAM privilege escalation via PassRole | Freeze change, validate identity, scope and recovery readiness |
| 18 | Azure federated credential wildcard | Quarantine exposure, revoke access, preserve evidence |
| 19 | GCP Workload Identity principal mismatch | Freeze change, validate identity, scope and recovery readiness |
| 20 | Long-lived access key in repository | Quarantine exposure, revoke access, preserve evidence |
| 21 | Provider binary substitution | Isolate supply chain, pin trusted digest and investigate |
| 22 | Unsigned module release | Isolate supply chain, pin trusted digest and investigate |
| 23 | Dependency confusion | Freeze change, validate identity, scope and recovery readiness |
| 24 | Typosquatted Ansible collection | Isolate supply chain, pin trusted digest and investigate |
| 25 | Unpinned GitHub Action | Isolate supply chain, pin trusted digest and investigate |
| 26 | Malicious container base image | Isolate supply chain, pin trusted digest and investigate |
| 27 | S3 backend public access | Freeze change, validate identity, scope and recovery readiness |
| 28 | Azure Blob state container public access | Quarantine exposure, revoke access, preserve evidence |
| 29 | GCS state object unauthorized read | Quarantine exposure, revoke access, preserve evidence |
| 30 | State encryption key disabled | Quarantine exposure, revoke access, preserve evidence |
| 31 | Backend state version deleted | Quarantine exposure, revoke access, preserve evidence |
| 32 | Break-glass role abused | Freeze change, validate identity, scope and recovery readiness |
| 33 | Secret rotation causes outage | Quarantine exposure, revoke access, preserve evidence |
| 34 | KMS key grant overly broad | Quarantine exposure, revoke access, preserve evidence |
| 35 | Kubernetes service account token over-scoped | Quarantine exposure, revoke access, preserve evidence |
| 36 | Cluster-admin kubeconfig in CI | Freeze change, validate identity, scope and recovery readiness |
| 37 | Sensitive output printed in CI | Quarantine exposure, revoke access, preserve evidence |
| 38 | Plan JSON uploaded publicly | Quarantine exposure, revoke access, preserve evidence |
| 39 | Supply-chain provenance missing | Isolate supply chain, pin trusted digest and investigate |
| 40 | CloudFormation stack policy disabled | Freeze change, validate identity, scope and recovery readiness |
| 41 | AWS SCP bypass attempt | Freeze change, validate identity, scope and recovery readiness |
| 42 | Azure Policy exemption misuse | Freeze change, validate identity, scope and recovery readiness |
| 43 | GCP org-policy exception | Freeze change, validate identity, scope and recovery readiness |
| 44 | Production DB deletion without DBRE approval | Freeze change, validate identity, scope and recovery readiness |
| 45 | Incident evidence tampered | Freeze change, validate identity, scope and recovery readiness |

## 9. Operational runbooks

**R1 — Threat-model intake:** Enumerate assets, actors, trust boundaries, STRIDE threats, blast radius and controls.

**R2 — CI credential exposure:** Revoke leaked tokens, rotate impacted secrets, isolate runner and preserve forensic logs.

**R3 — OIDC federation:** Inspect issuer, audience, subject, environment binding, expiration and least-privilege role.

**R4 — State exposure:** Quarantine backend, revoke access, identify exposed outputs and rotate all compromised secrets.

**R5 — Secrets rotation:** Stage dual-credential rotation, verify workloads, revoke old credential and monitor failures.

**R6 — Supply-chain compromise:** Pin known-good digest, quarantine artifact, verify provenance and rebuild from trusted source.

**R7 — Pulumi/CloudFormation/Bicep:** Inspect secret providers, dynamic references, secure parameters and access to deployment history.

**R8 — Ansible/Kubernetes/GitOps:** Audit Vault, ServiceAccount RBAC, External Secrets, Git repository keys and controller access.

**R9 — DBRE recovery:** Validate PITR, backups, encryption keys, replica quorum, restore rehearsal and RPO/RTO.

**R10 — Policy exception:** Require time-bound approval, compensating control, ticket, audit and expiry.

**R11 — Detection and escalation:** Correlate IAM audit events, runner logs, state access and SLO impact; page incident commander.

**R12 — Post-incident review:** Document timeline, affected identities/data, rotation, recovery, preventive controls and owner.

## 10. Troubleshooting

| Symptom | Investigate | Safe response |
|---|---|---|
| OIDC denied | issuer, audience, subject, branch protection | correct trust narrowly; do not wildcard |
| CI secrets exposed | logs, artifact retention, runner permissions | revoke and rotate, audit downstream |
| State access unexpectedly broad | backend ACL, encryption, logs | restrict, preserve evidence, rotate exposed secrets |
| Pulumi decryption fails | provider key, stack metadata | recover approved key; do not discard state |
| Ansible Vault task leaks | `no_log`, callbacks, debug | redact and rotate; test task |
| GitOps controller privilege drift | AppProject, RBAC, Flux service account | scope ownership and privileges |
| Credential rotation breaks DB app | connection pool, overlap, retries | restore service safely; complete rotation |
| KMS outage blocks restore | key policy, grants, region | invoke tested key-recovery runbook |

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Threat model, STRIDE, trust boundaries and risk register | 20 |
| Workload identity, OIDC and authorization | 20 |
| Secrets, state and encryption-key lifecycle | 20 |
| Executable offline tests and negative scenarios | 15 |
| SRE/DBRE incident response and recovery | 15 |
| Supply chain, audit and policy governance | 10 |
| **Total** | **100** |

Pass >=85 and zero critical findings. Critical: wildcard production identity trust, leaked secret, unencrypted exposed state, unapproved privileged change, untested database restore or broken audit trail. **Curriculum publication is not security certification or production acceptance.**

**Next proposed:** Chapter 082 — IaC Policy as Code, OPA/Rego, Sentinel and Enterprise Guardrails.
