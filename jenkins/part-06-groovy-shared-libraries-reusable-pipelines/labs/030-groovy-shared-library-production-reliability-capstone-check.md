# Chapter 030 — Enterprise Hands-on Capstone: Groovy and Shared Library Production Reliability

**Scope:** Disposable Jenkins and Git fixtures. Do not connect production secrets, customer repositories or deployment targets.

## Setup

Use Chapters 026–029 as reference. Prepare a reviewed shared-library repository with `vars/`, `src/`, `resources/`, and unit/mock tests; one Maven fixture and one Gradle fixture; a disposable Jenkins controller; an isolated Linux agent; JUnit and Workspace Cleanup plugins; and at least one known-good immutable library tag.

Record starting Jenkins core/plugin versions, agent label/image, library commit, fixture SHAs, and reviewer.

## 20 capstone labs

| # | Exercise | Execution | Acceptance evidence |
|---|---|---|---|
| 01 | Architecture review | Diagram controller, library SCM and agents | Boundaries and trust documented |
| 02 | Library inventory | Verify all `vars/`, `src/`, `resources/` files | Repository tree |
| 03 | API contract | Document keys, defaults, return values, errors | Versioned API table |
| 04 | Config validation | Run valid and invalid input tests | Positive/negative results |
| 05 | Command allowlist | Attempt injected buildTool | Rejected before `sh` |
| 06 | Groovy unit tests | Run pure `src/` tests | Runner report |
| 07 | Pipeline mock tests | Verify allowed Maven/Gradle commands | Captured invocations |
| 08 | Release provenance | Create reviewed protected candidate tag | Tag → commit SHA |
| 09 | Controller integration | Register library in disposable Jenkins | Resolved revision |
| 10 | Maven fixture | Execute Checkout/Validate/Build/Test/Archive | Stages, JUnit, artifact |
| 11 | Gradle fixture | Execute equivalent fixture | Stages, JUnit, artifact |
| 12 | Artifact audit | Check fingerprints and retention | Archive evidence |
| 13 | Negative fixture | Introduce failing unit test | Fail-closed result |
| 14 | Timeout | Use a disposable slow command/test fixture | Abort and cleanup |
| 15 | Agent interruption | Temporarily take isolated agent offline | Triage and recovery |
| 16 | SCM retrieval failure | Point canary to nonexistent tag | Diagnostic record |
| 17 | CPS resilience | Run a controlled restart test on disposable Jenkins | Resume outcome documented |
| 18 | Canary upgrade | Upgrade one consumer to candidate | Comparison against baseline |
| 19 | Breaking change | Publish intentionally incompatible test ref | Canary fails; baseline unaffected |
| 20 | Rollback and assessment | Restore known-good tag and score rubric | Verified recovery and 100-point score |

## 15 troubleshooting drills

1. `vars/` step missing or renamed.
2. Wrong `src/` package declaration.
3. Invalid `resources/` lookup.
4. Nonexistent library version.
5. Untrusted library sandbox rejection.
6. Nonserializable object retained across a Pipeline suspension.
7. Maven unavailable on the selected agent.
8. Gradle wrapper permission failure.
9. Invalid command input.
10. Missing JUnit report XML.
11. Artifact glob mismatch.
12. Agent queue starvation.
13. Test command exceeds timeout.
14. Canary regression after a library API change.
15. Rollback to an incompatible previous consumer configuration.

For each drill, record **symptom → evidence → hypothesis → safe correction → retest**. If a drill cannot be executed in the disposable environment, mark it blocked rather than inventing results.

## Useful commands

```bash
git status --short
git rev-parse HEAD
git tag --list
git rev-parse 'v1.2.0^{commit}'
git show --stat --oneline v1.2.0
# On an isolated Linux build agent:
df -h
free -m
java -version
git --version
```

Use a tag that actually exists in your test repository; `v1.2.0` is illustrative. Run unit tests through the configured pinned build tool, e.g. `./gradlew clean test`, and capture its exit code.

## Evidence and incident record

```text
Exercise/drill ID:
UTC timestamp:
Controller core/plugins:
Library tag + resolved SHA:
Fixture commit SHA:
Agent image/label:
Expected outcome:
Observed outcome:
Logs/test reports/artifacts:
Root cause:
Remediation:
Retest result:
Rollback version / duration:
Reviewer:
```

## Final 100-point evaluation

| Area | Points |
|---|---:|
| Architecture and library separation | 15 |
| Secure validation and command controls | 15 |
| Unit and Pipeline mock tests | 15 |
| Jenkins integration and two consumers | 15 |
| Observability and audit evidence | 10 |
| Fault injection and incident triage | 10 |
| Versioning and release governance | 10 |
| Canary and verified rollback | 10 |
| **Total** | **100** |

Pass at **85 or more**, subject to all critical gates: no credential leak, no arbitrary command execution, immutable release provenance, no production impact, and verified rollback.

## Final sign-off checklist

- [ ] All 20 capstone exercises attempted and recorded.
- [ ] All 15 drills completed or explicitly blocked.
- [ ] Maven and Gradle fixture builds pass.
- [ ] Positive and negative tests pass.
- [ ] Library version and commit are traceable.
- [ ] Test reports and artifacts verified.
- [ ] Canary detects a breaking change.
- [ ] Rollback recovers the known-good consumer.
- [ ] Reviewer signs the acceptance score and open risks.

**Chapter:** [030 — Production Reliability Capstone](../030-groovy-shared-library-production-reliability-capstone.md).  
**Next:** Chapter 031 — Jenkins Git and SCM Integration Fundamentals.
