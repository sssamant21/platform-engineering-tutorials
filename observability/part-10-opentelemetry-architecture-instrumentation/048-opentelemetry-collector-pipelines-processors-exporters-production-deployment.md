# Chapter 048 — OpenTelemetry Collector Pipelines, Processors, Exporters and Production Deployment

**Part 10 — OpenTelemetry Architecture and Instrumentation**  
**Audience:** SRE, DBRE, Kubernetes and observability platform engineers.  
**Prerequisites:** Chapters 046–047; Python 3.10+; Kubernetes fundamentals.

## 1. Outcomes

Build version-pinned Collector agent/gateway topologies; configure receivers, processors, exporters and extensions; manage batching, memory, queues, retries and security; perform safe staged deployments; troubleshoot pipeline degradation.

## 2. Reference architecture and tradeoffs

```text
Applications / Kubernetes / databases
         OTLP HTTP or gRPC
                  |
       node agent / sidecar
                  |
       gateway Collector pool
   receiver -> processor -> exporter
   memory limiter -> batch -> OTLP
                  |
  traces / metrics / logs backends
                  |
  independent SLOs + Collector self-metrics
```

Agent mode minimizes local hops; gateway mode centralizes credentials, policy and fan-out. Use both only when justified by capacity, fault isolation and tenant boundaries. The Collector is **not** durable storage; persistent sending queues reduce transient loss but do not guarantee exactly-once delivery.

## 3. Local three-signal Collector example

Use a **version-pinned Collector distribution** that includes `otlp`, `memory_limiter`, `batch`, `debug` and `health_check`. Save as `collector.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 127.0.0.1:4317
      http:
        endpoint: 127.0.0.1:4318
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 384
    spike_limit_mib: 64
  batch:
    timeout: 5s
    send_batch_size: 512
exporters:
  debug:
    verbosity: basic
extensions:
  health_check:
    endpoint: 127.0.0.1:13133
service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
```

Run locally with your pinned `otelcol-contrib` binary and inspect the health endpoint. Container-to-container traffic needs appropriate listener/service binding, TLS/auth and network policy; loopback is intentional here.

## 4. Production design

- **Receivers:** OTLP, Prometheus scrape, filelog or hostmetrics only when supported and justified; minimize exposure.
- **Processors:** put `memory_limiter` early, then filtering/transforming as appropriate, and batch later. Validate component ordering and failure semantics.
- **Exporters:** use authenticated OTLP to a gateway/backend; validate signal support and metric temporality.
- **Queues:** size bounded sending queues, retry windows and persistent storage based on failure duration and disk capacity.
- **Kubernetes:** pin image digest; set requests/limits, PodDisruptionBudget, readiness and controlled rolling updates; keep credentials in approved secret mechanisms.
- **Security:** TLS/mTLS, authentication, least privilege, NetworkPolicy, tenant isolation and sensitive-attribute filtering.
- **Observability:** track accepted/refused records, exporter send failures, queue utilization, memory, CPU and dropped telemetry.

## 5. Example staging-only Kubernetes deployment sketch

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-gateway-lab
  namespace: observability
spec:
  replicas: 2
  selector:
    matchLabels: {app: otel-gateway-lab}
  template:
    metadata:
      labels: {app: otel-gateway-lab}
    spec:
      containers:
        - name: collector
          image: otel/opentelemetry-collector-contrib:REPLACE_WITH_PINNED_VERSION
          args: ["--config=/etc/otelcol/collector.yaml"]
          resources:
            requests: {cpu: 100m, memory: 256Mi}
            limits: {cpu: "1", memory: 512Mi}
          volumeMounts:
            - {name: config, mountPath: /etc/otelcol, readOnly: true}
      volumes:
        - name: config
          configMap: {name: otel-gateway-lab-config}
