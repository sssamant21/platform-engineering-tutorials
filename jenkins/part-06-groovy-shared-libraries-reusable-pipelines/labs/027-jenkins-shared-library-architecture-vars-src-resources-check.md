# Chapter 027 — Companion Hands-on Lab: Jenkins Shared Library Architecture

**Environment:** Disposable Jenkins controller, isolated Linux agent, Git repository, Pipeline/Shared Libraries plugins. Do not run destructive tests on production controllers.

## Preparation

1. Create a dedicated library repository using the `vars/`, `src/` and `resources/` files from Chapter 027.
2. Commit and tag `v1.0.0`; record `git rev-parse HEAD` and `git show-ref --tags`.
3. Configure an appropriately trusted or untrusted `enterprise-ci` library in Jenkins.
4. Create a disposable Pipeline job pointing to the sample Jenkinsfile and select an isolated agent.

## Labs and expected results

| # | Exercise | Expected result / evidence |
|---|---|---|
| 1 | Validate Git layout and Groovy package paths | Three directories and matching `org/example/ci` package |
| 2 | Register SCM library at reviewed tag | Jenkins retrieves library with correct revision |
| 3 | Run sample staging Jenkinsfile | Validation stage succeeds |
| 4 | Invoke `validateInputs(environment: 'dev')` | Returns `dev` |
| 5 | Invoke `validateInputs(environment: 'production')` | Fails early with unsupported environment |
| 6 | Load defaults JSON using `libraryResource` | Timeout value is 15 |
| 7 | Rename resource path in disposable branch | Missing-resource error; restore path |
| 8 | Request nonexistent library tag | Controlled SCM resolution failure |
| 9 | Rename `vars/ciPipeline.groovy` in test branch | Global step resolution failure |
| 10 | Break `src/` package declaration in test branch | Compile/import error; restore package |
| 11 | Compare trusted and untrusted library policies | Document sandbox permissions and reviewer roles |
| 12 | Test secret-handling policy with a dummy credential | No credential appears in source or logs |
| 13 | Test two distinct pinned release tags | Consumers resolve requested revisions |
| 14 | Roll back from deliberately broken test tag | Last known good tag passes again |
| 15 | Run parallel canary consumers on isolated agents | Both complete with consistent behavior |
| 16 | Capture audit evidence and complete acceptance review | Revisions, logs, owner and rollback documented |

## Optional local unit test

Test the pure class without Jenkins Pipeline runtime using a compatible Groovy toolchain:

```groovy
import org.example.ci.BuildMetadata
assert BuildMetadata.normalizeEnvironment(' STAGING ') == 'staging'
try {
    BuildMetadata.normalizeEnvironment('invalid')
    assert false : 'Expected failure'
} catch (IllegalArgumentException expected) {
    assert expected.message == 'Unsupported environment'
}
println 'PASS'
```

For Pipeline step behavior, use Jenkins Pipeline Unit or an equivalent tested harness; pure Groovy tests alone do not prove Jenkins integration.

## Troubleshooting drills

1. SCM credentials invalid → rotate scoped credential and retry.
2. Missing tag → restore a valid immutable tag.
3. Incorrect global step name → fix `vars/` filename.
4. Incorrect package → fix `src/` path/package.
5. Missing resource → restore `resources/` path.
6. Invalid JSON → validate syntax before release.
7. Sandbox rejection → replace forbidden operation.
8. Serialization exception → eliminate nonserializable CPS state.
9. Agent unavailable → inspect labels, queue and provisioning.
10. Version drift → pin the reviewed release.
11. Library SCM outage → retry after recovery; do not silently fall back.
12. Leaked dummy credential → verify masking, eliminate logging and rehearse rotation.

## Operational evidence template

```text
Chapter: 027
Controller (non-sensitive identifier):
Library repository:
Pinned version:
Resolved commit:
Jenkins version / plugin baseline:
Agent label:
Lab IDs passed:
Failure drills passed:
Rollback version:
Reviewer:
Result: PASS / FAIL
```

## Final acceptance

PASS only when all core exercises succeed, invalid input fails safely, no secrets are logged, and rollback to a known-good immutable tag is demonstrated. Otherwise document remediation and rerun.
