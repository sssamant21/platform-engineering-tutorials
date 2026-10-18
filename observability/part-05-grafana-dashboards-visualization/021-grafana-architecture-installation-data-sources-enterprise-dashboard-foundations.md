# Chapter 021 — Grafana Architecture, Installation, Data Sources and Enterprise Dashboard Foundations

**Part 05 — Grafana Dashboards and Visualization**  
**Audience:** SRE/DBRE, platform engineers, observability operators.  
**Prerequisites:** Chapters 001–020, Docker Compose, Prometheus fundamentals, Python 3.10+.  
**Outcome:** Understand Grafana deployment architecture, provision Prometheus data sources and dashboards as code, validate access controls, and establish an enterprise operational baseline.

## 1. Architecture

```text
Users -> HTTPS reverse proxy / SSO / LB
                    |
              Grafana servers
               /         \
        SQL metadata     plugins / provisioning
              |
    Prometheus datasource (proxy mode)
              |
         Prometheus API -> TSDB -> exporters
```

Grafana primarily visualizes and queries telemetry held in data sources. Grafana's own database stores configuration, users, dashboard definitions and other metadata; it is **not** the Prometheus metrics TSDB. Production HA typically requires shared supported SQL metadata storage, consistent encryption keys and appropriate ingress/session architecture. A single Docker Compose Grafana with SQLite is a **local teaching environment**, not a production HA deployment.

## 2. Deployment patterns and choices

| Pattern | Use case | Caveat |
|---|---|---|
| Local Docker Compose | safe learning | single instance; local port only |
| Kubernetes Helm | managed platform deployments | verify chart version, values and secrets |
| Managed Grafana | reduced infrastructure operations | assess provider, cost, tenancy and access |
| Self-managed HA | advanced control | shared DB, load balancer, backups, SSO, upgrade tests |

Pin tested image/chart versions and maintain an upgrade compatibility matrix. The lab image tag is an illustrative pinned version; verify current support and security advisories before production use.

## 3. Security baseline

Use TLS at the ingress, OIDC/SAML where supported, least-privilege RBAC, organization/folder boundaries, short-lived service account tokens, secret-manager integration, audited provisioning changes and immutable dashboard releases. Never commit administrator credentials or datasource secrets. Disable anonymous access unless explicitly required and reviewed. Restrict datasource query permissions to prevent cross-tenant telemetry access.

## 4. Data source and dashboard provisioning

Provisioned data sources use stable UIDs referenced by dashboards. In proxy mode, Grafana's server reaches Prometheus, so `localhost` from the browser is not the same as `localhost` inside the Grafana container. The example `host.docker.internal` works in some Docker environments; on Linux it may require an explicit host-gateway mapping or replacement with a service DNS name. Start a separately authorized Prometheus instance on port 9090 before expecting live panels.

### docker-compose.yml

```yaml
services:
  grafana:
    image: grafana/grafana:11.5.2
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: "${GRAFANA_ADMIN_PASSWORD:?set in .env}"
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_AUTH_ANONYMOUS_ENABLED: "false"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./provisioning:/etc/grafana/provisioning:ro
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
volumes:
  grafana_data: {}
```

### provisioning/datasources/prometheus.yml

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prometheus-primary
    type: prometheus
    access: proxy
    url: http://host.docker.internal:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: 30s
```

### provisioning/dashboards/provider.yml

```yaml
apiVersion: 1
providers:
  - name: sre-foundations
    orgId: 1
    folder: SRE Foundations
    type: file
    disableDeletion: true
    editable: false
    options:
      path: /etc/grafana/provisioning/dashboards/json
