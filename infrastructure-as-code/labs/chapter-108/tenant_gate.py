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
