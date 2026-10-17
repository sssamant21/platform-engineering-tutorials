# Chapter 019 — Terraform Conditional Expressions, Null Handling, try/can and Defensive Configuration Patterns

**Part 04 — Variables and Expressions** | **Audience:** SRE/DBRE and Platform Engineering | **Cost:** $0 local lab | **Status:** Published materials; live execution pending.

## Learning outcomes
Design safe optional configuration, understand null and unknown values, use conditional expressions, try/can, coalesce and lookup correctly, prevent unsafe fallbacks, enforce production invariants, test configuration errors, and operate Terraform changes with auditability and rollback plans.

## 1. Architecture: fail-closed configuration boundary

~~~text
typed inputs + optional object attributes
                |
   validation + defensive expressions
                |
       normalized locals
                |
   terraform_data configuration records
                |
 policy JSON + unit tests + plan review
                |
 owner/DBRE approval -> apply -> verify
~~~

A defensive expression makes a valid, well-understood absence explicit. It must not convert missing production controls into an apparently successful plan. Terraform's type system, preconditions, CI policies, change approvals and live environment verification each address different failure modes.

## 2. Conditional expressions

~~~hcl
locals {
  is_production = var.environment == "prod"
  capacity     = local.is_production ? max(var.replicas, 3) : var.replicas
  label        = var.display_name != null ? trimspace(var.display_name) : var.service
}
~~~

Both branches must have compatible types. A condition can be unknown during planning; avoid using apply-time unknowns to decide for_each keys or count. An expression with null is not the same as an unknown value: null is an explicit absence; unknown means the value will be determined later. Never infer that an unknown production setting is safe.

## 3. Null, optional attributes and defaults

~~~hcl
variable "database" {
  type = object({
    engine         = optional(string, "postgres")
    backup_enabled = optional(bool)
    replicas       = optional(number)
  })
}
~~~

With an optional attribute that has no default, Terraform provides null when absent. With a non-null optional default, omitted and explicitly null inputs receive that default. If a production backup flag is absent, **do not** silently assume backups are enabled. Prefer explicit values, validation and hard production gates.

Use nullable = false for required non-null root inputs, noting behavior around defaults and explicit null depends on the declared contract. Test nulls in isolated fixtures.

## 4. try, can, coalesce and lookup

| Function | Purpose | Caveat |
|---|---|---|
| try(a, b) | First expression without dynamic evaluation error | Does not replace explicit validation |
| can(expr) | Boolean indicating whether expression can evaluate without error | A false result should not trigger an unsafe default |
| coalesce(a, b) | First non-null/nonempty string candidate | May hide an omitted required field |
| lookup(map, key, default) | Safe map lookup with explicit default | Default must be operationally safe |
| coalescelist | First nonempty list | Still validate required list contents |

~~~hcl
locals {
  owner          = coalesce(var.owner, "platform-sre")
  requested_tier = try(var.settings.tier, "standard")
  has_email      = can(regex("^[^@]+@[^@]+$", var.contact_email))
}
~~~

The snippet is illustrative. Production owner and backup policy must be explicit rather than silently falling back to a placeholder. Terraform try catches **dynamic** expression errors; statically invalid references remain errors. can is commonly used inside input validation.

## 5. Safe and unsafe fallback patterns

**Safe:** optional display label -> service identifier; optional description -> empty string; absent noncritical tag -> documented default.

**Unsafe:** absent production backup -> false; unknown RDS deletion protection -> false; missing encryption -> false; invalid network CIDR -> 0.0.0.0/0; missing owner -> generic team without accountability; missing replica count -> 1 in HA production.

Never rely on a Terraform check block as the only production gate: a failed check assertion may warn rather than block. Use variable validation, lifecycle preconditions where appropriate, and a hard CI policy. Avoid treating a Python JSON fixture as proof of the Terraform plan.

## 6. No-cloud lab layout

~~~text
labs/chapter-019/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  environments/dev.json
  environments/prod.json
  defensive-policy.json
  defensive_policy.py
  test_defensive_policy.py
  run-preflight.sh
  .gitignore
~~~

Requires Terraform >=1.5 or compatible OpenTofu, Python 3.9+, Git and Bash/WSL2. No cloud provider credentials or paid resources.

## 7. Lab A — Defensive normalization

~~~bash
cd infrastructure-as-code/labs/chapter-019
terraform fmt -check -recursive
terraform init -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=chapter019.tfplan
terraform show -no-color chapter019.tfplan
terraform apply chapter019.tfplan
terraform output -json
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

Expected: one terraform_data record and a subsequent no-change plan exit 0. A saved plan may contain sensitive information and must never be committed.

## 8. Lab B — Console expression investigation

~~~bash
terraform console -var-file=environments/dev.tfvars
~~~

Evaluate:

~~~hcl
var.environment == "prod" ? "strict" : "standard"
coalesce(null, "fallback")
try({ a = 1 }["missing"], "absent")
can(regex("^[a-z]+$", "UPPER"))
lookup({ dev = 2 }, "prod", 3)
var.database.backup_enabled == null
~~~

