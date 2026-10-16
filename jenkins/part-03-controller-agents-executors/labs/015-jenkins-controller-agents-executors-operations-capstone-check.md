# Chapter 015 — Companion Lab: Jenkins Controller, Agents and Executors Production Operations Capstone

**Parent:** [Chapter 015](../015-jenkins-controller-agents-executors-production-operations-capstone.md)

## Goal and safety

Produce a practical operational-readiness dossier from a disposable localhost Jenkins controller, with queue and orchestration demonstrations plus agent/cloud/DR design checks. Never claim live agent connectivity, production TLS, or disaster recovery was tested unless independently verified.

## Lab 01 — Verify Docker host

```bash
docker version
docker ps
```

**Operator task:** Record redacted evidence and distinguish actual observations from architecture-only review.

**Pass:** Disposable Docker host available. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 02 — Create persistent volume

```bash
docker volume create jenkins-ch015-home
```

**Operator task:** Record redacted evidence and distinguish actual observations from architecture-only review.

**Pass:** Dedicated lab volume exists. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 03 — Start private controller

```bash
docker run -d --name jenkins-ch015 --restart=no -p 127.0.0.1:8093:8080 --memory 4g --cpus 2 --mount source=jenkins-ch015-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Operator task:** Record redacted evidence and distinguish actual observations from architecture-only review.

**Pass:** Controller starts on loopback. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 04 — Review startup

```bash
docker logs --tail 80 jenkins-ch015
```

**Operator task:** Record redacted evidence and distinguish actual observations from architecture-only review.

**Pass:** No fatal startup errors. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 05 — Verify private listener

```bash
docker port jenkins-ch015
```

**Operator task:** Record redacted evidence and distinguish actual observations from architecture-only review.

**Pass:** Only 127.0.0.1:8093 exposed. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 06 — Complete bootstrap

```bash
docker exec jenkins-ch015 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Operator task:** Unlock privately at http://127.0.0.1:8093, create a named admin and do not capture the unlock secret.

**Pass:** Named admin created privately. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 07 — Disable built-in executors

```bash
docker ps --filter name=jenkins-ch015
```

**Operator task:** Set Manage Jenkins → Nodes → Built-In Node → executors = 0; capture the setting.

**Pass:** Controller executors zero. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 08 — Inspect runtime identity

```bash
docker inspect jenkins-ch015 --format '{{.Config.Image}} {{.Config.User}}'
```

**Operator task:** Record redacted evidence and distinguish actual observations from architecture-only review.

**Pass:** Image and user recorded. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 09 — Inspect home mount

```bash
docker inspect jenkins-ch015 --format '{{json .Mounts}}'
```

**Operator task:** Record redacted evidence and distinguish actual observations from architecture-only review.

**Pass:** Correct durable volume. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 10 — Inspect home capacity

```bash
docker exec jenkins-ch015 sh -c 'df -h /var/jenkins_home; df -i /var/jenkins_home'
```

**Operator task:** Record redacted evidence and distinguish actual observations from architecture-only review.

**Pass:** Storage baseline recorded. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 11 — Review controller monitoring

```bash
docker stats --no-stream jenkins-ch015
```

**Operator task:** Record redacted evidence and distinguish actual observations from architecture-only review.

**Pass:** CPU/memory and SLO plan. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 12 — Create no-agent Pipeline

```bash
docker logs --tail 25 jenkins-ch015
```

**Operator task:** Create and run the no-agent Pipeline from the parent chapter; record the build result.

**Pass:** Orchestration smoke job succeeds. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 13 — Create label-bound Pipeline

```bash
docker ps --filter name=jenkins-ch015
```

**Operator task:** Create the label-bound Pipeline from the parent chapter; no matching agent should exist.

**Pass:** Queue demonstration job created. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 14 — Observe and cancel queued job

```bash
docker logs --tail 25 jenkins-ch015
```

**Operator task:** Record the queue reason and cancel the build before timeout.

**Pass:** Missing-label queue reason recorded and cleared. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 15 — Plan SSH agent trust

```bash
docker inspect jenkins-ch015 --format '{{.State.Status}}'
```

**Operator task:** Record redacted evidence and distinguish actual observations from architecture-only review.

**Pass:** Dedicated identity and host-key policy. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 16 — Plan WebSocket and Kubernetes agents

```bash
docker inspect jenkins-ch015 --format '{{.Config.Image}}'
```

