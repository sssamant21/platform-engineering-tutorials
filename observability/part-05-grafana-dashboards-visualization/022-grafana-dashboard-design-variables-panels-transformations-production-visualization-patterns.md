# Chapter 022 — Grafana Dashboard Design, Variables, Panels, Transformations and Production Visualization Patterns

**Part 05 — Grafana Dashboards and Visualization**  
**Audience:** SRE/DBRE, observability platform engineers, on-call responders.  
**Prerequisites:** Chapter 021, PromQL Chapters 016–020, Python 3.10+.  
**Objective:** Design actionable, safe and efficient dashboards with scoped variables, appropriate panels, transformations, and Git-managed JSON.

## 1. Architecture and design principles

```text
Grafana dashboard -> template variables -> datasource query
       |                                      |
       |                                Prometheus API
       |                                      |
       +-> data frames -> transformations -> field overrides
                                               |
                                       stat/time series/table
```

Dashboards are an operational interface, not a replacement for alerting or authoritative inventory. Start with user decisions: **Is the service healthy? Which cluster/instance is affected? Is this new? What should on-call do?** Group panels by health, traffic, latency, saturation, dependencies and drill-down. Put owner, SLO, runbook and change references near the top.

## 2. Panels and query design

| Panel | Best use | Typical pitfall |
|---|---|---|
| Stat | current health, errors, targets | no-data silently interpreted as zero |
| Time series | rate, latency, capacity trends | mismatched units or excessive series |
| Table | inventory, top offenders, owners | unbounded rows and sensitive labels |
| State timeline | discrete operational state | sampling gaps and ambiguous state |
| Heatmap | latency distributions | bucket interpretation and query cost |

Prefer raw query validation in Prometheus before building a panel. `up == 0` identifies discovered targets with failed scrapes; it does not detect an undiscovered expected target. Validate panels at healthy, degraded and missing-data states.

## 3. Variables and isolation

Common variable types include query, custom, constant, textbox, interval and datasource. For Prometheus query variables, `label_values(up, cluster)` enumerates label values on matching series; this does not prove that a cluster is authorized or complete.

```promql
up{cluster="$cluster",job="$job"}
```

Variables are a convenience filter, **not an authorization boundary**. Enforce tenancy in datasource permissions and backend isolation. Avoid unbounded `All` and multi-select options in large fleets unless explicit cost and scope limits exist. When multi-value interpolation is needed, use the correct regex operators and escaping, e.g. `cluster=~"$cluster"`, and verify the exact interpolated query in Grafana Query Inspector.

## 4. Transformations versus PromQL

Grafana transformations operate on returned data frames. Common operations include **Reduce**, **Filter fields**, **Organize fields**, **Join by field**, **Add field from calculation** and **Labels to fields**. Transformations can simplify display, but do not reduce Prometheus query cost if raw data has already been fetched. Prefer PromQL for large-scale aggregation and rate math.

- **Reduce:** converts series to summary values; can conceal short spikes if used without a trend panel.
- **Join by field:** requires reliable unique keys; duplicate keys can expand rows unexpectedly.
- **Labels to fields:** useful for inventory tables; can increase frame width.
- **Organize fields:** display formatting; not data security.
- **Calculation:** verify units, null handling and divide-by-zero behavior.

## 5. Production visualization conventions

Use consistent naming (`cluster/service/instance`), labels, units and panel descriptions. Avoid red/green-only semantics; provide numeric values and text for accessibility. Set explicit thresholds based on SLO policy, not arbitrary aesthetics. Use dashboard-level variables and stable datasource UIDs. Document missing-data policy, expected scrape cadence, and the effect of dashboard refresh on Prometheus query load.

## 6. Example Git-managed dashboard

The following JSON uses a provisioned Prometheus datasource UID from Chapter 021. It shows target health and time-series detail for a selected cluster/job. **It is a teaching dashboard**, not a production authorization model; real target inventory and RBAC must be validated separately.

### fixtures/dashboard.json

