# Chapter 097 — IaC Cost Allocation, Showback, Chargeback and Shared Platform Cost Models

**Part 20 — FinOps · Chapter 097/120 · SRE/DBRE enterprise tutorial**

> **Evidence boundary:** The companion Python labs use synthetic USD billing records and resource-usage fixtures. No AWS/Azure/GCP billing exports, Kubernetes metering, database accounting, invoice settlement or production chargeback were executed. Publishing this chapter does not certify a chargeback ledger.

## 1. Learning objectives

Build an explainable enterprise allocation model that maps infrastructure-as-code (IaC) ownership and actual cloud billing to service, tenant and cost center. Distinguish **showback** (transparent reporting without a financial transfer) from **chargeback** (approved internal transfer of costs). Reconcile all allocated, unallocated and shared costs back to source billing totals while protecting service SLOs and DBRE recovery objectives.

## 2. Enterprise architecture

~~~text
Protected Git / Terraform / OpenTofu / Pulumi / CFN / Bicep / Ansible
               | mandatory ownership / approved policy
AWS CUR 2.0   Azure Cost Export   GCP Billing BigQuery
               | immutable raw ledger + source lineage
       normalize currency, basis, credits, usage time
               | deduplicate + completeness + reconciliation
Kubernetes namespace/node metering + DBRE service inventory
               | weighted shared-cost allocation policy
               | idle and unallocated residuals retained
          tenant / application / cost-center ledger
               | showback dashboards / disputes / review
         finance-approved chargeback settlement
               | budget and anomaly alerts + SLO guardrails
~~~

**Trust boundaries:** Read-only billing ingestion must not have cloud mutation privileges. Separate policy author, cost-data processor, finance approver and settlement publisher. Protect tenant financial visibility with row-level access. Keep raw source, normalization version, weights, approvals and adjustments immutable and reproducible.

## 3. Theory — allocation and accounting

### 3.1 Direct, shared, idle and unallocated cost

- **Direct:** a resource has a verified owner, workload and approved cost center; attribute directly.
- **Shared:** platform node pools, control planes, NAT, load balancers, observability, security, databases and Kafka clusters; allocate with documented causal drivers.
- **Idle:** capacity paid for but not used. Choose a policy: platform retains idle cost, distribute proportional to reservation, or charge teams for reserved capacity. Make this visible.
- **Unallocated:** absent/invalid ownership, incomplete telemetry or unsupported cost items. **Never silently spread or discard** this residual.

### 3.2 Allocation mathematics

For pool cost \(C\), positive weights \(w_i\), and eligible teams \(i\):

\[
A_i = C\frac{w_i}{\sum_j w_j}, \qquad \sum_i A_i = C.
\]

Implement using decimal arithmetic and integer cents. Assign rounding remainders deterministically by largest fractional remainder, then stable team ID. Preserve gross, credits, net, basis, currency and adjustment records separately.

**Coverage** = allocated eligible spend / total eligible spend. **Reconciliation residual** = source billed total − sum(direct + shared allocated + unallocated). Require exactly zero cents residual before publishing chargeback. An allocation is not proof that its *weights* are economically fair.

### 3.3 Kubernetes shared platform allocation

Track per-namespace CPU/memory requests, actual usage, GPU reservation, PVC GB-month, node-hour, load-balancer and network egress. For node pools, reserve a documented share for system workloads and idle nodes. Avoid assuming CPU alone explains GPU or memory cost. Compare Kubecost/OpenCost-style metering against the provider's invoice, without treating any estimate as final billing. Enforce labels for owner, service, environment and cost center; cross-check labels against IaC inventory.

### 3.4 Stateful database and analytics allocation

For PostgreSQL/Aurora/RDS use vCPU, storage, IOPS, connections, backups, replication and actual query/tenant metrics. For MongoDB use collection/tenant footprint, replica overhead, backups and query load. For Redis use reserved memory, eviction, throughput and persistence. For Kafka/MSK use broker-hours, storage, partition ownership, retention and inter-AZ transfer. For Elasticsearch/OpenSearch use shards, tiered storage and indexing/search workloads. For Snowflake use query attribution, warehouse credits, shared service accounts, storage and CDC. Preserve baseline durability, RPO/RTO, availability and data integrity; **cost allocation must not cause automatic downsizing or data deletion**.

