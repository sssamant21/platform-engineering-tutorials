# Chapter 070 — Enterprise APM Incident Response and Reliability Capstone Lab

**Part 14 final capstone**

## Offline validation

Save `healthy.json`, `apm_capstone_gate.py` and `test_apm_capstone_gate.py` from [Chapter 070](../070-enterprise-application-performance-monitoring-incident-response-reliability-capstone.md).

```bash
python3 apm_capstone_gate.py healthy.json
python3 -m unittest -v test_apm_capstone_gate.py
```

Expected PASS and 28 authored tests; record actual results.

## Approved staging game day

1. Confirm service owner, incident commander, change and rollback plan.
2. Capture independent API availability, error rate and p95/p99 SLOs.
3. Trace requests through PostgreSQL, Redis and Kafka dependencies.
4. Verify service map, W3C propagation and log/trace correlation.
5. Inspect Collector drops, sampling and sensitive attribute controls.
6. Capture bounded CPU, memory, GC and thread profiles.
7. Run isolated k6 smoke and constant-arrival-rate tests.
8. Compare achieved RPS, dropped iterations and downstream saturation.
9. Trigger bounded dependency slowdown and SLO alert.
10. Execute approved rollback and verify recovery.

## Negative drills

Test missing review controls, missing owner/change, unsafe environment, availability/latency/error/trace coverage breaches, invalid percentages and unsafe actions.

## Evidence worksheet

```text
UTC / incident commander / change:
RED and USE baseline:
Service map / trace continuity:
PostgreSQL / Redis / Kafka dependencies:
CPU / heap / GC / thread profiles:
Load requested/achieved and dropped iterations:
Collector drops and privacy:
SLO alert and burn-rate evidence:
Rollback and independent recovery:
Offline gate and 28 tests:
Final assessment score / reviewer:
```

Synthetic gate results do not establish live production reliability.
