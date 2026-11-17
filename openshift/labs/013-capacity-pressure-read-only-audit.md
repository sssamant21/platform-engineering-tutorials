# Lab 013 — Read-only Capacity and Scheduling Audit

**Time:** 30 minutes. **Environment:** authorized OCP 4.22 test/staging cluster or approved read-only production session. **Status:** Draft, not executed.

## Access and scope
Use an authenticated `oc` client; obtain read permissions on nodes and namespace pods/events; autoscaler visibility is optional. Do not export kubeconfig or credentials. Record sanitized cluster identifier, OCP version (if permitted), date/time, namespace and reviewer. Never save Secret objects.

```sh
oc whoami
oc config current-context
oc auth can-i list nodes
oc auth can-i list pods -n <project>
oc get nodes -o wide
oc describe node <node-name>
oc get pods -n <project> -o wide
oc get events -n <project> --sort-by=.metadata.creationTimestamp
oc get resourcequota,limitrange,pdb -n <project>
oc get hpa -n <project>
oc adm top nodes
```

For optional cluster-scoped inspection (only when authorized):
```sh
oc auth can-i list clusterautoscalers.autoscaling.openshift.io
oc get clusterautoscalers.autoscaling.openshift.io
oc get machineautoscalers.autoscaling.openshift.io -A
```

**PowerShell/Linux:** Run commands individually in PowerShell or Bash; replace angle-bracket placeholders with approved real names. Avoid redirecting full `oc describe` output to public files. Capture only redacted conditions, requests and event reasons.

## Expected observations (not test evidence)

- Nodes show Ready/NotReady and roles; `describe` shows Capacity, Allocatable, Conditions and Allocated resources.
- Pending pods may have `FailedScheduling` events identifying insufficient resources, taints, affinity or volume topology.
- `oc adm top` may show usage; metrics unavailable is a separate instrumentation limitation.
- `Forbidden` means insufficient RBAC; missing autoscaler API may mean unsupported/not installed for this topology. Neither is proof of cluster failure.
- `No resources found` for HPA or quotas is possible; never fabricate resources.

## Evidence checklist

Record: context and sanitized cluster ID; RBAC outcome; number of eligible nodes; allocatable and requested CPU/memory for one approved node; pod scheduling event reason; quota/PDB observations; optional metrics timestamp; any permission/API failures; conclusion and escalation owner. Do **not** calculate a definitive cluster headroom percentage by summing heterogeneous pools.

**Pass criteria:** commands interpreted correctly, read-only boundary respected, limitations recorded. **Pending:** actual runtime outputs, peer review, approval. Never execute scaling, cordon, drain or taint removal as part of this lab.

[Chapter 013](../chapters/013-capacity-resource-pressure-and-autoscaling.md) · [Runbook](../runbooks/capacity-scheduling-autoscaling-triage.md)
