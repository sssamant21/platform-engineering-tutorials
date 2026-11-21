# V06 — Offline regression evidence record (blank template)

**Status:** TEMPLATE ONLY — no execution or PASS result is implied. **Scope:** `openshift/` only. Use with [V06 protocol](V06-offline-regression-execution-protocol.md).

## Identity and isolation

| Field | Evidence (fill only after execution) |
| --- | --- |
| UTC timestamp | NOT RUN |
| Repository / branch / exact commit SHA | NOT RECORDED |
| Runner OS and version | NOT RECORDED |
| Python / Bash / PowerShell versions | NOT RECORDED |
| Temporary HOME and nonexistent KUBECONFIG confirmed | NOT VERIFIED |
| Real `oc` excluded from mock execution | NOT VERIFIED |
| Reviewer / evidence sanitizer | NOT ASSIGNED |

**Safety stop:** Do not execute worksheet code directly or against a real cluster. The Python tests invoke only their isolated mocks. If the mock setup is uncertain, mark BLOCKED and stop. Never record token values, kubeconfig contents, raw credentials or identifiable production endpoints.

## Command-level results

Run each command from the repository root, in a disposable environment, following the protocol. Fill counts from the actual test runner output; do not infer PASS from exit code alone.

| Suite / exact command | Expected authored cases | Executed | PASS | FAIL | ERROR | SKIP | Exit code | Evidence path |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `python -m unittest discover -s openshift/tests -p 'test_v05_bash_identity_guard.py' -v` | 14 | NOT RUN | — | — | — | — | — | — |
| `python -m unittest discover -s openshift/tests -p 'test_v05_powershell_identity_guard.py' -v` | 10 | NOT RUN | — | — | — | — | — | — |
| `python -m unittest discover -s openshift/validation -p 'test_*.py' -v` | Determine at runtime | NOT RUN | — | — | — | — | — | — |
| `python openshift/validation/check_relative_links.py` | Link targets, not test cases | NOT RUN | — | — | — | — | — | — |

**Classification:** PASS only when executed and assertions succeed; FAIL for assertion failure; ERROR for unexpected test exception; SKIP for an intentionally skipped test (for example, missing `pwsh`); BLOCKED if prerequisites prevent starting a suite. Link-audit exit 0 establishes only local target existence, not external URL reachability or anchor correctness.

## Failure triage

For each failure, record: test name, sanitized error, observed vs expected behavior, worksheet/test defect classification, fix commit SHA, rerun command, rerun outcome, and independent reviewer. Failures in identity, authorization or read-error handling are safety blockers. Do not weaken an assertion merely to make a test pass; first establish the intended fail-closed behavior.

## Release gate

- [ ] Full offline suites executed with recorded counts and sanitized evidence
- [ ] Link audit executed and all missing local targets resolved
- [ ] Version-sensitive claims reviewed against authoritative OpenShift 4.22 documentation
- [ ] Authorized isolated OCP cluster exercises completed with evidence
- [ ] Independent platform/DBRE review and least-privilege assessment completed
- [ ] Change approval, recovery/rollback and RPO/RTO evidence completed where applicable

**Decision: NOT PRODUCTION APPROVED.** This template must never be interpreted as a certification record without independently verified evidence.
