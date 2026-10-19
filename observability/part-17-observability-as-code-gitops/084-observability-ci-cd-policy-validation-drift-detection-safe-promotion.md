# Chapter 084 — Observability CI/CD, Policy Validation, Drift Detection and Safe Promotion

**Part 17 — Observability as Code and GitOps (4/5)**

## Architecture and theory

```text
Git PR -> CODEOWNERS -> CI lint + semantic validation -> policy + secret checks
     -> immutable artifact -> isolated staging GitOps -> SLI / alert / trace tests
     -> approval -> production promotion -> drift detection -> audited rollback
```

Validate Prometheus with `promtool check rules`, Alertmanager with `amtool check-config`, Grafana JSON with schema-aware tests and OpenTelemetry Collector configuration using the pinned distribution. Pin CI actions and container images to immutable digests. Enforce secrets scanning, least-privilege RBAC, environment separation, tenant isolation, metric-cardinality budgets and approved retention. Protect production paging receivers from staging tests. Record change ID, owner, Git SHA, image digest and reviewer evidence.

CI success does not prove alert delivery or telemetry health. Reconcile reviewed staging artifacts, generate a bounded synthetic alert and trace, verify Grafana queries and Loki/Tempo ingestion, and confirm SLO coverage. Drift reconciliation must account for incident-time manual mitigation and require approval before overriding it. Rollback by reverting the approved Git commit, checking compatibility and verifying independent monitoring recovery.

## Example CI pipeline

```yaml
name: observability-preflight
on: [pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: git diff --check
      - run: python3 -m unittest discover -s tests -p 'test_*.py'
```

Pin Actions to reviewed commit SHAs in real environments and add pinned binaries, PromQL/Alertmanager validation, policy tests and secret scanning. For DBRE, reject PostgreSQL query literals, Redis keys, Kafka message identifiers, Elasticsearch per-document labels and Snowflake query identifiers as unbounded/sensitive telemetry labels.

## Executable offline lab

Save the following as `healthy.json`, `cicd_gate.py`, and `test_cicd_gate.py`:

```json
{
  "owner": "sre",
  "environment": "staging",
  "change_id": "OBS-084",
  "approved": true,
  "policy_passed": true,
  "staging_verified": true,
  "destructive_action": false,
  "checks": {
    "ownership": true,
    "branch": true,
    "pinning": true,
    "yaml": true,
    "promql": true,
    "alertmanager": true,
    "grafana": true,
    "otel": true,
    "secrets": true,
    "identity": true,
    "rbac": true,
    "retention": true,
    "cardinality": true,
    "slo": true,
    "staging_route": true,
    "provenance": true,
    "staging": true,
    "drift": true,
    "approval": true,
    "rollback": true
  }
}
```

```python
import json,sys
from pathlib import Path
CHECKS=["ownership","branch","pinning","yaml","promql","alertmanager","grafana","otel","secrets","identity","rbac","retention","cardinality","slo","staging_route","provenance","staging","drift","approval","rollback"]
def validate(p):
 if not isinstance(p,dict):return ["not object"]
 e=[]
 for k in ("owner","change_id"):
  if not isinstance(p.get(k),str) or not p[k].strip():e.append(k)
 if p.get("environment") not in ("lab","staging"):e.append("environment")
 for k in ("approved","policy_passed","staging_verified"):
  if p.get(k) is not True:e.append(k)
 c=p.get("checks")
 if not isinstance(c,dict):e.append("checks");c={}
 for k in CHECKS:
  if c.get(k) is not True:e.append(k)
 if p.get("destructive_action") is not False:e.append("destructive_action")
 return e
if __name__=="__main__":
 try:e=validate(json.loads(Path(sys.argv[1]).read_text()))
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print("PASS" if not e else "FAIL: "+",".join(e));sys.exit(bool(e))
```

