# Chapter 026 — Hands-On Lab: Groovy Fundamentals for Jenkins Pipelines

**Parent:** [Chapter 026](../026-groovy-fundamentals-jenkins-pipelines-shared-libraries.md)

## Objective and safety

Validate Groovy variables, maps, lists, closures, branches, exception handling and CPS design on a disposable localhost Jenkins controller. **No controller executors, shell, external credentials or deployment.** Docker commands below run on the host.

## Exercise 01 — Check Docker runtime

```bash
docker version
docker ps
```

**Operator action:** Capture observed redacted evidence; do not claim design-only gates were executed.

**Pass:** Docker available. **Rollback:** revert lab-owned changes only.

## Exercise 02 — Create isolated state

```bash
docker volume create jenkins-ch026-home
```

**Operator action:** Capture observed redacted evidence; do not claim design-only gates were executed.

**Pass:** Volume exists. **Rollback:** revert lab-owned changes only.

## Exercise 03 — Launch localhost Jenkins

```bash
docker run -d --name jenkins-ch026 --restart=no -p 127.0.0.1:8104:8080 --memory 4g --cpus 2 --mount source=jenkins-ch026-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator action:** Capture observed redacted evidence; do not claim design-only gates were executed.

**Pass:** Controller started. **Rollback:** revert lab-owned changes only.

## Exercise 04 — Inspect startup logs

```bash
docker logs --tail 60 jenkins-ch026
```

**Operator action:** Capture observed redacted evidence; do not claim design-only gates were executed.

**Pass:** Healthy startup. **Rollback:** revert lab-owned changes only.

## Exercise 05 — Verify loopback port

```bash
docker port jenkins-ch026
```

**Operator action:** Capture observed redacted evidence; do not claim design-only gates were executed.

**Pass:** 127.0.0.1 only. **Rollback:** revert lab-owned changes only.

## Exercise 06 — Unlock privately

```bash
docker exec jenkins-ch026 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator action:** Unlock privately at http://127.0.0.1:8104; create named admin and do not retain the unlock password.

**Pass:** Named admin created. **Rollback:** revert lab-owned changes only.

## Exercise 07 — Set controller executors zero

```bash
docker ps --filter name=jenkins-ch026
```

**Operator action:** Manage Jenkins → Nodes → Built-In Node → executors = 0.

**Pass:** Zero built-in executors. **Rollback:** revert lab-owned changes only.

## Exercise 08 — Inspect runtime identity

```bash
docker inspect jenkins-ch026 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator action:** Capture observed redacted evidence; do not claim design-only gates were executed.

**Pass:** Runtime recorded. **Rollback:** revert lab-owned changes only.

## Exercise 09 — Inspect state volume

```bash
docker inspect jenkins-ch026 --format '{{json .Mounts}}'
```

**Operator action:** Capture observed redacted evidence; do not claim design-only gates were executed.

**Pass:** Dedicated mount. **Rollback:** revert lab-owned changes only.

## Exercise 10 — Inspect disk/inodes

```bash
docker exec jenkins-ch026 sh -c 'df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Operator action:** Capture observed redacted evidence; do not claim design-only gates were executed.

**Pass:** Capacity baseline. **Rollback:** revert lab-owned changes only.

## Exercise 11 — Create Scripted job

```bash
docker logs --tail 15 jenkins-ch026
```

**Operator action:** Create ch026-groovy-fundamentals Pipeline; add TARGET choice dev/staging and FORCE_FAIL boolean parameters; paste the parent Jenkinsfile.

**Pass:** Job saved. **Rollback:** revert lab-owned changes only.

## Exercise 12 — Run dev success

```bash
docker stats --no-stream jenkins-ch026
```

**Operator action:** Run TARGET=dev, FORCE_FAIL=false; verify region us-east-1 and three checks.

**Pass:** Dev region and checks. **Rollback:** revert lab-owned changes only.

## Exercise 13 — Run staging success

