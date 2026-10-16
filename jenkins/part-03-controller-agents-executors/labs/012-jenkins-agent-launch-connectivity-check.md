# Chapter 012 — Companion Lab: Jenkins Agent Launch and Connectivity Check

**Parent:** [Chapter 012](../012-jenkins-agent-architecture-launch-methods-secure-connectivity.md)

## Safety

Run on a disposable localhost controller. SSH, WebSocket and Kubernetes exercises are architecture/tabletop reviews unless an approved staging agent and network exist. Do not disable TLS or SSH host-key verification, expose node secrets or grant agent workloads controller credentials.

## Lab 01 — Verify Docker host

```bash
docker version
docker ps
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Engine ready. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 02 — Create dedicated volume

```bash
docker volume create jenkins-ch012-home
docker volume inspect jenkins-ch012-home
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Dedicated home exists. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 03 — Launch controller

```bash
docker run -d --name jenkins-ch012 --restart=no -p 127.0.0.1:8090:8080 --memory 4g --cpus 2 --mount source=jenkins-ch012-home,target=/var/jenkins_home jenkins/jenkins:lts-jdk21
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Private controller starts. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 04 — Inspect logs

```bash
docker logs --tail 80 jenkins-ch012
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** No fatal startup errors. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 05 — Inspect listener

```bash
docker port jenkins-ch012
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Loopback-only port. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 06 — Complete private bootstrap

```bash
docker exec jenkins-ch012 cat /var/jenkins_home/secrets/initialAdminPassword
```

**Action:** Unlock at http://127.0.0.1:8090 privately and create a named lab administrator.

**Pass:** Named lab admin; password not recorded. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 07 — Set controller executors zero

```bash
docker ps --filter name=jenkins-ch012
```

**Action:** Set Manage Jenkins → Nodes → Built-In Node → executors = 0.

**Pass:** Built-in node has zero executors. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 08 — Inspect runtime identity

```bash
docker inspect jenkins-ch012 --format '{{.Config.Image}} {{.Config.User}}'
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Image and user recorded. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 09 — Inspect home mount

```bash
docker inspect jenkins-ch012 --format '{{json .Mounts}}'
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Persistent home identified. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 10 — Inspect Java

```bash
docker exec jenkins-ch012 java -version
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Runtime version documented. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 11 — Compare SSH and inbound methods

```bash
docker inspect jenkins-ch012 --format '{{.State.Status}}'
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Launch methods and trust boundaries understood. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 12 — Design SSH identity and host-key policy

```bash
docker logs --tail 20 jenkins-ch012
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Dedicated account and strict verification documented. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 13 — Design inbound WebSocket connection

```bash
docker port jenkins-ch012
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Proxy/TLS and agent secret requirements documented. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 14 — Design inbound TCP firewall

```bash
docker inspect jenkins-ch012 --format '{{json .NetworkSettings.Networks}}'
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Approved listener and network restrictions. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 15 — Design Kubernetes ephemeral pod

```bash
docker inspect jenkins-ch012 --format '{{.Config.Image}}'
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** RBAC, pod security and image pinning documented. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 16 — Review labels and queue

```bash
docker stats --no-stream jenkins-ch012
```

**Action:** Review the labeled Pipeline below; do not run it without an actual approved matching agent.

**Pass:** Label mismatch and executor wait explained. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 17 — Review resource pressure

```bash
docker exec jenkins-ch012 sh -c 'df -h /var/jenkins_home && df -i /var/jenkins_home'
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Disk/inode baseline. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 18 — Diagnose three agent failures

```bash
docker logs --tail 80 jenkins-ch012
```

**Action:** Perform a tabletop diagnosis for SSH host-key mismatch, WebSocket 502 and Kubernetes Pending pod.

**Pass:** SSH, WebSocket and Pending pod incidents analyzed. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 19 — Write monitoring and rollback plan

```bash
docker volume inspect jenkins-ch012-home
```

**Action:** Record redacted evidence and identify the operational/security implication.

**Pass:** Agent telemetry, escalation and recovery documented. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Lab 20 — Cleanup and score

```bash
docker stop jenkins-ch012
docker rm jenkins-ch012
# After ownership check: docker volume rm jenkins-ch012-home
```

**Action:** Delete only lab-owned resources; verify volume ownership before deletion.

**Pass:** Lab cleaned safely. **Rollback:** revert only lab-owned changes or restore verified lab volume.

## Agent-backed Pipeline (approved staging only)

```groovy
pipeline {
  agent none
  stages {
    stage('Agent connectivity') {
      agent { label 'trusted-linux-build' }
      steps {
        sh 'java -version && id && hostname'
      }
    }
  }
}
```

If the label has no online agent, the Pipeline will queue. This is an expected scheduling outcome, not proof of a controller outage.

## Troubleshooting decision matrix

| Failure | Inspect | Safe fix |
|---|---|---|
| SSH denied | Identity, key, host-key fingerprint | Restore trusted SSH auth |
| WebSocket 502 | TLS proxy and upgrade headers | Repair upstream/headers |
| Agent secret rejected | Node identity and remoting | Rotate affected secret |
| Java mismatch | Controller and agent versions | Use supported runtime |
| No label match | Queue reason and node labels | Provision correct agent |
| Pod Pending | Kubernetes events and quotas | Fix scheduling/capacity |
| Disk full | Agent workspace disk/inodes | Approved retention/expand |
| Orphaned agent | Cloud/pod owner and TTL | Reconcile resources |

## Assessment — 100 points

| Domain | Points |
|---|---:|
| Launch methods | 20 |
| SSH/WebSocket/inbound security | 25 |
| Java, labels and executors | 20 |
| Ephemeral cloud agents | 15 |
| Troubleshooting/monitoring | 10 |
| Cleanup/evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with mandatory security gates.

## Evidence template

```text
Operator/date:
Controller URL and binding:
Jenkins/Java version:
Built-in executors:
SSH identity/host-key policy:
Inbound TCP/WebSocket design:
Agent labels and queue:
Kubernetes/cloud provisioning design:
Agent security isolation:
Three incident diagnoses:
Metrics and alert owners:
Cleanup proof:
Score/assessor:
```

**Next:** Chapter 013 — Jenkins Nodes, Labels, Executors and Workload Scheduling.
