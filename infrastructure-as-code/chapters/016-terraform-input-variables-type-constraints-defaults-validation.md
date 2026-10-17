# Chapter 016 — Terraform Input Variables, Type Constraints, Defaults and Validation

**Part 04 — Variables and Expressions** | **Audience:** SRE, DBRE, Platform Engineering | **Lab cost:** $0 (built-in Terraform provider only) | **Publication status:** Published; live lab acceptance pending

## Objectives
Design reliable module input contracts using primitive, collection and structural types; set safe defaults; understand nullable and sensitive variables; apply validation rules and cross-variable constraints with version awareness; reason about input precedence; use per-environment tfvars without leaking credentials; run automated tests and operational preflight checks; diagnose production misconfiguration.

## 1. Architecture: input contract as an operational boundary

~~~text
Git-tracked variables.tf (type, validation, defaults)
          +
CLI/env/var-files (selected environment inputs)
          |
   Terraform variable evaluation and validation
          |
locals: normalized names / capacity / tags
          |
terraform_data resources (no-cloud lab)
          |
outputs -> plan review -> approval -> apply
~~~

Inputs form an API for the root module or reusable child module. A type constraint is not merely documentation: it rejects incompatible values or converts compatible ones to the declared type. Explicit validation catches syntactically valid but operationally unsafe settings before cloud changes.

## 2. Variable blocks and type system

~~~hcl
variable "environment" {
  type        = string
  description = "Environment boundary"
  default     = "dev"
  nullable    = false

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Use dev, staging or prod."
  }
}
~~~

