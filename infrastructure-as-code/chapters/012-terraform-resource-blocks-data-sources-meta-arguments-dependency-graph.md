# Chapter 012 — Terraform Resource Blocks, Data Sources, Meta-Arguments and Dependency Graph

**Part 03 — Terraform Language and Workflow** · **Audience:** SRE / DBRE / Platform Engineering · **Cost:** $0 for core lab · **Status:** Published; live learner execution pending

## Learning outcomes
Explain managed resources vs data sources; provider/resource addressing; implicit and explicit dependencies; graph planning and destroy ordering; lifecycle, count, for_each, depends_on and provider meta-arguments; safely review replacement, drift and graph cycles. Execute a no-cloud Terraform/OpenTofu lab and automated policy tests.

## 1. Architecture: desired state and dependency graph
Terraform loads all .tf files in a root module, evaluates references, builds a dependency graph, compares state and configuration, and proposes operations. A plan is not a command execution trace: unknown values and provider behavior may affect the final operation.

~~~text
root module
  variables/locals
       |
 terraform_data.seed (managed resource)
       |
 terraform_data.service["api"]  terraform_data.service["worker"]
       |                              |
       +-----------+------------------+
                   |
          terraform_data.audit
                   |
                 output
~~~

An expression reference such as terraform_data.seed.output establishes an **implicit dependency**. Explicit depends_on is justified when a real ordering requirement cannot be expressed through data flow. Overuse makes plans conservative and reduces concurrency.

## 2. Resource and data blocks
A resource block declares a managed object and has a resource type and local name:

~~~hcl
resource "terraform_data" "example" {
  input = { owner = "platform-sre" }
}
~~~

A data block reads information through a provider, generally without managing its lifecycle:

~~~hcl
data "aws_caller_identity" "current" {}
~~~

The AWS example is illustrative only: it requires the AWS provider and suitable credentials. Data sources can be evaluated during plan or deferred until apply when their inputs depend on values not yet known. Data lookups can fail due to permissions, missing objects, network outages, or API throttling. Reading a data source does not imply Terraform owns that object.

Resource address examples: terraform_data.seed, terraform_data.service["api"], module.network.aws_subnet.private["a"]. Addresses identify state bindings. Changing count indices or for_each keys can cause replacements even when resource settings are similar.

## 3. Meta-arguments and operational tradeoffs
| Meta-argument | Purpose | Failure mode / safety control |
|---|---|---|
| count | Create indexed instances | List reordering or index shift causes churn |
| for_each | Create instances keyed by set/map | Key rename changes addresses; prefer stable keys |
| depends_on | Explicit dependency edge | Unnecessary broad edges and unknown values |
| lifecycle.create_before_destroy | Replacement ordering | Quota, name uniqueness, cost spikes |
| lifecycle.prevent_destroy | Block planned destruction | Does not prevent out-of-band deletion or deletion after removing block |
| lifecycle.ignore_changes | Ignore configured attribute drift | May conceal emergency/manual drift |
| lifecycle.replace_triggered_by | Force replacement on tracked change | Cascading replacement risk |
| provider | Select configured provider alias | Wrong cloud account/subscription |
| providers (module) | Pass provider configurations | Identity isolation errors |

**Important:** lifecycle settings are processed early; only literal values are allowed in lifecycle rules. Terraform/OpenTofu behavior and available meta-arguments depend on versions; test against the approved CLI. A provider alias does not automatically isolate backend or permissions.

## 4. Implicit, explicit and destroy dependencies
Resource B referencing resource A normally causes A to be created first and B to be destroyed first. The graph is not necessarily linear; independent resources may run concurrently. Use terraform graph to emit DOT for review (Graphviz optional). Avoid building brittle ordering with null_resource/local-exec sleeps or arbitrary time delays.

A dependency cycle such as A → B → A is invalid. Diagnose by examining mutual references, explicit depends_on, module outputs and provider configuration. Break the cycle through clearer resource boundaries rather than using -target as a permanent workaround.

## 5. Lab prerequisites
Terraform >=1.5 or an approved compatible OpenTofu, Python 3.9+, Git. Run on Linux, macOS or Windows/WSL2. No cloud account, credentials, external provider or charges required. Use one CLI consistently and keep local state disposable.

## 6. Lab A — Resource graph, stable keys and output
Inspect labs/chapter-012/main.tf, variables.tf and outputs.tf. The lab uses terraform_data (built-in provider) with a seed resource, keyed services and an audit resource that explicitly depends on all services.

~~~bash
cd infrastructure-as-code/labs/chapter-012
terraform fmt -check
terraform init
terraform validate
terraform plan -out=chapter012.tfplan
terraform show -no-color chapter012.tfplan
terraform apply chapter012.tfplan
terraform output -json
terraform state list
terraform plan -detailed-exitcode
terraform graph > graph.dot
~~~

Expected: seed, two service instances and audit. The second plan exits 0 (no change); exit 2 means changes proposed. DOT graph output is textual and can be rendered with dot -Tsvg graph.dot -o graph.svg if Graphviz is installed. The DOT file is an inspection artifact, not proof of runtime ordering.

## 7. Lab B — Count vs for_each and change risk
A count example is provided as commented teaching material in the tutorial; the canonical lab uses for_each with stable map keys.

~~~hcl
# Illustrative only: do not add alongside the canonical resources.
resource "terraform_data" "counted" {
  count = length(var.services)
  input = keys(var.services)[count.index]
}
~~~

