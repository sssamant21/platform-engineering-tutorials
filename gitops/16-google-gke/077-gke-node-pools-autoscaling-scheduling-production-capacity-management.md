# Chapter 077 — GKE Node Pools, Autoscaling, Scheduling and Production Capacity Management

**Curriculum:** Enterprise GitLab CI/CD, Helm, GitOps and Argo CD  
**Part 16:** Google Kubernetes Engine (GKE)  
**Chapter:** 077 / 100  
**Audience:** SREs, Platform Engineers, Cloud Architects, FinOps and Kubernetes Administrators

> **Safety:** Execute labs in a dedicated, budget-controlled GKE Standard staging cluster. Regional node counts may multiply across zones. Scaling, node-pool deletion, taints, PodDisruptionBudget changes and upgrades can disrupt applications or incur significant costs. Use synthetic workloads and confirm project, cluster, region and node pool before modifying resources.

## 1. Objectives

By the end of this chapter, you can:

1. Design GKE Standard system and application node pools.
2. Compare GKE Standard and Autopilot capacity management.
3. Understand regional node count, zones, quotas and reservations.
4. Configure Cluster Autoscaler and workload autoscaling without conflicting ownership.
5. Use HPA, VPA and workload resource requests appropriately.
6. Control placement with selectors, affinity, taints, tolerations and topology spread.
7. Use Spot VMs safely for interruption-tolerant workloads.
8. Plan GPU and specialized workload capacity.
9. Perform controlled node maintenance, surge upgrades and PDB validation.
10. Diagnose Pending Pods, scale-up failures, evictions and cost anomalies.

## 2. Architecture

~~~text
GitLab CI -> protected GitOps MR -> Argo CD
                         |
                 Deployments / Jobs
                         |
             HPA / VPA recommendations
                         |
           Kubernetes scheduler
                         |
               Cluster Autoscaler
                         |
              GKE Standard pools
               /       |       \
          system    on-demand   spot/batch
           pool       apps        pool
               \       |       /
             regional GKE nodes
                         |
      Google Cloud quotas / reservations
                         |
       Monitoring / Logging / FinOps
~~~

**Responsibility boundary:** HPA changes workload replicas; Cluster Autoscaler changes node capacity; GKE node auto-provisioning can create pools under supported configurations; VPA may adjust resource recommendations or Pod requests depending on its mode. Avoid configuring independent systems to compete over the same scaling decisions.

## 3. Standard versus Autopilot

In Standard, platform teams design node pools, machine types, upgrade strategy and autoscaling bounds. In Autopilot, GKE manages node provisioning based on workload requirements and supported platform constraints.

This chapter uses Standard for explicit node pool labs. For Autopilot, use supported workload resource specifications and validate the applicable scheduling, security and billing model; do not apply Standard node-pool commands to Autopilot.

## 4. Regional capacity math

For regional node pools, distinguish total nodes from per-zone counts. The behavior of CLI/Terraform node_count and autoscaling min/max can depend on the configuration and whether total min/max options are used.

**Example:** Three zones with two nodes per zone means six nodes, not two. Validate the actual node pool size with GKE and Compute Engine inventory before forecasting cost.

~~~bash
gcloud config get-value project
gcloud container clusters list --project PROJECT_ID
gcloud container node-pools list \
  --cluster gke-staging --region REGION --project PROJECT_ID
kubectl get nodes -L topology.kubernetes.io/zone,cloud.google.com/gke-nodepool
~~~

## 5. System and user pool strategy

Use reliable on-demand capacity for critical platform controllers (Argo CD, ingress, observability and security components) where supported. Separate application pools by resource profile, availability and lifecycle.

Apply node affinity or taints only with matching scheduling rules. A tainted system pool with no tolerations for critical controllers can make the platform unavailable.

## 6. Node sizing

Select machine families using CPU, memory, network, storage and cost needs. Compute allocatable resources rather than assuming all VM CPU/RAM is available to Pods. Reserve headroom for kubelet, system daemons, CNI, CSI, monitoring and rollout surge.

