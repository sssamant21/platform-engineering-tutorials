# Chapter 077 — Jenkins Kubernetes Agent Autoscaling, Dynamic Provisioning and Capacity Optimization

**Part 16 — Scaling, Controller Capacity and Reliability**  
**Audience:** Jenkins SRE, Kubernetes/EKS/AKS platform engineers, FinOps and CI/CD owners  
**Prerequisites:** Chapter 076, Jenkins LTS with Kubernetes plugin, disposable Kubernetes namespace, test registry and Prometheus/Grafana.

## Outcomes

Design reliable ephemeral Jenkins agents, explain the interaction between Jenkins cloud provisioning and Kubernetes node autoscaling, validate scheduling and resource controls, model cold starts, protect workload isolation and optimize capacity/cost without compromising security.

## 1. Two-stage scaling architecture

```text
Git push → Jenkins queue → Kubernetes plugin creates agent Pod
                                    |
                         Kubernetes scheduler
                           /             \
                     node fits       no node fits
                       |                 |
                  start agent      autoscaler/Karpenter
                       |                 |
                  execute job       launch node
                                         |
                                   schedule Pod
```

Jenkins requests **pods**; Cluster Autoscaler or Karpenter provisions **nodes** if constraints and cloud limits permit. Neither guarantees immediate capacity. Queue time includes Jenkins scheduling, pod creation, scheduling, image pulls, initialization, remoting and workspace readiness.

## 2. Agent lifecycle states

| Stage | SLI | Typical bottleneck |
|---|---|---|
| Queued | queue wait p95 | labels, executors, locks |
| Requested | request-to-pod-create | Kubernetes API/RBAC |
| Pending | pod schedule latency | CPU/memory/taints/affinity |
| Pulling | image pull duration | registry, image size |
| Starting | init/container startup | volumes, security context |
| Connecting | remoting handshake | Java, TLS, DNS |
| Executing | build duration/failure | workload, resources |
| Cleanup | pod deletion latency | finalizers, API failures |

Instrument actual timestamps before claiming p95 values. Do not infer per-build timings from coarse cluster-wide averages.

## 3. Secure ephemeral agent template

A **lab-only** Jenkins Kubernetes plugin example:

```groovy
pipeline {
  agent {
    kubernetes {
      yaml '''
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: jenkins-build
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
  containers:
    - name: tools
      image: registry.example.invalid/ci/tools@sha256:REPLACE_WITH_REAL_DIGEST
      command: ["sleep"]
      args: ["infinity"]
      resources:
        requests:
          cpu: "500m"
          memory: "1Gi"
        limits:
          cpu: "2"
          memory: "2Gi"
'''
    }
  }
  stages {
    stage('Verify') {
      steps {
        container('tools') {
          sh 'id && uname -m'
        }
      }
    }
  }
}
```

Replace placeholder registry/digest with a verified image and validate Kubernetes plugin support for the chosen Declarative syntax. Jenkins Kubernetes plugin may inject an inbound agent container; test compatibility with the plugin and cluster security policy. Disable token mounting only if the build does not require Kubernetes API access. Do not grant privileged mode or mount the host Docker socket by default.

## 4. Scheduling, quotas and node constraints

Verify ResourceQuota, LimitRange, node allocatable resources, topology spread, taints/tolerations, node affinity, max pods per node, IP/CNI allocation and PVC topology. The autoscaler cannot fix impossible constraints, denied quotas or invalid pod specs.

Useful commands:

```sh
kubectl get pods -n jenkins-build -o wide
kubectl get events -n jenkins-build --sort-by=.lastTimestamp
kubectl describe pod <agent-pod> -n jenkins-build
kubectl get resourcequota,limitrange -n jenkins-build
kubectl get nodes -o wide
```

Use approved namespaces and replace placeholders. Avoid broad cluster-admin access for agents.

## 5. Karpenter / Cluster Autoscaler

Compare:
- Node startup p50/p95 and cloud API throttling.
- Instance type flexibility, capacity type and AZ constraints.
- Node pool min/max, disruption policy and consolidation.
- Pod requests versus allocatable resources and daemon overhead.
- Interruption handling for spot/preemptible nodes.
- Scale-down protection for active builds.

Karpenter configuration varies by version and cloud provider; use the official provider-specific schema and a pinned tested release. Avoid aggressive consolidation that terminates active CI jobs.

## 6. EKS and AKS considerations

**EKS:** AWS VPC CNI IP limits, IAM roles for service accounts or Pod Identity, ECR auth, Karpenter/Cluster Autoscaler, node groups and instance quotas.

**AKS:** Azure CNI IP capacity, managed identity/workload identity, ACR auth, node pools, Cluster Autoscaler and VM quota.

Cloud workload identity for the build should be scoped to the exact required resources, not inherited from a broad controller identity.

## 7. Warm versus cold agent economics

