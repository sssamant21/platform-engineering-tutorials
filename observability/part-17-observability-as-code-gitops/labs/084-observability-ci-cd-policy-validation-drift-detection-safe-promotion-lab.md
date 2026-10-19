# Chapter 084 — Observability CI/CD and Drift Lab

Read [Chapter 084](../084-observability-ci-cd-policy-validation-drift-detection-safe-promotion.md) for the full theory, Python gate, test suite, 24 exercises, 24 scenarios, eight runbooks and assessment.

## Offline execution

Save the chapter's three examples as `healthy.json`, `cicd_gate.py` and `test_cicd_gate.py`.

```bash
python3 cicd_gate.py healthy.json
python3 -m unittest -v test_cicd_gate.py
```

Record actual results rather than assuming the expected PASS.

## Staging exercises

1. Configure CODEOWNERS, branch protection and pinned CI dependencies.
2. Lint YAML, Prometheus rules, Alertmanager routes and Grafana dashboards.
3. Reject secret exposure, overbroad RBAC, unbounded labels and unsafe retention.
4. Record artifact digest and owner approval.
5. Reconcile a reviewed immutable artifact to isolated staging.
6. Test staging-only alert delivery and trace/log ingestion.
7. Simulate manual staging drift and classify authorized emergency changes.
8. Revert a reviewed commit and independently verify monitoring recovery.

## Evidence

Record UTC, change ID, CI checks, policy denials, staging signal tests, drift classification, rollback and service-owner sign-off. Synthetic gate validation is not proof of production readiness.
