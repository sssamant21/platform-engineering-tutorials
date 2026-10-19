# Chapter 103 — Python Secrets Management, Encryption and Key Lifecycle Automation

**Part 11 — Production Security and Performance | Chapter 103/120 | Python 3.11+**

[Complete hands-on lab](labs/103-secrets-encryption-key-lifecycle-sre-dbre-lab.md) · [Executable offline project](labs/103/README.md)

## Learning outcomes

Design secrets management, encryption at rest/in transit, envelope encryption, KMS/key vault integrations, rotation, workload identity, incident response and safe DBRE credential lifecycles across AWS, Azure, GCP and Kubernetes. Build a **metadata-only, no-crypto/no-write simulator** for policy validation, version-bound advisory plans and simulated approval gates.

## Architecture

```text
AWS Secrets Manager / KMS ───┐
Azure Key Vault / Managed HSM ├──> metadata-only scoped inventory
GCP Secret Manager / Cloud KMS ┤             |
Kubernetes Secrets / KMS plugin ─┘            v
                            identity + version + rotation + audit
                                            |
                                policy-as-code findings
                                            |
                            version-bound advisory rotation plan
                                            |
                           independent approval + consumer readiness
                                            |
                              dry-run report / zero mutations
```

## 1. Cryptography fundamentals

**Encryption vs hashing vs signing:** encryption provides confidentiality; cryptographic hashes support integrity fingerprints but do not prove provenance; MACs and digital signatures authenticate integrity under appropriate key management. Never invent a cipher or construct your own crypto protocol. Use maintained, reviewed libraries and platform cryptographic services.

**Symmetric encryption:** AES-GCM is an authenticated-encryption construction. Use a fresh, unique nonce per encryption under the same key; protect associated data and verify authentication tags. Nonce reuse can catastrophically compromise security. Do not use ECB or unauthenticated CBC for new designs. Prefer KMS envelope-encryption APIs or reviewed libraries.

**Asymmetric cryptography:** public/private key pairs support signatures and key exchange. Avoid assuming that encryption and signing keys are interchangeable. Enforce algorithm policies, secure random generation, rotation and separation of duties.

**Hashing:** SHA-256 is suitable for deterministic plan identifiers, not password storage. Passwords require purpose-built, salted, memory-hard password hashing such as Argon2id with an appropriate work factor and rate limiting. Never use plain SHA-256 for passwords.

## 2. Encryption at rest and in transit

At rest: database/storage encryption, key access policies, backups, snapshots and log/telemetry handling all matter. KMS-backed storage encryption does not automatically encrypt every application-level secret or prevent authorized plaintext reads.

In transit: TLS 1.2+ with strong configurations (prefer TLS 1.3), hostname and certificate validation, mTLS where appropriate and controlled trust roots. Do not disable certificate verification to fix an outage. TLS does not replace application authorization.

## 3. Envelope encryption

```text
KMS-managed key-encryption key (KEK)
         |
         +-- Generate / wrap data-encryption key (DEK)
                       |
                 AES-GCM encrypt data
                       |
           store ciphertext + wrapped DEK + metadata
```

Decrypt only within an authorized service boundary; use KMS to unwrap the DEK, then authenticated-decrypt the data. Avoid plaintext DEK logging, caching beyond necessity or storing it alongside ciphertext without wrapping. Distinguish **KEK rotation**, **DEK rewrapping**, and **data re-encryption**; changing the KEK version does not necessarily re-encrypt existing data. Design key revocation carefully to avoid irreversible data loss.

## 4. AWS KMS and Secrets Manager

Use IAM roles/STS and least-privilege resource/key policies. AWS KMS supports key policies, grants, encryption context, rotation configurations and CloudTrail audit. Secrets Manager supports version staging and managed rotation patterns, including Lambda workflows. Distinguish `DescribeSecret` metadata from `GetSecretValue` payload retrieval. Encryption context is authenticated associated metadata, not a secret.

Validate region/account, cross-account grants, key state, deletion waiting periods and downstream consumers before rotating or disabling keys. The executable lab does not call boto3.

## 5. Azure Key Vault and Managed HSM