```python
import unittest,json,copy
from pathlib import Path
from cicd_gate import validate
class GateTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_pass(self):self.assertFalse(validate(self.p))
 def test_invalid_type(self):self.assertTrue(validate(None))
 def test_missing_control_1(self):
  p=copy.deepcopy(self.p);p["checks"]["ownership"]=False;self.assertTrue(validate(p))
 def test_missing_control_2(self):
  p=copy.deepcopy(self.p);p["checks"]["branch"]=False;self.assertTrue(validate(p))
 def test_missing_control_3(self):
  p=copy.deepcopy(self.p);p["checks"]["pinning"]=False;self.assertTrue(validate(p))
 def test_missing_control_4(self):
  p=copy.deepcopy(self.p);p["checks"]["yaml"]=False;self.assertTrue(validate(p))
 def test_missing_control_5(self):
  p=copy.deepcopy(self.p);p["checks"]["promql"]=False;self.assertTrue(validate(p))
 def test_missing_control_6(self):
  p=copy.deepcopy(self.p);p["checks"]["alertmanager"]=False;self.assertTrue(validate(p))
 def test_missing_control_7(self):
  p=copy.deepcopy(self.p);p["checks"]["grafana"]=False;self.assertTrue(validate(p))
 def test_missing_control_8(self):
  p=copy.deepcopy(self.p);p["checks"]["otel"]=False;self.assertTrue(validate(p))
 def test_missing_control_9(self):
  p=copy.deepcopy(self.p);p["checks"]["secrets"]=False;self.assertTrue(validate(p))
 def test_missing_control_10(self):
  p=copy.deepcopy(self.p);p["checks"]["identity"]=False;self.assertTrue(validate(p))
 def test_missing_control_11(self):
  p=copy.deepcopy(self.p);p["checks"]["rbac"]=False;self.assertTrue(validate(p))
 def test_missing_control_12(self):
  p=copy.deepcopy(self.p);p["checks"]["retention"]=False;self.assertTrue(validate(p))
 def test_missing_control_13(self):
  p=copy.deepcopy(self.p);p["checks"]["cardinality"]=False;self.assertTrue(validate(p))
 def test_missing_control_14(self):
  p=copy.deepcopy(self.p);p["checks"]["slo"]=False;self.assertTrue(validate(p))
 def test_missing_control_15(self):
  p=copy.deepcopy(self.p);p["checks"]["staging_route"]=False;self.assertTrue(validate(p))
 def test_missing_control_16(self):
  p=copy.deepcopy(self.p);p["checks"]["provenance"]=False;self.assertTrue(validate(p))
 def test_missing_control_17(self):
  p=copy.deepcopy(self.p);p["checks"]["staging"]=False;self.assertTrue(validate(p))
 def test_missing_control_18(self):
  p=copy.deepcopy(self.p);p["checks"]["drift"]=False;self.assertTrue(validate(p))
 def test_missing_control_19(self):
  p=copy.deepcopy(self.p);p["checks"]["approval"]=False;self.assertTrue(validate(p))
 def test_missing_control_20(self):
  p=copy.deepcopy(self.p);p["checks"]["rollback"]=False;self.assertTrue(validate(p))
 def test_bad_field_1(self):
  p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
 def test_bad_field_2(self):
  p=copy.deepcopy(self.p);p["change_id"]="";self.assertTrue(validate(p))
 def test_bad_field_3(self):
  p=copy.deepcopy(self.p);p["environment"]="production";self.assertTrue(validate(p))
 def test_bad_field_4(self):
  p=copy.deepcopy(self.p);p["approved"]=false;self.assertTrue(validate(p))
 def test_bad_field_5(self):
  p=copy.deepcopy(self.p);p["policy_passed"]=false;self.assertTrue(validate(p))
 def test_bad_field_6(self):
  p=copy.deepcopy(self.p);p["staging_verified"]=false;self.assertTrue(validate(p))
 def test_bad_field_7(self):
  p=copy.deepcopy(self.p);p["destructive_action"]=true;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()
```

```bash
python3 cicd_gate.py healthy.json
python3 -m unittest -v test_cicd_gate.py
```

Expected PASS and **29 authored tests**; not executed here. Synthetic attestation is not proof of live deployment readiness.

## 24 exercises

