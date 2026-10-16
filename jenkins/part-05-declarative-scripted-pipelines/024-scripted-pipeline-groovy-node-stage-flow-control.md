# Chapter 024 — Scripted Pipeline Groovy, Node, Stage and Flow Control

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 05:** Declarative and Scripted Pipelines  
**Chapter:** 024 / 100  
**Companion lab:** [Chapter 024 — Hands-on acceptance lab](labs/024-scripted-pipeline-groovy-flow-control-check.md)

> **Safety:** Use a disposable localhost Jenkins controller with **zero built-in executors**. The executable demonstration uses lightweight Pipeline steps without a `node` allocation, workspace or shell. Real builds require isolated trusted agents; do not approve unsafe Groovy signatures just to make a tutorial pass.

## 1. Objectives and prerequisites

After this chapter, explain the Scripted Pipeline execution model, Groovy variables and collections, `stage`, `node`, conditional and loop control, `try/catch/finally`, Pipeline steps versus controller-side Groovy, CPS serialization, restart durability, trust boundaries and safe migration from Declarative. Prerequisites: Chapters 021–023 and a disposable Jenkins controller with Pipeline plugins.

## 2. Execution architecture

```text
protected Jenkinsfile
       |
   Groovy/CPS Pipeline runtime (controller orchestration)
       |
   stage + branch/loop + step invocations
       |
   node('approved-label') -> queue -> isolated agent/workspace
       |
   checkout/build/test -> result, logs, artifacts
       |
   catch/finally -> audit, notification, cleanup
```

Scripted Pipeline uses Groovy to compose Jenkins Pipeline steps. Ordinary Groovy code runs as part of the Pipeline program and is **not** a replacement for compute on an agent. Avoid CPU-intensive processing, huge in-memory objects or secrets in Groovy variables on the controller.

## 3. Declarative versus Scripted

| Concern | Declarative | Scripted |
|---|---|---|
| Entry point | `pipeline { }` | Groovy statements and Pipeline steps |
| Stages | `stages { stage { steps { } } }` | `stage('Name') { ... }` |
| Agent | `agent` directive | Explicit `node('label') { ... }` |
| Branching | `when`, limited `script` | Groovy `if`, `switch`, loops |
| Post actions | `post { }` | `try/catch/finally` and result handling |
| Maintainability | Convention and validation | Flexibility with more review burden |

Prefer Declarative for standardized delivery. Use Scripted when genuinely needed and centralize reusable behavior in reviewed shared libraries.

## 4. Groovy variables and collections

```groovy
def target = 'dev'
def allowed = ['dev', 'staging']
def config = [timeoutMinutes: 10, retries: 2]
if (!allowed.contains(target)) {
  error('Target is not approved')
}
echo "Target=${target}; retryBudget=${config.retries}"
```

Use `def` for local variables and avoid mutable global script state. Groovy truth treats a nonempty string such as `'false'` as true. Compare typed parameters explicitly.

## 5. Runnable controller-only Scripted Pipeline

Create a Pipeline job `ch024-scripted-flow` with this definition. It requires Pipeline basic steps and uses no agent or workspace.

```groovy
def targets = ['dev', 'staging']
def selected = params.TARGET ?: 'dev'
def attempts = 0
def trace = []

try {
  stage('Validate') {
    if (!targets.contains(selected)) {
      error("Rejected target")
    }
    echo "Target=${selected}"
  }

  stage('Control flow') {
    for (int i = 1; i <= 3; i++) {
      trace.add("step-${i}")
      echo "Iteration ${i}"
    }
    switch (selected) {
      case 'staging':
        echo 'Staging path selected'
        break
      default:
        echo 'Development path selected'
    }
  }

  stage('Recovery') {
    retry(2) {
      attempts++
      echo "Attempt ${attempts}"
      if (params.FAIL_ONCE && attempts == 1) {
        error('Intentional transient lab error')
      }
    }
  }

  stage('Outcome') {
    if (params.FORCE_FAIL) {
      error('Intentional terminal failure')
    }
    echo "Trace count=${trace.size()}"
  }
} catch (org.jenkinsci.plugins.workflow.steps.FlowInterruptedException interrupted) {
  echo 'Build interrupted; preserving abort/timeout'
  throw interrupted
} catch (Exception ex) {
  echo "Build failed: ${ex.getClass().getSimpleName()}"
  throw ex
} finally {
  echo 'FINALLY: record redacted result evidence'
}
```

