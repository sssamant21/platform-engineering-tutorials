# Chapter 027 — Alertmanager Advanced Routing, Inhibition, Silences, High Availability and Incident Escalation

**Part 06 — Alertmanager and Alert Engineering**  
**Audience:** SRE/DBRE, observability platform engineers, incident commanders.  
**Prerequisites:** Chapter 026, Prometheus alert rules, Python 3.10+.  
**Objective:** Engineer safe multi-team routing, scoped suppression, HA delivery and incident escalation with an auditable rollback process.

## 1. Architecture and advanced delivery flow

```text
Prometheus A / B -> Alertmanager peer A, B, C
                          | gossip + notification log
                          v
             route tree / grouping / deduplication
                  /                \
            DBRE route          SRE route
                  \                /
                   fallback receiver
                          |
              inhibition and silences
                          |
                 incident escalation
```

Prometheus evaluates rules and sends alerts; Alertmanager manages notification dispatch. HA peers exchange state over the cluster protocol and coordinate notification behavior. **Multiple peers do not guarantee zero duplicate notifications**, especially during partitions or delivery retries. Each Prometheus should be configured to send alerts to the intended Alertmanager peers; verify actual discovery and fanout.

## 2. Advanced routing semantics

A route tree has a root receiver and ordered child routes. Matchers select child routes; `continue: true` allows evaluation of later siblings. Without `continue`, matching usually stops sibling traversal. Inherited grouping/timing settings can differ by child. Test representative label sets, missing labels and fallbacks.

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
      matchers: ['team="dbre"', 'severity="page"']
      continue: false
    - receiver: sre-test
      matchers: ['team="sre"', 'severity="page"']
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
  - name: sre-test
    webhook_configs:
      - url: http://webhook:8080/alerts
        send_resolved: true
inhibit_rules:
  - source_matchers: ['severity="page"']
    target_matchers: ['severity="warning"']
    equal: ['alertname', 'cluster', 'service']
