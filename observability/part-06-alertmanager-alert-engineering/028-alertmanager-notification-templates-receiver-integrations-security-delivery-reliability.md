# Chapter 028 — Alertmanager Notification Templates, Receiver Integrations, Security and Delivery Reliability

**Part 06 — Alertmanager and Alert Engineering**  
**Audience:** Enterprise SRE/DBRE, on-call engineering, observability security and platform teams.  
**Prerequisites:** Chapters 026–027, Alertmanager routing, Python 3.10+.  
**Objective:** Engineer secure, actionable, resilient notifications with reviewed templates, receivers, fallback routes, credential controls and delivery evidence.

## 1. End-to-end notification delivery

```text
Prometheus firing/resolved alerts
              |
    Alertmanager routing + grouping
              |
    inhibition and active silences
              |
    Go template rendering
              |
    webhook / email / paging integrations
              |
     retry / receiver / acknowledgement
              |
        incident escalation
```

Alertmanager controls notification dispatch, not PromQL evaluation. A successful dispatch attempt is not the same as on-call acknowledgement or mitigation. Maintain independent evidence for rule firing, Alertmanager dispatch, receiver acceptance and incident ownership.

## 2. Receiver integrations and tradeoffs

| Receiver | Use | Operational concern |
|---|---|---|
| Webhook | custom incident automation | TLS, auth, retries, payload schema |
| Email | informational delivery | SMTP credentials, delivery delay |
| PagerDuty/incident platform | on-call paging and escalation | API keys, routing keys, deduplication |
| Chat integration | team collaboration | channel access, noise and data exposure |

Validate receiver-specific capabilities and configuration fields against the deployed Alertmanager version. Prefer native integrations where appropriate, but avoid assuming that every receiver offers the same retry, acknowledgement or recovery semantics.

## 3. Alertmanager Go templates

Alertmanager notification templates use Go's template language and expose alert groups, common labels, annotations, status and per-alert data. Template logic must tolerate missing annotations and unexpected labels; never interpolate secrets or user-controlled data into unsafe destinations.

### templates/notifications.tmpl

```gotemplate
{{ define "custom.title" -}}
[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }} / {{ .CommonLabels.cluster }}
{{- end }}
{{ define "custom.body" -}}
Status: {{ .Status }}
Team: {{ .CommonLabels.team }}
Service: {{ .CommonLabels.service }}
Severity: {{ .CommonLabels.severity }}
{{ range .Alerts }}
Summary: {{ .Annotations.summary }}
Runbook: {{ .Annotations.runbook_url }}
{{ end }}
{{- end }}
```

The template is a reusable example for integrations that support custom title/text fields. **Generic webhook_configs send Alertmanager's webhook JSON payload and do not use this title/body template automatically.** Wire templates only into receiver integrations that explicitly support them, or implement a separate, reviewed webhook renderer.

## 4. Safe local receiver configuration

```yaml
global:
  resolve_timeout: 5m
templates:
  - /etc/alertmanager/templates/*.tmpl
route:
  receiver: fallback-test
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - receiver: dbre-test
      matchers: ['team="dbre"', 'severity="page"']
receivers:
  - name: fallback-test
    webhook_configs:
      - url: http://webhook:8080/alerts
        send_resolved: true
        max_alerts: 10
  - name: dbre-test
    webhook_configs:
      - url: http://webhook:8080/alerts
        send_resolved: true
        max_alerts: 10
```

This example assumes Chapter 026's internal `webhook` Docker service. It does not contact external paging endpoints. Test actual receiver behavior with staging-only alert data. `max_alerts` bounds the number of alert objects in a webhook notification but does not replace receiver-side size limits or rate controls.

## 5. Security controls

- Store receiver credentials in a secrets manager or protected environment, not plaintext Git.
- Enforce TLS and verify certificate chains for production outbound delivery.
- Restrict receiver egress, inbound webhooks and administrative Alertmanager API access.
- Scrub PHI/PII, customer identifiers, SQL text and sensitive labels from payloads.
- Test credential rotation and rollback with least-privilege service identities.
- Use explicit contact ownership, escalation and backup routes.

