# Chapter 088 — Incident Response, Diagnostics and Automated Remediation SRE/DBRE Lab

**Executable source:** [Project README](088/README.md) · [incident.py](088/incident.py) · [test_incident.py](088/test_incident.py)

## Objective and architecture

Build a safe incident-response pipeline:

\`\`\`text
synthetic diagnostics -> freshness validation -> rule-based correlation
 -> immutable plan + SHA-256 digest -> dry-run
 -> simulated scoped approval -> exclusive-create sandbox marker
 -> JSONL audit -> idempotent verification
\`\`\`

The lab is intentionally sandbox-only: no Kubernetes, database, cloud or Docker writes. The approval string is **not authenticated authorization** and must not be reused for production.

## Run the lab

\`\`\`bash
cd python/09-devops-sre-automation/labs/088
python -m compileall -q incident.py test_incident.py
python -m unittest -v test_incident.py
python incident.py --incident INC-1001 --service postgres-health
\`\`\`

The CLI defaults to dry-run with zero mutations. The project README explains how to create a disposable sandbox, simulate an approval with a matching plan digest, perform the local marker action and repeat it to demonstrate idempotency.

## Hands-on exercises

1. Collect bounded synthetic CPU, disk and error-rate diagnostics. Reject stale, future, unknown and invalid samples.
2. Correlate disk pressure and error rate to a candidate hypothesis; explain why correlation does not prove root cause.
3. Generate a plan digest and verify that modifying any plan field changes its digest.
4. Reject missing, mismatched, expired or overlong approvals.
5. Apply the allowlisted local marker operation to a disposable sandbox; verify exclusive creation and audit JSONL.
6. Retry the same plan; confirm \`already-applied\`. Change the rationale; confirm idempotency conflict.
7. Tamper with the marker; verify fail-closed behavior rather than a blind retry.
8. Demonstrate path traversal and unauthorized action rejection.
9. Review the difference between a local marker and an external operation with ambiguous outcomes.
10. Design a production replacement with authenticated approvals, transactional claims, fencing, durable audit and SLO postconditions.

## Incident simulations

| Scenario | Expected response | Type |
|---|---|---|
| Invalid incident ID or service | Reject | Automated |
| Unauthorized remediation | Reject | Automated |
| Invalid diagnostic kind/range | Reject | Automated |
| Stale or future diagnostic | Reject | Automated |
| Evidence budget exhausted | Reject | Automated |
| Disk pressure/error spike | Candidate hypothesis | Automated |
| Dry-run | No side effects | Automated |
| Missing or wrong approval | Reject | Automated |
| Expired approval | Reject | Automated |
| Invalid approver reference | Reject | Automated |
| Valid sandbox apply | One marker + audit | Automated |
| Duplicate apply | Already applied | Automated |
| Changed plan | Idempotency conflict | Automated |
| Corrupted marker | Fail closed | Automated |
| Audit symlink | Reject | Automated |
| Missing sandbox | Reject | Automated |
| Approval service outage | Stop and escalate | Guided |
| Crash after external side effect | Reconcile before retry | Guided |
| Distributed worker race | Lease, transaction and fencing | Guided |
| PostgreSQL primary outage | Preserve quorum and backups | Guided |
| Elasticsearch shard/disk pressure | No blind index deletion | Guided |
| MongoDB election | No blind stepdown | Guided |
| Kubernetes rollout regression | Approved rollback | Guided |
| Secret leak in diagnostics | Revoke, rotate and investigate | Guided |

## Troubleshooting and runbooks

**Triage:** confirm service impact, owner, UTC incident window and recent changes. Collect sanitized evidence and check its freshness.

**Approval failure:** halt and verify authenticated identity, exact digest, scope and expiry. Never bypass approval.

**Ambiguous result:** halt retries, inspect durable operation ledger and downstream state, escalate to incident commander.

**Duplicate action:** compare idempotency key and plan digest; reject conflicting operations.

**Rollback:** restore through an approved platform-specific runbook with quorum, backups and SLO validation. The lab itself changes only a disposable marker.

**Audit/security:** retain structured evidence with restricted access; never log credentials or protected health information.

## 100-point final assessment

| Domain | Points |
|---|---:|
| Diagnostic collection and correlation | 20 |
| Approval policy and secure defaults | 20 |
| Dry-run and safe sandbox execution | 15 |
| Idempotency and failure recovery | 15 |
| Audit logging and data protection | 10 |
| Automated tests and incident drills | 10 |
| Troubleshooting and runbooks | 10 |
| **Total** | **100** |

**Pass target:** 90/100 plus independent unit-test execution. Publication does not establish production readiness or authenticated approval integration.

**Validation:** The standalone Python source and tests are committed; runtime and CI verification remain pending.
