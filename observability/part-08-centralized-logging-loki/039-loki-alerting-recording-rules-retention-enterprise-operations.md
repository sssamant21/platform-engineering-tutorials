# Chapter 039 — Loki Alerting, Recording Rules, Retention and Enterprise Operations

**Part 08 — Centralized Logging with Loki**  
**Audience:** SRE/DBRE, observability platform teams, on-call engineers.  
**Prerequisites:** Chapters 026–030 and 036–038, Loki 3.x, LogQL, Alertmanager.

## 1. Operational architecture

```text
Alloy -> Loki ingesters / TSDB -> ruler (LogQL) -> Alertmanager -> on-call
                       |             |
                  compactor       recording rules
                       |
              object storage / retention
```

Loki's ruler evaluates LogQL expressions and sends alert notifications to Alertmanager. Recording rules can precompute expensive log-based aggregations. These signals reflect **observed logs**, not guaranteed user requests: drops, sampling, duplicate entries, or collector outages can invalidate an apparent error rate. Independently monitor the logging pipeline and application SLIs.

## 2. Rule semantics and alert engineering

For a service with structured JSON logs:

```logql
sum by (service) (rate({service="orders-api"} | json | level="error" [5m]))
sum by (service) (count_over_time({service="orders-api"} | json | level="error" [10m]))
```

Avoid regex-only broad selectors, expensive scans, unbounded labels and page-worthy alerts based solely on log text. Use `for` to damp transient spikes, explicit owner/severity/runbook labels, safe routing and independent missing-log alerts.

### Example ruler rules

```yaml
groups:
  - name: orders-api-logging
    interval: 1m
    rules:
      - record: orders_api:log_errors_per_second:rate5m
        expr: sum(rate({service="orders-api"} | json | level="error" [5m]))
      - alert: OrdersAPILogErrorBurst
        expr: orders_api:log_errors_per_second:rate5m > 0.1
        for: 10m
        labels:
          severity: warning
          team: platform-sre
        annotations:
          summary: "Sustained orders-api error logs"
          description: "Validate log completeness and compare to application request error metrics."
          runbook_url: "https://example.org/runbooks/loki-log-errors"
```

The threshold is illustrative; derive it from measured baseline and service objectives. Test rules using supported tooling and a staging ruler/Alertmanager integration. Recording rule storage and ruler backend configuration are deployment-specific.

## 3. Loki retention and deletion architecture

For TSDB schema v13, retention is enforced by the **compactor**, subject to correct deployment configuration and object-store behavior. A configuration declaration alone does not prove old log data was deleted. Verify compactor health, retention windows, deletion delays, object lifecycle, legal hold, backups and compliance requirements. Deletion is irreversible and should require change approval.

### Illustrative retention configuration

```yaml
compactor:
  working_directory: /loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  delete_request_store: filesystem
limits_config:
  retention_period: 168h
```

This fragment must be integrated with a compatible Loki deployment and storage backend; it is **not** a complete production configuration. Use durable object storage and review current Loki version-specific retention requirements. Never test destructive retention changes against production logs.

## 4. Enterprise operations checklist

| Domain | Operational evidence |
|---|---|
| Ingestion | accepted/rejected log rate, push errors, tenant limits |
| Query | latency, bytes scanned, frontend/querier saturation |
| Ruler | evaluations, failures, alert delivery |
| Retention | compactor health, actual age of stored data |
| Security | authenticated tenant boundary, TLS, RBAC |
| Reliability | multi-zone architecture, object storage, backups, restore |
| FinOps | GB/day, streams, retention, query costs |
| Change | staged rule test, reviewer, rollback |

Alertmanager routing, silences, inhibition and notification testing from Part 06 remain applicable. Preserve a separate monitoring path for Loki/Alloy failure so a broken logging stack cannot silently suppress its own alerts.

## 5. Executable offline rule-and-retention governance lab