## 6. Delivery reliability and SLOs

Define measurable stages: rule firing time, Alertmanager dispatch time, receiver accepted time, and on-call acknowledged time. For example, an internal staging goal might be 99% of synthetic critical notifications accepted by the test receiver within 2 minutes; **this is an illustrative target, not a validated production SLO**. Track retry attempts, HTTP 429/5xx, notification latency, receiver availability and end-to-end acknowledgement.

Do not treat a 2xx response as proof that an incident platform paged the correct human. Use synthetic delivery tests, backup routes and human acknowledgement checks.

## 7. Complete offline governance lab

The JSON below is **synthetic training metadata**, not native Alertmanager YAML. The Python gate validates test-only receivers, secret references, route fallback, ownership, notification fields and review evidence. It does not send notifications or parse Go templates.

Create:

```text
chapter028/
  templates/notifications.tmpl
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/notification_gate.py
  tests/test_notification_gate.py
```

### fixtures/healthy.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "config_reviewed": true,
  "secret_scan_passed": true,
  "rollback_tested": true,
  "receiver_tested": true,
  "backup_route_tested": true,
  "tls_reviewed": true,
  "notification_pii_reviewed": true,
  "template_tested": true,
  "rate_limit_reviewed": true,
  "delivery_slo_reviewed": true,
  "receivers": [
    {
      "name": "dbre-test",
      "kind": "webhook",
      "endpoint": "http://webhook:8080/alerts",
      "secret_ref": "env:TEST_WEBHOOK_TOKEN",
      "timeout_seconds": 10,
      "send_resolved": true,
      "owner": "dbre"
    },
    {
      "name": "fallback-test",
      "kind": "webhook",
      "endpoint": "http://webhook:8080/alerts",
      "secret_ref": "env:TEST_WEBHOOK_TOKEN",
      "timeout_seconds": 10,
      "send_resolved": true,
      "owner": "sre"
    }
  ],
  "routing": {
    "default_receiver": "fallback-test",
    "primary_receiver": "dbre-test",
    "group_by": [
      "alertname",
      "cluster",
      "service"
    ],
    "group_wait_seconds": 30,
    "group_interval_seconds": 300,
    "repeat_interval_seconds": 14400
  },
  "template": {
    "path": "templates/notifications.tmpl",
    "max_summary_chars": 160,
    "includes_runbook": true,
    "includes_owner": true,
    "includes_severity": true,
    "includes_sensitive_data": false
  }
}
```

### fixtures/degraded.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "config_reviewed": true,
  "secret_scan_passed": false,
  "rollback_tested": true,
  "receiver_tested": false,
  "backup_route_tested": true,
  "tls_reviewed": true,
  "notification_pii_reviewed": true,
  "template_tested": true,
  "rate_limit_reviewed": true,
  "delivery_slo_reviewed": true,
  "receivers": [
    {
      "name": "dbre-test",
      "kind": "webhook",
      "endpoint": "https://hooks.example.com/real",
      "secret_ref": "plaintext-token",
      "timeout_seconds": 10,
      "send_resolved": true,
      "owner": "dbre"
    },
    {
      "name": "dbre-test",
      "kind": "webhook",
      "endpoint": "http://webhook:8080/alerts",
      "secret_ref": "env:TEST_WEBHOOK_TOKEN",
      "timeout_seconds": 10,
      "send_resolved": true,
      "owner": "sre"
    }
  ],
  "routing": {
    "default_receiver": "missing",
    "primary_receiver": "dbre-test",
    "group_by": [
      "alertname",
      "cluster",
      "service"
    ],
    "group_wait_seconds": 30,
    "group_interval_seconds": 300,
    "repeat_interval_seconds": 14400
  },
  "template": {
    "path": "templates/notifications.tmpl",
    "max_summary_chars": 160,
    "includes_runbook": false,
    "includes_owner": true,
    "includes_severity": true,
    "includes_sensitive_data": true
  }
}
```

