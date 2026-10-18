# Chapter 072 — Python HTTP Authentication, API Security and Production Client Patterns

**Part 08 — APIs, Networking and Databases | Python 3.11+ | 10–14 hours**

## Goals
Design secure HTTP clients and service endpoints for SRE/DBRE workflows. Implement API keys and bearer tokens safely, understand OAuth 2.0 client credentials and token lifecycles, enforce TLS and trusted hosts, avoid credential leaks across redirects, classify authentication failures, handle 429/503 with bounded retries, and test the security contract using a disposable local HTTP server.

## Architecture
\`\`\`text
approved secret manager -> short-lived credential provider
                               |
Python client -> URL allowlist -> TLS/hostname validation -> Authorization header
      |                                                |
      +-- bounded GET retry (429/503) <- 401/403 terminal, no retry
      |                                                |
      +-- JSON contract and size limit <- local simulated API
      |
      +-- sanitized structured diagnostics (never tokens)
\`\`\`

## 1. API keys
An API key identifies a caller or project; its security properties depend on the provider. Send keys in an approved header such as \`X-API-Key\` rather than URLs. Restrict scopes, rotate keys, maintain separate credentials per environment and store in an approved secret manager. Do not embed keys in source, shell history, metrics labels or logs. API keys do not automatically provide user-level authorization.

## 2. Bearer tokens and OAuth 2.0
A bearer token grants access to whoever possesses it. The \`Authorization: Bearer <token>\` header is appropriate only over verified HTTPS in production. OAuth 2.0 is an authorization framework, not an authentication protocol; OpenID Connect adds an identity layer. Client credentials flow is suited to machine-to-machine services where supported. An OAuth client authenticates to a token endpoint, receives an access token, caches it until near expiration and refreshes/reacquires according to provider policy. Do not assume refresh tokens are issued with client credentials. Scope tokens narrowly; verify issuer/audience/expiry at the **resource server** according to token format and trust policy. Do not confuse decoding a JWT with validating its signature.

## 3. TLS, mTLS and certificate trust
HTTPS protects tokens in transit only when certificate chain, hostname and protocol validation remain enabled. Use default \`ssl.create_default_context()\` or provider-approved trust bundles. Never use \`verify=False\` or unverified contexts. mTLS adds client certificate authentication; protect private keys and rotate certificates. A loopback-only HTTP fixture is acceptable for a synthetic lab; it must not be used as a production security pattern.

## 4. Headers and redirects
Avoid tokens in query strings. Validate \`Content-Type\` and \`Accept\`; set \`Cache-Control: no-store\` for sensitive responses. Limit allowed hosts and reject redirects unless their destinations are independently verified; cross-origin redirects can leak credentials. Avoid following redirect chains with authorization headers by default. Correlation IDs should be validated and should never contain credentials.

## 5. Authentication failure semantics
\`401 Unauthorized\` means authentication is absent or invalid and can include \`WWW-Authenticate\`; \`403 Forbidden\` means the request is understood but access is denied. Do not repeatedly retry either status with the same credential. Refresh or rotate credentials through an approved workflow with a strict retry budget and never leak token values to diagnostics. \`429\` indicates rate limiting; \`503\` indicates temporary service unavailability. Retry only safe/idempotent requests.

## 6. Retry, backoff and rate limits
Use a bounded attempt count, exponential delay and jitter. Interpret \`Retry-After\` as seconds or HTTP-date when supported, cap delays and honor an overall request budget. Never retry POST automatically without a provider-supported idempotency key and documented semantics. Control concurrency, prevent retry storms and use circuit breakers where needed.

## 7. Input validation and SSRF
Never fetch arbitrary user-provided URLs. Allowlist scheme, host, port and path; reject embedded credentials, fragments, redirects, IP literal surprises and DNS rebinding risks. Limit response body size and parse only expected JSON fields. Treat external status messages and error bodies as untrusted, especially in logs.

## 8. Operational observability
Track status class, latency, attempts, rate limiting and sanitized error categories. Never record raw Authorization, API keys, client secrets, cookies, full URLs with sensitive query strings or complete response bodies. Maintain metrics cardinality using stable route templates. Use alerting on sustained SLO degradation, not individual expected 401 tests.

## 9. SRE/DBRE incident simulations
1. PostgreSQL monitoring API key is invalid: 401, no retry, escalate credential rotation.
2. Elasticsearch telemetry API rejects scope: 403, check least-privilege role assignments.
3. Kafka lag API returns 429: bounded retry and reduced polling.
4. Gateway returns 503 once: retry GET, verify recovery.
5. Service redirects to attacker host: refuse redirect; no token leak.
6. Invalid TLS certificate: fail closed and repair trust chain.
7. Expired OAuth access token: reacquire via approved token provider, not blind retry.
8. Oversized JSON payload: reject before parsing.
9. Unexpected response content type: reject contract drift.
10. Token accidentally appears in logs: block promotion, rotate and investigate.
11. Retry budget exhaustion: emit sanitized failure and preserve service stability.
12. Credential reused across staging and production: separate identities and scopes.

## 10. Troubleshooting
| Symptom | Investigation | Safe response |
|---|---|---|
| 401 | Token expiry, key rotation, wrong audience | Reacquire/rotate through approved flow |
| 403 | Missing scope or RBAC | Request least-privilege access |
| 429 | Rate-limit headers and polling load | Bounded backoff, reduce concurrency |
| 503 | Gateway/upstream saturation | Limited GET retries, incident triage |
| TLS verification failure | CA, hostname, certificate lifetime | Fix trust, never disable validation |
| Redirect rejection | Unexpected Location target | Verify destination out of band |
| Malformed JSON | Upstream version/schema | Contract test, no blind retry |
| Unexpected secrets in logs | Handler, proxy or exception serialization | Revoke/rotate, sanitize, audit |

## 11. Runbooks
**Credential compromise:** revoke immediately, rotate in secret manager, review access logs, invalidate caches and document incident.

**OAuth token failure:** verify issuer/audience/scope and clock skew; refresh/reacquire only via trusted provider, cap retries and never log tokens.

**TLS outage:** inspect certificate chain/hostname/CA trust, coordinate rotation, verify mTLS identity and refuse insecure bypass.

**429 storm:** reduce poll frequency/concurrency, apply bounded jittered backoff and coordinate quota changes.

**403 authorization drift:** compare approved role/scope policy with deployment identity, restore least privilege and audit changes.

**Rollback:** restore last approved client and credential configuration, run synthetic integration tests, validate error rates and record approval.

## 12. Lab and assessment
[Chapter 072 — Secure HTTP Authentication and API Client SRE/DBRE Lab](labs/072-secure-http-authentication-api-client-sre-dbre-lab.md) contains complete Python source, a loopback HTTP server, automated tests, fault injection, CI example, security runbooks and a 100-point acceptance rubric. The fixture demonstrates header authentication, **not** a full OAuth provider, JWT validator or TLS endpoint; those require separate provider-specific integration tests.

**Next proposed:** Chapter 073 — Python HTTP Requests, Sessions, Pagination and Resilient API Integrations.
