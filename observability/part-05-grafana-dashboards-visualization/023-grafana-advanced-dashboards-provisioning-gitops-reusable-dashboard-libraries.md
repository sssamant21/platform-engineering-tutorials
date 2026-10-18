# Chapter 023 — Grafana Advanced Dashboards, Provisioning, GitOps and Reusable Dashboard Libraries

**Part 05 — Grafana Dashboards and Visualization**  
**Audience:** Enterprise SRE/DBRE, platform and observability engineers.  
**Prerequisites:** Chapters 021–022, PromQL, Python 3.10+, Git and a staging Grafana for optional integration.  
**Goal:** Manage reusable Grafana dashboards through reviewed, reproducible GitOps workflows, safe provisioning, and environment-aware validation.

## 1. Enterprise architecture

```text
Dashboard source / Jsonnet or templates
             |
     Git pull request / CODEOWNERS
             |
   lint + JSON validation + policy gate
             |
    staging provisioning / API tests
             |
    approval and environment promotion
             |
  Grafana folders / datasources / RBAC
             |
    operational dashboards + rollback
```

Dashboards are software artifacts: version them, review them, test queries, assign ownership, and roll back deliberately. Reusable dashboard libraries should centralize conventions without accidentally merging tenant data.

## 2. Provisioning options and tradeoffs

| Option | Strength | Caveat |
|---|---|---|
| File provisioning | declarative dashboards, straightforward audit | provisioning owns changes; filesystem synchronization |
| Grafana HTTP API | flexible lifecycle and automation | credentials, retries, concurrency, version behavior |
| Terraform Grafana provider | stateful infrastructure management | state and provider compatibility |
| Grafana Operator / Kubernetes | cluster-native reconciliation | CRD/controller lifecycle |
| Jsonnet/Grafonnet | reusable dashboard definitions | compilation and library versioning |

Avoid managing the same dashboard simultaneously with multiple controllers. Establish one authoritative source per folder/dashboard and a documented drift-reconciliation policy.

## 3. Repository structure

```text
grafana-gitops/
  dashboards/
    postgres.json
    redis.json
  fixtures/
    manifest.json
    degraded.json
  scripts/
    gitops_gate.py
  tests/
    test_gitops_gate.py
  environments/
    staging/
    production/
  README.md
```

A production pipeline should also include compatible Grafana JSON/schema checks, PromQL tests, provisioning smoke tests, change approvals, dashboard screenshots when needed, and secret scanning. The offline gate in this chapter is a teaching example, not a complete security enforcement engine.

## 4. Reusable dashboard contract

Stable UIDs, consistent labels, datasource UIDs, owner tags, cluster-scoped variables, approved refresh intervals, panel budget and clear rollback revision are foundational. For PostgreSQL and Redis, avoid relying on a single `job` label to guarantee tenant isolation; enforce datasource and backend permissions separately.

### fixtures/manifest.json

```json
{
  "schema_version": 1,
  "environment": "staging",
  "owner": "platform-observability",
  "folder_uid": "dbre-fleet",
  "datasource_uid": "prometheus-primary",
  "dashboards": [
    {
      "uid": "dbre-postgres-023",
      "title": "DBRE PostgreSQL Fleet",
      "source": "dashboards/postgres.json",
      "owner": "dbre-postgres",
      "reviewed": true,
      "tested": true,
      "cluster_scoped": true,
      "tenant_scoped": true,
      "refresh": "1m",
      "estimated_queries_per_minute": 24,
      "panels": 8
    },
    {
      "uid": "dbre-redis-023",
      "title": "DBRE Redis Fleet",
      "source": "dashboards/redis.json",
      "owner": "dbre-redis",
      "reviewed": true,
      "tested": true,
      "cluster_scoped": true,
      "tenant_scoped": true,
      "refresh": "1m",
      "estimated_queries_per_minute": 18,
      "panels": 6
    }
  ],
  "max_queries_per_minute": 100,
  "rollback_revision": "git:previous-reviewed-commit",
  "promotion_approved": true
}
```

### fixtures/degraded.json

