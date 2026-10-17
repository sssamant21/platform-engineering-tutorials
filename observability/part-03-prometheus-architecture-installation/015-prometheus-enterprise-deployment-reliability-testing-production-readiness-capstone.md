# Chapter 015 — Prometheus Enterprise Deployment, Reliability Testing and Production Readiness Capstone

**Part 03 — Prometheus Architecture and Installation: FINAL CAPSTONE**  
**Audience:** Enterprise SRE/DBRE, observability platform owners, security engineers and incident commanders.  
**Prerequisites:** Chapters 011–014; Python 3.10+ for offline lab; optional Prometheus/Alertmanager staging environment.  
**Outcome:** Produce a reviewable deployment blueprint, SLO-based acceptance gate, failure drills, runbooks, rollback and production go/no-go decision.

## 1. Mission and acceptance boundaries

Build a production-readiness design for a fictional regional observability service collecting Linux, Kubernetes, PostgreSQL, MongoDB, Elasticsearch and Redis metrics. Evaluate target discovery, scrape reliability, local TSDB/WAL, HA, remote-write freshness, alert routing, capacity, security, recovery and operational governance.

The lab is **synthetic and offline**. A passing fixture is not evidence of live Prometheus availability, durable remote write or a tested production restore.

## 2. Enterprise reference architecture

```text
                   Linux / K8s / DB exporters
                               |
                  service discovery + RBAC
                               |
                  +------------+------------+
                  |                         |
           Prometheus A               Prometheus B
           zone-a / PVC               zone-b / PVC
           scrape + rules             scrape + rules
                  |                         |
                  +------------+------------+
                               |
                  remote-write receiver
                    / durable backend
                               |
                      query frontend
                               |
                        Grafana / API

            Alertmanager peers across failure domains
                               |
                   pager / ticket / on-call
```

Separate production and nonproduction tenancy, define service owner and escalation, review exporter permissions and data classification, and use a tested backend-specific HA deduplication strategy. Do not assume dual scrapers imply shared storage or exactly-once ingestion.

## 3. Deployment readiness checklist

| Domain | Design decision | Required evidence |
|---|---|---|
| Availability | two scrapers in independent domains | placement and failover drill |
| Target coverage | approved exporter inventory | targets API and missing-data rule |
| Scrape quality | interval, timeout, limits | duration and errors |
| TSDB | persistent storage, WAL, retention | disk/headroom/replay RTO |
| Cardinality | bounded label policy | series trend and review |
| Remote write | receiver, auth, queue/freshness | lag and outage drill |
| Query | frontend/backend and SLO | latency and success |
| Alerts | HA Alertmanager and route ownership | end-to-end page test |
| Security | TLS, least privilege, secrets | IAM/network review |
| DR | backup, restore, RPO/RTO | dated restore evidence |
| Change | GitOps, approvals, rollback | versioned plan and rehearsal |

## 4. Configuration baseline

```yaml
global:
  scrape_interval: 15s
  scrape_timeout: 10s
  evaluation_interval: 15s
  external_labels:
    cluster: prod-east
    replica: prom-a
scrape_configs:
  - job_name: node
    static_configs:
      - targets: ["node-exporter.internal:9100"]
    sample_limit: 50000
    label_limit: 50
```

This is a **configuration fragment**, not a complete secure production deployment. Replica B requires its own external replica label, independent PVC and failure-domain placement. Replace static targets with approved service discovery, network policies, TLS/auth and bounded relabeling.

## 5. Operational SLIs and PromQL

```promql
sum(up) / count(up)
```

```promql
scrape_duration_seconds / scrape_timeout_seconds
```

```promql
prometheus_tsdb_head_series
```

```promql
prometheus_tsdb_compactions_failed_total
```

```promql
prometheus_remote_storage_samples_pending
```

```promql
absent_over_time(up{job="node"}[5m])
```

The simple `sum(up)/count(up)` is a target-level availability snapshot, **not** a customer-facing service SLO. A missing target can vanish from the denominator; use inventory-based coverage and explicit absence alerts. Check remote-write metric names and labels against your Prometheus version.

## 6. Read-only production investigation commands

