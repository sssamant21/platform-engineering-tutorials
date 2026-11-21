# Chapter 005 — Machine API, MachineSets and Safe Node Operations

**Audience:** OCP administrators, platform SREs and DBREs  
**Duration:** ~60 minutes | **Baseline:** Red Hat OpenShift Container Platform 4.22  
**Status:** Drafted; not runtime validated

## Learning outcomes

Explain the relationship between Machines, MachineSets and Nodes; distinguish installer-provisioned from user-provisioned infrastructure; inventory worker capacity; diagnose an unhealthy Machine without changing cluster state; and design a safe maintenance plan that protects stateful workloads.

**Prerequisite:** Chapters [003](003-ocp-control-plane-rhcos-crio-and-nodes.md) and [004](004-cluster-operators-cvo-and-update-state.md). General Kubernetes node lifecycle is covered in [Kubernetes Chapter 047](../../../kubernetes/chapters/047-cordon-drain-and-node-maintenance.md).

## 1. Machine API architecture and scope

A **Node** is the Kubernetes representation of a compute host. A **Machine** is a declarative infrastructure resource, when supported, representing a host/VM that should exist. A **MachineSet** manages a desired number of Machines, broadly analogous to how ReplicaSets manage pods. The **Machine API Operator** provides Machine API components in supported configurations.

Not all OpenShift installations use the Machine API to manage worker nodes. On user-provisioned infrastructure, bare-metal or other configurations, machinesets might be absent or managed differently. **Never infer that a Node is safe to delete because no Machine object matches it.**

| Object | Main purpose | Typical scope |
| --- | --- | --- |
| `nodes` | Kubernetes host status, capacity and pod placement | Cluster |
| `machines.machine.openshift.io` | Provisioning state and infrastructure mapping | `openshift-machine-api` |
| `machinesets.machine.openshift.io` | Desired Machine replica management | `openshift-machine-api` |
| `machinehealthchecks.machine.openshift.io` | Optional remediation rules | `openshift-machine-api` |
| `machineconfigpools` | OS configuration rollout across node pools | Cluster |

MachineSet availability, autoscaling support and provider details are platform-specific. Control-plane Machine management must not be assumed equivalent to worker MachineSet management.

## 2. Before any diagnosis

Verify your cluster identity, access and recent change window. These commands do not mutate cluster state:

```bash
oc whoami
oc config current-context
oc whoami --show-server
oc get clusterversion
oc get clusteroperators machine-api
oc auth can-i list machines.machine.openshift.io -n openshift-machine-api
oc auth can-i list machinesets.machine.openshift.io -n openshift-machine-api
oc auth can-i get nodes
```

The Machine API Operator or resources may be absent on the target topology; document this as **not applicable** rather than declaring the cluster unhealthy. `oc auth can-i` evaluates effective permissions but does not grant them.

## 3. Read-only inventory

```bash
oc get nodes -o wide
oc get machines -n openshift-machine-api -o wide
oc get machinesets -n openshift-machine-api
oc get machinehealthchecks -n openshift-machine-api
oc get machineconfigpools
oc get events -n openshift-machine-api --sort-by=.lastTimestamp
```

If `machines` or `machinesets` is unsupported or forbidden, capture the exact error and verify infrastructure model and RBAC with the platform owner. Do not use cluster-admin credentials just to make the exercise pass.

To inspect a specific Machine without modifying it:

```bash
oc describe machine <machine-name> -n openshift-machine-api
oc get machine <machine-name> -n openshift-machine-api -o yaml
oc describe node <node-name>
oc get pods -A --field-selector spec.nodeName=<node-name>
```

**Security:** Machine YAML may contain provider IDs, infrastructure identifiers or other sensitive metadata. Sanitize evidence before sharing. Never collect Secrets as part of this lab.

## 4. Diagnose discrepancies

| Symptom | Investigation | Avoid |
| --- | --- | --- |
| Machine `Provisioning` for too long | Machine conditions/events, cloud quotas, infrastructure credentials and provider health | Repeatedly deleting the Machine |
| Machine `Failed` | Provider error, quotas, image, network, IAM, bootstrap and remediation events | Assuming the Node can be removed |
| Node `NotReady` while Machine exists | Node conditions, kubelet/network/OS health and Machine state | Rebooting before checking workload placement |
| MachineSet desired differs from available | Check scaling changes, provisioning, capacity and MachineHealthChecks | Blindly increasing replicas |
| Node exists but Machine absent | Check installation model and infrastructure ownership | Treating absence as an automatic defect |
| MachineConfigPool updating/degraded | Inspect MCP and related nodes; check for active upgrade | Manual OS edits or forced configuration changes |

**Important:** A Machine's `Running` phase does not guarantee that its Node is `Ready`, and a Ready Node does not by itself establish storage/application health.

## 5. Node maintenance decision gates (plan only)

This chapter does **not** instruct you to execute a production drain. A separate approved maintenance procedure must validate:

1. **Cluster state:** control-plane and etcd quorum, Cluster Operators, upgrade state, MachineConfigPools, capacity and incident activity.
2. **Workload resilience:** node role, critical DaemonSets, replicas, anti-affinity, topology spread, PodDisruptionBudgets and any local storage.
3. **DBRE impact:** Kafka partition replicas/ISR, PostgreSQL leader/replica roles and replication lag, Redis persistence/replication, PV access modes and CSI attachment.
4. **Drain feasibility:** sufficient destination capacity, tolerations, taints, resource requests, eviction behavior and graceful termination times.
5. **Approval:** named platform, application and DBRE owners, maintenance window, user impact, monitoring, rollback criteria and escalation contacts.

**Reference only — do not execute without approval:**

```bash
# STATE-CHANGING EXAMPLES — NOT PART OF THIS LAB
# oc adm cordon <node-name>
# oc adm drain <node-name> --ignore-daemonsets
# oc adm uncordon <node-name>
```

Drain may block on PodDisruptionBudgets or unmanaged pods. Do not add `--force`, `--delete-emptydir-data`, or disable eviction as a workaround without explicit data-loss and application-owner assessment. A successful drain does not mean a database has successfully failed over.

## 6. Lab and assessment

Complete [Lab 005 — Machine and Node Inventory](../labs/005-machine-api-node-inventory.md). Use [Machine API and Node Triage](../runbooks/machine-api-node-triage.md) for an incident-ready investigation template.

**Acceptance:** Identify topology, match Machines to Nodes where supported, explain any discrepancy, document one simulated node failure, and produce a maintenance go/no-go assessment without executing changes. Runtime evidence and independent review remain pending.

## Official references

- [OpenShift 4.22: Machine management](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/machine_management/index)
- [OpenShift 4.22: Nodes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/nodes/index)
- [OpenShift 4.22: Machine Config Operator](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/machine_configuration/index)
