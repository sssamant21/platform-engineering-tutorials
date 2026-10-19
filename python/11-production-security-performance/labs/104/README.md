# Chapter 104 — Security Auditing, Compliance and Policy-as-Code Executable Lab

[Offline Python policy engine](audit_lab.py) · [Automated tests](test_audit_lab.py) · [Full SRE/DBRE lab](../104-security-auditing-compliance-policy-as-code-sre-dbre-lab.md)

## Run offline

Python 3.11+ standard library only; no cloud credentials, Kubernetes access, secret values, network connections or writes.

```bash
cd python/11-production-security-performance/labs/104
python -m compileall -q audit_lab.py test_audit_lab.py
python -m unittest -v test_audit_lab.py
python audit_lab.py --dry-run
python audit_lab.py --partial
```

Windows PowerShell: `py -3 -m unittest -v test_audit_lab.py`.

## Implemented

- Synthetic AWS CloudTrail, Azure Activity, GCP Cloud Audit and Kubernetes audit evidence references.
- Normalized provider/scope/resource/control identity and source provenance.
- Policy checks for audit logging, least privilege, encryption at rest, owner and backup verification.
- Evidence freshness, duplicate detection, bounded pagination and unknown coverage on incomplete collection.
- Expiring exception records, compliance drift between complete snapshots and canonical SHA-256 report fingerprints.
- Version-bound advisory change plan with independent approver, expiry and rollback evidence.
- **No live cloud API calls, no secret reads, no cryptographic signatures and zero mutations.**

## Exercises

1. Normalize all four provider evidence sources.
2. Reject unknown controls, malformed IDs and invalid timestamps.
3. Detect failed controls and stale/future evidence.
4. Mark incomplete collection as unknown, not compliant.
5. Create an expiring, scoped risk exception and verify re-evaluation.
6. Compare complete snapshots for new compliance failures.
7. Verify deterministic report hashes and explain why SHA-256 is not a signature.
8. Reject pagination loops and collection budget violations.
9. Reject self-approval, expired approval and wrong plan digest.
10. Map controls to CIS, NIST SP 800-53 and SOC 2 without claiming certification.
11. Design a PostgreSQL backup restore-evidence workflow.
12. Build audit-gap incident and evidence-integrity runbooks.

## Production extensions — NOT implemented

- AWS: boto3 read-only CloudTrail, AWS Config, IAM Access Analyzer and account coverage adapters.
- Azure: Entra ID, Azure Policy, Activity Logs, resource diagnostic settings and Defender for Cloud.
- GCP: Cloud Asset Inventory, Cloud Audit Logs, IAM and Security Command Center.
- Kubernetes: API audit, RBAC, admission policy and encryption-at-rest posture checks.
- Implement bounded retries, quotas, cursor persistence, timestamps, signed evidence manifests, immutable retention and policy bundle versioning.
- Add authenticated independent approvals, exception ownership, compensating controls and live production acceptance.

## CI template (not enabled)

```yaml
name: chapter-104-audit-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/11-production-security-performance/labs/104
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q audit_lab.py test_audit_lab.py
      - run: python -m unittest -v test_audit_lab.py
```

Pin reviewed action SHAs before enabling. **Validation:** Tests are published; execution of exact committed files, CI, live cloud evidence collection and external compliance acceptance remain pending.