Record values and explain why a safe optional label default differs from a dangerous production backup default. Exit with exit.

## 9. Lab C — Negative configuration drills

~~~bash
terraform plan -var='environment=production'
terraform plan -var='replicas=0'
terraform plan -var-file=environments/prod.tfvars -var='replicas=1'
terraform plan -var-file=environments/prod.tfvars -var='backup_enabled=false'
terraform plan -var-file=environments/prod.tfvars -var='encryption_enabled=false'
~~~

All commands above must fail validation or lifecycle preconditions. Do not apply invalid plans. For production, test missing optional values using a disposable copied configuration and verify fail-closed behavior.

## 10. Lab D — Offline production policy and unit tests

~~~bash
python3 defensive_policy.py environments/dev.json defensive-policy.json
python3 defensive_policy.py environments/prod.json defensive-policy.json
python3 -m unittest -v test_defensive_policy.py
bash run-preflight.sh
~~~

The validator uses JSON inputs only, not arbitrary HCL or live plan JSON. It rejects absent owner/change ticket, invalid environments, unsafe production backups/encryption/deletion protection, replica underprovisioning, null or nonboolean controls and unapproved public network CIDRs. The Python tests cover valid dev/prod, missing values, unsafe defaults, type mismatches and invalid policy schema.

## 11. Lab E — Cleanup

~~~bash
terraform plan -destroy
terraform destroy
terraform state list
git status --short
~~~

Expect empty state. Do not commit .terraform, state, plans, tfvars containing secrets, credentials or logs with sensitive output.

## 12. Production SRE/DBRE scenarios

**RDS/Aurora:** Optional backup retention, encryption and deletion protection must be explicitly set and checked in prod. An absent value is not approval to destroy or disable recovery.

**PostgreSQL:** Guard max_connections, WAL and replica topology against null defaults that can destabilize failover or exhaust memory.

**Elasticsearch/OpenSearch:** Missing storage IOPS/throughput inputs must not default to underprovisioned disks; require capacity evidence and workload baselines.

**EKS:** Optional node pool limits need bounded min/max and approved scaling defaults; avoid accidental single-node production capacity.

**AKS:** Missing subscription or identity must halt deployment rather than fall back to a developer context.

**Redis:** A null HA replica count must not become zero; validate memory headroom and failover design.

**Snowflake:** Missing owner, cost center or auto-suspend settings can cause uncontrolled spend and privilege drift.

**Kafka/MSK:** Replication factor, broker count and multi-AZ constraints must be explicit; do not silently weaken quorum.

## 13. Troubleshooting matrix

| Symptom | Likely cause | Safe response |
|---|---|---|
| Invalid function argument | Null or wrong type | Validate before evaluation |
| Invalid index | Missing map key | Use lookup/try for optional fields |
| Unsupported attribute | Optional object omitted | Normalize once in locals |
| Inconsistent conditional types | Branch type mismatch | Make types explicit |
| Unknown for_each keys | Apply-time dependency | Derive from known input keys |
| Production validation fails | Missing critical control | Fix reviewed inputs |
| check block warns but plan proceeds | Check is not hard gate | Enforce precondition/CI policy |
| Unexpected fallback | coalesce/try hides error | Remove unsafe default |
| Drift after apply | Remote change or bad defaults | Inspect state and API; reconcile |
| Sensitive value exposed | State/plan/log handling | Contain, rotate, audit |

## 14. Operational runbooks

**Normal change:** verify repo commit, environment, identity and backend -> input validation -> policy/unit tests -> fmt/init/validate -> plan -> inspect destructive actions -> owner/DBRE approval -> apply -> SLO and backup verification.

**Missing production control:** block deployment -> identify source precedence -> require explicit backup/encryption/HA values -> rerun policy and plan -> approve.

**Partial apply:** stop concurrent writers -> compare state and remote objects -> preserve data -> generate new plan -> review -> recover -> document RCA/COA.

**Incident configuration rollback:** restore service first, not just HCL -> identify null/fallback regression -> test safe input in staging -> controlled production reconciliation.

## 15. Acceptance rubric (100 points)

| Area | Points |
|---|---:|
| Conditional and null semantics | 20 |
| try/can/coalesce/lookup reasoning | 15 |
| Validated no-cloud lab | 20 |
| Negative tests and hard prod gates | 20 |
| SRE/DBRE scenarios and runbooks | 15 |
| Cleanup and evidence hygiene | 10 |

Pass 85+ without critical violations. Capture sanitized CLI versions, policy and test output, plan exit codes, approved changes and cleanup evidence. Authored tests are not automatically executed.

## 16. Knowledge check

How does null differ from unknown? When does try fail to catch an error? What does can prove? Why is coalesce unsafe for mandatory production backup flags? How do optional object defaults work? Why can a check warning be insufficient? Why must for_each keys be known? What should DBRE review before an RDS replacement? How does a failed partial apply affect state? How do you prove the production policy is enforced?

**Next:** Chapter 020 — Terraform Variables, Expressions and Defensive Configuration Production Capstone.
