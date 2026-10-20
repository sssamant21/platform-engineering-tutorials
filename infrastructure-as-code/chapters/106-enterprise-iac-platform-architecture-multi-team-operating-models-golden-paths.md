# Chapter 106 — Enterprise IaC Platform Architecture, Multi-Team Operating Models and Golden Paths

**Part 22 — Enterprise Platforms · Chapter 106/120 · Enterprise SRE/DBRE**

> **Safety and verification:** The Python gate is a local synthetic model. It does not authenticate users, execute Terraform/OpenTofu, change cloud permissions, deploy Kubernetes workloads, or establish production readiness. Lab tests are authored but not independently executed.

## 1. Learning objectives
Design an enterprise self-service infrastructure platform for AWS, Azure, GCP and Kubernetes using Terraform/OpenTofu, GitOps and policy-as-code. Define platform versus application-team ownership, standardize golden paths, isolate tenants, secure state and secrets, enforce cost and reliability guardrails, and operate the platform using SLOs and production runbooks.

Prerequisites: IaC modules, state and workflows; Kubernetes and GitOps; security and policy-as-code; observability/SLOs; FinOps; disaster recovery (Chapters 101–105).

## 2. Platform architecture

```text
Developer portal / service catalog / approved request schema
                          |
        Golden path templates + versioned IaC modules
                          |
        Git PR + identity + policy + plan + cost gates
                          |
     Environment-specific approval + change audit trail
                          |
 Terraform/OpenTofu runners + isolated state + GitOps sync
                          |
 AWS / Azure / GCP accounts + Kubernetes + data services
                          |
      Observability, SLO, incident response and FinOps
                          |
       Backup, DR, lifecycle management and retirement
```

A golden path is an **approved, supportable default**, not a mandatory one-size-fits-all architecture. Teams must have an exception process for unusual latency, compliance, data residency, security or capacity requirements.

## 3. Team ownership and RACI

| Capability | Platform engineering | SRE | DBRE | Application team | Security |
|---|---|---|---|---|---|
| Module standards and registry | Accountable | Consulted | Consulted | Consumer | Reviewer |
| Cloud account/project baseline | Accountable | Consulted | Consulted | Informed | Approver |
| Cluster fleet lifecycle | Responsible | Accountable for reliability | Consulted | Consumer | Reviewer |
| Database provisioning template | Responsible | Consulted | Accountable | Requester | Reviewer |
| Application SLO and rollout | Support | Consulted | Consulted | Accountable | Informed |
| Backup/PITR and database DR | Support | Consulted | Accountable | Data owner | Reviewer |
| Identity, secrets and policies | Responsible | Consulted | Consulted | Compliant user | Accountable |
| Incident command | Support | Accountable | Responsible for DB incidents | Service owner | Consulted |

Clarify ownership in service catalog metadata, on-call routing, escalation policies and decommission workflows. Do not conflate infrastructure ownership with data stewardship.

## 4. Golden-path service tiers

**Standard web service:** approved container base, Kubernetes Deployment, Service, probes, PDB, HPA, resource quotas, NetworkPolicy, workload identity, centralized logs/traces/metrics, GitOps rollout and rollback.

**Stateful DB-backed service:** standard path plus data classification, encryption, PITR, backup retention, schema-change workflow, replication monitoring, restore test cadence, DBRE approval and explicit RPO/RTO.

**Critical regulated service:** multi-zone resilience, dedicated tenancy when required, policy exceptions, change windows, independent DR, stronger audit evidence and SRE/security approvals.

Every path must specify supported cloud regions, module versions, upgrade compatibility, observability, cost ownership, data retention and decommissioning.

## 5. Module and repository design

```text
platform/
  catalog/
    services/
    owners/
  modules/
    aws-network/
    azure-network/
    gcp-network/
    kubernetes-workload/
    postgres-service/
  templates/
    web-service/
    stateful-service/
  policies/
    terraform/
    kubernetes/
  environments/
    dev/
    stage/
    prod/
  workflows/
    validate-plan-policy-cost/
    promote/
    drift-check/
  runbooks/
    state-recovery/
    module-rollback/
    incident-response/
```

Pin module versions and providers; sign/review release artifacts; isolate production state and credentials; require separate PRs or promotions across environments. A service catalog entry should include team, service, environment, criticality, ownership, data classification, region, budget, SLO, RPO/RTO and support links.

## 6. Policy-as-code and supply-chain controls

