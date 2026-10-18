# Chapter 088 — Python Incident Response, Diagnostics and Automated Remediation

**Part 09 — DevOps, SRE and Automation | Chapter 088 of 120 | Python 3.11+**

## Mission and learning objectives

Build a safety-first incident-response pipeline that collects redacted diagnostics, correlates signals, proposes a remediation, requires explicit approval, verifies preconditions, applies a narrowly allowlisted **lab-only** action, records a durable audit trail, and supports idempotent retries and recovery. The project uses standard-library Python and synthetic incident fixtures. No production services are changed.

[Hands-on lab](labs/088-incident-response-diagnostics-remediation-sre-dbre-lab.md) · [Standalone executable project](labs/088/README.md).

## 1. Incident automation architecture

\`\`\`text
Alert / ticket / operator
  -> validated incident ID, service, scope, severity
  -> bounded diagnostic collection (redact credentials/PHI)
  -> correlation by service, incident window and evidence
  -> rule-based candidate action + confidence / blast radius
  -> policy: allowlist + approval + expiry + change window
  -> dry-run plan -> explicit apply
  -> precondition recheck + durable idempotency key
  -> bounded action execution -> postcondition verification
  -> append-only audit events + rollback/escalation
\`\`\`

**Safety invariant:** a diagnostic signal is never sufficient authorization to change a production system. The chapter lab's only automated action writes a marker into a sandbox directory, demonstrating the control plane without touching external systems.

## 2. Diagnostic collection

Collect the minimum evidence needed to distinguish symptom from cause: service status, time window, deployment version, saturation, error rate, dependencies, database health, and recent changes. Use timeouts and record budgets. Preserve UTC timestamps, provenance, trace/incident IDs and explicit gaps in evidence. Redact tokens, authorization headers, DSNs, private keys and sensitive patient/customer data. A redaction regex is a teaching control, not a substitute for structured allowlisting and data classification.

Python tooling:
- \`pathlib\` for safe lab paths and evidence artifacts; \`json\` for structured events.
- \`subprocess.run(..., shell=False, timeout=..., check=...)\` for narrowly allowlisted diagnostics only; never concatenate user-supplied shell commands.
- \`logging\` or JSONL audit events for traceability; never log secret-bearing environment variables.
- \`psutil\` and cloud SDKs can supply metrics, but permissions and resource budgets still apply.

## 3. Correlation and causality

Correlate by service, incident ID, time window and dependency. A spike in disk usage alongside query latency is a **hypothesis**, not proof of storage root cause. Compare baseline and post-change data, check whether the signal precedes the symptom, and inspect confounders. For example, Elasticsearch search latency and queue depth may rise together due to storage IOPS pressure; a separate load change may drive both. Do not automate an index deletion from that correlation.

A deterministic scoring function can rank candidate diagnoses. Scores are advisory; explain supporting evidence and missing data. Distinguish event correlation, root-cause hypothesis, approved remediation and verified recovery.

## 4. Policy and approval gates

Each candidate action requires:
1. A narrowly defined action name, service and environment.
2. Explicit scope and blast-radius estimate.
3. A change ticket or incident ID and authorized approver.
4. A time-bounded approval bound to the **exact plan digest**.
5. Fresh precondition checks immediately before apply.
6. Idempotency and audit evidence.
7. Verification and rollback/escalation.

Never treat an approval flag supplied by an untrusted client as authentication. The lab's \`--approval\` string is a **simulation**; production requires independently authenticated identity, separation of duties, a signed/recorded approval and an authorization service.

## 5. Idempotency and durable state

An idempotency key identifies a logical operation across retries. Persist the key and plan digest before executing; distinguish \`planned\`, \`approved\`, \`running\`, \`succeeded\`, \`failed\` and \`unknown\`. If a worker crashes after an external side effect but before recording success, a retry can duplicate the action unless the downstream system supports conditional writes or reconciliation. The lab uses exclusive marker-file creation as a local idempotent side effect; it is **not** a distributed exactly-once guarantee.

Use SQLite/PostgreSQL with unique keys and transactional claims for a real coordinator; distributed workers need leases, fencing tokens and recovery of unknown outcomes.

## 6. Dry-run and change safety

Dry-run is the default. It validates the plan and emits a redacted JSON proposal without performing remediation. An explicit \`--apply\` must pass an approved plan digest and a scoped approval. All actions are allowlisted; arbitrary shell commands, Kubernetes deletion, database restart, cloud mutation and credential rotation are excluded from the lab. Enforce a hard execution budget and an emergency stop.

## 7. SRE/DBRE production scenarios

| Platform | Diagnostics | Why remediation needs approval |
|---|---|---|
| PostgreSQL | replication lag, lock waits, connection saturation, WAL, disk | Restart/failover can lose availability or data |
| Elasticsearch/OpenSearch | search/fetch latency, rejections, shard allocation, IOPS | Deleting indices or force-merging is irreversible or costly |
| MongoDB | replication lag, WiredTiger cache, elections, disk | Stepdown and reconfig can affect quorum |
| Kafka/MSK | ISR, under-replicated partitions, consumer lag | Broker restart can amplify partition unavailability |
| Kubernetes/EKS/AKS | Pod events, probes, rollout, node pressure | Blind restarts can worsen stateful incidents |
| Snowflake | queueing, warehouse usage, task failures | Warehouse resizing and task changes affect costs/data freshness |

## 8. Retry and failure classification

Retry only transient, idempotent reads or actions with verified downstream idempotency. Use capped exponential backoff with jitter and total deadlines; honor Retry-After. Do **not** retry authorization errors, invalid scopes, schema failures or ambiguous external side effects blindly. A timeout during apply produces \`unknown\` until reconciliation proves whether the action occurred.

## 9. Audit logging and security

Audit each state transition with UTC time, incident ID, service, action, plan digest, actor reference, result and evidence checksum. Use append-only protected storage with restricted access and retention. JSONL on a local filesystem is educational; a production audit store needs tamper evidence, durable writes, access control, central retention and reconciliation. Never include raw secrets, kubeconfigs, DSNs, patient records or token contents.

## 10. Incident simulations

1. Invalid incident ID; 2. invalid service; 3. unauthorized action; 4. stale diagnostic; 5. conflicting evidence; 6. missing diagnostic; 7. secret-bearing evidence; 8. dry-run side-effect check; 9. missing approval; 10. approval-plan mismatch; 11. expired approval; 12. precondition drift; 13. duplicate apply; 14. concurrent apply race; 15. process crash before marker; 16. process crash after marker; 17. audit-write failure; 18. disk full; 19. path traversal; 20. tampered marker; 21. false-positive correlation; 22. dependency outage; 23. rollback failure; 24. alert storm; 25. API 429; 26. PostgreSQL failover risk; 27. Elasticsearch index-deletion risk; 28. MongoDB quorum risk; 29. Kubernetes rollout regression; 30. Snowflake cost spike.

## 11. Troubleshooting and runbooks

**Triage:** establish incident commander, impact and start time; collect sanitized evidence and verify alert freshness.

**Approval failure:** stop; confirm authenticated approver, exact plan digest, scope, expiry and separation of duties. Never bypass.

**Duplicate action:** inspect idempotency record and downstream state; do not blindly re-execute.

**Ambiguous outcome:** mark unknown, reconcile state, inspect durable audit and require human escalation before retry.

**Unexpected side effect:** stop automation, isolate credentials, invoke approved rollback, verify service SLO and document RCA.

**Database incident:** preserve backups and quorum; never automate destructive cleanup or primary restart from a single metric.

## 12. Assessment

The [lab](labs/088-incident-response-diagnostics-remediation-sre-dbre-lab.md) provides real Python files, a JSONL audit trail, simulated approvals, a sandbox-only idempotent action, offline tests, incident drills and a 100-point final assessment. **Publication is not runtime or production certification.**

**Next proposed:** Chapter 089 — Python Reliability Engineering, SLO Automation and Operational Readiness.