1. CODEOWNERS: implement, validate and record evidence.
2. Branch protection: implement, validate and record evidence.
3. Pinned dependencies: implement, validate and record evidence.
4. YAML lint: implement, validate and record evidence.
5. Prometheus rules: implement, validate and record evidence.
6. Alertmanager routes: implement, validate and record evidence.
7. Grafana JSON: implement, validate and record evidence.
8. Collector config: implement, validate and record evidence.
9. Secret scanning: implement, validate and record evidence.
10. Least privilege: implement, validate and record evidence.
11. Tenant isolation: implement, validate and record evidence.
12. Retention policy: implement, validate and record evidence.
13. Cardinality budget: implement, validate and record evidence.
14. SLO coverage: implement, validate and record evidence.
15. Staging paging: implement, validate and record evidence.
16. Artifact provenance: implement, validate and record evidence.
17. Staging reconciliation: implement, validate and record evidence.
18. Drift detection: implement, validate and record evidence.
19. Exception review: implement, validate and record evidence.
20. Rollback: implement, validate and record evidence.
21. Evidence collection: implement, validate and record evidence.
22. Owner signoff: implement, validate and record evidence.
23. CI failure simulation: implement, validate and record evidence.
24. Recovery verification: implement, validate and record evidence.

## 24 incident scenarios

1. **Malformed YAML:** identify policy/CI failure, customer risk, remediation and rollback.
2. **Invalid PromQL:** identify policy/CI failure, customer risk, remediation and rollback.
3. **Bad routing:** identify policy/CI failure, customer risk, remediation and rollback.
4. **Dashboard mismatch:** identify policy/CI failure, customer risk, remediation and rollback.
5. **Exporter failure:** identify policy/CI failure, customer risk, remediation and rollback.
6. **Secret exposure:** identify policy/CI failure, customer risk, remediation and rollback.
7. **Unpinned image:** identify policy/CI failure, customer risk, remediation and rollback.
8. **Policy bypass:** identify policy/CI failure, customer risk, remediation and rollback.
9. **Excessive RBAC:** identify policy/CI failure, customer risk, remediation and rollback.
10. **High cardinality:** identify policy/CI failure, customer risk, remediation and rollback.
11. **Unsafe retention:** identify policy/CI failure, customer risk, remediation and rollback.
12. **Wrong paging target:** identify policy/CI failure, customer risk, remediation and rollback.
13. **Missing owner:** identify policy/CI failure, customer risk, remediation and rollback.
14. **Artifact mismatch:** identify policy/CI failure, customer risk, remediation and rollback.
15. **Drift loop:** identify policy/CI failure, customer risk, remediation and rollback.
16. **Unauthorized patch:** identify policy/CI failure, customer risk, remediation and rollback.
17. **Argo sync failure:** identify policy/CI failure, customer risk, remediation and rollback.
18. **Flux sync failure:** identify policy/CI failure, customer risk, remediation and rollback.
19. **Stale CI evidence:** identify policy/CI failure, customer risk, remediation and rollback.
20. **Approval gap:** identify policy/CI failure, customer risk, remediation and rollback.
21. **Rollback mismatch:** identify policy/CI failure, customer risk, remediation and rollback.
22. **Missing telemetry:** identify policy/CI failure, customer risk, remediation and rollback.
23. **Alert silence:** identify policy/CI failure, customer risk, remediation and rollback.
24. **False-green pipeline:** identify policy/CI failure, customer risk, remediation and rollback.

## Eight runbooks

1. **CI lint and semantic validation:** identify owner, prerequisites, verification, rollback and audit evidence.
2. **Security and secrets policy enforcement:** identify owner, prerequisites, verification, rollback and audit evidence.
3. **Immutable provenance review:** identify owner, prerequisites, verification, rollback and audit evidence.
4. **Staging reconciliation and alert delivery:** identify owner, prerequisites, verification, rollback and audit evidence.
5. **Drift detection and exception handling:** identify owner, prerequisites, verification, rollback and audit evidence.
6. **Production promotion approval:** identify owner, prerequisites, verification, rollback and audit evidence.
7. **Revert and rollback verification:** identify owner, prerequisites, verification, rollback and audit evidence.
8. **Incident audit and corrective action:** identify owner, prerequisites, verification, rollback and audit evidence.

## 100-point acceptance

CI validation 20; security and policy 20; provenance and staging 20; drift and rollback 20; audit and recovery 20. Recommended pass: 85. Require witnessed staging tests and owner approval for production sign-off.

[Companion lab](labs/084-observability-ci-cd-policy-validation-drift-detection-safe-promotion-lab.md)

**Next:** Chapter 085 — Enterprise Observability as Code and GitOps Production Readiness Capstone.