```json
{
  "schema_version": 1,
  "environment": "staging",
  "owner": "platform-observability",
  "folder_uid": "dbre-fleet",
  "datasource_uid": "prometheus-primary",
  "dashboards": [
    {
      "uid": "dbre-postgres-023",
      "title": "DBRE PostgreSQL Fleet",
      "source": "dashboards/postgres.json",
      "owner": "dbre-postgres",
      "reviewed": false,
      "tested": true,
      "cluster_scoped": true,
      "tenant_scoped": false,
      "refresh": "1s",
      "estimated_queries_per_minute": 24,
      "panels": 8
    },
    {
      "uid": "dbre-postgres-023",
      "title": "DBRE Redis Fleet",
      "source": "dashboards/redis.json",
      "owner": "dbre-redis",
      "reviewed": true,
      "tested": true,
      "cluster_scoped": true,
      "tenant_scoped": true,
      "refresh": "1m",
      "estimated_queries_per_minute": 18,
      "panels": 6
    }
  ],
  "max_queries_per_minute": 20,
  "rollback_revision": "git:previous-reviewed-commit",
  "promotion_approved": false
}
```

### dashboards/postgres.json

```json
{
  "uid": "dbre-postgres-023",
  "title": "DBRE PostgreSQL Fleet",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "1m",
  "tags": [
    "dbre",
    "gitops",
    "chapter-023"
  ],
  "time": {
    "from": "now-6h",
    "to": "now"
  },
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
          "query": "label_values(up, cluster)",
          "refId": "cluster"
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
      "type": "timeseries",
      "title": "Target health by instance",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus-primary"
      },
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 24,
        "h": 8
      },
      "targets": [
        {
          "refId": "A",
          "expr": "up{cluster=\"$cluster\",job=\"postgres\"}",
          "legendFormat": "{{instance}}"
        }
      ]
    }
  ]
}
```

### dashboards/redis.json

```json
{
  "uid": "dbre-redis-023",
  "title": "DBRE Redis Fleet",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "1m",
  "tags": [
    "dbre",
    "gitops",
    "chapter-023"
  ],
  "time": {
    "from": "now-6h",
    "to": "now"
  },
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
          "query": "label_values(up, cluster)",
          "refId": "cluster"
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
      "type": "timeseries",
      "title": "Target health by instance",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus-primary"
      },
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 24,
        "h": 8
      },
      "targets": [
        {
          "refId": "A",
          "expr": "up{cluster=\"$cluster\",job=\"redis\"}",
          "legendFormat": "{{instance}}"
        }
      ]
    }
  ]
}
```

These dashboards demonstrate stable identity and cluster filtering, not full production DBRE signal coverage. Query `up` detects discovered targets, not expected-but-undiscovered instances.

## 5. GitOps CI/CD workflow

```text
PR opened
 -> JSON lint and formatting
 -> static policy and source consistency
 -> PromQL correctness in staging
 -> dashboard import / datasource smoke test
 -> access and query-budget review
 -> owner approval
 -> staging promotion and smoke tests
 -> production canary and rollback checkpoint
```

Do not commit Grafana admin tokens, datasource credentials or secrets. Use ephemeral CI credentials with least privilege and environment-scoped permissions. Validate that a dashboard's data source can access only authorized telemetry; variables are not an access-control mechanism.

## 6. Complete executable offline lab

The Python validator checks a JSON manifest and dashboard source files for governance requirements, budget, UID consistency, basic PromQL cluster scoping and approval. It does **not** parse PromQL, query Grafana, enforce actual RBAC, or prove GitOps reconciliation.

### scripts/gitops_gate.py

