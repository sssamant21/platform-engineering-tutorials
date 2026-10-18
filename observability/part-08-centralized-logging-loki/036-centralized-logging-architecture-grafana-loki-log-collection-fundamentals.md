# Chapter 036 — Centralized Logging Architecture, Grafana Loki and Log Collection Fundamentals

**Part 08 — Centralized Logging with Loki**  
**Audience:** SRE/DBRE, platform engineers, Kubernetes operations and application teams.  
**Prerequisites:** Linux, Docker Compose, Prometheus/Grafana concepts, Python 3.10+.  
**Objective:** Build a Loki logging pipeline, understand stream indexing and LogQL, secure log collection and govern cost, retention and sensitive data.

## 1. Centralized logging architecture

```text
Applications / OS / PostgreSQL / Kubernetes
                   |
            files / stdout / journald
                   |
             Grafana Alloy
       discovery -> process -> write
                   |
              Grafana Loki
         distributor / ingester / storage
                   |
            LogQL -> Grafana
                   |
        on-call / incident correlation
```

Loki indexes **stream labels**, not every word of every log line. This can reduce index overhead compared with full-text systems, but unbounded labels can create enormous stream counts. Use stable labels for service, environment and cluster; keep request IDs, trace IDs and SQL details out of index labels.

## 2. Data model and log quality

| Element | Example | Operational guidance |
|---|---|---|
| Stream labels | `service="orders-api"`, `environment="staging"` | bounded cardinality |
| Timestamp | RFC3339 UTC | preserve event time and clock sync |
| Body | JSON with message/level | redact secrets and PII |
| Parsed fields | `request_id`, `duration_ms` | filter at query time; don't label unbounded IDs |
| Retention | 7 days lab example | match compliance and budget |
| Tenant | separate org/tenant boundary | authenticate and authorize at gateway |

Logs are event records, not substitutes for low-cardinality SLI metrics. Correlate logs with metrics and traces, and use structured logging to support safe troubleshooting.

## 3. Loki deployment patterns

A single-binary filesystem Loki is appropriate for local development, **not** highly available production. Enterprise deployments require durable object storage, authentication/authorization gateway, multi-zone HA, replication, compaction/retention, ingestion limits, backup/DR and upgrade compatibility review. Grafana Alloy is a modern collection agent; avoid designing new production deployments around retired/legacy agents.

## 4. Disposable local Docker Compose lab

### docker-compose.yml

```yaml
services:
  loki:
    image: grafana/loki:3.2.1
    command: ["-config.file=/etc/loki/local-config.yaml"]
    ports: ["127.0.0.1:3100:3100"]
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml:ro
      - loki-data:/loki
    networks: [lab]
  alloy:
    image: grafana/alloy:v1.5.1
    command: ["run","/etc/alloy/config.alloy"]
    volumes:
      - ./config.alloy:/etc/alloy/config.alloy:ro
      - ./logs:/var/log/demo:ro
    depends_on: [loki]
    networks: [lab]
volumes:
  loki-data: {}
networks:
  lab: {}
```

### loki-config.yaml

```yaml
auth_enabled: false
server:
  http_listen_port: 3100
common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory
schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
limits_config:
  allow_structured_metadata: true
```

### config.alloy

```hcl
local.file_match "demo" {
  path_targets = [{"__path__" = "/var/log/demo/*.log", "service" = "orders-api", "environment" = "staging", "cluster" = "lab"}]
}
loki.source.file "demo" {
  targets = local.file_match.demo.targets
  forward_to = [loki.write.local.receiver]
}
loki.write "local" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
  }
}
```

### Generate a synthetic log

```bash
mkdir -p logs
printf '{"level":"info","message":"synthetic order processed","request_id":"req-001","duration_ms":42}\n' > logs/app.log
docker compose config
docker compose up -d
curl -fsS http://127.0.0.1:3100/ready
docker compose logs --tail=100 alloy
curl -fsSG --data-urlencode 'query={service="orders-api"}' --data-urlencode 'limit=20' http://127.0.0.1:3100/loki/api/v1/query_range
docker compose down
```

