# Chapter 084 — IaC Least Privilege, Zero Trust, Cloud IAM and Kubernetes Security Hardening

**Part 17 — Security and Policy · Chapter 084/120 · Enterprise SRE/DevOps/DBRE**

## Outcomes

Design and test least-privilege and zero-trust controls for Terraform/OpenTofu, Pulumi, CloudFormation, Bicep, Ansible, EKS/AKS/GKE, Argo CD and Flux. Build threat-aware IAM policies, scoped workload identity, Kubernetes RBAC/admission/network boundaries, audit, secret rotation and stateful recovery safeguards. Distinguish **offline evidence simulation** from real IAM or Kubernetes enforcement.

## 1. Zero-trust and privilege architecture

~~~text
Protected PR / signed source / CODEOWNERS
                 |
  untrusted CI (lint, tests, scans; no prod secrets)
                 |
    immutable verified artifact and plan
                 |
  protected CD with exact OIDC federation
                 |
  cloud permission boundary / org policy
                 |
  resource-scoped role + KMS + state backend
                 |
 independent security + SRE + DBRE approval
                 |
  protected Kubernetes API / admission / RBAC
                 |
  workload identity + network policy + secrets
                 |
 GitOps reconciliation + audit + SLO + PITR
~~~

**Zero trust** is a security architecture, not a single product: verify identity, device/workload context, target and authorization for each privileged operation. Assume compromised runners, repositories and workloads. Separate duties between code author, reviewer, pipeline operator, policy owner, cloud administrator and database recovery owner. Require short-lived credentials, explicit deny guardrails, minimal permissions, strong logging and tested emergency access.

### Attack paths and trust boundaries

1. Malicious PR modifies workflow to read production secrets: separate untrusted PR validation from protected CD and never expose prod tokens to forked PR code.
2. Stolen OIDC token attempts role assumption for another repository: bind exact issuer, audience and subject plus environment protection and expiry.
3. Overprivileged IAM role deletes backups: independent cloud-side deny/retention protection and tested restore.
4. Compromised pod uses default ServiceAccount to list Secrets: dedicated service accounts, RBAC, token mount reduction and network boundaries.
5. GitOps controller with cluster-admin applies dangerous CRDs: scoped Argo CD AppProjects/Flux controllers, admission, signed source and audit.

## 2. AWS IAM for IaC

Use workload identity federation (OIDC) with exact trust conditions and dedicated per-environment roles. Constrain permissions to required API actions and ARNs, avoid wildcard `iam:PassRole`, and use permissions boundaries and service control policies as defense-in-depth. Review KMS key grants, state S3/DynamoDB or supported backend locks, CloudTrail, IAM Access Analyzer, STS session details and CloudFormation execution roles.

**Illustrative trust conditions, not deploy-ready IAM JSON:** require `token.actions.githubusercontent.com:aud == sts.amazonaws.com` and exact `token.actions.githubusercontent.com:sub` for protected repository/branch or environment. Exact subject shape depends on workflow environment usage. Test trust against rejected branches and repositories before granting prod access.

## 3. Azure and GCP identity boundaries

**Azure:** Entra workload identity federation, narrowly scoped service principals/managed identities, least-privilege Azure RBAC at resource group/resource level, Key Vault access policies or RBAC, Azure Policy and subscription/tenant verification. Avoid Owner on CI and uncontrolled role-assignment permissions. Protect AKS identity, Azure Disk/CSI permissions and restore keys.

**GCP:** Workload Identity Federation with constrained attribute mapping and principal selectors, service account impersonation with minimal roles, IAM Conditions, organization policies, Cloud Audit Logs, Secret Manager and Cloud KMS. Avoid persistent service-account JSON keys and project Owner for pipelines. Scope GKE workload identities to intended Kubernetes service accounts.

## 4. Kubernetes RBAC, admission and workload hardening

~~~yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-reader
  namespace: demo-security
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: configmap-reader
  namespace: demo-security
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: configmap-reader-binding
  namespace: demo-security
subjects:
  - kind: ServiceAccount
    name: app-reader
    namespace: demo-security
roleRef:
  kind: Role
  name: configmap-reader
  apiGroup: rbac.authorization.k8s.io
