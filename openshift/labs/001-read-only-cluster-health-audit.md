# Lab 001 — Read-Only OpenShift Cluster Health Audit

**Prerequisites:** Authorized OCP login, compatible `oc` CLI, approval to inspect cluster metadata, knowledge of which cluster is safe to access. No administrative changes are part of this lab.

## Exercise

1. Run `oc whoami`, `oc whoami --show-server` and `oc config current-context`. Confirm the intended cluster and user before continuing.
2. Run `oc get clusterversion` and `oc get clusteroperators`.
3. Run `oc get nodes -o wide` and `oc get machineconfigpools`.
4. Run `oc get pods -A` and classify pods needing investigation. Do not count successful Job pods as failures.
5. If authorized and metrics are available, run `oc adm top nodes`.
6. Select one actual anomaly, or explicitly state 'no anomaly observed.' Document how you would investigate it without making changes.

## Evidence sheet

| Field | Value |
| --- | --- |
| Date/time (UTC) | _Not executed_ |
| Sanitized cluster/environment | _Not executed_ |
| `oc` client version | _Not executed_ |
| OCP server version | _Not executed_ |
| Identity/context verified | _Not executed_ |
| ClusterVersion assessment | _Not executed_ |
| Cluster Operators assessment | _Not executed_ |
| Node / MachineConfigPool assessment | _Not executed_ |
| Workload anomaly assessment | _Not executed_ |
| Remediation recommended? | _Not executed_ |
| Reviewer | _Pending_ |

## Acceptance criteria

- All executed commands are read-only and target the verified cluster.
- Any RBAC or metrics unavailability is recorded without escalating privileges ad hoc.
- Outputs and interpretations are stored securely and secrets are redacted.
- Each finding has a next diagnostic step or explains why no action is needed.

**Current result:** Not run. Example command correctness does not establish runtime validation.
