# Chapter 073 — Pulumi Stack Configuration, Secrets, State Backends and Enterprise Governance

**Part 15 — Pulumi · Chapter 073/120 · SRE/DevOps/DBRE**

## Objectives and prerequisites

Master Pulumi project/stack isolation, configuration and secret handling, state backends, encryption, locking/concurrent updates, stack exports/imports, drift, backup/restore, policy and operational governance. Prerequisites: Chapters 071–072; Python 3.10+, optional Pulumi CLI. The executable governance lab uses only the Python standard library; a separately opt-in local Pulumi CLI exercise requires Pulumi installation and a disposable lab passphrase.

## 1. Enterprise stack architecture

~~~text
Protected Git / PR / change approval
              |
Pulumi program / dependencies / tests
              |
    Stack selection and identity
    project + stack + backend URL
              |
Config namespaces / secret ciphertext
              |
    secrets provider / KMS trust
              |
Pulumi engine: preview / up / refresh
              |
backend checkpoint / lock / history
              |
provider APIs / infrastructure graph
              |
CloudTrail / Activity Log / metrics
              |
RPO/RTO / restore drill / audit trail
~~~

A Pulumi **project** is a code unit; a **stack** is an isolated deployment instance with its own configuration and state. A backend stores deployment checkpoints and operation history; state can contain sensitive inputs, provider outputs and resource metadata. The backend and secrets provider are distinct concerns. Treat stack identity, encryption keys, provider credentials and state backups as production-critical dependencies.

## 2. Stack configuration and secrets

