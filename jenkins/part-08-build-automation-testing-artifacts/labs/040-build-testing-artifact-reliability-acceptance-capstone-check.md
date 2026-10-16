# Chapter 040 — Build, Testing and Artifact Reliability Capstone Lab

**Environment:** Disposable Jenkins, isolated Maven/Gradle/npm agents, synthetic fixture repos, nonproduction artifact registry and optional nonproduction SonarQube.

## 20 capstone exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Architecture | Draw SCM → CI → registry trust boundaries | Diagram |
| 02 | Ownership | Record pipeline, registry, agent owners | RACI |
| 03 | Toolchain | Record JDK, Node, Maven/Gradle/npm versions | Manifest |
| 04 | SCM provenance | Checkout pinned commit | Git SHA |
| 05 | Maven | Build/test fixture | JAR + test result |
| 06 | Gradle | Build/test fixture | JAR + test result |
| 07 | npm | Run `npm ci`, test and build | Lockfile + output |
| 08 | JUnit | Publish Maven and Gradle XML | Test counts |
| 09 | Coverage | Generate fixture coverage | Percentage |
| 10 | Quality gate | Apply enforced threshold | Gate result |
| 11 | SonarQube | Submit analysis and await gate if available | Task + gate |
| 12 | SHA256 | Hash produced artifact | Digest |
| 13 | Candidate publish | Upload to nonproduction registry | Coordinate |
| 14 | Download verification | Fetch candidate and compare digest | Hash match |
| 15 | Immutable release | Attempt collision on test version | Overwrite blocked |
| 16 | Credential boundary | Inspect untrusted job access | No publish token |
| 17 | Negative test | Inject failing assertion | Promotion blocked |
| 18 | Registry failure | Revoke test token or simulate 503 | Fail-closed |
| 19 | Rollback | Select previous approved digest | Verified artifact |
| 20 | Review | Score rubric and sign off | Acceptance report |

## 15 troubleshooting drills

1. Maven wrapper permission error.
2. Gradle dependency resolution failure.
3. npm lockfile mismatch.
4. Build agent offline.
5. Agent disk or inode exhaustion.
6. Unit test assertion failure.
7. JUnit XML missing.
8. Coverage gate fails.
9. SonarQube token expired.
10. SonarQube webhook unavailable.
11. Artifact publish 401/403.
12. Artifact version conflict.
13. Artifact registry storage quota reached.
14. Downloaded artifact digest mismatch.
15. Rollback artifact unexpectedly missing.

For each drill record observed error, relevant logs, root cause, containment, remediation, retest and recovery duration. Mark unavailable or unsafe drills blocked with explanation.

## Reproducible generic artifact fixture

```sh
set -eu
mkdir -p dist evidence
printf 'chapter-040 synthetic artifact\n' > dist/README.txt
tar -czf dist/candidate-1.0.0.tar.gz -C dist README.txt
sha256sum dist/candidate-1.0.0.tar.gz > evidence/candidate.sha256
git rev-parse HEAD > evidence/source-sha.txt
```

Publish to an approved nonproduction repository and download the exact coordinate. Compare SHA256 of downloaded bytes with the expected digest. Do not publish a mutable release or overwrite an existing coordinate.

## Evidence template

```text
UTC timestamp:
Jenkins controller/plugins:
Source repository and commit SHA:
Agent image and toolchain:
Maven/Gradle/npm build results:
JUnit tests passed/failed/skipped:
Coverage percentage and threshold:
SonarQube task and gate (if available):
Artifact coordinate/version:
Expected and downloaded SHA256:
Registry publish response:
Credential review:
Failure injection and recovery:
Rollback artifact/digest:
Score and reviewer:
```

## 100-point scorecard

| Category | Max |
|---|---:|
| Architecture and governance | 10 |
| Build correctness | 15 |
| Tests/JUnit | 15 |
| Coverage/static quality | 15 |
| Artifact provenance and immutability | 15 |
| Registry security | 10 |
| Observability | 5 |
| Failure injection | 10 |
| Recovery/rollback | 5 |
| **Total** | **100** |

## Acceptance checklist

- [ ] All 20 exercises attempted with evidence.
- [ ] All 15 troubleshooting drills completed or marked blocked.
- [ ] Maven, Gradle and npm builds validated.
- [ ] Tests, coverage and applicable quality gates enforced.
- [ ] Artifact source SHA and digest recorded.
- [ ] Downloaded artifact digest verified.
- [ ] Immutable release collision blocked.
- [ ] Credential isolation, recovery and rollback validated.
- [ ] Score at least 85/100 and critical gates passed.
- [ ] Reviewer signs off on outstanding risks.

**Related:** [Chapter 040 — Build, Testing and Artifact Reliability Capstone](../040-build-testing-artifact-reliability-acceptance-capstone.md).
