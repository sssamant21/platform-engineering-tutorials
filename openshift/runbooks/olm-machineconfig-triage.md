# Runbook — OLM Add-on Operator and MachineConfigPool Triage

**Status:** Draft, not production-certified. **Owner:** Platform Engineering on-call; involve Operator owner, DBRE and application team for stateful services.

## Trigger and severity

Trigger on CSV Failed/Pending, Subscription/InstallPlan stall, unhealthy CatalogSource, or MCP Degraded/Updating beyond an approved window. Assess user-facing impact separately from condition state; escalate immediately for unavailable critical workloads or multiple NotReady nodes.

## Initial read-only checks

```sh
oc whoami
oc config current-context
oc get clusterversion
oc get clusteroperators
oc get subscriptions.operators.coreos.com -A
oc get clusterserviceversions.operators.coreos.com -A
oc get installplans.operators.coreos.com -A
oc get catalogsources.operators.coreos.com -A
oc get machineconfigpools
oc get nodes
```

Inspect the affected Subscription/CSV/InstallPlan with `oc -n <namespace> describe <resource> <name>`; inspect `oc describe mcp <pool>` for pool problems. Do not include Secret data or authentication tokens in incident tickets.

## Branching diagnosis

**OLM:** Is the Subscription on the intended channel? Is approval manual? Does an InstallPlan exist? Is the CSV blocked by requirements or deployment? Is the CatalogSource healthy? Capture status and event messages, then consult the Operator vendor's supported upgrade path.

**MCP:** Is the pool actually Updating versus Degraded? Which nodes are affected? Is an authorized MachineConfig rollout ongoing? Correlate `oc get nodes` and `oc describe mcp <pool>` with the change calendar. A degraded pool can reflect configuration or daemon failure; avoid unsupported manual remediation.

## Safeguards, escalation and recovery

Never approve an InstallPlan, edit a Subscription, delete a CSV, change MCP pause state, apply MachineConfig, reboot/drain nodes, or force a rollout without approved change and impact analysis. Preserve workload quorum, storage attachment and PDB protections. Involve security for SCC/RBAC requirements, network team for registry/catalog connectivity, and DBRE for stateful operands. Rollback of Operator upgrades and node configuration is version- and vendor-dependent; obtain a documented supported plan before change. For critical impact, follow incident command and approved recovery procedure rather than improvising.

## Closeout evidence

Record sanitized cluster/version, affected Operator/namespace or MCP, conditions and timeline, application impact, change correlation, owner decisions, recovery action, and post-checks. Verify the original alert clears and application health is independently restored. No live execution has been performed for this draft.

References: [Red Hat OCP 4.22 Operators](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/operators/understanding-operators), [Machine configuration](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/machine_configuration/index).
