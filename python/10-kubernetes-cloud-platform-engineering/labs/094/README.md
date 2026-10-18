# Chapter 094 — Executable AWS Infrastructure and Cloud Operations Lab

[Offline source](aws_lab.py) · [Offline unit tests](test_aws_lab.py) · [Optional read-only boto3 adapter](live_inventory.py)

## Offline setup

Requires Python 3.11+; the offline lab has **no external dependencies**.

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/094
python -m compileall -q aws_lab.py live_inventory.py test_aws_lab.py
python -m unittest -v test_aws_lab.py
python aws_lab.py --dry-run
python aws_lab.py --pressure
```

Windows: `py -3 -m unittest -v test_aws_lab.py`.

The offline simulator uses synthetic account, EC2, EKS and RDS records, metrics, capacity thresholds, cost proxy, change fingerprint and simulated approval. No AWS API requests or mutations occur.

## Optional AWS read-only lab

Run **only with approved credentials and a nonproduction account**:

```bash
python -m pip install "boto3>=1.35,<2"
aws sso login --profile YOUR_STAGING_PROFILE
aws sts get-caller-identity --profile YOUR_STAGING_PROFILE
python live_inventory.py --allow-live --profile YOUR_STAGING_PROFILE --region us-east-1 --expected-account YOUR_12_DIGIT_ACCOUNT --max-items 100
```

The adapter verifies STS account identity before inventory. It calls read-only EC2 DescribeInstances, EKS ListClusters/DescribeCluster and RDS DescribeDBInstances. It does not inspect Aurora DBClusters or CloudWatch directly. Missing IAM permission or an unexpected account causes failure, not a fallback to broader credentials.

Use the smallest IAM permissions that support STS caller identity and those specific read-only service APIs. Many AWS Describe/List APIs require resource wildcard in IAM, so compensate with account boundaries, SCPs, permission boundaries and tightly controlled role trust.

## Lab exercises

1. Verify a 12-digit account ID and AWS region.
2. Reject a wrong-account or malformed-region scope.
3. Paginate synthetic EC2/EKS/RDS records.
4. Detect duplicate resource IDs and malformed pages.
5. Trigger page and item budgets.
6. Reject stale/future/NaN metrics.
7. Diagnose CPU pressure and RDS free-storage pressure.
8. Calculate a simple hourly cost planning proxy.
9. Reject destructive action names such as `delete-db`.
10. Require simulated approval digest, owner and rollback evidence.
11. Confirm dry-run produces zero mutations.
12. Optionally inventory an approved staging account via boto3.

## Production extension checklist

- Implement CloudWatch `get_metric_data` with namespace/dimensions, freshness, datapoint and unit checks.
- Add Aurora DB cluster inventory and EKS node groups.
- Implement STS AssumeRole with account allowlist and audited role trust.
- Use boto3 Config timeouts and bounded standard/adaptive retries.
- Add Cost Explorer/CUR with billing lag and service attribution.
- Implement pagination and time budgets for every service.
- Add RDS backup, Multi-AZ, storage and IOPS readiness checks.
- Protect approvals with external authentication, signed plans and immutable audit.
- Validate staging first and never automate destructive DBRE actions from one metric.

## CI example (not enabled)

```yaml
name: chapter-094-aws-operations-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/10-kubernetes-cloud-platform-engineering/labs/094
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q aws_lab.py live_inventory.py test_aws_lab.py
      - run: python -m unittest -v test_aws_lab.py
```

Pin reviewed action SHAs before enabling. **Validation:** GitHub files published; runtime execution of committed tests, CI and live AWS adapter remains pending.
