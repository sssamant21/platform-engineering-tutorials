# Chapter 095 — Enterprise Observability Security, Governance and Reliability Acceptance Capstone Lab

**Part 19 final capstone · staging/lab only**

## Lab goals and safety

Demonstrate a reproducible security/reliability acceptance workflow for Prometheus, Grafana, Loki, Tempo, OpenTelemetry, Alertmanager, GitOps and storage. Do not run destructive tests or change production routing, IAM, DNS or KMS. Use synthetic tenants, synthetic tokens and a test paging receiver.

## Lab A — Offline evidence evaluator

Copy `acceptance_gate.py`, `make_fixture.py`, and `test_acceptance_gate.py` verbatim from [Chapter 095](../095-enterprise-observability-security-governance-reliability-acceptance-capstone.md). Python 3.10+ is sufficient; no third-party dependencies.

```bash
python3 make_fixture.py
python3 acceptance_gate.py synthetic-acceptance.json
python3 -m unittest -v test_acceptance_gate.py
```

Expected synthetic fixture result: `GO`, score 100, no findings. This is **only a software evaluator self-test**, not real operational certification. The suite has 13 authored unittest methods, including parameterized subtests over the 13 controls and six critical controls.

## Lab B — Negative gates

Change one item at a time in the synthetic fixture, rerun the gate, and confirm nonzero exit and `NO-GO`:

| Injection | Expected |
|---|---|
| environment = production | rejected |
| approved = false | rejected |
| destructive = true | rejected |
| reviewer = owner | rejected |
| remove tenant-isolation evidence | rejected; critical blocker |
| fail privacy redaction | rejected; critical blocker |
| remove paging evidence | rejected; critical blocker |
| fail clean restore | rejected; critical blocker |
| fail a noncritical policy check | rejected; remediation required |
| remove assessment ID | rejected |

Restore the fixture and confirm clean synthetic `GO`.

## Lab C — Enterprise acceptance staging exercises

1. **Architecture review:** draw ingress, tenant boundaries, identity propagation, storage, SOC integration and DR trust boundaries.
2. **Tenant isolation:** send tenant A and B synthetic metrics/logs/traces and verify tenant A cannot query B through Grafana *or direct APIs*.
3. **Redaction:** emit a `TRAINING_ONLY_TOKEN_DO_NOT_USE` canary; verify absence from backend storage, queries and exports.
4. **Retention:** check policy and object lifecycle with disposable fixtures; preserve any approved legal-hold samples.
5. **Detection:** generate synthetic failed-auth and unauthorized-query events; prove test SIEM/SOC and paging delivery.
6. **Incident response:** tabletop Collector credential compromise, audit preservation and scoped credential rotation.
7. **Backup:** create versioned encrypted staging backups, verify checksum, and restore into isolated namespace.
8. **DR:** measure backup age, recoverable sample timestamp, restore elapsed time, secure read/write and alerting.
9. **Reliability:** inject isolated ingest/query degradation and validate SLO alerts, escalation and rollback.
10. **GitOps:** inject disposable drift and verify policy rejection and reviewed reconciliation.
11. **Independent review:** obtain security/SRE sign-off and record unresolved risks and remediation owners.

## Lab D — Evidence manifest and final decision

For each control, collect test ID, UTC timestamp, owner, immutable evidence URI, command or test procedure, expected/actual result, reviewer and outcome. Replace synthetic evidence strings with actual traceable staging evidence only after tests are performed. Never mark a test as passed because a document or configuration exists.

Create a decision record containing assessment ID, system scope, deployment version, risk owner, security reviewer, SRE reviewer, score, critical blockers, exceptions, expiry, remediation plan and GO/NO-GO recommendation.

## Troubleshooting

| Symptom | Investigation |
|---|---|
| Synthetic gate returns NO-GO | inspect findings and fixture JSON types |
| Tenant B records visible to tenant A | check server-side auth, query gateway and backend bypass |
| Canary present in logs | check processor order and exporters, then purge via approved process |
| Alert not delivered | check receiver routes, silences, queue, network and test receiver |
| Restore succeeds but queries fail | check storage schema, indexes, tenant mapping and KMS |
| RPO/RTO cannot be measured | instrument backup timestamp and recovery start/end UTC |
| Drift not detected | verify reconciler health, Git commit and target namespace |
| Audit record missing | inspect collection pipeline and immutable retention |

## Completion criteria

All 13 required controls evidenced and reviewed; no critical blockers; full rollback and incident timeline; independently approved GO/NO-GO. Synthetic gate success alone does not satisfy this lab. Live operational validation and independent compliance verification remain pending unless actual evidence is produced.
