# Chapter 076 — Incident Response Architecture and On-Call Operations Lab

**Part 16 — Incident Response and Troubleshooting**

## Offline validation

Save `healthy.json`, `incident_gate.py` and `test_incident_gate.py` from [Chapter 076](../076-enterprise-incident-response-architecture-severity-models-on-call-operations.md).

```bash
python3 incident_gate.py healthy.json
python3 -m unittest -v test_incident_gate.py
```

Expected PASS and 27 authored tests. Capture actual results.

## Staging tabletop and game day

1. Confirm incident commander, operations lead, communications lead and scribe.
2. Review SEV1/SEV2/SEV3 impact definitions.
3. Test primary and secondary on-call escalation in a non-production route.
4. Capture UTC timeline and independent SLO evidence.
5. Correlate Grafana, Prometheus, Loki, Tempo and dependency metrics.
6. Simulate bounded API latency and PostgreSQL pool pressure.
7. Rehearse an incident update and owner escalation.
8. Apply reversible mitigation and verify rollback readiness.
9. Confirm independent user-facing SLI recovery.
10. Hold a blameless review with follow-up owners and deadlines.

## Negative drills

Reject missing command roles, unsupported severity, absent evidence, unsafe environment, invalid incident IDs and destructive actions.

## Evidence worksheet

```text
Incident ID / UTC / SEV:
Commander / operations / communications:
Affected user journey:
RED/USE and SLO burn:
Dependency evidence:
Primary/secondary escalation:
Mitigation and rollback:
Independent recovery:
Postmortem actions:
Offline gate and 27 tests:
```

Offline validation does not prove real paging or incident response readiness.
