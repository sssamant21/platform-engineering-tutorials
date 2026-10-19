# Chapter 083 — IaC Security Scanning, Supply-Chain Integrity, Secrets Detection and Continuous Compliance

**Part 17 — Security and Policy · Chapter 083/120 · SRE/DevOps/DBRE**

## Learning objectives

Design and operate a production-grade, defense-in-depth security scanning pipeline for Terraform/OpenTofu, Pulumi, CloudFormation, Bicep, Ansible, Helm, Kubernetes, Argo CD and Flux. Detect exposed secrets, insecure configuration, vulnerable dependencies, unsigned artifacts and drift; validate software supply-chain provenance; prioritize remediation; implement exception lifecycle and continuous compliance. The lab is **offline and non-provisioning**: it does not run native scanners or prove real signatures.

## 1. Reference architecture and trust boundaries

~~~text
Signed source / protected branch / CODEOWNERS
                  |
Pre-commit: gitleaks/trufflehog + format/lint
                  |
CI: IaC static analysis / SAST / SBOM / vuln scan
                  |
Lockfiles + dependency provenance + digest pinning
                  |
Build: signed artifact + attestations + SBOM
                  |
Preview: target-bound plan, policy-as-code
                  |
Protected OIDC / independent approvals / DBRE
                  |
Cloud-side IAM/org policy + K8s admission
                  |
CD: canary, SLO, GitOps reconciliation
                  |
Runtime: CSPM/Config/Defender/SCC + drift
                  |
Immutable evidence / exception expiry / audit
~~~

Separate untrusted pull-request code from privileged deployment workers, scanner rule bundles from candidate changes, artifact registries from execution targets, and state/secrets from CI logs. An attacker who controls a PR must not be able to modify the scanner's policy or access production secrets.

## 2. Scanner categories and complementary coverage

| Category | Representative tools | Detects | Limitation |
|---|---|---|---|
| Secret scanning | Gitleaks, TruffleHog, GitHub secret scanning | tokens, keys, credentials in code/history | cannot prove token validity; false positives |
| IaC misconfiguration | Checkov, Trivy config, Terrascan, tfsec (legacy) | insecure cloud/K8s resources | static analysis lacks runtime context |
| Dependency and SBOM | Syft, Trivy, Grype, osv-scanner | package inventory and known CVEs | vulnerability databases can lag |
| Provenance/signing | Sigstore Cosign, in-toto/SLSA | artifact identity and build provenance | trust root and policy must be verified |
| Container/Kubernetes | Trivy, kube-linter, admission controls | image and manifest risk | admission alone does not scan live state |
| Runtime compliance | AWS Config/Security Hub, Defender for Cloud, Security Command Center | cloud drift and violations | detection is not preventive enforcement |
| Policy as code | OPA/Rego, Sentinel, CrossGuard, Gatekeeper/Kyverno | defined governance constraints | bundle trust and enforcement mode matter |

Do not substitute one tool for all controls. Tool names and flags change; pin and verify versions in real CI, and consult official documentation when deploying.

## 3. Software supply-chain integrity

Use immutable source commits, signed releases, pinned provider/plugin/module versions, lockfile checksums, verified registries and SBOMs. Record artifact digests, builder identity, source repository/ref, workflow provenance and dependencies. Verify **attestations against trusted identities and policy**, not merely that a signature exists. A digest is an integrity identifier, not an authorization decision.

**SLSA:** distinguish provenance levels and supported build-system guarantees; a self-generated JSON file is not an independently trusted attestation. **Sigstore:** verify issuer, subject, certificate identity and transparency/logging assumptions for the chosen deployment model. **SBOM:** capture direct/transitive dependencies and licensing, monitor CVEs and rescan after disclosure. **Provider lockfiles:** protect Terraform/OpenTofu dependency resolution but do not eliminate malicious upstream releases or runtime cloud drift.

## 4. Secret scanning and incident response