```

### dashboards/sre-foundations.json

```json
{
  "uid": "sre-foundations-021",
  "title": "SRE Foundations — Prometheus Target Health",
  "tags": [
    "sre",
    "dbre",
    "chapter-021"
  ],
  "timezone": "browser",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "30s",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "templating": {
    "list": [
      {
        "name": "job",
        "type": "query",
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus-primary"
        },
        "query": {
          "query": "label_values(up, job)",
          "refId": "JobVariableQuery"
        },
        "refresh": 1,
        "includeAll": false,
        "multi": false
      }
    ]
  },
  "panels": [
    {
      "id": 1,
      "type": "stat",
      "title": "Discovered Targets",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus-primary"
      },
      "gridPos": {
        "h": 8,
        "w": 8,
        "x": 0,
        "y": 0
      },
      "targets": [
        {
          "expr": "count(up{job=~\"$job\"})",
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        },
        "overrides": []
      }
    },
    {
      "id": 2,
      "type": "stat",
      "title": "Down Targets",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus-primary"
      },
      "gridPos": {
        "h": 8,
        "w": 8,
        "x": 8,
        "y": 0
      },
      "targets": [
        {
          "expr": "count(up{job=~\"$job\"} == 0) or vector(0)",
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        },
        "overrides": []
      }
    },
    {
      "id": 3,
      "type": "timeseries",
      "title": "Scrape Health by Instance",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus-primary"
      },
      "gridPos": {
        "h": 9,
        "w": 24,
        "x": 0,
        "y": 8
      },
      "targets": [
        {
          "expr": "up{job=~\"$job\"}",
          "legendFormat": "{{instance}}",
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "min": 0,
          "max": 1
        },
        "overrides": []
      }
    }
  ]
}
```

**Important:** For file-based provisioning, place dashboard JSON at the path configured by the provider, for example `provisioning/dashboards/json/sre-foundations.json`. The separate `dashboards/sre-foundations.json` below is the version-controlled source; copy it into the provisioned directory before launching. Avoid treating a displayed `count(... ) or vector(0)` as authoritative target inventory: absent targets require inventory-based checks.

## 5. Hands-on deployment

```bash
mkdir -p chapter021/{provisioning/datasources,provisioning/dashboards/json,dashboards,scripts,tests}
cd chapter021
# Save the four blocks above to their matching files.
cp dashboards/sre-foundations.json provisioning/dashboards/json/sre-foundations.json
printf 'GRAFANA_ADMIN_PASSWORD=%s\n' 'replace-with-strong-local-secret' > .env
chmod 600 .env
docker compose config
docker compose up -d
docker compose logs --tail=100 grafana
curl -fsS http://127.0.0.1:3000/api/health
```

Use a strong local secret; do not use the literal placeholder in a shared environment. Grafana is bound to 127.0.0.1:3000 for local use. For Linux Docker, update Compose with `extra_hosts: ["host.docker.internal:host-gateway"]` if necessary and supported.

## 6. Dashboard design fundamentals

- **Stat:** a current target count or health indicator; distinguish missing from zero.
- **Timeseries:** `up` over time, split by instance; check scrape gaps.
- **Variables:** bounded `job` selection; avoid unbounded multi-select in large environments.
- **Units:** seconds vs milliseconds, bytes vs GiB, percentages vs ratios.
- **Refresh:** balance on-call freshness against Prometheus query load.
- **Ownership:** annotate dashboards with team, service, SLO, change link and runbook.
- **Templating:** verify dashboard JSON schema compatibility with installed Grafana.

## 7. Complete offline executable governance lab

The Python gate below checks dashboard identity, panel IDs, datasource UID, provisioning invariants, refresh policy and basic query presence. It **does not parse PromQL or validate Grafana JSON schemas**, and cannot replace Grafana API integration tests.

### scripts/dashboard_gate.py

```python
#!/usr/bin/env python3
"""Static offline Grafana provisioning safety gate; not Grafana API validation."""
import json,sys,re
from pathlib import Path
def check(d,source,provider):
    issues=[]
    if not isinstance(d,dict): return ["dashboard must be an object"]
    if not isinstance(d.get("uid"),str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}",d["uid"]):
        issues.append("invalid dashboard UID")
    if not isinstance(d.get("title"),str) or not d["title"].strip():
        issues.append("missing dashboard title")
    panels=d.get("panels")
    if not isinstance(panels,list) or not panels: issues.append("missing panels")
    else:
        ids=set()
        for p in panels:
            if not isinstance(p,dict):
                issues.append("invalid panel"); continue
            if type(p.get("id")) is not int or p["id"] in ids: issues.append("duplicate or invalid panel ID")
            else: ids.add(p["id"])
            if not p.get("title"): issues.append("missing panel title")
            ds=p.get("datasource")
            if not isinstance(ds,dict) or ds.get("uid")!="prometheus-primary":
                issues.append("unexpected datasource")
            for target in p.get("targets",[]):
                expr=target.get("expr","")
                if not isinstance(expr,str) or not expr.strip(): issues.append("empty PromQL")
                if len(expr)>500: issues.append("oversized PromQL")
    if "uid: prometheus-primary" not in source or "access: proxy" not in source:
        issues.append("datasource provisioning missing UID or proxy mode")
    if "editable: false" not in source or "editable: false" not in provider:
        issues.append("provisioned resources must be immutable")
    if "http://host.docker.internal:9090" not in source:
        issues.append("unexpected local Prometheus endpoint")
    if d.get("refresh") not in ("30s","1m","5m"):
        issues.append("unapproved refresh")
    return issues
