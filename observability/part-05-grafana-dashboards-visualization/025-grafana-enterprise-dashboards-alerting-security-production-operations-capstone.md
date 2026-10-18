# Chapter 025 — Grafana Enterprise Dashboards, Alerting, Security and Production Operations Capstone

**Part 05 — Grafana Dashboards and Visualization: FINAL CAPSTONE**  
**Audience:** SRE/DBRE, enterprise observability, incident management, platform security.  
**Prerequisites:** Chapters 021–024; Python 3.10+; approved staging Grafana for optional live drills.  
**Goal:** Integrate architecture, dashboard engineering, GitOps, alerting, security, HA, incident response and rollback into a production acceptance process.

## 1. Reference architecture

```text
Engineers / SSO / HTTPS ingress
               |
       Grafana HA instances
               |
    Shared SQL metadata database
      /                 \
  GitOps provisioning   Alert evaluation
      |                      |
 Dashboards -> datasource    notification policies
      |                      |
 Prometheus/Loki/etc       test paging receivers
      |                      |
 DB exporters / apps     incident runbooks
```

Grafana visualizes telemetry and maintains its own metadata; Prometheus stores metric samples. Use supported external SQL metadata storage for multi-instance Grafana, consistent secrets/encryption settings, health checks, backups, TLS, least privilege and environment-specific rollout controls. **A passing synthetic lab does not certify production HA, alert delivery, or recovery.**

## 2. Acceptance criteria

| Capability | Required evidence | Failure response |
|---|---|---|
| Architecture/HA | staging failover and DB connectivity | block promotion |
| Security | SSO/RBAC, secrets scan, tenant boundaries | revoke and remediate |
| Datasources | authorized read-only query and freshness | investigate network/auth |
| Dashboards | reviewed UIDs, scoped variables, units | revert Git revision |
| Performance | query budget, refresh, backend cost | optimize or rollback |
| Alerting | No Data/Error, test receiver, routing | restore backup route |
| GitOps | PR approval, desired/live reconciliation | freeze promotion |
| DR | tested backup restore and rollback | fail acceptance |

## 3. Enterprise security and governance

- Restrict administrative access with SSO/MFA where supported; use service accounts with narrow permissions.
- Separate Grafana folders and datasources by team/tenant; **dashboard variables are not authorization boundaries**.
- Use a secrets manager for datasource credentials, notification tokens and encryption keys. Do not commit them to Git.
- Review audit capability and retention for the deployed Grafana edition.
- Validate plugin versions and image advisories; stage upgrades and maintain backups before metadata schema changes.
- Protect notification payloads from sensitive identifiers, PHI/PII and raw database queries.

## 4. SRE/DBRE operational dashboard contract

PostgreSQL: exporter target health, availability, replication lag, connection saturation, deadlocks, long-running queries, WAL/storage, backups and failover evidence. Redis: exporter health, memory usage, evictions, command latency, replication, persistence and cluster availability. Validate exact metric names against exporter version and deployment. Show **no data** separately from **zero**. Include service owner, SLO, incident runbook and last reviewed Git revision.

## 5. Alerting and incident workflows

Grafana-managed and Prometheus-managed alerts have distinct evaluation ownership. Record evaluator, rule UID, datasource, state handling, contact points, notification policy, grouping, repeat interval, silences/mute timings and backup escalation. Test with non-production receivers. Verify No Data/Error behavior and ensure disappeared scrape targets are detected using expected-target inventory rather than only `up == 0`.

## 6. GitOps and change management

```text
PR -> JSON/policy validation -> PromQL/staging tests
   -> security review -> staging provisioning
   -> alert delivery and rollback drill
   -> change approval -> production canary
   -> operational verification -> evidence archive
```

Do not use simultaneous uncontrolled API, Terraform and file provisioning for the same dashboard. Identify the authoritative controller. Preserve last known-good image, configuration, Grafana DB backup, provisioning Git revision and datasource credentials.

## 7. Complete executable offline capstone

