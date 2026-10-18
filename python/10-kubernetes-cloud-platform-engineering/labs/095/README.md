# Chapter 095 — Executable Azure Cloud Operations Lab

[Offline simulator](azure_lab.py) · [Unit tests](test_azure_lab.py) · [Read-only Azure SDK adapter](live_inventory.py)

## Run offline (Python 3.11+)

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/095
python -m compileall -q azure_lab.py live_inventory.py test_azure_lab.py
python -m unittest -v test_azure_lab.py
python azure_lab.py --dry-run
python azure_lab.py --pressure
```

No Azure credentials or third-party dependencies are needed. The offline lab exercises subscription/resource-group validation, paginated VM/AKS/PostgreSQL-shaped inventory, metric freshness, capacity, cost proxy, simulated approval, idempotent plan hashes and dry-run. **Zero Azure API calls and mutations.**

## Optional approved staging inventory

```bash
python -m pip install azure-identity azure-mgmt-compute azure-mgmt-containerservice
az login
az account set --subscription YOUR_STAGING_SUBSCRIPTION_UUID
az account show --query '{subscription:id,tenant:tenantId}' -o json
python live_inventory.py --allow-live --subscription YOUR_STAGING_SUBSCRIPTION_UUID --resource-group YOUR_STAGING_RG --max-items 100
```

The live adapter uses `AzureCliCredential` and read-only VM and AKS list APIs only. It does not query PostgreSQL, Azure Monitor or Cost Management. Verify tenant/subscription and scoped Azure Reader permissions independently. Never use an unapproved production subscription.

## Exercises

1. Reject invalid subscription and resource group.
2. Detect wrong-subscription IDs and duplicates.
3. Enforce page and inventory limits.
4. Reject stale, future and NaN metrics.
5. Simulate high CPU and low free-storage percentage.
6. Estimate hourly cost as a planning proxy.
7. Reject destructive action names.
8. Verify deterministic SHA-256 plan fingerprints.
9. Hold when approval, owner or rollback evidence is absent.
10. Verify all modes produce zero mutations.
11. Design PostgreSQL Flexible Server and Azure Monitor SDK integrations.
12. Optionally inventory VM and AKS resources in staging.

## Production extensions

Implement PostgreSQL Flexible Server SDK inventory, Azure Monitor Metrics Query, Cost Management, managed identities, tenant allowlists, robust retries/deadlines, authenticated expiring approvals, resource-level audit and integration tests. Live mutations are intentionally not implemented.

## CI template (not enabled)

```yaml
name: chapter-095-azure-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/10-kubernetes-cloud-platform-engineering/labs/095
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q azure_lab.py live_inventory.py test_azure_lab.py
      - run: python -m unittest -v test_azure_lab.py
```

Pin reviewed GitHub Actions SHAs before enabling. **Validation:** GitHub publication confirmed; committed test execution, CI and live Azure validation pending.