~~~

This example intentionally **does not** allow Secrets, Pods exec, cluster roles or cross-namespace access. A workload requiring Kubernetes API calls must explicitly opt into a token; a tokenless ServiceAccount cannot authenticate using its in-cluster token.

Harden with Pod Security Admission restricted profile where compatible, non-root/read-only filesystem, seccomp, image provenance, resource limits, NetworkPolicy default-deny plus explicitly permitted egress, admission checks (Gatekeeper/Kyverno/ValidatingAdmissionPolicy), audit logs and encrypted Secrets. NetworkPolicy enforcement requires a supporting CNI; verify connectivity and DNS before production default-deny.

## 5. GitOps and IaC tool privilege boundaries

**Argo CD:** AppProjects limit destinations, repositories and cluster-scoped resources; restrict application-controller and repo-server identities. **Flux:** namespace-aware source and kustomization permissions, impersonation and controller isolation. **Terraform/OpenTofu:** distinct plan and apply roles, encrypted/versioned state and backend access separated from deployment rights. **Pulumi:** scoped organization/project/stack permissions and secret provider. **CloudFormation/Bicep:** narrowly scoped execution identity and independent cloud policy. **Ansible:** least-privilege SSH, constrained `become`, Vault and host inventories.

## 6. Stateful SRE/DBRE considerations

| Service | Least-privilege requirement | Reliability gate |
|---|---|---|
| PostgreSQL/RDS/Aurora | distinct migration/app/admin roles, scoped IAM DB auth | PITR, backup isolation, replication lag |
| MongoDB | database-scoped roles, avoid root | quorum, TLS, backup/restore |
| Redis | ACL command/key/channel scopes | connection rotation, failover |
| Kafka/MSK | topic/group ACL, IAM/SASL scopes | ISR and consumer lag |
| Elasticsearch/OpenSearch | index-scoped API keys, snapshot permissions | shard health and snapshot restore |
| Snowflake | task-specific roles, avoid ACCOUNTADMIN | audit and pipeline recovery |
| EKS/AKS/GKE | service-account identity and namespace RBAC | PDB, CSI snapshot and SLO |

Privilege reductions can cause production outages. Simulate credential rotation, IAM deny and Kubernetes API denial; monitor application SLO and verify backup access before deployment.

## 7. Hands-on labs

### Lab A — Offline IAM/RBAC policy gate

~~~bash
cd infrastructure-as-code/labs/chapter-084
python3 identity_gate.py fixtures/safe.json policy.json
python3 identity_gate.py fixtures/unsafe.json policy.json  # must fail
bash run-preflight.sh
~~~

The Python gate checks **self-declared** exact cloud targets, OIDC claims, IAM scopes, Kubernetes RBAC, admission, backup/restore, independent approval and audit. It does not call AWS IAM, Azure RBAC, GCP IAM or Kubernetes.

### Lab B — IAM permissions simulator

Use `iam.py` to reject wildcard actions/resources, overprivileged managed roles, missing environment separation and unauthorized `PassRole`. Validate sample policy decisions using `test_iam.py`. This is **not** a full IAM evaluator and cannot model SCP/deny/condition precedence.

### Lab C — Kubernetes RBAC simulator

Use `rbac.py` to test scoped namespace, resources and verbs. Verify that `get configmaps` is permitted only for the intended service account, while Secrets, cluster-wide and wildcard privileges are denied. This is a simplified model, not Kubernetes authorization API.

### Lab D — Credential rotation and emergency change

Simulate an expiring workload credential, failed DB connection pool refresh and emergency break-glass. Freeze promotion, preserve evidence, verify restored access, test PITR and require independent security/SRE/DBRE sign-off.

### Lab E — Real-world staging integration plan (not executed)

Create protected AWS/Azure/GCP OIDC roles, test `kubectl auth can-i --as` with properly authorized impersonation, audit Argo CD/Flux controllers, and run actual DB restore. Obtain change approval before any cloud or cluster mutation.

## 8. Production SRE/DBRE incident scenarios

