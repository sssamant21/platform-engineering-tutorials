# Chapter 083 — OpenTelemetry, Loki and Tempo Pipelines as Code

**Part 17 — Observability as Code and GitOps (3/5)**

## Outcomes

Version-control OpenTelemetry Collector pipelines, Loki log ingestion and Tempo trace ingestion; validate security, sampling, backpressure, data retention, correlation, GitOps promotion and rollback. Build a repeatable offline test suite and a witnessed staging acceptance plan.

## Architecture

```text
Application SDKs / Kubernetes logs
               |
         OTLP / filelog
               |
    OpenTelemetry Collector
      /     |      |       \
   memory  batch  redact   retry
      \     |      |       /
       logs -> Loki   traces -> Tempo
              \         /
              Grafana correlation
                     |
           CI -> staging -> approval
```

## Repository design

```text
observability-as-code/
  otel/collector.yaml
  loki/values-staging.yaml
  tempo/values-staging.yaml
  policies/telemetry-security.yaml
  environments/staging/kustomization.yaml
  environments/production/kustomization.yaml
  tests/pipeline_gate.py
  tests/test_pipeline_gate.py
```

Treat telemetry routing as application-critical infrastructure. Pin images and chart versions; require CODEOWNERS review; keep credentials in external secret references. Separate staging endpoints and tenants from production.

## Collector configuration example

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
    spike_limit_mib: 128
  resource:
    attributes:
      - key: deployment.environment.name
        value: staging
        action: upsert
  batch:
    timeout: 5s
    send_batch_size: 1024
exporters:
  otlp/tempo:
    endpoint: tempo-distributor.monitoring.svc:4317
    tls:
      insecure: true
  otlphttp/loki:
    endpoint: http://loki-gateway.monitoring.svc/otlp
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [otlp/tempo]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [otlphttp/loki]
```

**Staging-only illustration:** insecure gRPC and HTTP endpoints require secured transport or a documented trusted-mesh boundary before production. Verify actual collector component support and backend OTLP paths for the pinned versions. The sample intentionally omits credentials and needs a separate redaction processor/policy before handling sensitive telemetry.

## Signal design and correlation

Logs should include stable service/environment attributes and trace IDs without unbounded user IDs or database query text as Loki labels. Tempo traces need propagation through HTTP/gRPC and asynchronous Kafka boundaries; sampling policy must preserve incident investigation value. Use Grafana links and exemplars to pivot from an SLO panel to representative traces and logs. Missing spans or logs may indicate telemetry failure, not application health.

## Reliability and cost controls

Memory limiter, batch size, exporter retries and bounded queues protect the collector but may drop data under sustained saturation. Monitor collector accepted/refused/dropped spans and logs, exporter failures, queue utilization and process memory. Budget Loki ingestion and retention separately from Tempo span storage; evaluate tenant isolation and PII policy before changing retention.

## GitOps validation workflow

```bash
otelcol validate --config=otel/collector.yaml
git diff --check
# Run only against a reviewed staging Kubernetes context:
kubectl --context staging -n monitoring get pods
```

The collector executable name and validate flag depend on distribution/version; use the pinned image CLI and check supported flags. In CI, run schema/config checks, policy tests, secret scanning and pinned-image checks. After staging reconciliation, emit a known test span and log with matching trace ID; confirm both reach the correct tenant and survive query. Revert a reviewed commit and repeat the smoke test.

## DBRE operational examples

PostgreSQL waits and connection-pool traces, Redis command latency, Kafka consumer processing spans, Elasticsearch search latency and Snowflake task freshness need controlled attributes. Redact SQL literals, patient data, credentials and customer identifiers; never use per-request IDs as metric or Loki index labels.

## Executable offline synthetic gate

Save these three files locally.

### healthy.json

```json
{
  "owner": "telemetry-platform",
  "environment": "staging",
  "change_id": "OBS-083",
  "reviewed": true,
  "redaction_verified": true,
  "staging_pipeline_tested": true,
  "destructive_action": false,
  "controls": {
    "topology": true,
    "otlp_receivers": true,
    "memory_limiter": true,
    "batch": true,
    "resource_attributes": true,
    "redaction": true,
    "sampling": true,
    "retry_queue": true,
    "loki": true,
    "tempo": true,
    "retention": true,
    "correlation": true,
    "tls": true,
    "identity": true,
    "cardinality": true,
    "ci": true,
    "staging": true,
    "rollback": true
  }
}
```

### pipeline_gate.py

```python
"""Synthetic pipeline readiness evidence gate; no network calls."""
import json,sys
from pathlib import Path
CONTROLS=["topology","otlp_receivers","memory_limiter","batch","resource_attributes","redaction","sampling","retry_queue","loki","tempo","retention","correlation","tls","identity","cardinality","ci","staging","rollback"]
def validate(p):
 if not isinstance(p,dict):return ["expected object"]
 errors=[]
 for key in ("owner","change_id"):
  if not isinstance(p.get(key),str) or not p[key].strip():errors.append("missing "+key)
 if p.get("environment") not in ("lab","staging"):errors.append("unsafe environment")
 for key in ("reviewed","redaction_verified","staging_pipeline_tested"):
  if p.get(key) is not True:errors.append("missing "+key)
 controls=p.get("controls")
 if not isinstance(controls,dict):errors.append("invalid controls");controls={}
 for key in CONTROLS:
  if controls.get(key) is not True:errors.append("unverified "+key)
 if p.get("destructive_action") is not False:errors.append("unsafe action")
 return errors
