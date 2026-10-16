# Chapter 016 — Hands-On Lab: Jenkins Jobs, Freestyle and Pipeline Fundamentals

**Parent:** [Chapter 016](../016-jenkins-jobs-freestyle-projects-pipeline-job-fundamentals.md)

## Safety and prerequisites

Run a disposable Jenkins controller bound to localhost. No controller build executors. Freestyle shell execution and artifact creation are **staging-agent only**; the no-agent Pipeline runs on the disposable controller without executing shell commands.

## Lab instructions

### Exercise 01 — Check Docker prerequisites

```bash
docker version
docker ps
```

**Operator action:** Record observed evidence or mark design-only; do not claim tests you did not execute.

**Pass:** Engine ready. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 02 — Create isolated home

```bash
docker volume create jenkins-ch016-home
```

**Operator action:** Record observed evidence or mark design-only; do not claim tests you did not execute.

**Pass:** Dedicated volume exists. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 03 — Start controller

```bash
docker run -d --name jenkins-ch016 --restart=no -p 127.0.0.1:8094:8080 --memory 4g --cpus 2 --mount source=jenkins-ch016-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator action:** Record observed evidence or mark design-only; do not claim tests you did not execute.

**Pass:** Controller starts. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 04 — Inspect startup logs

```bash
docker logs --tail 60 jenkins-ch016
```

**Operator action:** Record observed evidence or mark design-only; do not claim tests you did not execute.

**Pass:** No fatal startup errors. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 05 — Check listener isolation

```bash
docker port jenkins-ch016
```

**Operator action:** Record observed evidence or mark design-only; do not claim tests you did not execute.

**Pass:** Loopback-only port. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 06 — Bootstrap named admin

```bash
docker exec jenkins-ch016 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator action:** Open http://127.0.0.1:8094 and complete setup without recording the unlock password.

**Pass:** Unlock privately; do not save secret. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 07 — Disable controller executors

```bash
docker ps --filter name=jenkins-ch016
```

**Operator action:** Manage Jenkins → Nodes → Built-In Node → configure executors = 0.

**Pass:** Built-in node executors zero. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 08 — Inspect runtime image

```bash
docker inspect jenkins-ch016 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator action:** Record observed evidence or mark design-only; do not claim tests you did not execute.

**Pass:** Runtime recorded. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 09 — Inspect home persistence

```bash
docker inspect jenkins-ch016 --format '{{json .Mounts}}'
```

**Operator action:** Record observed evidence or mark design-only; do not claim tests you did not execute.

**Pass:** Dedicated home attached. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 10 — Create Freestyle job

```bash
docker logs --tail 15 jenkins-ch016
```

**Operator action:** New Item → Freestyle project → ch016-freestyle-demo; add description, owner and retention.

**Pass:** Freestyle definition saved. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 11 — Set Freestyle agent restriction

```bash
docker ps --filter name=jenkins-ch016
```

**Operator action:** Enable Restrict where this project can be run with label lab-linux; do not create an unsafe controller agent.

**Pass:** No controller execution. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 12 — Create no-agent Pipeline

```bash
docker logs --tail 15 jenkins-ch016
```

**Operator action:** New Item → Pipeline → ch016-pipeline-smoke; paste the no-agent Jenkinsfile below.

**Pass:** Pipeline definition saved. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 13 — Run Pipeline smoke

```bash
docker logs --tail 25 jenkins-ch016
```

**Operator action:** Build with Parameters and record build number, result and redacted console output.

**Pass:** SUCCESS and console evidence. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 14 — Test choice parameter

```bash
docker ps --filter name=jenkins-ch016
```

**Operator action:** Run once with dev and once with staging; verify each displayed parameter.

**Pass:** dev/staging parameter output verified. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 15 — Review build history and retention

```bash
docker inspect jenkins-ch016 --format '{{.State.Status}}'
```

**Operator action:** Record observed evidence or mark design-only; do not claim tests you did not execute.

**Pass:** Build history and discard policy reviewed. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 16 — Review agent-backed Pipeline

```bash
docker stats --no-stream jenkins-ch016
```

**Operator action:** Review the agent-backed Pipeline in the chapter; without a matching agent, record expected queue behavior rather than running shell locally.

**Pass:** Missing-agent queue understood. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 17 — Review SCM and webhook trust

```bash
docker logs --tail 20 jenkins-ch016
```

**Operator action:** Record observed evidence or mark design-only; do not claim tests you did not execute.

**Pass:** Signed webhook and Git controls documented. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 18 — Review artifact and JUnit policy

```bash
docker inspect jenkins-ch016 --format '{{.Config.Image}}'
```

**Operator action:** Record observed evidence or mark design-only; do not claim tests you did not execute.

**Pass:** Workspace/report requirements documented. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 19 — Rehearse incidents and rollback

```bash
docker logs --tail 40 jenkins-ch016
```

**Operator action:** Tabletop: queued job, SCM authentication failure and exposed secret; document safe rollback.

**Pass:** Three failures diagnosed. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

### Exercise 20 — Cleanup and score

```bash
docker stop jenkins-ch016
docker rm jenkins-ch016
```

**Operator action:** Optionally remove the dedicated volume only after verifying it belongs exclusively to this lab.

**Pass:** Lab controller removed. **Rollback:** revert only lab-owned job settings or stop/remove disposable resources.

## No-agent Pipeline (run this)

```groovy
pipeline {
  agent none
  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '10'))
  }
  parameters {
    choice(name: 'ENVIRONMENT', choices: ['dev', 'staging'])
  }
  stages {
    stage('Validate') {
      steps { echo "Environment=${params.ENVIRONMENT}" }
    }
    stage('Report') {
      steps { echo 'Pipeline completed without a build agent.' }
    }
  }
}
```

Expected: SUCCESS, parameter value visible, controller executors remain zero.

## Freestyle agent-only example

On an approved Linux agent labeled `lab-linux`, configure an Execute shell step:

```bash
set -eu
mkdir -p output
printf 'hello from Freestyle\n' > output/result.txt
```

Add archive pattern `output/result.txt`. Without an approved agent, **do not run this step**; record the configuration as design-only.

## Failure drills

| Scenario | Evidence | Recovery |
|---|---|---|
| Freestyle queued | Label and node status | Provision authorized agent |
| Pipeline syntax failure | Jenkinsfile validation | Revert reviewed change |
| SCM 401 | Credential ID and scope | Repair scoped identity |
| Artifact missing | Workspace path and archive pattern | Correct archive configuration |
| Secret in log | Redacted console and credential audit | Revoke/rotate and contain |
| Unexpected concurrency | Build overlap and job settings | Disable concurrency |

## Acceptance (100 points)

| Domain | Points |
|---|---:|
| Job types and architecture | 20 |
| Freestyle configuration | 15 |
| Pipeline and parameters | 25 |
| SCM/security/agents | 15 |
| Operations and troubleshooting | 15 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with no critical security failure.

## Evidence checklist

- [ ] Controller localhost binding and named administrator
- [ ] Built-in executors zero
- [ ] Freestyle job configuration (no controller shell execution)
- [ ] Pipeline success with dev and staging parameters
- [ ] Build retention and history
- [ ] Agent-backed job routing documented
- [ ] SCM credentials and signed webhook policy
- [ ] Artifacts and reports policy
- [ ] Three incident analyses
- [ ] Lab cleanup and reviewer score

**Next:** Chapter 017 — Jenkins Build Triggers, Parameters and Scheduling.
