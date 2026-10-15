# Chapter 008 — Companion Lab: Jenkins Configuration and JENKINS_HOME Check

**Parent:** [Chapter 008](../008-jenkins-configuration-files-environment-variables-jenkins-home-management.md)

## Safety and prerequisites

Disposable Docker Linux container host, free localhost port 8086, no production credentials and a dedicated named volume. Do not print raw secret files or expose sensitive config.xml/credentials.xml in evidence.

## Lab 01 — Inspect Docker and host

```bash
docker version
docker ps
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Docker engine available. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 02 — Create dedicated Jenkins volume

```bash
docker volume create jenkins-ch008-home
docker volume inspect jenkins-ch008-home
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Dedicated persistent home. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 03 — Start localhost controller

```bash
docker run -d --name jenkins-ch008 --restart=no -p 127.0.0.1:8086:8080 --mount source=jenkins-ch008-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Controller running. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 04 — Check startup logs

```bash
docker logs --tail 80 jenkins-ch008
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** No fatal startup error. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 05 — Complete bootstrap privately

```bash
docker exec jenkins-ch008 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Follow-up:** Use http://127.0.0.1:8086 to create a disposable named administrator; keep the unlock password private.

**Pass:** Named lab administrator created; no token in evidence. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 06 — Set zero built-in executors

```bash
docker ps --filter name=jenkins-ch008
```

**Follow-up:** Manage Jenkins → Nodes → Built-In Node → Configure → Number of executors = 0.

**Pass:** Controller executor count zero. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 07 — Inspect effective home path

```bash
docker exec jenkins-ch008 sh -c 'printf "JENKINS_HOME=%s\n" "$JENKINS_HOME"'
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Correct home path. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 08 — Inspect mount identity

```bash
docker inspect jenkins-ch008 --format '{{json .Mounts}}'
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Volume maps to home. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 09 — Inspect non-sensitive directory names

```bash
docker exec jenkins-ch008 sh -c 'find /var/jenkins_home -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort'
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Directory inventory without secrets. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 10 — Inspect ownership and mode

```bash
docker exec jenkins-ch008 sh -c 'stat -c "%U:%G %a %n" /var/jenkins_home'
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Least-privilege owner understood. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 11 — Inspect disk and inodes

```bash
docker exec jenkins-ch008 sh -c 'df -h /var/jenkins_home && df -i /var/jenkins_home'
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Capacity baseline recorded. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 12 — Inspect Java and runtime image

```bash
docker exec jenkins-ch008 java -version
docker inspect jenkins-ch008 --format '{{.Config.Image}}'
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Versions recorded. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 13 — Review systemd configuration model

```bash
docker exec jenkins-ch008 sh -c 'echo "Docker controller: systemd inspection belongs on separate Linux VM"'
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Runtime boundary understood. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 14 — Review JCasC YAML and source of truth

```bash
docker exec jenkins-ch008 sh -c 'test -d /var/jenkins_home && echo ready'
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Validated conceptual JCasC policy. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 15 — Run no-agent Pipeline

```bash
docker logs --tail 30 jenkins-ch008
```

**Follow-up:** Create a Pipeline job with the Jenkinsfile below and record the result.

**Pass:** Environment-only Jenkinsfile below succeeds. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 16 — Review secret exposure prevention

```bash
docker inspect jenkins-ch008 --format '{{.Config.User}}'
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** No secrets committed or logged. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 17 — Restart and verify persistence

```bash
docker restart jenkins-ch008
docker logs --tail 70 jenkins-ch008
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Admin config and jobs persist. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 18 — Investigate three config failures

```bash
docker volume inspect jenkins-ch008-home
```

**Follow-up:** Document diagnostic evidence and rollback for three scenarios; do not delete keys or corrupt live state.

**Pass:** Home mismatch, JCasC schema and key loss diagnosed as tabletop. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 19 — Write backup and clean-room restore plan

```bash
docker inspect jenkins-ch008 --format '{{.State.Status}}'
```

**Follow-up:** Document the actual observed result and the security/operational implication.

**Pass:** Complete encrypted backup and key handling documented. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 20 — Cleanup and score

```bash
docker stop jenkins-ch008
docker rm jenkins-ch008
# After verifying exclusive ownership: docker volume rm jenkins-ch008-home
```

**Follow-up:** Delete the volume only if no other workload or restore drill needs it.

**Pass:** Lab resources safely removed. **Rollback:** revert only lab-owned configuration or restore a verified dedicated volume.

## Lab 15 — Jenkinsfile

```groovy
pipeline {
  agent none
  environment {
    APP_ENV = 'lab'
  }
  stages {
    stage('Configuration') {
      steps {
        echo "Environment: ${env.APP_ENV}"
        echo 'JENKINS_HOME must be persistent and protected.'
      }
    }
  }
}
```

No shell or workspace-consuming steps are used.

## Configuration failure triage

| Symptom | Verify | Safe remediation |
|---|---|---|
| Lost settings | Effective home and mount | Reattach correct volume |
| Permission denied | UID, ownership, SELinux | Repair least privilege |
| JCasC parse error | YAML and plugin schema | Revert approved bundle |
| Secret cannot decrypt | Key material and backup pairing | Restore complete backup |
| Disk full | df -h / df -i | Expand or approved retention |
| Startup config drift | JCasC, UI and init scripts | Reconcile Git source of truth |
| Java option ignored | systemd unit / container startup | Correct approved runtime setting |
| Config overwritten | UI/API writes and restart | Restore reviewed state |

## Final assessment

| Area | Points |
|---|---:|
| JENKINS_HOME mapping and structure | 20 |
| Runtime config and permissions | 20 |
| JCasC and drift management | 20 |
| Pipeline environment and secrets | 15 |
| Troubleshooting and recovery | 15 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with all mandatory safety gates.

## Evidence template

```text
Operator/date:
Jenkins image and Java:
JENKINS_HOME path:
Volume and mount:
Directory inventory (names only):
Owner/mode:
Disk/inodes:
Controller executor count:
JCasC source-of-truth design:
Pipeline result:
Restart persistence:
Three failure diagnoses:
Backup/restore and encryption keys:
Cleanup proof:
Score/assessor:
```

**Next:** Chapter 009 — Jenkins Reverse Proxy, HTTPS, Networking and Access Configuration.
