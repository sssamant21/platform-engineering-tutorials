# Chapter 011 — Terraform Configuration Language Fundamentals: Blocks, Arguments, Expressions and HCL Syntax

Part 03 — Terraform Language and Workflow | SRE / DBRE / Platform Engineering | Local-only, no cloud cost

## Learning objectives
Understand HCL blocks and labels, arguments, literal and computed expressions, variable types, locals, outputs, resource references, dependency inference, conditional expressions, comprehensions, formatting and validation. Practice failure injection and operational change reviews.

## 1. Architecture
Git root module → versions.tf (engine contract) + variables.tf (typed inputs) + main.tf (locals/resources) + outputs.tf (interfaces) → fmt → init → validate → plan → approved apply → verify → cleanup.

HCL is declarative: desired state is expressed in blocks, and Terraform computes a dependency graph and plan. Filenames in the same root directory do not determine resource creation order. A reference to another resource's output creates an implicit dependency; explicit depends_on is for dependencies that cannot be inferred.

## 2. Blocks, arguments and labels
~~~hcl
resource "terraform_data" "example" {
  input = {
    environment = "staging"
    owner       = "platform-sre"
  }
}
~~~
The resource block has two labels (resource type and local name); input is an argument with an expression as its value. Terraform, locals and output blocks have different label schemas. Nested blocks are not interchangeable with object-valued arguments. Comments can use #, // or /* ... */.

| Block | Role |
|---|---|
| terraform | Engine constraints, provider requirements, backend |
| provider | Provider instance configuration |
| resource | Managed resource lifecycle |
| data | Read-only provider data lookup |
| variable | Typed module input |
| locals | Reusable named expressions |
| output | Module output contract |
| module | Invoke reusable configuration |
| moved/import/check | Refactoring, adoption and assertions |

## 3. Expressions and types
HCL values include strings, numbers, booleans, null, lists/tuples, maps/objects and sets. Explicit input types prevent accidental coercion.

~~~hcl
locals {
  env        = "staging"
  replicas   = 3
  enabled    = true
  zones      = ["A", "B"]
  tags       = { owner = "dbre", service = "api" }
  dns        = "${local.env}.internal"
  tier       = local.env == "prod" ? "critical" : "standard"
  zone_index = { for z in local.zones : lower(z) => "enabled" }
}
~~~
Conditional branches must produce compatible types. Unknown values may remain unresolved until apply. null is not the string "null". Resource references define graph edges; count indices and for_each keys affect resource addresses. Prefer stable for_each keys for long-lived infrastructure.

## 4. Style, scope and safe operations
Run terraform fmt -check and terraform validate after init. These detect formatting and structural errors but do not prove safe infrastructure changes. Use short-lived CI credentials, remote encrypted state and environment-specific identities in production. Avoid sensitive values in outputs, Git and terminal transcripts; marking an output sensitive does not remove it from state.

## 5. Lab A — Typed configuration and resource references
Prerequisites: Terraform >=1.5 or approved compatible OpenTofu, Python 3.9+, Git. Use the supplied files in labs/chapter-011. The terraform_data resource is built into Terraform/OpenTofu; no cloud credentials or external provider downloads required.

~~~bash
cd infrastructure-as-code/labs/chapter-011
terraform fmt -check
terraform init
terraform validate
terraform plan -out=chapter011.tfplan
terraform show -no-color chapter011.tfplan
terraform apply chapter011.tfplan
terraform output -json
terraform plan -detailed-exitcode
~~~
Expected: two local resources and derived metadata outputs. After apply, the second plan must exit 0 (no changes); exit 2 means changes proposed. Use tofu consistently instead of terraform if using OpenTofu.

## 6. Lab B — Interactive expressions
Run terraform console in the initialized root. Evaluate:
~~~hcl
upper("staging")
length(["a", "b"])
join("-", ["platform", "dev"])
{ for z in ["a", "b"] : z => upper(z) }
"prod" == "prod" ? "critical" : "standard"
~~~
Expected values include STAGING, 2, platform-dev, a/b mapped to A/B, and critical. Exit the console using exit.

