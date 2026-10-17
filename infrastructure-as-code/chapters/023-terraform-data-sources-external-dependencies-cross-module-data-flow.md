# Chapter 023 — Terraform Data Sources, External Dependencies and Cross-Module Data Flow

**Part 05 — Providers and Dependencies** · **Audience:** SRE, DBRE and Platform Engineers · **Core lab:** local/no-cloud · **Status:** published content; execution acceptance pending

## 1. Learning objectives

Differentiate managed resources from data sources; understand plan-time versus apply-time reads; design module inputs and outputs as explicit interfaces; manage external system dependencies and sensitive data; avoid unknown for_each keys, stale remote-state contracts and cross-environment coupling; enforce data provenance, contract validation and safe rollout/rollback.

## 2. Architecture and trust boundaries

~~~text
Git commit + typed root inputs + approved identity
                     |
    external read-only sources / remote state
                     |
        provider data-source read
                     |
    normalized module input contract
                     |
        child module outputs
                     |
   dependent application/DBRE resources
                     |
     policy + plan + approval + apply
                     |
     SLO/data checks and audit evidence
~~~

Data sources query existing objects; managed resources create or manage objects and persist their state. Data sources are not necessarily immutable, authoritative, fresh or available. Data-source reads can occur during plan when inputs and dependencies are known, or be deferred to apply when required dependencies change or inputs are unknown. A module output is a public interface to its caller, not a durable integration API or secret vault.

## 3. Managed resource versus data source

~~~hcl
# Illustrative AWS example; NOT part of the no-cloud lab:
data "aws_vpc" "selected" {
  id = var.existing_vpc_id
}

resource "aws_security_group" "app" {
  name   = "app-allowlist"
  vpc_id = data.aws_vpc.selected.id
}
~~~

The data source reads the VPC but does not own its lifecycle. The resource manages a security group. A read can fail if the VPC is missing, credentials are wrong, permissions are insufficient, or region/account differs. A lookup that matches by tag may become ambiguous; prefer immutable identifiers and explicit environment identity.

## 4. Read timing, unknowns and graph behavior

A data source whose arguments are known can often read during plan. If an input is unknown or a changing resource is an explicit dependency, the read may occur during apply. Its outputs then appear as unknown in the plan, potentially preventing use as for_each keys. Overbroad module-level depends_on can unnecessarily defer data reads.

Use stable input keys for for_each and avoid basing addresses on data-source values that are unavailable at plan time. An external read is not a health check; provider success does not prove an application is ready.

## 5. Cross-module data flow

~~~hcl
module "network" {
  source = "./modules/network"
  environment = var.environment
  subnet_ids  = var.subnet_ids
}

module "database" {
  source = "./modules/database"
  environment = var.environment
  network = module.network.contract
}
~~~

The root passes an explicit contract between child modules. A child module declares input variables and exposes outputs; it should not reach into sibling internals. Avoid module outputs that expose credentials, unnecessary implementation details or unstable resource names. Use object type contracts and versioned modules when breaking changes are likely.

## 6. Remote state, external systems and secrets

