# Chapter 025 — Hands-On Lab: Declarative and Scripted Pipeline Production Reliability Capstone

**Parent:** [Chapter 025](../025-declarative-scripted-pipeline-production-reliability-capstone.md)

## Objective and safety

Compare Declarative and Scripted Pipeline reliability behavior on a disposable localhost controller. No built-in controller executors, external secrets, shell, workspace, live release or external notifications. Run commands below on the Docker **host**. The Pipeline definitions are in the parent chapter.

## Exercise 01 — Validate Docker host

```bash
docker version
docker ps
```

**Operator action:** Record observed redacted evidence; do not claim design-only integrations were executed.

**Pass:** Docker available. **Rollback:** revert lab-owned changes only.

## Exercise 02 — Create lab volume

```bash
docker volume create jenkins-ch025-home
```

**Operator action:** Record observed redacted evidence; do not claim design-only integrations were executed.

**Pass:** Dedicated volume. **Rollback:** revert lab-owned changes only.

## Exercise 03 — Start private controller

```bash
docker run -d --name jenkins-ch025 --restart=no -p 127.0.0.1:8103:8080 --memory 4g --cpus 2 --mount source=jenkins-ch025-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator action:** Record observed redacted evidence; do not claim design-only integrations were executed.

**Pass:** Controller running. **Rollback:** revert lab-owned changes only.

## Exercise 04 — Review startup

```bash
docker logs --tail 60 jenkins-ch025
```

**Operator action:** Record observed redacted evidence; do not claim design-only integrations were executed.

**Pass:** Startup healthy. **Rollback:** revert lab-owned changes only.

## Exercise 05 — Confirm localhost listener

```bash
docker port jenkins-ch025
```

**Operator action:** Record observed redacted evidence; do not claim design-only integrations were executed.

**Pass:** Loopback only. **Rollback:** revert lab-owned changes only.

## Exercise 06 — Bootstrap named admin

```bash
docker exec jenkins-ch025 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator action:** Unlock privately at http://127.0.0.1:8103, create named admin, never record the unlock password.

**Pass:** Private unlock. **Rollback:** revert lab-owned changes only.

## Exercise 07 — Set controller executors zero

```bash
docker ps --filter name=jenkins-ch025
```

**Operator action:** Set Manage Jenkins → Nodes → Built-In Node → executors = 0.

**Pass:** No controller executors. **Rollback:** revert lab-owned changes only.

## Exercise 08 — Inspect runtime image

```bash
docker inspect jenkins-ch025 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator action:** Record observed redacted evidence; do not claim design-only integrations were executed.

**Pass:** Runtime recorded. **Rollback:** revert lab-owned changes only.

## Exercise 09 — Inspect persistent home

```bash
docker inspect jenkins-ch025 --format '{{json .Mounts}}'
```

**Operator action:** Record observed redacted evidence; do not claim design-only integrations were executed.

**Pass:** Dedicated volume. **Rollback:** revert lab-owned changes only.

## Exercise 10 — Baseline disk and inodes

```bash
docker exec jenkins-ch025 sh -c 'df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Operator action:** Record observed redacted evidence; do not claim design-only integrations were executed.

**Pass:** Capacity baseline. **Rollback:** revert lab-owned changes only.

## Exercise 11 — Create Declarative smoke

```bash
docker logs --tail 15 jenkins-ch025
```

**Operator action:** Create ch025-declarative and paste the Declarative Jenkinsfile in the parent chapter.

**Pass:** Declarative job configured. **Rollback:** revert lab-owned changes only.

## Exercise 12 — Run dev success

```bash
docker stats --no-stream jenkins-ch025
```

**Operator action:** Run TARGET=dev, FAIL_DEMO=false, RETRY_DEMO=false and capture SUCCESS/skipped staging.

**Pass:** SUCCESS and skip staging. **Rollback:** revert lab-owned changes only.

## Exercise 13 — Run staging success

```bash
docker logs --tail 25 jenkins-ch025
```

**Operator action:** Run TARGET=staging and capture SUCCESS/staging path.

**Pass:** SUCCESS and staging branch. **Rollback:** revert lab-owned changes only.

## Exercise 14 — Run intentional failure

```bash
docker logs --tail 25 jenkins-ch025
```

**Operator action:** Run FAIL_DEMO=true and verify terminal FAILURE and post/finally.

**Pass:** FAILURE and post action. **Rollback:** revert lab-owned changes only.

## Exercise 15 — Run retry simulation

```bash
docker logs --tail 25 jenkins-ch025
```

**Operator action:** Run RETRY_DEMO=true, FAIL_DEMO=false and verify two attempts then SUCCESS.

**Pass:** Two attempts then SUCCESS. **Rollback:** revert lab-owned changes only.

## Exercise 16 — Run Scripted equivalent

