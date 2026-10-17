# Chapter 092 — Jenkins SLOs, Error Budgets and Enterprise Reliability Governance

**Part 19 — Enterprise Jenkins SRE Operations and FinOps**  
**Audience:** Jenkins SRE/DBRE, DevOps, service owners, incident commanders, platform governance.  
**Prerequisites:** Chapter 091, Prometheus/Grafana concepts, Python 3, Git, optional Jenkins staging controller.

## Learning outcomes

Define user-centered Jenkins service-level indicators, calculate availability and latency SLOs, build burn-rate alerting, distinguish platform failures from pipeline failures, govern error-budget consumption, connect policy to change control, and validate calculations with executable tests.

## 1. Reliability architecture

```text
Synthetic probes + Jenkins telemetry + CI job events
                       |
             SLI aggregation / labels
                       |
             30-day SLO + error budget
                       |
          burn-rate alerts and dashboards
                       |
     incident response / change governance
                       |
     owner review / RCA / COA / capacity plan
```

Do not use controller process uptime as the sole indicator of user experience. Jenkins may be healthy while agents cannot start, queues grow indefinitely or critical SCM integrations fail.

## 2. SLI contracts

| SLI | Good events | Eligible events | Exclusions / caveats |
|---|---|---|---|
| Controller availability | successful authenticated synthetic API transactions | scheduled synthetic transactions | documented, approved exclusions only |
| Critical job scheduling | critical jobs begin within 120 seconds | eligible runnable critical jobs | exclude user-paused jobs using explicit classification |
| Agent provisioning | agents connect within 180 seconds | valid provisioning attempts | differentiate quota and bad image |
| CI infrastructure reliability | jobs not failed by platform | eligible job executions | exclude application tests only with defensible classification |
| Backup recovery readiness | validated restore meeting RTO/RPO | scheduled DR drills | not an availability SLI by itself |

Define measurement source, unit, labels, eligibility, sampling cadence, ownership, retention and failure attribution. Avoid per-job labels with unbounded cardinality.

## 3. SLO mathematics

For event-based availability:

```text
SLI = good_events / eligible_events
Error budget events = floor(eligible_events × (1 - SLO))
Consumed errors = eligible_events - good_events
Remaining budget = max(0, budget events - consumed errors)
```

For a time-based 30-day window:

```text
total minutes = 30 × 24 × 60 = 43,200
99.9% budget = 43.2 minutes
99.95% budget = 21.6 minutes
99.99% budget = 4.32 minutes
```

Time-based and event-based budgets are **not interchangeable** when traffic is uneven. Choose one contract and keep its denominator stable.

## 4. Burn rate

```text
observed error fraction = bad / eligible
burn rate = observed error fraction / (1 - target SLO)
```

Example: 99.9% SLO, 2% observed errors => burn rate 20×. Multi-window burn alerts compare a fast window and a slower confirmation window to reduce noise.

Suggested starting patterns for a 30-day SLO (tune with real traffic and incident data):
- Page: 14.4× burn sustained across 5m and 1h.
- Page: 6× burn sustained across 30m and 6h.
- Ticket: 3× burn across 1h and 1d.
- Ticket: 1× burn across 3d.

These are policy examples, not guarantees. Ensure sufficient event volume and guard against division by zero.

## 5. Prometheus reference instrumentation

Proposed custom metric contracts:

```text
jenkins_sli_requests_total{service="jenkins",sli="api",result="good|bad"}
jenkins_sli_jobs_total{service="jenkins",tier="critical",result="good|bad"}
jenkins_queue_wait_seconds_bucket{service="jenkins",tier="critical",le="..."}
```

These are **not guaranteed standard Jenkins exporter metrics**; instrument and verify them before using PromQL.

API bad-event fraction over 5 minutes:

```promql
sum(rate(jenkins_sli_requests_total{sli="api",result="bad"}[5m]))
/
clamp_min(sum(rate(jenkins_sli_requests_total{sli="api"}[5m])), 1e-9)
```

14.4× burn threshold for 99.9% target:

```promql
(
  sum(rate(jenkins_sli_requests_total{sli="api",result="bad"}[5m]))
  /
  clamp_min(sum(rate(jenkins_sli_requests_total{sli="api"}[5m])), 1e-9)
) > (14.4 * 0.001)
```

Require the corresponding 1h condition for the multi-window alert. Validate metrics exist, eligible event counts are adequate and zero-traffic handling is explicit.

## 6. Recording rules and alert design

```yaml
groups:
  - name: jenkins-slo
    rules:
      - record: jenkins:api_bad_fraction:rate5m
        expr: |
          sum(rate(jenkins_sli_requests_total{sli="api",result="bad"}[5m]))
          /
          clamp_min(sum(rate(jenkins_sli_requests_total{sli="api"}[5m])), 1e-9)
      - alert: JenkinsAPIHighBurn
        expr: |
          (
            jenkins:api_bad_fraction:rate5m > 0.0144
          )
          and
          (
            (
              sum(rate(jenkins_sli_requests_total{sli="api",result="bad"}[1h]))
              /
              clamp_min(sum(rate(jenkins_sli_requests_total{sli="api"}[1h])), 1e-9)
            ) > 0.0144
          )
        for: 2m
        labels:
          severity: page
        annotations:
          summary: "Jenkins API availability error budget burning rapidly"
          runbook_url: "https://INTERNAL-RUNBOOK-URL"
```

Replace the runbook placeholder with an approved internal URL. The rules are illustrative and require metric instrumentation, promtool validation, test vectors and production tuning.

## 7. Error-budget governance

| Remaining budget | Action |
|---|---|
| > 50% | normal reviewed delivery |
| 25–50% | increased reliability review |
| 0–25% | restrict discretionary high-risk changes |
| exhausted | pause discretionary changes, prioritize reliability work |

