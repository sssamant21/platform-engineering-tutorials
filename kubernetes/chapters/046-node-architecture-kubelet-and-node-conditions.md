# Chapter 046 — Node Architecture, Kubelet and Node Conditions

**Track:** Kubernetes Administration · **Part 10 — Node Operations and Troubleshooting**  
**Status:** Draft — runtime validation and independent technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators and platform engineers  
**Prerequisites:** Chapters 006–010, 016–025 and 041–045; kubectl and Windows PowerShell; read access to nodes, Pods, events and Leases

## 1. Production scenario

During an application incident, one worker node reports `NotReady`. Some Pods remain in `Running`, while replacements are Pending. The on-call engineer must determine whether the issue involves kubelet, container runtime, API connectivity, node resource pressure or the underlying VM. The investigation must avoid unnecessary evictions and preserve forensic evidence.

**Goal:** understand the node control loop and build a reliable node-health investigation workflow before performing node maintenance in Chapter 047.

### Learning objectives

1. Describe the worker node architecture and kubelet responsibilities.
2. Read Node status, conditions, capacity, allocatable resources and taints.
3. Interpret node heartbeats and `kube-node-lease` Lease objects.
4. Correlate Node conditions with Pod placement, events and application health.
5. Distinguish CPU/memory/disk/PID pressure and their operational effects.
6. Identify kubelet, container runtime, CNI and cloud infrastructure failure domains.
7. Produce a node incident runbook with clear escalation and recovery criteria.

## 2. Worker node architecture

```text
                       Kubernetes control plane
                    API server / scheduler / controllers
                                  |
                         Node status + Lease
                                  |
+----------------------------- Worker Node ----------------------------+
| kubelet                                                             |
|  - watches assigned Pods                                            |
|  - coordinates container runtime through CRI                        |
|  - performs probes, mounts volumes and reports Pod/Node status      |
|                                                                      |
| containerd / CRI-O          CNI plugin            CSI node plugin   |
|  - image pulls                - Pod networking       - volume mounts |
|  - container lifecycle       - IP / routes / policy                  |
|                                                                      |
| OS / kernel / cgroups / filesystem / network / VM infrastructure    |
+----------------------------------------------------------------------+
```

The kubelet is the node agent responsible for making assigned Pods run according to their specifications. The scheduler chooses placement for unscheduled Pods; kubelet does **not** schedule Pods across nodes. Container runtimes implement the Container Runtime Interface (CRI). CNI configures Pod networking; CSI provides storage integration.

In managed Kubernetes, the provider may manage parts of node bootstrap, upgrades, certificates, autoscaling and infrastructure repair. The investigation workflow remains applicable, but host access and log collection differ.

## 3. Node conditions and meanings

| Condition | Healthy interpretation | Operational meaning when unhealthy |
|---|---|---|
| `Ready` | `True` | `False` or `Unknown` indicates node cannot reliably serve workloads |
| `MemoryPressure` | `False` | Kubelet detects memory pressure |
| `DiskPressure` | `False` | Node filesystem/image filesystem pressure |
| `PIDPressure` | `False` | Process ID exhaustion risk |
| `NetworkUnavailable` | Often `False` or absent | May indicate network not configured; behavior varies by CNI/provider |

A missing condition is not automatically equivalent to `False`. Read the actual status, reason, message and transition timestamp.

Kubernetes may add condition-related taints, including `node.kubernetes.io/not-ready`, `node.kubernetes.io/unreachable`, `node.kubernetes.io/memory-pressure`, `node.kubernetes.io/disk-pressure` and `node.kubernetes.io/pid-pressure`. Scheduling and eviction behavior depend on taint effects, tolerations, controller behavior and cluster configuration.

## 4. Lab prerequisites and safety

