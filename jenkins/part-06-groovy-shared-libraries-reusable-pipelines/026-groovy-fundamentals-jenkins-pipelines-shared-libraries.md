# Chapter 026 — Groovy Fundamentals for Jenkins Pipelines and Shared Libraries

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 06:** Groovy, Shared Libraries and Reusable Pipelines  
**Chapter:** 026 / 100  
**Companion lab:** [Chapter 026 — Groovy Fundamentals Check](labs/026-groovy-fundamentals-check.md)

> **Safety:** Groovy in Jenkins Pipelines is controller-side orchestration, not a place for heavy computation or untrusted shell execution. Keep controller built-in executors at zero. The runnable Scripted Pipeline below requires no agent, shell, workspace, credentials or external integrations.

## 1. Learning objectives

Understand Groovy variables, types, truth, strings, lists, maps, ranges, conditions, loops, closures, methods, regex, exceptions and null handling in the Jenkins Pipeline CPS environment. Learn how these concepts support future shared libraries, how Script Security applies, and how to avoid serialization, performance and credential failures.

## 2. Prerequisites and architecture

Complete Chapters 021–025. Have a disposable Jenkins LTS controller with Pipeline plugins and a named admin. Do not install unnecessary plugins or change production Script Approval settings.

```text
protected SCM -> Jenkinsfile (Groovy)
                       |
                 Scripted control
             variables/maps/closures
                       |
                Jenkins steps
                 echo / error
                       |
             node('trusted-agent')
                only when needed
                       |
             workspace/build/test
                       |
                 audit/results
```

Groovy is the language, Pipeline steps are Jenkins APIs, and CPS is the transformation enabling suspension/resumption. They are related but not interchangeable.

## 3. Variables, types and Groovy truth

```groovy
def service = 'orders'
String environment = 'dev'
int retries = 2
boolean dryRun = true
def threshold = 0.95
assert service instanceof String
assert retries == 2
assert dryRun
assert !''
assert 'false'  // Nonempty string is truthy: never use it as a boolean.
```

In Pipelines use `params.DRY_RUN` as a typed boolean and explicitly validate externally supplied strings. Use `def` for local state rather than undeclared global bindings.

## 4. Strings, GStrings and safe interpolation

```groovy
def target = 'staging'
def interpolated = "target=${target}"
def literal = 'target=${target}'
echo interpolated
echo literal
```

Double-quoted strings interpolate Groovy expressions; single-quoted strings do not. **Never** interpolate credentials into a shell command or log line. Prefer scoped Jenkins credential bindings and single-quoted shell scripts that let the shell expand variables in a trusted isolated agent.

## 5. Lists, maps and ranges

```groovy
def stages = ['validate', 'test', 'package']
def config = [dev: [region: 'us-east-1'], staging: [region: 'us-west-2']]
assert stages.size() == 3
assert config['dev']['region'] == 'us-east-1'
assert (1..3).toList() == [1, 2, 3]
```

Validate map keys before dereferencing. Avoid retaining large collections across Pipeline suspension points.

## 6. Conditions and switch

```groovy
def target = 'dev'
if (!(target in ['dev', 'staging'])) {
  error('Unapproved environment')
}
switch (target) {
  case 'staging': echo 'Staging dry run'; break
  default: echo 'Development dry run'
}
```

Avoid relying on implicit truth for user-controlled parameters.

## 7. Loops and closures

```groovy
def checks = ['syntax', 'security', 'quality']
checks.each { item ->
  echo "Checking ${item}"
}
for (int i = 0; i < 2; i++) {
  echo "Iteration ${i}"
}
```

Use small bounded loops. Groovy closures may capture mutable variables; do not share such state across parallel branches without isolation.

## 8. Methods and reusable pure logic

```groovy
def normalizeTarget(String input) {
  def value = input?.trim()?.toLowerCase()
  if (!(value in ['dev', 'staging'])) {
    throw new IllegalArgumentException('Invalid target')
  }
  return value
}
```

Keep reusable helpers small, deterministic and easy to test. The next chapters will move them into trusted `vars/` and `src/` shared-library layouts.

## 9. Regex, null safety and validation

```groovy
def release = 'v1.2.3'
assert release ==~ /^v[0-9]+\.[0-9]+\.[0-9]+$/
def optional = null
assert optional?.trim() == null
```