~~~bash
kubectl describe node NODE_NAME
kubectl top nodes
kubectl get pods -A -o wide
kubectl get --raw /metrics 2>/dev/null | head
~~~

The metrics-server and access to metrics may vary. Use Cloud Monitoring when direct Kubernetes metrics are unavailable.

## 7. Resource requests, limits and QoS

The scheduler uses requests to place Pods; actual usage can differ. CPU limits can throttle; memory limits can cause OOM kills. QoS classes affect eviction priority under resource pressure but do not replace SLO design.

~~~yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-api
  namespace: demo-staging
spec:
  replicas: 3
  selector:
    matchLabels: {app: demo-api}
  template:
    metadata:
      labels: {app: demo-api}
    spec:
      containers:
        - name: api
          image: REGION-docker.pkg.dev/PROJECT_ID/demo/api@sha256:REPLACE_WITH_DIGEST
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              memory: 512Mi
~~~

Pin a real digest and validate application behavior before setting CPU limits.

## 8. Cluster Autoscaler

GKE Cluster Autoscaler can add nodes when Pods cannot schedule and remove underutilized nodes when safe. It is constrained by node pool min/max, regional capacity, quota, scheduling constraints, PDBs and infrastructure availability.

~~~bash
gcloud container node-pools describe apps \
  --cluster gke-staging --region REGION --project PROJECT_ID \
  --format="yaml(autoscaling,locations,config.machineType)"
kubectl get events -A --sort-by=.lastTimestamp
~~~

Never rely on Cluster Autoscaler to fix invalid Pod selectors or unavailable volume topology.

## 9. Autoscaling Terraform ownership

Terraform should manage approved autoscaling configuration and pool policy without continuously resetting autoscaler-controlled current node count.

