# Chapter 024 — Grafana Alerting, Contact Points, Notification Policies and SRE Incident Workflows

**Part 05 — Grafana Dashboards and Visualization**  
**Audience:** Enterprise SRE/DBRE, on-call engineers, platform security and observability operators.  
**Prerequisites:** Chapters 021–023, PromQL, Python 3.10+.  
**Objective:** Design and operate reliable Grafana alert evaluation, contact points, routing, incident response and controlled rollback.

## 1. Grafana alerting architecture

```text
Prometheus / Loki / other datasources
                |
    Grafana-managed evaluation groups
       query -> reduce/math -> threshold
                |
    Normal / Pending / Alerting / Recovering
                |
       Alert instances with labels
                |
       Notification policy tree
       group / mute / active timings
                |
       Contact points / on-call
                |
    Incident / dashboard / runbook
```

Distinguish **Grafana-managed alert rules** from **data-source-managed rules** (for example Prometheus recording/alerting rules). Their evaluation and administration paths differ. Grafana unified alerting concepts include alert instances, evaluation groups, pending period, recovery behavior, contact points, notification policy routing, grouping and mute timings. Version-specific APIs and UI labels should be checked against the deployed Grafana release.

## 2. Rule evaluation and state machine

- **Normal:** query result does not meet the firing condition.
- **Pending:** condition is true but the pending period has not elapsed.
- **Alerting:** condition remains true for the required period.
- **Recovering:** condition has cleared but a configured keep-firing period may delay resolution.
- **No Data / Error:** evaluator cannot produce an expected valid result; these require explicit policies.

```promql
sum by (cluster, service) (
  up{job="postgres",cluster="east"} == 0
)
```

This expression reports **discovered, scraped targets that are down**; it does not detect an expected target that has disappeared from discovery. Use inventory-based coverage alerts and missing-series logic separately. Avoid interpreting `count(...)` of an absent vector as evidence of health.

## 3. Routing, contact points and escalation

A **contact point** defines notification delivery integration (email, webhook, paging service, etc.). A **notification policy** selects the receiver and grouping/interval behavior using labels. Organize routing by team, service, severity and cluster, and test fallback routing. Keep credentials in Grafana secure configuration or a secrets manager, never in Git or logs.

Example routing design:

```text
root (fallback on-call)
 ├─ team=platform, severity=page -> sre-pager
 ├─ team=dbre, severity=page -> dbre-pager
 └─ severity=warning -> ticket / low-priority channel
```

Use dedicated policies for silence/mute timing, grouping, repeat intervals and ownership. Grafana notification policies do not themselves replace an organization's incident command and escalation process. If Grafana and Alertmanager both route the same rule, assess duplicate paging risk.

## 4. Incident workflow

1. Detect alert, verify route and responder acknowledgement.
2. Confirm datasource freshness, rule expression, target inventory and user impact.
3. Classify severity, incident commander and service ownership.
4. Follow runbook and correlate metrics, logs and traces.
5. Mitigate impact using approved production controls; preserve incident timeline.
6. Verify recovery, rule state and downstream paging resolution.
7. Conduct post-incident review, tune noisy alerts and record evidence.

## 5. Secure alert policy fixture

The following JSON is **training policy metadata**, not Grafana provisioning/API schema. Use official Grafana provisioning schema and version-specific API docs for real deployment.

