# Chapter 096 — IaC Cost Observability, Cloud Billing Data, Tagging and FinOps Fundamentals

**Part 20 — FinOps · Chapter 096/120 · Enterprise SRE/DBRE**

> **Execution boundary:** The accompanying offline Python labs validate **synthetic billing records** and deterministic policy rules. They do not authenticate to AWS, Azure, GCP, Kubernetes, Snowflake or any database. Cost numbers in fixtures are illustrative, not real invoices. No real billing export, native cloud verification or DBRE performance acceptance has been executed.

## 1. Learning outcomes

Design an enterprise FinOps control plane that associates reviewed IaC changes with billing line items, tagged ownership, shared platform services, anomaly signals and reliability constraints. Explain invoice versus amortized cost, billing latency, discounts, credit treatment, workload allocation, and the distinction between forecast, realized savings and avoided future spend.

## 2. Enterprise reference architecture

~~~text
Protected Git + Terraform/OpenTofu/Pulumi/CFN/Bicep/Ansible
                     |
     tagging/ownership policy + CI cost estimate
                     |
   AWS accounts / Azure subscriptions / GCP projects
                     |
   AWS CUR 2.0/Data Exports | Azure Cost Management Export
            GCP Cloud Billing -> BigQuery
                     |
  immutable raw ingestion / provenance / currency / time
                     |
    schema validation + deduplication + late-data window
                     |
    resource tags + cloud inventory + Kubernetes allocation
                     |
   cost ledger -> showback/chargeback -> anomaly detection
                     |
      budget / owner / SRE-DBRE reliability guardrails
                     |
    approval -> controlled optimization -> actual bill check
~~~

**Trust boundaries:** billing data is sensitive; restrict access by account/project, encrypt exports, verify destination and source identity, avoid personal data in tags, and preserve raw immutable evidence. Billing export freshness is provider-dependent and can lag by hours or days. A fresh inventory does not mean a final invoice.

## 3. Theory: cloud billing semantics

**AWS:** AWS Data Exports/Cost and Usage Report (CUR 2.0) provides granular usage and cost records. Track payer/linked account, product, region, resource, usage period, pricing model, savings-plan/RI effects, and invoice adjustments. Resource IDs and tags can be absent or vary by service. Enable applicable cost allocation tags before expecting them in reports.

**Azure:** Cost Management exports may include actual and amortized cost views. Track billing scope, subscription, resource group, service, meter, pricing model, currency, reservation effects and export schedule. Some resource charges cannot be mapped to a specific workload.

**GCP:** Cloud Billing export to BigQuery provides standard/detailed usage and cost data, including credits and labels when present. Normalize billing account, project, SKU, usage dates, currency, adjustment and label semantics. Data availability and schema vary by export type.

**Never combine** unblended, amortized and net costs into one denominator without an explicit accounting policy. Credits, taxes, refunds, support fees, committed-use discounts and marketplace charges require separately declared treatment. Currency conversion needs dated FX rates and documented source.

## 4. FinOps data contract and ownership

The offline reference schema uses `line_id`, `provider`, `account`, `service`, `resource_id`, `usage_date`, `currency`, `cost_usd`, `cost_basis`, `tags`, `export_id` and `source_digest`. Native integration should additionally preserve billing period, ingestion time, unit of measure, usage quantity, pricing, credit type, invoice ID and original provider record for reconciliation.

Mandatory normalized tags: `owner`, `environment`, `cost_center`, `application`, `managed_by`. Normalize capitalization, whitespace and permitted values; avoid inferring an owner from a resource name. **Unallocated** is a first-class bucket and a policy failure for eligible spend. Shared EKS/AKS/GKE node, NAT, load balancer, monitoring and security costs need documented allocation weights and a residual bucket.

## 5. Cost, allocation and forecasting math