All core labs are **read-only** and safe for a cluster where you have observation permissions. Use an approved nonproduction cluster for any optional mutation. Do not restart kubelet, delete Nodes, drain workers or remove taints during the diagnostic labs.

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl auth can-i get nodes
kubectl auth can-i list leases.coordination.k8s.io -n kube-node-lease
```

Set a node name from the live cluster:

```powershell
$node = (kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
if ([string]::IsNullOrWhiteSpace($node)) { throw "No nodes found" }
"Selected node: $node"
```

**Expected:** a real node name is selected. In production, explicitly choose the affected worker instead of blindly using the first node.

## 5. Lab 1 — Inventory node architecture

```powershell
kubectl get node $node -o wide
kubectl describe node $node
kubectl get node $node -o jsonpath='{.status.nodeInfo.kubeletVersion}'
kubectl get node $node -o jsonpath='{.status.nodeInfo.containerRuntimeVersion}'
kubectl get node $node -o jsonpath='{.status.nodeInfo.osImage}'
kubectl get node $node -o jsonpath='{.status.nodeInfo.kernelVersion}'
kubectl get node $node -o jsonpath='{.spec.providerID}'
```

**Expected:** kubelet version, container runtime, OS, kernel and cloud provider identity are visible where populated. Record whether the node is Linux or Windows and whether the runtime is containerd or another CRI implementation.

### Interpretation

- Kubelet version skew matters during upgrades.
- Runtime version and OS image matter for CRI compatibility.
- Provider ID helps correlate Kubernetes Nodes with cloud instances.
- Node labels and topology identify zones, node pools and workload placement.
- A `Ready` Node can still have unhealthy applications or storage/network dependencies.

## 6. Lab 2 — Inspect node conditions, taints and transition times

```powershell
kubectl get node $node -o jsonpath='{range .status.conditions[*]}{.type}{"="}{.status}{" reason="}{.reason}{" transition="}{.lastTransitionTime}{"\n"}{end}'
kubectl get node $node -o jsonpath='{.spec.taints}'
kubectl describe node $node
```

**Expected:** Node condition statuses and reasons can be inspected alongside taints and events.

### Troubleshooting logic

- `Ready=False`: kubelet may be reporting unhealthy runtime/network conditions.
- `Ready=Unknown`: the control plane may not be receiving timely heartbeats.
- `MemoryPressure=True`: inspect working set, eviction thresholds and memory requests/limits.
- `DiskPressure=True`: inspect image garbage collection, logs, ephemeral storage and filesystem capacity.
- `PIDPressure=True`: inspect runaway processes and PID limits.

**Do not remove condition taints to hide a real problem.** Identify and remediate the underlying failure.

## 7. Lab 3 — Inspect kubelet heartbeats and Node Leases

Kubelet reports node status and updates a lightweight Lease in `kube-node-lease`. Lease renewals are a key signal used by node-health monitoring, but they are not an application-level health check.

```powershell
kubectl -n kube-node-lease get leases
kubectl -n kube-node-lease get lease $node -o yaml
kubectl -n kube-node-lease get lease $node -o jsonpath='{.spec.renewTime}'
kubectl get node $node -o jsonpath='{.status.conditions[?(@.type=="Ready")].lastHeartbeatTime}'
```

**Expected:** a Lease with a recent `renewTime` when node communication is healthy. Access to Leases may be restricted by RBAC.

### Interpretation

A stale Lease can indicate kubelet failure, network partition, API server reachability problems or control-plane issues. Correlate it with the Node's Ready condition and the health of other nodes. Do not conclude kubelet has crashed from one stale timestamp alone.

If all nodes show stale Leases, investigate API server availability and broader network/control-plane health before treating each worker as an independent failure.

## 8. Lab 4 — Compare capacity, allocatable and requested resources

```powershell
kubectl get node $node -o jsonpath='{.status.capacity}'
kubectl get node $node -o jsonpath='{.status.allocatable}'
kubectl describe node $node
kubectl top node $node
```

**Expected:** `capacity` reflects physical/logical node resources, while `allocatable` excludes resources reserved for the OS, kubelet and eviction headroom. The `Allocated resources` section of `kubectl describe node` shows requests and limits; it is not actual consumption.

`kubectl top` requires a working Metrics Server or equivalent metrics API. If unavailable, use approved Prometheus, cloud monitoring or node metrics; do not assume resource utilization is zero.

### Diagnostic matrix

| Metric | Source | Interpretation |
|---|---|---|
| Capacity | Node status | Total reported node resources |
| Allocatable | Node status | Resources available for scheduling |
| Requests | Pod specifications | Scheduler reservation |
| Limits | Pod specifications | Enforcement/upper bound, where applicable |
| Usage | Metrics Server/monitoring | Current observed consumption |
| Eviction signals | kubelet/Node conditions | Pressure thresholds and node protection |

High CPU usage does not automatically imply `Ready=False`. Memory and ephemeral-storage pressure may trigger kubelet evictions, and a node can be `Ready=True` while applications suffer latency.

## 9. Lab 5 — Correlate node health with assigned Pods

```powershell
kubectl get pods -A --field-selector spec.nodeName=$node -o wide
kubectl get pods -A --field-selector spec.nodeName=$node --no-headers
kubectl get events -A --sort-by=.lastTimestamp
kubectl describe node $node
```

**Expected:** Pods scheduled to the selected node are listed, including system agents where visible. Inspect their phases, restarts, readiness and recent events.

### Incident correlation

- Many Pods on one node fail simultaneously: investigate shared node, network, disk or runtime dependencies.
- One Pod fails while others remain healthy: investigate the application's image, probes, configuration, limits and dependencies first.
- Replacement Pods stay Pending: inspect scheduler events, taints, affinity, topology, PVC constraints and resource requests.
- Pods are Running but service requests fail: check readiness, endpoints, CNI, DNS, NetworkPolicies and upstream services.

Do not use Pod phase alone as a service-health SLI. Validate application traffic and error rates.

## 10. Lab 6 — Distinguish node fault domains

Use the following **read-only** evidence collection:

```powershell
kubectl get nodes -o wide
kubectl get node $node -o yaml
kubectl get pods -A --field-selector spec.nodeName=$node -o wide
kubectl -n kube-node-lease get lease $node -o yaml
kubectl get events -A --sort-by=.lastTimestamp
```

### Fault isolation decision table

| Symptom | Candidate fault domain | Additional evidence |
|---|---|---|
| Lease stale, Ready Unknown | Kubelet/API connectivity | Cloud instance/network, kubelet logs |
| Lease fresh, Ready False | Kubelet-reported node problem | Condition reason/message, runtime |
| Pods stuck ContainerCreating | Runtime/CNI/CSI/image pull | Pod events, CRI/CNI/CSI logs |
| DiskPressure True | Node storage | Filesystem usage, image/log growth |
| MemoryPressure True | Node memory | Working set, OOM/eviction events |
| PIDPressure True | Process exhaustion | PID usage, process count |
| All nodes affected | Control plane/network/provider | API server and infrastructure health |
| Only one app affected | Application or workload config | Probes, logs, dependencies |

**Optional host-level checks (authorized node access only):**

Linux systemd-based workers:

```bash
sudo systemctl status kubelet
sudo journalctl -u kubelet --since "30 minutes ago" --no-pager
sudo systemctl status containerd
sudo journalctl -u containerd --since "30 minutes ago" --no-pager
df -h
df -i
free -h
```

Not all clusters use `containerd`, systemd or SSH-accessible nodes. On EKS/AKS/GKE, use approved provider diagnostics, managed logging and node pool tools. Do not restart services as a first diagnostic action.

## 11. Lab 7 — Node incident tabletop and acceptance

**Scenario:** A single worker reports `Ready=Unknown`. Lease renewal is stale, several application Pods on the worker are unavailable, and replacement Pods are Pending. A team member suggests deleting the Node object immediately.

### Required response

1. Confirm cluster context, incident window, affected node and business impact.
2. Check whether other nodes and Leases are healthy.
3. Capture the selected Node's conditions, taints, Lease and events.
4. Inventory Pods and their owners, especially StatefulSets, DaemonSets and local-storage workloads.
5. Determine whether the worker VM is reachable and whether kubelet/CRI is running.
6. Investigate scheduling failures for replacement Pods.
7. Check PodDisruptionBudgets, topology, storage attachments and node group capacity before maintenance.
8. Decide whether to wait, escalate to infrastructure, or execute an approved recovery plan.
9. Validate application-level SLIs after recovery.

**Do not delete the Node object or force-delete Pods simply because the node is NotReady.** In a network partition, the underlying machine may still be running workloads; premature force deletion can create duplicate writers or storage consistency risks.

### Acceptance evidence

| Requirement | Evidence |
|---|---|
| Node architecture identified | Kubelet, runtime, OS and provider |
| Conditions interpreted | Ready and pressure statuses |
| Heartbeat checked | Lease renewTime and status |
| Capacity understood | Capacity, allocatable, requests, usage |
| Pod blast radius mapped | Pods assigned to affected node |
| Failure domain narrowed | Kubelet, runtime, network, storage or cloud |
| Recovery decision justified | Risk assessment and approval |
| Service restored | Application readiness and transaction SLIs |

## 12. Node conditions versus eviction and scheduling

Kubernetes may apply condition-based taints, and the node controller can react to missed heartbeats. Pods can tolerate certain taints for a period; DaemonSets and critical system workloads may have special tolerations.

Important operational distinctions:

- **Cordon** marks a node unschedulable for ordinary new Pods; it does not evict existing Pods.
- **Drain** requests eviction/deletion of workloads subject to flags, controller ownership and disruption protections.
- **Eviction due to resource pressure** is kubelet-driven and differs from an administrator-initiated drain.
- **Node unreachability** may cause controller-managed Pod replacement after configured delays; timing is not guaranteed to be immediate.
- **Force deletion** of a Pod on an unreachable node does not prove its process stopped.

Chapter 047 will cover controlled cordon/drain, PodDisruptionBudgets and maintenance execution.

## 13. Production node-health runbook

### Detect

Monitor Node Ready state, Lease freshness, kubelet health, container runtime errors, filesystem capacity, memory pressure, PID pressure, Pod restarts, eviction events and unschedulable workloads.

### Triage

1. Identify affected node, node pool, zone, workloads and service impact.
2. Compare neighboring nodes and control-plane health.
3. Read conditions, taints, transition times and Lease renewals.
4. Correlate events, Pod failures and scheduling constraints.
5. Collect cloud VM/network/storage and kubelet/runtime evidence.
6. Decide whether a safe workload migration is possible.

### Recover

Choose a recovery path based on the verified fault domain: fix network/API connectivity, restore runtime/kubelet, resolve disk pressure, add capacity, or perform approved node replacement. Respect workload disruption budgets and stateful storage safety. Avoid manual edits to kubelet configuration without a documented change plan.

### Validate

Require healthy Node conditions, fresh Lease renewal, expected Pod placement, no continuing eviction/restart surge, recovered application transactions and stable monitoring. Record actual detection and recovery times.

## 14. Troubleshooting matrix

| Symptom | Likely cause | Next action |
|---|---|---|
| Node NotReady | Kubelet, CRI, network or OS issue | Conditions, Lease, provider metrics |
| Ready Unknown | Missed heartbeat | Lease, API reachability |
| DiskPressure | Node filesystem/image pressure | Disk usage, logs, GC, eviction |
| MemoryPressure | Low available memory | Memory metrics, OOM, requests |
| PIDPressure | PID exhaustion | Host process metrics |
| Pods Pending | Taints, resources, affinity or PVC | Scheduler events |
| ImagePullBackOff | Registry/network/auth | Pod events and runtime logs |
| ContainerCreating | CNI/CSI/runtime | Pod events, node agents |
| Node healthy, app down | Application/dependency failure | Probes, traces, endpoints |

## 15. Cleanup

The core labs are read-only and create no Kubernetes resources. Remove any local incident evidence only according to your organization's retention policy. Do not delete Nodes, Leases, Pods or system DaemonSets as cleanup.

## 16. Acceptance checklist

- [ ] Node components and kubelet responsibilities explained.
- [ ] Node OS, runtime, kubelet and provider metadata inspected.
- [ ] Node conditions and taints interpreted.
- [ ] Node Lease and heartbeat behavior reviewed.
- [ ] Capacity, allocatable, requests and usage distinguished.
- [ ] Assigned Pod blast radius inventoried.
- [ ] Node fault domains classified without disruptive actions.
- [ ] Stateful and storage risks considered before recovery.
- [ ] Node incident report and validation evidence produced.
- [ ] Runtime lab validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 17. References

- [Kubernetes Nodes](https://kubernetes.io/docs/concepts/architecture/nodes/)
- [Node Status](https://kubernetes.io/docs/reference/node/node-status/)
- [Kubelet](https://kubernetes.io/docs/reference/command-line-tools-reference/kubelet/)
- [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
- [Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Lease API](https://kubernetes.io/docs/concepts/architecture/leases/)

**Next:** Chapter 047 — Cordon, Drain and Node Maintenance.
