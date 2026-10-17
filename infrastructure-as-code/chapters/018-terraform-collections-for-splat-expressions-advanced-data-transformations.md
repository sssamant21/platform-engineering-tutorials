# Chapter 018 — Terraform Collections, for Expressions, Splat Expressions and Advanced Data Transformations

**Part 04 — Variables and Expressions** · **Audience:** SRE/DBRE, Platform Engineers · **Prerequisite:** Chapters 011–017 · **Core lab:** $0, no cloud credentials · **Publication:** authored; learner execution evidence pending.

## Learning outcomes

1. Distinguish list, tuple, set, map and object semantics, including ordering, conversion and type unification.
2. Construct list and object for expressions with filters, grouped results and stable keys.
3. Apply splat expressions correctly and know why for_each maps require explicit for expressions.
4. Normalize nested configuration using flatten, merge, distinct, sort, keys, values, zipmap, setproduct and lookup.
5. Produce stable, reviewable for_each resource addresses without index churn.
6. Detect invalid/duplicate identifiers, CIDR overlap, missing ownership, unbounded production capacity and risky changes before apply.
7. Execute no-cloud Terraform and Python automated tests; collect sanitized SRE/DBRE change evidence.

## 1. Architecture

~~~text
environment tfvars + typed nested object inputs
                    |
          input validation / types
                    |
      for expressions / flatten / merge
                    |
    canonical keyed service × zone matrix
                    |
       terraform_data[stable keys]
                    |
        plan JSON + preflight policy
                    |
      approved apply -> state -> audit
~~~

Transformation code is infrastructure logic. A wrong key can cause replacement; a wrong filter can silently omit a workload. The result must be deterministic, reviewed and independently validated.

## 2. Collection semantics and conversions

| Type | Meaning | Operational implication |
|---|---|---|
| list(T) | Ordered homogeneous values | Index positions matter |
| tuple([T...]) | Ordered, possibly heterogeneous | Explicit shape |
| set(T) | Unordered unique elements | No stable index; sorting needed for presentation |
| map(T) | String-keyed homogeneous values | Stable keys for for_each |
| object({...}) | Named attributes with declared types | Best for nested input contracts |

Terraform automatically converts compatible types when a declared constraint requires it. Converting a set to a list does not promise original order. Use sort(tolist(...)) for deterministic strings. Avoid implicit type conversion in production-sensitive policy logic.

~~~hcl
locals {
  zones       = sort(tolist(toset(var.zones)))
  identifiers = distinct(["api", "worker", "api"])
  owner_tags  = merge(var.tags, { owner = var.owner, environment = var.environment })
}
~~~

## 3. for expressions

List transformation:

~~~hcl
[for name, service in var.services : upper(name) if service.enabled]
~~~

Object transformation:

~~~hcl
{ for name, service in var.services : name => service.replicas if service.enabled }
~~~

Grouped object values use the ellipsis grouping operator, for example:

~~~hcl
{ for name, service in var.services : service.tier => name... }
~~~

Grouping is intentional: ordinary object for expressions fail on duplicate keys. Never silently overwrite duplicate resource keys during normalization.

## 4. Splat expressions: capabilities and limits

Splat syntax such as aws_instance.worker[*].id is shorthand for projecting over a list, tuple or set-like sequence. It does **not** operate directly over a for_each resource map; instead write:

~~~hcl
[for key, item in terraform_data.workload : item.output.name]
~~~

A single non-null object can be treated as a one-element tuple by a splat, while null becomes an empty tuple; this is occasionally useful for optional dynamic nested blocks, but can obscure types. Prefer explicit conditional expressions for readability. Never assume a splat provides a stable ordering of set elements.

## 5. Nested data transformation

The lab defines a map of services and a list of zones. Each enabled service is expanded across every zone, then flattened into a list and re-keyed into a map. A key such as api@a is stable even if another service is added.