```python
#!/usr/bin/env python3
"""Offline Grafana GitOps manifest gate; no Grafana API calls."""
import json,sys,re
from pathlib import Path
UID=re.compile(r"^[A-Za-z0-9_-]{1,40}$")
def check(m):
    issues=[]
    if not isinstance(m,dict): return ["manifest must be object"]
    if m.get("schema_version")!=1: issues.append("unsupported schema")
    for k in ("environment","owner","folder_uid","datasource_uid","rollback_revision"):
        if not isinstance(m.get(k),str) or not m[k].strip(): issues.append("missing "+k)
    if m.get("datasource_uid")!="prometheus-primary": issues.append("unexpected datasource")
    if m.get("promotion_approved") is not True: issues.append("promotion not approved")
    budget=m.get("max_queries_per_minute")
    if type(budget) is not int or budget<=0: issues.append("invalid query budget")
    items=m.get("dashboards")
    if not isinstance(items,list) or not items: return issues+["missing dashboards"]
    seen=set();total=0
    for i,d in enumerate(items):
        p=f"dashboard[{i}]"
        if not isinstance(d,dict): issues.append(p+" invalid");continue
        uid=d.get("uid")
        if not isinstance(uid,str) or not UID.fullmatch(uid): issues.append(p+" invalid uid")
        elif uid in seen: issues.append(p+" duplicate uid")
        else: seen.add(uid)
        for k in ("title","source","owner"):
            if not isinstance(d.get(k),str) or not d[k].strip(): issues.append(p+" missing "+k)
        if not isinstance(d.get("source"),str) or not re.fullmatch(r"dashboards/[a-z0-9_-]+\.json",d["source"]):
            issues.append(p+" invalid source path")
        for k in ("reviewed","tested","cluster_scoped","tenant_scoped"):
            if d.get(k) is not True: issues.append(p+" mandatory "+k)
        if d.get("refresh") not in ("30s","1m","5m"): issues.append(p+" unsafe refresh")
        q=d.get("estimated_queries_per_minute")
        if type(q) is not int or q<0: issues.append(p+" invalid query estimate")
        else: total+=q
        panels=d.get("panels")
        if type(panels) is not int or panels<=0 or panels>50: issues.append(p+" invalid panel count")
    if type(budget) is int and total>budget: issues.append("query budget exceeded")
    return issues
def validate_sources(m,root):
    issues=[]
    for d in m.get("dashboards",[]):
        if not isinstance(d,dict) or not isinstance(d.get("source"),str): continue
        path=root/d["source"]
        try: dashboard=json.loads(path.read_text())
        except (OSError,ValueError): issues.append("unreadable dashboard "+d["source"]);continue
        if dashboard.get("uid")!=d.get("uid"): issues.append("UID mismatch "+d["source"])
        if dashboard.get("title")!=d.get("title"): issues.append("title mismatch "+d["source"])
        if dashboard.get("refresh")!=d.get("refresh"): issues.append("refresh mismatch "+d["source"])
        panels=dashboard.get("panels")
        if not isinstance(panels,list) or not panels: issues.append("missing panels "+d["source"])
        for p in panels if isinstance(panels,list) else []:
            if p.get("datasource",{}).get("uid")!=m.get("datasource_uid"):
                issues.append("datasource mismatch "+d["source"])
            for target in p.get("targets",[]):
                if 'cluster="$cluster"' not in target.get("expr",""):
                    issues.append("unscoped query "+d["source"])
    return issues
if __name__=="__main__":
    if len(sys.argv)!=3: sys.exit("usage: python3 gitops_gate.py manifest.json project-root")
    try:
        m=json.loads(Path(sys.argv[1]).read_text())
        findings=check(m)+validate_sources(m,Path(sys.argv[2]))
    except (OSError,ValueError) as e: sys.exit(f"input error: {e}")
    print(json.dumps({"status":"PASS" if not findings else "FAIL","findings":findings},indent=2))
    sys.exit(bool(findings))
```

### tests/test_gitops_gate.py

