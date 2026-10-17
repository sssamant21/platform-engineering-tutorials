# Chapter 053 — Python Decorators, Closures and Operational Instrumentation

**Part 06 — Advanced Python, Typing and Concurrency | Python 3.10+ | 6–8 hours**

## Learning outcomes

Explain first-class functions, lexical closures, decorators, decorator factories, @functools.wraps, ParamSpec/TypeVar, decorator ordering, instrumentation and read-only retries. Build a fully offline SRE/DBRE telemetry application with deterministic tests and explicit safety boundaries.

## 1. First-class functions and closures

Python functions can be passed as values, returned from other functions and assigned to variables. A closure retains references to variables from its enclosing lexical scope after the outer function returns.

\`\`\`python
def threshold_checker(limit: float):
    def check(value: float) -> bool:
        return value >= limit
    return check

critical_lag = threshold_checker(120.0)
assert critical_lag(125.0)
\`\`\`

The captured \`limit\` persists without global state. Avoid accidentally capturing mutable state in loops; use default arguments or a factory when binding the current iteration value.

## 2. Basic decorators

\`\`\`python
from functools import wraps

def announce(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper

@announce
def read_status():
    """Read-only status operation."""
    return "ok"
\`\`\`

\`@announce\` is equivalent to \`read_status = announce(read_status)\`. The wrapper can add behavior before and after the call. \`@wraps\` preserves \`__name__\`, \`__doc__\`, \`__wrapped__\` and other metadata used by introspection and tooling.

## 3. Decorator factories and lexical configuration

\`\`\`python
def tagged(name):
    def decorate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper
    return decorate
\`\`\`

A decorator factory captures a validated operation name and dependency references such as a metrics recorder or monotonic clock. This makes instrumentation testable without changing production logic.

## 4. Type-preserving wrappers

Use \`ParamSpec\` to preserve positional and keyword parameter types, and \`TypeVar\` for the return type:

\`\`\`python
from typing import Callable, ParamSpec, TypeVar
P = ParamSpec("P")
R = TypeVar("R")

def identity(fn: Callable[P, R]) -> Callable[P, R]:
    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return fn(*args, **kwargs)
    return wrapper
\`\`\`

This is preferable to returning \`Callable[..., Any]\`, which loses type information. For asynchronous functions, a synchronous wrapper is not sufficient: use an async-aware decorator that awaits the wrapped coroutine.

## 5. Timing and metrics

Use \`time.perf_counter()\` or another monotonic clock for durations; do not subtract wall-clock timestamps to measure latency. Record one logical invocation, its failure status, and elapsed milliseconds in a \`finally\` block so exceptions are included.

Never record raw function arguments, return values, connection strings or credentials as metric labels. Cardinality must be bounded: an operation name should be a fixed allowlisted label, not a user ID, SQL statement or URL with parameters. Histograms or fixed-size aggregates are preferable to keeping every duration in memory. The lab stores duration samples for demonstration; production should replace this with bounded histograms or a metrics backend.

## 6. Retry decorators and operational safety

Retries can amplify an outage or repeat side effects. The lab retries only a dedicated \`TransientReadError\` from explicitly **read-only** operations. Permanent and unexpected exceptions are propagated immediately. It validates a 1–4 attempt budget, applies capped exponential delays, and injects \`sleep\` for deterministic tests.

Production adapters should additionally enforce network timeouts, overall deadlines, jitter, retry budgets and cancellation. Never apply the teaching retry decorator to destructive actions, writes, payments, failovers or remediation without a separate idempotency and authorization design.

## 7. Decorator ordering

\`\`\`python
@instrument(metrics, "read")
@read_only_retry(metrics, "read")
def read():
    ...
\`\`\`

Decorators apply bottom-up. Here retry wraps the underlying function, while timing wraps the entire logical operation. Thus three attempts count as **one logical call** and **three attempts**. Reversing them records timing for each attempt instead.

## 8. SRE/DBRE architecture

\`\`\`text
synthetic PostgreSQL / Elasticsearch / Kafka telemetry
   -> validated operation name
   -> timing + outcome decorator
   -> bounded read-only retry decorator
   -> read-only fixture adapter
   -> metric/unit validation and severity classification
   -> sanitized deterministic JSON operational report
\`\`\`

| Engine | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag (seconds) | 30 | 120 |
| Elasticsearch | search_latency (milliseconds) | 200 | 500 |
| Kafka | consumer_lag (messages) | 1,000 | 10,000 |

These are synthetic thresholds, not production alert policy.

## 9. Failure modes and troubleshooting

| Symptom | Likely cause | Remedy |
|---|---|---|
| Function metadata missing | No \`@wraps\` | Apply \`@wraps(fn)\` |
| Incorrect call count | Decorator ordering | Distinguish logical calls and attempts |
| Retry storm | Unbounded attempts | Enforce budget and deadline |
| Permanent errors retried | Broad exception catch | Catch only transient read failures |
| Negative elapsed duration | Wrong clock | Use monotonic clock |
| Secret leaked in labels | Dynamic arguments as labels | Fixed operation names |
| Memory growth | Unlimited duration samples | Bounded histograms |
| Unexpected async behavior | Sync wrapper around coroutine | Implement async-aware decorator |

## 10. Production runbooks

**Latency regression:** check per-operation duration distribution and retry amplification, compare baseline, isolate downstream dependency, roll back instrumentation if overhead is material.

**Retry storm:** disable retry policy, check upstream rate limits and timeouts, restore a safe attempt budget and verify read-only semantics.

**Metric cardinality incident:** remove dynamic labels, apply allowlisted operation names, inspect metrics backend series growth and enforce limits.

**Secret exposure:** restrict affected telemetry, rotate compromised credentials and remove unsafe argument logging.

**Rollback:** revert decorator configuration, replay offline fixtures, confirm metadata and operational outputs, then resume deployment.

## 11. Hands-on lab

[Chapter 053 — Decorators and Instrumentation SRE/DBRE Lab](labs/053-decorators-closures-instrumentation-sre-dbre-lab.md) includes complete Python source, an automated test suite, retry incident simulations, troubleshooting, runbooks and a 100-point assessment.

**Next:** Chapter 054 — Python Context Managers and Resource Lifecycle Management (provisional).