Use Microsoft Entra ID managed identities and scoped RBAC. Key Vault stores secrets, keys and certificates; Managed HSM provides distinct isolation/governance options. Plan key/secret versioning, expiry, Event Grid-based lifecycle notifications and diagnostic logs. Azure data-plane permissions differ from management-plane roles. Never log values returned by `get_secret`; the lab never calls it.

## 6. GCP Cloud KMS and Secret Manager

Use Workload Identity Federation or GKE Workload Identity and least-privilege IAM. Cloud KMS manages CryptoKeys/CryptoKeyVersions with primary versions and lifecycle states; Secret Manager manages secret versions and replication. Distinguish KMS cryptographic operations from Secret Manager payload access. Cloud Audit Logs, key rotation schedules, destroy/disable states and regional availability are essential.

## 7. Kubernetes Secrets and encryption

Kubernetes Secret `data` is base64-encoded, **not inherently encrypted**. Enable encryption at rest for API-server-managed resources, control etcd and backup access, restrict RBAC and avoid unnecessarily mounting tokens/secrets. External Secrets Operator, Secrets Store CSI Driver and workload identity can reduce static secret distribution, but each adds reconciliation, refresh and failure-mode considerations. Secret volume updates and environment-variable updates have different refresh behavior; application reload may be required.

## 8. Credential and key lifecycle

Inventory → assign owner → define expiry/rotation → stage new version → validate consumers → promote new version → observe errors/latency → retire old version after overlap → audit. For PostgreSQL, test connection pools, replication/HA, backup agents and emergency accounts; for MongoDB, Elasticsearch, Kafka and Redis validate application auth and connection refresh.

Rotation must be **idempotent, version-aware and rollback-capable**. Avoid disabling a KMS key before confirming all historical ciphertext/backup dependencies. For compromised keys, containment and emergency re-encryption may be necessary; normal periodic rotation is not sufficient.

## 9. Policy-as-code and governance

Example controls: production owner required; TLS and at-rest encryption enabled; workload identities preferred; audit enabled; secret age known and within policy; key/version state and resource scope verified. A missing inventory segment must produce **unknown**, not compliant. Map evidence to actual CIS/NIST/SOC 2 requirements rather than claiming certification from synthetic checks.

## 10. Security incidents and runbooks

| Scenario | Safe response |
|---|---|
| KMS access denied | Verify identity, key policy, grants and scope |
| Azure Key Vault 403 | Check Entra principal, RBAC, firewall/private endpoint |
| GCP KMS key disabled | Stop and inspect version/decrypt dependencies |
| Kubernetes secret in logs | Contain, redact, rotate and audit |
| PostgreSQL password rotation outage | Validate consumers and restore tested rollback |
| TLS certificate expired | Restore valid certificate chain; never bypass verification |
| Old encrypted backup unreadable | Verify historical KEK/DEK lifecycle |
| KMS throttling | Bound retries, backoff and circuit breaker |
| Unowned secret | Escalate and assign owner |
| Partial inventory | Mark unknown and preserve evidence |

**Runbook — key disable/compromise:** contain, preserve audit, map ciphertext and backup dependencies, validate recovery, rotate/re-encrypt if required, monitor and document.

**Runbook — credential rotation failure:** stop revocation, verify version state, refresh connection pools, validate database HA and rollback safely.

**Runbook — TLS failure:** check expiry, chain, SAN/hostname, trust store, cipher policy and clock; no insecure fallback.

**Runbook — Kubernetes secret exposure:** assess RBAC/etcd/backups, revoke exposed credentials, enable encryption and audit.

**Runbook — compliance:** validate collection completeness, policy version, exceptions, ownership and evidence.

## 11. Hands-on lab and validation

The [full lab](labs/103-secrets-encryption-key-lifecycle-sre-dbre-lab.md) and [offline project](labs/103/README.md) provide synthetic AWS/Azure/GCP/Kubernetes metadata, rotation checks, policy findings, bounded pagination, version-bound SHA-256 advisory plans, simulated independent approval, consumer readiness, incident exercises, runbooks and a 100-point assessment.

**Critical distinction:** This lab **does not implement cryptographic encryption/decryption, live KMS/Secrets Manager calls, secret payload access or real key rotation**. Its purpose is to safely practice lifecycle governance and incident decisions. Runtime test execution, CI, live integration and security acceptance remain pending.

**Next proposed:** Chapter 104 — Python Security Auditing, Compliance Automation and Policy-as-Code.
