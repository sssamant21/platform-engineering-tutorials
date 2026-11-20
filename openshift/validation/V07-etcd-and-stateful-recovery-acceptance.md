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

## Rehearsal measurement and independent evidence template

Use this **only after an approved, isolated recovery rehearsal**; leave all values `NOT TESTED` until measured. Record UTC timestamps from a consistent time source and note clock uncertainty.

| Field | Recorded value |
| --- | --- |
| Change / exercise ID and reviewer | NOT TESTED |
| Sanitized cluster identity, exact OCP version, topology | NOT TESTED |
| Recovery scope: platform API state versus each application's data | NOT TESTED |
| Last recoverable consistent point (UTC) | NOT TESTED |
| Failure reference time (UTC) | NOT TESTED |
| Recovery decision / start time (UTC) | NOT TESTED |
| API restored and usable (UTC) | NOT TESTED |
| Critical application data validated (UTC), by service | NOT TESTED |
| Approved platform and per-service RPO/RTO targets | NOT TESTED |
| Measured data-loss window and service unavailability | NOT TESTED |
| Snapshot integrity, paired resources, external dependencies | NOT TESTED |
| Independent approvers and linked sanitized evidence | NOT TESTED |

**Measurement rules:** RPO measures the difference between the failure reference time and the latest *verified recoverable consistent data point* for the specific system. RTO measures the interval from the agreed service-disruption start to the agreed restored-service acceptance point. Document these definitions in the change ticket before testing; do not substitute backup creation time for proven recoverability, or API availability for application recovery. Report each application separately. If a reference time or consistency point is missing, record **NOT MEASURABLE**, not PASS.

**Failure injection and restore are state-changing operations.** The worksheet does not authorize them. Require approved scope, isolated infrastructure, named incident/change authority, a validated backup, explicit abort criteria and an independent observer. If a recovery attempt exceeds the approved time budget, stop at the predefined decision gate and escalate rather than improvising a production restore.

## Approval and stop conditions

**Stop** when the snapshot age is unknown, static-resource pairing is absent, topology is unsupported, the cluster identity differs from the ticket, storage/database consistency is unverified, or required approvals are missing. Escalate to the platform incident commander, application/database owners, storage team and Red Hat/provider support as applicable. The change record must identify recovery order, communications, expected data loss, fallback decision and measurable validation criteria.

## Review disposition

- Documentation drafted: **yes**.
- Source/command review for exact installed release: **pending**.
- Isolated backup/restore execution and timed RPO/RTO evidence: **not run**.
- Independent platform, security and DBRE approval: **pending**.
- Production-approved: **no**.

Authoritative baseline: [Red Hat OpenShift 4.22 Backup and restore](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/backup_and_restore/). Confirm the exact version-specific recovery procedure before any change.
