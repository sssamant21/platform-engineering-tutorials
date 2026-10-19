# Chapter 093 — Enterprise Observability Security Monitoring and Incident Response Automation Lab

## Prerequisites

Python 3.10+, a disposable staging environment for optional integrations, and no production credentials. Copy `security_gate.py`, `safe-event.json`, and `test_security_gate.py` from [Chapter 093](../093-enterprise-observability-security-monitoring-threat-detection-incident-response-automation.md).

## Lab A — Offline decision gate

```bash
python3 security_gate.py safe-event.json
python3 -m unittest -v test_security_gate.py
```

Expected: PASS for the synthetic notification and nine passing unit tests. Record actual output; no live execution is implied.

## Lab B — Safe negative tests

1. Change environment to production; verify the gate fails.
2. Set `tenant_scoped` false; verify denial.
3. Set `audit_preserved` false; verify denial.
4. Set action to `revoke_token` without approval; verify denial.
5. Set `destructive` true; verify denial.
6. Add approver and rollback plan to an approved staging revocation *decision record*; verify policy PASS, without executing revocation.

## Lab C — Optional isolated observability stack

1. Send synthetic JSON authentication and gateway denial events through a configured OpenTelemetry or Loki ingestion path.
2. Verify timestamps, tenant boundaries, redaction, and source identity.
3. Create and test a read-only dashboard for denial rates and audit-forwarder health.
4. Correlate synthetic IAM, Kubernetes and configuration-change events within a five-minute UTC window.
5. Simulate a collector exporter failure and validate that the alert reaches a staging-only notification endpoint.
6. Restore ingestion, verify alert resolution and archive an incident timeline.

## Lab D — SRE/SOC game day

Assign incident commander, security lead, observability operator and evidence custodian. Rehearse suspicious admin grant, cross-tenant query attempts, telemetry tampering and audit outage. For every scenario, capture detection timestamp, false-positive reasoning, affected scope, human approval, rollback decision and recovery proof.

## Evidence and sign-off

Attach command outputs, test counts, rule configurations, synthetic event samples, UTC timestamps, incident tickets, approved change records and a completed 100-point rubric. The offline PASS is not proof of production security, live threat detection, or independent compliance verification.
