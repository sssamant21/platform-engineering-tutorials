# Runbook — etcd Backup and Recovery Readiness Triage

**Status:** Draft / not production-approved. **Scope:** Assessment and escalation only; no restore commands.

## Trigger
Backup freshness alert, missing backup attestation, API/control-plane outage, suspected etcd quorum loss, or application recovery gap.

## Safe first response
1. Declare incident severity per local policy and establish incident commander. Confirm cluster alias, exact OCP version, topology, and authorized context; never expose tokens.
2. If the API is reachable, perform the least-privilege preflight below and run **only** reads individually authorized as `yes`. Do not substitute `get` for `list`: named `clusterversion/version` requires `get`, while ClusterOperator and node collections require `list`. For control-plane nodes, the label selector does not reduce the cluster-scoped `list nodes` permission requirement. If API access is unavailable, use approved out-of-band monitoring and provider escalation; do not attempt recovery by guessing commands.

   **Linux/macOS (Bash; authenticated `oc` context required):**

   ```bash
   oc whoami
   oc config current-context
   oc auth can-i get clusterversions.config.openshift.io/version
   oc auth can-i list clusteroperators.config.openshift.io
   oc auth can-i list nodes
   # Execute each read only after its matching check returns yes:
   oc get clusterversion version
   oc get clusteroperators
   oc get nodes -l node-role.kubernetes.io/master
   ```

   **Windows PowerShell (same permission requirements):**

   ```powershell
   oc whoami
   oc config current-context
   oc auth can-i get clusterversions.config.openshift.io/version
   oc auth can-i list clusteroperators.config.openshift.io
   oc auth can-i list nodes
   # Run each matching oc get only when the corresponding check returns yes:
   oc get clusterversion version
   oc get clusteroperators
   oc get nodes -l node-role.kubernetes.io/master
   ```

   These are **manual gates, not an automatically gated script**: do not copy/paste the entire block blindly. Expected `can-i` output is `yes` or `no`; `no`, `Forbidden`, missing authentication, or an indeterminate error means **skip that read**, preserve sanitized error text and request access through the designated cluster owner. Never switch to a privileged context solely to complete triage. `oc whoami` and context output can identify personnel or infrastructure; sanitize evidence before sharing.
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
