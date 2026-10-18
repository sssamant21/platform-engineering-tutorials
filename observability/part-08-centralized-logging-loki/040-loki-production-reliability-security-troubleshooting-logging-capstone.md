# Chapter 040 — Loki Production Reliability, Security, Troubleshooting and Logging Capstone

**Part 08 — Centralized Logging with Loki: FINAL CAPSTONE**  
**Audience:** SRE/DBRE, on-call, platform engineering, security and compliance.  
**Prerequisites:** Chapters 036–039; Linux, Kubernetes, Prometheus, Alertmanager, LogQL and Python 3.10+.

## 1. Capstone mission

Design, review and rehearse an enterprise logging platform integrating **Grafana Alloy, Grafana Loki, LogQL, ruler/Alertmanager, retention/compactor, security controls and incident response**. Establish measurable ingest/query reliability, tenant isolation, cardinality budgets, deletion governance and restore/rollback evidence.

## 2. Production architecture

```text
Kubernetes / Linux / PostgreSQL / applications
                    |
              Grafana Alloy
          discovery / parse / redact
                    |
             secure tenant gateway
                    |
      +--------- Loki HA ingestion ----------+
      |                                      |
  distributors -> ingesters -> object storage/TSDB
      |                                      |
  query frontend -> queriers             compactor
      |                                      |
  Grafana / LogQL                      retention review
      |
  ruler -> Alertmanager -> test receiver / on-call
      |
  independent health monitoring outside Loki
```

This architecture is conceptual, not a ready-to-deploy Helm chart. Production requires supported chart versions, tested credentials, TLS, tenancy, multi-zone deployment, object storage and explicit sizing.

## 3. Production reliability and data correctness

| Signal | Objective | Verification |
|---|---|---|
| Log collection completeness | no silent missing sources | expected source inventory and synthetic heartbeat |
| Ingestion availability | accepted pushes and bounded drops | Alloy/Loki metrics and independent probes |
| Query latency | bounded LogQL execution | p95/p99 and query timeout tests |
| Alert delivery | synthetic route received | Alertmanager acknowledgement and fallback |
| Retention | approved data lifecycle | compactor status and actual object age |
| Restore | recover usable logs/config | disposable recovery drill and measured RPO/RTO |

An empty LogQL result does not mean an application is healthy. Log-based metrics can be biased by dropped, sampled or duplicated logs; corroborate user-impact SLIs with independent application metrics.

## 4. Security, privacy and governance

- Authenticate tenant boundaries and enforce least privilege at the gateway, collector and storage layers.
- Encrypt transport and restrict egress; prevent unapproved access to Loki query endpoints.
- Redact secrets and sensitive personal information **before ingestion**, then test representative payloads.
- Keep request IDs, trace IDs, pod UIDs, SQL text and other volatile dimensions out of stream labels.
- Require reviewed retention, legal-hold/deletion controls, backup encryption and incident audit evidence.
- Use only synthetic logs for labs. Do not run destructive retention drills against production.

## 5. SRE/DBRE incident game day

A PostgreSQL-backed Kubernetes service slows after node storage contention. Application logs are missing because Alloy lost node log access. A hurried fix introduces `request_id` as a Loki label, increasing streams and producing 429 push failures. Simultaneously, a ruler alert fails to deliver and the compactor is unhealthy.

**Response:** establish actual user impact from Prometheus/DB metrics; diagnose node log access and Alloy offsets; restore stable labels; verify Loki push/query; test-only Alertmanager route; inspect compactor and approved retention; recover from a disposable backup; document incident timeline, customer impact, costs, RPO/RTO and rollback evidence.

## 6. Executable offline acceptance lab

The following manifest is **synthetic review metadata**, not native Loki configuration. The gate validates declared governance controls; boolean attestations do not prove that live redaction, delivery or restoration occurred.

