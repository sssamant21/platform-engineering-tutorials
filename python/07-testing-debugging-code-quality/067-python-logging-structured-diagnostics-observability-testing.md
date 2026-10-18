# Chapter 067 — Python Logging, Structured Diagnostics and Observability Testing

**Part 07 — Testing, Debugging and Code Quality | Python 3.11+ | 8–10 hours**

## Learning objectives
Design secure structured JSON logs, logging handlers and propagation policies; carry correlation and trace context across async tasks and threads; prevent sensitive-data leaks; validate metric label cardinality and span semantics; and test SRE/DBRE observability end to end.

## 1. The three observability signals
Logs are discrete events; metrics are aggregated measurements and alert inputs; traces represent a request's operation sequence and duration. They complement each other: a critical Kafka consumer-lag alert should link to a request correlation ID, an error log, and a trace when available. This chapter implements **local test doubles**, not an OpenTelemetry exporter or production telemetry backend.

## 2. Structured JSON logging
Python's \`logging\` provides loggers, levels, filters, formatters and handlers. Use a single JSON object per line, consistent event names, UTC timestamps, stable severity and a small set of validated fields. Emit event codes rather than arbitrary exception text or untrusted payloads. The lab deliberately does **not** call \`record.getMessage()\`, because interpolated arguments can leak secrets.

### Logger propagation and handlers
A named logger normally propagates to its ancestors. Adding handlers to both the child and root can duplicate events. The lab creates a fresh non-propagating logger with one \`StreamHandler\`. In production, configure handlers centrally, prevent double emission, and use a \`QueueHandler\`/\`QueueListener\` for high-volume or latency-sensitive logging. Never share mutable handler state across tests.

## 3. Redaction and data minimization
Do not log credentials, bearer tokens, cookies, SQL bind values, customer payloads or arbitrary exception messages. A key-name scrubber is defense-in-depth, **not** a complete secret detector. The safe approach is an allowlist of fields and event codes. Avoid logging raw request headers or free text; verify redaction with known canary secrets. Limit record sizes and retain logs only according to approved policies.

## 4. Correlation IDs and context propagation
\`contextvars.ContextVar\` supports request-scoped state across asynchronous tasks. Use \`set()\` tokens and \`reset()\` in \`finally\` to prevent context leaks. Context propagates to tasks created with \`asyncio.create_task\`, but **does not automatically propagate to arbitrary executor threads**: use \`contextvars.copy_context().run\` explicitly. Trace IDs are 32 lowercase hex digits and span IDs 16 lowercase hex digits in the synthetic lab; these values are validated, not generated from production traces.

## 5. Metrics engineering
The lab's in-memory \`Metrics\` records event counts and processing duration in nanoseconds. Production metrics should use counters, histograms and bounded label sets. Never label metrics with request IDs, user IDs or unbounded paths: this causes time-series cardinality explosions. Define stable units, exemplars where supported, recording rules and SLO-aligned alert thresholds.

## 6. Trace and span testing
A trace identifies a request; a span represents an operation. Tests should check trace/span identity, parent-child semantics when modeled, status and nonnegative duration. The lab emits a single synthetic \`telemetry.process\` span per request with a deterministic injected clock. This is not a full distributed tracing implementation. Production instrumentation should use an approved OpenTelemetry SDK and secure exporters, including sampling and collector backpressure controls.

## 7. SRE/DBRE architecture
\`\`\`text
synthetic PostgreSQL / Elasticsearch / Kafka readings
   -> strict validation -> severity classification
   -> JSON log (UTC, event code, correlation/trace/span IDs)
   -> bounded metric labels + monotonic durations
   -> synthetic trace sink
   -> deterministic unittest acceptance gates
   -> incident simulations + runbooks
\`\`\`

| Engine | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag_seconds | 30 | 120 |
| Elasticsearch | search_latency_ms | 200 | 500 |
| Kafka | consumer_lag_messages | 1,000 | 10,000 |

Thresholds are synthetic and must not be mistaken for production SLOs.

## 8. Production reliability and failure modes
Logging must not block critical operations indefinitely; design queue bounds, drop accounting and failure handling. Ensure instrumentation errors do not silently corrupt business outcomes. Use UTC timestamps and monotonic clocks for elapsed time. Sample verbose events; keep audit logs reliable and appropriately access-controlled. Track dropped telemetry, collector saturation, exporter errors and log ingestion lag.

| Symptom | Root cause | Remediation |
|---|---|---|
| Duplicate logs | Multiple handlers/propagation | Centralize handler, disable duplicate propagation |
| Missing correlation | Context not propagated to thread | Use \`copy_context()\` or explicit injection |
| Leaked context | Missing token reset | Reset in \`finally\` |
| Sensitive value in logs | Free-text interpolation | Event allowlist, redaction tests, rotate exposed secrets |
| High metric cost | Unbounded labels | Restrict to engine and severity |
| Trace duration negative | Wall-clock measurement | Use monotonic clock |
| Missing spans | Instrumentation failure | Verify trace sink/exporter and sampling |
| High logging latency | Synchronous output or backpressure | Bounded queue, monitor drops |

## 9. Production runbooks
**Log duplication incident:** compare handler trees and propagation, apply centralized configuration, validate counts.

**Sensitive log exposure:** restrict access immediately, identify affected sinks, rotate exposed credentials, apply retention policy and audit disclosure.

**Missing correlation:** inspect context boundaries, executor transitions and middleware, add propagation tests.

**Metric cardinality spike:** identify new labels, block unbounded dimensions, apply recording/retention remediation and verify dashboard costs.

**Trace loss:** inspect sampling, queue saturation, collector health and exporter credentials, restore last stable config.

**Rollback:** restore known-good instrumentation, rerun tests, verify alerts and record change approval.

## 10. Lab and assessment
[Chapter 067 — Structured Logging and Observability SRE/DBRE Lab](labs/067-structured-logging-observability-sre-dbre-lab.md) includes complete Python code, automated tests, failure injection, production runbooks and a 100-point assessment.

**Next:** Chapter 068 — Python Static Analysis, Linting and Code Quality Automation (provisional).
