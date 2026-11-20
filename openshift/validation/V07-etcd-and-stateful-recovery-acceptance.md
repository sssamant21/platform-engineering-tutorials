# V07 — etcd and stateful recovery acceptance gates

**Scope:** OpenShift 4.22 baseline; apply the recovery procedure for the exact installed version and deployment topology. **Status:** Drafted review worksheet; no restore, backup, or cluster test executed.

This worksheet supplements [Chapter 015](../chapters/015-etcd-backup-platform-and-application-recovery.md), [Lab 015](../labs/015-recovery-read-only-readiness-audit.md), [Chapter 017](../chapters/017-stateful-services-ha-and-data-safety.md), and the [recovery runbook](../runbooks/etcd-backup-recovery-readiness-triage.md). It is not an executable restore procedure.

## Mandatory recovery boundaries

1. **Control-plane state is not application data.** An etcd backup alone does not restore PostgreSQL WAL, MongoDB oplog, Kafka log segments, Redis persistence, PVC block data, object stores, or external identity/DNS systems.
2. **Supported backup set.** Verify the OpenShift-prescribed snapshot and associated static pod resources are paired, complete, encrypted, access-controlled and retained off cluster. Do not treat an arbitrary etcdctl snapshot as equivalent.
3. **Topology and version.** Record OCP exact release, installation/platform type, control-plane topology and recovery scenario. For hosted/managed variants, obtain provider-specific recovery authority. Do not apply self-managed control-plane steps blindly.
4. **No routine rollback assumption.** An etcd restore can discard API state created after the snapshot and may require reconciliation of external controllers and applications. Rollback is a separate recovery decision, not an inverse command.
5. **Never perform a live rehearsal on production.** Require an isolated authorized test environment and an independent reviewer.

## Evidence matrix (complete without secrets)

| Gate | Required sanitized evidence | Acceptance criterion |
| --- | --- | --- |
| Cluster identity | Alias, exact release, topology, UTC time, authorized reviewer | All match the change scope |
| Backup ownership | Named platform owner, retention policy, latest backup UTC | Ownership and retention approved |
| Artifact integrity | Approved verification method, checksum/integrity result, snapshot + static-resource pairing | Verified complete; never attach artifacts |
| Restore compatibility | Exact Red Hat release-specific procedure and support/provider confirmation | Applicable to this topology |
| Platform RPO/RTO | Approved targets, snapshot age, timed isolated restore | Measured results within approved objectives |
| App/database recovery | Per-service backup owner, consistency method, log retention, dependency map | Independent data restore verified |
| Storage | CSI driver, VolumeSnapshot support where used, topology, encryption key availability | Supported recovery path demonstrated |
| Security | Secret handling, encryption key custody, RBAC and break-glass approvals | Least privilege and audit trail confirmed |
| Post-recovery | API, CVO/CO, nodes/MCP, DNS/routes, PVC, workload and data consistency | Independent owner sign-off |
| Stop/rollback | Incident commander, abort thresholds, alternate recovery plan, escalation | Explicit decision and approvers recorded |

**Record each gate as PASS / FAIL / NOT TESTED / NOT APPLICABLE with rationale.** A documented backup is not proof of a successful restore. An isolated rehearsal does not certify a production topology without independent review.

## Read-only preparation

Only with authorized access and verified context, use:

```sh
oc whoami
oc config current-context
oc version
oc get clusterversion
oc get clusteroperators
oc get nodes
oc get machineconfigpools
```

For PowerShell, the same `oc` commands apply. Do not print kubeconfig, tokens, Secret resources, snapshot contents, raw backup paths or encryption keys. A `Forbidden` response means request approved read-only access; never escalate privileges automatically. Missing API connectivity means mark evidence unavailable rather than claiming health.

## Approval and stop conditions

**Stop** when the snapshot age is unknown, static-resource pairing is absent, topology is unsupported, the cluster identity differs from the ticket, storage/database consistency is unverified, or required approvals are missing. Escalate to the platform incident commander, application/database owners, storage team and Red Hat/provider support as applicable. The change record must identify recovery order, communications, expected data loss, fallback decision and measurable validation criteria.

## Review disposition

- Documentation drafted: **yes**.
- Source/command review for exact installed release: **pending**.
- Isolated backup/restore execution and timed RPO/RTO evidence: **not run**.
- Independent platform, security and DBRE approval: **pending**.
- Production-approved: **no**.

Authoritative baseline: [Red Hat OpenShift 4.22 Backup and restore](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/backup_and_restore/). Confirm the exact version-specific recovery procedure before any change.