- Gross usage cost: sum of eligible pre-credit usage line items for the declared basis.
- Net cost: gross minus eligible credits and discounts **only if not already reflected in the chosen basis**.
- Allocation coverage: allocated eligible spend / all eligible spend; disclose excluded spend.
- Unit cost: eligible workload spend / verified business units (requests, GB processed, Kafka messages, patient records, etc.).
- Daily anomaly: compare same-service/account/region against seasonally adjusted historical baseline; require minimum volume, completeness and billing finalization.
- Forecast: daily run rate times remaining days, with confidence ranges and explicit seasonality; never treat a naive projection as invoice truth.
- Savings: compare normalized post-change realized billed cost to an agreed counterfactual while verifying customer SLO, durability, RPO/RTO and data correctness.

### Example guardrail

A proposed RDS rightsizing saving of $400/month is **not approved** if it violates IOPS, p99 latency, backup retention, failover RTO or replication RPO. FinOps is a reliability-aware optimization, not an automatic cheapest-instance selector.

## 6. IaC and policy patterns

~~~hcl
variable "tags" {
  type = object({
    owner       = string
    environment = string
    cost_center = string
    application = string
    managed_by  = string
  })
  validation {
    condition = alltrue([
      for v in values(var.tags) : length(trimspace(v)) > 0
    ])
    error_message = "All required ownership tags must be nonempty."
  }
}
~~~

For AWS provider default tags, Azure resource tags, GCP labels and Kubernetes labels/annotations, check provider-specific constraints and propagation. A tag on an IaC root module does not prove all child resources are tagged. Validate deployed inventory independently. Use policy-as-code in CI and periodic read-only drift scans. Never make a production billing or tag mutation automatically on the basis of an offline fixture.

## 7. Hands-on labs

**Lab A — Billing contract and ownership:** `billing_gate.py` validates a synthetic export with exact test account, accepted provider/currency/basis, required ownership tags, duplicate line rejection, source digests, and explicit freshness threshold.

**Lab B — Allocation ledger:** `allocate.py` aggregates Decimal USD cost by cost center and flags unallocated charges. It refuses duplicate line IDs and incompatible currencies/bases.

**Lab C — Anomaly classification:** `anomaly.py` evaluates a current-day spend against a declared baseline with completeness/freshness controls; returns `UNKNOWN`, `OK` or `REVIEW` (not a real cloud alert).

**Lab D — Reliability-aware savings gate:** `optimization.py` returns `QUARANTINE`, `HOLD` or `REVIEW_ONLY` for synthetic rightsizing changes, with fail-closed DBRE/SLO and approval constraints.

~~~bash
cd infrastructure-as-code/labs/chapter-096
python3 billing_gate.py fixtures/safe.json policy.json
python3 billing_gate.py fixtures/unsafe.json policy.json # expected nonzero
bash run-preflight.sh
~~~

**Lab E — Native staging validation (manual; not executed):** Create read-only billing exports for an authorized sandbox, verify source integrity and latency, cross-check native cost explorer against raw records, reconcile resource tags with IaC state and cloud inventory, evaluate a controlled low-risk optimization, and verify next billing period plus service/DBRE SLO. Obtain finance, SRE, DBRE and security sign-off.

## 8. Production SRE/DBRE incident simulations

