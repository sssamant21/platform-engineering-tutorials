# Chapter 097 — Enterprise Observability Production Deployment, Integration and End-to-End Validation

**Part 20 — Final Production Observability Capstones (2/5)**

## Mission

Translate Chapter 096's reviewed architecture into a **reproducible staging deployment** and a verifiable end-to-end telemetry path. Production promotion is a separate change-controlled activity; this chapter does not claim live deployment.

### Outcomes

- Pin and deploy a compatible OpenTelemetry Collector, Prometheus, Grafana, Loki, Tempo and Alertmanager stack using approved charts/manifests.
- Instrument Kubernetes and database workloads without leaking secrets or crossing tenant boundaries.
- Validate metrics, logs, traces, dashboards, alert delivery, identity, resilience and recovery.
- Automate acceptance with negative tests, evidence records, CI and rollback criteria.
- Distinguish software smoke tests from live operational readiness evidence.

## Deployment topology

```text
synthetic app --OTLP--> OTel Collector gateway
      |                       |         |
  /metrics                metrics      traces
      |                       |         |
 Prometheus <--- scrape exporter       Tempo
      |                       |
  recording rules       logs pipeline -> Loki
      |                                  |
 Alertmanager <---- Prometheus rules     |
      |                                  |
  test receiver            Grafana dashboards
      |                       |
 audit / evidence     SSO + scoped data sources
      |
 GitOps + policy gates + isolated DR backups
```

Use an ingress and identity architecture that does not trust tenant headers supplied directly by untrusted clients. Validate supported Collector component names, Helm chart values, service ports, and backend ingestion protocols against the pinned versions. OpenTelemetry Collector distributions differ: a component in the contrib distribution may not exist in the core distribution.

## Repository layout

```text
observability-capstone/
  environments/
    staging/
      kustomization.yaml
      namespace.yaml
      collector-config.yaml
      synthetic-app.yaml
      networkpolicy.yaml
      values/
        prometheus.yaml
        loki.yaml
        tempo.yaml
        grafana.yaml
  policies/
    required-labels.rego
    deny-unapproved-exporters.rego
  tests/
    smoke.sh
    acceptance_gate.py
    test_acceptance_gate.py
  runbooks/
    ingestion-outage.md
    failed-deployment.md
    rollback.md
  evidence/
    README.md
```

The layout is illustrative. Use a vetted upstream Helm chart or internal module for each backend rather than assuming the simplified YAML in this chapter constitutes a full backend deployment.

## Preflight and dependency controls

Run in a **staging** Kubernetes context only:

```bash
kubectl config current-context
kubectl version --client
helm version
kubectl get nodes -o wide
kubectl get storageclass
kubectl get namespaces
```

Require explicit review of cluster identity, namespace, Kubernetes version, ingress, storage class, encryption/KMS, network policies, DNS, image registry, service accounts, secret delivery, pod security, resource quotas and backup targets. Never store tokens in values files or committed ConfigMaps.

## Stage 1 — Namespace and baseline policy

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: obs-capstone-staging
  labels:
    app.kubernetes.io/part-of: observability-capstone
    environment: staging
    pod-security.kubernetes.io/enforce: restricted
```

Use Pod Security Admission only after confirming that all required components support the selected policy level; security exceptions require explicit review.

```bash
kubectl apply --dry-run=server -f namespace.yaml
kubectl apply -f namespace.yaml
kubectl get namespace obs-capstone-staging --show-labels
```

### Collector reference configuration

The following is a **learning template**, not a deployable manifest until environment-specific exporters, certificates, credentials and services are configured. It assumes a Collector distribution supporting `file_storage` if persistent queues are enabled; this example deliberately avoids disk queues.

```yaml
# collector-config.yaml (Collector config, not a Kubernetes object)
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
  batch:
    timeout: 5s
    send_batch_size: 1024
exporters:
  otlphttp/traces:
    endpoint: http://tempo-distributor.obs-capstone-staging.svc.cluster.local:4318
  otlphttp/logs:
    endpoint: http://loki-gateway.obs-capstone-staging.svc.cluster.local/otlp
  debug:
    verbosity: basic
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp/traces]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp/logs]
```

**Compatibility warning:** Loki's native OTLP log ingestion requires a compatible Loki release and configuration; `/otlp` routing depends on gateway configuration. Tempo OTLP endpoint and service names vary by chart. This reference config intentionally does not export metrics; use Prometheus scraping or an explicitly reviewed metrics export pipeline. Before deployment, validate Collector configuration with the exact pinned image and verify each backend endpoint.

### Prometheus and alerting

Use approved Prometheus Operator/Helm deployments with explicit requests/limits, retention, persistent storage, TLS and rule review. A representative staging rule:

```yaml
groups:
- name: obs-capstone
  rules:
  - alert: SyntheticTargetDown
    expr: up{job="capstone-synthetic"} == 0
    for: 2m
    labels:
      severity: warning
      environment: staging
    annotations:
      summary: "Synthetic capstone target unavailable"
