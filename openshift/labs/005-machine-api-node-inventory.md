# Lab 005 — Machine API and Node Inventory (Read-only)

**Duration:** ~25 minutes, within Chapter 005.  
**Target:** Authorized OCP 4.x environment; OCP 4.22 documentation baseline.  
**Status:** Drafted; execution not performed.

## Prerequisites

- `oc` installed, an approved login, and explicit permission to view cluster and Machine API metadata.
- Know whether the installation is installer-provisioned or user-provisioned. Machine API may be absent; the lab remains valid as a Node-only inventory.
- Do not request elevated credentials to work around RBAC.

## Procedure

```bash
# Identify the target cluster and effective access
oc whoami
oc whoami --show-server
oc config current-context
oc auth can-i get nodes
oc auth can-i list machines.machine.openshift.io -n openshift-machine-api

# Record cluster and node status
oc get clusterversion
oc get nodes -o wide
oc get machineconfigpools

# Run only if Machine API is available and authorized
oc get machines -n openshift-machine-api -o wide
oc get machinesets -n openshift-machine-api
oc get machinehealthchecks -n openshift-machine-api

# Inspect one affected node, if available
oc describe node <node-name>
oc get pods -A --field-selector spec.nodeName=<node-name>
```

For a Machine-backed node, examine `oc describe machine <machine-name> -n openshift-machine-api` and correlate Machine provider ID/node reference with the corresponding Node. Do not assume identical resource names.

## Expected observations (not fabricated output)

- `oc get nodes`: expected hosts appear with Ready status during steady state.
- `oc get machinesets`: when applicable, desired/current/ready/available values can be compared.
- `oc get machineconfigpools`: pool updated/updating/degraded conditions explain configuration rollouts.
- A `Forbidden` error indicates insufficient permissions; `the server doesn't have a resource type` indicates API discovery/topology differences.
- Missing Machine resources on a user-provisioned topology are not automatically a failure.

## Simulated incident question

A worker is `NotReady`, the MachineSet shows fewer available than desired, and one Kafka broker has a PVC on the node. Write an investigation and **go/no-go** decision; do not run drain or delete. Include Kafka availability/ISR, PDBs, storage and capacity checks, plus escalation to DBRE and application owners.

## Evidence template

| Field | Recorded result |
| --- | --- |
| UTC time and sanitized cluster | Not executed |
| OCP version and infrastructure model | Not executed |
| Authorized user/context | Not executed |
| Machine API supported? | Not executed |
| Node Ready/NotReady counts | Not executed |
| MachineSet desired/current/ready (if applicable) | Not executed |
| MCP health | Not executed |
| Workload/PVC exposure | Not executed |
| Maintenance decision and owner | Not executed |
| Reviewer and sign-off | Pending |

## Pass criteria

Read-only collection, correct interpretation of Machine API applicability, no secrets in evidence, no infrastructure mutation, and a defensible maintenance decision. Record RBAC failures as constraints rather than bypassing them.

**Actual lab result:** Not run. Do not mark verified without recorded cluster evidence.
