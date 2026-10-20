# Chapter 107 — Enterprise IaC Self-Service Portals, Service Catalogs and Developer Experience

**Part 22 — Enterprise Platforms · Chapter 107/120 · Enterprise SRE/DBRE**

> **Evidence boundary:** The offline gate below is a synthetic request validator. It is not an identity provider, authorization service, Terraform runner, real service catalog or production deployment. All native tests and acceptance require separate execution.

## 1. Learning objectives
Design a self-service portal and service catalog that safely provisions AWS, Azure, GCP, Kubernetes and DBRE infrastructure through Terraform/OpenTofu and GitOps. Build service ownership contracts, golden-path templates, request validation, policy gates, cost approval, audit evidence, change workflows and retirement procedures.

**Prerequisites:** Chapter 106, IaC state and modules, Kubernetes/GitOps, OIDC/IAM, SRE SLOs, DBRE backup/PITR, policy-as-code and FinOps.

## 2. Enterprise portal architecture

```text
Developer -> portal (Backstage or equivalent)
                |
       SSO / OIDC + group RBAC
                |
 Service catalog + ownership + templates
                |
     request schema + policy + cost + approvals
                |
      Git pull request + plan + review
                |
  short-lived CI identity + Terraform/OpenTofu
                |
   AWS/Azure/GCP + Kubernetes + data platform
                |
 GitOps deployment + observability + SLO + DR
                |
    audit / drift / lifecycle / decommission
```

The portal is a **control-plane interface**, not a privileged shell. It should not hold long-lived cloud credentials or permit arbitrary user-supplied Terraform execution. Use approved templates, isolated runners and least-privilege environment identities.

## 3. Catalog and service ownership contract

Each catalog entry should declare: unique service ID, owner/team, escalation route, cost center, business criticality, data classification, environment, region, repository, golden-path template version, IaC state backend, SLO, RPO/RTO, backup/retention, DBRE owner where applicable, security reviewer, dependencies and decommission status.

Use an explicit lifecycle: **requested → validated → approved → planned → provisioned → verified → operated → retired**. Store immutable evidence of each transition. Request submission is not approval; successful infrastructure apply is not application acceptance.

### Platform ownership model
- Platform engineering owns templates, module registries, portal infrastructure, policy pipelines and state backend standards.
- SRE owns platform reliability controls, SLOs, incident escalation and critical change review.
- DBRE owns database recovery, performance, backup/PITR and data-integrity approval.
- Application teams own service configuration, business SLOs, application changes and data stewardship.
- Security owns access policy, sensitive-data controls, secrets and exception governance.
- FinOps owns cost allocation policy, budgets and chargeback evidence.

## 4. Golden-path catalog templates

| Template | Standardized outputs | Required approval |
|---|---|---|
| Stateless API | Namespace, Deployment, Service, HPA/PDB, observability | Team + policy |
| Critical API | Above plus multi-zone, stricter SLO and DR | SRE + security |
| PostgreSQL service | Private database, encryption, PITR, monitoring | DBRE |
| MongoDB service | Replica architecture, backup, indexes, monitoring | DBRE |
| Redis cache | Persistence policy, memory limits, failover | DBRE |
| Kafka workload | Topics, ACLs, quotas, offsets/retention | Data platform |
| Elasticsearch workload | Index lifecycle, snapshots, quotas | Search/DBRE |
| Batch/data pipeline | Job identity, schedule, logs, retries, cost tags | Data owner |

Template versions must be pinned, supported, tested and upgradeable. Expose approved configuration choices, not unbounded provider arguments.

## 5. Security, policy and execution workflow
1. Authenticate the requester using enterprise SSO/OIDC; map groups to service/team entitlements.
2. Validate service ownership, environment, allowed region, data class, cost center and template version.
3. Check whether the requester is authorized to create or modify that resource type and environment.
4. Create a pull request with a deterministic, reviewable configuration diff.
5. Run lint, Terraform/OpenTofu validate/plan, policy-as-code, supply-chain scanning and cost estimation.
6. Reject secrets in source, public data stores, unrestricted ingress, excessive IAM and unsupported regions.
7. Require separate approval for production, privileged resources, confidential data and database changes.
8. Execute the approved plan through a scoped short-lived workload identity; preserve plan and artifact hashes.
9. Verify deployed resource ownership, security posture, observability, application transactions and DR contract.
10. Publish the service record, support links, audit events and lifecycle operations back to the catalog.

**TOCTOU risk:** approval of one plan must not authorize a different later plan. Bind approval to a plan hash and revalidate policy immediately before apply.

## 6. Hands-on lab A — Offline request contract

