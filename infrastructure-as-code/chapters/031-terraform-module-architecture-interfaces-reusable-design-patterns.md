# Chapter 031 — Terraform Module Architecture, Interfaces and Reusable Design Patterns

**Part 07 — Reusable Modules · Chapter 031/120**  
**Audience:** Platform Engineers, SREs, DBREs · **Prerequisites:** Chapters 001–030  
**Lab:** local \`terraform_data\` resources only; no cloud account or cost.  
**Status:** curriculum published; live Terraform and production acceptance pending.

## 1. Outcomes and architectural principles

Build, consume, test and maintain reusable Terraform modules with explicit interfaces, typed contracts, version constraints, secure provider boundaries, deterministic composition, environment isolation and operational ownership. Understand module sources, \`required_providers\`, root versus child configuration, output sensitivity, dependency edges, lifecycle implications and versioning strategy.

A **root module** is the directory where Terraform runs. A **child module** is called through a \`module\` block. Every directory with Terraform configuration is a module. Modules organize and reuse resource definitions; they do **not** independently create state files, deployment boundaries, provider credentials or access controls. All child modules called from one root normally share that root's state and execution lifecycle.

### Reference architecture

~~~text
Git / CI / review + pinned CLI + lock file
                       |
                Root composition
              (env + state + IAM)
                       |
       +---------------+----------------+
       |               |                |
  module.network  module.database  module.application
       |               ^                ^
       +-- typed output+-- typed output-+
                       |
                 module.audit
                       |
          Fresh plan + policy + approval
                       |
        apply / verify / rollback / audit
~~~

Design modules around **cohesive operational ownership**, not one module per resource. A network module can own a network contract; a database module can own storage, encryption and backup configuration; an application module consumes database connectivity as a contract. Do not force all changes into a monolithic module or create circular dependencies.

## 2. Interface design and contracts

A child module should expose the smallest useful interface:
- **Inputs:** documented variables with type, validation, nullability, safe defaults and clear units.
- **Outputs:** stable names and meaningful types; mark confidential outputs \`sensitive = true\` but remember state still contains sensitive values.
- **Providers:** declare \`required_providers\` in every module that uses provider resources. Configure credentials and provider aliases at the root, pass aliases explicitly through \`providers = { ... }\` when needed.
- **Dependencies:** use references to outputs for implicit ordering; reserve \`depends_on\` for hidden dependencies not represented by values.
- **Lifecycle:** avoid accidental replacement and propagate contract changes deliberately; version breaking interfaces.
- **State:** choose root/state boundaries based on ownership, blast radius, security and deployment cadence, not only folder structure.

The lab demonstrates typed \`object\` contracts passed between network, database and application. It uses \`terraform_data\` so that the complete composition can be exercised offline. **Terraform variable type constraints do not constitute a complete runtime security or compliance policy.**

## 3. Reusable module layout

~~~text
labs/chapter-031/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  modules/network/{versions.tf,variables.tf,main.tf,outputs.tf}
  modules/database/{versions.tf,variables.tf,main.tf,outputs.tf}
  modules/application/{versions.tf,variables.tf,main.tf,outputs.tf}
  module-policy.json
  sample-modules-safe.json
  sample-modules-unsafe.json
  sample-plan-safe.json
  sample-plan-destructive.json
  module_policy.py
  test_module_policy.py
  run-preflight.sh
  .gitignore
~~~

## 4. Root module versus child module

~~~hcl
module "network" {
  source      = "./modules/network"
  environment = var.environment
  cidr        = var.network_cidr
  owner       = var.owner
}

module "database" {
  source            = "./modules/database"
  environment       = var.environment
  network           = module.network.contract
  replicas          = var.database_replicas
  backup_enabled    = var.backup_enabled
  encryption_enabled = var.encryption_enabled
}

module "application" {
  source      = "./modules/application"
  environment = var.environment
  database    = module.database.contract
  owner       = var.owner
}
~~~

The actual lab files are the source of truth. Local module paths are appropriate for development; production remote modules should use pinned, reviewed immutable releases (for example a Git commit SHA or registry version), not a floating branch. Modules should have change logs, maintainers, semantic versioning and compatibility tests.

## 5. Lab A — Initialize, validate and inspect composition

~~~bash
cd infrastructure-as-code/labs/chapter-031
terraform version
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter031.tfplan
terraform apply chapter031.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected state addresses include \`module.network.terraform_data.network\`, \`module.database.terraform_data.database\`, and \`module.application.terraform_data.application\`. The unchanged second plan should exit 0. \`terraform fmt -recursive\` deliberately formats a disposable checkout before \`fmt -check\`; CI should enforce formatting on committed sources.

## 6. Lab B — Production guardrails and negative scenarios

~~~bash
terraform plan -var-file=environments/prod.tfvars
terraform plan -var-file=environments/dev.tfvars -var="database_replicas=0"
~~~

The valid production fixture requires >=3 database replicas, encryption and backups. The invalid dev fixture must fail variable validation. Run dev and prod **in separate directories/states** if applying; do not apply production inputs against a dev state.

Exercise additional failures in disposable copies: remove an output, change an object attribute name, introduce a circular module dependency, misroute the network contract, remove backup protection, and simulate a module version breaking change. For each, capture plan/validation evidence, rollback strategy and contract owner approval.

## 7. Lab C — Automated module and plan policy

~~~bash
python3 module_policy.py sample-modules-safe.json sample-plan-safe.json module-policy.json
python3 module_policy.py sample-modules-unsafe.json sample-plan-destructive.json module-policy.json
python3 -m unittest -v test_module_policy.py
bash run-preflight.sh
~~~

The validator checks a **declared architecture manifest** and simplified Terraform plan JSON: allowed environments, change ticket, unique module names, pinned module references for nonlocal sources, required owners and contracts, network/database/application ordering, production encryption/backup/replica rules, and deny-by-default deletion/replacement. A passing fixture is **not proof** that actual Terraform module sources, provider authentication or remote infrastructure satisfy those controls. Validate live plans and real resources separately.

## 8. Module design patterns

| Pattern | Use | Tradeoff |
|---|---|---|
| Composition root | central orchestration, separate child ownership | shared state blast radius |
| Thin wrapper | consistent enterprise defaults around upstream module | version coupling |
| Contract module | stable typed outputs consumed downstream | breaking schema changes |
| Environment root | separate prod/dev state and identity | repeated orchestration |
| Platform building block | standardized DB/network/app provisioning | requires release governance |
| Nested modules | coherent internal composition | complex debugging if excessive |
| Feature flag | optional capabilities via \`count\`/\`for_each\` | address migrations and compatibility |

Do not use modules as a substitute for account isolation. Avoid excessive \`depends_on\` at module level, which can unnecessarily defer reads and obscure plan reasoning. Avoid leaking credentials or raw database passwords through outputs.

## 9. Provider configuration and supply-chain controls

The root should pin compatible provider versions and commit its dependency lock file. Child modules declare their own minimum compatible provider constraints; avoid unnecessarily narrow constraints in reusable libraries. Provider aliases are inherited only according to Terraform's provider configuration rules; explicitly pass non-default aliases and declare \`configuration_aliases\` where required. Review module source code and third-party dependencies, pin releases, verify provenance, and use workload identity rather than static credentials.

## 10. Testing strategy

1. **Static:** \`terraform fmt -check\`, \`terraform init -backend=false\`, \`terraform validate\`.
2. **Contract:** variable and output types, module interface compatibility, version upgrade tests.
3. **Policy:** architecture manifest and plan actions; negative cases required.
4. **Integration:** apply in isolated disposable state and verify outputs/state addresses.
5. **Production acceptance:** provider IAM, backup, encryption, service health, SLO, cost and ownership checks.
6. **Upgrade:** compare old/new module versions, \`moved\` blocks and planned replacements before promotion.

## 11. SRE/DBRE production scenarios

**RDS/Aurora/PostgreSQL:** network and DB modules must agree on subnet/identity/backup/encryption contracts; test failover, PITR, connection health and deletion protection separately from Terraform.  
**Elasticsearch/OpenSearch:** expose domain endpoints and capacity contracts, but verify shard health, snapshots and query SLO before accepting module upgrades.  
**EKS/AKS:** isolate cluster lifecycle from application release cadence; module outputs should expose only necessary cluster IDs and endpoints, not secrets.  
**Redis:** validate failover, persistence and client reconnection on topology changes.  
**Kafka/MSK:** preserve broker/partition and networking dependencies, monitor ISR and lag.  
**Snowflake:** use scoped roles for warehouse/grant modules; validate privilege drift and spend.  
**MongoDB:** test replica set health and backup/restore independently of infrastructure module output success.

## 12. Troubleshooting matrix

| Symptom | Likely cause | Response |
|---|---|---|
| Unsupported argument | changed child input contract | compare module version/interface |
| Unsupported attribute | missing/renamed output | restore contract or migrate consumer |
| Module not installed | source changed | run init, verify source/ref |
| Provider alias missing | incomplete providers map | configure alias at root and pass explicitly |
| Cycle detected | circular dependencies | redesign contract edges |
| Unknown values in plan | deferred provider/resource values | review plan-time assumptions |
| Unexpected replacement | address or immutable argument change | stop, use moved blocks when appropriate |
| Cross-environment drift | shared backend or identity | freeze and verify state isolation |
| Sensitive output leak | output/logging policy failure | contain, rotate, audit |
| Tests pass but service fails | infrastructure != workload health | run SRE/DBRE health checks |

## 13. Production runbooks

**Publish a module:** designate owner → document interface → review provider and module dependencies → test safe and negative cases → tag immutable release → publish changelog → promote through isolated environments → monitor.

**Upgrade a consumer:** pin target version → read migration notes → run init/validate/plan → inspect state address moves and replacements → get DBRE approval for stateful resources → apply under lock → verify real objects, data and SLO → record evidence.

**Breaking contract incident:** freeze pipeline → identify old/new module versions and affected roots → preserve state snapshot → restore compatible module version or use reviewed migration → fresh plan → validate workloads.

**Provider authentication failure:** verify caller, alias mapping and least-privilege roles; never inject credentials into module source or output.

**Rollback:** revert Git to last approved module version, reinitialize, plan and review; reverting code does not automatically reverse state mutations or restore deleted data.

## 14. Acceptance rubric (100 points)

| Area | Points |
|---|---:|
| Architecture and module boundaries | 20 |
| Typed inputs, outputs and validation | 20 |
| Composition and dependency graph | 15 |
| Automated tests and negative cases | 20 |
| Security, provider and version governance | 10 |
| SRE/DBRE runbooks and acceptance evidence | 15 |

Pass >=85 and zero critical failures. Critical: production destructive plan without approval, credential leakage, cross-environment state sharing, unsafe DB replacement, duplicate resource ownership or unverified recovery claim.

## 15. Cleanup and knowledge check

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Only destroy the disposable local lab. Do not commit state, plans or credentials.

Questions: How do modules differ from states? Why use typed object contracts? What makes an output stable? When does a provider alias need explicit passing? How does a module upgrade affect resource addresses? Why are module version tags and a lockfile different? How do you detect breaking interface changes? What is a safe DBRE module upgrade? What must be verified beyond Terraform apply? Why is a Git revert not a database restore?

**Next: Chapter 032 — Terraform Module Inputs, Outputs, Validation and Contract Testing.**