This **Python standard-library governance model** checks synthetic approval evidence, dashboard ownership, UID uniqueness, refresh/query budgets, alert routes and recovery flags. It does **not** connect to Grafana, run PromQL, perform backups or deliver pages.

Project structure:

```text
chapter025/
  fixtures/healthy.json
  fixtures/degraded.json
  scripts/acceptance.py
  tests/test_acceptance.py
```

### fixtures/healthy.json

```json
{
  "environment": "staging",
  "owner": "observability-sre",
  "grafana_version_reviewed": true,
  "high_availability_reviewed": true,
  "backup_restore_tested": true,
  "rollback_tested": true,
  "secret_scan_passed": true,
  "rbac_reviewed": true,
  "datasource_isolation_tested": true,
  "query_budget_passed": true,
  "alert_delivery_tested": true,
  "missing_data_tested": true,
  "incident_drill_completed": true,
  "gitops_approval": true,
  "dashboards": [
    {
      "uid": "postgres-overview",
      "owner": "dbre",
      "panels": 12,
      "refresh_seconds": 60,
      "query_cost": 20
    },
    {
      "uid": "redis-overview",
      "owner": "dbre",
      "panels": 9,
      "refresh_seconds": 60,
      "query_cost": 15
    }
  ],
  "query_budget": 100,
  "alerts": [
    {
      "name": "PostgresUnavailable",
      "owner": "dbre",
      "receiver": "dbre-test-pager",
      "route_tested": true,
      "runbook": "https://example.org/runbooks/postgres"
    },
    {
      "name": "RedisUnavailable",
      "owner": "dbre",
      "receiver": "dbre-test-pager",
      "route_tested": true,
      "runbook": "https://example.org/runbooks/redis"
    }
  ]
}
```

### fixtures/degraded.json

```json
{
  "environment": "staging",
  "owner": "observability-sre",
  "grafana_version_reviewed": true,
  "high_availability_reviewed": true,
  "backup_restore_tested": false,
  "rollback_tested": true,
  "secret_scan_passed": true,
  "rbac_reviewed": false,
  "datasource_isolation_tested": false,
  "query_budget_passed": true,
  "alert_delivery_tested": false,
  "missing_data_tested": true,
  "incident_drill_completed": true,
  "gitops_approval": true,
  "dashboards": [
    {
      "uid": "postgres-overview",
      "owner": "dbre",
      "panels": 12,
      "refresh_seconds": 1,
      "query_cost": 20
    },
    {
      "uid": "postgres-overview",
      "owner": "dbre",
      "panels": 9,
      "refresh_seconds": 60,
      "query_cost": 15
    }
  ],
  "query_budget": 10,
  "alerts": [
    {
      "name": "PostgresUnavailable",
      "owner": "dbre",
      "receiver": "dbre-test-pager",
      "route_tested": false,
      "runbook": "https://example.org/runbooks/postgres"
    },
    {
      "name": "RedisUnavailable",
      "owner": "dbre",
      "receiver": "dbre-test-pager",
      "route_tested": true,
      "runbook": "https://example.org/runbooks/redis"
    }
  ]
}
```

### scripts/acceptance.py

