# Chapter 035 — Enterprise Exporter Integration, Metrics Governance and Production Readiness Capstone

**Part 07 — Exporters and Custom Instrumentation: FINAL CAPSTONE**  
**Audience:** Enterprise SRE/DBRE, platform observability and production on-call.  
**Prerequisites:** Chapters 031–034, Prometheus/Alertmanager, Linux and PostgreSQL basics, Python 3.10+.

## 1. End-to-end enterprise architecture

```text
Linux nodes -> Node Exporter ----------+
PostgreSQL -> postgres_exporter -------+
HTTP service -> Blackbox Exporter -----+-> Prometheus HA -> recording rules -> Grafana
Application -> Python custom exporter -+                 |
                                                          v
                                               SLO alerts / Alertmanager
                                                          |
                                                on-call -> RCA -> rollback
```

The fleet must have explicit ownership, secure scrape paths, expected-target inventory, bounded label sets, metric contracts, query/collection timeouts, alert delivery tests and tested rollback. The four exporter classes have different failure modes; a successful `up` scrape is not proof of service health.

## 2. Metrics governance contract

| Component | Core signals | Safety/quality gates |
|---|---|---|
| Node Exporter | CPU, MemAvailable, diskstats, filesystem, network | host namespace/mount correctness; privileged surface review |
| PostgreSQL Exporter | `pg_up`, transactions, sessions, replication, vacuum | least privilege; DSN secrets; query cost |
| Blackbox Exporter | `probe_success`, duration, status, DNS/TLS | approved targets; SSRF controls; multi-vantage SLO |
| Custom Python Exporter | bounded counters, gauges, histograms | stable schema; unit/bucket review; series budget |

### Capacity and cardinality

Total estimated active series = sum across exporters, including histogram bucket expansion and label combinations. The policy fixture budget is an illustrative review threshold, not a universal safe Prometheus limit. Monitor active series, scrape samples, ingestion rate, churn, TSDB disk and query latency. Review retention and HA remote-write costs separately.

## 3. Deployment and change controls

1. Register service/target inventory and owner.
2. Review exporter versions, authentication, network paths and least-privilege configuration.
3. Validate metric naming, units, label sets, histogram buckets and retention.
4. Run offline policy tests and `promtool check config` / `promtool check rules`.
5. Deploy to isolated staging; validate `up`, `pg_up`, `probe_success`, application counters and missing-target detection.
6. Test synthetic alert route, fallback and acknowledgement without real paging.
7. Simulate exporter failure, DB failover, bad target and cardinality spike.
8. Approve rollout, monitor ingestion/cost and retain rollback evidence.

## 4. Production-style PromQL review

```promql
up{job=~"node|postgres|blackbox-http|custom-python"} == 0
pg_up == 0
probe_success{job="blackbox-http"} == 0
rate(node_disk_read_bytes_total[5m])
sum by (result) (rate(dbre_jobs_total[5m]))
histogram_quantile(0.95, sum by (le) (rate(dbre_job_duration_seconds_bucket[5m])))
```

Metric names/labels depend on installed versions and configuration. Maintain a separate expected-target inventory so disappearing targets cannot silently disappear from alert evaluation.

## 5. Security and resilience

Keep exporter endpoints private, use TLS/auth where appropriate, restrict Blackbox probe egress and prevent metadata-service access. Do not expose database credentials, SQL text, PHI/PII, request IDs or other unbounded labels. Test Alertmanager route delivery independently from rule evaluation. Design HA Prometheus/Alertmanager failure domains and validate DR/rollback using approved staging drills.

## 6. Executable offline capstone acceptance

This JSON is a **synthetic acceptance manifest**, not Prometheus or Kubernetes configuration. Its gate verifies declared reviews, scrape status, budget, inventory and notification evidence flags. Boolean flags are attestations; they do not independently prove real tests occurred.

Create:

```text
chapter035/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/acceptance.py
  tests/test_acceptance.py
```