```bash
date -u
curl -fsS 'http://127.0.0.1:9090/-/ready'
curl -fsS 'http://127.0.0.1:9090/api/v1/targets'
curl -fsS 'http://127.0.0.1:9090/api/v1/rules'
curl -fsS 'http://127.0.0.1:9090/api/v1/status/tsdb'
curl -fsS 'http://127.0.0.1:9090/api/v1/query?query=prometheus_tsdb_head_series'
```

Use only approved endpoints and credentials. No destructive changes, stress tests, alert silences or configuration reloads are authorized by this chapter.

## 7. Complete executable offline acceptance gate

Create:

```text
chapter015/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/readiness.py
  tests/test_readiness.py
```

### fixtures/healthy.json

```json
{
  "environment": "staging",
  "owner": "observability-sre",
  "prometheus_replicas": 2,
  "failure_domains": 2,
  "alertmanager_replicas": 3,
  "targets_total": 120,
  "targets_up": 120,
  "missing_expected_targets": 0,
  "scrape_p99_seconds": 2,
  "scrape_timeout_seconds": 10,
  "head_series": 400000,
  "series_budget": 1000000,
  "tsdb_disk_used_pct": 55,
  "remote_write_lag_seconds": 20,
  "remote_write_lag_budget_seconds": 120,
  "query_availability_pct": 99.99,
  "query_slo_pct": 99.9,
  "backup_restore_age_days": 20,
  "max_backup_restore_age_days": 90,
  "runbook_owners_assigned": true,
  "change_rollback_tested": true
}
```

### fixtures/degraded.json

```json
{
  "environment": "staging",
  "owner": "observability-sre",
  "prometheus_replicas": 1,
  "failure_domains": 1,
  "alertmanager_replicas": 1,
  "targets_total": 120,
  "targets_up": 104,
  "missing_expected_targets": 3,
  "scrape_p99_seconds": 15,
  "scrape_timeout_seconds": 10,
  "head_series": 1300000,
  "series_budget": 1000000,
  "tsdb_disk_used_pct": 94,
  "remote_write_lag_seconds": 900,
  "remote_write_lag_budget_seconds": 120,
  "query_availability_pct": 97,
  "query_slo_pct": 99.9,
  "backup_restore_age_days": 200,
  "max_backup_restore_age_days": 90,
  "runbook_owners_assigned": false,
  "change_rollback_tested": false
}
```

### scripts/readiness.py

```python
#!/usr/bin/env python3
"""Synthetic Prometheus production-readiness gate. No network or production actions."""
import json
import math
import sys
from pathlib import Path
COUNTS = ("prometheus_replicas", "failure_domains", "alertmanager_replicas",
          "targets_total", "targets_up", "missing_expected_targets", "head_series", "series_budget")
NUMBERS = ("scrape_p99_seconds", "scrape_timeout_seconds", "tsdb_disk_used_pct",
           "remote_write_lag_seconds", "remote_write_lag_budget_seconds",
           "query_availability_pct", "query_slo_pct",
           "backup_restore_age_days", "max_backup_restore_age_days")
BOOLS = ("runbook_owners_assigned", "change_rollback_tested")

def assess(d):
    findings = []
    for k in ("environment", "owner"):
        if not isinstance(d.get(k), str) or not d[k].strip():
            findings.append("missing " + k)
    for k in COUNTS:
        if type(d.get(k)) is not int or d[k] < 0:
            findings.append("invalid " + k)
    for k in NUMBERS:
        v = d.get(k)
        if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
            findings.append("invalid " + k)
    for k in BOOLS:
        if type(d.get(k)) is not bool:
            findings.append("invalid " + k)
    if findings:
        return sorted(set(findings))
    for k in ("targets_total", "series_budget", "scrape_timeout_seconds",
              "remote_write_lag_budget_seconds", "max_backup_restore_age_days"):
        if d[k] == 0:
            findings.append("invalid positive " + k)
    for k in ("tsdb_disk_used_pct", "query_availability_pct", "query_slo_pct"):
        if d[k] > 100:
            findings.append("invalid percentage " + k)
    if findings:
        return findings
    if d["targets_up"] > d["targets_total"]:
        findings.append("targets_up exceeds targets_total")
    if d["prometheus_replicas"] < 2 or d["failure_domains"] < 2:
        findings.append("insufficient scraper HA")
    if d["alertmanager_replicas"] < 2:
        findings.append("insufficient alert routing HA")
    if d["targets_up"] / d["targets_total"] < .99:
        findings.append("scrape availability below 99%")
    if d["missing_expected_targets"]:
        findings.append("expected target missing")
    if d["scrape_p99_seconds"] >= d["scrape_timeout_seconds"]:
        findings.append("scrape p99 exceeds timeout")
    if d["head_series"] > d["series_budget"]:
        findings.append("cardinality budget exceeded")
    if d["tsdb_disk_used_pct"] >= 85:
        findings.append("TSDB disk headroom low")
    if d["remote_write_lag_seconds"] > d["remote_write_lag_budget_seconds"]:
        findings.append("remote-write freshness budget exceeded")
    if d["query_availability_pct"] < d["query_slo_pct"]:
        findings.append("query availability below SLO")
    if d["backup_restore_age_days"] > d["max_backup_restore_age_days"]:
        findings.append("restore drill overdue")
    if not d["runbook_owners_assigned"]:
        findings.append("runbook ownership missing")
    if not d["change_rollback_tested"]:
        findings.append("rollback not tested")
    return findings

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 readiness.py fixtures/healthy.json")
    try:
        findings = assess(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError, ValueError) as exc:
        sys.exit(f"input error: {exc}")
    print("READINESS PASS (synthetic)" if not findings else "READINESS FAIL")
    for finding in findings:
        print("-", finding)
    sys.exit(bool(findings))
```

