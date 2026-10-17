# Chapter 017 — Terraform Local Values, Expressions, Functions and Dynamic Configuration

**Part 04 — Variables and Expressions** · **Audience:** SRE / DBRE / Platform Engineering · **Core lab:** $0, built-in Terraform provider · **Status:** Published; learner execution evidence pending

## Learning objectives

Build maintainable local values and expressions; select functions for strings, collections, types and networking; distinguish unknown values from null; design stable for_each maps and dynamic nested blocks; avoid leaking secrets; verify invariants with executable no-cloud labs and automated policy tests; apply production change controls.

## 1. Architecture: inputs → normalized locals → graph

~~~text
environment tfvars + typed variable declarations
                     |
        validation and expression evaluation
                     |
   locals: normalized names, tags, service maps
                     |
   stable for_each keys -> terraform_data resources
                     |
  dependency graph -> plan -> policy -> approval
                     |
       apply -> state inspection -> verify
~~~

A \`locals\` block defines named expressions, not mutable variables or an execution step. Terraform evaluates expressions as needed, and references create graph dependencies. Locals improve reuse and readability, but excessive layers can hide intent. Keep business rules near their owning module, with clear names and tests.

## 2. Expression foundations

~~~hcl
locals {
  prefix        = lower(trimspace(var.service))
  environment   = var.environment
  resource_name = format("%s-%s", local.prefix, local.environment)
  is_production = var.environment == "prod"
  replicas      = local.is_production ? max(var.replicas, 3) : var.replicas
}
~~~

**References:** \`var.service\`, \`local.prefix\`, \`terraform_data.service["api"].output\`, \`module.network.subnet_ids\`. **Conditionals:** \`condition ? true_value : false_value\`; Terraform must unify branch types. **For expressions:** \`[for x in xs : ...]\` or \`{for k, v in map : k => ...}\`, with optional \`if\` filters. **Splat:** \`resource.example[*].id\` for appropriate collections; prefer explicit keyed access for for_each maps.

**Null and unknown:** \`null\` means an intentionally absent value, while an unknown value is deferred until plan/apply resolves it. \`try\` catches dynamic expression errors, not arbitrary API failures. \`can\` is helpful for validations. \`coalesce\` selects the first non-null/nonempty string candidate; \`lookup\` retrieves map entries with a default. Do not use these functions to conceal a missing production configuration.

## 3. Function selection

| Category | Functions | Operational use |
|---|---|---|
| Strings | lower, upper, trimspace, replace, format, regex | Normalize naming and tags |
| Numeric | min, max, ceil, floor | Bounds and capacity calculations |
| Collections | keys, values, merge, concat, distinct, sort, flatten, setunion | Deterministic maps and inventory |
| Type/guard | tostring, tonumber, try, can, coalesce, lookup | Explicit conversion and optional inputs |
| Encoding | jsonencode, jsondecode, yamlencode, yamldecode | Generate configuration; protect sensitive content |
| Files | file, templatefile, fileset | Controlled static templates and assets |
| Network | cidrsubnet, cidrhost, cidrnetmask | Subnet design; verify overlap externally |
| Time/identity | timestamp, uuid, plantimestamp | Avoid volatile plan churn from unstable expressions |

Functions are not general-purpose side-effecting scripts. Do not use \`timestamp()\` or \`uuid()\` directly in stable resource attributes if you need idempotent plans. Use \`terraform console\` to evaluate expressions interactively without applying infrastructure.

## 4. Dynamic blocks and for_each

A \`dynamic\` block generates **nested blocks supported by a resource schema**, not arbitrary top-level resources or meta-arguments. For example, a cloud security-group resource can use \`dynamic "ingress"\` for provider-defined ingress blocks. The offline lab intentionally uses **for_each on terraform_data**, because terraform_data has no repeatable provider-specific nested block to generate.

~~~hcl
# Illustrative only; requires a provider with ingress block support.
dynamic "ingress" {
  for_each = var.ingress_rules
  content {
    from_port   = ingress.value.port
    to_port     = ingress.value.port
    protocol    = "tcp"
    cidr_blocks = ingress.value.cidrs
  }
}
~~~

A dynamic block does not justify wide-open production ingress. Validate CIDRs and ports, verify effective security groups and enforce policy-as-code. For resources, prefer \`for_each\` with stable map keys; count indices can shift and trigger churn. \`for_each\` keys must be known before apply and cannot be sensitive.

## 5. Lab files and prerequisites

~~~text
labs/chapter-017/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  expression-policy.json
  expression_policy.py
  test_expression_policy.py
  run-preflight.sh
  .gitignore
~~~

Terraform >=1.5 or compatible OpenTofu, Python 3.9+, Git. No external providers, cloud credentials or charges. Bash examples work on Linux, macOS and Windows WSL2; PowerShell users can run commands individually.

## 6. Lab A — Locals, comprehensions and stable addresses

Review the supplied HCL: typed service map, normalized labels, merged tags, production capacity calculation and a for_each collection of \`terraform_data\` resources. A dependent audit record captures the sorted service keys.

~~~bash
cd infrastructure-as-code/labs/chapter-017
terraform fmt -check -recursive
terraform init -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter017.tfplan
terraform show -no-color chapter017.tfplan
terraform apply chapter017.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected: one resource per service key and an audit record; a second plan exits 0. Resource addresses should remain stable across unrelated map-value changes.

## 7. Lab B — Explore expressions in terraform console

~~~bash
terraform console -var-file=environments/dev.tfvars
~~~

Evaluate the following expressions one by one:

~~~hcl
lower(trimspace("  PATIENT-API  "))
merge({ owner = "sre" }, { environment = "dev" })
sort(keys(var.services))
[for k, v in var.services : upper(k)]
{ for k, v in var.services : k => v.replicas if v.enabled }
cidrsubnet("10.20.0.0/16", 8, 1)
try(var.services["missing"].replicas, 0)
jsonencode({ environment = var.environment, services = keys(var.services) })
~~~

Exit with \`exit\`. Compare the results with the HCL locals and explain the type and ordering of each expression.

## 8. Lab C — Environment-specific and negative drills

~~~bash
terraform plan -var-file=environments/prod.tfvars
terraform plan -var='environment=production'
terraform plan -var='service=INVALID_NAME'
terraform plan -var='services={}'
~~~

The last three commands must fail validation. In a disposable copy, rename a service map key and inspect address replacement; restore the original key without applying the destructive change. Never run this drill against production state.

## 9. Lab D — Automated expression and capacity policy

The supplied Python standard-library validator reads a JSON policy and a **JSON representation of the intended input contract**; it does not parse arbitrary HCL. This is a preflight illustration, not a substitute for evaluating Terraform expressions or reading real cloud state. Tests exercise deterministic normalization, naming, duplicate canonical names, invalid environments, production capacity, owner and allowed CIDR ranges.

~~~bash
python3 expression_policy.py environments/dev.json expression-policy.json
python3 expression_policy.py environments/prod.json expression-policy.json
python3 -m unittest -v test_expression_policy.py
bash run-preflight.sh
~~~

Fail-closed production controls: minimum 3 replicas per enabled service, explicit owner, nonempty service set, allowed environment and private IPv4 CIDR. In production, complement this with Terraform plan JSON, IAM/backend checks and real network-policy review.

## 10. Lab E — Cleanup

~~~bash
terraform plan -destroy
terraform destroy
terraform state list
git status --short
~~~

Expected: empty state. Never commit state, saved plans, credentials or JSON plans containing sensitive data.

## 11. Production SRE/DBRE scenarios

**RDS/Aurora:** Compute storage/IOPS from bounded inputs, not volatile timestamps; verify actual provider limits, backup/PITR and replacement risk before apply.

**PostgreSQL:** Generate instance parameter maps deterministically. Dynamic defaults must not silently reduce max connections, WAL or replication safety.

**Elasticsearch/OpenSearch:** Normalize shard/volume tags and calculate capacity with real ingest/query measurements; do not encode a universal IOPS default that masks storage saturation.

**EKS:** for_each over node pools with stable keys, validate min/max and AZ placement; review PDBs and surge cost.

**AKS:** Generate consistent resource naming but verify subscription, tenant and state backend separately.

**Redis:** Use bounded capacity and replica settings; ensure failover topology and memory headroom before changes.

**Snowflake:** Map warehouses to owners and cost centers; enforce size/auto-suspend policy and least-privilege role grants.

**Kafka/MSK:** Generate broker/subnet mapping deterministically and verify broker/AZ constraints, replication and client connectivity.

## 12. Troubleshooting matrix

| Symptom | Cause | Safe response |
|---|---|---|
| Invalid function argument | Wrong type/format | Inspect type and inputs |
| Invalid index | Missing map key | Validate or use explicit lookup |
| Invalid for_each argument | Unknown/sensitive keys | Derive stable nonsensitive keys |
| Duplicate object key | Normalization collision | Reject canonical-name duplicates |
| Unexpected resource replacement | Key renamed or unstable expression | Halt, inspect plan, use moved block if appropriate |
| Dynamic block rejected | Provider schema has no nested block | Use supported block/resource structure |
| Null output | Optional value missing | Validate required production fields |
| Console expression unknown | Apply-time value | Inspect plan dependencies |
| Capacity check fails | Prod below minimum | Correct inputs, get DBRE approval |
| Network CIDR rejected | Invalid or public range | Correct approved network design |

## 13. Operational runbooks

**Expression change review:** confirm inputs and versions → console-check representative expressions → fmt/validate → policy tests → plan JSON → inspect key stability and replacement → SRE/DBRE approval → apply → SLO/cost verification.

**Unexpected replacement:** stop apply → compare for_each keys and normalized names → inspect moved-block migration → validate state/backend → regenerate approved plan.

**Capacity incident:** preserve service mitigation → compare intended vs observed capacity → fix local expressions and limits → test staging → approve production rollout → monitor.

**Security exposure:** halt deployment → inspect generated CIDRs, grants and templates → contain access → rotate credentials if exposed → reconcile and audit.

## 14. Acceptance rubric (100 points)

| Area | Points |
|---|---:|
| Locals, functions and type reasoning | 20 |
| Stable keyed resources and deterministic plan | 20 |
| Console and negative exercises | 15 |
| Automated policy and unit tests | 20 |
| Production runbooks and risk review | 15 |
| Cleanup, secrets and evidence | 10 |

Pass at 85+ without critical failures. Publication is not proof of execution; collect sanitized CLI versions, unit-test output, plan exit codes and cleanup evidence.

## 15. Knowledge check

Why use locals instead of duplicating expressions? What is the difference between null and unknown? When should you use try vs can? Why sort map keys? Why do volatile functions cause perpetual changes? What can dynamic blocks generate? Why must for_each keys be known? What happens when normalized keys collide? Why is a passing JSON policy not sufficient for production security? How do you prove idempotence?

**Next:** Chapter 018 — Terraform Collections, for Expressions, Splat Expressions and Advanced Data Transformations.