if __name__=="__main__":
    if len(sys.argv)!=4: sys.exit("usage: python3 dashboard_gate.py dashboard.json datasource.yml dashboards.yml")
    try:
        d=json.loads(Path(sys.argv[1]).read_text())
        findings=check(d,Path(sys.argv[2]).read_text(),Path(sys.argv[3]).read_text())
    except (OSError,ValueError) as e: sys.exit(f"input error: {e}")
    print("PASS" if not findings else "FAIL")
    for f in findings: print("-",f)
    sys.exit(bool(findings))
```

### tests/test_dashboard_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from dashboard_gate import check
class DashboardGateTests(unittest.TestCase):
    def setUp(self):
        self.d=json.loads((ROOT/"dashboards"/"sre-foundations.json").read_text())
        self.s=(ROOT/"provisioning"/"datasources"/"prometheus.yml").read_text()
        self.p=(ROOT/"provisioning"/"dashboards"/"provider.yml").read_text()
    def verify(self,d=None,s=None,p=None): return check(self.d if d is None else d,self.s if s is None else s,self.p if p is None else p)
    def mutate(self,key,value):
        d=copy.deepcopy(self.d);d[key]=value;return self.verify(d=d)
    def test_healthy(self): self.assertEqual(self.verify(),[])
    def test_no_dashboard(self): self.assertTrue(self.verify(d=None if False else {}))
    def test_invalid_uid(self): self.assertTrue(self.mutate("uid","unsafe space"))
    def test_long_uid(self): self.assertTrue(self.mutate("uid","x"*41))
    def test_empty_title(self): self.assertTrue(self.mutate("title",""))
    def test_empty_panels(self): self.assertTrue(self.mutate("panels",[]))
    def test_invalid_panels(self): self.assertTrue(self.mutate("panels","wrong"))
    def test_duplicate_ids(self):
        d=copy.deepcopy(self.d);d["panels"][1]["id"]=1;self.assertTrue(self.verify(d=d))
    def test_missing_panel_title(self):
        d=copy.deepcopy(self.d);d["panels"][0]["title"]="";self.assertTrue(self.verify(d=d))
    def test_wrong_datasource(self):
        d=copy.deepcopy(self.d);d["panels"][0]["datasource"]["uid"]="unknown";self.assertTrue(self.verify(d=d))
    def test_missing_promql(self):
        d=copy.deepcopy(self.d);d["panels"][0]["targets"][0]["expr"]="";self.assertTrue(self.verify(d=d))
    def test_long_promql(self):
        d=copy.deepcopy(self.d);d["panels"][0]["targets"][0]["expr"]="x"*501;self.assertTrue(self.verify(d=d))
    def test_missing_uid_provisioning(self): self.assertTrue(self.verify(s=self.s.replace("uid: prometheus-primary","uid: wrong")))
    def test_wrong_access(self): self.assertTrue(self.verify(s=self.s.replace("access: proxy","access: direct")))
    def test_editable_source(self): self.assertTrue(self.verify(s=self.s.replace("editable: false","editable: true")))
    def test_editable_provider(self): self.assertTrue(self.verify(p=self.p.replace("editable: false","editable: true")))
    def test_wrong_url(self): self.assertTrue(self.verify(s=self.s.replace("host.docker.internal:9090","example.com:9090")))
    def test_refresh(self): self.assertTrue(self.mutate("refresh","1s"))
    def test_valid_one_minute(self): self.assertEqual(self.mutate("refresh","1m"),[])
    def test_valid_five_minute(self): self.assertEqual(self.mutate("refresh","5m"),[])
if __name__=="__main__": unittest.main()
```

### Execute

```bash
cd chapter021
python3 scripts/dashboard_gate.py dashboards/sre-foundations.json provisioning/datasources/prometheus.yml provisioning/dashboards/provider.yml
python3 -m unittest discover -s tests -v
```

Expected: policy PASS and **20 unit tests pass**. Real Docker/Grafana deployment is optional and must be verified separately.

## 8. Twenty-four hands-on exercises

