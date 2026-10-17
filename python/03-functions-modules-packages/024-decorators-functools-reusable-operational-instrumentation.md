# Chapter 024 — Decorators, functools and Reusable Operational Instrumentation

**Part 03 — Functions, Modules and Packages | Python 3.10+ | 120 minutes**

## Objectives
Implement function decorators, parameterized decorator factories, `functools.wraps`, `partial`, `lru_cache`, safe retry policies, monotonic timing, and injectable observability. Build and test an offline SRE reliability wrapper without external dependencies.

## 1. Why decorators?
SRE scripts repeat cross-cutting concerns: timing, logging, retries, metrics and input validation. A decorator wraps a callable without changing its core business logic. Keep behavior explicit: excessive stacked decorators hide execution order and complicate debugging.

```python
from functools import wraps

def instrument(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper

@instrument
def health_status(): return "healthy"
assert health_status.__name__ == "health_status"
```

The decorator expression runs at **definition/import time**; the wrapper runs on each call. `@wraps` preserves `__name__`, `__doc__`, `__wrapped__` and signature introspection support.

## 2. Parameterized decorator factories
```python
def label(name):
    def decorate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return {"label": name, "result": fn(*args, **kwargs)}
        return wrapper
    return decorate
```
`@label("read-only")` is evaluated once to create the decorator, then applied to the function.

## 3. Retry semantics: only transient and safe operations
Retry **only** classified transient failures, with finite attempts, exponential backoff, jitter and a deadline. Never automatically retry non-idempotent writes without a verified idempotency key and owner-approved policy. In the lab, retries are immediate by default using an injected sleeper, so tests never wait.

```python
delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
```

Bound both `max_attempts` and total elapsed time in real production clients. Jitter reduces synchronized retry storms. Avoid catching `BaseException`, `KeyboardInterrupt` or every `Exception`; catch only an approved transient exception type.

## 4. Timing with monotonic clocks
Use `time.perf_counter()` for elapsed duration, not wall-clock `datetime.now()`. Clock changes can invalidate wall-clock elapsed measurements. Inject the clock in tests for deterministic assertions.

## 5. Metrics and cardinality
Instrument duration, success and failure with controlled labels such as operation name and outcome. Do **not** label metrics by request ID, patient ID, full URL, raw SQL, exception message or tenant identifier unless cardinality and privacy are explicitly managed. Metrics in this lab are in-memory snapshots, not distributed counters.

## 6. functools.partial
```python
from functools import partial
def is_slow(latency_ms, *, threshold_ms): return latency_ms >= threshold_ms
prod_slow = partial(is_slow, threshold_ms=250)
assert prod_slow(300)
```
`partial` binds arguments and creates a reusable callable. It does not validate values or make the function thread-safe.

## 7. functools.lru_cache
```python
from functools import lru_cache
@lru_cache(maxsize=128)
def normalize_status(code: int) -> str:
    return "server-error" if code >= 500 else "other"
```
Cache only functions whose results are stable for their arguments. Do not cache mutable objects, live credentials, unbounded user identifiers, or time-sensitive health checks. Cache operations may execute more than once under concurrent first access, even though cache bookkeeping is synchronized. Review TTL/invalidation requirements; `lru_cache` has no TTL.

## 8. Decorator stacking
```python
@outer
@inner
def operation(): ...
```
is equivalent to `operation = outer(inner(operation))`. Calls enter `outer` first, then `inner`; returns unwind in reverse order. Retry outside timing measures all attempts; timing outside retry measures the overall retry sequence. Explicitly choose what the metric represents.

## 9. Operational use cases
- Read-only Elasticsearch query probes with bounded transient retries.
- PostgreSQL health checks with monotonic timing.
- Kubernetes API discovery with safe 429/503 handling.
- Kafka metadata inspection and controlled backoff.
- Snowflake metadata retrieval with a cache policy and freshness contract.

## 10. Complexity and resource tradeoffs
A wrapper adds O(1) overhead per invocation apart from its delegated work. With at most a attempts, retry work is O(a × operation cost) plus backoff. An LRU cache with capacity k consumes O(k) memory. Instrumentation buffers must be bounded or exported asynchronously by a vetted metrics backend.

## 11. Security and failure analysis
| Symptom | Root cause | Action |
|---|---|---|
| Lost function metadata | Missing `@wraps` | Apply wraps |
| Retry storm | Unbounded attempts/backoff | Cap attempts and delay, add jitter |
| Duplicate writes | Retrying unsafe side effects | Require idempotency guarantees |
| Wrong duration | Wall clock used | Use monotonic clock |
| Sensitive metric labels | Raw identifiers logged | Use allowlisted low-cardinality labels |
| Stale health state | Cached live checks | Disable cache or define invalidation |
| Silent failures | Broad exception suppression | Propagate nontransient failures |
| Test sleeps | Real `time.sleep` | Inject sleeper and clock |
| Decorator order confusion | Wrapper nesting | Document order and test it |

## 12. Hands-on
[Chapter 024 — Instrumented SRE Probe Lab](labs/024-instrumented-sre-probe-lab.md) contains executable source, synthetic CLI, deterministic tests, failure injection and runbooks.

## 13. Production runbook
1. Confirm operation is read-only or explicitly idempotent.
2. Define retryable exception types and finite attempts.
3. Set deadline, backoff cap, jitter and rate limits at caller boundary.
4. Instrument attempt counts, terminal outcome and monotonic latency with safe labels.
5. Exercise persistent/transient failures in staging.
6. Confirm telemetry cardinality and privacy; review cache freshness.
7. Disable retry or rollback wrapper configuration if load amplification occurs.

**Next: Chapter 025 — Python Modules, Imports and Package Organization.**
