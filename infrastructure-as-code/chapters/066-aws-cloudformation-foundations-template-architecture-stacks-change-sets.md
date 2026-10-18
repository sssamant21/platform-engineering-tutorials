# Chapter 066 — AWS CloudFormation Foundations, Template Architecture, Stacks and Change Sets

**Part 14 — CloudFormation and Bicep · Chapter 066/120 · SRE/DevOps/DBRE**

## Objectives

Explain AWS CloudFormation declarative infrastructure management, stack lifecycle, templates, parameters, mappings, conditions, outputs, intrinsic functions, logical and physical IDs, change sets, drift detection, stack policies, IAM execution roles, rollback and nested stacks. Build a fully offline, provider-free template contract and a conservative change-set policy gate. Design production-safe AWS deployment and DBRE change processes.

**Prerequisites:** Chapters 001–065; Python 3.9+; optional AWS CLI v2 and AWS credentials for **read-only** AWS diagnostics. The executable core labs require **no AWS account or cloud credentials**.

## 1. Architecture

~~~text
Git PR -> template review / validation / policy / tests
                     |
               IAM/OIDC deployment identity
                     |
             CloudFormation execution role
                     |
       Change Set -> human/DBRE approval -> Execute
                     |
                Stack resources
        VPC / IAM / EKS / RDS / OpenSearch
                     |
        Events / Outputs / Drift / Rollback
                     |
          CloudTrail / CloudWatch / SLO
~~~

CloudFormation manages AWS resources from templates; its stack state and events are AWS service-managed, unlike Terraform's user-managed state file. CloudFormation templates are JSON or YAML. Stacks are regional, though StackSets can target multiple accounts/regions. A change set previews intended resource actions but does **not** guarantee successful deployment or reveal all side effects, such as runtime behavior or application impact.

## 2. Template model

- **AWSTemplateFormatVersion / Description:** template metadata and purpose.
- **Parameters:** typed inputs, allowed values, defaults and NoEcho; NoEcho is not a substitute for a secret manager and does not conceal every surface.
- **Mappings / Conditions:** static environment maps and conditional resources.
- **Resources:** logical IDs, resource properties, DependsOn and lifecycle policies.
- **Outputs / Exports:** useful integration contracts; avoid exporting secrets.
- **Intrinsic functions:** Ref, Fn::Sub, Fn::GetAtt, Fn::If, Fn::Join and Fn::ImportValue; understand replacement implications.
- **Stack policies and IAM:** restrict destructive updates; execution role and CI caller privileges are separate trust boundaries.
- **UpdateReplacePolicy / DeletionPolicy:** preserve critical stateful resources where appropriate, but retained resources need ownership, backup and cost governance.

## 3. Stack and change-set lifecycle

~~~text
CREATE -> CREATE_COMPLETE
UPDATE via reviewed change set -> UPDATE_COMPLETE
failed update -> UPDATE_ROLLBACK_* / UPDATE_FAILED
drift -> DETECT_DRIFT -> review and reconcile
delete -> DELETE_* (blocked by retain/policy/dependencies)
~~~

