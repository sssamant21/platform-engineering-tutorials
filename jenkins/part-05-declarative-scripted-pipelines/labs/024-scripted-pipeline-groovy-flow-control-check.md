# Chapter 024 — Hands-On Lab: Scripted Pipeline Groovy, Node, Stage and Flow Control

**Parent:** [Chapter 024](../024-scripted-pipeline-groovy-node-stage-flow-control.md)

## Safety and setup

Use a disposable localhost controller, no built-in executors, no external credentials, no real deployment and no shell commands from Pipeline. The Docker commands below manage the lab controller from the **host**, not from Jenkins. Review the parent chapter's runnable Scripted Jenkinsfile and paste it into a Pipeline job.

## Exercise 01 — Docker prerequisite

```bash
docker version
docker ps
```

**Operator action:** Capture observed redacted evidence and distinguish design-only controls.

**Pass:** Docker available. **Rollback:** revert only lab-owned changes.

## Exercise 02 — Create isolated volume

```bash
docker volume create jenkins-ch024-home
```

**Operator action:** Capture observed redacted evidence and distinguish design-only controls.

**Pass:** Volume created. **Rollback:** revert only lab-owned changes.

## Exercise 03 — Start localhost Jenkins

```bash
docker run -d --name jenkins-ch024 --restart=no -p 127.0.0.1:8102:8080 --memory 4g --cpus 2 --mount source=jenkins-ch024-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator action:** Capture observed redacted evidence and distinguish design-only controls.

**Pass:** Controller started. **Rollback:** revert only lab-owned changes.

## Exercise 04 — Check startup logs

```bash
docker logs --tail 60 jenkins-ch024
```

**Operator action:** Capture observed redacted evidence and distinguish design-only controls.

**Pass:** Startup healthy. **Rollback:** revert only lab-owned changes.

## Exercise 05 — Check binding

```bash
docker port jenkins-ch024
```

**Operator action:** Capture observed redacted evidence and distinguish design-only controls.

**Pass:** Loopback only. **Rollback:** revert only lab-owned changes.

## Exercise 06 — Unlock privately

```bash
docker exec jenkins-ch024 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator action:** Unlock at http://127.0.0.1:8102, create a named admin and never retain the unlock secret.

**Pass:** Private admin created. **Rollback:** revert only lab-owned changes.

## Exercise 07 — Disable controller executors

```bash
docker ps --filter name=jenkins-ch024
```

**Operator action:** Manage Jenkins → Nodes → Built-In Node → executors = 0.

**Pass:** Zero built-in executors. **Rollback:** revert only lab-owned changes.

## Exercise 08 — Inspect runtime

```bash
docker inspect jenkins-ch024 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator action:** Capture observed redacted evidence and distinguish design-only controls.

**Pass:** Runtime recorded. **Rollback:** revert only lab-owned changes.

## Exercise 09 — Inspect volume mount

```bash
docker inspect jenkins-ch024 --format '{{json .Mounts}}'
```

**Operator action:** Capture observed redacted evidence and distinguish design-only controls.

**Pass:** Dedicated state. **Rollback:** revert only lab-owned changes.

## Exercise 10 — Inspect disk/inodes

```bash
docker exec jenkins-ch024 sh -c 'df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Operator action:** Capture observed redacted evidence and distinguish design-only controls.

**Pass:** Capacity baseline. **Rollback:** revert only lab-owned changes.

## Exercise 11 — Create Scripted Pipeline job

```bash
docker logs --tail 15 jenkins-ch024
```

**Operator action:** Create Pipeline ch024-scripted-flow and paste the Jenkinsfile from the parent chapter. Configure TARGET choice dev/staging and FAIL_ONCE/FORCE_FAIL boolean parameters.

**Pass:** Scripted definition saved. **Rollback:** revert only lab-owned changes.

## Exercise 12 — Run dev success

```bash
docker stats --no-stream jenkins-ch024
```

**Operator action:** Run TARGET=dev, FAIL_ONCE=false, FORCE_FAIL=false; inspect stages.

**Pass:** SUCCESS dev path. **Rollback:** revert only lab-owned changes.

## Exercise 13 — Run staging success

```bash
docker logs --tail 25 jenkins-ch024
```

**Operator action:** Run TARGET=staging and confirm the staging branch.