if __name__=="__main__":
 try:p=json.loads(Path(sys.argv[1]).read_text());errors=validate(p)
 except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
 print(json.dumps({"status":"PASS" if not errors else "FAIL","findings":errors},indent=2))
 sys.exit(bool(errors))

```

### test_pipeline_gate.py

```python
import copy,json,unittest
from pathlib import Path
from pipeline_gate import validate
class PipelineTests(unittest.TestCase):
 def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
 def test_healthy(self):self.assertEqual(validate(self.p),[])
 def test_nonobject(self):self.assertTrue(validate(None))
 def test_negative_01(self):
  p=copy.deepcopy(self.p)
  p["controls"]["topology"]=False
  self.assertTrue(validate(p))
 def test_negative_02(self):
  p=copy.deepcopy(self.p)
  p["controls"]["otlp_receivers"]=False
  self.assertTrue(validate(p))
 def test_negative_03(self):
  p=copy.deepcopy(self.p)
  p["controls"]["memory_limiter"]=False
  self.assertTrue(validate(p))
 def test_negative_04(self):
  p=copy.deepcopy(self.p)
  p["controls"]["batch"]=False
  self.assertTrue(validate(p))
 def test_negative_05(self):
  p=copy.deepcopy(self.p)
  p["controls"]["resource_attributes"]=False
  self.assertTrue(validate(p))
 def test_negative_06(self):
  p=copy.deepcopy(self.p)
  p["controls"]["redaction"]=False
  self.assertTrue(validate(p))
 def test_negative_07(self):
  p=copy.deepcopy(self.p)
  p["controls"]["sampling"]=False
  self.assertTrue(validate(p))
 def test_negative_08(self):
  p=copy.deepcopy(self.p)
  p["controls"]["retry_queue"]=False
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
  p["controls"]["retention"]=False
  self.assertTrue(validate(p))
 def test_negative_12(self):
  p=copy.deepcopy(self.p)
  p["controls"]["correlation"]=False
  self.assertTrue(validate(p))
 def test_negative_13(self):
  p=copy.deepcopy(self.p)
  p["controls"]["tls"]=False
  self.assertTrue(validate(p))
 def test_negative_14(self):
  p=copy.deepcopy(self.p)
  p["controls"]["identity"]=False
  self.assertTrue(validate(p))
 def test_negative_15(self):
  p=copy.deepcopy(self.p)
  p["controls"]["cardinality"]=False
  self.assertTrue(validate(p))
 def test_negative_16(self):
  p=copy.deepcopy(self.p)
  p["controls"]["ci"]=False
  self.assertTrue(validate(p))
 def test_negative_17(self):
  p=copy.deepcopy(self.p)
  p["controls"]["staging"]=False
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
  p["reviewed"]=false
  self.assertTrue(validate(p))
 def test_negative_23(self):
  p=copy.deepcopy(self.p)
  p["redaction_verified"]=false
  self.assertTrue(validate(p))
 def test_negative_24(self):
  p=copy.deepcopy(self.p)
  p["staging_pipeline_tested"]=false
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
python3 pipeline_gate.py healthy.json
python3 -m unittest -v test_pipeline_gate.py
```

Expected PASS and **28 authored tests**. The gate validates synthetic attestations; actual telemetry delivery and execution remain unverified.

## 24 hands-on exercises

1. Define telemetry contract.
2. Draw collector topology.
3. Select OTLP receivers.
4. Configure memory limiter.
5. Configure batch processor.
6. Configure resource attributes.
7. Configure PII redaction.
8. Configure log filtering.
9. Set trace sampling policy.
10. Configure retry queue.
11. Configure Loki exporter.
12. Configure Tempo exporter.
13. Provision Loki retention.
14. Provision Tempo retention.
15. Validate trace correlation.
16. Inspect exemplars.
17. Pin collector image.
18. Run config validation.
19. Check collector metrics.
20. Test backpressure.
21. Inject exporter failure.
22. Reconcile staging overlay.
23. Verify rollback.
24. Review cost and SLO.

## 24 production failure scenarios

1. **Collector crash loop:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
2. **Exporter timeout:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
3. **Loki 429 throttling:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
4. **Tempo 503 error:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
5. **Trace sampling gap:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
6. **Missing trace ID:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
7. **Broken resource attributes:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
8. **PII in logs:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
9. **Unbounded log volume:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
10. **Cardinality explosion:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
11. **Memory limiter drops:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
12. **Queue saturation:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
13. **Disk buffer exhaustion:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
14. **Invalid TLS trust:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
15. **Expired certificate:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
16. **OTLP port mismatch:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
17. **Kubernetes selector mismatch:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
18. **Misconfigured retention:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
19. **Duplicate logs:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
20. **Trace context loss:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
21. **Multi-tenant routing error:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
22. **Bad GitOps overlay:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
23. **Rollback drift:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.
24. **Telemetry falsely healthy:** identify user impact, collector/backend evidence, hypothesis, safe remediation and verification.

## Eight production runbooks

1. **Collector deployment: validate receiver/processor/exporter graph and config version.**
2. **Loki incident: verify ingestion, tenant isolation, labels, retention and queryability.**
3. **Tempo incident: validate OTLP spans, trace ID propagation, sampling and storage.**
4. **Backpressure: inspect queue, retries, memory limiter, drop counters and upstream rate.**
5. **Security: sanitize secrets and sensitive attributes, validate TLS and workload identity.**
6. **Cost: bound label cardinality, logs volume, span sampling and retention.**
7. **GitOps promotion: lint, peer review, stage and verify end-to-end test traces.**
8. **Rollback: revert immutable commit and confirm independent telemetry recovery.**

## 100-point assessment

| Domain | Points |
|---|---:|
| Collector architecture and pipeline config | 20 |
| Loki/Tempo ingestion and correlation | 20 |
| Security, privacy and cost | 20 |
| Offline tests and staging verification | 20 |
| GitOps release, drift and rollback | 20 |
| **Total** | **100** |

Recommended pass: 85/100. Production acceptance requires real staging smoke tests, redaction verification, telemetry loss checks, owner approval and rollback evidence.

**Companion:** [Chapter 083 lab](labs/083-opentelemetry-loki-tempo-pipelines-as-code-lab.md).

**Next:** Chapter 084 — Observability CI/CD, Policy Validation, Drift Detection and Safe Promotion.
