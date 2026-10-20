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
