# Runbook — Machine API, MachineSet and Node Failure Triage

**Scope:** OCP 4.x Machine API installations and Node-only topologies.  
**Classification:** Read-only diagnostics; no infrastructure changes.  
**Baseline:** Red Hat OpenShift 4.22.  
**Status:** Drafted, not runtime-validated.

## Trigger and first response

Machine provisioning stalled, MachineSet below desired capacity, node NotReady, unexpected MachineHealthCheck remediation or worker failure.

1. Establish business impact, incident severity, on-call owners and any recent maintenance/upgrade.
2. Verify the active cluster and current user:

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc get clusterversion
oc get clusteroperators
```

3. Inspect node and Machine API status (where available and authorized):

```bash
oc get nodes -o wide
oc get machines -n openshift-machine-api -o wide
oc get machinesets -n openshift-machine-api
oc get machinehealthchecks -n openshift-machine-api
oc get machineconfigpools
oc get events -n openshift-machine-api --sort-by=.lastTimestamp
```

4. Drill into the affected resources:

```bash
oc describe node <node-name>
oc describe machine <machine-name> -n openshift-machine-api
oc describe machineset <machineset-name> -n openshift-machine-api
oc get pods -A --field-selector spec.nodeName=<node-name>
```

Run Machine-specific commands only on supported installations with the correct permissions. Check node conditions, provisioning errors, MachineSet availability, provider quotas, MachineHealthCheck behavior and current upgrades.

## Workload and data-safety assessment

- Identify StatefulSets, Kafka brokers, PostgreSQL instances, Redis replicas, PVCs, local PVs, CSI attach/detach dependencies and data-loss exposure.
- Confirm application owners, PDB constraints, node scheduling capacity and multi-zone failure domains.
- Record impact of a further node loss before considering any repair.
- A MachineSet below desired capacity does not automatically justify scaling or deleting a Machine; identify root cause first.

## Escalation

| Condition | Primary contact | Additional stakeholders |
| --- | --- | --- |
| Cloud provisioning / quota / machine credentials | Platform / infrastructure SRE | Cloud provider, security |
| Node runtime / RHCOS / MachineConfigPool | Platform SRE | Red Hat support when appropriate |
| Stateful pod or volume at risk | DBRE / storage owner | Application owner, platform SRE |
| Production change required | Change owner | Incident commander and affected service owners |

## Change approval and recovery

**No state-changing commands are authorized by this runbook.** If a drain, cordon, replacement, MachineSet scale, remediation pause or node reboot is proposed, use a separate approved procedure with prerequisites, quorum and data-safety checks, tested rollback and post-change acceptance criteria.

If a change is approved elsewhere, verify restored Node readiness, Machine/MachineSet reconciliation, MCP status, critical pod readiness, storage mounts, application SLIs and database replication health. Document residual risk and incident timeline.

## Evidence to preserve

Sanitized cluster and provider identity, UTC timestamps, affected Machine/Node references, Machine and Node conditions, events, relevant operator health, workloads at risk, change timeline and named escalation owners. Never include Secrets or bearer tokens.

## Reference

[Red Hat OpenShift 4.22 Machine management](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/machine_management/index)
