# Chapter 113 — Enterprise IaC Predictive Operations, Drift Intelligence and AI-Assisted Change Risk Analysis

**Part 23 — Advanced Automation · Chapter 113/120 · Enterprise SRE/DBRE**

> **Verification boundary:** The Python lab is a deterministic offline illustration, not a calibrated predictive model. Its risk score and thresholds are illustrative, not statistically validated. It cannot authenticate users, fetch live telemetry, detect real drift or authorize cloud changes. Live validation and independent acceptance remain pending.

## 1. Learning objectives
Build a proactive IaC reliability program covering drift intelligence, risk forecasting, change impact, capacity prediction, AI-assisted triage, approval workflows, safe automation and SRE/DBRE operational controls. Distinguish observed evidence from predictions and recommendations.

**Prerequisites:** Chapters 106–112, Terraform/OpenTofu state and plans, Kubernetes/GitOps, Prometheus/OpenTelemetry, cloud audit, FinOps, DBRE capacity and incident management.

## 2. Reference architecture
```text
IaC plans + state snapshots + Git diffs + cloud audit
                            |
Kubernetes/GitOps health + metrics + DBRE telemetry
                            |
       Normalize, correlate, timestamp and label
                            |
      Drift inventory + capacity trend forecasting
                            |
     Rule-based risk score + optional AI explanation
                            |
     Evidence freshness + deterministic policy gate
                            |
     Human SRE/DBRE/security approval as required
                            |
      Staged deployment + SLO/rollback validation
                            |
         Audit + outcomes + model evaluation
```

AI-generated risk explanations are untrusted advisory content. Never allow an LLM to issue a privileged Terraform/OpenTofu apply, destroy, state force-unlock, Kubernetes cluster mutation or database failover.

## 3. Drift intelligence taxonomy

| Drift category | Example | Operational response |
|---|---|---|
| Authorized emergency change | incident hotfix outside Git | reconcile through reviewed PR |
| Unauthorized manual change | console IAM permission edit | investigate security impact |
| Provider-generated change | default/tag normalization | validate provider semantics |
| Runtime controller change | Kubernetes HPA replicas | ignore intentionally controller-owned fields |
| Security drift | public ingress or weakened encryption | halt unsafe rollout |
| Data-platform drift | database parameter/retention change | DBRE review |
| State divergence | resource/state identity mismatch | preserve and reconcile state |
| Policy drift | admission or org-policy version mismatch | security review |

Run read-only plans using protected credentials and backend locks. Do not automatically apply drift corrections to production. Some drift is expected and should be explicitly modeled rather than suppressed.

## 4. Predictive operations and capacity
Forecast CPU, memory, storage, IOPS, network, CI runner queue depth, cloud API quotas, Terraform backend throughput and database growth. Begin with robust historical baselines and seasonality-aware forecasts before introducing ML. Record training windows, missing-data handling, forecast intervals, error metrics, concept drift and prediction provenance.

**Capacity guardrail:** compare predicted demand plus failover headroom with safe capacity, not just average utilization. For DBRE, forecast storage and transaction growth, replication lag, backup windows, PITR retention, restore bandwidth and read/write workload shifts.

## 5. Change risk factors
Score change size, destructive actions, IAM privilege modifications, blast radius, data sensitivity, deployment tier, maintenance window, dependency health, SLO error budget, rollback quality, state lock, plan integrity and observability freshness. Calibrate thresholds against historical incidents and false-positive/false-negative rates; do not present arbitrary heuristic scores as reliable probabilities.

A high score should trigger human review, smaller rollout or deeper tests—not autonomous execution. A low score never overrides missing mandatory security or DBRE evidence.

## 6. AI-assisted operations safety
- Use AI for summarizing sanitized diffs, grouping incidents, proposing tests and explaining observed metrics.
- Treat plans, logs, alerts and repository comments as untrusted inputs vulnerable to prompt injection.
- Redact secrets, credentials, customer data and protected resource identifiers.
- Ground recommendations in traceable plan hashes, metrics and runbooks.
- Use deterministic allowlists and policy-as-code for every execution decision.
- Measure recommendation accuracy, unsafe suggestion rate, reviewer disagreement and post-change outcomes.
- Keep a human accountable for production IAM, networking, state recovery and database-impacting changes.

## 7. Cross-cloud and platform implementation
**AWS:** AWS Config/CloudTrail, CloudWatch, Organizations controls and scoped plan roles.

**Azure:** Azure Policy/Activity Logs, Azure Monitor, RBAC and managed identities.

**GCP:** Cloud Asset Inventory/Audit Logs, Cloud Monitoring, organization policies and workload identity federation.

**Terraform/OpenTofu:** scheduled read-only plans, state encryption/locking, signed artifacts, module pinning, policy scans and reviewed reconciliation.