1. Authenticate requesters using enterprise identity; authorize by team and environment.
2. Enforce approved regions, instance classes, labels/tags, encryption and network isolation.
3. Run static analysis, IaC linting, plan checks, dependency/license scanning and cost estimation.
4. Use workload identity/OIDC for CI runners; avoid long-lived provider credentials.
5. Separate read-only plan from privileged apply; require approval for production or destructive diffs.
6. Keep Terraform/OpenTofu state encrypted, access-controlled, versioned, locked and recoverable.
7. Store secrets in a managed secret store, not Git, state output or logs.
8. Use signed immutable container images and controlled registries; restrict admission.
9. Preserve plan hashes, approvals, policy results, drift history and deployment audit evidence.
10. Support time-limited, reviewed exceptions with explicit owners and expiry.

## 7. Lab A — Offline platform request gate

Create `infrastructure-as-code/labs/chapter-106/platform_gate.py`:

```python
"""Offline golden-path request gate; never provisions infrastructure."""
from dataclasses import dataclass

ALLOWED_ENVIRONMENTS = frozenset({"dev", "stage", "prod"})
APPROVED_REGIONS = frozenset({"us-east-1", "us-west-2"})
APPROVED_TIERS = frozenset({"standard", "critical"})
MAX_MONTHLY_BUDGET_USD = 100000

@dataclass(frozen=True)
class PlatformRequest:
    team: str
    service: str
    environment: str
    region: str
    tier: str
    module_version_pinned: bool
    workload_identity_enabled: bool
    secrets_externalized: bool
    state_encrypted: bool
    state_locked: bool
    policy_checks_passed: bool
    plan_reviewed: bool
    cost_estimate_usd: int
    budget_approved: bool
    sre_approved: bool
    dbre_approved: bool
    contains_database: bool

def evaluate(request: PlatformRequest):
    if not request.team.strip() or not request.service.strip():
        raise ValueError("team and service are required")
    if request.cost_estimate_usd < 0:
        raise ValueError("negative cost estimate")
    checks = {
        "environment": request.environment in ALLOWED_ENVIRONMENTS,
        "region": request.region in APPROVED_REGIONS,
        "tier": request.tier in APPROVED_TIERS,
        "pinned_module": request.module_version_pinned,
        "workload_identity": request.workload_identity_enabled,
        "external_secrets": request.secrets_externalized,
        "encrypted_state": request.state_encrypted,
        "state_lock": request.state_locked,
        "policy": request.policy_checks_passed,
        "plan_review": request.plan_reviewed,
        "budget": request.budget_approved and request.cost_estimate_usd <= MAX_MONTHLY_BUDGET_USD,
        "sre_approval": request.sre_approved,
        "dbre_approval": (not request.contains_database) or request.dbre_approved,
    }
    failed = [name for name, ok in checks.items() if not ok]
    return {"decision": "REVIEW_READY" if not failed else "NO_GO",
            "failed_controls": failed}
```

The result `REVIEW_READY` means the **modeled request** meets the offline contract; it is not an authorization token and does not prove a real cloud configuration.

## 8. Lab B — Negative tests

Create `infrastructure-as-code/labs/chapter-106/test_platform_gate.py`:

```python
import unittest
from dataclasses import replace
from platform_gate import PlatformRequest, evaluate

class GoldenPathGateTests(unittest.TestCase):
    def setUp(self):
        self.valid = PlatformRequest(
            "checkout", "payments-api", "stage", "us-east-1", "critical",
            True, True, True, True, True, True, True,
            5000, True, True, True, True)
    def test_valid(self):
        self.assertEqual(evaluate(self.valid)["decision"], "REVIEW_READY")
    def test_invalid_region(self):
        self.assertIn("region", evaluate(replace(self.valid, region="unknown"))["failed_controls"])
    def test_production_security_controls(self):
        for field in ("module_version_pinned", "workload_identity_enabled",
                      "secrets_externalized", "state_encrypted", "state_locked",
                      "policy_checks_passed", "plan_reviewed", "budget_approved",
                      "sre_approved"):
            with self.subTest(field=field):
                self.assertEqual(evaluate(replace(self.valid, **{field:False}))["decision"], "NO_GO")
    def test_database_approval(self):
        self.assertIn("dbre_approval", evaluate(replace(self.valid, dbre_approved=False))["failed_controls"])
        self.assertEqual(evaluate(replace(self.valid, contains_database=False, dbre_approved=False))["decision"], "REVIEW_READY")
    def test_budget_cap(self):
        self.assertIn("budget", evaluate(replace(self.valid, cost_estimate_usd=100001))["failed_controls"])
    def test_negative_cost(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.valid, cost_estimate_usd=-1))
    def test_blank_service(self):
        with self.assertRaises(ValueError):
            evaluate(replace(self.valid, service=" "))
if __name__ == "__main__":
    unittest.main()
```