### fixtures/healthy.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "evaluation_interval_seconds": 60,
  "pending_period_seconds": 120,
  "keep_firing_for_seconds": 300,
  "labels": {
    "team": "platform",
    "service": "postgres",
    "severity": "page",
    "cluster": "east"
  },
  "query": {
    "datasource_uid": "prometheus-primary",
    "expression": "sum by (cluster, service) (up{job=\"postgres\",cluster=\"east\"} == 0)",
    "threshold": 0
  },
  "contact_point": {
    "name": "sre-pager",
    "type": "webhook",
    "secret_ref": "env:GRAFANA_PAGER_WEBHOOK",
    "tested": true
  },
  "routing": {
    "group_by": [
      "alertname",
      "cluster",
      "service"
    ],
    "group_wait_seconds": 30,
    "group_interval_seconds": 300,
    "repeat_interval_seconds": 14400,
    "receiver": "sre-pager",
    "mute_timings": [],
    "inhibition_reviewed": true
  },
  "runbook_url": "https://example.org/runbooks/postgres-target-down",
  "dashboard_uid": "dbre-postgres-023",
  "reviewed": true,
  "rollback_tested": true,
  "ownership_acknowledged": true
}
```

### fixtures/degraded.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "evaluation_interval_seconds": 60,
  "pending_period_seconds": 120,
  "keep_firing_for_seconds": 300,
  "labels": {
    "team": "platform",
    "service": "postgres",
    "severity": "page",
    "cluster": ""
  },
  "query": {
    "datasource_uid": "prometheus-primary",
    "expression": "sum by (cluster, service) (up{job=\"postgres\",cluster=\"east\"} == 0)",
    "threshold": 0
  },
  "contact_point": {
    "name": "sre-pager",
    "type": "webhook",
    "secret_ref": "https://hooks.example.org/secret",
    "tested": false
  },
  "routing": {
    "group_by": [
      "alertname",
      "cluster",
      "service"
    ],
    "group_wait_seconds": 30,
    "group_interval_seconds": 300,
    "repeat_interval_seconds": 0,
    "receiver": "unowned",
    "mute_timings": [],
    "inhibition_reviewed": true
  },
  "runbook_url": "https://example.org/runbooks/postgres-target-down",
  "dashboard_uid": "dbre-postgres-023",
  "reviewed": false,
  "rollback_tested": false,
  "ownership_acknowledged": true
}
```

## 6. Executable offline alerting governance lab

The Python gate validates policy metadata, labels, receiver alignment, secret references, tested delivery, interval limits and ownership. It **does not evaluate PromQL, contact a webhook, provision Grafana or prove that a page arrived**.

Create:

```text
chapter024/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/alert_gate.py
  tests/test_alert_gate.py
```

### scripts/alert_gate.py

```python
#!/usr/bin/env python3
"""Offline Grafana alerting governance gate; does not execute Grafana alert rules."""
import json,re,sys
from pathlib import Path
ALLOWED={"page","ticket","warning"}
def check(p):
    issues=[]
    if not isinstance(p,dict): return ["policy must be object"]
    for k in ("owner","environment","dashboard_uid","runbook_url"):
        if not isinstance(p.get(k),str) or not p[k].strip(): issues.append("missing "+k)
    for k in ("reviewed","rollback_tested","ownership_acknowledged"):
        if p.get(k) is not True: issues.append("missing approval "+k)
    for k in ("evaluation_interval_seconds","pending_period_seconds","keep_firing_for_seconds"):
        v=p.get(k)
        if type(v) is not int or v<0: issues.append("invalid "+k)
    if type(p.get("evaluation_interval_seconds")) is int and p["evaluation_interval_seconds"]<30:
        issues.append("evaluation too frequent")
    labels=p.get("labels")
    if not isinstance(labels,dict): issues.append("missing labels");labels={}
    for k in ("team","service","severity","cluster"):
        if not isinstance(labels.get(k),str) or not labels[k].strip(): issues.append("missing label "+k)
    if labels.get("severity") not in ALLOWED: issues.append("unknown severity")
    q=p.get("query")
    if not isinstance(q,dict): issues.append("missing query");q={}
    if q.get("datasource_uid")!="prometheus-primary": issues.append("unexpected datasource")
    expr=q.get("expression")
    if not isinstance(expr,str) or not expr.strip(): issues.append("empty expression")
    if isinstance(expr,str) and len(expr)>1000: issues.append("query too long")
    cp=p.get("contact_point")
    if not isinstance(cp,dict): issues.append("missing contact");cp={}
    if cp.get("type") not in ("webhook","email","pagerduty"): issues.append("unsupported contact type")
    if not isinstance(cp.get("name"),str) or not cp["name"]: issues.append("contact missing name")
    if not isinstance(cp.get("secret_ref"),str) or not cp["secret_ref"].startswith("env:"):
        issues.append("secret must be external reference")
    if cp.get("tested") is not True: issues.append("contact untested")
    routing=p.get("routing")
    if not isinstance(routing,dict): issues.append("missing routing");routing={}
    if routing.get("receiver")!=cp.get("name"): issues.append("receiver mismatch")
    if routing.get("inhibition_reviewed") is not True: issues.append("inhibition not reviewed")
    groups=routing.get("group_by")
    if not isinstance(groups,list) or "cluster" not in groups or "service" not in groups:
        issues.append("unsafe grouping")
    for k in ("group_wait_seconds","group_interval_seconds","repeat_interval_seconds"):
        v=routing.get(k)
        if type(v) is not int or v<1: issues.append("invalid "+k)
    return issues
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 alert_gate.py fixtures/healthy.json")
    try: issues=check(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as e: sys.exit(f"input error: {e}")
    print(json.dumps({"status":"PASS" if not issues else "FAIL","findings":issues},indent=2))
    sys.exit(bool(issues))
```