| # | Scenario | Immediate containment |
|---|---|---|
| 1 | AWS role trust accepts wildcard subject | Freeze privileged change; verify trust, scope and approvals |
| 2 | AWS IAM PassRole unrestricted | Freeze privileged change; verify trust, scope and approvals |
| 3 | AWS AdministratorAccess on CI role | Freeze privileged change; verify trust, scope and approvals |
| 4 | AWS STS session lacks source identity | Freeze privileged change; verify trust, scope and approvals |
| 5 | AWS S3 state bucket publicly readable | Revoke/quarantine identity, preserve evidence and verify recovery |
| 6 | AWS KMS key policy too permissive | Revoke/quarantine identity, preserve evidence and verify recovery |
| 7 | AWS IAM Access Analyzer flags cross-account access | Freeze privileged change; verify trust, scope and approvals |
| 8 | AWS SCP absent from prod OU | Freeze privileged change; verify trust, scope and approvals |
| 9 | Azure federated credential wildcard | Revoke/quarantine identity, preserve evidence and verify recovery |
| 10 | Azure Owner assigned to pipeline | Freeze privileged change; verify trust, scope and approvals |
| 11 | Azure subscription target mismatch | Freeze privileged change; verify trust, scope and approvals |
| 12 | Azure Key Vault broad secret access | Revoke/quarantine identity, preserve evidence and verify recovery |
| 13 | Azure managed identity scope drift | Freeze privileged change; verify trust, scope and approvals |
| 14 | Azure Policy exemption unbounded | Freeze privileged change; verify trust, scope and approvals |
| 15 | GCP workload identity principal wildcard | Freeze privileged change; verify trust, scope and approvals |
| 16 | GCP service account key downloaded | Revoke/quarantine identity, preserve evidence and verify recovery |
| 17 | GCP project IAM owner overgrant | Freeze privileged change; verify trust, scope and approvals |
| 18 | GCP org policy bypass | Freeze privileged change; verify trust, scope and approvals |
| 19 | GCP KMS decrypter too broad | Revoke/quarantine identity, preserve evidence and verify recovery |
| 20 | GKE Workload Identity mismatch | Restrict controller/workload privileges and check service health |
| 21 | Kubernetes default ServiceAccount token mounted | Revoke/quarantine identity, preserve evidence and verify recovery |
| 22 | Kubernetes cluster-admin binding in namespace | Restrict controller/workload privileges and check service health |
| 23 | Kubernetes wildcard verbs and resources | Restrict controller/workload privileges and check service health |
| 24 | Kubernetes admission webhook fail-open | Restrict controller/workload privileges and check service health |
| 25 | Kubernetes privileged container | Restrict controller/workload privileges and check service health |
| 26 | Kubernetes hostPath to host root | Restrict controller/workload privileges and check service health |
| 27 | Kubernetes unrestricted egress | Restrict controller/workload privileges and check service health |
| 28 | Kubernetes API server audit disabled | Restrict controller/workload privileges and check service health |
| 29 | Argo CD AppProject allows all clusters | Restrict controller/workload privileges and check service health |
| 30 | Argo CD repo credential shared globally | Revoke/quarantine identity, preserve evidence and verify recovery |
| 31 | Flux controller cluster-admin | Restrict controller/workload privileges and check service health |
| 32 | Flux source points to mutable ref | Restrict controller/workload privileges and check service health |
| 33 | Terraform provider uses admin access key | Revoke/quarantine identity, preserve evidence and verify recovery |
| 34 | Terraform state exposes RDS password | Revoke/quarantine identity, preserve evidence and verify recovery |
| 35 | OpenTofu backend role can delete state | Revoke/quarantine identity, preserve evidence and verify recovery |
| 36 | Pulumi secrets provider key lost | Revoke/quarantine identity, preserve evidence and verify recovery |
| 37 | CloudFormation execution role overly broad | Freeze privileged change; verify trust, scope and approvals |
| 38 | Bicep deployment principal subscription Owner | Freeze privileged change; verify trust, scope and approvals |
| 39 | Ansible become unrestricted sudo | Freeze privileged change; verify trust, scope and approvals |
| 40 | Ansible Vault key leaked in runner | Revoke/quarantine identity, preserve evidence and verify recovery |
| 41 | PostgreSQL admin role used by app | Freeze privileged change; verify trust, scope and approvals |
| 42 | MongoDB root credentials in CI | Revoke/quarantine identity, preserve evidence and verify recovery |
| 43 | Redis ACL user allows all commands | Freeze privileged change; verify trust, scope and approvals |
| 44 | Kafka MSK SCRAM secret overexposed | Revoke/quarantine identity, preserve evidence and verify recovery |
| 45 | OpenSearch API key has all privileges | Revoke/quarantine identity, preserve evidence and verify recovery |
| 46 | Snowflake ACCOUNTADMIN used by automation | Freeze privileged change; verify trust, scope and approvals |
| 47 | OIDC token replay from compromised runner | Revoke/quarantine identity, preserve evidence and verify recovery |
| 48 | Break-glass role not time bounded | Freeze privileged change; verify trust, scope and approvals |
| 49 | Network perimeter allows public database ingress | Freeze privileged change; verify trust, scope and approvals |
| 50 | Pod service account cross-namespace escalation | Restrict controller/workload privileges and check service health |
| 51 | Secrets rotation breaks database connection pools | Revoke/quarantine identity, preserve evidence and verify recovery |
| 52 | PITR restore fails due to KMS denial | Revoke/quarantine identity, preserve evidence and verify recovery |
| 53 | SRE on-call locked out during IAM rollback | Freeze privileged change; verify trust, scope and approvals |
| 54 | Privileged GitOps reconciliation undoes security fix | Freeze privileged change; verify trust, scope and approvals |
| 55 | Cloud audit logs disabled by deploy role | Freeze privileged change; verify trust, scope and approvals |