Warm capacity lowers startup latency but incurs idle cost. Cold pools reduce idle cost but increase queue-to-start latency. Model separately by workload class, peak arrival patterns, release criticality and cloud startup time. Image pre-pull/caching may reduce latency but requires security and storage controls.

## 8. Capacity and cost model

Illustrative workload:
- 90 jobs/hour, 10 minutes average duration → 15 offered concurrent jobs.
- At 70% target slot utilization → `ceil(15 / 0.70) = 22` compatible slots.
- At 2 vCPU and 3 GiB requested per job → 44 vCPU and 66 GiB requests before node/daemon overhead.

This is **not** a direct node count: bin-packing, pod density, topology, memory, CPU limits and burst distribution matter. Price compute, storage, egress and artifact retention with actual provider rates. Use bounded scale tests to validate queue p95.

## 9. Monitoring and SLOs

Track queue wait p95, agent request-to-ready p95, pod Pending reasons, image-pull errors, node provisioning p95, executor utilization, infrastructure-caused build failures, spot interruption rate and cost per successful build. Alert on sustained SLO degradation and provisioning failures, not every transient Pending pod.

## 10. Autoscaling load test

1. Record controller/agent/node baseline and cluster quota.
2. Generate synthetic jobs with fixed CPU/memory and bounded arrival rate.
3. Measure cold start, steady state and burst scenarios.
4. Observe Kubernetes scheduling and autoscaler events.
5. Simulate reduced capacity in an isolated node pool.
6. Restore capacity; verify queue drain and representative builds.
7. Record cost, SLO performance and abort criteria.
8. Remove test agents and confirm no orphaned resources.

## 11. Troubleshooting scenarios

| # | Symptom | Root-cause candidates |
|---|---|---|
| 01 | No agent pod | Kubernetes plugin, RBAC |
| 02 | Pod Pending | quota, affinity, capacity |
| 03 | Autoscaler ignores pod | unsupported constraints |
| 04 | Node provisioning slow | cloud API/instance quota |
| 05 | Node launches but pod Pending | taints/IP/PVC |
| 06 | ImagePullBackOff | auth, digest, registry |
| 07 | Slow image pulls | large images/network |
| 08 | Agent remoting timeout | DNS/TLS/Java |
| 09 | Pod OOMKilled | memory sizing |
| 10 | Node disk pressure | image/cache/logs |
| 11 | Spot interruption | disruption handling |
| 12 | Active job killed on scale-down | drain policy |
| 13 | Workspace collision | shared PVC/path |
| 14 | Idle nodes persist | PDB/daemon/disruption |
| 15 | Agent cloud API 403 | service account RBAC |
| 16 | Build AWS/Azure access denied | workload identity |
| 17 | CNI IP exhaustion | subnet/IP capacity |
| 18 | Pod count limit reached | kubelet/cloud limits |
| 19 | Queue backlog with idle agents | label mismatch |
| 20 | Cloud spend spike | retry storm/overprovision |

## 12. Six production runbooks

### A. Agent provisioning outage
Check queue, Jenkins Kubernetes plugin logs, service account RBAC, API connectivity and pod creation; repair least privilege; validate request-to-ready and clean build.

### B. Pending pods and autoscaler stall
Inspect scheduler events, requests, quota, affinity, taints, PVC, autoscaler logs and cloud quotas; restore compatible capacity; verify p95 queue recovery.

### C. Image pull or remoting failure
Validate pinned digest, registry credentials, DNS/TLS, Java and remoting configuration; repair approved image/identity; test startup and cleanup.

### D. Capacity and cost spike
Identify arrival burst, retries, orphaned pods and idle nodes; apply safe concurrency limits and scale-down policy; measure cost and SLO impact.

### E. Spot/preemptible interruption
Inspect termination notice and build interruption; use retry for safe idempotent jobs; route critical release work to reliable pool; validate no artifact corruption.

### F. Node pool disruption
Check drain/consolidation policy and active builds; pause disruptive changes, restore capacity, recover affected jobs and validate cleanup.

## 13. Acceptance checklist

- [ ] Two-stage scaling architecture explained.
- [ ] Pod template tested with pinned image and least privilege.
- [ ] Scheduling/quota/IP constraints validated.
- [ ] Agent and node provisioning p95 measured.
- [ ] Cold and warm capacity compared.
- [ ] Burst test bounded and recoverable.
- [ ] Spot/disruption risk documented.
- [ ] Cost per successful build estimated.
- [ ] Queue/agent SLO and alert ownership defined.
- [ ] Rollback and cleanup verified.

**Companion:** [Chapter 077 hands-on lab](labs/077-jenkins-kubernetes-agent-autoscaling-dynamic-provisioning-capacity-optimization-check.md).  
**Next:** Chapter 078 — Jenkins High Availability, Workload Isolation and Controller Reliability Engineering.