### tests/test_readiness.py

```python
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from readiness import assess

class ReadinessTests(unittest.TestCase):
    def fixture(self, name="healthy.json"):
        return json.loads((ROOT / "fixtures" / name).read_text())
    def changed(self, **kw):
        d = self.fixture()
        d.update(kw)
        return assess(d)
    def test_healthy(self): self.assertEqual(assess(self.fixture()), [])
    def test_degraded(self): self.assertTrue(assess(self.fixture("degraded.json")))
    def test_replica(self): self.assertTrue(self.changed(prometheus_replicas=1))
    def test_domain(self): self.assertTrue(self.changed(failure_domains=1))
    def test_alertmanager(self): self.assertTrue(self.changed(alertmanager_replicas=1))
    def test_scrape(self): self.assertTrue(self.changed(targets_up=110))
    def test_absent(self): self.assertTrue(self.changed(missing_expected_targets=1))
    def test_timeout(self): self.assertTrue(self.changed(scrape_p99_seconds=12))
    def test_cardinality(self): self.assertTrue(self.changed(head_series=1200000))
    def test_disk(self): self.assertTrue(self.changed(tsdb_disk_used_pct=90))
    def test_lag(self): self.assertTrue(self.changed(remote_write_lag_seconds=500))
    def test_query(self): self.assertTrue(self.changed(query_availability_pct=98))
    def test_restore(self): self.assertTrue(self.changed(backup_restore_age_days=120))
    def test_owner(self): self.assertTrue(self.changed(runbook_owners_assigned=False))
    def test_rollback(self): self.assertTrue(self.changed(change_rollback_tested=False))
    def test_invalid_total(self): self.assertTrue(self.changed(targets_total=0))
    def test_invalid_bool(self): self.assertTrue(self.changed(change_rollback_tested="yes"))
    def test_invalid_nan(self): self.assertTrue(self.changed(remote_write_lag_seconds=float("nan")))
    def test_invalid_target_count(self): self.assertTrue(self.changed(targets_up=200))
    def test_missing_owner(self): self.assertTrue(self.changed(owner=""))

if __name__ == "__main__":
    unittest.main()
```

### Run acceptance