Scan staged changes, full repository history where appropriate, CI logs and published artifacts. Treat findings as potentially exposed credentials until verified safely. **Never paste a live token into a validator or public issue.** Revoke/rotate first, inspect access logs, isolate affected runners and repair the exposure path. Removing a secret from the latest commit does not remove it from Git history, caches or artifacts.

Use approved suppression rules with exact finding fingerprint, owner, reason, expiration and independent approval. Broad ignores or permanent baselines hide new leaks. Ensure scanner outputs are access-controlled and do not echo the secret value.

## 5. Continuous compliance and drift

Define compliance as an ongoing process: baseline policy -> deploy gate -> cloud-side enforcement -> scheduled inventory -> drift detection -> owner ticket -> remediation -> evidence retention -> reassessment. Map controls to CIS, NIST, SOC 2, HIPAA or organization-specific standards only where applicable; **tool results do not themselves establish regulatory compliance**. Record scanner versions, rule packs, finding IDs, resource scopes, target environments, severity, remediation and closure evidence.

## 6. Production DBRE and platform risks

| Platform | Security scan focus | Operational safeguard |
|---|---|---|
| PostgreSQL/RDS/Aurora | encryption, public access, backup/PITR, secret exposure | tested restore, replica lag, DBRE approval |
| MongoDB | admin roles, keyfile, TLS, backup | quorum, oplog and recovery |
| Redis | ACLs, TLS, persistence | rotation and failover verification |
| Kafka/MSK | encryption, SCRAM/IAM, broker ACLs | ISR and lag monitoring |
| Elasticsearch/OpenSearch | API keys, snapshots, network exposure | IOPS/shard capacity and snapshot restore |
| Snowflake | service key, role privilege, network policies | query/pipeline health and audit |
| EKS/AKS/GKE | image provenance, RBAC, admission, secrets | PDB/CSI snapshot and SLO |

Prioritize changes by exploitability, reachability, blast radius, data classification and recovery readiness—not severity alone. Coordinate credential rotation and encryption-key changes with application owners and DBRE to avoid cascading outages.

## 7. Hands-on executable labs

### Lab A — Offline security-evidence gate

~~~bash
cd infrastructure-as-code/labs/chapter-083
python3 security_gate.py fixtures/safe.json policy.json
python3 security_gate.py fixtures/unsafe.json policy.json # expected failure
bash run-preflight.sh
~~~

The lab verifies **self-declared** scanner freshness, pinned artifacts, SBOM/provenance presence, secret scanning, exception governance, backup/restore and SLO controls. It does not execute Checkov, Trivy, Gitleaks, Cosign, native OPA or cloud APIs. Production requires independent machine-verifiable evidence.

### Lab B — Secret-finding triage

Use `findings.py` to evaluate **synthetic** findings with severity, owner, evidence fingerprint, remediation status and expiry. Fail closed on unresolved critical secrets and unapproved suppressions. No actual credential material is included.

### Lab C — Supply-chain attestation checks

Use `supply_chain.py` to reject malformed digest, missing provenance, untrusted builder identity and stale SBOM. This is **metadata schema validation only**, not cryptographic verification.

### Lab D — CI pipeline and continuous compliance

Review example GitLab and GitHub Actions YAML. The examples run offline tests only; they intentionally contain no privileged deployment. Add pinned native scanner binaries, isolated runners, protected approvals, attestation verification, cloud inventory and alerting before production.

### Lab E — Production incident game day

Simulate a leaked PostgreSQL credential in Terraform plan JSON, a compromised runner and a stale Trivy vulnerability database. Freeze release, revoke credentials, isolate runner, preserve audit, verify backups and SLO, rebuild signed artifacts and restore the scanner gate. Require independent SRE/security/DBRE sign-off.

## 8. Production incident simulations