### 3.5 Cloud billing basis and adjustments

AWS CUR/Data Exports, Azure Cost Management exports and GCP Cloud Billing BigQuery exports differ in account scope, credit representation, labels and timing. Normalize to one approved basis (for example amortized net USD) with explicit treatment of savings plans, reserved instances, CUDs, marketplace charges, taxes, refunds and FX. Never sum overlapping actual and amortized views. Version effective-dated ownership changes so historical chargeback remains reproducible.

## 4. IaC policy and operational design

~~~hcl
variable "cost_tags" {
  type = object({
    owner       = string
    cost_center = string
    application = string
    environment = string
    managed_by  = string
  })
  validation {
    condition = alltrue([for v in values(var.cost_tags) : length(trimspace(v)) > 0])
    error_message = "Every resource requires complete ownership metadata."
  }
}
~~~

A module-level tag declaration does **not** prove tags reached every provider resource. Use read-only cloud inventory checks, Kubernetes admission policy, policy-as-code CI, effective-dated ownership registry and exception expiry. Finance must approve allocation formulas and chargeback rates; SRE/DBRE must approve any infrastructure optimization proposed from the resulting reports.

## 5. Executable offline labs

**Lab A — Billing ledger validation:** `ledger_gate.py` checks an exact synthetic account/period, USD amortized basis, unique line IDs, valid source digest, finite decimal amounts, nonempty ownership, and freshness. Supports direct, shared and unallocated pools.

**Lab B — Deterministic weighted allocation:** `allocate.py` uses integer cents and largest-remainder rounding; every cent is allocated once, and unallocated is explicitly preserved.

**Lab C — Reconciliation:** `reconcile.py` rejects missing pool allocations, duplicate lines, negative or mismatched cents, and nonzero ledger residual.

**Lab D — Chargeback decision:** `chargeback_gate.py` is an **advice-only** HOLD/QUARANTINE/READY_FOR_REVIEW control; it never sends a financial settlement or changes cloud resources.

~~~bash
cd infrastructure-as-code/labs/chapter-097
python3 ledger_gate.py fixtures/safe.json policy.json
python3 ledger_gate.py fixtures/unsafe.json policy.json # expected failure
bash run-preflight.sh
~~~

**Native staging lab (manual, not executed):** Authorize read-only exports from a disposable billing scope; verify line provenance and usage-period completeness; reconcile a native AWS/Azure/GCP cost view; collect Kubernetes namespace usage and DBRE capacity metrics; compare multiple shared-cost drivers; review disputed ownership with Finance; publish a *draft* showback report; obtain finance/SRE/DBRE approval before any chargeback.

## 6. Sixty SRE/DBRE incident simulations