```

The example sends DBRE and SRE page-level alerts to **internal test webhook receivers** and uses a fallback for other alerts. The receiver URL is an example local Docker service from Chapter 026, not a production paging destination. Validate syntax with the `amtool` version matching the deployed Alertmanager.

## 3. Inhibition versus silences

**Inhibition** suppresses notifications for target alerts when a source alert is active and configured labels match. The example suppresses a warning with the same `alertname`, `cluster` and `service` while a page-level alert fires. Never use a broad source matcher that can suppress unrelated clusters.

**Silences** are time-bounded suppression rules created through the Alertmanager API/UI or tooling. They need a clear owner, ticket, matcher scope, start/end and expiration. A silence does not delete or resolve a Prometheus alert. Check time zones and post-maintenance expiration.

## 4. HA design and failure modes

- Run two or more supported Alertmanager peers across failure domains.
- Establish peer gossip connectivity and consistent receiver configuration.
- Send alerts to all peers as recommended for the deployment topology.
- Validate network policies, discovery, DNS, TLS/auth and peer status.
- Rehearse one-peer loss, network partition, restart and recovery.
- Monitor notification delivery, retries, peer health and receiver failure.
- Plan escalation independently of the Alertmanager cluster.

A healthy peer count alone does not prove correct HA: test actual delivery and deduplication under failure.

## 5. Production escalation workflow

Use a severity and service ownership matrix. A page should have a primary and backup escalation path, an acknowledgement SLO, an incident commander, a runbook and a safe fallback receiver. Do not rely on a dashboard variable to establish notification authorization or tenant isolation. Limit alert labels and payloads to approved operational metadata.

## 6. Executable offline governance lab

The following JSON is **synthetic policy metadata**, not native Alertmanager YAML. The Python gate validates team routing, fallback, HA review, inhibition equality, silence ownership/expiration and escalation readiness. It does not execute the Alertmanager route engine or verify live gossip/delivery.

Create:

```text
chapter027/
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
  "peer_count": 3,
  "peers_healthy": 3,
  "config_reviewed": true,
  "backup_receiver_tested": true,
  "escalation_tested": true,
  "rollback_tested": true,
  "default_receiver": "fallback-test",
  "receivers": [
    "fallback-test",
    "dbre-test",
    "sre-test"
  ],
  "routes": [
    {
      "receiver": "dbre-test",
      "matchers": {
        "team": "dbre",
        "severity": "page"
      },
      "continue": false
    },
    {
      "receiver": "sre-test",
      "matchers": {
        "team": "sre",
        "severity": "page"
      },
      "continue": false
    }
  ],
  "group_by": [
    "alertname",
    "cluster",
    "service"
  ],
  "group_wait_seconds": 30,
  "group_interval_seconds": 300,
  "repeat_interval_seconds": 14400,
  "inhibitions": [
    {
      "source": {
        "severity": "page"
      },
      "target": {
        "severity": "warning"
      },
      "equal": [
        "alertname",
        "cluster",
        "service"
      ]
    }
  ],
  "silences": [
    {
      "id": "maintenance-window-1",
      "owner": "dbre",
      "reason": "approved maintenance",
      "expires_in_minutes": 60,
      "matchers": {
        "cluster": "lab",
        "service": "postgres"
      },
      "approved": true
    }
  ]
}
```

### fixtures/degraded.json

```json
{
  "owner": "platform-sre",
  "environment": "staging",
  "peer_count": 3,
  "peers_healthy": 1,
  "config_reviewed": true,
  "backup_receiver_tested": true,
  "escalation_tested": false,
  "rollback_tested": true,
  "default_receiver": "missing",
  "receivers": [
    "fallback-test",
    "dbre-test",
    "sre-test"
  ],
  "routes": [
    {
      "receiver": "dbre-test",
      "matchers": {},
      "continue": false
    },
    {
      "receiver": "sre-test",
      "matchers": {
        "team": "sre",
        "severity": "page"
      },
      "continue": false
    }
  ],
  "group_by": [
    "alertname",
    "cluster",
    "service"
  ],
  "group_wait_seconds": 30,
  "group_interval_seconds": 300,
  "repeat_interval_seconds": 14400,
  "inhibitions": [
    {
      "source": {
        "severity": "page"
      },
      "target": {
        "severity": "warning"
      },
      "equal": [
        "alertname"
      ]
    }
  ],
  "silences": [
    {
      "id": "maintenance-window-1",
      "owner": "dbre",
      "reason": "approved maintenance",
      "expires_in_minutes": 0,
      "matchers": {
        "cluster": "lab",
        "service": "postgres"
      },
      "approved": false
    }
  ]
}
```

### scripts/acceptance.py

```python
#!/usr/bin/env python3
"""Offline Alertmanager HA and routing policy acceptance; not native YAML validation."""
import json,sys
from pathlib import Path
def check(p):
    errors=[]
    if not isinstance(p,dict): return ["policy must be object"]
    for k in ("owner","environment"):
        if not isinstance(p.get(k),str) or not p[k]: errors.append("missing "+k)
    for k in ("config_reviewed","backup_receiver_tested","escalation_tested","rollback_tested"):
        if p.get(k) is not True: errors.append("unverified "+k)
    count=p.get("peer_count");healthy=p.get("peers_healthy")
    if type(count) is not int or count<2: errors.append("insufficient peers")
    if type(healthy) is not int or type(count) is not int or healthy<2 or healthy>count: errors.append("HA unhealthy")
    receivers=p.get("receivers",[])
    if not isinstance(receivers,list) or not receivers: errors.append("no receivers");receivers=[]
    if len(receivers)!=len(set(receivers)): errors.append("duplicate receivers")
    if p.get("default_receiver") not in receivers: errors.append("fallback missing")
    groups=p.get("group_by",[])
    if not isinstance(groups,list) or not {"alertname","cluster","service"}.issubset(groups): errors.append("unsafe grouping")
    for k,minimum in (("group_wait_seconds",0),("group_interval_seconds",1),("repeat_interval_seconds",1)):
        v=p.get(k)
        if type(v) is not int or v<minimum: errors.append("invalid "+k)
    routes=p.get("routes",[])
    if not isinstance(routes,list) or not routes: errors.append("no routes");routes=[]
    for i,r in enumerate(routes):
        if not isinstance(r,dict): errors.append("bad route "+str(i));continue
        if r.get("receiver") not in receivers: errors.append("unknown receiver "+str(i))
        m=r.get("matchers")
        if not isinstance(m,dict) or not m.get("team") or not m.get("severity"): errors.append("unscoped route "+str(i))
        if r.get("continue") is not False: errors.append("unsafe continue "+str(i))
    inhibitions=p.get("inhibitions",[])
    if not isinstance(inhibitions,list) or not inhibitions: errors.append("no inhibition");inhibitions=[]
    for i,x in enumerate(inhibitions):
        if not isinstance(x,dict) or x.get("source",{}).get("severity")!="page" or x.get("target",{}).get("severity")!="warning" or not {"alertname","cluster","service"}.issubset(x.get("equal",[]) if isinstance(x.get("equal",[]),list) else []):
            errors.append("unsafe inhibition "+str(i))
    silences=p.get("silences",[])
    if not isinstance(silences,list): errors.append("bad silences");silences=[]
    for i,s in enumerate(silences):
        if not isinstance(s,dict): errors.append("bad silence "+str(i));continue
        for k in ("id","owner","reason"):
            if not isinstance(s.get(k),str) or not s[k]: errors.append("silence missing "+k)
        if s.get("approved") is not True: errors.append("unapproved silence")
        expiry=s.get("expires_in_minutes")
        if type(expiry) is not int or not 1<=expiry<=1440: errors.append("unsafe silence expiry")
        m=s.get("matchers")
        if not isinstance(m,dict) or not m.get("cluster") or not m.get("service"): errors.append("broad silence")
    return errors
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 acceptance.py fixtures/healthy.json")
    try: errors=check(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as e: sys.exit("input error: "+str(e))
    print(json.dumps({"status":"FAIL" if errors else "PASS","errors":errors},indent=2))
    sys.exit(bool(errors))
```

### tests/test_acceptance.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from acceptance import check
class AlertmanagerTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def mutate(self,f):
        p=copy.deepcopy(self.p);f(p);return check(p)
    def test_healthy(self): self.assertEqual(check(self.p),[])
    def test_degraded(self): self.assertTrue(check(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_not_object(self): self.assertTrue(check(None))
    def test_owner(self): self.assertTrue(self.mutate(lambda p:p.update(owner="")))
    def test_review(self): self.assertTrue(self.mutate(lambda p:p.update(config_reviewed=False)))
    def test_backup(self): self.assertTrue(self.mutate(lambda p:p.update(backup_receiver_tested=False)))
    def test_escalation(self): self.assertTrue(self.mutate(lambda p:p.update(escalation_tested=False)))
    def test_rollback(self): self.assertTrue(self.mutate(lambda p:p.update(rollback_tested=False)))
    def test_peer_count(self): self.assertTrue(self.mutate(lambda p:p.update(peer_count=1)))
    def test_peer_health(self): self.assertTrue(self.mutate(lambda p:p.update(peers_healthy=1)))
    def test_peer_overcount(self): self.assertTrue(self.mutate(lambda p:p.update(peers_healthy=4)))
    def test_receivers(self): self.assertTrue(self.mutate(lambda p:p.update(receivers=[])))
    def test_duplicate_receivers(self): self.assertTrue(self.mutate(lambda p:p["receivers"].append("dbre-test")))
    def test_fallback(self): self.assertTrue(self.mutate(lambda p:p.update(default_receiver="missing")))
    def test_grouping(self): self.assertTrue(self.mutate(lambda p:p.update(group_by=["alertname"])))
    def test_group_wait(self): self.assertTrue(self.mutate(lambda p:p.update(group_wait_seconds=-1)))
    def test_group_interval(self): self.assertTrue(self.mutate(lambda p:p.update(group_interval_seconds=0)))
    def test_repeat(self): self.assertTrue(self.mutate(lambda p:p.update(repeat_interval_seconds=0)))
    def test_routes(self): self.assertTrue(self.mutate(lambda p:p.update(routes=[])))
    def test_receiver(self): self.assertTrue(self.mutate(lambda p:p["routes"][0].update(receiver="wrong")))
    def test_matchers(self): self.assertTrue(self.mutate(lambda p:p["routes"][0].update(matchers={})))
    def test_continue(self): self.assertTrue(self.mutate(lambda p:p["routes"][0].update({"continue":True})))
    def test_inhibition(self): self.assertTrue(self.mutate(lambda p:p["inhibitions"][0].update(equal=["alertname"])))
    def test_silence_expiry(self): self.assertTrue(self.mutate(lambda p:p["silences"][0].update(expires_in_minutes=0)))
    def test_silence_approval(self): self.assertTrue(self.mutate(lambda p:p["silences"][0].update(approved=False)))
    def test_broad_silence(self): self.assertTrue(self.mutate(lambda p:p["silences"][0].update(matchers={})))
if __name__=="__main__": unittest.main()
```

### Run

```bash
cd chapter027
python3 scripts/acceptance.py fixtures/healthy.json
if python3 scripts/acceptance.py fixtures/degraded.json; then
  echo "FAIL: degraded policy accepted"; exit 1
else
  echo "PASS: degraded policy rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and **26 automated tests pass**.

## 7. Optional staging Alertmanager integration

1. Start Chapter 026's isolated stack and use a test-only webhook receiver.
2. Validate the native YAML with `amtool check-config`.
3. Apply approved child routes and verify representative DBRE/SRE/fallback alerts.
4. Create a narrowly scoped, expiring test silence and confirm suppressed notification only.
5. Test inhibition with matching cluster/service and confirm unrelated alerts still notify.
6. Add HA peers in a dedicated staging environment; validate peer health, notification deduplication and failover.
7. Restore the reviewed configuration and verify test notifications after rollback.

Do not generate synthetic production pages or silence real production alerts.

## 8. Twenty-four hands-on exercises

1. Trace Alertmanager route traversal.
2. Design fallback receiver.
3. Add DBRE page route.
4. Add SRE page route.
5. Compare continue true and false.
6. Define grouping keys.
7. Tune group wait.
8. Tune group interval.
9. Tune repeat interval.
10. Model severity inhibition.
11. Require equal labels.
12. Create scoped maintenance silence.
13. Validate silence expiration.
14. Review silence audit.
15. Explain HA gossip membership.
16. Plan Prometheus fanout to all peers.
17. Validate cluster peer count.
18. Review notification log deduplication.
19. Test receiver outage tabletop.
20. Test failover and split-brain tabletop.
21. Run healthy policy fixture.
22. Reject degraded fixture.
23. Execute 26 automated tests.
24. Complete incident escalation review.

## 9. Twenty-four production failure scenarios

| # | Failure | Initial diagnostic |
|---|---|---|
| 01 | Wrong child route order | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 02 | Missing fallback receiver | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 03 | Unexpected continue duplicates notifications | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 04 | Team matcher missing | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 05 | Severity label missing | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 06 | Grouping collapses services | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 07 | Grouping explodes cardinality | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 08 | Repeat interval too short | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 09 | Notification suppressed by inhibition | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 10 | Inhibition lacks cluster equality | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 11 | Silence too broad | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 12 | Silence without expiration | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 13 | Silence approval missing | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 14 | HA peer gossip blocked | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 15 | Only one healthy Alertmanager peer | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 16 | Prometheus targets only one peer | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 17 | Peer version mismatch | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 18 | Notification log inconsistency | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 19 | Duplicate paging during failover | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 20 | Receiver webhook 5xx | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 21 | Receiver secret rotation failure | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 22 | Split-brain peer partition | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 23 | Alertmanager config reload rejected | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |
| 24 | Escalation owner unavailable | Inspect Alertmanager route, labels, suppression state, peers and receiver logs |

## 10. Eight production runbooks

**A. Routing regression:** Inspect alert labels, ordered child routes, matcher syntax, fallback and continue semantics.

**B. Inhibition misfire:** Compare firing source, target matchers and equal labels; narrow policy.

**C. Silence outage:** Audit matcher scope, owner, reason, start/end and approval; expire unsafe silence.

**D. HA peer failure:** Inspect cluster status, peer discovery, gossip ports, network policy and logs.

**E. Duplicate notifications:** Review peer connectivity, notification log, group labels, receiver retries and rule duplication.

**F. Escalation failure:** Verify test receiver, backup on-call route, acknowledgement and incident commander.

**G. Secret compromise:** Rotate webhook credentials, restrict receiver network and audit notification payloads.

**H. Rollback:** Restore reviewed config, run amtool validation, reload safely and verify both fallback and team routes.

## 11. SRE/DBRE incident simulation

During a PostgreSQL failover, a page-level alert fires, a broad inhibition rule hides unrelated warnings, one Alertmanager peer becomes isolated and the primary on-call receiver is unavailable. Investigate routing, peer status and suppression separately. Restore safe receiver routing, expire the unsafe silence/inhibition, use backup escalation and verify delivery in staging.

## 12. 100-point assessment

| Domain | Points |
|---|---:|
| Routing and matcher correctness | 20 |
| Inhibition and silence safety | 20 |
| HA topology and failure recovery | 20 |
| Offline governance and 26 tests | 20 |
| Incident escalation, runbooks and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory: safe fallback, cluster-scoped suppression, expiring silences, tested escalation, documented HA plan and rollback.

## 13. Evidence worksheet

```text
UTC / owner / Alertmanager version:
HA peer topology / gossip checks:
Prometheus fanout targets:
Routing and fallback label test cases:
Inhibition and silence scope / expiration:
Test receiver and backup escalation:
Healthy/degraded gate / 26 tests:
Incident drill / rollback / reviewer / score:
```

**Companion:** [Chapter 027 executable advanced routing lab](labs/027-alertmanager-advanced-routing-inhibition-silences-high-availability-incident-escalation-lab.md).

**Next:** Chapter 028 — Alertmanager Notification Templates, Receiver Integrations, Security and Delivery Reliability.
