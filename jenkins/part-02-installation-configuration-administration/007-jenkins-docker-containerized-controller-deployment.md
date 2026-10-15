# Chapter 007 — Jenkins Docker and Containerized Controller Deployment

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 02:** Installation, Configuration and Administration  
**Chapter:** 007 / 100  
**Companion lab:** [007 — Jenkins Docker Controller Deployment Check](labs/007-jenkins-docker-controller-deployment-check.md)

> **Safety:** All executable examples use a disposable local Docker engine and a dedicated lab volume. The published `jenkins/jenkins:lts-jdk21` tag is mutable; pin an approved image digest for production. Do not mount the host Docker socket into the controller or expose port 8080 publicly.

## 1. Objectives

Build a persistent containerized Jenkins controller, understand images, layers, mounts, user IDs, networking, health checks and resource limits, compare `docker run` and Compose, plan image/plugin/JCasC governance, diagnose container incidents, and rehearse safe upgrades and restores.

## 2. Architecture and trust boundaries

```text
SCM webhooks / admin users
          |
   TLS reverse proxy
          |
 localhost:8085 -> container:8080
          |
   Jenkins LTS container (non-root)
          |           |
     plugins/JCasC   controller logs
          |
   /var/jenkins_home (named volume)
          |
   encrypted consistent backup + keys
          |
    agent provisioning
     /             \
isolated VM       K8s pod
     \             /
      build/test/scan
          |
      OCI registry -> GitOps PR
```

The controller coordinates builds; it should have **zero executors**. Containers do not make Jenkins stateless. Do not attach the same writable JENKINS_HOME to two active controllers.

## 3. Docker image and lifecycle concepts

| Concept | SRE consequence |
|---|---|
| Image tag | Mutable pointer; record immutable digest |
| Container filesystem | Ephemeral; never rely on it for Jenkins state |
| Named volume | Persists JENKINS_HOME across container replacement |
| Bind mount | Explicit host permissions, SELinux and backup ownership |
| Container UID | Match non-root image user to volume access |
| Published port | Bind to localhost for labs; use trusted TLS proxy in production |
| Resource limits | Bound memory/CPU and monitor OOM/GC |
| Restart policy | Supervision only; cannot repair corrupt state |
| Health check | Validate HTTP readiness without leaking credentials |
| Compose | Declarative single-host runtime, not HA orchestration |
| Plugin catalog | Must match Jenkins core/Java and JCasC schema |
| Backup | Consistent home + encryption keys + tested clean-room restore |

## 4. Disposable Docker installation

```bash
docker version
docker volume create jenkins-ch007-home
docker run -d --name jenkins-ch007 --restart=no \
  -p 127.0.0.1:8085:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch007-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch007
docker logs --tail 100 jenkins-ch007
```

**Prerequisites:** the Docker host must have enough memory for the container and its own processes; 4 GiB and 2 CPUs are illustrative lab allocations, not universal production requirements.

Read the bootstrap password privately:

```bash
docker exec jenkins-ch007 cat /var/jenkins_home/secrets/initialAdminPassword
```

Open `http://127.0.0.1:8085`, create a disposable named administrator, and set **Manage Jenkins → Nodes → Built-In Node → Number of executors = 0**.

## 5. Container and volume inspection

```bash
docker inspect jenkins-ch007 --format '{{.Config.Image}}'
docker inspect jenkins-ch007 --format '{{.Image}}'
docker inspect jenkins-ch007 --format '{{.Config.User}}'
docker inspect jenkins-ch007 --format '{{json .Mounts}}'
docker port jenkins-ch007
docker stats --no-stream jenkins-ch007
docker exec jenkins-ch007 sh -c 'df -h /var/jenkins_home && df -i /var/jenkins_home'
```

The image ID and registry digest are not always the same; capture the approved registry digest when pulling and record the exact runtime image ID after deployment.

## 6. Docker Compose deployment

Use this example **instead of** the `docker run` container, not concurrently on port 8085. The file is a disposable local template.

```yaml
services:
  jenkins:
    image: jenkins/jenkins:lts-jdk21
    container_name: jenkins-ch007-compose
    restart: "no"
    ports:
      - "127.0.0.1:8085:8080"
    volumes:
      - jenkins-home:/var/jenkins_home
    mem_limit: 4g
    cpus: 2.0
    security_opt:
      - no-new-privileges:true
volumes:
  jenkins-home:
```