```python
#!/usr/bin/env python3
"""Offline Grafana production readiness policy model. No network calls."""
import json,re,sys
from pathlib import Path
FLAGS=("grafana_version_reviewed","high_availability_reviewed","backup_restore_tested",
"rollback_tested","secret_scan_passed","rbac_reviewed","datasource_isolation_tested",
"query_budget_passed","alert_delivery_tested","missing_data_tested",
"incident_drill_completed","gitops_approval")
def evaluate(d):
    problems=[]
    if not isinstance(d,dict): return ["manifest must be object"]
    for k in ("environment","owner"):
        if not isinstance(d.get(k),str) or not d[k].strip(): problems.append("missing "+k)
    for k in FLAGS:
        if d.get(k) is not True: problems.append("gate failed "+k)
    budget=d.get("query_budget")
    if type(budget) is not int or budget<=0: problems.append("invalid query budget")
    dashboards=d.get("dashboards")
    if not isinstance(dashboards,list) or not dashboards: problems.append("no dashboards");dashboards=[]
    seen=set();total=0
    for i,item in enumerate(dashboards):
        p="dashboard["+str(i)+"]"
        if not isinstance(item,dict): problems.append(p+" invalid");continue
        uid=item.get("uid")
        if not isinstance(uid,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}",uid): problems.append(p+" invalid UID")
        elif uid in seen: problems.append(p+" duplicate UID")
        else: seen.add(uid)
        if not isinstance(item.get("owner"),str) or not item["owner"]: problems.append(p+" missing owner")
        panels=item.get("panels")
        if type(panels) is not int or not 1<=panels<=50: problems.append(p+" invalid panel count")
        refresh=item.get("refresh_seconds")
        if type(refresh) is not int or refresh<30: problems.append(p+" unsafe refresh")
        cost=item.get("query_cost")
        if type(cost) is not int or cost<0: problems.append(p+" invalid query cost")
        else: total+=cost
    if type(budget) is int and total>budget: problems.append("query budget exceeded")
    alerts=d.get("alerts")
    if not isinstance(alerts,list) or not alerts: problems.append("no alerts");alerts=[]
    for i,a in enumerate(alerts):
        p="alert["+str(i)+"]"
        if not isinstance(a,dict): problems.append(p+" invalid");continue
        for k in ("name","owner","receiver","runbook"):
            if not isinstance(a.get(k),str) or not a[k].strip(): problems.append(p+" missing "+k)
        if a.get("route_tested") is not True: problems.append(p+" route untested")
    return problems
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 acceptance.py fixtures/healthy.json")
    try: findings=evaluate(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as e: sys.exit("input error: "+str(e))
    print(json.dumps({"status":"FAIL" if findings else "PASS","findings":findings},indent=2))
    sys.exit(bool(findings))
```

### tests/test_acceptance.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from acceptance import evaluate
class CapstoneTests(unittest.TestCase):
    def setUp(self): self.d=json.loads((ROOT/"fixtures"/"healthy.json").read_text())
    def mutate(self,f):
        d=copy.deepcopy(self.d);f(d);return evaluate(d)
    def test_healthy(self): self.assertEqual(evaluate(self.d),[])
    def test_degraded(self): self.assertTrue(evaluate(json.loads((ROOT/"fixtures"/"degraded.json").read_text())))
    def test_not_object(self): self.assertTrue(evaluate(None))
    def test_owner(self): self.assertTrue(self.mutate(lambda d:d.update(owner="")))
    def test_ha(self): self.assertTrue(self.mutate(lambda d:d.update(high_availability_reviewed=False)))
    def test_restore(self): self.assertTrue(self.mutate(lambda d:d.update(backup_restore_tested=False)))
    def test_rollback(self): self.assertTrue(self.mutate(lambda d:d.update(rollback_tested=False)))
    def test_secrets(self): self.assertTrue(self.mutate(lambda d:d.update(secret_scan_passed=False)))
    def test_rbac(self): self.assertTrue(self.mutate(lambda d:d.update(rbac_reviewed=False)))
    def test_isolation(self): self.assertTrue(self.mutate(lambda d:d.update(datasource_isolation_tested=False)))
    def test_alert_delivery(self): self.assertTrue(self.mutate(lambda d:d.update(alert_delivery_tested=False)))
    def test_missing_data(self): self.assertTrue(self.mutate(lambda d:d.update(missing_data_tested=False)))
    def test_incident(self): self.assertTrue(self.mutate(lambda d:d.update(incident_drill_completed=False)))
    def test_approval(self): self.assertTrue(self.mutate(lambda d:d.update(gitops_approval=False)))
    def test_no_dashboards(self): self.assertTrue(self.mutate(lambda d:d.update(dashboards=[])))
    def test_duplicate_uid(self): self.assertTrue(self.mutate(lambda d:d["dashboards"][1].update(uid="postgres-overview")))
    def test_invalid_uid(self): self.assertTrue(self.mutate(lambda d:d["dashboards"][0].update(uid="bad uid")))
    def test_missing_dashboard_owner(self): self.assertTrue(self.mutate(lambda d:d["dashboards"][0].update(owner="")))
    def test_panels(self): self.assertTrue(self.mutate(lambda d:d["dashboards"][0].update(panels=100)))
    def test_refresh(self): self.assertTrue(self.mutate(lambda d:d["dashboards"][0].update(refresh_seconds=1)))
    def test_budget(self): self.assertTrue(self.mutate(lambda d:d.update(query_budget=1)))
    def test_invalid_cost(self): self.assertTrue(self.mutate(lambda d:d["dashboards"][0].update(query_cost=-1)))
    def test_no_alerts(self): self.assertTrue(self.mutate(lambda d:d.update(alerts=[])))
    def test_receiver(self): self.assertTrue(self.mutate(lambda d:d["alerts"][0].update(receiver="")))
    def test_route(self): self.assertTrue(self.mutate(lambda d:d["alerts"][0].update(route_tested=False)))
    def test_runbook(self): self.assertTrue(self.mutate(lambda d:d["alerts"][0].update(runbook="")))