From the repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-106 -p 'test_*.py' -v
```

## 9. Lab C — Build a Kubernetes golden path (manual)

1. Create a dedicated staging namespace and least-privilege workload identity.
2. Author a reusable module/template for Deployment, Service, probes, requests/limits, PDB, HPA, NetworkPolicy and standard labels.
3. Define an approved service catalog schema with team ownership, SLO, cost center and data classification.
4. Validate `terraform fmt -check`, `terraform validate` and a reviewed `terraform plan`; use isolated staging state.
5. Add CI policy checks for allowed regions, encrypted storage, prohibited public exposure, resource limits and signed images.
6. Require a reviewer for changes to IAM, networking, state backend or production resources.
7. Deploy via GitOps in staging and validate health, autoscaling, traffic, logs, traces and SLO dashboards.
8. Simulate an invalid policy request and verify deployment is blocked without changing infrastructure.
9. Record module version, plan hash, approval, deployment and rollback evidence.
10. Destroy only explicitly approved disposable staging resources.

## 10. Lab D — Stateful DBRE golden path (manual)

Create a synthetic PostgreSQL service request with explicit RPO/RTO, PITR retention, storage capacity, encryption, SLO, maintenance windows and DBRE owner. Provision only in staging using an approved module; test connection security, backup job evidence, PITR restore to an isolated instance, storage growth alerts and failback plan. Repeat architecture review for MongoDB, Redis, Kafka and Elasticsearch, accounting for their distinct durability and recovery semantics.

## 11. Troubleshooting scenarios

| Failure | Signal | Safe response |
|---|---|---|
| Wrong team ownership | missing catalog owner | block request |
| Unauthorized prod request | RBAC denial | verify identity/approval |
| Module version drift | mismatched lockfiles | pin and review |
| Terraform state contention | backend lock | identify owner, retry safely |
| State backend unavailable | API errors | isolated recovery procedure |
| Excessive IAM privileges | policy scan | reduce permissions |
| Secrets in plan output | sensitive output | stop and rotate as required |
| Unsupported region | policy gate | choose approved location |
| Budget exceeded | cost estimate | revise or approve exception |
| Public storage exposure | security scan | block deployment |
| Kubernetes quota exceeded | admission failure | adjust approved quota |
| NetworkPolicy denies traffic | connection failures | review allowed paths |
| HPA never scales | metrics unavailable | restore metrics pipeline |
| PDB blocks maintenance | eviction failures | revise disruption policy |
| GitOps drift loop | reconciliation events | fix source of truth |
| Database PITR missing | archive gap | stop acceptance |
| DBRE restore inconsistent | checksum mismatch | quarantine recovery |
| SLO absent | no telemetry | block critical promotion |
| Module rollback fails | incompatible schema | use reviewed migration |
| Service retirement incomplete | orphaned resources | owner-led cleanup |

## 12. Production runbooks

**RB-01 Service onboarding:** verify owner, service tier, catalog contract, budget and support contacts.

**RB-02 Module release:** test compatibility, pin versions, scan dependencies and stage rollout.

**RB-03 Policy rejection:** explain violated control, remediation and approved exception route.

**RB-04 State incident:** preserve locks and snapshots; restore isolated state before any reconciliation.

**RB-05 Credential incident:** revoke exposed identity, audit activity and restore workload identity.

**RB-06 Kubernetes golden path incident:** validate admission, quotas, probes, PDB/HPA, routing and GitOps sync.

**RB-07 DBRE platform incident:** verify database ownership, PITR, replication, capacity and recovery SLO.

**RB-08 Drift and reconciliation:** compare Git, state and live resources; review plan before apply.

**RB-09 Rollback:** restore approved module/application version, verify state and customer transactions.

**RB-10 Platform decommission:** obtain data owner approval, respect retention, remove access and record resource disposal.

## 13. Enterprise acceptance (100 points)

| Control | Points |
|---|---:|
| Ownership and service catalog | 10 |
| Versioned modules and golden paths | 15 |
| Least privilege and workload identity | 15 |
| Policy, supply-chain and approvals | 15 |
| Isolated IaC state and recovery | 10 |
| Kubernetes deployment and SLO | 10 |
| DBRE data durability and restore | 10 |
| FinOps tagging and budget controls | 5 |
| Incident response, rollback and audit | 10 |
| **Total** | **100** |

Production acceptance requires at least 90/100 **plus** real policy enforcement, reviewed production plans, state recovery, application SLOs, DBRE restore evidence where relevant, and independent security/SRE approval. Any mandatory control failure is **NO-GO** regardless of score.

## 14. Cleanup and next chapter
Preserve sanitized plans, policy outputs, module hashes, catalog entries, test reports and approvals. Do not delete production infrastructure or data to complete the lab.

**Next:** Chapter 107 — Enterprise IaC Self-Service Portals, Service Catalogs and Developer Experience.
