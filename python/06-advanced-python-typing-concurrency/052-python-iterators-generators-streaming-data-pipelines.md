# Chapter 052 — Python Iterators, Generators and Streaming Data Pipelines

**Part 06 — Advanced Python, Typing and Concurrency | Python 3.10+ | 6–8 hours**

## Learning objectives
Understand the iterator protocol, lazy evaluation, generator functions and expressions, `yield`, `yield from`, batching, streaming operational log files, resource lifetime, bounded memory and failure handling. Build an executable SRE/DBRE NDJSON telemetry analyzer.

## 1. Iterable versus iterator

An *iterable* provides `iter(obj)`; an *iterator* provides `__next__()` and returns itself from `__iter__()`. A `for` loop calls `iter` then repeatedly calls `next` until `StopIteration`.

```python
values = [10, 20, 30]
it = iter(values)
assert next(it) == 10
assert list(it) == [20, 30]
assert list(it) == []  # exhausted iterators are not reusable
```

A list can be traversed repeatedly; a generator object is normally single-use. Never assume a stream can be replayed without reopening its source.

## 2. Generator functions and lazy evaluation

```python
def critical_values(values):
    for value in values:
        if value >= 120:
            yield value
```

Calling `critical_values` returns a generator without executing its body. Execution begins when the consumer advances it. Generator expressions, e.g. `(x*x for x in range(1000000))`, avoid materializing the whole output.

## 3. Yield from, delegation and composition

```python
def flatten(batches):
    for group in batches:
        yield from group
```

`yield from` delegates iteration and propagates generator protocol behavior. Be careful with `send`, `throw` and `close` in advanced coroutine-like generators; most operational streaming pipelines only need ordinary iteration.

## 4. Bounded batching

Use `itertools.islice` to read up to N items per batch, producing tuples of size at most N. The last batch may be shorter. A batch is not a retry or transaction boundary unless the downstream system explicitly defines it that way.

Memory usage is approximately `O(batch_size + largest_line)` for the lab's streaming summarizer, not `O(total_events)`. This does not imply an absolute constant memory guarantee for arbitrary input sources or Python runtimes.

## 5. Streaming files safely

Read NDJSON line-by-line, enforce a maximum byte length *before decoding*, validate UTF-8 and JSON schema, and stop at a bounded event count. A line-based file reader is simpler than loading an entire multi-gigabyte JSON array. The lab caps each line at 4096 bytes and total records at 100,000.

**Important limitation:** `for line in binary_file` may allocate memory for an oversized line before the length check. For genuinely hostile unbounded files, use `readline(MAX_LINE_BYTES + 1)` with explicit overlong-line handling or a bounded framing parser. The lab is an educational read-only pipeline, not a hardened adversarial ingestion service.

## 6. File and generator lifecycle

The `with path.open(...)` inside a generator keeps the file open while the generator is suspended. Fully consume the generator, explicitly call `close()` on early termination, or use a context manager to ensure prompt cleanup. Do not retain unconsumed generators indefinitely.

## 7. Backpressure and throughput

A synchronous generator naturally produces the next item only when the consumer requests it. It does not provide distributed backpressure, Kafka offset commits, concurrency control, queue durability or exactly-once semantics. Measure producer/consumer throughput, memory, file descriptor count and processing latency.

## 8. Operational architecture

```text
synthetic events.ndjson
   -> lazy bounded binary-line reader
   -> UTF-8 + strict JSON validation
   -> typed Event generator
   -> itertools.islice batches
   -> streaming counters
   -> deterministic JSON summary
```

The pipeline is **read-only**: no database writes, Kafka acknowledgments or Kubernetes mutations.

## 9. SRE/DBRE examples

| Engine | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag (seconds) | 30 | 120 |
| Elasticsearch | search_latency (milliseconds) | 200 | 500 |
| Kafka | consumer_lag (messages) | 1,000 | 10,000 |

Thresholds are synthetic teaching examples and must not be reused as production SLOs.

## 10. Troubleshooting

| Symptom | Likely cause | Response |
|---|---|---|
| No output | Generator never consumed | Iterate explicitly |
| Missing records | Iterator exhausted | Reopen input |
| High memory | `list()` or unbounded buffering | Keep lazy stages |
| Open file descriptors | Generator not closed | Use cleanup or context manager |
| Slow batches | Batch too small / I/O overhead | Benchmark size |
| Oversized record | Producer format drift | Reject/quarantine |
| Malformed JSON | Corrupt NDJSON | Fail with sanitized line number |
| Partial report | Error mid-stream | Fail closed; do not publish partial success |

## 11. Production runbooks

**Backlog or memory incident:** suspend downstream side effects, inspect throughput and buffering, reduce batch size or rate, profile memory and verify complete replay.

**Schema drift:** quarantine bad records with sanitized metadata, coordinate producer schema, rerun regression tests before replay.

**Resource leak:** inspect open file descriptors, close suspended generators, add lifecycle tests and redeploy.

**Rollback:** pin the known-good parser, replay immutable source files and compare deterministic counters.

**Data-quality incident:** stop automated decisions on partial data, verify counts, timestamps, units and source completeness.

## 12. Hands-on lab
[Chapter 052 — Streaming SRE/DBRE Telemetry Pipeline Lab](labs/052-streaming-sre-dbre-telemetry-pipeline-lab.md) contains complete Python source, NDJSON fixtures, automated tests, CLI commands, failure injection and a 100-point assessment.

**Next:** Chapter 053 — Python Decorators, Closures and Operational Instrumentation (provisional).
