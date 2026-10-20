"""Offline platform reliability SLO acceptance gate; no infrastructure actions."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ReliabilityEvidence:
    platform: str
    window_days: int
    requests_total: int
    requests_successful: int
    availability_slo_percent: float
    p95_provision_seconds: float
    p95_target_seconds: float
    queue_depth: int
    queue_limit: int
    runner_capacity_percent: float
    runner_capacity_limit_percent: float
    state_backend_healthy: bool
    state_restore_tested: bool
    policy_engine_healthy: bool
    gitops_reconciliation_healthy: bool
    audit_events_complete: bool
    incident_runbook_tested: bool
    sre_approved: bool
    dbre_approved: bool
    manages_databases: bool

def assess(e: ReliabilityEvidence):
    if not e.platform.strip() or e.window_days <= 0 or e.requests_total <= 0:
        raise ValueError("invalid platform, window or request count")
    if not 0 <= e.requests_successful <= e.requests_total:
        raise ValueError("invalid successful request count")
    if not 0 < e.availability_slo_percent <= 100:
        raise ValueError("invalid SLO")
    values=(e.p95_provision_seconds,e.p95_target_seconds,e.queue_depth,
            e.queue_limit,e.runner_capacity_percent,e.runner_capacity_limit_percent)
    if any(v < 0 for v in values) or e.queue_limit <= 0 or e.p95_target_seconds <= 0:
        raise ValueError("invalid performance or capacity")
    availability=100*e.requests_successful/e.requests_total
    allowed_failures=e.requests_total*(100-e.availability_slo_percent)/100
    observed_failures=e.requests_total-e.requests_successful
    checks={
        "availability":availability >= e.availability_slo_percent,
        "provision_latency":e.p95_provision_seconds <= e.p95_target_seconds,
        "queue":e.queue_depth <= e.queue_limit,
        "runner_capacity":e.runner_capacity_percent <= e.runner_capacity_limit_percent,
        "state_backend":e.state_backend_healthy,
        "state_restore":e.state_restore_tested,
        "policy":e.policy_engine_healthy,
        "gitops":e.gitops_reconciliation_healthy,
        "audit":e.audit_events_complete,
        "incident_runbook":e.incident_runbook_tested,
        "sre_signoff":e.sre_approved,
        "dbre_signoff":not e.manages_databases or e.dbre_approved,
    }
    failed=[k for k,v in checks.items() if not v]
    return {"decision":"REVIEW_READY" if not failed else "NO_GO",
            "availability_percent":round(availability,4),
            "error_budget_remaining_requests":round(allowed_failures-observed_failures,4),
            "failed":failed}
