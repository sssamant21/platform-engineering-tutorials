# Chapter 082 — Prometheus, Alertmanager and Grafana Configuration as Code

**Part 17 — Observability as Code and GitOps (2/5)**  
**Audience:** SRE, DBRE, observability platform engineers.  
**Prerequisites:** Chapter 081; Prometheus, Alertmanager and Grafana.

## Learning objectives

Treat monitoring rules, alert routes, dashboards and datasources as immutable reviewed artifacts with CI validation, staging smoke tests, environment isolation and safe rollback.

## Architecture

```text
Git PR / CODEOWNERS / CI lint + policy
                  |
          staging GitOps sync
                  |
         PrometheusRule + recording
                  |
        Alertmanager -> staging receiver
                  |
      Grafana datasource + dashboards
                  |
         SLI / route / access checks
                  |
       approved production promotion
```

## Repository layout

```text
observability/
  prometheus/rules/api-slo.yaml
  alertmanager/alertmanager.yaml
  grafana/provisioning/datasources/prometheus.yaml
  grafana/provisioning/dashboards/providers.yaml
  grafana/dashboards/api-overview.json
  environments/staging/
  environments/production/
  tests/
```

## Prometheus recording and alert rules

```yaml
groups:
  - name: api-slo
    interval: 30s
    rules:
      - record: job:api_error_ratio:rate5m
        expr: |
          sum(rate(http_requests_total{job="api",code=~"5.."}[5m]))
          /
          clamp_min(sum(rate(http_requests_total{job="api"}[5m])), 1e-9)
      - alert: ApiFastBurn
        expr: |
          (
            sum(rate(http_requests_total{job="api",code=~"5.."}[5m]))
            /
            clamp_min(sum(rate(http_requests_total{job="api"}[5m])), 1e-9)
          ) > 0.0144
          and
          (
            sum(rate(http_requests_total{job="api",code=~"5.."}[1h]))
            /
            clamp_min(sum(rate(http_requests_total{job="api"}[1h])), 1e-9)
          ) > 0.0144
        labels:
          severity: page
          team: platform
        annotations:
          summary: API error-budget fast burn
```

The example assumes a 99.9% SLO and 14.4× burn; add separate 30m/6h slow burn, no-data, minimum-volume checks and route tests. Validate real metric labels and eligible populations.

## Alertmanager as code

```yaml
route:
  receiver: staging-null
  group_by: [alertname, team]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
receivers:
  - name: staging-null
```

This receiver intentionally discards notifications and is suitable only for illustrating configuration structure, **not verifying page delivery**. For staging delivery tests, configure an approved test webhook or isolated receiver using secret references, never production paging.

## Grafana provisioning

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus.monitoring.svc:9090
    isDefault: true
```

Provision dashboards using JSON with stable UIDs and datasource references; validate panel queries, permissions and retention. Keep credentials outside Git and do not expose sensitive DBRE metric labels.

## CI validation and deployment gates

```bash
promtool check rules prometheus/rules/api-slo.yaml
amtool check-config alertmanager/alertmanager.yaml
git diff --check
```

Commands require the corresponding binaries. Test dashboard JSON syntax and alert routing in staging. Review Git diff, CODEOWNERS approvals, secret scans, pinned dependencies and drift. A passing lint job cannot prove real alert delivery.

## DBRE-specific considerations

PostgreSQL exporters need cardinality budgets and redaction; Redis key names should not become labels; Kafka partition metrics can be expensive; Elasticsearch shard/index labels may multiply series; Snowflake query identifiers may expose sensitive information. Ensure dashboards correlate to actual customer-facing SLIs.

## Executable offline synthetic acceptance gate

### healthy.json

```json
{
  "owner": "observability-platform",
  "environment": "staging",
  "change_id": "OBS-082",
  "reviewed": true,
  "secret_free": true,
  "staging_alert_tested": true,
  "destructive_action": false,
  "controls": {
    "prometheus_rules": true,
    "recording_rules": true,
    "slo_alerts": true,
    "no_data": true,
    "cardinality": true,
    "alertmanager_routes": true,
    "inhibition": true,
    "staging_receiver": true,
    "grafana_datasources": true,
    "grafana_dashboards": true,
    "permissions": true,
    "secrets": true,
    "version_pinning": true,
    "ci": true,
    "review": true,
    "staging": true,
    "drift": true,
    "rollback": true
  }
}
```

### config_gate.py

```python
"""Offline synthetic observability-config acceptance; does not deploy."""
import json,sys
from pathlib import Path
CONTROLS=["prometheus_rules","recording_rules","slo_alerts","no_data","cardinality","alertmanager_routes","inhibition","staging_receiver","grafana_datasources","grafana_dashboards","permissions","secrets","version_pinning","ci","review","staging","drift","rollback"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 for k in ("reviewed","secret_free","staging_alert_tested"):
  if p.get(k) is not True:e.append("missing "+k)
 c=p.get("controls")
 if not isinstance(c,dict):e.append("invalid controls");c={}
 for k in CONTROLS:
  if c.get(k) is not True:e.append("unverified "+k)
 if p.get("destructive_action") is not False:e.append("unsafe action")
 return e
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());e=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not e else "FAIL","findings":e},indent=2));sys.exit(bool(e))

