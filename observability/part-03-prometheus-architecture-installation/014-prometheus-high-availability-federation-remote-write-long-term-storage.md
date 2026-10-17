# Chapter 014 — Prometheus High Availability, Federation, Remote Write and Long-Term Storage

**Part 03 — Prometheus Architecture and Installation**  
**Audience:** Enterprise SRE/DBRE, observability platform and cloud infrastructure engineers.  
**Prerequisites:** Chapters 011–013, PromQL fundamentals, Python 3.10+.  
**Deliverables:** HA topology, remote-write durability model, federation decision, long-term storage architecture, incident runbooks and executable acceptance tests.

## 1. Architecture and design objectives

Prometheus is a local-first TSDB and scraper, not a shared-disk clustered database. Running multiple identical Prometheus servers with independent storage provides scrape/query resilience; it does not by itself deduplicate samples, guarantee exactly-once remote write or preserve data during every failure.

```text
                 Service / DB / node exporters
                            |
                +-----------+-----------+
                |                       |
       Prometheus replica A     Prometheus replica B
        zone-a, local TSDB       zone-b, local TSDB
        replica="a"              replica="b"
                |                       |
          remote_write             remote_write
                +-----------+-----------+
                            |
                Receive / durable backend
              (Thanos, Mimir, Cortex or
               managed compatible service)
                            |
                 HA dedup / query frontend
                            |
                       Grafana / API

          Alertmanager cluster in >=2 failure domains
```

Choose a **specific** backend and test its HA replica-label and ingestion semantics. Query deduplication and write-path deduplication differ by backend. A load balancer across two local Prometheus servers can give query availability but will not magically merge their local histories.

## 2. HA design: scrape replicas and failure domains

- Two independent scrapers per critical target set, ideally across distinct failure domains, with separate persistent volumes and identical discovery/scrape policy.
- External labels identify cluster, region and replica. Example: `cluster="prod-east"`, `replica="prom-a"`; a second replica uses `replica="prom-b"`.
- External labels are added to communication with external systems; understand local query semantics and avoid collisions with scraped labels.
- Alertmanager HA requires peer discovery, network reachability, reliable notification configuration and deduplication testing. Redundant Prometheus instances may independently evaluate the same alert.
- Define blast radius, query-path failover, backend failure behavior and target discovery dependency.

### Example replica-specific fragment

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: prod-east
    replica: prom-a
scrape_configs:
  - job_name: node
    static_configs:
      - targets: ["node-exporter.internal:9100"]
```

This is an illustrative configuration fragment, **not** a secure, runnable production manifest. The second replica requires its own identity, storage and placement.

## 3. Federation versus remote write

| Dimension | Federation | Remote write |
|---|---|---|
| Model | Prometheus scrapes another Prometheus `/federate` endpoint | Prometheus pushes samples to a receiver |
| Primary purpose | Hierarchical aggregation, selected series | Centralized durable ingestion/long-term analytics |
| Selection | `match[]` series selectors | write relabeling, backend policy |
| Failure mode | Scrape failure and missing central samples | Queue/retry/backpressure and possible data gaps |
| Cardinality | Limit exported series intentionally | Guard both source and receiver |
| Security | Protect federation endpoint | TLS/auth, least privilege and tenant isolation |

### Federation example

```yaml
scrape_configs:
  - job_name: federation
    honor_labels: true
    metrics_path: /federate
    params:
      match[]:
        - '{job="node"}'
        - '{__name__=~"slo:.*"}'
    static_configs:
      - targets: ["regional-prometheus.internal:9090"]
```

Use `honor_labels` deliberately and review label collisions. A global federation server that scrapes every raw series is rarely an appropriate default. Federation does not provide automatic durable HA deduplication.

## 4. Remote write internals and reliability

Prometheus remote write reads samples from its WAL into shard queues and sends batches to a compatible receiver. Retries and queue buffering are finite; prolonged receiver outage can result in lost samples when the local WAL/retention lifecycle advances. Delivery semantics and receiver-side deduplication are implementation dependent; **do not claim exactly-once**.

Example:

```yaml
remote_write:
  - url: https://metrics-receiver.example.invalid/api/v1/push
    remote_timeout: 30s
    queue_config:
      capacity: 10000
      max_shards: 10
      max_samples_per_send: 2000
      batch_send_deadline: 5s
    write_relabel_configs:
      - source_labels: [job]
        regex: '(node|postgres|elasticsearch)'
        action: keep
