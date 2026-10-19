# Chapter 097 — Enterprise Observability Production Deployment, Integration and End-to-End Validation Lab

**Part 20 — Final Production Observability Capstones**

## Scope and safety

Use a disposable lab or approved staging cluster. Never run destructive experiments or change production IAM, DNS, alert routes, data retention or storage. All synthetic tests use training-only telemetry.

## Lab 1 — Staging deployment preflight

```bash
kubectl config current-context
kubectl version --client
helm version
kubectl get nodes
kubectl get storageclass
```

Confirm context and approval before any apply. Pin exact images and Helm chart versions, validate CRDs, Pod Security Admission, network policies, TLS, workload identity and persistent storage.

## Lab 2 — Build a telemetry integration matrix

For synthetic app, PostgreSQL, MongoDB, Kafka and Kubernetes signals, document receiver, processor, exporter, backend, dashboard, alert, owner and security classification. Confirm no secrets or sensitive IDs are used as metric labels.

## Lab 3 — Deploy in isolated staging

Use reviewed manifests and Helm values from [Chapter 097](../097-enterprise-observability-production-deployment-integration-end-to-end-validation.md) and pinned upstream charts. Deploy Collector, Prometheus, Grafana, Loki, Tempo and Alertmanager using the approved environment-specific modules. Validate endpoints, TLS, storage, readiness and logs. The chapter's Collector YAML is a reference template, not a ready-to-apply Kubernetes resource.

## Lab 4 — End-to-end signal validation

1. Generate one synthetic HTTP request and retain its trace ID.
2. Query Tempo for the trace and Loki for correlated logs.
3. Query Prometheus for a synthetic metric and check labels.
4. Open Grafana panels and inspect data source health.
5. Fire a staging-only synthetic alert and verify test receiver.
6. Restart a disposable Collector and record gaps/dropped signals.
7. Attempt denied cross-tenant query through all relevant APIs.
8. Inject a synthetic canary and confirm redaction in stored outputs.
9. Restore a staging backup in an isolated namespace.
10. Perform a GitOps rollback rehearsal.
11. Verify DBRE exporter metrics with scoped read-only access.
12. Capture baseline ingestion/query latency and queue metrics.

## Lab 5 — Offline acceptance gate

Copy `integration_gate.py`, `make_fixture.py`, and `test_integration_gate.py` from the main chapter.

```bash
python3 make_fixture.py
python3 integration_gate.py synthetic-integration.json
python3 -m unittest -v test_integration_gate.py
```

Expected: synthetic GO with 12/12 and 12 authored unittest methods passing. This validates only the local evaluator.

## Lab 6 — Negative tests

Modify one synthetic fixture field at a time: environment=production; approved=false; destructive=true; reviewer=owner; missing git_sha; fail E2E-05; fail E2E-07; missing E2E-08 evidence; fail E2E-09; fail E2E-10. Each must produce NO-GO and a nonzero exit code.

## Lab 7 — Evidence and operational handoff

Capture Git commit, image digests, chart versions, manifest checksums, backend query results, alert receiver proof, timestamps, tenant negative-test logs, canary checks, backup hashes, restore measurements, rollback logs, reviewer approval and incident escalation contacts.

## Troubleshooting exercise

Diagnose one missing trace, one failed scrape target, one broken log exporter, one undelivered staging alert, one excessive queue and one denied/incorrect tenant query. Record symptom, hypothesis, commands, root cause, mitigation, verification and preventive action.

## Exit criteria

All E2E-01–12 checks must be supported by real staging evidence and reviewed independently for actual acceptance. Offline synthetic GO is not operational validation or compliance certification.
