# Chapter 094 — Python AWS Infrastructure and Cloud Operations Automation

**Part 10 — Kubernetes, AWS, Azure and GCP | Chapter 094/120 | Python 3.11+**

[Complete hands-on lab](labs/094-aws-infrastructure-cloud-operations-sre-dbre-lab.md) · [Executable project](labs/094/README.md)

## Objectives

Use Python and boto3 to build safe, bounded, least-privilege AWS operational tooling for identity, EC2, EKS, RDS, CloudWatch, capacity, cost and incident diagnostics. Practice pagination, rate limiting, idempotency, approval gates, dry-run, auditability and failure recovery.

## Architecture

```text
Approved operator / scheduled job
    -> AWS SSO / IAM role / STS AssumeRole
    -> account+region+resource scope validation
    -> boto3 session + per-service clients
    -> paginated EC2/EKS/RDS inventory
    -> CloudWatch metric observations
    -> capacity/cost diagnostics + policy evaluation
    -> JSON report + signed change request (production extension)
    -> default dry-run; no mutations in executable lab
```

The included executable project is an **offline AWS-shaped fake-client simulator**. A separate opt-in adapter demonstrates real **read-only** boto3 inventory with explicit AWS profile and region. No AWS mutations are implemented.

## 1. AWS SDK fundamentals

boto3 sessions resolve identity via explicit profiles, environment credentials, instance/task roles or workload identity. For a workstation, use AWS IAM Identity Center (SSO) and named profiles. For EKS Pods, prefer IRSA or EKS Pod Identity, not node-wide credentials. Avoid static access keys, hard-coded secrets and printing credential fields.

Use `boto3.Session(profile_name=...,region_name=...)` and service clients: `sts`, `ec2`, `eks`, `rds`, `cloudwatch` and `ce` (Cost Explorer). `sts.get_caller_identity()` confirms the current account and ARN; do not infer permission from successful authentication. Cross-account `AssumeRole` requires explicit trust and least-privilege role policy. Restrict approved account IDs and regions.

Use botocore `Config(retries={"mode":"standard","max_attempts":...},connect_timeout=...,read_timeout=...)` and application-level deadlines. Never stack uncontrolled retries.

## 2. Inventory and pagination

**EC2:** `describe_instances` returns Reservations containing Instances; use a paginator and bounded max items/pages. Extract instance ID, state, instance type, VPC/subnet, private IP and tags while redacting sensitive metadata.

**EKS:** `list_clusters` is paginated; `describe_cluster` yields status/version/endpoint and control-plane metadata. Node groups and Fargate profiles are separate APIs. Do not log private endpoint credentials or token data.

**RDS:** `describe_db_instances` is paginated; inspect identifier, engine/version, instance class, Multi-AZ, storage, status and backup retention. Aurora clusters require `describe_db_clusters`; an RDS DB instance alone does not capture Aurora topology. Never stop/delete production databases from inventory automation.

All collectors should enforce account, region, page and record budgets; detect malformed responses and duplicate identifiers. Pagination consistency is not a transactional snapshot.

## 3. Monitoring and CloudWatch

CloudWatch `get_metric_data` retrieves metric time series. EC2 CPUUtilization, RDS CPUUtilization, FreeStorageSpace, DatabaseConnections, ReadLatency and WriteLatency can help diagnose incidents. Check dimensions, unit, statistic, period, timestamp freshness, datapoint count and missing-data policy. EKS control-plane metrics and container/node metrics require appropriate add-ons and telemetry setup.

Use Prometheus/OpenTelemetry for app-level latency, errors and SLOs. Do not treat absent CloudWatch data as zero utilization or a healthy service. Correlate CloudWatch with Kubernetes events, PostgreSQL replication/locks, MongoDB WiredTiger, Elasticsearch disk IOPS, and Kafka lag.

## 4. Capacity and FinOps

