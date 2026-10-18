# Chapter 026 — Prometheus Alertmanager Architecture, Installation and Notification Routing Fundamentals

**Part 06 — Alertmanager and Alert Engineering**  
**Audience:** SRE, DBRE, platform engineering, on-call operators.  
**Prerequisites:** Prometheus Chapters 011–020, Grafana Chapters 021–025, Docker Compose, Python 3.10+.  
**Objective:** Deploy a safe local Prometheus–Alertmanager pipeline, understand notification routing, grouping, inhibition and silences, and validate recovery procedures.

## 1. Architecture and responsibilities

```text
exporters -> Prometheus scrape/TSDB -> rule evaluation
                                        |
                               pending / firing alerts
                                        |
                                 Alertmanager API
                                        |
                          routing tree and grouping
                                        |
                         inhibition / active silences
                                        |
                           receiver integrations
                                        |
                        test webhook / incident desk
```

Prometheus evaluates alert expressions and sends firing/resolved alerts to Alertmanager. Alertmanager **does not evaluate PromQL**; it deduplicates, groups, routes and dispatches notifications. Alertmanager silences and inhibition affect notifications, not Prometheus rule evaluation. A Prometheus alert can be firing while its notification is inhibited, silenced or waiting for grouping.

## 2. Core concepts

| Concept | Behavior | SRE concern |
|---|---|---|
| Alert identity | label set identifies alert instance | avoid volatile labels |
| Grouping | coalesces alerts with common labels | preserve service/cluster |
| group_wait | delay before initial group notification | trade latency for grouping |
| group_interval | interval for changes to an existing group | reduce notification bursts |
| repeat_interval | repeat unchanged firing notifications | coordinate with retention and escalation |
| Routing tree | parent/child matcher traversal | safe fallback route |
| Inhibition | suppress target notifications when matching source fires | constrain equality labels |
| Silence | temporary matcher-based suppression | expiry, author and audit |
| HA gossip | peer coordination and notification deduplication | test network and failover |

Routing child evaluation order matters. A matching child route ordinarily stops sibling evaluation unless `continue: true`; parent routes provide inherited configuration. Silence and inhibition must not be used as substitutes for fixing broken signals.

## 3. Isolated runnable local stack

**Safety:** This lab uses only an internal test webhook; no external paging or production receivers. Prometheus and Alertmanager ports bind to localhost. Versions below are pinned examples, not an assertion of current security support; review advisories before production.

Project:

```text
chapter026/
  docker-compose.yml
  prometheus.yml
  rules.yml
  alertmanager.yml
  webhook.py
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/policy_gate.py
  tests/test_policy_gate.py
```

### docker-compose.yml

```yaml
services:
  prometheus:
    image: prom/prometheus:v2.55.1
    command: ["--config.file=/etc/prometheus/prometheus.yml"]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./rules.yml:/etc/prometheus/rules.yml:ro
    ports: ["127.0.0.1:9090:9090"]
    networks: [lab]
  alertmanager:
    image: prom/alertmanager:v0.28.1
    command: ["--config.file=/etc/alertmanager/alertmanager.yml"]
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    ports: ["127.0.0.1:9093:9093"]
    networks: [lab]
  webhook:
    image: python:3.12-alpine
    command: ["python", "/app/webhook.py"]
    volumes:
      - ./webhook.py:/app/webhook.py:ro
    networks: [lab]
networks:
  lab: {}
```

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
rule_files:
  - /etc/prometheus/rules.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ['prometheus:9090']
```

### rules.yml

```yaml
groups:
  - name: sre-dbre-demo
    rules:
      - alert: DemoAlwaysFiring
        expr: vector(1)
        for: 1m
        labels:
          team: dbre
          severity: page
          cluster: lab
          service: demo
        annotations:
          summary: "Synthetic test alert - local lab only"
          runbook_url: "https://example.org/runbooks/demo"
```

### alertmanager.yml

```yaml
global:
  resolve_timeout: 5m