Use \`pulumi config set key value\` for nonsecret settings and \`pulumi config set --secret key value\` for sensitive settings. Pulumi's secret metadata propagates through Outputs, but plaintext can still leak through logs, shell history, ad hoc print statements or incorrectly handled provider arguments. Avoid passing secret values on command lines in production; prefer approved secret injection workflows and short-lived workload identities.

Configuration can be scoped by project namespace; avoid accidental collisions. Do not commit real secrets, unencrypted state exports, KMS key material or personal access tokens. Pin stack environment, owner, region, account, retention, backup policy and recovery objectives.

## 3. State backends and encryption

Pulumi supports managed and self-managed backends. A local filesystem backend is useful for learning but not a high-availability enterprise control plane. Object-store backends require versioning, encryption, restricted access, backup, lifecycle policy and recoverability validation. Managed backends require their own organization access controls, audit and recovery policy.

**State backup and recovery:** \`pulumi stack export\` produces a sensitive checkpoint snapshot; protect it and restrict access. \`pulumi stack import\` can overwrite current state and must be approval-gated, performed only after validating stack identity, backup, resource URNs, provider versions and recovery ownership. Never hand-edit production state or remove a lock while an update may still be active. Review backend-specific concurrency guarantees.

## 4. Drift, refresh and lifecycle

\`pulumi preview\` compares desired program state against the recorded checkpoint and provider observations as appropriate; \`pulumi refresh\` updates the checkpoint to reflect observed provider state. Review refresh effects before applying changes. Drift caused by emergency hotfixes should be documented, owned and reconciled through code. Deleting a resource from source may propose deletion; \`protect\`, \`retain_on_delete\` and aliases have different operational semantics.

## 5. Hands-on lab A — Offline governance evidence

~~~bash
cd infrastructure-as-code/labs/chapter-073
python3 stack_gate.py fixtures/safe.json policy.json
python3 stack_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_stack_gate.py
bash run-preflight.sh
~~~

Safe evidence passes; unsafe evidence must fail. The policy gate validates a **declared evidence manifest** and a small static contract. It does not decrypt Pulumi secrets, inspect actual state, verify backend IAM, parse native CLI output or contact any cloud.

## 6. Hands-on lab B — Local-only stack configuration

The accompanying \`Pulumi.yaml\` and \`__main__.py\` export a nonsecret environment label only; **no resources are created**. Use an isolated directory and disposable passphrase. The following commands are optional:

~~~bash
cd infrastructure-as-code/labs/chapter-073
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export PULUMI_CONFIG_PASSPHRASE='disposable-lab-only-passphrase'
export PULUMI_BACKEND_URL="file://$(pwd)/.pulumi-state"
pulumi login "$PULUMI_BACKEND_URL"
pulumi stack init dev
pulumi config set environment lab
pulumi preview --diff
pulumi up --yes
pulumi stack output environment
pulumi stack export > .pulumi-state/ch073-export.json
~~~

The exported checkpoint is sensitive; this directory is Git-ignored. Inspect the selected stack and backend before running commands. Do not use real credentials in this exercise.

## 7. Hands-on lab C — Secret handling tabletop

Explain how a stack's encrypted secret differs from plaintext config, where encryption metadata lives, how a secrets-provider rotation or key loss affects recoverability, and how to avoid secret leakage through CI and stack outputs. Use synthetic placeholders only; do not commit actual secrets.

## 8. Hands-on lab D — Backup and restore simulation

Model backend outage, concurrent update, corrupted checkpoint and wrong-stack import. Write a recovery plan: freeze updates, establish stack identity, preserve backup, verify URNs, check KMS access, restore into an isolated environment, review preview, obtain approval and only then recover the intended stack. **No destructive state import is performed in this lab.**

## 9. Production SRE/DBRE incidents

| Incident | Detection | Containment |
|---|---|---|
| Wrong stack selected | identity mismatch | abort |
| Wrong backend | unexpected URL | freeze |
| Wrong AWS account | caller mismatch | stop |
| Wrong Azure subscription | target mismatch | stop |
| Wrong GCP project | project mismatch | stop |
| Secrets provider key lost | decrypt failure | preserve ciphertext |
| Secret in CI log | audit alert | rotate/revoke |
| Plaintext config committed | repository scan | revoke and remove |
| State checkpoint leaked | access alert | revoke and rotate |
| State backend unavailable | operation error | pause |
| Concurrent update | lock conflict | identify owner |
| Stale lock after crash | update status | investigate before unlock |
| Corrupt checkpoint | parse error | recover verified backup |
| Wrong-stack import | URN mismatch | block |
| Provider version drift | unexpected preview | pin |
| Drift after hotfix | refresh delta | reconcile |
| Protected resource deletion | protection error | review |
| Unexpected DB replacement | replace diff | DBRE approval |
| RDS snapshot missing | backup check | block |
| Aurora replica lag | lag alert | stop |
| PostgreSQL PITR gap | recovery test | block |
| MongoDB election instability | stepdown | preserve quorum |
| Redis failover | p99 spike | inspect clients |
| MSK ISR shrink | replica alert | freeze |
| OpenSearch disk pressure | latency | capacity remediation |
| EKS/AKS rollout disruption | PDB failures | halt |
| Backup retention expired | compliance finding | repair policy |
| KMS permission revoked | decrypt denied | scoped recovery |
| Canary SLO regression | error budget burn | stop |
| Audit evidence missing | compliance gap | block acceptance |

## 10. Runbooks

**R1 Identity:** verify project, stack, backend, provider account and environment before preview/update.

**R2 Secret incident:** revoke/rotate, restrict state and logs, review encryption and access.

**R3 Backend outage:** freeze updates, check backend health, preserve state evidence, avoid unsafe unlock.

**R4 Lock conflict:** identify active update owner and incident ticket; never force unlock blindly.

**R5 Checkpoint recovery:** verify encrypted backup, resource URNs, provider versions and restore isolation.

**R6 DBRE stateful change:** verify PITR, backup, replica quorum, RPO/RTO and restore drill.

**R7 Drift:** review refresh impact and reconcile manual changes via approved code.

**R8 Key rotation:** inventory stacks, secrets-provider dependencies and decrypt/re-encrypt plan.

**R9 FinOps:** review retained/orphaned resources, tags, budgets and state ownership.

**R10 Post-change:** validate outputs, state protection, monitoring, SLO and handover.

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Stack/project architecture and identity | 20 |
| Configuration, secrets and encryption | 20 |
| Backend, locking and checkpoint recovery | 20 |
| Governance and change control | 15 |
| Automated tests and negative fixtures | 15 |
| SRE/DBRE incidents and runbooks | 10 |
| **Total** | **100** |

Pass >=85 with zero critical findings. Critical: wrong stack/account, leaked plaintext secret, unapproved state import, unrecoverable encryption keys, missing backup or unauthorized DB replacement. Require test logs, authorized Pulumi preview, verified restore and signed approval before production acceptance.

**Status:** authored and published; unit tests, native CLI rehearsal, backend restore and operational acceptance pending.

**Next:** Chapter 074 — Pulumi Automation API, CI/CD Pipelines, Policy as Code and Enterprise Delivery.