Track EC2 instance type and fleet size, RDS allocated storage and free space, EKS node capacity, CPU utilization and historical demand. Cost Explorer `get_cost_and_usage` is account/permission/region dependent and billing data can lag. Treat a simple hourly estimate as a **planning proxy**, not actual billed cost. Reserved Instances, Savings Plans, storage, data transfer, NAT, licenses and regional prices require authoritative billing data.

Set thresholds for CPU, storage, latency and cost growth; require time-window evidence before recommending rightsizing. Capacity is constrained by peak demand, memory, IOPS, failover headroom and SLOs, not CPU alone.

## 5. Retries and idempotency

Use boto3 paginators and SDK retry policy for throttling and transient service failures. Bound retries, page counts and overall execution time. A 403/AccessDenied is an authorization issue, not a retry candidate. For ambiguous writes, reconcile authoritative state before retry; use API idempotency tokens where supported. The lab intentionally has no mutating AWS operations.

## 6. Approval gates and dry-run

A production change plan binds account, region, resource ARN, intended action, current state, expected version, rollback, owner, approval expiration and audit correlation. Compute a canonical SHA-256 plan fingerprint, then require **independently authenticated approval**. A fingerprint or CLI flag is not an authorization mechanism.

Default to read-only and dry-run. For high-risk DBRE actions (RDS failover, cluster deletion, storage changes, IAM grants), require human approval, backups, maintenance windows, blast-radius review and recovery evidence.

## 7. AWS IAM and STS security

- Use dedicated roles with least-privilege actions and resource conditions where supported.
- Scope `ec2:Describe*`, `eks:ListClusters`, `eks:DescribeCluster`, `rds:DescribeDBInstances`, `cloudwatch:GetMetricData` and `sts:GetCallerIdentity` as narrowly as AWS permits.
- Be aware that many Describe/List APIs require `Resource:"*"`; compensate with account/region boundaries, SCPs, permission boundaries and output filtering.
- Log role ARN and request IDs, never session tokens or secrets.
- Validate assumed account ID and role ARN before collecting cross-account inventory.

## 8. Production incident simulations

| Scenario | Investigation and guardrail |
|---|---|
| STS wrong account | Reject before discovery |
| Expired SSO session | Reauthenticate, do not fall back to static keys |
| AccessDenied | Inspect IAM trust/permission boundary |
| EC2 throttling | Bounded retry and page budget |
| EKS cluster DEGRADED | Check control plane, nodes, events |
| RDS storage pressure | Check FreeStorageSpace, IOPS, backup/maintenance |
| Aurora writer failover | Check cluster writer, replica lag, endpoint |
| CloudWatch missing datapoints | Mark unknown, do not assume healthy |
| EC2 CPU sustained high | Correlate load, scaling and memory |
| Cost spike | Verify CUR/Cost Explorer attribution and lag |
| AWS regional outage | Validate dependencies and DR plan |
| MongoDB/Elasticsearch on EC2 | Correlate IOPS/latency with workload |

## 9. Runbooks

**Credential/STS failure:** verify AWS SSO profile, session validity, caller identity, approved account and region. Never echo secrets.

**Inventory failure:** verify service permissions, pagination tokens, API throttling, region availability and budgets; preserve partial-data warning.

**EKS incident:** check cluster status, node groups, add-ons, Kubernetes events and API reachability. Avoid blind node termination.

**RDS incident:** check storage/IOPS, connections, replication, backup and failover health. Do not restart a production primary without an approved plan.

**Cost anomaly:** correlate resource inventory with Cost Explorer/CUR, Savings Plans and tags; confirm billing lag before conclusions.

**CloudWatch missing data:** validate metric dimensions, periods, namespace and permissions; escalate unknown telemetry.

## 10. Assessment and next chapter

The [hands-on lab](labs/094-aws-infrastructure-cloud-operations-sre-dbre-lab.md) contains executable offline code, unit tests, opt-in read-only boto3 adapter, incident drills, runbooks and a **100-point assessment**.

**Validation boundary:** Source publication and offline tests are distinct from live AWS validation. No cloud account access or production changes are required for the default lab.

**Next proposed:** Chapter 095 — Python Azure Infrastructure and Cloud Operations Automation.