route:
  receiver: fallback-test
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - receiver: dbre-test
      matchers:
        - 'team="dbre"'
        - 'severity="page"'
      continue: false
receivers:
  - name: fallback-test
    webhook_configs:
      - url: http://webhook:8080/alerts
        send_resolved: true
  - name: dbre-test
    webhook_configs:
      - url: http://webhook:8080/alerts
        send_resolved: true
inhibit_rules:
  - source_matchers: ['severity="page"']
    target_matchers: ['severity="warning"']
    equal: ['alertname', 'cluster', 'service']
```

### webhook.py

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        size=int(self.headers.get("Content-Length","0"))
        if size>65536:
            self.send_error(413);return
        try:
            body=json.loads(self.rfile.read(size))
            alerts=body.get("alerts",[])
            print(json.dumps({"receiver":body.get("receiver"),"statuses":[a.get("status") for a in alerts],"count":len(alerts)}),flush=True)
        except (ValueError,TypeError):
            self.send_error(400);return
        self.send_response(200);self.end_headers();self.wfile.write(b"ok")
HTTPServer(("0.0.0.0",8080),Handler).serve_forever()
```

Start and validate:

```bash
cd chapter026
docker compose config
docker compose run --rm --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose run --rm --entrypoint promtool prometheus check rules /etc/prometheus/rules.yml
docker compose run --rm --entrypoint amtool alertmanager check-config /etc/alertmanager/alertmanager.yml
docker compose up -d
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS http://127.0.0.1:9093/-/ready
curl -fsS http://127.0.0.1:9090/api/v1/alerts
curl -fsS http://127.0.0.1:9093/api/v2/alerts
docker compose logs --tail=100 webhook
```

The synthetic `vector(1)` rule should fire after its one-minute pending period and eventually be delivered to the internal `dbre-test` receiver. Depending on scrape/evaluation and grouping delays, allow additional time. A successful HTTP response does not prove end-to-end paging; inspect the webhook logs for receipt. Never point this test rule at a production receiver.

## 4. Route matching and grouping

The root route is a fallback; the DBRE child route matches `team=dbre` and `severity=page`. The route groups by alert name, cluster and service, preventing unrelated service incidents from being collapsed into a single group. The inhibition rule suppresses warning notifications for the same alertname/cluster/service while a page-level source alert is active; review this logic carefully for real services.

A missing `team` or `severity` label may route to fallback. Label values should be stable, low cardinality, and free of PHI/PII. Treat notification payloads as potentially sensitive.

## 5. High availability and production design

Deploy at least two Alertmanager instances for resilience, configure each Prometheus to send alerts to all intended Alertmanager peers, establish reliable peer discovery/gossip, and validate notification deduplication under failure. Check network policy, TLS/auth, persistent state and notification log behavior. Do not assume that simply placing two instances behind a load balancer provides correct HA semantics. Test partial outages and recovery in staging.

Protect the API and UI with authenticated ingress; do not expose the administrative API directly. Back up relevant configuration and operational state, and maintain reviewed receiver credentials in a secret manager.

## 6. Offline policy contract and governance gate

This JSON is a **teaching policy fixture**, not the native Alertmanager YAML schema. The Python gate checks governance invariants; native config validation is handled by `amtool`.

### fixtures/healthy.json

```json
{
  "route": {
    "receiver": "fallback-test",
    "group_by": [
      "alertname",
      "cluster",
      "service"
    ],
    "group_wait_seconds": 30,
    "group_interval_seconds": 300,
    "repeat_interval_seconds": 14400,
    "routes": [
      {
        "receiver": "dbre-test",
        "matchers": {
          "team": "dbre",
          "severity": "page"
        },
        "continue": false
      }
    ]
  },
  "receivers": [
    "fallback-test",
    "dbre-test"
  ],
  "inhibition": [
    {
      "source_severity": "page",
      "target_severity": "warning",
      "equal": [
        "alertname",
        "cluster",
        "service"
      ]
    }
  ],
  "required_labels": [
    "team",
    "severity",
    "cluster",
    "service"
  ],
  "external_delivery": false,
  "owner": "platform-sre",
  "reviewed": true,
  "rollback_tested": true
}
```

