# Chapter 099 — Enterprise Observability Operational Readiness, Incident Command and Production Reliability Acceptance Lab

**Part 20 — Final Production Observability Capstones**

## Guardrails

Use a tabletop or approved staging environment, never live production paging, destructive fault injection or unapproved credential changes. Designate an incident commander and independent reviewer.

## Lab 1 — Service ownership and escalation

Create a service catalogue for Collector, Prometheus, Alertmanager, Grafana, Loki, Tempo, Kubernetes, PostgreSQL, MongoDB and Kafka. For each, record primary/secondary owner, critical SLI, escalation, runbook, backup/DR tier and support hours.

## Lab 2 — SLO and alert quality

Choose critical user journeys: metrics query, telemetry ingest, alert delivery and trace lookup. Document numerator/denominator, objective, time window, excluded traffic, error budget, burn-rate rules and independent probe. Exercise a staging-only synthetic alert and record receipt time.

## Lab 3 — Incident command tabletop

Simulate a simultaneous Collector outage and Alertmanager routing failure. Assign IC, operations, communications and scribe. Record declaration, severity, customer impact, out-of-band paging, diagnosis, rollback, verified recovery, status updates and postmortem.

## Lab 4 — Offline ORR evaluator

Copy `orr_gate.py`, `make_fixture.py` and `test_orr_gate.py` from [Chapter 099](../099-enterprise-observability-operational-readiness-incident-command-production-reliability-acceptance.md).

```bash
python3 make_fixture.py
python3 orr_gate.py synthetic-orr.json
python3 -m unittest -v test_orr_gate.py
```

Expected synthetic result: GO with 100 points; 15 authored unittest methods pass. This proves only offline policy logic.

## Lab 5 — Negative acceptance tests

Modify one fixture field at a time: environment=production, approved=false, destructive=true, abort_triggered=true, reviewer=owner, empty change_id, failed alerting, missing security evidence, failed DR, missing privacy evidence, failed ORR-05, failed ORR-11. Every change must yield NO-GO and nonzero exit. Restore fixture afterward.

## Lab 6 — DBRE and security handoff

Tabletop PostgreSQL replication lag, MongoDB storage pressure and Kafka consumer lag. Validate that missing exporter metrics are not mistaken for database health. Rehearse synthetic tenant A/B denial, redaction canary and SOC escalation.

## Lab 7 — DR and change acceptance

Review backup hashes, clean-room restore, RPO/RTO measurements, GitOps pinned revision, schema compatibility, rollback timing, change approvals and evidence chain. Any untested critical requirement remains a blocker.

## Lab 8 — Formal ORR

Produce a signed decision record with scope, version, evidence references, score, open risks, action owners, due dates, security/SRE/DBRE sign-offs, operational roster and explicit GO/NO-GO. Do not treat a synthetic GO as deployment approval.

## Troubleshooting prompts

- Why are dashboards green while Collector exports are failing?
- How do you detect Alertmanager failure without Alertmanager?
- What is the difference between a missing DB exporter signal and a healthy database?
- Why does successful backup creation not prove recovery?
- What must be rechecked after a regional failover?
- Which critical findings always block promotion?

## Completion criteria

Real operational acceptance requires all 12 controls and all 12 incident scenarios evidenced in staging, no critical blockers, reviewed incident command and rollback, and independent approval. Chapter publication alone does not satisfy this lab.