~~~hcl
locals {
  enabled_services = {
    for name, svc in var.services : name => svc
    if svc.enabled
  }
  workload_rows = flatten([
    for name, svc in local.enabled_services : [
      for zone in sort(distinct(var.zones)) : {
        key         = format("%s@%s", name, zone)
        service     = name
        zone        = zone
        tier        = svc.tier
        replicas    = svc.replicas
      }
    ]
  ])
  workloads = { for row in local.workload_rows : row.key => row }
}
~~~

The Terraform plan is the authority for resource actions; the Python policy is an independent guard for a simplified JSON representation of the same input contract, not an HCL parser.

## 6. Advanced transformation toolbox

- **flatten:** reduce nested lists by one or more levels; does not flatten values nested in maps.
- **merge:** merge maps/objects, later arguments win; review precedence to avoid accidentally overriding mandatory owner/environment tags.
- **distinct / toset:** remove duplicates; retain a deterministic presentation with sort.
- **zipmap:** combine equal-length key and value sequences; validate keys are unique.
- **setproduct:** Cartesian product of input collections; useful for environment × region or service × zone, but watch combinatorial growth.
- **transpose:** invert a map of string lists to grouped keys.
- **lookup / try / can:** handle optional attributes and dynamic errors without masking required values.
- **jsonencode / yamlencode:** generate valid structured text; outputs and plans can still expose secrets.

## 7. Lab layout and prerequisites

~~~text
labs/chapter-018/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  environments/dev.json
  environments/prod.json
  transformation-policy.json
  validate_transformations.py
  test_validate_transformations.py
  run-preflight.sh
  .gitignore
~~~

Terraform >=1.5 or an approved compatible OpenTofu, Python 3.9+, Bash (WSL2 supported). Core resources use built-in terraform_data; no external provider, account, or billable infrastructure.

## 8. Lab A — Type and expression exploration

~~~bash
cd infrastructure-as-code/labs/chapter-018
terraform fmt -check -recursive
terraform init -input=false
terraform validate
terraform console -var-file=environments/dev.tfvars
~~~

In console, evaluate:

~~~hcl
sort(distinct(var.zones))
keys(var.services)
[for name, svc in var.services : name if svc.enabled]
{ for name, svc in var.services : svc.tier => name... }
flatten([["api", "worker"], ["audit"]])
setproduct(["api", "worker"], ["a", "b"])
zipmap(["a", "b"], [1, 2])
merge({ owner = "unknown" }, { owner = var.owner })
~~~

Exit with exit. Verify ordering, types and overwrite behavior. The map of service tiers groups all names with the same tier into a list.

## 9. Lab B — Apply deterministic keyed resources

~~~bash
terraform plan -var-file=environments/dev.tfvars -out=chapter018.tfplan
terraform show -no-color chapter018.tfplan
terraform apply chapter018.tfplan
terraform state list
terraform output -json
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "plan_exit=$?"
~~~

Expected: four service×zone terraform_data.workload instances plus one audit record, and a subsequent plan exit code 0. Addresses resemble terraform_data.workload["api@a"] and terraform_data.workload["worker@b"].

## 10. Lab C — Transformation and change-control negative cases

~~~bash
terraform plan -var-file=environments/prod.tfvars
terraform plan -var='zones=[]'
terraform plan -var='environment=production'
python3 validate_transformations.py environments/dev.json transformation-policy.json
python3 validate_transformations.py environments/prod.json transformation-policy.json
python3 -m unittest -v test_validate_transformations.py
bash run-preflight.sh
~~~

Invalid zones and environment must fail. The JSON policy checks production replicas, owner, duplicate canonical keys, allowed zones and the maximum service×zone resource count. It does not prove that the Terraform HCL and JSON files are synchronized; compare reviewed inputs in CI or generate both from one canonical source for real production.

In a disposable copy, rename api to api-v2 and inspect the proposed destroy/create for each zone. Do not apply the destructive plan; explain how a reviewed moved block could preserve addresses when renaming resources without changing underlying identity.

## 11. Lab D — State and cleanup

~~~bash
terraform state list
terraform plan -destroy
terraform destroy
terraform state list
git status --short
~~~

