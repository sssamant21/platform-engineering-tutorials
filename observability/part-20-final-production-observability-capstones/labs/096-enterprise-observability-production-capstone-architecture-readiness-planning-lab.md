# Chapter 096 — Enterprise Observability Production Capstone Architecture and Readiness Planning Lab

**Part 20 · Final Production Observability Capstones**

## Prerequisites and guardrails

Use a local workstation with Python 3.10+ and an optional disposable Kubernetes staging cluster. No production credentials, destructive changes or live DNS/IAM modifications are required.

## Lab 1 — Build an architecture inventory

Document all synthetic application, PostgreSQL, MongoDB, Kafka, Kubernetes and cloud telemetry sources. For each record: region, owner, data classification, signal type, retention, SLO, alert route, tenant identity and recovery tier.

Create diagrams for: workload → Collector → backend → dashboard/alert; human and workload authentication; storage encryption and backups; regional failure domains; SOC/audit integration.

## Lab 2 — Capacity worksheet

Calculate for the sample scenario:

- 100,000 active time series at 30-second scrape interval.
- 5,000 log events/s averaging 800 bytes.
- 2,000 spans/s averaging 600 bytes.
- 30-day metrics, 14-day logs and 7-day trace retention.

Compute daily raw ingestion and compare at least two sampling/compression scenarios. Include replication, index and network costs as separate variables, not invented constants. State assumptions and uncertainties.

## Lab 3 — Offline readiness acceptance gate

Copy the complete `readiness_gate.py`, `make_fixture.py`, and `test_readiness_gate.py` from [Chapter 096](../096-enterprise-observability-production-capstone-architecture-readiness-planning.md).

```bash
python3 make_fixture.py
python3 readiness_gate.py synthetic-readiness.json
python3 -m unittest -v test_readiness_gate.py
```

Expected: synthetic fixture returns GO with 100 points, and the 12 authored test methods pass. This is not proof of any real infrastructure control.

## Lab 4 — Negative policy and evidence tests

Change one fixture field at a time and verify NO-GO:

| Test | Change |
|---|---|
| Unauthorized target | `environment` to `production` |
| Missing approval | `approved` to false |
| Unsafe activity | `destructive` to true |
| Reviewer conflict | `reviewer` equal to `owner` |
| Missing architecture | empty `architecture_ref` |
| Security blocker | `security_reviewed.passed` false |
| Tenant blocker | `tenant_isolation_tested.passed` false |
| Paging blocker | `alerting_tested.passed` false |
| DR blocker | `dr_tested.passed` false |
| Unsupported evidence | empty `capacity_tested.ref` |

Rebuild the fixture and verify the synthetic happy path again.

## Lab 5 — Optional isolated staging review

Deploy only with approved local/staging manifests. Review OpenTelemetry pipeline connectivity, backend queries, dashboards, test paging, TLS and tenant identity. Inject a disposable Collector outage, check telemetry loss and rollback. Verify encrypted staging backup and an isolated restore. Collect timestamps, logs, hashes and approvals. Never infer real RPO/RTO from the offline fixture.

## Lab 6 — Architecture decision meeting

Have independent reviewers challenge the following: region failure, cardinality explosion, cost overrun, log PII leakage, untrusted exporter destination, cross-tenant query bypass, unavailable KMS, compromised Collector identity and alerting failure. Record the design change and accountable owner for each unresolved risk.

## Deliverables

Submit diagrams, ADRs, requirements and SLO catalogue, capacity model, security/privacy threat model, DR plan, runbooks, executed synthetic gate output, staging evidence where available, and a signed GO/NO-GO recommendation.

**Completion rule:** A synthetic PASS verifies only the offline evaluator. Production readiness remains unverified until independent evidence-backed review.
