# Chapter 071 — Python HTTP Fundamentals, REST APIs and Reliable API Clients

**Part 08 — APIs, Networking and Databases | Python 3.11+ | 8–12 hours**

## Learning objectives
Understand HTTP/HTTPS, DNS, TLS, REST conventions, status codes, headers, authentication, JSON contracts, idempotency, timeouts, retries, exponential backoff with jitter, pagination, rate limits, observability and secure API client design. Build a standard-library SRE/DBRE client that works with an in-process HTTP server, then apply production runbooks.

## 1. Network architecture
\`\`\`text
SRE/DBRE Python client
  -> URL validation and HTTPS policy
  -> DNS -> TCP -> TLS -> HTTP request
  -> gateway / load balancer / auth / rate limiting
  -> PostgreSQL/Elasticsearch/Kafka telemetry API
  -> JSON schema validation and safe structured diagnostics
  -> bounded retry and alert/report
\`\`\`
An HTTP request passes through name resolution, connection establishment, TLS negotiation, request transmission, response headers and response body. Distinguish DNS failures, connection refusals, timeouts, HTTP errors, malformed JSON and schema violations. A \`200\` response does not guarantee that its payload is valid.

## 2. HTTP fundamentals
- Methods: GET reads, HEAD inspects metadata, POST submits, PUT replaces, PATCH modifies, DELETE removes. **Idempotency** describes the effect of repeated requests, not whether a method can fail.
- Status families: 2xx success; 3xx redirects; 4xx client/auth/rate-limit; 5xx server failures. \`429\` commonly means throttling; \`503\` may indicate temporary unavailability.
- Headers: \`Accept\`, \`Content-Type\`, \`Authorization\`, \`Retry-After\`, \`ETag\`, \`If-None-Match\`, \`X-Request-ID\`. Avoid logging sensitive header values.
- REST resources should use consistent URIs and documented contracts. Never rely on arbitrary JSON keys without validation.

## 3. urllib.request and urllib.error
Python's standard library provides \`urllib.request.Request\`, \`urlopen\`, \`HTTPError\`, \`URLError\` and \`urllib.parse\`. Always set a finite timeout, enforce maximum response size and validate JSON types. \`HTTPError\` is an exception that also exposes the HTTP response status. Avoid disabling TLS verification. The lab uses a local \`ThreadingHTTPServer\` on loopback; it does not make external network calls.

## 4. Timeouts and retries
A timeout limits a blocking operation, but \`urllib\`'s timeout is not a guaranteed total end-to-end deadline across all phases. Enforce an application-level budget where appropriate. Retry only **safe/idempotent** operations or requests with a server-supported idempotency key. Use bounded attempts, exponential backoff, optional jitter and a maximum delay. Handle \`429\`, \`502\`, \`503\`, \`504\` and transient transport failures according to a documented policy. Avoid retrying malformed payloads, \`401\`, \`403\`, or \`404\` without a specific contract.

## 5. TLS, credentials and SSRF
Use HTTPS with default certificate validation for remote APIs. Keep tokens in approved secret stores and avoid printing them. Construct URLs from a trusted fixed base and allowlisted relative paths. Do not follow arbitrary user-provided URLs, redirects or hosts. The lab intentionally restricts requests to \`http://127.0.0.1\` for a disposable local server; production clients must enforce HTTPS and trusted hosts.

## 6. Pagination and rate limits
Prefer bounded pagination with explicit page size and total page caps. Validate continuation tokens and avoid infinite loops. Treat \`Retry-After\` as a server hint, bound its value and keep within a global retry budget. Use client-side concurrency limits and respect API quotas.

## 7. Observability and reliability
Record method, trusted endpoint template, response status class, retry count, elapsed duration and sanitized correlation ID. Do not label metrics by raw URL/query/token or log raw response bodies. Track request success rate, latency percentiles, timeouts, retry amplification, 429s, schema errors and upstream saturation. Use SLO-based alerts rather than alerting on every transient retry.

## 8. SRE/DBRE scenarios
1. PostgreSQL replica lag endpoint returns \`503\` once then succeeds: bounded GET retry recovers.
2. Elasticsearch latency endpoint returns invalid JSON: reject without retry.
3. Kafka lag endpoint returns \`429\`: honor bounded backoff and avoid retry storm.
4. API token expires: \`401\` is terminal; rotate credential through approved workflow.
5. Upstream responds slowly: finite timeout and incident evidence prevent indefinite hang.
6. Gateway returns \`302\` to an untrusted host: reject redirect and prevent credential leakage.
7. A payload exceeds configured size: stop reading and fail safely.
8. DNS resolution fails: classify as transport error; do not report a healthy metric.
9. API returns \`200\` with negative lag: reject at the contract boundary.
10. Repeated \`503\` errors exhaust retries: return sanitized failure and escalate.

## 9. Troubleshooting
| Symptom | Likely cause | Action |
|---|---|---|
| \`URLError\` | DNS/TCP/TLS/transport failure | Check resolver, route, certificates and timeout |
| \`HTTPError 401/403\` | Auth/authorization | Validate identity and permissions; do not blind retry |
| \`429\` | Rate limiting | Honor bounded backoff and reduce concurrency |
| \`502/503/504\` | Gateway/upstream unavailable | Check upstream SLO, retry budget and circuit policy |
| Invalid JSON | Contract or proxy error | Capture sanitized status/content type, fail closed |
| Schema mismatch | Version/metric drift | Verify API version and update contract/tests |
| Payload too large | Unexpected response or abuse | Enforce cap and investigate |
| Redirect rejected | Unexpected target | Review trusted host and redirect policy |
| Certificate error | TLS trust/hostname mismatch | Repair CA/hostname; never disable verification |

## 10. Production runbooks
**API degradation:** identify impacted endpoint and error classes, compare SLO and retry amplification, reduce concurrency and apply safe failover if approved.

**Credential incident:** rotate/revoke through secret management, avoid logging token, verify scopes and audit access.

**Schema drift:** pin API version, compare sanitized response schema, patch validation and deploy through tests.

**Rate-limit incident:** stop aggressive polling, apply jittered backoff, adjust workload scheduling and coordinate with API owner.

**Rollback:** restore approved client version/configuration, rerun integration tests, validate SLO and document change approval.

## 11. Lab
[Chapter 071 — Reliable HTTP API Client SRE/DBRE Lab](labs/071-reliable-http-api-client-sre-dbre-lab.md) includes an executable loopback HTTP fixture server, a retrying API client, strict JSON validation, 20+ automated tests, fault injection, production runbooks and a 100-point assessment.

**Next:** Chapter 072 — Python HTTP Authentication, API Security and Production Client Patterns (proposed; not yet in the master curriculum).
