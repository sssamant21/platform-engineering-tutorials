# Chapter 004 — Jenkins Core Components, Plugins and Extension Architecture

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 01:** Jenkins Fundamentals and Architecture  
**Chapter:** 004 / 100  
**Companion lab:** [004 — Jenkins Components, Plugins and Extension Check](labs/004-jenkins-components-plugins-extension-check.md)

> **Safety:** Use a disposable Jenkins controller for hands-on experiments. Plugin installation, removal and version changes can modify persistent controller state. Never experiment on production without a tested backup, approved change and compatibility review.

## 1. Learning objectives

Explain the boundaries between Jenkins core and plugins; identify controller, agent, executor, queue, item/job, run/build, workspace and credentials responsibilities; understand Jenkins plugin extension points, descriptors and Pipeline steps; inspect plugin dependency graphs; diagnose plugin loading failures and safely plan upgrades, rollback and restore.

## 2. Core versus plugin architecture

```text
                  Browser / REST / Webhooks
                            |
                      Jenkins Core
         +------------------+------------------+
         |                  |                  |
      Items/Jobs          Queue           Security Realm
         |                  |                  |
      Runs/Builds        Nodes/Agents       Authorization
         |                  |                  |
         +------------------+------------------+
                            |
                      Extension API
                            |
           +----------------+----------------+
           |                |                |
       SCM Plugins     Pipeline Plugins   Cloud Plugins
           |                |                |
        Git hooks      Groovy/CPS steps  Kubernetes pods
           |                |                |
           +----------------+----------------+
                            |
                   Trusted build agents
                            |
                   Registry / GitOps PR
```

**Jenkins core** owns fundamental runtime and extension APIs. **Plugins** add SCM providers, Pipeline steps, credentials integrations, UI, cloud agent provisioning, metrics and other behavior. Plugin compatibility is a **dependency graph**, not a set of independent jar upgrades.

## 3. Component reference

| Component | Responsibility | Typical location |
|---|---|---|
| Jenkins core | Core lifecycle, queue, nodes, job model, Stapler web routing, persistence and API contracts | Controller |
| Plugin manager | Plugin installation, dependencies, updates, disablement, advisories and restart behavior | Controller |
| Extension points | Java interfaces and annotated implementations exposed through Jenkins plugin API | Plugin code |
| Descriptors | Configuration metadata and form validation for describable objects | Plugin/controller |
| Pipeline engine | Declarative Pipeline, CPS-transformed Groovy, step execution and resume behavior | Controller plus agents |
| Credentials | Credential providers, scopes, binding and secret redaction | Controller and trusted agents |
| SCM integration | Git checkout, webhooks, indexing, multibranch events | Controller and agents |
| Cloud/agent plugins | Dynamic provisioning, Kubernetes pod templates, remoting transport | Controller and agents |
| JCasC | Declarative global settings via compatible plugins | Controller |
| Observability | JVM, queue, build, agent, plugin and audit telemetry | Controller and agents |

## 4. Core runtime concepts

- **Item/Job:** persistent automation configuration and metadata.
- **Run/Build:** an execution record with status, logs, timing and artifacts.
- **Queue:** schedules eligible tasks based on labels, capacity, throttles and locks.
- **Node:** controller built-in node or an agent registered with Jenkins.
- **Executor:** concurrency slot on a node; not a CPU core.
- **Workspace:** filesystem directory for checkout/build, usually on an agent.
- **Remoting:** controller/agent communication protocol, with transport depending on configuration.
- **JENKINS_HOME:** stateful controller directory containing configuration, jobs, plugins, credentials and encryption material.

For enterprise security, set controller executors to **zero**, keep builds on isolated agents and separate trusted/untrusted workloads.

## 5. Plugin lifecycle and metadata

A Jenkins plugin commonly uses an `.hpi` or `.jpi` archive, a manifest declaring dependencies and a minimum compatible Jenkins core version, plus optional plugins and extension implementations. Plugins can contribute UI views, credentials providers, Pipeline steps, SCM sources, build wrappers, cloud integrations and administrative pages.

Lifecycle:

```text
Discover -> security review -> compatibility check -> stage test
 -> pin version/dependencies -> backup -> approved install
 -> restart if required -> smoke test -> monitor -> rollback plan
```

**Do not blindly install all suggested plugins in a regulated production controller.** Use a reviewed bill of materials and test plugin upgrades together with the chosen Jenkins LTS and Java runtime.

## 6. Extension points and descriptors

A plugin implements Jenkins APIs and registers an extension, often with the Java `@Extension` annotation. Descriptors expose configurable metadata and form validation for `Describable` types. Pipeline step plugins expose `Step` implementations that become Jenkinsfile DSL steps.

