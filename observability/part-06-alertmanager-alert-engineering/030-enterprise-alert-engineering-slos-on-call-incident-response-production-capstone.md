# Chapter 030 — Enterprise Alert Engineering, SLOs, On-Call and Incident Response Production Capstone

**Part 06 — Alertmanager and Alert Engineering: FINAL CAPSTONE**  
**Audience:** Enterprise SRE/DBRE, platform observability, on-call and incident command.  
**Prerequisites:** Chapters 026–029, Prometheus/PromQL, Python 3.10+, optional isolated staging.  
**Objective:** Integrate actionable SLO alerts, HA Alertmanager, secure notification routing, on-call escalation, incident response, recovery and operational acceptance.

## 1. End-to-end reference architecture

```text
Kubernetes / PostgreSQL / Redis / MongoDB / Elasticsearch
                   |
         app + exporter telemetry
                   |
       Prometheus HA scrape and rules
                   |
     SLI / error budget / burn-rate alerts
                   |
     Alertmanager peers (gossip / HA)
                   |
      route / group / inhibit / silence
                   |
     test paging / fallback escalation
                   |
     responder -> incident commander -> RCA
                   |
       GitOps rollback and DR evidence
```

Prometheus evaluates alert rules; Alertmanager handles notification routing and suppression. A firing alert is not proof of successful paging, and a 2xx webhook response is not proof of human acknowledgement. Separate these stages in acceptance evidence.

## 2. Production alert engineering contract

Each critical alert must have a service owner, SLI/SLO or user-impact rationale, rule UID/name, severity, threshold, time window, low-traffic/no-data policy, route and fallback, runbook, notification template, recovery semantics, security review, test evidence and rollback plan.

**Golden rules:** page only for actionable impact; use multiwindow multi-burn-rate alerts for SLO consumption; ticket non-urgent risks; preserve missing-series detection; avoid volatile/high-cardinality labels; do not expose secrets or PHI/PII in notification payloads.

## 3. SLO and burn-rate acceptance

For SLO target \(S\), allowed error fraction \(1-S\). Burn rate equals observed error fraction divided by allowed fraction. For a 99.9% 30-day SLO, 14.4× for one hour consumes about 2% of the budget, while 6× for six hours consumes about 5%. Use paired short and long windows and validate denominator volume. Calibrate thresholds using real traffic and incident history rather than copying examples directly.

| Class | Illustrative windows | Burn | Action |
|---|---|---:|---|
| Fast burn | 1h AND 5m | 14.4× | page |
| Medium burn | 6h AND 30m | 6× | page |
| Slow burn | 3d AND 6h | 1× | ticket |

These are starting points, not production-ready thresholds without SLO and workload validation.

## 4. Alertmanager architecture, HA and delivery

- Use an approved HA topology with peer gossip and tested failure-domain placement.
- Configure Prometheus to send alerts to the intended Alertmanager peers.
- Maintain fallback receiver, distinct backup escalation, stable grouping keys and tested receiver credentials.
- Scope inhibition and silences by service/cluster; require owner, ticket and expiry for maintenance silences.
- Protect APIs and outbound integrations with network controls, TLS and secrets management.
- Track rule firing, notification dispatch, receiver acceptance and human acknowledgement separately.
- Preserve reviewed configuration and a tested rollback plan.

## 5. GitOps production change workflow

```text
Rule and routing PR
  -> lint / promtool / amtool
  -> policy gate / unit tests
  -> security and on-call review
  -> isolated staging deployment
  -> synthetic alert and fallback delivery
  -> no-data / low-traffic / failover drills
  -> change approval
  -> controlled production rollout
  -> monitoring and evidence archive
  -> rollback if acceptance fails
```

The offline policy fixture below does not replace `promtool`, `amtool`, staging integration, HA drills or production readiness review.

## 6. Executable offline capstone lab

Create:

```text
chapter030/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/capstone_gate.py
  tests/test_capstone_gate.py
```

### fixtures/healthy.json