1. Review Grafana server architecture.
2. Identify Grafana storage and database responsibilities.
3. Explain Grafana vs Prometheus roles.
4. Plan HA and session storage.
5. Create isolated lab directory.
6. Set administrator password via environment.
7. Review container image pinning.
8. Launch local Docker Compose.
9. Inspect startup and health logs.
10. Verify local-only port binding.
11. Verify no anonymous access.
12. Provision Prometheus datasource.
13. Test network reachability from Grafana.
14. Provision dashboard provider.
15. Import the JSON dashboard.
16. Explain stat panel semantics.
17. Explain timeseries panel semantics.
18. Inspect job variable query.
19. Investigate no-data behavior.
20. Review dashboard refresh cost.
21. Inspect RBAC and folder permissions.
22. Run offline governance gate.
23. Run 20 unit tests and failure drills.
24. Record deployment, rollback and ownership evidence.

## 9. Twenty production failure scenarios

| # | Scenario | First diagnostic |
|---|---|---|
| 01 | Grafana container cannot start | Check Grafana logs, provisioning, network, access and owner |
| 02 | administrator secret missing | Check Grafana logs, provisioning, network, access and owner |
| 03 | port 3000 occupied | Check Grafana logs, provisioning, network, access and owner |
| 04 | volume permission denied | Check Grafana logs, provisioning, network, access and owner |
| 05 | Grafana UI accessible publicly | Check Grafana logs, provisioning, network, access and owner |
| 06 | anonymous auth accidentally enabled | Check Grafana logs, provisioning, network, access and owner |
| 07 | Prometheus endpoint unreachable | Check Grafana logs, provisioning, network, access and owner |
| 08 | host.docker.internal unavailable on Linux | Check Grafana logs, provisioning, network, access and owner |
| 09 | datasource UID mismatch | Check Grafana logs, provisioning, network, access and owner |
| 10 | datasource provisioning malformed | Check Grafana logs, provisioning, network, access and owner |
| 11 | dashboard provider path mismatch | Check Grafana logs, provisioning, network, access and owner |
| 12 | dashboard JSON invalid | Check Grafana logs, provisioning, network, access and owner |
| 13 | dashboard UID duplicated | Check Grafana logs, provisioning, network, access and owner |
| 14 | dashboard panel shows no data | Check Grafana logs, provisioning, network, access and owner |
| 15 | job variable has no options | Check Grafana logs, provisioning, network, access and owner |
| 16 | Prometheus scrape target down | Check Grafana logs, provisioning, network, access and owner |
| 17 | dashboard refresh overload | Check Grafana logs, provisioning, network, access and owner |
| 18 | folder RBAC too permissive | Check Grafana logs, provisioning, network, access and owner |
| 19 | provisioned dashboard edited in UI | Check Grafana logs, provisioning, network, access and owner |
| 20 | Grafana SQLite locking under HA | Check Grafana logs, provisioning, network, access and owner |

## 10. Eight production runbooks

**A. Startup failure:** Inspect docker compose config/logs, env, port and persistent volume; restore known-good image.

**B. Datasource unavailable:** Test Prometheus URL from Grafana network namespace, verify DNS, proxy, TLS and auth.

**C. No-data dashboard:** Check variable values, PromQL labels, time range, target discovery and staleness.

**D. Provisioning drift:** Inspect datasource UID and provider path, validate YAML/JSON, restart staging service after review.

**E. RBAC exposure:** Audit organization roles, folder permissions, service accounts, tokens and anonymous auth.

**F. Dashboard performance:** Reduce refresh frequency, query fan-out, variable cardinality and wide time ranges.

**G. HA failure:** Review shared SQL database, load balancer, session handling and replica health; avoid SQLite for production HA.

**H. Upgrade and rollback:** Backup Grafana DB and dashboards, test plugin compatibility, canary upgrade, revert image and verify data.

## 11. 100-point assessment

| Area | Points |
|---|---:|
| Grafana architecture and deployment patterns | 20 |
| Datasource and dashboard provisioning | 20 |
| Security, RBAC, tenancy and performance | 20 |
| Offline gate and 20 unit tests | 20 |
| Troubleshooting, runbooks and evidence | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory gates: no committed secrets, local-only lab exposure, stable datasource UID, tested provisioning and documented rollback.

## 12. Evidence worksheet

```text
UTC / operator / Grafana version:
Deployment mode / container image:
Admin secret storage and access policy:
Datasource UID / Prometheus reachability:
Dashboard UID / panels / variables:
Provisioning gate / 20 tests:
RBAC and folder owner:
No-data and outage drill:
Backup / rollback / reviewer / score:
```

**Companion:** [Chapter 021 executable lab](labs/021-grafana-architecture-installation-data-sources-enterprise-dashboard-foundations-lab.md).

**Next:** Chapter 022 — Grafana Dashboard Design, Variables, Panels, Transformations and Production Visualization Patterns.
