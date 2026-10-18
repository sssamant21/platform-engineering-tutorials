# Chapter 100 — Cloud-Native Platform Engineering Production Capstone

[Executable simulator](capstone.py) · [51 unit tests](test_capstone.py) · [Full lab](../100-cloud-native-platform-engineering-production-capstone-lab.md)

## Run

Python 3.11+ standard library only. **No credentials, cloud SDKs, network access or Kubernetes cluster required.**

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/100
python -m compileall -q capstone.py test_capstone.py
python -m unittest -v test_capstone.py
python capstone.py --dry-run
python capstone.py --partial
```

Windows PowerShell: `py -3 -m unittest -v test_capstone.py`.

## Integrated simulation

The simulator produces synthetic AWS, Azure, GCP and Kubernetes resources; paginates bounded inventory; preserves provider-scoped identities; compares complete vs partial snapshots; checks GitOps revision drift, owner, audit, workload identity, rotation age and storage headroom; aggregates request-based SLOs and incident hypotheses; calculates synthetic FinOps; creates a deterministic SHA-256 advisory plan and evaluates independent, expiring approval with rollback evidence.

**Zero cloud API calls, zero secret reads, zero Kubernetes writes and zero remediation operations**, even with `dry_run=False`.

## Practical exercises

1. Validate four provider identities and Azure ARM ID casing.
2. Trigger malformed resource, NaN cost and capacity errors.
3. Enforce pagination, item/page budgets and loop detection.
4. Compare full snapshots and partial-inventory unknown removal.
5. Trigger GitOps revision mismatch and owner drift.
6. Investigate PostgreSQL/RDS storage headroom under 15%.
7. Find overdue rotation, missing audit and static workload identity.
8. Calculate request SLO and measured-window budget consumption.
9. Deduplicate identical alerts and group incident hypotheses.
10. Calculate synthetic monthly cost; explain why it is not billing.
11. Reject destructive actions and self-approval.
12. Validate expiry, plan digest, rollback evidence and no-write behavior.

## Production architecture extensions (not implemented)

- AWS: boto3 STS/EC2/EKS/RDS/CloudWatch read-only adapters with role and region allowlists.
- Azure: Entra ID managed identities, Azure SDK for AKS/PostgreSQL/Monitor and subscription allowlists.
- GCP: ADC/Workload Identity Federation, GKE/Cloud SQL/Monitoring clients and project allowlists.
- Kubernetes: official Python client with explicit context/namespace and read-only RBAC.
- GitOps: Argo CD/Flux status and deployment event correlation; immutable image digest checks.
- OpenTelemetry: trace context, metric semantic normalization and exporter backpressure.
- Secrets: metadata-only inventory, audit evidence and staged rotation design.
- SLO: multi-window burn-rate alerts with traffic safeguards.
- Safety: bounded retries, idempotent persistence, authenticated approval, verified rollback, change tickets, audits and staged testing.

## CI template (not enabled)

```yaml
name: chapter-100-capstone-offline
on: workflow_dispatch
jobs:
  tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: python/10-kubernetes-cloud-platform-engineering/labs/100
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m compileall -q capstone.py test_capstone.py
      - run: python -m unittest -v test_capstone.py
```

Pin reviewed GitHub Actions SHAs before enabling. **Validation:** Equivalent local source passed 51 unit tests and compilation; the exact committed GitHub revision and live cloud integrations have not been executed.