```

This is a **deployment sketch**, not a complete production installation: supply reviewed ConfigMap, Service, probes, NetworkPolicy, authentication, TLS and version-compatible image before any rollout.

## 6. Executable offline change-control gate

The following synthetic metadata checks declared controls; it does **not** parse Collector YAML or test live export.

### healthy.json

```json
{
  "owner": "observability-sre",
  "environment": "staging",
  "collector_distribution": "otelcol-contrib",
  "collector_version": "pinned-in-deployment",
  "receivers": [
    "otlp"
  ],
  "processors": [
    "memory_limiter",
    "batch"
  ],
  "exporters": [
    "debug"
  ],
  "pipelines": [
    "traces",
    "metrics",
    "logs"
  ],
  "health_check_enabled": true,
  "memory_limit_mib": 512,
  "memory_limiter_mib": 384,
  "memory_spike_mib": 64,
  "batch_size": 512,
  "queue_capacity": 2048,
  "estimated_peak_batch": 1000,
  "tls_reviewed": true,
  "authentication_reviewed": true,
  "redaction_reviewed": true,
  "network_policy_reviewed": true,
  "resource_limits_reviewed": true,
  "retry_reviewed": true,
  "rollback_tested": true,
  "load_tested": true,
  "production_exposure": false
}
```

### collector_gate.py

```python
"""Synthetic OTel Collector change gate; no Kubernetes or Collector calls."""
import json,sys
from pathlib import Path
def validate(p):
    errors=[]
    if not isinstance(p,dict):return ["manifest must be an object"]
    for k in ("owner","environment","collector_distribution","collector_version"):
        if not isinstance(p.get(k),str) or not p[k]:errors.append("missing "+k)
    for k,required in (("receivers",{"otlp"}),("processors",{"memory_limiter","batch"}),("exporters",{"debug"}),("pipelines",{"traces","metrics","logs"})):
        v=p.get(k)
        if not isinstance(v,list) or not required.issubset(v):errors.append("missing "+k)
    for k in ["health_check_enabled","tls_reviewed","authentication_reviewed","redaction_reviewed","network_policy_reviewed","resource_limits_reviewed","retry_reviewed","rollback_tested","load_tested"]:
        if p.get(k) is not True:errors.append("unverified "+k)
    if p.get("production_exposure") is not False:errors.append("unsafe exposure")
    for k in ("memory_limit_mib","memory_limiter_mib","memory_spike_mib","batch_size","queue_capacity","estimated_peak_batch"):
        if type(p.get(k)) is not int or p[k]<=0:errors.append("invalid "+k)
    if all(type(p.get(k)) is int for k in ("memory_limit_mib","memory_limiter_mib","memory_spike_mib")):
        if not 0<p["memory_spike_mib"]<p["memory_limiter_mib"]<p["memory_limit_mib"]:errors.append("memory budget mismatch")
    if all(type(p.get(k)) is int for k in ("batch_size","queue_capacity","estimated_peak_batch")):
        if p["batch_size"]>p["queue_capacity"] or p["estimated_peak_batch"]>p["queue_capacity"]:errors.append("queue capacity exceeded")
    return errors
if __name__=="__main__":
    try: result=validate(json.loads(Path(sys.argv[1]).read_text()))
    except (IndexError,OSError,ValueError) as exc:sys.exit(str(exc))
    print(json.dumps({"status":"PASS" if not result else "FAIL","findings":result},indent=2))
    sys.exit(bool(result))

```

### test_collector_gate.py

```python
import copy,json,unittest
from pathlib import Path
from collector_gate import validate
class CollectorGateTests(unittest.TestCase):
    def setUp(self):self.p=json.loads(Path(__file__).with_name("healthy.json").read_text())
    def test_healthy(self):self.assertEqual(validate(self.p),[])
    def test_invalid_object(self):self.assertTrue(validate(None))
    def test_01_owner(self):
        p=copy.deepcopy(self.p);p["owner"]="";self.assertTrue(validate(p))
    def test_02_environment(self):
        p=copy.deepcopy(self.p);p["environment"]="";self.assertTrue(validate(p))
    def test_03_collector_distribution(self):
        p=copy.deepcopy(self.p);p["collector_distribution"]="";self.assertTrue(validate(p))
    def test_04_collector_version(self):
        p=copy.deepcopy(self.p);p["collector_version"]="";self.assertTrue(validate(p))
    def test_05_receivers(self):
        p=copy.deepcopy(self.p);p["receivers"]=[];self.assertTrue(validate(p))
    def test_06_processors(self):
        p=copy.deepcopy(self.p);p["processors"]=["batch"];self.assertTrue(validate(p))
    def test_07_processors(self):
        p=copy.deepcopy(self.p);p["processors"]=["memory_limiter"];self.assertTrue(validate(p))
    def test_08_exporters(self):
        p=copy.deepcopy(self.p);p["exporters"]=[];self.assertTrue(validate(p))
    def test_09_pipelines(self):
        p=copy.deepcopy(self.p);p["pipelines"]=["traces"];self.assertTrue(validate(p))
    def test_10_health_check_enabled(self):
        p=copy.deepcopy(self.p);p["health_check_enabled"]=False;self.assertTrue(validate(p))
    def test_11_tls_reviewed(self):
        p=copy.deepcopy(self.p);p["tls_reviewed"]=False;self.assertTrue(validate(p))
    def test_12_authentication_reviewed(self):
        p=copy.deepcopy(self.p);p["authentication_reviewed"]=False;self.assertTrue(validate(p))
    def test_13_redaction_reviewed(self):
        p=copy.deepcopy(self.p);p["redaction_reviewed"]=False;self.assertTrue(validate(p))
    def test_14_network_policy_reviewed(self):
        p=copy.deepcopy(self.p);p["network_policy_reviewed"]=False;self.assertTrue(validate(p))
    def test_15_resource_limits_reviewed(self):
        p=copy.deepcopy(self.p);p["resource_limits_reviewed"]=False;self.assertTrue(validate(p))
    def test_16_retry_reviewed(self):
        p=copy.deepcopy(self.p);p["retry_reviewed"]=False;self.assertTrue(validate(p))
    def test_17_rollback_tested(self):
        p=copy.deepcopy(self.p);p["rollback_tested"]=False;self.assertTrue(validate(p))
    def test_18_load_tested(self):
        p=copy.deepcopy(self.p);p["load_tested"]=False;self.assertTrue(validate(p))
    def test_19_production_exposure(self):
        p=copy.deepcopy(self.p);p["production_exposure"]=True;self.assertTrue(validate(p))
    def test_20_memory_limit_mib(self):
        p=copy.deepcopy(self.p);p["memory_limit_mib"]=0;self.assertTrue(validate(p))
    def test_21_memory_limiter_mib(self):
        p=copy.deepcopy(self.p);p["memory_limiter_mib"]=600;self.assertTrue(validate(p))
    def test_22_memory_spike_mib(self):
        p=copy.deepcopy(self.p);p["memory_spike_mib"]=500;self.assertTrue(validate(p))
    def test_23_batch_size(self):
        p=copy.deepcopy(self.p);p["batch_size"]=0;self.assertTrue(validate(p))
    def test_24_queue_capacity(self):
        p=copy.deepcopy(self.p);p["queue_capacity"]=0;self.assertTrue(validate(p))
    def test_25_estimated_peak_batch(self):
        p=copy.deepcopy(self.p);p["estimated_peak_batch"]=5000;self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()

