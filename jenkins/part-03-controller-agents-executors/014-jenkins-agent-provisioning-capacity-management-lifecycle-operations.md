# Chapter 014 — Jenkins Agent Provisioning, Capacity Management and Lifecycle Operations

**Series:** Jenkins Enterprise Administration, CI/CD & SRE Operations  
**Part 03:** Controller, Agents and Executors  
**Chapter:** 014 / 100  
**Companion lab:** [014 — Agent Provisioning, Capacity and Lifecycle Check](labs/014-jenkins-agent-provisioning-capacity-lifecycle-check.md)

> **Safety:** Execute controller exercises on a disposable localhost deployment. Cloud/Kubernetes provisioning is a staging design exercise unless you have approved credentials and an isolated account/namespace. Never expose controller credentials or mount the host Docker socket in untrusted agents.

## 1. Objectives

Design static, cloud VM and Kubernetes agent pools; understand plugin-based provisioning, identity, quotas, autoscaling, queue-driven capacity, agent lifecycle, termination and cleanup; estimate cost and diagnose provisioning incidents.

## 2. Enterprise reference architecture

```text
SCM events -> Jenkins controller (0 executors)
                  |
           queue / labels / demand
                  |
          agent provisioning plugin
           /         |          \
    static VMs    cloud VMs     Kubernetes
      SSH          ephemeral     pod agents
       |              |            |
   workspace       workspace     workspace
       \              |           /
            build / test / scan
                    |
          artifacts + audit events
                    |
        idle timeout / drain / TTL
                    |
           verified deprovision
```

The controller remains the orchestration and trust plane. Agent provisioning is asynchronous; a provisioned agent is not necessarily online or ready to execute a job.

## 3. Pool types and tradeoffs

| Pool | Strength | Operational tradeoff |
|---|---|---|
| Static Linux VM | Stable toolchain, low startup latency | Idle cost, patching, drift |
| Ephemeral cloud VM | Per-VM isolation, autoscaling | API quotas, startup delay, orphan cost |
| Ephemeral Kubernetes pod | Fast elasticity, workload isolation | Scheduling, images, namespace quotas |
| Warm pool | Predictable latency | Higher idle cost |
| Mixed pool | Match trust, cost and resource requirements | More labels, templates and monitoring |

## 4. Lifecycle state machine

```text
queued demand
   -> requested -> cloud/pod provisioning
   -> booting -> remoting connected
   -> online + eligible label
   -> executor assigned -> job running
   -> job complete -> idle/drain
   -> terminate -> verify resource removed
```

Track both **provisioning time** and **time to usable executor**. A VM/pod existing does not prove a healthy Jenkins agent. During termination, prevent new assignments and respect active jobs; unexpected termination should be treated as a failure requiring safe retries.

## 5. Configuration and identity boundaries

- Jenkins cloud plugins need only the permissions required to provision, inspect and delete agent resources.
- Agent workload identities should be **separate** from controller provisioning credentials.
- Use approved immutable VM images or container digests, least-privilege OS accounts, restricted workspaces and short-lived credentials.
- Separate untrusted PR agents from release/deployment agents using network, IAM, namespace and credential isolation; **labels alone are not security**.
- Define ownership tags/labels, TTL and orphan reconciliation before enabling autoscaling.

## 6. Kubernetes agent template example

This YAML illustrates **pod security and resource shape**, not a complete functional Jenkins agent. The Jenkins Kubernetes plugin supplies remoting connection details and controls pod lifecycle.

```yaml
apiVersion: v1
kind: Pod
metadata:
  labels:
    workload: jenkins-build
spec:
  restartPolicy: Never
  serviceAccountName: jenkins-build
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: jnlp
      image: jenkins/inbound-agent:latest-jdk21 # pin digest in production
      resources:
        requests:
          cpu: 500m
          memory: 1Gi
        limits:
          cpu: "2"
          memory: 2Gi
```

If the workload needs Kubernetes API access, use a purpose-built service account and narrowly scoped RBAC rather than enabling token automount by default. Validate UID, writable workspaces and plugin compatibility with the chosen image.

## 7. Cloud VM provisioning design

Use dedicated subnet/security groups, approved AMI/image, encrypted disks, instance profile/workload identity, user-data hardening and short bootstrap. Require tags for environment, owner, build ID, TTL and cost center. Reconcile cloud inventory against Jenkins node inventory before deleting resources.

