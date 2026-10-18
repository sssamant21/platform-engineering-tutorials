# Chapter 070 — CloudFormation and Bicep Enterprise Multi-Cloud Automation and Reliability Capstone

**Part 14 — CloudFormation and Bicep · Chapter 070/120 · Final SRE/DBRE capstone**

## Learning outcomes

Combine AWS CloudFormation nested stacks and StackSets with Azure Bicep modules, subscription governance, deployment stacks, policy-as-code, supply-chain checks, approval gates, SLO-driven rollout and recovery. Design a repeatable multi-cloud change process with zero unauthorized destructive operations. This chapter completes Part 14 (Chapters 066–070). **The executable labs are offline simulations; they do not provision cloud resources or demonstrate real database disaster recovery.**

Prerequisites: Chapters 066–069, Python 3.9+, POSIX shell. Optional AWS CLI v2 and Azure CLI/Bicep CLI for separately authorized, read-only diagnostics and offline Bicep compilation.

## 1. Reference architecture

~~~text
                   Git protected branch
                           |
        PR review / change ticket / IaC owners
                           |
   policy tests / static template checks / artifact pins
                           |
      security + SRE + DBRE approval and backup proof
                           |
              target/account matrix
                 /               \
     AWS deployment track     Azure deployment track
      CloudFormation             Bicep / ARM
      nested stacks              scoped modules
      StackSets                  deployment stacks
                 \               /
             normalized change evidence
                           |
            canary -> health gate -> rollout
                           |
      CloudTrail / Azure Activity Log / SLO / audit
                           |
       rollback / PITR / RPO-RTO / postmortem
~~~

AWS and Azure have different control-plane and lifecycle semantics. CloudFormation stacks are AWS-region scoped; StackSets coordinate across accounts/regions. Bicep compiles to ARM templates, supports multiple deployment scopes and modules; Azure deployment stacks have explicit managed-resource deletion/detach semantics. Never treat a CloudFormation change set or ARM what-if as a complete prediction of runtime consequences. Separate Terraform/OpenTofu ownership from native IaC to avoid competing writers.

## 2. Governance and change contract

The lab's normalized evidence includes a change ticket, owner, AWS account/region, Azure tenant/subscription/resource group, approved environments, template provenance, least-privilege identities, change preview review, zero destructive changes, verified backups, DBRE approval, SLO gates, incident escalation, rollback and RPO/RTO. An **offline fail-closed Python policy gate** validates the declared evidence and a narrow static contract for the CloudFormation and Bicep sample files. It does not parse native cloud change-set/what-if APIs, validate real IAM/RBAC, inspect actual secrets or prove backups.

### Production gates
1. Confirm AWS account and region, Azure tenant and subscription, exact target resources and owner.
2. Pin CloudFormation child templates, Bicep modules, execution environment and CI dependencies; verify signatures/digests.
3. Use AWS IAM execution roles and Azure federated workload identities with least privilege.
4. Review AWS change sets and Azure what-if, plus deletion policies, deployment-stack action-on-unmanage and unknown values.
5. Require security and DBRE approval for RDS, Aurora, PostgreSQL, Cosmos DB, Redis, MSK, OpenSearch, AKS/EKS and stateful storage.
6. Validate snapshots/PITR, restore drills, replication/quorum, capacity, SLO, RPO/RTO and rollback plan.
7. Deploy to sandbox/canary first; halt on health or error-budget regression.
8. Capture CloudTrail/Activity Log, CloudWatch/Azure Monitor, drift, cost and handover evidence.

## 3. Lab topology

~~~text
labs/chapter-070/
  aws/parent-template.json
  aws/child-template.json
  azure/main.bicep
  azure/modules/private-storage.bicep
  azure/parameters/lab.bicepparam
  fixtures/safe.json
  fixtures/unsafe.json
  policy.json
  multicloud_gate.py
  test_multicloud_gate.py
  run-preflight.sh
  runbook.md
  acceptance.md
  examples/readonly-cloud-diagnostics.sh.example
~~~

