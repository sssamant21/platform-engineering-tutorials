# Chapter 081 — Observability as Code Foundations, Repository Architecture and GitOps Workflows

**Part 17 — Observability as Code and GitOps (1/5)**  
**Audience:** SRE, DBRE, platform engineers, security and observability teams.  
**Prerequisites:** Chapters 001–080; Git, Kubernetes, Prometheus and Grafana basics.

## Learning outcomes

Manage Prometheus rules, Alertmanager routes, Grafana dashboards, Loki, Tempo and OpenTelemetry Collector configurations as version-controlled, peer-reviewed, testable artifacts promoted through staging to production.

## Reference architecture

```text
Git repository / CODEOWNERS / protected branch
                       |
           pull request + CI preflight
            /         |          \
       syntax       policy      secrets
                       |
                staging GitOps
                       |
        Prometheus / Grafana / Loki / Tempo
                       |
               SLI and paging tests
                       |
            approved production promotion
                       |
              drift + rollback audit
```

## Repository design

```text
observability-as-code/
  README.md
  CODEOWNERS
  environments/
    lab/
    staging/
    production/
  prometheus/
    rules/
    servicemonitors/
  alertmanager/
    routes/
  grafana/
    dashboards/
    datasources/
  loki/
  tempo/
  otel-collector/
  policies/
  tests/
  .github/workflows/
```

Separate shared definitions from environment overlays. Do not store plaintext credentials or customer data in Git. Pin image digests, Helm charts and policy versions. Production changes require approvals, a documented rollback and an audit trail. GitOps reconciles desired state but cannot independently prove a healthy application.

## Example PrometheusRule

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: api-slo
  namespace: monitoring
spec:
  groups:
    - name: api.slo
      rules:
        - alert: ApiHighErrorRate
          expr: |
            (
              sum(rate(http_requests_total{job="api",code=~"5.."}[5m]))
              /
              clamp_min(sum(rate(http_requests_total{job="api"}[5m])), 1e-9)
            ) > 0.0144
          for: 5m
          labels:
            severity: page
          annotations:
            summary: API high error fraction
```

This is an introductory example, **not a complete multiwindow SLO alert**. Production burn-rate paging should require paired short/long windows, traffic safeguards, absence detection and verified ownership.

## Example Grafana dashboard provisioning

```yaml
apiVersion: 1
providers:
  - name: sre-dashboards
    type: file
    allowUiUpdates: false
    options:
      path: /var/lib/grafana/dashboards
