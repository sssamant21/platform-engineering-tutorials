# Chapter 108 — Enterprise IaC Multi-Tenancy, Governance, RBAC and Policy Enforcement at Scale

**Part 22 — Enterprise Platforms · Chapter 108/120 · Enterprise SRE/DBRE**

> **Boundary:** The included Python gate evaluates synthetic requests only. It does not authenticate identities, query real IAM/RBAC, enforce Kubernetes admission, or approve production changes. Native security validation and independent acceptance remain pending.

## 1. Learning objectives
Build a governed, multi-tenant infrastructure platform using AWS, Azure, GCP, Kubernetes, Terraform/OpenTofu and GitOps. Implement identity federation, scoped RBAC, workload identity, policy-as-code, tenant-specific state, network and data isolation, approvals, exception workflows, emergency access and audit evidence.

Prerequisites: Chapters 106–107, cloud IAM, Kubernetes RBAC/NetworkPolicy, OIDC, IaC state, policy-as-code, secrets and SRE/DBRE incident management.

## 2. Enterprise tenancy architecture
```text
SSO / IdP / OIDC + enterprise directory
                   |
     Tenant service catalog + ownership
                   |
    Request schema + authorization engine
                   |
  Policy-as-code + signed plan + approvals
                   |
    Isolated CI runners + workload identity
                   |
 Tenant account/project/subscription + IaC state
                   |
 Namespace/cluster boundary + network + storage
                   |
      Observability + audit + cost + DR
```

Use isolation boundaries proportional to risk. Kubernetes namespaces are not sufficient isolation for hostile tenants or workloads requiring separate cluster administrators. Cloud accounts/projects/subscriptions, dedicated clusters, network boundaries, KMS keys and database instances may be required for higher assurance.

## 3. Tenant identity and RBAC

Define **principal, tenant, resource, environment, action, role, policy decision and approval evidence** for every request. Avoid global admin roles in self-service workflows.

| Role | Read | Plan | Apply | Destroy |
|---|---|---|---|---|
| Reader | Tenant-scoped | No | No | No |
| Operator | Tenant-scoped | Yes | Approved only | No |
| Admin | Tenant-scoped | Yes | Approved only | Separately approved |
| Platform security | Audit and policy review | Review | Controlled | Controlled |

Actual permissions must be enforced by cloud IAM, Kubernetes RBAC, admission policy and the CI execution identity. Portal-level visibility controls are not a security boundary.

## 4. AWS, Azure and GCP governance

**AWS:** Organizations/OUs, account isolation, SCPs, IAM Identity Center, IAM roles, STS/OIDC, permission boundaries, KMS, VPC controls, AWS Config and CloudTrail. Test both allowed and denied requests under representative identities.

**Azure:** Management groups, subscriptions, Entra ID, Azure RBAC, Policy initiatives, managed identities, Key Vault, resource locks and Activity Logs. Verify role assignments at the correct scopes.

**GCP:** Organization/folders/projects, IAM, organization policies, service account impersonation/workload identity federation, VPC Service Controls where applicable, Cloud KMS and Cloud Audit Logs.

Cloud organization policies and service-control boundaries vary by service. Never assume an IaC plan gate replaces provider-native deny controls.

## 5. Terraform/OpenTofu and GitOps separation
- Maintain tenant/environment-specific backends and encryption keys; grant state read/write only to approved runners.
- Keep provider aliases, credentials, plan artifacts and module registries scoped by environment.
- Pin module/provider versions; verify plan hashes immediately before apply.
- Deny direct apply from developer workstations to production; require protected branches and environment approvals.
- Separate plan permissions from apply credentials and require human review for sensitive diffs.
- Reconcile GitOps using scoped projects/namespaces and service accounts; deny cluster-scoped resource creation unless explicitly approved.
- Alert on drift, out-of-band IAM changes and unexpected policy exceptions.

## 6. Kubernetes multi-tenancy controls
Use namespaces and ResourceQuota/LimitRange for shared low-risk workloads; namespace RBAC and admission controls; default-deny NetworkPolicy where supported by the CNI; Pod Security Admission restricted profile; workload identity, image provenance and secrets isolation; topology-aware placement; separate clusters for stronger trust boundaries. Verify CRDs/operators and admission webhooks do not expose cross-tenant privilege escalation.

## 7. DBRE isolation and data governance
Database access must be scoped to a tenant and service identity, not a shared administrative credential. Validate PostgreSQL roles and schema/database isolation, MongoDB roles and deployment boundaries, Redis ACLs and keyspace limitations, Kafka ACLs and topic quotas, and Elasticsearch roles, index-level permissions and snapshot repository controls. Stronger isolation may require dedicated instances/clusters. Preserve tenant-specific retention, backup encryption, audit, PITR, RPO/RTO and data deletion approvals.

