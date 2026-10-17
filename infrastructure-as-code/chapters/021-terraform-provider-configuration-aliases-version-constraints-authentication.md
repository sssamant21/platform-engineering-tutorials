# Chapter 021 — Terraform Provider Configuration, Aliases, Version Constraints and Authentication

**Part 05 — Providers and Dependencies** · **Audience:** SRE, DBRE, DevOps, Platform Engineering · **Core lab:** offline and no cloud credentials · **Status:** Published; execution evidence pending.

## Objectives

Explain Terraform Core versus provider plugins, source addresses and dependency resolution; distinguish required_providers from provider configurations; understand constraints and lock files; use aliases and explicit module provider wiring; implement least-privilege short-lived authentication; inspect a plan for destructive changes; and troubleshoot multi-account/region identity failures safely.

## 1. Provider architecture and execution lifecycle

~~~text
Git revision + root module + child modules
                  |
   terraform.required_providers
                  |
   terraform init -> dependency solver
                  |
 .terraform.lock.hcl + provider plugin verification
                  |
 provider configurations / aliases
                  |
 cloud identity / workload federation
                  |
 plan (refresh + diff) -> review -> apply
                  |
 cloud APIs / remote state / observability
~~~

Terraform Core evaluates HCL, constructs a dependency graph and orchestrates operations. Providers are separate plugins that implement resource and data-source schemas and CRUD/read behavior. A provider source address identifies a plugin (for example hashicorp/aws), while a provider configuration selects settings such as region, endpoint and credentials. Multiple aliases reference distinct configurations of the **same** provider source. An alias does not create a new provider version.

Provider configuration is typically declared in the root module; child modules declare requirements and receive provider instances via inheritance or explicit module providers maps. **Do not put credentials in provider blocks or Terraform variable files.** Provider configuration values and generated plans can be sensitive.

## 2. Provider source, versions and lock file

~~~hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}
~~~

The version constraint defines the acceptable range; the dependency lock file records the selected provider version and checksums. Commit .terraform.lock.hcl for reproducible root-module runs. Run terraform init -upgrade only as an explicit change with review, staging tests and rollback. Do not casually delete lock files to solve provider incompatibility.

Semver-style constraints: = 5.1.0 pins exactly; >= 5.0 allows future major versions; ~> 5.0 allows 5.x but not 6.x. Validate precise behavior before choosing an upgrade policy. Providers and Terraform Core have independent versions. Child modules should usually specify compatible lower bounds rather than hard-pin conflicting versions.

## 3. Aliases, default configuration and module wiring

~~~hcl
provider "aws" {
  region = "us-east-1"
}

provider "aws" {
  alias  = "dr"
  region = "us-west-2"
}

# Illustrative provider-specific resource:
resource "aws_s3_bucket" "dr" {
  provider = aws.dr
  bucket   = "replace-with-approved-globally-unique-name"
}
~~~

For child modules:

~~~hcl
# Child module terraform block declares the provider source.
terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      configuration_aliases = [aws.dr]
    }
  }
}

# Root module call:
module "replica" {
  source = "./modules/replica"
  providers = {
    aws    = aws
    aws.dr = aws.dr
  }
}
~~~

The root caller must define and pass referenced aliases; resource/provider selection is static, not a runtime variable. A module's aliases must be declared in configuration_aliases. Avoid provider blocks inside reusable child modules, especially with count, for_each and depends_on module meta-arguments. Alias wiring does **not** imply cross-region replication; the resources and data flows must implement it.

## 4. Authentication and least privilege

**AWS:** Prefer IAM roles, OIDC federation, AWS SSO/Identity Center or workload identity. Use STS caller identity to verify account, role and session. Avoid hardcoded access keys, committed profiles or long-lived CI credentials.

**Azure:** Prefer managed identity or workload identity federation. Verify tenant, subscription and RBAC scope; isolate provider and backend authentication. A successful az login is not proof that Terraform is targeting the intended subscription.

**GCP:** Prefer Workload Identity Federation and scoped service accounts. Verify project, impersonated identity and permissions. Avoid service-account JSON keys in repositories or CI variables.

**Kubernetes/Helm:** Prefer short-lived workload identity and bounded kubeconfig contexts. Confirm cluster UID/context and namespace; avoid insecure token output.

