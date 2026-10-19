# Chapter 077 — Enterprise Incident Triage and Root Cause Investigation Lab

**Part 16 — Incident Response and Troubleshooting**

## Offline setup

Copy `healthy.json`, `triage_gate.py` and `test_triage_gate.py` from [Chapter 077](../077-enterprise-incident-triage-signal-correlation-root-cause-investigation.md).

```bash
python3 triage_gate.py healthy.json
python3 -m unittest -v test_triage_gate.py
```

Expected PASS and 28 authored tests. Capture actual output.

## Staging game day

1. Define incident ID, user impact, UTC window and SLO burn.
2. Correlate request errors, latency and resource saturation.
3. Inspect bounded Loki logs and Tempo traces using trace IDs.
4. Compare deployment changes and service dependency graph.
5. Inspect PostgreSQL waits/pool, Redis latency, Kafka lag, search rejections and Snowflake freshness.
6. Record two competing hypotheses with predicted and disconfirming evidence.
7. Rehearse a reversible mitigation in staging.
8. Verify independent SLI recovery and data freshness.
9. Preserve redacted evidence and timestamps.
10. Draft a blameless RCA with owners and corrective deadlines.

## Negative drills

Test missing evidence controls, absent impact, invalid incident ID, missing timeline, unsafe environment and destructive action rejection.

## Evidence worksheet

```text
Incident / owner / UTC:
Customer impact and SLO burn:
RED/USE metrics:
Logs and traces:
Change timeline:
Dependency observations:
Hypotheses and counterevidence:
Mitigation / rollback:
Independent recovery:
RCA and corrective actions:
Offline gate and 28 tests:
```

Synthetic evidence validation does not prove a root cause or live recovery.
