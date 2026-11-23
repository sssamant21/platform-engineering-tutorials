# Chapter 011 — Operator Lifecycle Manager, Add-on Operators and MachineConfig

**Audience:** OCP administrators, SREs, DBREs. **Duration:** ~60 minutes. **Baseline:** Red Hat OCP 4.22; verify the actual cluster version before applying guidance. **Status:** Documentation draft; no cluster execution.

## Objectives and prerequisites

Distinguish cluster-managed Operators from OLM-managed add-ons; trace CatalogSource → Subscription → InstallPlan → ClusterServiceVersion (CSV) → deployed Operator; diagnose an unhealthy Operator without forcing an upgrade; identify MachineConfig and MachineConfigPool (MCP) rollout state.

Prerequisites: authenticated `oc` CLI, approved read-only access to namespaces containing OLM resources, and cluster-scope read permissions where granted. Confirm `oc whoami`, `oc config current-context` and the intended cluster identity; do not expose kubeconfig contents or tokens.

## Concepts

**Cluster Operators** are OpenShift platform components reconciled by platform management; they are not interchangeable with user-installed OLM add-ons. **OLM** manages installation and lifecycle of supported add-on Operators through catalogs, subscriptions, install plans and CSVs. Subscription channels and approval strategy influence upgrades. A CSV phase alone does not prove application health; also inspect deployments and Operator-specific operands.

**MachineConfig Operator (MCO)** reconciles node-level configuration using MachineConfig and MCP resources. MachineConfig changes can cause worker disruption and reboots; do not treat them as harmless YAML changes. MCP `UPDATED`, `UPDATING` and `DEGRADED` must be interpreted alongside node state and active rollout.

## Read-only investigation (Linux shell or PowerShell)

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

If permissions allow, choose a specific Operator namespace and name from the inventory (never assume the namespace):

```sh
oc -n <operator-namespace> describe subscription <subscription-name>
oc -n <operator-namespace> describe csv <csv-name>
oc -n <operator-namespace> describe installplan <installplan-name>
oc describe machineconfigpool worker
```

Replace angle-bracket placeholders with validated resource names. The commands are illustrative and must not be pasted with placeholders intact. Avoid `oc get ... -o yaml` on arbitrary resources when capturing evidence; redact sensitive annotations and identifiers.

## Diagnostic decision points

| Observation | Interpretation | Next safe check |
| --- | --- | --- |
| Subscription missing | Operator may not be OLM-managed or may live elsewhere | Confirm installation model and namespace |
| InstallPlan requires approval | Manual approval policy may intentionally block change | Obtain owner/change approval; do not approve during diagnosis |
| CSV Pending/Failed | Requirements, permissions, image retrieval or deployment may be blocking | Describe CSV and check namespace events |
| CatalogSource unhealthy | Catalog connectivity, image or pod issues | Check CatalogSource status and related pods |
| MCP Updating | Configuration rollout may be underway | Check nodes, pool conditions and change window |
| MCP Degraded | Reconciliation or node configuration problem | Capture condition message, affected nodes, MCO logs through approved access |

**Expected results:** Lists show available resources, or a documented `Forbidden` if RBAC is insufficient. Some clusters have no tenant add-on Subscriptions. Do not assume all healthy CSVs are `Succeeded` without checking the Operator's documented version-specific lifecycle.

## Production safety and change control

Read-only inspection is the default. Never approve InstallPlans, change Subscription channels, remove finalizers, delete CSVs, patch MachineConfigs/MCPs, pause pools, drain nodes, or restart Operators as an exploratory fix. A change requires named service owner, platform/DBRE reviewer for stateful impact, change record, compatibility matrix, maintenance window, backups and tested recovery plan. **Rollback is not automatically supported** for Operator upgrades or node OS/config transitions; verify vendor-supported recovery rather than promising a downgrade. For PostgreSQL/Kafka/Redis Operators, check application quorum, PDBs, PVC topology and reconciliation behavior before any upgrade.

## Exercise and assessment

Complete [Lab 011](../labs/011-olm-machineconfig-read-only-audit.md), then use the [OLM/MCP triage runbook](../runbooks/olm-machineconfig-triage.md). Explain why a ClusterOperator is different from a CSV, and why a manual InstallPlan is not automatically an incident.

## References

- [Red Hat OCP 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [OLM concepts and workflows](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/operators/understanding-operators)
- [Machine configuration](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/machine_configuration/index)
