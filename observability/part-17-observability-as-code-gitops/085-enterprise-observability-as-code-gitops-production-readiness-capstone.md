# Chapter 085 — Enterprise Observability as Code and GitOps Production Readiness Capstone

**Part 17 — Observability as Code and GitOps (5/5, final capstone)**

## Mission and architecture

Deliver a version-controlled, peer-reviewed observability stack with repeatable CI, policy checks, staged reconciliation, signal verification, drift response, rollback and audit evidence.

```text
Git + CODEOWNERS + pinned dependencies
             |
      CI + policy + secrets
             |
      immutable release artifact
             |
       staging Argo CD / Flux
             |
Prometheus + Alertmanager + Grafana
             |
 OpenTelemetry -> Loki + Tempo
             |
   SLO / page / trace / log tests
             |
     approved production gate
             |
  drift detection / safe rollback
```

## Production readiness principles

Observability as code must preserve service ownership, deterministic promotion and trustworthy signal delivery. A valid manifest is not proof that a rule evaluates, a page reaches on-call or a trace is queryable. Verify real staging outcomes before production approval.

Enforce least-privilege RBAC, protected branches, CODEOWNERS, pinned artifact digests, secret references, TLS, tenant isolation, sensitive-data redaction and bounded metric cardinality. Review Prometheus TSDB growth, Loki retention and Tempo sampling cost. Avoid leaking PostgreSQL SQL literals, Redis keys, Kafka message payloads, Elasticsearch identifiers and Snowflake query content.

## Reference CI workflow

```yaml
name: observability-readiness
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

Pin Actions by reviewed SHA for real deployment; add `promtool`, `amtool`, dashboard schema checks, Collector validation, policy-as-code, secret scanning and supply-chain provenance. Production promotion requires human approval and witnessed staging checks.

## Staging game day

1. Reconcile reviewed Git commit to isolated staging.
2. Trigger a bounded synthetic API SLO burn and verify Alertmanager test receiver delivery.
3. Emit a synthetic OTLP trace and log; verify Tempo/Loki and Grafana correlation.
4. Inject collector exporter failure and measure retry, queue and drop counters.
5. Introduce an unauthorized staging edit; detect drift and document emergency exception policy.
6. Revert a reviewed Git change; verify independent recovery of metrics, alerts, logs and traces.
7. Preserve UTC evidence, sign-off and corrective action ownership.

## DBRE reliability acceptance

Validate PostgreSQL connection and replication alerts, Redis latency and memory, Kafka consumer lag, Elasticsearch/OpenSearch search and storage pressure, Snowflake pipeline freshness and Kubernetes application SLIs. Tie each to an accountable owner, customer-impact severity, recovery threshold and tested paging route.

## Offline synthetic acceptance gate

Save the three files locally.

### healthy.json

```json
{
  "owner": "observability-sre",
  "environment": "staging",
  "change_id": "OBS-085",
  "peer_reviewed": true,
  "staging_evidence": true,
  "rollback_approved": true,
  "destructive_action": false,
  "controls": {
    "repo": true,
    "owners": true,
    "pinning": true,
    "prometheus": true,
    "slo": true,
    "alertmanager": true,
    "grafana": true,
    "otel": true,
    "loki": true,
    "tempo": true,
    "redaction": true,
    "rbac": true,
    "cardinality": true,
    "retention": true,
    "ci": true,
    "policy": true,
    "provenance": true,
    "staging": true,
    "alert_delivery": true,
    "correlation": true,
    "drift": true,
    "rollback": true,
    "approval": true,
    "acceptance": true
  }
}
```

### readiness_gate.py

```python
"""Offline synthetic observability readiness gate; no deployments."""
import json,sys
from pathlib import Path
CONTROLS=["repo","owners","pinning","prometheus","slo","alertmanager","grafana","otel","loki","tempo","redaction","rbac","cardinality","retention","ci","policy","provenance","staging","alert_delivery","correlation","drift","rollback","approval","acceptance"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 errors=[]
 for key in ("owner","change_id"):
  if not isinstance(p.get(key),str) or not p[key].strip():errors.append("missing "+key)
 if p.get("environment") not in ("lab","staging"):errors.append("unsafe environment")
 for key in ("peer_reviewed","staging_evidence","rollback_approved"):
  if p.get(key) is not True:errors.append("missing "+key)
 c=p.get("controls")
 if not isinstance(c,dict):errors.append("invalid controls");c={}
 for key in CONTROLS:
  if c.get(key) is not True:errors.append("unverified "+key)
 if p.get("destructive_action") is not False:errors.append("unsafe action")
 return errors
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());errors=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not errors else "FAIL","findings":errors},indent=2))
 sys.exit(bool(errors))

