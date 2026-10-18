# Chapter 099 — Cloud Platform Security, Secrets and Compliance Executable Lab

[Source](security_lab.py) · [36 unit tests](test_security_lab.py) · [Full lab](../099-cloud-security-secrets-compliance-sre-dbre-lab.md)

## Execute offline

Python 3.11+ standard library only. No AWS, Azure, GCP or Kubernetes credentials, network access or secret values are required.

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/099
python -m compileall -q security_lab.py test_security_lab.py
python -m unittest -v test_security_lab.py
python security_lab.py --dry-run
```

PowerShell: `py -3 -m unittest -v test_security_lab.py`.

The simulator inspects **synthetic metadata only** for AWS Secrets Manager, Azure Key Vault, GCP Secret Manager and Kubernetes Secrets. It checks ownership, workload identity, public-access indicator, audit enablement and credential age. It generates an advisory rotation proposal bound to scope, resource ID, ticket and expected version, then checks simulated independent approval, expiration and rollback evidence. **Zero secret payload reads, cloud API calls or mutations.**

## Hands-on exercises

1. Validate all four provider resource scopes and native identifiers.
2. Reject malformed metadata, negative ages and duplicate resources.
3. Detect overdue credential rotation and unknown credential age.
4. Flag production owner missing, public exposure and disabled audit.
5. Enforce synthetic pagination, page/item budgets and loop detection.
6. Reject destructive plan actions.
7. Verify deterministic SHA-256 plan digest.
8. Reject wrong digest, self-approval, expired approval and missing rollback evidence.
9. Confirm simulated approval never enables cloud writes.
10. Design a safe database credential rotation with consumer validation and rollback.
11. Explain why Kubernetes Secret base64 is not encryption.
12. Propose real audit evidence mapping and exemption lifecycle.

## Production extension blueprint (not implemented)

- AWS: boto3 STS and Secrets Manager `list_secrets`/`describe_secret`, IAM and CloudTrail metadata, without `get_secret_value`.
- Azure: `azure-identity` and `azure-keyvault-secrets` metadata/version listing, Entra ID managed identity and RBAC, without reading values.
- GCP: `google-cloud-secret-manager` list/get secret metadata, IAM and Cloud Audit Logs, without accessing secret version payloads.
- Kubernetes: minimal scoped metadata inventory, Kubernetes RBAC, audit and encryption-at-rest checks; avoid listing Secret data fields.
- Add provider deadlines, bounded retry/backoff, principal/scope allowlists, credential redaction, exception expiry and authenticated approvals.
- Real rotation requires dual-version overlap, consumer readiness, rollback, provider-specific APIs and staging validation. No mutation adapter is included.

## CI example (not enabled)

```yaml
name: chapter-099-cloud-security-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/10-kubernetes-cloud-platform-engineering/labs/099
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q security_lab.py test_security_lab.py
      - run: python -m unittest -v test_security_lab.py
```

Pin reviewed GitHub Actions SHAs before enabling. **Validation:** Equivalent local source passed 36 unit tests and syntax compilation. Execution of the exact GitHub revision, CI and live provider integrations remains pending.