The image versions are teaching examples; verify currently supported versions and security updates before deployment. The lab disables Loki authentication and binds its port to localhost only. Never expose this configuration publicly.

## 5. LogQL essentials

```logql
{service="orders-api"}
{service="orders-api"} |= "synthetic"
{service="orders-api"} | json | level="info"
sum by (service) (count_over_time({service="orders-api"}[5m]))
sum by (service) (rate({service="orders-api"}[5m]))
```

Use bounded time ranges and narrow stream selectors. Query-time JSON parsing does not imply JSON fields are indexed as stream labels. For high-volume workloads, estimate scanned bytes and query cost.

## 6. Security, privacy, retention and FinOps

Redact credentials, tokens, passwords, personal data and sensitive SQL values **before** ingestion. Enforce multi-tenancy and access control outside unauthenticated lab configurations. Define retention and deletion processes according to policy. Monitor ingestion throughput, stream cardinality, dropped entries, push errors, storage growth and query latency.

## 7. Executable offline logging governance lab

The following JSON is synthetic governance metadata, not a Loki or Alloy config. The Python gate validates labels, pipeline stage declarations, redaction attestations, retention and ingestion budgets. It does not read actual log contents or prove redaction.

Create:

```text
chapter036/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/log_gate.py
  tests/test_log_gate.py
```

### fixtures/healthy.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "tenant": "lab",
  "source": "api",
  "labels": {
    "service": "orders-api",
    "environment": "staging",
    "cluster": "lab"
  },
  "max_streams": 200,
  "estimated_streams": 12,
  "retention_days": 7,
  "retention_approved": true,
  "pii_redaction_reviewed": true,
  "secret_redaction_reviewed": true,
  "rbac_reviewed": true,
  "ingestion_budget_mb_day": 250,
  "estimated_ingestion_mb_day": 80,
  "rollback_tested": true,
  "runbook": "https://example.org/runbooks/loki",
  "pipeline_stages": [
    "json",
    "labels",
    "drop_sensitive"
  ],
  "structured_fields": [
    "level",
    "message",
    "request_id"
  ],
  "index_request_id": false
}
```

### fixtures/degraded.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "tenant": "lab",
  "source": "api",
  "labels": {
    "service": "orders-api",
    "environment": "staging",
    "cluster": "lab",
    "request_id": "abc123"
  },
  "max_streams": 200,
  "estimated_streams": 500,
  "retention_days": 7,
  "retention_approved": true,
  "pii_redaction_reviewed": false,
  "secret_redaction_reviewed": true,
  "rbac_reviewed": true,
  "ingestion_budget_mb_day": 250,
  "estimated_ingestion_mb_day": 400,
  "rollback_tested": true,
  "runbook": "https://example.org/runbooks/loki",
  "pipeline_stages": [
    "json",
    "labels",
    "drop_sensitive"
  ],
  "structured_fields": [
    "level",
    "message",
    "request_id"
  ],
  "index_request_id": true
}
```

### scripts/log_gate.py