### tests/test_alert_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from alert_gate import check
class AlertTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def mutate(self,f):
        p=copy.deepcopy(self.p);f(p);return check(p)
    def test_healthy(self): self.assertEqual(check(self.p),[])
    def test_degraded(self): self.assertTrue(check(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_not_object(self): self.assertTrue(check(None))
    def test_owner(self): self.assertTrue(self.mutate(lambda p:p.update(owner="")))
    def test_runbook(self): self.assertTrue(self.mutate(lambda p:p.update(runbook_url="")))
    def test_review(self): self.assertTrue(self.mutate(lambda p:p.update(reviewed=False)))
    def test_rollback(self): self.assertTrue(self.mutate(lambda p:p.update(rollback_tested=False)))
    def test_ack(self): self.assertTrue(self.mutate(lambda p:p.update(ownership_acknowledged=False)))
    def test_eval(self): self.assertTrue(self.mutate(lambda p:p.update(evaluation_interval_seconds=10)))
    def test_pending(self): self.assertTrue(self.mutate(lambda p:p.update(pending_period_seconds=-1)))
    def test_team(self): self.assertTrue(self.mutate(lambda p:p["labels"].update(team="")))
    def test_cluster(self): self.assertTrue(self.mutate(lambda p:p["labels"].update(cluster="")))
    def test_severity(self): self.assertTrue(self.mutate(lambda p:p["labels"].update(severity="unknown")))
    def test_datasource(self): self.assertTrue(self.mutate(lambda p:p["query"].update(datasource_uid="wrong")))
    def test_expression(self): self.assertTrue(self.mutate(lambda p:p["query"].update(expression="")))
    def test_contact_type(self): self.assertTrue(self.mutate(lambda p:p["contact_point"].update(type="sms")))
    def test_contact_name(self): self.assertTrue(self.mutate(lambda p:p["contact_point"].update(name="")))
    def test_secret(self): self.assertTrue(self.mutate(lambda p:p["contact_point"].update(secret_ref="inline-secret")))
    def test_contact_test(self): self.assertTrue(self.mutate(lambda p:p["contact_point"].update(tested=False)))
    def test_receiver(self): self.assertTrue(self.mutate(lambda p:p["routing"].update(receiver="other")))
    def test_inhibition(self): self.assertTrue(self.mutate(lambda p:p["routing"].update(inhibition_reviewed=False)))
    def test_group(self): self.assertTrue(self.mutate(lambda p:p["routing"].update(group_by=["alertname"])))
    def test_repeat(self): self.assertTrue(self.mutate(lambda p:p["routing"].update(repeat_interval_seconds=0)))
    def test_wait(self): self.assertTrue(self.mutate(lambda p:p["routing"].update(group_wait_seconds=0)))
if __name__=="__main__": unittest.main()
```

### Execute

```bash
cd chapter024
python3 scripts/alert_gate.py fixtures/healthy.json
if python3 scripts/alert_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded alert policy accepted"; exit 1
else
  echo "PASS: degraded alert policy rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and **24 automated tests pass**.

## 7. Optional approved Grafana staging integration

Provision a Grafana-managed rule using the official API or supported file provisioning for your deployed version. Use a **test receiver**, never a real paging receiver, for drills. Verify evaluation state transitions, No Data/Error policies, contact-point test, notification policy matches, grouping, mute timing and rollback. Capture timestamps, screenshots/API results and acknowledgement evidence.

## 8. Twenty-four hands-on exercises

1. Diagram Grafana-managed versus data-source-managed alerting.
2. Identify evaluation groups and intervals.
3. Create PromQL condition for target failures.
4. Compare Reduce, Threshold and Math expressions.
5. Explain Pending, Alerting, Recovering and Normal states.
6. Set pending period and keep-firing-for behavior.
7. Define No Data and Error policies.
8. Plan labels and annotations.
9. Design contact point using secret references.
10. Test webhook delivery in staging.
11. Create notification policy routing tree.
12. Choose group-by labels.
13. Tune group wait, interval and repeat.
14. Plan silence and mute timing policy.
15. Review inhibition/deduplication boundaries.
16. Map on-call escalation and ownership.
17. Connect dashboard and runbook.
18. Review RBAC for alert changes.
19. Model HA evaluation and notification reliability.
20. Create a change ticket and rollback plan.
21. Run healthy fixture.
22. Reject degraded fixture.
23. Run 24 automated tests.
24. Conduct DBRE incident tabletop.

## 9. Twenty-four production failure scenarios

| # | Failure | Initial diagnostic |
|---|---|---|
| 01 | Grafana alert evaluator unavailable | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 02 | Prometheus datasource unreachable | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 03 | Alert enters No Data | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 04 | Alert enters Error | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 05 | Alert remains Pending too long | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 06 | Flapping alerts | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 07 | Wrong threshold or units | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 08 | Missing cluster label | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 09 | Cross-tenant routing | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 10 | Contact point secret leaked | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 11 | Webhook receiver rejects requests | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 12 | Email notifications delayed | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 13 | PagerDuty integration misconfigured | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 14 | Policy receiver mismatch | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 15 | Excessive grouping | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 16 | Repeat interval too short | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 17 | Silence suppresses critical alert | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 18 | Mute timing timezone incorrect | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 19 | Duplicate Grafana/Alertmanager pages | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 20 | Alert rule UID collision | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 21 | Alert annotations missing | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 22 | Runbook URL stale | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 23 | RBAC prevents rule edits | Inspect evaluation state, labels, policy, receiver, ownership and logs |
| 24 | Rollback fails after alert migration | Inspect evaluation state, labels, policy, receiver, ownership and logs |

## 10. Eight production runbooks

**A. No Data/Error state:** Inspect evaluator logs, datasource query, scrape health, no-data/error policies and missing-series behavior.

**B. Notification delivery failure:** Review contact-point test, receiver logs, policy match, secret rotation, network/TLS and escalation.

**C. Alert storm:** Inspect group-by labels, repeat intervals, cardinality, rule duplication and flap suppression.

**D. False positive/negative:** Validate SLI, thresholds, time windows, pending period, missing data and evaluation frequency.

**E. Silence or mute incident:** Audit active silences/mute timings, timezone, owner, expiry and emergency override.

**F. Cross-tenant exposure:** Inspect labels, routing policies, RBAC, datasource isolation and notification payloads.

**G. Grafana HA evaluator issue:** Check instance health, alert scheduler, shared database, HA behavior and delivery duplication.

**H. Safe alert rollback:** Revert Git-managed alert resources, re-test receiver, verify paging and document handover.

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Grafana alert evaluation and state handling | 20 |
| Contact points and routing design | 20 |
| Security, tenancy and incident workflows | 20 |
| Offline governance gate and 24 tests | 20 |
| Failure drills, runbooks and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory gates: approved contact points, safe secret handling, tested paging route, explicit No Data/Error policy, tenant isolation, rollback evidence.

## 12. Evidence worksheet

```text
UTC / operator / Grafana version:
Alert rule UID / evaluator / datasource:
PromQL / pending / keep-firing / No Data/Error:
Labels / severity / cluster / service:
Notification policy match / grouping:
Contact-point test receiver and delivery evidence:
Silences / mute timing / timezone:
Offline healthy/degraded / 24 tests:
Incident timeline / RCA / rollback / reviewer:
```

**Companion:** [Chapter 024 executable alerting lab](labs/024-grafana-alerting-contact-points-notification-policies-sre-incident-workflows-lab.md).

**Next:** Chapter 025 — Grafana Enterprise Dashboards, Alerting, Security and Production Operations Capstone.