```

Route to a **test receiver** only. Do not assume `up` exists until the corresponding scrape job is configured and verified.

## Stage 2 — Signal producers

Instrument a disposable app with OTel SDK for HTTP request traces, log correlation and a `/metrics` endpoint. Record a unique synthetic request ID. Include a PostgreSQL/MongoDB/Kafka metrics exporter or collector receiver only where credentials and metrics exposure are approved.

Recommended DBRE signals:

| Platform | Metrics / signals | Operational question |
|---|---|---|
| PostgreSQL | connection saturation, WAL rate, replication lag, locks | Is latency driven by database pressure? |
| MongoDB | WiredTiger cache, replication lag, disk, connections | Is storage/cache pressure affecting requests? |
| Kafka | consumer lag, broker request latency, under-replicated partitions | Is backlog growing or durability degraded? |
| Elasticsearch/OpenSearch | search latency, rejections, JVM heap, shard health | Are queries blocked by CPU, heap or storage? |
| Kubernetes | restarts, throttling, memory pressure, network errors | Is platform capacity constraining telemetry? |

Avoid high-cardinality labels containing patient IDs, user emails, tokens, request bodies or other sensitive values.

## Stage 3 — End-to-end validation matrix

| ID | Test | Evidence | Pass criterion |
|---|---|---|---|
| E2E-01 | synthetic HTTP request | trace ID and service name | trace searchable in Tempo |
| E2E-02 | correlated synthetic log | trace ID and log query | log searchable in Loki |
| E2E-03 | synthetic request metric | PromQL query result | series and labels visible |
| E2E-04 | Grafana dashboards | data source health and screenshot | all approved panels query |
| E2E-05 | staging alert | Alertmanager receiver log | test notification delivered |
| E2E-06 | collector restart | exporter queue/drop counters | recovery and gap documented |
| E2E-07 | tenant negative query | denied request and audit event | no cross-tenant data |
| E2E-08 | synthetic redaction canary | backend queries | canary absent from stored output |
| E2E-09 | backup and restore | hashes and isolated queries | clean restore validated |
| E2E-10 | GitOps rollback | pinned revision and probe results | previous known-good state restored |
| E2E-11 | DBRE integration | approved exporter series | metrics accurate and access scoped |
| E2E-12 | performance baseline | p95 ingest/query and drops | within approved thresholds |

Do not mark a test passed merely because a pod is Ready. Query the actual backend, inspect results, and retain UTC timestamps.

## Offline acceptance evidence gate

This executable evaluator is deliberately limited to **staging/lab self-reported evidence**. It does not contact any real service and cannot prove deployment success.

Save `integration_gate.py`:

```python
"""Fail-closed offline evidence manifest validator for Chapter 097."""
import json
import sys
from pathlib import Path

TESTS = tuple(f"E2E-{n:02d}" for n in range(1, 13))
CRITICAL = frozenset(("E2E-05", "E2E-07", "E2E-08", "E2E-09", "E2E-10"))

def evaluate(doc):
    if not isinstance(doc, dict):
        return {"decision": "NO-GO", "passed": 0, "total": len(TESTS),
                "findings": ["manifest must be an object"]}
    findings = []
    for field in ("deployment_id", "git_sha", "owner", "reviewer", "change_id"):
        if not isinstance(doc.get(field), str) or not doc[field].strip():
            findings.append("missing " + field)
    if doc.get("owner") == doc.get("reviewer"):
        findings.append("independent reviewer required")
    if doc.get("environment") not in ("staging", "lab"):
        findings.append("unsafe environment")
    if doc.get("approved") is not True:
        findings.append("approval missing")
    if doc.get("destructive") is not False:
        findings.append("destructive actions prohibited")
    results = doc.get("tests")
    if not isinstance(results, dict):
        results = {}
        findings.append("tests map missing")
    passed = 0
    for test_id in TESTS:
        item = results.get(test_id)
        if (isinstance(item, dict) and item.get("passed") is True
                and isinstance(item.get("evidence"), str)
                and item["evidence"].strip()):
            passed += 1
        else:
            findings.append("failed or unsupported " + test_id)
            if test_id in CRITICAL:
                findings.append("critical blocker: " + test_id)
    return {"decision": "GO" if not findings else "NO-GO",
            "passed": passed, "total": len(TESTS), "findings": findings}

if __name__ == "__main__":
    try:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        result = evaluate(data)
    except (IndexError, OSError, ValueError) as exc:
        sys.exit(str(exc))
    print(json.dumps(result, indent=2))
    sys.exit(result["decision"] != "GO")
```

Save `make_fixture.py`:

```python
import json
from pathlib import Path
from integration_gate import TESTS
doc = {
    "deployment_id": "OBS-097-SYNTHETIC",
    "git_sha": "synthetic-not-a-real-commit",
    "owner": "sre", "reviewer": "security",
    "change_id": "CHG-097-TRAINING",
    "environment": "staging", "approved": True, "destructive": False,
    "tests": {test_id: {"passed": True, "evidence": "synthetic://" + test_id}
              for test_id in TESTS},
}
Path("synthetic-integration.json").write_text(json.dumps(doc, indent=2))
```

Save `test_integration_gate.py`:

```python
import unittest
from integration_gate import TESTS, CRITICAL, evaluate

