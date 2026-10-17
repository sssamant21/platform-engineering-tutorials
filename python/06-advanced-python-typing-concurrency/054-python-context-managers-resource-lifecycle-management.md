# Chapter 054 — Python Context Managers and Resource Lifecycle Management

**Part 06 — Advanced Python, Typing and Concurrency | Python 3.10+ | 6–8 hours**

## Objectives
Understand deterministic cleanup with \`with\`, implement \`__enter__\` and \`__exit__\`, use \`contextlib.contextmanager\`, \`closing\` and \`ExitStack\`, manage files and database connections safely, preserve exceptions, and implement an offline SRE/DBRE reporting workflow.

## 1. Why resource ownership matters
Operational tools open file descriptors, sockets, temporary files, database sessions, locks and telemetry exporters. Failure to release them can cause connection exhaustion, file descriptor leaks, blocked deployments and incomplete backups. Python's \`with\` statement defines a scoped lifecycle with cleanup even when the body raises.

\`\`\`python
with open("events.json", encoding="utf-8") as handle:
    text = handle.read()
# file is closed here even if the body raised
\`\`\`

Garbage collection is not a reliable substitute for explicit resource management.

## 2. The context manager protocol
\`__enter__\` acquires or exposes a resource and returns the value bound by \`as\`. \`__exit__(exc_type, exc, tb)\` runs when leaving the body. Returning a truthy value suppresses an exception; return \`False\` or \`None\` to propagate it.

\`\`\`python
class Managed:
    def __enter__(self):
        self.open = True
        return self
    def __exit__(self, exc_type, exc, tb):
        self.open = False
        return False
\`\`\`

Important nuance: if \`__enter__\` itself raises, that manager's \`__exit__\` is **not** called. Implement acquisition cleanup inside \`__enter__\` or use an \`ExitStack\` to register partial resources as they are acquired.

## 3. Generator-based context managers
\`@contextlib.contextmanager\` converts a generator that yields exactly once into a context manager. Put cleanup in \`finally\` and avoid accidentally swallowing exceptions.

\`\`\`python
from contextlib import contextmanager

@contextmanager
def lease():
    resource = acquire_resource()
    try:
        yield resource
    finally:
        resource.close()
\`\`\`

Exceptions from the body are thrown back into the generator at the \`yield\` expression. If the generator catches and does not re-raise them, they can be suppressed.

## 4. ExitStack and dynamic ownership
\`contextlib.ExitStack\` owns an arbitrary number of context managers and invokes cleanup in last-in-first-out order.

\`\`\`python
from contextlib import ExitStack
with ExitStack() as stack:
    handles = [stack.enter_context(open(path, "rb")) for path in paths]
    # all successfully entered handles are closed on exit
\`\`\`

Use \`stack.callback\` for cleanup functions and \`stack.pop_all()\` only when intentionally transferring ownership.

## 5. Closing and suppress
\`contextlib.closing(obj)\` calls \`obj.close()\` at exit for objects without context-manager support. \`contextlib.suppress\` should be used narrowly, such as ignoring \`FileNotFoundError\` during best-effort temporary cleanup. Never suppress database transaction failures, authorization failures or unexpected exceptions merely to keep a pipeline green.

## 6. Database connection versus transaction semantics
\`sqlite3.Connection\` supports \`with connection:\` as a **transaction** manager, but that context does **not** close the connection. The lab explicitly calls \`connection.close()\` in \`finally\`. The lab uses only an ephemeral \`:memory:\` SQLite database and parameterized SQL, not production PostgreSQL or other live systems.

For a real database, use a driver-specific connection/pool manager, explicitly scoped transactions, bounded timeouts, read-only credentials and tested rollback behavior. Never assume all drivers share sqlite3's context-manager semantics.

## 7. Safe filesystem reporting
The lab bounds input to 64 KiB, validates strict JSON with duplicate-key and nonfinite-number rejection, validates metric units and values, and writes a sanitized JSON report through a temporary file and \`os.replace\`.

Atomic replacement depends on filesystem semantics and does not guarantee cross-filesystem durability. The lab is intended for a trusted private output directory: path checks can race with hostile filesystem modifications. Hardened multiuser environments require platform-specific safe-open and directory ownership controls.

## 8. SRE/DBRE architecture
\`\`\`text
synthetic events.json
    -> bounded_json_file context manager
    -> strict schema + metric validation
    -> ManagedReader (__enter__/__exit__)
    -> sqlite_snapshot context manager (:memory: only)
    -> parameterized aggregate query
    -> sanitized report
    -> atomic JSON file replacement
\`\`\`

Synthetic thresholds (not production SLOs):

| System | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag seconds | 30 | 120 |
| Elasticsearch | search_latency milliseconds | 200 | 500 |
| Kafka | consumer_lag messages | 1,000 | 10,000 |

## 9. Failure modes and troubleshooting
| Symptom | Cause | Mitigation |
|---|---|---|
| File descriptor exhaustion | Missing \`with\` or leaked generator | Scope and close resources |
| Connection leak | Transaction manager mistaken for connection manager | Explicitly close connection |
| Hidden exception | Truthy \`__exit__\` | Return \`False\` |
| Partial acquisition leak | \`__enter__\` raises | Clean up within acquisition |
| Incomplete report | Write interrupted | Temporary file + atomic replacement |
| Path escape | Unvalidated filename | Restrict filenames and trusted directory |
| Corrupt input | Invalid JSON or schema | Reject and re-export |
| Lock contention | Transaction not finalized | Commit/rollback and close |

## 10. Production runbooks
**Connection exhaustion:** stop new work, inspect active sessions and connection-pool metrics, release leaked sessions, restore bounded pool settings, and run regression tests.

**File descriptor leak:** inspect process descriptors, close suspended generators, verify all context manager paths and redeploy.

**Partial output or disk full:** retain previous known-good report, validate free space and permissions, retry only safe idempotent report generation, verify report checksum.

**Database failure:** roll back active transactions, close connections, investigate query/timeout behavior and replay against a read-only test environment.

**Rollback:** restore the prior implementation, run cleanup/exception tests, verify no resource leaks and resume scheduled execution.

## 11. Lab and assessment
[Chapter 054 — Resource Lifecycle SRE/DBRE Lab](labs/054-context-managers-resource-lifecycle-sre-dbre-lab.md) includes complete source code, synthetic fixtures, automated tests, failure injection, troubleshooting, runbooks and a 100-point assessment.

**Next:** Chapter 055 — Python Threading, Locks and Concurrent I/O (provisional).
