# Chapter 082 — IaC Policy as Code, OPA/Rego, Sentinel and Enterprise Guardrails

**Part 17 — Security and Policy · Chapter 082/120 · SRE/DevOps/DBRE**

## Outcomes and scope

Design, implement, test and operate **policy as code (PaC)** across Terraform/OpenTofu, Pulumi, CloudFormation, Bicep, Ansible, Kubernetes and GitOps. Compare **Open Policy Agent (OPA)/Rego**, **HashiCorp Sentinel**, **Pulumi CrossGuard**, AWS SCP/Config/CloudFormation Guard, Azure Policy, GCP Organization Policy, and Kubernetes Gatekeeper/Kyverno**. Enforce least privilege, immutable provenance, destructive-change review, data protection, exception lifecycle and production SLO gates.

The accompanying Python standard-library lab is **offline and read-only**. It evaluates **self-declared evidence**, not authentic cloud identity, signed artifacts, native OPA/Sentinel execution or real backup restorations. Do not treat a passing fixture as production approval.

## 1. Enterprise policy architecture

~~~text
Signed PR + CODEOWNERS + change ticket
                  |
     CI lint / unit / SAST / SBOM
                  |
 Native plan/preview/diff (protected identity)
                  |
     normalized policy input (sensitive!)
                  |
     OPA/Rego | Sentinel | CrossGuard
                  |
  cloud org guardrails + Kubernetes admission
                  |
  independent SRE/security/DBRE approval
                  |
   state lock + backup + SLO/canary gate
                  |
    protected apply / GitOps reconciliation
                  |
 immutable audit, exception expiry, monitoring
~~~

**Preventive policy** rejects changes before execution. **Detective policy** reports violations in running environments; detection alone cannot block a destructive API call. **Cloud-side enforcement** (SCPs, Azure Policy, GCP organization constraints, admission controls) remains important when someone bypasses CI. **Reconciliation** restores desired GitOps state but must not be used to hide drift or repeatedly undo emergency changes.

### Trust boundaries

Untrusted PR authors must not control policy bundles, privileged runner images, protected approvals, OIDC claims or production exception registries. Policy data may include credentials, database endpoints and private network structure. Terraform `show -json`, Pulumi exports and Kubernetes diffs may reveal sensitive values; restrict access, retention and logging.

## 2. OPA and Rego fundamentals

OPA evaluates structured input and policy rules and can run in CI, services or Kubernetes admission. Rego separates **data** (trusted policy configuration) from **input** (candidate change). Evaluate with `opa eval` or `opa test`, and validate policy bundle version/provenance. A policy's default decision must be deny, with explicit allow rules. Verify syntax and semantics against the installed OPA version; examples here use modern Rego v1 syntax.

~~~rego
package iac.security
import rego.v1

default allow := false

allow if {
  input.environment == "staging"
  input.source_signed == true
  input.plan_digest_verified == true
  input.destructive_changes == 0
  input.state_encrypted == true
}
~~~

Example optional command (requires installed OPA): `opa eval -d examples/guardrails.rego -i examples/opa-input.json 'data.iac.security.allow'`. This illustrative rule is intentionally narrow and **not sufficient for production authorization**.

## 3. Sentinel policy lifecycle

Sentinel is HashiCorp's policy-as-code language, integrated with supported HCP Terraform/Terraform Enterprise workflows. Policy sets must be attached to intended workspaces and enforcement levels verified: **advisory** reports, **soft mandatory** can allow authorized override, and **hard mandatory** blocks. Confirm product/edition compatibility and native plan import versions. Sentinel is not a drop-in Rego interpreter; tests, import schemas and exception mechanics differ.

~~~hcl
# Illustrative Sentinel policy logic; verify native imports and workspace setup.
import "tfplan/v2" as tfplan
main = rule {
  length(tfplan.resource_changes) >= 0
}
~~~

The rule above is a **syntax-oriented placeholder**, not a security gate; never deploy it as an allow policy. Implement explicit deny conditions for destroys, replacements, public exposure and missing encryption, then test against real native plan imports.

## 4. Policy mapping across tools

| Platform | Policy surface | Important limitation |
|---|---|---|
| Terraform/OpenTofu | plan JSON + OPA, Sentinel where supported | plan/state can contain secrets |
| Pulumi | policy packs / CrossGuard, OPA adapter | preview is not an immutable apply guarantee |
| CloudFormation | Guard, hooks, SCP, Config | stack rollback cannot restore deleted data |
| Bicep/Azure | Azure Policy, what-if, RBAC | what-if can be incomplete; exemptions must expire |
| Ansible | ansible-lint, inventory checks, custom rules | check mode is not fully side-effect free |
| Kubernetes | Gatekeeper, Kyverno, ValidatingAdmissionPolicy | webhook failurePolicy and timeout are critical |
| Argo CD/Flux | PR gates, admission, AppProject/RBAC | controller permissions can bypass CI |
| AWS/Azure/GCP | org policies, IAM boundaries, audit | organizational guardrails need separate ownership |

