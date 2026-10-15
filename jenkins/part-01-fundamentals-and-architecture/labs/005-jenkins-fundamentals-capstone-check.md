# Chapter 005 — Hands-On Capstone: Jenkins Architecture and Administration Fundamentals

**Parent:** [Chapter 005](../005-jenkins-architecture-administration-fundamentals-capstone.md)

## Goal

Demonstrate Part 01 skills end-to-end using a disposable local controller and an enterprise architecture tabletop. This is a learning exercise, **not** an approval to alter production.

## Prerequisites and safety

Docker Linux containers, localhost port 8084 available, dedicated volume, sufficient RAM/disk, no production credentials and no public network exposure. Keep controller executors at zero.

## Lab 01 — Validate local Docker host

**Command or inspection:**

```bash
docker version
docker ps
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Docker daemon and host capacity ready.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 02 — Create dedicated state volume

**Command or inspection:**

```bash
docker volume create jenkins-ch005-home
docker volume inspect jenkins-ch005-home
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Lab-owned volume exists.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 03 — Start localhost controller

**Command or inspection:**

```bash
docker run -d --name jenkins-ch005 --restart=no -p 127.0.0.1:8084:8080 -v jenkins-ch005-home:/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Controller starts without public port.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 04 — Inspect startup health

**Command or inspection:**

```bash
docker logs --tail 100 jenkins-ch005
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** No fatal runtime or plugin error.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 05 — Complete private bootstrap

**Command or inspection:**

```bash
docker exec jenkins-ch005 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Required follow-up:** Complete first-run setup in the local browser without saving the unlock password.

**Pass:** Named lab admin created; token not recorded.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 06 — Verify zero controller executors

**Command or inspection:**

```bash
docker ps --filter name=jenkins-ch005
```

**Required follow-up:** In Manage Jenkins → Nodes → Built-In Node, configure zero executors.

**Pass:** Built-in node shows zero executors.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 07 — Review security and authorization

**Command or inspection:**

```bash
docker port jenkins-ch005
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Authentication on; localhost-only access.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 08 — Inventory Jenkins and Java versions

**Command or inspection:**

```bash
docker exec jenkins-ch005 java -version
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Observed versions recorded.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 09 — Inspect plugins and dependencies

**Command or inspection:**

```bash
docker exec jenkins-ch005 sh -c 'ls -1 /var/jenkins_home/plugins | head -40'
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Plugin inventory and compatibility notes recorded.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 10 — Inspect controller storage

**Command or inspection:**

```bash
docker exec jenkins-ch005 sh -c 'df -h /var/jenkins_home && df -i /var/jenkins_home'
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Storage/inode baseline captured.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 11 — Execute capstone Pipeline

**Command or inspection:**

```bash
docker logs --tail 20 jenkins-ch005
```

**Required follow-up:** Create a Pipeline job using the Jenkinsfile below and record its build result.

**Pass:** Smoke Jenkinsfile below succeeds.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 12 — Simulate missing-agent queue safely

**Command or inspection:**

```bash
docker ps --filter name=jenkins-ch005
```

**Required follow-up:** Create a temporary job with agent label missing-capstone-agent, observe the queue reason, then cancel.

**Pass:** Job with nonexistent agent label queues; cancel test.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 13 — Design agent trust boundaries

**Command or inspection:**

```bash
docker inspect jenkins-ch005 --format '{{json .Mounts}}'
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Trusted/untrusted agent classes documented.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 14 — Design JCasC and plugin governance

**Command or inspection:**

```bash
docker exec jenkins-ch005 sh -c 'test -d /var/jenkins_home && echo home-ready'
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Reviewed config and plugin lifecycle plan.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 15 — Design backup and restore

**Command or inspection:**

```bash
docker volume inspect jenkins-ch005-home
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Consistent backup/key escrow and clean-room restore plan.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 16 — Restart controller and validate state

**Command or inspection:**

