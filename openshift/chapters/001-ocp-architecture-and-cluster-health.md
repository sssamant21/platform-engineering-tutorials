# Chapter 001 — OpenShift Architecture and Cluster Health

**Track:** Platform Engineering > OpenShift Administration  
**Audience:** Beginner OCP administrator / SRE / DBRE  
**Estimated duration:** 60 minutes  
**Environment:** Authorized OCP 4.x cluster with appropriate *read-only* permissions; Red Hat 4.22 documentation baseline.  
**Status:** Documentation drafted; live lab not yet executed.

## Learning objectives

By the end, you can distinguish an OpenShift control plane from workers, explain what Cluster Operators and Machine Config Pools do, use `oc` to identify the target cluster, and collect read-only health evidence without changing its state.

## 1. OpenShift architecture

OpenShift is a supported Kubernetes distribution with a coordinated platform lifecycle. Core components include:

| Component | Administrator concern |
| --- | --- |
| Kubernetes API server | API availability, admission/authentication, control-plane access |
| etcd | Cluster state and quorum; platform-level backup/recovery |
| Scheduler/controllers | Pod placement and workload reconciliation |
| Red Hat Enterprise Linux CoreOS (RHCOS) | Node OS lifecycle and managed configuration |
| CRI-O | Container runtime on RHCOS nodes |
| Cluster Version Operator (CVO) | Cluster release payload and managed Cluster Operators |
| Cluster Operators | Health and lifecycle of platform capabilities |
| Machine Config Operator / Pools | Managed node configuration and rollout status |
| Worker nodes / pods | Application readiness, resources and disruption exposure |

**Important distinction:** Cluster Operators delivered with OCP and managed by the CVO are not the same thing as optional add-on Operators installed through Operator Lifecycle Manager (OLM).

**Architecture path:** Administrator → OpenShift API → control-plane reconciliation → worker-node workloads and managed cluster services.

## 2. Privileges and safe access

Use a workstation with the version-compatible `oc` CLI and a legitimate cluster login. Do not paste access tokens into examples, shell history or screenshots. The examples below are read-only and may still be forbidden under RBAC; permission errors should be reported, not bypassed.

```bash
oc version --client
oc login https://api.example.com:6443
oc whoami
oc config current-context
oc whoami --show-server
oc auth can-i get nodes
oc auth can-i get clusteroperators
```

`oc login` should be interactive and should use an endpoint supplied by your platform team; never disable TLS verification casually. Verify the context before running *any* operational command.

## 3. Read-only cluster audit

```bash
# Platform version and update condition
oc get clusterversion
oc describe clusterversion version

# Cluster-level Operators
oc get clusteroperators

# Nodes and OS/configuration rollouts
oc get nodes -o wide
oc get machineconfigpools

# Application and system workloads
oc get pods -A

# Cluster events (may be verbose)
oc get events -A --sort-by=.lastTimestamp

# Resource utilization requires operational metrics and authorization
oc adm top nodes
```

Use `oc get` to gather current conditions, then `oc describe` for the specific object that appears unhealthy. A pod in `Completed` state may be healthy for a Job. A cluster upgrade can legitimately cause a temporary `Progressing=True` or a MachineConfigPool to update. Always assess lifecycle context.

## 4. Interpretation checklist

| Signal | Typical steady-state expectation | Follow-up if different |
| --- | --- | --- |
| ClusterVersion | `Available=True`, `Progressing=False` | Review version conditions and planned changes |
| Cluster Operators | `AVAILABLE=True`, `PROGRESSING=False`, `DEGRADED=False` | Describe affected Operator; check its related pods/logs |
| Nodes | Expected worker/control-plane nodes `Ready` | Describe the node; inspect conditions, pressure and events |
| MachineConfigPools | `UPDATED=True`, `UPDATING=False`, `DEGRADED=False` | Investigate pending configuration and node rollout |
| Pods | Expected replicas healthy; no unexplained restarts | Identify namespace, owner, events and recent changes |
| Resource usage | Headroom according to organization policy | Correlate CPU/memory with limits, reservations and trends |

Do not treat the table as universal: upgrades, maintenance, scheduling constraints and cluster topologies alter expected conditions.

## 5. Troubleshooting scenario: one worker is NotReady

**Do not drain, reboot, delete or restart anything during this initial investigation.**

```bash
oc get nodes
oc describe node <node-name>
oc get pods -A --field-selector spec.nodeName=<node-name>
oc get events -A --sort-by=.lastTimestamp
```

Look for `Ready`, `MemoryPressure`, `DiskPressure`, `PIDPressure`, kubelet and networking conditions, scheduled workloads, storage dependencies, and recent maintenance. If the issue might affect stateful workloads, inspect replica placement, PV/PVC attachment, disruption budgets and recovery responsibilities before suggesting action.

## 6. Evidence and acceptance

Complete the dedicated [Lab 001](../labs/001-read-only-cluster-health-audit.md). Capture the following in an internal evidence store:

- Sanitized cluster identifier and exact OCP version;
- Identity and current context (never a token);
- ClusterVersion and Cluster Operator health;
- Node and MachineConfigPool health;
- Count and classification of failing pods;
- Findings, unknowns and escalation owner.

**Completion is not assumed.** This written chapter requires a real authorized test and technical review before being marked verified.

## Production safety

This chapter contains no state-changing administration commands. Later chapters on MachineSets, draining, upgrades, SCC/RBAC changes, etcd recovery or storage mutation must use a non-production lab first and an approved change procedure for production.

## Official references

- [OCP 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [Cluster Operators](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/observability/operators/index)
- [Node health troubleshooting](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/support/troubleshooting)
- [Overview of nodes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/nodes/overview-of-nodes)
