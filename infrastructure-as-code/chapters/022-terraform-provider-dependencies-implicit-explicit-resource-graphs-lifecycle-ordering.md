# Chapter 022 — Terraform Provider Dependencies, Implicit and Explicit Resource Graphs and Lifecycle Ordering

**Part 05 — Providers and Dependencies** · **SRE/DBRE practical tutorial** · **No-cloud lab** · **Status: published; live acceptance pending**

## 1. Learning outcomes

Explain Terraform's dependency directed acyclic graph (DAG), infer edges from expression references, distinguish explicit depends_on from implicit dependencies, understand provider initialization and data-source reads, analyze lifecycle ordering and replacements, inspect terraform graph and plan JSON, write automated graph-policy tests, and design safe production sequencing and recovery.

## 2. Architecture and mental model

~~~text
HCL + module inputs + provider configurations
                 |
       static reference analysis
                 |
        dependency graph (DAG)
                 |
   provider setup + data reads + refresh
                 |
        plan actions and ordering
                 |
     approved apply / state changes
                 |
  post-apply verification and audit
~~~

Terraform graph nodes represent resource instances, data reads, provider configurations and other internal operations. Edges encode dependencies; Terraform can schedule independent nodes concurrently (subject to parallelism and provider behavior). **File order is not execution order.** Terraform graph is not a universal business-workflow engine: external readiness (DNS propagation, database recovery, application health) often requires separate probes, retries and orchestration.

A dependency A → B means B must wait for A to reach the relevant graph stage; graph direction may be drawn differently by tooling. In the lab's JSON policy, edges are explicitly modeled as \`{"before":"database","after":"application"}\` to remove ambiguity.

## 3. Implicit dependencies

Terraform infers an edge when an expression references another managed resource's attribute:

~~~hcl
resource "terraform_data" "database" {
  input = { name = "db" }
}
resource "terraform_data" "application" {
  input = { database_name = terraform_data.database.output.name }
}
~~~

The application depends on the database because of the reference. Prefer meaningful attribute references over manually forcing depends_on; this makes the contract visible and often allows more precise planning. A reference to a module output creates the required dependency chain through the output expression.

## 4. Explicit depends_on

~~~hcl
resource "terraform_data" "audit" {
  input      = { change_ticket = var.change_ticket }
  depends_on = [terraform_data.application]
}
~~~

Use depends_on only when a real dependency exists but cannot be represented by a direct expression, such as an IAM permission required before another operation. Overuse creates coarse edges, unnecessary unknown values and slower plans. At module level, depends_on may conservatively affect all child resources and data reads. It does not guarantee an external service has become healthy or replicated.

## 5. Data sources and ordering

Data sources read existing objects and normally run during planning when inputs are known and no dependency forces deferral. A data source depending on a changing resource can be deferred until apply, producing unknown outputs in the plan. This can cause surprising diffs or invalid for_each keys. Never assume a data source's result is a fresh readiness signal without checking provider semantics. Avoid cycles where resource A depends on a data source that indirectly depends on A.

## 6. Provider configuration dependencies

Provider configurations select credentials, region and endpoints. A resource depends on its selected provider configuration being available. Provider aliases control **which** configuration handles the resource; they are not an ordering mechanism. When configuring Kubernetes/Helm providers from newly created clusters, carefully separate bootstrap and workload phases if provider initialization or plan-time API access cannot succeed before the cluster exists.

## 7. Lifecycle meta-arguments and replacement

| Feature | Meaning | Caution |
|---|---|---|
| create_before_destroy | Request replacement ordering with new object first | May fail for unique names/quotas; behavior propagates to dependencies |
| prevent_destroy | Block destroy plans for protected resources | Removing configuration can remove the guard; not a backup |
| ignore_changes | Ignore configured remote changes during update planning | Can conceal important drift |
| replace_triggered_by | Replace when referenced managed object/attribute changes | Can cascade replacement |
| precondition / postcondition | Validate assumptions and outcomes | Not substitute for production health checks |