Configure job parameters: choice `TARGET` with `dev`, `staging`; boolean `FAIL_ONCE` default false; boolean `FORCE_FAIL` default false. Run dev success, staging success, transient retry and intentional failure. A first run after defining parameters in the UI should expose them immediately. No external side effects occur.

## 6. Node and workspace boundaries

```groovy
stage('Compile') {
  node('lab-linux') {
    checkout scm
    sh 'set -eu; ./gradlew test'
    junit 'build/test-results/test/*.xml'
    archiveArtifacts artifacts: 'build/libs/*.jar', fingerprint: true
  }
}
```

This is an **approved staging design example**, not runnable on the controller-only lab. `checkout scm` requires a job with an SCM context (for example Pipeline from SCM/multibranch). `lab-linux` must be a preconfigured isolated agent. Archive only approved non-secret outputs; validate generated test XML and artifact checksums.

## 7. Branching and bounded loops

```groovy
def regions = ['east', 'west']
for (int index = 0; index < regions.size(); index++) {
  stage("Validate-${regions[index]}") {
    echo "Region=${regions[index]}"
  }
}
```

Prefer deterministic small loops and bounded `timeout` for operations that might hang. Never build an unbounded `while(true)` poller without explicit deadline, sleep and cancellation semantics.

## 8. Exceptions, interrupts and finally

`try/catch/finally` enables recovery but should not hide deployment failures. Jenkins abort and timeout may propagate as `FlowInterruptedException`; rethrow it. A `finally` block runs on ordinary completion or thrown exceptions, but Jenkins process termination or parse errors may prevent it. Cleanup must be idempotent and must not destroy incident evidence.

## 9. CPS and durability

Jenkins Pipeline transforms most Groovy code using continuation-passing style (CPS), enabling suspension at steps and controller restarts. Nonserializable objects retained across suspension can cause `NotSerializableException`. Use simple maps/lists/strings for durable state; do not hold open file handles, streams or arbitrary Java client objects. `@NonCPS` is for small pure computations and **must not invoke Pipeline steps**.

## 10. Parallelism and shared state

`parallel` branches can execute concurrently; isolate workspaces, artifacts, mutable maps and credentials. If an external write is shared, use reviewed locking/idempotency. Never assume `parallel` is automatically safe or that each branch receives its own agent.

## 11. Security and governance

Version Jenkinsfiles in protected SCM, enforce review and least-privilege job/folder RBAC, use credentials bindings scoped to trusted jobs, restrict Script Approval, and pin plugins. Avoid Groovy interpolation of credentials into shell commands or URLs. Untrusted PRs must not run with deployment identities.

## 12. Monitoring and operational acceptance

Observe parser/sandbox failures, CPS serialization errors, queue p95, script execution duration, retry counts, abort handling, stage failure rate, controller CPU and Groovy heap pressure. Correlate build number, SCM revision, agent and stage; keep rollback commit available.

## 13. Twenty troubleshooting scenarios

| # | Symptom | Investigation | Safe response |
|---|---|---|---|
| 1 | Missing node context | A workspace step such as sh, checkout or archiveArtifacts runs outside node | Move workspace operations to a trusted labeled node |
| 2 | Queue never clears | Requested label lacks online eligible executors | Inspect node labels and provisioning, not controller executors |
| 3 | Untrusted code reaches release node | Unreviewed node label and permissive folder access | Quarantine job, separate identities and agents |
| 4 | Stage absent from UI | Stage not executed or nested control path skipped | Inspect branch conditions and stage metadata |
| 5 | Groovy truth surprises | String 'false' treated truthy | Use typed parameters and explicit comparisons |
| 6 | NullPointerException | Missing map key or uninitialized variable | Validate inputs before dereference |
| 7 | MissingPropertyException | Incorrect variable scope | Declare local variables and pass arguments |
| 8 | Sandbox rejects method | Unapproved Groovy API | Use supported Pipeline steps or reviewed shared library |
| 9 | Script approval backlog | Unsafe custom method or plugin mismatch | Refactor rather than blanket approval |
| 10 | CPS serialization error | Nonserializable object crosses Pipeline suspension | Keep durable state serializable and short-lived |
| 11 | Pipeline restarts incorrectly | Nonresumable step or state assumption | Test restart recovery and idempotency |
| 12 | Infinite loop | Unbounded while/recursive control flow | Set explicit maximum attempts and timeout |
| 13 | Retry duplicates side effects | Non-idempotent publish/deploy in retry block | Use idempotency key and reconciliation |
| 14 | Parallel branches overwrite files | Shared workspace or mutable map | Separate workspaces and immutable data |
| 15 | Exception swallowed | Catch block logs but does not fail | Rethrow or mark result deliberately |
| 16 | Abort ignored | InterruptedException caught and discarded | Rethrow interruption |
| 17 | Post cleanup obscures failure | Finally block raises another exception | Guard cleanup and preserve original error |
| 18 | Secret appears in logs | GString or print of environment variable | Contain logs, rotate secret and correct binding |
| 19 | Long Groovy CPU spike | Large in-memory transformations on controller | Move compute to isolated agent |
| 20 | SCM Jenkinsfile drift | Inline Pipeline differs from protected Git | Review and restore versioned definition |

