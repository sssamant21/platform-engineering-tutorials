# Chapter 011 — Jenkins Controller Architecture, Responsibilities and Operational Boundaries

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 03:** Controller, Agents and Executors  
**Chapter:** 011 / 100  
**Companion lab:** [011 — Controller Architecture and Boundaries Check](labs/011-jenkins-controller-architecture-boundaries-check.md)

> **Safety:** Run executable exercises only on a disposable controller. Do not use controller executors for untrusted builds, share a writable JENKINS_HOME across active controllers, grant agent workloads controller credentials, or expose the Docker socket.

## 1. Learning outcomes

Explain what the Jenkins controller owns, how jobs move through queue/scheduler/executors, distinguish Pipeline orchestration from agent execution, isolate security trust boundaries, design observability and backup/recovery, and diagnose production controller incidents.

## 2. Reference architecture

```text
Developers / GitHub / GitLab
          |
  Trusted HTTPS proxy + SSO
          |
  Jenkins controller (0 executors)
  +-------------------------------------+
  | Authentication / RBAC               |
  | Job config / JCasC / plugin runtime |
  | Queue / scheduler / Pipeline state  |
  | Credentials policy / audit          |
  | Agent provisioning / remoting       |
  +-------------------------------------+
       |                   |
  JENKINS_HOME        Isolated agents
  encrypted state     /           \
  backups/keys       VM          K8s Pod
                       \          /
                   build/test/scan
                         |
                artifact registry
```

**Critical distinction:** Jenkins controller is the coordination and authority plane; agents are the execution plane. The built-in node is physically part of the controller and should not execute production builds.

## 3. Controller responsibilities and boundaries

| Responsibility | Controller behavior and operational implication |
|---|---|
| Queue and scheduling | Controller accepts jobs, evaluates labels, provisions/assigns executors; monitor queue wait |
| Pipeline orchestration | Pipeline execution state and coordination reside in controller; steps requiring workspace execute on agents |
| Configuration | Core/plugin settings, credentials metadata, jobs and JCasC are controller-managed |
| Security authority | Authentication, authorization, credentials scope and audit must be restricted |
| Plugin runtime | Plugins execute controller-side code; test compatibility and limit trusted administrators |
| Persistent state | JENKINS_HOME, secrets, encryption keys, build history and Pipeline durability |
| Agent connections | Controller manages agent lifecycle and remoting, but agents execute workload steps |
| Built-in node | Set built-in executors to zero for production controller isolation |
| Ingress | Trusted TLS proxy, canonical URL, webhooks and secure remoting |
| Recovery | Consistent encrypted backup, key escrow, version compatibility and clean-room restore |

## 4. Jenkins queue, labels and executor model

```text
SCM event / scheduled build
       |
    Job trigger
       |
 Jenkins queue
       |
 label and resource matching
       |
 compatible online agent
       |
 available executor
       |
 Pipeline workspace + steps
       |
 artifacts/logs/results -> controller metadata
```

A Jenkins executor is a concurrent build slot on a node, **not** a CPU core. Set executor count based on workload and resource profiling. A node may be online but unavailable due to label mismatch, executor saturation, temporary offline state or provisioning delay.

## 5. Lab controller setup

```bash
docker version
docker volume create jenkins-ch011-home
docker run -d --name jenkins-ch011 --restart=no \
  -p 127.0.0.1:8089:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch011-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch011
docker logs --tail 80 jenkins-ch011
docker port jenkins-ch011
```

This uses a mutable LTS image tag for disposable learning; production must pin a reviewed digest and tested plugin/Java versions. Keep the backend bound to loopback.

Complete first-run setup privately at `http://127.0.0.1:8089`. Create a named admin and configure **Manage Jenkins → Nodes → Built-In Node → Number of executors = 0**.

## 6. Inspect controller runtime and persistence

```bash
docker inspect jenkins-ch011 --format '{{.Config.Image}} {{.Config.User}}'
docker inspect jenkins-ch011 --format '{{json .Mounts}}'
docker exec jenkins-ch011 sh -c 'printf "JENKINS_HOME=%s\n" "$JENKINS_HOME"'
docker exec jenkins-ch011 sh -c 'df -h /var/jenkins_home && df -i /var/jenkins_home'
docker stats --no-stream jenkins-ch011
```

Avoid dumping raw environment variables, credentials files or full XML configuration into logs or evidence.

