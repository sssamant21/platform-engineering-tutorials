# Chapter 038 — Iterators, Generators and Lazy Object-Oriented Pipelines

**Part 04 — Object-Oriented Programming | Python 3.10+ | 3–4 hours**

## Learning outcomes

Implement the iterator protocol (`__iter__`, `__next__`), generator functions and expressions, `yield from`, lazy filtering and aggregation, single-pass stream semantics, bounded-memory telemetry processing, and safe cleanup. Build a deterministic SRE/DBRE streaming pipeline with validation, synthetic JSON Lines input, alert classification and automated tests.

## 1. Why streaming matters to SRE and DBRE

Log exports, PostgreSQL replication samples, Elasticsearch query metrics and Kafka consumer lag can produce millions of records. Loading an entire file with `readlines()` or `json.load()` creates unnecessary memory pressure. Lazy pipelines process records incrementally and permit early termination, provided downstream stages do not materialize the stream.

```python
def valid_lines(lines):
    for line in lines:
        if line.strip():
            yield line

with open("telemetry.jsonl", encoding="utf-8") as source:
    for line in valid_lines(source):
        process(line)
```

This uses memory proportional to one line plus pipeline state rather than the entire input file. The lab also caps individual line size to avoid pathological records.

## 2. Iterator protocol

An **iterable** supplies `__iter__()`; an **iterator** supplies `__next__()` and normally returns itself from `__iter__()`. `next(iterator)` raises `StopIteration` when exhausted.

```python
class Counter:
    def __init__(self, limit):
        self.current = 0
        self.limit = limit

    def __iter__(self):
        return self

    def __next__(self):
        if self.current >= self.limit:
            raise StopIteration
        self.current += 1
        return self.current
```

This iterator is **single-use**. A reusable iterable can create a fresh iterator each time. Document whether a consumer may iterate twice.

## 3. Generator functions

A function containing `yield` creates a generator object when called; its body runs when advanced. Local variables persist between yields. Generator expressions are concise for simple transforms:

```python
squared = (x * x for x in range(1000))
first = next(squared)
```

`yield from other_iterable` delegates iteration to another iterable and propagates values. Generator exceptions surface during consumption, not creation.

## 4. Lazy composition

```python
def warnings(records):
    for record in records:
        if record["severity"] != "healthy":
            yield record

def services(records):
    for record in records:
        yield record["service"]

pipeline = services(warnings(source))
```

Avoid `list(pipeline)` on unbounded sources. For a bounded summary, retain counters and a capped preview. A lazy pipeline is only as memory efficient as its most eager stage.

## 5. Backpressure, early termination and cleanup

Synchronous pull-based iteration naturally advances upstream only when downstream requests another item. It does **not** provide distributed queue backpressure, retries, delivery guarantees or checkpointing. Real Kafka consumers require explicit offset/commit semantics and replay strategy.

File handles should be owned by a `with` block. Generator `close()` triggers generator cleanup, but do not rely on garbage collection timing. If a consumer exits early, close generators that own resources or keep resources scoped to the outer context.

## 6. Validation and security boundaries

A JSON Lines reader must reject malformed JSON, oversized lines, unknown fields, invalid units, negative metrics, NaN/infinity and booleans. Treat incoming records as untrusted. Do not evaluate expressions from input or dynamically import arbitrary handlers. Include line numbers in sanitized errors without echoing secrets.

## 7. Architecture

```text
synthetic .jsonl fixture
       |
   line iterator (bounded size)
       |
  JSON parser + schema validator
       |
  lazy severity classifier
       |
  optional filter / take
       |
  bounded accumulator
       |
  deterministic JSON report
```

The executable lab uses only the standard library and never contacts live services.

## 8. Production SRE/DBRE applications

| Domain | Stream | Operational concern |
|---|---|---|
| PostgreSQL | Replication lag observations | Correct units and sampling gaps |
| Elasticsearch | Query latency samples | Large slow-log volume |
| Kafka | Consumer lag measurements | Offset checkpoint and replay |
| Kubernetes | Pod events | Watch reconnect and resource versions |
| Snowflake | Query-history exports | Pagination and credit budgets |

Synthetic thresholds in the lab are examples, not universal SLOs. Production integrations need reviewed alert policies, read-only identities, bounded timeouts and retention limits.

## 9. Common mistakes

| Problem | Cause | Mitigation |
|---|---|---|
| Generator appears empty | Already consumed | Recreate source or document single-pass |
| Memory still grows | `list()` or unbounded grouping | Keep bounded summaries |
| File left open | Resource ownership unclear | Use `with` and explicit close |
| Error appears late | Lazy execution | Exercise full stream in tests |
| `StopIteration` surprise | Manual iterator exhaustion | Prefer `for` loops |
| Incorrect totals | Stream consumed twice | Aggregate in one pass |
| Partial report published | Error midstream | Finish validation before output |
| One enormous JSONL line | No size cap | Enforce per-line byte/character limit |
| False healthy state | Exception swallowed | Fail closed and alert |

## 10. Production runbooks

**Malformed telemetry:** stop report publication, record line number and safe error category, preserve sanitized fixture, correct upstream schema, replay through tests.

**Memory growth:** inspect eager transforms, retained references, preview limits and line-size caps; benchmark with synthetic high-volume fixtures.

**Truncated stream:** compare expected and observed counts, verify source completeness, avoid silent partial success and implement checkpointing for live adapters.

**Release:** run unit tests and performance checks, verify no live connections in CI, stage on synthetic data and preserve rollback.

## 11. Hands-on lab

[Chapter 038 — Streaming SRE/DBRE Telemetry Pipeline Lab](labs/038-streaming-sre-dbre-telemetry-pipeline-lab.md) includes executable source, synthetic JSONL fixture, **32 unit tests**, failure injection and runbooks.

**Next: Chapter 039 — Context Managers, Resource Management and Exception-Safe Operations.**