| # | Scenario | First action |
|---|---|---|
| 1 | Terraform plan exposes password | Quarantine, revoke/rotate and preserve evidence |
| 2 | OpenTofu state accidentally uploaded | Quarantine, revoke/rotate and preserve evidence |
| 3 | Pulumi stack secret decrypted in CI | Quarantine, revoke/rotate and preserve evidence |
| 4 | CloudFormation template embeds access key | Quarantine, revoke/rotate and preserve evidence |
| 5 | Bicep secure parameter logged | Freeze release; validate provenance, policy, target and recovery |
| 6 | Ansible Vault password in inventory | Quarantine, revoke/rotate and preserve evidence |
| 7 | Kubernetes Secret committed unencrypted | Quarantine, revoke/rotate and preserve evidence |
| 8 | GitHub Action pinned to mutable tag | Freeze release; validate provenance, policy, target and recovery |
| 9 | GitLab runner compromised | Freeze release; validate provenance, policy, target and recovery |
| 10 | Jenkins shared library tampered | Freeze release; validate provenance, policy, target and recovery |
| 11 | Terraform provider checksum mismatch | Freeze release; validate provenance, policy, target and recovery |
| 12 | OpenTofu module source unpinned | Freeze release; validate provenance, policy, target and recovery |
| 13 | Pulumi package dependency confusion | Freeze release; validate provenance, policy, target and recovery |
| 14 | Ansible collection typosquatted | Freeze release; validate provenance, policy, target and recovery |
| 15 | Helm chart provenance invalid | Freeze release; validate provenance, policy, target and recovery |
| 16 | Container image tag drift | Freeze release; validate provenance, policy, target and recovery |
| 17 | SBOM missing transitive dependency | Freeze release; validate provenance, policy, target and recovery |
| 18 | SLSA provenance unverifiable | Freeze release; validate provenance, policy, target and recovery |
| 19 | Artifact signature expired | Freeze release; validate provenance, policy, target and recovery |
| 20 | Cosign trust root misconfigured | Freeze release; validate provenance, policy, target and recovery |
| 21 | Trivy database stale | Fail closed, refresh scanner/rules and triage |
| 22 | Checkov finding suppressed globally | Fail closed, refresh scanner/rules and triage |
| 23 | tfsec legacy config not migrated | Fail closed, refresh scanner/rules and triage |
| 24 | Terrascan rules bypassed | Freeze release; validate provenance, policy, target and recovery |
| 25 | Gitleaks baseline masks new leak | Fail closed, refresh scanner/rules and triage |
| 26 | TruffleHog finding ignored | Fail closed, refresh scanner/rules and triage |
| 27 | Secret leaked in PR history | Quarantine, revoke/rotate and preserve evidence |
| 28 | CI job log contains token | Quarantine, revoke/rotate and preserve evidence |
| 29 | Public S3 backend ACL | Freeze release; validate provenance, policy, target and recovery |
| 30 | Azure Blob state access too broad | Quarantine, revoke/rotate and preserve evidence |
| 31 | GCS state encryption disabled | Quarantine, revoke/rotate and preserve evidence |
| 32 | KMS key scheduled for deletion | Quarantine, revoke/rotate and preserve evidence |
| 33 | Unscanned CloudFormation StackSet | Freeze release; validate provenance, policy, target and recovery |
| 34 | Azure Policy drift not detected | Freeze release; validate provenance, policy, target and recovery |
| 35 | GCP org policy drift | Freeze release; validate provenance, policy, target and recovery |
| 36 | Gatekeeper audit-only enforcement | Freeze release; validate provenance, policy, target and recovery |
| 37 | Kyverno admission webhook unavailable | Freeze release; validate provenance, policy, target and recovery |
| 38 | Argo CD self-heal overwrites emergency fix | Freeze release; validate provenance, policy, target and recovery |
| 39 | Flux image automation unreviewed | Freeze release; validate provenance, policy, target and recovery |
| 40 | RDS backup retention reduced | Freeze release; validate provenance, policy, target and recovery |
| 41 | PostgreSQL superuser password exposed | Quarantine, revoke/rotate and preserve evidence |
| 42 | MongoDB keyfile committed | Quarantine, revoke/rotate and preserve evidence |
| 43 | Redis ACL password exposed | Quarantine, revoke/rotate and preserve evidence |
| 44 | Kafka SCRAM credential leaked | Quarantine, revoke/rotate and preserve evidence |
| 45 | OpenSearch API key leaked | Quarantine, revoke/rotate and preserve evidence |
| 46 | Snowflake private key in repository | Quarantine, revoke/rotate and preserve evidence |
| 47 | EKS service account privilege escalation | Freeze release; validate provenance, policy, target and recovery |
| 48 | AKS workload identity audience mismatch | Freeze release; validate provenance, policy, target and recovery |
| 49 | GKE service account key exposed | Quarantine, revoke/rotate and preserve evidence |
| 50 | Vulnerability exception expired | Fail closed, refresh scanner/rules and triage |
| 51 | Critical CVE ignored by scanner | Fail closed, refresh scanner/rules and triage |
| 52 | Scanner outage treated as pass | Fail closed, refresh scanner/rules and triage |
| 53 | Evidence retention policy violated | Freeze release; validate provenance, policy, target and recovery |
| 54 | Compliance report falsely marked complete | Freeze release; validate provenance, policy, target and recovery |
| 55 | Database restore drill missing | Freeze release; validate provenance, policy, target and recovery |

