# Chapter 027 — Jenkins Shared Library Architecture: vars/, src/ and resources/

**Part 06 — Groovy, Shared Libraries and Reusable Pipelines**  
**Audience:** Jenkins administrators, DevOps, SRE and platform engineers  
**Prerequisite:** Chapter 026, a disposable Jenkins controller with Pipeline and Shared Libraries support, Git, and an isolated build agent.

## Learning objectives

Explain Shared Library resolution, design the three canonical directories, register and pin a library, implement reusable steps and classes, load packaged resources, test and troubleshoot safely, and roll back a breaking release.

## 1. Why Shared Libraries?

Repeated Jenkinsfiles lead to divergent retry behavior, inconsistent security controls, and duplicated deployment logic. A Shared Library centralizes reviewed functions while keeping application-specific pipeline stages visible. Jenkins loads library code from SCM; this code can execute powerful Pipeline operations and must be treated as executable supply-chain input.

**Architecture:** Application repository Jenkinsfile → Jenkins library resolver (configured SCM repository and version) → `vars/` global steps → `src/` Groovy classes → `resources/` templates → isolated Jenkins agent for build commands.

## 2. Canonical repository layout

```text
jenkins-shared-library/
├── vars/
│   ├── ciPipeline.groovy
│   └── validateInputs.groovy
├── src/
│   └── org/example/ci/BuildMetadata.groovy
├── resources/
│   └── org/example/ci/defaults.json
├── test/
│   └── ... unit tests ...
└── README.md
```

| Directory | Role | Operational guidance |
|---|---|---|
| `vars/` | Pipeline global variables/steps; `call` enables function-like invocation | Keep stateless; use Pipeline steps via script context |
| `src/` | Namespaced Groovy classes on library classpath | Keep pure logic testable; avoid retaining nonserializable state across suspension |
| `resources/` | Static text assets loaded by `libraryResource` | Treat as source-controlled inputs, not secrets |
| `test/` | Local unit and behavior tests | Run before approving a release |

## 3. Build the reusable library

**src/org/example/ci/BuildMetadata.groovy**

```groovy
package org.example.ci

class BuildMetadata implements Serializable {
    static String normalizeEnvironment(String value) {
        String normalized = (value ?: '').trim().toLowerCase()
        if (!(normalized in ['dev', 'staging', 'prod'])) {
            throw new IllegalArgumentException("Unsupported environment")
        }
        return normalized
    }
}
```

**resources/org/example/ci/defaults.json**

```json
{"timeoutMinutes": 15, "allowedEnvironments": ["dev", "staging", "prod"]}
```

**vars/validateInputs.groovy**

```groovy
import org.example.ci.BuildMetadata

def call(Map config = [:]) {
    String target = BuildMetadata.normalizeEnvironment(config.environment as String)
    echo "Validated target environment: ${target}"
    return target
}
```

**vars/ciPipeline.groovy**

```groovy
import groovy.json.JsonSlurperClassic

def call(Map config = [:]) {
    String target = validateInputs(environment: config.environment)
    Map defaults = new JsonSlurperClassic().parseText(
        libraryResource('org/example/ci/defaults.json')
    ) as Map
    int timeoutMinutes = defaults.timeoutMinutes as int
    timeout(time: timeoutMinutes, unit: 'MINUTES') {
        stage('Shared Library Validation') {
            echo "Shared library loaded for ${target}"
        }
    }
}
```

**Application Jenkinsfile** (use a reviewed immutable tag or commit SHA, not an unreviewed branch):

```groovy
@Library('enterprise-ci@v1.0.0') _
pipeline {
    agent { label 'isolated-linux' }
    options { skipDefaultCheckout(true) }
    stages {
        stage('Validate') {
            steps {
                script {
                    ciPipeline(environment: 'staging')
                }
            }
        }
    }
}
```

Note: This example invokes a shared step within a Declarative stage. For production code, prefer keeping the top-level stage graph in the application Jenkinsfile; avoid nested `stage` wrappers inside shared steps if they make visualization ambiguous.

## 4. Register the library

1. Commit library sources to a dedicated SCM repository.
2. In a disposable Jenkins instance, go to **Manage Jenkins → System → Global Trusted Pipeline Libraries** or **Global Untrusted Pipeline Libraries**, as appropriate for the installed plugins and security model.
3. Configure the name `enterprise-ci`, Modern SCM/Git repository, credentials if required, and a reviewed default version.
4. Restrict who can change trusted library sources; prefer untrusted libraries when possible. Trusted libraries can bypass the Groovy sandbox and effectively grant powerful controller-side access.
5. Set the application's `@Library` version to the reviewed tag `v1.0.0`. Protect the tag against modification.