```bash
docker stats --no-stream jenkins-ch025
```

**Operator action:** Create ch025-scripted with the same typed parameters; paste Scripted Jenkinsfile and compare result/branch behavior.

**Pass:** Equivalent branch and result. **Rollback:** revert lab-owned changes only.

## Exercise 17 — Review agent/secret trust

```bash
docker inspect jenkins-ch025 --format '{{.Config.Image}}'
```

**Operator action:** Review approved agent pool, credential isolation, JUnit/artifact provenance; mark unexecuted staging gates design-only.

**Pass:** Approved agent and credential design. **Rollback:** revert lab-owned changes only.

## Exercise 18 — Review SLO and rollback

```bash
docker exec jenkins-ch025 sh -c 'df -h /var/jenkins_home'
```

**Operator action:** Document queue p95, retry counts, failure SLO, immutable release and rollback commit.

**Pass:** Reliability scorecard. **Rollback:** revert lab-owned changes only.

## Exercise 19 — Three incident tabletops

```bash
docker logs --tail 40 jenkins-ch025
```

**Operator action:** Tabletop secret exposure, retry duplicate deployment and CPS serialization failure.

**Pass:** Triage, containment and recovery. **Rollback:** revert lab-owned changes only.

## Exercise 20 — Cleanup and score

```bash
docker stop jenkins-ch025
docker rm jenkins-ch025
```

**Operator action:** Remove the volume only after confirming exclusive lab ownership.

**Pass:** Lab controller removed. **Rollback:** revert lab-owned changes only.

## Jenkinsfiles under test

Use the two complete Jenkinsfiles in the parent chapter:

- `ch025-declarative`: Declarative syntax, typed parameters, `when`, `retry`, `post`.
- `ch025-scripted`: Scripted `stage`, `if`, `retry`, `try/catch/finally`.

For Scripted, configure `TARGET` as choice `dev`/`staging`, and `FAIL_DEMO`/`RETRY_DEMO` as booleans. Keep the controller executors at zero.

## Comparative acceptance matrix

| Case | Declarative | Scripted | Evidence |
|---|---|---|---|
| Dev success | SUCCESS, staging skipped | SUCCESS, staging not entered | |
| Staging success | SUCCESS, staging executed | SUCCESS, staging executed | |
| Transient retry | 2 attempts then SUCCESS | 2 attempts then SUCCESS | |
| Terminal failure | FAILURE + post failure | FAILURE + catch/finally | |
| Invalid target | Rejected | Rejected | |
| Agent trust | Design-only unless staged | Design-only unless staged | |
| JUnit/artifact | Design-only unless staged | Design-only unless staged | |
| Restart durability | Separate staging drill | Separate staging drill | |

## Incident tabletop

| Incident | First checks | Safe recovery |
|---|---|---|
| Agent starvation | Labels, online agents, provisioner | Restore approved pool |
| Secret leaked in logs | Console, bindings, access audit | Restrict and rotate |
| Retry duplicates release | Attempt history and idempotency | Stop and reconcile |
| Timeout or abort swallowed | Interruption stack and catches | Rethrow interruption |
| CPS serialization failure | Suspended state and stack | Refactor durable state |
| Artifact not traceable | Digest, registry, SCM SHA | Block release and rebuild |

## Ten gate evidence worksheet

| Gate | Pass / Fail / Design-only | Evidence |
|---|---|---|
| G1 Zero controller executors | | |
| G2 Reviewed Jenkinsfile | | |
| G3 Parameter/condition controls | | |
| G4 Dev/staging branches | | |
| G5 Retry/failure | | |
| G6 Post/finally/interruption | | |
| G7 Agent/credential isolation | | |
| G8 Artifacts/tests/rollback | | |
| G9 SRE tabletop/SLO | | |
| G10 Cleanup and signoff | | |

## Assessment — 100 points

| Domain | Points |
|---|---:|
| Declarative and Scripted | 25 |
| Inputs/agents/security | 20 |
| Error and recovery | 20 |
| CPS/rollback | 15 |
| SRE response | 10 |
| Evidence/cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ and no critical security failure. Production acceptance requires staging proof and independent approval.

## Evidence handoff

```text
Operator/date:
Controller URL:
Built-in executors:
Lab volume:
Declarative dev SUCCESS:
Declarative staging SUCCESS:
Declarative FAILURE:
Declarative retry SUCCESS:
Scripted dev/staging:
Scripted failure/retry:
Agent and credential review:
CPS/restart plan:
Artifact/JUnit provenance plan:
SLO, alert and rollback owners:
Three incident analyses:
Cleanup proof:
Score/reviewer:
Residual risks and approval:
```

**Part 05 complete. Next:** Chapter 026 — Groovy Fundamentals for Jenkins Pipelines and Shared Libraries.
