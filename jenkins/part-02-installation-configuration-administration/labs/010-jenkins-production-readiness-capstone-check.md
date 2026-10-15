# Chapter 010 — Hands-On Capstone: Jenkins Production Readiness Check

**Parent:** [Chapter 010](../010-jenkins-installation-configuration-administration-production-readiness-capstone.md)

## Goal

Assess a disposable Jenkins controller and produce a production-readiness design dossier. **Do not claim production readiness** from localhost-only testing; TLS/SSO/DR integration gates need independently verified staging/production evidence.

## Safety

Docker Linux containers, free localhost port 8088, dedicated volume, no real secrets, no public exposure and no destructive fault injection.

## Lab 01 — Confirm Docker host and capacity

```bash
docker version
docker ps
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Disposable host and resources confirmed. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 02 — Create protected home volume

```bash
docker volume create jenkins-ch010-home
docker volume inspect jenkins-ch010-home
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Dedicated volume exists. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 03 — Launch controller

```bash
docker run -d --name jenkins-ch010 --restart=no -p 127.0.0.1:8088:8080 --memory 4g --cpus 2 --mount source=jenkins-ch010-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Controller starts privately. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 04 — Review startup health

```bash
docker logs --tail 80 jenkins-ch010
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** No fatal errors. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 05 — Complete private bootstrap

```bash
docker exec jenkins-ch010 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Follow-up:** Complete first-run setup privately at http://127.0.0.1:8088.

**Pass:** Named lab admin; unlock secret never recorded. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 06 — Verify controller isolation

```bash
docker ps --filter name=jenkins-ch010
```

**Follow-up:** Set Manage Jenkins → Nodes → Built-In Node → executors = 0.

**Pass:** Built-in executors zero. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 07 — Inspect image and runtime identity

```bash
docker inspect jenkins-ch010 --format '{{.Config.Image}} {{.Config.User}}'
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Image and non-root user recorded. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 08 — Inspect JENKINS_HOME volume

```bash
docker inspect jenkins-ch010 --format '{{json .Mounts}}'
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Persistent mount correct. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 09 — Inspect home and capacity

```bash
docker exec jenkins-ch010 sh -c 'printf "JENKINS_HOME=%s\n" "$JENKINS_HOME"; df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Effective home and storage recorded. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 10 — Verify private backend listener

```bash
docker port jenkins-ch010
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Only localhost port published. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 11 — Review Jenkins URL/TLS architecture

```bash
docker logs --tail 20 jenkins-ch010
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Production HTTPS proxy and URL design documented. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 12 — Review SSO and RBAC

```bash
docker inspect jenkins-ch010 --format '{{.State.Status}}'
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Least privilege and audited break-glass design. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 13 — Review plugin and JCasC catalog

```bash
docker exec jenkins-ch010 java -version
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Version compatibility and config review documented. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 14 — Review credentials boundaries

```bash
docker inspect jenkins-ch010 --format '{{.Config.User}}'
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** No production secrets in lab or evidence. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 15 — Run no-agent Pipeline smoke

```bash
docker logs --tail 40 jenkins-ch010
```

**Follow-up:** Create a disposable Pipeline job using the Jenkinsfile in the parent chapter and record build number/result.

**Pass:** Parent chapter Jenkinsfile succeeds. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 16 — Design agent isolation

```bash
docker stats --no-stream jenkins-ch010
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Trusted/untrusted agents and resource isolation specified. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 17 — Restart and validate persistence

```bash
docker restart jenkins-ch010
docker logs --tail 60 jenkins-ch010
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** Admin config and job persist. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 18 — Define SLOs and alerts

```bash
docker stats --no-stream jenkins-ch010
```

**Follow-up:** Record redacted observed evidence, distinguish actual tests from design-only checks.

**Pass:** HTTP, JVM, queue, disk, agent and backup monitoring plan. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 19 — Write backup/restore rehearsal

```bash
docker volume inspect jenkins-ch010-home
```

**Follow-up:** Document backup manifest and clean-room restore verification steps; do not claim restore was tested unless actually performed.

**Pass:** Encryption keys, snapshot consistency, RPO/RTO and clean-room restore. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Lab 20 — Complete incident and cleanup

```bash
docker stop jenkins-ch010
docker rm jenkins-ch010
# After exclusive ownership verification: docker volume rm jenkins-ch010-home
```

**Follow-up:** Use controller startup failure, SSO redirect loop and backup key mismatch as tabletop incidents. Remove only lab-owned resources.

**Pass:** Three tabletop incidents, acceptance, cleanup and signoff. **Rollback:** revert approved lab changes or restore verified lab snapshot; never delete shared state.

## Ten readiness gates

| Gate | Lab evidence | Production evidence |
|---|---|---|
| G1 — Supported runtime | Image/Java inspection | Approved immutable image/package |
| G2 — Persistent state | Volume and restart | Storage/backup review |
| G3 — Secure administration | Named admin | SSO/MFA/RBAC |
| G4 — Controller isolation | Zero executors | Agent isolation audit |
| G5 — HTTPS and private backend | Localhost bind | Valid TLS and proxy tests |
| G6 — Config and plugin governance | Version inventory | Staging JCasC and plugin tests |
| G7 — Pipeline and agents | No-agent smoke | Isolated agent build |
| G8 — Monitoring | Baseline design | Live alerts/on-call |
| G9 — Recovery | Restore plan | Clean-room restore evidence |
| G10 — Handoff | Runbooks and score | Signed go-live approval |

## Troubleshooting tabletop

| Scenario | Evidence | Recovery |
|---|---|---|
| Jenkins fails to start | Container logs and image ID | Restore supported runtime |
| Wrong home mounted | Docker volume and config | Reattach correct state |
| Plugin incompatible | Plugin/core/Java matrix | Restore tested catalog |
| SSO redirect loop | Root URL and headers | Correct trusted HTTPS configuration |
| Webhook rejected | Provider signature and endpoint | Restore signed delivery |
| Controller OOM | Docker state and JVM/GC | Profile and right-size |
| Secrets lost | Backup manifest and keys | Restore complete protected set |
| Disk full | df -h and df -i | Expand or approved retention |

## Scoring (100 points)

| Domain | Points |
|---|---:|
| Installation and runtime | 15 |
| Persistence and security | 20 |
| Config/plugins/secrets | 15 |
| TLS/access/network | 15 |
| Pipeline and agent design | 10 |
| Monitoring, incidents and DR | 15 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Educational pass:** 90+ and no critical security failure. A separate production go-live review is required.

## Evidence and signoff template

```text
Operator/date:
Host and runtime:
Jenkins/Java version and image digest:
Controller executor count:
Volume/home and restart proof:
Backend binding:
TLS/SSO production design:
Plugin/JCasC catalog:
Credential trust boundary:
Pipeline result:
Agent isolation plan:
Monitoring and alert ownership:
Backup/restore test status:
Three incident diagnoses:
Lab cleanup proof:
Lab score:
Production gates independently verified:
Approver/decision/residual risks:
```

**Part 02 complete when reviewed. Next:** Chapter 011 — Jenkins Controller Architecture, Responsibilities and Operational Boundaries.