Never commit terraform.tfstate, .terraform, saved plans, secrets or unredacted plan JSON. terraform_data does not create real cloud objects; a passing no-cloud lab is not a production readiness certification.

## 12. Production SRE/DBRE cases

**RDS/Aurora:** Expand approved database instances across AZs with stable IDs; reject duplicate IDs and destructive storage changes. Verify snapshots, PITR, RPO/RTO and cost before apply.

**PostgreSQL:** Derive replication topology maps without accidental duplicate instance keys; validate sync/async design, failover and connection pool impacts.

**Elasticsearch/OpenSearch:** Build index or data-node inventory from zone maps. Stable addresses prevent unplanned node replacements; validate storage IOPS, shard placement and heap sizing.

**EKS:** Build node-group × AZ maps and enforce max node counts, PDB and disruption constraints. Plan action review must catch replacement even if JSON policy passes.

**AKS:** Derive pool configurations by region/zone while verifying tenant, subscription, backend and cluster identity.

**Redis:** Expand shard/replica placements deterministically; validate failover and memory headroom, not only replica counts.

**Snowflake:** Group warehouses by cost center and owner; enforce size, suspend and grants through independent policy.

**Kafka/MSK:** Derive broker × AZ placement and inspect replication factor, quorum, partition leadership and maintenance sequencing.

## 13. Troubleshooting

| Symptom | Root cause | Safe response |
|---|---|---|
| Duplicate object key | Canonicalized keys collide | Reject input or use intentional grouping |
| Invalid for_each | Unknown/sensitive or unsupported keys | Use known, stable nonsensitive map |
| Index out of range | List length changed | Use keyed maps or validate bounds |
| Splat expression fails | for_each map not a sequence | Use explicit for expression |
| Unexpected replace | Key rename or index churn | Halt, inspect addresses, plan migration |
| Map merge loses owner | Later map overwrites tag | Set mandatory tags last |
| Too many resources | Cartesian product explosion | Enforce count and cost caps |
| Wrong ordering | Set/list conversion | sort deterministic strings |
| Missing workload | for expression filter excludes it | Inspect enabled flags and test |
| Plan differs after apply | Unstable inputs or drift | Inspect state, plan, backend and source |

## 14. Runbooks

**Transformation change review:** pin CLI/provider versions → verify input types → console-test representative expressions → run unit tests and policy → fmt/validate → inspect plan JSON and for_each addresses → SRE/DBRE approval → apply → SLO/cost checks.

**Unexpected replacement:** stop automation → compare prior/current keys → inspect moved block eligibility and provider identity → obtain approval → replan → stage and verify.

**Capacity incident:** preserve mitigation → compare generated topology to actual inventory → validate replica, AZ and disk/IOPS limits → reconcile safely → RCA/COA.

**Security exposure:** freeze apply → inspect generated grants/network CIDRs/tags → contain access → rotate leaked credentials → audit and remediate.

## 15. Acceptance and assessment

| Domain | Points |
|---|---:|
| Type and collection semantics | 15 |
| for/splat and grouping exercises | 20 |
| Stable key and idempotent plan | 20 |
| Automated tests and negative cases | 20 |
| Production runbooks and approvals | 15 |
| Cleanup and evidence hygiene | 10 |

Passing threshold 85/100, with zero critical failures (unreviewed production delete, secret leakage, missing data backup or unsafe lock bypass). Capture sanitized CLI versions, unit-test output, addresses, plan exit codes, owner approval and cleanup. **Tests are authored, not asserted as executed.**

## 16. Knowledge check

Why sort sets? How does grouping mode differ from normal object for? Why cannot splat project a for_each map directly? What does flatten do to maps? Why must keys be stable? What happens when merge arguments conflict? How do you limit setproduct explosion? Why does policy JSON not prove HCL correctness? How can an address rename cause replacement? What evidence does a DBRE need before apply?

**Next:** Chapter 019 — Terraform Conditional Expressions, Null Handling, try/can and Defensive Configuration Patterns.
