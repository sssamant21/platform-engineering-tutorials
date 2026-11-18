# Runbook — OpenShift Cluster Incident Response and Triage

**Status:** Draft, not production-approved. **Baseline:** OCP 4.22. **Default:** read-only.

## Trigger and incident ownership
API timeouts, widespread 5xx, ClusterOperator Degraded, nodes NotReady, inaccessible Routes, or stateful service disruption. Assign incident commander, platform lead, communications lead and affected application/DBRE owners. Record UTC start time, affected regions/clusters and severity.

## Immediate safety gates
1. Verify cluster and context using `oc whoami` and `oc config current-context`; do not copy kubeconfig/token output.
2. Freeze unrelated changes; identify current upgrades, MachineConfigPool rollouts, maintenance and cloud events.
3. Use authorized read-only queries only; collect sanitized outputs with timestamps. Avoid broad secret or support bundle exports.
4. If API inaccessible, compare multiple authorized clients and external DNS/network/TLS observations; do not attempt unsupported control-plane recovery.

## Read-only authorization and decision tree
**Prerequisites:** `oc` matching the target cluster's supported client compatibility, an approved read-only identity, a verified current context, and an explicitly selected namespace. The following commands do not change cluster resources, but their output may contain sensitive workload metadata. Do not paste unredacted outputs into tickets or the repository.

Check permissions **for each resource and scope** before issuing a query. `get` for a named object and `list` for a collection are different RBAC verbs. A `no` or `Forbidden` response is a stop for that query, not permission to elevate access. Some clusters restrict discovery and resource visibility.

```sh
# Linux/macOS shell; replace the example namespace with the approved target.
NS=example-project
oc config current-context
oc whoami
oc auth can-i list clusterversions.config.openshift.io
oc auth can-i list clusteroperators.config.openshift.io
oc auth can-i list nodes
oc auth can-i list machineconfigpools.machineconfiguration.openshift.io
oc auth can-i list pods -n "$NS"
oc auth can-i list events -n "$NS"
oc auth can-i list routes.route.openshift.io -n "$NS"
oc auth can-i list services -n "$NS"
oc auth can-i list endpointslices.discovery.k8s.io -n "$NS"
```

```powershell
# PowerShell: equivalent preflight; use an approved namespace.
$Ns = "example-project"
oc config current-context
oc whoami
oc auth can-i list clusterversions.config.openshift.io
oc auth can-i list clusteroperators.config.openshift.io
oc auth can-i list nodes
oc auth can-i list machineconfigpools.machineconfiguration.openshift.io
oc auth can-i list pods -n $Ns
oc auth can-i list events -n $Ns
oc auth can-i list routes.route.openshift.io -n $Ns
oc auth can-i list services -n $Ns
oc auth can-i list endpointslices.discovery.k8s.io -n $Ns
```

**Run only those collection reads for which the corresponding check returned `yes`:**

```sh
oc get clusterversion
oc get clusteroperators
oc get nodes -o wide
oc get machineconfigpools
oc get pods -n example-project -o wide
oc get events -n example-project --sort-by=.metadata.creationTimestamp
oc get routes -n example-project
oc get services -n example-project
oc get endpointslices.discovery.k8s.io -n example-project
```

For a named-object investigation, first verify the appropriate `get` verb for that exact resource and scope, then run `oc describe clusteroperator <name>`, `oc describe node <name>` or `oc describe pod <pod> -n example-project` only when authorized. `describe` may also retrieve related events and other objects, so a `Forbidden` on supplementary information does not automatically invalidate all displayed fields.

**Expected:** `yes`/`no` authorization decisions; allowed collection reads return rows or an empty list. **Common errors:** `Forbidden` (insufficient RBAC), `Unauthorized` (expired/invalid authentication), `the server doesn't have a resource type` (API discovery/resource mismatch), or connection timeouts (API/network outage). Stop and escalate rather than retrying with elevated credentials. A `yes` precheck is not a guarantee the subsequent request will succeed. For cluster-wide events or restricted diagnostics, request a sanitized handoff from an authorized platform administrator.

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