```

Provision datasources separately with secure references. Restrict access to sensitive dashboards and labels.

## CI and GitOps release workflow

1. Pull request updates a bounded config change with owner approval.
2. CI validates YAML, Prometheus rules (`promtool check rules`), policies and secret scanning.
3. Staging reconciles the pinned revision; verify scrapes, dashboard queries and alert routing.
4. Review cardinality, costs, retention, security and SLO impact.
5. Promote the same immutable artifact to production after explicit approval.
6. Detect drift, preserve evidence and rollback by reviewed Git revert when safe.

Example optional checks (require installed tools):

```bash
promtool check rules prometheus/rules/*.yaml
kubectl --context staging apply --dry-run=server -f prometheus/rules/
git diff --check
```

Do not run apply or sync commands against production as part of this chapter.

## DBRE-specific GitOps controls

PostgreSQL exporter labels must avoid SQL/PHI cardinality. Redis key names should not become metric labels. Kafka consumer group labels need governance. Elasticsearch/OpenSearch indices and Snowflake query identifiers may contain sensitive or high-cardinality values. Ensure alert rules map to actual service owners.

## Executable offline synthetic acceptance gate

### healthy.json

```json
{
  "owner": "observability-platform",
  "environment": "staging",
  "change_id": "OBS-081",
  "gitops_reviewed": true,
  "artifact_pinned": true,
  "secret_free": true,
  "destructive_action": false,
  "controls": {
    "repo_layout": true,
    "owners": true,
    "environments": true,
    "pinned_versions": true,
    "prometheus_rules": true,
    "alertmanager": true,
    "grafana": true,
    "loki": true,
    "tempo": true,
    "otel": true,
    "rbac": true,
    "secrets": true,
    "ci_lint": true,
    "policy": true,
    "pull_request": true,
    "staging": true,
    "drift": true,
    "rollback": true
  }
}
```

### gitops_gate.py

```python
"""Offline synthetic GitOps acceptance; does not deploy."""
import json,sys
from pathlib import Path
CONTROLS=["repo_layout","owners","environments","pinned_versions","prometheus_rules","alertmanager","grafana","loki","tempo","otel","rbac","secrets","ci_lint","policy","pull_request","staging","drift","rollback"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 e=[]
 for k in ("owner","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append("missing "+k)
 if p.get("environment") not in ("lab","staging"):e.append("unsafe environment")
 for k in ("gitops_reviewed","artifact_pinned","secret_free"):
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

### test_gitops_gate.py

```python
import copy,json,unittest
from pathlib import Path
from gitops_gate import validate
class GitOpsTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["controls"]["repo_layout"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["controls"]["owners"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["controls"]["environments"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["controls"]["pinned_versions"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["controls"]["prometheus_rules"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["controls"]["alertmanager"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["controls"]["grafana"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["controls"]["loki"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["controls"]["tempo"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["controls"]["otel"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["controls"]["rbac"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["controls"]["secrets"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["controls"]["ci_lint"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["controls"]["policy"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["controls"]["pull_request"]=False
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
  p["gitops_reviewed"]=false
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["artifact_pinned"]=false
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["secret_free"]=false
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
python3 gitops_gate.py healthy.json
python3 -m unittest -v test_gitops_gate.py
```

Expected PASS and **28 authored tests**. Execution not claimed; this gate checks attestations, not actual cluster state.

## 24 hands-on exercises

1. Create repository layout.
2. Define service ownership.
3. Declare environment overlays.
4. Pin chart versions.
5. Pin container digests.
6. Write PrometheusRule.
7. Write ServiceMonitor.
8. Write Alertmanager route.
9. Provision Grafana datasource.
10. Provision Grafana dashboard.
11. Define Loki retention.
12. Define Tempo sampling.
13. Configure OTel Collector.
14. Apply least-privilege RBAC.
15. Set secrets references.
16. Validate YAML syntax.
17. Validate rule syntax.
18. Review metric cardinality.
19. Create CI lint stage.
20. Create policy gate.
21. Review pull request.
22. Promote staging.
23. Verify drift.
24. Rehearse rollback.

## 24 production failure scenarios

1. **Unpinned image:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
2. **Bad PromQL:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
3. **Missing alert route:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
4. **Dashboard datasource mismatch:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
5. **ServiceMonitor selector mismatch:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
6. **Grafana secret leak:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
7. **Excessive metric labels:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
8. **Loki retention misconfiguration:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
9. **Tempo sampling blind spot:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
10. **Collector export failure:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
11. **Invalid Helm values:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
12. **Wrong namespace:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
13. **Overbroad RBAC:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
14. **Secret committed:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
15. **CI bypass:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
16. **Unreviewed promotion:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
17. **Environment drift:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
18. **Alert flood:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
19. **Missing scrape:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
20. **Misrouted pages:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
21. **Stale dashboard:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
22. **Bad rollback:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
23. **Staging/prod divergence:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.
24. **Repository ownership gap:** identify configuration drift, customer impact, policy gap, safe correction and rollback evidence.

## Eight production runbooks

1. **Repository bootstrap: owners, CODEOWNERS, environment folders and protected branches.**
2. **CI preflight: lint manifests, validate Prometheus rules, schemas and policy.**
3. **Security review: detect secrets, least privilege and pinned artifacts.**
4. **Staging promotion: deploy only approved immutable revisions and verify signals.**
5. **Alert acceptance: route test pages and validate paired burn windows.**
6. **Drift investigation: compare declared state with observed configuration.**
7. **Rollback: revert approved Git commit and reconcile safely.**
8. **Production readiness: evidence, audit, SLOs, owner sign-off and recovery.**

## 100-point assessment

| Domain | Points |
|---|---:|
| Repository architecture and ownership | 20 |
| Prometheus/Grafana/OTel configuration | 20 |
| CI validation and security controls | 20 |
| GitOps promotion and rollback | 20 |
| Observability acceptance and audit | 20 |
| **Total** | **100** |

Suggested pass 85/100. Production sign-off requires actual CI results, witnessed staging reconciliation, alert routing tests and owner approval.

**Companion:** [Chapter 081 lab](labs/081-observability-as-code-foundations-repository-architecture-gitops-workflows-lab.md).

**Next:** Chapter 082 — Prometheus, Alertmanager and Grafana Configuration as Code.