```python
#!/usr/bin/env python3
"""Offline Loki log-contract governance, not a running Loki validation."""
import json,sys
from pathlib import Path
LABELS={"service","environment","cluster","region","namespace","team","severity"}
FIELDS={"level","message","request_id","trace_id","duration_ms","status"}
STAGES={"json","labels","drop_sensitive","timestamp","static_labels"}
def validate(p):
    e=[]
    if not isinstance(p,dict): return ["manifest must be object"]
    for k in ("owner","environment","tenant","source","runbook"):
        if not isinstance(p.get(k),str) or not p[k]: e.append("missing "+k)
    for k in ("retention_approved","pii_redaction_reviewed","secret_redaction_reviewed","rbac_reviewed","rollback_tested"):
        if p.get(k) is not True: e.append("unverified "+k)
    labels=p.get("labels")
    if not isinstance(labels,dict) or not {"service","environment","cluster"}.issubset(labels) or not set(labels).issubset(LABELS) or any(not isinstance(v,str) or not v for v in labels.values()): e.append("unsafe stream labels")
    stages=p.get("pipeline_stages")
    if not isinstance(stages,list) or not {"json","labels","drop_sensitive"}.issubset(stages) or not set(stages).issubset(STAGES): e.append("unsafe pipeline")
    fields=p.get("structured_fields")
    if not isinstance(fields,list) or not {"level","message"}.issubset(fields) or not set(fields).issubset(FIELDS): e.append("unsafe structured fields")
    if p.get("index_request_id") is not False: e.append("request ID must not be index label")
    for k in ("max_streams","estimated_streams","retention_days","ingestion_budget_mb_day","estimated_ingestion_mb_day"):
        if type(p.get(k)) is not int or p[k]<0: e.append("invalid "+k)
    maximum=p.get("max_streams");streams=p.get("estimated_streams")
    if type(maximum) is int and type(streams) is int and streams>maximum: e.append("stream budget exceeded")
    budget=p.get("ingestion_budget_mb_day");estimate=p.get("estimated_ingestion_mb_day")
    if type(budget) is int and type(estimate) is int and estimate>budget: e.append("ingestion budget exceeded")
    if p.get("retention_days") not in range(1,91): e.append("retention outside lab policy")
    return e
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 log_gate.py fixtures/healthy.json")
    try: findings=validate(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as exc: sys.exit(str(exc))
    print(json.dumps({"status":"FAIL" if findings else "PASS","findings":findings},indent=2))
    sys.exit(bool(findings))
```