### scripts/notification_gate.py

```python
#!/usr/bin/env python3
"""Offline notification delivery governance; not native Alertmanager config parsing."""
import json,sys
from pathlib import Path
FLAGS=("config_reviewed","secret_scan_passed","rollback_tested","receiver_tested",
"backup_route_tested","tls_reviewed","notification_pii_reviewed","template_tested",
"rate_limit_reviewed","delivery_slo_reviewed")
def check(p):
    problems=[]
    if not isinstance(p,dict): return ["policy must be object"]
    for k in ("owner","environment"):
        if not isinstance(p.get(k),str) or not p[k]: problems.append("missing "+k)
    for k in FLAGS:
        if p.get(k) is not True: problems.append("gate failed "+k)
    rec=p.get("receivers")
    if not isinstance(rec,list) or not rec: problems.append("missing receivers");rec=[]
    names=set()
    for i,r in enumerate(rec):
        x="receiver["+str(i)+"]"
        if not isinstance(r,dict): problems.append(x+" invalid");continue
        name=r.get("name")
        if not isinstance(name,str) or not name: problems.append(x+" missing name")
        elif name in names: problems.append(x+" duplicate name")
        else: names.add(name)
        if r.get("kind")!="webhook": problems.append(x+" unsupported integration")
        if r.get("endpoint")!="http://webhook:8080/alerts": problems.append(x+" external endpoint")
        if not isinstance(r.get("secret_ref"),str) or not r["secret_ref"].startswith("env:"):
            problems.append(x+" inline secret")
        t=r.get("timeout_seconds")
        if type(t) is not int or not 1<=t<=30: problems.append(x+" unsafe timeout")
        if r.get("send_resolved") is not True: problems.append(x+" missing recovery")
        if not isinstance(r.get("owner"),str) or not r["owner"]: problems.append(x+" missing owner")
    route=p.get("routing")
    if not isinstance(route,dict): problems.append("missing routing");route={}
    for k in ("default_receiver","primary_receiver"):
        if route.get(k) not in names: problems.append("unknown "+k)
    if route.get("default_receiver")==route.get("primary_receiver"): problems.append("no backup route")
    groups=route.get("group_by")
    if not isinstance(groups,list) or not {"alertname","cluster","service"}.issubset(groups): problems.append("unsafe grouping")
    for k,minimum in (("group_wait_seconds",0),("group_interval_seconds",1),("repeat_interval_seconds",1)):
        v=route.get(k)
        if type(v) is not int or v<minimum: problems.append("invalid "+k)
    t=p.get("template")
    if not isinstance(t,dict): problems.append("missing template");t={}
    if t.get("path")!="templates/notifications.tmpl": problems.append("unapproved template")
    limit=t.get("max_summary_chars")
    if type(limit) is not int or not 1<=limit<=500: problems.append("summary length unbounded")
    for k in ("includes_runbook","includes_owner","includes_severity"):
        if t.get(k) is not True: problems.append("missing template field "+k)
    if t.get("includes_sensitive_data") is not False: problems.append("sensitive data exposure")
    return problems
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 notification_gate.py fixtures/healthy.json")
    try: errors=check(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as e: sys.exit("input error: "+str(e))
    print(json.dumps({"status":"FAIL" if errors else "PASS","errors":errors},indent=2))
    sys.exit(bool(errors))
```

