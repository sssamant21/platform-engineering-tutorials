# Chapter 103 — Secrets, Encryption and Key Lifecycle Executable Lab

[Offline Python engine](secrets_lab.py) · [Automated tests](test_secrets_lab.py) · [Complete lab](../103-secrets-encryption-key-lifecycle-sre-dbre-lab.md)

## Run

Python 3.11+ standard library only. No credentials, cloud SDKs, Kubernetes access, secret payloads or network connections.

```bash
cd python/11-production-security-performance/labs/103
python -m compileall -q secrets_lab.py test_secrets_lab.py
python -m unittest -v test_secrets_lab.py
python secrets_lab.py --dry-run
python secrets_lab.py --partial
```

PowerShell: `py -3 -m unittest -v test_secrets_lab.py`.

## Implemented

- Four-provider synthetic secret metadata (AWS, Azure, GCP, Kubernetes).
- Scope, native resource ID, secret/key version, owner, age, rotation policy, encryption-at-rest flag, TLS requirement, workload identity and audit controls.
- Policy findings for overdue/unknown rotation, missing owner, at-rest/TLS gaps, static identity and audit gaps.
- Bounded pagination, duplicate detection and partial inventory status **unknown**.
- Canonical SHA-256 advisory plan bound to secret version, key version, scope and incident ticket.
- Simulated independent, expiring approval with rollback and consumer-verification requirements.
- **Zero secret reads, cryptographic operations, cloud calls or mutations.**

## Exercises

1. Inspect AWS Secrets Manager/KMS metadata, version and owner.
2. Compare Azure Key Vault/Managed HSM identity and versioning.
3. Compare GCP Secret Manager/Cloud KMS version lifecycles.
4. Explain why Kubernetes Secret base64 is not encryption.
5. Detect missing TLS, audit, at-rest encryption and workload identity.
6. Detect overdue rotation and unknown secret age.
7. Exercise bounded pagination and partial inventory.
8. Compare secret version rotation vs KMS key rotation vs DEK rewrapping.
9. Validate deterministic plan digest and version binding.
10. Reject destructive key deletion, wrong digest and self-approval.
11. Require consumer readiness and rollback before approval.
12. Design PostgreSQL credential rotation and old-backup decrypt runbooks.

## Production extension blueprint (NOT implemented)

- AWS boto3: STS identity, KMS `describe_key`/`list_key_rotations` where applicable, Secrets Manager `describe_secret`/`list_secret_version_ids`; never fetch payloads for inventory.
- Azure SDK: `azure-identity`, Key Vault keys/secrets metadata and managed identity RBAC; avoid `get_secret` value access.
- GCP SDK: Cloud KMS key/version metadata, Secret Manager list/get secret metadata; avoid `access_secret_version`.
- Kubernetes API: namespace-scoped metadata-only inventory, encryption-at-rest configuration review, minimal RBAC and audit.
- For **real cryptography**, use KMS-backed envelope encryption or reviewed AEAD libraries, unique nonces, associated-data validation and key access controls. This project intentionally has no crypto routines.
- For **real rotation**, add authenticated change approvals, version compare-and-swap, consumer validation, rollback, idempotency, audit retention and staged provider tests.

## CI template (not enabled)

```yaml
name: chapter-103-secrets-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/11-production-security-performance/labs/103
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q secrets_lab.py test_secrets_lab.py
      - run: python -m unittest -v test_secrets_lab.py
```

Pin reviewed action commit SHAs before enabling. **Validation:** Automated test source is published; execution of exact committed code, CI, live cloud SDKs and cryptographic acceptance tests remain pending.