### fixtures/healthy.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "change_id": "OBS-035",
  "services": [
    "linux-node",
    "postgresql",
    "api"
  ],
  "exporters": [
    {
      "name": "node",
      "target": "node-exporter:9100",
      "scrape_ok": true,
      "owner": "sre",
      "series": 12000
    },
    {
      "name": "postgres",
      "target": "postgres-exporter:9187",
      "scrape_ok": true,
      "owner": "dbre",
      "series": 8500
    },
    {
      "name": "blackbox",
      "target": "blackbox:9115",
      "scrape_ok": true,
      "owner": "sre",
      "series": 1200
    },
    {
      "name": "custom",
      "target": "custom-exporter:9108",
      "scrape_ok": true,
      "owner": "platform",
      "series": 600
    }
  ],
  "series_budget": 30000,
  "retention_reviewed": true,
  "metric_schema_reviewed": true,
  "cardinality_reviewed": true,
  "security_reviewed": true,
  "alert_tested": true,
  "rollback_tested": true,
  "drill_completed": true,
  "backup_owner": "secondary-oncall",
  "runbook": "https://example.org/runbooks/observability-exporters",
  "scrape_interval_seconds": 30,
  "scrape_timeout_seconds": 10,
  "protected_metrics_endpoint": true,
  "synthetic_notification_received": true
}
```

### fixtures/degraded.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "change_id": "OBS-035",
  "services": [
    "linux-node",
    "postgresql",
    "api"
  ],
  "exporters": [
    {
      "name": "node",
      "target": "node-exporter:9100",
      "scrape_ok": true,
      "owner": "sre",
      "series": 12000
    },
    {
      "name": "postgres",
      "target": "postgres-exporter:9187",
      "scrape_ok": false,
      "owner": "dbre",
      "series": 8500
    },
    {
      "name": "blackbox",
      "target": "blackbox:9115",
      "scrape_ok": true,
      "owner": "sre",
      "series": 22000
    },
    {
      "name": "custom",
      "target": "custom-exporter:9108",
      "scrape_ok": true,
      "owner": "platform",
      "series": 600
    }
  ],
  "series_budget": 30000,
  "retention_reviewed": true,
  "metric_schema_reviewed": true,
  "cardinality_reviewed": true,
  "security_reviewed": false,
  "alert_tested": true,
  "rollback_tested": true,
  "drill_completed": true,
  "backup_owner": "secondary-oncall",
  "runbook": "https://example.org/runbooks/observability-exporters",
  "scrape_interval_seconds": 30,
  "scrape_timeout_seconds": 35,
  "protected_metrics_endpoint": true,
  "synthetic_notification_received": false
}
```

### scripts/acceptance.py

```python
#!/usr/bin/env python3
"""Offline exporter capstone acceptance; not a live scrape or notification test."""
import json,sys
from pathlib import Path
REQUIRED={"node","postgres","blackbox","custom"}
def validate(p):
    e=[]
    if not isinstance(p,dict): return ["manifest must be object"]
    for k in ("owner","environment","change_id","backup_owner","runbook"):
        if not isinstance(p.get(k),str) or not p[k]: e.append("missing "+k)
    for k in ("retention_reviewed","metric_schema_reviewed","cardinality_reviewed","security_reviewed","alert_tested","rollback_tested","drill_completed","protected_metrics_endpoint","synthetic_notification_received"):
        if p.get(k) is not True: e.append("gate failed "+k)
    interval=p.get("scrape_interval_seconds");timeout=p.get("scrape_timeout_seconds")
    if type(interval) is not int or type(timeout) is not int or not 0<timeout<interval<=300: e.append("invalid timing")
    services=p.get("services")
    if not isinstance(services,list) or not {"linux-node","postgresql","api"}.issubset(services): e.append("missing services")
    exporters=p.get("exporters")
    if not isinstance(exporters,list) or not exporters: e.append("missing exporters");exporters=[]
    names=set();total=0
    for i,x in enumerate(exporters):
        tag="exporter "+str(i)
        if not isinstance(x,dict): e.append(tag+" invalid");continue
        name=x.get("name")
        if not isinstance(name,str) or not name or name in names: e.append(tag+" duplicate/missing name")
        else: names.add(name)
        if not isinstance(x.get("target"),str) or not x["target"]: e.append(tag+" missing target")
        if not isinstance(x.get("owner"),str) or not x["owner"]: e.append(tag+" missing owner")
        if x.get("scrape_ok") is not True: e.append(tag+" scrape failed")
        count=x.get("series")
        if type(count) is not int or count<0: e.append(tag+" invalid series")
        else: total+=count
    if not REQUIRED.issubset(names): e.append("missing required exporters")
    budget=p.get("series_budget")
    if type(budget) is not int or budget<=0: e.append("invalid series budget")
    elif total>budget: e.append("series budget exceeded")
    return e
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 acceptance.py fixtures/healthy.json")
    try: findings=validate(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as exc: sys.exit(str(exc))
    print(json.dumps({"status":"FAIL" if findings else "PASS","findings":findings},indent=2))
    sys.exit(bool(findings))
```

