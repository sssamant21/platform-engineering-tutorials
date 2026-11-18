# Lab 016 — Read-only Cluster Incident Triage

**Duration:** 30–40 minutes within Chapter 016. **Mode:** authorized read-only cluster or tabletop with fictional outputs. **Status:** Draft; no live execution or production approval.

## Prerequisites and safety
- Compatible `oc` CLI, approved cluster context, sanitized incident ID, and a specific authorized namespace.
- Least-privilege `list` access is required separately for each collection read; a named-object `get` is a different permission. ClusterVersion, ClusterOperators, nodes and MachineConfigPools are cluster-scoped; pods and events are namespace-scoped.
- Verify the target context and namespace before collecting anything. Do not export kubeconfig, access tokens, Secrets, customer data or raw support bundles.
- Commands below are read-only, but outputs may expose sensitive infrastructure metadata. Redact before sharing.

## Procedure — Bash (Linux/macOS)
```sh
NS=example-project  # replace with approved namespace
oc whoami
oc config current-context
oc version
oc auth can-i list clusterversions.config.openshift.io
oc auth can-i list clusteroperators.config.openshift.io
oc auth can-i list nodes
oc auth can-i list machineconfigpools.machineconfiguration.openshift.io
oc auth can-i list pods -n "$NS"
oc auth can-i list events -n "$NS"
```

## Procedure — PowerShell (Windows)
```powershell
$Ns = "example-project"  # replace with approved namespace
oc whoami
oc config current-context
oc version
oc auth can-i list clusterversions.config.openshift.io
oc auth can-i list clusteroperators.config.openshift.io
oc auth can-i list nodes
oc auth can-i list machineconfigpools.machineconfiguration.openshift.io
oc auth can-i list pods -n $Ns
oc auth can-i list events -n $Ns
```

**Only run the corresponding command below if its own authorization check returned `yes`.** Do not execute the entire block indiscriminately. Substitute the same approved namespace in either shell; do not paste angle-bracket placeholders literally.

```sh
oc get clusterversions.config.openshift.io
oc get clusteroperators.config.openshift.io
oc get nodes
oc get machineconfigpools.machineconfiguration.openshift.io
oc get pods -n example-project -o wide
oc get events -n example-project --sort-by=.metadata.creationTimestamp
```

For PowerShell, run each authorized command individually with `-n $Ns` for the last two namespace-scoped reads. If the API or SelfSubjectAccessReview check fails, record the error and stop that query; do not switch to cluster-admin. For `oc describe clusteroperator NAME` or `oc describe node NAME`, check `oc auth can-i get RESOURCE --resource-name=NAME` first; `describe` can attempt supplementary reads that may still be forbidden.

## Expected and failure patterns (illustrative, not observed)
- Authorized preflight: `yes`; unauthorized: `no`. A `yes` is not a guarantee of subsequent successful access.
- Healthy Operator: `AVAILABLE=True PROGRESSING=False DEGRADED=False` (actual conditions vary).
- Incident: `DEGRADED=True`, node `NotReady`, or pods not Ready; investigate without restarting or draining.
- `Forbidden` / `Unauthorized`: insufficient authorization or invalid session; skip and escalate.
- `the server doesn't have a resource type`: discovery/resource mismatch; verify API availability and exact version.
- `Unable to connect to the server`: investigate connectivity and API reachability; do not assume etcd failure.
- No events: events may have expired; absence does not prove no incident.

## Investigation and acceptance
Record UTC timestamps, sanitized cluster alias, OCP version, incident ID, namespace, actual commands and redacted output, skipped checks, impact, hypothesis, responsible owner and escalation. For platform/API failures involve the platform incident lead; for persistent services involve DBRE/application owners before any mitigation. Mutations (drain, restart, Operator changes, failover or restore) require a separately approved runbook, impact assessment, supported recovery/rollback decision and post-change validation.

A reviewer must be able to trace symptom → evidence → hypothesis → owner → safe next action. **Documentation review is not runtime validation**; actual lab execution, independent technical review and production acceptance remain pending.

[Chapter 016](../chapters/016-incident-response-and-cluster-failure-triage.md) · [Runbook](../runbooks/cluster-incident-response-triage.md)
