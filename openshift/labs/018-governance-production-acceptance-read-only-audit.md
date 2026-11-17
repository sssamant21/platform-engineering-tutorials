# Lab 018 — Read-only Governance and Production Acceptance Audit

**Status:** Draft only; not executed. **Duration:** 25–35 minutes. **Scope:** Authorized cluster inventory only; no writes.

## Prerequisites

`oc` compatible with the target cluster, authenticated context, permissions to `get` ClusterVersion, ClusterOperators, nodes and MachineConfigPools. Namespace workload checks additionally require `get` pods in the approved namespace. Use least-privilege roles granted by the cluster owner; do not grant yourself `cluster-admin` to complete the lab. Commands work in PowerShell and Linux shells unless noted.

## Safety and identity

```sh
oc config current-context
oc whoami
oc version --client
oc auth can-i get clusterversions.config.openshift.io
oc auth can-i get clusteroperators.config.openshift.io
oc auth can-i get nodes
oc auth can-i get machineconfigpools.machineconfiguration.openshift.io
```

**Expected:** a known context/user, client version and yes/no authorization responses. **Stop** if the context is not the approved cluster. Do not run `oc config view --raw`, `oc whoami -t`, `oc get secrets`, or `oc adm must-gather` for this basic audit.

## Read-only health evidence

Only execute commands authorized by the permission checks:

```sh
oc get clusterversion
oc get clusteroperators
oc get nodes
oc get mcp
```

**Expected examples (illustrative, not actual test output):** a ClusterVersion record, Operators with Available/Progressing/Degraded status, node Ready status and MCP UPDATED/UPDATING/DEGRADED fields. A degraded Operator or node is a **finding**, not automatic authorization to change it.

For an explicitly approved namespace (replace placeholder with a real authorized name):

```sh
oc auth can-i get pods -n <approved-namespace>
oc get pods -n <approved-namespace>
```

## Failure cases and evidence

- `Forbidden`: stop that query; request a narrowly scoped read permission from the owner, never privilege escalation as a workaround.
- `Unauthorized` or TLS/connectivity failure: validate context and approved connectivity with IAM/platform owner; never bypass TLS verification.
- `the server doesn't have a resource type`: verify exact API/version and installed capabilities; do not assume a Machine API or optional Operator exists on every topology.
- Missing/unknown output: record as **not verified**, not PASS.
- Do not store raw output publicly: names, addresses, annotations and topology may be sensitive.

## Evidence worksheet

| Field | Record |
| --- | --- |
| Date/time UTC and reviewer | Not executed |
| Cluster type and exact OCP version | Not verified |
| Approved context and scope | Not verified |
| RBAC checks and denials | Not executed |
| CVO/CO/node/MCP baseline | Not executed |
| Namespace/service owners and SLO | Not verified |
| Backup restore / RPO / RTO evidence | Not verified |
| Findings, ticket and escalation | Pending |
| Independent signoff | Pending |

**Pass criteria:** command output captured privately with time/version/scope, all gaps classified, named owner acknowledgment. **No lab pass** without real execution. Windows PowerShell: run the same `oc` commands in PowerShell; avoid Unix-only `grep`/`jq` dependencies. Never export credentials into evidence.