**Primitive:** string, number, bool. **Collections:** list(T), set(T), map(T). **Structural:** object({ key = T }), tuple([T1, T2]). **Dynamic:** any (use sparingly). An object can contain optional attributes, for example \`optional(string, "standard")\`, when supported by the pinned CLI. Sets remove duplicates and have no meaningful positional order; convert to stable keys for resource for_each.

**Type conversion:** Terraform may coerce compatible values (for example \`"3"\` to a number) rather than rejecting every mismatched lexical representation. Do not assume coercion is a security control. Use explicit validation for ranges, enums and invariants.

**Defaults:** A default makes an input optional; omitting a default makes it required. Production-impacting settings should not silently inherit unsafe values. \`nullable = false\` prevents an explicit null value from bypassing a non-null input contract (exact behavior with defaults varies by Terraform version).

**Sensitive inputs:** \`sensitive = true\` masks many CLI displays, but does **not** remove the value from state or saved plans. Use short-lived credentials, workload identity and secret managers. Never commit real secrets in tfvars or environment dumps.

## 3. Validation and cross-variable constraints

~~~hcl
variable "replicas" {
  type = number
  validation {
    condition     = var.replicas >= 1 && var.replicas <= 12 && floor(var.replicas) == var.replicas
    error_message = "replicas must be an integer between 1 and 12."
  }
}
~~~

Terraform 1.9+ supports validation conditions referring to other input variables; earlier versions restrict validation references. This chapter deliberately uses **self-contained variable validations** compatible with Terraform >=1.5 and puts cross-variable operational checks into a preflight policy and a Terraform \`check\` block. Check-block failures are warnings in supported Terraform versions and must **not** be relied on as the only hard production gate. Use an explicit CI policy or suitable preconditions to fail closed.

For production, combine validation with policy-as-code, approved tfvars, identity/backend verification, plan review and DBRE sign-off.

## 4. Input precedence and environment isolation

Terraform variable values may come from defaults, \`TF_VAR_name\` environment variables, \`terraform.tfvars\`, \`terraform.tfvars.json\`, automatically loaded \`*.auto.tfvars\` / JSON files, explicit \`-var-file\`, and \`-var\`. Later applicable sources override earlier ones; explicit CLI assignments are highest precedence, and multiple explicit flags are processed in order. Avoid conflicting sources and do not put secret values on shell command lines, where process lists/history may expose them.

For a root module:
~~~bash
terraform plan -var-file=environments/dev.tfvars
terraform plan -var-file=environments/prod.tfvars
~~~
The provided example tfvars files contain only fictional metadata, not credentials. Environment labels alone do not isolate AWS accounts, Azure subscriptions, backends or IAM; verify those separately.

## 5. Lab structure and prerequisites

~~~text
labs/chapter-016/
  versions.tf
  variables.tf
  main.tf
  outputs.tf
  environments/dev.tfvars
  environments/prod.tfvars
  input-policy.json
  validate_inputs.py
  test_validate_inputs.py
  run-preflight.sh
  .gitignore
~~~

Terraform >=1.5 or compatible OpenTofu, Python 3.9+, Git. Use one CLI consistently. Linux/WSL2/macOS Bash commands below; PowerShell equivalents use \`py -3\` and \`$LASTEXITCODE\`. No cloud credentials or external providers required.

## 6. Lab A — Typed inputs and safe defaults

Review \`variables.tf\`: environment, service, owner, replicas, zones, tags, and database settings are strongly typed. \`main.tf\` normalizes inputs and creates a local \`terraform_data\` record.

~~~bash
cd infrastructure-as-code/labs/chapter-016
terraform fmt -check -recursive
terraform init -input=false
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=dev.tfplan
terraform show -no-color dev.tfplan
terraform apply dev.tfplan
terraform output -json
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "plan_exit=$?"
~~~

Expected: one \`terraform_data\` object created; second plan exits 0. Saved plans are sensitive even when inputs are fictional.

## 7. Lab B — Validation failures

Run these against the disposable lab; no apply:

~~~bash
terraform plan -var='environment=production'
terraform plan -var='replicas=0'
terraform plan -var='replicas=2.5'
terraform plan -var='service=INVALID_SERVICE'
terraform plan -var='zones=[]'
~~~

Each must fail input validation. Test an explicit \`null\` value in a disposable \`tfvars.json\` file to observe \`nullable = false\`. Restore the valid baseline.

## 8. Lab C — Environment-specific safety

~~~bash
terraform plan -var-file=environments/prod.tfvars
python3 validate_inputs.py environments/dev.tfvars input-policy.json
python3 validate_inputs.py environments/prod.tfvars input-policy.json
~~~

The Python policy checks that production database settings have at least two replicas, encryption and backup enabled, a named owner, and an explicit change ticket. It parses only the **simple string/number/bool assignments** used in these example tfvars files, not general HCL; real production policy should use Terraform plan JSON or a proper HCL parser. The policy checks production invariants as a hard gate because a Terraform \`check\` warning is not a reliable CI failure.

## 9. Lab D — Automated tests and failure injection

~~~bash
python3 -m unittest -v test_validate_inputs.py
bash run-preflight.sh
~~~

Tests cover valid dev/prod, invalid environment, unsafe prod replica count, missing backup/encryption, missing ticket/owner, malformed numeric inputs, duplicate keys and unsupported HCL syntax. Restore all files after negative drills. Preflight does not apply resources.

## 10. Lab E — Cleanup

~~~bash
terraform plan -destroy
terraform destroy
terraform state list
git status --short
~~~

The local state must be empty. Do not commit .terraform, state, saved plans, credentials, or secret tfvars.

## 11. Production SRE/DBRE scenarios

**RDS/Aurora:** Inputs for storage class, backups, encryption and deletion protection must have environment-specific hard controls. Require DBRE approval and restore evidence before a plan.

**PostgreSQL:** A number-like string may coerce into a valid but unsafe connection limit; use bounded validation and load testing.

**Elasticsearch/OpenSearch:** IOPS and throughput defaults unsuitable for search load can create storage bottlenecks. Require performance baselines, capacity approval and a rollback path.

**EKS:** A map of node pools needs stable keys and limits on min/max desired nodes. Avoid unbounded cost increases.

**AKS:** Subscription identity and backend isolation are independent of environment variable strings. Confirm actual Azure context.

**Redis:** Production replica count below HA minimum is an operational failure even if HCL type checking succeeds.

**Snowflake:** Warehouse size and auto-suspend inputs influence cost and latency; enforce allowed sizes and owner/cost center tags.

**Kafka/MSK:** Broker count and replication settings must respect quorum and partition availability; validate topology constraints and maintenance plans.

## 12. Troubleshooting

| Symptom | Likely cause | Safe response |
|---|---|---|
| No value for required variable | Missing default or input | Supply reviewed tfvars |
| Invalid value for variable | Type/validation mismatch | Correct input |
| Unexpected value despite tfvars | Higher precedence override | Inspect TF_VAR and CLI flags |
| Unknown variable in tfvars | Typo or module scope | Fix declaration/input |
| Null bypasses expectations | Nullable/default behavior | Set nullable=false, test |
| Sensitive output leaked | Inadequate secret handling | Contain, rotate, audit |
| Wrong prod account | Identity/backend mismatch | Stop, verify actual scope |
| Cross-variable check warns | Check block not a hard gate | Enforce CI policy |
| Unexpected cost | Oversized inputs | Review capacity and FinOps |
| State lock contention | Concurrent writer | Coordinate, never blind unlock |

## 13. Runbooks

**Input change review:** identify owner/environment/backend/identity → compare tfvars → validate types and business invariants → unit tests → fmt/init/validate → plan → cost and data-impact review → owner/DBRE approval → apply → SLO verification.

**Production validation failure:** stop pipeline → capture sanitized input sources → identify override precedence → correct reviewed values → rerun policy and plan → reapprove.

**Secret exposure:** restrict access, revoke/rotate, inspect state/plan/logs, use workload identity and secret manager; document incident.

**Capacity regression:** compare requested vs actual replicas/IOPS/storage → restore service under incident control → reconcile inputs in Git → test and document RCA/COA.

## 14. Acceptance checklist
- [ ] All input types/defaults/validations reviewed.
- [ ] dev and prod tfvars pass Python policy.
- [ ] Terraform fmt/init/validate and local apply pass.
- [ ] Invalid values fail as expected.
- [ ] Production HA/backup/encryption/ticket gates fail closed.
- [ ] Idempotent plan exits 0.
- [ ] No state, plan or secrets committed.
- [ ] Cleanup leaves no managed resources.

## 15. Knowledge check
Why can string values be converted to numbers? What does nullable=false do? Why does sensitive not protect state? Which variable sources override defaults? Why is a check block not a hard gate? How do stable map keys affect for_each? What should be validated for RDS backups? Why is an environment label insufficient for isolation? How do you detect unsafe production replicas? What is the proper recovery when validation fails during a release?

**Next:** Chapter 017 — Terraform Local Values, Expressions, Functions and Dynamic Configuration.