\`terraform_remote_state\` can read root outputs from another state snapshot, but access to state may expose more sensitive information than the outputs alone. Do not assume sensitive outputs provide an access-control boundary. Prefer published configuration APIs, parameter stores or provider data sources with narrow permissions where appropriate.

For AWS SSM, Azure Key Vault, GCP Secret Manager, Snowflake or Kubernetes secrets, data-source values may flow into Terraform state, saved plans and logs. Prefer workload identity and secret injection that avoids unnecessary state persistence. Never put production secrets in this lab's JSON fixtures.

The \`external\` data source invokes an external program through a provider and requires a stable JSON protocol; it adds runtime, dependency, supply-chain and timeout risks. It is illustrated here but **not executed** in the core lab because that would require an external provider. Prefer first-class providers and explicit input contracts over shell-driven hidden infrastructure changes.

## 7. Offline lab layout

~~~text
labs/chapter-023/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  modules/network/variables.tf
  modules/network/main.tf
  modules/network/outputs.tf
  modules/database/variables.tf
  modules/database/main.tf
  modules/database/outputs.tf
  examples/aws-data-sources.tf.example
  examples/external-data-source.tf.example
  environments/dev.tfvars
  environments/prod.tfvars
  data-contract-policy.json
  sample-contract.json
  data_contract_policy.py
  test_data_contract_policy.py
  run-preflight.sh
  .gitignore
~~~

Terraform >=1.5 or approved compatible OpenTofu; Python >=3.9; Bash/WSL2; no cloud credentials. The executable core uses built-in terraform_data resources, module outputs and input contracts, **not** a real cloud data source. Cloud data-source examples have .example extensions so init stays offline.

## 8. Lab A — Explicit module contracts

The network module accepts an environment and a map of known subnet IDs and exports a normalized contract. The database module consumes the network output and exports a database connection metadata contract (no password or real endpoint). The root application terraform_data record references the database output, establishing an implicit graph dependency.

~~~bash
cd infrastructure-as-code/labs/chapter-023
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform graph > graph.dot
terraform plan -var-file=environments/dev.tfvars -out=chapter023.tfplan
terraform show -no-color chapter023.tfplan
terraform apply chapter023.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected: module.network.terraform_data.contract, module.database.terraform_data.contract and terraform_data.application. A second plan should return 0. No real database, VPC or secret is created.

## 9. Lab B — Data contract policy and tests

~~~bash
python3 data_contract_policy.py sample-contract.json data-contract-policy.json
python3 -m unittest -v test_data_contract_policy.py
bash run-preflight.sh
~~~

The Python validator checks source identity, contract schema/version, environment, subnet keys, CIDR-like metadata, owner, change ticket, secret-like field names, production backup/encryption requirements and allowed source types. It validates a **standalone JSON fixture**, not Terraform HCL or a live provider read. The 18 tests exercise valid/invalid contracts, missing values, unsafe prod settings, duplicate identifiers and unsupported versions.

## 10. Lab C — Data-source read timing tabletop

In examples/aws-data-sources.tf.example, identify data sources, selection predicates and the dependency on existing resources. Explain when plan-time reads are possible. In examples/external-data-source.tf.example, review the read-only protocol and explain why a script returning changing values would produce noisy plans. Do not copy these examples into the offline lab or apply cloud resources without a separately approved workspace.

## 11. Lab D — Failure injection

1. Change the root subnet map to omit the required primary subnet. Expect input validation failure; restore it.
2. Change the database module environment input to a different environment in a disposable copy. Observe module precondition rejection; restore it.
3. Change a module output field name without changing the caller. Expect an unsupported attribute or missing contract failure; restore it.
4. Add a secret-like key to sample-contract.json. The policy must deny it.
5. Set production backup_enabled=false or encryption_enabled=false in the fixture. The policy must deny it.
6. Discuss how a remote-state producer changing output schema breaks downstream consumers; design staged compatibility and migration.

Never run negative drills against shared remote state or live database systems.

## 12. Lab E — Cleanup

~~~bash
terraform plan -destroy
terraform destroy
terraform state list
git status --short
~~~

Expected empty state. Do not commit .terraform, state, saved plans, graph.dot, secrets or raw plan JSON.

## 13. Production SRE/DBRE scenarios

**RDS/Aurora:** Consume approved VPC, subnet and KMS identifiers as inputs or data sources; verify region/account and backup settings. Treat failover endpoints and replica health as runtime checks.

**PostgreSQL:** Separate module output metadata from credentials. Validate endpoint, TLS, connection pool and migration compatibility before application rollout.

**Elasticsearch/OpenSearch:** Read existing cluster/network identifiers with exact matches; confirm storage tier, shard capacity and API health before dependent workloads.

**EKS:** Network/identity module outputs feed cluster and node modules; bootstrap Kubernetes provider only after cluster readiness, possibly in separate phases.

**AKS:** Pass tenant/subscription and subnet IDs explicitly; verify managed identity and RBAC rather than trusting a tag-based lookup.

**Redis:** Module outputs may publish endpoints but should not expose auth tokens. Validate HA and client reconnect behavior outside Terraform.

**Snowflake:** Use approved role/warehouse identifiers; protect credentials and verify grants/ownership with the Snowflake API.

**Kafka/MSK:** Pass broker/network metadata with a versioned contract; validate broker readiness, partition replication and consumer lag independently.

## 14. Troubleshooting matrix

| Symptom | Cause | Safe response |
|---|---|---|
| Data source not found | Wrong ID/account/region | Verify provider identity and selector |
| Multiple matches | Non-unique tags/filter | Require stable identifier |
| Data read during apply | Unknown or changing dependency | Inspect graph, remove broad depends_on |
| Unknown for_each keys | Lookup deferred | Use known input keys |
| Unsupported attribute | Module output schema changed | Version and migrate interface |
| Sensitive output leaks | Data flowed into plan/state | Contain, rotate, redesign contract |
| Remote-state access denied | Backend permissions | Use scoped identity; avoid broad state access |
| Stale external value | Cache/API timing | Revalidate at apply and runtime |
| Provider timeout | API outage/rate limit | Retry with backoff, preserve state |
| Unexpected replacement | Changed module output | Stop, review plan and migration |
| Module cycle | Cross-module reference loop | Refactor ownership and interfaces |
| Prod guard fails | Backup/encryption mismatch | Block and correct reviewed inputs |

## 15. Operational runbooks

**Data source onboarding:** identify authoritative system -> verify identity/region -> use exact lookup -> test missing/ambiguous cases -> classify secrets -> version output contract -> stage rollout.

**Cross-module breaking change:** publish backward-compatible output -> update consumers -> validate staging -> review production plan -> coordinate owners -> remove old output only after migration.

**External dependency outage:** stop unsafe apply -> confirm upstream availability -> preserve current state -> retry fresh plan after recovery -> verify application health.

**Secret exposure:** isolate logs/state artifacts -> revoke/rotate secret -> review backend permissions -> redesign data flow -> document incident.

**Wrong-environment read:** freeze pipeline -> verify cloud caller identity/backend -> assess impact -> recover through approved plan and change control.

## 16. Acceptance assessment (100 points)

| Area | Points |
|---|---:|
| Data source semantics and read timing | 20 |
| Explicit module input/output contracts | 20 |
| Sensitive/remote-state risk controls | 20 |
| No-cloud plan/apply and graph evidence | 15 |
| Policy and negative tests | 15 |
| Runbooks, cleanup and audit | 10 |

Pass 85+ with no critical failures. Record sanitized CLI version, plan/idempotence results, policy tests, module graph, change ticket and cleanup. **Authored tests have not been executed by publication alone.**

## 17. Knowledge check

Why is a data source not an ownership boundary? What causes apply-time reads? Why are data-source results unsafe as unknown for_each keys? What does a child module output expose? Why is remote state not a secret-isolation boundary? What are the risks of the external data source? How do you handle an output schema migration? What evidence proves the correct cloud account? What should DBRE check before database endpoint cutover? Why are runtime health checks still necessary?

**Next:** Chapter 024 — Terraform Lifecycle Meta-Arguments, Preconditions, Postconditions and Safe Replacement Strategies.