## 7. Pipeline orchestration vs execution

Create a no-agent Pipeline job:

```groovy
pipeline {
  agent none
  options { timestamps() }
  stages {
    stage('Controller orchestration') {
      steps {
        echo 'Controller schedules and records Pipeline state.'
      }
    }
    stage('Agent boundary') {
      steps {
        echo 'Real shell/build/test steps must run on isolated agents.'
      }
    }
  }
}
```

The `echo` step is a lightweight Pipeline step that does not require a workspace. Do not add `sh`, `checkout` or other workspace-dependent steps without an agent.

### Agent-backed production pattern

```groovy
pipeline {
  agent none
  stages {
    stage('Build on isolated agent') {
      agent { label 'trusted-linux-build' }
      steps {
        sh 'id && hostname && pwd'
      }
    }
  }
}
```

This example intentionally requires an **already provisioned** agent with the `trusted-linux-build` label; it will queue if no compatible agent is available. Do not assign production credentials to untrusted PR builds.

## 8. Controller isolation and agent trust

- Controller built-in executors: **0**.
- Run agents with dedicated least-privilege identities and isolated workspaces.
- Separate trusted release agents from untrusted PR/test agents.
- Avoid host Docker socket mounts and privileged agents unless explicitly justified and isolated.
- Scope credentials to the narrowest appropriate job/folder and identity.
- Use short-lived agents and ephemeral workspaces where practical.
- Review remoting Java compatibility, transport authentication and network restrictions.
- Treat agent-side logs and artifacts as potentially untrusted input.

## 9. Plugin, Pipeline and JCasC authority

Plugins and administrative scripts can execute privileged code in the controller process. Use approved plugin versions, staging validation, controlled JCasC changes and least-privilege administrative permissions. Protect Pipeline shared libraries and SCM branch trust: a Jenkinsfile from an untrusted branch must not gain production credentials.

## 10. State, backups and disaster recovery

JENKINS_HOME stores jobs, configuration, plugins, secrets and Pipeline-related state. Back up a consistent snapshot with matching encryption keys; store encrypted copies off-controller. Test clean-room restore with compatible core/plugins/Java and verify representative jobs, login, credentials and agent connections.

A single writable home is not an active/active HA architecture. Recovery objectives depend on measured restore times, storage, plugin compatibility and failover procedures.

## 11. Monitoring and SLOs

Monitor controller HTTP availability, queue wait, executor utilization, agent availability, JVM heap/GC, CPU, thread pools, plugin errors, disk/inodes, backup age and failed webhooks. Establish service-specific thresholds and alerts with named owners.

## 12. Twenty controller/agent incident scenarios

| # | Symptom | Diagnosis | Safe response |
|---|---|---|---|
| 1 | Queue builds forever | Inspect label expressions, offline agents, executor capacity | Fix matching agent or provision capacity |
| 2 | Controller CPU saturated | Inspect JVM threads, GC, plugin activity and queue | Reduce controller work and tune after profiling |
| 3 | Controller heap exhausted | Check GC, heap dump policy and plugin memory | Right-size or resolve leak in staging |
| 4 | Build runs on controller | Check built-in executors and job agent directive | Set built-in executors zero; use agents |
| 5 | Agent unexpectedly disconnected | Review remoting logs, network and Java compatibility | Restore trusted transport |
| 6 | Unknown agent connects | Inspect identity, node inventory and access logs | Revoke and investigate |
| 7 | Plugin stalls controller | Correlate thread dump, plugin version and recent changes | Rollback tested plugin/core bundle |
| 8 | JCasC drift | Diff approved YAML against live configuration | Reconcile reviewed source of truth |
| 9 | Secrets exposed to untrusted PR | Inspect credential scope and job trust boundary | Revoke/rotate and isolate pipelines |
| 10 | Multiple controllers share home | Check mounts, process owners and locking | Fence duplicate writer, restore integrity |
| 11 | Controller restart loses state | Inspect volume identity and persistence | Restore correct JENKINS_HOME |
| 12 | Credentials cannot decrypt | Inspect backup key pairing and encryption metadata | Restore complete protected snapshot |
| 13 | Agent runs as root | Inspect runtime identity and permissions | Use least-privilege agent account |
| 14 | Cloud agent provisioning slow | Inspect Kubernetes/VM API, quotas and templates | Correct provisioning bottleneck |
| 15 | Agent workspace disk full | Inspect remote disk and retention | Expand or clean approved workspace |
| 16 | Webhook requests back up | Inspect proxy latency and queue metrics | Fix ingress/controller capacity |
| 17 | Jenkins URL redirect loop | Inspect root URL and forwarded headers | Repair trusted proxy configuration |
| 18 | Backup is incomplete | Audit manifest, keys and restore rehearsal | Rebuild consistent encrypted backup |
| 19 | Controller disk/inodes exhausted | Check home growth, logs, builds and fingerprints | Apply retention or expand storage |
| 20 | Upgrade causes Pipeline failures | Compare core/plugin/remoting versions and smoke tests | Restore compatible pre-upgrade snapshot |