## 9. Production runbooks

**R1 — IAM role overprivilege containment:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

**R2 — OIDC trust boundary investigation:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

**R3 — AWS SCP/permission boundary outage:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

**R4 — Azure federated credential and RBAC recovery:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

**R5 — GCP workload identity compromise:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

**R6 — Kubernetes RBAC and ServiceAccount incident:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

**R7 — Admission/network policy emergency recovery:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

**R8 — GitOps controller privilege escalation:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

**R9 — State backend and KMS access compromise:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

**R10 — Database credential rotation and connection recovery:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

**R11 — Break-glass with independent approval:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

**R12 — Post-incident identity audit and DR acceptance:** Identify affected identities and resources, freeze unauthorized promotion, capture audit and state evidence, confirm least-privilege target, execute approved containment, verify application SLO and DBRE backup/restore, then document owner, ticket, recovery and prevention.

## 10. Troubleshooting

| Symptom | Likely cause | Safe response |
|---|---|---|
| AWS AssumeRole denied | audience/subject or trust mismatch | verify exact OIDC claims, never wildcard |
| Azure deployment unauthorized | RBAC scope/tenant mismatch | correct narrowly scoped assignment |
| GCP service account impersonation denied | WIF attribute or IAM binding | inspect principal and condition |
| Kubernetes 403 | RBAC, ServiceAccount token, admission | `kubectl auth can-i` in staging; scope role |
| NetworkPolicy breaks DNS | missing DNS egress | add narrowly scoped DNS rules |
| Argo CD/Flux cannot reconcile | controller scope, AppProject, RBAC | inspect ownership; do not grant cluster-admin |
| DB connections fail after rotation | stale pool/overlap | restore service, complete staged rotation |
| PITR restore denied | KMS/backup IAM missing | invoke tested break-glass and recovery |

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Zero-trust architecture and threat modeling | 15 |
| AWS/Azure/GCP IAM and workload identity | 25 |
| Kubernetes RBAC, admission and GitOps hardening | 20 |
| Executable offline tests and negative cases | 15 |
| SRE/DBRE incident response and recovery | 15 |
| Audit, break-glass and operational handover | 10 |
| **Total** | **100** |

Pass >=85 and zero critical findings with independent security/SRE/DBRE sign-off. Critical failures: wildcard production identity, CI administrator access, cluster-admin workload, leaked secret, unsafe state backend, missing DB restore or uncontrolled break-glass. **Publication is not production security acceptance.**

**Next:** Chapter 085 — Enterprise IaC Security, Policy and Zero-Trust Production Readiness Capstone.
