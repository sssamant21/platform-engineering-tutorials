# Chapter 093 — Jenkins Enterprise Capacity Planning, Cost Allocation and FinOps Optimization

**Part 19 — Enterprise Jenkins SRE Operations and FinOps**  
**Audience:** SRE/DBRE, Jenkins platform engineering, DevOps, cloud finance, security and service owners.  
**Prerequisites:** Chapters 091–092, Python 3, basic Prometheus, Kubernetes/EKS/AKS and cloud billing concepts.

## Outcomes

Build workload-aware Jenkins capacity forecasts, understand controller/agent bottlenecks, allocate spend by team, evaluate rightsizing without violating SLOs, and produce repeatable evidence for cost governance.

## 1. Architecture

```text
Jenkins job/queue events ──┐
Agent/executor telemetry ──┤
Cloud compute & storage ───┼─> normalized usage model
Billing tags & invoices ───┤         |
SLOs/error budgets ────────┘         v
                             forecast + allocation
                                      |
                          budget, capacity, approval
                                      |
                           staging load/DR validation
```

Optimize cost per successful, comparable build while preserving queue-time, agent-provisioning and reliability objectives. Never reduce the number of active Jenkins controller writers below one or create a second writer to shared JENKINS_HOME for capacity.

## 2. Capacity model

| Layer | Primary signals | Risks |
|---|---|---|
| Controller | CPU, heap, GC, queue processing, threads, disk I/O | unresponsive UI, delayed scheduling |
| Static agents | executor utilization, idle hours, JVM/process pressure | wasted spend, queue bottleneck |
| Ephemeral agents | startup latency, pending pods, node scaling, image pulls | quota, scheduling, cold-start delays |
| Storage | JENKINS_HOME growth, workspace/cache, artifact retention, IOPS | outages, expensive volumes |
| Network | SCM pulls, registry traffic, artifacts, cross-region egress | latency and transfer charges |
| Cloud node pools | requested vs used resources, bin-packing, spot interruption | overprovisioning or reliability loss |

Use p50/p95/p99 job queue and agent start time by workload class. Track burst concurrency separately from daily averages.

## 3. Sizing calculations

Approximate required executors:

```text
average concurrent jobs = arrival rate (jobs/min) × mean runtime (min)
capacity with headroom = ceil(average concurrency / target utilization)
```

Little's Law is a long-run average relation for a stable system; it does **not** guarantee burst queue latency. For critical workloads use empirical peak-concurrency traces, load tests and admission controls.

Example: 10 jobs/min × 6 min = 60 concurrent jobs on average. At 70% target utilization, initial estimate is ceil(60/0.7) = 86 executors, then validate against burst traces and SLOs.

## 4. Cloud cost components

```text
total = controller compute + agent compute + persistent volumes
      + artifacts + backups + egress + logging/metrics
      + licenses/support + shared platform overhead
```

Allocate directly tagged resources first. For shared controller/storage costs, select and document a defensible allocation key (e.g. weighted agent-minutes or successful build-minutes). Reconcile allocated total to invoice and maintain an unallocated bucket for incomplete tagging.

## 5. Optimization decision matrix

| Candidate | Potential gain | Guardrail |
|---|---|---|
| Scale ephemeral agents to zero when idle | lower idle compute | queue-start SLO |
| Right-size CPU/memory requests | better node packing | OOM/CPU throttling |
| Use spot for interruptible builds | lower unit cost | retry and interruption handling |
| Cache dependencies close to runners | shorter builds and egress | cache integrity/security |
| Artifact lifecycle policies | lower storage | audit/retention requirements |
| Split pools by workload | more accurate rightsizing | isolation and quotas |
| Controller JVM tuning | avoid excess headroom | GC and stability tests |
| Schedule nonurgent builds | smooth demand | release deadlines |

Measure baseline and post-change SLOs before claiming savings. Do not delete backups or compliance artifacts solely to reduce spend.

## 6. Executable capacity and cost calculator

Save `scripts/capacity_finops.py`:

