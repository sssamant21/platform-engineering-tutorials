# Chapter 013 — Companion Lab: Nodes, Labels, Executors and Scheduling Check

**Parent:** [Chapter 013](../013-jenkins-nodes-labels-executors-workload-scheduling.md)

## Goal and safety

Use a disposable controller to examine node/executor state and demonstrate label-driven queue behavior. Do not enable built-in controller executors or create a privileged agent to satisfy a queued job.

## Lab 01 — Check Docker host

```bash
docker version
docker ps
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Engine available. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 02 — Create dedicated volume

```bash
docker volume create jenkins-ch013-home
docker volume inspect jenkins-ch013-home
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Volume exists. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 03 — Start controller

```bash
docker run -d --name jenkins-ch013 --restart=no -p 127.0.0.1:8091:8080 --memory 4g --cpus 2 --mount source=jenkins-ch013-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Controller running privately. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 04 — Review startup logs

```bash
docker logs --tail 80 jenkins-ch013
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** No fatal errors. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 05 — Inspect published listener

```bash
docker port jenkins-ch013
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Only loopback port. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 06 — Complete bootstrap privately

```bash
docker exec jenkins-ch013 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Action:** Unlock at http://127.0.0.1:8091 privately; never include the unlock secret in evidence.

**Pass:** Named lab admin; secret never recorded. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 07 — Set built-in executors zero

```bash
docker ps --filter name=jenkins-ch013
```

**Action:** In Manage Jenkins → Nodes → Built-In Node, configure executors = 0.

**Pass:** Built-in executors zero. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 08 — Inspect node UI

```bash
docker inspect jenkins-ch013 --format '{{.State.Status}}'
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Built-in node status and labels recorded. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 09 — Inspect image and identity

```bash
docker inspect jenkins-ch013 --format '{{.Config.Image}} {{.Config.User}}'
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Runtime inventory. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 10 — Inspect persistent home

```bash
docker inspect jenkins-ch013 --format '{{json .Mounts}}'
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Volume identity verified. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 11 — Inspect resource baseline

```bash
docker stats --no-stream jenkins-ch013
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Controller resources observed. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 12 — Create label-bound Pipeline

```bash
docker logs --tail 20 jenkins-ch013
```

**Action:** Create a Pipeline job using the labeled Jenkinsfile below.

**Pass:** Pipeline saved with missing labels. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 13 — Run queue demonstration

```bash
docker stats --no-stream jenkins-ch013
```

**Action:** Run the job and record the queue reason. No matching agent should exist.

**Pass:** Job waits for matching agent. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 14 — Cancel queued build

```bash
docker logs --tail 30 jenkins-ch013
```

**Action:** Cancel the queued build and confirm queue is clear.

**Pass:** Queue cleared without controller build. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 15 — Review boolean label expressions

```bash
docker ps --filter name=jenkins-ch013
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** AND/OR/NOT behavior explained. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 16 — Design static agent pool

```bash
docker inspect jenkins-ch013 --format '{{.State.Status}}'
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Executor and label plan. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 17 — Design ephemeral Kubernetes pool

```bash
docker inspect jenkins-ch013 --format '{{.Config.Image}}'
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Pod, quota and identity policy. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 18 — Review maintenance drain

```bash
docker logs --tail 30 jenkins-ch013
```

**Action:** Record redacted observed evidence and the operational interpretation.

**Pass:** Temporary offline and recovery plan. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 19 — Diagnose queue starvation

```bash
docker stats --no-stream jenkins-ch013
```

**Action:** Diagnose label mismatch, offline node and executor saturation as tabletop cases.

**Pass:** Three scheduling failures and rollback. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Lab 20 — Cleanup and score

```bash
docker stop jenkins-ch013
docker rm jenkins-ch013
# After ownership check: docker volume rm jenkins-ch013-home
```

**Action:** Remove only resources owned by this lab.

**Pass:** Lab safely removed. **Rollback:** cancel lab jobs or revert only lab-owned settings.

## Queue demonstration Jenkinsfile

```groovy
pipeline {
  agent none
  options { timeout(time: 10, unit: 'MINUTES') }
  stages {
    stage('Label matching') {
      agent { label 'pool-trusted && os-linux' }
      steps {
        sh 'echo Agent selected'
      }
    }
  }
}
```

Expected result: the build waits for an eligible agent. Cancel it after recording the queue reason. If an eligible agent unexpectedly exists, stop and inspect before running the build.

## Label-expression exercises

| Expression | Interpretation |
|---|---|
| `os-linux` | Agent must have os-linux label |
| `os-linux && pool-trusted` | Both labels required |
| `arch-amd64 || arch-arm64` | Either architecture |
| `pool-trusted && !pool-untrusted` | Trusted label present, untrusted label absent |
| `os-linux && (tool-java21 || tool-python)` | Linux and one approved tool capability |

Labels are routing hints, **not** an authorization boundary.

## Scheduling troubleshooting

| Symptom | Inspect | Safe response |
|---|---|---|
| No label match | Queue reason and node labels | Correct approved labels |
| Offline agent | Launch/remoting logs | Restore connection |
| No free executors | Executor occupancy | Scale or tune from evidence |
| Cloud pod Pending | Events, quotas and node capacity | Correct scheduling |
| Wrong trust pool | SCM trust and credentials | Quarantine and isolate |
| Workspace full | Agent disk/inodes | Approved cleanup/expansion |

## Assessment — 100 points

| Domain | Points |
|---|---:|
| Nodes and executors | 20 |
| Label expressions and queue | 25 |
| Capacity and maintenance | 20 |
| Trust boundaries | 15 |
| Troubleshooting/monitoring | 10 |
| Cleanup/evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with mandatory security gates.

## Evidence template

```text
Operator/date:
Controller URL and port binding:
Built-in executor count:
Node inventory and labels:
Queued job and reason:
Queue cancellation proof:
Label expressions reviewed:
Static pool sizing:
Ephemeral pool design:
Maintenance drain procedure:
Three incident diagnoses:
Queue/executor alerts:
Cleanup proof:
Score/assessor:
```

**Next:** Chapter 014 — Jenkins Agent Provisioning, Capacity Management and Lifecycle Operations.
