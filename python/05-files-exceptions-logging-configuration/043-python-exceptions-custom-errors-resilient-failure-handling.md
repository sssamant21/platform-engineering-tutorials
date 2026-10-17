# Chapter 043 — Python Exceptions, Custom Errors and Resilient Failure Handling

**Part 05 — Files, Exceptions, Logging and Configuration | Python 3.10+ | 4–5 hours**

## Learning objectives

Design explicit exception hierarchies, preserve root causes with exception chaining, classify retryable and permanent failures, enforce retry budgets and deadlines, apply exponential backoff, avoid unsafe retries, and implement deterministic SRE/DBRE resilience tests.

## 1. Exception hierarchy and semantics

Python exceptions derive from `BaseException`; application failures normally derive from `Exception`. Do not broadly catch `BaseException`, which includes process termination and interrupts. Catch only exceptions you can meaningfully handle. Keep error messages sanitized: never embed passwords, access tokens, patient information, or raw connection strings.

```python
class OperationalError(Exception):
    pass

class TransientError(OperationalError):
    pass

class PermanentError(OperationalError):
    pass

class DeadlineExceeded(OperationalError):
    pass
```

An explicit hierarchy supports stable classification and actionable runbooks. Preserve machine-readable fields (service, category, attempts) separately from the human-readable message.

## 2. try, except, else, finally

`except` handles selected failures; `else` executes only when no exception was raised; `finally` executes on normal and exceptional exits. Prefer `with` for resource ownership. A `return` inside `finally` can accidentally suppress an exception—avoid it.

## 3. Exception chaining

```python
try:
    parse_config()
except ValueError as exc:
    raise OperationalError("invalid operational configuration") from exc
```

Chaining preserves the original traceback for diagnostics. The public error should avoid exposing raw sensitive inputs. Use `raise` (not `raise exc`) when re-raising an unchanged exception.

## 4. Error taxonomy

| Category | Examples | Retry? |
|---|---|---|
| Transient | Short-lived service overload, retryable connection reset | Bounded and conditional |
| Permanent | Invalid schema, unauthorized, bad configuration | No |
| Timeout | Request exceeded a deadline | Depends on idempotency and remaining budget |
| Exhausted | Attempts consumed | No further automatic retries |

HTTP 429/503 and throttling may be retryable if the API contract permits. A timeout does not prove a write failed; it may have completed remotely.

## 5. Exponential backoff and budgets

For retry number `n`, bounded exponential backoff is `min(max_delay, base_delay × 2^(n-1))`. Production systems should add randomized jitter, respect `Retry-After`, limit concurrency, and enforce **one overall deadline**. A retry count alone is not a time budget.

The lab uses a **virtual clock** and deterministic backoff to make tests reproducible; it is not a real wall-clock timeout or cancellation mechanism.

## 6. Idempotency and safe retry design

Retries of reads are often safer than retries of writes, but even reads can overload dependencies. For mutation operations, use a server-supported idempotency key, transaction semantics or a reconciliation strategy. Do not retry index deletion, backups, failovers, schema changes, or Kubernetes mutations without explicit approval and documented safety guarantees.

## 7. Architecture

```text
synthetic scenario JSON
        |
 schema/allowlist validation
        |
   SyntheticProbe
        |
  RetryPolicy + VirtualClock
        |
  classified Outcome
        |
 deterministic JSON report
```

The lab simulates PostgreSQL replication checks, Elasticsearch search checks, Kafka consumer checks, and Redis cache checks. It makes no network calls or infrastructure changes.

## 8. Failure handling pitfalls

- Swallowing exceptions makes incidents appear healthy.
- Retrying validation failures wastes time and can amplify outages.
- Unbounded retries can cause cascading failure and retry storms.
- Treating all timeouts as safe-to-retry can duplicate writes.
- Logging entire exception objects can expose secrets.
- A virtual-clock deadline does not stop a blocked production network call.
- Shared retry budgets should be enforced across nested calls; avoid multiplicative retries.
- Circuit breakers and bulkheads can complement—but not replace—timeouts and bounded retries.

## 9. Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| Retry storm | Unbounded or nested retries | Set attempt/time budgets, jitter, load shedding |
| Authentication errors retried | Incorrect classification | Mark permanent |
| Deadline exceeded | Slow dependency or backoff | Inspect latency, remaining budget |
| Duplicate writes | Non-idempotent retry | Stop writes, reconcile state, use idempotency keys |
| Root cause missing | Exception replaced without chaining | Use `raise ... from exc` |
| Error marked healthy | Broad catch and default success | Fail closed |
| Backoff tests flaky | Real sleeping | Inject virtual clock |
| Secrets in error logs | Unsanitized exception text | Redact and allowlist fields |

## 10. Production runbooks

**Transient dependency incident:** establish impact and SLOs, check saturation and throttling, cap retry rate, verify jitter and deadlines, disable aggressive retries if they amplify load.

**Permanent error incident:** stop retries, verify schema/permissions/configuration, preserve sanitized evidence, repair through approved change and validate before replay.

**Timeout incident:** determine whether the operation may have completed remotely; reconcile state before retrying mutations, check end-to-end deadline and upstream/downstream timeout alignment.

**Retry exhaustion:** surface degraded status, preserve attempts and failure category, escalate through on-call policy; do not hide failures.

**Deployment rollback:** use a synthetic replay fixture, confirm retry budgets and nonretryable cases, deploy behind controlled rollout, revert on elevated error rate or latency.

## 11. Hands-on lab

[Chapter 043 — Resilient SRE/DBRE Probe and Retry Lab](labs/043-resilient-sre-dbre-probe-retry-lab.md) includes a complete offline Python implementation, virtual clock, JSON CLI, **46 automated tests**, failure injection and runbooks. All 46 tests were executed successfully in the authoring Linux sandbox.

**Next: Chapter 044 — Python Logging, Structured Logs and Operational Observability.**
