# Chapter 013 — Jenkins Nodes, Labels, Executors and Workload Scheduling

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 03:** Controller, Agents and Executors  
**Chapter:** 013 / 100  
**Companion lab:** [013 — Nodes, Labels, Executors and Scheduling Check](labs/013-jenkins-nodes-labels-executors-scheduling-check.md)

> **Safety:** Use a disposable Jenkins controller. Keep the built-in node at zero executors. Node labels route work; they are **not** a security boundary. Do not run untrusted PRs on release agents or mount privileged host resources into build agents.

## 1. Learning objectives

Model Jenkins nodes and executor slots; apply label expressions to route jobs; diagnose queue wait; design static and ephemeral pools; handle maintenance/drain; measure capacity and security isolation; rehearse SRE troubleshooting.

## 2. Scheduling model

```text
Git event / scheduled job
          |
      Jenkins queue
          |
  Pipeline agent selector
          |
  label expression evaluation
          |
 eligible online nodes?
    | yes          | no
    v              v
 available slots?  queue wait
    | yes
    v
 executor reservation
          |
   workspace / steps
          |
 artifacts + results
```

Jenkins **nodes** represent agent-capable machines or pods. **Executors** are concurrent build slots on nodes, not guaranteed CPU cores. **Labels** express capabilities; use approved agent pools and credential scopes to enforce actual isolation.

## 3. Node and executor fundamentals

| Term | Operational meaning |
|---|---|
| Controller built-in node | Controller-local node; production executors should be 0 |
| Permanent node | Long-lived registered VM/host with stable remote root |
| Ephemeral node | Dynamically provisioned Kubernetes pod/cloud VM |
| Label | String assigned to node for capability routing |
| Label expression | Boolean selection using AND, OR, NOT and grouping |
| Executor | Concurrent build slot, subject to actual resource capacity |
| Queue | Pending work waiting for suitable node/executor |
| Remote root | Agent-side location for remoting/workspaces |
| Temporarily offline | Administrative state preventing new assignments |

## 4. Label expression design

Examples:

```groovy
agent { label 'linux && docker' }
agent { label 'linux && (amd64 || arm64)' }
agent { label 'release && !untrusted' }
```

Prefer a controlled taxonomy such as `os-linux`, `arch-amd64`, `tool-java21`, `pool-trusted`, `pool-untrusted`, `cloud-eks`. Avoid ambiguous labels and make node capabilities verifiable. Parentheses make precedence explicit.

## 5. Executor sizing principles

- Begin with one executor for expensive or untrusted workloads and profile CPU, memory, I/O and build duration.
- More executors can increase contention and **worsen** queue latency.
- Reserve capacity for release and incident jobs where required.
- Prefer ephemeral agents for burst workloads, with quotas and TTL cleanup.
- Observe queue wait percentile, executor utilization, provisioning time and build failure rate.
- Do not confuse Jenkins executor slots with Kubernetes CPU limits or VM vCPU count.

## 6. Disposable controller

```bash
docker volume create jenkins-ch013-home
docker run -d --name jenkins-ch013 --restart=no \
  -p 127.0.0.1:8091:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch013-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch013
docker logs --tail 80 jenkins-ch013
docker port jenkins-ch013
```

This mutable LTS tag is for learning; pin a verified digest in production. Unlock privately at `http://127.0.0.1:8091`, create a named admin, and set built-in executors to zero.

## 7. Inspect nodes and queue in UI

Navigate **Manage Jenkins → Nodes**. Record built-in node executors, node names, labels, online/offline status, temporary offline reason and available executor slots. Inspect the build queue and note the exact scheduling reason shown for waiting jobs.

## 8. Pipeline with an explicit label

```groovy
pipeline {
  agent none
  options {
    timestamps()
    timeout(time: 10, unit: 'MINUTES')
  }
  stages {
    stage('Build on trusted agent') {
      agent { label 'pool-trusted && os-linux' }
      steps {
        sh 'id && hostname && pwd'
      }
    }
  }
}
```

This requires a real approved agent matching both labels. Without it, the build remains queued until timeout. Do not use this Pipeline as a no-agent smoke test.

## 9. Safe no-agent queue demonstration

Create a Pipeline job with the example above on the disposable controller **without** adding any agents. Confirm the job waits for `pool-trusted && os-linux`, then cancel it. Do not enable controller executors just to make it run. Queue cancellation is an expected outcome for this exercise.

## 10. Static versus ephemeral capacity

| Design | Advantage | Operational risk |
|---|---|---|
| Static VM agents | Predictable warm capacity and toolchains | Drift, idle cost, maintenance |
| Kubernetes ephemeral pods | Isolation and burst scheduling | Pod Pending, quota, image pulls |
| Cloud VM ephemeral agents | Stronger per-VM isolation | Provisioning delay, cost, orphaned VMs |
| Mixed pools | Match workload to trust/cost needs | Label sprawl and routing complexity |

## 11. Maintenance and drain procedure

1. Announce maintenance and identify running builds.
2. Mark node **temporarily offline** to stop new assignments.
3. Wait for existing builds to complete or use approved cancellation policy.
4. Patch/restart agent and verify remoting/toolchain/workspace.
5. Bring node online, run labeled smoke job and monitor.
6. Record change, capacity impact and rollback.

## 12. Monitoring and SLOs

Track queue wait percentiles, queued build counts by label, executor occupancy, node online ratio, provisioning latency, CPU/memory/disk, job duration and cancellation/timeout rates. Alert on sustained queue starvation and unexpected execution on sensitive pools.

## 13. Twenty scheduling failure scenarios

