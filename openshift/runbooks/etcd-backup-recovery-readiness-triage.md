# Runbook — etcd Backup and Recovery Readiness Triage

**Status:** Draft / not production-approved. **Scope:** Assessment and escalation only; no restore commands.

## Trigger
Backup freshness alert, missing backup attestation, API/control-plane outage, suspected etcd quorum loss, or application recovery gap.

## Safe first response
1. Declare incident severity per local policy and establish incident commander. Confirm cluster alias, exact OCP version, topology, and authorized context; never expose tokens.
2. If API is reachable, gather read-only `oc get clusterversion`, `oc get co`, `oc get nodes -l node-role.kubernetes.io/master` and timestamps. If API is unavailable, use approved out-of-band monitoring and provider escalation; do not repeatedly issue destructive recovery commands.
3. Ask backup owner to **attest**, without sharing sensitive artifacts, to last successful supported backup, matching static resources, protected off-cluster retention, and restore rehearsal. Separate etcd backup assurance from CSI/PV and database backups.
4. Classify: transient API/network issue; operator degradation; single control-plane node failure; confirmed quorum loss; workload data failure. Do not use etcd restore for routine node, Route or PVC incidents.
5. Record recovery objectives and business risk: API RPO/RTO versus per-database RPO/RTO, last verified restore, potential loss of API changes since snapshot.

## Escalation and authorization
- **Platform SRE/cluster owner:** control-plane diagnosis and approved supported recovery plan.
- **Red Hat/provider support:** unsupported or uncertain topology, quorum-loss recovery, or ambiguous version-specific procedure.
- **Security/backup owner:** artifact encryption, restricted access, chain of custody, retention.
- **DBRE/application/data owner:** WAL/log/PVC restore sequence, consistency checks, transaction/data-loss sign-off.
- **Incident commander/change manager:** business impact, maintenance window, go/no-go, rollback limitations, communications.

## Stop / no-go conditions
Unknown cluster identity, missing or unverified snapshot/static-resource pair, uncertain release compatibility, absent approvals, no data-loss estimate, unprotected credentials, or unresolved application recovery dependency. Recovery is a high-risk state-changing procedure; never infer it is reversible. Use the exact OCP 4.22 (or installed-version) Red Hat documented workflow only after approval, in a separate authorized execution plan.

## Post-recovery acceptance (for separately authorized exercise)
Check API health, CVO/ClusterOperators, nodes and MCPs, storage, networking/routes, RBAC, application service checks and database consistency; collect actual timings, data-loss estimate, approval records and independent reviewer sign-off. A successful API response alone is insufficient.

[Chapter](../chapters/015-etcd-backup-platform-and-application-recovery.md) · [Read-only lab](../labs/015-recovery-read-only-readiness-audit.md) · [Red Hat 4.22 backup and restore](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/backup_and_restore/)