```bash
docker restart jenkins-ch005
docker logs --tail 60 jenkins-ch005
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Admin config and Pipeline persist.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 17 — Incident tabletop: three failures

**Command or inspection:**

```bash
docker logs --tail 100 jenkins-ch005
```

**Required follow-up:** Use three scenarios from the parent chapter; tabletop only, do not corrupt controller state.

**Pass:** Root cause, evidence, mitigation and rollback documented.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 18 — Define SLO and on-call handoff

**Command or inspection:**

```bash
docker inspect jenkins-ch005 --format '{{.State.Status}}'
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** Metrics, owners, alerts and escalation plan.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 19 — Review ten acceptance gates

**Command or inspection:**

```bash
docker port jenkins-ch005
```

**Required follow-up:** Capture redacted evidence and explain the operational significance.

**Pass:** All mandatory gates checked.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Lab 20 — Cleanup and final scoring

**Command or inspection:**

```bash
docker stop jenkins-ch005
docker rm jenkins-ch005
# After exclusive ownership verification: docker volume rm jenkins-ch005-home
```

**Required follow-up:** Delete the volume only after confirming it is not used by another container or restore exercise.

**Pass:** Lab resources removed and score at least 90/100.

**Safety/rollback:** stop if a production target, shared volume or real credential is involved. Restore only approved lab state.

## Jenkinsfile for Lab 11

```groovy
pipeline {
  agent none
  options {
    timestamps()
    disableConcurrentBuilds()
  }
  stages {
    stage('Architecture') {
      steps { echo 'Jenkins coordinates CI on isolated agents.' }
    }
    stage('Administration') {
      steps { echo 'Controller executors remain zero.' }
    }
    stage('Operational readiness') {
      steps { echo 'Backup, monitoring and plugin governance reviewed.' }
    }
  }
}
```

## Troubleshooting checklist

| Symptom | Check | Recovery |
|---|---|---|
| Container exits | Docker logs, JVM, volume | Fix dependency and restart |
| Local UI unreachable | docker port, browser, logs | Correct localhost binding |
| Setup fails | Jenkins logs and plugin manager | Resolve compatible plugins |
| Pipeline queued | Agent label and node capacity | Cancel job or add isolated agent |
| Jobs lost after restart | Named volume and JENKINS_HOME | Reattach correct volume |
| Admin locked out | Security realm and approved break-glass | Restore auth without disabling security |
| Disk pressure | df -h and df -i | Expand or reclaim only owned lab data |
| Restore lacks credentials | Backup encryption keys and plugin compatibility | Restore complete protected set |

## Final acceptance record

| Gate | Result |
|---|---|
| G1 — localhost-only controller | Pass / Fail |
| G2 — named admin and authentication | Pass / Fail |
| G3 — controller executors zero | Pass / Fail |
| G4 — smoke Pipeline successful | Pass / Fail |
| G5 — plugin inventory and dependency review | Pass / Fail |
| G6 — agent trust boundary design | Pass / Fail |
| G7 — backup/restore plan | Pass / Fail |
| G8 — three incident tabletop cases | Pass / Fail |
| G9 — monitoring and on-call handoff | Pass / Fail |
| G10 — cleanup | Pass / Fail |

## Scoring

Architecture 15, installation 15, security 20, Pipeline/agents 15, plugin/JCasC 10, SRE operations 15, recovery/evidence 10 = **100 points**. **Pass at 90+** with every mandatory gate met.

## Evidence template

```text
Operator and date:
Docker host:
Jenkins image / observed version:
Java version:
Controller executor count:
Port binding:
Pipeline job and result:
Plugin inventory:
Agent isolation design:
JCasC/plugin governance:
Monitoring baseline and alerts:
Backup and restore design:
Three incident scenarios:
Acceptance gates:
Cleanup proof:
Score / assessor / signoff:
```

**Part 01 complete when reviewed. Next:** Chapter 006 — Jenkins Installation on Linux, Packages and systemd.
