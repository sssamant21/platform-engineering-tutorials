# Chapter 072 — Jenkins Controller Startup, Plugin and Configuration Failure Troubleshooting

**Part 15 — Troubleshooting and Incident Response**  
**Audience:** Jenkins SRE, platform engineers, incident responders  
**Prerequisites:** Chapter 071, isolated Jenkins LTS, tested backup, container or VM deployment, JCasC and plugin manifest.

## Learning objectives

Diagnose controller boot failures, plugin dependency errors, JCasC validation problems, broken credentials providers, Jenkins home permissions and Java/core incompatibility. Recover safely using known-good artifacts while preserving evidence and state.

## 1. Controller startup lifecycle

```text
OS/container → JVM → Jenkins WAR/core → plugins/dependencies
                                      ↓
                               JCasC/init hooks
                                      ↓
                            credentials/security/jobs
                                      ↓
                          HTTP ready + agents + builds
```

A running process is not proof of readiness. Validate user-facing login, job inventory, agent connectivity and a representative synthetic build after recovery.

## 2. Initial incident decision tree

1. Is the process/pod running or repeatedly restarting?
2. Is it JVM startup, Jenkins core initialization, plugin loading, JCasC or external dependency?
3. Did a core/plugin/image/JCasC/secret change precede failure?
4. Are Jenkins home storage, permissions and encryption keys intact?
5. Is the UI blocked by proxy/SSO rather than controller startup?
6. What is the safest tested rollback path?

Preserve logs, container status, events and current image/plugin inventory **before** any restart or rollback.

## 3. Kubernetes diagnostics

```sh
kubectl get pods -n jenkins -o wide
kubectl describe pod -n jenkins <controller-pod>
kubectl logs -n jenkins <controller-pod> --previous
kubectl logs -n jenkins <controller-pod> --since=30m
kubectl get events -n jenkins --sort-by=.lastTimestamp
```

Replace placeholders with real resource names. Previous logs may not exist if the container has not restarted. On VM installations inspect service manager logs, filesystem and JVM startup options.

## 4. JVM and core compatibility

Inspect Java version, Jenkins core requirements, heap flags, container limits, file permissions, JVM native memory and exit status. Do not blindly increase heap: leave room for native memory, threads and plugin overhead. Compare installed Java/core/plugin compatibility matrix with the approved build manifest.

## 5. Plugin dependency troubleshooting

Symptoms include failed plugin initialization, missing Pipeline steps, class-loading errors and disabled required dependencies.

Workflow:
1. Inventory core and installed plugins/versions.
2. Locate first meaningful startup exception, not only the final cascade.
3. Inspect missing, disabled, incompatible or circular plugin dependencies.
4. Compare approved plugin lock and release notes.
5. Rebuild tested immutable image in staging.
6. Restore from a compatible backup if plugin changes mutated persisted state.
7. Validate jobs, RBAC, credentials and agents.

**Never blindly delete plugin files from a live Jenkins home.** Downgrades can be incompatible with persisted configuration.

## 6. JCasC and init-hook failures

Common causes: invalid YAML, duplicate root settings, unknown attributes after plugin changes, missing secret substitutions, invalid credentials provider, incompatible security realm and unexpected initialization order.

Recommended checks:
- Validate YAML syntax and duplicate keys.
- Validate schema against **the exact Jenkins core and plugin set**.
- Confirm `CASC_JENKINS_CONFIG` paths and read permissions.
- Verify secret provider connectivity without printing values.
- Review init Groovy hooks and Job DSL side effects.
- Compare Git revision with last known-good controller configuration.

A syntactically valid YAML file can still be invalid for installed JCasC schemas.

## 7. Storage, permissions and identity

Check Jenkins home filesystem capacity/inodes, ownership, volume mounts, read-only filesystem, backup/restore state, secrets and encryption keys. Missing Jenkins secrets or master-key material can make credentials unreadable even when jobs load. Protect and restore keys from approved backups; never create replacement keys to force a boot without assessing impact.

## 8. Reverse proxy, TLS and SSO

If the controller is ready but the UI is unavailable, check ingress/service, HTTP status, context path, redirect URL, TLS certificate chain, proxy headers, SSO issuer and clock skew. Do not disable TLS validation or switch to permissive authentication as a quick fix.

