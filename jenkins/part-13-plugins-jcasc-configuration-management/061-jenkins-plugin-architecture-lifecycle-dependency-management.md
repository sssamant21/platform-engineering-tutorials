# Chapter 061 — Jenkins Plugin Architecture, Lifecycle and Dependency Management

**Part 13 — Plugins, JCasC and Configuration Management**  
**Audience:** Jenkins SRE, platform engineers, DevSecOps, controller administrators  
**Prerequisites:** Chapters 056–060, disposable Jenkins LTS, Java runtime, Docker/Podman lab, backup and approved maintenance window.

## Learning outcomes

Understand Jenkins plugin architecture and dependency resolution; create a reproducible plugin baseline; validate compatibility, security advisories and upgrade order; detect plugin failures and drift; safely roll forward or recover; operate plugins with Git-reviewed change management.

## 1. Architecture

```text
Jenkins core (LTS) + Java runtime
           |
      Plugin Manager
           |
  plugin manifest (.hpi/.jpi)
           |
  required + optional dependencies
           |
  extensions, descriptors, steps, UI, APIs
           |
  Jenkins jobs / Pipelines / JCasC
```

Plugins run in the Jenkins controller process with significant trust. A compromised or incompatible plugin can affect authentication, credentials, scheduling, configuration or controller availability. Plugins are **not** isolated security sandboxes.

## 2. Plugin metadata

Plugin manifests define short name, version, required Jenkins core, dependencies, optional dependencies and implementation details. Distinguish:

- **Required dependencies:** must be installed at compatible versions.
- **Optional dependencies:** may enable integrations; version compatibility still matters.
- **Detached plugins:** formerly bundled functionality now delivered as plugins.
- **Bundled/transitive plugins:** installed to satisfy dependencies.
- **Pinned plugin versions:** an intentional reproducible baseline, not an instruction to ignore security updates.

Plugin API and dependency behavior can change with core and plugin versions. Read changelogs and security advisories before changes.

## 3. Plugin inventory

From a trusted administrator session, use the Jenkins Plugin Manager UI or authenticated supported API. Do not expose administrative credentials in shell history.

```sh
# Example inside an isolated container with the plugin CLI available
jenkins-plugin-cli --version
jenkins-plugin-cli --help
```

In an official Jenkins Docker image, the plugin installation manager CLI is normally available. Confirm the exact image/version and CLI options before scripting; `jenkins-plugin-cli` is not a generic command installed on every Jenkins host.

## 4. Reproducible plugin manifest

Maintain an explicit list in Git:

```text
# plugins.txt — example names only; resolve versions against approved core
configuration-as-code
credentials
credentials-binding
git
workflow-aggregator
job-dsl
matrix-auth
role-strategy
kubernetes
```

For production, pin reviewed versions and generate a lock/inventory of resolved transitive dependencies. Never assume the example set is sufficient for every chapter or secure for a particular Jenkins LTS.

## 5. Containerized plugin baseline

```dockerfile
FROM jenkins/jenkins:lts-jdk21
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
```

**Important:** `lts-jdk21` is a moving tag and is shown for lab simplicity. For production, pin a tested image digest and review the base image/core version. The plugin CLI resolves dependencies at build time; archive the resulting inventory and scan for vulnerabilities. Never use unreviewed latest plugin versions in production without testing.

## 6. Compatibility and dependency management

Before upgrading:
1. Capture Jenkins core, Java and all plugin versions.
2. Review minimum core requirements and plugin dependency constraints.
3. Review Jenkins security advisories and plugin changelogs.
4. Build a staging image with the proposed pinned plugin set.
5. Run startup, JCasC validation, authentication, Pipeline and agent tests.
6. Compare effective plugin inventory against approved manifest.
7. Approve production rollout and rollback.

Avoid upgrading core and all plugins simultaneously unless the compatibility plan explicitly requires it; smaller change batches simplify diagnosis.

## 7. Plugin lifecycle

```text
Request → security/maintenance review → dependency resolution
       → test image → staging acceptance → change approval
       → production rollout → post-change verification
       → periodic audit / retirement
```

Document plugin owner, use case, installed version, dependency tree, advisory exposure, replacement strategy and removal risk.

## 8. Safe upgrade strategy

For controller containers, prefer immutable image rebuild and rolling replacement at the **service architecture** level, not two active Jenkins controllers sharing the same Jenkins home. Jenkins controller state is not generally safe for simultaneous writers. Use planned maintenance, quiet down/drain, verified backup, image rollout, startup checks and job smoke tests.

For VM-based controllers, test plugin changes on a restored staging clone before applying to production.

## 9. Failure and recovery