The JSON manifest is **synthetic review metadata**, not a native Loki config. It verifies basic alert/retention approval gates and budgets; it does not prove retention deletion, real rule execution or notification delivery.

Create `chapter039/policy.json`:

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "retention_days": 7,
  "retention_approved": true,
  "compactor_reviewed": true,
  "deletion_safety_reviewed": true,
  "alert_route_reviewed": true,
  "synthetic_notification_tested": true,
  "rollback_tested": true,
  "independent_pipeline_alert": true,
  "max_rule_range_minutes": 30,
  "rules": [
    {"name": "OrdersAPILogErrorBurst", "service": "orders-api", "severity": "warning", "for_minutes": 10, "query_range_minutes": 5, "runbook": "https://example.org/runbooks/loki"}
  ]
}
```

Create `chapter039/policy_gate.py`:

```python
import json,sys
from pathlib import Path

def validate(p):
    errors=[]
    if not isinstance(p,dict):return ["manifest must be object"]
    if not p.get("owner") or not p.get("environment"):errors.append("missing ownership")
    for k in ("retention_approved","compactor_reviewed","deletion_safety_reviewed","alert_route_reviewed","synthetic_notification_tested","rollback_tested","independent_pipeline_alert"):
        if p.get(k) is not True:errors.append("missing gate "+k)
    days=p.get("retention_days")
    if type(days) is not int or not 1<=days<=90:errors.append("invalid retention")
    maximum=p.get("max_rule_range_minutes")
    if type(maximum) is not int or not 1<=maximum<=60:errors.append("invalid query budget")
    rules=p.get("rules")
    if not isinstance(rules,list) or not rules:return errors+["rules required"]
    names=set()
    for rule in rules:
        if not isinstance(rule,dict):errors.append("invalid rule");continue
        name=rule.get("name")
        if not isinstance(name,str) or not name or name in names:errors.append("duplicate/invalid rule name")
        else:names.add(name)
        if rule.get("severity") not in ("warning","critical"):errors.append("invalid severity")
        if not rule.get("service") or not rule.get("runbook"):errors.append("missing service/runbook")
        wait=rule.get("for_minutes");span=rule.get("query_range_minutes")
        if type(wait) is not int or wait<1:errors.append("invalid for")
        if type(span) is not int or type(maximum) is not int or not 0<span<=maximum:errors.append("invalid query range")
    return errors

if __name__=="__main__":
    findings=validate(json.loads(Path(sys.argv[1]).read_text()))
    print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
    sys.exit(bool(findings))
```

Create `chapter039/test_policy_gate.py`:

```python
import copy,json,unittest
from pathlib import Path
from policy_gate import validate
class PolicyTests(unittest.TestCase):
    def setUp(self):self.p=json.loads(Path(__file__).with_name("policy.json").read_text())
    def reject(self,key,value):
        p=copy.deepcopy(self.p);p[key]=value;self.assertTrue(validate(p))
    def test_healthy(self):self.assertEqual(validate(self.p),[])
    def test_invalid_manifest(self):self.assertTrue(validate(None))
    def test_owner(self):self.reject("owner","")
    def test_retention_review(self):self.reject("retention_approved",False)
    def test_compactor(self):self.reject("compactor_reviewed",False)
    def test_deletion_review(self):self.reject("deletion_safety_reviewed",False)
    def test_alert_route(self):self.reject("alert_route_reviewed",False)
    def test_notification(self):self.reject("synthetic_notification_tested",False)
    def test_rollback(self):self.reject("rollback_tested",False)
    def test_independent_alert(self):self.reject("independent_pipeline_alert",False)
    def test_retention_zero(self):self.reject("retention_days",0)
    def test_retention_high(self):self.reject("retention_days",365)
    def test_range_budget(self):self.reject("max_rule_range_minutes",0)
    def test_missing_rules(self):self.reject("rules",[])
    def test_bad_severity(self):
        self.p["rules"][0]["severity"]="page-everyone";self.assertTrue(validate(self.p))
    def test_bad_query_range(self):
        self.p["rules"][0]["query_range_minutes"]=999;self.assertTrue(validate(self.p))
    def test_bad_for(self):
        self.p["rules"][0]["for_minutes"]=0;self.assertTrue(validate(self.p))
    def test_no_runbook(self):
        self.p["rules"][0]["runbook"]="";self.assertTrue(validate(self.p))
