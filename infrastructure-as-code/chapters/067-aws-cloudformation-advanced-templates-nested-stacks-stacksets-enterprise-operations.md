# Chapter 067 — AWS CloudFormation Advanced Templates, Nested Stacks, StackSets and Enterprise Operations

**Part 14 — CloudFormation and Bicep · Chapter 067/120 · SRE/DBRE**

## Objectives and prerequisites
Design modular AWS CloudFormation templates, nested stacks, cross-stack exports, StackSets and multi-account deployment controls. Learn parameter contracts, Conditions, mappings, transforms, dependency graphs, stack drift, IAM execution roles, organizational guardrails, change sets, rollback and safe stateful infrastructure updates. Prerequisites: Chapter 066, Python 3.9+, optionally AWS CLI v2 with approved read-only access. The executable lab is **offline and does not create AWS resources**.

## 1. Architecture and ownership

~~~text
Git + protected PR + CI tests + approval
              |
      Template / policy bundle
              |
   parent stack (AWS regional)
       |               |
   nested network    nested app
       |               |
  outputs/contracts  exports/imports
              |
 StackSet administrator account
              |
  trusted execution role / Organizations
              |
   target account x region matrix
              |
 operations -> stack events -> drift -> SLO
~~~

Nested stacks use \`AWS::CloudFormation::Stack\` with a child \`TemplateURL\` (typically an immutable S3 object). The parent orchestrates child lifecycle; deletion and replacement can cascade. StackSets deploy stacks across selected accounts and regions, with service-managed or self-managed permissions, concurrency and failure tolerance. Their execution models and target restrictions must be verified per AWS configuration. Cross-stack exports can block changes when consumers import values. A template contract must distinguish logical IDs, physical resource identities and retained state.

## 2. Advanced template design

- **Parameters:** typed, bounded, named inputs; \`NoEcho\` is not a full secrets boundary.
- **Mappings and Conditions:** express supported environments explicitly; avoid environment-driven privilege expansion.
- **Intrinsic functions:** \`Ref\`, \`Fn::Sub\`, \`Fn::GetAtt\`, \`Fn::If\`, \`Fn::ImportValue\`, \`Fn::Join\` and \`AWS::NoValue\`; document references and replacement behavior.
- **Nested stacks:** version child templates; pin S3 object versions/digests and review parent/child outputs. Do not assume child updates are atomic.
- **Modules and macros:** understand transforms, registry types and third-party execution trust. Scan dependencies and enforce least privilege.
- **Resource lifecycle:** use \`DeletionPolicy\` and \`UpdateReplacePolicy\` for critical data; retained resources need owner, backup, cost and cleanup procedures.
- **Exports:** version interfaces and avoid cyclic dependencies or export renames that break consumers.
- **Change sets:** inspect Add/Modify/Remove, replacement, dynamic evaluations and IAM changes. Change-set output is not a guarantee of runtime success.

## 3. StackSets enterprise controls

Use a deliberate account/region allowlist, Organizations OU scoping, permission model, execution-role boundaries, operation preferences, failure tolerance and concurrency. Review auto-deployment behavior for newly added accounts and removal semantics for departing accounts. Guard against StackSet instances in the wrong OU, partially failed regions, stale targets, IAM role drift and quota exhaustion. Preserve a per-account/region audit matrix and verify successful instance status before declaring completion.

## 4. Executable offline labs

The lab provides a **parent template contract** and a **child template contract** in JSON. The parent contains a nested-stack resource with a deliberately nondeployable example \`TemplateURL\`; the local gate checks the contract, expected parameters and declared StackSet evidence. It does **not** fetch child templates, call AWS or parse native \`describe-stack-set-operation\` responses. Never deploy the sample URL.

~~~bash
cd infrastructure-as-code/labs/chapter-067
python3 stackset_gate.py parent-template.json child-template.json fixtures/safe.json policy.json
python3 stackset_gate.py parent-template.json child-template.json fixtures/unsafe.json policy.json
python3 -m unittest -v test_stackset_gate.py
bash run-preflight.sh
~~~

Expected: safe evidence passes; unsafe cross-account, region and destructive-operation evidence fails. The gate is a **declared-evidence** validator, not AWS IAM or deployment verification.

### Lab A — Contract inspection
Trace parent \`TemplateURL\`, child parameter \`Environment\`, outputs, \`Ref\` and \`Fn::GetAtt\`. Confirm no embedded secrets and no production account identifiers.

### Lab B — StackSet deployment matrix
Review \`fixtures/safe.json\`: lab-only account alias, approved region, bounded concurrency, failure tolerance zero, change ticket and approval. Modify account, region, permission scope and approval flags; confirm rejection.

### Lab C — Recovery tabletop
Simulate a failed nested-stack update, a partial StackSet operation and a blocked cross-stack export. Produce a recovery plan with affected account/region list, preserved event logs, last-known-good template digest and SRE/DBRE approvals.

### Optional read-only AWS commands
~~~bash
aws sts get-caller-identity --profile approved-readonly
aws cloudformation validate-template --template-body file://child-template.json --profile approved-readonly
aws cloudformation list-stack-sets --status ACTIVE --profile approved-readonly
aws cloudformation describe-stack-set --stack-set-name APPROVED_STACKSET --profile approved-readonly
aws cloudformation list-stack-instances --stack-set-name APPROVED_STACKSET --profile approved-readonly
~~~
These commands require valid authorized targets and may need AWS permissions. The offline gate does not establish live deployability.

## 5. SRE/DBRE production incident scenarios

| Incident | Signal | Containment |
|---|---|---|
| Wrong AWS account | unexpected caller | abort, revoke session |
| Wrong StackSet OU | unexpected instances | stop operations and reconcile targets |
| Wrong region | deployment in unapproved region | freeze and audit |
| Nested child unavailable | TemplateURL fetch failure | restore immutable artifact |
| Child parameter mismatch | validation failure | restore versioned contract |
| Cross-stack export in use | update blocked | coordinate consumers |
| StackSet partial failure | failed instance count | isolate region/account |
| Excessive concurrency | SLO degradation | reduce operation preference |
| Failure tolerance exceeded | halted operation | inspect per-instance events |
| IAM execution role denied | AccessDenied | review trust and scope |
| IAM privilege escalation | unexpected capabilities | block and security review |
| Drift in child stack | DRIFTED | reconcile ownership |
| Stack policy conflict | update denied | evaluate policy, not blanket disable |
| RDS replacement | Replacement=True | stop; backup/PITR and DBRE |
| Aurora cluster change | failover risk | connection and replication gate |
| ElastiCache topology change | p99 spike | check replica health |
| OpenSearch data-node change | disk pressure | capacity and shard review |
| MSK broker replacement | ISR shrink | halt rollout |
| EKS node group update | PDB violations | stage and capacity gate |
| Retained orphaned resource | cost drift | tag, reconcile ownership |
| StackSet account removed | orphaned instance | assess retention/removal |
| Secret in output | audit alert | revoke/rotate and redact |
| Drift detection unsupported | unknown drift | document limitations |
| Template artifact compromised | digest mismatch | quarantine and rebuild |

## 6. Operational runbooks

**R1 Preflight:** verify account, region, Organizations scope, target matrix, template digest, IAM execution role, quotas, change ticket and DBRE approvals.

**R2 Nested stack failure:** inspect parent and child events; restore reviewed child artifact and reconcile resources without force deletion.

**R3 StackSet partial deployment:** enumerate instances, record failures by account/region, stop further rollout, verify IAM and quotas, then re-plan.

**R4 Export dependency:** identify consumers, coordinate interface migration and avoid destructive export rename.

**R5 Stateful database change:** validate backup/PITR, replication/quorum, connection budget, SLO and restore drill before replacement.

**R6 Security incident:** revoke compromised role, inspect CloudTrail, quarantine template/transform and rotate exposed secrets.

**R7 Drift:** compare stack and resource drift, establish owner, create reviewed reconciliation change set.

**R8 Rollback:** inspect status and failed resources, preserve evidence, restore approved template and verify data health.

**R9 FinOps and cleanup:** inventory retained/orphaned resources, ownership tags and cost before disposal.

**R10 Post-change:** verify every account/region instance, CloudWatch SLO, backups, drift and handover.

## 7. 100-point acceptance

| Domain | Max |
|---|---:|
| Advanced template and nested-stack architecture | 20 |
| StackSet accounts, regions and permissions | 20 |
| Change sets, drift and recovery controls | 15 |
| Security, IAM, secrets and supply chain | 15 |
| Automated tests and negative fixtures | 15 |
| SRE/DBRE incidents and runbooks | 15 |
| **Total** | **100** |

Pass >=85 with zero critical findings. Critical: wrong account/region/OU, unintended data replacement, IAM expansion, leaked secret, unverified backup or unapproved deployment. Evidence: offline test output, native AWS validation, signed target matrix, StackSet operation review, database restore evidence and incident-game-day record.

**Status:** authored and published; offline test execution, AWS-native integration and production acceptance pending.

**Next proposed:** Chapter 068 — Azure Bicep Foundations, ARM Templates, Modules and Deployment Operations.