```

The endpoint is a placeholder and is not a real deployment target. In production, use supported authentication, TLS trust, receiver quotas, retry and rate-limit design. Queue capacity is **not** equivalent to durable outage buffering duration. WAL retention, queue behavior and the backend determine actual loss risk.

Monitor version-supported metrics such as `prometheus_remote_storage_samples_pending`, `prometheus_remote_storage_failed_samples_total`, `prometheus_remote_storage_retried_samples_total`, `prometheus_remote_storage_highest_timestamp_in_seconds`, `prometheus_remote_storage_queue_highest_sent_timestamp_seconds`, and `prometheus_remote_storage_samples_total`. Exact names can differ by Prometheus version: inspect `/metrics` before deploying rules.

## 5. Long-term storage choices

**Thanos:** Sidecar + object-store blocks, Store Gateway, Compactor and Querier can provide long-term query and deduplication. Object storage, bucket lifecycle and compactor ownership need operational controls.

**Grafana Mimir/Cortex:** Horizontally scalable multi-tenant remote-write ingestion/query, with ingesters, object storage, compaction and tenant quotas. The exact component layout depends on version and deployment mode.

**Managed backends:** Reduce some operations but introduce service quotas, retention/cost models, network egress, tenant IAM and data residency considerations.

Review block durability, object-store consistency, compactor ownership, tenancy, query fanout, downsampling (where supported), series limits, cost and disaster recovery. Do not equate a successful remote-write HTTP response with end-to-end query availability.

## 6. Production SLIs and PromQL

Useful SLIs: scrape coverage, freshness, remote-write lag, query success and latency, alert delivery, HA failover time, backend durability and restore RPO/RTO.

```promql
sum by (instance) (up{job="prometheus"})
```

```promql
sum by (instance, remote_name) (prometheus_remote_storage_samples_pending)
```

```promql
increase(prometheus_remote_storage_failed_samples_total[15m])
```

```promql
time() - prometheus_remote_storage_queue_highest_sent_timestamp_seconds
```

Check metric names and labels against the deployed release; the lag expression needs guarding when a queue has never sent samples. Evaluate freshness against a defined budget and test absence behavior separately. Prometheus internal metrics alone cannot prove end-to-end storage durability.

## 7. Executable offline HA acceptance gate

The lab models redundancy, replica identity, Alertmanager availability, remote-write backlog/failures/freshness, local retention versus backend outage, query SLO and restore drill recency. Thresholds are **illustrative**, not universal production defaults.

Create:

```text
chapter014/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/ha_gate.py
  tests/test_ha_gate.py
```

### fixtures/healthy.json

```json
{
  "environment": "staging",
  "replicas": 2,
  "distinct_failure_domains": 2,
  "external_replica_labels_unique": true,
  "alertmanager_replicas": 3,
  "remote_write_queue_pending": 1200,
  "remote_write_queue_limit": 100000,
  "remote_write_failures_delta": 0,
  "remote_write_lag_seconds": 18,
  "lag_budget_seconds": 120,
  "local_retention_hours": 48,
  "backend_outage_hours": 3,
  "buffer_safety_factor": 2,
  "query_availability_pct": 99.99,
  "query_slo_pct": 99.9,
  "restore_drill_age_days": 12,
  "max_restore_drill_age_days": 90
}
```

### fixtures/degraded.json

```json
{
  "environment": "staging",
  "replicas": 1,
  "distinct_failure_domains": 1,
  "external_replica_labels_unique": false,
  "alertmanager_replicas": 1,
  "remote_write_queue_pending": 99000,
  "remote_write_queue_limit": 100000,
  "remote_write_failures_delta": 45,
  "remote_write_lag_seconds": 900,
  "lag_budget_seconds": 120,
  "local_retention_hours": 2,
  "backend_outage_hours": 4,
  "buffer_safety_factor": 2,
  "query_availability_pct": 97,
  "query_slo_pct": 99.9,
  "restore_drill_age_days": 140,
  "max_restore_drill_age_days": 90
}
```

### scripts/ha_gate.py

```python
#!/usr/bin/env python3
"""Synthetic HA/remote-write design acceptance gate; no network operations."""
import json
import math
import sys
from pathlib import Path

INTEGER = ("replicas", "distinct_failure_domains", "alertmanager_replicas",
           "remote_write_queue_pending", "remote_write_queue_limit",
           "remote_write_failures_delta")