**Important:** A library's default version is not a substitute for explicit version pinning. `@Library` resolves at compilation time; the dynamic `library()` step loads at runtime and has different import constraints. `libraryResource` is intended for external-library resources; do not assume it works with internal libraries.

## 5. Operational architecture and tradeoffs

- **Library ownership:** platform team reviews APIs, versions and compatibility; application teams own their Jenkinsfiles.
- **API design:** use small named steps with explicit configuration Maps and validated values; avoid implicit mutable globals.
- **Versioning:** semantic tags with release notes; test downstream Jenkinsfiles against changes before release.
- **Supply-chain controls:** SCM branch protection, least-privilege read credentials, signed/reviewed releases where supported, and audit logs.
- **Security:** never embed tokens in `resources/`, Groovy sources, build logs or Jenkinsfiles. Use Jenkins Credentials Binding only around the steps that require credentials.
- **Agent boundaries:** `sh`, `bat` and build tools run on an allocated agent. Groovy code and Pipeline orchestration are not automatically isolated from the controller.
- **Performance:** avoid large libraries, expensive top-level initialization, excessive SCM retrieval, and controller-side I/O.
- **Serialization:** Pipeline CPS can suspend execution; keep state serializable and use `@NonCPS` only for pure computations that do not call Pipeline steps.

## 6. Troubleshooting matrix

| Symptom | Likely cause | Verification | Safe fix |
|---|---|---|---|
| Library not found | Name/version/SCM mismatch | Build log and library config | Correct name and tag |
| `No such DSL method` | Missing `vars` file or wrong `call` signature | Inspect file name and signature | Match invocation to global step |
| `unable to resolve class` | Wrong package/path or dynamic loading | Compare `src` package; inspect `@Library` | Align package; use static load for imports |
| Resource missing | Incorrect resource path | Check repository tree | Use relative resource path under `resources/` |
| Sandbox rejection | Restricted operation in untrusted code | Review rejected signature | Redesign for approved steps; avoid blanket approvals |
| `NotSerializableException` | CPS state holds incompatible object | Read stack trace | Keep state simple and serializable |
| Works on one controller only | Plugin/configuration drift | Compare plugin versions and JCasC | Align tested versions/configuration |
| Unexpected version | Mutable ref/default selection | Log resolved SCM revision | Pin immutable revision |
| Secret exposed | Unsafe interpolation or logging | Review pipeline log/access | Revoke and rotate, remove logging |
| Pipeline hangs | SCM retrieval, agent or step timeout | Stage timing and agent queue | Bound timeouts; investigate dependency |

## 7. Production runbooks

### Runbook A — Safe rollout
Create a release branch, run Groovy tests and Jenkins integration checks, peer-review, tag `v1.0.0`, deploy to a canary Jenkinsfile, compare stage results and logs, then expand adoption. Record library commit SHA and consumers.

### Runbook B — Incident rollback
Identify the last good tag; update consuming Jenkinsfiles to that immutable version through review; rerun only safe/idempotent jobs; verify outcomes. Never force-move a released tag.

### Runbook C — Security event
Disable affected consumers where necessary, revoke exposed credentials, review SCM history and Jenkins logs, rotate secrets, and restore a reviewed release. Record incident timeline and ownership.

## 8. Production use cases

1. Standardize build/test stages across microservices.
2. Enforce environment validation before Kubernetes deployments.
3. Centralize artifact metadata and provenance checks.
4. Apply consistent timeouts and error handling.
5. Support Jenkins controllers across EKS/AKS without hard-coding cloud credentials.

## 9. Acceptance criteria

- [ ] Directory layout and package naming validated
- [ ] Global steps work from an application Jenkinsfile
- [ ] Resource loading and configuration parsing pass
- [ ] Invalid environment is rejected before action
- [ ] Library version is immutable and review-controlled
- [ ] No plaintext secrets or unsafe shell interpolation
- [ ] Unit/integration tests and failure scenarios recorded
- [ ] Rollback tested against a previous tag
- [ ] Build logs capture resolved library revision and evidence

## 10. Key takeaways

`vars/` provides the public Pipeline API, `src/` houses reusable classes, and `resources/` stores versioned static assets. A production Shared Library is an executable dependency: govern it with tests, reviews, version pinning, security controls and rollback procedures.

**Next:** Chapter 028 — Reusable Jenkins Pipeline Functions, Configuration and Design Patterns.