```bash
docker compose config
docker compose up -d
docker compose ps
docker compose logs --tail 80 jenkins
```

**Important:** Compose's project-scoped volume may differ from `jenkins-ch007-home`. Verify the actual volume name before backing up, restoring or cleaning up. For production, pin an image digest and review the Compose/runtime compatibility of resource fields.

## 7. Controller security hardening

- Keep authentication and CSRF protection enabled, with named admin and SSO/RBAC in production.
- Set controller executors to zero.
- Use a non-root controller and restrict volume ownership.
- Do not mount `/var/run/docker.sock` or privileged host paths.
- Use trusted TLS reverse proxy and restricted backend listener.
- Use short-lived workload credentials; never commit secrets to Dockerfile, Compose or JCasC.
- Pin Jenkins, Java, plugins and container image digests.
- Use isolated agents for untrusted jobs and image builds.
- Scan images, record provenance and review advisories.
- Configure logging, retention and backup encryption.

## 8. Building a controlled custom image

The following is **illustrative**; pin a digest and tested plugin versions before production:

```dockerfile
FROM jenkins/jenkins:lts-jdk21
USER jenkins
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
```

Use a compatible plugin catalog with exact approved versions and test it against the chosen Jenkins LTS. Never bake credentials or private keys into the image. A custom image is not a replacement for persistent JENKINS_HOME backup.

## 9. JCasC and runtime configuration

```yaml
jenkins:
  numExecutors: 0
  systemMessage: "Managed Jenkins controller — containerized"
```

Mount reviewed configuration read-only and use approved secret references. JCasC requires the appropriate plugin and version-compatible schema. Validate on a disposable controller before rollout.

## 10. Controlled restart and upgrade strategy

```bash
docker restart jenkins-ch007
docker logs --tail 80 jenkins-ch007
docker inspect jenkins-ch007 --format '{{.State.Status}}'
```

A restart validates persistence but **does not** validate disaster recovery. For an upgrade: freeze changes, confirm backups, test Jenkins/Java/plugin/JCasC compatibility, pin a new image digest, deploy in staging, run Pipeline/agent smoke tests and prepare rollback using a full compatible pre-upgrade snapshot. Do not blindly downgrade an upgraded JENKINS_HOME.

## 11. Backup and restore architecture

Consistent backup requires controller state, encryption keys, plugin inventory and configuration. For a cold backup in a lab, stop the controller before copying the volume to encrypted storage. A tarball alone is not a production backup strategy until encryption, integrity, retention and restore have been tested.

```bash
docker stop jenkins-ch007
docker volume inspect jenkins-ch007-home
# Create a backup only through an approved encrypted destination/workflow.
docker start jenkins-ch007
```

Test restore on a separate controller with matching Jenkins and plugin versions; verify login, credentials decryption and representative jobs.

## 12. Observability and SLO baseline

Track container restarts, OOM kills, CPU/memory, JVM heap/GC, disk/inodes, controller HTTP readiness, queue wait, agent availability, plugin errors and backup age. Establish workload-specific thresholds and on-call ownership.

## 13. Twenty Docker deployment troubleshooting scenarios

| # | Symptom | Diagnosis | Safe response |
|---|---|---|---|
| 1 | Container exits immediately | docker logs, image architecture, Java runtime | Use supported pinned image |
| 2 | Port 8085 occupied | docker ps, ss/netstat | Choose approved localhost port |
| 3 | Cannot write JENKINS_HOME | docker inspect mounts, UID/GID, SELinux labels | Correct volume ownership and policy |
| 4 | Controller starts with empty jobs | Inspect named volume identity and mount | Reattach correct volume; avoid overwrite |
| 5 | Container OOMKilled | docker inspect state, docker stats, heap settings | Profile and right-size memory |
| 6 | Disk or inodes exhausted | docker system df, df -h, df -i | Expand storage or approved cleanup |
| 7 | Unhealthy restart loop | Inspect logs, restart policy and probes | Fix cause before auto-restart |
| 8 | Wrong Java version | docker exec java -version, Jenkins requirements | Use compatible image |
| 9 | Plugin dependencies fail | Review logs and plugin catalog | Restore tested plugin set |
| 10 | JCasC invalid | Check config path and schema/plugin compatibility | Rollback reviewed YAML |
| 11 | Secret printed in logs | Inspect build logs, env and Docker inspect | Revoke and rotate, remove unsafe logging |
| 12 | Image tag unexpectedly changed | Compare digest and release notes | Pin digest and stage upgrades |
| 13 | Proxy 502 | Inspect container listener and proxy upstream | Restore routing/TLS |
| 14 | Webhook cannot reach Jenkins | Check external URL and authenticated endpoint | Fix reverse proxy and webhook trust |
| 15 | Agent cannot connect | Check network, remoting and identity | Repair isolated agent path |
| 16 | Docker socket exposure | Inspect mounts and group access | Remove host socket and use isolated builders |
| 17 | Root container execution | docker inspect User and file ownership | Use non-root image/runtime |
| 18 | Backup missing encryption keys | Review snapshot manifest and restore | Restore complete protected key material |
| 19 | Restore fails after upgrade | Compare core/plugins/data migrations | Restore compatible pre-upgrade snapshot |
| 20 | Container removed deletes state | Inspect bind/volume strategy | Use named volume and verified backups |