**Kubernetes/GitOps:** compare desired Git state against live resources, distinguish controller-managed fields, use admission policy and measure reconciliation SLO.

**DBRE:** monitor PostgreSQL/MongoDB/Redis/Kafka/Elasticsearch performance, capacity, data durability and restore readiness. Require database-specific recovery and data-integrity evidence.

## 8. Lab A — Offline change-risk evaluator

Create `infrastructure-as-code/labs/chapter-113/risk_gate.py`:

```python
"""Offline IaC change-risk assessment. No model inference or infrastructure changes."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ChangeEvidence:
    change_id:str
    tenant:str
    authorized_tenant:str
    environment:str
    drift_resources:int
    destructive_changes:int
    privileged_changes:int
    estimated_capacity_utilization_pct:float
    projected_capacity_utilization_pct:float
    telemetry_fresh:bool
    drift_plan_reviewed:bool
    policy_passed:bool
    plan_hash_approved:bool
    audit_available:bool
    rollback_tested:bool
    security_approved:bool
    sre_approved:bool
    dbre_approved:bool
    database_affected:bool

def assess(e:ChangeEvidence):
    if not e.change_id.strip() or not e.tenant.strip():
        raise ValueError("change and tenant required")
    if any(v<0 for v in (e.drift_resources,e.destructive_changes,e.privileged_changes)):
        raise ValueError("change counts cannot be negative")
    if not all(0<=v<=100 for v in (e.estimated_capacity_utilization_pct,
                                  e.projected_capacity_utilization_pct)):
        raise ValueError("capacity percentage outside 0..100")
    score=min(100, e.drift_resources*3+e.destructive_changes*25+
              e.privileged_changes*20+
              max(0,e.projected_capacity_utilization_pct-75)*2)
    checks={
        "tenant_scope":e.tenant==e.authorized_tenant,
        "environment":e.environment in {"dev","stage","prod"},
        "telemetry":e.telemetry_fresh,
        "plan_review":e.drift_plan_reviewed,
        "policy":e.policy_passed,
        "plan_binding":e.plan_hash_approved,
        "audit":e.audit_available,
        "rollback":e.rollback_tested,
        "capacity":e.projected_capacity_utilization_pct<=85,
        "destructive_change":e.destructive_changes==0,
        "privileged_change":e.privileged_changes==0,
        "security_signoff":e.environment!="prod" or e.security_approved,
        "sre_signoff":e.environment!="prod" or e.sre_approved,
        "dbre_signoff":not e.database_affected or e.dbre_approved,
        "risk_threshold":score<=25,
    }
    failed=[name for name,ok in checks.items() if not ok]
    return {"decision":"REVIEW_READY" if not failed else "NO_GO",
            "risk_score":score,"failed_controls":failed}
```

The `REVIEW_READY` result only means supplied synthetic evidence meets this illustrative policy; it is not authorization to deploy.

## 9. Lab B — Negative tests

Create `infrastructure-as-code/labs/chapter-113/test_risk_gate.py`:

```python
import unittest
from dataclasses import replace
from risk_gate import ChangeEvidence,assess

class RiskGateTests(unittest.TestCase):
    def setUp(self):
        self.e=ChangeEvidence("CHG-113","team-a","team-a","prod",2,0,0,
            55,65,True,True,True,True,True,True,True,True,True,True)
    def test_baseline(self):
        self.assertEqual(assess(self.e)["decision"],"REVIEW_READY")
    def test_tenant_isolation(self):
        self.assertIn("tenant_scope",assess(replace(self.e,authorized_tenant="team-b"))["failed_controls"])
    def test_destructive_change(self):
        self.assertIn("destructive_change",assess(replace(self.e,destructive_changes=1))["failed_controls"])
    def test_privileged_change(self):
        self.assertIn("privileged_change",assess(replace(self.e,privileged_changes=1))["failed_controls"])
    def test_capacity(self):
        self.assertIn("capacity",assess(replace(self.e,projected_capacity_utilization_pct=90))["failed_controls"])
    def test_fail_closed_controls(self):
        for field in ("telemetry_fresh","drift_plan_reviewed","policy_passed",
                      "plan_hash_approved","audit_available","rollback_tested",
                      "security_approved","sre_approved","dbre_approved"):
            with self.subTest(field=field):
                self.assertEqual(assess(replace(self.e,**{field:False}))["decision"],"NO_GO")
    def test_invalid_count(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,drift_resources=-1))
    def test_invalid_utilization(self):
        with self.assertRaises(ValueError):
            assess(replace(self.e,projected_capacity_utilization_pct=101))
if __name__=="__main__":
    unittest.main()
```

Run from the repository root:

```bash
python -m unittest discover -s infrastructure-as-code/labs/chapter-113 -p 'test_*.py' -v
```

## 10. Lab C — Drift detection and change-risk workflow (manual)
1. Provision disposable staging IaC resources using a protected, versioned backend.
2. Establish read-only drift detection and capture an approved baseline plan.
3. Introduce one controlled, non-sensitive staging drift and record cloud audit evidence.
4. Compare Git desired state, Terraform/OpenTofu plan and actual resource state.
5. Classify drift as expected, authorized emergency, security-sensitive or unexplained.
6. Collect CI, Kubernetes, cost and SLO telemetry with timestamps and provenance.
7. Produce a heuristic risk score; compare with a human reviewer assessment.
8. Test a proposed privileged change and verify deterministic policy denies automation.
9. Restore staging state through a reviewed plan and verify SLO/rollback.
10. Preserve sanitized evidence and destroy only approved disposable resources.

## 11. Lab D — Capacity forecasting and DBRE safeguards (manual)
1. Generate synthetic staging CPU, memory, disk and runner queue metrics.
2. Compute historical baseline and a simple forecast; document forecast error.
3. Simulate a projected capacity threshold breach and test alerting.
4. Model database storage growth, replication lag, PITR retention and recovery headroom.
5. Request a synthetic database parameter change; verify DBRE approval is required.
6. Demonstrate that a low heuristic score cannot bypass missing backup or recovery evidence.
7. Record false-positive and false-negative examples and reviewer feedback.
8. Validate that no AI suggestion can directly execute database failover or state mutation.

## 12. Troubleshooting scenarios

| Failure | Evidence | Safe response |
|---|---|---|
| False-positive drift | controller-owned field | refine ignore rules |
| False-negative drift | missing resource | audit scope |
| Stale plan | old plan timestamp | regenerate |
| Wrong tenant scope | access mismatch | deny |
| Backend state lock | lock event | inspect owner |
| Unreviewed console change | cloud audit | security review |
| Provider schema change | version diff | pin and test |
| Missing metric series | scrape gaps | restore telemetry |
| Forecast seasonality error | residual pattern | retrain baseline |
| Capacity spike | queue/utilization | preserve headroom |
| Risk score uncalibrated | no outcomes | human review |
| AI invents resource | unsupported ID | reject |
| Prompt injection in logs | adversarial text | ignore instructions |
| Sensitive plan leaked | data exposure | revoke/rotate |
| Plan hash mismatch | artifact check | reapprove |
| SLO error budget depleted | burn alert | review rollout |
| GitOps reconciliation loop | sync events | fix Git source |
| IAM privilege expansion | policy diff | block |
| Database PITR gap | backup audit | DBRE NO-GO |
| Rollback fails | recovery drill | incident command |

## 13. Production runbooks

**RB-01 Drift triage:** preserve read-only plan, state version and cloud audit trail.

**RB-02 Security drift:** halt deployment, assess exposure and escalate to security.

**RB-03 Forecast anomaly:** verify telemetry, seasonality, quotas and capacity headroom.

**RB-04 Risk score disagreement:** document evidence, reviewer decision and model limitation.

**RB-05 AI unsafe recommendation:** quarantine output, block execution and review controls.

**RB-06 State divergence:** preserve locks and snapshots; reconcile via approved plan.

**RB-07 Kubernetes/GitOps drift:** compare controller ownership and Git desired state.

**RB-08 DBRE capacity incident:** assess storage/IOPS, replication, backups and data correctness.

**RB-09 Failed change rollback:** stop further automation, recover and validate service transactions.

**RB-10 Predictive operations review:** evaluate drift coverage, prediction errors, incidents and false alarms.

## 14. Enterprise acceptance (100 points)

| Domain | Points |
|---|---:|
| Drift coverage and classification | 15 |
| Evidence freshness and provenance | 10 |
| Capacity forecast and validation | 15 |
| Deterministic policy and plan binding | 15 |
| Tenant isolation and least privilege | 10 |
| AI safety and recommendation evaluation | 10 |
| SLO/rollback and incident response | 10 |
| DBRE capacity, backup and recovery | 10 |
| Audit and ownership | 5 |
| **Total** | **100** |

**Acceptance:** at least 90/100 and mandatory live proof of tenant isolation, policy fail-closed, fresh plan and telemetry, reviewed production changes, tested rollback, accurate audit and DBRE approval where data is affected. Any mandatory failure yields **NO-GO**.

## 15. Cleanup and next chapter
Preserve sanitized plans, forecast error reports, approval records, SLO evidence and review outcomes. Avoid treating heuristic or AI-derived scores as production safety certification.

**Next:** Chapter 114 — Enterprise IaC Automation Safety, Guardrails, Human-in-the-Loop and Governance.