```json
{
  "uid": "dbre-overview-022",
  "title": "DBRE Fleet Overview",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "1m",
  "time": {
    "from": "now-6h",
    "to": "now"
  },
  "tags": [
    "dbre",
    "sre",
    "observability"
  ],
  "templating": {
    "list": [
      {
        "name": "cluster",
        "type": "query",
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus-primary"
        },
        "query": {
          "query": "label_values(up{job=~\"postgres|redis\"}, cluster)",
          "refId": "cluster"
        },
        "refresh": 1,
        "multi": false,
        "includeAll": false
      },
      {
        "name": "job",
        "type": "custom",
        "query": "postgres,redis",
        "current": {
          "text": "postgres",
          "value": "postgres"
        },
        "multi": false,
        "includeAll": false
      }
    ]
  },
  "panels": [
    {
      "id": 1,
      "title": "Targets up",
      "type": "stat",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus-primary"
      },
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 8,
        "h": 7
      },
      "targets": [
        {
          "refId": "A",
          "expr": "sum(up{cluster=\"$cluster\",job=\"$job\"})"
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
      "title": "Discovered targets",
      "type": "stat",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus-primary"
      },
      "gridPos": {
        "x": 8,
        "y": 0,
        "w": 8,
        "h": 7
      },
      "targets": [
        {
          "refId": "A",
          "expr": "count(up{cluster=\"$cluster\",job=\"$job\"})"
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
      "title": "Availability by instance",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus-primary"
      },
      "gridPos": {
        "x": 0,
        "y": 7,
        "w": 24,
        "h": 9
      },
      "targets": [
        {
          "refId": "A",
          "expr": "up{cluster=\"$cluster\",job=\"$job\"}",
          "legendFormat": "{{instance}}"
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

Import this JSON through an authorized Grafana instance or provision it using Chapter 021's dashboard provider. The selected `cluster` value must exist in your metric labels; otherwise panels will show no data. Confirm compatibility with your deployed Grafana version.

## 7. Executable offline dashboard governance lab

The Python validator enforces local dashboard policy for UID, refresh, bounded variables, panel types, layout, datasource UID and basic cluster scoping. It **does not parse PromQL, inspect actual permissions, validate full Grafana schemas, or execute transformations**.

Create:

```text
chapter022/
  fixtures/dashboard.json
  scripts/dashboard_gate.py
  tests/test_dashboard_gate.py
