# Chapter 040 — Object-Oriented SRE/DBRE Production Capstone

**Part 04 final capstone | Python 3.10+ | Estimated 5–7 hours | Offline and read-only**

## Mission

Build a production-style, deterministic **multi-datastore reliability preflight**. A single CLI reads synthetic JSON Lines telemetry, validates each observation, classifies PostgreSQL replication lag, Elasticsearch search latency, and Kafka consumer lag, and emits a structured report. It must be extensible without rewriting orchestration, fail closed on malformed input, preserve exception context, and release resources reliably.

**Safety boundary:** This is an educational, synthetic **read-only** simulation. No database connections, network requests, Kubernetes changes, index deletion, remediation, credentials, or cloud spending.

## Learning outcomes

1. Encapsulate immutable telemetry and policy with validated frozen dataclasses.
2. Use an ABC for the controlled adapter hierarchy and a Protocol for structural report sinks.
3. Apply inheritance, `super()`, method overriding and dependency injection.
4. Use generators to stream JSONL without loading all input records into memory.
5. Use context managers and `ExitStack` for exception-safe resource ownership.
6. Expose Python object protocols for an immutable bounded incident preview.
7. Exercise classification, schema drift, failures, cleanup, sorting, and publication boundaries with automated tests.
8. Conduct a scored production-readiness assessment and incident-response game day.

## Architecture

```text
synthetic JSONL file
         |
  File context manager
         |
  JSONL generator -> schema validation -> immutable Observation
         |                                  |
         |                       Adapter ABC / subclasses
         |                       PostgreSQL / ES / Kafka
         |                                  |
         +-----------> HealthEngine <-------+
                         |
                ThresholdPolicy
                         |
                  bounded Preview
                         |
                immutable Report
                         |
                  Sink Protocol
                         |
              MemorySink / JSON CLI
```

The source reader is lazy; the aggregation stores only counters and a bounded preview. The CLI emits output **only after the entire stream has been validated**. The lab uses a memory sink to demonstrate publication isolation.

## 1. Design contracts

### Immutable domain models

`Observation` is a frozen, slotted dataclass with a normalized finite nonnegative value, an explicit unit, and a validated service identifier. Type hints alone do not validate untrusted input. Threshold policies are immutable and enforce `0 < warning < critical`.

### Controlled inheritance and `super()`

`BaseAdapter` is an ABC that owns shared validation and classification mechanics. Concrete adapters override `kind`, `unit`, and `thresholds`; each calls `super().__init__()` to preserve the common initialization invariant. The engine uses the base interface, not concrete class branches.

### Protocol-based sink

A `ReportSink` Protocol defines `publish(report)`. The engine accepts a sink via constructor injection. Protocols support structural typing; a runtime `isinstance` check is not a substitute for behavioral contract tests. The lab uses a trusted in-memory sink and tests that invalid batches never publish.

### Object protocols

A bounded immutable `IncidentPreview` supports `len()`, iteration, indexing and a sanitized `repr`. Avoid overloading operators without meaningful domain semantics.

### Generator semantics

The JSONL parser yields one validated observation at a time. It rejects oversized lines, unknown fields, non-finite numbers, wrong units, and malformed JSON. Exceptions surface while consuming the generator. The CLI owns the file with `with`, so errors still close it.

### Context manager lifecycle

`RunScope` is a class-based context manager. It records open/close and never suppresses exceptions. `ExitStack` owns it and any future resources. The audit scope uses `@contextmanager` and records success/failure. A failed run does not publish a report.

## 2. SRE/DBRE scenarios

| System | Synthetic metric | Unit | Warning | Critical |
|---|---|---|---:|---:|
| PostgreSQL | Replica lag | seconds | 30 | 120 |
| Elasticsearch | Search latency | milliseconds | 200 | 500 |
| Kafka | Consumer lag | messages | 1,000 | 10,000 |

These are **illustrative lab thresholds**, not recommended production alert values. Production policies require approved SLOs, sampling cadence, freshness, baselines, owner review and alert-routing configuration.

