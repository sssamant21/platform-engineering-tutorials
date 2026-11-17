# Runbook — OpenShift Cluster Incident Response and Triage

**Status:** Draft, not production-approved. **Baseline:** OCP 4.22. **Default:** read-only.

## Trigger and incident ownership
API timeouts, widespread 5xx, ClusterOperator Degraded, nodes NotReady, inaccessible Routes, or stateful service disruption. Assign incident commander, platform lead, communications lead and affected application/DBRE owners. Record UTC start time, affected regions/clusters and severity.

## Immediate safety gates
1. Verify cluster and context using `oc whoami` and `oc config current-context`; do not copy kubeconfig/token output.
2. Freeze unrelated changes; identify current upgrades, MachineConfigPool rollouts, maintenance and cloud events.
3. Use authorized read-only queries only; collect sanitized outputs with timestamps. Avoid broad secret or support bundle exports.
4. If API inaccessible, compare multiple authorized clients and external DNS/network/TLS observations; do not attempt unsupported control-plane recovery.

## Read-only decision tree
```sh
oc get clusterversion
oc get clusteroperators
oc get nodes -o wide
oc get machineconfigpools
oc get pods -n <namespace> -o wide
oc get events -n <namespace> --sort-by=.metadata.creationTimestamp
```
For a specific issue:
```sh
oc describe clusteroperator <name>
oc describe node <name>
oc describe pod <pod> -n <namespace>
oc get routes,services,endpointslices -n <namespace>
```
If RBAC denies a query, obtain an approved handoff; do not grant yourself `cluster-admin`. If cluster-wide events are needed, have an authorized administrator retrieve and sanitize them. Use `oc auth can-i` for permission prechecks.

## Escalation
- API/control plane or etcd concern: platform control-plane owner, incident commander, Red Hat Support as appropriate.
- MCP/NotReady: compute/node owner; consult DBRE for affected persistent workloads.
- Route/ingress: networking and application owner.
- PVC/CSI: storage team and DBRE; no PVC/PV deletion or detach.
- PostgreSQL/Kafka/MongoDB/Redis: DBRE and application owner for quorum, leader and recovery decisions.

## Remediation approval and stop conditions
Before **any** mutation, capture approved change/incident authorization, exact target, owner, rollback or supported recovery decision, snapshot/backup relevance, business impact, monitoring and stop conditions. Do not run node drains, restarts, scaling, Operator edits, etcd restore or failover without explicit approved procedure. For an upgrade, generic rollback promises are unsafe; verify vendor-supported options.

## Validation and closure
Recheck cluster/Operator conditions, node readiness, ingress and application SLIs, database replication/leader health, persistent storage, and customer-facing errors. Obtain platform + application/DBRE acceptance; document residual risks, timeline, root-cause hypotheses and follow-up owners. Do not claim restored solely because `oc get nodes` shows Ready.

[Chapter 016](../chapters/016-incident-response-and-cluster-failure-triage.md) · [Lab 016](../labs/016-incident-read-only-triage.md)

Official reference: [OCP 4.22 troubleshooting](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/support/troubleshooting). Validate exact release-specific procedures before operational changes.