## 14. Eight SRE runbooks

### RB-01 Syntax or Groovy runtime failure

**Procedure:** Capture build number, Jenkinsfile SHA and exception; distinguish parser, binding, sandbox and missing node context; reproduce on staging.

**Exit criteria:** correct stage result, trusted agent boundaries, bounded control flow, interruption preserved, and evidence recorded.

### RB-02 Queue and agent isolation

**Procedure:** Inspect labels, online executors, agent provisioner and trust zone; restore approved capacity without enabling controller builds.

**Exit criteria:** correct stage result, trusted agent boundaries, bounded control flow, interruption preserved, and evidence recorded.

### RB-03 CPS and restart recovery

**Procedure:** Identify suspension point, nonserializable state and nonresumable steps; refactor, then test restart and rollback.

**Exit criteria:** correct stage result, trusted agent boundaries, bounded control flow, interruption preserved, and evidence recorded.

### RB-04 Loop or retry storm

**Procedure:** Abort safely, inventory external side effects, cap iterations and implement idempotent operations.

**Exit criteria:** correct stage result, trusted agent boundaries, bounded control flow, interruption preserved, and evidence recorded.

### RB-05 Exception/abort handling

**Procedure:** Trace catch/finally paths; preserve InterruptedException, original build result and redacted error evidence.

**Exit criteria:** correct stage result, trusted agent boundaries, bounded control flow, interruption preserved, and evidence recorded.

### RB-06 Shared-state race

**Procedure:** Inspect parallel branch mutation, shared workspace and output names; isolate state and serialize critical writes.

**Exit criteria:** correct stage result, trusted agent boundaries, bounded control flow, interruption preserved, and evidence recorded.

### RB-07 Credential leak

**Procedure:** Restrict affected console and artifacts, rotate credentials, remove interpolation and audit access.

**Exit criteria:** correct stage result, trusted agent boundaries, bounded control flow, interruption preserved, and evidence recorded.

### RB-08 Change acceptance

**Procedure:** Verify reviewed SCM definition, rollback commit, controlled labels, stage results, evidence and owner signoff.

**Exit criteria:** correct stage result, trusted agent boundaries, bounded control flow, interruption preserved, and evidence recorded.

## 15. Acceptance gates

| Gate | Required outcome |
|---|---|
| G1 | Controller built-in executors zero |
| G2 | Scripted vs Declarative architecture explained |
| G3 | Groovy variables/collections and typed parameters validated |
| G4 | Dev and staging branches tested |
| G5 | Bounded loop output observed |
| G6 | Retry succeeds after simulated transient error |
| G7 | Terminal FAILURE propagates; finally evidence recorded |
| G8 | Agent and CPS trust/durability limitations explained |
| G9 | Three incident diagnoses and rollback |
| G10 | Redacted evidence, cleanup and reviewer signoff |

## 16. Assessment — 100 points

| Domain | Points |
|---|---:|
| Scripted Groovy and control flow | 25 |
| Node/stage and trust boundaries | 20 |
| Retry, exceptions and interruption | 20 |
| CPS, restart and durability | 15 |
| SRE troubleshooting | 10 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ with all critical security gates. This controller-only smoke does not certify external builds or restart recovery.

## 17. Cleanup

```bash
docker stop jenkins-ch024
docker rm jenkins-ch024
# Only after verifying exclusive lab ownership:
docker volume rm jenkins-ch024-home
```

**Next:** Chapter 025 — Declarative and Scripted Pipeline Production Reliability Capstone.