### fixtures/degraded.json

```json
{
  "route": {
    "receiver": "missing",
    "group_by": [
      "alertname"
    ],
    "group_wait_seconds": 30,
    "group_interval_seconds": 300,
    "repeat_interval_seconds": 0,
    "routes": [
      {
        "receiver": "unknown",
        "matchers": {
          "team": "dbre",
          "severity": "page"
        },
        "continue": false
      }
    ]
  },
  "receivers": [
    "fallback-test",
    "dbre-test"
  ],
  "inhibition": [
    {
      "source_severity": "page",
      "target_severity": "warning",
      "equal": [
        "alertname",
        "cluster",
        "service"
      ]
    }
  ],
  "required_labels": [
    "team",
    "severity",
    "cluster",
    "service"
  ],
  "external_delivery": false,
  "owner": "platform-sre",
  "reviewed": false,
  "rollback_tested": false
}
```

### scripts/policy_gate.py

```python
#!/usr/bin/env python3
"""Offline policy fixture gate; not an Alertmanager YAML parser."""
import json,sys
from pathlib import Path
def check(p):
    issues=[]
    if not isinstance(p,dict): return ["policy must be object"]
    if not isinstance(p.get("owner"),str) or not p["owner"]: issues.append("missing owner")
    for k in ("reviewed","rollback_tested"):
        if p.get(k) is not True: issues.append("missing "+k)
    if p.get("external_delivery") is not False: issues.append("external delivery prohibited in lab")
    receivers=p.get("receivers",[])
    if not isinstance(receivers,list) or not receivers or any(not isinstance(x,str) or not x for x in receivers):
        issues.append("invalid receivers");receivers=[]
    if len(set(receivers))!=len(receivers): issues.append("duplicate receivers")
    route=p.get("route",{})
    if not isinstance(route,dict): issues.append("missing route");route={}
    if route.get("receiver") not in receivers: issues.append("unknown default receiver")
    groups=route.get("group_by")
    if not isinstance(groups,list) or not {"alertname","cluster","service"}.issubset(groups): issues.append("unsafe grouping")
    for key,low in (("group_wait_seconds",0),("group_interval_seconds",1),("repeat_interval_seconds",1)):
        val=route.get(key)
        if type(val) is not int or val<low: issues.append("invalid "+key)
    children=route.get("routes",[])
    if not isinstance(children,list): issues.append("invalid child routes");children=[]
    for i,r in enumerate(children):
        if not isinstance(r,dict): issues.append("invalid child route");continue
        if r.get("receiver") not in receivers: issues.append("unknown child receiver "+str(i))
        m=r.get("matchers")
        if not isinstance(m,dict) or not m.get("team") or not m.get("severity"): issues.append("unscoped child route "+str(i))
        if r.get("continue") is not False: issues.append("unexpected continue "+str(i))
    labels=p.get("required_labels",[])
    if not isinstance(labels,list) or not {"team","severity","cluster","service"}.issubset(labels): issues.append("missing required labels")
    inhibit=p.get("inhibition",[])
    if not isinstance(inhibit,list) or not inhibit: issues.append("no inhibition policy");inhibit=[]
    for i,r in enumerate(inhibit):
        if not isinstance(r,dict) or r.get("source_severity")!="page" or r.get("target_severity")!="warning" or not {"alertname","cluster","service"}.issubset(r.get("equal",[]) if isinstance(r.get("equal",[]),list) else []):
            issues.append("unsafe inhibition "+str(i))
    return issues
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 policy_gate.py fixtures/healthy.json")
    try: issues=check(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as e: sys.exit("input error: "+str(e))
    print(json.dumps({"status":"FAIL" if issues else "PASS","issues":issues},indent=2))
    sys.exit(bool(issues))
```

