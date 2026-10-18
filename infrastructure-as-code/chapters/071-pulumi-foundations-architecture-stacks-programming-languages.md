# Chapter 071 — Pulumi Foundations, Architecture, Stacks and Infrastructure as Code with Programming Languages

**Part 15 — Pulumi · Chapter 071/120 · Enterprise SRE/DevOps/DBRE**

## Learning objectives and prerequisites

Explain Pulumi's desired-state engine, resource providers, SDKs, stack configuration, state/backends, outputs and dependency graph. Write a working Python Pulumi project using **local-only resources**, inspect previews, protect secrets, test governance, and design a safe production delivery pipeline. Python 3.10+, Pulumi CLI and \`pip\` are recommended for native execution. The separate Python policy tests need only Python 3.9+. No cloud account, credentials, paid resources or local Docker daemon are required.

## 1. Architecture and operational model

~~~text
Source Git / pull request / change approval
                 |
Python Pulumi program + packages + tests
                 |
        Pulumi CLI / Automation API
                 |
  stack configuration / secrets provider
                 |
  backend (Pulumi Cloud or self-managed)
                 |
   engine: refresh / preview / update
                 |
 resource graph -> provider plugins -> APIs
                 |
    stack outputs / audit / SLO / drift
~~~

Pulumi uses general-purpose languages (TypeScript/JavaScript, Python, Go, C#, Java and YAML) to declare resources. The language host executes the program and registers resources with the engine; providers then reconcile resource changes. The preview is a plan, not a guarantee that the eventual update succeeds. Pulumi state records resource identities and dependencies; protect it as sensitive operational data. \`pulumi refresh\` reconciles observed resource state and may affect subsequent plans; review changes before adoption.

## 2. Stacks, configuration and backends

A **project** contains the Pulumi program and \`Pulumi.yaml\`. A **stack** is an isolated instance of the project with configuration and state. \`pulumi stack init\`, \`pulumi config set\`, \`pulumi preview\`, \`pulumi up\`, \`pulumi refresh\` and \`pulumi destroy\` are lifecycle commands; never run update/destroy on unverified production stacks.

Backends can include Pulumi Cloud or supported self-managed object storage/local filesystem. This chapter uses \`file://\` local state in a disposable directory. A local backend is appropriate for learning, **not enterprise HA/DR**. State must have encryption, access control, versioning, retention, audit and restore evidence in production. Stack names, organization/project scoping and secrets-provider selection vary by backend. Pulumi configuration secrets should use \`pulumi config set --secret\`; do not put tokens in source, plaintext config, outputs or CI logs.

## 3. Resource graph, Inputs and Outputs

Resources accept \`Input[T]\` values, which can be plain values or asynchronous \`Output[T]\` values. Use \`apply\` to transform outputs when required; avoid assuming resource IDs exist before provisioning. Explicit \`depends_on\` is useful for dependencies not inferred from property references. Protect important resources with \`protect=True\`, use \`ignore_changes\` narrowly, and review replacements and aliases before renaming resources. Provider versions and Python dependencies must be pinned and reviewed.

### Architecture exercise
Model a database service with separate network, identity, storage, database, monitoring and backup components. Specify dependencies, secrets, capacity, failover and SLO gates. Do **not** connect this lab to a real database.

## 4. Executable Lab A — Local-only Pulumi program

The accompanying project uses the Pulumi **command provider** to write a marker file in a local sandbox, demonstrating stack outputs, inputs and resource lifecycle. This intentionally invokes a local shell command; review any \`command\` provider usage carefully and never pass secrets to shell arguments. The lab uses a harmless marker only. It requires \`pulumi-command\` Python SDK and matching Pulumi command provider plugin, installed on demand by Pulumi.

~~~bash
cd infrastructure-as-code/labs/chapter-071
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
bash run-preflight.sh
~~~

For a **native** Pulumi rehearsal, explicitly opt in after reviewing the program and dependencies:

~~~bash
export PULUMI_CONFIG_PASSPHRASE="choose-a-disposable-lab-only-passphrase"
export PULUMI_BACKEND_URL="file://$(pwd)/.pulumi-state"
pulumi login "$PULUMI_BACKEND_URL"
pulumi stack init dev
pulumi config set environment lab
pulumi preview --diff
pulumi up --yes
pulumi stack output
pulumi preview --diff
pulumi destroy --yes
~~~

Use a **disposable** lab passphrase only; do not reuse enterprise credentials. The example is deliberately local-only but \`pulumi up\` does execute a local shell command. State and sandbox artifacts are ignored by Git. If \`pulumi stack init dev\` reports an existing stack, inspect the current stack before proceeding.

## 5. Executable Lab B — Fail-closed governance

~~~bash
python3 pulumi_gate.py fixtures/safe.json policy.json
python3 pulumi_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_pulumi_gate.py
~~~

The safe evidence should pass; the unsafe evidence must fail. The Python gate checks **declared change evidence and a small static source contract**. It is not a Pulumi AST parser, state inspector, secrets scanner, provider-policy evaluator or cloud IAM verifier.

## 6. Executable Lab C — Stack and state recovery tabletop

Simulate a preview containing replacement of an RDS primary, unauthorized \`pulumi destroy\`, leaked config secret, stale state and backend outage. Record resource URNs, dependency order, provider version, last-known-good stack export, protected resource list and recovery approval. Do not run \`pulumi state delete\` or manual state edits on production without a separate recovery plan and backup. Importing an existing resource requires carefully verified identifiers and ownership.

## 7. Enterprise delivery workflow

1. Verify repository revision, dependency lock and provider plugin provenance.
2. Select backend, organization/project/stack and cloud identity; fail on mismatches.
3. Resolve encrypted secrets through approved provider; enforce least privilege.
4. Run unit tests, policy gate, lint and \`pulumi preview --diff\`.
5. Review creates, updates, replacements and deletes; require SRE/DBRE approvals.
6. Verify backups/PITR, restore tests, replica quorum, capacity and error budgets.
7. Deploy canary with concurrency and blast-radius controls.
8. Validate SLO, audit trail, stack outputs and drift; hand over operational evidence.

## 8. Production SRE/DBRE incident scenarios

| Incident | Detection | Containment |
|---|---|---|
| Wrong Pulumi stack | stack identity mismatch | abort |
| Wrong backend | state URL mismatch | stop |
| Leaked config secret | CI audit | rotate/revoke |
| State backend outage | failed preview | freeze |
| State lock conflict | concurrent operation | identify owner |
| Provider plugin mismatch | version diff | pin and rebuild |
| SDK supply-chain issue | checksum finding | quarantine |
| Preview differs from update | resource drift | halt and re-preview |
| Protected resource deletion | protection failure | investigate |
| Unapproved destroy | change-policy alert | block |
| Unexpected replacement | diff contains replace | DBRE review |
| RDS failover | connection errors | assess replicas/PITR |
| Aurora replica lag | replication alarm | stop rollout |
| PostgreSQL connection saturation | pool alert | capacity gate |
| MongoDB primary stepdown | election alert | preserve quorum |
| Redis failover | p99 regression | client health gate |
| MSK broker replacement | ISR shrink | halt |
| OpenSearch shard pressure | disk/latency | capacity plan |
| EKS workload disruption | PDB errors | adjust rollout |
| AKS node drain blocked | pod eviction failure | halt |
| Backup validation failed | restore checksum | block stateful change |
| State corruption | resource URN mismatch | restore state backup |
| Drift after hotfix | refresh delta | reconcile owner |
| Policy pack bypass | missing approval | reject |
| Provider rate limiting | 429 errors | bounded retry |
| Orphaned cloud resource | cost drift | owner cleanup |
| Output contains secret | sensitive log | rotate/redact |
| Canary SLO regression | error budget burn | stop rollout |

## 9. Production runbooks

**R1 Stack identity:** inspect \`pulumi stack\`, backend URL, project, organization, environment and cloud account.

**R2 Secrets:** revoke leaked credentials, review config encryption, restrict outputs and audit access.

**R3 Preview/change approval:** review replacement/deletion, resource protection, provider upgrades and approvals.

**R4 State lock/outage:** preserve logs, identify active operation and avoid manual lock/state surgery.

**R5 Drift:** review \`pulumi refresh --preview-only\` where supported by installed CLI; reconcile manual changes safely.

**R6 DBRE change:** verify PITR, backup, replica/quorum, RPO/RTO and restore evidence before updates.

**R7 Failed update:** inspect stack events, provider error, last-known-good checkpoint and recovery options.

**R8 Identity/permissions:** validate least-privilege provider credentials and target account before retry.

**R9 FinOps:** inventory orphaned resources, provider SKUs, tags, budgets and ownership.

**R10 Post-change:** validate SLO, backup, stack outputs, state encryption, monitoring and handover.

## 10. 100-point acceptance

| Domain | Points |
|---|---:|
| Pulumi architecture, engine and providers | 20 |
| Stacks, state, configuration and secrets | 20 |
| Executable local program and resource graph | 15 |
| Governance, preview and CI/CD controls | 15 |
| Automated tests and negative fixtures | 15 |
| SRE/DBRE incidents, runbooks and DR | 15 |
| **Total** | **100** |

Pass >=85 with zero critical findings. Critical failures include wrong stack/account, unauthorized destroy/replacement, plaintext secret, corrupt/unrecoverable state, missing backup or unapproved database operation. Require signed reviewer evidence and actual native CLI logs for production acceptance.

**Status:** published educational artifacts. Offline unit tests, Pulumi CLI execution and production integration remain pending.

**Next proposed:** Chapter 072 — Pulumi Resource Models, Providers, Components and Dependency Management.