## 7. Lab C — Negative testing and recovery
Copy the lab into a disposable directory before introducing faults:
1. Delete an equals sign from a variable argument: validate must fail.
2. Reference local.unknown: validate must fail.
3. Pass -var='environment=production': input validation must reject it.
4. Pass -var='replicas=-1': input validation must reject it.
5. Duplicate variable "environment": validation must fail.
6. Rename a resource local name without a moved block: inspect plan for address churn.

Restore files, rerun fmt/validate and confirm a no-change plan. Do not run negative drills against shared or production state.

## 8. Lab D — Automated HCL source policy
~~~bash
python3 hcl_policy.py .
python3 -m unittest -v test_hcl_policy.py
~~~
The policy checks required files, required_version, typed variable declarations and obvious hard-coded credential assignments. It is a teaching tool, not a full HCL parser, credential scanner or replacement for terraform validate. Tests cover missing files, untyped variables, credentials and missing version constraints.

## 9. Lab E — Cleanup
~~~bash
terraform destroy
terraform state list
~~~
Expected: empty managed state. Never commit state, plan files, .terraform, credentials or secret tfvars.

## 10. Production SRE/DBRE scenarios
**RDS/Aurora:** Conditional expression selects a storage class; an incorrect environment default could cause a performance regression or replacement. Require DBRE plan review, backups and PITR.

**Elasticsearch/OpenSearch:** Locals compute disk throughput and IOPS; manual incident hotfixes cause drift. Preserve mitigation and reconcile after SLO stabilization.

**EKS:** for_each key changes can replace node group resources. Use supported moved blocks and staged migrations, verify PDBs and cluster health.

**AKS:** An HCL environment label does not change Azure subscription or identity. Verify subscription, backend and role separately.

**PostgreSQL:** Untyped parameter inputs can hide incorrect values; use validation, database checks and a rollback plan.

**Redis:** A conditional replica count could disable HA. Validate production minimums and failover behavior.

**Snowflake:** A for expression creates grants; key changes can cause revocation/recreation. Inspect plan and require security owner approval.

**Kafka/MSK:** count index churn after list reordering can replace broker resources. Prefer stable keys and controlled migration.

## 11. Troubleshooting
| Symptom | Likely cause | Response |
|---|---|---|
| Invalid block definition | Braces or labels wrong | fmt/validate |
| Unsupported argument | Wrong schema or provider version | Check provider documentation |
| Undeclared local/variable | Incorrect reference | Fix name and scope |
| Invalid variable value | Type or validation mismatch | Correct input |
| Inconsistent conditional types | Branch type mismatch | Normalize types |
| Duplicate declaration | Repeated block labels | Remove duplicate |
| Invalid for expression | Bad syntax or duplicate keys | Stabilize keys |
| Unexpected replacement | Changed address or immutable property | Stop and review |
| Sensitive data in state | Unsafe output/attribute | Contain and rotate if exposed |

## 12. Operational runbooks
**HCL review:** identify environment and owner → fmt → init → validate → policy/tests → scoped plan → assess delete/replace → DBRE approval where needed → apply → verify SLO and cost.

**Unexpected destructive plan:** halt pipeline → verify commit, backend, identity and versions → inspect resource address changes and drift → involve owner → validate restore path → replan.

**CI syntax failure:** reproduce under pinned CLI → inspect error → minimal correction → fmt/validate/tests → attach PR evidence.

**Incident drift:** document manual hotfix → stabilize service → compare declared and actual state → reconcile in Git → close RCA/COA.

## 13. Security and FinOps
Type and validate inputs; pin providers and CI tools; use separate prod identities, encrypted state, owner/cost tags, peer-reviewed plans, cost estimates and recovery checks. Do not interpret a passing validate as production readiness.

## 14. Acceptance checklist
- [ ] Typed variables and validation constraints verified
- [ ] fmt, init, validate, plan and apply succeed
- [ ] Second plan exits 0
- [ ] Console expressions evaluated
- [ ] Policy tests pass and negative cases fail
- [ ] No state, plans or credentials committed
- [ ] Destroy leaves no local resources
- [ ] Production scenarios include owner and rollback assessment

## 15. Knowledge check
Explain block vs argument; reference-driven dependency; variable type validation; null vs string "null"; stable for_each keys; unknown plan values; why validate is not approval; how to handle destructive plans; sensitive state exposure; how Git revert differs from database recovery.

**Next:** Chapter 012 — Terraform Resource Blocks, Data Sources, Meta-Arguments and Dependency Graph.
