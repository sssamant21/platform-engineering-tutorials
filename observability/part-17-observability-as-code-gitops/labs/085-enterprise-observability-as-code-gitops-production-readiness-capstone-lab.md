# Chapter 085 — Enterprise Observability GitOps Production Readiness Lab

Follow [Chapter 085](../085-enterprise-observability-as-code-gitops-production-readiness-capstone.md) for complete executable Python examples, tests, 24 exercises, 24 incidents, eight runbooks and the 100-point assessment.

## Offline gate

Save `healthy.json`, `readiness_gate.py` and `test_readiness_gate.py` from the chapter.

```bash
python3 readiness_gate.py healthy.json
python3 -m unittest -v test_readiness_gate.py
```

Expected PASS and 35 authored tests; capture actual results.

## Staging acceptance

1. Verify Git ownership, protected branches and immutable artifacts.
2. Lint Prometheus, Alertmanager, Grafana and OpenTelemetry configurations.
3. Enforce secrets, RBAC, tenant, retention and cardinality policies.
4. Reconcile a reviewed artifact into isolated staging.
5. Confirm real staging page delivery, Grafana SLO panels and Loki/Tempo correlation.
6. Simulate bounded collector backpressure and capture loss/retry metrics.
7. Detect manual drift and review any incident-related exception.
8. Revert an approved change and independently verify recovery.
9. Capture owner approval, UTC timeline, artifacts and test evidence.
10. Score readiness across five 20-point domains.

## Evidence

Record change ID, owner, artifact digest, CI/policy checks, staging alert and trace IDs, drift classification, rollback result, score and sign-off. Synthetic gate success is not proof of production readiness.