Use fully anchored patterns and explicit allowlists. Null-safe navigation avoids an exception but does not replace validation of required inputs.

## 10. Runnable no-agent Scripted Jenkinsfile

Create a Pipeline job with choice parameter `TARGET` (dev/staging) and boolean `FORCE_FAIL` (default false). Paste:

```groovy
def allowedTargets = ['dev', 'staging']
def selected = params.TARGET ?: 'dev'
def settings = [dev: [region: 'us-east-1', attempts: 1],
                staging: [region: 'us-west-2', attempts: 2]]
def events = []
def result = 'SUCCESS'

try {
  stage('Validate') {
    if (!allowedTargets.contains(selected)) {
      error('Unapproved target')
    }
    echo "Target=${selected}"
  }
  stage('Collections') {
    def cfg = settings[selected]
    echo "Region=${cfg.region}; budget=${cfg.attempts}"
    ['syntax', 'security', 'quality'].each { check ->
      events.add(check)
      echo "Checked ${check}"
    }
  }
  stage('Control flow') {
    def quality = params.FORCE_FAIL ? 40 : 95
    if (quality < 80) {
      error('Intentional quality-gate failure')
    }
    switch (selected) {
      case 'staging': echo 'Staging simulation only'; break
      default: echo 'Development simulation only'
    }
    echo "Checks=${events.size()}"
  }
} catch (org.jenkinsci.plugins.workflow.steps.FlowInterruptedException interrupted) {
  result = 'ABORTED'
  throw interrupted
} catch (Exception ex) {
  result = 'FAILURE'
  echo "ErrorType=${ex.getClass().getSimpleName()}"
  throw ex
} finally {
  echo "Audit result=${result}; no deployment"
}
```

Expected: dev and staging succeed with their respective region and budget; three checks are logged; `FORCE_FAIL=true` produces FAILURE with a redacted audit line. No deployment occurs. This is a controller-only language and control-flow smoke, not a real build.

## 11. CPS serialization and suspension

Most Pipeline Groovy is CPS-transformed so it can pause at steps and resume after restarts. Retained state must be serializable; `NotSerializableException` can occur if a stream, matcher, connection or arbitrary Java object survives across a suspension. Use simple maps/lists/strings. `@NonCPS` is appropriate only for bounded pure calculations and **must not call Jenkins Pipeline steps**.

## 12. Script Security and shared-library trust

Sandboxed Pipelines may reject certain method signatures. Review rejected signatures and prefer supported Pipeline APIs over broad Script Approval. Trusted libraries execute with elevated capability; protect their SCM branches, review maintainers, pin versions where possible and separate untrusted PR builds from privileged jobs.

## 13. Observability and SRE operating model

Measure Groovy/CPS exceptions, sandbox rejections, controller CPU/heap, Pipeline duration, restart failures, invalid input attempts, library version drift and credential exposure. Correlate by job, build, commit, stage and library revision.

## 14. Twenty troubleshooting scenarios

| # | Symptom | Investigation | Safe recovery |
|---|---|---|---|
| 1 | String 'false' is truthy | Groovy truth vs typed boolean | Use params.FLAG and explicit boolean logic |
| 2 | Null map entry | Missing key or unvalidated parameter | Validate allowlist before lookup |
| 3 | PropertyMissingException | Wrong variable or binding scope | Use local def and explicit arguments |
| 4 | Unexpected integer division | Numeric coercion and type semantics | Test BigDecimal/int conversion |
| 5 | Mutable list shared across branches | Race and CPS state | Use immutable snapshots or locks |
| 6 | Closure captures loop variable | Late binding or mutable loop variable | Bind local copy per iteration |
| 7 | Nonserializable object | CPS checkpoint across suspension | Keep state simple and serializable |
| 8 | @NonCPS invokes echo | Pipeline steps unavailable in NonCPS method | Return pure value and call steps outside |
| 9 | Script approval rejection | Sandbox method not permitted | Refactor to approved APIs |
| 10 | Unbounded collection processing | Controller CPU/heap overload | Offload heavy work to agent |
| 11 | Secret printed by interpolation | GString and console output | Contain and rotate credential |
| 12 | Regex allows unsafe target | Pattern not anchored or input not normalized | Anchor and allowlist |
| 13 | Unbounded recursion | Stack or CPS memory pressure | Use bounded iterative control |
| 14 | Unexpected GString conversion | Lazy/interpolated string evaluation | Avoid secrets in Groovy strings |
| 15 | Retry repeats state mutation | Side effects inside closure | Separate pure calculation and idempotent operation |
| 16 | Null-safe operator hides bug | Unexpected null propagation | Validate required values explicitly |
| 17 | Groovy map key confusion | Dot syntax vs bracket syntax | Use bracket access for dynamic keys |
| 18 | Method visibility confusion | Jenkinsfile method vs closure binding | Pass inputs and test isolated function |
| 19 | Restart resumes with bad state | Nonserializable closure/object | Test durability and simplify state |
| 20 | Untrusted PR changes library | SCM trust and library source | Pin trusted library and protect branch |