| # | Scenario | Investigation priority |
|---|---|---|
| 1 | AWS CUR export missing a billing day | Verify provider source, billing basis, currency and export completeness |
| 2 | AWS cost allocation tag not activated | Trace ownership, IaC change, allocation and budget alert |
| 3 | Azure Cost Management export delivery stops | Verify provider source, billing basis, currency and export completeness |
| 4 | GCP Billing export BigQuery partition missing | Verify provider source, billing basis, currency and export completeness |
| 5 | AWS account misattributed to wrong business unit | Trace ownership, IaC change, allocation and budget alert |
| 6 | Azure subscription ownership unknown | Trace ownership, IaC change, allocation and budget alert |
| 7 | GCP project labels fail policy | Trace ownership, IaC change, allocation and budget alert |
| 8 | Terraform resource tags omitted | Trace ownership, IaC change, allocation and budget alert |
| 9 | OpenTofu module overwrites required tags | Trace ownership, IaC change, allocation and budget alert |
| 10 | Pulumi stack lacks cost-center metadata | Trace ownership, IaC change, allocation and budget alert |
| 11 | CloudFormation stack tags do not propagate | Trace ownership, IaC change, allocation and budget alert |
| 12 | Bicep resource group tags diverge from child resources | Trace ownership, IaC change, allocation and budget alert |
| 13 | Ansible-created EC2 resource is untracked | Trace ownership, IaC change, allocation and budget alert |
| 14 | Kubernetes namespace has no cost owner | Trace ownership, IaC change, allocation and budget alert |
| 15 | EKS cluster shared costs double-counted | Trace ownership, IaC change, allocation and budget alert |
| 16 | AKS node pool cost not allocated to namespace | Trace ownership, IaC change, allocation and budget alert |
| 17 | GKE idle node costs omitted | Trace ownership, IaC change, allocation and budget alert |
| 18 | Kubernetes pod requests exceed actual usage | Trace ownership, IaC change, allocation and budget alert |
| 19 | GPU reservation causes runaway cost | Trace ownership, IaC change, allocation and budget alert |
| 20 | Cloud NAT data processing spikes | Trace ownership, IaC change, allocation and budget alert |
| 21 | Cross-AZ traffic spikes after topology change | Trace ownership, IaC change, allocation and budget alert |
| 22 | Inter-region egress grows after DR test | Trace ownership, IaC change, allocation and budget alert |
| 23 | RDS provisioned IOPS exceeds workload needs | Protect data correctness, performance and recovery objectives |
| 24 | Aurora storage growth exceeds forecast | Protect data correctness, performance and recovery objectives |
| 25 | PostgreSQL replica unused but billed | Protect data correctness, performance and recovery objectives |
| 26 | MongoDB disk volume orphaned after restore | Protect data correctness, performance and recovery objectives |
| 27 | MongoDB backup retention doubles storage | Protect data correctness, performance and recovery objectives |
| 28 | Redis cache oversized for working set | Protect data correctness, performance and recovery objectives |
| 29 | Redis Enterprise license costs misallocated | Protect data correctness, performance and recovery objectives |
| 30 | MSK broker class oversized | Protect data correctness, performance and recovery objectives |
| 31 | Kafka retention expands storage bills | Protect data correctness, performance and recovery objectives |
| 32 | Elasticsearch hot tier overprovisioned | Protect data correctness, performance and recovery objectives |
| 33 | OpenSearch snapshot retention creates excess charges | Protect data correctness, performance and recovery objectives |
| 34 | Snowflake warehouse auto-suspend disabled | Protect data correctness, performance and recovery objectives |
| 35 | Snowflake query spill increases credits | Protect data correctness, performance and recovery objectives |
| 36 | Snowflake storage retention costs grow | Protect data correctness, performance and recovery objectives |
| 37 | Object storage lifecycle rule missing | Trace ownership, IaC change, allocation and budget alert |
| 38 | EBS volume orphaned after node replacement | Trace ownership, IaC change, allocation and budget alert |
| 39 | Public IPv4 charges not allocated | Trace ownership, IaC change, allocation and budget alert |
| 40 | Load balancer remains after app deletion | Trace ownership, IaC change, allocation and budget alert |
| 41 | Kubernetes PersistentVolume remains after namespace deletion | Trace ownership, IaC change, allocation and budget alert |
| 42 | Terraform destroy leaves cloud resource orphan | Trace ownership, IaC change, allocation and budget alert |
| 43 | Unreviewed provider upgrade changes pricing | Trace ownership, IaC change, allocation and budget alert |
| 44 | Spot interruption leads to expensive fallback | Trace ownership, IaC change, allocation and budget alert |
| 45 | Savings Plan commitment underutilized | Trace ownership, IaC change, allocation and budget alert |
| 46 | Reserved Instance coverage misreported | Trace ownership, IaC change, allocation and budget alert |
| 47 | Azure reservation utilization drops | Trace ownership, IaC change, allocation and budget alert |
| 48 | GCP committed-use discount applied to wrong project | Trace ownership, IaC change, allocation and budget alert |
| 49 | Currency conversion mixes USD and EUR | Verify provider source, billing basis, currency and export completeness |
| 50 | Credit adjustments counted as resource savings | Verify provider source, billing basis, currency and export completeness |
| 51 | Refund counted twice in cost report | Verify provider source, billing basis, currency and export completeness |
| 52 | Amortized and unblended costs mixed | Verify provider source, billing basis, currency and export completeness |
| 53 | Forecast ignores seasonal ingestion | Trace ownership, IaC change, allocation and budget alert |
| 54 | Cost anomaly alert routed to wrong owner | Trace ownership, IaC change, allocation and budget alert |
| 55 | Budget threshold alert delivered late | Trace ownership, IaC change, allocation and budget alert |
| 56 | Tag normalization changes historical grouping | Trace ownership, IaC change, allocation and budget alert |
| 57 | Shared observability cost hidden from product teams | Trace ownership, IaC change, allocation and budget alert |
| 58 | Cost reduction harms DBRE RPO/RTO | Protect data correctness, performance and recovery objectives |
| 59 | Cost reduction violates service latency SLO | Trace ownership, IaC change, allocation and budget alert |
| 60 | Finance reconciliation differs from provider invoice | Verify provider source, billing basis, currency and export completeness |