~~~hcl
resource "google_container_node_pool" "apps" {
  name     = "apps"
  cluster  = google_container_cluster.gke.name
  location = var.region

  autoscaling {
    min_node_count = 1
    max_node_count = 4
  }

  node_config {
    machine_type    = "e2-standard-4"
    service_account = google_service_account.nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  lifecycle {
    ignore_changes = [node_count]
  }
}
~~~

**Caution:** For regional pools, review per-zone versus total bounds and current Google provider semantics. This is an instructional fragment; pin provider versions and validate all required arguments.

## 10. HPA fundamentals

Horizontal Pod Autoscaler adjusts replicas using CPU, memory or supported custom/external metrics. CPU utilization scaling depends on valid resource requests and functioning metrics pipeline.

~~~yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: demo-api
  namespace: demo-staging
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: demo-api
  minReplicas: 3
  maxReplicas: 12
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
~~~

Do not run another controller or CI job that continually overwrites the Deployment replica count.

## 11. VPA fundamentals

Vertical Pod Autoscaler recommends or adjusts requests depending on its configured mode and installed components. Applying VPA changes may recreate Pods. Combining VPA and HPA on the same CPU/memory resource can create competing feedback loops.

Use recommendation-only VPA first for critical workloads and test interactions with HPA, PDBs and stateful storage.

## 12. Node auto-provisioning

GKE node auto-provisioning can create pools for unschedulable workloads under supported configurations. It needs clear resource limits, service accounts, machine family restrictions and workload scheduling design.

Do not assume it is enabled, available in all cluster modes, or appropriate for specialized workloads without testing.

## 13. Node selectors and affinity

~~~yaml
spec:
  nodeSelector:
    workload_tier: applications
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: cloud.google.com/gke-nodepool
                operator: In
                values: ["apps"]
~~~

The snippet is a PodSpec fragment. Verify the actual node labels before deployment. Hard constraints improve isolation but can block scaling during capacity shortages.

## 14. Taints and tolerations

~~~bash
kubectl taint nodes NODE_NAME workload=batch:NoSchedule
kubectl describe node NODE_NAME | grep -A2 Taints
~~~

Use disposable staging nodes only. Prefer node pool taints configured through approved infrastructure code, since manual node changes may be lost on replacement.

~~~yaml
tolerations:
  - key: workload
    operator: Equal
    value: batch
    effect: NoSchedule
~~~

Toleration permits placement but does not require it; combine with affinity where isolation is required.

## 15. Topology spread

~~~yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: demo-api
~~~

A strict topology rule can leave Pods Pending if an AZ lacks compatible capacity. Review minDomains support and placement behavior for your Kubernetes version.

## 16. PodDisruptionBudgets

~~~yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: demo-api
  namespace: demo-staging
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: demo-api
~~~

PDBs control voluntary evictions, not all outages. A restrictive PDB with insufficient healthy replicas can stall node upgrades and scale-down.

## 17. Spot VM pools

Spot VMs are interruptible and suited to stateless, retryable or checkpointed workloads. Do not place critical quorum systems or sole replicas on Spot without an explicit resilience design.

Use taints, tolerations, node affinity, priority classes and fallback capacity. Handle termination signals and verify jobs can restart without data loss.

## 18. GPU and specialized nodes

GPU workloads require supported accelerator machine types, regional quota, drivers, compatible GKE versions and correct Pod GPU resource requests. Validate device plugin/runtime integration and scheduling labels.

A Pod requesting GPU cannot be rescued by scaling a CPU-only pool. Cost controls should include scale-to-zero where supported, job timeouts and idle GPU alerts.

## 19. Storage topology and node scheduling

Zonal Persistent Disk volumes constrain Pod placement. VolumeBindingMode WaitForFirstConsumer helps align new PVC provisioning with scheduling. Existing bound PVs may prevent a workload from moving to another AZ.

For stateful workloads, combine topology, backup and recovery testing; replicas do not automatically make a single-writer disk portable.

## 20. Node upgrades and maintenance

Use approved GKE maintenance windows, release channels and node upgrade strategies. Check surge capacity, PDBs, stateful attachment, admission webhooks and controller compatibility.

~~~bash
gcloud container clusters describe gke-staging \
  --region REGION --project PROJECT_ID \
  --format="yaml(releaseChannel,maintenancePolicy)"
gcloud container node-pools describe apps \
  --cluster gke-staging --region REGION --project PROJECT_ID \
  --format="yaml(management,upgradeSettings,version)"
~~~

Never assume a failed control-plane upgrade can be rolled back by downgrading Kubernetes.

## 21. Capacity forecasting

Track per-node allocatable CPU/memory, p95/p99 workload utilization, Pending Pod time, HPA demand, autoscaler latency, storage/network saturation, zone quota and upgrade headroom.

Illustrative sizing formula:

~~~text
required_nodes =
  ceil(total_scheduled_cpu_requests / usable_cpu_per_node)
  adjusted upward for:
  - memory constraints
  - per-zone topology requirements
  - DaemonSet overhead
  - upgrade surge and failure tolerance
~~~

Do not size solely on aggregate CPU; scheduling is multidimensional and Pod placement constraints matter.

## 22. FinOps model

Account for regional node multiplicity, machine families, persistent disks, egress, load balancers, Cloud NAT, logging/metrics ingestion and GKE cluster fees where applicable.

Set budgets, resource labels, idle pool reviews and namespace chargeback. Savings from Spot or autoscaling should be measured against reliability and operational overhead.

## 23. Observability

~~~text
Kubernetes events + scheduler
            |
    Cluster Autoscaler logs
            |
Cloud Monitoring node/Pod metrics
            |
 HPA/VPA status and recommendations
            |
  Grafana capacity dashboards
            |
  SRE alerts and runbooks
~~~

Monitor Pending Pods, unschedulable reasons, node Ready, pool min/max saturation, evictions, OOMKills, CPU throttling, quota errors, GPU idle and cost trends.

## 24. GitOps ownership

Terraform owns node pool configuration, IAM, quotas and infrastructure policy. Argo CD owns approved Deployment/HPA/PDB/affinity manifests. Manual emergency changes require incident tracking and reconciliation back into Git.

Do not let HPA, Argo CD and Terraform independently fight over the same replica/node-count fields.

## 25. Lab A — Node pool baseline

1. Verify project, cluster and region.
2. List node pools and machine types.
3. Record zones and current node counts.
4. Inspect allocatable CPU/memory.
5. Map system and application Pods to pools.
6. Record hourly cost estimate.

**Pass:** node capacity inventory is accurate.

## 26. Lab B — Regional count and quota

1. Inspect node pool locations and per-zone counts.
2. Compare configured bounds to actual VMs.
3. Review Compute Engine regional quotas.
4. Model one-zone capacity loss.
5. Validate reserved headroom.
6. Document scale-up limits.

**Pass:** regional multiplicity and quota are understood.

## 27. Lab C — Terraform autoscaling bounds

1. Inspect approved Terraform node pool config.
2. Set safe min/max bounds in staging.
3. Run plan and review impact.
4. Apply through approved pipeline.
5. Verify autoscaling settings in GKE.
6. Confirm Terraform does not reset current autoscaled size.

**Pass:** infrastructure ownership does not conflict with autoscaler.

## 28. Lab D — HPA CPU scaling

1. Deploy synthetic app with CPU requests.
2. Apply autoscaling/v2 HPA.
3. Generate controlled CPU load.
4. Observe target utilization and replicas.
5. Stop load and observe stabilization.
6. Record scale latency.

**Pass:** HPA reacts predictably.

## 29. Lab E — Cluster Autoscaler scale-up

1. Record pool baseline.
2. Increase synthetic Pod replicas/requests.
3. Observe Pending scheduling events.
4. Confirm autoscaler adds compatible nodes.
5. Verify Pods become Ready.
6. Scale down and measure recovery.

**Pass:** scale-up works within approved quota.

## 30. Lab F — Unschedulable affinity

1. Deploy synthetic Pod with nonexistent node label.
2. Observe FailedScheduling event.
3. Confirm Cluster Autoscaler cannot fix invalid constraint.
4. Correct selector to approved pool.
5. Verify scheduling.
6. Record diagnosis.

**Pass:** constraint failure is distinguished from capacity shortage.

## 31. Lab G — Taints and tolerations

1. Create disposable tainted pool or test node.
2. Deploy Pod without toleration.
3. Confirm scheduling denial.
4. Add scoped toleration and matching affinity.
5. Verify placement.
6. Remove test resources.

**Pass:** isolation is explicit.

## 32. Lab H — Zone topology spread

1. Deploy three-replica synthetic app.
2. Configure zone spread constraint.
3. Verify AZ placement.
4. Simulate missing capacity in one test AZ.
5. Observe Pending behavior.
6. Restore capacity and confirm distribution.

**Pass:** availability tradeoffs are documented.

## 33. Lab I — PDB and controlled drain

1. Deploy healthy replicas.
2. Apply PDB minAvailable.
3. Test eviction behavior on disposable node.
4. Observe blocked drain if healthy replicas insufficient.
5. Restore replicas/capacity.
6. Verify safe drain.

**Pass:** PDB protects availability without indefinite maintenance blockage.

## 34. Lab J — Spot batch resilience

1. Create isolated Spot pool.
2. Deploy retryable synthetic Job with checkpoint.
3. Verify node affinity and toleration.
4. Simulate interruption using approved test method.
5. Confirm retry/fallback.
6. Review cost and completion time.

**Pass:** interruption does not lose job progress.

## 35. Lab K — VPA recommendation

1. Deploy synthetic app with resource requests.
2. Enable supported VPA recommendation mode.
3. Generate workload.
4. Review recommendations.
5. Compare with HPA configuration.
6. Record request adjustments for review.

**Pass:** resource tuning avoids conflicting autoscalers.

## 36. Lab L — GPU capacity planning

1. Review available accelerator SKU and regional quota.
2. Inspect GPU node pool labels and taints.
3. Validate GPU Pod resource requests.
4. Simulate unavailable accelerator capacity without provisioning costly GPU VMs.
5. Review Pending diagnostics.
6. Document GPU cost safeguards.

**Pass:** GPU scheduling requirements are understood without unnecessary spend.

## 37. Lab M — Zonal storage placement

1. Create disposable Persistent Disk PVC.
2. Deploy consuming Pod.
3. Record disk zone and node zone.
4. Simulate incompatible node affinity.
5. Inspect scheduler/CSI events.
6. Restore compatible placement and verify data.

**Pass:** disk topology is diagnosed safely.

## 38. Lab N — Node image upgrade rehearsal

1. Verify supported target image/version.
2. Inspect surge capacity and PDBs.
3. Approve staging node pool upgrade.
4. Observe cordon/drain/replacement.
5. Verify app readiness and storage.
6. Record disruption and forward repair.

**Pass:** node maintenance meets SLO.

## 39. Lab O — Capacity incident capstone

1. Deploy synthetic multi-tier workload.
2. Trigger CPU demand and constrained scheduling.
3. Simulate one quota or pool-bound limitation.
4. Correlate HPA, scheduler and autoscaler.
5. Restore bounds or placement through approved changes.
6. Measure recovery, cost and postmortem evidence.

**Pass:** capacity incident can be resolved without unsafe scaling.

## 40. Troubleshooting — eighteen scenarios

| # | Symptom | Likely cause | Safe response |
| --- | --- | --- | --- |
| 1 | Pod Pending | Insufficient requests capacity | Inspect scheduler |
| 2 | Autoscaler no scale-up | Pool max reached | Review bounds |
| 3 | Autoscaler no scale-up | Regional VM quota | Request quota/alternate SKU |
| 4 | Autoscaler no scale-up | Invalid node affinity | Fix placement |
| 5 | Pods stuck in one zone | Topology constraints | Restore AZ capacity |
| 6 | HPA unknown metrics | Metrics pipeline | Repair collection |
| 7 | HPA no scale | Missing CPU requests | Set realistic requests |
| 8 | HPA oscillation | Unstable load/targets | Tune stabilization |
| 9 | VPA/HPA conflict | Same resource control | Separate strategies |
| 10 | Node drain blocked | PDB/no healthy replicas | Restore capacity |
| 11 | Spot Job lost | Missing retry/checkpoint | Fix batch semantics |
| 12 | GPU Pod Pending | No GPU capacity/driver | Check accelerator pool |
| 13 | Disk-attached Pod Pending | Wrong AZ | Align placement |
| 14 | Node NotReady | Runtime/network/pressure | Inspect node |
| 15 | OOMKilled | Memory limit/workload | Profile and resize |
| 16 | CPU throttling | Low CPU limit | Tune resources |
| 17 | Unexpected cost spike | Regional count/idle pool | Audit capacity |
| 18 | Upgrade stalled | PDB/surge/quota | Restore headroom |

## 41. Runbook — Pending Pods and autoscaler failure

1. Confirm affected namespace, Deployment and Pod requests.
2. Inspect FailedScheduling events.
3. Review node selectors, taints, topology and PVC zone.
4. Check autoscaler logs, pool bounds and regional quota.
5. Restore compatible capacity or correct GitOps constraints.
6. Verify Pod Ready and application SLO.
7. Record cause and preventive alerts.

## 42. Runbook — node pool outage

1. Identify impacted pool, zones and nodes.
2. Check GKE operation and Compute Engine status.
3. Verify critical system controllers remain available.
4. Restore on-demand capacity and safe placement.
5. Confirm ingress, DNS, storage and workload readiness.
6. Measure RTO and cost.
7. Document RCA.

## 43. Runbook — HPA/VPA instability

1. Inspect HPA metrics, targets and replica history.
2. Compare requests/limits with measured usage.
3. Check metrics availability and VPA mode.
4. Remove conflicting automation through reviewed GitOps.
5. Tune stabilization and capacity headroom.
6. Verify steady-state SLO.
7. Record tuning rationale.

## 44. Runbook — Spot interruption and batch recovery

1. Identify affected Spot pool and Jobs.
2. Check Pod termination and retry events.
3. Verify checkpoint and idempotent processing.
4. Restore approved on-demand fallback if necessary.
5. Confirm output correctness and no duplicate side effects.
6. Review interruption frequency and savings.
7. Update workload placement policy.

## 45. Runbook — node upgrade stalled

1. Freeze concurrent changes.
2. Inspect GKE upgrade status and node pool settings.
3. Review PDBs, surge capacity, quota and unhealthy Pods.
4. Restore sufficient capacity without force-evicting stateful data.
5. Resume supported upgrade or plan forward repair.
6. Validate CSI, ingress and application SLO.
7. Document corrective actions.

## 46. Evidence template

~~~text
Change / incident ID:
GCP project, cluster, region:
GKE mode and Kubernetes version:
Node pool, machine type, zones:
Configured per-zone/total min and max:
Actual nodes and allocatable resources:
CPU/memory requests and observed usage:
HPA targets, replica history:
VPA recommendations:
Autoscaler and scheduler events:
Taints, affinity and topology constraints:
PDB and drain evidence:
Spot/GPU workload handling:
Persistent Disk topology:
Node upgrade status:
Measured recovery and cost:
GitLab/Argo CD revision and approver:
~~~

## 47. Scored readiness assessment

| Domain | Points | Evidence |
| --- | ---: | --- |
| Regional node pool architecture | 20 | AZ and capacity inventory |
| Cluster Autoscaler and quota | 20 | Scale-up/scale-down test |
| HPA/VPA resource management | 15 | Metrics and stability |
| Scheduling and disruption control | 20 | Affinity, topology, PDB |
| Spot/GPU and specialized workloads | 10 | Safe placement |
| Upgrade operations and incident response | 10 | Runbooks and rehearsal |
| FinOps and evidence | 5 | Cost review |
| **Total** | **100** | |

**Pass:** at least 85/100 and no critical failure: missing stable platform capacity, unbounded scaling cost, forced disruption of protected workloads, unsupported GPU/Spot placement for critical state or no capacity recovery path.

## 48. Final acceptance checklist

- [ ] GKE mode and regional node count semantics documented.
- [ ] System and application pools isolated appropriately.
- [ ] Per-zone capacity, quotas and headroom verified.
- [ ] Cluster Autoscaler bounds and Terraform ownership reviewed.
- [ ] HPA and metrics tested.
- [ ] VPA interaction reviewed.
- [ ] Resource requests/limits based on measurements.
- [ ] Taints, affinity and topology tested.
- [ ] PDB and drain behavior verified.
- [ ] Spot and GPU safeguards reviewed.
- [ ] Persistent Disk topology understood.
- [ ] Node upgrade rehearsal completed.
- [ ] Fifteen hands-on labs completed.
- [ ] Eighteen troubleshooting scenarios reviewed.
- [ ] Five production runbooks validated.
- [ ] Cost and operational evidence approved.

## 49. Knowledge check

1. How does regional node pool sizing affect cost?
2. What is the difference between HPA and Cluster Autoscaler?
3. Why can Cluster Autoscaler fail even with free quota?
4. Why are CPU requests important for CPU-based HPA?
5. When can VPA conflict with HPA?
6. How do taints differ from node affinity?
7. Why can strict topology spread leave Pods Pending?
8. What is a safe workload for Spot VMs?
9. Why can Persistent Disk topology block rescheduling?
10. How do PDBs affect GKE node upgrades?

## 50. References

- [GKE node pools](https://cloud.google.com/kubernetes-engine/docs/concepts/node-pools)
- [GKE Cluster Autoscaler](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-autoscaler)
- [GKE node auto-provisioning](https://cloud.google.com/kubernetes-engine/docs/how-to/node-auto-provisioning)
- [GKE Spot VMs](https://cloud.google.com/kubernetes-engine/docs/how-to/spot-vms)
- [GKE node upgrades](https://cloud.google.com/kubernetes-engine/docs/how-to/upgrade-nodes)
- [GKE GPU workloads](https://cloud.google.com/kubernetes-engine/docs/how-to/gpus)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Kubernetes node affinity](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [Kubernetes topology spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Kubernetes PodDisruptionBudget](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Kubernetes resource management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)

---

**Chapter 077 complete.** Next: **Chapter 078 — GKE Networking, Ingress, Gateway API and Persistent Storage Integration for GitOps**.