## 9. Safe recovery and rollback

1. Declare impact and freeze additional configuration changes.
2. Preserve diagnostic evidence and verify backup integrity.
3. Identify last known-good core/plugin/JCasC/image combination.
4. Reproduce failure in staging with a **copy** of sanitized state.
5. Apply approved correction or restore compatible snapshot.
6. Ensure only one controller writes to Jenkins home.
7. Validate readiness, RBAC, credentials, jobs, queue and agents.
8. Record recovery timestamp, residual risks and RCA owner.

Rollback means restoring compatible application state, not merely reverting a container tag.

## 10. Failure scenarios

| # | Failure | Evidence and remediation |
|---|---|---|
| 01 | Wrong Java version | Core requirements and JVM log |
| 02 | Invalid JVM option | Startup stderr |
| 03 | Heap exceeds pod limit | OOMKilled and memory config |
| 04 | Missing plugin dependency | Plugin load log |
| 05 | Plugin requires newer core | Compatibility report |
| 06 | Plugin class linkage error | Stack trace/version diff |
| 07 | Disabled essential plugin | Plugin inventory |
| 08 | Incompatible plugin downgrade | Restore tested state |
| 09 | Invalid JCasC YAML | Parser output |
| 10 | Unknown JCasC attribute | Schema validation |
| 11 | Duplicate JCasC root config | Conflict output |
| 12 | Missing JCasC environment secret | Provider health |
| 13 | Broken init Groovy hook | Init log |
| 14 | Job DSL seed fails after boot | Seed console and approvals |
| 15 | Jenkins home read-only | Mount/permissions |
| 16 | Disk/inodes exhausted | Filesystem stats |
| 17 | Missing encryption key | Credentials errors |
| 18 | Reverse proxy redirects wrong | Headers/context path |
| 19 | SSO realm unavailable | Auth logs/IdP |
| 20 | CrashLoop after upgrade | Image/plugin/config diff |

## 11. Five production runbooks

### A. CrashLoopBackOff
Inspect pod events, previous logs and exit code; isolate JVM/core/plugin/JCasC stage; compare recent changes; restore tested image/state; verify readiness and build execution.

### B. Plugin startup failure
Identify first dependency exception; inspect core and plugin compatibility; rebuild plugin set; stage-test; deploy approved artifact with backup and rollback.

### C. JCasC initialization failure
Validate syntax and schema against installed plugins; verify paths and secret substitutions; correct Git-managed configuration; redeploy; test RBAC and jobs.

### D. Jenkins home corruption or permission failure
Stop concurrent writers; preserve snapshot; inspect mount ownership, capacity and errors; restore verified compatible backup; test credentials and jobs.

### E. UI/SSO unavailable
Distinguish controller readiness from ingress/SSO failure; check proxy, TLS and IdP; repair configuration through change control; validate privileged and unprivileged access.

## 12. Incident evidence worksheet

```text
Incident ID / severity:
UTC detection time:
Controller image digest:
Jenkins core / Java / plugins:
Pod/VM exit code and restart reason:
First startup exception:
JCasC Git revision:
Jenkins home storage/permissions:
Recent change:
Hypothesis and falsification:
Backup compatibility:
Mitigation and risk:
Recovery verification:
RCA/COA owner:
```

## 13. Acceptance criteria

- [ ] Failure stage identified from evidence.
- [ ] Core/Java/plugin/JCasC compatibility checked.
- [ ] Credentials and encryption keys protected.
- [ ] No destructive plugin/home cleanup.
- [ ] Recovery artifact and backup verified.
- [ ] Controller UI and API accessible.
- [ ] RBAC and secret access tested.
- [ ] Representative Pipeline and agents healthy.
- [ ] Incident timeline and RCA/COA documented.
- [ ] On-call handover completed.

**Companion:** [Chapter 072 hands-on lab](labs/072-jenkins-controller-startup-plugin-configuration-failure-troubleshooting-check.md).  
**Next:** Chapter 073 — Jenkins Pipeline, SCM, Credentials and Build Failure Troubleshooting.