```

### test_config_gate.py

```python
import copy,json,unittest
from pathlib import Path
from config_gate import validate
class ConfigTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["controls"]["prometheus_rules"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["controls"]["recording_rules"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["controls"]["slo_alerts"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["controls"]["no_data"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["controls"]["cardinality"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["controls"]["alertmanager_routes"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["controls"]["inhibition"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["controls"]["staging_receiver"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["controls"]["grafana_datasources"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["controls"]["grafana_dashboards"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["controls"]["permissions"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["controls"]["secrets"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["controls"]["version_pinning"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["controls"]["ci"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["controls"]["review"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["controls"]["staging"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["controls"]["drift"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["controls"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["reviewed"]=false
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["secret_free"]=false
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["staging_alert_tested"]=false
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["destructive_action"]=true
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["controls"]=null
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 config_gate.py healthy.json
python3 -m unittest -v test_config_gate.py
```

Expected PASS and **28 authored tests**. No live execution or cluster reconciliation is claimed.

## 24 hands-on exercises

1. Define rule ownership.
2. Create rule groups.
3. Create recording rules.
4. Create SLO burn alerts.
5. Check paired windows.
6. Check no-data alerts.
7. Check low traffic.
8. Validate labels.
9. Check metric cardinality.
10. Validate rule syntax.
11. Configure Alertmanager grouping.
12. Configure inhibition.
13. Configure routing.
14. Test staging receiver.
15. Provision Grafana datasource.
16. Provision Grafana dashboards.
17. Pin plugin versions.
18. Check dashboard permissions.
19. Review secret references.
20. Create CI lint workflow.
21. Review pull request.
22. Promote to staging.
23. Verify alerts and panels.
24. Rehearse Git revert.

## 24 production failure scenarios

1. **Bad PromQL:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
2. **Absent series:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
3. **High cardinality:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
4. **Duplicate alerts:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
5. **Wrong group_by:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
6. **Overbroad inhibition:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
7. **Missing receiver:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
8. **Broken webhook:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
9. **Secret in YAML:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
10. **Datasource UID mismatch:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
11. **Dashboard missing panel:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
12. **Plugin incompatibility:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
13. **Unpinned chart:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
14. **Rule evaluation slow:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
15. **Prometheus reload failure:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
16. **Scrape label mismatch:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
17. **Stale recording rule:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
18. **Incorrect SLO target:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
19. **Missing low-traffic guard:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
20. **Production route used in staging:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
21. **Unauthorized dashboard:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
22. **CI bypass:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
23. **Config drift:** identify impact, configuration defect, CI/policy gap, remediation and rollback.
24. **Rollback fails:** identify impact, configuration defect, CI/policy gap, remediation and rollback.

## Eight production runbooks

1. **Prometheus rule validation: lint, check expressions, ownership, labels and alert evidence.**
2. **Burn-rate acceptance: paired windows, eligible-event denominators and missing telemetry.**
3. **Alertmanager routing: grouping, deduplication, inhibition and receiver smoke tests.**
4. **Grafana provisioning: datasource UID, dashboard JSON, permissions and secret references.**
5. **Security gate: pinned versions, secret scanning and least-privilege reviewers.**
6. **CI/CD promotion: immutable commit, staging verification and change approval.**
7. **Drift investigation: compare repository config to observed cluster state.**
8. **Rollback: revert approved commit, reconcile staging and verify alert delivery.**

## 100-point assessment

| Domain | Points |
|---|---:|
| Prometheus rules and SLO math | 20 |
| Alertmanager routing and delivery | 20 |
| Grafana provisioning and access | 20 |
| CI validation and synthetic tests | 20 |
| GitOps promotion and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production readiness requires witnessed staging rule evaluation, actual test alert delivery, dashboard validation and change-owner approval.

**Companion:** [Chapter 082 lab](labs/082-prometheus-alertmanager-grafana-configuration-as-code-lab.md).

**Next:** Chapter 083 — OpenTelemetry, Loki and Tempo Pipelines as Code.
