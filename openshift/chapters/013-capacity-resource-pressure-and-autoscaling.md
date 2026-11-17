# 013 — Capacity, Resource Pressure and Autoscaling (OCP 4.22)

**Audience:** Platform administrators, SREs and DBREs. **Duration:** ~60 minutes (15 theory, 30 read-only lab, 15 review). **Status:** Draft; not cluster-tested or production-approved.

## Outcomes and prerequisites

Distinguish CPU/memory requests from actual usage, calculate schedulable headroom, interpret node pressure and Pending pods, and identify whether Cluster Autoscaler/MachineAutoscaler and workload HPA are applicable. Prerequisites: authorized `oc` session; known cluster identity and topology; read permissions for nodes, pods, events and namespaces; optional permission to inspect autoscaler APIs. Follow [Kubernetes fundamentals](../../kubernetes/README.md) for generic scheduler/HPA theory.

**Before collecting evidence:** `oc whoami`; `oc config current-context`; `oc cluster-info` (do not publish token-bearing kubeconfig). Read-only access is not guaranteed: `oc auth can-i list nodes`, `oc auth can-i list pods --all-namespaces`; for a project, `oc auth can-i get pods -n <project>`. Do not request cluster-admin merely to complete the lab.

## OpenShift capacity model

- **Capacity** is physical node CPU/memory; **allocatable** is what the scheduler can assign after reservations. Compare total *requested* resources to allocatable, not raw hardware. Usage is a different signal and requires metrics availability.
- Headroom per node (requested-resource view) = allocatable − sum of scheduled pod requests. Aggregate only across nodes eligible for the same workload (labels, taints, affinity, topology and resource type); a cluster-wide sum does **not** prove any individual pod fits.
- Memory pressure, disk pressure, PID pressure, taints, unavailable nodes, PVC topology, quota and PodDisruptionBudgets can block scheduling or safe maintenance independently of CPU availability.
- `oc adm top nodes` and `oc adm top pods -n <project>` are point-in-time consumption samples, not requests or guaranteed historical trends. If metrics APIs are unavailable, use spec/status and observability dashboards; do not infer zero usage.
- OpenShift MachineAutoscaler and ClusterAutoscaler applicability depends on platform, Machine API and deployment topology. HPA changes workload replica count; cluster autoscaling changes eligible machine capacity. Neither guarantees database quorum or storage throughput.

## Read-only triage workflow

```sh
oc get nodes -o wide
oc describe node <node-name>
oc get pods -A --field-selector=status.phase=Pending
oc get events -A --sort-by=.metadata.creationTimestamp
oc get resourcequotas,limitranges -n <project>
oc get pdb -n <project>
oc adm top nodes
oc get clusterautoscalers.autoscaling.openshift.io
oc get machineautoscalers.autoscaling.openshift.io -A
oc get hpa -A
```

Commands can return `Forbidden`, `the server doesn't have a resource type`, or `Metrics API not available`; record the error and verify authorization/API availability rather than assuming a cluster defect. `oc describe node` exposes allocatable, allocated resources, conditions and scheduling taints; inspect only approved sanitized excerpts. PowerShell: the same `oc` commands work; avoid Unix `grep`/shell substitutions in shared lab scripts.

## Example interpretation (illustrative, not actual cluster output)

A Pending pod event `0/6 nodes are available: 3 Insufficient cpu, 3 node(s) had untolerated taint` shows two distinct placement constraints. Increasing an HPA maximum does not resolve either. Check pod requests, topology, eligible node pools, quotas and node taints before proposing capacity or scheduling changes.

For PostgreSQL/Kafka/Redis, preserve anti-affinity, zone placement, quorum, storage attach limits, disruption budgets and replication health. Do not scale stateful replicas, alter requests, drain nodes or remove taints as a diagnostic shortcut.

## Change and recovery gate

Read-only audit requires approved access. State changes (MachineAutoscaler limits, node scaling, requests/limits, HPA settings, taints, drain) require owner approval, change window, capacity/cost estimate, workload and storage impact assessment, baseline SLOs, rollback owner and explicit stop conditions. A rollback to old replica counts or MachineSet sizes is **not** guaranteed to restore evicted stateful data; validate recoverability before any action. Escalate scheduling policy to platform, application demand to application owners, data replication/quorum to DBRE, and cloud quota to infrastructure.

## Validation and references

Review [Lab 013](../labs/013-capacity-pressure-read-only-audit.md) and [capacity triage runbook](../runbooks/capacity-scheduling-autoscaling-triage.md). Content is drafted only: no live cluster execution, independent review or production certification.

- [Red Hat OCP 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [OpenShift Machine management](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/machine_management/index)
- [OpenShift Nodes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/nodes/index)
