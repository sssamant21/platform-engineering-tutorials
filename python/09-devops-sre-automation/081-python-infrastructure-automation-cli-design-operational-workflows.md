# Chapter 081 — Python Infrastructure Automation, CLI Design and Operational Workflows

**Part 09 — DevOps, SRE and Automation | Python 3.11+ | SRE/DevOps/DBRE**

## Objectives
Build auditable, safe command-line automation using \`argparse\`, subprocess execution without shell injection, layered configuration, idempotent state reconciliation, dry-run previews, structured logging, bounded retries, tests and production runbooks.

## 1. Operational architecture
\`\`\`text
operator/CI -> argparse CLI -> validated config -> explicit plan
 -> policy gate / dry-run -> bounded subprocess or file action
 -> verify postcondition -> JSON audit event -> exit status
\`\`\`
A production automation tool should expose a clear desired state, preconditions, execution budget, idempotency guarantee and rollback strategy. Prefer declarative reconciliation to ad hoc command sequences. Never silently run destructive commands.

## 2. argparse and CLI contracts
Use \`ArgumentParser\` with subcommands such as \`plan\`, \`apply\` and \`status\`. Document exit codes: 0 success, 2 usage/configuration error, 3 policy violation, 4 transient dependency failure, 5 operation failed. Prefer explicit \`--apply\` for mutation; default to dry-run. Keep stdout machine-readable and diagnostics on stderr where appropriate. Support \`--json\`, \`--timeout\`, \`--max-attempts\` and scoped targets; validate bounds.

## 3. subprocess safety
Use \`subprocess.run(["program", "arg", ...], shell=False, check=True, timeout=...)\` with an explicit allowlist and a controlled environment. Do not pass user input into shell strings, \`shell=True\`, \`eval\`, or \`os.system\`. Avoid executing untrusted binaries via \`PATH\`; in production use a reviewed absolute executable path. Limit stdout/stderr capture and redact secrets. \`timeout\` terminates the direct child; process groups and descendants may need separate platform-specific cleanup. A subprocess can partially mutate state before timing out: reconcile postconditions before retry.

## 4. Configuration and secrets
Use defaults, a validated configuration file and explicit CLI overrides. Do not assume environment variables are safe: they may leak through diagnostics or process inspection. Use secret providers for credentials, least privilege and approved token rotation. Treat JSON/YAML input as untrusted and enforce schema, path constraints, maximum file size and no implicit code execution.

## 5. Idempotency and change control
A safe automation function computes a desired state, compares current state, generates a plan, and applies only necessary changes. The lab creates a marker file using atomic replace and a content hash; repeated apply is a no-op. File-level idempotency does not imply concurrent-writer safety: use locks, version checks or distributed coordination when multiple runners may operate on the same resource. Plan/apply drift should be checked immediately before mutation.

## 6. Dry-run semantics
Dry-run must not modify managed state. It may perform bounded read-only checks and produce a deterministic plan. Separate a preview from a real write path; do not call mutating APIs in plan mode. Explicit approval and a confirmation token may be required for production resources.

## 7. Structured logging and observability
Emit JSON events with timestamp, operation, target alias, outcome, duration, attempt count and correlation ID. Redact tokens, credentials, PII and command arguments. Metrics: success/error counts, p95 duration, retries, drift count, skipped/no-op count, and dependency latency. Propagate trace IDs across CI, API and infrastructure calls.

## 8. Retry and timeout policies
Retry only known transient conditions, using capped exponential backoff, jitter and a total deadline. A failed command can leave partial state; retry only after checking idempotency and the actual resource state. Do not retry permission failures, invalid arguments or destructive operations with ambiguous outcomes. Respect API rate limits and upstream circuit breakers.

## 9. Production use cases
- Kubernetes: verify deployment rollout and compare desired image digest; apply through reviewed GitOps changes.
- PostgreSQL: validate backups, replication lag and maintenance preconditions; never run \`DROP\` by default.
- Elasticsearch: inspect shard count/size and create a maintenance recommendation without deleting indices.
- Kafka/MSK: audit topic configuration and consumer lag before change.
- AWS/Azure: perform read-only inventory and scoped resource reconciliation with least privilege.
- CI/CD: publish deterministic JSON plans as approval artifacts and attach audit IDs.

## 10. Incident simulations
1. Shell injection payload supplied as target.
2. Unknown command rejected by allowlist.
3. Command times out.
4. Child process returns nonzero.
5. Missing executable.
6. Partial file write interrupted.
7. Repeat apply is a no-op.
8. Dry-run unexpectedly mutates state.
9. Config path traversal attempt.
10. Malformed JSON configuration.
11. Concurrent writers race.
12. Dependency returns 429/503.
13. Expired cloud token.
14. Kubernetes context points to production.
15. PostgreSQL replica lag breaches maintenance threshold.
16. Elasticsearch index owner approval missing.
17. Audit log includes a secret.
18. Unexpected drift between plan and apply.
19. Disk full during atomic replace.
20. Retry storm causes downstream outage.

## 11. Troubleshooting matrix
| Signal | Likely cause | Response |
|---|---|---|
| Exit 2 | Invalid CLI/config | Correct input; no mutation |
| Timeout | Hung subprocess/API | Inspect state, then bounded retry if safe |
| No-op despite change | Incorrect drift detection | Verify hashes/postconditions |
| Duplicate actions | Missing idempotency | Add stable operation key and locking |
| Permission denied | RBAC/IAM | Request scoped approval, do not bypass |
| Secret in logs | Insufficient redaction | Rotate credential and scrub logs |
| Partial apply | Interrupted write | Reconcile state, rollback or resume safely |
| High retry count | Dependency outage | Shed load and disable unsafe retries |

## 12. Runbooks
**Preflight:** verify target/environment, approved scope, least-privilege identity, dry-run plan, backup and rollback path.

**Subprocess failure:** record exit code and sanitized stderr, inspect postcondition, classify transient/permanent failure and avoid blind replay.

**Drift:** compare actual/desired state, refresh plan, require new approval when scope changes.

**Credential exposure:** revoke/rotate, restrict logs and artifacts, audit access, rerun approved canary.

**Rollback:** restore previous managed state from verified backup or reapply prior desired configuration; confirm SLO and document change.

## 13. Lab and assessment
[Chapter 081 — Safe Infrastructure CLI Automation SRE/DevOps/DBRE Lab](labs/081-safe-infrastructure-cli-automation-sre-devops-dbre-lab.md) includes executable \`argparse\` CLI, JSON config, safe subprocess execution, atomic file reconciliation, dry-run, structured logging, bounded retry, automated tests, incident drills and a 100-point assessment. No cloud or production access is required.

**Next proposed:** Chapter 082 — Python Operating System, Process and Service Automation.
