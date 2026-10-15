# Chapter 003 — Hands-On Lab: Initial Setup, Global Configuration and Administration

**Parent:** [Chapter 003](../003-jenkins-initial-setup-global-configuration-administration.md)

**Scope:** disposable Docker-based localhost controller. No production secrets, no public ingress and no build executors on controller.

## Prerequisites

Docker Linux containers, free localhost port 8082, adequate RAM/disk and a dedicated lab operator. Do not expose screenshots containing credentials or bootstrap passwords.

## Lab 01 — Check local prerequisites

**Action:**

```bash
docker version
docker ps
```

**Pass condition:** Docker daemon responds and environment is disposable.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 02 — Create lab home

**Action:**

```bash
docker volume create jenkins-ch003-home
docker volume inspect jenkins-ch003-home
```

**Pass condition:** Dedicated persistent volume exists.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 03 — Start Jenkins

**Action:**

```bash
docker run -d --name jenkins-ch003 --restart=no -p 127.0.0.1:8082:8080 -v jenkins-ch003-home:/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Pass condition:** Controller starts and port is localhost only.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 04 — Review startup logs

**Action:**

```bash
docker logs --tail 80 jenkins-ch003
```

**Pass condition:** No fatal startup failure.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 05 — Complete bootstrap

**Action:**

```bash
docker exec jenkins-ch003 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Pass condition:** Unlock in local UI and create named lab admin; never capture token.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 06 — Set controller executors to zero

**Action:**

```bash
docker ps --filter name=jenkins-ch003
```

**UI/design step:** Inspect the corresponding setting in **Manage Jenkins**, capture only redacted evidence, and avoid modifying security-critical settings outside the lab.

**Pass condition:** Built-in Node configuration displays zero executors.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 07 — Review security realm

**Action:**

```bash
docker logs --tail 30 jenkins-ch003
```

**UI/design step:** Inspect the corresponding setting in **Manage Jenkins**, capture only redacted evidence, and avoid modifying security-critical settings outside the lab.

**Pass condition:** Authentication is enabled; no unintended anonymous administration.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 08 — Review authorization

**Action:**

```bash
docker inspect jenkins-ch003 --format '{{.Config.Image}}'
```

**UI/design step:** Inspect the corresponding setting in **Manage Jenkins**, capture only redacted evidence, and avoid modifying security-critical settings outside the lab.

**Pass condition:** Least-privilege design documented and admin access retained.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 09 — Set Jenkins root URL

**Action:**

```bash
docker port jenkins-ch003
```

**UI/design step:** Inspect the corresponding setting in **Manage Jenkins**, capture only redacted evidence, and avoid modifying security-critical settings outside the lab.

**Pass condition:** Local root URL is http://127.0.0.1:8082/.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 10 — Inspect plugin inventory

**Action:**

```bash
docker exec jenkins-ch003 java -version
```

**UI/design step:** Inspect the corresponding setting in **Manage Jenkins**, capture only redacted evidence, and avoid modifying security-critical settings outside the lab.

**Pass condition:** Installed plugin and Java versions recorded.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 11 — Check storage and inode pressure

**Action:**

```bash
docker exec jenkins-ch003 sh -c 'df -h /var/jenkins_home && df -i /var/jenkins_home'
```

**Pass condition:** Enough disk/inodes for operation.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 12 — Review credentials boundaries

**Action:**

```bash
docker inspect jenkins-ch003 --format '{{json .Mounts}}'
```

**UI/design step:** Inspect the corresponding setting in **Manage Jenkins**, capture only redacted evidence, and avoid modifying security-critical settings outside the lab.

**Pass condition:** Candidate describes folder scope and secret handling; no real secret entered.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 13 — Validate JCasC fragment

**Action:**

```bash
docker exec jenkins-ch003 sh -c 'test -d /var/jenkins_home && echo home-ready'
```

**UI/design step:** Inspect the corresponding setting in **Manage Jenkins**, capture only redacted evidence, and avoid modifying security-critical settings outside the lab.

**Pass condition:** Candidate explains numExecutors: 0 and version-dependent plugin schema.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 14 — Run no-agent Pipeline

**Action:**

```bash
docker logs --tail 20 jenkins-ch003
```

**UI/design step:** Inspect the corresponding setting in **Manage Jenkins**, capture only redacted evidence, and avoid modifying security-critical settings outside the lab.

**Pass condition:** UI Pipeline with agent none and echo steps succeeds.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 15 — Test safe restart

**Action:**

```bash
docker restart jenkins-ch003
docker logs --tail 60 jenkins-ch003
```

**Pass condition:** Login, settings and Pipeline persist.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 16 — Practice administration troubleshooting

**Action:**

```bash
docker ps --filter name=jenkins-ch003
```

**UI/design step:** Inspect the corresponding setting in **Manage Jenkins**, capture only redacted evidence, and avoid modifying security-critical settings outside the lab.

**Pass condition:** Three tabletop cases documented: SSO failure, plugin conflict, missing secrets.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 17 — Design clean-room recovery

**Action:**

```bash
docker volume inspect jenkins-ch003-home
```

**UI/design step:** Inspect the corresponding setting in **Manage Jenkins**, capture only redacted evidence, and avoid modifying security-critical settings outside the lab.

**Pass condition:** Backup inventory includes encrypted keys and tested restore checklist.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Lab 18 — Cleanup and score

**Action:**

```bash
docker stop jenkins-ch003
docker rm jenkins-ch003
# After verifying volume ownership: docker volume rm jenkins-ch003-home
```

**Pass condition:** Lab resources removed; 100-point scorecard completed.

**Safety/rollback:** stop on unexpected controller identity or credential exposure; restore the previous approved setting or remove only lab-owned resources.

## Pipeline for Lab 14

Create a disposable Pipeline job with:

```groovy
pipeline {
  agent none
  options { timestamps() }
  stages {
    stage('Admin configuration check') {
      steps { echo 'Controller has zero executors; this is a coordination-only Pipeline.' }
    }
    stage('Policy evidence') {
      steps { echo 'No secret values are printed.' }
    }
  }
}
```

This Pipeline uses no shell or external build executor.

## Troubleshooting quick reference

| Symptom | Check | Safe action |
|---|---|---|
| Jenkins fails to start | Container logs, Java, volume ownership | Restore supported runtime and permissions |
| Login denied | Security realm, SSO, proxy headers | Approved break-glass; do not disable auth |
| Pipeline queued | Agent label and controller executor policy | Provision isolated agent or cancel job |
| Plugin fails to load | Plugin dependencies and startup logs | Restore tested catalog |
| Config missing after restart | Named volume and home mount | Reattach correct lab volume |
| Root URL wrong | Jenkins location and proxy | Fix local URL and validate redirect |
| Secrets visible | Console log, job access | Revoke, rotate and preserve incident evidence |
| Disk full | df -h / df -i | Expand or safely clean owned data |

## Final scorecard

| Area | Points |
|---|---:|
| Secure bootstrap and identity | 20 |
| Controller isolation and global settings | 20 |
| Credentials and authorization | 20 |
| Plugins, JCasC and API awareness | 15 |
| Restart, recovery and troubleshooting | 15 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with no critical security failures.

## Evidence template

```text
Operator / date:
Jenkins version / Java version:
Controller URL and bind:
Admin identity (no secrets):
Controller executor count:
Authorization review:
Plugin inventory:
JCasC validation:
Pipeline job and build result:
Restart and persistence:
Troubleshooting notes:
Backup/restore design:
Cleanup proof:
Score and assessor:
```

**Next:** Chapter 004 — Jenkins Core Components, Plugins and Extension Architecture.
