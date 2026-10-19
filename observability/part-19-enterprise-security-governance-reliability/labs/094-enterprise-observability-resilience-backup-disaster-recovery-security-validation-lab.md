# Chapter 094 — Enterprise Observability Resilience, Backup and Disaster Recovery Lab

## Safety and prerequisites

Use a disposable lab or staging environment. Do not run destructive operations against production, alter live IAM/KMS policies, or fail over real endpoints. Python 3.10+ is sufficient for the offline tests.

Copy `recovery_gate.py`, `healthy-recovery.json` and `test_recovery_gate.py` from [Chapter 094](../094-enterprise-observability-resilience-backup-disaster-recovery-security-validation.md).

## Lab 1 — Offline RPO/RTO acceptance

```bash
python3 recovery_gate.py healthy-recovery.json
python3 -m unittest -v test_recovery_gate.py
```

Expected synthetic PASS and 12 authored unittest methods (the last iterates over 12 required controls). Record actual output.

## Lab 2 — Negative evidence drills

1. Set `measured_rpo_minutes` to 16; expect FAIL for the 15-minute target.
2. Set `measured_rto_minutes` to 61; expect FAIL for the 60-minute target.
3. Mark `backup_integrity` false; expect FAIL.
4. Mark `tenant_isolation` false; expect FAIL.
5. Set `approved` false; expect FAIL.
6. Set `environment` to `production`; expect FAIL.
7. Set `destructive` true; expect FAIL.
8. Restore original fixture and confirm PASS.

## Lab 3 — Optional isolated restore rehearsal

1. Inventory Grafana DB, Prometheus config and TSDB, Loki/Tempo object stores, Collector config, IAM/KMS and Alertmanager state.
2. Capture version, checksum, snapshot timestamp and backup manifest for disposable fixtures.
3. Export staging Grafana provisioning/config and take a database-consistent staging backup.
4. Restore to a fresh isolated namespace and verify dashboard, data source and permission behavior.
5. Reconcile Prometheus and Alertmanager rules from pinned GitOps commits; validate paging to a staging-only receiver.
6. Inject synthetic logs and traces through Collector; query them after recovery.
7. Test denied tenant B access using a tenant A identity.
8. Measure actual UTC restore start/end, last recoverable sample and alert delivery.
9. Require human approval for any DNS or traffic cutover simulation; use a non-production hostname.
10. Store hashes, screenshots, CLI output, incident timeline, approval record and rollback evidence.

## Lab 4 — Tabletop failure scenarios

Run Grafana database loss, Prometheus TSDB corruption, Loki/Tempo partial storage loss, unavailable KMS key, collector outage, regional failure and replicated deletion. For each, document detection, dependencies, data-loss window, clean recovery point, restore validation, security rechecks and postmortem action.

## Evidence package

Submit RPO/RTO measurements, backup manifest and checksums, restore logs, Grafana/Prometheus/Loki/Tempo/Collector checks, tenant isolation test, Alertmanager notification proof, rollback decision and 100-point rubric. Synthetic offline PASS is not live DR validation or independent compliance verification.
