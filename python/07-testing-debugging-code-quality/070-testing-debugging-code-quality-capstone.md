# Chapter 070 — Testing, Debugging and Code Quality Capstone

**Part 07 — Testing, Debugging and Code Quality | Final capstone | Python 3.11+ | 12–16 hours**

## Mission
Deliver an auditable, failure-resistant SRE/DBRE telemetry validator and its production quality gates. The system processes **synthetic** PostgreSQL replication lag, Elasticsearch search latency and Kafka consumer lag. It must reject malformed inputs, classify thresholds, deduplicate by source, emit sanitized structured logs, provide bounded metrics, support profiling, and pass layered testing and security gates. No real database, cluster, credentials or destructive operation is used.

## Learning outcomes
- Build a deterministic Python service with typed immutable models and strict validation.
- Combine \`unittest\`, \`pytest\`, mocks, fixtures, parameterization and Hypothesis properties.
- Use dependency injection for telemetry sinks and test doubles; isolate failures without real cloud resources.
- Profile with \`cProfile\`, \`pstats\`, \`tracemalloc\`; debug locally with \`pdb\`, \`breakpoint()\`, \`traceback\`, \`faulthandler\`.
- Emit structured JSON logs with correlation IDs and redacted/allowlisted fields.
- Validate Ruff, mypy, Bandit, pip-audit, secrets scanning and CI controls.
- Perform incident simulations and document safe remediation, rollback and audit evidence.

## System design
\`\`\`text
synthetic SRE/DBRE telemetry
     |
     v
strict schema, identifier and finite-value validation
     |
     v
typed immutable Reading -> severity classifier
     |
     v
per-batch duplicate guard -> deterministic summary
     |
     +--> structured JSON event (no raw payloads)
     +--> bounded engine/severity counters
     +--> injected clock -> duration metric
     +--> injected sink -> mock and failure tests
     |
     v
unittest + pytest + Hypothesis
     |
     v
Ruff + mypy + Bandit + pip-audit + secret scan
     |
     v
trusted CI gate -> release review -> rollback plan
\`\`\`

## Acceptance requirements
| ID | Control | Evidence |
|---|---|---|
| C01 | Strict schema, types, units and bounded batch | Unit tests and negative fixtures |
| C02 | Correct warning/critical boundaries | Parameterized tests |
| C03 | Stable deterministic summaries | Permutation and property tests |
| C04 | No secrets or arbitrary payloads in logs | Canary redaction tests |
| C05 | Bounded metric labels | Metrics assertions |
| C06 | Sink failures do not falsify processing results | Mock failure injection |
| C07 | Python profiling and memory instrumentation | Captured local reports |
| C08 | Static quality and typing | Ruff/mypy logs |
| C09 | Security and dependency gates | Bandit/pip-audit/secrets results |
| C10 | CI fail-closed, review and rollback | Workflow plus runbook |

## 1. Test strategy
Unit tests run without third-party services. Pytest tests add fixtures, parametrization and mock injection. Hypothesis generates valid/invalid telemetry and checks invariants: total equals sum of severity counts, output is independent of input order, threshold classification is monotonic, and rejected batches never produce a success summary. Hypothesis shrinking reduces a counterexample to a minimal failing case. Keep examples reproducible by preserving failing seeds and settings in incident evidence.

## 2. Integration testing
The capstone's integration boundary is a real in-process \`logging.StreamHandler\` and a JSON-lines sink with real serialization. External PostgreSQL/Redis container integration is intentionally **optional**, because this capstone validates a synthetic service rather than connecting to production systems. For real driver integration, execute Chapter 065's explicitly opt-in disposable Testcontainers lab on a trusted Docker runner. Do not misrepresent mocked integrations as real PostgreSQL or Redis tests.

## 3. Mocking and dependency injection
Inject a metric sink, logger and monotonic clock. Mock failures in the logger/sink and assert the defined policy: processing returns the computed summary, while observability failures are recorded as local diagnostics and do not silently corrupt results. Production implementations must surface instrumentation-drop counters or a protected fallback logger.

## 4. Debugging and profiling
Use \`python -m pdb\` and temporary \`breakpoint()\` only on a disposable local process. \`traceback\` and \`faulthandler\` can expose paths and sensitive data; store dumps securely. Use \`cProfile\` and \`pstats\` for CPU function-call analysis; use \`tracemalloc\` for Python allocation tracking, not total RSS. Compare against OS/cgroup memory and workload baselines.

## 5. Structured observability
Use event codes rather than untrusted messages, UTC timestamps, validated correlation IDs, fixed metric label dimensions (engine and severity) and monotonic durations. Avoid request IDs as metric labels. The lab uses an in-memory counter sink, not a production Prometheus/OpenTelemetry exporter.

## 6. Quality and security gates
Ruff lint and format checks enforce code hygiene; mypy checks typed contracts; Bandit checks common security anti-patterns; pip-audit checks declared dependencies against advisories; a dedicated secrets scanner checks Git content. None alone proves security. Pin dependencies and GitHub Actions to reviewed immutable revisions for production, restrict workflow permissions, and never expose secrets to untrusted pull requests.

## 7. Failure injection matrix
| Failure | Expected behavior |
|---|---|
| NaN, Infinity, boolean, negative | Reject before classification |
| Unknown metric/unit/engine | Reject with sanitized error |
| Duplicate engine/service | Reject entire batch |
| Oversized batch | Reject before processing |
| Boundary off-by-one | Parameterized test failure |
| Sink raises exception | Summary remains deterministic; local failure marker |
| Logger interpolation attack | No raw user payload emitted |
| Correlation ID injection | Reject unsafe ID |
| Profiling overhead | Benchmark in bounded synthetic environment |
| Ruff/mypy regression | CI blocks promotion |
| Bandit finding | Triage and remediate before release |
| Vulnerable dependency | Block promotion pending risk review |
| Advisory network outage | Fail closed; do not report clean |
| Secret canary committed | Scanner blocks promotion and response runbook applies |

## 8. Production runbooks
**Alert misclassification:** stop release, reproduce boundary fixture, fix policy and rerun property/regression tests; restore prior policy if needed.

**Missing observability:** verify handler configuration, metric cardinality and exporter health, inspect fallback/drop counters and restore known-good instrumentation.

**CPU/memory regression:** collect short sanitized profiles, compare baselines, cap workload and roll back offending change.

**Critical dependency CVE:** freeze promotion, identify affected version and transitive chain, patch or obtain time-bound exception, rebuild and retest.

**Secret exposure:** revoke/rotate, restrict affected logs/artifacts, investigate Git history and document impact.

**CI gate bypass:** restore branch protection, invalidate unreviewed artifacts, rerun trusted gates and require approvals.

**Rollback:** restore known-good commit and approved lockfile, rerun all gates, verify service health and record change approval.

## 9. Lab and grading
[Chapter 070 — Testing and Code Quality Enterprise Capstone Lab](labs/070-testing-debugging-code-quality-capstone-sre-dbre-lab.md) contains complete application code, unittest/pytest/Hypothesis tests, configuration, a fail-closed CI template, profiling instructions, 15 incident drills, runbooks and a 100-point acceptance assessment.

**Part 07 completion:** Chapters 061–070. **Next:** Chapter 071 — APIs, Networking and Databases (verify final chapter title in the master curriculum).
