# Chapter 096 — Executable GCP Infrastructure and Operations Lab

[Offline simulator](gcp_lab.py) · [Automated unit tests](test_gcp_lab.py) · [Optional read-only SDK adapter](live_inventory.py)

## Offline setup

Python 3.11+ standard library only. No GCP credentials, network or billing access required.

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/096
python -m compileall -q gcp_lab.py live_inventory.py test_gcp_lab.py
python -m unittest -v test_gcp_lab.py
python gcp_lab.py --dry-run
python gcp_lab.py --pressure
```

Windows: `py -3 -m unittest -v test_gcp_lab.py`.

The offline simulator validates project/location, paginates synthetic Compute/GKE/Cloud SQL inventory, rejects invalid metrics, flags capacity, estimates a simple cost proxy and evaluates advisory change approval. **Zero GCP API calls and mutations**.

## Optional approved staging inventory

```bash
python -m pip install google-auth google-cloud-compute google-cloud-container
gcloud auth application-default login
gcloud config set project YOUR_STAGING_PROJECT
python live_inventory.py --allow-live --project YOUR_STAGING_PROJECT --zone us-central1-a --max-items 100
```

The adapter calls only read-only Compute Engine InstancesClient.list and GKE ClusterManagerClient.list_clusters. It does not call Cloud SQL Admin, Cloud Monitoring or billing APIs. It rejects an ADC project mismatch when the ADC project is provided, but project identity and IAM permissions must be independently verified. Use least-privilege Viewer roles in a nonproduction project.

## Hands-on exercises

1. Validate project ID and zone.
2. Reject malformed scope.
3. Paginate synthetic resources and enforce budgets.
4. Reject duplicate resources and malformed pages.
5. Reject stale/future/NaN metrics.
6. Simulate high CPU and low storage headroom.
7. Calculate hourly cost proxy.
8. Reject destructive action names.
9. Validate deterministic SHA-256 plan digest.
10. Require simulated owner approval and rollback evidence.
11. Verify no cloud writes, even when approval is true.
12. Design Cloud SQL and Cloud Monitoring read-only SDK extensions.

## Production extensions

Implement Cloud SQL Admin inventory, Cloud Monitoring metrics, Billing Export cost analysis, workload identity federation, IAM allowlists, service account impersonation, retries/deadlines, resource scope checks, authenticated approvals and audit. Test in staging and avoid destructive database automation.

## CI example (not enabled)

```yaml
name: chapter-096-gcp-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/10-kubernetes-cloud-platform-engineering/labs/096
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q gcp_lab.py live_inventory.py test_gcp_lab.py
      - run: python -m unittest -v test_gcp_lab.py
```

Pin reviewed action SHAs before enabling. **Validation:** Source and tests published; committed runtime, CI and live GCP execution remain pending.