### healthy.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "tenant": "lab",
  "collection_sources": [
    "kubernetes",
    "postgresql",
    "application"
  ],
  "stable_labels": [
    "cluster",
    "namespace",
    "service",
    "environment"
  ],
  "retention_days": 7,
  "retention_approved": true,
  "tenant_isolation_reviewed": true,
  "redaction_tested": true,
  "ingestion_slo_reviewed": true,
  "query_slo_reviewed": true,
  "alert_delivery_tested": true,
  "independent_monitoring_reviewed": true,
  "rollback_tested": true,
  "restore_tested": true,
  "incident_drill_completed": true,
  "estimated_streams": 120,
  "stream_budget": 500,
  "estimated_ingestion_gb_day": 2,
  "ingestion_budget_gb_day": 5,
  "runbook": "https://example.org/runbooks/loki",
  "change_id": "OBS-040"
}
```

### acceptance.py

```python
"""Offline acceptance of declared Loki capstone controls; not live integration evidence."""
import json,sys
from pathlib import Path
REQUIRED={"cluster","namespace","service","environment"}
ALLOWED=REQUIRED|{"region","team","severity"}
def validate(p):
    errors=[]
    if not isinstance(p,dict):return ["manifest must be object"]
    for key in ("owner","environment","tenant","runbook","change_id"):
        if not isinstance(p.get(key),str) or not p[key]:errors.append("missing "+key)
    sources=p.get("collection_sources")
    if not isinstance(sources,list) or not {"kubernetes","postgresql","application"}.issubset(sources):errors.append("missing sources")
    labels=p.get("stable_labels")
    if not isinstance(labels,list) or not REQUIRED.issubset(labels) or not set(labels).issubset(ALLOWED):errors.append("unsafe labels")
    for key in ("retention_approved","tenant_isolation_reviewed","redaction_tested","ingestion_slo_reviewed","query_slo_reviewed","alert_delivery_tested","independent_monitoring_reviewed","rollback_tested","restore_tested","incident_drill_completed"):
        if p.get(key) is not True:errors.append("unverified "+key)
    days=p.get("retention_days")
    if type(days) is not int or not 1<=days<=90:errors.append("invalid retention")
    for estimated,budget in (("estimated_streams","stream_budget"),("estimated_ingestion_gb_day","ingestion_budget_gb_day")):
        x=p.get(estimated);y=p.get(budget)
        if type(x) is not int or type(y) is not int or x<0 or y<=0 or x>y:errors.append("budget exceeded/invalid "+estimated)
    return errors
if __name__=="__main__":
    findings=validate(json.loads(Path(sys.argv[1]).read_text()))
    print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
    sys.exit(bool(findings))

```

### test_acceptance.py

```python
import copy,json,unittest
from pathlib import Path
from acceptance import validate
class CapstoneTests(unittest.TestCase):
    def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
    def test_healthy(self):self.assertEqual(validate(self.p),[])
    def test_not_object(self):self.assertTrue(validate(None))
    def test_01_owner(self):
        p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
    def test_02_environment(self):
        p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
    def test_03_tenant(self):
        p=copy.deepcopy(self.p);p["tenant"]="";self.assertTrue(validate(p))
    def test_04_runbook(self):
        p=copy.deepcopy(self.p);p["runbook"]="";self.assertTrue(validate(p))
    def test_05_change_id(self):
        p=copy.deepcopy(self.p);p["change_id"]="";self.assertTrue(validate(p))
    def test_06_collection_sources(self):
        p=copy.deepcopy(self.p);p["collection_sources"]=[];self.assertTrue(validate(p))
    def test_07_stable_labels(self):
        p=copy.deepcopy(self.p);p["stable_labels"]=["service"];self.assertTrue(validate(p))
    def test_08_stable_labels(self):
        p=copy.deepcopy(self.p);p["stable_labels"]=["cluster","namespace","service","environment","request_id"];self.assertTrue(validate(p))
    def test_09_retention_days(self):
        p=copy.deepcopy(self.p);p["retention_days"]=0;self.assertTrue(validate(p))
    def test_10_retention_days(self):
        p=copy.deepcopy(self.p);p["retention_days"]=100;self.assertTrue(validate(p))
    def test_11_retention_approved(self):
        p=copy.deepcopy(self.p);p["retention_approved"]=False;self.assertTrue(validate(p))
    def test_12_tenant_isolation_reviewed(self):
        p=copy.deepcopy(self.p);p["tenant_isolation_reviewed"]=False;self.assertTrue(validate(p))
    def test_13_redaction_tested(self):
        p=copy.deepcopy(self.p);p["redaction_tested"]=False;self.assertTrue(validate(p))
    def test_14_ingestion_slo_reviewed(self):
        p=copy.deepcopy(self.p);p["ingestion_slo_reviewed"]=False;self.assertTrue(validate(p))
    def test_15_query_slo_reviewed(self):
        p=copy.deepcopy(self.p);p["query_slo_reviewed"]=False;self.assertTrue(validate(p))
    def test_16_alert_delivery_tested(self):
        p=copy.deepcopy(self.p);p["alert_delivery_tested"]=False;self.assertTrue(validate(p))
    def test_17_independent_monitoring_reviewed(self):
        p=copy.deepcopy(self.p);p["independent_monitoring_reviewed"]=False;self.assertTrue(validate(p))
    def test_18_rollback_tested(self):
        p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
    def test_19_restore_tested(self):
        p=copy.deepcopy(self.p);p["restore_tested"]=False;self.assertTrue(validate(p))
    def test_20_incident_drill_completed(self):
        p=copy.deepcopy(self.p);p["incident_drill_completed"]=False;self.assertTrue(validate(p))
    def test_21_estimated_streams(self):
        p=copy.deepcopy(self.p);p["estimated_streams"]=900;self.assertTrue(validate(p))
    def test_22_stream_budget(self):
        p=copy.deepcopy(self.p);p["stream_budget"]=0;self.assertTrue(validate(p))
    def test_23_estimated_ingestion_gb_day(self):
        p=copy.deepcopy(self.p);p["estimated_ingestion_gb_day"]=900;self.assertTrue(validate(p))
    def test_24_ingestion_budget_gb_day(self):
        p=copy.deepcopy(self.p);p["ingestion_budget_gb_day"]=0;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

