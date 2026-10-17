# Chapter 025 — Terraform Providers, Dependencies and Lifecycle Production Capstone

**Part 05 — Providers and Dependencies (Final Capstone)** · **Audience:** SRE / DBRE / Platform Engineering · **Core lab:** Terraform >= 1.5, Python >= 3.9, Bash/WSL2 · **No cloud account or external providers needed** · **Publication is not execution acceptance**

## 1. Mission and outcomes

Build and defend a production-style IaC change workflow that combines Chapters 021–024: provider trust and identity, module input/output contracts, explicit and implicit dependency edges, Terraform lifecycle protection, preconditions/postconditions, deterministic plans, policy-as-code, incident simulations, and audited recovery.

You will deliver a no-cloud **network → database → application → monitoring → audit** dependency chain, a separately versioned provider/identity manifest, a fail-closed plan gate, unit tests, negative drills, and an operator sign-off. This lab uses \`terraform_data\` as a teaching stand-in; it does **not** deploy real RDS, Elasticsearch, Kubernetes, Redis or Kafka infrastructure.

## 2. Reference architecture

~~~text
                    Git revision / change ticket
                               |
                  policy: identity + provenance
                               |
               terraform init / fmt / validate
                               |
                 module network (contract v1)
                               |
                module database (contract v1)
                               |
             app resource --> monitoring resource
                               |
                    audit + lifecycle guard
                               |
                    saved Terraform plan
                               |
           terraform show -json --> plan gate
                               |
                   SRE/DBRE approval
                               |
                   apply saved plan
                               |
              state, health, SLO, audit review
~~~

**Control plane boundaries:** Terraform Core resolves graph dependencies; providers authenticate to target APIs; remote backends store state; policies examine selected review artifacts; external health probes verify reality. These are separate controls. An alias does not authenticate, a graph edge does not prove readiness, and a successful plan does not prove backup recoverability.

## 3. Provider trust and authentication

A provider source identifies the plugin, \`required_providers\` constrains acceptable versions, \`.terraform.lock.hcl\` records selected provider versions/checksums, and provider configurations select region/account and credentials. Root modules should own provider configurations; child modules declare requirements and receive aliases explicitly. Prefer short-lived workload identity federation or approved roles over static keys.

The **core executable lab uses only built-in \`terraform_data\`** and needs no cloud provider. The \`provider-manifest.json\` file documents a hypothetical AWS primary/DR deployment for policy review; it does not configure Terraform or prove real AWS identity. For a real rollout, verify STS caller identity, subscription/project, region, backend identity and permissions independently. Never commit tokens, keys, state or plans.

## 4. Dependencies and module boundaries

The network child module produces a typed versioned contract; the database child module consumes it and checks matching environment and schema. The root application references the database output; monitoring references application output; audit explicitly depends on monitoring. Terraform's DAG governs graph ordering but not asynchronous replication, readiness, DNS propagation or cutover.

Use explicit \`depends_on\` only when references cannot express a genuine dependency. Avoid cycles, overbroad module dependencies, apply-time unknown for_each keys, and sibling modules reading each other's internals.

## 5. Lifecycle protection and safe replacements

The database module has a **hard production precondition** requiring backups, encryption, deletion protection and at least three replicas. The audit resource uses \`prevent_destroy\`; the application resource uses \`create_before_destroy\` and \`triggers_replace\` for a controlled replacement exercise. A postcondition verifies the application contract.

**Important:** \`prevent_destroy\` blocks destruction only while the lifecycle rule is present in configuration; removing the resource block can remove the guard. \`create_before_destroy\` requires capacity and naming compatibility and cannot guarantee zero downtime. \`ignore_changes\` can mask dangerous drift. A plan with \`["create","delete"]\` or \`["delete","create"]\` is a replacement and is denied by the default policy.

## 6. Repository layout

~~~text
labs/chapter-025/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  modules/network/{variables,main,outputs}.tf
  modules/database/{variables,main,outputs}.tf
  environments/{dev,prod}.tfvars
  provider-manifest.json
  capstone-policy.json
  sample-safe-plan.json
  sample-replacement-plan.json
  capstone_policy.py
  test_capstone_policy.py
  run-preflight.sh
  .gitignore
~~~

The manifest and plan fixtures are **educational review inputs**, not a live provider configuration or substitute for checking real plan JSON and cloud identity. The plan validator handles actual \`terraform show -json\` resource-change actions, but its manifest review remains separate from the Terraform CLI and cloud API.

## 7. Lab A — Reproducible baseline

~~~bash
cd infrastructure-as-code/labs/chapter-025
terraform version
python3 --version
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform graph > graph.dot
terraform plan -var-file=environments/dev.tfvars -out=chapter025.tfplan
terraform show -json chapter025.tfplan > chapter025-plan.json
python3 capstone_policy.py provider-manifest.json chapter025-plan.json capstone-policy.json
terraform apply chapter025.tfplan
terraform state list
terraform output -json
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected resources: \`module.network.terraform_data.contract\`, \`module.database.terraform_data.contract\`, \`terraform_data.application\`, \`terraform_data.monitoring\`, \`terraform_data.audit\`. The second plan should exit 0. Do not run these commands against an existing production backend. \`terraform init -backend=false\` is used for the isolated lab; do not transplant this flag into production backend operations without understanding the backend lifecycle.

## 8. Lab B — Production contract and negative drills

Use a **separate disposable state directory** for production inputs; do not apply dev and prod var-files against the same state.

~~~bash
terraform plan -var-file=environments/prod.tfvars
terraform plan -var-file=environments/prod.tfvars -var='replicas=1'
terraform plan -var-file=environments/prod.tfvars -var='backup_enabled=false'
terraform plan -var-file=environments/prod.tfvars -var='encryption_enabled=false'
terraform plan -var-file=environments/prod.tfvars -var='deletion_protection=false'
~~~

The first is a valid *configuration contract* (still only a local simulation). Each negative variant must fail the database precondition. Never override safeguards to make an unsafe plan pass.

## 9. Lab C — Provider and plan policy

~~~bash
python3 capstone_policy.py provider-manifest.json sample-safe-plan.json capstone-policy.json
python3 capstone_policy.py provider-manifest.json sample-replacement-plan.json capstone-policy.json
python3 -m unittest -v test_capstone_policy.py
bash run-preflight.sh
~~~

The second command **must fail** because replacement is denied. The Python policy validates allowlisted provider source/alias/region/identity references, production change-ticket requirements, resource-type allowlists, plan action schemas and destructive operations. It does not inspect the real cloud caller identity, backups, application health, or state lock. A passing fixture is not sufficient production approval.

## 10. Lab D — Change and failure simulations

**Scenario 1 — Unauthorized provider:** change the manifest provider source to an untrusted namespace; the policy must deny it.

**Scenario 2 — Wrong region:** change primary to an unapproved region; deny. In real cloud operations, verify account and region with the provider API.

**Scenario 3 — Static credentials:** add an \`access_key\` field or replace the federated identity reference with a plaintext token; deny.

**Scenario 4 — Graph contract break:** change database module network schema to an unsupported version in a disposable copy; Terraform precondition must fail.

**Scenario 5 — Production safety:** set replicas to one, disable backup/encryption, or disable deletion protection; Terraform must fail.

**Scenario 6 — Replacement:** change \`release\` to v2; Terraform \`triggers_replace\` should plan application replacement. Save JSON and confirm the policy rejects the delete action. Do not apply an unapproved replacement.

**Scenario 7 — Lifecycle guard:** try a destroy plan while audit \`prevent_destroy\` is present; it should fail. Do not remove a guard from production.

**Scenario 8 — Partial apply:** tabletop a provider timeout after a database update. Freeze concurrent changes, inspect actual state, restore service, replan and seek approval; do not force-unlock or blindly edit state.

## 11. Plan gates and CI/CD workflow

A production pipeline should run pinned Terraform and Python, \`fmt\`, \`init -lockfile=readonly\`, \`validate\`, unit tests, static scans, plan, plan JSON inspection, policy, approval, and **apply the exact saved reviewed plan**. Protect state and plan artifacts as sensitive, enforce single-writer locking, and replan after changes to state or configuration. A no-cloud lab may not generate a provider lock file because it has no external providers.

Illustrative GitLab stages:

~~~yaml
stages: [validate, test, plan, policy, approve, apply]
# Pin a reviewed runner image; use federated identity and protected environments.
# Each stage must preserve only approved artifacts with limited retention.
# Never auto-apply production after a policy failure.
~~~

## 12. Production SRE/DBRE use cases

| Platform | Dependency and replacement hazard | Required out-of-band gate |
|---|---|---|
| RDS/Aurora | subnet/KMS/cluster/instance ordering; storage replacement | snapshot/PITR restore, replica lag, cutover |
| PostgreSQL | parameter, extension and instance changes | WAL, backups, failover drill |
| Elasticsearch/OpenSearch | node/storage replacement and shard movement | shard health, disk headroom, search SLO |
| EKS | IAM/VPC/node group and Kubernetes provider bootstrap | PDBs, draining, cluster readiness |
| AKS | subscription/identity/node pool replacement | quota, drain, RBAC and health |
| Redis | cache node replacement/failover | replica convergence, client retries |
| Snowflake | warehouse/grant role changes | least privilege, query/cost baselines |
| Kafka/MSK | broker/VPC/replication topology | ISR, quorum, consumer lag |

## 13. Troubleshooting

| Symptom | Likely cause | Operator response |
|---|---|---|
| Provider version conflict | incompatible constraints | review lock and module requirements |
| Wrong cloud account | default/expired identity | stop, verify caller and backend |
| Missing alias | child module wiring | declare configuration_aliases and pass providers |
| Cycle detected | circular reference/depends_on | inspect graph and split ownership |
| Data source deferred | unknown inputs or broad depends_on | inspect plan and dependency chain |
| Module contract mismatch | schema/env drift | version interface and migrate |
| Production precondition fails | unsafe backup/replica settings | correct input, do not bypass |
| Replacement denied | immutable field or trigger | create migration and rollback plan |
| prevent_destroy blocks cleanup | guard working | use disposable lab-only cleanup |
| Plan stale | state changed since review | replan and reapprove |
| Apply partially fails | API timeout, rate limit | inspect state/remote health, recover |
| Healthy Terraform, unhealthy DB | readiness outside IaC | follow DBRE incident runbook |

## 14. Production runbooks

**Change approval:** verify commit, identity, backend, lock, drift, backups, restore test, SLO baseline, plan JSON, replacement gate, DBRE owner approval and maintenance window.

**Wrong identity:** immediately stop apply; capture sanitized caller identity/account/region/backend, inspect potential impact, correct federation, replan, reapprove.

**Stateful replacement:** confirm capacity for dual running, snapshot/PITR, replica sync, DNS/client cutover, health gates, rollback and post-change validation.

**Policy failure:** preserve denial evidence, fix source input or propose reviewed exception outside the default fail-closed policy; never mutate policy in the same unreviewed change to force success.

**Partial apply / recovery:** freeze concurrent writers; inspect state and actual resources; prioritize data/service recovery; reconcile drift through a fresh reviewed plan; document RCA/COA.

**DR exercise:** prove restore and application connectivity against explicit RPO/RTO, not just Terraform resource creation.

## 15. Acceptance rubric (100 points)

| Area | Points |
|---|---:|
| Provider source, alias and authentication controls | 15 |
| Graph and cross-module contracts | 20 |
| Lifecycle and production preconditions | 20 |
| Reproducible local plan/apply and idempotence | 15 |
| Automated policy, tests and negative drills | 20 |
| Runbooks, recovery and audit evidence | 10 |

**Pass:** 85+ with no critical failures. Critical failures include plaintext credentials, unverified production identity, destructive plan bypass, missing backup/recovery evidence, cross-environment state reuse or unapproved guard removal.

Record sanitized versions, graph, policy output, plan action summary, unit-test evidence, production negative-drill results, and approved cleanup. **Publication is not proof that Terraform or tests have been executed.**

## 16. Cleanup and guardrail warning

The audit resource intentionally uses \`prevent_destroy\`, so a normal \`terraform destroy\` will be blocked. In a **disposable local-only copy**, obtain explicit lab cleanup approval, remove the audit lifecycle guard while retaining the resource, review a destroy plan, then destroy the simulated records and verify \`terraform state list\` is empty. Never use this technique against production data or remote state.

## 17. Final assessment questions

What does a provider alias select? Why is \`.terraform.lock.hcl\` reviewed? How does module output create an implicit edge? When is depends_on justified? What does a precondition block? What does postcondition fail to prove? Why is prevent_destroy not permanent? How does create_before_destroy change replacement ordering? What does a plan JSON replacement look like? Why is a JSON fixture not live evidence? How is state/backend identity verified? What constitutes a DBRE-safe rollback?

**Part 05 complete after Chapter 025 publication. Next: Chapter 026 — Terraform State Architecture, State Files, Metadata and Backend Fundamentals (Part 06 — State and Remote Backends).**
