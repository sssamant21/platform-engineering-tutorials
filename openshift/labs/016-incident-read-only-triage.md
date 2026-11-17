# Lab 016 — Read-only Cluster Incident Triage

**Duration:** 30–40 minutes within Chapter 016. **Mode:** authorized read-only cluster or tabletop with fictional outputs. **Not executed.**

## Prerequisites
- `oc` client and valid scoped access; record OCP version and context without exporting credentials.
- Incident/ticket identifier, sanitized cluster alias, affected namespace and operator/node names supplied by the administrator.
- Cluster-wide resources require appropriate `get/list` RBAC. Check permissions before queries.

## Procedure (Linux/macOS shells and PowerShell)
```sh
oc whoami
oc config current-context
oc auth can-i list clusteroperators
oc auth can-i list nodes
oc auth can-i list pods -n <namespace>
oc get clusterversion
oc get clusteroperators
oc get nodes
oc get machineconfigpools
oc get pods -n <namespace> -o wide
oc get events -n <namespace> --sort-by=.metadata.creationTimestamp
```
Commands above use `oc` and work in PowerShell too; replace angle-bracket placeholders with approved values before execution. Avoid `grep` and Unix-only pipes in the cross-platform baseline. For least privilege, skip any cluster-wide command returning `no` from `oc auth can-i`.

## Expected and failure patterns (illustrative, not real output)
- Healthy Operator: `AVAILABLE=True PROGRESSING=False DEGRADED=False` (actual conditions may vary by lifecycle state).
- Incident: `DEGRADED=True` with a message requiring `oc describe clusteroperator <name>`.
- Node: `NotReady`; follow node conditions and workload placement rather than restarting it.
- Permission: `Error from server (Forbidden)`; stop and request approved evidence from authorized platform staff.
- Connectivity: `Unable to connect to the server`; investigate DNS/network/API reachability outside the cluster, do not infer etcd failure.
- Empty events: absence of retained events does not prove absence of incident.

## Investigation worksheet
Record UTC timestamps, sanitized cluster alias, `oc version`, context name (if non-sensitive), incident ID, observed impact, commands attempted, sanitized result excerpts, permission failures, and next owner. Never collect tokens, Secret YAML, kubeconfig contents, customer data or unredacted `must-gather` bundles.

## Acceptance
A reviewer can trace symptom → evidence → hypothesis → owner → safe next action. No state-changing command performed. Runtime verification remains **Not run** until genuine authorized execution and redacted evidence are recorded.

[Chapter 016](../chapters/016-incident-response-and-cluster-failure-triage.md) · [Runbook](../runbooks/cluster-incident-response-triage.md)