```

### scripts/dashboard_gate.py

```python
#!/usr/bin/env python3
"""Static Grafana dashboard policy gate. Not Grafana schema/PromQL validation."""
import json,re,sys
from pathlib import Path
UID=re.compile(r"^[A-Za-z0-9_-]{1,40}$")
def validate(d):
    issues=[]
    if not isinstance(d,dict): return ["dashboard must be object"]
    if not isinstance(d.get("uid"),str) or not UID.fullmatch(d["uid"]): issues.append("invalid UID")
    if not isinstance(d.get("title"),str) or not d["title"].strip(): issues.append("missing title")
    if d.get("refresh") not in ("30s","1m","5m"): issues.append("unsafe refresh")
    vars=d.get("templating",{}).get("list",[])
    if not isinstance(vars,list) or not vars: issues.append("missing variables");vars=[]
    names=set()
    for v in vars:
        if not isinstance(v,dict): issues.append("invalid variable");continue
        name=v.get("name")
        if not isinstance(name,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",name): issues.append("invalid variable name")
        elif name in names: issues.append("duplicate variable")
        else: names.add(name)
        if v.get("multi") is not False or v.get("includeAll") is not False: issues.append("unbounded variable")
        if v.get("type") not in ("custom","query"): issues.append("unapproved variable type")
    if "cluster" not in names: issues.append("cluster variable required")
    panels=d.get("panels")
    if not isinstance(panels,list) or not panels: issues.append("no panels");panels=[]
    ids=set()
    for p in panels:
        if not isinstance(p,dict): issues.append("invalid panel");continue
        if type(p.get("id")) is not int or p["id"] in ids: issues.append("duplicate/invalid panel ID")
        else: ids.add(p["id"])
        if p.get("type") not in ("stat","timeseries","table"): issues.append("unapproved panel type")
        if not isinstance(p.get("title"),str) or not p["title"].strip(): issues.append("missing panel title")
        if p.get("datasource",{}).get("uid")!="prometheus-primary": issues.append("unexpected datasource UID")
        pos=p.get("gridPos",{})
        if not isinstance(pos,dict) or any(type(pos.get(k)) is not int or pos[k]<0 for k in ("x","y","w","h")) or pos.get("w",0)<1 or pos.get("h",0)<1 or pos.get("x",0)+pos.get("w",0)>24: issues.append("invalid panel grid")
        targets=p.get("targets",[])
        if not isinstance(targets,list) or not targets: issues.append("missing targets");continue
        for t in targets:
            expr=t.get("expr") if isinstance(t,dict) else None
            if not isinstance(expr,str) or not expr.strip(): issues.append("empty query")
            elif len(expr)>500: issues.append("query exceeds length policy")
            elif "up{" in expr and 'cluster="$cluster"' not in expr: issues.append("missing cluster scope")
    return issues
if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("usage: python3 dashboard_gate.py fixtures/dashboard.json")
    try: issues=validate(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError,ValueError) as e: sys.exit(f"input error: {e}")
    print(json.dumps({"status":"PASS" if not issues else "FAIL","issues":issues},indent=2))
    sys.exit(bool(issues))
```

### tests/test_dashboard_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from dashboard_gate import validate
class DashboardTests(unittest.TestCase):
    def setUp(self): self.d=json.loads((ROOT/"fixtures"/"dashboard.json").read_text())
    def changed(self,callback):
        d=copy.deepcopy(self.d);callback(d);return validate(d)
    def test_valid(self): self.assertEqual(validate(self.d),[])
    def test_invalid_object(self): self.assertTrue(validate(None))
    def test_uid(self): self.assertTrue(self.changed(lambda d:d.update(uid="bad uid")))
    def test_missing_title(self): self.assertTrue(self.changed(lambda d:d.update(title="")))
    def test_refresh(self): self.assertTrue(self.changed(lambda d:d.update(refresh="1s")))
    def test_missing_vars(self): self.assertTrue(self.changed(lambda d:d["templating"].update(list=[])))
    def test_missing_cluster(self): self.assertTrue(self.changed(lambda d:d["templating"]["list"][0].update(name="region")))
    def test_duplicate_vars(self): self.assertTrue(self.changed(lambda d:d["templating"]["list"][1].update(name="cluster")))
    def test_multiselect(self): self.assertTrue(self.changed(lambda d:d["templating"]["list"][0].update(multi=True)))
    def test_all(self): self.assertTrue(self.changed(lambda d:d["templating"]["list"][0].update(includeAll=True)))
    def test_variable_type(self): self.assertTrue(self.changed(lambda d:d["templating"]["list"][0].update(type="textbox")))
    def test_empty_panels(self): self.assertTrue(self.changed(lambda d:d.update(panels=[])))
    def test_duplicate_id(self): self.assertTrue(self.changed(lambda d:d["panels"][1].update(id=1)))
    def test_panel_type(self): self.assertTrue(self.changed(lambda d:d["panels"][0].update(type="plugin-unknown")))
    def test_panel_title(self): self.assertTrue(self.changed(lambda d:d["panels"][0].update(title="")))
    def test_datasource(self): self.assertTrue(self.changed(lambda d:d["panels"][0]["datasource"].update(uid="wrong")))
    def test_grid(self): self.assertTrue(self.changed(lambda d:d["panels"][0]["gridPos"].update(w=25)))
    def test_targets(self): self.assertTrue(self.changed(lambda d:d["panels"][0].update(targets=[])))
    def test_empty_query(self): self.assertTrue(self.changed(lambda d:d["panels"][0]["targets"][0].update(expr="")))
    def test_query_length(self): self.assertTrue(self.changed(lambda d:d["panels"][0]["targets"][0].update(expr="x"*501)))
    def test_cluster_scope(self): self.assertTrue(self.changed(lambda d:d["panels"][0]["targets"][0].update(expr="up{job=\"postgres\"}")))
    def test_invalid_var_name(self): self.assertTrue(self.changed(lambda d:d["templating"]["list"][0].update(name="bad-name")))
    def test_valid_refresh(self): self.assertEqual(self.changed(lambda d:d.update(refresh="30s")),[])
    def test_valid_table(self): self.assertEqual(self.changed(lambda d:d["panels"][0].update(type="table")),[])
if __name__=="__main__": unittest.main()
```

### Run

```bash
cd chapter022
python3 scripts/dashboard_gate.py fixtures/dashboard.json
python3 -m unittest discover -s tests -v
```

Expected: dashboard policy PASS and **24 automated unit tests pass**. The validator is intentionally conservative and specific to this example's `up` queries.

## 8. Optional Grafana integration

1. Provision a Prometheus datasource with UID `prometheus-primary` and verify reachability.
2. Import the JSON into a staging Grafana folder with appropriate RBAC.
3. Verify the `cluster` and `job` variables and inspect interpolated PromQL.
4. Validate stat and time-series panels in healthy, down-target and missing-target states.
5. Inspect Grafana Query Inspector for latency, row counts, errors and backend query cost.
6. Test dashboard import/export and rollback using reviewed Git revisions.

Do not expose Grafana publicly for this lab or use live production secrets in JSON.

## 9. Twenty-four hands-on exercises

1. Establish dashboard audience and questions.
2. Define dashboard ownership and lifecycle.
3. Choose time range and refresh.
4. Use stat panels for health.
5. Use time series for trends.
6. Use table panels for inventory.
7. Set units and thresholds.
8. Distinguish no-data from zero.
9. Build cluster variable.
10. Build job variable.
11. Review variable injection and regex.
12. Disable unbounded all-values selection.
13. Preserve tenant and cluster scope.
14. Use stable datasource UIDs.
15. Choose legend and field names.
16. Apply field overrides.
17. Evaluate transformations vs PromQL.
18. Review join-by-field risks.
19. Review reduce transformation semantics.
20. Review data frame and null handling.
21. Run policy gate.
22. Run 24 unit tests.
23. Complete incident dashboard tabletop.
24. Document change and rollback evidence.

## 10. Twenty-four production failure scenarios

| # | Scenario | Initial diagnostic |
|---|---|---|
| 01 | Dashboard no data | Inspect raw query, variable scope, data frames, access policy and owner |
| 02 | Variable query returns empty | Inspect raw query, variable scope, data frames, access policy and owner |
| 03 | Cluster label missing | Inspect raw query, variable scope, data frames, access policy and owner |
| 04 | Tenant cross-contamination | Inspect raw query, variable scope, data frames, access policy and owner |
| 05 | Regex expansion too broad | Inspect raw query, variable scope, data frames, access policy and owner |
| 06 | All option overloads Prometheus | Inspect raw query, variable scope, data frames, access policy and owner |
| 07 | Wrong units | Inspect raw query, variable scope, data frames, access policy and owner |
| 08 | Stat panel hides null | Inspect raw query, variable scope, data frames, access policy and owner |
| 09 | Stale samples look healthy | Inspect raw query, variable scope, data frames, access policy and owner |
| 10 | Grafana panel query timeout | Inspect raw query, variable scope, data frames, access policy and owner |
| 11 | Datasource UID drift | Inspect raw query, variable scope, data frames, access policy and owner |
| 12 | Dashboard UID collision | Inspect raw query, variable scope, data frames, access policy and owner |
| 13 | Duplicate panel IDs | Inspect raw query, variable scope, data frames, access policy and owner |
| 14 | Broken grid layout | Inspect raw query, variable scope, data frames, access policy and owner |
| 15 | Transform join multiplies rows | Inspect raw query, variable scope, data frames, access policy and owner |
| 16 | Reduce transformation hides spikes | Inspect raw query, variable scope, data frames, access policy and owner |
| 17 | Alert dashboard mismatch | Inspect raw query, variable scope, data frames, access policy and owner |
| 18 | Wrong default time range | Inspect raw query, variable scope, data frames, access policy and owner |
| 19 | Too frequent refresh | Inspect raw query, variable scope, data frames, access policy and owner |
| 20 | Cardinality explosion | Inspect raw query, variable scope, data frames, access policy and owner |
| 21 | Dashboard provisioning overwritten | Inspect raw query, variable scope, data frames, access policy and owner |
| 22 | RBAC exposes restricted dashboard | Inspect raw query, variable scope, data frames, access policy and owner |
| 23 | Exporter schema changes | Inspect raw query, variable scope, data frames, access policy and owner |
| 24 | Dashboard rollback fails | Inspect raw query, variable scope, data frames, access policy and owner |

## 11. Eight production runbooks

**A. No-data diagnosis:** Check dashboard time range, variable values, Prometheus discovery, query inspector and staleness.

**B. Variable failure:** Inspect label_values results, query scope, datasource access and bounded variable configuration.

**C. Wrong units or thresholds:** Verify metric semantics, field units, null handling, gauge/counter interpretation and SLO ownership.

**D. Transform anomaly:** Inspect raw frames, join keys, row counts and null handling; move aggregation to PromQL where appropriate.

**E. Query overload:** Reduce refresh rate, time range, variable fan-out and expensive regex; inspect query inspector and Prometheus metrics.

**F. Access and tenancy incident:** Audit folder permissions, service accounts, datasource rights, cluster filters and potential cross-tenant exposure.

**G. Provisioning drift:** Compare version-controlled JSON, datasource UID and provider path; restore reviewed artifact.

**H. Safe rollback:** Revert dashboard revision, validate key panels, confirm query load, alert links and record change evidence.

## 12. 100-point assessment

| Domain | Points |
|---|---:|
| Dashboard UX, panels and units | 20 |
| Variables, labels and isolation | 20 |
| Transformations and query performance | 20 |
| Executable lab and 24 tests | 20 |
| Incident drills, runbooks and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory gates: no cross-tenant exposure, bounded variable choices, no-data semantics, stable datasource UID and passing offline tests.

## 13. Evidence worksheet

```text
UTC / operator / Grafana version:
Dashboard UID / folder / owner:
Datasource UID / query inspector evidence:
Variable values and interpolated queries:
Panel units / thresholds / no-data behavior:
Transformations and row-count checks:
Offline gate / 24 tests:
Incident drill / rollback / reviewer / score:
```

**Companion:** [Chapter 022 executable dashboard lab](labs/022-grafana-dashboard-design-variables-panels-transformations-production-visualization-patterns-lab.md).

**Next:** Chapter 023 — Grafana Advanced Dashboards, Provisioning, GitOps and Reusable Dashboard Libraries.