```

### test_readiness_gate.py

```python
import copy,json,unittest
from pathlib import Path
from readiness_gate import validate
class ReadinessTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["controls"]["repo"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["controls"]["owners"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["controls"]["pinning"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["controls"]["prometheus"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["controls"]["slo"]=False
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
  p["controls"]["otel"]=False
  self.assertTrue(validate(p))
 def test_negative_09(self):
  p=copy.deepcopy(self.p)
  p["controls"]["loki"]=False
  self.assertTrue(validate(p))
 def test_negative_10(self):
  p=copy.deepcopy(self.p)
  p["controls"]["tempo"]=False
  self.assertTrue(validate(p))
 def test_negative_11(self):
  p=copy.deepcopy(self.p)
  p["controls"]["redaction"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["controls"]["rbac"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["controls"]["cardinality"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["controls"]["retention"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["controls"]["ci"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["controls"]["policy"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["controls"]["provenance"]=False
  self.assertTrue(validate(p))
 def test_negative_18(self):
  p=copy.deepcopy(self.p)
  p["controls"]["staging"]=False
  self.assertTrue(validate(p))
 def test_negative_19(self):
  p=copy.deepcopy(self.p)
  p["controls"]["alert_delivery"]=False
  self.assertTrue(validate(p))
 def test_negative_20(self):
  p=copy.deepcopy(self.p)
  p["controls"]["correlation"]=False
  self.assertTrue(validate(p))
 def test_negative_21(self):
  p=copy.deepcopy(self.p)
  p["controls"]["drift"]=False
  self.assertTrue(validate(p))
 def test_negative_22(self):
  p=copy.deepcopy(self.p)
  p["controls"]["rollback"]=False
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["controls"]["approval"]=False
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["controls"]["acceptance"]=False
  self.assertTrue(validate(p))
 def test_negative_25(self):
  p=copy.deepcopy(self.p)
  p["owner"]=""
  self.assertTrue(validate(p))
 def test_negative_26(self):
  p=copy.deepcopy(self.p)
  p["environment"]="production"
  self.assertTrue(validate(p))
 def test_negative_27(self):
  p=copy.deepcopy(self.p)
  p["change_id"]=""
  self.assertTrue(validate(p))
 def test_negative_28(self):
  p=copy.deepcopy(self.p)
  p["peer_reviewed"]=false
  self.assertTrue(validate(p))
 def test_negative_29(self):
  p=copy.deepcopy(self.p)
  p["staging_evidence"]=false
  self.assertTrue(validate(p))
 def test_negative_30(self):
  p=copy.deepcopy(self.p)
  p["rollback_approved"]=false
  self.assertTrue(validate(p))
 def test_negative_31(self):
  p=copy.deepcopy(self.p)
  p["destructive_action"]=true
  self.assertTrue(validate(p))
 def test_negative_32(self):
  p=copy.deepcopy(self.p)
  p["controls"]=null
  self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
python3 readiness_gate.py healthy.json
python3 -m unittest -v test_readiness_gate.py
```

Expected PASS and **34 authored tests**. This synthetic attestation does not independently inspect a real cluster; no live execution is claimed.

## 24 hands-on exercises

1. Repository architecture: implement, review, verify and preserve evidence.
2. CODEOWNERS and approval: implement, review, verify and preserve evidence.
3. Immutable image pinning: implement, review, verify and preserve evidence.
4. PrometheusRule validation: implement, review, verify and preserve evidence.
5. SLO multiwindow alerts: implement, review, verify and preserve evidence.
6. Alertmanager routing: implement, review, verify and preserve evidence.
7. Grafana provisioning: implement, review, verify and preserve evidence.
8. OTel collector pipeline: implement, review, verify and preserve evidence.
9. Loki log ingestion: implement, review, verify and preserve evidence.
10. Tempo trace ingestion: implement, review, verify and preserve evidence.
11. Telemetry redaction: implement, review, verify and preserve evidence.
12. RBAC and secrets: implement, review, verify and preserve evidence.
13. Metric cardinality budget: implement, review, verify and preserve evidence.
14. Retention and FinOps: implement, review, verify and preserve evidence.
15. CI lint: implement, review, verify and preserve evidence.
16. Policy denial tests: implement, review, verify and preserve evidence.
17. Artifact provenance: implement, review, verify and preserve evidence.
18. Staging GitOps sync: implement, review, verify and preserve evidence.
19. Alert delivery smoke test: implement, review, verify and preserve evidence.
20. Cross-signal correlation: implement, review, verify and preserve evidence.
21. Drift classification: implement, review, verify and preserve evidence.
22. Safe Git revert: implement, review, verify and preserve evidence.
23. Production change review: implement, review, verify and preserve evidence.
24. Reliability acceptance: implement, review, verify and preserve evidence.

## 24 production incident scenarios

1. **Invalid PromQL:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
2. **Missing alert owner:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
3. **Misrouted page:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
4. **Silenced critical alert:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
5. **Grafana datasource mismatch:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
6. **Collector backpressure:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
7. **Loki ingestion failure:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
8. **Tempo trace loss:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
9. **PII in logs:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
10. **Overbroad RBAC:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
11. **Unpinned container:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
12. **Secrets in Git:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
13. **Cardinality explosion:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
14. **Storage retention spike:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
15. **Argo CD drift loop:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
16. **Flux sync error:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
17. **CI bypass:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
18. **Staging/prod divergence:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
19. **Wrong tenant route:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
20. **Missing SLO denominator:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
21. **No-data false green:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
22. **Unsafe rollback:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
23. **Stale provenance:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.
24. **Unverified production promotion:** identify impact, detection failure, policy gap, mitigation, rollback and evidence.

## Eight production runbooks

1. **Repository and ownership audit:** document prerequisites, owner, decision gate, verification and recovery.
2. **Prometheus and Alertmanager rule validation:** document prerequisites, owner, decision gate, verification and recovery.
3. **Grafana and OTLP staging smoke tests:** document prerequisites, owner, decision gate, verification and recovery.
4. **Policy, secrets and tenant isolation:** document prerequisites, owner, decision gate, verification and recovery.
5. **Cost and cardinality control:** document prerequisites, owner, decision gate, verification and recovery.
6. **Drift triage and emergency change exception:** document prerequisites, owner, decision gate, verification and recovery.
7. **Approved rollback and independent recovery:** document prerequisites, owner, decision gate, verification and recovery.
8. **Production acceptance and postmortem follow-up:** document prerequisites, owner, decision gate, verification and recovery.

## 100-point production readiness assessment

| Domain | Points |
|---|---:|
| Repository architecture, ownership and provenance | 20 |
| Prometheus, Alertmanager, Grafana and SLO verification | 20 |
| OTel, Loki, Tempo, privacy and cost controls | 20 |
| CI, policy, GitOps promotion and drift response | 20 |
| Safe rollback, audit evidence and incident acceptance | 20 |
| **Total** | **100** |

Recommended passing score 85/100; require no critical security exceptions and witnessed staging rollback. Sign-off: platform owner, security, service owner and on-call lead.

**Companion:** [Chapter 085 lab](labs/085-enterprise-observability-as-code-gitops-production-readiness-capstone-lab.md).

**Part 17 complete. Next:** Chapter 086 — Enterprise Observability Scale, Capacity Planning and High Availability Architecture (Part 18).