### tests/test_acceptance.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from acceptance import validate
class AcceptanceTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def bad(self,change):
        p=copy.deepcopy(self.p);exec(change,{},{"p":p});self.assertTrue(validate(p))
    def test_healthy(self): self.assertEqual(validate(self.p),[])
    def test_degraded(self): self.assertTrue(validate(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_non_object(self): self.assertTrue(validate(None))
    def test_01_owner(self): self.bad("p[\"owner\"]=\"\"")
    def test_02_change(self): self.bad("p[\"change_id\"]=\"\"")
    def test_03_backup(self): self.bad("p[\"backup_owner\"]=\"\"")
    def test_04_retention(self): self.bad("p[\"retention_reviewed\"]=False")
    def test_05_schema(self): self.bad("p[\"metric_schema_reviewed\"]=False")
    def test_06_cardinality(self): self.bad("p[\"cardinality_reviewed\"]=False")
    def test_07_security(self): self.bad("p[\"security_reviewed\"]=False")
    def test_08_alert(self): self.bad("p[\"alert_tested\"]=False")
    def test_09_rollback(self): self.bad("p[\"rollback_tested\"]=False")
    def test_10_drill(self): self.bad("p[\"drill_completed\"]=False")
    def test_11_protected(self): self.bad("p[\"protected_metrics_endpoint\"]=False")
    def test_12_notification(self): self.bad("p[\"synthetic_notification_received\"]=False")
    def test_13_timeout(self): self.bad("p[\"scrape_timeout_seconds\"]=30")
    def test_14_interval(self): self.bad("p[\"scrape_interval_seconds\"]=0")
    def test_15_services(self): self.bad("p[\"services\"]=[\"api\"]")
    def test_16_exporters(self): self.bad("p[\"exporters\"]=[]")
    def test_17_missing_node(self): self.bad("p[\"exporters\"]=p[\"exporters\"][1:]")
    def test_18_duplicate(self): self.bad("p[\"exporters\"][1][\"name\"]=\"node\"")
    def test_19_scrape(self): self.bad("p[\"exporters\"][0][\"scrape_ok\"]=False")
    def test_20_target(self): self.bad("p[\"exporters\"][0][\"target\"]=\"\"")
    def test_21_exporter_owner(self): self.bad("p[\"exporters\"][0][\"owner\"]=\"\"")
    def test_22_series_negative(self): self.bad("p[\"exporters\"][0][\"series\"]=-1")
    def test_23_budget(self): self.bad("p[\"series_budget\"]=0")
    def test_24_over_budget(self): self.bad("p[\"series_budget\"]=100")
    def test_25_runbook(self): self.bad("p[\"runbook\"]=\"\"")
    def test_26_wrong_type(self): self.bad("p[\"exporters\"][0][\"series\"]=\"100\"")
if __name__=="__main__": unittest.main()
```

### Run

```bash
cd chapter035
python3 scripts/acceptance.py fixtures/healthy.json
if python3 scripts/acceptance.py fixtures/degraded.json; then
  echo "FAIL: degraded acceptance manifest accepted"; exit 1
else
  echo "PASS: degraded manifest rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and **29 authored unit tests** pass.

## 7. Twenty-four hands-on exercises

1. Inventory Linux nodes.
2. Inventory PostgreSQL targets.
3. Inventory application endpoints.
4. Inventory custom metrics.
5. Assign metric ownership.
6. Set scrape SLAs.
7. Validate target discovery.
8. Validate up vs probe_success.
9. Validate pg_up vs up.
10. Inspect metric schema.
11. Inspect histogram buckets.
12. Audit label cardinality.
13. Calculate series budget.
14. Review retention impact.
15. Review secure endpoints.
16. Review least privilege.
17. Review no-data alerts.
18. Review actionable alert routes.
19. Simulate exporter outage.
20. Simulate PostgreSQL failover.
21. Simulate probe failure.
22. Simulate cardinality explosion.
23. Run healthy/degraded acceptance.
24. Run 29 tests and score capstone.

## 8. Twenty-six production failure scenarios

| # | Failure | First diagnostic |
|---|---|---|
| 1 | Node exporter unavailable | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 2 | Postgres exporter unavailable | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 3 | Blackbox probe fails | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 4 | Custom exporter unavailable | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 5 | Prometheus target absent | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 6 | Scrape timeout | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 7 | DNS failure | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 8 | TLS failure | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 9 | Postgres authentication error | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 10 | DB connection saturation | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 11 | High CPU | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 12 | Low memory | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 13 | Disk I/O pressure | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 14 | Filesystem full | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 15 | Probe endpoint returns 500 | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 16 | Probe SSRF exposure | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 17 | Custom query overload | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 18 | High-cardinality labels | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 19 | Metric schema regression | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 20 | Counter reset misread | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 21 | Missing expected target | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 22 | Wrong route severity | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 23 | Notification not delivered | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 24 | Fallback receiver missing | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 25 | Rollback not tested | Inspect expected target, exporter health, collector, labels, alerts and rollback |
| 26 | Exporter upgrade regression | Inspect expected target, exporter health, collector, labels, alerts and rollback |

## 9. Eight production runbooks

1. Exporter fleet outage: triage Prometheus scrape health, service discovery and network policy.
2. PostgreSQL monitoring outage: distinguish pg_up from exporter up, validate grants and credentials.
3. Blackbox false positive: check vantage point, target inventory, status, DNS/TLS and application SLIs.
4. Cardinality emergency: identify high-churn labels, disable offending exporter and restore budgets.
5. Missing telemetry: reconcile target inventory with up/absent series and independent heartbeat.
6. Security incident: isolate exporter endpoints, review privileges and rotate exposed credentials.
7. Alert delivery failure: trace rule, Alertmanager route, receiver response and human acknowledgement.
8. Rollback and recovery: revert reviewed config, confirm scrape, alerts and dashboard recovery.

## 10. Capstone incident game day

**Scenario:** PostgreSQL primary failover breaks monitoring credentials; the API returns intermittent 5xx; a Blackbox probe still returns 200 from its basic health endpoint; Node Exporter reports disk I/O pressure; a custom exporter adds a per-query label causing a series explosion. Prometheus is overloaded and notification routing is delayed.

**Mission:** isolate user impact from telemetry failure, recover PostgreSQL visibility, design representative probes, roll back unsafe custom labels, restore scrape health and validate test-only alert delivery. Capture incident timeline, decisions, evidence, on-call acknowledgement, cost impact and follow-up owners. Run only in disposable/staging infrastructure.

## 11. 100-point Part 07 acceptance

| Domain | Points |
|---|---:|
| Four-exporter architecture and metric correctness | 20 |
| Deployment and operational diagnostics | 20 |
| Security, cardinality and cost governance | 20 |
| Offline acceptance gate and 29 tests | 20 |
| Incident simulation, runbooks and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Mandatory: service ownership, safe secrets, target inventory, bounded labels, no-data detection, notification evidence and tested rollback. Offline acceptance alone does **not** certify production readiness.

## 12. Evidence worksheet

```text
UTC / change ID / environment / owner:
Node/PostgreSQL/Blackbox/custom exporter versions:
Prometheus target inventory and scrape evidence:
PostgreSQL pg_up and probe_success:
Cardinality / series budget / retention:
Secrets, TLS, network and SSRF review:
Healthy/degraded acceptance / 29 tests:
Synthetic alert delivery and backup escalation:
Game day / rollback / reviewer / 100-point score:
```

**Companion:** [Chapter 035 enterprise exporter capstone lab](labs/035-enterprise-exporter-integration-metrics-governance-production-readiness-capstone-lab.md).

**Part 07 complete. Next:** Chapter 036 — Centralized Logging Architecture, Grafana Loki and Log Collection Fundamentals (Part 08 — Centralized Logging with Loki).