**Snowflake:** Prefer supported key-pair or federated/service principal patterns as appropriate for the provider and organization; use least-privilege roles and avoid plaintext private keys in state, plans or CI logs.

Backend credentials and provider credentials are distinct trust domains. Protect remote state with encryption, scoped access, locking where supported, audit trails and retention. Secret values may still enter state even if marked sensitive.

## 5. Dependency lock and supply-chain controls

Pin a reviewed Terraform/OpenTofu version, provider source and acceptable version range; commit lock file. Use terraform providers to inspect dependency requirements and terraform providers lock for intended platforms when required. Download from trusted registries and verify signatures/checksums through the standard init flow. In restricted networks, use a controlled provider mirror and document its trust boundary.

Review provider changelogs for schema changes, default changes, deprecated arguments, replacement behavior, API permissions and region support. Maintain an approved upgrade matrix for prod/staging.

## 6. Offline lab architecture and files

~~~text
labs/chapter-021/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  examples/aws-providers.tf.example
  examples/aws-child-module.tf.example
  examples/azure-auth.md
  examples/gcp-auth.md
  provider-policy.json
  provider-manifest-good.json
  provider-manifest-bad.json
  provider_policy.py
  test_provider_policy.py
  run-preflight.sh
  .gitignore
~~~

The runnable core uses only terraform_data (built into Terraform). The AWS example files are **illustrative** and deliberately use .example extensions so offline init does not download a cloud provider. No cloud credentials, account or charges required. Python 3.9+, Terraform >=1.5 or approved compatible OpenTofu, Bash/WSL2.

## 7. Lab A — Verify core and provider resolution

~~~bash
cd infrastructure-as-code/labs/chapter-021
terraform version
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform providers
terraform plan -out=chapter021.tfplan
terraform show -no-color chapter021.tfplan
terraform apply chapter021.tfplan
terraform output -json
terraform state list
terraform plan -detailed-exitcode
echo "exit=$?"
~~~

Expected: terraform_data.identity_contract and terraform_data.audit resources, and a no-change exit 0. terraform providers should not show external providers in the runnable core. Do not apply the .example cloud configurations without separately reviewed identities, accounts and backend.

## 8. Lab B — Review aliased cloud configurations without applying

Read examples/aws-providers.tf.example and examples/aws-child-module.tf.example. Identify default and dr provider aliases, required_providers, child configuration_aliases and the module providers map. Verify that authentication is delegated to the environment and no credential is embedded. Explain why AWS account verification is required **in addition to** the region argument.

To run a real AWS/Azure/GCP lab later, copy examples into a **new isolated workspace**, configure a safe backend and short-lived read-only credentials, run terraform init/validate/plan, verify actual account and permission boundaries, and obtain approval before provisioning. Do not run a cloud apply as part of this offline exercise.

## 9. Lab C — Manifest policy and negative tests

The Python manifest is a **review artifact** describing intended provider requirements and identities. It is not an HCL parser, cloud authentication verifier, or substitute for terraform providers and the real lock file.

~~~bash
python3 provider_policy.py provider-manifest-good.json provider-policy.json
python3 provider_policy.py provider-manifest-bad.json provider-policy.json
# The previous command must fail; do not treat it as a preflight success.
python3 -m unittest -v test_provider_policy.py
bash run-preflight.sh
~~~

The validator checks allowlisted provider sources, allowed version-constraint patterns, alias uniqueness, environment labels, expected regions, identity reference types, prohibition on inline secrets and production approval requirements. Negative tests cover bad sources, missing aliases, unsafe credentials, malformed manifests, wrong regions, prod without ticket and duplicate aliases.

## 10. Lab D — Lockfile and upgrade review

~~~bash
terraform providers
terraform init -lockfile=readonly -input=false
git diff -- .terraform.lock.hcl
~~~

The offline lab has no external providers and may not produce a lock file; a no-op diff is expected. For real provider dependencies, capture current selected versions and checksums, propose an upgrade in a dedicated branch, run init -upgrade only there, review the lockfile diff, run tests, inspect plan for replacements, and roll back by restoring the reviewed lockfile and module code if needed.

## 11. Lab E — Cleanup

~~~bash
terraform plan -destroy
terraform destroy
terraform state list
git status --short
~~~

Do not commit state, saved plans, .terraform, tokens, credentials or cloud CLI profiles.

