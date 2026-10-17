# Chapter 039 — Context Managers, Resource Management and Exception-Safe Operations

**Part 04 — Object-Oriented Programming | Python 3.10+ | 3–4 hours**

## Objectives

Understand `with` statement semantics, `__enter__`/`__exit__`, exception propagation, `contextlib.contextmanager`, `closing`, `nullcontext`, `ExitStack`, resource ownership, cleanup ordering, exception-safe temporary files, and reliable SRE/DBRE operational workflows. Implement a synthetic maintenance preflight with a guaranteed audit trail.

## 1. Why deterministic cleanup matters

DBRE and SRE tools acquire files, locks, sessions, temporary workspaces and API connections. Failure during validation or processing must not leak resources or silently suppress the original incident. Context managers scope ownership explicitly and run cleanup on normal completion and exceptions.

```python
with open("fixture.json", encoding="utf-8") as handle:
    data = handle.read()
```

The file closes whether parsing succeeds or raises. The lab never connects to a live database or performs maintenance.

## 2. Class-based context managers

```python
class ManagedResource:
    def __enter__(self):
        self.opened = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.opened = False
        return False
```

The `__exit__` method receives exception information when the body raises. Returning a truthy value suppresses that exception; return `False` or `None` to propagate it. An exception raised in `__enter__` does **not** trigger that manager's `__exit__`: use internal `try/finally` or `ExitStack` during multi-step acquisition.

## 3. Generator-based managers with contextlib

```python
from contextlib import contextmanager

@contextmanager
def audit_scope(events):
    events.append("enter")
    try:
        yield events
    finally:
        events.append("exit")
```

A `@contextmanager` generator must yield exactly once. Exceptions from the `with` body are thrown into the generator at the yield point. To avoid swallowing exceptions, re-raise them or use a `finally` block without suppression.

## 4. ExitStack and partial acquisition

`contextlib.ExitStack` registers cleanup callbacks or nested context managers dynamically. Cleanup runs in last-in, first-out order. Use it when the number of resources depends on configuration.

```python
from contextlib import ExitStack

with ExitStack() as stack:
    handles = [stack.enter_context(open(path, encoding="utf-8")) for path in paths]
    # all previously opened handles close if a later open fails
```

For `AsyncExitStack`, see asynchronous programming chapters; do not mix synchronous and asynchronous resource protocols inadvertently.

## 5. Temporary files and atomic publication

For operational reports, write to a temporary file in the destination directory, flush and `fsync` as appropriate, then `os.replace` to atomically replace the destination on a supported local filesystem. Atomic rename does not guarantee durability across power failure or remote filesystems; production deployments must account for filesystem semantics. Do not claim a report is committed before the rename succeeds.

The lab uses **in-memory audit sinks** and synthetic fixtures only, so there are no filesystem mutations beyond reading the supplied fixture.

## 6. Exception taxonomy

Catch only errors that you can handle. Preserve exception chains with `raise ... from exc` where helpful; do not catch `BaseException` casually. Cleanup should be idempotent and should avoid masking the primary exception. When cleanup itself can fail, log or aggregate failures with a clear policy, using `ExceptionGroup` on Python 3.11+ when appropriate.

## 7. SRE/DBRE architecture

```text
synthetic JSON fixture
        |
   validated work items
        |
   ExitStack orchestration
     /      |       \
  audit   session   guard
     \      |       /
       safe cleanup
            |
     final report JSON
```

The lab models a **dry-run maintenance preflight**, not execution: each task is evaluated as approved/rejected using an allowlist, and audit events are recorded even if a simulated task raises.

## 8. Production scenarios

| Resource | Correct ownership | Common failure |
|---|---|---|
| PostgreSQL connection | Context-managed read-only session | Connection leak after exception |
| Elasticsearch client | Explicit close/timeout | Socket exhaustion |
| Kubernetes watch | Scoped iterator and cancellation | Stale watch never terminates |
| Temporary audit artifact | Atomic write and cleanup | Partial report publication |
| File lock | Context-managed lock scope | Lock left held |
| Maintenance dry run | Explicit audit scope | Missing failure record |

Real production operations require approved change tickets, least-privilege credentials, timeouts, rollback and service-owner signoff.

## 9. Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| `__exit__` never ran | `__enter__` failed | Clean up inside acquisition |
| Exception disappeared | Truthy `__exit__` | Return `False` |
| Resource leaked | Missing registration | Use `ExitStack` |
| Cleanup in wrong order | Incorrect stack registration | Verify LIFO |
| Double close error | Non-idempotent cleanup | Track state |
| Audit incomplete | Exception before audit scope | Enter audit first |
| Cleanup masks root cause | Cleanup raises | Preserve primary error |
| Partial report | Published before validation | Validate then publish |

## 10. Production runbooks

**Leaked resource:** stop repeated executions, inspect open sessions/handles, verify enter/exit paths, add exception-injection regression test, deploy fix.

**Missing audit trail:** preserve sanitized evidence, verify audit manager enters before work, fail closed if audit sink unavailable.

**Exception suppression:** inspect `__exit__` return value and generator manager exception handling; re-raise original exception.

**Change execution safety:** dry-run first, verify owner approval, scope read-only validation, capture change ID, and do not convert preflight checks into live mutations without separate authorization.

## 11. Lab and assessment

[Chapter 039 — Exception-Safe SRE/DBRE Resource Management Lab](labs/039-exception-safe-sre-dbre-resource-management-lab.md) provides complete source, synthetic fixture, **32 unit tests**, failure injection and operational runbooks.

**Next: Chapter 040 — Object-Oriented SRE/DBRE Production Capstone.**
