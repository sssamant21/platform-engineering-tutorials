# Chapter 007 — Companion Lab: Jenkins Docker Controller Deployment Check

**Parent:** [Chapter 007](../007-jenkins-docker-containerized-controller-deployment.md)

## Safety

Disposable local Docker engine only. Port 8085 must be free. Use a dedicated volume and no production credentials. Do not mount Docker socket into Jenkins or use privileged containers.

## Prerequisites

Docker Engine, Docker Compose plugin for optional labs, enough RAM/disk and permission to create/remove lab containers and volumes.

## Lab 01 — Inspect Docker runtime

```bash
docker version
docker info
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** Daemon ready.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 02 — Inspect existing containers and ports

```bash
docker ps
docker volume ls
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** No name or port conflict.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 03 — Create Jenkins named volume

```bash
docker volume create jenkins-ch007-home
docker volume inspect jenkins-ch007-home
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** Dedicated home volume exists.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 04 — Launch bounded controller

```bash
docker run -d --name jenkins-ch007 --restart=no -p 127.0.0.1:8085:8080 --memory 4g --cpus 2 --mount source=jenkins-ch007-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** Controller starts with resource limits.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 05 — Inspect startup logs

```bash
docker logs --tail 100 jenkins-ch007
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** No fatal startup errors.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 06 — Complete bootstrap privately

```bash
docker exec jenkins-ch007 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Additional action:** Use the local browser at http://127.0.0.1:8085 and create a named administrator; never paste unlock password into evidence.

**Pass:** Named lab administrator created; no token captured.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 07 — Set controller executors to zero

```bash
docker ps --filter name=jenkins-ch007
```

**Additional action:** Set Manage Jenkins → Nodes → Built-In Node executors to zero.

**Pass:** Built-in node reports zero executors.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 08 — Inspect image and non-root identity

```bash
docker inspect jenkins-ch007 --format '{{.Config.Image}} {{.Config.User}}'
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** Image and non-root user recorded.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 09 — Inspect persistent mount

```bash
docker inspect jenkins-ch007 --format '{{json .Mounts}}'
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** Named volume mounted to correct home.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 10 — Validate loopback-only port

```bash
docker port jenkins-ch007
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** Only 127.0.0.1:8085 published.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 11 — Measure container resources

```bash
docker stats --no-stream jenkins-ch007
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** CPU and memory baseline recorded.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 12 — Measure filesystem/inodes

```bash
docker exec jenkins-ch007 sh -c 'df -h /var/jenkins_home && df -i /var/jenkins_home'
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** Capacity baseline recorded.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 13 — Review Docker Compose design

```bash
docker compose version
```

**Additional action:** Create the Compose YAML from the chapter, run docker compose config, and do not start it while the docker run controller owns port 8085.

**Pass:** Compose config validated offline; no concurrent conflicting deployment.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 14 — Review plugin and custom image governance

```bash
docker exec jenkins-ch007 java -version
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** Approved image/plugin pinning approach documented.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 15 — Review JCasC security boundaries

```bash
docker inspect jenkins-ch007 --format '{{json .HostConfig.Binds}}'
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** No host socket or secret-bearing bind mount.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 16 — Restart and validate persistence

```bash
docker restart jenkins-ch007
docker logs --tail 80 jenkins-ch007
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** Configuration persists.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 17 — Design consistent encrypted backup

```bash
docker volume inspect jenkins-ch007-home
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** Backup/key escrow and clean-room restore documented.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 18 — Troubleshooting tabletop

```bash
docker inspect jenkins-ch007 --format '{{.State.Status}}'
```

**Additional action:** Investigate a hypothetical volume permission error, OOM kill and plugin incompatibility; document rollback.

**Pass:** Three failures diagnosed without destructive injection.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 19 — Record production readiness and score

```bash
docker ps --filter name=jenkins-ch007
```

**Additional action:** Record redacted output and explain the operational implication.

**Pass:** Security, monitoring and rollback reviewed.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Lab 20 — Cleanup lab

```bash
docker stop jenkins-ch007
docker rm jenkins-ch007
# After ownership check: docker volume rm jenkins-ch007-home
```

**Additional action:** Remove only this lab's container and volume; check for other consumers before volume deletion.

**Pass:** Lab resources removed safely.

**Rollback:** restore only the lab-owned container/volume or revert the reviewed configuration. Never delete shared Docker resources.

## Optional Pipeline smoke test

After setting controller executors to zero, create a disposable Pipeline job:

```groovy
pipeline {
  agent none
  stages {
    stage('Container architecture') {
      steps { echo 'Controller coordinates builds; agents execute tools.' }
    }
    stage('Persistence') {
      steps { echo 'JENKINS_HOME is backed by a named volume.' }
    }
  }
}
```

This Pipeline has no shell steps or workspace allocation; real builds require isolated agents.

## Troubleshooting checklist

| Failure | Evidence | Recovery |
|---|---|---|
| Container exits | docker logs and inspect | Correct image/runtime |
| Port conflict | docker ps and port | Select approved local port |
| Home unwritable | mount and UID inspection | Repair ownership/policy |
| Config lost | volume inspect and restart | Reattach correct volume |
| OOMKilled | docker stats and inspect | Profile and adjust memory |
| Plugin load error | logs and plugin inventory | Restore tested versions |
| Security exposure | inspect mounts and ports | Remove socket/public port |
| Restore failure | backup and key inventory | Restore full compatible set |

## Assessment (100 points)

| Competency | Points |
|---|---:|
| Docker installation and image inspection | 20 |
| Volume and restart persistence | 20 |
| Network, non-root and secret security | 20 |
| Compose/JCasC/plugin governance | 15 |
| Troubleshooting and monitoring | 15 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with all mandatory gates.

## Evidence template

```text
Operator/date:
Docker version:
Image reference and immutable digest:
Runtime user:
Published port:
Container limits:
Volume name and mount:
Jenkins/Java version:
Controller executor count:
Restart validation:
Compose validation:
JCasC/plugin review:
Backup and restore plan:
Three failure diagnoses:
Cleanup proof:
Score/assessor:
```

**Next:** Chapter 008 — Jenkins Configuration Files, Environment Variables and JENKINS_HOME Management.