Common issues include unmet dependency, unsupported core version, incompatible Java runtime, failed plugin initialization, class loading conflicts, JCasC schema changes, missing Pipeline steps and agent protocol mismatch.

**Recovery procedure:**
1. Stop new builds and preserve logs.
2. Identify the first plugin/core initialization failure.
3. Compare baseline vs proposed versions and dependencies.
4. Restore tested image/plugin set and compatible Jenkins home backup if required.
5. Start isolated recovery controller and validate jobs/security.
6. Reopen builds only after health checks and incident review.

Do not blindly downgrade plugins against a Jenkins home that has undergone incompatible data migrations.

## 10. Observability

Monitor controller startup time, failed plugin loads, disabled plugins, update center reachability, plugin advisories, JVM memory/GC, executor availability, Pipeline step failures and plugin-related exceptions. Record plugin inventory as change evidence; correlate failures with deployment timestamps.

## 11. Security controls

- Restrict plugin install/update rights to approved administrators.
- Use trusted update centers and artifact sources.
- Pin reviewed versions and scan advisories.
- Remove unused plugins after dependency review.
- Test SSO, RBAC, credentials and Script Console permissions after upgrades.
- Keep plugin credentials out of Docker build context and logs.
- Audit changes to `plugins.txt`, image digest and Jenkins home.
- Treat plugin deprecation or abandonment as operational risk.

## 12. Troubleshooting matrix

| Symptom | Likely cause | Response |
|---|---|---|
| Plugin failed to load | Missing/incompatible dependency | Inspect startup logs/dependency |
| Jenkins requires newer core | Plugin minimum core | Plan core upgrade or compatible plugin |
| Missing Pipeline step | Workflow plugin unavailable | Restore approved plugin |
| JCasC rejects YAML | Plugin schema drift | Export/validate installed schema |
| Role assignments disappear | Authorization plugin/config mismatch | Restore known-good JCasC |
| Kubernetes agents fail | Plugin/agent protocol mismatch | Check versions and remoting |
| UI error after upgrade | Plugin API incompatibility | Roll back tested set |
| Plugin security advisory | Vulnerable installed version | Patch/test and deploy |
| Update center unavailable | Proxy/TLS/network | Restore connectivity |
| Plugin dependency cycle/conflict | Version constraints | Resolve in staging |
| Slow startup | Plugin initialization/dependency | Profile logs/heap |
| Plugin disabled unexpectedly | Failed startup/admin change | Inspect audit/config |
| Secret binding fails | Credentials plugin regression | Validate integration |
| Git checkout fails | SCM plugin compatibility | Test supported versions |
| Agent channel drops | Remoting compatibility | Align supported versions |
| Controller OOM | Plugin memory/leak | Capture heap/GC, rollback |

## 13. Production runbooks

### A. New plugin request
1. Confirm business need and alternatives.
2. Review maintenance status, advisories and dependencies.
3. Add approved version to manifest.
4. Build/test staging image.
5. Approve rollout and record owner.

### B. Plugin upgrade
1. Back up controller and capture baseline.
2. Resolve dependencies and compatibility.
3. Run staging security/Pipeline tests.
4. Quiet down/drain and deploy approved image.
5. Validate startup, auth, agents, jobs and monitoring.

### C. Plugin startup incident
1. Freeze changes and collect logs.
2. Identify failed plugin and dependency chain.
3. Restore tested image and compatible state.
4. Run acceptance tests.
5. Complete RCA and regression test.

### D. Security advisory response
1. Identify affected core/plugin versions.
2. Assess exploitability and exposure.
3. Patch/test with urgency appropriate to risk.
4. Deploy approved remediation or compensating control.
5. Document residual risk and verification.

### E. Plugin retirement
1. Find dependent plugins, jobs, JCasC and shared libraries.
2. Migrate functionality and test.
3. Remove plugin from manifest and rebuild staging.
4. Validate absence of dependent failures.
5. Retire with rollback evidence.

## 14. Acceptance criteria

- [ ] Core/Java/plugin inventory captured.
- [ ] Approved plugin manifest versioned in Git.
- [ ] Dependencies resolved and reviewed.
- [ ] Security advisories checked.
- [ ] Staging startup and JCasC tests pass.
- [ ] SSO/RBAC/credentials tests pass after changes.
- [ ] Agent and representative Pipeline smoke tests pass.
- [ ] Rollback tested on disposable controller.
- [ ] Plugin owner and retirement process documented.
- [ ] Production rollout change evidence retained.

**Companion:** [Chapter 061 hands-on lab](labs/061-jenkins-plugin-architecture-lifecycle-dependency-management-check.md).  
**Next:** Chapter 062 — Jenkins Configuration as Code (JCasC) Architecture and Automation.
