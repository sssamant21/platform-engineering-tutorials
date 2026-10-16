# Chapter 015 — Jenkins Controller, Agents and Executors Production Operations Capstone

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 03:** Controller, Agents and Executors  
**Chapter:** 015 / 100 — **Part 03 capstone**  
**Companion lab:** [015 — Controller, Agents and Executors Operations Capstone Check](labs/015-jenkins-controller-agents-executors-operations-capstone-check.md)

> **Safety:** This capstone uses a disposable localhost Jenkins controller. SSH/Kubernetes/cloud agent provisioning, production TLS, and disaster recovery are **design or approved-staging activities**, not automatically executed by the lab. Never enable built-in controller executors for untrusted builds, expose controller secrets or run fault injection on production.

## 1. Capstone mission and prerequisites

Integrate controller architecture, secure agent launch, node labels/executors, queue management, provisioning, scaling, observability, incident response and recoverability into one operational readiness assessment.

Prerequisites:

- [011 — Controller Architecture and Operational Boundaries](011-jenkins-controller-architecture-responsibilities-operational-boundaries.md)
- [012 — Agent Launch Methods and Secure Connectivity](012-jenkins-agent-architecture-launch-methods-secure-connectivity.md)
- [013 — Nodes, Labels, Executors and Workload Scheduling](013-jenkins-nodes-labels-executors-workload-scheduling.md)
- [014 — Agent Provisioning, Capacity and Lifecycle](014-jenkins-agent-provisioning-capacity-management-lifecycle-operations.md)

## 2. Enterprise reference architecture

```text
 GitHub / GitLab -> trusted HTTPS proxy + SSO
                            |
               Jenkins controller (0 executors)
               +---------------------------+
               | queue, scheduler, RBAC    |
               | Pipeline state, JCasC     |
               | credentials policy        |
               | plugins and audit         |
               +---------------------------+
                  |          |         |
              SSH agents   WebSocket   cloud provisioner
                static      inbound      /         \
                 VM           VM      Kubernetes    cloud VM
                  \           |         |           /
                   trusted and untrusted pools separated
                              |
                    build / test / scan
                              |
                 artifact registry + GitOps
                              |
         controller state: encrypted JENKINS_HOME + keys
                              |
               backup / monitoring / DR restore
```

A Jenkins controller coordinates work; workspace-dependent build steps run on isolated agents. Node labels route jobs but **do not enforce security isolation**. Active/active controllers must not share one writable JENKINS_HOME.

## 3. Operational control matrix

| Domain | Production requirement | Evidence |
|---|---|---|
| Controller runtime | Approved LTS, supported Java and tested plugins | Versions and change record |
| Controller isolation | Built-in node executors = 0 | Node configuration |
| State | Protected persistent home, keys and backups | Mount and restore report |
| Access | Trusted HTTPS, SSO/RBAC and audited admin | Security review |
| Agent transport | Verified SSH host keys or authenticated encrypted inbound/WebSocket | Connection test |
| Workload isolation | Separate untrusted and privileged pools | IAM/RBAC, network and credentials |
| Queue scheduling | Approved label taxonomy and capacity | Queue and node metrics |
| Ephemeral lifecycle | Bounded provisioning, TTL, drain and orphan cleanup | Cloud/pod inventory |
| Monitoring | Queue p95, agent health, JVM, disk, cost and backup age | Dashboard/alerts |
| Recovery | Runbooks, compatible snapshots, clean-room restore | Drill evidence |

## 4. Disposable controller deployment

```bash
docker volume create jenkins-ch015-home
docker run -d --name jenkins-ch015 --restart=no \
  -p 127.0.0.1:8093:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch015-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch015
docker logs --tail 80 jenkins-ch015
docker port jenkins-ch015
```

The mutable LTS tag is for disposable learning only; pin a reviewed image digest in production. Open `http://127.0.0.1:8093`, unlock privately, create a named admin and configure **Manage Jenkins → Nodes → Built-In Node → executors = 0**.

## 5. Runtime and persistence inspection

```bash
docker inspect jenkins-ch015 --format '{{.Config.Image}} {{.Config.User}}'
docker inspect jenkins-ch015 --format '{{json .Mounts}}'
docker exec jenkins-ch015 sh -c 'printf "JENKINS_HOME=%s\n" "$JENKINS_HOME"; df -h /var/jenkins_home; df -i /var/jenkins_home'
docker stats --no-stream jenkins-ch015
```

Capture redacted evidence; never print full environment dumps, credential XML, unlock tokens or controller secret keys in a shared report.

## 6. No-agent controller orchestration smoke test

Create a Pipeline job named `ch015-controller-smoke`:

```groovy
pipeline {
  agent none
  options { timestamps() }
  stages {
    stage('Orchestration') {
      steps { echo 'Controller coordinates Pipeline state.' }
    }
    stage('Isolation') {
      steps { echo 'Built-in node executors remain zero.' }
    }
  }
}
```

This tests Pipeline orchestration without a workspace; it does **not** validate agent connectivity.

