# Chapter 061 — Python Testing Foundations with unittest and pytest

**Part 07 — Testing, Debugging and Code Quality | Python 3.11+ | 6–8 hours**

## Learning objectives
Design testable SRE/DBRE code; write assertions; distinguish unit, integration, contract and acceptance tests; use \`unittest.TestCase\`, pytest functions, fixtures and parameterization; isolate external dependencies with mocks; measure coverage and build safe CI quality gates.

## 1. Test pyramid for operational automation
**Unit tests** validate pure functions, thresholds, parsing and edge cases without live infrastructure. **Integration tests** validate adapters, serialization and persistence in isolated environments. **Contract tests** validate producer/consumer schemas and error handling. **Acceptance tests** exercise rollback, idempotency, safety and incident recovery. Never run destructive infrastructure tests against production by default.

## 2. Assertions and boundary testing
\`\`\`python
assert classify(Sample("pg", "postgresql", 30)).severity == "warning"
\`\`\`
An assertion is appropriate for test code, not for validating untrusted production input: \`python -O\` can remove \`assert\` statements. Production validation should raise explicit exceptions. Test exact boundaries (29.99, 30, 119.99, 120), malformed data, duplicates, empty input and resource caps.

## 3. unittest
\`unittest\` ships with Python. It supports \`TestCase\`, \`assertEqual\`, \`assertRaises\`, \`setUp\`, \`tearDown\`, \`subTest\`, test discovery and \`unittest.mock\`.

\`\`\`python
import unittest
class TestThreshold(unittest.TestCase):
    def test_warning(self):
        self.assertEqual(classify(Sample("pg","postgresql",30)).severity, "warning")
\`\`\`

Run \`python -m unittest discover -v -p 'test_unittest_*.py'\` from the lab directory. A \`subTest\` reports multiple cases in one test method but is not the same as pytest parameterization.

## 4. pytest
pytest uses simple test functions and plain \`assert\` with assertion introspection. Install and pin it in your project's development dependencies. Run \`python -m pytest -q\`. pytest can collect \`unittest.TestCase\` suites alongside pytest functions.

## 5. Fixtures and dependency isolation
A pytest fixture is a reusable setup function decorated with \`@pytest.fixture\`; scope can be function, class, module, package or session. Prefer function scope for mutable test data. For cleanup, use \`yield\` fixtures so teardown runs even when a test fails. Use \`tmp_path\` for isolated files and \`monkeypatch\` for temporary environment changes.

## 6. Parameterization
\`@pytest.mark.parametrize\` expands input/output tables into separate test cases. It is ideal for threshold boundaries, invalid schemas, OS variations and configuration matrices. Keep case IDs descriptive in larger suites.

## 7. Mocking
Use \`unittest.mock.Mock\`, \`AsyncMock\`, \`patch\` or pytest's \`monkeypatch\` to replace network clients, clocks, randomness and error paths. **Patch where the dependency is looked up**, not where it was originally defined. Assert both outcomes and interactions (for example, \`assert_called_once_with\`). Over-mocking implementation details makes tests brittle; prefer dependency injection for operational adapters.

## 8. Coverage
Coverage answers which code ran, not whether the tests are meaningful. With optional \`pytest-cov\`:
\`\`\`bash
python -m pip install pytest pytest-cov
python -m pytest -q --cov=telemetry_tests_lab --cov-branch --cov-report=term-missing
\`\`\`
Aim for high coverage of safety-critical branches and failure paths. Avoid inventing a passing percentage without execution. Combine coverage with mutation testing, boundary cases and incident simulations.

## 9. CI quality gates
Recommended stages: compile and lint, deterministic unit tests, pytest tests, branch coverage, dependency vulnerability scanning, isolated integration tests, manual approval for any production-impacting actions. Pin dependencies and isolate secrets. Treat flaky tests as defects, not as candidates for unconditional retries.

## 10. SRE/DBRE lab architecture
\`\`\`text
synthetic PostgreSQL / Elasticsearch / Kafka telemetry
  -> Reader dependency injection
  -> strict schema validation
  -> deterministic alert classifier
  -> sanitized JSON summary
  -> unittest + pytest + mocks + parameterized boundaries
  -> optional coverage reporting
\`\`\`

| Engine | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag seconds | 30 | 120 |
| Elasticsearch | search_latency milliseconds | 200 | 500 |
| Kafka | consumer_lag messages | 1,000 | 10,000 |

All values and thresholds are synthetic. No real database, cluster or broker connections.

## 11. Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| Tests not discovered | Naming or working directory | Use test_*.py and explicit discovery |
| ImportError | Wrong interpreter or path | Run from project root with python -m |
| Mock not applied | Wrong patch target | Patch lookup site |
| Flaky tests | Shared state, clock, sleeps | Isolate fixtures, fake clock |
| Coverage low | Uncovered error branches | Add negative and boundary cases |
| CI differs from local | Python/dependency drift | Pin versions and environment |
| Secrets in test output | Unsafe fixture/logging | Synthetic credentials and redaction |

## 12. Production runbooks
**CI regression:** identify first failing commit, reproduce in pinned environment, quarantine unsafe deployment and roll back changes.

**Flaky test incident:** capture failure seeds and environment, remove timing dependencies and repair isolation before restoring gate.

**Mock drift:** compare adapter contract with production API, add contract tests and update fake behavior.

**Coverage regression:** inspect missed branches, prioritize safety-critical validation and failure handling, and enforce reviewed thresholds.

**Rollback:** restore known-good tests and code, rerun all gates and document exceptions with approval.

## 13. Hands-on lab
[Chapter 061 — Testing Foundations SRE/DBRE Lab](labs/061-testing-foundations-unittest-pytest-sre-dbre-lab.md) provides complete source, unittest and pytest suites, fixtures, parameterization, mocks, coverage commands, incident simulations and a 100-point assessment.

**Next:** Chapter 062 — Python Mocking, Test Doubles and Dependency Injection (provisional).
