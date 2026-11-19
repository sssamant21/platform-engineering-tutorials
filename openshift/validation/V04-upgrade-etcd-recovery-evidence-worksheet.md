# V04 — OCP 4.22 Upgrade and etcd Recovery Evidence Worksheet (Draft)

**Status:** documentation-only template; NOT executed, lab-tested, independently reviewed or production-approved. Use alongside [V03 change review matrix](V03-high-risk-change-review-matrix.md), Chapter 014 (upgrade) and Chapter 015 (etcd backup/recovery). This is an evidence worksheet, not an executable recovery runbook.

## Scope and prerequisite gate

- Record cluster identifier **without** copying kubeconfig, tokens, certificates or credentials; environment (isolated lab/staging/production); OCP version; platform (bare metal/vSphere/cloud); control-plane topology; change ticket; named platform owner, SRE/DBRE reviewer and business owner.
- Confirm the *installed* OCP release and supported upgrade graph with Red Hat's 4.22 documentation and the cluster's available update recommendations. Do not infer an upgrade path from the target version alone.
- Record current cluster health before proposing any change. Collect only metadata approved for the evidence store; redact internal addresses, usernames and sensitive annotations.
- Require an approved maintenance window, verified recent restore-capable backups, storage capacity, incident communications, and a documented stop/escalation decision. A backup file existing is not proof of a successful restore.

## Read-only evidence capture (authorized operator)

Run each command only if its resource permission is granted. These are **examples for an approved diagnostic session**, not claims of execution:

```sh
oc whoami
oc version
oc auth can-i get clusterversions.config.openshift.io --resource-name=version
oc auth can-i list clusteroperators.config.openshift.io
oc auth can-i list nodes
oc auth can-i list machineconfigpools.machineconfiguration.openshift.io
oc get clusterversion version -o json
oc get clusteroperators
oc get nodes
oc get machineconfigpools
```

For PowerShell, run the same individual `oc` commands; avoid piping sensitive JSON into shared logs. The displayed reads are an inventory, **not a single executable block**: evaluate each `can-i` result first, then run only the matching authorized `oc get` command. **Only run a read when its corresponding `can-i` check returns yes.** For `oc get clusterversion version`, `get` must be authorized for the named resource; a `list` grant is not equivalent. If any preflight is denied or inconclusive, skip the read and ask the cluster administrator for a sanitized report. Some cluster-scoped reads may require additional authorization.

Record timestamp (UTC), sanitized output path, command exit code, and reviewer for each observation. Expected healthy signals include stable cluster version conditions, available/non-degraded Operators and ready nodes; do not equate these broad signals with full application health. Document every anomalous condition rather than silently accepting it.

## Upgrade review gates (Chapter 014)

| Gate | Evidence required | Decision |
| --- | --- | --- |
| Version and path | Installed version, target, supported graph, release notes and known issues | PASS / HOLD |
| Platform readiness | Operator conditions, node/MCP health, capacity, critical workloads and disruption budgets | PASS / HOLD |
| Recovery readiness | Supported backups, restore rehearsal evidence, owner and RPO/RTO | PASS / HOLD |
| Change approval | Named change authority, maintenance window, rollback/contingency plan and communications | PASS / HOLD |
| Post-change | Cluster version, Operators, nodes, routes, storage and application SLO checks | PASS / HOLD |

**Stop conditions:** degraded critical Operators, unready control-plane nodes, unresolved MCP rollout, missing restore evidence, unsupported upgrade path or absent approval. Upgrades are not assumed to support a simple downgrade; use Red Hat's release-specific recovery guidance and escalate before attempting any reversal.

## etcd backup and recovery gates (Chapter 015)

- Confirm the official OCP 4.22 procedure appropriate to the platform/topology and the exact release. Capture the official documentation URL and access date in the change ticket.
- Record backup timestamp, storage location (reference only), encryption/access controls, retention, restore test date, and measured RPO/RTO. Never commit snapshot archives, keys, kubeconfigs or credential-bearing output.
- Identify control-plane quorum, failure domain, static-pod/revision implications, and dependency impact. **Do not run backup/restore, node replacement, force quorum, or control-plane changes from this worksheet.**
- Require explicit incident commander and platform owner authorization plus an independent reviewer before any recovery operation. Confirm fencing/single-writer requirements where applicable.
- Restore execution must use an approved, version-matched Red Hat runbook in an isolated rehearsal first. Record failure cases and independent acceptance of post-restore cluster and application consistency.

## Evidence record

| Field | Value |
| --- | --- |
| UTC timestamp / change ID | PENDING |
| Cluster/version/topology (sanitized) | PENDING |
| Read-only authorization and output checks | NOT RUN |
| Upgrade support/path verification | NOT REVIEWED |
| Backup/restore rehearsal reference | NOT PROVIDED |
| Independent technical reviewer | PENDING |
| Platform/change approval | PENDING |
| Runtime/lab status | NOT TESTED |
| Production acceptance | NOT APPROVED |

## Authoritative references

- [Red Hat OpenShift Container Platform 4.22 documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22)
- [OCP 4.22 Updating clusters](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/updating_clusters/index)
- [OCP 4.22 Backup and restore](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/backup_and_restore/index)

**Validation boundary:** Links and exact version-specific commands must be checked against live official documentation before operational use; no cluster access or official release-specific command certification is claimed here.