## 5. Enterprise guardrail catalog

Use independent controls for: exact cloud account/subscription/project and Kubernetes context; immutable source and artifact digests; short-lived workload identity; no wildcard administrator role; encrypted/versioned state and protected lock; encryption at rest and in transit; no unrestricted ingress; deletion protection for stateful resources; verified PITR and restore rehearsal; minimum backup retention; owner, cost-center and classification tags; immutable logs; signed approval; policy exception expiry; and SLO/error-budget acceptance.

### Exceptions and break-glass

Exceptions require an exact control ID, scope, affected resource, ticket, business reason, independent approver, compensating control and expiry. Never allow a blanket production exemption, indefinite waiver, self-approval or policy-bundle modification by the same deployment principal. Break-glass use must be logged, time-bound, reviewed and followed by reconciliation.

## 6. SRE/DBRE production scenarios

**PostgreSQL/RDS/Aurora:** deny instance deletion/replacement, unencrypted storage, backup-retention reduction and unsafe parameter changes without DBRE approval. **MongoDB:** deny quorum loss, backup removal and exposed administrative endpoints. **Redis:** protect persistence, ACLs and failover readiness. **Kafka/MSK:** enforce TLS, IAM/SASL and ISR safeguards. **OpenSearch/Elasticsearch:** enforce snapshot and shard/IOPS review. **Snowflake:** enforce restricted network/role changes. **EKS/AKS/GKE:** enforce namespace RBAC, PDB, CSI snapshots, admission and GitOps ownership.

Policy may block urgent remediation. Design a documented emergency override path with a second approver, compensating safeguards and post-incident audit; do not silently switch production enforcement to advisory.

## 7. Executable hands-on labs

### Lab 1 — Offline enterprise policy evaluator

~~~bash
cd infrastructure-as-code/labs/chapter-082
python3 policy_gate.py fixtures/safe.json policy.json
python3 policy_gate.py fixtures/unsafe.json policy.json  # expected rejection
bash run-preflight.sh
~~~

The evaluator checks exact target, immutable digest, workload identity, encryption, state, approval, DBRE recovery, no destructive changes, exception expiry and canary SLO. It does **not** cryptographically verify these claims.

### Lab 2 — Rego policy exercise

Review `examples/guardrails.rego` and `examples/opa-input.json`. If OPA is installed, run the optional command above and confirm only the narrow staging fixture passes. Add negative cases for `destructive_changes`, unsigned source and unencrypted state. Production policy should use native plan resources, not a self-asserted boolean.

### Lab 3 — Exception lifecycle

`exceptions.py` rejects indefinite, expired, self-approved, unscoped and uncompensated exceptions. Run `python3 -m unittest -v test_exceptions.py`.

### Lab 4 — CI gate sequencing

`promotion.py` simulates `source -> preview -> scan -> policy -> approval -> backup -> canary -> health -> promote -> audit`; no stage may be skipped, and any failure halts promotion. The example CI configurations **only run offline tests**.

### Lab 5 — Stateful incident game day

Simulate an unapproved RDS replacement with missing PITR, an Azure Policy exemption and a Kubernetes admission outage. Freeze promotion, preserve plan evidence, inspect target/identity, restore policy enforcement, verify backup/restore and SLO, and document independent DBRE/security approvals.

## 8. Production incident simulations