The AWS parent template points at an intentionally invalid \`example.invalid\` child URL to prevent accidental deployment. The Azure sample declares a private storage-account module with no public blob access. **Do not deploy either sample as-is.** Production templates require provider-native validation, approved accounts, immutable artifact hosting and live integration tests.

## 4. Lab A — Offline multi-cloud policy gate

~~~bash
cd infrastructure-as-code/labs/chapter-070
python3 multicloud_gate.py fixtures/safe.json policy.json
python3 multicloud_gate.py fixtures/unsafe.json policy.json
python3 -m unittest -v test_multicloud_gate.py
bash run-preflight.sh
~~~

Expected: safe fixture passes; unsafe fixture is rejected; all unit tests pass. The gate fails closed if mandatory fields, policy flags, expected static contract markers, approval or backup evidence are missing.

## 5. Lab B — Cloud template contracts

Inspect the AWS parent/child parameters, outputs, \`AWS::CloudFormation::Stack\` resource and retained child resource. Inspect the Azure subscription-scope Bicep entrypoint, existing resource-group reference, private storage module, module outputs and lab parameter file.

Optional local Bicep compilation (no deployment):

~~~bash
az bicep build --file azure/main.bicep --outfile /tmp/ch070-azure.json
az bicep build-params --file azure/parameters/lab.bicepparam --outfile /tmp/ch070-azure-params.json
~~~

AWS \`validate-template\` is an AWS API call; do not treat it as offline. The parent template's \`example.invalid\` URL is intentionally not resolvable and must be replaced only through a reviewed production process.

## 6. Lab C — Incident injection

Change one control at a time: production AWS account, unapproved Azure subscription, missing change ticket, disabled least privilege, destructive StackSet action, deployment-stack delete-all, missing backup, unapproved DBRE change, unreviewed change preview or failed SLO gate. Re-run the policy gate. Each must fail.

## 7. Lab D — Multi-cloud rollout and recovery tabletop

Simulate canary-first deployment to approved AWS and Azure sandbox targets. Produce an account/subscription target matrix, preview review, signed approval, DBRE restore evidence, CloudTrail/Activity Log links, rollback triggers and final handover. Simulate partial AWS StackSet success followed by an Azure deployment failure; **do not automatically roll back a database**. Instead freeze rollout, preserve evidence, assess data consistency and invoke DBRE-controlled recovery.

## 8. Production incident simulations

| Scenario | Detection | Containment |
|---|---|---|
| Wrong AWS account | caller mismatch | abort and revoke session |
| Wrong Azure tenant | identity mismatch | stop deployment |
| Wrong region/subscription | target matrix mismatch | freeze and audit |
| AWS StackSet wrong OU | unexpected instance | quarantine target |
| CloudFormation child artifact missing | nested failure | restore pinned artifact |
| Cross-stack export conflict | update blocked | coordinate consumers |
| Azure module tampered | provenance failure | quarantine build |
| Azure deployment-stack delete-all | destructive preview | block change |
| IAM escalation | permission diff | security review |
| Azure RBAC broad Owner | scope audit | revoke and re-scope |
| Secret in CI logs | audit alert | rotate and restrict |
| CloudFormation rollback failure | stack status | inspect events and recover |
| Azure partial deployment | failed operations | isolate affected resources |
| AWS drift | unexpected resource state | owner reconciliation |
| Azure drift | unexpected ARM diff | reviewed what-if |
| RDS replacement | change-set replacement | PITR and DBRE gate |
| Aurora failover | connection errors | replication/connection checks |
| Azure PostgreSQL failover | replica lag | halt changes |
| Cosmos DB RU throttling | 429 increase | capacity gate |
| Redis failover | elevated p99 | client/replica validation |
| MSK ISR shrink | under-replicated partitions | stop broker change |
| OpenSearch disk pressure | high latency | capacity remediation |
| EKS/AKS PDB block | failed drain | disruption budget review |
| Backup corruption | checksum failure | isolate recovery artifact |
| RPO/RTO exceeded | recovery drill | incident escalation |
| Canary SLO regression | error budget burn | stop rollout |
| Retained resources | FinOps drift | ownership cleanup |
| CI identity compromised | anomalous deployment | revoke OIDC |
| Missing audit evidence | compliance gap | block acceptance |
| Cross-cloud partial rollout | inconsistent version | freeze, assess and re-plan |

## 9. Production runbooks

**R1 Preflight:** validate caller identity, account/tenant, region/subscription, exact targets, policy, approvals and backup.

**R2 Supply chain:** verify CloudFormation artifact digests, Bicep module provenance, runner identity and pinned versions.

**R3 Change previews:** review AWS change set and Azure what-if, deletion/replacement and unknown impacts.

**R4 Canary failure:** stop remaining targets, preserve telemetry, inspect changed resources, escalate to SRE/DBRE.

**R5 Stateful recovery:** verify PITR/backup, replication, RPO/RTO and service SLO before approved recovery.

**R6 Cloud control-plane failure:** inspect CloudFormation events and ARM deployment operations; avoid force deletion.

**R7 Identity/secret incident:** revoke roles/tokens, rotate credentials, audit CloudTrail and Activity Log.

**R8 Drift:** reconcile ownership and apply approved source of truth, never silently overwrite hotfixes.

**R9 FinOps:** inventory retained resources, tags, budgets, orphaned storage and cleanup owners.

**R10 Post-change:** verify application SLOs, cloud resource health, backup, drift, monitoring and handover.

## 10. Final 100-point assessment

| Domain | Points |
|---|---:|
| Multi-cloud architecture, ownership and template contracts | 15 |
| AWS CloudFormation nested stacks / StackSets | 15 |
| Azure Bicep modules / deployment stacks | 15 |
| IAM/RBAC, secrets, policy and supply chain | 15 |
| Safe previews, canaries, SLOs and recovery | 15 |
| Automated tests and negative scenarios | 15 |
| Incident runbooks, evidence and handover | 10 |
| **Total** | **100** |

**Pass:** >=85/100, zero critical findings, signed SRE/DBRE/security acceptance. Critical failures: wrong account/subscription, unauthorized deletion, leaked credentials, lost database quorum, unverified restore, masked canary failure or missing approval.

**Status:** curriculum artifact authored; offline test execution, AWS/Azure native integration, DBRE restore, SLO game day and production acceptance are pending.

## 11. Part 14 completion

Chapters 066–070 cover CloudFormation fundamentals, advanced nested stacks/StackSets, Bicep foundations, advanced deployment stacks/multi-subscription governance and this multi-cloud reliability capstone.

**Next proposed:** Chapter 071 — Pulumi Foundations, Architecture, Stacks and Infrastructure as Code with Programming Languages, beginning Part 15.
