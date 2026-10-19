# Chapter 098 — Enterprise Observability Failure Injection, Chaos Engineering and Disaster Recovery Validation Lab

**Part 20 · Final Production Observability Capstones**

## Prerequisites and safety

Use Python 3.10+ and optionally a disposable, approved staging Kubernetes namespace. Never disrupt production, shared services, real paging receivers, KMS, DNS or persistent production storage. Require written approval, incident commander, abort procedure and rollback before real fault injection.

## Lab 1 — Build the experiment plan

For each CH-01–CH-12 in [Chapter 098](../098-enterprise-observability-production-failure-injection-chaos-engineering-disaster-recovery-validation.md), record hypothesis, fault scope, owner, duration, steady-state signals, blast-radius limit, abort conditions, backup status, rollback and evidence location. Choose **one** staging fault at a time.

## Lab 2 — Offline synthetic acceptance gate

Copy `chaos_gate.py`, `make_fixture.py` and `test_chaos_gate.py` from the main chapter.

```bash
python3 make_fixture.py
python3 chaos_gate.py synthetic-chaos.json
python3 -m unittest -v test_chaos_gate.py
```

Expected: synthetic GO with 12/12 scenarios and 15 authored unittest methods passing. This verifies only the local policy evaluator, not any real chaos experiment.

## Lab 3 — Negative policy drills

Edit the fixture one condition at a time, expect NO-GO and nonzero exit: environment=production, approved=false, destructive=true, reviewer=owner, abort_triggered=true, measured_rpo_minutes=16, measured_rto_minutes=61, measured_alert_latency_minutes=3, CH-07 failed, CH-10 failed, CH-11 missing evidence, CH-12 failed. Restore original fixture and rerun.

## Lab 4 — Optional Collector restart drill

After context and scope approval:

```bash
kubectl config current-context
kubectl -n obs-capstone-staging get deploy
kubectl -n obs-capstone-staging rollout restart deployment/otel-collector
kubectl -n obs-capstone-staging rollout status deployment/otel-collector --timeout=180s
```

Only run when `otel-collector` is confirmed to be a disposable staging Deployment. Measure signal ingestion before, during and after restart, queue/dropped metrics, test paging and rollback.

## Lab 5 — Storage and regional DR tabletop

Simulate object-store unavailability using a mock or isolated test endpoint. Validate clean backup checksum, KMS/key availability, restoration in an isolated namespace, synthetic queries and tenant negative tests. Tabletop a regional failure, measure assumed versus **actually observed** RPO/RTO separately, and document missing evidence.

## Lab 6 — Security and privacy recovery

After a simulated restore, test tenant A identity against tenant B metrics/logs/traces through direct APIs and dashboards. Emit a training-only secret canary and verify redaction. Confirm audit continuity and restricted recovery credentials.

## Lab 7 — Incident review and evidence

Collect UTC timeline, hypothesis, injected fault, commands, before/after metric queries, log/trace IDs, test paging receipt, backup hashes, measured RPO/RTO, security tests, rollback proof, approvals and action items.

## Troubleshooting practice

Investigate collector saturation, Prometheus query loss, Loki/Tempo missing objects, broken alert routing, cross-tenant access and KMS failure. For each, produce symptom → evidence → hypothesis → mitigation → verification → prevention.

## Completion criteria

All 12 scenario outcomes supported by actual staging evidence, safety controls satisfied, no critical security/DR blocker, independent review and documented rollback. Offline synthetic GO alone is insufficient for operational acceptance.