Urgent security fixes and incident mitigation may proceed through emergency change control with documented risk acceptance. Budget exhaustion should drive investment and corrective action, not punitive blame.

## 8. SLO reporting cadence

- Daily: burn-rate and critical queue dashboard, alert hygiene.
- Weekly: SLO trend, incidents, high-risk changes, agent capacity.
- Monthly: error budget reconciliation, reliability investment and roadmap.
- Quarterly: SLI contract review, SLO target negotiation and disaster recovery drill.

## 9. Executable offline SLO calculator

Save `scripts/slo_calculator.py`:

```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

def calculate(good, total, target):
    if not isinstance(good, int) or isinstance(good, bool):
        raise ValueError("good must be integer")
    if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
        raise ValueError("total must be positive integer")
    if good < 0 or good > total:
        raise ValueError("good must be between zero and total")
    if not isinstance(target, (int, float)) or isinstance(target, bool) or not 0 < target < 1:
        raise ValueError("target must be strictly between zero and one")
    bad = total - good
    allowed = int(total * (1 - target) + 1e-9)
    remaining = max(0, allowed - bad)
    return {
        "sli": round(good / total, 8),
        "bad_events": bad,
        "allowed_bad_events": allowed,
        "remaining_bad_events": remaining,
        "burn_rate": round((bad / total) / (1 - target), 4),
        "slo_met": good / total >= target,
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--good", type=int, required=True)
    p.add_argument("--total", type=int, required=True)
    p.add_argument("--target", type=float, default=0.999)
    args = p.parse_args()
    print(json.dumps(calculate(args.good, args.total, args.target), indent=2))
```

```bash
python3 scripts/slo_calculator.py --good 99950 --total 100000 --target 0.999
```

Expected: 50 bad events, 100 allowed, 50 remaining, 0.5× burn rate and SLO met.

## 10. Automated tests

Save `tests/test_slo.py` (adjust import path to repository layout):

```python
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from slo_calculator import calculate

class SLOTests(unittest.TestCase):
    def test_healthy(self):
        result = calculate(99950, 100000, 0.999)
        self.assertEqual(result["bad_events"], 50)
        self.assertEqual(result["allowed_bad_events"], 100)
        self.assertTrue(result["slo_met"])

    def test_burn(self):
        self.assertEqual(calculate(98000, 100000, 0.999)["burn_rate"], 20.0)

    def test_invalid(self):
        for good, total in ((101, 100), (0, 0), (-1, 100)):
            with self.assertRaises(ValueError):
                calculate(good, total, 0.999)

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest discover -s tests -v
```

## 11. Twenty troubleshooting scenarios

| # | Symptom | Investigation |
|---|---|---|
| 01 | SLI reports 100% with zero traffic | denominator |
| 02 | Controller healthy but jobs stuck | queue SLI |
| 03 | Test failures inflate platform errors | attribution |
| 04 | Missing agent metric | exporter |
| 05 | Excessive metric labels | cardinality |
| 06 | Synthetic probe unauthenticated | test validity |
| 07 | SLO window mismatched | range |
| 08 | Burn alert too noisy | multi-window |
| 09 | Burn alert never fires | rule expression |
| 10 | Prometheus target down | scrape |
| 11 | Counter reset causes spikes | rate |
| 12 | Alert without runbook | routing |
| 13 | Error budget overdrawn | event math |
| 14 | Planned downtime excluded silently | governance |
| 15 | DR success misread as uptime | SLI contract |
| 16 | Queue p95 misses critical tier | segmentation |
| 17 | Owner disputes failed event | classification |
| 18 | Budget freeze blocks security fix | exception |
| 19 | Missing historical telemetry | retention |
| 20 | SLO met but users complain | revise SLI |

## 12. Six production runbooks

### A. Rapid error-budget burn
Validate probe and eligible events, declare severity, isolate controller/agent/SCM bottleneck, mitigate and track consumption.

### B. Queue latency SLO breach
Inspect executor capacity, agent provisioning, node pressure, throttling and build demand; scale only within budget and quotas.

### C. SLI instrumentation failure
Confirm exporter, label schema, scraping, missing data and counter semantics; flag data quality and avoid false healthy claims.

### D. Error budget exhausted
Review incidents and trend, restrict discretionary changes, prioritize reliability work and document emergency exceptions.

### E. False-positive burn alert
Reproduce queries, inspect low-traffic windows, label filters and rule tests, tune thresholds and verify no missed incidents.

### F. Reliability governance dispute
Review SLI contract, data, impact, exclusions and service-owner approvals; record decision and update policy transparently.

## 13. 100-point acceptance

| Domain | Points |
|---|---:|
| SLI contract and attribution | 20 |
| SLO and error-budget math | 20 |
| Burn alerts and telemetry validation | 20 |
| Incident and change governance | 15 |
| Reliability review and capacity | 15 |
| Tests, evidence and runbooks | 10 |
| **Total** | **100** |

Suggested pass 85/100 plus mandatory gates: valid SLI denominator, correct failure attribution, reproducible budget calculation, actionable alert route, approved budget policy and owner sign-off.

## 14. Evidence template

```text
UTC / service tier / owner:
SLI contracts and eligible events:
SLO target and window:
Event counts and remaining budget:
Burn-rate alerts and promtool tests:
Platform vs pipeline failure attribution:
Incident and change governance:
Capacity/queue/agent review:
Automated tests:
20 scenarios / six runbooks:
Score / RCA / COA / reviewer:
```

**Companion:** [Chapter 092 hands-on lab](labs/092-jenkins-slos-error-budgets-enterprise-reliability-governance-check.md).  
**Next:** Chapter 093 — Jenkins Enterprise Capacity Planning, Cost Allocation and FinOps Optimization.