### tests/test_log_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from log_gate import validate
class LogContractTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def bad(self,change):
        p=copy.deepcopy(self.p);exec(change,{},{"p":p});self.assertTrue(validate(p))
    def test_healthy(self): self.assertEqual(validate(self.p),[])
    def test_degraded(self): self.assertTrue(validate(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_non_object(self): self.assertTrue(validate(None))
    def test_01_owner(self): self.bad("p[\"owner\"]=\"\"")
    def test_02_tenant(self): self.bad("p[\"tenant\"]=\"\"")
    def test_03_retention_review(self): self.bad("p[\"retention_approved\"]=False")
    def test_04_pii(self): self.bad("p[\"pii_redaction_reviewed\"]=False")
    def test_05_secrets(self): self.bad("p[\"secret_redaction_reviewed\"]=False")
    def test_06_rbac(self): self.bad("p[\"rbac_reviewed\"]=False")
    def test_07_rollback(self): self.bad("p[\"rollback_tested\"]=False")
    def test_08_labels(self): self.bad("p[\"labels\"][\"request_id\"]=\"abc\"")
    def test_09_missing_labels(self): self.bad("p[\"labels\"]={\"service\":\"api\"}")
    def test_10_bad_label_value(self): self.bad("p[\"labels\"][\"service\"]=\"\"")
    def test_11_stages(self): self.bad("p[\"pipeline_stages\"]=[\"json\"]")
    def test_12_bad_stage(self): self.bad("p[\"pipeline_stages\"].append(\"exec\")")
    def test_13_fields(self): self.bad("p[\"structured_fields\"]=[\"level\"]")
    def test_14_bad_field(self): self.bad("p[\"structured_fields\"].append(\"password\")")
    def test_15_request_id(self): self.bad("p[\"index_request_id\"]=True")
    def test_16_max_streams(self): self.bad("p[\"max_streams\"]=-1")
    def test_17_streams(self): self.bad("p[\"estimated_streams\"]=500")
    def test_18_retention_zero(self): self.bad("p[\"retention_days\"]=0")
    def test_19_retention_high(self): self.bad("p[\"retention_days\"]=100")
    def test_20_ingest_budget(self): self.bad("p[\"ingestion_budget_mb_day\"]=-1")
    def test_21_ingest_over(self): self.bad("p[\"estimated_ingestion_mb_day\"]=900")
    def test_22_runbook(self): self.bad("p[\"runbook\"]=\"\"")
    def test_23_source(self): self.bad("p[\"source\"]=\"\"")
    def test_24_environment(self): self.bad("p[\"environment\"]=\"\"")
if __name__=="__main__": unittest.main()
```

### Run

```bash
cd chapter036
python3 scripts/log_gate.py fixtures/healthy.json
if python3 scripts/log_gate.py fixtures/degraded.json; then
  echo "FAIL: unsafe log contract accepted"; exit 1
else
  echo "PASS: unsafe contract rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL, **27 authored tests** pass.

## 8. Twenty-four hands-on exercises

1. Diagram Loki components.
2. Distinguish labels from log body.
3. Plan tenant isolation.
4. Start local Loki.
5. Start Alloy file source.
6. Write JSON sample log.
7. Verify Loki readiness.
8. Inspect Alloy logs.
9. Query LogQL selector.
10. Filter error text.
11. Parse JSON fields.
12. Aggregate count_over_time.
13. Aggregate rate of logs.
14. Review log timestamp semantics.
15. Review out-of-order entries.
16. Review chunk and index storage.
17. Review stream cardinality.
18. Review retention.
19. Review ingestion budgets.
20. Review secret redaction.
21. Review PII redaction.
22. Run healthy governance gate.
23. Reject degraded fixture.
24. Run 27 tests and rollback.

## 9. Twenty-four production failure scenarios

| # | Failure | First diagnostic |
|---|---|---|
| 1 | Loki readiness fails | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 2 | Alloy cannot read file | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 3 | Loki push returns 429 | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 4 | Wrong push URL | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 5 | Log timestamp invalid | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 6 | Log line too large | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 7 | Stream cardinality explosion | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 8 | Request ID indexed as label | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 9 | Secret leaked in log | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 10 | PII leaked in log | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 11 | JSON parsing fails | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 12 | LogQL query empty | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 13 | Out-of-order logs | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 14 | Duplicate logs | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 15 | High ingestion cost | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 16 | Retention misconfigured | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 17 | Disk full | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 18 | Loki ring unhealthy | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 19 | Alloy restarts | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 20 | Missing log source | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 21 | Noisy debug logs | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 22 | Alert misses logs | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 23 | RBAC bypass | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |
| 24 | Rollback fails | Inspect Alloy source, Loki readiness, labels, timestamps, storage and policy |

## 10. Eight production runbooks

1. Ingestion stopped: inspect Alloy source, permissions, write endpoint and Loki readiness.
2. High cardinality: inspect stream labels and remove request IDs or other unbounded dimensions.
3. Sensitive log leak: stop ingestion, revoke access, coordinate retention/deletion and rotate secrets.
4. Query returns no data: verify time range, stream labels, parsing and source timestamps.
5. Loki storage pressure: inspect ingestion, retention, disk, chunks and backpressure.
6. Out-of-order or duplicate logs: review timestamps, file offsets, restarts and retry semantics.
7. Tenant/RBAC incident: restrict endpoints, audit tenant boundaries and credentials.
8. Rollback: revert collector pipeline, confirm ingestion and query results, document evidence.

## 11. SRE/DBRE incident simulation

PostgreSQL queries slow down after a storage I/O event. Application logs contain correlation IDs, but an engineer added `request_id` as a Loki stream label. Ingestion begins failing due to high cardinality and the incident dashboard appears empty. Remove unbounded labels, preserve IDs in JSON, validate Alloy offsets and query logs by service/time. Correlate with Node Exporter disk signals and PostgreSQL query metrics.

## 12. 100-point assessment

| Domain | Points |
|---|---:|
| Loki architecture and log model | 20 |
| Local collection and LogQL | 20 |
| Security, redaction and retention | 20 |
| Offline governance and 27 tests | 20 |
| Incident drills and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Mandatory: safe stream labels, redaction controls, tenant access, retention approval, collector rollback and log-query evidence.

## 13. Evidence worksheet

```text
UTC / owner / environment:
Loki / Alloy versions:
Log source / labels / sample synthetic event:
Ready / push / query verification:
Stream cardinality / retention / ingest budget:
PII / secrets / RBAC review:
Healthy/degraded gate / 27 tests:
Incident drill / rollback / reviewer / score:
```

**Companion:** [Chapter 036 Loki log collection lab](labs/036-centralized-logging-architecture-grafana-loki-log-collection-fundamentals-lab.md).

**Next:** Chapter 037 — Grafana Alloy Log Pipelines, Parsing, Labeling and Kubernetes Collection.
