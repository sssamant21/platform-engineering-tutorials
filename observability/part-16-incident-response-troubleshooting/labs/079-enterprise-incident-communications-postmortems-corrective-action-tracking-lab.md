# Chapter 079 — Incident Communications, Postmortems and Corrective Action Lab

**Part 16 — Incident Response and Troubleshooting**

## Offline validation

Copy `healthy.json`, `comms_gate.py` and `test_comms_gate.py` from [Chapter 079](../079-enterprise-incident-communications-postmortems-corrective-action-tracking.md).

```bash
python3 comms_gate.py healthy.json
python3 -m unittest -v test_comms_gate.py
```

Expected PASS and 28 authored tests; capture actual output.

## Staging tabletop

1. Declare incident and assign incident commander and communications lead.
2. Define internal, leadership and customer stakeholder groups.
3. Confirm affected user journeys and SLO evidence.
4. Draft initial update with verified impact and next UTC update.
5. Simulate a change in incident severity and revise communications.
6. Redact sensitive details from timeline and evidence.
7. Publish a monitoring update only after independent SLI recovery.
8. Facilitate blameless postmortem with trigger and contributing factors.
9. Create corrective actions with owners, deadlines and measurable acceptance criteria.
10. Review overdue actions and effectiveness evidence.

## Negative drills

Reject missing impact verification, unowned actions, invalid severity, missing timeline, unsafe environment and sensitive-data leakage.

## Evidence worksheet

```text
Incident / severity / UTC:
Communications lead:
Affected customer journey:
Audience and update cadence:
Verified evidence and redactions:
Recovery SLIs:
Postmortem timeline and causal hypotheses:
Corrective action owner / deadline:
Effectiveness test:
Offline gate and 28 tests:
```

The offline gate does not send messages or certify real postmortem quality.
