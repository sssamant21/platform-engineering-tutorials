# Chapter 090 — DevOps/SRE Automation Production Capstone Lab

[Standalone executable project](090/README.md) · [Python capstone engine](090/capstone.py) · [Offline unit tests](090/test_capstone.py)

## Mission

Integrate bounded infrastructure inventory, host metrics, request availability SLI, error budgets, burn-rate detection, incident correlation, operational readiness, plan digests, simulated approval, sandbox-only idempotent action and JSONL audit.

## Architecture

\`\`\`text
synthetic inventory ─┐
host utilization ────┼─> validation ─> SLO and incident assessment
request outcomes ────┘                  |
                                  readiness gate
                                        |
                               plan + SHA-256 digest
                                        |
                                dry-run by default
                                        |
                            simulated approval and expiry
                                        |
                              sandbox-only local marker
                                        |
                               JSONL audit and verify
\`\`\`

## Lab 1 — Offline tests and CLI

\`\`\`bash
cd python/09-devops-sre-automation/labs/090
python -m compileall -q capstone.py test_capstone.py
python -m unittest -v test_capstone.py
python capstone.py --dry-run
python capstone.py --failures 0
python capstone.py --failures 20 --pressure
\`\`\`

All input is synthetic. No Kubernetes cluster, cloud account, database, Docker socket, Prometheus server or production credentials are needed.

## Lab 2 — Inventory and monitoring

Inspect synthetic PostgreSQL database and Pod records. Validate resource names, service scope, health classification and inventory budgets. Introduce unhealthy resources, CPU pressure, disk pressure, NaN utilization and stale timestamps. Confirm invalid inputs fail closed.

## Lab 3 — SLI, SLO and burn rate

With a 99% target and 100 eligible requests, the error budget is one failed request. Ten failures exhaust the budget by nine and create a burn rate of ten. Compare with a healthy 100/100 window and a no-traffic window. The latter is unknown and must block release readiness.

## Lab 4 — Readiness and incident correlation

Require fresh telemetry, assigned owner, tested rollback, backup/restore, paging route and capacity review. Simulate active Sev1, failed backup test and missing inventory. Verify release readiness is blocked. Inspect the incident plan rationale: high burn takes precedence over resource pressure, but neither proves root cause.

## Lab 5 — Simulated approval and idempotent action

Follow [090/README.md](090/README.md) to create a disposable sandbox and run \`apply_marker\` with an exact plan digest, simulated approver and unexpired approval. Confirm the first apply writes one marker and an audit event; a repeat returns \`already-applied\`; a conflicting plan is rejected. The approval mechanism is **not** authenticated and cannot be used to authorize production actions.

## Lab 6 — Incident simulations

| Scenario | Expected result | Mode |
|---|---|---|
| Healthy inventory | Scoped resources counted | Automated |
| Unhealthy workload | Unhealthy count and blocked gate | Automated |
| Invalid resource/scope | Reject | Automated |
| Inventory budget exceeded | Reject | Automated |
| Valid host sample | Accepted | Automated |
| NaN/negative sample | Reject | Automated |
| Stale/future metric | Reject | Automated |
| Healthy SLO | Availability 100% | Automated |
| Error budget exhausted | Negative budget | Automated |
| Fast burn | High burn rate | Automated |
| No/low traffic | Unknown or insufficient | Automated |
| Invalid target/outcome | Reject | Automated |
| Missing owner/rollback | Block release | Automated |
| Active Sev1 | Block release | Automated |
| Missing inventory | Block release | Automated |
| CPU/disk pressure | Block release | Automated |
| High burn correlation | Candidate incident | Automated |
| Invalid remediation action | Reject | Automated |
| Dry-run | Zero mutations | Automated |
| Missing/mismatched/expired approval | Reject | Automated |
| Sandbox apply | One marker | Automated |
| Duplicate apply | Already applied | Automated |
| Conflicting plan | Reject | Automated |
| Tampered marker | Fail closed | Automated |
| Audit events | Applied and duplicate | Automated |
| Missing sandbox | Reject | Automated |
| CLI healthy/incident/invalid input | Structured output | Automated |
| Alert routing outage | Restore paging path | Guided |
| External side effect ambiguous | Reconcile before retry | Guided |
| Concurrent worker race | Transactional claim/fencing | Guided |
| PostgreSQL primary outage | Preserve quorum and backup | Guided |
| Elasticsearch IOPS bottleneck | Correlate latency, queue, disk | Guided |
| MongoDB election instability | Avoid blind stepdown | Guided |
| Kafka lag and ISR loss | Protect partition availability | Guided |
| Kubernetes rollout regression | Approved rollback | Guided |
| Snowflake freshness breach | Check task/warehouse dependency | Guided |

## Lab 7 — Troubleshooting and runbooks

**Monitoring failure:** inspect timestamp freshness, missing data and collector health; do not declare a service healthy on zero samples.

**SLO breach:** validate denominator, compare deployment timeline, identify dependency failure, stop risky rollout and confirm user-visible recovery.

**Readiness blocked:** inspect owner, rollback, backups, paging, capacity and budget; collect independent evidence before approval.

**Idempotency conflict:** stop, inspect marker/digest and reconcile. Never overwrite unknown state.

**DBRE incident:** inspect replication/quorum, IOPS, lock waits, backups and RPO/RTO. Never automatically restart a primary or delete indices from a single metric.

**Audit failure:** halt execution, preserve evidence and reconcile marker state; JSONL is educational, not a production audit store.

## 100-point final assessment

| Domain | Points |
|---|---:|
| Inventory and telemetry validation | 15 |
| SLI/SLO and error-budget calculations | 20 |
| Burn rate and incident correlation | 15 |
| Readiness and approval policy | 15 |
| Dry-run, idempotency and audit | 15 |
| Automated tests and failure drills | 10 |
| Troubleshooting, runbooks and security | 10 |
| **Total** | **100** |

**Pass target:** ≥90/100, independently executed tests, verified dry-run and sandbox-only effects, and an operator-reviewed incident response plan. This is a training capstone, not a production deployment acceptance.

**Validation:** GitHub source, lab and test suite are published. Execution of the final committed version and CI remain pending.
