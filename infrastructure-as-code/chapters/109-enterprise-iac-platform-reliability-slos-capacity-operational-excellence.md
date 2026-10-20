# Chapter 109 — Enterprise IaC Platform Reliability, SLOs, Capacity and Operational Excellence

**Part 22 — Enterprise Platforms · Chapter 109/120 · Enterprise SRE/DBRE**

> **Verification boundary:** The included Python evaluator uses synthetic SLI inputs. It neither queries Prometheus nor deploys infrastructure. Authored tests, live recovery, operational acceptance and production SLO evidence must be independently verified.

## 1. Objectives and prerequisites
Operate an enterprise IaC platform as a production service, with measurable reliability across self-service portals, service catalogs, Terraform/OpenTofu plan/apply pipelines, state backends, policy-as-code, GitOps reconciliation, Kubernetes clusters and DBRE provisioning. Define SLIs/SLOs, error budgets, capacity forecasts, toil reduction, incident management, disaster recovery and operational acceptance.

Prerequisites: Chapters 106–108, Prometheus/OpenTelemetry, Kubernetes, GitOps, Terraform/OpenTofu state, incident command, SRE SLOs, DBRE backup and recovery.

## 2. Reliability architecture
```text
Developer portal / service catalog / API
                   |
        OIDC + RBAC + policy gate
                   |
   CI queue + runners + plan/apply engine
                   |
    State backend + secrets + cloud APIs
                   |
    Kubernetes/GitOps + database services
                   |
 Metrics + logs + traces + synthetic probes
                   |
  SLOs + error budgets + capacity forecasts
                   |
 Alert routing + on-call + incident command
                   |
 Recovery tests + postmortems + improvements
```

The platform is a dependency of delivery pipelines and recovery operations. A broken state backend or policy engine can block incident remediation even when existing applications continue serving traffic. Track **platform availability** separately from **application availability**.

## 3. Service-level indicators and objectives

| User journey | SLI | Illustrative SLO |
|---|---|---|
| Catalog discovery | successful catalog responses / valid requests | 99.9% / 30 days |
| Template generation | successful template runs / valid requests | 99.5% / 30 days |
| Plan pipeline | valid plans completing within 10 min | 99% / 30 days |
| Apply pipeline | approved applies succeeding without platform error | 99% / 30 days |
| State backend | successful state operations / valid operations | 99.99% / 30 days |
| Policy service | valid policy decisions within 2 sec | 99.9% / 30 days |
| GitOps | desired-state convergence within 10 min | 99% / 30 days |
| DBRE provisioning | requests provisioned and verified within tier target | tier-specific |

All targets are examples requiring business approval and baselines. Exclude user-invalid requests from platform error rate, but **do not** silently exclude policy engine outages, runner starvation, state errors or missing audit records.

### Error budget
For an availability objective S and N valid requests, the allowable failure count is N × (1 − S). Track consumed budget, burn rate, remaining budget and windows. A depleted error budget should trigger a documented change-risk review; do not disable emergency security or recovery fixes.

## 4. Observability implementation

Instrument the platform with OpenTelemetry traces linking request ID, PR ID, plan hash, CI run, policy decision, state operation and GitOps sync. Prometheus-style metrics should include request totals and failures, histograms for plan/apply duration, queue depth, runner utilization, policy decision latency, state lock wait time, GitOps convergence lag, and database restore validation age.

**Illustrative PromQL** (adapt label names and counters to actual instrumentation):

```promql
sum(rate(platform_requests_total{outcome="success"}[5m]))
/
clamp_min(sum(rate(platform_requests_total{valid="true"}[5m])), 1)
```

```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(platform_provision_duration_seconds_bucket[5m]))
)
```

Do not confuse request-rate success with an exact rolling-window compliance score; calculate reporting-window SLO compliance from full-window counters and verify missing-data handling.

## 5. Capacity and performance engineering
- Forecast plan/apply arrivals, concurrency, runner slots, queue wait, API throttling and state backend throughput.
- Segment workload by environment, tenant, region, template and database complexity.
- Reserve incident-response capacity and avoid letting bulk developer requests starve emergency recovery.
- Use autoscaling runners with concurrency limits, budget controls, ephemeral credentials and cleanup.
- Rate-limit expensive cloud APIs and provider retries with jitter; avoid thundering herds.
- Capacity-test control-plane dependencies including identity provider, artifact registry, policy service, backend locks and GitOps controllers.
- Model N-1 resilience and regional failover capacity; reserve DBRE recovery IOPS and network bandwidth.

## 6. Reliability guardrails and change safety
Require pinned modules/providers, reviewed plans, policy pass, cost estimation, scoped credentials, immutable audit events and state locking. For critical changes use staged rollouts, maintenance windows, canary deployments, SLO gates, abort conditions and rollback. Never bypass security policy or DBRE recovery requirements solely to improve deployment success metrics.

## 7. Lab A — Offline platform reliability evaluator

Create `infrastructure-as-code/labs/chapter-109/reliability_gate.py`:

```python
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
```

`REVIEW_READY` is only a synthetic assessment of supplied evidence. It does not certify a live platform.

## 8. Lab B — Automated negative tests

Create `infrastructure-as-code/labs/chapter-109/test_reliability_gate.py`:

```python
import unittest
from dataclasses import replace
from reliability_gate import ReliabilityEvidence, assess

class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.e=ReliabilityEvidence("iac-platform",30,100000,99980,99.9,
            90,120,12,100,55,80,True,True,True,True,True,True,True,True,True)
    def test_valid(self):
        self.assertEqual(assess(self.e)["decision"],"REVIEW_READY")
    def test_slo_breach(self):
        self.assertIn("availability",assess(replace(self.e,requests_successful=99000))["failed"])
    def test_latency_breach(self):
        self.assertIn("provision_latency",assess(replace(self.e,p95_provision_seconds=150))["failed"])
    def test_queue_and_capacity(self):
        self.assertEqual(assess(replace(self.e,queue_depth=101,runner_capacity_percent=90))["decision"],"NO_GO")
    def test_critical_controls(self):
        for f in ("state_backend_healthy","state_restore_tested","policy_engine_healthy",
                  "gitops_reconciliation_healthy","audit_events_complete",
                  "incident_runbook_tested","sre_approved","dbre_approved"):
            with self.subTest(field=f):
                self.assertEqual(assess(replace(self.e,**{f:False}))["decision"],"NO_GO")
    def test_no_database_requires_no_dbre_signoff(self):
        self.assertEqual(assess(replace(self.e,manages_databases=False,dbre_approved=False))["decision"],"REVIEW_READY")
    def test_invalid_counters(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,requests_successful=100001))
    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,window_days=0))
if __name__=="__main__":
    unittest.main()
```

Run from repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-109 -p 'test_*.py' -v
```

## 9. Lab C — Platform SLO and capacity dashboard (manual)
1. Deploy a disposable staging portal and CI workflow with synthetic service requests.
2. Instrument request success, duration, queue depth, runner utilization, state backend latency and policy decisions.
3. Generate controlled low-volume synthetic requests and record baselines; avoid production load.
4. Define recording rules, 30-day SLO dashboards and multiwindow burn-rate alerts.
5. Test a staging policy engine outage and verify fail-closed behavior with a visible alert.
6. Saturate staging runners within approved limits; measure queue wait and safe shedding.
7. Recover the service, measure detection/mitigation time and validate audit continuity.
8. Archive dashboards, traces, alerts, incident timeline and corrective actions.

## 10. Lab D — DBRE and IaC state recovery rehearsal (manual)
1. Establish a disposable staging Terraform/OpenTofu backend with versioning, encryption and locking.
2. Capture an approved snapshot and restore into a separate isolated backend; verify plan consistency.
3. Exercise a controlled runner outage and validate resumability without duplicate applies.
4. Provision a synthetic database via an approved module; verify credentials, backup and restore.
5. Simulate database provisioning failure; confirm the portal reports an actionable error without leaking secrets.
6. Validate database integrity, PITR coverage, recovery objective evidence and DBRE approval.
7. Record RTO/RPO, recovery logs and rollback outcomes; retain only sanitized evidence.

## 11. Troubleshooting scenarios

| Failure | Signal | Safe response |
|---|---|---|
| Portal unavailable | synthetic probe | fail over or restore |
| Catalog stale | metadata age | reconcile owners |
| OIDC outage | authentication errors | incident escalation |
| Policy service timeout | missing decision | fail closed |
| CI runner saturation | queue depth | scale within limits |
| Queue starvation | wait histogram | reserve priority capacity |
| Cloud API throttling | 429 events | backoff and jitter |
| State backend unavailable | backend errors | recover isolated backend |
| State lock contention | lock wait | identify owner |
| Corrupt state snapshot | checksum mismatch | use verified version |
| Plan/apply mismatch | hash mismatch | stop apply |
| Provider regression | error spike | roll back pinned version |
| GitOps reconciliation stalled | sync age | investigate controller |
| Kubernetes admission failure | deny events | correct policy |
| Secret store outage | auth/decrypt errors | invoke recovery runbook |
| Database provisioning stuck | workflow timeout | DBRE escalation |
| Backup freshness breached | missing recovery point | block acceptance |
| SLO telemetry absent | scrape gaps | restore instrumentation |
| Error budget exhausted | burn alert | review change risk |
| Audit events missing | evidence gap | halt privileged workflow |

## 12. Production runbooks

**RB-01 Platform incident command:** classify impact, appoint commander, communicate and preserve evidence.

**RB-02 Portal recovery:** validate SSO, catalog DB, ingress, dependencies and failover.

**RB-03 CI runner outage:** inspect capacity, job queues, identity and retry idempotency.

**RB-04 State backend incident:** preserve locks, validate snapshots, restore isolated state and review plans.

**RB-05 Policy service outage:** deny privileged operations until authoritative policy decisions recover.

**RB-06 GitOps recovery:** inspect controllers, projects, permissions, sync status and desired-state drift.

**RB-07 Capacity saturation:** throttle noncritical workloads, protect recovery capacity and scale safely.

**RB-08 DBRE provisioning incident:** validate backup, PITR, credentials, data integrity and service SLO.

**RB-09 Error budget breach:** assess customer impact, pause risky changes and document exceptions.

**RB-10 Operational review:** score controls, archive SLO evidence, assign remediation owners and repeat drill.

## 13. Enterprise acceptance assessment (100 points)

| Domain | Points |
|---|---:|
| Service catalog and platform ownership | 10 |
| SLI/SLO definitions and accurate measurement | 15 |
| Error budget policy and alerting | 10 |
| Capacity forecasting and runner resilience | 15 |
| IaC state availability and restore | 15 |
| Policy and identity service reliability | 10 |
| GitOps and Kubernetes recovery | 10 |
| DBRE provisioning and backup validation | 5 |
| Incident response, rollback and audit | 10 |
| **Total** | **100** |

**Acceptance:** 90+ points and mandatory proof of representative SLO measurement, state restore, policy fail-closed behavior, incident recovery, complete audit trail, and DBRE restore evidence for managed databases. Missing mandatory evidence means **NO-GO**, regardless of score.

## 14. Cleanup and next chapter
Remove only approved staging resources, preserve SLO baselines, runbooks, test reports and audit evidence. Publication of this chapter is not production acceptance.

**Next:** Chapter 110 — Enterprise IaC Platform Engineering, Governance and Reliability Acceptance Capstone.