if __name__=="__main__":unittest.main()
```

Run:

```bash
cd chapter039
python3 policy_gate.py policy.json
python3 -m unittest -v test_policy_gate.py
```

Expected: PASS and **18 authored unit tests**.

## 6. Twenty-four hands-on exercises

1. Inventory log streams.
2. Review application SLIs.
3. Build LogQL error rate.
4. Build count_over_time query.
5. Create ruler recording rule.
6. Create ruler alert rule.
7. Set severity.
8. Set owner.
9. Set runbook.
10. Tune for duration.
11. Review baseline threshold.
12. Validate parser errors.
13. Validate rule configuration.
14. Test staging ruler.
15. Test Alertmanager route.
16. Test backup receiver.
17. Design independent pipeline alert.
18. Review compactor.
19. Review retention period.
20. Review deletion safety.
21. Estimate storage cost.
22. Simulate ingestion outage.
23. Run offline governance tests.
24. Document rollback and evidence.

## 7. Twenty-four failure scenarios

1. **Ruler unavailable:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
2. **Rule parse error:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
3. **Rule evaluation timeout:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
4. **Query too broad:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
5. **Parser errors:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
6. **Alert not routed:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
7. **Notification fails:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
8. **No backup receiver:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
9. **Silence masks alert:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
10. **Ingestion stops:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
11. **Missing log stream:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
12. **Duplicated logs:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
13. **Log-based SLI misleading:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
14. **Compactor unhealthy:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
15. **Retention not applied:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
16. **Unexpected early deletion:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
17. **Object storage unavailable:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
18. **Tenant limit exceeded:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
19. **High-cardinality labels:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
20. **Query frontend overloaded:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
21. **Disk pressure:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
22. **Incorrect severity:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
23. **Runbook missing:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.
24. **Rollback fails:** check ruler, ingestion, tenant limits, compactor, Alertmanager and change history.

## 8. Eight production runbooks

1. **Ruler failure:** inspect evaluation errors, query health, rule configuration and tenant context.
2. **Alert missing:** inspect LogQL output, rule state, `for`, Alertmanager routing and silences.
3. **False positive:** compare logs with direct application SLIs and pipeline completeness.
4. **Logging outage:** validate Alloy and Loki independently and use out-of-band pipeline alerts.
5. **Compactor failure:** inspect storage, retention settings, permissions and compactor logs.
6. **Retention incident:** freeze destructive changes, preserve evidence and escalate to data governance.
7. **Cost surge:** inspect ingestion rate, stream labels, retention and query patterns.
8. **Rollback:** restore last reviewed rules/limits, confirm evaluation and synthetic delivery.

## 9. Production incident game day

A PostgreSQL-backed service begins logging repeated timeouts. A Loki ruler alert does not page because log ingestion is throttled, while retention unexpectedly retains old data due to compactor errors. Diagnose user impact via Prometheus SLIs, restore logging, validate independent pipeline alerts, recover ruler routing and correct compactor settings in staging. Record RTO, cost and change approvals.

## 10. 100-point acceptance

| Domain | Points |
|---|---:|
| LogQL and ruler semantics | 20 |
| Alertmanager routing and validation | 20 |
| Retention, compactor and FinOps | 20 |
| Offline gate and tests | 20 |
| Incident response and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Actual production acceptance requires witnessed ruler execution, notification delivery, retention verification and DR evidence.

**Companion:** [Chapter 039 operational lab](labs/039-loki-alerting-recording-rules-retention-enterprise-operations-lab.md).

**Next:** Chapter 040 — Loki Production Reliability, Security, Troubleshooting and Logging Capstone.