## 14. Eight SRE runbooks

### RB-01 Container startup failure

**Procedure:** Inspect image digest, logs, Java, port, volume and UID; restore tested runtime.

**Exit criteria:** authenticated controller UI, zero controller executors, persistent state verified, healthy plugins and agents, incident/change evidence recorded.

### RB-02 Persistent volume recovery

**Procedure:** Stop writes, verify volume identity, ownership and backups, reattach correct home.

**Exit criteria:** authenticated controller UI, zero controller executors, persistent state verified, healthy plugins and agents, incident/change evidence recorded.

### RB-03 Image upgrade and rollback

**Procedure:** Pin image digest, stage plugin/JCasC tests, backup, perform controlled rollout and rollback via full compatible snapshot.

**Exit criteria:** authenticated controller UI, zero controller executors, persistent state verified, healthy plugins and agents, incident/change evidence recorded.

### RB-04 Memory and disk incident

**Procedure:** Inspect docker stats, OOM state, heap/GC, disk/inodes and build retention; right-size after evidence.

**Exit criteria:** authenticated controller UI, zero controller executors, persistent state verified, healthy plugins and agents, incident/change evidence recorded.

### RB-05 Network/TLS outage

**Procedure:** Validate loopback backend, reverse proxy, certificates, Jenkins URL and webhook delivery.

**Exit criteria:** authenticated controller UI, zero controller executors, persistent state verified, healthy plugins and agents, incident/change evidence recorded.

### RB-06 Credential exposure

**Procedure:** Stop affected build, revoke/rotate, inspect Docker environment, logs and mount permissions.

**Exit criteria:** authenticated controller UI, zero controller executors, persistent state verified, healthy plugins and agents, incident/change evidence recorded.

### RB-07 Backup and clean-room restore

**Procedure:** Create consistent encrypted home backup including keys, restore to separate disposable controller, verify login and jobs.

**Exit criteria:** authenticated controller UI, zero controller executors, persistent state verified, healthy plugins and agents, incident/change evidence recorded.

### RB-08 SRE deployment handoff

**Procedure:** Record image digest, SBOM, resource limits, network, secrets, alerts, change owner and RPO/RTO.

**Exit criteria:** authenticated controller UI, zero controller executors, persistent state verified, healthy plugins and agents, incident/change evidence recorded.

## 15. Acceptance assessment — 100 points

| Domain | Points |
|---|---:|
| Image, runtime and container architecture | 15 |
| Persistent volume and restart validation | 20 |
| Network and security hardening | 20 |
| Compose/custom image/JCasC design | 15 |
| Troubleshooting and monitoring | 15 |
| Backup, rollback and evidence | 15 |
| **Total** | **100** |

**Pass:** 90+ and mandatory gates: localhost-only binding, zero controller executors, non-root runtime, no Docker socket, persistent home, no secrets in evidence, documented restore.

## 16. Cleanup

```bash
docker stop jenkins-ch007
docker rm jenkins-ch007
# Destructive: only if this volume is exclusively owned by the lab:
docker volume rm jenkins-ch007-home
```

If Compose was used, run `docker compose down` first and remove project volumes only after verifying ownership; **do not** use `docker compose down -v` against a shared or needed volume.

**Next:** Chapter 008 — Jenkins Configuration Files, Environment Variables and JENKINS_HOME Management.