Illustrative extension sketch (not a complete compilable plugin):

```java
@Extension
public class ExampleDescriptor extends Descriptor<ExampleConfiguration> {
    @Override
    public String getDisplayName() {
        return "Example extension";
    }
}
```

A real plugin also requires correct Jenkins plugin parent/POM, package structure, implementation classes, annotations, tests and security review. The plugin's Java API must match the selected Jenkins baseline.

## 7. Pipeline plugin model

```groovy
pipeline {
  agent none
  stages {
    stage('Plugin inventory awareness') {
      steps {
        echo 'Pipeline syntax and steps are provided by compatible plugins.'
      }
    }
  }
}
```

Declarative Pipeline, Workflow/Pipeline engine, SCM and Credentials Binding features rely on plugins. Some steps are controller-coordinated; commands such as `sh`, `bat` and `checkout` require a suitable allocated agent/workspace. Do not interpret `agent none` as a way to execute builds on the controller.

## 8. Safe plugin inventory and version verification

For the disposable Chapter 004 Docker lab:

```bash
docker ps --filter name=jenkins-ch004
docker exec jenkins-ch004 java -version
docker exec jenkins-ch004 sh -c 'ls -1 /var/jenkins_home/plugins | head -40'
docker logs --tail 100 jenkins-ch004
```

In the UI open **Manage Jenkins → Plugins** and inspect installed versions, dependencies and available security notices. File names alone do not prove plugin load success; check startup logs and plugin manager state.

### Offline dependency review

The Jenkins Plugin Installation Manager Tool can resolve a requested plugin catalog against a chosen Jenkins core and update-center metadata. In production, pin the exact tool version, core version, plugin versions and artifact checksums; perform resolution in CI before touching the controller.

Illustrative catalog:

```text
workflow-aggregator:<approved-version>
git:<approved-version>
configuration-as-code:<approved-version>
credentials-binding:<approved-version>
```

Placeholders must be replaced with a tested compatible set; this is not a runnable catalog until resolved.

## 9. Plugin supply-chain and security model

- Download from approved, trusted distribution sources.
- Verify publisher, integrity and advisory status.
- Restrict plugin installation and Script Console permissions.
- Treat plugins as highly privileged code running inside the controller JVM.
- Isolate credentials from untrusted builds and extensions.
- Stage plugin updates with representative Pipelines, JCasC reload and agent provisioning tests.
- Protect plugin archives, controller home and backup encryption keys.
- Record version changes and rollback criteria in change management.

## 10. Dependency failure investigation

```bash
docker logs --tail 250 jenkins-ch004
docker exec jenkins-ch004 sh -c 'find /var/jenkins_home/plugins -maxdepth 1 -type f | head -30'
```

Search for `Failed Loading plugin`, missing dependency, incompatible Jenkins version, Java class loading failures and configuration migration warnings. Never manually delete a plugin directory on a running controller as a first response. Use a clean-room reproduction and tested backup before making stateful changes.

## 11. JCasC and plugin interaction

JCasC configuration keys and supported schemas depend on the installed plugins. A YAML file that worked previously can fail after a plugin upgrade or removal. Validate against the exact plugin bill of materials and test reloads before rollout.

```yaml
jenkins:
  numExecutors: 0
  systemMessage: "Controller managed by approved configuration"
```

This is a deliberately small example. Authentication, authorization and secrets configuration must be supplied through approved, version-compatible mechanisms.

## 12. Plugin health and performance

Measure plugin startup time, controller heap/GC, thread activity, queue age, Pipeline resume failures, agent provisioning time, API response latency and errors. Investigate regressions with before/after baselines. Avoid increasing controller resources to mask faulty plugin behavior.

## 13. Twenty troubleshooting scenarios

