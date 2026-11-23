# Runbook — OpenShift Node Runtime and MachineConfigPool Triage

**Use for:** Unexpected `NotReady` nodes, CRI-O/kubelet symptoms, or MachineConfigPool `Degraded`/stuck `Updating`.  
**OCP baseline:** 4.22, adapt to actual installed version.  
**Risk classification:** Read-only triage; any remediation requires separately approved change.  
**Status:** Draft, not production-certified.

## 1. Establish blast radius and identity

Determine application/customer impact, cluster environment, alert start, recent rollout and affected failure domains. Verify identity and server:

```bash
oc whoami
oc whoami --show-server
oc config current-context
oc get clusterversion
```

If the cluster does not match the independently approved inventory, **stop**.

## 2. Collect node and pool conditions

```bash
oc get nodes -o wide
oc get machineconfigpools
oc get clusteroperator machine-config
oc describe node <affected-node>
oc describe machineconfigpool <affected-pool>
```

Check Ready, MemoryPressure, DiskPressure and PIDPressure, nodeInfo runtime, pool Updated/Updating/Degraded, reported messages and last transition times.

## 3. Correlate workload and control-plane impact

```bash
oc get pods -A --field-selector spec.nodeName=<affected-node>
oc get clusteroperators
oc get events -A --sort-by=.lastTimestamp
```

For stateful workloads, document replica placement, PV/PVC attachments, quorum dependencies and disruption budgets before recommending any change. Do not collect Secret values or unredacted support bundles into public repositories.

## 4. Decision and escalation

| Condition | Recommended next step |
| --- | --- |
| Node NotReady and pool healthy | Investigate node/network/host conditions with platform and infrastructure owners |
| Node Ready and pool Degraded | Diagnose desired/current MachineConfig mismatch and MCO condition |
| Pool Updating during approved maintenance | Check expected rollout stage, timeout and change owner |
| Multiple control-plane failures | Escalate immediately; preserve etcd quorum, avoid ad hoc restarts |
| Read access denied | Record exact resource/action denied and request authorized read scope |

**Do not** use `oc debug node`, `chroot /host`, `oc adm drain`, host reboots, MCO pod deletion, MachineConfig patching or etcd recovery as part of this read-only runbook.

## 5. Required handoff and closure

Escalation package: incident ID, time window, cluster version, sanitized identity, impacted nodes/pools, condition changes, affected applications, recent change, evidence locations, suspected failure domain, recommended next read and named owner.

For remediation, require an approved version-specific runbook with prechecks, maintenance approval, storage and application owner signoff, rollback/forward recovery, and post-change verification. This read-only runbook has **no rollback**, because it makes no cluster changes.

## References

- [Red Hat OCP 4.22 nodes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/nodes/overview-of-nodes)
- [Red Hat OCP 4.22 RHCOS](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/architecture/architecture-rhcos)
