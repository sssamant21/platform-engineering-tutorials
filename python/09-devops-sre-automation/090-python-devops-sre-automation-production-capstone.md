# Chapter 090 — Python DevOps/SRE Automation Production Capstone

**Part 09 — DevOps, SRE and Automation | Chapter 090 of 120 | Part 09 final capstone | Python 3.11+**

[Executable lab](labs/090-devops-sre-automation-production-capstone-lab.md) · [Standalone source and tests](labs/090/README.md)

## Learning outcomes

Integrate infrastructure inventory, synthetic monitoring, SLI/SLO and error-budget evaluation, incident correlation, an approval-gated automation plan, dry-run by default, idempotency, audit logging, bounded failure handling and operational readiness into a single executable SRE/DevOps/DBRE workflow. Distinguish educational local safeguards from production-grade controls.

## 1. Architecture and trust boundaries

\`\`\`text
synthetic inventory + metrics + request events
      | schema validation, freshness, provenance
      v
  SLI/SLO and burn-rate calculation
      |       incident signal correlation
      +------------+
                   v
        incident assessment and immutable plan
                   |
         dry-run (default, no writes)
                   |
       authenticated approval REQUIRED in production
                   |
         lab approval simulation only
                   |
        exact digest + expiry + allowlist
                   |
        sandbox marker (atomic exclusive create)
                   |
      append-only local JSONL audit (educational)
                   |
       verification and readiness report
\`\`\`

The code uses **only synthetic telemetry and inventory**. It does not access AWS, Azure, GCP, Kubernetes, Docker, databases, ticket systems, production metrics, or external incident managers. The sole apply action creates a marker file inside a user-created disposable sandbox. It cannot restart a Pod, delete an index, fail over a database, or modify infrastructure.

### Component contracts

| Component | Input | Output | Safety |
|---|---|---|---|
| Inventory | Synthetic resource records | Health and ownership summary | Bounded, read-only |
| Monitoring | CPU, memory, disk samples | Pressure classification | Percent validation |
| Reliability | Eligible request outcomes | Availability, error budget, burn | No-traffic = unknown |
| Incident correlation | SLI + infrastructure evidence | Candidate incident and rationale | Hypothesis, not causality |
| Planner | Service, incident, candidate | Canonical plan + SHA-256 digest | Action allowlist |
| Gate | Plan, simulated approval, expiry | Permit/deny | Fail closed |
| Executor | Approved plan + sandbox | Exclusive local marker | Idempotent local side effect |
| Audit | Plan digest, event, actor reference | JSONL evidence | No credentials |
| Readiness | Monitoring, budget, backups, owner, rollback | Go/no-go advisory | Missing evidence blocks |

## 2. Inventory and monitoring

Inventory must be scoped by environment and namespace, validated against an allowlist and bounded by resource count. A resource marked unhealthy does not itself authorize remediation. Host CPU, memory and disk-space utilization are useful symptoms but do not measure query latency, filesystem IOPS or data integrity. Real Kubernetes inventories require least-privilege list/watch and correct pagination. Real Docker socket access is privileged. The capstone deliberately avoids those access paths.

## 3. SLI, SLO and error budget

Availability SLI = successful eligible requests / all eligible requests. For target \`T\`, allowed failures = \`N × (1-T)\`; remaining = allowed - observed bad requests. Burn rate = observed failure fraction / allowed failure fraction. A negative remaining budget means overspend. Unknown telemetry and zero eligible traffic must **not** be interpreted as perfect reliability.

For production, implement durable windows, late-event reconciliation, deduplication by event ID, minimum sample sizes and multiwindow/multiburn alert rules. This lab uses a single synthetic window with explicit minimum-event checks and a demonstration burn threshold.

## 4. Incident correlation

The capstone combines SLI degradation, high CPU/disk, and inventory health to produce a *candidate* incident. Correlation is not proof of root cause. An Elasticsearch search regression with high disk utilization could be caused by IOPS saturation, excessive query concurrency, or an unrelated dependency. Database restart, force merge, index deletion, replica-set reconfiguration and cloud scaling remain manual, separately authorized workflows.

## 5. Approval, idempotency and audit

An action is represented by a canonical JSON plan and SHA-256 digest. Dry-run prints the digest and performs zero writes. Apply requires a matching digest, simulated approver and unexpired approval, and targets only a local sandbox. The marker is created using \`O_CREAT|O_EXCL\`; retrying the same plan returns \`already-applied\`, while a conflicting plan is rejected. The JSONL audit records applied and duplicate events with incident ID and digest.

**Production gaps:** a CLI approver string is not authenticated authorization; JSONL is not tamper-evident, durable distributed audit; a local exclusive marker does not guarantee exactly-once cloud or database writes; a filesystem path check is not a security boundary against a malicious local actor. Production implementation requires signed approvals, separation of duties, a transactional idempotency ledger, fencing/reconciliation, immutable audit, policy-as-code, rate limiting, bounded retries, and postcondition SLO verification.

## 6. Reliability release gate

Require fresh monitoring, sufficient request samples, no active high-severity incident, nonexhausted error budget, tested rollback, owner assignment, paging route, backup/restore evidence and capacity review. Missing or invalid evidence blocks the release. The result is **advisory**: do not wire it directly to production deploy permissions without authenticated inputs and governance.

## 7. Production incident simulations

1. Healthy inventory; 2. missing owner; 3. unhealthy workload; 4. CPU saturation; 5. memory pressure; 6. disk full; 7. NaN metric; 8. stale sample; 9. no traffic; 10. low traffic; 11. error budget exhausted; 12. high burn; 13. incorrect SLI denominator; 14. 5xx spike; 15. false-positive correlation; 16. missing rollback; 17. backup restore untested; 18. paging route broken; 19. active Sev1; 20. unauthorized action; 21. missing approval; 22. mismatched plan digest; 23. expired approval; 24. duplicate apply; 25. conflicting plan; 26. tampered marker; 27. audit write failure; 28. sandbox missing; 29. concurrent workers; 30. external side effect ambiguous; 31. PostgreSQL replication incident; 32. Elasticsearch storage IOPS bottleneck; 33. MongoDB election; 34. Kafka lag; 35. Kubernetes rollout; 36. Snowflake pipeline freshness.

## 8. Troubleshooting matrix

| Symptom | Validate | Response |
|---|---|---|
| Readiness blocked | evidence freshness, budget, owner, rollback | Repair evidence or halt change |
| High burn | SLI denominator, window, deployment history | Page owner, pause risky rollout |
| Metrics healthy but users impacted | telemetry completeness, app SLI, dependencies | Investigate blind spots |
| Approval rejected | exact digest, actor, expiry, scope | Reapprove through proper authority |
| Duplicate apply | marker and digest | Treat same plan as idempotent; reject conflict |
| Unknown execution result | downstream state, durable ledger | Stop retries and reconcile |
| Database/storage pressure | replication, IOPS, locks, backup | Use owner-approved DBRE runbook |

## 9. Production runbooks

**Triage:** establish impact, UTC timeline, incident commander and owner; collect redacted evidence; verify telemetry freshness and recent changes.

**SLO burn:** validate eligible traffic, compare short and long windows, stop risky deployments, assess rollback and verify recovery.

**Approval gate:** verify independently authenticated approver, exact plan digest, expiry and separation of duties. Never use the lab's CLI approval as production authentication.

**Idempotency conflict:** halt, compare operation intent and downstream state, escalate; do not overwrite a prior marker.

**DBRE escalation:** preserve backups, replication quorum and RPO/RTO; do not blindly restart primaries or delete indices.

**Post-incident:** document cause vs correlation, corrective actions, alert quality, evidence gaps, and SLO/error-budget policy changes.

## 10. Capstone acceptance

[Hands-on lab](labs/090-devops-sre-automation-production-capstone-lab.md) includes real standalone Python source and offline unit tests, incident drills, a CI template and a 100-point acceptance rubric. Production readiness is **not** conferred by passing the offline lab.

**Part 09 completed by publication of Chapters 081–090.** Next: Chapter 091 — Python Kubernetes API and Cloud-Native Platform Engineering (proposed; Part 10).
