# Chapter 097 — Multi-Cloud Inventory and Governance Executable Lab

[Source](multicloud.py) · [Automated tests](test_multicloud.py) · [Full SRE/DBRE lab](../097-multi-cloud-inventory-governance-sre-dbre-lab.md)

## Requirements and execution

Python 3.11+ standard library only. No cloud credentials, SDK installations or network access required.

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/097
python -m compileall -q multicloud.py test_multicloud.py
python -m unittest -v test_multicloud.py
python multicloud.py --dry-run
python multicloud.py --partial
```

Windows PowerShell: `py -3 -m unittest -v test_multicloud.py`.

The lab simulates AWS, Azure and GCP inventory, normalizes provider identities, enforces pagination budgets, detects snapshot drift, flags ownership/tagging/storage governance violations, estimates synthetic monthly cost, computes a deterministic SHA-256 advisory plan and simulates approval. It makes **zero cloud API calls and zero mutations**.

## Exercises

1. Inspect normalized records and composite identity.
2. Verify Azure ARM ID case-insensitive comparison.
3. Test duplicate resource detection.
4. Trigger pagination loop, malformed page and item budgets.
5. Compare two complete inventory snapshots.
6. Mark a snapshot partial; verify removal becomes **unknown**.
7. Change an owner; detect configuration drift.
8. Find missing production owner, cost center and storage headroom.
9. Calculate estimated cost per provider.
10. Verify deterministic fingerprint regardless of resource ordering.
11. Reject destructive action names.
12. Verify simulated approval never authorizes a cloud write.

## Production SDK integration blueprint (not implemented)

- AWS: boto3 STS identity validation; EC2/RDS/EKS read-only paginators, account and region allowlists.
- Azure: Entra ID managed identity or AzureCliCredential; Compute/AKS/PostgreSQL read-only management clients, tenant/subscription/resource-group allowlists.
- GCP: ADC and Workload Identity Federation; Compute/GKE/Cloud SQL read-only SDK clients, project/zone allowlists.
- For each provider: bounded deadlines and page budgets, retry 429/5xx only, audit request IDs, normalize provider-native identifiers and retain source provenance.
- Mark incomplete inventories explicitly and suppress deletion claims.
- Integrate provider billing exports, telemetry freshness and CMDB ownership before production decisions.
- Require independently authenticated, expiring approvals for real remediation; no write adapters are provided.

## Example CI (not enabled)

```yaml
name: chapter-097-multicloud-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/10-kubernetes-cloud-platform-engineering/labs/097
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q multicloud.py test_multicloud.py
      - run: python -m unittest -v test_multicloud.py
```

Pin reviewed GitHub Actions SHAs before enabling. **Validation:** source/tests published; committed runtime execution, CI and live provider integration remain pending.