```python
#!/usr/bin/env python3
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

REQUIRED = {"team", "jobs", "mean_runtime_minutes", "agent_hourly_usd"}

def compute(rows, utilization=0.70, jobs_per_minute=None):
    if not 0 < utilization < 1:
        raise ValueError("utilization must be between 0 and 1")
    by_team = defaultdict(lambda: {"jobs": 0, "agent_hours": 0.0, "agent_cost_usd": 0.0})
    for row in rows:
        if not REQUIRED.issubset(row):
            raise ValueError("missing required columns")
        team = row["team"].strip()
        jobs = int(row["jobs"])
        runtime = float(row["mean_runtime_minutes"])
        rate = float(row["agent_hourly_usd"])
        if not team or jobs < 0 or runtime < 0 or rate < 0:
            raise ValueError("invalid team, jobs, runtime or rate")
        hours = jobs * runtime / 60
        by_team[team]["jobs"] += jobs
        by_team[team]["agent_hours"] += hours
        by_team[team]["agent_cost_usd"] += hours * rate
    result = {"teams": {}, "total_agent_cost_usd": 0.0}
    for team, values in sorted(by_team.items()):
        result["teams"][team] = {
            "jobs": values["jobs"],
            "agent_hours": round(values["agent_hours"], 2),
            "agent_cost_usd": round(values["agent_cost_usd"], 2),
        }
        result["total_agent_cost_usd"] += values["agent_cost_usd"]
    result["total_agent_cost_usd"] = round(result["total_agent_cost_usd"], 2)
    if jobs_per_minute is not None:
        if jobs_per_minute < 0:
            raise ValueError("jobs_per_minute cannot be negative")
        total_jobs = sum(v["jobs"] for v in by_team.values())
        total_minutes = sum(v["agent_hours"] for v in by_team.values()) * 60
        mean_runtime = total_minutes / total_jobs if total_jobs else 0
        result["average_concurrency"] = round(jobs_per_minute * mean_runtime, 2)
        result["estimated_executors"] = math.ceil(
            jobs_per_minute * mean_runtime / utilization
        )
    return result

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv_file")
    p.add_argument("--utilization", type=float, default=0.70)
    p.add_argument("--jobs-per-minute", type=float)
    args = p.parse_args()
    with Path(args.csv_file).open(newline="") as f:
        rows = list(csv.DictReader(f))
    print(json.dumps(compute(rows, args.utilization, args.jobs_per_minute), indent=2))
```

Save `data/build_usage.csv`:

```csv
team,jobs,mean_runtime_minutes,agent_hourly_usd
payments,600,8,0.24
analytics,300,12,0.30
platform,100,6,0.20
```

Run:

```bash
python3 scripts/capacity_finops.py data/build_usage.csv --jobs-per-minute 2 --utilization 0.70
```

Expected agent costs: payments $19.20, analytics $18.00, platform $2.00, total $39.20. This simplified model assumes one billed agent per build and excludes idle time, controller/storage/network, minimum billing increments and shared overhead.

## 7. Automated tests

Save `tests/test_capacity_finops.py`:

```python
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from capacity_finops import compute

class CapacityTests(unittest.TestCase):
    def test_cost(self):
        rows = [{"team":"a","jobs":"60","mean_runtime_minutes":"10","agent_hourly_usd":"0.20"}]
        result = compute(rows, jobs_per_minute=1, utilization=0.5)
        self.assertEqual(result["total_agent_cost_usd"], 2.0)
        self.assertEqual(result["estimated_executors"], 20)

    def test_invalid(self):
        rows = [{"team":"a","jobs":"-1","mean_runtime_minutes":"5","agent_hourly_usd":"0.20"}]
        with self.assertRaises(ValueError):
            compute(rows)

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 -m unittest discover -s tests -v
```

## 8. Forecasting workflow