| # | Incident | First safe response |
|---|---|---|
| 1 | AWS CUR shared EC2 cost assigned twice | Preserve raw records; validate ownership, weights and residual |
| 2 | Azure subscription charge mapped to wrong team | Preserve raw records; validate ownership, weights and residual |
| 3 | GCP BigQuery export delayed by two days | Preserve raw records; validate ownership, weights and residual |
| 4 | AWS savings plan benefit allocated inconsistently | Preserve raw records; validate ownership, weights and residual |
| 5 | Azure reservation amortization misapplied | Quarantine ledger publication; reconcile source and basis |
| 6 | GCP CUD credits double-subtracted | Quarantine ledger publication; reconcile source and basis |
| 7 | Unblended and amortized costs mixed | Quarantine ledger publication; reconcile source and basis |
| 8 | Cross-currency allocation without FX evidence | Quarantine ledger publication; reconcile source and basis |
| 9 | Invoice adjustment omitted from reconciliation | Quarantine ledger publication; reconcile source and basis |
| 10 | Refund misclassified as savings | Quarantine ledger publication; reconcile source and basis |
| 11 | Tax incorrectly charged to workload | Preserve raw records; validate ownership, weights and residual |
| 12 | Marketplace subscription has no owner | Preserve raw records; validate ownership, weights and residual |
| 13 | EKS node idle cost omitted | Preserve raw records; validate ownership, weights and residual |
| 14 | EKS system namespace cost billed to tenant | Preserve raw records; validate ownership, weights and residual |
| 15 | AKS node pool cost shared across wrong namespaces | Preserve raw records; validate ownership, weights and residual |
| 16 | GKE autopilot cost mixed with standard cluster | Preserve raw records; validate ownership, weights and residual |
| 17 | Kubernetes requests used without actual usage context | Preserve raw records; validate ownership, weights and residual |
| 18 | Pod CPU request exceeds node allocatable | Preserve raw records; validate ownership, weights and residual |
| 19 | Namespace deleted before billing reconciliation | Quarantine ledger publication; reconcile source and basis |
| 20 | PersistentVolume cost remains after namespace deletion | Preserve raw records; validate ownership, weights and residual |
| 21 | Ingress load balancer shared by four services | Preserve raw records; validate ownership, weights and residual |
| 22 | NAT gateway egress cost assigned to one team | Preserve raw records; validate ownership, weights and residual |
| 23 | Cross-region transfer billed to wrong service | Preserve raw records; validate ownership, weights and residual |
| 24 | CloudWatch/Prometheus shared observability cost omitted | Preserve raw records; validate ownership, weights and residual |
| 25 | OpenTelemetry trace ingestion grows unexpectedly | Preserve raw records; validate ownership, weights and residual |
| 26 | Service mesh telemetry cardinality spikes | Preserve raw records; validate ownership, weights and residual |
| 27 | Shared KMS key cost cannot be attributed | Preserve raw records; validate ownership, weights and residual |
| 28 | Platform control plane fee missing | Preserve raw records; validate ownership, weights and residual |
| 29 | Cluster autoscaler node churn changes allocation | Preserve raw records; validate ownership, weights and residual |
| 30 | GPU pool idle capacity hidden from tenants | Preserve raw records; validate ownership, weights and residual |
| 31 | PostgreSQL shared instance billed entirely to one schema | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 32 | Aurora shared cluster storage misallocated | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 33 | RDS backup overage incorrectly assigned | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 34 | PostgreSQL replica cost missing from allocation | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 35 | MongoDB shared replica set charged by query count only | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 36 | MongoDB snapshot cost assigned to retired tenant | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 37 | Redis shared cluster memory reservation ignored | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 38 | Redis Enterprise license spread without policy | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 39 | Kafka broker shared storage attributed to one topic | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 40 | MSK cross-AZ traffic omitted from chargeback | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 41 | Kafka partition skew distorts cost allocation | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 42 | OpenSearch shared shard costs attributed by document count | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 43 | Elasticsearch hot/warm storage allocation is stale | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 44 | Snowflake multi-team warehouse credits misattributed | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 45 | Snowflake storage billed by current rather than historical owner | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 46 | Snowflake CDC warehouse cost omitted | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 47 | Chargeback rate changes without approval | Preserve raw records; validate ownership, weights and residual |
| 48 | Finance ledger rounding creates cents mismatch | Quarantine ledger publication; reconcile source and basis |
| 49 | Negative credit line breaks allocation engine | Quarantine ledger publication; reconcile source and basis |
| 50 | Duplicate source billing line doubles chargeback | Quarantine ledger publication; reconcile source and basis |
| 51 | Billing feed missing provider account | Quarantine ledger publication; reconcile source and basis |
| 52 | Unallocated residual silently discarded | Preserve raw records; validate ownership, weights and residual |
| 53 | Team tag renamed mid-billing period | Quarantine ledger publication; reconcile source and basis |
| 54 | Cost center owner departed organization | Preserve raw records; validate ownership, weights and residual |
| 55 | Showback dashboard exposes another team's financial data | Preserve raw records; validate ownership, weights and residual |
| 56 | Chargeback export changes after invoice signoff | Quarantine ledger publication; reconcile source and basis |
| 57 | Budget alert points to wrong business owner | Preserve raw records; validate ownership, weights and residual |
| 58 | Optimization reduces PostgreSQL recovery capacity | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 59 | Chargeback incentive encourages unsafe Kafka retention | Freeze unsafe cost optimization; verify DBRE SLO and data protection |
| 60 | Shared platform allocation dispute has no escalation | Preserve raw records; validate ownership, weights and residual |