## 9. Twelve production runbooks

### R01 — Cloud billing export freshness and integrity

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

### R02 — AWS CUR and cost allocation ownership

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

### R03 — Azure Cost Management exports and subscriptions

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

### R04 — GCP Billing BigQuery exports and labels

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

### R05 — Terraform/OpenTofu/Pulumi tagging enforcement

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

### R06 — CloudFormation/Bicep/Ansible tagging and drift

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

### R07 — Kubernetes shared-cost and namespace allocation

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

### R08 — Storage and network egress cost anomaly

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

### R09 — PostgreSQL/Aurora/RDS/MongoDB rightsizing safety

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

### R10 — Redis/Kafka/MSK/Elasticsearch/OpenSearch capacity

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

### R11 — Snowflake credits, warehouse and retention

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

### R12 — FinOps incident escalation, reconciliation and acceptance

**Trigger:** missing billing records, allocation failure, budget alert, unowned spend or cost-related reliability regression. **Owner:** FinOps analyst and service SRE; DBRE and security join for data, access or recovery risk. **Detect:** identify provider, billing scope, UTC usage period, cost basis, currency, export ID, source freshness and affected account. **Contain:** freeze automated cost optimization; do not destroy, downsize or change stateful production resources. **Diagnose:** reconcile immutable provider raw records to normalized ledger, IaC desired tags, observed resource inventory, historical baseline and invoice adjustments. **Recover:** repair read-only export ingestion or propose a separately approved reversible optimization; validate application latency, capacity, data integrity and RPO/RTO. **Close:** record cost delta, residual unallocated spend, owner, evidence, budget route and follow-up.

## 10. Troubleshooting

| Symptom | Cause to test | Correct response |
|---|---|---|
| Daily spend appears zero | missing export or delayed billing | UNKNOWN; never assume free usage |
| Double-counted cost | duplicate line IDs or overlapping export windows | deduplicate with provider key |
| Unallocated spend rises | tags absent, propagation or unsupported resource | preserve unallocated bucket |
| Cost dashboard differs from invoice | credits, basis, taxes, timing | reconcile like-for-like |
| Forecast spikes | seasonal workload or incomplete baseline | disclose uncertainty |
| Savings appears high | excluded shared costs or degraded SLO | validate real bill and service |
| Budget alert absent | stale feed or wrong owner route | verify end-to-end notification |
| Tag policy passes CI, fails cloud | propagation or manual drift | compare actual inventory |

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Billing architecture, IAM and data provenance | 15 |
| Provider exports, currency/basis and reconciliation | 20 |
| Tag governance, ownership and shared allocation | 20 |
| Offline labs, negative tests and cost anomaly logic | 20 |
| Reliability-aware optimization and DBRE validation | 15 |
| Runbooks, audit and independent acceptance | 10 |
| **Total** | **100** |

Pass >=85 and zero critical failures. Critical: wrong billing scope, double-counting, unverified currency conversion, destructive optimization, degraded customer SLO or DBRE RPO/RTO, or fabricated invoice evidence. **Offline lab success is not native billing or production acceptance.**

## 12. Handoff

Chapter 096 begins Part 20 — FinOps. **Next:** Chapter 097 — IaC Cost Allocation, Showback, Chargeback and Shared Platform Cost Models.