### tests/test_notification_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from notification_gate import check
class NotificationTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def mutate(self,f):
        d=copy.deepcopy(self.p);f(d);return check(d)
    def test_valid(self): self.assertEqual(check(self.p),[])
    def test_degraded(self): self.assertTrue(check(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_non_object(self): self.assertTrue(check(None))
    def test_owner(self): self.assertTrue(self.mutate(lambda d:d.update(owner="")))
    def test_config(self): self.assertTrue(self.mutate(lambda d:d.update(config_reviewed=False)))
    def test_secrets(self): self.assertTrue(self.mutate(lambda d:d.update(secret_scan_passed=False)))
    def test_rollback(self): self.assertTrue(self.mutate(lambda d:d.update(rollback_tested=False)))
    def test_receiver_test(self): self.assertTrue(self.mutate(lambda d:d.update(receiver_tested=False)))
    def test_backup_test(self): self.assertTrue(self.mutate(lambda d:d.update(backup_route_tested=False)))
    def test_tls(self): self.assertTrue(self.mutate(lambda d:d.update(tls_reviewed=False)))
    def test_pii(self): self.assertTrue(self.mutate(lambda d:d.update(notification_pii_reviewed=False)))
    def test_template_test(self): self.assertTrue(self.mutate(lambda d:d.update(template_tested=False)))
    def test_rate_limit(self): self.assertTrue(self.mutate(lambda d:d.update(rate_limit_reviewed=False)))
    def test_slo(self): self.assertTrue(self.mutate(lambda d:d.update(delivery_slo_reviewed=False)))
    def test_no_receivers(self): self.assertTrue(self.mutate(lambda d:d.update(receivers=[])))
    def test_duplicate(self): self.assertTrue(self.mutate(lambda d:d["receivers"][1].update(name="dbre-test")))
    def test_endpoint(self): self.assertTrue(self.mutate(lambda d:d["receivers"][0].update(endpoint="https://real.example.com")))
    def test_inline_secret(self): self.assertTrue(self.mutate(lambda d:d["receivers"][0].update(secret_ref="secret")))
    def test_timeout(self): self.assertTrue(self.mutate(lambda d:d["receivers"][0].update(timeout_seconds=0)))
    def test_recovery(self): self.assertTrue(self.mutate(lambda d:d["receivers"][0].update(send_resolved=False)))
    def test_receiver_owner(self): self.assertTrue(self.mutate(lambda d:d["receivers"][0].update(owner="")))
    def test_default(self): self.assertTrue(self.mutate(lambda d:d["routing"].update(default_receiver="missing")))
    def test_no_backup(self): self.assertTrue(self.mutate(lambda d:d["routing"].update(default_receiver="dbre-test")))
    def test_group(self): self.assertTrue(self.mutate(lambda d:d["routing"].update(group_by=["alertname"])))
    def test_repeat(self): self.assertTrue(self.mutate(lambda d:d["routing"].update(repeat_interval_seconds=0)))
    def test_template_path(self): self.assertTrue(self.mutate(lambda d:d["template"].update(path="../bad")))
    def test_summary(self): self.assertTrue(self.mutate(lambda d:d["template"].update(max_summary_chars=10000)))
    def test_runbook(self): self.assertTrue(self.mutate(lambda d:d["template"].update(includes_runbook=False)))
    def test_sensitive(self): self.assertTrue(self.mutate(lambda d:d["template"].update(includes_sensitive_data=True)))
if __name__=="__main__": unittest.main()
```

### Execute

```bash
cd chapter028
python3 scripts/notification_gate.py fixtures/healthy.json
if python3 scripts/notification_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded notification policy accepted"; exit 1
else
  echo "PASS: degraded notification policy rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and **29 automated unit tests pass**. This is policy modeling, not delivery validation.

## 8. Optional staging integration

1. Start Chapter 026's isolated Prometheus/Alertmanager/test-webhook stack.
2. Validate native config using `amtool check-config`.
3. Add reviewed receiver-specific templates where supported.
4. Fire a synthetic test alert and inspect webhook logs for status, receiver and timestamps.
5. Simulate webhook 500/429 and latency in a dedicated staging test receiver; observe retry behavior.
6. Restore receiver and verify a resolved notification.
7. Review backup escalation and credential rotation procedures.
8. Roll back config and confirm test-only delivery.

Never point synthetic rules at production paging endpoints.

## 9. Twenty-four hands-on exercises

1. Inventory receiver integrations.
2. Design default fallback receiver.
3. Design DBRE primary receiver.
4. Review Alertmanager Go templates.
5. Create title template.
6. Create body template.
7. Include severity and service.
8. Include runbook URL.
9. Bound annotation length.
10. Avoid PHI/PII in notifications.
11. Compare email and webhook transport.
12. Review PagerDuty or incident platform integration.
13. Document API credential rotation.
14. Test TLS trust and proxy.
15. Review HTTP retry behavior.
16. Review webhook timeout.
17. Review receiver 429/5xx.
18. Set max_alerts guard.
19. Plan delivery SLO and synthetic test.
20. Review recovery notifications.
21. Test backup escalation route.
22. Run healthy policy gate.
23. Reject degraded policy.
24. Execute 29 automated tests.

## 10. Twenty-four production failure scenarios

| # | Failure | First diagnostic |
|---|---|---|
| 01 | Template parse error | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 02 | Missing annotation in template | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 03 | Sensitive metadata exposed | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 04 | Receiver secret committed | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 05 | Webhook certificate invalid | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 06 | Webhook DNS failure | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 07 | Webhook timeout | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 08 | Webhook HTTP 429 | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 09 | Webhook HTTP 500 | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 10 | Webhook accepts but drops payload | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 11 | Notification payload too large | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 12 | Notification storm | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 13 | Missing resolved event | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 14 | Receiver name mismatch | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 15 | Fallback receiver absent | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 16 | Misconfigured PagerDuty integration | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 17 | Email SMTP authentication failure | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 18 | Proxy egress blocked | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 19 | Credential rotation outage | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 20 | Alertmanager config reload rejected | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 21 | Rate limit exceeded | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 22 | Delivery SLO breached | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 23 | Receiver retry amplification | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |
| 24 | Unacknowledged incident escalation | Inspect config, template, Alertmanager logs, HTTP result, receiver state and escalation |

## 11. Eight production runbooks

**A. Template failure:** Validate template syntax, missing labels/annotations, escaping and sample render before reload.

**B. Webhook failure:** Check DNS, TLS, timeout, HTTP response, receiver logs, retries and test-only endpoint.

**C. Secret leak:** Revoke exposed credentials, rotate secrets, review Git history and notification payloads.

**D. Rate limit incident:** Inspect grouping, repeat interval, receiver 429 and queue/retry metrics; reduce alert noise.

**E. Missing resolved notification:** Inspect send_resolved, alert lifecycle, receiver logs, silences and deduplication.

**F. Wrong receiver:** Trace route labels, fallback, child ordering, receiver names and matching rules.

**G. Delivery SLO breach:** Correlate alert firing, dispatch, webhook receipt, acknowledgement and incident timeline.

**H. Safe rollback:** Restore reviewed template/config, validate with amtool, reload and test primary/fallback delivery.

## 12. SRE/DBRE incident simulation

A PostgreSQL failover generates a critical alert. The DBRE receiver returns HTTP 429, the template omits the runbook URL, and a secret rotation breaks webhook authentication. Determine whether the alert fired, whether Alertmanager dispatched it, whether the receiver accepted it and whether the on-call responder acknowledged. Restore a test-only backup route, rotate credentials safely and document recovery.

## 13. 100-point assessment

| Domain | Points |
|---|---:|
| Template and receiver design | 20 |
| Credential and payload security | 20 |
| Delivery SLOs and failure recovery | 20 |
| Offline governance and 29 tests | 20 |
| Troubleshooting, runbooks and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory: no plaintext secrets, approved test-only endpoints, fallback route, recovery notification and rollback evidence.

## 14. Evidence worksheet

```text
UTC / owner / Alertmanager version:
Template version / sample rendered content:
Primary and fallback receiver:
Credential source / rotation evidence:
Alert fired / dispatched / received / acknowledged:
HTTP status / retry / delivery latency:
Healthy/degraded gate / 29 tests:
Incident drill / rollback / reviewer / score:
```

**Companion:** [Chapter 028 executable receiver reliability lab](labs/028-alertmanager-notification-templates-receiver-integrations-security-delivery-reliability-lab.md).

**Next:** Chapter 029 — Alert Quality Engineering, Noise Reduction, SLO Burn-Rate Alerts and Incident Signal Design.