Change var.services by adding a new stable key, then inspect the plan. Existing for_each keys should remain bound to the same addresses. Rename an existing key in a disposable copy and inspect deletion/creation; do not apply destructive changes to shared state. If a key rename is intentional, use a reviewed moved block when supported.

## 8. Lab C — Lifecycle safeguards and failure injection
The audit resource uses prevent_destroy = true. After applying, try terraform destroy -plan? Instead use the safe preview command:

~~~bash
terraform plan -destroy
~~~

Expected: Terraform refuses a plan that would destroy the protected audit resource. **For cleanup**, remove the lifecycle prevent_destroy setting from the audit resource, review the diff, and then run terraform destroy. Never use state rm or force-unlock as a casual workaround. Production prevent_destroy does not replace backups, IAM, deletion protection or change approvals.

Optional: modify the seed input and observe replace_triggered_by behavior only in a disposable copy if you add that lifecycle rule. Check for unexpected cascades.

## 9. Lab D — Automated graph policy checks
The supplied graph_policy.py validates a fictional dependency inventory (graph.json), detecting duplicate IDs, missing references, cycles, prohibited prod auto-apply and production DB destroy without DBRE approval. It is not a Terraform graph parser and does not replace plan analysis.

~~~bash
python3 graph_policy.py graph.json
python3 -m unittest -v test_graph_policy.py
~~~

Expected: PASS and all unit tests pass. Negative tests cover cycles, missing dependencies, duplicate IDs, destructive DB changes and unsafe prod automation.

## 10. Lab E — Cleanup and acceptance
Remove the prevent_destroy line from the local audit resource after reviewing the lab-only change. Then:

~~~bash
terraform plan -destroy
terraform destroy
terraform state list
~~~

Expected: empty managed state. Do not commit state, plan files, graph artifacts containing sensitive names, .terraform, or credentials.

## 11. Production SRE/DBRE scenarios
**RDS/Aurora:** create_before_destroy may not work for a uniquely named DB and could trigger expensive or destructive replacement. Stop, validate snapshot/PITR and DBRE cutover plan.

**Elasticsearch/OpenSearch:** ignore_changes on disk throughput hides emergency IOPS remediation. Track drift explicitly and reconcile only after service SLOs recover.

**EKS:** for_each key rename can replace node groups; check PDBs, AZ capacity and safe migration before approving.

**AKS:** provider alias targeting a different subscription can manage the wrong cluster. Verify tenant/subscription, backend and workload identity.

**PostgreSQL:** dependency graph does not guarantee app schema readiness. Use controlled migrations and health gates rather than arbitrary sleeps.

**Redis:** count index changes can churn replicas and affect failover; prefer stable instance identity and maintenance windows.

**Snowflake:** data source lookup of an existing role does not manage grants. Review access and least-privilege changes separately.

**Kafka/MSK:** destroy ordering of security groups, subnets and brokers affects availability; preserve quorum and review planned changes.

## 12. Troubleshooting matrix
| Symptom | Cause | Safe response |
|---|---|---|
| Cycle: ... | Circular references/depends_on | Break mutual edge; redesign boundaries |
| Invalid for_each argument | Unknown keys or wrong collection type | Use known stable map/set keys |
| Reference to undeclared resource | Typo or module scope | Correct address and module output |
| Instance key missing | Renamed/deleted key | Review moved block/state migration |
| prevent_destroy blocks destroy | Lifecycle safeguard | Owner-approved config change before cleanup |
| Unexpected replacement | Immutable field/key/index drift | Halt and inspect plan |
| Data source not found | API permission/missing object | Check credentials, scope and resource existence |
| Excessive unknown values | Overbroad depends_on | Narrow dependencies |
| Provider alias mismatch | Wrong identity or account | Validate subscription/account/backend |
| Graph command fails | Configuration not initialized | init/validate and retry |

## 13. Operational runbooks
**Dependency review:** identify root module and owner → verify provider/CLI lock → terraform validate → terraform graph → inspect plan addresses, create/delete/replace → review DBRE impact → approve → apply → monitor.

**Cycle recovery:** preserve error → locate references and explicit edges → break dependency in code → validate/plan → document change; avoid -target as routine repair.

**Destructive DB plan:** stop CI → verify identity/backend → compare state and resource address changes → confirm backup/PITR → owner+DBRE sign-off → schedule cutover or reject.

**Emergency drift:** record manual incident changes → stabilize SLO → reconcile HCL and state under change control → test → RCA/COA.

**State lock contention:** identify legitimate writer → wait or coordinate abort → never force-unlock without evidence and authorization.

## 14. Security, FinOps and acceptance
- [ ] Resource vs data-source semantics explained.
- [ ] for_each addresses and dependency graph reviewed.
- [ ] fmt/init/validate/plan/apply and no-change plan pass.
- [ ] prevent_destroy negative drill blocks deletion.
- [ ] Python policy tests pass and negative tests fail closed.
- [ ] Production replacements have owner/DBRE approval, recovery and cost assessment.
- [ ] Cleanup completed; state and plan files not committed.
- [ ] Lab evidence captured without secrets.

## 15. Knowledge check
Why does a data source not own its target? When does Terraform defer a data read? How do references create edges? When is depends_on needed? Why do count indices churn? How can moved blocks help? What are prevent_destroy limitations? Why can create_before_destroy fail for databases? What is a graph cycle? Why does a passing graph review not replace an approved plan?

**Next:** Chapter 013 — Terraform Plan, Apply, Refresh, Destroy and Execution Lifecycle.