NONNEG = ("remote_write_lag_seconds", "lag_budget_seconds", "local_retention_hours",
          "backend_outage_hours", "buffer_safety_factor", "query_availability_pct",
          "query_slo_pct", "restore_drill_age_days", "max_restore_drill_age_days")

def assess(d):
    errors = []
    if not isinstance(d.get("environment"), str) or not d["environment"].strip():
        errors.append("missing environment")
    if type(d.get("external_replica_labels_unique")) is not bool:
        errors.append("invalid external_replica_labels_unique")
    for k in INTEGER:
        if type(d.get(k)) is not int or d[k] < 0:
            errors.append("invalid " + k)
    for k in NONNEG:
        v = d.get(k)
        if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
            errors.append("invalid " + k)
    if errors:
        return sorted(set(errors))
    for k in ("remote_write_queue_limit", "lag_budget_seconds", "buffer_safety_factor",
              "max_restore_drill_age_days"):
        if d[k] == 0:
            errors.append("invalid positive " + k)
    for k in ("query_availability_pct", "query_slo_pct"):
        if d[k] > 100:
            errors.append("invalid percentage " + k)
    if errors:
        return errors
    if d["replicas"] < 2 or d["distinct_failure_domains"] < 2:
        errors.append("insufficient Prometheus failure-domain redundancy")
    if not d["external_replica_labels_unique"]:
        errors.append("nonunique replica identity")
    if d["alertmanager_replicas"] < 2:
        errors.append("Alertmanager redundancy insufficient")
    if d["remote_write_queue_pending"] >= .8 * d["remote_write_queue_limit"]:
        errors.append("remote-write queue near capacity")
    if d["remote_write_failures_delta"] > 0:
        errors.append("remote-write failures observed")
    if d["remote_write_lag_seconds"] > d["lag_budget_seconds"]:
        errors.append("remote-write freshness budget exceeded")
    if d["local_retention_hours"] < d["backend_outage_hours"] * d["buffer_safety_factor"]:
        errors.append("insufficient local retention for backend outage")
    if d["query_availability_pct"] < d["query_slo_pct"]:
        errors.append("query availability below SLO")
    if d["restore_drill_age_days"] > d["max_restore_drill_age_days"]:
        errors.append("restore drill overdue")
    return errors

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 ha_gate.py fixtures/healthy.json")
    try:
        findings = assess(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError, ValueError) as exc:
        sys.exit(f"input error: {exc}")
    print("HA DESIGN PASS (synthetic)" if not findings else "HA DESIGN FAIL")
    for finding in findings:
        print("-", finding)
    sys.exit(bool(findings))
```

### tests/test_ha_gate.py

```python
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ha_gate import assess

class HADesignTests(unittest.TestCase):
    def fixture(self, name="healthy.json"):
        return json.loads((ROOT / "fixtures" / name).read_text())
    def changed(self, **changes):
        d = self.fixture()
        d.update(changes)
        return assess(d)
    def test_healthy(self): self.assertEqual(assess(self.fixture()), [])
    def test_degraded(self): self.assertTrue(assess(self.fixture("degraded.json")))
    def test_one_replica(self): self.assertTrue(self.changed(replicas=1))
    def test_one_domain(self): self.assertTrue(self.changed(distinct_failure_domains=1))
    def test_duplicate_label(self): self.assertTrue(self.changed(external_replica_labels_unique=False))
    def test_alertmanager(self): self.assertTrue(self.changed(alertmanager_replicas=1))
    def test_queue(self): self.assertTrue(self.changed(remote_write_queue_pending=90000))
    def test_write_failure(self): self.assertTrue(self.changed(remote_write_failures_delta=1))
    def test_lag(self): self.assertTrue(self.changed(remote_write_lag_seconds=500))
    def test_retention(self): self.assertTrue(self.changed(local_retention_hours=2))
    def test_query_slo(self): self.assertTrue(self.changed(query_availability_pct=99))
    def test_restore(self): self.assertTrue(self.changed(restore_drill_age_days=100))
    def test_invalid_limit(self): self.assertTrue(self.changed(remote_write_queue_limit=0))
    def test_invalid_boolean(self): self.assertTrue(self.changed(external_replica_labels_unique="true"))
    def test_nan(self): self.assertTrue(self.changed(remote_write_lag_seconds=float("nan")))
    def test_invalid_percent(self): self.assertTrue(self.changed(query_slo_pct=101))

if __name__ == "__main__":
    unittest.main()
