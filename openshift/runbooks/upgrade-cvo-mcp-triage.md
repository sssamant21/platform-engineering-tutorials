# Runbook — Upgrade, CVO and MachineConfigPool Triage

**Status:** Draft / not production-certified. **Scope:** Read-only investigation of a failed, blocked or stalled OCP 4.22 update. **Owner:** Platform/SRE incident commander with Red Hat Support escalation as needed.

## Trigger and immediate safety
Trigger: CVO Progressing unexpectedly long, Degraded ClusterOperator, degraded MCP, NotReady nodes or application SLO breach during a planned update. Freeze unrelated changes; **do not** force update, edit ClusterVersion desired version, pause/unpause MCPs, reboot/drain nodes or restore etcd from this runbook. Declare severity using actual customer impact and change policy.

## Read-only triage
```sh
oc whoami
oc config current-context
oc get clusterversion version -o json
oc get co
oc get mcp
oc get nodes
oc get events -A --sort-by=.lastTimestamp
```
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