**Pass:** SUCCESS staging path. **Rollback:** revert only lab-owned changes.

## Exercise 14 — Run retry simulation

```bash
docker logs --tail 25 jenkins-ch024
```

**Operator action:** Run FAIL_ONCE=true and verify exactly two attempts.

**Pass:** Two attempts and SUCCESS. **Rollback:** revert only lab-owned changes.

## Exercise 15 — Run terminal failure

```bash
docker logs --tail 25 jenkins-ch024
```

**Operator action:** Run FORCE_FAIL=true and verify FAILURE and FINALLY output.

**Pass:** FAILURE and finally. **Rollback:** revert only lab-owned changes.

## Exercise 16 — Inspect stage and trace

```bash
docker inspect jenkins-ch024 --format '{{.State.Status}}'
```

**Operator action:** Confirm three bounded loop iterations and trace count.

**Pass:** Three bounded iterations. **Rollback:** revert only lab-owned changes.

## Exercise 17 — Review node/agent design

```bash
docker stats --no-stream jenkins-ch024
```

**Operator action:** Review the parent node('lab-linux') example; mark design-only unless an approved isolated agent exists.

**Pass:** Isolated agent requirement. **Rollback:** revert only lab-owned changes.

## Exercise 18 — Review CPS/security

```bash
docker inspect jenkins-ch024 --format '{{.Config.Image}}'
```

**Operator action:** Document CPS/serialization, Script Approval and credential scope without changing global policy.

**Pass:** Durability and approvals documented. **Rollback:** revert only lab-owned changes.

## Exercise 19 — Three incident tabletop drills

```bash
docker logs --tail 40 jenkins-ch024
```

**Operator action:** Tabletop missing node, CPS serialization and swallowed interruption; record safe rollback.

**Pass:** Diagnoses and rollback. **Rollback:** revert only lab-owned changes.

## Exercise 20 — Cleanup and score

```bash
docker stop jenkins-ch024
docker rm jenkins-ch024
```

**Operator action:** Remove the volume only after verifying exclusive lab ownership.

**Pass:** Controller removed. **Rollback:** revert only lab-owned changes.

## Scripted Pipeline under test

Use the exact runnable `ch024-scripted-flow` Pipeline in the parent chapter. It includes `stage`, `if`, `switch`, a bounded `for` loop, `retry(2)`, `try/catch/finally` and interruption propagation. Keep `node` and `sh` out of the local smoke.

## Acceptance matrix

| Case | Parameters | Expected |
|---|---|---|
| A | dev, FAIL_ONCE=false, FORCE_FAIL=false | SUCCESS; dev path |
| B | staging, FAIL_ONCE=false, FORCE_FAIL=false | SUCCESS; staging path |
| C | dev, FAIL_ONCE=true, FORCE_FAIL=false | Two attempts then SUCCESS |
| D | dev, FAIL_ONCE=false, FORCE_FAIL=true | FAILURE; finally executes |
| E | invalid TARGET (design/negative test) | Validation rejects target |
| F | no approved lab-linux (design) | Agent-backed example would queue |

## Incident tabletop

| Incident | Evidence | Safe recovery |
|---|---|---|
| Missing node context | MissingContextVariableException | Allocate isolated node |
| CPS serialization error | NotSerializableException | Remove nonserializable state |
| Retry duplicates release | Side-effect audit | Stop and add idempotency |
| Abort swallowed | Interruption trace | Rethrow interruption |
| Secret in console | Restricted/redacted logs | Rotate and scope |
| Script approval denied | Sandbox log | Refactor or reviewed approval |

## Assessment — 100 points

| Domain | Points |
|---|---:|
| Groovy flow and stages | 25 |
| Node and isolation | 20 |
| Retry/exceptions | 20 |
| CPS/restart | 15 |
| SRE incidents | 10 |
| Evidence/cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ with all security-critical gates.

## Evidence template

```text
Operator/date:
Controller URL:
Built-in executors:
Volume:
Dev SUCCESS build:
Staging SUCCESS build:
Retry attempt logs:
Terminal FAILURE build:
Finally output:
Loop trace:
Agent trust review:
CPS/Script Approval review:
Three incident diagnoses:
Cleanup proof:
Score/reviewer:
```

**Next:** Chapter 025 — Declarative and Scripted Pipeline Production Reliability Capstone.
