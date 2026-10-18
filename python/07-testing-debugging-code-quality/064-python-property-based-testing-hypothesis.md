# Chapter 064 — Python Property-Based Testing and Hypothesis

**Part 07 — Testing, Debugging and Code Quality | Python 3.11+**

## Learning objectives
Use Hypothesis strategies to generate structured SRE/DBRE telemetry, assert invariants, inspect shrinking, test stateful models, fuzz malformed data, exercise floating-point boundaries, and add safe CI quality gates.

## Theory
Example tests check selected inputs; property tests express contracts across generated inputs. Use `@given` with `st.integers`, `st.floats`, `st.text`, `st.sampled_from`, `st.lists` and `@st.composite`. Constrain valid inputs by construction; use separate invalid-input strategies to check rejection. Hypothesis shrinks failing inputs into smaller counterexamples. Preserve important counterexamples using `@example` and regression tests. The example database is a convenience, not a CI reproducibility guarantee.

Core invariants: severity counts sum to total; reversing input preserves a sorted report; increasing a nonnegative metric cannot lower severity; valid records round-trip; malformed records fail closed. Use `math.nextafter` to test values immediately below floating-point boundaries. Test stateful upsert/remove operations with `RuleBasedStateMachine`, checking invariants after each transition. No randomized test should modify production infrastructure.

## SRE/DBRE architecture
```text
Hypothesis strategies -> synthetic PostgreSQL/Elasticsearch/Kafka telemetry
  -> strict parser -> severity classifier -> deterministic report
  -> generated invariants + stateful model + shrinking
  -> CI test gate -> incident runbook
```

| Engine | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag seconds | 30 | 120 |
| Elasticsearch | search_latency milliseconds | 200 | 500 |
| Kafka | consumer_lag messages | 1000 | 10000 |

These are synthetic thresholds, not production SLO recommendations.

## Troubleshooting
- **Excessive filtering:** build valid composite records directly instead of discarding most examples.
- **Flaky failures:** isolate mutable state, remove wall-clock sleeps, pin dependencies and save regression examples.
- **Slow generation:** bound list sizes, cap examples and use an external CI job timeout.
- **Incorrect property:** compare the invariant against the contract, not merely the current implementation.
- **Floating-point surprises:** explicitly handle NaN, Infinity, negative values and exact threshold neighbors.
- **Stateful mismatch:** replay the minimized operation sequence against a verified reference model.

## Production runbooks
**Generated test regression:** preserve minimized input, block deployment, reproduce in isolated CI, fix code, add `@example` and rerun.

**Fuzz safety incident:** disconnect live clients, audit credentials and side effects, rerun against synthetic adapters.

**Coverage gap:** combine property tests with branch coverage and targeted negative cases.

**Rollback:** restore last accepted release, rerun counterexamples and verify change approval.

## Hands-on lab
[Chapter 064 — Hypothesis SRE/DBRE Lab](labs/064-property-based-testing-hypothesis-sre-dbre-lab.md) includes executable Python, generated tests, a stateful model, incident simulations, runbooks and a 100-point acceptance rubric.

**Next:** Chapter 065 — Python Integration Testing and Testcontainers (provisional).