| # | Failure | Investigation | Recovery |
|---|---|---|---|
| 1 | Plugin fails to load | Review startup logs, required core version and transitive dependencies | Restore compatible tested set |
| 2 | Plugin disabled unexpectedly | Inspect disabled state and dependency tree | Re-enable only after review |
| 3 | Update requires restart | Check pending restart and running jobs | Schedule controlled safe restart |
| 4 | Missing Pipeline step | Check plugin providing step and installed version | Install approved compatible plugin |
| 5 | NoSuchMethodError | Inspect conflicting plugin API versions | Resolve dependency set in staging |
| 6 | ClassNotFoundException | Check classloader and missing dependencies | Align plugin versions |
| 7 | JCasC unknown key | Validate schema against installed plugin set | Correct config and revert |
| 8 | Configuration lost after restart | Inspect JENKINS_HOME volume and JCasC reload | Restore persisted config |
| 9 | Credentials Binding missing | Check plugin installation and permission | Install compatible plugin and verify scopes |
| 10 | Git checkout fails | Inspect SCM plugin, auth, host key and agent tools | Repair trust and token |
| 11 | Webhook does not trigger | Inspect provider delivery, URL and plugin endpoint | Restore secure callback |
| 12 | Agent cloud provisioning fails | Inspect plugin logs, quota and Kubernetes permissions | Fix scoped identity or capacity |
| 13 | Plugin UI missing | Check permission, installed plugin and navigation changes | Review access and version |
| 14 | Plugin download TLS error | Inspect truststore, proxy and update center connectivity | Repair CA/proxy without bypassing TLS |
| 15 | Plugin has security advisory | Check advisory severity, affected version and exposure | Patch, mitigate or disable |
| 16 | Controller memory grows | Inspect heap, plugin memory and build retention | Profile and remediate |
| 17 | Pipeline cannot resume | Check durability, nonresumable steps and plugin changes | Re-run safely with idempotency |
| 18 | Plugin conflicts with Java | Check Jenkins/Java/plugin compatibility matrix | Select supported runtime |
| 19 | Unexpected extension behavior | Review extension ordering and plugin-specific settings | Disable conflicting extension safely |
| 20 | Rollback corrupts state | Inspect migrations and backup compatibility | Restore full pre-change snapshot |

## 14. Eight SRE runbooks

### RB-01 Plugin dependency outage

**Procedure:** Freeze changes, inspect plugin manager and logs, compare tested bill of materials, restore compatible set.

**Evidence:** incident/change ID, versions and dependency graph, UTC timeline, affected jobs, approval, recovery validation and follow-up owner.

### RB-02 Security advisory response

**Procedure:** Identify affected plugin and reachability, restrict exposure, apply approved upgrade or compensating controls.

**Evidence:** incident/change ID, versions and dependency graph, UTC timeline, affected jobs, approval, recovery validation and follow-up owner.

### RB-03 Controller boot failure after upgrade

**Procedure:** Collect JVM and plugin logs, validate Java/core versions, restore pre-upgrade consistent home if required.

**Evidence:** incident/change ID, versions and dependency graph, UTC timeline, affected jobs, approval, recovery validation and follow-up owner.

### RB-04 JCasC extension schema failure

**Procedure:** Validate config against installed plugins in staging, revert reviewed bundle and reload safely.

**Evidence:** incident/change ID, versions and dependency graph, UTC timeline, affected jobs, approval, recovery validation and follow-up owner.

### RB-05 Pipeline step regression

**Procedure:** Locate step provider, plugin compatibility and failing build stage, reproduce and rollback approved change.

**Evidence:** incident/change ID, versions and dependency graph, UTC timeline, affected jobs, approval, recovery validation and follow-up owner.

### RB-06 Agent provisioning plugin incident

**Procedure:** Check cloud API permissions, pod events, node resources and plugin logs, restore isolated agent capacity.

**Evidence:** incident/change ID, versions and dependency graph, UTC timeline, affected jobs, approval, recovery validation and follow-up owner.

### RB-07 Plugin performance regression

**Procedure:** Measure heap/GC, threads, queue latency and extension activity, mitigate and perform controlled rollback.

**Evidence:** incident/change ID, versions and dependency graph, UTC timeline, affected jobs, approval, recovery validation and follow-up owner.

### RB-08 Upgrade/change acceptance

**Procedure:** Document pinned core/plugins, test matrix, backups, safe restart, smoke tests, on-call owner and rollback.

**Evidence:** incident/change ID, versions and dependency graph, UTC timeline, affected jobs, approval, recovery validation and follow-up owner.

## 15. Acceptance assessment (100 points)

| Domain | Points |
|---|---:|
| Core components and controller/agent boundary | 20 |
| Plugin lifecycle and dependency architecture | 20 |
| Extension points, descriptors and Pipeline model | 15 |
| Plugin inventory and compatibility validation | 15 |
| Security, JCasC and supply-chain controls | 15 |
| Troubleshooting, rollback and operational evidence | 15 |
| **Total** | **100** |

**Pass:** 90+ with mandatory gates: no untrusted controller build, no plugin installation without review, no exposed secrets and documented backup/rollback.

## 16. Cleanup

```bash
docker stop jenkins-ch004
docker rm jenkins-ch004
# Destructive: only after confirming volume belongs exclusively to this lab:
docker volume rm jenkins-ch004-home
```

**Next:** Chapter 005 — Jenkins Architecture and Administration Fundamentals Capstone.