Lifecycle settings are statically constrained. Never set create_before_destroy without checking capacity, naming constraints, database replication and application compatibility. prevent_destroy is a guardrail, not a permanent protection boundary. Do not use ignore_changes to suppress security-relevant drift.

## 8. Graph analysis commands

~~~bash
terraform init -input=false
terraform validate
terraform graph > graph.dot
terraform plan -out=chapter022.tfplan
terraform show -json chapter022.tfplan > chapter022-plan.json
terraform state list
~~~

terraform graph outputs DOT; Graphviz is optional for rendering: \`dot -Tsvg graph.dot -o graph.svg\`. DOT edges may include provider/internal nodes; do not assume the visual graph maps one-to-one to the lab's simplified JSON fixture. Plan JSON \`resource_changes[].change.actions\` indicates create, update, delete, replacement (delete+create), read or no-op. Review actual addresses and unknown values before approval.

## 9. Hands-on lab: files and prerequisites

~~~text
labs/chapter-022/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  dependency-policy.json
  dependency-graph.json
  sample-plan.json
  graph_policy.py
  test_graph_policy.py
  run-preflight.sh
  .gitignore
~~~

Requires Terraform >=1.5 or compatible OpenTofu, Python >=3.9, Bash/WSL2 and optionally Graphviz. No cloud credentials, providers or charges; all managed objects are terraform_data.

### Lab A — Initialize and inspect

~~~bash
cd infrastructure-as-code/labs/chapter-022
terraform fmt -check -recursive
terraform init -input=false
terraform validate
terraform graph > graph.dot
terraform plan -out=chapter022.tfplan
terraform show -no-color chapter022.tfplan
terraform show -json chapter022.tfplan > chapter022-plan.json
terraform apply chapter022.tfplan
terraform state list
terraform output -json
terraform plan -detailed-exitcode
echo "plan_exit=$?"
~~~

Expected: foundation, database, application, monitoring and audit resources; second plan exits 0. Database explicitly references foundation; application references database; monitoring references application; audit depends_on monitoring. Confirm addresses and graph edges. The \`terraform_data\` records are not real databases or monitoring agents.

### Lab B — Policy and automated tests

~~~bash
python3 graph_policy.py dependency-graph.json sample-plan.json dependency-policy.json
python3 -m unittest -v test_graph_policy.py
bash run-preflight.sh
~~~

The Python policy validates a **simplified graph manifest** and **Terraform-style plan action fixture**; it does not parse DOT or infer the true Terraform graph. Its tests cover cycles, missing vertices, missing required edges, self-edges, duplicate edges, destructive actions, malformed actions, and unsafe policy settings. A passing fixture cannot prove real HCL graph or cloud safety. Independently inspect terraform graph and real plan JSON.

### Lab C — Inject dependency failures safely

1. In a disposable copy, remove the application reference to the database and replace it with a literal. Compare terraform graph and explain the lost implicit edge. Restore before applying.
2. Add a reverse depends_on from foundation to audit in the disposable copy; terraform validate/plan should identify a cycle. Restore the file.
3. Add an unnecessary depends_on to a read-only resource and compare the plan; explain deferred reads and over-constraining the graph.
4. In the Python graph fixture, add \`{"before":"audit","after":"foundation"}\` and run the policy. It must reject the cycle.
5. Change sample-plan.json actions to ["delete","create"] and verify fail-closed denial. Restore the fixture.

Do not inject graph cycles or destructive changes into a shared remote state or production repository branch.

### Lab D — Lifecycle and replacement tabletop

Discuss a PostgreSQL/RDS replacement: if create_before_destroy is set, can both instances coexist under naming, IP, quota and cost constraints? Is replication/cutover required? Does a backup restore prove RPO/RTO? Explain why Terraform ordering alone cannot guarantee zero downtime. For Elasticsearch data nodes, consider shard relocation and disk headroom; for EKS, node disruption budgets.

### Lab E — Cleanup

~~~bash
terraform plan -destroy
terraform destroy
terraform state list
git status --short
~~~

Expected empty state. Do not commit .terraform, state, plans, graph.svg or raw plan JSON if they contain sensitive infrastructure metadata.

## 10. Production SRE/DBRE scenarios

**RDS/Aurora:** Network/subnets/security groups → cluster → instances → application connections; require backups, KMS, PITR and cutover sequencing. A graph edge cannot ensure replication catch-up.

**PostgreSQL:** Role grants, extensions, parameter groups and replicas require operational ordering; validate WAL and failover health outside Terraform.

**Elasticsearch/OpenSearch:** Data-node replacement depends on storage and networking but also requires shard relocation, capacity and search-latency gates.

**EKS:** IAM/OIDC/VPC dependencies precede cluster/node-group and Kubernetes workloads. Provider initialization may require two-stage provisioning.

**AKS:** Resource group, identity, subnet and cluster dependencies; ensure correct subscription and staged node-pool changes.

**Redis:** Network and cluster dependencies plus replica sync and client failover checks; do not assume provider success means data is safe.

**Snowflake:** Roles/warehouses/grants have dependencies; protect grants and data access during changes.

**Kafka/MSK:** VPC/subnets/security groups → brokers → topic/client configs; replication, broker health and consumer lag require independent checks.

## 11. Troubleshooting

| Symptom | Cause | Response |
|---|---|---|
| Cycle detected | Reverse/recursive references | Inspect graph; break architectural cycle |
| Resource not found | Bad address/reference | Fix HCL reference |
| Data read deferred | Changing upstream dependency | Inspect plan unknowns and dependencies |
| Unexpected replacement | Immutable attribute/lifecycle | Stop, review change and recovery |
| Too many unknowns | Broad depends_on | Replace with precise references |
| Provider configure fails | Cluster/API not ready | Stage bootstrap and workload |
| Apply hangs | API/readiness timeout | Inspect provider logs and remote health |
| Parallel changes overload API | High parallelism/rate limits | Bound concurrency, retry safely |
| prevent_destroy fails | Protected resource replacement | Review migration; do not bypass casually |
| create_before_destroy fails | Quota/name collision | Plan capacity and cutover |
| Drift hidden | Overbroad ignore_changes | Remove masking and reconcile |
| State lock held | Concurrent apply | Coordinate; never blindly force-unlock |

## 12. Operational runbooks

**Graph change review:** pin CLI/provider versions → fmt/validate → inspect graph → compare plan addresses/actions → check data reads and unknowns → SRE/DBRE approval → apply reviewed plan → verify health/SLOs.

**Cycle incident:** stop pipeline → identify shortest cycle and implicit/explicit edges → remove inappropriate edge or split bootstrap stages → validate → replan → review.

**Replacement/ordering incident:** halt → preserve data and state → inspect lifecycle, quotas, backups and cutover plan → remediate in staging → obtain production approval.

**Partial apply:** prevent concurrent writers → inspect actual cloud state and Terraform state → prioritize service/data recovery → reconcile with fresh approved plan → RCA/COA.

**Provider bootstrap:** verify identity and endpoint → stage cluster creation separately → configure workload provider with known endpoint → verify access and rollout.

## 13. Acceptance rubric (100 points)

| Dimension | Points |
|---|---:|
| DAG, implicit/explicit dependencies | 20 |
| Data sources/provider sequencing | 15 |
| Lifecycle/replacement reasoning | 20 |
| No-cloud lab and plan evidence | 15 |
| Automated graph policy and negative tests | 20 |
| Runbooks, cleanup and audit | 10 |

Pass 85+ and zero critical violations. Capture sanitized CLI version, graph screenshot/DOT, plan action review, test results, idempotence exit code and cleanup. **Tests are authored, not claimed executed.**

## 14. Knowledge check

Why does HCL file order not define apply order? When is depends_on necessary? What causes deferred data reads? Why can a module-level depends_on be costly? What does create_before_destroy actually guarantee? Why is prevent_destroy not a backup? How can ignore_changes mask security drift? Why does a provider alias not imply dependency ordering? How do you investigate cycles? What external readiness evidence is required before DB cutover?

**Next:** Chapter 023 — Terraform Data Sources, External Dependencies and Cross-Module Data Flow.
