# Chapter 037 — Hands-on Lab: Automated Testing, JUnit and Quality Gates

**Environment:** Disposable Jenkins, isolated Python agent, test repository with `app/calculator.py`, `tests/test_calculator.py` and pinned pytest dependencies. Do not use production data or secrets.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Tool inventory | Record Jenkins, JUnit plugin, Python | Versions |
| 02 | Fixture repository | Commit calculator and test | SHA |
| 03 | Dependency pinning | Review pytest/coverage pins | Dependency record |
| 04 | Isolated agent | Verify agent label/workspace | Agent identity |
| 05 | Checkout | Run `checkout scm` | Exact SHA |
| 06 | Virtualenv | Create `.venv` | Environment |
| 07 | Unit test | Run pytest | Pass result |
| 08 | JUnit generation | Add `--junitxml` | XML present |
| 09 | JUnit publishing | Use Jenkins `junit` | Test trend |
| 10 | Coverage | Generate coverage XML | Coverage percentage |
| 11 | Coverage gate | Set `--cov-fail-under=80` | Gate evidence |
| 12 | Negative assertion | Change expected value | Build fails |
| 13 | Missing report | Change report glob in fixture | Fail-closed behavior |
| 14 | Zero test discovery | Run empty test directory | Detection |
| 15 | Integration fixture | Add isolated dependency test | Suite result |
| 16 | Parallel suites | Run unit/integration on separate agents | Per-stage reports |
| 17 | Test timeout | Bound test runtime | Timeout evidence |
| 18 | Flake simulation | Introduce controlled nondeterminism | Initial failure recorded |
| 19 | Failure recovery | Restore fixture and agent | Successful retest |
| 20 | Quality review | Verify gate, SHA, report and reviewer | Acceptance record |

## 12 troubleshooting drills

1. Wrong JUnit glob.
2. Malformed JUnit XML.
3. Zero tests collected.
4. Coverage threshold fails.
5. Test runner exits before writing XML.
6. Parallel agent workspace mismatch.
7. Integration service unavailable.
8. Dependency install TLS/registry failure.
9. Agent OOM or timeout.
10. Test flakiness under concurrency.
11. Status publisher reports wrong SHA.
12. Secret appears in test logs.

Capture symptom, logs, test count, XML path, root cause, remediation and retest. Mark drills blocked if unavailable or unsafe.

## Fixture source

`app/calculator.py`:
```python
def add(a, b):
    return a + b
```

`tests/test_calculator.py`:
```python
import unittest
from app.calculator import add

class CalculatorTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
```

`requirements-test.txt`:
```text
pytest==8.3.5
pytest-cov==6.0.0
```

Run:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-test.txt
mkdir -p reports/junit reports/coverage
python -m pytest tests --junitxml=reports/junit/unit.xml \
  --cov=app --cov-report=xml:reports/coverage/coverage.xml \
  --cov-fail-under=80
```

## Evidence template

```text
UTC timestamp:
Repository and SHA:
Jenkins build/agent:
Python and pytest versions:
Tests collected/passed/failed/skipped:
JUnit XML path:
Coverage percent and gate:
Stage duration:
Injected fault:
Root cause:
Recovery:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 12 drills completed or marked blocked.
- [ ] Real unit test executes and publishes JUnit XML.
- [ ] Coverage threshold enforced.
- [ ] Failed assertion, missing report and zero-test conditions detected.
- [ ] Parallel test report handling validated.
- [ ] Flaky-test and infrastructure failure handling documented.
- [ ] No production secrets or data used.

**Related:** [Chapter 037 — Automated Testing and Quality Gates](../037-jenkins-automated-testing-junit-reporting-quality-gates.md).
