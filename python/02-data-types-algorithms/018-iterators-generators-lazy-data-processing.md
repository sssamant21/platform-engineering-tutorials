# Chapter 018 — Iterators, Generators and Lazy Data Processing

**Part 02 — Data Types and Algorithms | Python 3.10+ | Estimated 100–140 minutes**

## Learning outcomes
- Explain iterables, iterators, `iter()`, `next()`, and `StopIteration`.
- Write generator functions using `yield`, generator expressions and `yield from`.
- Understand lazy evaluation, one-shot consumption, resource lifetimes and backpressure.
- Process large synthetic SRE JSON Lines (JSONL) logs without loading the whole file into memory.
- Design deterministic, read-only streaming aggregations with validation, line-numbered errors, tests and bounded state.

## 1. Iterable versus iterator

An **iterable** can produce an iterator. An **iterator** maintains traversal state, exposes `__next__()` and raises `StopIteration` when exhausted.

```python
services = ["api", "worker", "db"]  # iterable
cursor = iter(services)             # iterator
assert next(cursor) == "api"
assert list(cursor) == ["worker", "db"]
assert list(cursor) == []           # exhausted iterator
assert list(services) == ["api", "worker", "db"]
```

Calling `iter()` on a list creates a new iterator. Calling `iter()` on a generator normally returns that same one-shot generator. Reuse requires creating a new generator.

## 2. Generators and yield

A generator function returns a generator object immediately. Its body runs only when the caller advances the iterator.

```python
def health_events():
    print("started")
    yield {"service": "api", "severity": "warning"}
    yield {"service": "db", "severity": "critical"}

stream = health_events()   # nothing printed yet
first = next(stream)       # prints started
rest = list(stream)
```

The suspended function retains local variables between yields. When exhausted, it raises `StopIteration`. Do not manually raise `StopIteration` inside a generator; use `return` to end it.

## 3. Generator expressions and short-circuiting

```python
cpu_values = [20, 40, 91, 25]
critical = any(cpu >= 90 for cpu in cpu_values)
average = sum(cpu_values) / len(cpu_values)
```

`any()` stops at the first truthy result, and `all()` stops at the first falsy result. A generator expression avoids allocating an intermediate list, but the source list in this example still occupies memory.

## 4. yield from

```python
def all_events(groups):
    for group in groups:
        yield from group
```

`yield from` delegates iteration to a sub-iterable. It is convenient for composing streams, but does not magically limit memory if the source is already materialized.

## 5. File iteration and resource lifetime

```python
from pathlib import Path

def nonempty_lines(path: Path):
    with path.open("r", encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if line.strip():
                yield number, line
```

The file remains open while the generator is suspended inside the `with` block. **Consume or explicitly close generators that own resources.** If a consumer stops early, use `contextlib.closing` or a context manager with a scoped file handle. Do not rely on garbage collection for timely cleanup.

## 6. JSONL versus JSON arrays

JSONL stores one JSON object per line, allowing incremental parsing and line-numbered errors:

```json
{"service":"api","severity":"warning","latency_ms":220}
{"service":"db","severity":"critical","latency_ms":950}
```

A JSON array parsed using `json.load()` materializes the entire document. JSONL with line iteration supports bounded per-record memory, but a full in-memory index or list of all records can still grow with the input.

## 7. Streaming transformations

```python
def slow_events(events, threshold_ms):
    for event in events:
        if event["latency_ms"] >= threshold_ms:
            yield event
```

Use a pipeline of validation, filtering and aggregation. Validate **before** trusting fields. For an aggregation by service, memory is O(k), where k is the number of distinct service keys, rather than O(n) for n events. A high-cardinality service field can still make k large, so production systems need explicit cardinality limits or external storage.

## 8. Errors and partial processing

A streaming parser may encounter a malformed record after earlier valid records. For batch audit reports, fail the entire operation and do **not** emit a partial success report. The lab writes a JSON report only after complete successful iteration. Diagnostics go to stderr through `argparse`; stdout is reserved for successful JSON.

Production ingestion pipelines require a deliberate dead-letter, retry and checkpoint policy. Silently skipping malformed logs can hide incidents.

## 9. Complexity

| Operation | Time | Additional memory |
|---|---|---|
| Iterate n records | O(n) | O(1) beyond current record |
| Filter generator | O(n) | O(1) beyond current record |
| Count by k services | O(n) expected | O(k) |
| Sort k service summaries | O(k log k) | O(k) |
| Materialize `list(generator)` | O(n) | O(n) |

File iteration uses buffering and one record at a time; exceptionally long lines still consume memory. The lab rejects oversized lines and caps distinct service keys.

## 10. Operational use cases
- Stream and summarize synthetic Elasticsearch slowlog-style records.
- Count Kubernetes event severities from exported JSONL.
- Analyze simulated PostgreSQL query latency events.
- Aggregate API gateway response-time records.
- Detect high-latency samples without retaining every event.

Do not put credentials, PHI, access tokens or sensitive log payloads in training fixtures.

## 11. Hands-on lab
Follow [Chapter 018 — SRE Streaming Log Analyzer Lab](labs/018-sre-streaming-log-analyzer-lab.md) to build a JSONL streaming CLI, validate event schemas, summarize severities and latency by service, enforce cardinality and line-size limits, and run unit tests.

## 12. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Generator yields no values on second pass | One-shot iterator exhausted | Create a new generator |
| File remains open | Partially consumed generator | Use scoped context manager or close |
| `StopIteration` | End of stream | Use `for` loop or `next(iterator, default)` |
| Memory grows with logs | Materialized records or high-cardinality keys | Stream, cap keys, aggregate externally |
| `JSONDecodeError` | Malformed JSONL line | Report line number; reject batch |
| Incorrect report | Partial output before parse completed | Emit report only after full validation |
| Slow pipeline | Expensive per-record operations | Profile with representative fixtures |

## 13. Acceptance criteria
- Correct iterator and generator semantics.
- Incremental file parsing, not `readlines()` or `json.load()` for the JSONL stream.
- Strict schema validation with useful errors.
- Deterministic service-level report.
- Line-size and cardinality limits.
- Automated tests and failure-injection exercises.
- No external service calls or mutations.

**Next: Chapter 019 — Algorithmic Patterns: Two Pointers, Sliding Windows and Frequency Maps.**
