# Chapter 020 — Data Structures and Algorithms Capstone: SRE Telemetry Analyzer

**Part 02 — Data Types, Collections and Algorithms | Python 3.10+ | 2–3 hours**

## Capstone mission
Build an offline, read-only telemetry analyzer for synthetic SRE events. Combine the previous chapters into a single reproducible workflow: validated records, tuple identities, dictionaries and sets, lazy JSONL parsing, deques for sliding windows, frequency maps, stable sorting, and deterministic JSON output.

**Safety:** No Kubernetes, cloud, database, paging, or network access. Never put secrets or patient data in fixtures.

## Architecture

```text
local synthetic JSONL
        |
        v
  line-by-line iterator
        |
        v
 strict schema validator ----> line-numbered fail-closed error
        |
        v
 streaming aggregation
   |          |          |
   v          v          v
Counter     set/tuple   deque per service
severity    identity    rolling error window
   |          |          |
   +----------+----------+
              |
              v
 deterministic sorted report
              |
              v
 stdout JSON (only after full validation)
```

## Functional requirements
1. Parse one JSON object per line using a generator, without `readlines()` or materializing all events.
2. Require `timestamp`, `environment`, `service`, `severity`, `latency_ms`, and `is_error`.
3. Reject booleans in numeric fields, negative/non-finite numbers, unknown severities, malformed JSON, out-of-order timestamps and unexpected fields.
4. Use `(environment, service)` as the composite service identity; reject excessive identity cardinality.
5. Count total events and severity frequencies; compute per-service maximum latency and slow-event count.
6. Use a trailing inclusive time window `[t - window_seconds, t]` to calculate error rates.
7. Report rolling windows **as of each service's last event**, not as a synchronized global snapshot.
8. Generate stable ordering by environment then service; do not emit a success report if any line fails.
9. Bound retained events per window and physical line length; reject overflow rather than silently drop events.
10. Include automated tests, failure injection, and a production-readiness discussion.

## Data structures and why they fit

| Requirement | Structure | Reason |
|---|---|---|
| JSONL traversal | generator | Lazy, one record at a time |
| Composite service identity | tuple | Hashable and unambiguous |
| Group summaries | dict | Average O(1) lookup |
| Unique identities | set / dict keys | Detect cardinality growth |
| Severity totals | Counter | Compact frequency map |
| Sliding error window | deque | O(1) append and left eviction |
| Final ranking | sorted list | Deterministic O(k log k) output |

For n records, k unique services, and maximum retained window occupancy w across services, expected processing is O(n), final sorting O(k log k), and auxiliary memory O(k + w). Window duration does not by itself cap memory: a burst can contain many events. The lab enforces a configurable event-capacity limit.

## Algorithm: streaming event-time window
For each event in nondecreasing timestamp order:
1. Validate the event and its timestamp.
2. Find the per-service bucket using its composite key.
3. Append the event's timestamp and error flag to that service's deque.
4. Evict entries strictly older than `timestamp - window_seconds`.
5. Update the rolling error count and derive error rate from current deque length.
6. Update cumulative severity counts, slow counts and maximum latency.

Each event enters and leaves its deque at most once. A record exactly on the left boundary remains in the window.

## Operational interpretation
- **Slow event:** `latency_ms >= slow_threshold_ms`.
- **Rolling error rate:** errors / events in the service's current window.
- **Candidate alert:** window sample count >= `min_samples` and error rate >= `alert_rate`.
- **Freshness:** each service's report is anchored to its last observed timestamp. A stale service must not be interpreted as healthy.
- **Percentiles:** not calculated in this streaming capstone; exact percentiles require retaining/sorting samples or a separate quantile data structure/sketch.
- **No actual paging:** `would_alert` is a simulation flag.

## Production SRE/DBRE scenarios
- Compare synthetic Elasticsearch timeout and latency bursts by cluster service.
- Summarize exported Kubernetes warning/error events by namespace-equivalent environment.
- Review PostgreSQL query error/latency events from sanitized fixtures.
- Detect repeated Kafka consumer errors in an offline incident exercise.
- Generate a deterministic artifact for incident review without touching production.

## Failure modes and troubleshooting

| Symptom | Root cause | Safe response |
|---|---|---|
| Wrong window count | Boundary or eviction error | Assert inclusive boundary with tests |
| Negative/NaN latency accepted | Weak validation | Reject non-finite and boolean numeric values |
| Memory growth | Unbounded labels or event bursts | Enforce identity and window-event caps |
| Silent partial report | Output emitted during iteration | Emit only after successful completion |
| Out-of-order events | Event-time skew | Reject; design explicit lateness buffering later |
| Inconsistent results | Nondeterministic dict/set traversal | Sort report by composite identity |
| Stale rate appears current | Per-service last-event anchoring | Add freshness policy for production |
| Duplicate data | Replayed events | Define event IDs and idempotency separately |
| Sensitive output | Raw production logs | Use sanitized synthetic data |

## Operational acceptance
- All input-validation tests pass.
- Fixture output matches documented counts and rates.
- Repeated runs produce byte-identical JSON output.
- Malformed input exits nonzero without a success JSON document.
- No network, infrastructure mutation or alert delivery.
- Document remaining gaps: durable ingestion, idempotency, late events, common-time windows, telemetry sampling, alert policy, retention and observability.

## Hands-on implementation
Follow the complete [Chapter 020 — SRE Telemetry Analyzer Capstone Lab](labs/020-sre-telemetry-analyzer-capstone-lab.md), which includes a fixture, full executable Python source, unit tests, commands, expected results, failure injection, and acceptance checklist.

## Part 02 review questions
1. Why are tuple composite keys safer than service name alone?
2. How does a deque reduce repeated work in rolling windows?
3. When does streaming aggregation still grow without bound?
4. Why is `hash()` not a durable event fingerprint?
5. What is the distinction between a batch-local simulated alert and a production SLO alert?
6. How would you incorporate late events without changing prior reports silently?

**Part 02 completed with Chapter 020. Next: Chapter 021 — Functions as Reusable Interfaces: Parameters, Return Values and Contracts.**
