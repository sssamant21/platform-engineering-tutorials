# Chapter 074 — Pulumi Automation API, CI/CD Pipelines, Policy as Code and Enterprise Delivery

**Part 15 — Pulumi · Chapter 074/120 · Enterprise SRE/DevOps/DBRE**

## Outcomes and prerequisites

Build controlled infrastructure delivery with Pulumi Automation API, CI/CD approval gates, policy-as-code, workload identity, audit evidence and SLO-aware rollback decisions. Design for GitLab CI, GitHub Actions and enterprise deployment orchestration. Understand Automation API's execution model, stack lifecycle, deployment concurrency and failure recovery. Prerequisites: Chapters 071–073; Python 3.10+, optional Pulumi CLI and SDK for native lab. The offline policy/test suite needs Python 3.9+ only. No cloud account is required.

## 1. Reference architecture

~~~text
PR + signed commit + change ticket
             |
Static lint / unit tests / dependency scan
             |
Governance policy / provider target verification
             |
CI workload identity federation (short-lived)
             |
Pulumi Automation API orchestrator
             |
  stack selection -> refresh? -> preview
             |
Security + SRE + DBRE approval / backup evidence
             |
  canary up -> telemetry / SLO gate
             |
  controlled environment promotion
             |
CloudTrail / Azure Activity Log / Pulumi audit
             |
state checkpoints / recovery / postmortem
~~~

The Automation API embeds Pulumi's engine workflow into a program; it does not replace the Pulumi CLI or providers. A language host, backend and provider plugins are still required for real previews and updates. The API can create/select stacks, configure them, preview, update, refresh and destroy. An Automation API process is a **deployment orchestrator**, not an authorization boundary: enforce account identity, RBAC, approvals and policies independently.

## 2. CI/CD design and security

Separate pull-request validation from deployment. PR jobs run syntax, unit, security and policy checks without privileged credentials. Protected environment jobs require approval, verified stack identity, short-lived federated credentials, provider target matrix and a fresh preview. Pin Pulumi CLI, SDK, plugins, Python dependencies and runner image; verify provenance. Use protected branches, CODEOWNERS, artifact retention and immutable preview evidence. Never place secrets in CI variables in plaintext when federation or a secret manager is available.

**GitLab CI example** (review and adapt; not enabled automatically):

~~~yaml
stages: [test, preview, deploy]
policy_test:
  stage: test
  image: python:3.12
  script:
    - cd infrastructure-as-code/labs/chapter-074
    - python -m unittest -v test_delivery_gate.py
    - python delivery_gate.py fixtures/safe.json policy.json
preview:
  stage: preview
  when: manual
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
  script:
    - echo "Implement approved short-lived identity and Pulumi preview here"
deploy:
  stage: deploy
  when: manual
  environment: production
  script:
    - echo "Deployment intentionally disabled in example"
~~~

The example has placeholders, not production deployment automation. Do not treat manual jobs alone as sufficient authorization.

## 3. Policy as code and deployment contracts

Policy enforcement may use Pulumi CrossGuard policy packs, organization-level policies and CI checks. CrossGuard policies can validate resource properties; some enforcement capabilities vary by edition and workflow. This lab uses an independent **declared-evidence policy gate**, not CrossGuard. Required controls: identity and target verification, least privilege, signed change ticket, no unauthorized destroy, no stateful replacement, approved preview, backup/restore evidence, DBRE approval, canary, SLO and audit.

Policy inputs must be trusted: a self-asserted JSON manifest is insufficient as a production attestation. Production pipelines should obtain evidence directly from CI identity, cloud account APIs, signed approvals, Pulumi preview JSON, backup systems and monitoring.

## 4. Automation API fundamentals

