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