Create `infrastructure-as-code/labs/chapter-107/catalog_gate.py`:

```python
"""Offline service-catalog request evaluator. No API, deployment or auth side effects."""
from dataclasses import dataclass
import re

NAME = re.compile(r"^[a-z][a-z0-9-]{2,39}$")
TIERS = {"standard", "critical"}
ENVIRONMENTS = {"dev", "stage", "prod"}
DATA_CLASSES = {"public", "internal", "confidential", "restricted"}

@dataclass(frozen=True)
class CatalogRequest:
    service: str
    owner: str
    cost_center: str
    environment: str
    tier: str
    data_class: str
    template_version: str
    region_allowed: bool
    authenticated: bool
    authorized: bool
    policy_passed: bool
    estimated_monthly_cost: int
    approved_budget: int
    sre_approved: bool
    security_approved: bool
    database_requested: bool
    dbre_approved: bool
    rpo_minutes: int
    rto_minutes: int
    rollback_documented: bool

def validate(request: CatalogRequest):
    if request.estimated_monthly_cost < 0 or request.approved_budget < 0:
        raise ValueError("costs cannot be negative")
    if request.rpo_minutes < 0 or request.rto_minutes < 0:
        raise ValueError("recovery objectives cannot be negative")
    checks = {
        "service_name": bool(NAME.fullmatch(request.service)),
        "owner": bool(request.owner.strip()),
        "cost_center": bool(request.cost_center.strip()),
        "environment": request.environment in ENVIRONMENTS,
        "tier": request.tier in TIERS,
        "data_class": request.data_class in DATA_CLASSES,
        "template_pinned": bool(re.fullmatch(r"v[0-9]+\\.[0-9]+\\.[0-9]+", request.template_version)),
        "region": request.region_allowed,
        "authentication": request.authenticated,
        "authorization": request.authorized,
        "policy": request.policy_passed,
        "budget": request.estimated_monthly_cost <= request.approved_budget,
        "sre_approval": request.environment != "prod" or request.sre_approved,
        "security_approval": request.data_class not in {"confidential", "restricted"} or request.security_approved,
        "dbre_approval": not request.database_requested or request.dbre_approved,
        "recovery_contract": not request.database_requested or (request.rpo_minutes > 0 and request.rto_minutes > 0),
        "rollback": request.rollback_documented,
    }
    failed = [key for key, passed in checks.items() if not passed]
    return {"decision": "REVIEW_READY" if not failed else "NO_GO", "failed": failed}
```

`REVIEW_READY` means only that the modeled inputs satisfy the checks. It does not prove the identity claims or approve a live deployment.

## 7. Hands-on lab B — Unit and negative tests

Create `infrastructure-as-code/labs/chapter-107/test_catalog_gate.py`:

```python
import unittest
from dataclasses import replace
from catalog_gate import CatalogRequest, validate

class CatalogGateTests(unittest.TestCase):
    def setUp(self):
        self.r = CatalogRequest("orders-api", "orders-team", "CC-100", "prod",
            "critical", "confidential", "v1.2.3", True, True, True, True,
            4000, 5000, True, True, True, True, 15, 60, True)
    def test_valid(self):
        self.assertEqual(validate(self.r)["decision"], "REVIEW_READY")
    def test_security_and_ownership(self):
        for field in ("authenticated","authorized","policy_passed","sre_approved",
                      "security_approved","dbre_approved","rollback_documented"):
            with self.subTest(field=field):
                self.assertEqual(validate(replace(self.r, **{field:False}))["decision"],"NO_GO")
    def test_budget(self):
        self.assertIn("budget",validate(replace(self.r,estimated_monthly_cost=9000))["failed"])
    def test_unpinned_template(self):
        self.assertIn("template_pinned",validate(replace(self.r,template_version="latest"))["failed"])
    def test_database_recovery(self):
        self.assertIn("recovery_contract",validate(replace(self.r,rpo_minutes=0))["failed"])
    def test_bad_name(self):
        self.assertIn("service_name",validate(replace(self.r,service="Bad Name"))["failed"])
    def test_negative_cost(self):
        with self.assertRaises(ValueError):
            validate(replace(self.r,approved_budget=-1))
if __name__ == "__main__":
    unittest.main()
```