**Operator task:** Record redacted evidence and distinguish actual observations from architecture-only review.

**Pass:** TLS, RBAC, resource and identity controls. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 17 — Calculate capacity

```bash
docker stats --no-stream jenkins-ch015
```

**Operator task:** Calculate ceil(6 × 4 / 0.70) = 35 executor slots; explain burst and resource limitations.

**Pass:** Executor sizing assumptions recorded. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 18 — Restart and verify persistence

```bash
docker restart jenkins-ch015
docker logs --tail 60 jenkins-ch015
```

**Operator task:** After restart, verify login, job definitions and home state persist.

**Pass:** Jobs/admin survive restart. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 19 — Incident and DR tabletop

```bash
docker volume inspect jenkins-ch015-home
```

**Operator task:** Tabletop: controller disk full, WebSocket agent 502, Kubernetes Pending; document clean-room restore evidence requirements.

**Pass:** Three incidents, encrypted backup/restore plan. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Lab 20 — Cleanup and acceptance

```bash
docker stop jenkins-ch015
docker rm jenkins-ch015
# Verify exclusive ownership before optional: docker volume rm jenkins-ch015-home
```

**Operator task:** Remove only lab-owned resources and verify volume ownership before optional deletion.

**Pass:** Cleanup and scoring recorded. **Rollback:** revert only disposable lab settings; do not delete shared volumes or cloud resources.

## Pipeline A — Controller orchestration smoke

```groovy
pipeline {
  agent none
  stages {
    stage('Orchestration') {
      steps { echo 'Controller coordinates Pipeline state.' }
    }
    stage('Security') {
      steps { echo 'Build steps require isolated agents.' }
    }
  }
}
```

## Pipeline B — Queue and label routing

```groovy
pipeline {
  agent none
  options { timeout(time: 5, unit: 'MINUTES') }
  stages {
    stage('Queue demonstration') {
      agent { label 'pool-trusted && os-linux' }
      steps { sh 'id && hostname' }
    }
  }
}
```

Expected behavior: without a matching agent, Pipeline B queues. Record the reason, cancel the build and confirm no job executed on the controller.

## Incident tabletop matrix

| Scenario | Evidence | Recovery |
|---|---|---|
| Controller disk/inode full | df -h/df -i, retention | Approved cleanup or expansion |
| Agent WebSocket 502 | TLS/proxy upgrade and remoting | Repair trusted proxy |
| Kubernetes pod Pending | Events, requests, quota, taints | Fix scheduling/capacity |
| Queue starvation | Labels, node availability, executors | Restore eligible capacity |
| Secret exposure | Credentials scope, agent identity | Quarantine and rotate |
| Backup/key mismatch | Snapshot manifest and key inventory | Compatible clean-room restore |

## Ten gates

| Gate | Status (Pass/Fail/Design only) | Evidence |
|---|---|---|
| G1 Private controller and named admin | | |
| G2 Zero built-in executors | | |
| G3 Persistent home/restart | | |
| G4 No-agent Pipeline smoke | | |
| G5 Queue demo and cancellation | | |
| G6 Secure SSH/WebSocket design | | |
| G7 Kubernetes/cloud provisioning plan | | |
| G8 Capacity and lifecycle | | |
| G9 Incident and DR tabletop | | |
| G10 Evidence and cleanup | | |

## Acceptance score — 100 points

| Area | Points |
|---|---:|
| Controller architecture/isolation | 20 |
| Agent security and transport | 20 |
| Nodes, labels, executors | 20 |
| Provisioning and capacity | 15 |
| Observability and recovery | 15 |
| Evidence and cleanup | 10 |
| **Total** | **100** |

**Pass:** 90+ and no security-critical failure. Live production gates remain separate.

## Evidence and handoff template

```text
Operator/date:
Jenkins/Java/image versions:
Controller URL and port binding:
Built-in executor count:
JENKINS_HOME and volume:
Restart persistence proof:
No-agent Pipeline result:
Label-bound queue reason and cancellation:
SSH and WebSocket security design:
Kubernetes/cloud IAM and lifecycle design:
Executor sizing assumptions:
Queue/provisioning SLO and alert owners:
Three incident diagnoses:
Backup, keys and clean-room restore status:
Cleanup proof:
Score and reviewer:
Production controls independently verified:
Approval / residual risk:
```

**Part 03 complete. Next:** Chapter 016 — Jenkins Jobs, Freestyle Projects and Pipeline Job Fundamentals.
