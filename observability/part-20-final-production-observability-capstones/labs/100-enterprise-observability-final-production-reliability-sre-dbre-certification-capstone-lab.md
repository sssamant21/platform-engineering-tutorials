# Chapter 100 — Enterprise Observability Final Production Reliability and SRE/DBRE Certification Capstone Lab

**Part 20 — Final Production Observability Capstones (5/5)**

## Guardrails

Training assessment only; not accredited certification or production approval. Use a disposable lab or separately approved staging namespace. Do not use customer data, live paging, production credentials or destructive chaos.

## Lab 1 — Architecture (10 points)

Produce system diagrams, ADRs, SLO catalogue, data classification, retention, security threat model, tenant identity and RACI. Include Kubernetes, OpenTelemetry, Prometheus, Loki, Tempo, Grafana, Alertmanager and PostgreSQL/MongoDB/Kafka exporters.

## Lab 2 — Staging deployment and rollback (10 points)

Deploy pinned approved components through GitOps. Validate IAM, TLS, network policy, resource quotas, storage, image provenance, readiness and rollback compatibility. Capture Git revision and commands.

## Lab 3 — Signal correctness (15 points)

Emit a synthetic request with correlation ID. Query metrics in Prometheus, logs in Loki and traces in Tempo. Check ingestion delays, dropped-signal counters, label cardinality and sampling.

## Lab 4 — SLO and paging (15 points)

Define numerator, denominator, objective, error budget and burn-rate rules. Trigger staging-only synthetic alert and prove delivery via independent test receiver.

## Lab 5 — Security and privacy (15 points)

Verify SSO/RBAC, tenant A/B denied direct API queries, synthetic canary redaction, audit, encryption and retention. Any cross-tenant exposure is an immediate NO-GO.

## Lab 6 — Capacity and FinOps (5 points)

Model ingest and query volume, cardinality, storage retention, network egress and budget. Compare with measured staging load.

## Lab 7 — Incident command and DBRE (10 points)

Tabletop Collector failure and database replication lag. Assign incident commander, operations, communications and scribe. Record timeline, detection, mitigation, escalation and verified recovery.

## Lab 8 — Backup and DR (15 points)

Validate backup hashes and encryption keys, restore in isolation, query all signals, recheck tenant isolation and paging, and measure RPO/RTO. Backup creation alone is insufficient.

## Lab 9 — Independent acceptance (5 points)

Submit evidence index, signed review, operational roster, runbooks, rollback proof, risk register and GO/NO-GO. Unverified critical controls remain blockers.

## Lab 10 — Automated offline gate

Copy `final_gate.py`, `make_fixture.py`, `test_final_gate.py` from [Chapter 100](../100-enterprise-observability-final-production-reliability-sre-dbre-certification-capstone.md).

```bash
python3 make_fixture.py
python3 final_gate.py synthetic-final.json
python3 -m unittest -v test_final_gate.py
```

Expected: synthetic GO 100/100 and 17 authored unittest methods. This is only a software fixture test, not real acceptance.

## Negative tests

Individually set: environment=production; approved=false; destructive=true; abort_triggered=true; reviewer=owner; git_sha empty; signals failed; slo_alerting failed; security_privacy failed; backup_dr failed; independent_review evidence empty; FIN-06 failed; FIN-07 failed; FIN-11 failed. Every case must return NO-GO and nonzero exit.

## Final scenario assessment

Complete FIN-01 through FIN-12 in the main chapter. For each, record hypothesis, approved scope, commands, query output, UTC timestamps, incident owner, evidence reference, recovery, rollback and independent review. Clearly distinguish executed staging tests from tabletop exercises.

## Grading

| Domain | Points |
|---|---:|
| Architecture | 10 |
| Deployment/GitOps | 10 |
| Signals | 15 |
| SLOs/alerting | 15 |
| Security/privacy | 15 |
| Capacity/FinOps | 5 |
| Incident/DBRE | 10 |
| Backup/DR | 15 |
| Independent review | 5 |
| **Total** | **100** |

All domains and FIN scenarios are mandatory for a GO. A synthetic manifest does not award points to an actual learner.

## Completion

The published 100-chapter curriculum ends here. Hands-on execution, independent certification, compliance sign-off and production promotion require separate verifiable evidence.
