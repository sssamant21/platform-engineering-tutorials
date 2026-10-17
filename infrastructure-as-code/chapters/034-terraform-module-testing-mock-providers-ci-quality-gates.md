# Chapter 034 — Terraform Module Testing, Mock Providers and CI Quality Gates

**Part 07 — Reusable Modules · Chapter 034/120**  
**Audience:** Platform Engineers, SREs, DBREs, DevSecOps · **Prerequisite:** Chapters 001–033  
**Tooling:** Terraform >=1.7 for \`mock_provider\` and \`override_resource\`, Python >=3.9; built-in \`terraform_data\` resources only.  
**Execution status:** Source and tests published; live Terraform execution and CI evidence must be collected separately.

## 1. Learning objectives

Create an enterprise Terraform module testing strategy that catches interface breakage, invalid configuration, unsafe replacements, insecure production defaults, stateful-service reliability regressions and accidental supply-chain changes **before** production apply. Implement Terraform native \`.tftest.hcl\` tests, mocked providers, overridden resources, Python policy/unit tests and CI quality gates.

## 2. Testing pyramid and production architecture

~~~text
Developer PR
   |
   +-- formatting + lint + static validation
   +-- Python policy unit tests + negative fixtures
   +-- terraform test (command = plan)
   |      +-- typed input/output assertions
   |      +-- mock_provider + override_resource
   |      +-- invalid input with expect_failures
   +-- disposable integration test (real provider, isolated state)
   +-- plan JSON + delete/replace deny policy
   +-- peer/DBRE approval + signed artifacts
   +-- production deployment under backend lock
   +-- DB health, SLO, backup, failover acceptance
~~~

**Test isolation:** child modules in one root share state. Separate root directories/backends and identities for dev, staging and prod. Mocked tests do not provision real resources, verify IAM, prove encryption or validate database recovery.

## 3. Native Terraform test language

Terraform's \`terraform test\` executes \`.tftest.hcl\` run blocks. \`command = plan\` evaluates a plan without applying; \`command = apply\` creates resources and must be confined to disposable environments. Assertions use \`assert\` with \`condition\` and \`error_message\`. \`expect_failures\` is for expected check failures, including variable validation and preconditions; verify that a negative test fails for the *intended* reason. \`mock_provider\` (Terraform 1.7+) allows testing provider-dependent configurations without real provider API calls; mocks are not replacements for real integration tests.

For a module with provider resources, use \`mock_provider "aws" {}\` or an appropriate provider, and use \`override_resource\` when a specific resource output must be deterministic. This chapter's executable lab uses Terraform's built-in \`terraform_data\` and a mocked **terraform** provider with an overridden network ID; no cloud credentials are required. Terraform's built-in \`terraform\` provider availability and mock support are verified by the CI \`terraform test\` step, not assumed as production evidence.

## 4. Module interface and composition

The root composes \`network -> database -> application\`. Every child returns a minimal typed contract with \`schema_version = 1\`. Database preconditions reject environment mismatch and require backups, encryption and at least three replicas in prod. Application preconditions require a supported database schema and matching environment. Optional \`labels\` and \`settings\` demonstrate compatible interface evolution. \`sensitive\` suppresses routine output display but does not remove secrets from state; never store credentials in this lab.

## 5. Hands-on lab layout

~~~text
labs/chapter-034/
  versions.tf, variables.tf, main.tf, outputs.tf
  environments/dev.tfvars, environments/prod.tfvars
  modules/network/{versions.tf,variables.tf,main.tf,outputs.tf}
  modules/database/{versions.tf,variables.tf,main.tf,outputs.tf}
  modules/application/{versions.tf,variables.tf,main.tf,outputs.tf}
  tests/{contracts.tftest.hcl,negative.tftest.hcl,mocks.tftest.hcl}
  ci/{github-actions.yml.example,gitlab-ci.yml.example}
  fixtures/{architecture-safe.json,architecture-unsafe.json,plan-safe.json,plan-destructive.json}
  quality-policy.json, quality_gate.py, test_quality_gate.py, run-preflight.sh, .gitignore
~~~

## 6. Lab A — Local validation and native tests

~~~bash
cd infrastructure-as-code/labs/chapter-034
terraform version
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform test -verbose
python3 -m unittest -v test_quality_gate.py
~~~

Use Terraform >=1.7. Native tests use plan-only execution. An actual test run is required before recording results. If the mock test is unsupported in your pinned CLI, fail the quality gate rather than silently skipping it.

## 7. Lab B — Disposable integration and plan policy

~~~bash
terraform plan -var-file=environments/dev.tfvars -out=chapter034.tfplan
terraform show -json chapter034.tfplan > chapter034-plan.json
python3 quality_gate.py fixtures/architecture-safe.json fixtures/plan-safe.json quality-policy.json
python3 quality_gate.py fixtures/architecture-unsafe.json fixtures/plan-destructive.json quality-policy.json
terraform apply chapter034.tfplan
terraform output -json
terraform state list
terraform plan -var-file=environments/dev.tfvars -detailed-exitcode
echo "exit=$?"
~~~

The JSON policy fixtures are **synthetic**. The validator can also inspect real Terraform plan JSON for destructive actions when the real plan uses the allowed resource types, but the architecture manifest still contains declared controls that require independent verification. Never pass secrets or unredacted production plans to untrusted CI artifacts.

## 8. Lab C — Negative and mutation tests

- Set \`database_replicas=0\` and expect variable validation to fail.
- Set production \`backup_enabled=false\` and expect a precondition failure.
- Set production \`database_replicas=1\` and expect a precondition failure.
- Change a database contract \`schema_version\` and expect application rejection.
- Introduce a module dependency cycle; expect \`terraform validate\` failure.
- Introduce a plan action \`["delete","create"]\`; expect Python policy rejection.
- Remove a required attestation or production control; expect fail-closed rejection.
- Remove a test or weaken a policy control; CI must fail.
- Deliberately change a module output name and verify consumer contract failure.

Do negative tests in disposable copies; never induce database deletion or failover in production.

## 9. CI quality gates

1. **Preflight:** pinned Terraform version, trusted runner, least-privilege identity, format and validation.
2. **Native tests:** run all \`.tftest.hcl\` tests; do not allow \`continue-on-error\`.
3. **Policy:** positive and negative fixtures, Python unit tests and coverage review.
4. **Security:** scan dependencies, module source and secrets; review \`.terraform.lock.hcl\`.
5. **Integration:** isolated state, temporary infrastructure, strict teardown and cost guardrails.
6. **Plan:** save plan, convert to JSON, deny unapproved deletes/replacements, require code owner review.
7. **Release:** immutable artifact and provenance, promotion approval, rollback plan and audit trail.
8. **Post-deploy:** workload readiness, backup verification, latency and error-budget checks.

Example GitHub Actions and GitLab CI templates are included under \`ci/\`. They use no cloud provider; adapt with OIDC and approval controls before production use.

## 10. SRE/DBRE production scenarios

| System | Terraform test focus | Real operational acceptance |
|---|---|---|
| PostgreSQL / RDS / Aurora | encrypted backups, replica count, replacement denial | PITR/WAL, replication lag, failover and queries |
| Elasticsearch / OpenSearch | snapshot intent, node topology | shard allocation, recovery, p99 search latency |
| EKS / AKS | cluster version and node pool interfaces | rollout, PDB, persistent volume and API health |
| Redis | persistence/failover flags | replica sync, reconnect and latency |
| Kafka / MSK | broker/ACL/endpoint contract | ISR, consumer lag and produce/consume |
| Snowflake | warehouse and role contract | grant audits, workload and spend |
| MongoDB | backup and replica topology contract | quorum, restore and query checks |

## 11. Troubleshooting matrix

| Symptom | Cause | Safe remediation |
|---|---|---|
| \`terraform test\` command unavailable | CLI too old | install pinned Terraform >=1.7 |
| Mock override ignored | wrong resource address or mock scope | inspect test provider and override target |
| Test unexpectedly applies | \`command = apply\` or default run | explicitly use \`command = plan\` |
| Failed assertion with unknown | computed value unavailable at plan | mock deterministic value or test post-apply in sandbox |
| \`expect_failures\` passes unexpectedly | wrong failing object | target variable/check precisely |
| Module output missing | interface breaking change | pin compatible module and update consumers |
| Provider dependency failure | incompatible constraints | inspect \`terraform providers\`, lockfile |
| CI plan differs from local | inputs, CLI, provider or state | reproduce with pinned versions and same state snapshot |
| Destructive action rejected | real delete or replacement | investigate, never disable guard blindly |
| Apply succeeds but service fails | tests only checked configuration | invoke DBRE/SRE health runbook |

## 12. Production runbooks

**Module release:** code owner → typed contract review → native positive/negative tests → policy checks → isolated integration → plan diff → provenance and changelog → immutable release → staged promotion → SLO acceptance.

**CI failure:** freeze promotion → collect failing assertion and tool versions → identify input/source/provider drift → reproduce offline → repair module/test → re-run all gates → approve.

**Unexpected replacement:** stop apply → preserve plan and state backup → inspect address changes, provider behavior and \`moved\` blocks → DBRE approval → verify backups before any destructive action.

**Incident after upgrade:** halt concurrent applies → verify state lock → capture module/lockfile SHA and service health → roll back to compatible module version or reviewed migration → fresh plan → validate data and SLO. Git revert is not database restore.

**Secret exposure:** revoke credentials, contain CI logs/artifacts, rotate secrets, audit access and update least-privilege policy.

## 13. Acceptance rubric (100 points)

| Area | Points |
|---|---:|
| Native Terraform test coverage and mocks | 25 |
| Contract/negative tests | 20 |
| Policy and destructive-plan gates | 20 |
| CI security and release controls | 15 |
| SRE/DBRE integration evidence and runbooks | 20 |

Pass >=85 with no critical failures. Critical: unapproved destructive production plan, bypassed native tests, exposed credentials, cross-environment state, missing DB backup or a false recovery claim.

## 14. Cleanup and knowledge check

~~~bash
terraform destroy -var-file=environments/dev.tfvars
terraform state list
~~~

Destroy only the disposable local lab. Do not commit state, saved plans or credentials.

Questions: What does a mocked provider prove? Why use plan-only runs? What does \`expect_failures\` validate? What is the difference between a module contract test and a provider integration test? Why does the lockfile matter? What does a replacement action look like in plan JSON? How should a CI gate handle skipped tests? Why must a DBRE validate recovery separately? What does a Git rollback *not* restore? How should a production release be promoted?

**Next: Chapter 035 — Terraform Reusable Modules Production Engineering Capstone.**