## 7. Label-based queue demonstration

Create a second Pipeline `ch015-label-queue`:

```groovy
pipeline {
  agent none
  options { timeout(time: 5, unit: 'MINUTES') }
  stages {
    stage('Build') {
      agent { label 'pool-trusted && os-linux' }
      steps { sh 'id && hostname' }
    }
  }
}
```

Without an eligible agent, Jenkins queues the job. Record the displayed queue reason and **cancel** the build. If a matching agent exists unexpectedly, stop and review the pool before execution. Never enable controller executors to bypass the queue.

## 8. Secure agent design acceptance

### SSH static agents

Use a dedicated non-root OS account, separate remote root, supported Java/remoting, approved SSH credentials and strict host-key verification. Never use `StrictHostKeyChecking=no`.

### Inbound/WebSocket agents

Use agent-specific secrets, authenticated encrypted transport and trusted HTTPS proxy upgrade headers. Restrict inbound TCP listener if enabled; WebSocket can simplify controlled outbound connectivity.

### Kubernetes/cloud ephemeral agents

Use immutable images, dedicated workload identity, namespace/IAM boundaries, resource requests/limits, pod security, owner tags, TTL and cleanup. Do not mount the host Docker socket into untrusted builds.

## 9. Capacity and scaling model

Estimate executor demand with arrival rate `λ`, mean job duration `W`, and target utilization `u`:

```text
estimated_slots = ceil((arrival_jobs_per_minute * mean_minutes) / utilization)
example: ceil((6 * 4) / 0.70) = 35 slots
```

This is an initial sizing approximation, **not** a queue SLO guarantee. Include burstiness, agent startup latency, label fragmentation, workload CPU/memory/I/O and p95 queue wait in load tests. Executors are scheduling slots, not equivalent to vCPUs.

## 10. Maintenance and lifecycle acceptance

1. Identify active builds and owner.
2. Mark the target node temporarily offline to prevent new assignments.
3. Drain existing jobs or follow an approved cancellation policy.
4. Patch/replace agent using tested immutable image or VM baseline.
5. Verify Java, remoting, toolchain, workspace and labels.
6. Re-enable, run representative labeled job, monitor queue and failures.
7. Reconcile cloud/pod inventory and orphan cleanup.

## 11. SLO, observability and FinOps

Define alerts for controller HTTP availability, JVM heap/GC, queue p95, online agent ratio, executor utilization, agent connection errors, provisioning p95, pod OOM/evictions, disk/inodes, backup freshness, orphan resources and idle spend. Record named owners, escalation and budget ceilings.

## 12. Twenty production failure scenarios

| # | Symptom | Investigation | Safe recovery |
|---|---|---|---|
| 1 | Controller unavailable | Proxy 502, Jenkins process, JVM and persistent volume | Restore approved runtime; validate login and queue |
| 2 | Controller JVM heap pressure | GC pause, heap occupancy and thread dumps | Profile and right-size; investigate plugin leaks |
| 3 | Controller disk full | JENKINS_HOME bytes/inodes and retention | Expand or perform reviewed cleanup |
| 4 | Two controllers share writable home | Mount ownership, process inventory and fencing | Stop second writer; assess integrity and restore |
| 5 | Credentials cannot decrypt | Snapshot/key pairing and secrets directory | Restore complete protected backup |
| 6 | Controller runs builds | Built-in node executors and Pipeline agent | Set zero executors and isolate builds |
| 7 | Queue starvation | Queue reasons, labels, offline nodes and capacity | Correct routing or provision eligible capacity |
| 8 | Label mismatch | Pipeline expression and agent labels | Fix taxonomy and verify in staging |
| 9 | All executors saturated | CPU/memory, slot occupancy and duration | Tune from workload profiles |
| 10 | SSH launch failure | Agent SSH key, known_hosts, firewall and Java | Repair verified host trust and least privilege |
| 11 | Inbound WebSocket failure | Proxy Upgrade headers, TLS and agent token | Restore secure agent transport |
| 12 | Agent remoting incompatibility | Controller, Java, remoting and plugin matrix | Roll back compatible versions |
| 13 | Kubernetes agent Pending | Pod events, quotas, requests, taints | Fix scheduling/capacity |
| 14 | Kubernetes agent OOMKilled | Exit reason, memory limits and workload | Right-size agent and test |
| 15 | Cloud VM provisioning denied | Cloud IAM, API errors and quota | Correct scoped provisioning permissions |
| 16 | Agent privilege escalation | Agent OS identity, mounts, secrets and RBAC | Quarantine, rotate, audit and rebuild |
| 17 | Untrusted PR accesses release credentials | SCM trust, credential scope, pool separation | Stop affected jobs, revoke/rotate, investigate |
| 18 | Workspace/inode exhaustion | Agent disk, workspaces and cleanup | Approved retention or capacity |
| 19 | Orphaned ephemeral agents | Owner tags, job references, TTL and cloud inventory | Reconcile verified orphan only |
| 20 | Backup cannot restore | Encrypted snapshot, keys, plugin and Java versions | Clean-room restore from compatible set |