### tests/test_policy_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from policy_gate import check
class PolicyTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def mutate(self,fn):
        d=copy.deepcopy(self.p);fn(d);return check(d)
    def test_valid(self): self.assertEqual(check(self.p),[])
    def test_degraded(self): self.assertTrue(check(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_non_object(self): self.assertTrue(check(None))
    def test_owner(self): self.assertTrue(self.mutate(lambda p:p.update(owner="")))
    def test_review(self): self.assertTrue(self.mutate(lambda p:p.update(reviewed=False)))
    def test_rollback(self): self.assertTrue(self.mutate(lambda p:p.update(rollback_tested=False)))
    def test_external(self): self.assertTrue(self.mutate(lambda p:p.update(external_delivery=True)))
    def test_no_receivers(self): self.assertTrue(self.mutate(lambda p:p.update(receivers=[])))
    def test_duplicate_receivers(self): self.assertTrue(self.mutate(lambda p:p["receivers"].append("dbre-test")))
    def test_default(self): self.assertTrue(self.mutate(lambda p:p["route"].update(receiver="missing")))
    def test_group(self): self.assertTrue(self.mutate(lambda p:p["route"].update(group_by=["alertname"])))
    def test_group_wait(self): self.assertTrue(self.mutate(lambda p:p["route"].update(group_wait_seconds=-1)))
    def test_group_interval(self): self.assertTrue(self.mutate(lambda p:p["route"].update(group_interval_seconds=0)))
    def test_repeat(self): self.assertTrue(self.mutate(lambda p:p["route"].update(repeat_interval_seconds=0)))
    def test_bad_children(self): self.assertTrue(self.mutate(lambda p:p["route"].update(routes="bad")))
    def test_unknown_child(self): self.assertTrue(self.mutate(lambda p:p["route"]["routes"][0].update(receiver="wrong")))
    def test_unscoped(self): self.assertTrue(self.mutate(lambda p:p["route"]["routes"][0].update(matchers={})))
    def test_continue(self): self.assertTrue(self.mutate(lambda p:p["route"]["routes"][0].update(continue_=True) or p["route"]["routes"][0].update({"continue":True})))
    def test_labels(self): self.assertTrue(self.mutate(lambda p:p.update(required_labels=["severity"])))
    def test_no_inhibition(self): self.assertTrue(self.mutate(lambda p:p.update(inhibition=[])))
    def test_wrong_inhibition(self): self.assertTrue(self.mutate(lambda p:p["inhibition"][0].update(source_severity="warning")))
    def test_missing_equal(self): self.assertTrue(self.mutate(lambda p:p["inhibition"][0].update(equal=["alertname"])))
    def test_empty_route(self): self.assertTrue(self.mutate(lambda p:p.update(route={})))
    def test_valid_second_route(self): self.assertEqual(self.mutate(lambda p:p["route"]["routes"].append({"receiver":"fallback-test","matchers":{"team":"sre","severity":"ticket"},"continue":False})),[])
if __name__=="__main__": unittest.main()
```

Run offline:

```bash
cd chapter026
python3 scripts/policy_gate.py fixtures/healthy.json
if python3 scripts/policy_gate.py fixtures/degraded.json; then
  echo "FAIL: degraded routing accepted"; exit 1
else
  echo "PASS: degraded routing rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and **24 automated tests pass**. Offline policy tests do not establish live notification delivery or Prometheus rule correctness.

## 7. Twenty-four hands-on exercises

1. Trace Prometheus rule evaluation to Alertmanager delivery.
2. Explain alert state versus notification state.
3. Deploy isolated Docker Compose stack.
4. Inspect Alertmanager web UI.
5. Check /-/ready and /-/healthy.
6. Validate configuration using amtool.
7. Validate Prometheus rules with promtool.
8. Inspect Prometheus Alertmanagers status.
9. Inspect firing alert via Prometheus API.
10. Inspect grouped alerts in Alertmanager.
11. Explain grouping and label identity.
12. Design root fallback receiver.
13. Design DBRE team route.
14. Compare equality and regex matchers.
15. Demonstrate route traversal and continue.
16. Tune group_wait and group_interval.
17. Explain repeat_interval semantics.
18. Observe resolved webhook event.
19. Simulate warning inhibition.
20. Review silence matchers and expiration.
21. Validate local-only network and ports.
22. Run offline policy gate.
23. Execute 24 automated tests.
24. Perform incident and rollback tabletop.

## 8. Twenty-four production failure scenarios

| # | Scenario | Initial diagnostic |
|---|---|---|
| 01 | Prometheus cannot reach Alertmanager | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 02 | Alertmanager config invalid | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 03 | Alertmanager container crashloop | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 04 | Alertmanager UI unavailable | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 05 | Alert rule never fires | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 06 | Rule stuck pending | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 07 | Webhook receiver unavailable | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 08 | Wrong receiver selected | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 09 | Fallback route missing | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 10 | Grouping merges unrelated services | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 11 | Excessive duplicate pages | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 12 | Resolved notification missing | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 13 | Alertmanager restart causes repeated notification | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 14 | Inhibition suppresses unrelated warning | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 15 | Silence matches too broadly | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 16 | Silence expires unexpectedly | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 17 | External labels missing | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 18 | High-cardinality alert labels | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 19 | Peer discovery failure in HA | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 20 | Split-brain notification duplication | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 21 | TLS or auth mismatch | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 22 | Receiver secret leaked | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 23 | Prometheus rule reload fails | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |
| 24 | Rollback breaks routing | Check Prometheus alert state, Alertmanager API, route labels, silence and receiver logs |

## 9. Eight production runbooks

**A. No notifications:** Check Prometheus /api/v1/alerts, Alertmanager targets, /api/v2/alerts, routing and receiver logs.

**B. Wrong routing:** Inspect label set, route matchers, fallback receiver, traversal and continue flags.

**C. Alert storm:** Audit label cardinality, grouping, repeat interval, duplicate rules, inhibition and silences.

**D. Inhibition issue:** Compare source/target severities, equal labels and whether source alert is actually firing.

**E. Silence incident:** Inspect matcher breadth, author, expiration, timezone and documented approval.

**F. Receiver failure:** Check network, HTTP status, retries, receiver logs and safe escalation; rotate leaked secrets.

**G. HA incident:** Review gossip peer health, notification log behavior, persistent state and load balancing.

**H. Safe rollback:** Validate config, retain last known-good file, reload safely, test fallback and DBRE routes.

## 10. Incident simulation

A PostgreSQL cluster fails over, creating multiple down-target alerts. An incorrectly broad silence suppresses all DBRE notifications while the webhook receiver is also unhealthy. Investigate Prometheus firing state separately from Alertmanager routing and suppression. Narrow the silence, restore the test receiver, verify delivery and document the incident. **Run only in the isolated lab/staging environment.**

## 11. 100-point acceptance assessment

| Domain | Points |
|---|---:|
| Prometheus–Alertmanager architecture and states | 20 |
| Routing, grouping, inhibition and silences | 20 |
| Local deployment, config validation and safety | 20 |
| Offline governance and 24 automated tests | 20 |
| Troubleshooting, runbooks, HA and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory: no real paging endpoints, local-only published ports, tested fallback route, documented silence policy and rollback plan.

## 12. Evidence worksheet

```text
UTC / operator / environment:
Prometheus and Alertmanager versions:
Config validation (promtool/amtool):
Prometheus firing alert / Alertmanager API:
Matched receiver / grouping / inhibition / silences:
Webhook receipt / resolved notification:
Healthy/degraded policy gate / 24 tests:
Incident drill / rollback / reviewer / score:
```

**Companion:** [Chapter 026 executable lab](labs/026-prometheus-alertmanager-architecture-installation-notification-routing-fundamentals-lab.md).

**Next:** Chapter 027 — Alertmanager Advanced Routing, Inhibition, Silences, High Availability and Incident Escalation.
