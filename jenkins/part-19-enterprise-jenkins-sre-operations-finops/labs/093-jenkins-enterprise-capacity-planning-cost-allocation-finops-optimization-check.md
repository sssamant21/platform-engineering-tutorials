# Chapter 093 — Hands-on Lab: Jenkins Enterprise Capacity and FinOps

**Safety:** Offline Python cost modeling, optional read-only cloud/Jenkins metrics. No production rightsizing or deletion.

## 20 hands-on exercises

| # | Exercise | Evidence |
|---|---|---|
| 01 | Define Jenkins service tier and SLO | Contract |
| 02 | Inventory controller and agent pools | Diagram |
| 03 | Segment jobs by workload | Catalog |
| 04 | Record arrival rate and runtime | Data |
| 05 | Calculate average concurrency | Formula |
| 06 | Calculate executor headroom | Result |
| 07 | Record CPU/memory requests | Matrix |
| 08 | Review queue p95 and bursts | Baseline |
| 09 | Model controller cost | Worksheet |
| 10 | Model agent cost | CSV |
| 11 | Model storage/artifacts/egress | Worksheet |
| 12 | Define cost-center allocation | Policy |
| 13 | Run Python calculator | Output |
| 14 | Run automated unit tests | Result |
| 15 | Simulate +25% workload | Forecast |
| 16 | Simulate +50% workload | Forecast |
| 17 | Evaluate ephemeral/spot agent tradeoffs | Risk |
| 18 | Review DR/security constraints | Gate |
| 19 | Simulate rightsizing rollback | Runbook |
| 20 | Score 100-point acceptance and COA | Sign-off |

## 12 failure drills

1. Missing cost-center tags.
2. Duplicate billing rows.
3. Negative job count.
4. Invalid runtime.
5. Invalid hourly rate.
6. Overestimated utilization.
7. Burst demand beyond forecast.
8. Spot interruption storm.
9. CPU throttling after rightsizing.
10. Queue SLO regression.
11. Artifact storage growth.
12. Billing reconciliation gap.

## Executable calculator

Use `scripts/capacity_finops.py` and `data/build_usage.csv` from the chapter.

```bash
python3 scripts/capacity_finops.py data/build_usage.csv --jobs-per-minute 2 --utilization 0.70
python3 -m unittest discover -s tests -v
```

Expected modeled agent cost: payments $19.20, analytics $18.00, platform $2.00, total $39.20. Costs are synthetic and exclude idle, shared and storage overhead.

## Capacity scenario drill

For 10 jobs/minute and 6 minutes mean runtime:

```python
import math
for util in (0.5, 0.7, 0.8):
    print(util, math.ceil(10 * 6 / util))
```

Expected executor estimates: 120, 86 and 75. These are initial average-load estimates, not proof of p95 queue SLO compliance.

## Evidence worksheet

```text
UTC / lab owner:
Workload classes and job demand:
Controller/agent utilization:
Cost data and allocation:
Baseline and peak executor estimate:
Storage/network/shared overhead:
Python calculator and tests:
SLO and DR guardrails:
12 failure drills:
Score / RCA / COA / reviewer:
```

## Acceptance

- [ ] 20 exercises attempted with evidence.
- [ ] 12 failure drills completed or explicitly blocked.
- [ ] Workloads segmented.
- [ ] Capacity estimates validated.
- [ ] Cost allocation model documented.
- [ ] Python tests executed.
- [ ] Growth scenarios modeled.
- [ ] SLO/DR/security constraints reviewed.
- [ ] Billing reconciliation and rollback planned.
- [ ] Reviewer sign-off recorded.

**Related:** [Chapter 093 — Jenkins Enterprise Capacity Planning, Cost Allocation and FinOps Optimization](../093-jenkins-enterprise-capacity-planning-cost-allocation-finops-optimization.md).
