# Chapter 103 — Secrets Management, Encryption and Key Lifecycle SRE/DBRE Lab

[Python simulator](103/secrets_lab.py) · [Automated tests](103/test_secrets_lab.py) · [Project guide](103/README.md)

## Mission

Investigate a production PostgreSQL credential approaching rotation expiry, a Kubernetes Secret lacking confirmed at-rest encryption and a KMS key version that must remain available to decrypt backups. Design safe AWS/Azure/GCP/Kubernetes controls and practice **metadata-only** governance.

```text
Synthetic AWS/Azure/GCP/Kubernetes secret + key metadata
   -> identity, version, age and control validation
   -> policy-as-code and completeness checks
   -> version-bound SHA-256 advisory rotation plan
   -> independent approval, expiry, consumer and rollback checks
   -> JSON report / zero secret reads / zero crypto / zero writes
```

## Lab 1 — Execute

```bash
cd python/11-production-security-performance/labs/103
python -m compileall -q secrets_lab.py test_secrets_lab.py
python -m unittest -v test_secrets_lab.py
python secrets_lab.py --dry-run
python secrets_lab.py --partial
```

## Lab 2 — Encryption architecture

Draw an envelope-encryption workflow: KMS KEK wraps a randomly generated DEK; AES-GCM encrypts data using a unique nonce and authenticated associated data; ciphertext and wrapped DEK are stored. Explain why KEK rotation does not necessarily re-encrypt data. Map encryption at rest, TLS in transit and backup key dependencies. This lab intentionally performs **no cryptography**.

## Lab 3 — AWS, Azure, GCP and Kubernetes

Inspect synthetic AWS KMS/Secrets Manager, Azure Key Vault, GCP Cloud KMS/Secret Manager and Kubernetes Secret metadata. Explain least-privilege IAM/RBAC, managed/workload identities, audit evidence, version lifecycle and provider-specific failure modes. Do not request payloads.

## Lab 4 — Rotation and policy-as-code

Detect overdue rotation, unknown age, missing production owner, disabled audit, unverified at-rest encryption, TLS gap and static identity. Design dual-credential overlap, application connection-pool refresh, database authentication checks, rollback and audit. For Kubernetes, compare etcd encryption-at-rest configuration and external secret synchronization.

## Lab 5 — Safe change governance

Bind provider, scope, resource, expected secret version, expected key version and incident ticket into a canonical SHA-256 plan digest. Reject key deletion, self-approval, expired approval, missing rollback, unverified consumers and wrong fingerprint. The simulator cannot rotate or disable keys.

## Production incident simulations

| # | Scenario | Expected response | Mode |
|---|---|---|---|
| 1 | Four provider metadata records | Normalize | Automated |
| 2 | Unknown provider | Reject | Automated |
| 3 | Invalid scope or owner | Reject | Automated |
| 4 | Negative credential age | Reject | Automated |
| 5 | Malformed boolean | Reject | Automated |
| 6 | Azure identifier case | Normalize key | Automated |
| 7 | Overdue rotation | Finding | Automated |
| 8 | At-rest encryption unverified | Finding | Automated |
| 9 | Workload identity missing | Finding | Automated |
| 10 | Audit disabled | Finding | Automated |
| 11 | Rotation age unknown | Finding | Automated |
| 12 | Production owner missing | Finding | Automated |
| 13 | TLS disabled | Critical finding | Automated |
| 14 | Compliant metadata | No findings | Automated |
| 15 | Partial inventory | Compliance unknown | Automated |
| 16 | Duplicate/malformed record | Reject | Automated |
| 17 | Paginated inventory | Combine | Automated |
| 18 | Page/item limit | Fail closed | Automated |
| 19 | Pagination loop | Reject | Automated |
| 20 | Invalid page | Reject | Automated |
| 21 | Stable advisory digest | Deterministic | Automated |
| 22 | Secret version changes | Digest changes | Automated |
| 23 | KMS key version changes | Digest changes | Automated |
| 24 | Destructive key action | Reject | Automated |
| 25 | No approval | Hold | Automated |
| 26 | Valid simulated approval | Advisory only | Automated |
| 27 | Expired/self approval | Hold | Automated |
| 28 | Wrong digest | Hold | Automated |
| 29 | Rollback or consumer checks missing | Hold | Automated |
| 30 | Approved plan with dry_run=false | Zero writes | Automated |
| 31 | AWS KMS AccessDenied | Inspect key policy/grants | Guided |
| 32 | Azure Key Vault firewall/RBAC denial | Inspect network and Entra identity | Guided |
| 33 | GCP KMS key disabled | Verify backup dependencies | Guided |
| 34 | Kubernetes Secret in logs | Contain, revoke and audit | Guided |
| 35 | PostgreSQL rotation causes outage | Restore verified consumers | Guided |
| 36 | MongoDB auth mismatch | Verify users, roles and pools | Guided |
| 37 | Elasticsearch service token compromise | Revoke and audit | Guided |
| 38 | Old encrypted backup unreadable | Recover historical key access | Guided |
| 39 | TLS certificate expiry | Restore chain and trust | Guided |
| 40 | KMS API throttling | Backoff and circuit breaker | Guided |

## Operational runbooks

**Key compromise:** isolate access, preserve logs, map ciphertext and backups, stage new key/DEK strategy, validate decryption and recovery, then retire compromised material safely.

**Rotation outage:** stop old-version revocation, inspect secret version labels, refresh application pools, validate PostgreSQL replication/HA and roll back as needed.

**Kubernetes Secret exposure:** identify impacted namespaces, audit API access, restrict RBAC, assess etcd/backup encryption and rotate affected credentials.

**TLS outage:** validate chain, SAN, expiry, clock, cipher suites and trust store. Never disable certificate verification.

**Backup decrypt failure:** inventory historical key versions and wrapped DEKs, restore access through approved recovery processes; never destroy keys prematurely.

**Compliance drift:** validate inventory completeness, policy revision, owner and exception expiry; unknown is not compliant.

## Final 100-point assessment

| Competency | Points |
|---|---:|
| Cryptography, TLS and envelope encryption design | 20 |
| AWS/Azure/GCP/Kubernetes secrets architecture | 20 |
| Rotation, versioning and DBRE recovery | 20 |
| Policy-as-code, audit and compliance | 15 |
| Approval, dry-run and idempotency | 15 |
| Automated tests and incident runbooks | 10 |
| **Total** | **100** |

**Pass:** ≥90 points, independent execution of offline tests, no-secret-read/no-write evidence, reviewed rotation rollback and clear distinction between simulated policy checks and live cryptographic acceptance.

**Validation:** Test source published; runtime execution, CI and real cryptographic/provider integration tests remain pending.
