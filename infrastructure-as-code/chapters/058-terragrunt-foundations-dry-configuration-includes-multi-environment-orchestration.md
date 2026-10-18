# Chapter 058 — Terragrunt Foundations, DRY Configuration, Includes and Multi-Environment Orchestration

**Part 12 — OpenTofu and Terragrunt | Chapter 058 of 120**  
**Audience:** Platform SRE, DBRE, DevOps, IaC and security engineers.  
**Prerequisites:** Chapters 056–057; pinned OpenTofu/Terragrunt CLI, Python 3.9+, disposable lab.  
**Execution boundary:** The runnable lab uses local OpenTofu \`terraform_data\` resources; it creates no cloud infrastructure. A declared policy pass is not proof of live remote state, RBAC, networking or database controls.

## 1. Learning outcomes

- Explain Terragrunt as an orchestration and configuration layer for Terraform/OpenTofu rather than an independent infrastructure provider.
- Build a maintainable live infrastructure layout with reusable modules and isolated environment/account/region roots.
- Use \`include\`, \`find_in_parent_folders\`, \`read_terragrunt_config\`, \`locals\`, \`inputs\`, \`dependency\` and \`dependencies\` deliberately.
- Generate backend/provider configuration safely, pin module revisions and toolchain versions, and prevent backend-key collisions.
- Apply dependency-aware orchestration, bounded concurrency, failure isolation and gated promotion.
- Execute offline OpenTofu contracts and Python policy tests, diagnose failures and perform SRE/DBRE recovery.

## 2. Architecture and ownership

~~~text
git protected branch + change approval
               |
  policy / lint / CI identity / plan gate
               |
      Terragrunt live root
   environments/{dev,staging,prod}
      |             |
   region/account  region/account
      |             |
      v             v
   network -> identity -> cluster -> data -> apps
      |          |           |
    module     module      module
      +----------------------+
      pinned OpenTofu/Terraform modules
               |
      per-unit encrypted remote state
        lock + version + audit
               |
   DBRE/SRE health and drift verification
~~~

Terragrunt manages configuration composition, remote state conventions and execution order. The underlying engine remains responsible for provider operations and actual infrastructure. An \`include\` merges configuration according to Terragrunt's documented merge behavior; \`dependency\` consumes upstream outputs and imposes ordering, while \`dependencies\` establishes ordering without outputs. Never treat either as a substitute for a real cross-system readiness check.

## 3. Repository layout and DRY strategy

~~~text
infrastructure-live/
  root.hcl                 # shared backend/provider defaults
  account.hcl              # account identity metadata
  region.hcl               # region defaults
  environments/
    dev/us-east-1/
      network/terragrunt.hcl
      database/terragrunt.hcl
    prod/us-east-1/
      network/terragrunt.hcl
      database/terragrunt.hcl
infrastructure-modules/
  network/
  database/
~~~

**DRY is not permission to hide critical production differences.** Keep environment-specific RPO/RTO, retention, deletion protection, replication, KMS, instance sizing and database backup requirements explicit and reviewable. Split remote state by unit, environment, account and region. Make backend keys unique and deterministic; do not allow two live units to target the same key.

## 4. Terragrunt primitives

**\`include\` and \`find_in_parent_folders\`:** share root configuration. Favor explicit include paths and review merge precedence. Parent and child \`locals\` have specific scoping rules; do not assume arbitrary parent locals are automatically visible in child expressions. Expose shared values via inputs or supported exposed includes.

**\`read_terragrunt_config\`:** load a separate account/region metadata file. Treat its output as configuration, not secret storage.

**\`inputs\`:** pass typed module variables. Review how Terragrunt serializes values to the underlying engine. Validate required variables in the module itself.

**\`terraform.source\`:** pin a module version, immutable commit or approved artifact. Do not point production at a mutable main branch.

**\`generate\`:** emit provider/backend files consistently. Ensure the generated path, permissions and overwrite behavior are deliberate. Generated backend files must not expose secrets in Git or CI logs.

**\`dependency\`:** use output contracts for dependencies. The upstream state must already exist or the dependency must be explicitly mocked in a safe validation workflow. Do not use mocked database IDs for production applies.

**\`dependencies\`:** order units that have no required outputs. Cycles must fail and be redesigned.

**Run-all orchestration:** CLI subcommands and syntax differ by Terragrunt version. Modern versions use the \`run --all\` form; older versions may use \`run-all\`. Pin and verify the installed version, then use the exact documented syntax. A graph is not a transaction: partial failures leave some units applied.

## 5. Example: review-only Terragrunt configurations

See \`labs/chapter-058/examples/\` for:
- \`root.hcl.example\` — shared remote state and module policy conventions.
- \`network/terragrunt.hcl.example\` — pinned module source and isolated backend key.
- \`database/terragrunt.hcl.example\` — upstream network outputs and DBRE inputs.
- \`readonly-diagnostics.sh.example\` — version checks and read-only inventory.

These are **illustrations**, not a deployable production backend. Replace placeholder account, bucket, module source, identity and version with approved values before any actual use.

## 6. Lab A — Offline OpenTofu orchestration contracts

~~~bash
cd infrastructure-as-code/labs/chapter-058
tofu version
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
tofu plan -var-file=environments/dev.tfvars -out=dev.tfplan
tofu apply dev.tfplan
tofu output -json
tofu state list
tofu destroy -var-file=environments/dev.tfvars
~~~

Four \`terraform_data\` resources model composition, state isolation, dependency orchestration and operational readiness. The dev/prod tfvars files demonstrate different root names and backend keys; they do **not** configure remote state. Production preconditions require declared safeguards. Do not run \`destroy\` on any real stateful root.

## 7. Lab B — Policy-as-code and automated negative tests

~~~bash
python3 terragrunt_gate.py fixtures/terragrunt-safe.json fixtures/plan-safe.json terragrunt-policy.json
python3 terragrunt_gate.py fixtures/terragrunt-unsafe.json fixtures/plan-destructive.json terragrunt-policy.json
python3 -m unittest -v test_terragrunt_gate.py
bash run-preflight.sh
~~~

Expected: safe fixture passes; unsafe/destructive fixtures fail. Tests mutate environment identity, backend key, pinned module, dependency cycle, concurrency, DBRE approvals, change ticket, policy flags and plan actions. The fixture format is simplified and **not** native \`tofu show -json\`; adapt and test native plan parsing before any production enforcement.

## 8. Lab C — Dependency graph and promotion

1. Draw the graph \`network → identity → cluster → database → application\`.
2. Identify outputs required by each downstream unit and define stable, versioned contracts.
3. Pin Terragrunt/OpenTofu and module versions in CI; use separate plan artifacts per unit.
4. Apply only to disposable dev state after independent review.
5. Simulate failure after network succeeds but before database; observe that orchestration is not atomic.
6. Require explicit human approval for prod; verify state locks, backup, DB connectivity, rollout health and SLO before promotion.
7. Document recovery order, rollback limitations and state reconciliation.

## 9. Production SRE/DBRE incidents

| Incident | Signal | Investigation | Safe containment |
|---|---|---|---|
| Backend key collision | unexpected shared state | computed key, account/region | freeze all writers; isolate state |
| Concurrent unit applies | lock contention | CI jobs, graph, concurrency | stop overlapping writers |
| Dependency cycle | graph resolution error | \`dependency\` edges | split ownership or contract |
| Upstream output missing | evaluation fails | state, output contract | repair upstream; no prod mocks |
| Wrong include precedence | wrong tags/region | effective config | stop and fix hierarchy |
| Mutable module source | unexpected replacement | Git SHA/module cache | pin reviewed revision |
| Partial graph apply | network changed, DB failed | per-unit plans and logs | contain, reconcile, resume safely |
| Database replacement | destructive plan | DB lifecycle, provider schema | deny, involve DBRE |
| Connection storm after rollout | DB pool saturation | pod counts × pool size | throttle, backpressure |
| KMS/secret access failure | 403 or connection failure | workload identity, key policy | restore least-privilege access |
| Remote state outage | lock/backend errors | storage and audit | fail closed; use DR runbook |
| Secret in logs/state | security alert | CI outputs, backend access | revoke/rotate, preserve evidence |
| Prod region mismatch | wrong resource target | account/region config | stop, validate identity |
| Rollback divergence | drift after partial apply | state lineage and real IDs | forward repair/isolated restore |

## 10. Troubleshooting

~~~bash
terragrunt --version
tofu version
tofu fmt -check -recursive
tofu init -backend=false -input=false
tofu validate
tofu providers
python3 -m unittest -v test_terragrunt_gate.py
~~~

For a pinned Terragrunt release, use its documented graph, render and validate commands to inspect effective configuration without mutation. Avoid logging generated credentials, raw state or sensitive plan values.

## 11. Production runbooks

**R1 — Change preflight:** verify repo SHA, module pins, executor versions, account/region, backend uniqueness, lock owner, encrypted backup, DBRE/Security approvals and change ticket.

**R2 — Dependency graph failure:** identify cycle or missing output, freeze downstream applies, repair upstream contract and re-plan.

**R3 — Backend collision:** stop writers, capture audit/lineage/serial, determine authoritative state, migrate only under approved isolated procedure.

**R4 — Partial graph apply:** capture completed units, compare real resources, do not blindly rerun every unit, reconcile before resume.

**R5 — Database incident:** block unapproved replacement, validate PITR/snapshots, control retry storms, restore under DBRE leadership.

**R6 — Security event:** revoke exposed identities, audit generated files/state/CI, rotate secrets and enforce scoped OIDC.

**R7 — State/region DR:** recover versioned encrypted state to isolated backend, verify lineage and actual IDs, approve controlled failover.

**R8 — Post-change:** verify SLO, drift, DB connections, backup success, FinOps, ownership and incident notes.

## 12. 100-point acceptance

| Domain | Points |
|---|---:|
| DRY architecture, includes and config boundaries | 20 |
| Unique state keys, backend locks and security | 20 |
| Dependency graph, ordering and safe concurrency | 20 |
| Pinned modules and multi-environment promotion | 15 |
| Automated policy, negative tests and CI evidence | 10 |
| SRE/DBRE incidents, restore and runbooks | 15 |
| **Total** | **100** |

Pass **>=85/100** with zero critical findings. Critical failures: backend collisions, concurrent writers, unapproved database deletion, secret exposure, untested restore or prod apply with mock dependencies. Authoring and publication are not live operational acceptance.

## 13. Exit criteria and next chapter

Provide reviewed effective configurations, pinned versions, dependency graph, isolated backend mapping, CI test output, negative tests, restore drill, DBRE/Security approvals and a signed promotion plan.

**Next proposed:** Chapter 059 — Terragrunt Dependency Graphs, Remote State, CI/CD and Enterprise Orchestration.
