# Runbook — Cluster Operator / CVO Degraded Triage

**Scope:** Read-only first response for Cluster Operator degradation or unexpected cluster update state on OCP 4.x.  
**Reference baseline:** OCP 4.22. Verify target release and topology.  
**Safety:** No restart, patch, upgrade, force-update, delete or rollback actions are authorized by this runbook.

## Triggers

- ClusterOperator `Available=False` or `Degraded=True`.
- ClusterVersion `Failing=True` or unexpected `Progressing=True`.
- Cluster update stalls or Operator condition messages indicate persistent failure.

## Procedure

### 1. Confirm impact and identity

Identify affected business services, alert start time, ongoing maintenance/change ID, cluster and incident commander. Verify the active target:

```bash
oc whoami
oc whoami --show-server
oc config current-context
```

### 2. Capture release and Operator conditions

```bash
oc get clusterversion
oc describe clusterversion version
oc get clusteroperators
oc describe clusteroperator <affected-operator>
oc get machineconfigpools
oc get nodes -o wide
```

All are read-only. Some may return `Forbidden` due to RBAC; report missing access without privilege bypass. Substitute a real Operator name returned by `oc get clusteroperators`.

### 3. Distinguish expected progress from failure

- During an approved update, `Progressing=True` may be expected; check timing and actual condition messages.
- `Degraded=True` represents persistent divergence, but an Operator may remain `Available=True`; validate application impact separately.
- `Available=False` indicates component availability problems; correlate with service health.
- `Upgradeable=False` is a safety gate. Do not force past it.
- `Failing=True` in ClusterVersion requires urgent platform-owner escalation.

### 4. Narrow scope

Use `oc describe clusteroperator` for `Reason`, `Message`, transition time and related objects. If the namespace is identified and authorized:

```bash
oc get pods -n <identified-namespace>
oc get events -n <identified-namespace> --sort-by=.lastTimestamp
```

Do not assume Operator names map directly to namespaces. Inspect related nodes, pools, storage, network or API availability based on the affected component and incident symptoms. Avoid broad log dumps that may expose credentials or patient/application data.

### 5. Escalate and preserve evidence

Record sanitized environment, version, Operator, condition transitions, upgrade history, workload impact, recent changes, RBAC limitations, relevant events, owner, and recommended next diagnostic action. Engage platform SRE and, for stateful workloads, DBRE/application owners.

## Prohibited shortcuts

Do not directly patch `ClusterVersion`, change channel, force an upgrade, delete ClusterOperators, manually edit CVO-managed objects, restart platform pods or drain nodes as first response. Such actions can worsen quorum, availability or storage attachment problems.

## Recovery decision / rollback

This runbook makes no state changes, so no rollback is needed. If a corrective change is required, obtain a separate supported version-specific remediation runbook with approvals, prerequisites, failure-domain/quorum and PVC checks, backup/recovery readiness, maintenance window, expected conditions, and post-change acceptance. Do not promise in-place downgrade as a rollback.

## References

- [Understanding OpenShift updates](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/updating_clusters/understanding-openshift-updates-1)
- [Installation validation and cluster version](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/validation_and_troubleshooting/validating-an-installation)
- [Red Hat Operator troubleshooting](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/pdf/support/getting-support)

[Chapter 004](../chapters/004-cluster-operators-cvo-and-update-state.md)