```json
{
  "environment": "staging",
  "service": "postgres-api",
  "owner": "dbre",
  "slo_target": 0.999,
  "window_days": 30,
  "reviewed": true,
  "security_reviewed": true,
  "rollback_tested": true,
  "restore_tested": true,
  "route_tested": true,
  "backup_escalation_tested": true,
  "synthetic_page_received": true,
  "no_data_tested": true,
  "low_traffic_tested": true,
  "incident_drill_completed": true,
  "receiver": "dbre-test",
  "fallback_receiver": "sre-test",
  "labels": [
    "service",
    "team",
    "severity",
    "cluster"
  ],
  "runbook": "https://example.org/runbooks/postgres-api",
  "alerts": [
    {
      "name": "FastBurn",
      "severity": "page",
      "burn_rate": 14.4,
      "long_minutes": 60,
      "short_minutes": 5
    },
    {
      "name": "MediumBurn",
      "severity": "page",
      "burn_rate": 6,
      "long_minutes": 360,
      "short_minutes": 30
    },
    {
      "name": "SlowBurn",
      "severity": "ticket",
      "burn_rate": 1,
      "long_minutes": 4320,
      "short_minutes": 360
    }
  ],
  "noise_budget_pages_per_week": 5,
  "observed_pages_per_week": 2,
  "acknowledgement_minutes": 5,
  "acknowledgement_slo_minutes": 10
}
```

### fixtures/degraded.json

```json
{
  "environment": "staging",
  "service": "postgres-api",
  "owner": "dbre",
  "slo_target": 0.999,
  "window_days": 30,
  "reviewed": true,
  "security_reviewed": true,
  "rollback_tested": false,
  "restore_tested": true,
  "route_tested": false,
  "backup_escalation_tested": false,
  "synthetic_page_received": false,
  "no_data_tested": true,
  "low_traffic_tested": true,
  "incident_drill_completed": true,
  "receiver": "dbre-test",
  "fallback_receiver": "sre-test",
  "labels": [
    "service",
    "team",
    "severity",
    "cluster",
    "request_id"
  ],
  "runbook": "https://example.org/runbooks/postgres-api",
  "alerts": [
    {
      "name": "FastBurn",
      "severity": "page",
      "burn_rate": 14.4,
      "long_minutes": 60,
      "short_minutes": 90
    },
    {
      "name": "MediumBurn",
      "severity": "page",
      "burn_rate": 6,
      "long_minutes": 360,
      "short_minutes": 30
    },
    {
      "name": "SlowBurn",
      "severity": "ticket",
      "burn_rate": 1,
      "long_minutes": 4320,
      "short_minutes": 360
    }
  ],
  "noise_budget_pages_per_week": 5,
  "observed_pages_per_week": 30,
  "acknowledgement_minutes": 5,
  "acknowledgement_slo_minutes": 10
}
```

### scripts/capstone_gate.py

```python
#!/usr/bin/env python3
"""Offline Part 06 capstone policy gate; no Prometheus/Alertmanager network calls."""
import json,sys
from pathlib import Path
FLAGS=("reviewed","security_reviewed","rollback_tested","restore_tested",
"route_tested","backup_escalation_tested","synthetic_page_received",
"no_data_tested","low_traffic_tested","incident_drill_completed")
LABELS={"service","team","severity","cluster","environment","region"}
def check(p):
    errors=[]
    if not isinstance(p,dict): return ["manifest must be object"]
    for k in ("environment","service","owner","runbook","receiver","fallback_receiver"):
        if not isinstance(p.get(k),str) or not p[k]: errors.append("missing "+k)
    for k in FLAGS:
        if p.get(k) is not True: errors.append("gate failed "+k)
    if p.get("receiver")==p.get("fallback_receiver"): errors.append("missing distinct fallback")
    slo=p.get("slo_target")
    if type(slo) not in (int,float) or not 0<slo<1: errors.append("invalid SLO")
    window=p.get("window_days")
    if type(window) is not int or not 1<=window<=90: errors.append("invalid SLO window")
    labels=p.get("labels")
    if not isinstance(labels,list) or not {"service","team","severity","cluster"}.issubset(labels) or not set(labels).issubset(LABELS): errors.append("unsafe alert labels")
    alerts=p.get("alerts")
    if not isinstance(alerts,list) or len(alerts)<2: errors.append("missing alert coverage");alerts=[]
    names=set()
    for i,a in enumerate(alerts):
        tag="alert "+str(i)
        if not isinstance(a,dict): errors.append(tag+" invalid");continue
        n=a.get("name")
        if not isinstance(n,str) or not n or n in names: errors.append(tag+" duplicate/missing name")
        else: names.add(n)
        if a.get("severity") not in ("page","ticket"): errors.append(tag+" invalid severity")
        b=a.get("burn_rate")
        if type(b) not in (int,float) or b<=0: errors.append(tag+" invalid burn")
        short=a.get("short_minutes");long=a.get("long_minutes")
        if type(short) is not int or type(long) is not int or not 0<short<long: errors.append(tag+" invalid windows")
    for k in ("noise_budget_pages_per_week","observed_pages_per_week","acknowledgement_minutes","acknowledgement_slo_minutes"):
        v=p.get(k)
        if type(v) not in (int,float) or v<0: errors.append("invalid "+k)
    if type(p.get("observed_pages_per_week")) in (int,float) and type(p.get("noise_budget_pages_per_week")) in (int,float) and p["observed_pages_per_week"]>p["noise_budget_pages_per_week"]: errors.append("noise budget exceeded")
    if type(p.get("acknowledgement_minutes")) in (int,float) and type(p.get("acknowledgement_slo_minutes")) in (int,float) and p["acknowledgement_minutes"]>p["acknowledgement_slo_minutes"]: errors.append("acknowledgement SLO missed")
    return errors
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 capstone_gate.py fixtures/healthy.json")
    try: findings=check(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as exc: sys.exit("input error: "+str(exc))
    print(json.dumps({"status":"FAIL" if findings else "PASS","findings":findings},indent=2))
    sys.exit(bool(findings))
```

