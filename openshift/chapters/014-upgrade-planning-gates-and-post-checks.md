# Chapter 014 — OpenShift Upgrade Planning, Gates and Post-Checks

**Audience:** Platform administrators, SREs, DBREs | **Duration:** ~60 minutes | **Baseline:** OCP 4.22 | **Status:** Drafted; not cluster-tested or production-approved.

## Outcomes and prerequisites
Understand CVO-managed updates, distinguish recommended/available updates from supported paths, build a change plan, and interpret upgrade health without changing the cluster. Prerequisites: approved read-only access to ClusterVersion, ClusterOperators, nodes and MachineConfigPools; installed compatible `oc`; identified cluster, platform type, maintenance owner, change ticket, SLOs and support contacts. Start with [Kubernetes fundamentals](../../kubernetes/README.md), [Chapter 004](004-cluster-operators-cvo-and-update-state.md) and [Chapter 013](013-capacity-resource-pressure-and-autoscaling.md).

## Update model and safety boundaries
The Cluster Version Operator (CVO) reconciles the desired release payload and reports progress through `clusterversion/version`. ClusterOperators and MachineConfigPools have separate health and rollout conditions. OCP minor-version updates must follow Red Hat's **exact source-to-target supported update graph**, channel, architecture, platform and conditional update risks; a version appearing in an image registry is **not** proof that the upgrade is supported. Consult the live `status.availableUpdates` and `status.conditionalUpdates` and the version-specific Red Hat documentation. A successful CVO version transition alone does not certify application availability.

**No production `oc adm upgrade`, channel edits, MachineConfigPool pauses, node drains, reboot, force flags or manual operator overrides are authorized by this tutorial.** Downgrades are not a general-purpose rollback mechanism; plan recovery with Red Hat Support and documented backups. For stateful PostgreSQL, Kafka, MongoDB and Redis, require owners to approve disruption budgets, quorum, replica placement, storage health, backups and application-level recovery.

## Read-only baseline (Linux, macOS, PowerShell)
```sh
oc whoami
oc config current-context
oc version
oc auth can-i get clusterversions.config.openshift.io
oc auth can-i list clusteroperators.config.openshift.io
oc get clusterversion version
oc get clusterversion version -o json
oc get clusteroperators
oc get mcp
oc get nodes
oc get pods -A --field-selector=status.phase!=Running
```
**Caution:** Non-Running pods include completed Jobs; classify before escalating. `oc config current-context` may expose an environment identifier, not credentials; do not export full kubeconfig or token-bearing command output. `oc get clusterversion -o json` may contain cluster metadata; sanitize before sharing. A permission-denied response is a least-privilege boundary, not a reason to escalate permissions automatically.

Interpret `Available=True`, `Progressing=False`, `Degraded=False` on ClusterOperators as a typical healthy baseline, while checking transition timestamps, operator-specific messages, CVO history, MCP `UPDATED`/`UPDATING`/`DEGRADED` and node readiness. Never infer that an update is safe solely from green conditions.

## Production change gates (planning only)
1. **Compatibility:** Record current version, target, recommended/conditional update status, Red Hat advisory, known issues, supported upgrade edges, architecture and provider constraints.
2. **Dependencies:** Validate Operators/OLM compatibility, storage CSI, network ingress, MachineConfigPools, workload APIs, external integrations and certificates.
3. **Capacity and data:** Confirm node surge/headroom, PodDisruptionBudgets, topology spread, database quorum, application backups and a separately tested recovery path.
4. **Governance:** Obtain named platform, security, application/DBRE and change-management approvals, maintenance window, communication plan, abort criteria and Red Hat escalation route.
5. **Execution:** Only an authorized operator follows the approved Red Hat procedure; this chapter supplies **no** executable upgrade step.
6. **Post-check:** Compare CVO history, ClusterOperator and MCP conditions, node readiness, pod restarts, routes, storage attachment, app SLIs and replication lag against the recorded baseline. Continue heightened monitoring through the agreed observation window.
7. **Failure decision:** Stop further changes, preserve sanitized evidence, escalate; do not attempt arbitrary version rollback, force completion or etcd restore without a supported recovery plan and approvals.

## Expected observations and common errors
- `Forbidden`: RBAC scope insufficient; request a scoped read-only evidence collector.
- `Unable to connect to the server`: verify VPN/API endpoint, context and certificate trust without bypassing TLS.
- `Progressing=True`: could indicate ongoing reconciliation; compare messages and timestamps, not an automatic failure.
- `Degraded=True` or MCP degraded: hold change gate; use [upgrade triage runbook](../runbooks/upgrade-cvo-mcp-triage.md).
- No `availableUpdates`: may reflect graph connectivity, channel, eligibility or current version; **do not** invent a target or force an update.

## Practice and validation
Complete [Lab 014](../labs/014-upgrade-read-only-preflight.md) with sanitized evidence, a go/no-go decision and failure scenarios. Lab pass requires commands and interpretation recorded in an authorized isolated cluster; documentation review alone is not a runtime pass.

## Authoritative baseline
- [Red Hat OCP 4.22 — Updating clusters](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/updating_clusters/)
- [Red Hat OCP 4.22 documentation index](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [Red Hat OCP 4.22 — Backup and restore](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/backup_and_restore/)

**Version-specific source review and live execution remain pending.** Check official documentation again at change time; this draft is not an upgrade authorization.