```python
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from gitops_gate import check,validate_sources
class GitOpsTests(unittest.TestCase):
    def setUp(self): self.m=json.loads((ROOT/"fixtures"/"manifest.json").read_text())
    def changed(self,callback):
        d=copy.deepcopy(self.m);callback(d);return check(d)
    def test_healthy(self): self.assertEqual(check(self.m),[])
    def test_sources(self): self.assertEqual(validate_sources(self.m,ROOT),[])
    def test_invalid_manifest(self): self.assertTrue(check(None))
    def test_schema(self): self.assertTrue(self.changed(lambda d:d.update(schema_version=2)))
    def test_owner(self): self.assertTrue(self.changed(lambda d:d.update(owner="")))
    def test_folder(self): self.assertTrue(self.changed(lambda d:d.update(folder_uid="")))
    def test_datasource(self): self.assertTrue(self.changed(lambda d:d.update(datasource_uid="other")))
    def test_rollback(self): self.assertTrue(self.changed(lambda d:d.update(rollback_revision="")))
    def test_approval(self): self.assertTrue(self.changed(lambda d:d.update(promotion_approved=False)))
    def test_budget(self): self.assertTrue(self.changed(lambda d:d.update(max_queries_per_minute=10)))
    def test_missing_dashboards(self): self.assertTrue(self.changed(lambda d:d.update(dashboards=[])))
    def test_duplicate_uid(self): self.assertTrue(self.changed(lambda d:d["dashboards"][1].update(uid=d["dashboards"][0]["uid"])))
    def test_bad_uid(self): self.assertTrue(self.changed(lambda d:d["dashboards"][0].update(uid="bad uid")))
    def test_bad_path(self): self.assertTrue(self.changed(lambda d:d["dashboards"][0].update(source="../secret")))
    def test_review(self): self.assertTrue(self.changed(lambda d:d["dashboards"][0].update(reviewed=False)))
    def test_tested(self): self.assertTrue(self.changed(lambda d:d["dashboards"][0].update(tested=False)))
    def test_cluster(self): self.assertTrue(self.changed(lambda d:d["dashboards"][0].update(cluster_scoped=False)))
    def test_tenant(self): self.assertTrue(self.changed(lambda d:d["dashboards"][0].update(tenant_scoped=False)))
    def test_refresh(self): self.assertTrue(self.changed(lambda d:d["dashboards"][0].update(refresh="1s")))
    def test_query_estimate(self): self.assertTrue(self.changed(lambda d:d["dashboards"][0].update(estimated_queries_per_minute=-1)))
    def test_panel_count(self): self.assertTrue(self.changed(lambda d:d["dashboards"][0].update(panels=100)))
    def test_invalid_budget(self): self.assertTrue(self.changed(lambda d:d.update(max_queries_per_minute=0)))
    def test_invalid_source(self): self.assertTrue(self.changed(lambda d:d["dashboards"][0].update(source="dashboards/missing.json")))
    def test_degraded(self):
        d=json.loads((ROOT/"fixtures"/"degraded.json").read_text())
        self.assertTrue(check(d))
if __name__=="__main__": unittest.main()
```

### Run

```bash
cd grafana-gitops
python3 scripts/gitops_gate.py fixtures/manifest.json .
if python3 scripts/gitops_gate.py fixtures/degraded.json .; then
  echo "FAIL: degraded manifest accepted"; exit 1
else
  echo "PASS: degraded manifest rejected"
fi
python3 -m unittest discover -s tests -v
```

Expected: healthy manifest PASS, degraded manifest FAIL and **24 automated unit tests pass**. The lab uses only the Python standard library.

## 7. Safe rollout and rollback

Use separate environment overlays and explicit version references; stage dashboards with a consistent datasource UID contract. Capture the last known-good Git commit, Grafana version, plugin versions and dashboard UIDs. On failure, revert the Git change and allow the chosen controller to reconcile. Validate query outputs, access permissions and owner links after rollback.

A successful Git merge does not prove that Grafana loaded the dashboard. Verify actual state via the UI/API or provisioning logs, and test representative panels in staging.

## 8. Twenty-four hands-on exercises

1. Design GitOps repository layout.
2. Separate staging and production overlays.
3. Pin Grafana and plugin versions.
4. Define folder UID ownership.
5. Define datasource UID contract.
6. Author reusable dashboard template.
7. Apply cluster-scoped variables.
8. Define dashboard JSON metadata.
9. Define stable panel IDs.
10. Review UID collision behavior.
11. Provision dashboards from files.
12. Compare API versus file provisioning.
13. Plan Git PR review workflow.
14. Validate schema with compatible tooling.
15. Validate PromQL against staging.
16. Estimate refresh/query cost.
17. Set query budget.
18. Enforce tenant isolation.
19. Review RBAC folder boundaries.
20. Test dashboard library reuse.
21. Run healthy policy gate.
22. Reject degraded fixture.
23. Execute 24 tests and failure drills.
24. Run promotion/rollback tabletop.

## 9. Twenty-four production failure scenarios