## 9. SRE/DBRE runbooks

**R1 — Secrets detected in source:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

**R2 — State or plan artifact exposure:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

**R3 — CI runner compromise:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

**R4 — Dependency and provider tampering:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

**R5 — SBOM/provenance validation failure:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

**R6 — Scanner outage and stale signatures:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

**R7 — False positive triage and suppressions:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

**R8 — Policy drift and cloud organization guardrails:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

**R9 — Kubernetes admission and GitOps integrity:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

**R10 — DBRE credential rotation and restore:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

**R11 — Critical vulnerability emergency response:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

**R12 — Audit evidence and compliance handover:** Identify scope and affected services; halt unsafe promotion; preserve immutable logs, scanner findings and artifacts; verify source and target; coordinate containment and DBRE recovery; document change ticket, owner, remediation, SLO and signed acceptance.

## 10. Troubleshooting matrix

| Symptom | Likely cause | Safe response |
|---|---|---|
| Scanner passes insecure resource | missing rules, ignored path, advisory mode | halt, inspect config and negative tests |
| Excessive false positives | weak fingerprint, missing context | narrowly triage with expiring approval |
| Secret reappears | Git history, artifacts, logs, caches | revoke, scrub allowed copies, rescan |
| Cosign verification fails | wrong issuer/subject/trust root | reject artifact, verify source |
| SBOM missing packages | incomplete dependency resolution | rebuild SBOM with pinned tool |
| CVE database stale | network/update failure | fail closed for protected releases |
| Runtime drift despite green CI | direct console change or unmanaged resource | cloud-side inventory and incident ticket |
| Rotation breaks database app | pool reuse, credential overlap | restore service and complete staged rotation |

## 11. 100-point enterprise assessment

| Domain | Points |
|---|---:|
| Security architecture and threat model | 15 |
| Secrets scanning and incident handling | 20 |
| Supply-chain provenance, SBOM and signing | 20 |
| IaC scanners, policy and continuous compliance | 20 |
| Executable labs and negative tests | 15 |
| SRE/DBRE recovery, audit and handover | 10 |
| **Total** | **100** |

Pass >=85 with zero critical findings and signed security/SRE/DBRE acceptance. Critical failures include exposed production secrets, unsigned/untrusted deployment artifact, disabled scanning, wrong cloud target, unencrypted state or untested DB restore. **Published training content is not a production compliance certification.**

**Next:** Chapter 084 — IaC Least Privilege, Zero Trust, Cloud IAM and Kubernetes Security Hardening.