```

### Execute

```bash
cd chapter014
python3 scripts/ha_gate.py fixtures/healthy.json
if python3 scripts/ha_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded HA design was accepted"; exit 1
else
  echo "PASS: degraded HA design rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy passes, degraded fails, 16 tests pass. No live backend, Prometheus or Alertmanager installation is required.

## 8. Twenty-four hands-on exercises

1. Draw two-replica scrape architecture.
2. Identify independent failure domains.
3. Assign unique replica external labels.
4. Explain local TSDB independence.
5. Document duplicate sample handling.
6. Model query failover.
7. Design Alertmanager cluster placement.
8. Test alert deduplication tabletop.
9. Write a bounded federation selector.
10. Explain federation label semantics.
11. Compare federation to remote write.
12. Explain WAL-to-queue pipeline.
13. Model remote-write queue backlog.
14. Define freshness budget.
15. Model backend outage duration.
16. Assess local retention headroom.
17. Select long-term backend.
18. Review multi-tenant quotas.
19. Design RPO/RTO and restore drill.
20. Create healthy fixture.
21. Create degraded fixture.
22. Run positive/negative gate.
23. Run 16 unit tests.
24. Complete enterprise architecture review.

## 9. Twenty production failure scenarios

| # | Failure | Evidence and response |
|---|---|---|
| 01 | Prometheus replica crash | scrape/query failover |
| 02 | Single availability zone lost | domain placement |
| 03 | duplicate replica labels | dedup policy |
| 04 | divergent scrape configs | GitOps drift |
| 05 | target absent in one replica | discovery |
| 06 | Alertmanager peer partition | gossip and delivery |
| 07 | duplicate pages | alert identity |
| 08 | federation overload | selectors/cardinality |
| 09 | federation scrape timeout | network/limits |
| 10 | remote receiver outage | queue/failures |
| 11 | remote-write retry storm | rate limits |
| 12 | remote-write queue saturation | backlog |
| 13 | local WAL ages out | data loss window |
| 14 | long-term store query outage | frontend/store |
| 15 | object-store permission denied | IAM |
| 16 | compactor malfunction | logs/blocks |
| 17 | tenant cardinality explosion | quotas |
| 18 | wrong replica dedup key | backend policy |
| 19 | stale query results | end-to-end freshness |
| 20 | restore fails RTO | drill/backup |

## 10. Eight production runbooks

**A. Prometheus replica failure:** Confirm scrape coverage and independent replica health, shift query traffic through approved path, inspect persistent storage and restore safely.

**B. Alertmanager HA failure:** Check cluster peer health, routing and notification dedup; preserve incident delivery evidence.

**C. Remote-write backlog:** Correlate pending samples, send lag, retries, receiver status, network and WAL age; avoid assuming unlimited buffering.

**D. Remote-write data gap:** Bound missing timestamps, inspect receiver and local WAL, document recoverability and user-facing reporting impact.

**E. Federation failure:** Inspect `/federate` access, selectors, scrape timeout, label collisions and central ingestion.

**F. Long-term storage outage:** Verify object store, ingesters, compactor and query frontend; apply tested failover and tenant isolation.

**G. High cardinality/cost:** Identify series explosion, apply source instrumentation changes and tenant limits, estimate storage/network egress.

**H. Disaster recovery acceptance:** Restore isolated environment, query known samples, compare RPO/RTO, alert routing and HA failover, obtain owner signoff.

## 11. 100-point acceptance

| Area | Points |
|---|---:|
| HA architecture, replica labels, failure domains | 20 |
| Federation and remote-write semantics | 20 |
| Long-term storage and durability design | 20 |
| Executable gate and 16 tests | 20 |
| Incident runbooks, security and evidence | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory gates: independent replicas, unique replica identity, remote-write data-loss caveat, end-to-end freshness plan, degraded-case rejection, 16 tests and documented restore drill.

## 12. Evidence worksheet

```text
UTC / architecture owner / environment:
Replica count / zones / external labels:
Alertmanager peers / notification test:
Federation selector / target inventory:
Remote-write pending / failed / lag:
Local WAL and retention assumptions:
Backend selection / object store / tenant quotas:
Query SLO / restore RPO/RTO:
Positive/negative gate / 16 tests:
RCA / COA / reviewer / acceptance score:
```

**Companion:** [Chapter 014 executable HA lab](labs/014-prometheus-high-availability-federation-remote-write-long-term-storage-lab.md).

**Next:** Chapter 015 — Prometheus Enterprise Deployment, Reliability Testing and Production Readiness Capstone.
