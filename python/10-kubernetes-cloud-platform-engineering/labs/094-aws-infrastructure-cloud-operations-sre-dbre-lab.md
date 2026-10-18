# Chapter 094 — Python AWS Infrastructure and Cloud Operations SRE/DBRE Lab

[Standalone project](094/README.md) · [Offline Python](094/aws_lab.py) · [Read-only boto3 adapter](094/live_inventory.py) · [Automated tests](094/test_aws_lab.py)

## Mission and architecture

Build safe AWS cloud operations diagnostics for EC2, EKS, RDS, identity, inventory, CloudWatch monitoring design, capacity, cost and change governance.

```text
STS identity/account allowlist -> bounded EC2/EKS/RDS inventory
          |                                 |
          |                          CloudWatch metrics (design)
          |                                 |
          +-> capacity and cost proxy -> advisory change plan
                                              |
                                    simulated approval + digest
                                              |
                                    dry-run / zero mutations
```

The offline simulator makes no AWS calls. The optional boto3 adapter uses only approved read-only AWS APIs.

## Lab 1 — Offline execution

```bash
cd python/10-kubernetes-cloud-platform-engineering/labs/094
python -m compileall -q aws_lab.py live_inventory.py test_aws_lab.py
python -m unittest -v test_aws_lab.py
python aws_lab.py --dry-run
python aws_lab.py --pressure
```

## Lab 2 — IAM, STS and identity

Validate a 12-digit account and AWS region. Compare `sts:GetCallerIdentity` with the approved account before any discovery. Explain IAM role trust, AWS SSO, EKS Pod Identity/IRSA and least-privilege Describe/List permissions. Never log tokens or use static access keys in source.

## Lab 3 — EC2/EKS/RDS inventory and pagination

Exercise the fake paginator and item/page budgets. Detect duplicate resources and malformed responses. Optionally run the [read-only boto3 adapter](094/README.md) against an approved staging account with explicit profile, region, expected account and `--allow-live`.

## Lab 4 — Monitoring, capacity and CloudWatch

Use synthetic metric freshness and CPU/free-storage thresholds. Design CloudWatch `get_metric_data` queries for EC2 CPUUtilization and RDS FreeStorageSpace, DatabaseConnections, ReadLatency and WriteLatency. **Live CloudWatch API collection is not implemented in the project.** Never treat missing datapoints as zero.

## Lab 5 — Cost and FinOps

Calculate a simple EC2 hourly cost proxy; explain why it excludes storage, data transfer, reserved pricing, Savings Plans, RDS, NAT and taxes. Design a Cost Explorer/CUR follow-up with billing lag, account and tag attribution.

## Lab 6 — Approval, dry-run and idempotency

Build a canonical SHA-256 fingerprint for an advisory capacity review. Simulate owner approval and rollback evidence. Reject destructive action names. No AWS mutation API is implemented, even with simulated approval.

## Production incident simulations

| Scenario | Expected behavior | Mode |
|---|---|---|
| Valid account/region | Accept | Automated |
| Invalid account/region | Reject | Automated |
| GovCloud region format | Accept | Automated |
| Paginated inventory | Combine pages | Automated |
| Empty inventory | Empty result | Automated |
| Page/item budget | Reject | Automated |
| Repeated pagination token | Reject | Automated |
| Malformed page | Reject | Automated |
| Duplicate resource ID | Reject | Automated |
| Missing resource status | Reject | Automated |
| Stale/future CloudWatch-like metric | Reject | Automated |
| NaN/negative metric | Reject | Automated |
| CPU/free-storage pressure | Flag | Automated |
| Invalid capacity range | Reject | Automated |
| Cost proxy | Calculate | Automated |
| Negative cost input | Reject | Automated |
| Destructive action name | Reject | Automated |
| Missing approval | Hold | Automated |
| Wrong digest | Hold | Automated |
| Rollback untested | Hold | Automated |
| Dry-run | Zero mutations | Automated |
| STS wrong account | Stop before inventory | Guided/live |
| Expired SSO credentials | Reauthenticate | Guided |
| IAM AccessDenied | Review least privilege | Guided |
| EC2 API throttling | Bound retry | Guided |
| EKS degraded | Inspect node groups and control plane | Guided |
| RDS storage/IOPS saturation | Diagnose before scaling | Guided |
| Aurora writer failover | Check cluster topology | Guided |
| CloudWatch no datapoints | Mark unknown | Guided |
| AWS cost anomaly | Reconcile billing attribution | Guided |
| PostgreSQL/MongoDB/Elasticsearch on AWS | Correlate workload and infrastructure | Guided |

## Troubleshooting runbooks

**STS/credentials:** check SSO session, caller ARN/account, role trust, SCPs and region. No secret logging.

**Inventory:** inspect paginator, IAM permissions, throttling, region and budgets; label partial data.

**EKS:** inspect cluster status, node groups, control-plane logs, Kubernetes events and CNI.

**RDS:** inspect FreeStorageSpace, connections, IOPS/latency, replication, backup and Multi-AZ before remediation.

**CloudWatch:** validate namespace, metric dimensions, period, units, datapoint count and freshness.

**FinOps:** verify Cost Explorer/CUR, billing lag, tags and Savings Plans before recommendations.

**Change gate:** require independently authenticated approval, tested rollback, blast-radius review and immutable audit evidence.

## 100-point assessment

| Domain | Points |
|---|---:|
| boto3, IAM, STS and security | 20 |
| EC2/EKS/RDS inventory and pagination | 20 |
| CloudWatch monitoring and capacity | 20 |
| Cost governance and estimation | 10 |
| Dry-run, approval, idempotency and retries | 15 |
| Automated tests, incident drills and runbooks | 15 |
| **Total** | **100** |

**Pass:** ≥90/100 with independently executed tests, correct dry-run evidence, least-privilege review and incident runbooks.

**Validation:** Source, tests and lab published. Runtime execution of the exact committed files, CI and live AWS integration remain pending.