```bash
docker logs --tail 25 jenkins-ch026
```

**Operator action:** Run TARGET=staging, FORCE_FAIL=false; verify region us-west-2 and staging branch.

**Pass:** Staging region and checks. **Rollback:** revert lab-owned changes only.

## Exercise 14 — Run intentional failure

```bash
docker logs --tail 25 jenkins-ch026
```

**Operator action:** Run FORCE_FAIL=true and capture FAILURE plus audit output.

**Pass:** FAILURE and audit. **Rollback:** revert lab-owned changes only.

## Exercise 15 — Validate collection behavior

```bash
docker inspect jenkins-ch026 --format '{{.State.Status}}'
```

**Operator action:** Verify the syntax/security/quality collection iteration count.

**Pass:** Three checks. **Rollback:** revert lab-owned changes only.

## Exercise 16 — Review regex/null safety

```bash
docker logs --tail 20 jenkins-ch026
```

**Operator action:** Review parent regex/null-safety examples; do not run arbitrary Groovy approvals.

**Pass:** Negative cases explained. **Rollback:** revert lab-owned changes only.

## Exercise 17 — Review CPS restrictions

```bash
docker stats --no-stream jenkins-ch026
```

**Operator action:** Explain nonserializable objects across CPS suspension and when @NonCPS is safe.

**Pass:** Durable-state design. **Rollback:** revert lab-owned changes only.

## Exercise 18 — Review sandbox and secrets

```bash
docker inspect jenkins-ch026 --format '{{.Config.Image}}'
```

**Operator action:** Review protected SCM, Script Approval and credential interpolation policy.

**Pass:** No unsafe approvals. **Rollback:** revert lab-owned changes only.

## Exercise 19 — Incident tabletop

```bash
docker logs --tail 40 jenkins-ch026
```

**Operator action:** Tabletop: sandbox rejection, NotSerializableException and Groovy truth mistake.

**Pass:** Three diagnoses. **Rollback:** revert lab-owned changes only.

## Exercise 20 — Cleanup and score

```bash
docker stop jenkins-ch026
docker rm jenkins-ch026
```

**Operator action:** Remove dedicated volume only after confirming exclusive ownership.

**Pass:** Lab removed. **Rollback:** revert lab-owned changes only.

## Runnable Scripted Pipeline

Paste the complete controller-only `ch026-groovy-fundamentals` Jenkinsfile from the parent chapter. It contains validated target selection, map/list access, a bounded `each` closure, conditional and `switch` branches, explicit error propagation and `finally` audit.

## Expected results

| Test | Parameters | Expected |
|---|---|---|
| A | dev, FORCE_FAIL=false | SUCCESS; us-east-1; three checks |
| B | staging, FORCE_FAIL=false | SUCCESS; us-west-2; three checks |
| C | dev, FORCE_FAIL=true | FAILURE; audit result FAILURE |
| D | invalid target (design-only negative test) | Reject before any side effect |
| E | nonserializable object (tabletop) | CPS review, no unsafe execution |

## Three incident tabletops

1. **Script Approval rejection:** identify rejected signature, confirm SCM trust and refactor to approved APIs.
2. **NotSerializableException:** identify object surviving a suspension and replace with a serializable value.
3. **Groovy truth bug:** explain why `'false'` is truthy and use typed booleans.

## Acceptance and scoring

| Area | Points |
|---|---:|
| Groovy types/variables | 25 |
| Maps/lists/closures | 20 |
| Input/null/regex | 15 |
| CPS and security | 20 |
| Incident response | 10 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ and all critical security gates.

## Evidence handoff

```text
Operator/date:
Controller URL:
Built-in executors:
JENKINS_HOME volume:
Dev build/result:
Staging build/result:
Failure build/result:
Collection output:
CPS design review:
Script Approval/secret handling review:
Three incident analyses:
Cleanup proof:
Score/reviewer:
```

**Next:** Chapter 027 — Jenkins Shared Library Architecture, vars, src and resources.