## 15. Eight SRE runbooks

### RB-01 Groovy syntax and binding

**Procedure:** Capture Jenkinsfile SHA and stack trace, identify parser versus runtime error, reproduce in disposable staging and revert.

**Exit criteria:** reviewed Jenkinsfile/library, correct result, bounded controller work, safe input and redacted evidence.

### RB-02 CPS serialization

**Procedure:** Locate suspension point, remove nonserializable state, test restart and document any nonresumable step.

**Exit criteria:** reviewed Jenkinsfile/library, correct result, bounded controller work, safe input and redacted evidence.

### RB-03 Script Approval failure

**Procedure:** Inspect rejected signature and source trust; refactor or obtain narrow reviewed approval, never blanket approve.

**Exit criteria:** reviewed Jenkinsfile/library, correct result, bounded controller work, safe input and redacted evidence.

### RB-04 Controller CPU/heap regression

**Procedure:** Identify loops, large collections, closures and long computations; bound work and move CPU-heavy operations to agents.

**Exit criteria:** reviewed Jenkinsfile/library, correct result, bounded controller work, safe input and redacted evidence.

### RB-05 Input validation failure

**Procedure:** Inspect typed params, allowlist, regex and null handling; reject invalid values before any side effect.

**Exit criteria:** reviewed Jenkinsfile/library, correct result, bounded controller work, safe input and redacted evidence.

### RB-06 Secret disclosure

**Procedure:** Restrict logs/artifacts, revoke and rotate exposed secret, remove unsafe interpolation and verify scope.

**Exit criteria:** reviewed Jenkinsfile/library, correct result, bounded controller work, safe input and redacted evidence.

### RB-07 Mutable state race

**Procedure:** Review parallel branches, captured variables and shared map/list mutation; isolate state or lock critical section.

**Exit criteria:** reviewed Jenkinsfile/library, correct result, bounded controller work, safe input and redacted evidence.

### RB-08 Library change rollback

**Procedure:** Pin reviewed SCM revision, verify trusted/untrusted boundaries, roll back last-good library and re-run acceptance.

**Exit criteria:** reviewed Jenkinsfile/library, correct result, bounded controller work, safe input and redacted evidence.

## 16. Production checklist

| Gate | Evidence |
|---|---|
| Controller executors zero | Node configuration |
| Groovy syntax and typed input | Passing dev/staging smoke |
| Collection/closure/loop behavior | Three logged checks |
| Failure propagation | FORCE_FAIL build |
| Null and regex validation | Negative tests |
| CPS-safe state | Review and staged restart drill |
| Sandbox/library trust | SCM and approvals review |
| No secrets in Groovy logs | Redacted console review |
| Three incident tabletops | Owner signoff |
| Cleanup and rollback | Recorded proof |

## 17. Assessment — 100 points

| Domain | Points |
|---|---:|
| Groovy fundamentals and types | 25 |
| Collections, closures and control flow | 20 |
| Input/regex/null safety | 15 |
| CPS, sandbox and library trust | 20 |
| SRE troubleshooting | 10 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ and all security-critical gates. Controller-only tests do not certify agent builds, shared-library distribution or production restart recovery.

## 18. Cleanup

```bash
docker stop jenkins-ch026
docker rm jenkins-ch026
# Destructive: only if this volume belongs exclusively to the lab
docker volume rm jenkins-ch026-home
```

**Next:** Chapter 027 — Jenkins Shared Library Architecture, vars, src and resources.