if __name__=="__main__": unittest.main()
```

### Execute

```bash
cd chapter025
python3 scripts/acceptance.py fixtures/healthy.json
if python3 scripts/acceptance.py fixtures/degraded.json; then
  echo "FAIL: degraded capstone accepted"; exit 1
else
  echo "PASS: degraded capstone rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy PASS, degraded FAIL and **26 automated unit tests pass**. This is synthetic acceptance evidence only.

## 8. Twenty-four hands-on exercises

1. Draw production Grafana architecture.
2. Review database HA topology.
3. Validate load balancer and TLS.
4. Audit SSO and service accounts.
5. Review folder and datasource permissions.
6. Check tenant isolation.
7. Define dashboard owners.
8. Review PostgreSQL panels.
9. Review Redis panels.
10. Review dashboard UID stability.
11. Validate units and no-data behavior.
12. Review query cost and refresh budget.
13. Validate provisioning ownership.
14. Review dashboard promotion.
15. Review alert state policies.
16. Review notification routes.
17. Conduct test receiver page drill.
18. Test alert silence expiration.
19. Review secrets and audit logs.
20. Exercise database backup restore.
21. Rehearse Grafana rollback.
22. Run healthy and degraded fixtures.
23. Execute 26 unit tests.
24. Complete production acceptance board.

## 9. Twenty-four production failure scenarios

| # | Failure | First investigation |
|---|---|---|
| 01 | Grafana frontend unavailable | Inspect owner, live state, provisioning, access, routing and rollback |
| 02 | Grafana metadata DB down | Inspect owner, live state, provisioning, access, routing and rollback |
| 03 | Grafana replicas disagree | Inspect owner, live state, provisioning, access, routing and rollback |
| 04 | Ingress TLS certificate expired | Inspect owner, live state, provisioning, access, routing and rollback |
| 05 | SSO login failure | Inspect owner, live state, provisioning, access, routing and rollback |
| 06 | RBAC cross-tenant exposure | Inspect owner, live state, provisioning, access, routing and rollback |
| 07 | Datasource secret leak | Inspect owner, live state, provisioning, access, routing and rollback |
| 08 | Datasource Prometheus unreachable | Inspect owner, live state, provisioning, access, routing and rollback |
| 09 | Dashboard UID collision | Inspect owner, live state, provisioning, access, routing and rollback |
| 10 | Dashboard variable unbounded | Inspect owner, live state, provisioning, access, routing and rollback |
| 11 | Dashboard query storm | Inspect owner, live state, provisioning, access, routing and rollback |
| 12 | Missing telemetry appears healthy | Inspect owner, live state, provisioning, access, routing and rollback |
| 13 | Incorrect latency unit | Inspect owner, live state, provisioning, access, routing and rollback |
| 14 | Provisioning drift | Inspect owner, live state, provisioning, access, routing and rollback |
| 15 | Grafana plugin incompatibility | Inspect owner, live state, provisioning, access, routing and rollback |
| 16 | Alert evaluator stalled | Inspect owner, live state, provisioning, access, routing and rollback |
| 17 | No Data silently ignored | Inspect owner, live state, provisioning, access, routing and rollback |
| 18 | Contact point unreachable | Inspect owner, live state, provisioning, access, routing and rollback |
| 19 | Notification route mismatch | Inspect owner, live state, provisioning, access, routing and rollback |
| 20 | Mute timing suppresses page | Inspect owner, live state, provisioning, access, routing and rollback |
| 21 | Duplicate alert notifications | Inspect owner, live state, provisioning, access, routing and rollback |
| 22 | Backup restore fails | Inspect owner, live state, provisioning, access, routing and rollback |
| 23 | Rollback revision unavailable | Inspect owner, live state, provisioning, access, routing and rollback |
| 24 | Change audit trail missing | Inspect owner, live state, provisioning, access, routing and rollback |