## 8. Lab A — Offline authorization decision engine
Create `infrastructure-as-code/labs/chapter-108/tenant_gate.py`:

```python
"""Offline tenant authorization gate. No external identity or cloud calls."""
from dataclasses import dataclass

ENVIRONMENTS={"dev","stage","prod"}
ACTIONS={"plan","apply","read","destroy"}
SENSITIVE={"apply","destroy"}

@dataclass(frozen=True)
class AccessRequest:
    principal: str
    principal_tenant: str
    resource_tenant: str
    environment: str
    action: str
    role: str
    workload_identity: bool
    policy_passed: bool
    approval_bound_to_plan: bool
    change_approved: bool
    security_approved: bool
    dbre_approved: bool
    database_resource: bool
    emergency_access: bool
    emergency_ticket_valid: bool
    emergency_expires_in_minutes: int

def authorize(r: AccessRequest):
    if not r.principal.strip() or not r.principal_tenant.strip() or not r.resource_tenant.strip():
        raise ValueError("identity and tenant identifiers required")
    if r.emergency_expires_in_minutes < 0:
        raise ValueError("invalid emergency TTL")
    cross_tenant = r.principal_tenant != r.resource_tenant
    elevated = r.action in SENSITIVE
    checks={
        "environment":r.environment in ENVIRONMENTS,
        "action":r.action in ACTIONS,
        "role":r.role in {"reader","operator","admin"},
        "role_scope":r.role=="admin" or (r.role=="operator" and r.action!="destroy") or (r.role=="reader" and r.action=="read"),
        "tenant_isolation":not cross_tenant,
        "workload_identity":r.workload_identity,
        "policy":r.policy_passed,
        "plan_binding":not elevated or r.approval_bound_to_plan,
        "change_approval":not elevated or r.change_approved,
        "security_approval":r.environment!="prod" or not elevated or r.security_approved,
        "dbre_approval":not (r.database_resource and elevated) or r.dbre_approved,
        "break_glass":not r.emergency_access or (r.emergency_ticket_valid and 0<r.emergency_expires_in_minutes<=60),
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {"decision":"REVIEW_READY" if not failed else "DENY","failed":failed}
```

A result of `REVIEW_READY` is a modeled preflight result, **not** a bearer token or authorization to apply changes.

## 9. Lab B — Negative tests
Create `infrastructure-as-code/labs/chapter-108/test_tenant_gate.py`:

```python
import unittest
from dataclasses import replace
from tenant_gate import AccessRequest, authorize

class TenantGateTests(unittest.TestCase):
    def setUp(self):
        self.r=AccessRequest("ci-orders","orders","orders","prod","apply",
            "operator",True,True,True,True,True,True,True,False,False,0)
    def test_valid(self):
        self.assertEqual(authorize(self.r)["decision"],"REVIEW_READY")
    def test_cross_tenant(self):
        self.assertIn("tenant_isolation",authorize(replace(self.r,resource_tenant="billing"))["failed"])
    def test_production_approvals(self):
        for field in ("workload_identity","policy_passed","approval_bound_to_plan",
                      "change_approved","security_approved","dbre_approved"):
            with self.subTest(field=field):
                self.assertEqual(authorize(replace(self.r,**{field:False}))["decision"],"DENY")
    def test_reader_cannot_apply(self):
        self.assertIn("role_scope",authorize(replace(self.r,role="reader"))["failed"])
    def test_destroy_requires_admin(self):
        self.assertIn("role_scope",authorize(replace(self.r,action="destroy"))["failed"])
    def test_break_glass_expires(self):
        self.assertIn("break_glass",authorize(replace(self.r,emergency_access=True,
            emergency_ticket_valid=True,emergency_expires_in_minutes=61))["failed"])
    def test_emergency_does_not_override_tenant(self):
        self.assertIn("tenant_isolation",authorize(replace(self.r,resource_tenant="billing",
            emergency_access=True,emergency_ticket_valid=True,emergency_expires_in_minutes=30))["failed"])
    def test_invalid_ttl(self):
        with self.assertRaises(ValueError):
            authorize(replace(self.r,emergency_expires_in_minutes=-1))
if __name__=="__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-108 -p 'test_*.py' -v
```

Tests cover cross-tenant denial, production approvals, role boundaries, destroy restrictions, emergency access expiry and invalid inputs.

