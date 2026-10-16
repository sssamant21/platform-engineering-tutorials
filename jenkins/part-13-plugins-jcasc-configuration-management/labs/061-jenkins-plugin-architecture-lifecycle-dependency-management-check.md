# Chapter 061 — Hands-on Lab: Jenkins Plugin Lifecycle and Dependency Management

**Environment:** Disposable Jenkins LTS Docker/Podman container, plugin CLI, Git, test JCasC, synthetic Pipeline jobs. Never experiment on a production controller.

## 20 hands-on exercises

| # | Exercise | Procedure | Evidence |
|---|---|---|---|
| 01 | Inventory | Record core/Java/plugin versions | Baseline |
| 02 | Architecture | Diagram plugin extension/dependency | Diagram |
| 03 | Manifest | Create plugins.txt | Git |
| 04 | CLI | Inspect jenkins-plugin-cli help | Output |
| 05 | Dependencies | Resolve transitive plugin set | Inventory |
| 06 | Image | Build immutable lab controller image | Digest |
| 07 | Startup | Verify clean plugin initialization | Logs |
| 08 | JCasC | Validate security configuration | Result |
| 09 | Auth | Test admin/developer access | Matrix |
| 10 | Credentials | Test synthetic binding | Build |
| 11 | SCM | Test Git checkout | Build |
| 12 | Pipeline | Run representative Declarative job | Build |
| 13 | Agents | Validate agent connection | Status |
| 14 | Advisory | Review security notices | Report |
| 15 | Upgrade | Pin and test one plugin update | Diff |
| 16 | Negative | Introduce incompatible dependency in lab | Failure |
| 17 | Recovery | Restore known-good image/plugin set | RTO |
| 18 | Drift | Compare actual vs manifest | Report |
| 19 | Retirement | Test unused plugin removal | Diff |
| 20 | Review | Complete acceptance and sign-off | Report |

## 12 troubleshooting drills

1. Missing required dependency.
2. Plugin requires newer Jenkins core.
3. Unsupported Java runtime.
4. Plugin fails initialization.
5. Missing Pipeline DSL step.
6. JCasC schema mismatch.
7. Authorization plugin regression.
8. Credential binding regression.
9. SCM checkout plugin error.
10. Kubernetes agent compatibility issue.
11. Plugin security advisory.
12. Rollback after incompatible plugin upgrade.

Mark unavailable integrations blocked, not passed. Use a disposable controller and backed-up synthetic state.

## Lab files

```text
plugin-lab/
  Dockerfile
  plugins.txt
  evidence/
    plugin-inventory.txt
    startup.log
    acceptance.md
```

## Commands

```sh
jenkins-plugin-cli --version
jenkins-plugin-cli --help
docker build -t jenkins-plugin-lab:ch061 .
docker image inspect jenkins-plugin-lab:ch061 --format '{{.Id}}'
```

Run plugin CLI commands in the Jenkins image or host where installed. Use pinned versions and digest in production.

## Evidence template

```text
UTC timestamp:
Jenkins core/Java versions:
Plugin manifest revision:
Resolved plugin inventory:
Controller image digest:
Security advisory review:
JCasC/auth/credentials tests:
SCM/Pipeline/agent tests:
Injected failure:
Recovery image/state:
Measured recovery:
Reviewer:
```

## Acceptance checklist

- [ ] 20 exercises attempted and documented.
- [ ] 12 drills completed or blocked.
- [ ] Plugin manifest and dependencies reproducible.
- [ ] Startup and security smoke tests pass.
- [ ] Failed plugin upgrade recovered safely.
- [ ] No production controller changed.
- [ ] Reviewer signs off.

**Related:** [Chapter 061 — Jenkins Plugin Architecture, Lifecycle and Dependency Management](../061-jenkins-plugin-architecture-lifecycle-dependency-management.md).