## 7. Twelve enterprise production runbooks

### R01 — Billing ledger source completeness and replay

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

### R02 — Cost basis, credits, refunds and currency

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

### R03 — AWS account and commitment allocation

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

### R04 — Azure subscription and reservation allocation

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

### R05 — GCP billing project and CUD allocation

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

### R06 — Kubernetes CPU/memory and idle node allocation

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

### R07 — Shared networking, ingress and observability

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

### R08 — PostgreSQL/Aurora/RDS shared cost and DBRE safety

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

### R09 — MongoDB/Redis shared tenancy and recovery

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

### R10 — Kafka/MSK and Elasticsearch/OpenSearch shared cost

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

### R11 — Snowflake warehouses, CDC and chargeback

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

### R12 — Finance reconciliation, dispute and sign-off

**Trigger:** unexplained charge, missing owner, duplicate allocation, budget anomaly, disputed shared cost or cost-related reliability regression. **Owner:** FinOps and service SRE, with Finance settlement approver and DBRE for stateful resources. **Detect:** establish provider account, UTC usage period, export ID, cost basis, currency, owner and source freshness. **Contain:** suspend chargeback publication, not the workload; preserve raw immutable records and policy version. **Diagnose:** compare source line IDs, IaC tags, actual inventory, Kubernetes/DBRE metering, shared-pool weights, discounts, rounding and unallocated residual. **Recover:** correct approved mappings or reprocess the same immutable inputs; obtain independent approval for effective-dated changes. **Verify:** zero-cent reconciliation, tenant access controls, customer SLO, RPO/RTO and data integrity. **Close:** signed finance ledger, dispute record, owner and corrective action.

## 8. Troubleshooting matrix

| Symptom | Likely failure | Required action |
|---|---|---|
| Chargeback exceeds invoice | duplicate line, mixed basis or rounding | quarantine, reconcile raw export |
| Shared pool has no weight | missing namespace/tenant usage | unallocated/UNKNOWN, never invent weights |
| Deleted namespace still billed | persistent volume or delayed billing | inspect cloud inventory and usage period |
| One team receives all NAT charges | single-owner heuristic | verify shared egress policy |
| Negative cost breaks ledger | refund or credit handling | separate adjustment ledger |
| Historical report changes | ownership mapping overwritten | effective-dated immutable policy |
| Invoice total differs from dashboard | credits, taxes, FX or late export | like-for-like accounting comparison |
| Database becomes slow after optimization | underprovisioning | rollback with DBRE and SLO evidence |
| Team can see other tenant cost | missing row-level access | revoke access and investigate |
| Cost allocation passes but no approval | showback conflated with chargeback | finance approval gate |

## 9. Final 100-point assessment

| Category | Points |
|---|---:|
| Enterprise architecture, IAM, billing provenance | 15 |
| Direct/shared/idle/unallocated model and accounting | 20 |
| Kubernetes and DBRE workload allocation | 20 |
| Offline labs, negative tests, deterministic cents | 20 |
| Finance reconciliation, showback/chargeback governance | 15 |
| Incident response, runbooks and independent acceptance | 10 |
| **Total** | **100** |

Pass >=85 with **zero critical failures**. Critical: wrong billing account, double-charging, unallocated spend hidden, false invoice reconciliation, tenant data leak, unauthorized financial settlement, destructive cost remediation or DBRE/SLO regression. Offline tests are not native billing acceptance.

## 10. Completion and next chapter

Chapter 097 is the second chapter of **Part 20 — FinOps**. Next: **Chapter 098 — IaC Cost Forecasting, Budget Governance, Anomaly Detection and FinOps Automation**.
