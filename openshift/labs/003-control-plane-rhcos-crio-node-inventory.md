# Lab 003 — Control Plane, RHCOS, CRI-O and Node Inventory

**Type:** Read-only administration exercise. **Duration:** 30–40 minutes.  
**Environment:** Authorized OCP 4.x cluster, compatible `oc`, cluster-level read access as granted.  
**Status:** Not executed. Use a non-production cluster when available.

## Safety preflight

Record a sanitized cluster name, environment, exact OCP version and change/incident context. Never commit kubeconfig, credentials, full sensitive node metadata or raw logs. All commands below are reads; login may update local kubeconfig.

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc get clusterversion
```

## Exercise A — Node and runtime inventory

```bash
oc auth can-i list nodes
oc get nodes -o wide
oc get nodes --show-labels
oc describe node <approved-node-name>
```

Record expected node count, roles, Ready conditions, RHCOS image, kubelet and CRI-O versions. If `Forbidden`, record that RBAC blocked the exercise and do not escalate access on your own.

## Exercise B — Control-plane visibility

```bash
oc get clusteroperator kube-apiserver etcd kube-scheduler kube-controller-manager
oc get pods -n openshift-kube-apiserver
oc get pods -n openshift-etcd
```

Identify `Available`, `Progressing`, `Degraded` and whether the cluster is undergoing an approved update. Note that a Job pod in `Completed` may be normal.

## Exercise C — Configuration convergence

```bash
oc get machineconfigpools
oc get clusteroperator machine-config
oc describe machineconfigpool <existing-pool-name>
```

Use a real pool name from the list, not a guessed one. Record `UPDATED`, `UPDATING`, `DEGRADED` and the stated reason if unexpected.

## Evidence template

| Field | Observed result |
| --- | --- |
| Execution timestamp UTC | Not executed |
| Sanitized cluster ID / OCP release | Not executed |
| Identity and API server verified | Not executed |
| Node count / roles / Ready count | Not executed |
| RHCOS and CRI-O observation | Not executed |
| Control-plane Operator conditions | Not executed |
| MachineConfigPool conditions | Not executed |
| Anomaly and read-only next action | Not executed |
| Permission limitations | Not executed |
| Independent reviewer | Pending |

## Acceptance gates

- Identity, context and target environment verified against inventory.
- Node, runtime, control-plane and MachineConfigPool signals interpreted without assuming a fixed topology.
- Every denied/unsupported command documented accurately.
- Evidence is sanitized and independently reviewed before the lab is marked verified.
- No node debug, host shell, drains, MachineConfig patches or control-plane recovery actions performed.

**Outcome at publication:** Documentation drafted, runtime not run, production approval not granted.
