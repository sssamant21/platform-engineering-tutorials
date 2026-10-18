# Chapter 061 — Database and Data Platform Observability Architecture Lab

**Part 13 — Database and Data Platform Observability**

## Offline acceptance

Copy `healthy.json`, `dbre_signals_gate.py` and `test_dbre_signals_gate.py` from [Chapter 061](../061-database-data-platform-observability-architecture-metrics-reliability-signals.md).

```bash
cd chapter061
python3 dbre_signals_gate.py healthy.json
python3 -m unittest -v test_dbre_signals_gate.py
```

Expected PASS and 30 authored tests.

## Approved staging integration

1. Record owner, platform, service dependency and environment.
2. Verify a platform exporter or managed monitoring source.
3. Query availability, p95 latency, throughput and errors.
4. Compare CPU, memory, connections, IOPS and queueing.
5. Inspect replication lag and downstream freshness separately.
6. Validate Grafana dashboards and alert routing.
7. Simulate a bounded lag or saturation fault in staging.
8. Verify sensitive-data redaction and bounded metric labels.
9. Confirm independent user-facing SLI recovery.
10. Capture runbook, rollback and reviewer evidence.

## Twelve negative drills

1. Missing owner.
2. Unsupported platform.
3. Availability review absent.
4. Latency review absent.
5. Storage review absent.
6. Replication review absent.
7. Freshness review absent.
8. Backup review absent.
9. Security review absent.
10. Availability below threshold.
11. Replication lag over threshold.
12. Rollback untested.

## Evidence worksheet

```text
UTC / platform / owner / change ID:
Exporter/provider source and scrape:
Availability / latency / throughput / errors:
CPU / cache / disk / connections:
Replication lag / CDC freshness:
Backup/restore evidence:
Alert routing and runbook:
Incident timeline / recovery / rollback:
Offline gate / 30 tests:
```

Offline validation is not a substitute for live DBRE evidence.
