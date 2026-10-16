# Chapter 011 — Companion Hands-On Lab: Jenkins Controller Architecture and Boundaries Check

**Parent:** [Chapter 011](../011-jenkins-controller-architecture-responsibilities-operational-boundaries.md)

## Goal and safety

Validate controller responsibilities, queue/agent concepts, persistent state and least-privilege trust boundaries using a disposable localhost Docker controller. Never run real builds on the built-in node or share controller secrets with untrusted agents.

## Lab 01 — Inspect Docker host

```bash
docker version
docker ps
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Disposable Docker engine ready. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 02 — Create dedicated home volume

```bash
docker volume create jenkins-ch011-home
docker volume inspect jenkins-ch011-home
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Dedicated volume exists. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 03 — Start controller

```bash
docker run -d --name jenkins-ch011 --restart=no -p 127.0.0.1:8089:8080 --memory 4g --cpus 2 --mount source=jenkins-ch011-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Controller running. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 04 — Inspect logs

```bash
docker logs --tail 80 jenkins-ch011
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** No fatal startup errors. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 05 — Inspect listener

```bash
docker port jenkins-ch011
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Only loopback port 8089 published. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 06 — Bootstrap privately

```bash
docker exec jenkins-ch011 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Action:** Use http://127.0.0.1:8089 to complete first-run setup; do not record unlock password.

**Pass:** Named lab admin, secret not recorded. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 07 — Set built-in executors zero

```bash
docker ps --filter name=jenkins-ch011
```

**Action:** In Manage Jenkins → Nodes → Built-In Node, set executors to zero and verify.

**Pass:** Controller has zero executors. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 08 — Inspect image and runtime user

```bash
docker inspect jenkins-ch011 --format '{{.Config.Image}} {{.Config.User}}'
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Image and non-root runtime documented. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 09 — Inspect persistent volume

```bash
docker inspect jenkins-ch011 --format '{{json .Mounts}}'
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Correct home mount. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 10 — Inspect home and capacity

```bash
docker exec jenkins-ch011 sh -c 'printf "JENKINS_HOME=%s\n" "$JENKINS_HOME"; df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Home and capacity baseline. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 11 — Review queue/executor concepts

```bash
docker stats --no-stream jenkins-ch011
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Queue and executor signals mapped. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 12 — Create no-agent Pipeline

```bash
docker logs --tail 30 jenkins-ch011
```

**Action:** Create a Pipeline job with the no-agent Jenkinsfile below, run it and record result.

**Pass:** Controller-only echo Pipeline succeeds. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 13 — Review agent-backed Pipeline

```bash
docker inspect jenkins-ch011 --format '{{.State.Status}}'
```

**Action:** Read the agent-backed example in the parent chapter; explain why a missing label leaves the build queued.

**Pass:** Label behavior documented without running builds. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 14 — Review trusted/untrusted agent isolation

```bash
docker inspect jenkins-ch011 --format '{{.Config.User}}'
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Credential and runtime boundaries defined. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 15 — Review plugin/JCasC authority

```bash
docker exec jenkins-ch011 java -version
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Plugin/Java compatibility policy documented. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 16 — Restart and verify persistence

```bash
docker restart jenkins-ch011
docker logs --tail 60 jenkins-ch011
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Admin config and job persist. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 17 — Review queue starvation tabletop

```bash
docker stats --no-stream jenkins-ch011
```

**Action:** Explain label mismatch, offline agent and executor saturation; do not inject destructive failures.

**Pass:** Label mismatch and offline agent diagnosed. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 18 — Review controller incident tabletop

```bash
docker logs --tail 80 jenkins-ch011
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Startup, plugin and home mismatch diagnosed. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 19 — Document backup/monitoring

```bash
docker volume inspect jenkins-ch011-home
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** SLO, alerts, encryption keys and restore plan. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## Lab 20 — Cleanup and assessment

```bash
docker stop jenkins-ch011
docker rm jenkins-ch011
# After ownership check: docker volume rm jenkins-ch011-home
```

**Action:** Delete only lab-owned resources and check volume ownership before removal.

**Pass:** Lab removed safely and score recorded. **Rollback:** restore only lab-owned configuration or volume; never remove shared resources.

## No-agent Pipeline smoke test

```groovy
pipeline {
  agent none
  stages {
    stage('Orchestration') {
      steps { echo 'Controller coordinates Pipeline state.' }
    }
    stage('Security') {
      steps { echo 'Build steps must execute on isolated agents.' }
    }
  }
}
```

## Queue and executor tabletop

| Scenario | Expected behavior | Operational action |
|---|---|---|
| No agent with requested label | Build remains queued | Provision correctly labeled agent |
| Agent offline | Queue waits | Repair remoting/network |
| All executors busy | Queue wait rises | Capacity planning and workload isolation |
| Controller executor accidentally enabled | Risk of local build execution | Restore zero built-in executors |
| Untrusted job sees privileged credentials | Security incident | Quarantine, revoke, rotate and audit |

## Assessment (100 points)

| Domain | Points |
|---|---:|
| Controller architecture | 20 |
| Queue, nodes and executors | 20 |
| Agent trust boundaries | 20 |
| Home, plugins and config | 15 |
| Troubleshooting and monitoring | 15 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with mandatory security gates.

## Evidence template

```text
Operator/date:
Jenkins image and Java:
Controller URL and binding:
Built-in executor count:
Volume and home path:
Non-root runtime:
Pipeline job and result:
Agent label behavior:
Trusted/untrusted agent design:
Queue/executor monitoring:
Three incident diagnoses:
Backup/restore and keys:
Cleanup proof:
Score/assessor:
```

**Next:** Chapter 012 — Jenkins Agent Architecture, Launch Methods and Secure Connectivity.