## 10. Eight production runbooks

**A. Grafana outage:** Check ingress, application logs, replicas, database connectivity, recovery objective and failover.

**B. Datasource outage:** Test server-side datasource reachability, credentials, proxy and upstream health.

**C. RBAC breach:** Restrict access, rotate exposed credentials, audit folders and datasource authorization.

**D. Dashboard regression:** Compare Git revision, datasource UID, query inspector, variables, no-data handling and rollback.

**E. Alert delivery incident:** Test receiver, notification policy match, mute timings, evaluator status and backup paging.

**F. Query saturation:** Limit refresh/query fanout, inspect Prometheus duration and cardinality, roll back expensive dashboards.

**G. Backup/restore drill:** Validate encrypted backup, recovery point, restore staging DB, keys, dashboards and alert resources.

**H. Production rollback:** Restore reviewed image/config revision, check Grafana metadata, dashboards, paging and incident evidence.

## 11. Enterprise incident simulation

**Scenario:** A PostgreSQL primary failover causes exporter target churn; Grafana panels show stale values because the cluster variable is wrong. A new notification policy routes the alert to an untested receiver while a dashboard refresh change overloads Prometheus. Operators must distinguish missing data from service failure, restore a reliable page route, preserve tenant isolation, revert the dashboard, and document recovery.

**Acceptance:** demonstrate accurate diagnosis, incident commander assignment, notification recovery, query budget remediation, change rollback and post-incident review. All live actions require staging authorization.

## 12. 100-point final capstone assessment

| Domain | Points |
|---|---:|
| HA architecture, security and RBAC | 20 |
| Dashboards, datasources and query budgets | 20 |
| Alerting, paging and incident workflows | 20 |
| Offline lab and 26 unit tests | 20 |
| DR, rollback, runbooks and evidence | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory gates: tenant isolation, secure secrets, tested notification route, approved change, restore/rollback evidence and 26 passing tests. Offline success does **not** imply live readiness.

## 13. Evidence worksheet

```text
UTC / environment / Grafana version / owner:
Grafana HA / metadata DB / ingress / SSO:
Dashboard UIDs / datasource isolation / Git revision:
PromQL freshness / no-data / query budget:
Alert evaluator / contact point / route / test page:
Secret scan / RBAC / audit:
Backup / restore / rollback:
Healthy/degraded gate / 26 tests:
Incident commander / RCA / approval / score:
```

**Companion:** [Chapter 025 executable enterprise capstone lab](labs/025-grafana-enterprise-dashboards-alerting-security-production-operations-capstone-lab.md).

**Part 05 complete. Next:** Chapter 026 — Prometheus Alertmanager Architecture, Installation and Notification Routing Fundamentals (Part 06).