## 8. Capacity planning model

Define:

- `λ`: arriving jobs per minute
- `W`: average execution time in minutes
- `C`: required busy executors
- `u`: target utilization, between 0 and 1

Little's Law implies average concurrent executing jobs approximately `λ × W` under stable conditions. A rough capacity starting point is `C ≈ ceil(λ × W / u)`; **this is not a queue-wait guarantee** and ignores burstiness, heavy-tailed durations, startup latency, label fragmentation and resource contention.

**Example:** 6 jobs/minute × 4 minutes / 0.70 = 34.3, so start evaluating **35 executor slots**, then load-test with real resource demand, burst patterns and SLOs. Do not map executor slots one-to-one to vCPUs.

## 9. Autoscaling controls

- Scale from queue demand, eligible labels and available executors—not only aggregate CPU.
- Bound maximum nodes/pods, cloud quotas, cost budgets and provisioning concurrency.
- Use conservative idle termination and drain semantics; avoid thrashing from aggressive scale-down.
- Separate expensive GPU/high-memory builds into dedicated pools.
- Track failed provision requests, API throttling and orphaned resources.
- Prefer stateless agents with disposable workspaces; publish artifacts to managed storage.

## 10. Disposable controller setup

```bash
docker volume create jenkins-ch014-home
docker run -d --name jenkins-ch014 --restart=no \
  -p 127.0.0.1:8092:8080 \
  --memory 4g --cpus 2 \
  --mount source=jenkins-ch014-home,target=/var/jenkins_home \
  jenkins/jenkins:lts-jdk21
docker ps --filter name=jenkins-ch014
docker logs --tail 60 jenkins-ch014
docker port jenkins-ch014
```

Use the mutable LTS tag only for a disposable lab; production should pin a reviewed digest. Unlock privately at `http://127.0.0.1:8092`, create a named admin and set built-in executors to **0**.

## 11. Label-bound queue demonstration

```groovy
pipeline {
  agent none
  options { timeout(time: 5, unit: 'MINUTES') }
  stages {
    stage('Ephemeral build') {
      agent { label 'pool-ephemeral && os-linux' }
      steps {
        sh 'id && hostname'
      }
    }
  }
}
```

With no matching agents, observe the queue reason and cancel the build. This is a safe scheduling demonstration, not an actual provisioning test. An approved staging Kubernetes/cloud pool is required to validate real provisioning.

## 12. Metrics and SLOs

Track queue wait p50/p95, executor utilization, provisioning p95, online-ready ratio, build failures, OOM/evictions, pod/VM churn, orphan count, idle cost and cleanup latency. Set alert ownership and budget guardrails.

## 13. Twenty provisioning and lifecycle failure scenarios

| # | Symptom | Investigation | Safe response |
|---|---|---|---|
| 1 | VM API permission denied | Inspect service principal/IAM role and audit logs | Restore least privilege permissions |
| 2 | Cloud quota exhausted | Check instance, vCPU and IP quotas | Request capacity or choose approved pool |
| 3 | Kubernetes pod Pending | kubectl describe pod and scheduler events | Correct resources, affinity, taints or capacity |
| 4 | ImagePullBackOff | Inspect registry auth, digest and events | Repair image access |
| 5 | Provisioning latency spikes | Measure API, image pull and startup phases | Optimize warm capacity or images |
| 6 | Agent Java mismatch | Check java -version and remoting logs | Use supported Java and agent image |
| 7 | Inbound WebSocket fails | Check TLS proxy upgrade and connection logs | Repair trusted proxy path |
| 8 | SSH host-key mismatch | Verify host identity against inventory | Rotate approved known_hosts entry |
| 9 | Ephemeral agent never terminates | Check job lifecycle, pod/VM tags and plugin logs | Reconcile orphan after ownership check |
| 10 | Agent OOMKilled | Inspect limits, exit reason and build memory | Right-size agent |
| 11 | Node disk pressure | df -h, df -i and workspace usage | Expand or approved cleanup |
| 12 | Queue waiting for labels | Compare job selectors and pool labels | Correct matching pool |
| 13 | Executors oversubscribed | Correlate CPU, memory and queue wait | Reduce concurrency |
| 14 | Scale-down interrupts job | Review termination/drain and build status | Gracefully drain or retry idempotently |
| 15 | Provisioned agent lacks tools | Inspect image/toolchain manifest | Use approved immutable image |
| 16 | Agent has broad cloud privileges | Review service account and IAM bindings | Restrict workload identity |
| 17 | Untrusted PR reaches release pool | Audit SCM trust, labels and credential scope | Quarantine and rotate affected secrets |
| 18 | Kubernetes API throttling | Inspect 429s, plugin polling and QPS | Tune requests and backoff |
| 19 | Provisioner stuck after upgrade | Compare plugin, Jenkins, Java and cloud API | Rollback compatible tested versions |
| 20 | Idle agent cost increases | Compare billing, idle time and TTL | Adjust warm pool and cleanup policy |

