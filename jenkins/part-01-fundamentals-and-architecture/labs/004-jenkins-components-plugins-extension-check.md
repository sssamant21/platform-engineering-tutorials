# Chapter 004 — Companion Hands-On Lab: Jenkins Components, Plugins and Extension Check

**Parent:** [Chapter 004](../004-jenkins-core-components-plugins-extension-architecture.md)

## Goal and safety

Inspect core components, plugin inventory, extension concepts, Pipeline steps, dependency risks and SRE recovery in a disposable Jenkins controller. Do not install arbitrary plugins or modify production controllers. Keep controller executors at zero.

## Prerequisites

Docker Linux containers, localhost port 8083 available, sufficient resources and a dedicated lab volume. Record the actual Jenkins and Java versions; `jenkins/jenkins:lts-jdk21` is a mutable learning tag.

## Lab 01 — Check Docker environment

```bash
docker version
docker ps
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Docker daemon responds. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 02 — Create persistent home

```bash
docker volume create jenkins-ch004-home
docker volume inspect jenkins-ch004-home
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Dedicated volume exists. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 03 — Start disposable controller

```bash
docker run -d --name jenkins-ch004 --restart=no -p 127.0.0.1:8083:8080 -v jenkins-ch004-home:/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Controller starts on localhost. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 04 — Inspect bootstrap and logs

```bash
docker logs --tail 100 jenkins-ch004
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** No fatal startup errors. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 05 — Complete setup and verify isolation

```bash
docker exec jenkins-ch004 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Additional action:** Complete the local unlock wizard privately and set built-in node executors to zero.

**Pass:** Local UI accessible; built-in executors set to zero. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 06 — Identify core components

```bash
docker inspect jenkins-ch004 --format '{{.Config.Image}}'
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Candidate maps jobs, runs, queue, nodes and controller. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 07 — Inspect plugin directory

```bash
docker exec jenkins-ch004 sh -c 'ls -1 /var/jenkins_home/plugins | head -40'
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Installed plugin files recorded. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 08 — Check plugin manager

```bash
docker logs --tail 80 jenkins-ch004
```

**Additional action:** Inspect Manage Jenkins → Plugins and record the installed versions; no upgrades.

**Pass:** Installed plugin versions and warnings captured from UI. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 09 — Review plugin dependencies

```bash
docker exec jenkins-ch004 java -version
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Candidate explains core/plugin/Java compatibility. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 10 — Review extension architecture

```bash
docker ps --filter name=jenkins-ch004
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Candidate maps Step, Descriptor and extension APIs. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 11 — Execute no-agent Pipeline

```bash
docker logs --tail 20 jenkins-ch004
```

**Additional action:** Create a Pipeline job using the Jenkinsfile below and run it.

**Pass:** UI echo-only Pipeline succeeds. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 12 — Test queue and missing agent

```bash
docker ps --filter name=jenkins-ch004
```

**Additional action:** Create a temporary Pipeline with agent label missing-ch004-agent, observe queued state, then cancel it.

**Pass:** Job requiring nonexistent label queues and is cancelled. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 13 — Inspect JCasC schema concept

```bash
docker exec jenkins-ch004 sh -c 'test -d /var/jenkins_home && echo home-ready'
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Candidate explains schema version coupling. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 14 — Review plugin security

```bash
docker inspect jenkins-ch004 --format '{{json .Mounts}}'
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Security advisory and plugin approval process documented. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 15 — Restart and validate persistence

```bash
docker restart jenkins-ch004
docker logs --tail 60 jenkins-ch004
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Settings and jobs survive restart. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 16 — Investigate plugin loading failure

```bash
docker logs --tail 200 jenkins-ch004
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Candidate identifies dependency/version failure signatures without injecting faults. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 17 — Design rollback and backup

```bash
docker volume inspect jenkins-ch004-home
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Recovery includes Jenkins home, encryption keys, plugin versions and clean-room restore. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 18 — Cleanup and acceptance

```bash
docker stop jenkins-ch004
docker rm jenkins-ch004
# After verifying exclusive ownership: docker volume rm jenkins-ch004-home
```

**Additional action:** Inspect corresponding UI or architecture evidence and document findings.

**Pass:** Disposable resources removed and score recorded. **Rollback:** cancel only lab jobs, restore reviewed configuration, or stop/remove only the dedicated lab resources.

## Lab 11 Jenkinsfile

```groovy
pipeline {
  agent none
  stages {
    stage('Core architecture') {
      steps { echo 'Core owns jobs, queue, security and nodes.' }
    }
    stage('Plugin extension') {
      steps { echo 'Plugins supply Pipeline steps and integrations.' }
    }
  }
}
```

## Plugin failure triage matrix

| Symptom | Likely issue | Verification |
|---|---|---|
| Missing step | Pipeline plugin unavailable | Installed plugin list and logs |
| Plugin disabled | Administrative action or dependency | Plugin manager and dependency graph |
| Class loading failure | Incompatible API/JVM | Core/Java/plugin version matrix |
| JCasC key rejected | Plugin schema changed | Validate YAML against installed versions |
| Agent provisioning failed | Cloud plugin, auth, quota | Cloud logs and pod events |
| Plugin update stalled | Network/proxy/update center | TLS and update center connectivity |
| Credentials step failed | Plugin or scope | Credentials Binding plugin and folder permissions |
| Restart loses plugin state | Wrong JENKINS_HOME mount | Docker volume inspection |

## Final assessment

| Area | Points |
|---|---:|
| Core architecture and agent isolation | 20 |
| Plugin inventory and dependencies | 20 |
| Extension points and Pipeline steps | 20 |
| Security and upgrade governance | 15 |
| Troubleshooting and restore design | 15 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ and all safety gates.

## Evidence

```text
Operator/date:
Controller image and Java:
Controller executor count:
Installed plugin inventory:
Dependency observations:
Pipeline result:
Queued agent test:
JCasC validation notes:
Security advisory review:
Restart evidence:
Backup/restore plan:
Cleanup proof:
Score/assessor:
```

**Next:** Chapter 005 — Jenkins Architecture and Administration Fundamentals Capstone.