```

```bash
mkdir -p chapter048 && cd chapter048
# Save the blocks as healthy.json, collector_gate.py, test_collector_gate.py
python3 collector_gate.py healthy.json
python3 -m unittest -v test_collector_gate.py
```

Expected PASS and **27 authored Python tests**.

## 7. Twenty-four exercises

1. Inventory telemetry producers.
2. Select agent versus gateway.
3. Pin Collector distribution.
4. Define OTLP receiver.
5. Bind safe local endpoints.
6. Configure memory limiter.
7. Configure batch processor.
8. Configure debug exporter.
9. Route traces pipeline.
10. Route metrics pipeline.
11. Route logs pipeline.
12. Validate YAML syntax.
13. Validate component availability.
14. Configure health check.
15. Set resource requests/limits.
16. Review TLS and auth.
17. Review NetworkPolicy.
18. Plan bounded retry.
19. Plan persistent queue.
20. Measure accepted/refused signals.
21. Simulate exporter outage.
22. Load-test memory pressure.
23. Run governance tests.
24. Practice rollback.

## 8. Twenty-four failure scenarios

1. **OTLP port blocked:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
2. **gRPC/HTTP mismatch:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
3. **Receiver unauthenticated:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
4. **Collector config invalid:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
5. **Missing contrib component:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
6. **Memory limiter rejects:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
7. **Batch queue saturation:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
8. **Exporter timeout:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
9. **Exporter 429:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
10. **TLS handshake failure:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
11. **Expired credentials:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
12. **DNS resolution failure:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
13. **NetworkPolicy denies traffic:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
14. **OOMKilled pod:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
15. **CPU throttling:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
16. **Persistent queue full:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
17. **Storage extension misconfigured:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
18. **Dropped traces:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
19. **Metric temporality mismatch:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
20. **Logs lost during restart:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
21. **High-cardinality attributes:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
22. **Collector health check fails:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
23. **Rollout causes telemetry gap:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.
24. **Rollback fails:** investigate receiver, processor, exporter, Kubernetes, queue and security evidence.

## 9. Eight production runbooks

1. **No signals:** inspect SDK endpoints, receiver listeners, pipeline wiring and exporter counters..
2. **Memory pressure:** inspect limiter, queues, pod limits and accepted/refused telemetry; reduce load safely..
3. **Exporter failures:** inspect per-exporter error metrics, TLS, auth, DNS and retry backoff..
4. **Collector rollout:** stage config, canary, validate all three signals, then gradually promote..
5. **Data loss:** compare source telemetry, queue usage, refused counters and backend persistence..
6. **Security:** restrict ingress, require authenticated TLS and redact sensitive attributes..
7. **Storage queue:** inspect capacity, disk saturation, corruption and safe recovery without blind replay..
8. **Rollback:** restore previous image/config and confirm service SLOs and pipeline continuity..

## 10. Production SRE/DBRE incident game day

During a PostgreSQL-backed API latency incident, OTel exporters return 429 while Collector memory reaches its limit. Inspect accepted/refused records, queue depth, retry errors, application SLOs and downstream storage. Test a bounded staging load, adjust safe capacity, restore telemetry with a canary and roll back if export latency worsens.

## 11. 100-point assessment

| Domain | Points |
|---|---:|
| Collector architecture and pipeline design | 20 |
| Reliability, memory and queues | 20 |
| Kubernetes deployment and security | 20 |
| Offline tests and governance | 20 |
| Incident response and rollback | 20 |
| **Total** | **100** |

Recommended pass 85/100. Production acceptance requires witnessed end-to-end telemetry delivery, auth/TLS tests, rollout and rollback evidence.

**Companion:** [Chapter 048 hands-on lab](labs/048-opentelemetry-collector-pipelines-processors-exporters-production-deployment-lab.md).

**Next:** Chapter 049 — OpenTelemetry Collector Reliability, Scaling, Tail Sampling and Advanced Processing.