### tests/test_capstone_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from capstone_gate import check
class CapstoneTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def mutate(self,f):
        p=copy.deepcopy(self.p);f(p);return check(p)
    def test_healthy(self): self.assertEqual(check(self.p),[])
    def test_degraded(self): self.assertTrue(check(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_non_object(self): self.assertTrue(check(None))
    def test_owner(self): self.assertTrue(self.mutate(lambda p:p.update(owner="")))
    def test_runbook(self): self.assertTrue(self.mutate(lambda p:p.update(runbook="")))
    def test_review(self): self.assertTrue(self.mutate(lambda p:p.update(reviewed=False)))
    def test_security(self): self.assertTrue(self.mutate(lambda p:p.update(security_reviewed=False)))
    def test_rollback(self): self.assertTrue(self.mutate(lambda p:p.update(rollback_tested=False)))
    def test_restore(self): self.assertTrue(self.mutate(lambda p:p.update(restore_tested=False)))
    def test_route(self): self.assertTrue(self.mutate(lambda p:p.update(route_tested=False)))
    def test_escalation(self): self.assertTrue(self.mutate(lambda p:p.update(backup_escalation_tested=False)))
    def test_page(self): self.assertTrue(self.mutate(lambda p:p.update(synthetic_page_received=False)))
    def test_no_data(self): self.assertTrue(self.mutate(lambda p:p.update(no_data_tested=False)))
    def test_low_traffic(self): self.assertTrue(self.mutate(lambda p:p.update(low_traffic_tested=False)))
    def test_drill(self): self.assertTrue(self.mutate(lambda p:p.update(incident_drill_completed=False)))
    def test_same_receiver(self): self.assertTrue(self.mutate(lambda p:p.update(fallback_receiver="dbre-test")))
    def test_slo(self): self.assertTrue(self.mutate(lambda p:p.update(slo_target=1)))
    def test_window(self): self.assertTrue(self.mutate(lambda p:p.update(window_days=0)))
    def test_labels(self): self.assertTrue(self.mutate(lambda p:p["labels"].append("request_id")))
    def test_no_alerts(self): self.assertTrue(self.mutate(lambda p:p.update(alerts=[])))
    def test_duplicate(self): self.assertTrue(self.mutate(lambda p:p["alerts"][1].update(name="FastBurn")))
    def test_severity(self): self.assertTrue(self.mutate(lambda p:p["alerts"][0].update(severity="debug")))
    def test_burn(self): self.assertTrue(self.mutate(lambda p:p["alerts"][0].update(burn_rate=0)))
    def test_windows(self): self.assertTrue(self.mutate(lambda p:p["alerts"][0].update(short_minutes=90)))
    def test_noise(self): self.assertTrue(self.mutate(lambda p:p.update(observed_pages_per_week=50)))
    def test_ack(self): self.assertTrue(self.mutate(lambda p:p.update(acknowledgement_minutes=50)))
    def test_missing_receiver(self): self.assertTrue(self.mutate(lambda p:p.update(receiver="")))
    def test_negative_budget(self): self.assertTrue(self.mutate(lambda p:p.update(noise_budget_pages_per_week=-1)))
    def test_missing_service(self): self.assertTrue(self.mutate(lambda p:p.update(service="")))
    def test_missing_environment(self): self.assertTrue(self.mutate(lambda p:p.update(environment="")))
if __name__=="__main__": unittest.main()
```

### Execute

```bash
cd chapter030
python3 scripts/capstone_gate.py fixtures/healthy.json
if python3 scripts/capstone_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded acceptance manifest accepted"; exit 1
else
  echo "PASS: degraded manifest rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and **30 automated unit tests pass**. This is a synthetic acceptance gate, not live SLO measurement or paging validation.

## 7. Twenty-four hands-on exercises

1. Define SLO and eligible traffic.
2. Calculate error budget.
3. Review fast-burn rule.
4. Review medium-burn rule.
5. Review slow-burn ticket.
6. Validate low-traffic handling.
7. Validate missing-target alert.
8. Review Prometheus rule evaluation.
9. Review Alertmanager peer topology.
10. Validate fallback routing.
11. Verify test-only contact point.
12. Check notification grouping.
13. Check inhibition safety.
14. Review maintenance silence.
15. Check template payload sensitivity.
16. Review secret rotation.
17. Run test-only page.
18. Check acknowledgement SLO.
19. Measure weekly alert noise.
20. Simulate receiver failure.
21. Simulate PostgreSQL failover.
22. Run healthy acceptance gate.
23. Reject degraded acceptance gate.
24. Execute 30 tests and complete assessment.

## 8. Twenty-four production failure scenarios

| # | Failure | First diagnostic |
|---|---|---|
| 01 | SLO calculation wrong | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 02 | Burn threshold wrong | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 03 | Missing telemetry | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 04 | Scrape target absent | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 05 | Low traffic false page | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 06 | Fast-burn rule not firing | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 07 | Rule evaluation failed | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 08 | Wrong severity route | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 09 | Fallback receiver absent | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 10 | Inhibition suppresses page | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 11 | Silence too broad | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 12 | Webhook 500 | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 13 | Receiver 429 | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 14 | Notification duplicated | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 15 | Peer network partition | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 16 | Alertmanager config invalid | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 17 | Credential leaked | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 18 | PHI in notification | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 19 | Runbook missing | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 20 | On-call unacknowledged | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 21 | Noise budget exceeded | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 22 | Rollback unavailable | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 23 | Restore untested | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |
| 24 | Post-incident evidence missing | Check rule state, telemetry, routing, suppression, receiver, owner and rollback |

## 9. Eight production runbooks

**A. SLO burn incident:** Confirm numerator, denominator, long/short windows, user impact and remaining error budget.

**B. Missing metrics:** Inspect expected target inventory, scrape health, absent series and independent telemetry-health alerts.

**C. Alertmanager routing:** Trace alert labels, child matcher order, fallback, inhibition and silences.

**D. Receiver outage:** Check HTTP status, TLS/auth, retries, test receiver and backup escalation.

**E. HA degradation:** Inspect peer membership, gossip connectivity, notification deduplication and failover.

**F. Alert storm:** Review cardinality, grouping, repeat interval, duplicate rules and noisy thresholds.

**G. Security incident:** Revoke exposed secrets, sanitize payloads, review audit logs and notification destinations.

**H. Rollback/DR:** Validate reviewed rules/config, restore safe revision, test receiver and record recovery evidence.

## 10. Production-style SRE/DBRE incident simulation

**Scenario:** A PostgreSQL primary fails over. The API error ratio breaches a 99.9% SLO while the expected scrape target disappears, a silence hides a critical notification, one Alertmanager peer is partitioned and the primary receiver returns 429. The incident commander must restore accurate impact signals, route a test-only fallback page, coordinate DBRE mitigation, roll back unsafe policy and document recovery.

**Evidence:** incident timeline, SLO budget calculation, Prometheus firing state, Alertmanager routing and silence state, receiver receipt, acknowledgement, recovery, owner approval and follow-up actions.

**Safety:** use only isolated staging and synthetic receivers for drills. No real production failover or paging without explicit operational authorization.

## 11. 100-point final Part 06 assessment

| Domain | Points |
|---|---:|
| SLO/SLI and alert quality | 20 |
| Alertmanager routing, HA and security | 20 |
| Receiver delivery and on-call escalation | 20 |
| Offline capstone gate and 30 tests | 20 |
| Incident simulation, DR and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory: reviewed SLO, tested fallback, scoped inhibition/silences, secrets controls, backup escalation, no-data/low-traffic strategy and rollback evidence. Offline passing results alone do **not** certify production readiness.

## 12. Evidence worksheet

```text
UTC / environment / owner / reviewers:
Service SLO / budget / alert windows:
Prometheus rule validation / missing-series test:
Alertmanager HA / routing / silence / inhibition:
Receiver / fallback / human acknowledgement:
Secret and payload review:
Healthy/degraded gate / 30 tests:
Staging failover / recovery / rollback:
Incident commander / RCA / 100-point score:
```

**Companion:** [Chapter 030 executable Part 06 capstone lab](labs/030-enterprise-alert-engineering-slos-on-call-incident-response-production-capstone-lab.md).

**Part 06 complete. Next:** Chapter 031 — Prometheus Exporters, Node Exporter and Enterprise Infrastructure Metrics Foundations (Part 07 — Exporters and Custom Instrumentation).