### Run

```bash
mkdir -p chapter040 && cd chapter040
# Save the three blocks above as healthy.json, acceptance.py and test_acceptance.py
python3 acceptance.py healthy.json
python3 -m unittest -v test_acceptance.py
```

Expected: healthy PASS and **26 authored unit tests** pass.

## 7. Twenty-four practical exercises

1. Build service and log-source inventory.
2. Verify node and pod collection design.
3. Review Alloy source pipeline.
4. Verify PostgreSQL log contract.
5. Verify application JSON contract.
6. Enforce stable stream labels.
7. Review request/trace IDs as fields.
8. Set tenant authentication boundary.
9. Review TLS and network policy.
10. Test synthetic redaction.
11. Validate Loki ingestion.
12. Validate bounded LogQL.
13. Validate log-based metric caveats.
14. Review ruler alert.
15. Test synthetic Alertmanager route.
16. Verify independent Loki health alert.
17. Inspect compactor health.
18. Verify retention in disposable store.
19. Estimate ingestion budget.
20. Estimate stream budget.
21. Simulate collector outage.
22. Simulate Loki query degradation.
23. Run offline acceptance tests.
24. Document rollback and DR evidence.

## 8. Twenty-four production failure scenarios

1. **Alloy source inaccessible:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
2. **Node rotation loses logs:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
3. **Pod discovery permissions denied:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
4. **Pipeline parsing regression:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
5. **PII enters logs:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
6. **Credential leaked:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
7. **Loki tenant header missing:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
8. **Loki push 429:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
9. **Loki push 500:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
10. **Object store latency:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
11. **Ingester unavailable:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
12. **Query frontend overloaded:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
13. **Querier OOM:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
14. **Ruler evaluation failure:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
15. **Alertmanager route fails:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
16. **Independent pipeline alert absent:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
17. **Compactor unhealthy:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
18. **Retention not enforced:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
19. **Unexpected early deletion:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
20. **Cardinality explosion:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
21. **Debug log flood:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
22. **Log timestamps skewed:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
23. **Duplicate log ingestion:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.
24. **Restore fails:** inspect collector, tenant gateway, Loki ingest/query/ruler, retention, independent metrics and recovery evidence.

## 9. Eight production runbooks

1. **Collection outage:** check Alloy discovery, node file access, offsets and Loki push status; compare expected source inventory.
2. **Ingestion throttling:** inspect tenant 429s, ingest volume, retries and stream count; fix labels before increasing limits.
3. **Query outage:** narrow LogQL selectors, inspect query frontend, querier, cache, object storage and time range.
4. **Ruler/alert failure:** validate query result, ruler evaluation, Alertmanager routing, receiver acknowledgement and backup route.
5. **Sensitive data incident:** stop unsafe ingestion, restrict access, rotate affected credentials and coordinate approved retention/deletion.
6. **Compactor/retention failure:** verify compactor health, storage backend, legal hold and age of retained objects; avoid destructive production tests.
7. **Cardinality emergency:** remove volatile labels, roll back collector schema and confirm stream budget recovery.
8. **DR and rollback:** restore approved configs and disposable backup, confirm ingestion/query/rules and record RPO/RTO.

## 10. 100-point enterprise logging acceptance

| Area | Points |
|---|---:|
| End-to-end logging architecture and correctness | 20 |
| SLOs, alerting and reliability engineering | 20 |
| Security, privacy, retention and FinOps | 20 |
| Offline acceptance and 26 tests | 20 |
| Incident response, restore and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Mandatory: tenant isolation, actual redaction validation, bounded labels, independent health monitoring, tested alert delivery, approved retention and restore evidence. Offline acceptance alone is **not** production certification.

## 11. Evidence worksheet

```text
UTC / owner / change ID / environment:
Alloy / Loki / Alertmanager versions:
Sources / tenant gateway / stable labels:
Ingestion and query SLOs / independent probes:
Redaction and RBAC / privacy review:
Stream and ingestion budgets / compactor retention:
Synthetic alert route / backup / restore / RPO / RTO:
Offline acceptance / 26 tests:
Game day / rollback / reviewer / 100-point score:
```

**Companion:** [Chapter 040 enterprise logging capstone lab](labs/040-loki-production-reliability-security-troubleshooting-logging-capstone-lab.md).

**Part 08 complete. Next:** Chapter 041 — Elasticsearch and OpenSearch Logging Architecture, Index Design and Ingestion Foundations (Part 09).
