# Chapter 032 — Terraform Module Inputs, Outputs, Validation and Contract Testing

**Part 07 — Reusable Modules · Chapter 032/120**  
**Audience:** SRE, DBRE, Platform Engineering · **Prerequisites:** Chapters 001–031  
**Lab:** no-cloud, Terraform >=1.5 and Python 3.9+ · **Publication status:** content published; execution evidence tracked separately.

## 1. Learning objectives

Build a versionable, fail-closed Terraform module interface with typed inputs, optional object attributes, defaults, \`nullable\`, variable validation, sensitive values, preconditions, postconditions, stable outputs, automated contract tests and upgrade compatibility reviews. Detect incompatible changes before promoting network/database/application modules to production.

## 2. Architecture and responsibility boundaries

~~~text
Environment root (dev / staging / prod)
  |-- input contract + policy + change ticket
  |-- module.network: network contract
  |-- module.database: typed network input -> database contract
  |-- module.application: typed database input -> application contract
  |-- acceptance: static checks -> contract tests -> plan -> health
  |
  +-- separate backend, state, identity and approval per environment
~~~

A module is a reusable configuration unit, **not** an isolation boundary. Root modules own backend, provider authentication, environment selection and execution. Child modules own a documented interface and implementation. Use explicit outputs rather than reaching into internal resource addresses. Avoid returning secrets or oversized internal objects. An output marked \`sensitive\` is redacted in ordinary CLI output but may still be stored in state and revealed to authorized consumers.

## 3. Input contracts

| Mechanism | Production intent | Pitfall |
|---|---|---|
| \`type = object({...})\` | exact documented fields and types | extra object attributes can be discarded during conversion |
| \`optional(T, default)\` | backward-compatible extension | defaults can conceal invalid caller intent |
| \`nullable = false\` | reject explicit null for mandatory input | only applies at variable boundary |
| \`validation\` | validate ranges, enums, CIDR, format | cannot replace provider or remote validation |
| \`sensitive = true\` | reduce accidental CLI disclosure | not state encryption |
| \`precondition\` | enforce cross-resource/cross-input invariants | may evaluate at plan or apply |
| \`postcondition\` | validate observed output/resource guarantees | requires available values |

Prefer narrow semantic inputs (for example \`replicas\`, \`backup_enabled\`, \`network\`) over opaque \`any\` or loosely structured maps. Document units, failure behavior and compatibility guarantees. Production defaults should not silently disable backups, encryption or deletion protection.

## 4. Output contracts

Export a stable, minimal object with an explicit \`schema_version\` and operational fields, not provider-private attributes. Consumers should declare typed input objects so incompatible schemas fail early. Version the module release separately from the output schema. An output schema change can break consumers even when no infrastructure resource changes.

The lab has three child modules: network -> database -> application. The database module checks network/environment alignment and production backup/encryption/replica controls. The application checks database/environment alignment and a supported schema version. Root outputs expose the composed contracts and change ticket.

## 5. Versioning and compatibility

| Change | Compatibility | Review |
|---|---|---|
| Add optional input with safe default | usually backward compatible | validate behavior and cost |
| Add output field | usually compatible | review sensitive data exposure |
| Rename/remove input | breaking | release major version, migrate callers |
| Rename/remove output | breaking | coordinate all consumers |
| Tighten validation | potentially breaking | test all existing environment fixtures |
| Change resource address | state migration risk | \`moved\` block and plan |
| Change immutable provider argument | replacement risk | DBRE approval and rollback |

Use immutable module releases (registry version or Git SHA), changelogs, semantic versioning and consumer contract tests. Avoid \`?ref=main\` and unaudited third-party sources. Root provider lock files and module source version pins solve different supply-chain problems.

## 6. Lab layout

~~~text
labs/chapter-032/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  modules/network/{versions.tf,variables.tf,main.tf,outputs.tf}
  modules/database/{versions.tf,variables.tf,main.tf,outputs.tf}
  modules/application/{versions.tf,variables.tf,main.tf,outputs.tf}
  contract-policy.json
  fixtures/contract-safe.json
  fixtures/contract-unsafe.json
  fixtures/plan-safe.json
  fixtures/plan-destructive.json
  contract_policy.py
  test_contract_policy.py
  run-preflight.sh
  .gitignore
~~~

All executable Terraform resources use built-in \`terraform_data\`. This demonstrates interfaces and dependency ordering without creating a cloud network or database. The Python fixtures are declared evidence, not independent verification of real cloud settings.

## 7. Lab A — Static validation and deployment

~~~bash
cd infrastructure-as-code/labs/chapter-032
terraform version
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter032.tfplan
terraform apply chapter032.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected module addresses: \`module.network.terraform_data.network\`, \`module.database.terraform_data.database\`, \`module.application.terraform_data.application\`. An unchanged second plan exits 0. Use separate workspaces/directories and state for each environment.

## 8. Lab B — Negative validation and contract failures

Run in a disposable copy:

~~~bash
terraform plan -var-file=environments/dev.tfvars -var="database_replicas=0"
terraform plan -var-file=environments/dev.tfvars -var="network_cidr=not-a-cidr"
terraform plan -var-file=environments/prod.tfvars -var="backup_enabled=false"
terraform plan -var-file=environments/prod.tfvars -var="database_replicas=1"
~~~

All should fail validation or preconditions. Additional drills: remove a required output field, change \`schema_version\`, introduce a mismatched environment, change an optional input default, and simulate a resource rename without a \`moved\` block. Review plans for unintended replacements before applying.

## 9. Lab C — Automated contract policy

~~~bash
python3 contract_policy.py fixtures/contract-safe.json fixtures/plan-safe.json contract-policy.json
python3 contract_policy.py fixtures/contract-unsafe.json fixtures/plan-destructive.json contract-policy.json
python3 -m unittest -v test_contract_policy.py
bash run-preflight.sh
~~~

The safe fixture must pass; the unsafe fixture must be denied. The validator checks environment, change ticket, unique module names, required input/output fields, compatible contract schema versions, non-nullable input declarations, valid dependency order, production database safeguards and deny-by-default destructive plan actions. It is a **fixture-level educational gate**; use \`terraform validate\`, \`terraform test\` (where appropriate), real plan JSON, provider integration tests and service health checks for stronger acceptance.

## 10. Contract test design

1. **Syntax:** format, init, validate.
2. **Input:** correct type, invalid enum/range, null handling, optional defaults.
3. **Output:** required keys, schema version, absence of secrets.
4. **Compatibility:** old consumer against new producer, new consumer against old producer.
5. **Lifecycle:** no unintended delete/replace when updating a module.
6. **Security:** sensitive output policy, provider identity, remote state encryption and RBAC.
7. **Production:** backup, encryption, RPO/RTO, availability and SLO checks.
8. **Negative tests:** every critical guard must have a failing test.

A JSON policy manifest cannot prove Terraform's runtime types or real infrastructure security; record its limitations in the change ticket.

## 11. Production SRE/DBRE scenarios

**PostgreSQL/RDS/Aurora:** typed database contract includes backup/encryption/replica intent, but acceptance additionally verifies snapshots, WAL/PITR, connectivity and failover.  
**Elasticsearch/OpenSearch:** schema changes to domain endpoints or capacity outputs must preserve search client behavior; verify shards, snapshots and latency.  
**EKS/AKS:** a cluster module output schema must not expose kubeconfig credentials; test consumers across cluster upgrades.  
**Redis:** test persistence, failover and client reconnect on endpoint contract changes.  
**Kafka/MSK:** broker endpoint changes require consumer and ISR/lag checks.  
**Snowflake:** role/warehouse outputs need scoped grants, audit and cost checks.  
**MongoDB:** validate replica set topology and data backups independently of module validation.

## 12. Troubleshooting

| Failure | Root cause | Safe action |
|---|---|---|
| Unsupported argument | renamed/removed input | pin compatible module release |
| Unsupported attribute | output contract changed | restore/migrate schema |
| Invalid value for input variable | type/validation failure | correct caller or version |
| Null not allowed | mandatory input unset | supply explicit value |
| Precondition failed | environment or backup mismatch | investigate, do not bypass |
| Unknown output at plan time | computed resource attribute | avoid plan-time dependence |
| Sensitive value in logs | output/logging mistake | contain, rotate, audit |
| Unexpected resource replacement | address or immutable change | stop, review moved strategy |
| Module version mismatch | floating/incorrect source | pin immutable release |
| Apply succeeds, app unhealthy | Terraform != service readiness | run DBRE/SRE health checks |

## 13. Production runbooks

**Publish contract:** assign owner → define schema and types → add validation and examples → negative tests → peer review → immutable release → changelog → staged promotion.

**Upgrade consumer:** inventory consumers → compare input/output schemas → test old/new compatibility → initialize/validate → inspect plan JSON and address changes → DBRE approval for stateful resources → apply under lock → verify data and SLO.

**Contract incident:** freeze deployments → capture module versions and affected roots → preserve state backup → revert to compatible module or approved migration → fresh plan → verify application and database health → RCA.

**Rollback:** revert module source/version, reinitialize and review fresh plan. A Git revert does not reverse state changes or restore deleted data.

## 14. Acceptance rubric (100 points)

| Category | Points |
|---|---:|
| Typed input design, defaults and validation | 25 |
| Output schemas and compatibility | 20 |
| Module composition and dependencies | 15 |
| Automated tests and negative cases | 20 |
| Security, production SRE/DBRE runbooks | 20 |

Pass >=85 and zero critical failures. Critical failures include secret leakage, production backup/encryption disabled, unapproved destructive plan, cross-environment state reuse, or a breaking contract promoted without consumer validation.

## 15. Cleanup and knowledge check

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Only destroy the isolated local lab. Do not commit state, plans or credentials.

Questions: Why are object types preferable to \`any\`? What does \`optional()\` change? How do \`nullable\` and \`sensitive\` differ? When are preconditions evaluated? What makes an output contract breaking? Why is \`schema_version\` useful? How do modules differ from state isolation? Why can Git rollback be insufficient? How do you test backward compatibility? What production evidence supplements a green plan?

**Next: Chapter 033 — Terraform Module Versioning, Registries and Dependency Management.**
