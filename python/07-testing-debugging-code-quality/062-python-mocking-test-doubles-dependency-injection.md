# Chapter 062 — Python Mocking, Test Doubles and Dependency Injection

**Part 07 — Testing, Debugging and Code Quality | Python 3.11+ | 6–8 hours**

## Objectives
Design testable SRE/DBRE adapters; distinguish stubs, fakes, spies and mocks; use \`unittest.mock.Mock\`, \`MagicMock\`, \`AsyncMock\`, \`patch\` and \`side_effect\`; inject clients and clocks; simulate transient failures without sleeping; and validate safe retry/deadline policies.

## 1. Why operational automation needs test doubles
Real PostgreSQL, Elasticsearch and Kafka connections make unit tests slow, fragile and potentially destructive. Dependency injection lets tests replace network clients, clocks and retry policies with deterministic objects. A mock verifies interactions; a stub returns configured values; a fake implements lightweight working behavior; a spy records calls. The distinction is conceptual rather than enforced by Python types.

## 2. Dependency inversion and Protocol
\`\`\`python
from typing import Protocol
class Client(Protocol):
    async def read(self, engine: str, service: str) -> dict[str, object]: ...
\`\`\`
Pass \`Client\` and \`Clock\` as arguments instead of constructing live SDK clients inside business logic. The lab uses structural Protocol typing, an in-memory \`FakeClient\`, and a \`FakeClock\`. Python type hints do not validate runtime inputs.

## 3. Mock and MagicMock
\`Mock\` records call arguments and can supply \`return_value\`, \`side_effect\` and \`spec\`. Use \`spec_set\` or \`autospec\` where practical to catch invalid attribute access. \`MagicMock\` supplies magic methods, such as \`__enter__\` and \`__exit__\`, for testing context managers. Do not use a mock as a substitute for real integration contract testing.

## 4. AsyncMock
Async methods require await-aware doubles:
\`\`\`python
from unittest.mock import AsyncMock
client.read = AsyncMock(return_value=synthetic_reading)
result = await client.read("postgresql", "pg-replica")
client.read.assert_awaited_once_with("postgresql", "pg-replica")
\`\`\`
A plain \`Mock\` is not a reliable substitute for an awaited coroutine. Inspect \`await_count\`, \`await_args_list\` and \`assert_awaited_once_with\` for asynchronous interactions.

## 5. patch and lookup sites
Patch **where the name is looked up**, not where it was originally declared. For example, if \`my_module\` imports \`from clock import monotonic\`, patch \`my_module.monotonic\`. Use context-manager or decorator scope so patches are restored even when assertions fail. Avoid global patches leaking into other tests.

## 6. side_effect and failure injection
\`side_effect\` can raise an exception, call a function or return a sequence of outcomes. The lab scripts a transient failure followed by success to verify retry counts. For async clients, use \`AsyncMock(side_effect=[TransientReadError(...), reading])\`. Never retry permanent validation errors or uncertain non-idempotent writes.

## 7. Fake clocks and deadlines
Wall-clock sleeps make tests slow and flaky. Inject a monotonic clock and a sleep abstraction; a fake advances simulated time immediately. This is useful for deterministic backoff assertions. **Important limitation:** fake time cannot interrupt a hung awaited network operation. Production code still needs real I/O timeouts, cooperative cancellation and an overall deadline enforced by the runtime or driver.

## 8. Retry and testability contracts
The lab uses at most five attempts, exponential backoff, strict schema validation, source identity checks and a synthetic deadline. Backoff is capped by validated input but does not include jitter, which real distributed clients should use. No production network I/O is performed.

## 9. Architecture
\`\`\`text
test runner
   |---- Mock / MagicMock / AsyncMock / patch
   |---- FakeClock (monotonic + sleep)
   |---- FakeClient (stateful scripted responses)
   v
fetch_with_retry(Client, Clock)
   -> schema and source identity validation
   -> bounded retry / deadline checks
   -> deterministic SRE/DBRE alert classifier
   -> sanitized JSON report
\`\`\`

| Engine | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag seconds | 30 | 120 |
| Elasticsearch | search_latency milliseconds | 200 | 500 |
| Kafka | consumer_lag messages | 1,000 | 10,000 |

These thresholds and telemetry readings are synthetic training data.

## 10. Troubleshooting
| Symptom | Cause | Remedy |
|---|---|---|
| Patch has no effect | Wrong lookup target | Patch importing module's symbol |
| Mock unexpectedly accepts typo | No spec/autospec | Use spec_set or autospec |
| Async test fails on await | Mock instead of AsyncMock | Use await-aware double |
| Retry test takes seconds | Real clock and sleep | Inject fake monotonic clock |
| Flaky test order | Shared fake state | New fixture per test |
| False green test | Mock behavior differs from SDK | Add isolated contract tests |
| Deadline not enforced | Fake time only | Add real driver/async timeout |
| Credentials in logs | Unsanitized mock exception | Redact errors and fixtures |

## 11. Production runbooks
**Mock drift:** compare fake responses with provider schemas in isolated contract tests, update fake and rerun safety checks.

**Retry incident:** inspect attempts and error taxonomy, stop unsafe retries, enforce rate limits and total deadlines.

**Clock-dependent flakes:** replace sleeps with fake monotonic time and deterministic scheduling.

**Credential leak:** remove unsafe fixture/logging, rotate exposed credentials if real, and add redaction tests.

**Rollback:** restore prior client adapter and test double, rerun deterministic and integration gates, then resume deployments.

## 12. Lab
[Chapter 062 — Mocking and Dependency Injection SRE/DBRE Lab](labs/062-mocking-test-doubles-dependency-injection-sre-dbre-lab.md) provides complete executable code, automated tests, fake clocks, fake clients, interaction assertions, failure simulations and a 100-point assessment.

**Next:** Chapter 063 — Python Test Fixtures, Parameterization and Coverage Engineering (provisional).