| # | Scenario | First investigation |
|---|---|---|
| 01 | GitOps sync failure | Compare Git desired state, provisioning logs, Grafana API and owner |
| 02 | dashboard UID collision | Compare Git desired state, provisioning logs, Grafana API and owner |
| 03 | datasource UID mismatch | Compare Git desired state, provisioning logs, Grafana API and owner |
| 04 | folder UID mismatch | Compare Git desired state, provisioning logs, Grafana API and owner |
| 05 | provisioning provider path wrong | Compare Git desired state, provisioning logs, Grafana API and owner |
| 06 | dashboard JSON parse error | Compare Git desired state, provisioning logs, Grafana API and owner |
| 07 | Grafana version schema drift | Compare Git desired state, provisioning logs, Grafana API and owner |
| 08 | plugin version incompatibility | Compare Git desired state, provisioning logs, Grafana API and owner |
| 09 | missing source dashboard | Compare Git desired state, provisioning logs, Grafana API and owner |
| 10 | stale dashboard revision | Compare Git desired state, provisioning logs, Grafana API and owner |
| 11 | unreviewed dashboard change | Compare Git desired state, provisioning logs, Grafana API and owner |
| 12 | unbounded variable fanout | Compare Git desired state, provisioning logs, Grafana API and owner |
| 13 | cluster scope removed | Compare Git desired state, provisioning logs, Grafana API and owner |
| 14 | tenant scope removed | Compare Git desired state, provisioning logs, Grafana API and owner |
| 15 | query budget exceeded | Compare Git desired state, provisioning logs, Grafana API and owner |
| 16 | panel count explosion | Compare Git desired state, provisioning logs, Grafana API and owner |
| 17 | Grafana RBAC denies access | Compare Git desired state, provisioning logs, Grafana API and owner |
| 18 | provisioned dashboard edited manually | Compare Git desired state, provisioning logs, Grafana API and owner |
| 19 | promotion without approval | Compare Git desired state, provisioning logs, Grafana API and owner |
| 20 | rollback revision missing | Compare Git desired state, provisioning logs, Grafana API and owner |
| 21 | multi-environment drift | Compare Git desired state, provisioning logs, Grafana API and owner |
| 22 | Git merge conflict | Compare Git desired state, provisioning logs, Grafana API and owner |
| 23 | datasource secret leaked | Compare Git desired state, provisioning logs, Grafana API and owner |
| 24 | Grafana API rate limit | Compare Git desired state, provisioning logs, Grafana API and owner |

## 10. Eight production runbooks

**A. Provisioning failure:** Inspect provider path, Grafana startup logs, JSON validity, dashboard UID and datasource UID.

**B. GitOps drift:** Compare desired manifest with live API state; restore reviewed revision and record manual changes.

**C. Query budget regression:** Inspect refresh rates, panel counts, variable fanout and Prometheus query load; revert expensive changes.

**D. RBAC or tenancy incident:** Audit folders, datasource permissions, service accounts and cluster/tenant scoping; restrict access immediately.

**E. Upgrade incompatibility:** Validate pinned Grafana/plugin versions and dashboard schema in staging; revert image if needed.

**F. Datasource migration:** Preserve stable UIDs or migrate references atomically, validate all dashboards and rollback.

**G. Dashboard ownership handoff:** Review service owner, SLO, runbook links, change records and stale dashboards.

**H. Promotion and rollback:** Validate PR, test artifacts, canary dashboard, approval, post-deploy checks and known-good Git revision.

## 11. 100-point assessment

| Area | Points |
|---|---:|
| Grafana provisioning architecture | 20 |
| Reusable dashboard libraries and GitOps | 20 |
| Security, tenancy and query budgets | 20 |
| Offline governance gate and 24 tests | 20 |
| Troubleshooting, runbooks and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Mandatory gates: unique dashboard UIDs, reviewed/tested source, tenant isolation, bounded query cost, approved promotion and rollback revision.

## 12. Evidence worksheet

```text
UTC / owner / Grafana version / environment:
Git revision / PR / reviewers:
Dashboard and folder UIDs:
Datasource UID and access controls:
Manifest and dashboard source consistency:
Query estimate / refresh budget:
Healthy/degraded gate / 24 tests:
Optional staging import and query checks:
Canary / rollback revision / reviewer / score:
```

**Companion:** [Chapter 023 executable GitOps lab](labs/023-grafana-advanced-dashboards-provisioning-gitops-reusable-dashboard-libraries-lab.md).

**Next:** Chapter 024 — Grafana Alerting, Contact Points, Notification Policies and SRE Incident Workflows.