A change set is a preview; use it to inspect \`Add\`, \`Modify\`, \`Remove\`, replacement indications, IAM changes, parameter changes and dependencies. Some changes have dynamic evaluation and the exact replacement impact may not be fully known. Avoid automatic execution on production. Use approved stack policies, termination protection, scoped execution roles, separate environment accounts and a recovery plan.

## 4. Offline executable lab

The lab uses a provider-free CloudFormation JSON template containing a \`AWS::CloudFormation::WaitConditionHandle\` resource as a syntax/structure exercise. It does **not** provision infrastructure; it is not a production deployment recommendation. A Python validator enforces required template fields and checks a **simplified change-set evidence document**. The gate does **not** parse native AWS \`describe-change-set\` JSON and must not be used as a production approval engine without an adapter and integration tests.

~~~bash
cd infrastructure-as-code/labs/chapter-066
python3 template_gate.py template.json fixtures/change-safe.json policy.json
python3 template_gate.py template.json fixtures/change-unsafe.json policy.json
python3 -m unittest -v test_template_gate.py
bash run-preflight.sh
~~~

Expected: safe fixture passes, unsafe fixture fails, unit tests pass. The local lab has no AWS API calls and no cloud spend.

## 5. Optional read-only AWS exercises

Only after configuring an approved, read-only AWS profile:

~~~bash
aws sts get-caller-identity --profile approved-readonly
aws cloudformation validate-template --template-body file://template.json --profile approved-readonly
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --profile approved-readonly
aws cloudformation describe-stack-events --stack-name APPROVED_STACK --profile approved-readonly
aws cloudformation describe-stack-drift-detection-status --stack-drift-detection-id APPROVED_ID --profile approved-readonly
~~~

\`describe-stack-drift-detection-status\` requires a pre-existing detection ID. Starting a new drift detection is an AWS API action and is not part of this read-only lab. Never use \`execute-change-set\`, \`delete-stack\` or production \`update-stack\` from this chapter.

## 6. SRE/DBRE production design scenarios

| Scenario | Signal | Investigation and safe response |
|---|---|---|
| RDS replacement proposed | change-set Replacement | block, DBRE review, backup/PITR |
| Stack update rollback | UPDATE_ROLLBACK_* | inspect events and dependencies |
| Drifted security group | DRIFTED | review manual change and owner |
| IAM privilege escalation | new IAM action | security review and CAPABILITY flags |
| Stack policy denies update | access failure | assess policy, not blanket disable |
| Retained resource orphan | cost/inventory discrepancy | tag, ownership and cleanup plan |
| OpenSearch disk bottleneck | latency and IOPS | avoid concurrent node replacement |
| MSK broker maintenance | ISR/availability risk | coordinate rollout |
| ElastiCache failover | elevated p99 | verify replicas and client reconnect |
| EKS node group replacement | unavailable pods | PDB and capacity review |
| Secret exposure | output/parameter leak | rotate and restrict logs |
| Nested stack failure | nested events | trace parent/child dependencies |
| Quota exceeded | deployment failure | service quota and capacity review |
| StackSet region mismatch | partial deployment | account/region reconciliation |
| Missing termination protection | deletion risk | protect critical stacks |
| Wrong account | unexpected caller ARN | stop and correct identity |
| Change-set stale | revision mismatch | recreate and reapprove |
| CloudFormation export in use | update blocked | consumer dependency review |
| Template limit/size | validation failure | package and modularize |
| Backup policy gap | failed restore drill | block stateful change |

## 7. Troubleshooting runbooks

**R1 Identity and preflight:** verify AWS account/region, caller and execution role, template validation, resource count, quotas and tags.

**R2 Change-set review:** examine actions, replacement, IAM and parameters; require change ticket and DBRE/security approval.

**R3 Rollback failure:** inspect stack events and dependencies, preserve diagnostics, avoid forceful deletion, establish recovery owner.

**R4 Drift:** capture drift evidence, identify source-of-truth owner, reconcile via reviewed change set.

**R5 Stateful data:** validate RDS snapshots/PITR, encryption, retention, replication and restore before changes.

**R6 IAM incident:** revoke overbroad identity, audit CloudTrail and re-scope permissions.

**R7 StackSet failure:** compare accounts/regions, permissions and operation results; isolate partial deployment.

**R8 Cost and cleanup:** inspect retained resources, orphaned volumes and tags before removal.

**R9 Post-change:** verify CloudWatch SLOs, backups, stack status, drift and application health.

## 8. 100-point acceptance

| Domain | Points |
|---|---:|
| CloudFormation architecture and template contracts | 20 |
| Parameters, conditions, resources and lifecycle | 15 |
| Change-set review and rollback safeguards | 20 |
| IAM, secrets and policy security | 15 |
| Automated tests and negative cases | 15 |
| SRE/DBRE scenarios and runbooks | 15 |
| **Total** | **100** |

Pass >=85 with zero critical findings. Critical: unintended destructive replacement, leaked secret, wrong account, unapproved IAM expansion, unverified DB backup or missing rollback. The local validator checks authored evidence only; production acceptance requires AWS-native change-set tests, IAM review, stack event and restore evidence.

## 9. Exit criteria

Submit offline test results, safe/unsafe gate output, a reviewed example change set, account isolation evidence, RDS replacement incident analysis and a signed runbook. **Live AWS provisioning and operational acceptance remain pending.**

**Next proposed:** Chapter 067 — AWS CloudFormation Advanced Templates, Nested Stacks, StackSets and Enterprise Operations.