| # | Symptom | Investigation | Safe response |
|---|---|---|---|
| 1 | Build queued: no matching label | Compare Pipeline expression and node labels | Provision compatible labeled node |
| 2 | Build queued: agent offline | Inspect node status and launch logs | Restore connection |
| 3 | Build queued: all executors busy | Inspect node executors and queue time | Add capacity or adjust concurrency |
| 4 | Build queued: node temporarily offline | Inspect administrative offline cause | Re-enable after validation |
| 5 | Wrong agent selected | Review label expression and node inventory | Correct labels and workload routing |
| 6 | Untrusted PR on release agent | Review job SCM trust and credential scope | Quarantine, rotate and isolate |
| 7 | Controller executes a build | Check built-in executors and agent directive | Set built-in executors zero |
| 8 | Executor count exceeds CPU/memory | Inspect agent saturation and per-build demand | Right-size from load tests |
| 9 | Large workspace fills disk | Inspect df, df -i, retention and workspace | Expand or approved cleanup |
| 10 | Node label typo | Compare label expressions and node labels | Correct approved configuration |
| 11 | AND/OR expression unexpected | Review Jenkins label expression syntax | Add parentheses and test |
| 12 | Agent stuck reconnecting | Inspect remoting, Java, TLS, network | Restore compatible transport |
| 13 | Kubernetes pod Pending | Inspect scheduling events and quotas | Fix resources, selectors or capacity |
| 14 | Kubernetes agent eviction | Inspect QoS, pressure and events | Right-size requests/limits |
| 15 | Cloud agent provisioning timeout | Inspect API quotas and provisioning logs | Fix plugin/permissions/quotas |
| 16 | Queue wait increases after deploy | Compare workload mix and available slots | Scale eligible agent pool |
| 17 | Build starvation from long jobs | Inspect build durations and concurrency | Separate queues/labels and set timeouts |
| 18 | Parallel stages oversubscribe node | Review executor slots and nested parallelism | Control concurrency and resources |
| 19 | Node in maintenance still schedules | Inspect temporarily offline and drain plan | Mark offline and wait for active builds |
| 20 | Misleading online agent | Verify actual toolchain, disk and connectivity | Run capability health check |

## 14. Eight SRE runbooks

### RB-01 Queue starvation

**Procedure:** Inspect queue reason, label expression, online nodes, available executors and provisioning logs; restore capacity.

**Exit criteria:** queue reason understood, correct label routing, healthy agents, appropriate executor capacity, trust boundary maintained, evidence recorded.

### RB-02 Wrong-node execution

**Procedure:** Stop affected workload, audit labels and trust boundaries, correct Pipeline selectors and retest.

**Exit criteria:** queue reason understood, correct label routing, healthy agents, appropriate executor capacity, trust boundary maintained, evidence recorded.

### RB-03 Executor saturation

**Procedure:** Correlate CPU/memory, queue wait, job durations and executor counts; adjust only with evidence.

**Exit criteria:** queue reason understood, correct label routing, healthy agents, appropriate executor capacity, trust boundary maintained, evidence recorded.

### RB-04 Planned node maintenance

**Procedure:** Mark node temporarily offline, wait for builds to finish, perform work, run smoke and return to service.

**Exit criteria:** queue reason understood, correct label routing, healthy agents, appropriate executor capacity, trust boundary maintained, evidence recorded.

### RB-05 Ephemeral agent provisioning

**Procedure:** Inspect Kubernetes/cloud quotas, templates, IAM, scheduling and TTL; repair then verify cleanup.

**Exit criteria:** queue reason understood, correct label routing, healthy agents, appropriate executor capacity, trust boundary maintained, evidence recorded.

### RB-06 Security isolation incident

**Procedure:** Quarantine untrusted job/agent, revoke credentials, review logs and restore trusted routing.

**Exit criteria:** queue reason understood, correct label routing, healthy agents, appropriate executor capacity, trust boundary maintained, evidence recorded.

### RB-07 Workspace/disk pressure

**Procedure:** Inspect per-node disk and inode growth, apply approved cleanup or capacity expansion.

**Exit criteria:** queue reason understood, correct label routing, healthy agents, appropriate executor capacity, trust boundary maintained, evidence recorded.

### RB-08 Scheduling change acceptance

**Procedure:** Validate label expressions, workload routing, SLOs, rollback, owner and evidence.

**Exit criteria:** queue reason understood, correct label routing, healthy agents, appropriate executor capacity, trust boundary maintained, evidence recorded.

## 15. Acceptance gates

| Gate | Requirement |
|---|---|
| G1 | Built-in controller executors zero |
| G2 | Nodes, labels, executors and queue differentiated |
| G3 | Boolean label expression behavior explained |
| G4 | Missing-label queue demonstration observed and canceled |
| G5 | Trusted/untrusted workload isolation documented |
| G6 | Static/ephemeral pool tradeoffs reviewed |
| G7 | Node maintenance/drain procedure defined |
| G8 | Queue and executor telemetry specified |
| G9 | Three incidents diagnosed with rollback |
| G10 | Cleanup and evidence complete |

## 16. Assessment — 100 points

| Domain | Points |
|---|---:|
| Nodes and executor fundamentals | 20 |
| Label expressions and scheduling | 25 |
| Capacity, maintenance and agent pools | 20 |
| Security and isolation | 15 |
| Troubleshooting and monitoring | 10 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ and no security-critical failures. Local queue exercises are not proof of a production-ready agent fleet.

## 17. Cleanup

```bash
docker stop jenkins-ch013
docker rm jenkins-ch013
# Destructive: only if exclusively lab-owned.
docker volume rm jenkins-ch013-home
```

**Next:** Chapter 014 — Jenkins Agent Provisioning, Capacity Management and Lifecycle Operations.
