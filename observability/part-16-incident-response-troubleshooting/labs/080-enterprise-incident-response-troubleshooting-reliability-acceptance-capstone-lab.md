# Chapter 080 — Enterprise Incident Response Reliability Acceptance Lab

**Part 16 final capstone**

## Offline setup

Copy `healthy.json`, `acceptance_gate.py` and `test_acceptance_gate.py` from [Chapter 080](../080-enterprise-incident-response-troubleshooting-reliability-acceptance-capstone.md).

```bash
python3 acceptance_gate.py healthy.json
python3 -m unittest -v test_acceptance_gate.py
```

Expected PASS and 35 authored tests. Capture actual results; execution remains pending.

## Approved staging game day

1. Confirm incident commander, communications lead, service owners and rollback approval.
2. Baseline API availability, latency and Kafka-to-Snowflake freshness.
3. Test primary/secondary escalation in a staging-only route.
4. Inject a bounded synthetic API error/latency regression.
5. Correlate Grafana, Prometheus, Loki, Tempo and UTC deployment events.
6. Investigate PostgreSQL pool waits, Redis hot keys, Kafka lag and search rejections.
7. Compare at least two causal hypotheses and document counterevidence.
8. Execute only an approved reversible staging mitigation.
9. Verify independent API SLIs, data correctness, freshness and stable observation.
10. Publish incident communications, blameless review and owned corrective actions.

## Negative drills

Reject missing owners, severity, telemetry evidence, recovery verification, action ownership, approvals and unsafe environments.

## Evidence worksheet

```text
Incident / UTC / SEV / commander:
User impact / SLO burn:
Primary and secondary escalation:
RED/USE / logs / traces:
PostgreSQL / Redis / Kafka / Search / Snowflake:
Hypotheses / counterevidence:
Mitigation approval / rollback:
Independent recovery and stability:
Communications and postmortem:
Corrective owner / deadline / effectiveness:
Offline gate and 35 tests:
```

## Scoring

20 points each: detection and severity; correlation and dependencies; command and communications; safe mitigation and recovery; postmortem and corrective action. Recommended pass: 85/100.

Synthetic gate success is not evidence of live incident readiness.