Run:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-107 -p 'test_*.py' -v
```

Tests cover authorization, SRE/security/DBRE approvals, cost limits, template pinning, recovery objectives, service naming and invalid inputs.

## 8. Hands-on lab C — Portal and service catalog (manual)

1. Deploy an approved portal implementation such as Backstage into an isolated staging environment; use enterprise SSO test identities.
2. Configure a software catalog and define ownership entities for platform, SRE, DBRE and application teams.
3. Publish a versioned stateless-service template that generates catalog metadata, IaC configuration and a Git pull request.
4. Map template parameters to a constrained request schema; reject unsupported regions, unauthorized teams and invalid tags.
5. Connect the template to CI plan/policy/cost checks, without giving the portal direct privileged cloud credentials.
6. Create a staging request, review the generated PR and capture the plan hash and approvals.
7. Deploy through an isolated runner and GitOps; verify owner, namespace, SLO probes, security and cost tags.
8. Test unauthorized production access and confirm no deployment occurs.
9. Capture audit trail, logs, screenshots, request IDs and reviewer sign-off.
10. Retire the disposable staging service through an approved lifecycle workflow.

## 9. Hands-on lab D — Database self-service with DBRE safeguards (manual)

Request a nonproduction PostgreSQL service with a 15-minute illustrative RPO and 60-minute illustrative RTO. Verify private networking, encryption, restricted credentials, PITR configuration, backup evidence, storage alerts, database ownership, schema-change process and DBRE approval. Perform a restore into an isolated staging database, verify transactions and record actual RPO/RTO. Repeat a policy review for MongoDB, Redis, Kafka and Elasticsearch according to their durability semantics.

## 10. Troubleshooting scenarios

| Failure | Signal | Safe resolution |
|---|---|---|
| Missing service owner | catalog validation | reject request |
| Duplicate service ID | uniqueness check | reconcile catalog |
| Unauthorized environment | RBAC denial | block and review |
| Expired SSO token | authentication error | reauthenticate |
| Wrong team group | entitlement mismatch | correct IAM |
| Template version unpinned | schema check | pin approved release |
| Malicious template input | unsafe generated diff | reject and sanitize |
| Secrets in PR | scanning alert | revoke and remove |
| Terraform state conflict | lock contention | identify owner |
| Plan changed after approval | hash mismatch | require new review |
| Policy engine unavailable | missing result | fail closed |
| Unsupported region | residency policy | select approved region |
| Budget exceeded | cost gate | seek exception |
| CI identity overprivileged | IAM audit | restrict role |
| GitOps drift loop | reconciliation events | fix desired state |
| Kubernetes quota exceeded | admission failure | review quota |
| Database backup missing | restore check | block acceptance |
| RPO/RTO unspecified | catalog contract | reject DB request |
| Service has no SLO | observability audit | add telemetry |
| Decommission leaves data | retention mismatch | data-owner review |

## 11. Production runbooks

**RB-01 Portal outage:** preserve queued requests; verify SSO, catalog backend, CI and Git integrations; no direct privileged workaround.

**RB-02 Catalog ownership:** identify orphaned services and route to accountable owners.

**RB-03 Authorization failure:** inspect entitlement mapping and audit; do not bypass policy.

**RB-04 Template rollback:** pin prior approved release and validate generated diffs.

**RB-05 Plan approval mismatch:** halt apply, regenerate plan and obtain new approval.

**RB-06 State lock incident:** inspect lock owner and backend health; avoid blind force-unlock.

**RB-07 Policy engine outage:** fail closed, preserve request and escalate.

**RB-08 DBRE provisioning failure:** validate backup/PITR, access, capacity, SLO and recovery ownership.

**RB-09 Service SLO regression:** correlate portal provisioned changes with traces, metrics, logs and rollbacks.

**RB-10 Service retirement:** confirm retention, owner approval, secrets revocation, resource cleanup and audit record.

## 12. Enterprise acceptance (100 points)

| Domain | Points |
|---|---:|
| Catalog ownership and lifecycle | 15 |
| Authentication, authorization and tenant isolation | 15 |
| Versioned templates and developer experience | 10 |
| Plan/policy/cost controls | 15 |
| Short-lived execution identity and state safety | 10 |
| Kubernetes and application SLO verification | 10 |
| DBRE backup, PITR and data recovery | 10 |
| Audit, rollback and incident response | 10 |
| Documentation and onboarding | 5 |
| **Total** | **100** |

**Production acceptance:** at least 90/100 plus mandatory live identity authorization, policy enforcement, approved plan hash, state protection, workload SLO, database restore evidence where applicable and independent security/SRE/DBRE review. Any mandatory failure means **NO-GO**.

## 13. Cleanup and next chapter
Remove only disposable staging resources after service/data-owner approval. Preserve sanitized requests, generated PRs, plans, policy results, cost estimates, approval records, restore evidence and lifecycle events.

**Next:** Chapter 108 — Enterprise IaC Multi-Tenancy, Governance, RBAC and Policy Enforcement at Scale.