1. Gather at least four weeks of job and billing data; include month-end peaks.
2. Normalize by job class, architecture, region, runner type and successful outcomes.
3. Estimate demand scenarios: baseline, +25%, +50% and burst.
4. Compare requested/used CPU and memory and node packing.
5. Quantify storage and artifact growth separately.
6. Review rightsizing candidates and failure blast radius.
7. Run staging load tests with realistic concurrency and queue SLIs.
8. Approve cost changes only after SLO, DR and security checks.
9. Track realized savings against actual bills and attribution.

## 9. Prometheus metric design

Illustrative **custom** metrics (not guaranteed Jenkins exporter names):

```text
jenkins_build_runtime_seconds_bucket{team,tier,le}
jenkins_agent_active_seconds_total{pool,team}
jenkins_agent_idle_seconds_total{pool}
jenkins_queue_wait_seconds_bucket{tier,le}
jenkins_agent_provision_seconds_bucket{pool,le}
```

Avoid high-cardinality labels such as build ID or commit SHA. Confirm metric sources and query semantics before relying on dashboards.

## 10. Twenty troubleshooting scenarios

| # | Symptom | Investigation |
|---|---|---|
| 01 | Cost report misses shared overhead | allocation |
| 02 | Cloud bill exceeds estimate | idle/billing |
| 03 | Duplicate agent charges | billing joins |
| 04 | Missing cost-center tag | governance |
| 05 | Queue p95 rises after rightsizing | capacity |
| 06 | Spot interruption fails builds | retry |
| 07 | Agent pod Pending | quota/scheduler |
| 08 | Controller heap pressure | GC |
| 09 | CPU throttling | limits |
| 10 | Disk fills | retention |
| 11 | Artifact egress spikes | region/network |
| 12 | Cache corruption | validation |
| 13 | Executor count misleading | heterogeneity |
| 14 | Monthly average hides burst | peak trace |
| 15 | SLO target violated | rollback |
| 16 | Savings not realized | invoice |
| 17 | Billing data stale | ingestion |
| 18 | Shared team attribution disputed | allocation rule |
| 19 | Critical builds starved | priority/isolation |
| 20 | FinOps change breaks DR | resilience gate |

## 11. Six production runbooks

### A. Capacity exhaustion
Validate queue and agent metrics, identify bottleneck, scale approved pools, check quotas and preserve evidence.

### B. Unexpected cloud spend
Reconcile billing with tags, ephemeral agent lifecycle, idle time, artifacts, egress and storage growth; assign owners.

### C. Failed rightsizing
Compare before/after SLOs and error budgets, revert resource limits or pool sizing and document COA.

### D. Spot interruption storm
Route critical builds to stable pools, enforce retries and monitor build failure attribution.

### E. Storage or artifact growth
Identify top consumers, apply approved retention only after backup/audit review, validate restore paths.

### F. Cost attribution dispute
Reconcile source data, allocation method and invoice, document shared overhead and approve corrections.

## 12. 100-point acceptance

| Domain | Points |
|---|---:|
| Capacity signals and workload segmentation | 20 |
| Cost model and allocation accuracy | 20 |
| Forecast and scenario testing | 20 |
| SLO, DR and security guardrails | 15 |
| Rightsizing and realized-savings validation | 15 |
| Tests, runbooks and evidence | 10 |
| **Total** | **100** |

Suggested pass 85/100 plus mandatory gates: reconciled billing, documented allocation, no SLO regression, no DR/security reduction, validated cost assumptions and owner sign-off.

## 13. Evidence template

```text
UTC / owner / environment:
Billing period and source:
Agent usage and runtime classes:
Controller/agent/storage/network cost:
Shared overhead allocation:
Queue/agent SLO baseline:
Capacity forecast and burst scenario:
Rightsizing proposal and rollback:
Tests and invoice reconciliation:
20 scenarios / six runbooks:
Score / RCA / COA / reviewer:
```

**Companion:** [Chapter 093 hands-on lab](labs/093-jenkins-enterprise-capacity-planning-cost-allocation-finops-optimization-check.md).  
**Next:** Chapter 094 — Jenkins Enterprise Security, Compliance and Operational Risk Management.