## 13. Eight SRE operational runbooks

### RB-01 Controller outage

**Procedure:** Declare incident; inspect ingress, process, JVM and home; restore approved service and smoke test.

**Exit criteria:** controller authenticated, persistent home correct, built-in executors zero, queue/agent state healthy, workload isolation intact, alerts and evidence recorded.

### RB-02 Queue/executor incident

**Procedure:** Record queue reason and p95 wait, labels, online agents, executor utilization; recover capacity.

**Exit criteria:** controller authenticated, persistent home correct, built-in executors zero, queue/agent state healthy, workload isolation intact, alerts and evidence recorded.

### RB-03 Agent connectivity outage

**Procedure:** Inspect SSH/WebSocket/TCP transport, TLS, Java, remoting and network policy.

**Exit criteria:** controller authenticated, persistent home correct, built-in executors zero, queue/agent state healthy, workload isolation intact, alerts and evidence recorded.

### RB-04 Kubernetes/cloud provisioning incident

**Procedure:** Review pod events, cloud quotas, IAM, templates and plugin errors; validate provisioning and cleanup.

**Exit criteria:** controller authenticated, persistent home correct, built-in executors zero, queue/agent state healthy, workload isolation intact, alerts and evidence recorded.

### RB-05 Security boundary breach

**Procedure:** Quarantine job/agent, revoke credentials, preserve evidence, notify security and rebuild trusted images.

**Exit criteria:** controller authenticated, persistent home correct, built-in executors zero, queue/agent state healthy, workload isolation intact, alerts and evidence recorded.

### RB-06 State/backup disaster recovery

**Procedure:** Fence writers, restore matching encrypted JENKINS_HOME and keys in clean room, verify jobs and agents.

**Exit criteria:** controller authenticated, persistent home correct, built-in executors zero, queue/agent state healthy, workload isolation intact, alerts and evidence recorded.

### RB-07 Controlled agent maintenance

**Procedure:** Mark temporarily offline, drain jobs, patch/replace, verify capability, re-enable and observe.

**Exit criteria:** controller authenticated, persistent home correct, built-in executors zero, queue/agent state healthy, workload isolation intact, alerts and evidence recorded.

### RB-08 Change approval and rollback

**Procedure:** Record baseline, approvals, version matrix, gates, owner, rollback trigger and post-change evidence.

**Exit criteria:** controller authenticated, persistent home correct, built-in executors zero, queue/agent state healthy, workload isolation intact, alerts and evidence recorded.

## 14. Ten mandatory acceptance gates

| Gate | Lab evidence | Production requirement |
|---|---|---|
| G1 | Private controller and named admin | TLS/SSO/RBAC and restricted backend |
| G2 | Zero built-in executors | Continuous policy check |
| G3 | Durable home and restart proof | Encrypted backup, keys and tested restore |
| G4 | No-agent Pipeline success | Representative orchestration test |
| G5 | Missing-label queue demonstrated and canceled | Correct workload routing |
| G6 | SSH/WebSocket security design | Approved live agent connectivity |
| G7 | Kubernetes/cloud provisioning plan | Live staging quota, IAM and cleanup tests |
| G8 | Capacity sizing and lifecycle drain | Measured queue p95 and cost controls |
| G9 | Three incident tabletop exercises | On-call runbooks and DR rehearsal |
| G10 | Redacted evidence and cleanup | Independent change/go-live approval |

**Important:** Educational lab success is not production certification. Live agent transport, cloud provisioning, TLS and disaster recovery gates require separate staging/production evidence.

## 15. Assessment — 100 points

| Domain | Points |
|---|---:|
| Controller architecture and isolation | 20 |
| Agent security and transport | 20 |
| Nodes, labels and executor scheduling | 20 |
| Provisioning, scaling and lifecycle | 15 |
| Observability, incidents and DR | 15 |
| Evidence, cleanup and handoff | 10 |
| **Total** | **100** |

**Educational pass:** 90+ with no security-critical failures. Production acceptance requires verified mandatory controls and accountable approval.

## 16. Recovery and rollback playbook

Before changes, capture immutable versions, plugin catalog, JCasC diff, protected home snapshot and key inventory. Stage the upgrade and agent tests; quiet-down where required. After change, verify login, Pipeline smoke, queue/agents, webhook and SLO. If incompatible plugin/data migrations prevent safe downgrade, restore the **compatible full pre-change state**, rather than swapping only a binary.

## 17. Safe teardown

```bash
docker stop jenkins-ch015
docker rm jenkins-ch015
# Destructive only if the volume is exclusively owned by this lab:
docker volume rm jenkins-ch015-home
```

**Part 03 complete:** Controller, Agents and Executors — Chapters 011–015.

**Next:** Chapter 016 — Jenkins Jobs, Freestyle Projects and Pipeline Job Fundamentals, beginning Part 04 — Jenkins Jobs and Pipeline Fundamentals.
