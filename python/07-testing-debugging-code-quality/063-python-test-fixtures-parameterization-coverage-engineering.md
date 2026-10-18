# Chapter 063 — Python Test Fixtures, Parameterization and Coverage Engineering

**Part 07 — Testing, Debugging and Code Quality | Python 3.11+ | 6–8 hours**

## Learning objectives
Engineer isolated pytest fixtures, choose fixture scopes, use yield-based teardown, temporary paths, monkeypatching and parameterization, measure line and branch coverage with coverage.py/pytest-cov, and enforce meaningful quality gates for SRE/DBRE automation.

## 1. Fixture lifecycle and scope
A pytest fixture is a dependency injected into tests by name. The supported scopes are function, class, module, package and session. **Function** scope is the safest default for mutable state. Module and session scope can reduce setup cost but risk cross-test pollution. Shared scoped fixtures should return immutable data or defensive copies.

\`\`\`python
import pytest

@pytest.fixture
def sample():
    return {"value": 45}

def test_sample(sample):
    assert sample["value"] == 45
\`\`\`

## 2. Yield fixtures and cleanup
\`yield\` fixtures run setup before yielding and teardown afterward, including after test failures. Prefer \`try/finally\` inside complex fixtures and register cleanup immediately after acquiring each resource. Teardown code **after** a yield will not execute if setup fails before reaching the yield. For database integration tests, create disposable resources and explicitly roll back or delete them.

## 3. tmp_path and filesystem safety
\`tmp_path\` supplies a unique \`pathlib.Path\` for each test. Use it instead of fixed shared filenames, which can cause parallel CI collisions and accidental deletion. Never direct test cleanup at production paths. The lab reads bounded local JSON fixtures and rejects malformed/nonfinite data.

## 4. monkeypatch
The built-in \`monkeypatch\` fixture temporarily changes environment variables, module attributes, dictionaries and current directories, restoring state at teardown. Patch the dependency's lookup site. Avoid patching global builtins or pytest internals, which can destabilize the runner.

## 5. Parameterization
\`@pytest.mark.parametrize\` expands boundary tables into separate test cases. Cover healthy/warning/critical boundaries for PostgreSQL replication lag, Elasticsearch search latency and Kafka consumer lag. Test invalid units, booleans, NaN, Infinity, negative numbers, duplicates and oversized inputs. Prefer descriptive \`ids\` for large matrices.

## 6. coverage.py and pytest-cov
\`coverage.py\` instruments executed lines and branches. Branch coverage measures whether distinct control-flow paths ran, such as both the valid and rejected input cases.

\`\`\`bash
python -m pip install pytest pytest-cov coverage
python -m pytest -q --cov=telemetry_quality --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=90
python -m coverage report -m
\`\`\`

\`--cov-fail-under=90\` enforces an overall percentage threshold for the measured scope; it does **not** prove that every safety-critical branch was exercised. Avoid claiming a passing coverage score without executing the suite.

## 7. Coverage configuration
A small optional \`.coveragerc\` file:
\`\`\`ini
[run]
branch = True
source = telemetry_quality

[report]
show_missing = True
fail_under = 90
exclude_also =
    if __name__ == .__main__.:
\`\`\`

Do not exclude complex validation or exception branches just to raise coverage. Document intentional exclusions and review them in code review.

## 8. Test engineering and CI
Recommended gates: syntax, formatting/linting, pytest collection, deterministic unit tests, branch coverage, isolated integration tests, dependency scanning and manual approval for production-affecting actions. Pin development dependencies and keep test fixtures synthetic. Coverage should be measured in the same interpreter/environment used by CI. A low or flaky result blocks promotion; do not rerun until green without root-cause analysis.

## 9. SRE/DBRE architecture
\`\`\`text
synthetic PostgreSQL / Elasticsearch / Kafka JSON fixtures
       -> tmp_path and monkeypatch isolation
       -> strict validation and alert classification
       -> parameterized pytest safety cases
       -> coverage.py branch measurement
       -> CI quality threshold and sanitized report
\`\`\`

| Engine | Metric | Warning | Critical |
|---|---|---:|---:|
| PostgreSQL | replication_lag seconds | 30 | 120 |
| Elasticsearch | search_latency milliseconds | 200 | 500 |
| Kafka | consumer_lag messages | 1,000 | 10,000 |

All thresholds are synthetic, not production SLO recommendations.

## 10. Troubleshooting
| Symptom | Likely cause | Recovery |
|---|---|---|
| Fixture not found | Incorrect conftest scope | Inspect fixture discovery and imports |
| Test order dependence | Shared mutable scoped fixture | Use function scope or copy data |
| Teardown leak | Setup fails before yield | Register cleanup immediately |
| tmp_path test fails | File not created or wrong encoding | Verify path and UTF-8 |
| monkeypatch ineffective | Wrong lookup target | Patch module reference |
| Branch coverage low | Missing negative paths | Add rejected-input and boundary cases |
| CI coverage differs | Different test selection or interpreter | Pin versions and coverage configuration |
| Coverage gate fails | Threshold unmet | Add meaningful tests; review omissions |

## 11. Production runbooks
**Coverage regression:** identify missing branches and changed code, prioritize safety-critical paths, block unsafe deployment and add tests.

**Flaky fixture incident:** reproduce with random test order, isolate state and resources, remove shared filesystem paths.

**Unsafe cleanup:** stop test execution, inspect paths and permissions, restore affected data from verified backups if necessary, and replace cleanup with tmp_path isolation.

**CI environment drift:** compare Python, pytest and coverage versions, lock dependencies and rerun in a clean environment.

**Rollback:** restore known-good code and tests, rerun quality gates, record approval and monitor deployment.

## 12. Hands-on lab
[Chapter 063 — Fixtures, Parameterization and Coverage SRE/DBRE Lab](labs/063-fixtures-parameterization-coverage-sre-dbre-lab.md) provides complete Python code, pytest tests, coverage commands, CI workflow, incident simulations and a 100-point assessment.

**Next:** Chapter 064 — Python Property-Based Testing and Hypothesis (provisional).
