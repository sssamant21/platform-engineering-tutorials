# Chapter 097 — Python Multi-Cloud Infrastructure Inventory and Governance

**Part 10 | Chapter 097 of 120 | Python 3.11+**

[Complete hands-on lab](labs/097-multi-cloud-inventory-governance-sre-dbre-lab.md) · [Executable project](labs/097/README.md)

## Learning objectives

Build a safe inventory and governance system across **AWS, Azure and Google Cloud**. Normalize resource identity, scope, tags/labels, ownership, configuration and capacity; detect inventory drift, compliance violations, cost exposure and orphaned assets; enforce pagination, retry budgets, deterministic reporting, dry-run, approval and idempotency.

## Reference architecture

```text
AWS boto3 read-only APIs  ──┐
Azure management SDK      ──┼──> scoped adapters / bounded pagination
GCP Python SDK            ──┘                  |
                         provider-specific records
                                    |
                      normalization + provenance
                                    |
               stable IDs / ownership / tags / policies
                                    |
                snapshot diff + compliance + FinOps
                                    |
             deterministic JSON report / advisory plan
                                    |
           authenticated approval (production extension)
                                    |
                 NO MUTATIONS in published lab
```

## 1. Normalized resource model

Use `provider`, `account_or_project`, `region`, `resource_id`, `kind`, `name`, `state`, `owner`, `environment`, `cost_center`, `monthly_cost_usd`, `capacity`, `tags` and `observed_at`. Keep original provider identifiers unchanged: AWS ARNs/instance IDs, Azure ARM IDs and GCP full resource names. A normalized identity must include provider, account/project and native ID to prevent cross-cloud collisions. Separate missing attributes from known-empty attributes.

Do not interpret AWS tags, Azure tags and GCP labels as identical. GCP labels have naming constraints and are not a substitute for IAM. Tag casing and inherited governance vary. Normalize only after defining explicit precedence rules and preserving raw metadata.

## 2. Authentication and least privilege

**AWS:** boto3 Session, STS GetCallerIdentity, scoped IAM roles and cross-account AssumeRole with external ID where appropriate. Verify account and region before inventory. Use paginators for EC2, RDS and EKS.

**Azure:** Microsoft Entra ID, managed identity or workload identity, Azure SDK and resource-group/subscription scoped Reader. Validate tenant, subscription and RBAC. Azure ARM resource IDs are case-insensitive for comparison, but preserve originals for audit.

**GCP:** Application Default Credentials, Workload Identity Federation and least-privilege Compute/GKE/Cloud SQL Viewer roles. Verify project and quota project. Avoid long-lived service-account keys.

A successful token exchange does not establish authorization to read all assets. Fail closed on unexpected account/project, and explicitly mark partial inventories caused by 403, throttling or API outages.

## 3. Inventory collectors and pagination

Build a provider adapter contract: `collect(scope, deadline, max_pages, max_items) -> records, warnings`. Collect only approved resource groups/projects/regions. Use SDK-native pagination with item and time budgets. AWS examples: EC2 DescribeInstances, RDS DescribeDBInstances, EKS ListClusters. Azure examples: VirtualMachines.list, ManagedClusters.list_by_resource_group, PostgreSQL Flexible Server list. GCP examples: InstancesClient.list, ClusterManagerClient.list_clusters, Cloud SQL Admin instances.list.

The executable lab uses **synthetic records** and fake pagination for all three providers; it makes no real cloud API calls. Real adapters are documented as opt-in extensions and should be read-only.

## 4. Drift detection

Compare two complete, time-stamped snapshots using stable composite keys. Classify **added**, **removed**, **changed** and **unchanged** resources. Treat resource disappearance during partial or stale collection as **unknown**, not deletion. Ignore volatile telemetry fields when computing configuration drift; include owner, environment, cost center, state and capacity when policy-relevant.

Use Git or a versioned CMDB as an approved desired-state source; a prior observed snapshot is not necessarily desired state. Never automatically revert a cloud resource based only on snapshot difference.

## 5. Compliance, ownership and tagging

Illustrative policies: production assets require owner, environment and cost center; critical databases require a backup review; public exposure needs security review; unknown owner is a governance violation. Define policy-as-code with versioned exemptions, expiration, approval and audit. Separate missing metadata from a real security vulnerability.

For SRE/DBRE, correlate ownership and lifecycle with Elasticsearch/OpenSearch clusters, PostgreSQL/RDS/Azure PostgreSQL/Cloud SQL, MongoDB and Kafka. Never delete untagged or allegedly unused resources automatically.

## 6. Capacity and FinOps

Collect CPU, storage headroom, provisioned IOPS, throughput, memory, HA/replication and observed peak demand. AWS CloudWatch, Azure Monitor and GCP Cloud Monitoring have different units, time grains and metric availability. Missing telemetry is unknown. Cost proxies must be labeled as estimates, not billing: use AWS CUR/Cost Explorer, Azure Cost Management and GCP Billing Export for actual attribution. Factor reservations/commitments, network egress, storage, backups, observability and cross-region traffic.

## 7. Retry, idempotency and governance

Retry only transient 429/5xx with bounded exponential backoff, jitter, deadlines and provider rate limits. Do not retry 401/403 without fixing authorization. Use deterministic sorted JSON, snapshot digests and idempotent reports. A proposed change should bind the exact scope, resources, action, reason, owner, rollback evidence and SHA-256 digest. The hash is not approval. Require externally authenticated, expiring approval and change-management controls for production modifications.

**Safety:** This chapter implements advisory plans only, even if simulated approval is true.

## 8. Production incident scenarios

| Scenario | Investigation |
|---|---|
| AWS STS wrong account | Abort, verify role and account allowlist |
| Azure wrong subscription | Abort before collection |
| GCP ADC wrong project | Abort, validate project and principal |
| Cross-cloud duplicate native IDs | Use composite identity |
| Missing owner on production RDS | Raise governance finding, do not delete |
| Partial API response | Mark incomplete and suppress deletion claims |
| Pagination loop | Fail closed with bounded budget |
| Provider API 429 | Backoff with deadline |
| Stale metrics | Mark unknown, avoid rightsizing |
| Cost spike | Verify billing exports and commitment effects |
| Elasticsearch disk saturation | Check IOPS, throughput, latency and queue |
| PostgreSQL HA/failover risk | Validate backups, replicas and RPO/RTO |
| Unapproved tag remediation | Hold for approval |
| Conflicting CMDB desired state | Require owner review |

## 9. Operational runbooks

**Collector outage:** identify provider/scope, permission and pagination failure; preserve last good snapshot with freshness label.

**Drift spike:** validate snapshot completeness and normalizer version before opening change tickets.

**Orphaned asset:** verify ownership, application dependencies, backups, retention and change approval before any action.

**Cost anomaly:** reconcile cost with provider billing, tagging and committed discounts; check network and observability charges.

**DBRE pressure:** investigate IOPS, storage, locks, replication and workload before recommending scaling or failover.

**Approval failure:** verify signed plan, exact resource IDs, owner, rollback and expiry; no mutation.

## 10. Lab and assessment

The [Chapter 097 lab](labs/097-multi-cloud-inventory-governance-sre-dbre-lab.md) includes a complete executable Python simulator, automated tests, drift/compliance/FinOps drills, runbooks and a 100-point assessment.

**Validation boundary:** Published code is offline and uses fake providers. Real SDK integrations, CI and production validation are separate acceptance gates.

**Next proposed:** Chapter 098 — Python Multi-Cloud Observability and Incident Automation.