```bash
cd chapter015
python3 scripts/readiness.py fixtures/healthy.json
if python3 scripts/readiness.py fixtures/degraded.json; then
  echo "FAIL: unsafe readiness accepted"; exit 1
else
  echo "PASS: degraded readiness rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy passes, degraded fails and **20 tests pass**. Thresholds are illustrative and require service-specific tuning. The gate validates fixture values, not live Prometheus metrics.

## 8. Twenty-four capstone exercises

1. Document SLO and service owner.
2. Draw HA topology and failure domains.
3. Map Linux, Kubernetes and DB exporters.
4. Define target inventory.
5. Define bounded label contract.
6. Review scrape interval/timeout.
7. Design missing-target alerts.
8. Define TSDB retention.
9. Size WAL and disk headroom.
10. Define cardinality budget.
11. Review federation use cases.
12. Design remote-write path.
13. Define backend dedup semantics.
14. Review tenant isolation and IAM.
15. Design Alertmanager peer placement.
16. Test notification escalation tabletop.
17. Define query availability SLO.
18. Define backup and restore RPO/RTO.
19. Prepare rollback plan.
20. Create healthy fixture.
21. Create degraded fixture.
22. Execute positive/negative gate.
23. Run 20 automated tests.
24. Conduct production go/no-go review.

## 9. Twenty production failure scenarios

| # | Scenario | Diagnostic focus |
|---|---|---|
| 01 | Prometheus pod crash | replica failover |
| 02 | availability-zone outage | placement |
| 03 | exporter unavailable | scrape error |
| 04 | missing discovery target | inventory/absence |
| 05 | scrape timeout | latency |
| 06 | sample limit exceeded | scrape health |
| 07 | high-cardinality regression | labels |
| 08 | WAL replay exceeds RTO | I/O |
| 09 | TSDB disk 95% | retention/headroom |
| 10 | compaction failure | TSDB metrics |
| 11 | remote-write queue backlog | receiver |
| 12 | remote-write data gap | WAL age |
| 13 | query frontend outage | availability |
| 14 | duplicate HA samples | replica labels |
| 15 | Alertmanager peer partition | clustering |
| 16 | notification delivery failure | route |
| 17 | certificate expiry | TLS |
| 18 | leaked exporter credentials | secrets |
| 19 | untested rollback | change risk |
| 20 | restore exceeds RTO | DR |

## 10. Eight production runbooks

**A. Scrape coverage incident:** Compare target inventory with discovery, check `up`, absent targets, DNS, exporter, network and credentials; restore safely.

**B. Prometheus HA failover:** Verify surviving replica, rule evaluation, query access, target coverage and customer impact; preserve timeline.

**C. TSDB/WAL emergency:** Assess disk, head series, compaction, replay and retention; stage capacity/retention changes with backup and rollback.

**D. Remote-write outage:** Check receiver, queue, retries, freshness and WAL retention; document potential missing samples and recovery.

**E. Cardinality explosion:** Identify label source, contain ingestion growth at instrumentation, enforce policy and estimate storage costs.

**F. Alert routing failure:** Inspect Alertmanager peers, routes, receivers, silences, inhibition and end-to-end page test.

**G. Security incident:** Restrict exposed APIs/exporters, preserve evidence, rotate compromised secrets, notify security owner.

**H. Production go/no-go and rollback:** Review mandatory gates, approvals, deployment artifacts, rollback rehearsal, DR and post-deploy verification.

## 11. 100-point production acceptance rubric

| Domain | Points |
|---|---:|
| Architecture, failure domains and ownership | 20 |
| Scrape coverage, TSDB and capacity | 20 |
| Remote write, alerting, security and SLOs | 20 |
| Executable gate and 20 tests | 20 |
| Runbooks, incident drills, rollback and DR | 20 |
| **Total** | **100** |

Suggested pass: **85/100**, with mandatory zero-tolerance gates for exposed credentials, missing rollback, no restore evidence, missing target detection or single-failure-domain HA. Passing the synthetic test alone does not grant production approval.

## 12. Acceptance evidence and handover

```text
UTC / change ID / reviewer / service owner:
Prometheus version / deployment topology:
Replica zones and query failover:
Target inventory / coverage / missing-data alerts:
Scrape p99 / timeout / sample limits:
TSDB series / retention / disk / WAL replay:
Remote-write lag / receiver availability:
Alertmanager peers / end-to-end page:
TLS / IAM / tenancy / secret review:
Backup restore age / RPO / RTO:
Healthy/degraded gate / 20 tests:
Rollback rehearsal / production signoff:
```

**Companion:** [Chapter 015 executable readiness lab](labs/015-prometheus-enterprise-deployment-reliability-testing-production-readiness-capstone-lab.md).

**Part 03 complete. Next:** Chapter 016 — PromQL Fundamentals, Selectors, Instant Vectors, Range Vectors and Query Semantics (Part 04).