| # | Incident | Containment |
|---|---|---|
| 1 | OPA unavailable during deploy | Fail closed; validate target, policy bundle and approvals |
| 2 | Policy bundle signature invalid | Revoke or quarantine; verify provenance |
| 3 | Rego rule accidentally permits all | Fail closed; validate target, policy bundle and approvals |
| 4 | Sentinel advisory mode on production | Fail closed; validate target, policy bundle and approvals |
| 5 | Sentinel policy set unattached | Fail closed; validate target, policy bundle and approvals |
| 6 | Wrong workspace policy scope | Fail closed; validate target, policy bundle and approvals |
| 7 | Terraform plan JSON secret exposed | Revoke or quarantine; verify provenance |
| 8 | OpenTofu provider schema change | Fail closed; validate target, policy bundle and approvals |
| 9 | CloudFormation delete bypass | Fail closed; validate target, policy bundle and approvals |
| 10 | Azure Bicep policy exemption expired | Fail closed; validate target, policy bundle and approvals |
| 11 | Pulumi policy pack version drift | Fail closed; validate target, policy bundle and approvals |
| 12 | Kubernetes admission fail-open | Fail closed; validate target, policy bundle and approvals |
| 13 | Gatekeeper webhook timeout | Fail closed; validate target, policy bundle and approvals |
| 14 | Kyverno background audit only | Fail closed; validate target, policy bundle and approvals |
| 15 | GitOps bypass via direct kubectl | Fail closed; validate target, policy bundle and approvals |
| 16 | GitOps prune protected namespace | Fail closed; validate target, policy bundle and approvals |
| 17 | IAM policy privilege escalation | Revoke or quarantine; verify provenance |
| 18 | S3 state backend public access | Fail closed; validate target, policy bundle and approvals |
| 19 | Unencrypted RDS volume | Block destructive action; DBRE verifies recovery |
| 20 | PostgreSQL cluster replacement | Block destructive action; DBRE verifies recovery |
| 21 | Aurora backup retention reduced | Block destructive action; DBRE verifies recovery |
| 22 | MongoDB backup disabled | Block destructive action; DBRE verifies recovery |
| 23 | Redis persistence disabled | Block destructive action; DBRE verifies recovery |
| 24 | MSK broker encryption disabled | Block destructive action; DBRE verifies recovery |
| 25 | OpenSearch snapshots missing | Block destructive action; DBRE verifies recovery |
| 26 | Snowflake network policy weakened | Fail closed; validate target, policy bundle and approvals |
| 27 | Unapproved wildcard CIDR | Fail closed; validate target, policy bundle and approvals |
| 28 | Production resource without tags | Fail closed; validate target, policy bundle and approvals |
| 29 | Missing owner on exception | Fail closed; validate target, policy bundle and approvals |
| 30 | Exception expiration ignored | Fail closed; validate target, policy bundle and approvals |
| 31 | Exception approval self-signed | Fail closed; validate target, policy bundle and approvals |
| 32 | Change ticket mismatched | Fail closed; validate target, policy bundle and approvals |
| 33 | Artifact digest mismatch | Revoke or quarantine; verify provenance |
| 34 | Wrong AWS account | Fail closed; validate target, policy bundle and approvals |
| 35 | Wrong Azure subscription | Fail closed; validate target, policy bundle and approvals |
| 36 | Wrong GCP project | Fail closed; validate target, policy bundle and approvals |
| 37 | Wrong Kubernetes context | Fail closed; validate target, policy bundle and approvals |
| 38 | Plan destroy not reviewed | Fail closed; validate target, policy bundle and approvals |
| 39 | State lock disabled | Fail closed; validate target, policy bundle and approvals |
| 40 | Provider download unverified | Fail closed; validate target, policy bundle and approvals |
| 41 | Cost threshold bypass | Fail closed; validate target, policy bundle and approvals |
| 42 | SLO canary unhealthy | Fail closed; validate target, policy bundle and approvals |
| 43 | Emergency break-glass abused | Fail closed; validate target, policy bundle and approvals |
| 44 | Audit log tampering | Fail closed; validate target, policy bundle and approvals |
| 45 | DR restore evidence missing | Block destructive action; DBRE verifies recovery |

## 9. Production runbooks

**R1 — Policy gate outage and fail-closed recovery:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

**R2 — Rego regression and test rollback:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

**R3 — Sentinel enforcement-level verification:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

**R4 — OPA bundle provenance and signing:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

**R5 — Plan JSON sensitive-data containment:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

**R6 — CloudFormation guardrail and stack recovery:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

**R7 — Azure Policy exemption governance:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

**R8 — Pulumi policy pack version rollback:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

**R9 — Kubernetes admission/Gatekeeper/Kyverno recovery:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

**R10 — GitOps drift and dual-controller ownership:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

**R11 — DBRE destructive change and restore drill:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

**R12 — Emergency exception audit and expiry:** Identify owner and blast radius; freeze promotion; collect immutable evidence; validate target and policy version; execute approved containment; test service health and recovery; document ticket, approvals and post-incident follow-up.

## 10. Troubleshooting

| Symptom | Investigation | Safe action |
|---|---|---|
| OPA unexpectedly allows | default rule, input schema, bundle version | disable deployment and test deny cases |
| OPA unexpectedly denies | missing input, wrong path, bundle mismatch | correct data; never bypass silently |
| Sentinel reports but does not block | advisory/soft mandatory, workspace attachment | verify enforcement level and override rules |
| Admission webhook times out | failurePolicy, API server, webhook pods | halt risky changes; restore admission safely |
| Exception still effective after expiry | clock, scope, registry sync | revoke and audit exception |
| Database replacement proposed | plan actions, dependency graph | block; require DBRE and restore evidence |
| Policy gate exposes secrets | logs, plan JSON, artifact retention | quarantine, rotate and redact |
| GitOps repeatedly reverts changes | resource ownership, reconciliation | restore single writer and protected Git flow |

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Policy architecture and trust boundaries | 15 |
| OPA/Rego and Sentinel design | 20 |
| Cloud, Kubernetes and GitOps guardrails | 20 |
| Executable labs and negative automated tests | 15 |
| Stateful SRE/DBRE recovery and incident response | 15 |
| Exception governance, audit and rollout SLO | 15 |
| **Total** | **100** |

**Pass >=85**, zero critical failures, independently verified native policy results, signed security/SRE/DBRE approval and tested restore evidence. Critical failures include production allow-all, wrong target, destructive database change, unencrypted exposed state, indefinite exemption, unsigned artifact or failed SLO. **Publication is not production certification.**

**Next:** Chapter 083 — IaC Security Scanning, Supply-Chain Integrity, Secrets Detection and Continuous Compliance.