## 12. Production SRE/DBRE scenarios

**RDS/Aurora:** Distinguish primary and DR AWS provider aliases; verify account, region, snapshot replication and KMS keys. Aliasing alone does not implement failover.

**PostgreSQL:** Verify RDS provider identity and subnet/region before parameter-group, storage or instance replacements; require backup and PITR evidence.

**Elasticsearch/OpenSearch:** Use distinct AWS/Azure provider configurations for each cluster; confirm storage tiers, encryption, node replacement and access policy.

**EKS:** Separate cluster bootstrap, workload and Helm/Kubernetes identities; ensure kubeconfig targets the intended cluster.

**AKS:** Validate Azure tenant/subscription and provider alias mapping before changing node pools or identities.

**Redis:** Confirm account/region and provider-supported topology before failover or resizing; review connection effects.

**Snowflake:** Separate administrative and workload roles; verify account/organization identifiers and grants before modifying warehouses.

**Kafka/MSK:** Confirm VPC/account and broker AZs; avoid applying provider upgrades alongside production broker changes.

## 13. Troubleshooting matrix

| Symptom | Likely cause | Safe response |
|---|---|---|
| Provider not found | Incorrect source or mirror | Check required_providers and registry |
| Failed to query versions | Network, constraint conflict | Inspect constraints, proxy and mirror |
| Lockfile inconsistent | Dependency changed without init | Re-run reviewed init; commit lock diff |
| Missing provider alias | Child configuration_aliases/wiring | Declare and pass alias |
| Wrong region/account | Default provider or stale credentials | Verify caller identity before plan |
| AccessDenied/403 | Insufficient or wrong principal | Inspect least-privilege grants |
| Expired token | Short-lived auth session | Renew federation; never commit token |
| Wrong Azure subscription | CLI/default selection mismatch | Explicitly verify tenant/subscription |
| Wrong GCP project | Project/impersonation mismatch | Verify project and service account |
| Kubernetes forbidden | Context/RBAC mismatch | Check context, identity and namespace |
| Unexpected replacement | Provider schema/default upgrade | Stop, review changelog and plan |
| State lock conflict | Concurrent change | Coordinate; do not force-unlock blindly |

## 14. Production runbooks

**Provider onboarding:** validate source/publisher, provider version matrix, registry trust and plugin mirror -> configure root provider and aliases -> bind workload identity -> verify target account -> test staging -> review plan -> approve production.

**Provider upgrade:** freeze unrelated changes -> snapshot state/backend metadata -> update constraint and lock in branch -> inspect changelog -> validate/tests/plan -> identify replacements -> DBRE approval -> controlled rollout -> observe and rollback code/lock if needed.

**Wrong account or region:** stop apply immediately -> record current caller identity and backend -> assess unintended changes -> preserve evidence -> recover through approved plan, not manual blind state edits.

**Authentication outage:** identify provider versus backend credentials -> renew federated session -> verify permissions and identity -> retry a fresh plan; never paste tokens into logs.

**Production DR region:** verify separate credentials, KMS/CMK, backup copy, networking and replication health; conduct a restore drill. Alias selection is not a DR strategy.

## 15. Acceptance rubric

| Dimension | Points |
|---|---:|
| Provider architecture and source/version reasoning | 20 |
| Aliases and module provider wiring | 20 |
| Secure authentication and identity verification | 20 |
| Offline lab and deterministic plan | 15 |
| Policy/unit tests and negative drills | 15 |
| Runbooks, cleanup and audit evidence | 10 |

Pass at 85/100 with zero critical failures. Critical: applying to unverified account, committing secrets/state, unapproved production replacement, bypassing state lock, or trusting a fake manifest as proof of live identity. Record CLI versions, policy results, plan exit code, reviewed provider/lockfile diff and sanitized approval evidence.

## 16. Knowledge check

What is the difference between provider source and provider configuration? Does an alias choose a different plugin version? Why is the lock file committed? What happens when child modules require aliases? How do AWS provider and backend identities differ? How do you prove Azure subscription scope? Why is a Kubernetes context dangerous? When should init -upgrade be used? Why is the offline manifest only an educational policy? What evidence is required before an RDS provider upgrade?

**Next:** Chapter 022 — Terraform Provider Dependencies, Implicit and Explicit Resource Graphs and Lifecycle Ordering.
