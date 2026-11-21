# Chapter 003 — OpenShift Control Plane, RHCOS, CRI-O and Node Architecture

**Track:** Platform Engineering / OpenShift Administration  
**Audience:** OCP administrators, SREs and DBREs  
**Duration:** 60 minutes (15 min concepts, 30 min read-only lab, 15 min triage and evidence)  
**Baseline:** OpenShift Container Platform 4.22; confirm the installed cluster's actual release and topology.  
**Status:** Draft only; not executed or independently reviewed.

## Objectives

1. Identify control-plane and worker-node roles in the real cluster.
2. Explain how the Kubernetes API, etcd, scheduler and controllers relate to OpenShift platform Operators.
3. Understand Red Hat Enterprise Linux CoreOS (RHCOS), Ignition, CRI-O, kubelet and Machine Config Operator (MCO) responsibilities.
4. Trace a node from its API object to its MachineConfigPool without modifying configuration.
5. Distinguish read-only inspection from privileged node-debug or configuration operations.

For generic Kubernetes architecture and etcd concepts, refer to [Kubernetes Chapter 004](../../kubernetes/chapters/004-control-plane-worker-nodes-and-etcd.md). This chapter focuses on **OpenShift-specific operational surfaces**.

## 1. Production architecture and responsibility boundaries

Typical OpenShift control-plane nodes host components that implement cluster state and reconciliation. Worker nodes run scheduled workloads. Compact, single-node, hosted-control-plane and provider-managed topologies differ; **do not assume a three-control-plane / three-worker deployment**.

| Component | Function | Operator diagnostic surface |
| --- | --- | --- |
| kube-apiserver | Authenticated cluster API | `oc get clusteroperator kube-apiserver` |
| etcd | Durable cluster state, quorum-sensitive | `oc get clusteroperator etcd` |
| scheduler and controller-manager | Placement and reconciliation | Related Cluster Operators and control-plane pod health |
| CVO (Cluster Version Operator) | Manages release and platform Operator lifecycle | `oc get clusterversion`, `oc get clusteroperators` |
| RHCOS | OpenShift node operating system on standard supported installations | Node OS image, node conditions and MachineConfigPool status |
| CRI-O | Container runtime integrated with kubelet | Node runtime version and kubelet/node symptoms |
| MCO | Reconciles managed OS and kubelet-related configuration | `oc get machineconfigpools`, Machine Config Operator condition |
| Machine API (when installed) | Infrastructure-backed machine lifecycle | Machine/MachineSet objects; not universally present |

**Key distinction:** A Kubernetes `Node` is not the same resource as a Machine API `Machine`; a MachineConfigPool describes managed node configuration convergence, not the availability of a particular application. Do not conflate CVO-managed Cluster Operators with OLM-installed add-on Operators.

RHCOS is designed for cluster-managed operation. Ignition provisions first-boot configuration; ongoing supported node configuration changes normally use MachineConfig and other supported OpenShift APIs. Manual host changes can be overwritten or conflict with reconciliation.

## 2. Preflight: identity, version, authorization

All commands in this chapter after an existing authorized login are read-only. Confirm your target cluster from an independent inventory.

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc get clusterversion
oc auth can-i list nodes
oc auth can-i list machineconfigpools.machineconfiguration.openshift.io
oc auth can-i list pods -n openshift-kube-apiserver
```

`no` from `oc auth can-i` is a legitimate result; do not grant yourself broader roles or substitute emergency credentials. The sample commands require cluster-level visibility and may be restricted.

## 3. Inspect nodes, roles and runtime

```bash
oc get nodes -o wide
oc get nodes --show-labels
oc describe node <approved-node-name>
```

Inspect `ROLES`, `STATUS`, `VERSION`, `OS-IMAGE`, `CONTAINER-RUNTIME` and `KERNEL-VERSION` from `-o wide` where shown. Node roles come from labels; topology-specific roles may include `master`, `control-plane`, `worker`, `infra`, or other configured labels. Never assume an arbitrary label is proof of workload placement.

For a more focused view:

```bash
oc get node <approved-node-name> -o jsonpath='{.status.nodeInfo.osImage}{"\n"}{.status.nodeInfo.containerRuntimeVersion}{"\n"}{.status.nodeInfo.kubeletVersion}{"\n"}'
```

On Windows PowerShell, run the same `oc` commands; single-quoted JSONPath arguments are supported in PowerShell. If a JSONPath quoting problem arises, prefer `oc describe node` rather than switching to a secret-revealing raw dump.

**Expected interpretation:** On a conventional RHCOS node, OS image identifies RHCOS and container runtime commonly reports `cri-o://...`. The exact values depend on the release and node type; exceptions require investigation rather than automatic failure classification.