Use \`pulumi.automation\` to select/create a stack, configure it and run preview/update with event callbacks. Handle operation locks, cancellation, timeouts, transient API errors and partial failure. Never assume a failed update is rolled back automatically. Capture operation summaries, changed resource URNs, logs and stack checkpoints. A preview may become stale between approval and execution; revalidate the target and rerun a preview close to apply time.

### Lab A — Offline automation workflow simulator

~~~bash
cd infrastructure-as-code/labs/chapter-074
python3 delivery_gate.py fixtures/safe.json policy.json
python3 delivery_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_delivery_gate.py
python3 -m unittest -v test_pipeline.py
bash run-preflight.sh
~~~

The simulator models \`validate -> preview -> approve -> canary -> health -> promote\`, fails closed on missing gates, and does not invoke cloud providers or Pulumi.

### Lab B — Optional native Automation API read-only preview

Install Pulumi CLI and Python SDK in an isolated virtual environment, then run \`python3 automation_preview.py\` only after setting an isolated local backend and passphrase. The program selects/creates a **no-resource local Pulumi stack** and calls \`preview\`; it does not call \`up\` or \`destroy\`. See the lab README for setup and safety limitations.

### Lab C — Failure injection

Change one safe fixture property at a time: wrong stack, production account, unsigned change, missing OIDC federation, destructive change, database replacement, unreviewed preview, missing backup, failed canary or SLO breach. Confirm rejection. Simulate a CI job retry after a partial failure: require a fresh preview and human approval before retry.

### Lab D — Enterprise delivery tabletop

Design a two-cloud deployment with separate AWS and Azure stacks. Define environment promotion, concurrency, short-lived identity, provider pins, cross-cloud change windows, change-freeze rules, audit evidence, rollback decision tree, DBRE restore gates and error-budget policies. No real infrastructure is changed.

## 5. Production SRE/DBRE incidents

| Incident | Detection | Containment |
|---|---|---|
| Wrong stack selected | identity mismatch | abort |
| Wrong AWS account | caller mismatch | stop |
| Wrong Azure subscription | tenant/sub mismatch | stop |
| OIDC subject spoofing | claims mismatch | revoke |
| CI token leakage | audit alert | rotate |
| Privileged runner compromised | anomalous job | isolate |
| Pulumi CLI/SDK mismatch | version error | pin |
| Provider plugin tampering | digest mismatch | quarantine |
| Automation API lock | concurrent operation | identify owner |
| Stale preview | resource drift | re-preview |
| Approval bypass | missing signature | reject |
| CrossGuard policy failure | policy diagnostic | remediate |
| Policy pack unavailable | missing enforcement | fail closed |
| Destructive replace | preview replace | DBRE review |
| Failed update | partial state | freeze |
| RDS/Aurora replacement | data risk | PITR gate |
| PostgreSQL replica lag | replication alarm | stop |
| MongoDB primary election | topology alert | protect quorum |
| Redis failover | p99 regression | halt |
| MSK ISR shrink | under-replicated | halt |
| OpenSearch shard pressure | disk/latency | capacity plan |
| EKS rollout disruption | PDB error | stop |
| AKS node drain blocked | eviction failure | pause |
| Backup integrity failure | checksum error | block |
| State checkpoint loss | backend error | restore plan |
| Canary health regression | SLO burn | stop promotion |
| Cloud API throttling | 429 errors | bounded backoff |
| Secret output leaked | log scan | revoke |
| Audit evidence missing | compliance gap | reject |
| FinOps cost spike | budget alert | owner review |

## 6. Production runbooks

**R1 Pipeline preflight:** validate signed source, runner, project, stack, backend, account/subscription and provider pins.

**R2 Identity:** verify OIDC audience/subject, scoped role, token expiry and protected environment.

**R3 Preview review:** inspect creates, deletes, replacements, drift, policy findings and change approval.

**R4 Lock conflict:** identify active operation, preserve logs, never blindly clear locks.

**R5 Partial update:** freeze later stages, capture checkpoint and events, obtain SRE/DBRE recovery approval.

**R6 Stateful recovery:** verify PITR, backups, replicas, RPO/RTO and restore drill before database changes.

**R7 Canary SLO failure:** stop promotion, inspect telemetry, choose safe rollback/forward-fix with owners.

**R8 Supply chain:** quarantine tampered artifacts, revoke credentials and rebuild from pinned inputs.

**R9 FinOps:** review unexpected resource additions, retention, cost tags and budgets.

**R10 Post-deployment:** verify SLO, backup, state encryption, audit trail, drift and handover.

## 7. 100-point acceptance

| Domain | Points |
|---|---:|
| Automation API and architecture | 20 |
| CI/CD, identity and supply-chain controls | 20 |
| Policy as code and approval gates | 20 |
| Executable offline pipeline and tests | 15 |
| SRE/DBRE incidents, recovery and runbooks | 15 |
| Audit, observability and handover | 10 |
| **Total** | **100** |

Pass >=85 with zero critical findings. Critical: wrong target, unauthorized destroy/replacement, exposed credentials, missing restore evidence, bypassed policy, or unapproved production change. Require actual CI evidence, native preview, DBRE restore drill and signatures for production acceptance.

**Status:** authored and published; offline test execution, native Automation API preview and production operational acceptance pending.

**Next:** Chapter 075 — Pulumi Enterprise Platform Automation, Multi-Cloud SRE/DBRE Reliability Capstone.