## 13. Eight SRE operational runbooks

### RB-01 Controller saturation

**Procedure:** Capture CPU, heap/GC, thread dumps, queue and plugin activity; protect availability and isolate root cause.

**Exit criteria:** authenticated controller, zero built-in executors, correct home, healthy plugin state, queue/agent status understood, security and monitoring evidence captured.

### RB-02 Queue and executor starvation

**Procedure:** Inspect label matching, node availability, executor count, agent provisioning and queue reasons.

**Exit criteria:** authenticated controller, zero built-in executors, correct home, healthy plugin state, queue/agent status understood, security and monitoring evidence captured.

### RB-03 Agent trust boundary incident

**Procedure:** Quarantine untrusted agent/job, rotate affected credentials and review controller permissions.

**Exit criteria:** authenticated controller, zero built-in executors, correct home, healthy plugin state, queue/agent status understood, security and monitoring evidence captured.

### RB-04 Plugin/JCasC regression

**Procedure:** Freeze changes, compare approved versions/config, restore tested bundle or compatible snapshot.

**Exit criteria:** authenticated controller, zero built-in executors, correct home, healthy plugin state, queue/agent status understood, security and monitoring evidence captured.

### RB-05 Controller home corruption

**Procedure:** Fence duplicate writers, verify volume identity, recover encrypted consistent snapshot.

**Exit criteria:** authenticated controller, zero built-in executors, correct home, healthy plugin state, queue/agent status understood, security and monitoring evidence captured.

### RB-06 Controller restart outage

**Procedure:** Inspect logs, Java, plugin state, storage and ingress; restore service and smoke test.

**Exit criteria:** authenticated controller, zero built-in executors, correct home, healthy plugin state, queue/agent status understood, security and monitoring evidence captured.

### RB-07 Backup and clean-room restore

**Procedure:** Restore home and keys to isolated compatible controller; validate jobs, login and credentials.

**Exit criteria:** authenticated controller, zero built-in executors, correct home, healthy plugin state, queue/agent status understood, security and monitoring evidence captured.

### RB-08 Change handoff and acceptance

**Procedure:** Record SLO, monitoring, agent ownership, escalation, rollback triggers and production approval.

**Exit criteria:** authenticated controller, zero built-in executors, correct home, healthy plugin state, queue/agent status understood, security and monitoring evidence captured.

## 14. Acceptance gates

| Gate | Required evidence |
|---|---|
| G1 | Controller vs agent responsibilities explained |
| G2 | Built-in node has zero executors |
| G3 | Persistent home and protected secrets boundary identified |
| G4 | Controller ingress private and authenticated |
| G5 | No-agent Pipeline smoke succeeds |
| G6 | Agent-backed Pipeline label behavior understood |
| G7 | Trusted/untrusted agent security isolation documented |
| G8 | Queue, executor, JVM and disk monitoring plan |
| G9 | Backup/restore and rollback plan |
| G10 | Three incidents diagnosed and lab cleanup complete |

## 15. Assessment — 100 points

| Domain | Points |
|---|---:|
| Architecture and controller duties | 20 |
| Queue, nodes, labels and executors | 20 |
| Agent security boundaries | 20 |
| State, plugins and configuration | 15 |
| Troubleshooting and observability | 15 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ and mandatory security gates. A localhost educational lab is not production certification.

## 16. Safe cleanup

```bash
docker stop jenkins-ch011
docker rm jenkins-ch011
# Destructive only after verifying the volume belongs solely to this lab:
docker volume rm jenkins-ch011-home
```

**Next:** Chapter 012 — Jenkins Agent Architecture, Launch Methods and Secure Connectivity.