## 4. Map the control plane to Operators and pods

```bash
oc get clusteroperators
oc get clusteroperator kube-apiserver etcd kube-scheduler kube-controller-manager
oc get pods -n openshift-kube-apiserver
oc get pods -n openshift-etcd
```

Cluster Operator `Available=True`, `Progressing=False`, `Degraded=False` is a typical steady-state expectation, **not a universal requirement during approved updates**. A control-plane namespace may contain static-pod revision management and supporting pods. Evaluate pod owners, revision changes and current upgrade state before treating `Completed` pods as failures.

If permitted:

```bash
oc describe clusteroperator kube-apiserver
oc describe clusteroperator etcd
```

Never attempt direct etcd access, static-pod deletion, or manual manifest editing as a diagnostic shortcut. Control-plane recovery requires a separate approved, version-specific procedure.

## 5. Inspect MachineConfigPool convergence

```bash
oc get machineconfigpools
oc describe machineconfigpool worker
oc get clusteroperator machine-config
```

The `worker` pool is common but not guaranteed: first inspect `oc get machineconfigpools` and substitute an existing pool name. Check `UPDATED`, `UPDATING`, `DEGRADED`, machine counts, node annotations and relevant events. During a controlled rollout, `UPDATING=True` may be expected.

**Do not create or patch MachineConfigs in this lab.** A seemingly small change can cause node reconfiguration, drains and reboots, impacting StatefulSets, PVC attachment, availability and quorum.

## 6. Diagnostic scenario: worker Ready but pool Degraded

A worker is `Ready`, but `oc get machineconfigpools` reports `DEGRADED=True`.

1. Confirm the cluster and whether a rollout is approved/in progress.
2. Run `oc describe machineconfigpool <pool-name>` and `oc get clusteroperator machine-config`.
3. Correlate the affected node's annotations, node conditions, recent events and workload placement.
4. Capture the exact degraded reason, change identifier and timestamp.
5. Escalate to the OpenShift platform owner; do not edit annotations, restart MCO components or reboot the node without an approved procedure.

A `Ready` node does not prove that desired OS configuration has converged. Conversely, a temporarily `UPDATING` pool may be normal during a rollout.

## 7. Failure patterns and safe responses

| Symptom | Possible cause | Read-only next step |
| --- | --- | --- |
| `Forbidden` | RBAC lacks cluster scope | `oc auth can-i`; request least privilege |
| Node `NotReady` | Kubelet, network, resource pressure, host failure | `oc describe node`, events, affected pods |
| CRI-O runtime version missing/unexpected | Runtime reporting or node type difference | Inspect nodeInfo and cluster release |
| MachineConfigPool `Degraded` | Configuration rollout failure | Describe pool and machine-config Operator |
| API/etcd Operator `Degraded` | Control-plane availability or reconciliation issue | Describe Operator; escalate with sanitized evidence |
| `NotFound` for MachineConfigPool | Different pool names or restricted resource visibility | List pools; verify context and permissions |

## 8. Production change and recovery boundaries

This chapter performs **no cluster mutations**. Local login and context selection can update kubeconfig; restore the prior context if needed. If an investigation suggests node replacement, MCO intervention, control-plane restart or etcd recovery, stop and obtain the separate approved runbook with:

- current quorum/replica and failure-domain assessment;
- change owner, impact and maintenance window;
- application/DBRE review for stateful workloads;
- backup/recovery evidence and rollback or forward-recovery decision;
- post-change validation of Operators, MachineConfigPools, nodes, application readiness and storage.

Complete [Lab 003](../labs/003-control-plane-rhcos-crio-node-inventory.md) and use the [node configuration triage runbook](../runbooks/node-runtime-and-machineconfigpool-triage.md). No actual cluster validation is implied.

## Official references

- [Red Hat OCP 4.22 RHCOS architecture](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/architecture/architecture-rhcos)
- [Red Hat OCP 4.22 node overview](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/nodes/overview-of-nodes)
- [Red Hat OCP 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
