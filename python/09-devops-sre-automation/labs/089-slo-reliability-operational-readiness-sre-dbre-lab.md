# Chapter 089 — Reliability Engineering, SLO Automation and Operational Readiness SRE/DBRE Lab

**Executable project:** [089/README.md](089/README.md) · [reliability.py](089/reliability.py) · [offline tests](089/test_reliability.py)

## Mission

Calculate request availability and latency SLIs, error budgets and burn rates; combine SLO health with operational readiness evidence to evaluate whether a release is safe. Use synthetic events and no production mutations.

\`\`\`text
synthetic requests -> eligibility and latency classification
 -> short/long window SLI -> error budget + burn
 -> readiness checks (telemetry, rollback, paging, backups, owner, capacity)
 -> release gate decision -> operator-reviewed runbook
\`\`\`

## Exercise 1 — Run automated tests

\`\`\`bash
cd python/09-devops-sre-automation/labs/089
python -m compileall -q reliability.py test_reliability.py
python -m unittest -v test_reliability.py
python reliability.py --dry-run
python reliability.py --failures 0
python reliability.py --failures 20 --target 0.99
\`\`\`

The lab uses Python 3.11+ standard library only. No credentials, cluster access, exporter or database are required.

## Exercise 2 — SLIs and error budgets

For a 99.9% availability target and 100,000 eligible requests, approximately 100 bad requests are permitted. If 150 requests fail, remaining budget is -50. Compute the same quantities from the lab fixture and explain how low traffic affects statistical confidence. Compare availability and latency SLIs: a successful but slow request is good for availability yet bad for latency.

## Exercise 3 — Multiwindow burn-rate alerts

\`multiwindow_burn\` evaluates short and long half-open windows and requires minimum traffic in both. Test a burst of failures versus an extended degradation. Explain why production alerting uses multiple window pairs and distinct burn thresholds, and why missing telemetry must not be interpreted as good performance.

## Exercise 4 — Readiness gates

Use \`readiness\` to require fresh telemetry, tested rollback, assigned owner, paging-route test, backup/restore evidence and capacity review. Block a release if an active Sev1 incident exists, fast burn is active, evidence is missing, or sample volume is insufficient. In production, collect checks from authenticated systems; never trust client-provided booleans as change approval.

## Incident simulations

| # | Scenario | Expected behavior | Coverage |
|---|---|---|---|
| 1 | Availability calculation | Correct SLI | Automated |
| 2 | Latency SLI | Correct threshold ratio | Automated |
| 3 | Excluded event | Not counted | Automated |
| 4 | Window boundary | Half-open semantics | Automated |
| 5 | No traffic | Unknown SLI | Automated |
| 6 | Missing traffic burn | Unknown burn | Automated |
| 7 | Budget exhaustion | Negative remainder | Automated |
| 8 | Burn-rate calculation | Bad fraction / allowed fraction | Automated |
| 9 | Minimum event gate | Reject low-confidence alert | Automated |
| 10 | Invalid target/window | Reject | Automated |
| 11 | Invalid latency/classification | Reject | Automated |
| 12 | Fast burn | Alert active | Automated |
| 13 | No burn | Alert inactive | Automated |
| 14 | Missing samples | No false positive | Automated |
| 15 | Invalid burn window policy | Reject | Automated |
| 16 | Healthy readiness | Pass | Automated |
| 17 | Missing evidence | Fail closed | Automated |
| 18 | Backup not tested | Block release | Automated |
| 19 | Active Sev1 | Block release | Automated |
| 20 | Fast burn | Block release | Automated |
| 21 | Insufficient SLI samples | Block release | Automated |
| 22 | Missing burn evidence | Block release | Automated |
| 23 | Invalid fixture | Reject | Automated |
| 24 | CLI dry-run | No side effects | Automated |
| 25 | Offline evaluation | Structured JSON | Automated |
| 26 | Collector outage | Restore telemetry | Guided |
| 27 | PostgreSQL replica lag | Review failover and RPO | Guided |
| 28 | Elasticsearch disk IOPS saturation | Correlate query SLI and storage | Guided |
| 29 | MongoDB election | Preserve quorum | Guided |
| 30 | Kubernetes rollout regression | Controlled rollback | Guided |
| 31 | Kafka consumer freshness | Check lag and ISR | Guided |
| 32 | Snowflake pipeline delay | Evaluate freshness SLI | Guided |

## Troubleshooting and runbooks

**SLO burn:** validate eligible traffic, source freshness and error classification; correlate deployments, dependencies and incident timeline; pause risky changes.

**Readiness blocked:** inspect each failed check and collect fresh evidence; do not bypass through unreviewed CLI flags.

**Missing telemetry:** mark SLI unknown, restore exporters and scrape targets, validate timestamps and completeness.

**Database pressure:** check replication, backups, disk IOPS, lock waits and failover prerequisites before remediation.

**Rollback:** follow approved rollout history and service-specific restore procedures; verify user-visible SLIs after rollback.

## 100-point final assessment

| Competency | Points |
|---|---:|
| Availability and latency SLIs | 20 |
| Error budgets and burn-rate alerts | 20 |
| Readiness and release safety gates | 20 |
| Automated tests and incident drills | 15 |
| SRE/DBRE reliability scenarios | 15 |
| Troubleshooting and runbooks | 10 |
| **Total** | **100** |

**Pass target:** ≥90/100, independently executed tests and an operator-reviewed incident/release runbook.

**Validation:** GitHub source and tests are published; committed runtime tests, CI and real telemetry integration have not been executed during publication.