## 3. Failure modes and defenses

| Failure | Expected response |
|---|---|
| Malformed JSON or schema drift | Raise sanitized validation error; publish nothing |
| Wrong metric unit | Reject rather than silently convert |
| NaN, infinity, bool, negative value | Reject |
| Unknown adapter | Reject against static allowlist |
| Injected adapter failure | Propagate error; audit failure and cleanup |
| Large input | Stream records; cap line length and preview |
| Partial sink publication | Publish only after full validation |
| Duplicate identity | Allowed as time-series samples; counted individually |
| Sink failure | Propagate; do not report successful publication |
| Resource scope reused | Reject invalid lifecycle |

## 4. Operational runbooks

**Runbook A — Misclassification:** Verify metric kind, unit, thresholds, boundary inclusivity, and sample freshness. Reproduce with a synthetic fixture and add regression tests before changing production policy.

**Runbook B — Schema drift:** Preserve a sanitized failing line number, compare producer and consumer schema, stop report publication, deploy compatible parser and replay the fixture.

**Runbook C — Resource leak:** Inspect context manager enter/exit, exceptions and `ExitStack` registration. Inject a failure and assert the active counter returns to baseline.

**Runbook D — Report publication incident:** Treat the output as incomplete if any record fails. Do not emit a successful report until parsing and aggregation finish. Real sinks should use atomic publication and idempotency keys.

**Runbook E — Capacity pressure:** Inspect line-size caps, preview limit, eager `list()` calls and large retained collections. Benchmark against synthetic 100k-line input.

**Runbook F — Production adapter onboarding:** Review least-privilege identity, timeouts, retry budgets, secrets hygiene, metric units, provenance, observability, feature flags and rollback before enabling any real integration.

## 5. Incident simulations

1. PostgreSQL lag crosses the critical boundary.
2. Elasticsearch latency spikes while Kafka stays healthy.
3. An invalid unit arrives midway through a stream.
4. A reader returns an invalid value.
5. A custom adapter raises during evaluation.
6. A sink rejects publication.
7. The context manager closes after an exception.
8. A high-volume stream exceeds the bounded preview count.

Capture expected versus observed results, sanitized evidence, root cause, containment, and corrective actions for each.

## 6. Validation and release gates

```bash
python -m unittest -v test_capstone.py
python -m py_compile capstone.py cli.py
python cli.py --input sample.jsonl
```

No external dependencies are required. CI should additionally run a supported Python version matrix, static typing and security scanning when available. Unit tests prove local behavior, not real infrastructure readiness.

## 7. Acceptance assessment (100 points)

| Category | Points | Evidence |
|---|---:|---|
| Domain model validation and immutability | 15 | Boundary tests and frozen model |
| ABC inheritance and `super()` invariants | 10 | Adapter tests |
| Protocol injection and sink contract | 10 | Fake sink and no-partial-publish tests |
| Lazy streaming and bounded memory | 15 | Generator and 100k-line test |
| Context management and cleanup | 15 | Injected exception and active counter |
| Deterministic report and CLI | 10 | Golden-schema test |
| Incident simulation and troubleshooting | 10 | At least four game days |
| Security, audit and rollback runbooks | 10 | Review checklist |
| Reproducible documentation | 5 | Commands and evidence |

**Passing criteria:** At least 85/100, all mandatory safety checks, all published unit tests passing in the learner's environment, and no uncontrolled live infrastructure access.

## 8. Lab

[Chapter 040 — Integrated Object-Oriented SRE/DBRE Production Capstone Lab](labs/040-object-oriented-sre-dbre-production-capstone-lab.md) provides complete Python source, synthetic fixtures, **40 unit tests**, failure injection, acceptance exercises and runbooks.

**Part 04 complete after tutorial and lab publication. Next: Chapter 041 — Files, Paths and Filesystem Operations**, starting Part 05 — Files, Exceptions, Logging and Configuration.