def good():
    return {
        "deployment_id": "test", "git_sha": "synthetic",
        "owner": "sre", "reviewer": "security", "change_id": "CHG-097",
        "environment": "staging", "approved": True, "destructive": False,
        "tests": {name: {"passed": True, "evidence": "synthetic://" + name}
                  for name in TESTS},
    }

class IntegrationGateTests(unittest.TestCase):
    def test_healthy_fixture(self):
        self.assertEqual(evaluate(good())["decision"], "GO")
    def test_test_count(self):
        self.assertEqual(len(TESTS), 12)
    def test_not_object(self):
        self.assertEqual(evaluate([])["decision"], "NO-GO")
    def test_production_denied(self):
        self.assertEqual(evaluate(dict(good(), environment="production"))["decision"], "NO-GO")
    def test_unapproved_denied(self):
        self.assertEqual(evaluate(dict(good(), approved=False))["decision"], "NO-GO")
    def test_destructive_denied(self):
        self.assertEqual(evaluate(dict(good(), destructive=True))["decision"], "NO-GO")
    def test_independent_reviewer(self):
        self.assertEqual(evaluate(dict(good(), reviewer="sre"))["decision"], "NO-GO")
    def test_missing_git_sha(self):
        self.assertEqual(evaluate(dict(good(), git_sha=""))["decision"], "NO-GO")
    def test_missing_tests(self):
        self.assertEqual(evaluate(dict(good(), tests=None))["decision"], "NO-GO")
    def test_each_failed_test(self):
        for name in TESTS:
            with self.subTest(name=name):
                doc = good()
                doc["tests"][name]["passed"] = False
                self.assertEqual(evaluate(doc)["decision"], "NO-GO")
    def test_each_missing_evidence(self):
        for name in TESTS:
            with self.subTest(name=name):
                doc = good()
                doc["tests"][name]["evidence"] = ""
                self.assertEqual(evaluate(doc)["decision"], "NO-GO")
    def test_critical_failures(self):
        for name in CRITICAL:
            with self.subTest(name=name):
                doc = good()
                del doc["tests"][name]
                self.assertTrue(any("critical blocker" in f
                                    for f in evaluate(doc)["findings"]))

if __name__ == "__main__":
    unittest.main()
```

Run:

```bash
python3 make_fixture.py
python3 integration_gate.py synthetic-integration.json
python3 -m unittest -v test_integration_gate.py
```

A synthetic GO only validates manifest logic; it is **not** evidence that a live stack was deployed, queried or recovered.

## CI/CD promotion stages

1. Static checks: YAML schema, Helm lint, image digest pinning and secret scanning.
2. Policy checks: least privilege, approved exporters, data residency, network policies and resource limits.
3. Staging deploy: approved GitOps revision and version compatibility matrix.
4. Integration: E2E-01 through E2E-12 using synthetic data and real backend queries.
5. Resilience: staged restart, alert failure and restore rehearsal.
6. Independent security/SRE review: evidence hashes, exception register and GO/NO-GO.
7. Production promotion: separately authorized change with canary and rollback conditions.

## Troubleshooting matrix

| Symptom | Investigate | Recovery |
|---|---|---|
| No traces | OTel exporter errors, endpoint/protocol, sampling | fix routing and verify trace ID |
| No Loki logs | OTLP gateway, labels, auth, tenant identity | validate ingestion and query |
| Prometheus target down | ServiceMonitor selectors, port, TLS, RBAC | repair scrape path |
| Grafana blank panels | data source auth, query errors, time range | fix provisioning |
| Alert not delivered | silences, routes, receiver credentials | use test receiver and rollback |
| High collector memory | queues, batching, cardinality | tune budgets and load |
| Cross-tenant query | proxy identity, direct API bypass | block cutover and involve security |
| Rollback failure | CRD/schema mismatch, storage migration | restore compatible release and state |

## Production runbooks

### RB-097-01 — Failed staging rollout
Freeze promotion, capture Git revision, Helm/Kubernetes events and logs, compare expected manifests, roll back only to a compatible approved version, rerun E2E tests.

### RB-097-02 — Missing telemetry
Trace synthetic request across application, Collector receiver, processor, exporter, backend and query. Record dropped signals and queue saturation; never silently claim zero data loss.

### RB-097-03 — Alert routing outage
Activate independent paging, restore staging receiver configuration, test synthetic alert and reconcile missed incidents.

### RB-097-04 — Security control failure
Stop deployment, preserve audit evidence, isolate tenant/secret exposure, correct backend authorization and redaction, and obtain independent security approval.

### RB-097-05 — Recovery and rollback
Use versioned backup and pinned release, restore in isolated namespace, validate metrics/logs/traces and paging, measure RPO/RTO and document approval before traffic changes.

## Final acceptance

**GO** requires all 12 integration tests passed with traceable real staging evidence, zero critical blockers, approved version matrix, rollback rehearsal and independent review. A synthetic manifest GO cannot authorize production deployment.

**Next:** Chapter 098 — Enterprise Observability Production Failure Injection, Chaos Engineering and Disaster Recovery Validation.
