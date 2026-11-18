# Runbook — Upgrade, CVO and MachineConfigPool Triage

**Status:** Draft / not production-certified. **Scope:** Read-only investigation of a failed, blocked or stalled OCP 4.22 update. **Owner:** Platform/SRE incident commander with Red Hat Support escalation as needed.

## Trigger and immediate safety
Trigger: CVO Progressing unexpectedly long, Degraded ClusterOperator, degraded MCP, NotReady nodes or application SLO breach during a planned update. Freeze unrelated changes; **do not** force update, edit ClusterVersion desired version, pause/unpause MCPs, reboot/drain nodes or restore etcd from this runbook. Declare severity using actual customer impact and change policy.

## Read-only triage and least-privilege preflight
**Prerequisites:** approved incident/change scope, a known cluster context, a compatible `oc` client, and an identity authorized for each requested resource. `oc auth can-i` checks are advisory; a subsequent request can still fail. A denied permission is a stop for that specific query, not a reason to elevate privileges. Cluster-wide events are optional and often intentionally restricted.

```sh
# Linux/macOS; each collection query needs its own list permission.
oc config current-context
oc whoami
oc auth can-i get clusterversions.config.openshift.io --resource-name=version
oc auth can-i list clusteroperators.config.openshift.io
oc auth can-i list machineconfigpools.machineconfiguration.openshift.io
oc auth can-i list nodes
oc auth can-i list events --all-namespaces
```

```powershell
# PowerShell; identical checks, no shell-specific variable interpolation.
oc config current-context
oc whoami
oc auth can-i get clusterversions.config.openshift.io --resource-name=version
oc auth can-i list clusteroperators.config.openshift.io
oc auth can-i list machineconfigpools.machineconfiguration.openshift.io
oc auth can-i list nodes
oc auth can-i list events --all-namespaces
```

Run **only** the reads for which the matching check returned `yes`:

```sh
oc get clusterversion version -o json
oc get clusteroperators
oc get machineconfigpools
oc get nodes
oc get events -A --sort-by=.metadata.creationTimestamp
```

The ClusterVersion JSON and events may expose infrastructure metadata; sanitize before sharing. If cluster-wide events are denied, omit that query and request scoped evidence from the platform owner. For `oc describe co <name>`, `oc describe mcp <name>` or `oc describe node <name>`, separately check `oc auth can-i get <resource> --resource-name=<name>` and expect optional related-event lookups to be denied in restricted roles.

**Expected:** authorization checks return `yes` or `no`; authorized collection reads return objects or an empty result. **Errors:** `Forbidden` means insufficient RBAC, `Unauthorized` means invalid/expired authentication, missing resource types may indicate API discovery/version mismatch, and timeouts require network/API escalation. Never paste credentials, raw kubeconfig, or unsanitized JSON into tickets.

Read CVO history and condition messages; correlate ClusterOperator condition transitions with MCP updates and node readiness. Events may be rotated and `--sort-by` may require permission/field availability. Narrow follow-up with `oc describe co <operator-name>`, `oc describe mcp <pool-name>` or `oc describe node <node-name>` **only** for authorized scope. Avoid exporting Secrets or sensitive full diagnostic archives.

## Decision tree
- **API unreachable:** verify network, DNS, VPN, endpoint and authorized access; escalate to control-plane/platform owners.
- **CVO Degraded / update blocked:** capture condition reason and timestamps, confirm target support and known risks, engage platform lead and Red Hat Support.
- **MCP degraded / node NotReady:** assess rollout and node health; involve MachineConfig and infrastructure owners; do not change pool state without a plan.
- **Operator healthy, app degraded:** investigate application rollout, Route, storage and database quorum with owners; healthy Operators do not prove application recovery.
- **Forbidden:** obtain a scoped read-only evidence request, never borrow credentials.

## Approval and recovery boundaries
Incident commander and change owner authorize any subsequent intervention. For DBRE-managed PostgreSQL/Kafka/Redis/MongoDB, require quorum and replication review, backup verification, disruption risk and explicit application approval. A prior OCP version is **not** a generic rollback target. Supported recovery may require Red Hat Support; etcd restore has cluster-wide data-loss implications and is a separate controlled procedure.

## Exit criteria and evidence
Record sanitized timestamps, exact source/target version, change ID, CVO and Operator conditions, MCP and node status, impact, database health, owner decisions, escalation ticket and post-incident actions. Exit only after stable platform and application SLIs during the agreed observation window and independent approval.

References: [Chapter 014](../chapters/014-upgrade-planning-gates-and-post-checks.md), [Lab 014](../labs/014-upgrade-read-only-preflight.md), [Red Hat OCP 4.22 updating clusters](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/updating_clusters/).