## 14. Eight SRE runbooks

### RB-01 Provisioning outage

**Procedure:** Correlate queue, cloud API, IAM, quota, image and remoting logs; restore compatible capacity.

**Exit criteria:** expected labels online, queue draining, secure identities, bounded provisioning, clean termination, cost and SLO evidence recorded.

### RB-02 Capacity saturation

**Procedure:** Measure queue p95, executor occupancy, CPU/memory and arrival rates; right-size pool and quotas.

**Exit criteria:** expected labels online, queue draining, secure identities, bounded provisioning, clean termination, cost and SLO evidence recorded.

### RB-03 Agent security incident

**Procedure:** Quarantine compromised agent, revoke/rotate secrets, audit access and rebuild immutable image.

**Exit criteria:** expected labels online, queue draining, secure identities, bounded provisioning, clean termination, cost and SLO evidence recorded.

### RB-04 Kubernetes Pending/OOM

**Procedure:** Inspect pod events, requests/limits, node capacity, quotas and pod security.

**Exit criteria:** expected labels online, queue draining, secure identities, bounded provisioning, clean termination, cost and SLO evidence recorded.

### RB-05 Cloud orphan cleanup

**Procedure:** Identify owner tags, job references and age; quarantine and delete only verified orphan resources.

**Exit criteria:** expected labels online, queue draining, secure identities, bounded provisioning, clean termination, cost and SLO evidence recorded.

### RB-06 Planned agent rotation

**Procedure:** Drain, wait for active jobs, replace immutable image and run capability smoke.

**Exit criteria:** expected labels online, queue draining, secure identities, bounded provisioning, clean termination, cost and SLO evidence recorded.

### RB-07 Plugin/remoting compatibility

**Procedure:** Review Jenkins core, plugin and Java matrix; stage upgrade and roll back if needed.

**Exit criteria:** expected labels online, queue draining, secure identities, bounded provisioning, clean termination, cost and SLO evidence recorded.

### RB-08 Cost and SLO handoff

**Procedure:** Publish utilization, queue wait, provisioning latency, TTL, budget and on-call ownership.

**Exit criteria:** expected labels online, queue draining, secure identities, bounded provisioning, clean termination, cost and SLO evidence recorded.

## 15. Acceptance gates

| Gate | Evidence |
|---|---|
| G1 | Controller has zero built-in executors |
| G2 | Static, cloud VM and Kubernetes pool differences understood |
| G3 | Agent lifecycle and readiness state documented |
| G4 | IAM/RBAC and trusted/untrusted isolation designed |
| G5 | Immutable images, resource limits and quotas reviewed |
| G6 | Queue-driven capacity example calculated |
| G7 | Idle termination, drain and orphan reconciliation planned |
| G8 | Queue/provisioning SLO and FinOps metrics defined |
| G9 | Three incidents and rollback rehearsed |
| G10 | No secret exposure; cleanup and evidence complete |

## 16. Assessment — 100 points

| Domain | Points |
|---|---:|
| Agent pool architecture and lifecycle | 20 |
| Cloud/Kubernetes provisioning security | 20 |
| Capacity and autoscaling | 25 |
| Cost, drain and orphan cleanup | 15 |
| Troubleshooting and monitoring | 10 |
| Cleanup and evidence | 10 |
| **Total** | **100** |

**Pass:** 90+ with mandatory security gates. Local exercises do not certify production cloud autoscaling.

## 17. Safe cleanup

```bash
docker stop jenkins-ch014
docker rm jenkins-ch014
# Destructive only after verifying the volume belongs exclusively to this lab:
docker volume rm jenkins-ch014-home
```

**Next:** Chapter 015 — Jenkins Controller, Agents and Executors Production Operations Capstone.