## 10. Lab C — Tenant isolation in Kubernetes (manual)
1. Create two disposable staging namespaces, tenant-a and tenant-b, and separate test service accounts.
2. Apply least-privilege Roles/RoleBindings, quotas, Pod Security Admission and default-deny network policies.
3. Bind each workload to its own cloud workload identity and secret store path.
4. Verify tenant-a can read only authorized tenant-a resources; test denied reads of tenant-b secrets, ConfigMaps and workloads.
5. Attempt a controlled cross-namespace network connection and confirm the network policy denies it where enforced by the CNI.
6. Verify neither tenant can create ClusterRoleBindings, mutate admission webhooks or modify cluster-scoped resources.
7. Test an approved scoped deployment through GitOps and a rejected privilege escalation.
8. Capture sanitized audit events, identity claims, policy results and approvals.
9. Remove only disposable staging resources after owner approval.

## 11. Lab D — Cloud and DBRE policy validation (manual)
1. Create isolated staging cloud tenants (accounts/subscriptions/projects) with separate IAM and state backends.
2. Verify a CI runner for tenant-a cannot read tenant-b state, KMS keys or storage.
3. Execute read-only policy simulations for unauthorized regions, public buckets, unrestricted ingress and excessive IAM grants.
4. Request a staging PostgreSQL/MongoDB service; confirm DBRE approval and tenant-scoped database credentials.
5. Verify a second tenant cannot connect, read backup copies or restore data using its own credentials.
6. Confirm audit logs, retention and cost attribution are tenant-scoped.
7. Exercise a time-limited emergency access request with approval and revocation evidence.
8. Record control-plane and data-plane results independently.

## 12. Troubleshooting scenarios
| Scenario | Evidence | Safe response |
|---|---|---|
| Cross-tenant state read | access logs | revoke and rotate |
| Wrong IAM scope | role evaluation | narrow assignment |
| Privilege escalation | policy denial | block and review |
| Missing workload identity | pod auth failure | repair federation |
| OIDC claim mismatch | token audience | fix trust mapping |
| Expired credentials | STS/IdP error | renew approved identity |
| SCP/org policy blocks request | deny event | review permitted design |
| Namespace escape attempt | admission audit | quarantine workload |
| NetworkPolicy ineffective | CNI tests | enforce supported policy |
| Shared secret exposure | access log | rotate and isolate |
| Global Terraform runner role | IAM inventory | split runner identities |
| Shared state backend | access boundary | migrate safely |
| Unreviewed plan change | hash mismatch | regenerate approval |
| GitOps project overreach | sync permissions | scope controller |
| Database admin reused | DB auth logs | create tenant roles |
| Backup cross-tenant access | vault audit | isolate keys/copies |
| Cost tags missing | billing report | enforce admission |
| Emergency access not revoked | IAM audit | revoke immediately |
| Policy engine unavailable | missing decision | fail closed |
| Tenant offboarding incomplete | inventory | retention-led cleanup |

## 13. Production runbooks
**RB-01 Cross-tenant incident:** contain access, preserve logs, revoke credentials and notify owners.

**RB-02 IAM misconfiguration:** compare intended policy with effective provider permissions and correct scope.

**RB-03 Kubernetes RBAC escalation:** inspect audit, admission, cluster roles and service accounts.

**RB-04 State isolation breach:** lock access, preserve versions, rotate keys and reconcile affected states.

**RB-05 OIDC failure:** validate issuer, audience, subject claims, role trust and token expiry.

**RB-06 Policy denial:** document violated control and remediation; never silently bypass.

**RB-07 Break-glass:** authorize, time-limit, log, monitor and revoke emergency permissions.

**RB-08 DBRE tenant isolation:** validate database roles, credentials, backup access and audit evidence.

**RB-09 GitOps privilege incident:** suspend affected reconciliation and review controller scope.

**RB-10 Tenant retirement:** obtain data-owner sign-off, respect retention and remove credentials, resources and access.

## 14. Enterprise acceptance assessment (100 points)
| Domain | Points |
|---|---:|
| Tenant ownership and identity | 10 |
| Cloud IAM and organizational boundaries | 15 |
| Kubernetes RBAC, network and admission | 15 |
| Terraform/OpenTofu state and runner isolation | 15 |
| Policy-as-code and approval binding | 15 |
| DBRE credentials, backup and data boundaries | 10 |
| Audit, detection and incident response | 10 |
| Break-glass and offboarding | 5 |
| Cost attribution and exception governance | 5 |
| **Total** | **100** |

**Acceptance:** 90+ points and mandatory evidence of denied cross-tenant access, least privilege, isolated state and keys, working policy enforcement, database access isolation, audited emergency access and independent security/SRE/DBRE sign-off. Any mandatory failure is **NO-GO**.

## 15. Cleanup and next chapter
Preserve sanitized authorization traces, negative-test results, audit IDs, plan hashes and approvals. Remove only authorized staging resources; do not use real customer data for negative-access tests.

**Next:** Chapter 109 — Enterprise IaC Platform Reliability, SLOs, Capacity and Operational Excellence.
