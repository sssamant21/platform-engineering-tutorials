# V03 — High-Risk OpenShift Administration Change Review Matrix

**Baseline:** Red Hat OpenShift Container Platform 4.22 (verify against the actual installed minor and patch release before any change). **Scope:** chapters 005, 008, 010, 011, 014, 015 and 017, associated labs/runbooks. **Status:** documentation review checklist only; not executed, approved or production-certified.

## Mandatory evidence for each proposed state-changing exercise

Record the change ticket, cluster identity (sanitized), OCP version, platform topology (managed/self-managed, cloud/bare metal), affected namespaces, data criticality, named owner, authorized operator, maintenance window, backup/restore evidence, preflight snapshot of health, expected effects, rollback decision point and independent approvers. Do not paste kubeconfigs, bearer tokens, Secret data, customer records or unsanitized support bundles into evidence.

Read-only access is the default for tutorials. Any create, patch, delete, drain, upgrade, restore, scale or permission change must be **separated from the diagnostic workflow** and clearly marked **approval-only**. Never interpret a successful `oc auth can-i` as authorization from change management.

| Topic | Read-only baseline to collect (RBAC permitting) | Approval-only action and risk | Required decision gate |
| --- | --- | --- | --- |
| CVO / upgrade (014) | `oc get clusterversion`; `oc get clusteroperators`; `oc get nodes` | Upgrade changes control plane and operators; downgrade is **not** a routine rollback | Supported upgrade graph, release notes, backup, operator compatibility, outage budget and vendor escalation |
| etcd recovery (015) | `oc get clusteroperators`; `oc get nodes`; review approved backup inventory without displaying sensitive archive contents | Restore can replace cluster state and invalidate newer writes | Incident commander, platform owner, recovery point/time objectives, tested restore procedure for exact topology and independent approval |
| MachineConfig / nodes (005) | `oc get machineconfigpools`; `oc get nodes` | MCP changes and drains can restart nodes or disrupt quorum | Capacity, PodDisruptionBudgets, workload placement, canary, stop thresholds and maintenance approval |
| OLM / operators (011) | `oc get subscriptions -A`; `oc get csv -A` | InstallPlan approval or operator changes can affect controllers and CRDs | Channel/version compatibility, CRD impact, supported rollback plan and owner approval |
| Storage / stateful HA (008, 017) | `oc get pvc -A`; `oc get storageclasses` | PVC deletion, storage migration and failover can cause irreversible data loss or split brain | Storage and DBRE owners, application-consistent backup, fencing and single-writer proof, restore test |
| RBAC / SCC (010) | `oc auth can-i --list -n <approved-namespace>` (only where permitted); scoped binding inventory | Role, ClusterRoleBinding or SCC changes can grant privilege | Security review, least privilege, affected service accounts, expiry and access recertification |

These examples are **observation only**, but cluster-wide list operations may be denied and may expose infrastructure metadata. Check access first, skip denied reads, sanitize output, and escalate through the normal owner rather than elevating privileges. Replace placeholders; do not paste them literally.

## Stop and escalation conditions

Stop immediately if cluster version/topology is unknown, CVO or critical Cluster Operators are degraded, a backup cannot be verified, quorum/fencing is uncertain, an unexpected permission is required, or the proposed recovery depends on an untested downgrade. Escalate to the platform incident commander; involve DBRE for stateful data and security for access changes. Preserve sanitized timestamps, symptoms and command exit status.

## Validation status and release-specific sources

- **Drafted:** review matrix and safety gates.
- **Not completed:** OCP 4.22 command-by-command documentation comparison, isolated lab execution, negative-case evidence, independent reviewer signatures, production approval.
- Authoritative baseline to consult for each procedure: [Red Hat OpenShift 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22), particularly Updating clusters, Backup and restore, Machine configuration, Operators, Authentication and authorization, and Storage.
- Confirm the actual cluster version and platform-specific vendor guidance before approving any state-changing command. This matrix is not a substitute for an executable recovery runbook.

Related: [V01 gates](V01-documentation-security-and-runtime-evidence-gates.md), [progress tracker](../PROGRESS-TRACKER.md).
