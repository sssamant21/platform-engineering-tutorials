# Chapter 082 — Configuration as Code Companion Lab

Follow [Chapter 082](../082-prometheus-alertmanager-grafana-configuration-as-code.md) for the full Prometheus, Alertmanager and Grafana configuration examples, offline Python gate, and unit tests.

## Staging checklist

1. Author and lint Prometheus SLO recording and alert rules.
2. Validate paired burn windows and absent-data safeguards.
3. Configure a staging-only Alertmanager test receiver and verify delivery.
4. Provision Grafana datasource and dashboards with stable UIDs.
5. Run CI lint, policy checks, peer review and secrets scan.
6. Reconcile an approved staging commit, then rehearse a Git revert.
7. Capture actual command output, screenshots and owner sign-off.

## Evidence

Record UTC, owner, change ID, rule evaluation, alert delivery, Grafana query checks, drift, rollback and executed test results. A synthetic gate PASS does not prove production readiness.
